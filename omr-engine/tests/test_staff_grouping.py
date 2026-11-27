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


def test_classifies_vertical_mark_with_two_external_terminals_as_square_bracket():
    image = np.full((220, 600), 255, dtype=np.uint8)
    cv2.line(image, (35, 36), (35, 169), 0, 2)
    cv2.line(image, (35, 36), (46, 36), 0, 2)
    cv2.line(image, (35, 169), (46, 169), 0, 2)

    results = detect_staff_grouping_mark_candidates(image, two_staves())

    assert len(results) == 1
    assert results[0].kind == "square_bracket_candidate"
    assert "no confirma instrumento" in results[0].warning


def test_does_not_call_plain_vertical_mark_a_square_bracket():
    image = np.full((220, 600), 255, dtype=np.uint8)
    cv2.line(image, (35, 40), (35, 165), 0, 2)

    results = detect_staff_grouping_mark_candidates(image, two_staves())

    assert len(results) == 1
    assert results[0].kind == "vertical_grouping_mark_candidate"


def test_detects_curved_brace_shape_candidate():
    image = np.full((220, 600), 255, dtype=np.uint8)
    brace_points = np.array(
        [[35, 40], [30, 50], [30, 65], [38, 78], [45, 90],
         [45, 100], [38, 112], [30, 125], [30, 145], [35, 165]],
        dtype=np.int32,
    )
    cv2.polylines(image, [brace_points], False, 0, 2)

    results = detect_staff_grouping_mark_candidates(image, two_staves())

    assert len(results) == 1
    assert results[0].kind == "curly_brace_candidate"
    assert results[0].staff_indices == (0, 1)
    assert "No confirma piano" in results[0].warning


def test_validates_system_spacing_threshold():
    import pytest
    image = np.full((220, 600), 255, dtype=np.uint8)
    with pytest.raises(ValueError):
        detect_staff_grouping_mark_candidates(
            image, two_staves(), max_interstaff_gap_spacing=0
        )


def test_vertical_grouping_does_not_merge_overwide_staff_pair():
    image = np.full((250, 600), 255, dtype=np.uint8)
    cv2.line(image, (35, 40), (35, 195), 0, 2)
    wide_pair = [
        StaffCandidate([40, 50, 60, 70, 80], 10.0, 1.0),
        StaffCandidate([155, 165, 175, 185, 195], 10.0, 1.0),
    ]

    results = detect_staff_grouping_mark_candidates(image, wide_pair)

    assert results == []


def test_curved_brace_is_matched_to_adjacent_pair_not_a_three_staff_system():
    image = np.full((360, 600), 255, dtype=np.uint8)
    brace_points = np.array(
        [[35, 40], [30, 50], [30, 65], [38, 78], [45, 90],
         [45, 100], [38, 112], [30, 125], [30, 145], [35, 195]],
        dtype=np.int32,
    )
    cv2.polylines(image, [brace_points], False, 0, 2)
    three_staves = [
        StaffCandidate([40, 50, 60, 70, 80], 10.0, 1.0),
        StaffCandidate([155, 165, 175, 185, 195], 10.0, 1.0),
        StaffCandidate([270, 280, 290, 300, 310], 10.0, 1.0),
    ]

    results = detect_staff_grouping_mark_candidates(image, three_staves)

    curved = [item for item in results if item.kind == "curly_brace_candidate"]
    assert len(curved) == 1
    assert curved[0].staff_indices == (0, 1)


def test_validates_curved_brace_spacing_threshold():
    import pytest
    image = np.full((220, 600), 255, dtype=np.uint8)
    with pytest.raises(ValueError):
        detect_staff_grouping_mark_candidates(
            image, two_staves(), max_brace_gap_spacing=0
        )


def test_ignores_invalid_staff_candidates_without_five_lines():
    invalid = [StaffCandidate([], 0.0, 0.0)]
    image = np.full((120, 300), 255, dtype=np.uint8)

    assert detect_staff_grouping_mark_candidates(image, invalid) == []



def test_detect_grouping_marks_uses_supplied_system_candidates():
    from palermo_omr.measure_layout import StaffSystemCandidate

    image = np.full((240, 220), 255, dtype=np.uint8)
    staves = [
        StaffCandidate([40, 50, 60, 70, 80], 10, 1.0),
        StaffCandidate([150, 160, 170, 180, 190], 10, 1.0),
    ]
    for staff in staves:
        for y in staff.lines_y:
            cv2.line(image, (40, y), (200, y), 0, 1)
    cv2.line(image, (15, 35), (15, 195), 0, 2)
    systems = [StaffSystemCandidate(0, [0, 1], 40, 190, 0.82, "connector")]

    marks = detect_staff_grouping_mark_candidates(
        image, staves, system_candidates=systems
    )
    assert any(mark.staff_indices == (0, 1) for mark in marks)
