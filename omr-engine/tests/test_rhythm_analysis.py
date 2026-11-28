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


def _wide_head(shape_score=0.95):
    return NoteheadCandidate(
        bbox=(90, 75, 26, 10), center_x=103.0, center_y=80.0,
        staff_index=0, diatonic_step_from_bottom=2,
        fill_ratio=0.8, notehead_shape_score=shape_score, confidence=0.9,
    )


def test_bbox_edge_fallback_recovers_up_stem_without_promoting_confidence():
    image = np.full((180, 260), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (250, y), 0, 1)
    cv2.ellipse(image, (103, 80), (11, 5), -20, 0, 360, 0, -1)
    cv2.line(image, (114, 80), (114, 45), 0, 2)

    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)
    result = analyze_rhythm_candidates(image, [staff], [_wide_head()])[0]

    assert result.stem_direction == "up"
    assert result.base_duration == "quarter"
    assert result.confidence <= 0.78
    assert any("borde de la cabeza" in warning for warning in result.warnings)


def test_bbox_edge_fallback_recovers_down_stem_on_left_edge():
    image = np.full((180, 260), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (250, y), 0, 1)
    cv2.ellipse(image, (103, 80), (11, 5), -20, 0, 360, 0, -1)
    cv2.line(image, (91, 80), (91, 115), 0, 2)

    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)
    result = analyze_rhythm_candidates(image, [staff], [_wide_head()])[0]

    assert result.stem_direction == "down"
    assert result.base_duration == "quarter"
    assert result.confidence <= 0.78


def test_bbox_edge_fallback_rejects_low_shape_score_and_unconnected_stems():
    image = np.full((180, 260), 255, dtype=np.uint8)
    for y in [60, 70, 80, 90, 100]:
        cv2.line(image, (5, y), (250, y), 0, 1)
    cv2.ellipse(image, (103, 80), (11, 5), -20, 0, 360, 0, -1)
    cv2.line(image, (114, 80), (114, 45), 0, 2)

    staff = StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)
    result = analyze_rhythm_candidates(image, [staff], [_wide_head(shape_score=0.55)])[0]

    assert result.stem_direction == "none"
    assert result.base_duration == "unknown"
