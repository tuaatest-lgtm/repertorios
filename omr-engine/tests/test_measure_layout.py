import cv2
import numpy as np

from palermo_omr.imaging import StaffCandidate
from palermo_omr.measure_layout import detect_barline_candidates


def _staff():
    return StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0)


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

    candidates = detect_barline_candidates(image, [_staff()])

    assert candidates == []


def test_rejects_empty_image():
    try:
        detect_barline_candidates(np.array([], dtype=np.uint8), [_staff()])
    except ValueError:
        return
    raise AssertionError("Expected ValueError")
