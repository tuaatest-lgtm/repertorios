import cv2
import numpy as np

from palermo_omr.imaging import StaffCandidate
from palermo_omr.staff_grouping import detect_staff_grouping_mark_candidates


def two_staves():
    return [
        StaffCandidate([40, 50, 60, 70, 80], 10.0, 1.0),
        StaffCandidate([125, 135, 145, 155, 165], 10.0, 1.0),
    ]


def test_detects_long_vertical_mark_at_left_of_two_staff_system():
    image = np.full((220, 600), 255, dtype=np.uint8)
    cv2.line(image, (35, 40), (35, 165), 0, 2)
    results = detect_staff_grouping_mark_candidates(image, two_staves())
    assert len(results) == 1
    assert results[0].staff_indices == (0, 1)
    assert results[0].kind == "vertical_grouping_mark_candidate"
    assert "no confirma" in results[0].warning


def test_ignores_short_vertical_mark_and_marks_on_right_side():
    image = np.full((220, 600), 255, dtype=np.uint8)
    cv2.line(image, (35, 40), (35, 70), 0, 2)
    cv2.line(image, (500, 40), (500, 165), 0, 2)
    assert detect_staff_grouping_mark_candidates(image, two_staves()) == []


def test_does_not_propose_group_mark_for_single_staff():
    image = np.full((120, 300), 255, dtype=np.uint8)
    one = [StaffCandidate([20, 30, 40, 50, 60], 10.0, 1.0)]
    assert detect_staff_grouping_mark_candidates(image, one) == []


def test_validates_image_and_parameters():
    import pytest
    with pytest.raises(ValueError):
        detect_staff_grouping_mark_candidates(None, two_staves())
    image = np.full((220, 600), 255, dtype=np.uint8)
    with pytest.raises(ValueError):
        detect_staff_grouping_mark_candidates(image, two_staves(), left_margin_ratio=0)
