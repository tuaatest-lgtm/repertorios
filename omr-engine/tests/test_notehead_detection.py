import cv2
import numpy as np

from palermo_omr.imaging import StaffCandidate
from palermo_omr.symbols import (
    detect_hollow_notehead_candidates,
    detect_notehead_candidates,
)


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


def test_splits_two_touching_noteheads_displaced_by_a_second():
    image = np.full((180, 500), 255, dtype=np.uint8)
    lines = [60, 70, 80, 90, 100]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    # Acorde de segunda: las cabezas se tocan y quedan desplazadas en X/Y.
    cv2.ellipse(image, (200, 95), (8, 5), -20, 0, 360, 0, -1)
    cv2.ellipse(image, (207, 90), (8, 5), -20, 0, 360, 0, -1)
    cv2.line(image, (208, 90), (208, 45), 0, 2)

    staff = StaffCandidate(lines_y=lines, spacing_px=10.0, confidence=1.0)
    candidates = detect_notehead_candidates(image, [staff])

    lower = [
        item for item in candidates
        if abs(item.center_x - 200) <= 3 and item.diatonic_step_from_bottom == 1
    ]
    upper = [
        item for item in candidates
        if abs(item.center_x - 207) <= 3 and item.diatonic_step_from_bottom == 2
    ]
    assert lower, "Debe recuperar la cabeza inferior del acorde"
    assert upper, "Debe recuperar la cabeza superior del acorde"
    assert lower[0].center_x != upper[0].center_x
    assert lower[0].confidence <= 0.72
    assert upper[0].confidence <= 0.72


def test_does_not_split_a_sloped_beam_into_noteheads():
    image = np.full((180, 500), 255, dtype=np.uint8)
    lines = [60, 70, 80, 90, 100]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    # Una viga diagonal gruesa conectada a plicas puede crear dos máximos
    # locales, pero no debe interpretarse como dos cabezas de nota.
    cv2.line(image, (160, 75), (260, 95), 0, 8)
    cv2.line(image, (180, 75), (180, 45), 0, 2)
    cv2.line(image, (240, 91), (240, 45), 0, 2)

    staff = StaffCandidate(lines_y=lines, spacing_px=10.0, confidence=1.0)
    candidates = detect_notehead_candidates(image, [staff])

    assert not candidates, "Una viga inclinada no debe generar cabezas de nota"


def test_detects_hollow_notehead_on_staff_line_with_stem():
    image = np.full((180, 500), 255, dtype=np.uint8)
    lines = [60, 70, 80, 90, 100]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    cv2.ellipse(image, (220, 90), (9, 5), -20, 0, 360, 0, 2)
    cv2.line(image, (228, 90), (228, 45), 0, 2)

    staff = StaffCandidate(lines_y=lines, spacing_px=10.0, confidence=1.0)
    candidates = detect_hollow_notehead_candidates(image, [staff])

    nearest = min(candidates, key=lambda item: abs(item.center_x - 220))
    assert abs(nearest.center_x - 220) <= 2
    assert nearest.diatonic_step_from_bottom == 2
    assert nearest.fill_ratio < 0.5
    assert nearest.confidence <= 0.68
    assert len(candidates) == 1


def test_detects_hollow_notehead_without_stem():
    image = np.full((180, 500), 255, dtype=np.uint8)
    lines = [60, 70, 80, 90, 100]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    cv2.ellipse(image, (300, 95), (9, 5), -20, 0, 360, 0, 2)

    staff = StaffCandidate(lines_y=lines, spacing_px=10.0, confidence=1.0)
    candidates = detect_hollow_notehead_candidates(image, [staff])

    nearest = min(candidates, key=lambda item: abs(item.center_x - 300))
    assert abs(nearest.center_x - 300) <= 2
    assert nearest.diatonic_step_from_bottom == 1


def test_hollow_notehead_detector_rejects_oversized_hollow_symbol():
    image = np.full((180, 500), 255, dtype=np.uint8)
    lines = [60, 70, 80, 90, 100]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    # Un símbolo hueco grande no debe confundirse con una cabeza de nota.
    cv2.ellipse(image, (300, 90), (28, 20), 0, 0, 360, 0, 3)

    staff = StaffCandidate(lines_y=lines, spacing_px=10.0, confidence=1.0)
    candidates = detect_hollow_notehead_candidates(image, [staff])

    assert not candidates


def test_does_not_treat_gap_between_filled_heads_as_hollow():
    image = np.full((180, 500), 255, dtype=np.uint8)
    lines = [60, 70, 80, 90, 100]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    # Dos cabezas rellenas próximas pueden dejar un hueco irregular entre ellas.
    cv2.ellipse(image, (220, 90), (9, 5), -20, 0, 360, 0, -1)
    cv2.ellipse(image, (220, 100), (9, 5), -20, 0, 360, 0, -1)
    cv2.line(image, (228, 90), (228, 45), 0, 2)

    staff = StaffCandidate(lines_y=lines, spacing_px=10.0, confidence=1.0)
    candidates = detect_hollow_notehead_candidates(image, [staff])

    assert not candidates

def test_detects_two_hollow_noteheads_sharing_one_outer_contour():
    image = np.full((300, 500), 255, dtype=np.uint8)
    lines = [80, 100, 120, 140, 160]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    # Dos cabezas de blanca en acorde: la plica une los contornos exteriores,
    # pero cada cabeza conserva su propio hueco interior.
    for y in (120, 140):
        cv2.ellipse(image, (240, y), (9, 5), -20, 0, 360, 0, 2)
    cv2.line(image, (231, 120), (231, 143), 0, 2)

    staff = StaffCandidate(lines_y=lines, spacing_px=20.0, confidence=1.0)
    candidates = detect_hollow_notehead_candidates(image, [staff])

    chord = [
        item for item in candidates
        if abs(item.center_x - 240) <= 2
        and item.diatonic_step_from_bottom in (2, 4)
    ]
    assert len(chord) == 2
    assert len({item.diatonic_step_from_bottom for item in chord}) == 2


def test_detects_three_hollow_noteheads_sharing_one_outer_contour():
    image = np.full((300, 500), 255, dtype=np.uint8)
    lines = [80, 100, 120, 140, 160]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    # Acorde de tres cabezas con una plica común: tres huecos interiores.
    for y in (120, 140, 160):
        cv2.ellipse(image, (240, y), (9, 5), -20, 0, 360, 0, 2)
    cv2.line(image, (231, 120), (231, 163), 0, 2)

    staff = StaffCandidate(lines_y=lines, spacing_px=20.0, confidence=1.0)
    candidates = detect_hollow_notehead_candidates(image, [staff])

    chord = [
        item for item in candidates
        if abs(item.center_x - 240) <= 2
        and item.diatonic_step_from_bottom in (0, 2, 4)
    ]
    assert len(chord) == 3
    assert len({item.diatonic_step_from_bottom for item in chord}) == 3

def test_detects_hollow_second_interval_chord_with_displaced_heads():
    image = np.full((300, 500), 255, dtype=np.uint8)
    lines = [80, 100, 120, 140, 160]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    # En una segunda, las cabezas se desplazan horizontalmente para evitar
    # superponerse; sus huecos deben seguir siendo candidatos independientes.
    centers = [(240, 120), (250, 130), (240, 140)]
    for x, y in centers:
        cv2.ellipse(image, (x, y), (9, 5), -20, 0, 360, 0, 2)
    cv2.line(image, (259, 120), (259, 144), 0, 2)

    staff = StaffCandidate(lines_y=lines, spacing_px=20.0, confidence=1.0)
    candidates = detect_hollow_notehead_candidates(image, [staff])

    expected_steps = {2, 3, 4}
    chord = [
        item for item in candidates
        if 235 <= item.center_x <= 256
        and item.diatonic_step_from_bottom in expected_steps
    ]
    assert len(chord) == 3
    assert {item.diatonic_step_from_bottom for item in chord} == expected_steps

def test_detects_hollow_notehead_two_staff_spacings_above_top_line():
    image = np.full((300, 500), 255, dtype=np.uint8)
    lines = [80, 100, 120, 140, 160]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    # Nota en línea adicional, dos separaciones de pentagrama por encima.
    cv2.ellipse(image, (300, 40), (18, 10), -20, 0, 360, 0, 2)
    cv2.line(image, (270, 40), (330, 40), 0, 1)
    cv2.line(image, (316, 40), (316, 10), 0, 2)

    staff = StaffCandidate(lines_y=lines, spacing_px=20.0, confidence=1.0)
    candidates = detect_hollow_notehead_candidates(image, [staff])

    assert any(
        abs(item.center_x - 300) <= 2
        and item.diatonic_step_from_bottom == 12
        for item in candidates
    )


def test_detects_hollow_notehead_two_staff_spacings_below_bottom_line():
    image = np.full((300, 500), 255, dtype=np.uint8)
    lines = [80, 100, 120, 140, 160]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    # Nota en línea adicional, dos separaciones de pentagrama por debajo.
    cv2.ellipse(image, (300, 200), (18, 10), -20, 0, 360, 0, 2)
    cv2.line(image, (270, 200), (330, 200), 0, 1)
    cv2.line(image, (284, 200), (284, 245), 0, 2)

    staff = StaffCandidate(lines_y=lines, spacing_px=20.0, confidence=1.0)
    candidates = detect_hollow_notehead_candidates(image, [staff])

    assert any(
        abs(item.center_x - 300) <= 2
        and item.diatonic_step_from_bottom == -4
        for item in candidates
    )

def test_rejects_hollow_text_like_shape_outside_staff_without_ledger_line():
    image = np.full((300, 500), 255, dtype=np.uint8)
    lines = [80, 100, 120, 140, 160]
    for y in lines:
        cv2.line(image, (10, y), (490, y), 0, 1)

    # Un óvalo hueco aislado fuera del pentagrama no basta para afirmar
    # que existe una nota en línea adicional.
    cv2.ellipse(image, (300, 40), (18, 10), -20, 0, 360, 0, 2)

    staff = StaffCandidate(lines_y=lines, spacing_px=20.0, confidence=1.0)
    candidates = detect_hollow_notehead_candidates(image, [staff])

    assert not any(abs(item.center_x - 300) <= 2 for item in candidates)

