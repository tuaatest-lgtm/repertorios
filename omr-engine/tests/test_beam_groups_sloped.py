import cv2
import numpy as np
import pytest

from palermo_omr.beam_geometry import _find_stem_anchor, detect_local_beam_candidates
from palermo_omr.beam_groups import detect_beam_group_candidates
from palermo_omr.imaging import StaffCandidate
from palermo_omr.rhythm import RhythmCandidate
from palermo_omr.symbols import NoteheadCandidate


def _sloped_fixture(slope=-0.16, beam_count=1, with_beam=True):
    image = np.full((170, 230), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (220, y), 0, 1)

    first_x, second_x = 80, 130
    first_y = 80
    second_y = int(round(first_y + slope * (second_x - first_x)))
    heads = [
        NoteheadCandidate((72, 75, 16, 10), 80.0, float(first_y), 0, 2, .8, .9, .9),
        NoteheadCandidate((122, second_y - 5, 16, 10), 130.0, float(second_y), 0, 2, .8, .9, .9),
    ]
    for head in heads:
        cv2.ellipse(
            image,
            (int(round(head.center_x)), int(round(head.center_y))),
            (8, 5), -20, 0, 360, 0, -1,
        )

    stem_xs = [86, 136]
    anchor_ys = [40, int(round(40 + slope * 50))]
    for x, head, anchor_y in zip(stem_xs, heads, anchor_ys):
        cv2.line(
            image, (x, int(round(head.center_y))), (x, anchor_y), 0, 2
        )

    if with_beam:
        dx, dy = 50.0, float(anchor_ys[1] - anchor_ys[0])
        length = (dx * dx + dy * dy) ** .5
        nx, ny = -dy / length, dx / length
        for index in range(beam_count):
            shift = 7.0 * index
            p1 = (int(round(stem_xs[0] + nx * shift)),
                  int(round(anchor_ys[0] + ny * shift)))
            p2 = (int(round(stem_xs[1] + nx * shift)),
                  int(round(anchor_ys[1] + ny * shift)))
            cv2.line(image, p1, p2, 0, 3)

    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)
    rhythms = [
        RhythmCandidate(head.bbox, 0, "filled", .9, "up", 35, 0,
                        "quarter", .8, ())
        for head in heads
    ]
    return image, [staff], heads, rhythms


@pytest.mark.parametrize("slope", [-0.16, 0.16])
def test_detects_sloped_beam_between_stem_anchors(slope):
    image, staves, heads, rhythms = _sloped_fixture(slope=slope)
    candidates = detect_local_beam_candidates(image, staves, heads, rhythms)
    assert len(candidates) == 1
    assert candidates[0].notehead_indices == (0, 1)
    assert candidates[0].support >= .82
    assert candidates[0].slope * slope > 0


@pytest.mark.parametrize("beam_count", [1, 2, 3, 4])
def test_counts_parallel_sloped_beams_without_using_slope_as_rhythm(beam_count):
    image, staves, heads, rhythms = _sloped_fixture(
        slope=-0.16, beam_count=beam_count
    )
    groups = detect_beam_group_candidates(image, staves, heads, rhythms)
    shared = [group for group in groups if group.notehead_indices == [0, 1]]
    assert len(shared) == 1
    assert shared[0].beam_count_candidate == beam_count
    assert "pendiente no modifica el valor rítmico" in shared[0].warning


def test_does_not_invent_sloped_beam_from_staff_lines_and_stems():
    image, staves, heads, rhythms = _sloped_fixture(
        slope=-0.16, with_beam=False
    )
    assert detect_local_beam_candidates(image, staves, heads, rhythms) == []


def test_local_detector_does_not_reclassify_horizontal_beam_as_diagonal():
    image, staves, heads, rhythms = _sloped_fixture(
        slope=0.0, with_beam=True
    )
    assert detect_local_beam_candidates(image, staves, heads, rhythms) == []


def test_rejects_incompatible_stem_directions():
    image, staves, heads, rhythms = _sloped_fixture(slope=-0.16)
    rhythms[1] = RhythmCandidate(
        heads[1].bbox, 0, "filled", .9, "down", 35, 0, "quarter", .8, ()
    )
    assert detect_local_beam_candidates(image, staves, heads, rhythms) == []


def test_rejects_note_pair_farther_than_local_search_limit():
    image, staves, heads, rhythms = _sloped_fixture(slope=-0.16)
    far_head = NoteheadCandidate(
        (202, 75, 16, 10), 210.0, 80.0, 0, 2, .8, .9, .9
    )
    heads.append(far_head)
    rhythms.append(RhythmCandidate(
        far_head.bbox, 0, "filled", .9, "up", 35, 0, "quarter", .8, ()
    ))
    assert detect_local_beam_candidates(image, staves, heads, rhythms) == [
        candidate for candidate in detect_local_beam_candidates(
            image, staves, heads[:2], rhythms[:2]
        )
    ]


def test_chord_noteheads_sharing_one_stem_are_kept_in_same_beam_candidate():
    image, staves, heads, rhythms = _sloped_fixture(slope=-0.16)
    chord_head = NoteheadCandidate(
        (74, 65, 16, 10), 82.0, 70.0, 0, 4, .8, .9, .9
    )
    cv2.ellipse(image, (82, 70), (8, 5), -20, 0, 360, 0, -1)
    cv2.line(image, (86, 70), (86, 40), 0, 2)
    heads.append(chord_head)
    rhythms.append(RhythmCandidate(
        chord_head.bbox, 0, "filled", .9, "up", 30, 0, "quarter", .8, ()
    ))
    candidates = detect_local_beam_candidates(image, staves, heads, rhythms)
    assert len(candidates) == 1
    assert set(candidates[0].notehead_indices) == {0, 1, 2}



def test_stem_anchor_scan_is_clamped_at_bottom_page_edge():
    vertical_ink = np.zeros((170, 60), dtype=np.uint8)
    vertical_ink[167:170, 25] = 1
    head = NoteheadCandidate(
        (20, 160, 10, 10), 25.0, 165.0, 0, 0, .8, .9, .9
    )
    assert _find_stem_anchor(vertical_ink, head, 2.0, "down") == (25, 169, 3)
