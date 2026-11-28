import pytest

from palermo_omr.visual_anchor_map import (
    build_visual_anchor_map,
    build_visual_anchor_map_from_score_structure,
)
from palermo_omr.score_structure import MeasureRegion, ScoreStaff, ScoreStructure, ScoreSystem


def test_maps_single_notehead_geometry_to_cursor_anchor():
    result = build_visual_anchor_map(
        [{"event_id": "s1", "staff_index": 2, "notehead_candidate_ids": ["h1"]}],
        {"h1": {"bbox": [100, 50, 12, 8]}},
        page_index=0, system_by_staff={2: 1}, measure_by_event={"s1": 3},
    )
    assert result["anchors"] == [{
        "event_id": "s1", "page_index": 0, "system_index": 1,
        "measure_index": 3, "x": 98.0, "y": 48.0, "width": 16.0, "height": 12.0,
    }]
    assert result["unresolved"] == []


def test_unions_notehead_boxes_for_chord_without_losing_heads():
    result = build_visual_anchor_map(
        [{"event_id": "chord", "staff_index": 0, "notehead_candidate_ids": ["h1", "h2"]}],
        {"h1": {"bbox": [100, 50, 12, 8]}, "h2": {"bbox": [108, 40, 12, 8]}},
        page_index=1, system_by_staff={0: 0}, measure_by_event={"chord": 4},
        padding_px=0,
    )
    assert result["anchors"][0]["x"] == 100
    assert result["anchors"][0]["y"] == 40
    assert result["anchors"][0]["width"] == 20
    assert result["anchors"][0]["height"] == 18


def test_keeps_missing_geometry_and_context_unresolved():
    result = build_visual_anchor_map(
        [
            {"event_id": "missing-head", "staff_index": 0, "notehead_candidate_ids": ["absent"]},
            {"event_id": "missing-system", "staff_index": 1, "notehead_candidate_ids": ["h1"]},
            {"event_id": "rest", "staff_index": 0, "notehead_candidate_ids": []},
        ],
        {"h1": {"bbox": [10, 20, 5, 5]}},
        page_index=0, system_by_staff={0: 0}, measure_by_event={"missing-head": 0, "missing-system": 0, "rest": 0},
    )
    assert result["anchors"] == []
    assert {item["reason"] for item in result["unresolved"]} == {
        "missing_notehead_geometry", "missing_system_mapping", "missing_event_geometry",
    }


def test_maps_rest_from_explicit_glyph_geometry():
    result = build_visual_anchor_map(
        [{"event_id": "rest", "staff_index": 0, "notehead_candidate_ids": []}],
        {}, page_index=0, system_by_staff={0: 0}, measure_by_event={"rest": 0},
        event_geometry_by_id={"rest": {"bbox": [40, 60, 8, 12]}},
    )
    assert result["anchors"][0]["event_id"] == "rest"
    assert result["anchors"][0]["width"] == 12


def test_rejects_duplicate_events_and_invalid_boxes():
    with pytest.raises(ValueError, match="único"):
        build_visual_anchor_map(
            [{"event_id": "x", "staff_index": 0}, {"event_id": "x", "staff_index": 0}],
            {}, page_index=0, system_by_staff={0: 0}, measure_by_event={"x": 0},
        )
    with pytest.raises(ValueError, match="dimensiones positivas"):
        build_visual_anchor_map(
            [{"event_id": "x", "staff_index": 0, "notehead_candidate_ids": ["h"]}],
            {"h": {"bbox": [1, 2, 0, 4]}}, page_index=0,
            system_by_staff={0: 0}, measure_by_event={"x": 0},
        )


def test_derives_page_system_and_measure_from_score_structure():
    structure = ScoreStructure(
        page_number=2,
        systems=(ScoreSystem("sys-a", 2, ("staff-a", "staff-b")),
                 ScoreSystem("sys-b", 2, ("staff-c",))),
        staves=(ScoreStaff("staff-a", 2, 0), ScoreStaff("staff-b", 2, 1),
                ScoreStaff("staff-c", 2, 2)),
        measure_regions=(
            MeasureRegion("m1a", "sys-a", "staff-a", 5, 20, 100),
            MeasureRegion("m2a", "sys-a", "staff-a", 6, 100, 200),
            MeasureRegion("m1b", "sys-a", "staff-b", 5, 20, 200),
            MeasureRegion("m1c", "sys-b", "staff-c", 5, 20, 200),
        ),
    )
    result = build_visual_anchor_map_from_score_structure(
        [{"event_id": "note", "staff_index": 0, "notehead_candidate_ids": ["h1"]}],
        {"h1": {"bbox": [120, 50, 12, 8]}},
        structure,
    )
    assert result["anchors"] == [{
        "event_id": "note", "page_index": 1, "system_index": 0,
        "measure_index": 5, "x": 118.0, "y": 48.0, "width": 16.0, "height": 12.0,
    }]


def test_score_structure_adapter_does_not_guess_missing_or_overlapping_measures():
    structure = ScoreStructure(
        page_number=1,
        systems=(ScoreSystem("sys", 1, ("staff",)),),
        staves=(ScoreStaff("staff", 1, 0),),
        measure_regions=(
            MeasureRegion("m1", "sys", "staff", 1, 0, 100),
            MeasureRegion("m2", "sys", "staff", 2, 90, 200),
        ),
    )
    result = build_visual_anchor_map_from_score_structure(
        [
            {"event_id": "overlap", "staff_index": 0, "notehead_candidate_ids": ["h1"]},
            {"event_id": "outside", "staff_index": 0, "notehead_candidate_ids": ["h2"]},
        ],
        {"h1": {"bbox": [95, 40, 10, 8]}, "h2": {"bbox": [250, 40, 10, 8]}},
        structure,
    )
    assert result["anchors"] == []
    assert {item["reason"] for item in result["unresolved"]} == {
        "ambiguous_measure_region", "missing_measure_region",
    }
