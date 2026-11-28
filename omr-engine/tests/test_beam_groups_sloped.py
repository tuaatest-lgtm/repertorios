import cv2
import numpy as np
import pytest

from palermo_omr.beam_groups import detect_beam_group_candidates
from palermo_omr.imaging import StaffCandidate
from palermo_omr.rhythm import RhythmCandidate
from palermo_omr.symbols import NoteheadCandidate


@pytest.mark.parametrize("rise", [-7, 7])
def test_groups_noteheads_connected_by_sloped_beam(rise):
    image = np.full((160, 240), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (230, y), 0, 1)

    heads = [
        NoteheadCandidate((97, 75, 16, 10), 105.0, 80.0, 0, 2, .8, .9, .9),
        NoteheadCandidate((137, 75, 16, 10), 145.0, 80.0, 0, 2, .8, .9, .9),
    ]
    for x in [105, 145]:
        cv2.ellipse(image, (x, 80), (8, 5), -20, 0, 360, 0, -1)

    y_left = 39 if rise < 0 else 32
    y_right = y_left + rise
    stem_points = [(112, y_left), (152, y_right)]
    for x, beam_y in stem_points:
        cv2.line(image, (x, beam_y), (x, 80), 0, 2)
    cv2.line(image, (112, y_left), (152, y_right), 0, 3)

    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)
    rhythms = [
        RhythmCandidate(head.bbox, 0, "filled", .9, "up", 30, 1,
                        "eighth", .8, ())
        for head in heads
    ]

    groups = detect_beam_group_candidates(image, [staff], heads, rhythms)

    assert any(
        group.notehead_indices == [0, 1]
        and group.connection_type_candidate == "shared"
        for group in groups
    )
