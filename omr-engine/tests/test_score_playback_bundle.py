from fractions import Fraction

from palermo_omr.event_fusion import ScoreEventCandidate
from palermo_omr.score_document import ScoreDocument
from palermo_omr.score_structure import ScoreStaff, ScoreStructure, ScoreSystem, MeasureRegion

from palermo_omr.score_playback_bundle import build_score_playback_bundle


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
