from fractions import Fraction

from palermo_omr.event_fusion import ScoreEventCandidate
from palermo_omr.score_document import ScoreDocument
from palermo_omr.score_structure import ScoreStaff, ScoreStructure, ScoreSystem, MeasureRegion

from palermo_omr.score_playback_bundle import (
    build_score_playback_bundle,
    build_score_playback_bundle_from_page_analyses,
)


def _candidate(event_id, staff, heads, midi, event_type="note", status="ready_for_review"):
    return ScoreEventCandidate(
        event_id=event_id, staff_index=staff,
        notehead_candidate_ids=tuple(heads),
        pitch_candidates=tuple({"pitch": {"midi": value}} for value in midi),
        voice_id_candidate="soprano" if event_type == "note" else "alto",
        duration_candidate="quarter",
        duration_quarters_candidate=Fraction(1),
        status=status, warnings=(), event_type=event_type,
    )


def _document():
    page1 = ScoreStructure(
        page_number=1,
        systems=(ScoreSystem("p1s1", 1, ("p1staff",)),),
        staves=(ScoreStaff("p1staff", 1, 0),),
        measure_regions=(MeasureRegion("p1m1", "p1s1", "p1staff", 1, 0, 200),),
    )
    page2 = ScoreStructure(
        page_number=2,
        systems=(ScoreSystem("p2s1", 2, ("p2staff",)),),
        staves=(ScoreStaff("p2staff", 2, 0),),
        measure_regions=(MeasureRegion("p2m1", "p2s1", "p2staff", 2, 0, 200),),
    )
    return ScoreDocument(pages=(page1, page2))


def test_bundle_connects_polyphonic_audio_and_visual_anchors_across_pages():
    candidates = [
        _candidate("s1", 0, ["h1"], [67]),
        _candidate("s2", 0, ["h2"], [69]),
    ]
    timelines = [
        {"measure_index": 0, "expected_quarters": "4", "events": [
            {"event_id": "s1", "event_type": "note", "voice_id": "soprano",
             "onset_quarters": "0", "duration_quarters": "1"},
        ]},
        {"measure_index": 1, "expected_quarters": "4", "events": [
            {"event_id": "s2", "event_type": "note", "voice_id": "soprano",
             "onset_quarters": "0", "duration_quarters": "1"},
        ]},
    ]
    result = build_score_playback_bundle(
        timelines, candidates, _document(),
        event_page_numbers={"s1": 1, "s2": 2},
        notehead_geometry_by_id={
            "h1": {"bbox": [30, 40, 10, 8]},
            "h2": {"bbox": [50, 60, 10, 8]},
        },
        tempo_bpm=120,
    )
    assert result["status"] == "unconfirmed_score_playback_bundle"
    assert len(result["playback_projection"]["events"]) == 2
    assert len(result["command_stream"]["commands"]) == 4
    anchors = result["visual_anchor_map"]["anchors"]
    assert [(a["event_id"], a["page_index"], a["system_index"], a["measure_index"])
            for a in anchors] == [("s1", 0, 0, 0), ("s2", 1, 0, 1)]
    assert result["coverage"]["playable_without_visual_anchor"] == []


def test_bundle_reports_missing_page_or_visual_geometry_without_guessing():
    candidates = [
        _candidate("missing-page", 0, ["h1"], [60]),
        _candidate("missing-head", 0, ["absent"], [62]),
    ]
    timelines = [{"measure_index": 0, "expected_quarters": "4", "events": [
        {"event_id": "missing-page", "event_type": "note", "voice_id": "soprano",
         "onset_quarters": "0", "duration_quarters": "1"},
        {"event_id": "missing-head", "event_type": "note", "voice_id": "soprano",
         "onset_quarters": "1", "duration_quarters": "1"},
    ]}]
    result = build_score_playback_bundle(
        timelines, candidates, _document(),
        event_page_numbers={"missing-head": 1},
        notehead_geometry_by_id={"h1": {"bbox": [10, 20, 8, 6]}},
        tempo_bpm=100,
    )
    reasons = {item["event_id"]: item["reason"] for item in result["visual_anchor_map"]["unresolved"]}
    assert reasons == {
        "missing-head": "missing_notehead_geometry",
        "missing-page": "missing_page_mapping",
    }
    assert result["coverage"]["playable_without_visual_anchor"] == ["missing-head", "missing-page"]


def test_builds_complete_bundle_from_raw_page_analysis_json():
    page = {
        "page_number": 1,
        "staves": [{"lines_y": [40, 50, 60, 70, 80], "spacing_px": 10, "confidence": 0.9}],
        "staff_system_candidates": [{
            "system_index": 0, "staff_indices": [0], "y_top": 40, "y_bottom": 80,
            "confidence": 0.65, "warning": "candidate",
        }],
        "measure_span_candidates": [{
            "staff_index": 0, "measure_index": 1, "x_start": 0, "x_end": 100,
            "width_px": 100, "left_boundary_observed": True, "right_boundary_observed": True,
            "confidence": 0.8, "warning": "candidate",
        }],
        "notehead_candidates": [{"bbox": [20, 50, 10, 6], "staff_index": 0}],
    }
    result = build_score_playback_bundle_from_page_analyses(
        [{"measure_index": 0, "expected_quarters": "4", "events": [{
            "event_id": "n1", "event_type": "note", "voice_id": "soprano",
            "onset_quarters": "0", "duration_quarters": "1",
        }]}],
        [_candidate("n1", 0, ["head-id"], [67])],
        [page],
        event_page_numbers={"n1": 1},
        event_notehead_indices={"n1": [0]},
        tempo_bpm=120,
    )
    assert len(result["command_stream"]["commands"]) == 2
    assert result["visual_anchor_map"]["anchors"][0]["event_id"] == "n1"
    assert result["coverage"]["playable_without_visual_anchor"] == []


def test_raw_page_bundle_does_not_guess_notehead_index_alignment():
    page = {
        "page_number": 1,
        "staves": [{"lines_y": [40, 50, 60, 70, 80], "spacing_px": 10, "confidence": 0.9}],
        "staff_system_candidates": [{
            "system_index": 0, "staff_indices": [0], "y_top": 40, "y_bottom": 80,
            "confidence": 0.65, "warning": "candidate",
        }],
        "measure_span_candidates": [{
            "staff_index": 0, "measure_index": 1, "x_start": 0, "x_end": 100,
            "width_px": 100, "left_boundary_observed": True, "right_boundary_observed": True,
            "confidence": 0.8, "warning": "candidate",
        }],
        "notehead_candidates": [{"bbox": [20, 50, 10, 6], "staff_index": 0}],
    }
    result = build_score_playback_bundle_from_page_analyses(
        [{"measure_index": 0, "expected_quarters": "4", "events": [{
            "event_id": "n1", "event_type": "note", "voice_id": "soprano",
            "onset_quarters": "0", "duration_quarters": "1",
        }]}],
        [_candidate("n1", 0, ["head-id"], [67])],
        [page], event_page_numbers={"n1": 1},
        event_notehead_indices={"n1": []}, tempo_bpm=120,
    )
    assert result["visual_anchor_map"]["anchors"] == []
    assert result["visual_anchor_map"]["unresolved"] == [
        {"event_id": "n1", "reason": "notehead_index_mapping_mismatch"},
    ]


def _raw_page(number, x):
    return {
        "page_number": number,
        "staves": [{"lines_y": [40, 50, 60, 70, 80], "spacing_px": 10, "confidence": 0.9}],
        "staff_system_candidates": [{
            "system_index": 0, "staff_indices": [0], "y_top": 40, "y_bottom": 80,
            "confidence": 0.65, "warning": "candidate",
        }],
        "measure_span_candidates": [{
            "staff_index": 0, "measure_index": 1, "x_start": 0, "x_end": 200,
            "width_px": 200, "left_boundary_observed": True, "right_boundary_observed": True,
            "confidence": 0.8, "warning": "candidate",
        }],
        "notehead_candidates": [{"bbox": [x, 50, 10, 6], "staff_index": 0}],
    }


def test_raw_page_bundle_keeps_audio_clock_contiguous_across_page_turn():
    candidates = [
        _candidate("p1n1", 0, ["head-p1"], [60]),
        _candidate("p2n1", 0, ["head-p2"], [62]),
    ]
    page_timelines = [
        {"page_number": 1, "measure_index": 0, "expected_quarters": "4", "events": [{
            "event_id": "p1n1", "event_type": "note", "voice_id": "soprano",
            "onset_quarters": "0", "duration_quarters": "1",
        }]},
        {"page_number": 2, "measure_index": 0, "expected_quarters": "4", "events": [{
            "event_id": "p2n1", "event_type": "note", "voice_id": "soprano",
            "onset_quarters": "0", "duration_quarters": "1",
        }]},
    ]
    result = build_score_playback_bundle_from_page_analyses(
        page_timelines, candidates, [_raw_page(1, 20), _raw_page(2, 40)],
        event_page_numbers={"p1n1": 1, "p2n1": 2},
        event_notehead_indices={"p1n1": [0], "p2n1": [0]},
        page_measure_global_indices={1: {0: 0}, 2: {0: 1}},
        tempo_bpm=120,
    )
    by_id = {item["event_id"]: item for item in result["playback_projection"]["events"]}
    assert by_id["p1n1"]["start_seconds"] == 0
    assert by_id["p2n1"]["start_seconds"] == 2
    assert [item["measure_index"] for item in result["document_timeline"]["timelines"]] == [0, 1]


def test_raw_page_bundle_stops_at_missing_global_measure_instead_of_compressing_time():
    candidates = [
        _candidate("p1n1", 0, ["head-p1"], [60]),
        _candidate("p2n1", 0, ["head-p2"], [62]),
    ]
    page_timelines = [
        {"page_number": 1, "measure_index": 0, "expected_quarters": "4", "events": [{
            "event_id": "p1n1", "event_type": "note", "voice_id": "soprano",
            "onset_quarters": "0", "duration_quarters": "1",
        }]},
        {"page_number": 2, "measure_index": 0, "expected_quarters": "4", "events": [{
            "event_id": "p2n1", "event_type": "note", "voice_id": "soprano",
            "onset_quarters": "0", "duration_quarters": "1",
        }]},
    ]
    result = build_score_playback_bundle_from_page_analyses(
        page_timelines, candidates, [_raw_page(1, 20), _raw_page(2, 40)],
        event_page_numbers={"p1n1": 1, "p2n1": 2},
        event_notehead_indices={"p1n1": [0], "p2n1": [0]},
        page_measure_global_indices={1: {0: 0}, 2: {0: 2}},
        tempo_bpm=120,
    )
    assert [item["event_id"] for item in result["playback_projection"]["events"]] == ["p1n1"]
    assert result["document_timeline"]["missing_global_measure_indices"] == [1]
    assert result["document_timeline"]["unresolved_measures"][0]["reason"] == "global_measure_index_gap"
