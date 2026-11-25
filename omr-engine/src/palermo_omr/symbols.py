"""Propuestas geométricas de cabezas de nota y posición diatónica.

Este módulo produce candidatos visuales, no decisiones musicales definitivas.
La clasificación de altura requiere conocer la clave y la armadura.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .imaging import StaffCandidate


@dataclass(frozen=True)
class NoteheadCandidate:
    bbox: tuple[int, int, int, int]
    center_x: float
    center_y: float
    staff_index: int
    diatonic_step_from_bottom: int
    fill_ratio: float
    notehead_shape_score: float
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


def _remove_staff_lines(binary: np.ndarray, staff_spacing: float) -> np.ndarray:
    """Elimina líneas horizontales largas y conserva tinta restante."""
    ink = cv2.bitwise_not(binary)
    width = binary.shape[1]
    kernel_width = max(15, min(width // 4, int(width * 0.12)))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1))
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
    without_lines = cv2.subtract(ink, horizontal)

    # Reconecta pequeños cortes producidos por la eliminación de las líneas.
    close_size = max(2, int(round(staff_spacing * 0.18)))
    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (close_size, close_size)
    )
    return cv2.morphologyEx(without_lines, cv2.MORPH_CLOSE, close_kernel)


def detect_notehead_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
) -> list[NoteheadCandidate]:
    """Propone cabezas de nota y su posición respecto a cada pentagrama.

    Convención geométrica: el índice 0 es la línea inferior; los espacios
    y líneas sucesivos hacia arriba son 1, 2, 3... No asigna nombres de nota
    porque eso depende de la clave.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    if not staves:
        return []

    candidates: list[NoteheadCandidate] = []
    for staff_index, staff in enumerate(staves):
        if len(staff.lines_y) != 5:
            continue
        spacing = float(staff.spacing_px)
        if spacing <= 1:
            continue

        cleaned = _remove_staff_lines(binary, spacing)
        count, _, stats, centroids = cv2.connectedComponentsWithStats(
            cleaned, connectivity=8
        )

        top = staff.lines_y[0] - spacing * 1.6
        bottom = staff.lines_y[-1] + spacing * 1.6
        min_w, max_w = spacing * 0.65, spacing * 2.8
        min_h, max_h = spacing * 0.42, spacing * 1.9

        for label in range(1, count):
            x, y, w, h, area = (int(v) for v in stats[label])
            cx, cy = (float(v) for v in centroids[label])
            if not (top <= cy <= bottom):
                continue
            if not (min_w <= w <= max_w and min_h <= h <= max_h):
                continue
            aspect = w / max(h, 1)
            if not 1.05 <= aspect <= 2.5:
                continue

            component = cleaned[y : y + h, x : x + w]
            fill_ratio = float(np.count_nonzero(component)) / float(w * h)
            # Rango amplio: incluye notas rellenas y huecas; evita manchas
            # extremadamente densas o contornos casi inexistentes.
            if not 0.12 <= fill_ratio <= 0.88:
                continue

            # La distancia entre posiciones musicales consecutivas es
            # aproximadamente la mitad de la separación entre líneas.
            bottom_line = float(staff.lines_y[-1])
            step = int(round((bottom_line - cy) / (spacing / 2.0)))
            snapped_y = bottom_line - step * spacing / 2.0
            vertical_error = abs(cy - snapped_y) / max(spacing / 2.0, 1.0)
            if vertical_error > 0.48:
                continue

            shape_score = max(0.0, 1.0 - abs(aspect - 1.45) / 1.45)
            alignment_score = max(0.0, 1.0 - vertical_error)
            size_score = min(1.0, w / max(spacing * 1.1, 1.0))
            confidence = (
                0.45 * shape_score
                + 0.35 * alignment_score
                + 0.20 * size_score
            )
            candidates.append(
                NoteheadCandidate(
                    bbox=(x, y, w, h),
                    center_x=round(cx, 2),
                    center_y=round(cy, 2),
                    staff_index=staff_index,
                    diatonic_step_from_bottom=step,
                    fill_ratio=round(fill_ratio, 3),
                    notehead_shape_score=round(shape_score, 3),
                    confidence=round(confidence, 3),
                )
            )

    # Deduplicación conservadora por proximidad; una misma cabeza puede
    # aparecer en candidatos de pentagramas cercanos en partituras densas.
    candidates.sort(key=lambda item: (item.staff_index, item.center_x, item.center_y))
    return candidates
