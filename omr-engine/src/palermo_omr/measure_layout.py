"""Candidatos geométricos de barras de compás.

Detecta trazos verticales que cubren casi toda la altura de un pentagrama.
No determina por sí solo límites de compás: dobles barras, líneas de sistema,
picas largas y otros trazos requieren contexto adicional.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .imaging import StaffCandidate


@dataclass(frozen=True)
class BarlineCandidate:
    x: float
    y_top: int
    y_bottom: int
    width_px: int
    staff_index: int
    coverage: float
    confidence: float
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


def detect_barline_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
) -> list[BarlineCandidate]:
    """Propone barras verticales que atraviesan la mayor parte del pentagrama."""
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")

    ink = cv2.bitwise_not(binary)
    results: list[BarlineCandidate] = []
    for staff_index, staff in enumerate(staves):
        if len(staff.lines_y) != 5 or staff.spacing_px <= 1:
            continue

        top = int(round(staff.lines_y[0]))
        bottom = int(round(staff.lines_y[-1]))
        staff_height = bottom - top
        if staff_height <= 0 or top < 0 or bottom >= binary.shape[0]:
            continue

        kernel_height = max(3, int(round(staff.spacing_px * 3.2)))
        vertical = cv2.morphologyEx(
            ink,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_height)),
        )
        roi = vertical[top:bottom + 1, :]
        count, _, stats, centroids = cv2.connectedComponentsWithStats(roi, 8)

        for label in range(1, count):
            x, y, width, height, _ = (int(v) for v in stats[label])
            if width > max(2, int(round(staff.spacing_px * 0.35))):
                continue
            coverage = height / max(staff_height, 1)
            if coverage < 0.78:
                continue
            center_x = float(centroids[label][0])
            results.append(
                BarlineCandidate(
                    x=round(center_x, 2),
                    y_top=top + y,
                    y_bottom=top + y + height - 1,
                    width_px=width,
                    staff_index=staff_index,
                    coverage=round(min(1.0, coverage), 3),
                    confidence=round(min(0.9, 0.55 + 0.35 * min(1.0, coverage)), 3),
                    warning=(
                        "Candidato geométrico no confirmado: debe distinguirse de "
                        "trazos verticales, límites de sistema y otros símbolos."
                    ),
                )
            )

    results.sort(key=lambda item: (item.staff_index, item.x))
    return results
