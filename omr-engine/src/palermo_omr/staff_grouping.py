"""Candidatos geométricos de trazos verticales de agrupación de pentagramas.

No clasifica por sí solo una llave, corchete o barra de sistema.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .imaging import StaffCandidate
from .measure_layout import detect_staff_systems


@dataclass(frozen=True)
class StaffGroupingMarkCandidate:
    x: float
    y_top: int
    y_bottom: int
    width_px: int
    staff_indices: tuple[int, ...]
    vertical_coverage: float
    kind: str
    confidence: float
    warning: str

    def to_dict(self) -> dict:
        return asdict(self)


def detect_staff_grouping_mark_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
    *,
    left_margin_ratio: float = 0.18,
    max_width_spacing: float = 1.2,
) -> list[StaffGroupingMarkCandidate]:
    """Propone trazos verticales largos a la izquierda de sistemas.

    Es deliberadamente conservador: solo encuentra segmentos casi verticales
    dentro del margen izquierdo. Llaves curvas, etiquetas y relaciones
    musicales requieren detectores y revisión separados.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    if not 0 < left_margin_ratio <= 1:
        raise ValueError("left_margin_ratio debe estar entre 0 y 1")
    if max_width_spacing <= 0:
        raise ValueError("max_width_spacing debe ser positivo")
    if not staves:
        return []

    systems = detect_staff_systems(staves)
    ink = cv2.bitwise_not(binary)
    page_height, page_width = binary.shape
    results: list[StaffGroupingMarkCandidate] = []

    for system in systems:
        indices = tuple(sorted(system.staff_indices))
        if len(indices) < 2:
            continue
        top = max(0, int(round(system.y_top)))
        bottom = min(page_height - 1, int(round(system.y_bottom)))
        span = bottom - top + 1
        if span < 8:
            continue
        roi = ink[top:bottom + 1, :max(1, int(page_width * left_margin_ratio))]
        kernel_height = max(8, int(round(span * 0.72)))
        vertical = cv2.morphologyEx(
            roi, cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_height)),
        )
        count, _, stats, centroids = cv2.connectedComponentsWithStats(vertical, 8)
        spacing = float(np.median([staves[i].spacing_px for i in indices]))
        for label in range(1, count):
            x, y, width, height, _ = (int(v) for v in stats[label])
            if width > max(2, int(round(spacing * max_width_spacing))):
                continue
            coverage = height / span
            if coverage < 0.68:
                continue
            results.append(StaffGroupingMarkCandidate(
                x=round(float(centroids[label][0]), 2),
                y_top=top + y,
                y_bottom=top + y + height - 1,
                width_px=width,
                staff_indices=indices,
                vertical_coverage=round(min(1.0, coverage), 3),
                kind="vertical_grouping_mark_candidate",
                confidence=round(min(0.78, 0.45 + 0.3 * coverage), 3),
                warning=(
                    "Trazo vertical candidato a marca de agrupación. Puede ser "
                    "un corchete, parte de una llave u otro trazo; no confirma "
                    "instrumento, piano ni relación entre pentagramas."
                ),
            ))
    results.sort(key=lambda item: (item.y_top, item.x))
    return results
