import cv2
import numpy as np

from palermo_omr.imaging import StaffCandidate
from palermo_omr.measure_layout import (
    BarlineCandidate,
    classify_barline_groups,
    detect_barline_candidates,
    detect_staff_systems,
    group_system_barlines,
    infer_measure_spans,
)


def _staff(y=60):
    return StaffCandidate([y, y + 10, y + 20, y + 30, y + 40], 10.0, 1.0)


def _bar(x, staff):
    return BarlineCandidate(
        x=float(x), y_top=60 + staff * 70, y_bottom=100 + staff * 70,
        width_px=2, staff_index=staff, coverage=1.0, confidence=0.9,
        warning="test",
    )


def test_detects_vertical_stroke_crossing_full_staff():
    image = np.full((160, 260), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (250, y), 0, 1)
    cv2.line(image, (140, 60), (140, 100), 0, 2)
    candidates = detect_barline_candidates(image, [_staff()])
    assert len(candidates) == 1
    assert abs(candidates[0].x - 140) <= 1
    assert candidates[0].coverage >= 0.78
    assert "no confirmado" in candidates[0].warning.lower()


def test_does_not_promote_short_note_stem_to_barline():
    image = np.full((160, 260), 255, dtype=np.uint8)
    cv2.line(image, (140, 72), (140, 95), 0, 2)
    assert detect_barline_candidates(image, [_staff()]) == []


def test_rejects_empty_image():
    try:
        detect_barline_candidates(np.array([], dtype=np.uint8), [_staff()])
    except ValueError:
        return
    raise AssertionError("Expected ValueError")


def test_groups_aligned_barlines_across_staves():
    candidates = [_bar(100, 0), _bar(101, 1), _bar(200, 0), _bar(201, 1)]
    systems = group_system_barlines(candidates, [_staff(), _staff(130)])
    assert len(systems) == 2
    assert systems[0].staff_indices == [0, 1]
    assert systems[1].support_count == 2


def test_detects_vertical_gap_between_two_systems():
    systems = detect_staff_systems([_staff(60), _staff(130), _staff(260)])
    assert len(systems) == 2
    assert systems[0].staff_indices == [0, 1]
    assert systems[1].staff_indices == [2]


def test_does_not_merge_aligned_barlines_from_separate_systems():
    staves = [_staff(60), _staff(130), _staff(260), _staff(330)]
    candidates = [
        _bar(120, 0), _bar(120, 1),
        _bar(120, 2), _bar(120, 3),
    ]
    grouped = group_system_barlines(candidates, staves)
    assert len(grouped) == 2
    assert grouped[0].system_index == 0
    assert grouped[0].staff_indices == [0, 1]
    assert grouped[1].system_index == 1
    assert grouped[1].staff_indices == [2, 3]


def test_does_not_group_barline_supported_by_only_one_staff():
    systems = group_system_barlines([_bar(100, 0)], [_staff()], min_staff_support=2)
    assert systems == []


def test_infers_only_intervals_between_observed_consecutive_bars():
    spans = infer_measure_spans([_bar(50, 0), _bar(150, 0), _bar(260, 0)])
    assert len(spans) == 2
    assert spans[0].measure_index == 1
    assert spans[0].x_start == 50
    assert spans[0].x_end == 150
    assert spans[0].left_boundary_observed
    assert spans[0].right_boundary_observed


def test_ignores_too_narrow_intervals():
    spans = infer_measure_spans([_bar(50, 0), _bar(54, 0), _bar(150, 0)])
    assert len(spans) == 1
    assert spans[0].x_start == 54


def test_rejects_invalid_grouping_parameters():
    for call in (
        lambda: group_system_barlines([], [], x_tolerance_spacing=0),
        lambda: group_system_barlines([], [], min_staff_support=0),
        lambda: detect_staff_systems([_staff()], max_interstaff_gap_spacing=0),
        lambda: infer_measure_spans([], min_width_px=0),
    ):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("Expected ValueError")



def test_classifies_single_barline_candidate():
    result = classify_barline_groups([_bar(100, 0)], [_staff()])
    assert len(result) == 1
    assert result[0].kind == "single_candidate"


def test_classifies_two_similar_lines_as_double_barline_candidate():
    bars = [_bar(100, 0), _bar(110, 0)]
    result = classify_barline_groups(bars, [_staff()])
    assert len(result) == 1
    assert result[0].kind == "double_candidate"
    assert len(result[0].x_positions) == 2


def test_classifies_thin_and_thick_pair_as_final_barline_candidate():
    thin = _bar(100, 0)
    thick = BarlineCandidate(
        x=110, y_top=60, y_bottom=100, width_px=4, staff_index=0,
        coverage=1.0, confidence=0.9, warning="test",
    )
    result = classify_barline_groups([thin, thick], [_staff()])
    assert len(result) == 1
    assert result[0].kind == "final_candidate"


def test_keeps_three_close_lines_ambiguous():
    bars = [_bar(100, 0), _bar(110, 0), _bar(120, 0)]
    result = classify_barline_groups(bars, [_staff()])
    assert len(result) == 1
    assert result[0].kind == "ambiguous_group"


def test_rejects_invalid_barline_classification_parameters():
    for call in (
        lambda: classify_barline_groups([], [_staff()], max_pair_gap_spacing=0),
        lambda: classify_barline_groups([], [_staff()], thick_line_ratio=1),
    ):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("Expected ValueError")



def test_detect_staff_systems_from_connectors_groups_only_connected_pairs():
    from palermo_omr.measure_layout import detect_staff_systems_from_connectors

    binary = np.full((460, 320), 255, dtype=np.uint8)
    staves = []
    for top in (40, 150, 260, 370):
        lines = [top + offset for offset in (0, 10, 20, 30, 40)]
        staves.append(StaffCandidate(lines, 10, 1.0))
        for y in lines:
            cv2.line(binary, (40, y), (300, y), 0, 1)
    # Los conectores separan dos sistemas: (0, 1) y (2, 3).
    cv2.line(binary, (20, 35), (20, 195), 0, 2)
    cv2.line(binary, (20, 255), (20, 415), 0, 2)

    systems = detect_staff_systems_from_connectors(staves, binary)
    assert [item.staff_indices for item in systems] == [[0, 1], [2, 3]]
    assert all(item.confidence > 0.8 for item in systems)


def test_detect_staff_systems_from_connectors_keeps_unconnected_staves_separate():
    from palermo_omr.measure_layout import detect_staff_systems_from_connectors

    binary = np.full((260, 320), 255, dtype=np.uint8)
    staves = []
    for top in (40, 170):
        lines = [top + offset for offset in (0, 10, 20, 30, 40)]
        staves.append(StaffCandidate(lines, 10, 1.0))
        for y in lines:
            cv2.line(binary, (40, y), (300, y), 0, 1)

    systems = detect_staff_systems_from_connectors(staves, binary)
    assert [item.staff_indices for item in systems] == [[0], [1]]
    assert all(item.confidence == 0.45 for item in systems)
