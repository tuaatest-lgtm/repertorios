import cv2
import numpy as np
import pytest

from palermo_omr.beam_groups import detect_beam_group_candidates
from palermo_omr.imaging import StaffCandidate
from palermo_omr.rhythm import RhythmCandidate
from palermo_omr.symbols import NoteheadCandidate


def _fixture(with_beam=True, beam_count=1):
    image = np.full((160, 240), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (230, y), 0, 1)
    heads = [
        NoteheadCandidate((97, 75, 16, 10), 105.0, 80.0, 0, 2, .8, .9, .9),
        NoteheadCandidate((137, 75, 16, 10), 145.0, 80.0, 0, 2, .8, .9, .9),
    ]
    for x in [105, 145]:
        cv2.ellipse(image, (x, 80), (8, 5), -20, 0, 360, 0, -1)
    for x in [112, 152]:
        cv2.line(image, (x, 80), (x, 35), 0, 2)
    if with_beam:
        for offset in range(beam_count):
            y = 35 + offset * 7
            cv2.line(image, (112, y), (152, y), 0, 3)
    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)
    rhythms = [
        RhythmCandidate(head.bbox, 0, "filled", .9, "up", 30, 1,
                        "eighth", .8, ())
        for head in heads
    ]
    return image, [staff], heads, rhythms


def test_groups_two_noteheads_connected_by_shared_beam():
    image, staves, heads, rhythms = _fixture()
    groups = detect_beam_group_candidates(image, staves, heads, rhythms)
    assert len(groups) == 1
    assert groups[0].staff_index == 0
    assert groups[0].notehead_indices == [0, 1]
    assert groups[0].beam_count_candidate == 1
    assert "candidato" in groups[0].warning.lower()


def test_detects_partial_beam_attached_to_one_notehead():
    image, staves, heads, rhythms = _fixture(with_beam=False)
    cv2.line(image, (112, 35), (132, 35), 0, 3)
    groups = detect_beam_group_candidates(image, staves, heads, rhythms)
    assert len(groups) == 1
    assert groups[0].notehead_indices == [0]
    assert groups[0].beam_count_candidate == 1
    assert groups[0].connection_type_candidate == "partial"
    assert "haz parcial" in groups[0].warning.lower()


def test_does_not_group_nearby_notes_without_horizontal_beam():
    image, staves, heads, rhythms = _fixture(with_beam=False)
    assert detect_beam_group_candidates(image, staves, heads, rhythms) == []


def test_does_not_associate_a_nearby_beam_that_misses_both_stem_anchors():
    image, staves, heads, rhythms = _fixture(with_beam=False)
    # El trazo está dentro del intervalo horizontal de ambas cabezas, pero no
    # cruza las posiciones esperadas de sus plicas (x=112 y x=152).
    cv2.line(image, (120, 35), (140, 35), 0, 3)
    assert detect_beam_group_candidates(image, staves, heads, rhythms) == []


def test_does_not_group_notes_from_different_staves():
    image, staves, heads, rhythms = _fixture()
    second_staff = StaffCandidate([115, 125, 135, 145, 155], 10.0, 1.0)
    heads[1] = NoteheadCandidate(
        heads[1].bbox, heads[1].center_x, heads[1].center_y, 1, 2, .8, .9, .9
    )
    rhythms[1] = RhythmCandidate(
        heads[1].bbox, 1, "filled", .9, "up", 30, 1, "eighth", .8, ()
    )
    assert detect_beam_group_candidates(image, [staves[0], second_staff],
                                        heads, rhythms) == []


def test_rejects_mismatched_notehead_and_rhythm_lists():
    image, staves, heads, rhythms = _fixture()
    with pytest.raises(ValueError):
        detect_beam_group_candidates(image, staves, heads, rhythms[:1])



@pytest.mark.parametrize("beam_count", [1, 2, 3, 4])
def test_counts_parallel_shared_beams(beam_count):
    image, staves, heads, rhythms = _fixture(beam_count=beam_count)
    groups = detect_beam_group_candidates(image, staves, heads, rhythms)
    assert len(groups) == 1
    assert groups[0].notehead_indices == [0, 1]
    assert groups[0].beam_count_candidate == beam_count
