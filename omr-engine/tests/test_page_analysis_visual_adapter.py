import pytest

from palermo_omr.page_analysis_visual_adapter import (
    build_visual_anchor_map_from_page_analysis,
    evaluate_visual_anchor_coverage,
)


def page_analysis():
    return {
        "page_number": 2,
        "staves": [
            {"lines_y": [40, 50, 60, 70, 80], "spacing_px": 10, "confidence": 0.95},
            {"lines_y": [150, 160, 170, 180, 190], "spacing_px": 10, "confidence": 0.9},
        ],
        "staff_system_candidates": [
            {"system_index": 0, "staff_indices": [0], "y_top": 40, "y_bottom": 80,
             "confidence": 0.65, "warning": "staff 0"},
            {"system_index": 1, "staff_indices": [1], "y_top": 150, "y_bottom": 190,
             "confidence": 0.65, "warning": "staff 1"},
        ],
        "measure_span_candidates": [
            {"staff_index": 0, "measure_index": 1, "x_start": 0, "x_end": 100,
             "width_px": 100, "left_boundary_observed": True, "right_boundary_observed": True,
             "confidence": 0.8, "warning": "measure"},
            {"staff_index": 0, "measure_index": 2, "x_start": 100, "x_end": 200,
             "width_px": 100, "left_boundary_observed": True, "right_boundary_observed": True,
             "confidence": 0.8, "warning": "measure"},
            {"staff_index": 1, "measure_index": 1, "x_start": 0, "x_end": 200,
             "width_px": 200, "left_boundary_observed": True, "right_boundary_observed": True,
             "confidence": 0.8, "warning": "measure"},
        ],
        "notehead_candidates": [
            {"bbox": [20, 60, 10, 6], "staff_index": 0},
            {"bbox": [28, 50, 10, 6], "staff_index": 0},
            {"bbox": [130, 70, 10, 6], "staff_index": 0},
            {"bbox": [40, 160, 10, 6], "staff_index": 1},
        ],
    }


def test_page_analysis_adapter_builds_chord_and_single_note_anchors():
    result = build_visual_anchor_map_from_page_analysis(
        page_analysis(), {"chord": [0, 1], "single": [2]},
    )
    assert [(a["event_id"], a["page_index"], a["system_index"], a["measure_index"])
            for a in result["anchors"]] == [
        ("chord", 1, 0, 0), ("single", 1, 0, 1),
    ]
    assert result["notehead_id_by_index"]["2"] == "p2-head-2"


def test_page_analysis_adapter_uses_explicit_rest_geometry_and_voice_staff():
    result = build_visual_anchor_map_from_page_analysis(
        page_analysis(), {}, event_staff_indices={"rest": 1},
        event_geometry_by_id={"rest": {"bbox": [50, 160, 8, 10]}},
    )
    assert result["anchors"][0]["event_id"] == "rest"
    assert result["anchors"][0]["system_index"] == 1
    assert result["anchors"][0]["measure_index"] == 0


def test_page_analysis_adapter_keeps_cross_staff_events_unresolved():
    result = build_visual_anchor_map_from_page_analysis(
        page_analysis(), {"cross": [0, 3]},
    )
    assert result["anchors"] == []
    assert result["unresolved"] == [
        {"event_id": "cross", "reason": "cross_staff_event"},
    ]


def test_page_analysis_adapter_rejects_invalid_head_indices_and_shared_heads():
    with pytest.raises(ValueError, match="fuera del rango"):
        build_visual_anchor_map_from_page_analysis(page_analysis(), {"bad": [99]})
    with pytest.raises(ValueError, match="más de un evento"):
        build_visual_anchor_map_from_page_analysis(
            page_analysis(), {"a": [0], "b": [0]},
        )


def test_evaluates_geometry_coverage_without_claiming_music_accuracy():
    result = evaluate_visual_anchor_coverage(page_analysis())
    assert result["candidate_noteheads"] == 4
    assert result["anchored_noteheads"] == 4
    assert result["unresolved_noteheads"] == 0
    assert result["coverage_ratio"] == 1.0
    assert "no precisión" in result["warning"]
