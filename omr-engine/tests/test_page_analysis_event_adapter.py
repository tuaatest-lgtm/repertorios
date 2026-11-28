import pytest

from palermo_omr.page_analysis_event_adapter import build_event_candidates_from_page_analysis


def _page():
    return {
        "page_number": 2,
        "staves": [{"lines_y": [40, 50, 60, 70, 80], "spacing_px": 10, "confidence": 0.9}],
        "notehead_candidates": [
            {"bbox": [20, 50, 10, 8], "center_x": 25, "center_y": 54,
             "staff_index": 0, "diatonic_step_from_bottom": 1,
             "fill_ratio": 0.8, "notehead_shape_score": 0.9, "confidence": 0.9},
            {"bbox": [80, 50, 10, 8], "center_x": 85, "center_y": 54,
             "staff_index": 0, "diatonic_step_from_bottom": 2,
             "fill_ratio": 0.8, "notehead_shape_score": 0.9, "confidence": 0.9},
        ],
        "rhythm_candidates": [
            {"notehead_bbox": [20, 50, 10, 8], "staff_index": 0, "notehead_fill": "filled",
             "notehead_fill_score": 0.9, "stem_direction": "up", "stem_length_px": 35,
             "beam_count": 0, "base_duration": "quarter", "confidence": 0.9, "warnings": []},
            {"notehead_bbox": [80, 50, 10, 8], "staff_index": 0, "notehead_fill": "filled",
             "notehead_fill_score": 0.9, "stem_direction": "up", "stem_length_px": 35,
             "beam_count": 0, "base_duration": "quarter", "confidence": 0.9, "warnings": []},
        ],
        "rhythmic_interpretation_candidates": [
            {"notehead_index": 0, "staff_index": 0, "duration_candidate": "quarter",
             "beam_count_candidate": 0, "beam_group_indices": [], "confidence": 0.9,
             "status": "resolved", "warnings": []},
            {"notehead_index": 1, "staff_index": 0, "duration_candidate": "quarter",
             "beam_count_candidate": 0, "beam_group_indices": [], "confidence": 0.9,
             "status": "resolved", "warnings": []},
        ],
        "beam_group_candidates": [],
    }


def test_builds_page_prefixed_fused_events_from_aligned_raw_analysis():
    pitches = [
        {"staff_index": 0, "status": "resolved_from_supplied_clef", "pitch": {"midi": 64}},
        {"staff_index": 0, "status": "resolved_from_supplied_clef", "pitch": {"midi": 65}},
    ]
    result = build_event_candidates_from_page_analysis(
        _page(), pitches, ["p2-head-0", "p2-head-1"],
    )
    assert [item["event_id"] for item in result["event_candidates"]] == [
        "p2-staff-1-event-1", "p2-staff-1-event-2",
    ]
    assert all(item["status"] == "incomplete_candidate" for item in result["event_candidates"])
    assert all(item["voice_id_candidate"] is None for item in result["event_candidates"])


def test_fusion_accepts_pitch_candidate_mappings_and_keeps_unresolved_height():
    pitches = [
        {"staff_index": 0, "status": "resolved_from_supplied_clef", "pitch": {"midi": 64}},
        {"staff_index": 0, "status": "unresolved_clef", "pitch": None},
    ]
    result = build_event_candidates_from_page_analysis(
        _page(), pitches, ["head-0", "head-1"],
    )
    assert result["event_candidates"][0]["pitch_candidates"][0]["pitch"]["midi"] == 64
    assert result["event_candidates"][1]["status"] == "incomplete_candidate"
    assert result["event_candidates"][1]["pitch_candidates"][0]["pitch"] is None


def test_rejects_unaligned_or_duplicate_page_notehead_ids():
    pitches = [
        {"staff_index": 0, "status": "resolved_from_supplied_clef", "pitch": {"midi": 64}},
        {"staff_index": 0, "status": "resolved_from_supplied_clef", "pitch": {"midi": 65}},
    ]
    with pytest.raises(ValueError, match="alinearse"):
        build_event_candidates_from_page_analysis(_page(), pitches, ["only-one"])
    with pytest.raises(ValueError, match="únicos"):
        build_event_candidates_from_page_analysis(_page(), pitches, ["same", "same"])
