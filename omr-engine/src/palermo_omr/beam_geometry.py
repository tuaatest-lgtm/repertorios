"""Detección local de barras compartidas anclada en parejas de plicas.

La búsqueda no recorre la página en busca de diagonales: parte de dos cabezas
con plicas compatibles, estima sus anclajes y verifica continuidad raster a lo
largo del segmento que podría unirlas. El resultado es evidencia geométrica,
no una duración musical confirmada.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .imaging import StaffCandidate
from .rhythm import RhythmCandidate
from .symbols import NoteheadCandidate


@dataclass(frozen=True)
class LocalBeamCandidate:
    notehead_indices: tuple[int, int]
    start: tuple[int, int]
    end: tuple[int, int]
    beam_count: int
    slope: float
    support: float
    bbox: tuple[int, int, int, int]


def _sample_line(
    ink: np.ndarray,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    half_width: int = 1,
) -> tuple[float, float]:
    """Devuelve cobertura longitudinal y densidad perpendicular de tinta."""
    dx, dy = x2 - x1, y2 - y1
    length = max(2, int(math.ceil(math.hypot(dx, dy))))
    nx, ny = -dy / max(math.hypot(dx, dy), 1.0), dx / max(math.hypot(dx, dy), 1.0)
    present = 0
    density = 0.0
    valid = 0
    height, width = ink.shape
    for step in range(length + 1):
        ratio = step / length
        x = x1 + dx * ratio
        y = y1 + dy * ratio
        samples = []
        for offset in range(-half_width, half_width + 1):
            px = int(round(x + nx * offset))
            py = int(round(y + ny * offset))
            if 0 <= px < width and 0 <= py < height:
                samples.append(int(ink[py, px]))
        if samples:
            valid += 1
            count = sum(samples)
            density += count / len(samples)
            if count >= 2:
                present += 1
    if valid == 0:
        return 0.0, 0.0
    return present / valid, density / valid


def _stem_reaches_anchor(
    ink: np.ndarray,
    head: NoteheadCandidate,
    stem_x: int,
    anchor_y: int,
    direction: str,
) -> bool:
    """Exige continuidad vertical entre el núcleo de cabeza y el anclaje."""
    cy = int(round(head.center_y))
    x0, x1 = max(0, stem_x - 1), min(ink.shape[1], stem_x + 2)
    vertical_sign = -1 if direction == "up" else 1

    # Primero localiza el extremo real de la plica recorriéndola desde la
    # cabeza. No basta con que la barra pase cerca: debe tocar el extremo.
    tip_y = None
    gap = 0
    for y in range(cy, -1 if direction == "up" else ink.shape[0], vertical_sign):
        if ink[y, x0:x1].any():
            tip_y = y
            gap = 0
        else:
            gap += 1
            if gap > 1 and tip_y is not None:
                break
    if tip_y is None or abs(anchor_y - tip_y) > 2:
        return False

    start, end = sorted((cy, anchor_y))
    if end - start < 3:
        return False
    values = []
    for y in range(start, end + 1):
        values.append(bool(ink[y, x0:x1].any()))
    coverage = sum(values) / len(values)
    longest_gap = current = 0
    for value in values:
        current = 0 if value else current + 1
        longest_gap = max(longest_gap, current)
    return coverage >= 0.78 and longest_gap <= 1


def _parallel_beam_count(
    ink: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    spacing: float,
) -> int:
    """Cuenta centros de trazos paralelos sin confundir grosor con cantidad."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = max(math.hypot(dx, dy), 1.0)
    nx, ny = -dy / length, dx / length
    offsets_with_support: list[float] = []
    max_offset = spacing * 3.6
    offset = spacing * 0.42
    while offset <= max_offset:
        for sign in (-1.0, 1.0):
            shift = sign * offset
            support, density = _sample_line(
                ink,
                start[0] + nx * shift,
                start[1] + ny * shift,
                end[0] + nx * shift,
                end[1] + ny * shift,
                half_width=1,
            )
            if support >= 0.78 and density >= 0.62:
                offsets_with_support.append(shift)
        offset += 1.0

    clusters: list[list[float]] = []
    for value in sorted(offsets_with_support):
        if not clusters or value - clusters[-1][-1] > 2.5:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    return min(4, 1 + len(clusters))


def detect_local_beam_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
    noteheads: list[NoteheadCandidate],
    rhythms: list[RhythmCandidate],
    *,
    max_slope: float = 0.24,
    min_pair_spacing: float = 1.5,
    max_pair_spacing: float = 8.0,
) -> list[LocalBeamCandidate]:
    """Detecta haces inclinados compartidos mediante hipótesis entre dos plicas.

    Se limita a pendientes no horizontales; la ruta horizontal existente sigue
    funcionando en paralelo. Las barras parciales de una sola plica también
    permanecen en el detector anterior.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    if len(noteheads) != len(rhythms):
        raise ValueError("Debe existir un candidato rítmico por cada cabeza")
    if not 0 < max_slope <= 0.5:
        raise ValueError("max_slope debe estar entre 0 y 0.5")

    ink = (binary < 128).astype(np.uint8)
    results: list[LocalBeamCandidate] = []
    for staff_index, staff in enumerate(staves):
        spacing = float(staff.spacing_px)
        if spacing <= 1:
            continue
        staff_heads = [
            index for index, (head, rhythm) in enumerate(zip(noteheads, rhythms))
            if head.staff_index == staff_index and rhythm.stem_direction in ("up", "down")
        ]
        for pos, first_index in enumerate(staff_heads):
            first = noteheads[first_index]
            first_rhythm = rhythms[first_index]
            for second_index in staff_heads[pos + 1:]:
                second = noteheads[second_index]
                second_rhythm = rhythms[second_index]
                dx = second.center_x - first.center_x
                if dx <= 0:
                    continue
                if not spacing * min_pair_spacing <= dx <= spacing * max_pair_spacing:
                    continue
                if first_rhythm.stem_direction != second_rhythm.stem_direction:
                    continue

                direction = first_rhythm.stem_direction
                stem_sign = 1 if direction == "up" else -1
                stem_offset = max(1, int(round(spacing * 0.72)))
                stem_x1 = int(round(first.center_x + stem_sign * stem_offset))
                stem_x2 = int(round(second.center_x + stem_sign * stem_offset))
                if not (0 <= stem_x1 < binary.shape[1] and 0 <= stem_x2 < binary.shape[1]):
                    continue

                # Los extremos de las plicas deben quedar fuera del núcleo de
                # las cabezas y dentro de una longitud tipográfica plausible.
                vertical_sign = -1 if direction == "up" else 1
                best: tuple[float, float, int, int, float] | None = None
                first_min = int(round(first.center_y + vertical_sign * spacing * 4.8))
                first_max = int(round(first.center_y + vertical_sign * spacing * 1.15))
                y_values = range(min(first_min, first_max), max(first_min, first_max) + 1)
                for y1 in y_values:
                    for slope_step in range(-10, 11):
                        slope = slope_step * max_slope / 10.0
                        if abs(slope) < 0.08:
                            continue
                        y2_float = y1 + slope * (stem_x2 - stem_x1)
                        y2 = int(round(y2_float))
                        distance2 = (y2 - second.center_y) * vertical_sign
                        if not spacing * 1.15 <= distance2 <= spacing * 4.8:
                            continue
                        support, density = _sample_line(
                            ink, stem_x1, y1, stem_x2, y2, half_width=1
                        )
                        if support < 0.82 or density < 0.68:
                            continue
                        if not _stem_reaches_anchor(ink, first, stem_x1, y1, direction):
                            continue
                        if not _stem_reaches_anchor(ink, second, stem_x2, y2, direction):
                            continue
                        score = support * 0.75 + density * 0.25 - abs(slope) * 0.025
                        if best is None or score > best[0]:
                            best = (score, slope, y1, y2, support)

                if best is None:
                    continue
                score, slope, y1, y2, support = best
                start, end = (stem_x1, y1), (stem_x2, y2)
                beam_count = _parallel_beam_count(ink, start, end, spacing)
                left, right = min(stem_x1, stem_x2), max(stem_x1, stem_x2)
                top, bottom = min(y1, y2), max(y1, y2)
                results.append(LocalBeamCandidate(
                    notehead_indices=(first_index, second_index),
                    start=start,
                    end=end,
                    beam_count=beam_count,
                    slope=round(slope, 4),
                    support=round(support, 3),
                    bbox=(left, top, right - left + 1, bottom - top + 1),
                ))

    # Un mismo par puede admitir varios trazos candidatos; conservar la
    # hipótesis con mayor soporte y evitar duplicados por pequeñas variaciones.
    unique: dict[tuple[int, int], LocalBeamCandidate] = {}
    for candidate in results:
        previous = unique.get(candidate.notehead_indices)
        if previous is None or candidate.support > previous.support:
            unique[candidate.notehead_indices] = candidate
    return list(unique.values())
