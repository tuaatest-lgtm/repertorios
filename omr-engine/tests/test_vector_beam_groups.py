from dataclasses import replace

import pytest

from palermo_omr.beam_groups import BeamGroupCandidate
from palermo_omr.imaging import StaffCandidate
from palermo_omr.rhythm import RhythmCandidate
from palermo_omr.symbols import NoteheadCandidate
from palermo_omr.vector_beam_groups import (
    apply_vector_stem_candidates,
    detect_vector_beam_group_candidates,
    detect_vector_stem_candidates,
    merge_beam_group_candidates,
)


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Rect:
    def __init__(self, x0, y0, x1, y1):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1


def _head(x, y, staff=0):
    return NoteheadCandidate(
        bbox=(x, y - 4, 12, 8), center_x=x + 6, center_y=y,
        staff_index=staff, diatonic_step_from_bottom=2,
        fill_ratio=.8, notehead_shape_score=.92, confidence=.9,
    )


def _line(x, y0, y1):
    return {"type": "s", "color": (0, 0, 0),
            "items": [("l", Point(x, y0), Point(x, y1))]}


def _beam(x1, y1, x2, y2, thickness=3):
    points = [(x1, y1), (x2, y2), (x2, y2 + thickness), (x1, y1 + thickness)]
    items = [
        ("l", Point(*points[0]), Point(*points[1])),
        ("l", Point(*points[1]), Point(*points[2])),
        ("l", Point(*points[2]), Point(*points[3])),
        ("l", Point(*points[3]), Point(*points[0])),
    ]
    return {
        "type": "f", "fill": (0, 0, 0),
        "rect": Rect(x1, min(y1, y2), x2, max(y1, y2) + thickness),
        "items": items,
    }


def _drawings(two_beams=True, slope=0.12):
    first, second = _head(40, 59), _head(80, 64)
    y1, y2 = 36, 36 + (40 * slope)
    drawings = [_line(50, 20, 59), _line(90, 25, 64), _beam(50, y1, 90, y2)]
    if two_beams:
        drawings.append(_beam(50, y1 + 5, 90, y2 + 5))
    return drawings, [first, second]


def _rhythm(staff=0):
    return RhythmCandidate(
        (40, 55, 12, 8), staff, "filled", .9, "none", 0,
        0, "unknown", .45, ("Cabeza rellena sin plica confirmada.",),
    )


def test_vector_stems_recover_up_direction_from_pdf_paths():
    drawings, heads = _drawings()
    candidates = detect_vector_stem_candidates(
        drawings, [StaffCandidate([40, 50, 60, 70, 80], 10, 1)], heads, dpi=72,
    )
    assert len(candidates) == 2
    assert {item.direction for item in candidates} == {"up"}
    assert all(item.status == "candidate_from_pdf_vector" for item in candidates)
    assert all(item.confidence <= .78 for item in candidates)


def test_vector_stem_candidates_fill_only_missing_raster_directions():
    drawings, heads = _drawings()
    candidates = detect_vector_stem_candidates(
        drawings, [StaffCandidate([40, 50, 60, 70, 80], 10, 1)], heads, dpi=72,
    )
    rhythms = [_rhythm(), replace(_rhythm(), stem_direction="down", base_duration="quarter")]
    result = apply_vector_stem_candidates(rhythms, candidates)
    assert result[0].stem_direction == "up"
    assert result[0].base_duration == "quarter"
    assert result[0].confidence <= .78
    assert "Plica candidata recuperada" in result[0].warnings[-1]
    assert result[1].stem_direction == "down"


@pytest.mark.parametrize("slope", [-0.18, -0.12, 0.12, 0.18])
def test_vector_beam_groups_support_moderately_sloped_beams(slope):
    drawings, heads = _drawings(two_beams=True, slope=slope)
    groups = detect_vector_beam_group_candidates(
        drawings, [StaffCandidate([40, 50, 60, 70, 80], 10, 1)], heads,
    )
    assert len(groups) == 1
    assert groups[0].notehead_indices == [0, 1]
    assert groups[0].beam_count_candidate == 2
    assert groups[0].connection_type_candidate == "shared"


def test_single_vector_flag_is_kept_as_partial_candidate():
    head = _head(40, 59)
    drawings = [_line(50, 20, 59), _beam(50, 36, 75, 39)]
    groups = detect_vector_beam_group_candidates(
        drawings, [StaffCandidate([40, 50, 60, 70, 80], 10, 1)], [head], dpi=72,
    )
    assert len(groups) == 1
    assert groups[0].notehead_indices == [0]
    assert groups[0].connection_type_candidate == "partial"


def test_vector_beam_without_stem_connections_is_not_promoted():
    drawings, heads = _drawings()
    drawings = drawings[:2] + [_beam(120, 10, 160, 15)]
    groups = detect_vector_beam_group_candidates(
        drawings, [StaffCandidate([40, 50, 60, 70, 80], 10, 1)], heads,
    )
    assert groups == ()


def test_vector_detector_returns_empty_for_raster_only_pages():
    staves = [StaffCandidate([40, 50, 60, 70, 80], 10, 1)]
    assert detect_vector_stem_candidates([], staves, [_head(40, 59)]) == ()
    assert detect_vector_beam_group_candidates([], staves, [_head(40, 59)]) == ()


def test_vector_beam_merge_prefers_shared_group_over_duplicate_partial():
    partial = BeamGroupCandidate(0, [0], (50, 36, 25, 3), 1, .55, "partial", "partial")
    shared = BeamGroupCandidate(0, [0, 1], (50, 36, 40, 3), 1, .72, "shared", "shared")
    duplicate = BeamGroupCandidate(0, [0, 1], (50, 36, 40, 3), 1, .68, "duplicate", "shared")
    result = merge_beam_group_candidates([partial, duplicate], [shared])
    assert len(result) == 2
    assert next(item for item in result if item.notehead_indices == [0, 1]) == shared


def test_rejects_invalid_dpi_and_stem_candidate_indices():
    with pytest.raises(ValueError, match="dpi"):
        detect_vector_stem_candidates([], [StaffCandidate([1, 2, 3, 4, 5], 2, 1)], [_head(40, 59)], dpi=30)
    with pytest.raises(ValueError, match="inexistente"):
        apply_vector_stem_candidates([], [
            type("Candidate", (), {"notehead_index": 0, "direction": "up", "confidence": .7})()
        ])
