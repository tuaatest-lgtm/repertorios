import cv2
import numpy as np

from palermo_omr.imaging import StaffCandidate
from palermo_omr.symbols import detect_notehead_candidates


def test_proposes_notehead_and_diatonic_position():
    image = np.full((180, 500), 255, dtype=np.uint8)
    lines = [60, 70, 80, 90, 100]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    # Cabeza rellena centrada en el espacio inmediatamente sobre la línea inferior.
    cv2.ellipse(image, (150, 95), (8, 5), -20, 0, 360, 0, -1)

    staff = StaffCandidate(lines_y=lines, spacing_px=10.0, confidence=1.0)
    candidates = detect_notehead_candidates(image, [staff])

    assert candidates
    nearest = min(candidates, key=lambda item: abs(item.center_x - 150))
    assert abs(nearest.center_x - 150) <= 2
    assert nearest.diatonic_step_from_bottom == 1
    assert nearest.staff_index == 0


def test_detects_notehead_even_when_connected_to_staff_line_and_stem():
    image = np.full((180, 500), 255, dtype=np.uint8)
    lines = [60, 70, 80, 90, 100]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    # Cabeza centrada sobre una línea, con plica que toca su borde.
    cv2.ellipse(image, (220, 90), (8, 5), -20, 0, 360, 0, -1)
    cv2.line(image, (228, 90), (228, 45), 0, 2)

    staff = StaffCandidate(lines_y=lines, spacing_px=10.0, confidence=1.0)
    candidates = detect_notehead_candidates(image, [staff])

    nearest = min(candidates, key=lambda item: abs(item.center_x - 220))
    assert abs(nearest.center_x - 220) <= 2
    assert nearest.diatonic_step_from_bottom == 2


def test_detects_multiple_beamed_noteheads_without_merging_them():
    image = np.full((180, 500), 255, dtype=np.uint8)
    lines = [60, 70, 80, 90, 100]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    for x in (150, 190, 230):
        cv2.ellipse(image, (x, 95), (8, 5), -20, 0, 360, 0, -1)
        cv2.line(image, (x + 7, 95), (x + 7, 50), 0, 2)
    cv2.line(image, (157, 50), (237, 50), 0, 3)

    staff = StaffCandidate(lines_y=lines, spacing_px=10.0, confidence=1.0)
    candidates = detect_notehead_candidates(image, [staff])

    for x in (150, 190, 230):
        assert any(abs(item.center_x - x) <= 2 for item in candidates)


def test_empty_staff_returns_no_candidates():
    image = np.full((160, 400), 255, dtype=np.uint8)
    staff = StaffCandidate(
        lines_y=[40, 50, 60, 70, 80],
        spacing_px=10.0,
        confidence=1.0,
    )
    assert detect_notehead_candidates(image, [staff]) == []
