"""Candidatos geométricos de marcas de agrupación de pentagramas.

Las etiquetas de corchete y llave son hipótesis visuales conservadoras, no
identificaciones musicales ni asignaciones automáticas de instrumentos.
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


def _curved_brace_components(
    ink: np.ndarray,
    *,
    top: int,
    bottom: int,
    spacing: float,
    left_width: int,
) -> list[tuple[int, int, int, int, float]]:
    """Devuelve componentes altos con desplazamiento lateral en su zona media."""
    page_height, _ = ink.shape
    span = bottom - top + 1
    y_start = max(0, top - int(round(spacing)))
    y_end = min(page_height, bottom + int(round(spacing)) + 1)
    roi = ink[y_start:y_end, :left_width]
    count, labels, stats, _ = cv2.connectedComponentsWithStats(roi, 8)
    found: list[tuple[int, int, int, int, float]] = []

    for label in range(1, count):
        x, y, width, height, _ = (int(v) for v in stats[label])
        if height < span * 0.65 or height > span * 1.4:
            continue
        if width < spacing * 0.4 or width > spacing * 2.2:
            continue

        component = labels[y:y + height, x:x + width] == label
        row_centers: list[float] = []
        for row in component:
            pixels = np.flatnonzero(row)
            if pixels.size:
                row_centers.append(float(np.mean(pixels + x))
                )
        if len(row_centers) < height * 0.72:
            continue

        row_count = len(row_centers)
        thirds = [
            row_centers[index * row_count // 3:(index + 1) * row_count // 3]
            for index in range(3)
        ]
        means = [float(np.mean(part)) for part in thirds if part]
        if len(means) != 3:
            continue
        middle_shift = abs(means[1] - (means[0] + means[2]) / 2)
        outer_difference = abs(means[0] - means[2])
        if middle_shift < spacing * 0.2 or outer_difference > spacing * 0.8:
            continue

        found.append((
            x, y_start + y, width, height,
            round(min(1.0, middle_shift / spacing), 3),
        ))
    return found


def detect_staff_grouping_mark_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
    *,
    left_margin_ratio: float = 0.18,
    max_width_spacing: float = 1.2,
    max_interstaff_gap_spacing: float = 8.0,
) -> list[StaffGroupingMarkCandidate]:
    """Propone corchetes rectos, llaves curvas y trazos verticales candidatos.

    El umbral de separación entre pentagramas es configurable y local a este
    detector. La forma curva se busca como un componente alto, estrecho y con
    desplazamiento lateral de su zona media. Ninguna etiqueta confirma piano,
    coro, instrumento ni relación musical entre pentagramas.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    if not 0 < left_margin_ratio <= 1:
        raise ValueError("left_margin_ratio debe estar entre 0 y 1")
    if max_width_spacing <= 0:
        raise ValueError("max_width_spacing debe ser positivo")
    if max_interstaff_gap_spacing <= 0:
        raise ValueError("max_interstaff_gap_spacing debe ser positivo")
    if not staves:
        return []

    systems = detect_staff_systems(
        staves, max_interstaff_gap_spacing=max_interstaff_gap_spacing
    )
    ink = cv2.bitwise_not(binary)
    page_height, page_width = binary.shape
    left_width = max(1, int(page_width * left_margin_ratio))
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
        spacing = float(np.median([staves[i].spacing_px for i in indices]))

        roi = ink[top:bottom + 1, :left_width]
        kernel_height = max(8, int(round(span * 0.72)))
        vertical = cv2.morphologyEx(
            roi, cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_height)),
        )
        count, _, stats, centroids = cv2.connectedComponentsWithStats(vertical, 8)
        for label in range(1, count):
            _, y, width, height, _ = (int(v) for v in stats[label])
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
            results.append(StaffGroupingMarkCandidate(
                x=round(float(centroids[label][0]), 2),
                y_top=top + y,
                y_bottom=top + y + height - 1,
                width_px=width,
                staff_indices=indices,
                vertical_coverage=round(min(1.0, coverage), 3),
                kind=(
                    "square_bracket_candidate" if is_bracket
                    else "vertical_grouping_mark_candidate"
                ),
                confidence=round(min(0.84, 0.54 + (0.06 if is_bracket else 0.0)), 3),
                warning=(
                    "Forma compatible con un corchete recto por sus dos remates; "
                    "requiere revisión visual y no confirma instrumento ni relación "
                    "musical entre pentagramas."
                    if is_bracket else
                    "Trazo vertical candidato a marca de agrupación; no confirma "
                    "instrumento ni relación musical entre pentagramas."
                ),
            ))

        for x, y_top, width, height, curve_strength in _curved_brace_components(
            ink, top=top, bottom=bottom, spacing=spacing, left_width=left_width
        ):
            y_bottom = y_top + height - 1
            if any(
                item.staff_indices == indices
                and item.y_top <= y_bottom and item.y_bottom >= y_top
                and abs(item.x - (x + width / 2)) <= spacing
                for item in results
            ):
                continue
            results.append(StaffGroupingMarkCandidate(
                x=round(x + width / 2, 2),
                y_top=y_top,
                y_bottom=y_bottom,
                width_px=width,
                staff_indices=indices,
                vertical_coverage=round(min(1.0, height / span), 3),
                kind="curly_brace_candidate",
                confidence=round(min(0.72, 0.5 + curve_strength * 0.12), 3),
                warning=(
                    "Componente curvo compatible con una llave musical; requiere "
                    "revisión visual. No confirma piano ni la función de los "
                    "pentagramas agrupados."
                ),
            ))

    results.sort(key=lambda item: (item.y_top, item.x))
    return results
