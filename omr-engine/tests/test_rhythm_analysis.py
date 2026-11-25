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
