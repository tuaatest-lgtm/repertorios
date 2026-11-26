"""Candidatos geométricos de marcas de agrupación de pentagramas.

La clasificación de corchete es una hipótesis visual conservadora, no una
identificación musical ni una asignación automática de instrumentos.
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


def _has_horizontal_terminal(
    ink: np.ndarray,
    *,
    x: int,
    y_start: int,
    y_end: int,
    spacing: float,
) -> bool:
    """Busca un remate horizontal corto junto al extremo de un trazo vertical."""
    height, width = ink.shape
    x_start = max(0, x - 2)
    x_end = min(width, x_start + max(5, int(round(spacing * 1.8))))
    y_start = max(0, y_start)
    y_end = min(height, y_end)
    if x_end - x_start < 4 or y_end <= y_start:
        return False

    roi = ink[y_start:y_end, x_start:x_end]
    kernel_width = max(4, int(round(spacing * 0.45)))
    horizontal = cv2.morphologyEx(
        roi,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1)),
    )
    count, _, stats, _ = cv2.connectedComponentsWithStats(horizontal, 8)
    return any(
        int(stats[label, cv2.CC_STAT_WIDTH]) >= kernel_width
        for label in range(1, count)
    )


def detect_staff_grouping_mark_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
    *,
    left_margin_ratio: float = 0.18,
    max_width_spacing: float = 1.2,
) -> list[StaffGroupingMarkCandidate]:
    """Propone trazos verticales y, si hay dos remates, corchetes candidatos.

    Solo analiza el margen izquierdo de sistemas geométricos con dos o más
    pentagramas. Un par de remates horizontales permite etiquetar una forma
    compatible con corchete recto; no reconoce llaves curvas ni confirma que
    los pentagramas sean de piano, coro u otra parte.
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

            center_x = int(round(float(centroids[label][0])))
            top_terminal = _has_horizontal_terminal(
                ink, x=center_x, y_start=top - int(round(spacing * 0.7)),
                y_end=top, spacing=spacing,
            )
            bottom_terminal = _has_horizontal_terminal(
                ink, x=center_x, y_start=bottom + 1,
                y_end=bottom + 1 + int(round(spacing * 0.7)),
                spacing=spacing,
            )
            is_bracket = top_terminal and bottom_terminal
            kind = (
                "square_bracket_candidate"
                if is_bracket else "vertical_grouping_mark_candidate"
            )
            confidence = min(0.84 if is_bracket else 0.78, 0.48 + 0.3 * coverage)
            if is_bracket:
                confidence += 0.06
            results.append(StaffGroupingMarkCandidate(
                x=round(float(centroids[label][0]), 2),
                y_top=top + y,
                y_bottom=top + y + height - 1,
                width_px=width,
                staff_indices=indices,
                vertical_coverage=round(min(1.0, coverage), 3),
                kind=kind,
                confidence=round(min(confidence, 0.84), 3),
                warning=(
                    "Forma compatible con un corchete recto por sus dos remates; "
                    "requiere revisión visual y no confirma instrumento, piano "
                    "ni relación musical entre pentagramas."
                    if is_bracket else
                    "Trazo vertical candidato a marca de agrupación. Puede ser "
                    "parte de una llave u otro trazo; no confirma instrumento, "
                    "piano ni relación entre pentagramas."
                ),
            ))
    results.sort(key=lambda item: (item.y_top, item.x))
    return results
