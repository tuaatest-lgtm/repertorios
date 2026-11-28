import cv2
import numpy as np

from palermo_omr.imaging import StaffCandidate
from palermo_omr.rhythm import analyze_rhythm_candidates
from palermo_omr.symbols import NoteheadCandidate


def _head():
    return NoteheadCandidate(
        bbox=(95, 75, 16, 10), center_x=103.0, center_y=80.0,
        staff_index=0, diatonic_step_from_bottom=2,
        fill_ratio=0.8, notehead_shape_score=0.9, confidence=0.9,
    )


def test_filled_head_with_stem_proposes_quarter():
    image = np.full((180, 260), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (250, y), 0, 1)
    cv2.ellipse(image, (103, 80), (8, 5), -20, 0, 360, 0, -1)
    cv2.line(image, (110, 80), (110, 45), 0, 2)

    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)
    result = analyze_rhythm_candidates(image, [staff], [_head()])[0]

    assert result.notehead_fill == "filled"
    assert result.stem_direction == "up"
    assert result.beam_count == 0
    assert result.base_duration == "quarter"


def test_empty_input_is_rejected():
    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)
    try:
        analyze_rhythm_candidates(np.array([], dtype=np.uint8), [staff], [_head()])
    except ValueError:
        return
    raise AssertionError("Expected ValueError")


def test_hollow_head_with_stem_proposes_half_note():
    image = np.full((180, 260), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (250, y), 0, 1)
    cv2.ellipse(image, (103, 80), (9, 5), -20, 0, 360, 0, 2)
    cv2.line(image, (110, 80), (110, 45), 0, 2)

    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)
    result = analyze_rhythm_candidates(image, [staff], [_head()])[0]

    assert result.notehead_fill == "hollow"
    assert result.stem_direction == "up"
    assert result.base_duration == "half"


def test_hollow_head_without_stem_proposes_whole_note():
    image = np.full((180, 260), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (250, y), 0, 1)
    cv2.ellipse(image, (103, 80), (9, 5), -20, 0, 360, 0, 2)

    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)
    result = analyze_rhythm_candidates(image, [staff], [_head()])[0]

    assert result.notehead_fill == "hollow"
    assert result.stem_direction == "none"
    assert result.base_duration == "whole"


def test_detects_stem_at_actual_notehead_edge_not_fixed_center_offset():
    image = np.full((180, 260), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (250, y), 0, 1)
    cv2.ellipse(image, (103, 80), (8, 5), -20, 0, 360, 0, -1)
    # La plica real está en x=112; el muestreo antiguo (x=96 y x=110)
    # no la intercepta. El bbox de la cabeza sí contiene el punto de unión.
    cv2.line(image, (112, 80), (112, 35), 0, 2)

    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)
    result = analyze_rhythm_candidates(image, [staff], [_head()])[0]

    assert result.stem_direction == "up"
    assert result.stem_x == 112
    assert result.stem_length_px >= 45
