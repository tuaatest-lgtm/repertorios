"""Detección local de barras compartidas anclada en parejas de plicas.

La búsqueda no recorre la página en busca de diagonales: parte de dos cabezas
con plicas compatibles, estima sus anclajes y verifica continuidad raster a lo
largo del segmento que podría unirlas. El resultado es evidencia geométrica,
no una duración musical confirmada.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import cv2
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


def _find_stem_anchor(
    vertical_ink: np.ndarray,
    head: NoteheadCandidate,
    spacing: float,
    direction: str,
) -> tuple[int, int, int] | None:
    """Localiza la plica dentro de la caja de la cabeza y devuelve su extremo.

    La apertura vertical elimina la mayoría de barras y líneas horizontales.
    La búsqueda queda limitada al entorno de la cabeza y a la longitud
    tipográfica esperada, evitando capturar plicas de otros sistemas.
    """
    x, _y, width, _height = head.bbox
    center_y = int(round(head.center_y))
    sign = -1 if direction == "up" else 1
    expected_x = head.center_x + sign * spacing * 0.72
    x_min = max(0, int(x) - 3)
    x_max = min(vertical_ink.shape[1] - 1, int(x + width) + 3)
    y_start = center_y + sign * int(round(spacing * 0.25))
    y_stop = center_y + sign * int(round(spacing * 4.8))

    best: tuple[float, int, int, int] | None = None
    for stem_x in range(x_min, x_max + 1):
        column = vertical_ink[
            :, max(0, stem_x - 1):min(vertical_ink.shape[1], stem_x + 2)
        ].max(axis=1)
        run_start = last_y = None
        gap = 0
        for y in range(y_start, y_stop, sign):
            if column[y]:
                if run_start is None:
                    run_start = y
                last_y = y
                gap = 0
            elif run_start is not None:
                gap += 1
                if gap > 1:
                    break
        if run_start is None or last_y is None:
            continue
        run_length = abs(last_y - run_start) + 1
        if run_length < spacing * 1.35:
            continue
        score = run_length - abs(stem_x - expected_x) * 0.25
        if best is None or score > best[0]:
            best = (score, stem_x, last_y, run_length)

    if best is None:
        return None
    return best[1], best[2], best[3]


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
    """Detecta haces inclinados siguiendo los extremos reales de las plicas.

    La trayectoria candidata se define por los extremos de dos plicas
    localizadas en la imagen, no por posiciones estimadas desde el centro de
    las cabezas. La ruta horizontal sigue siendo independiente.
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

        vertical_ink = cv2.morphologyEx(
            ink,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(
                cv2.MORPH_RECT,
                (1, max(3, int(round(spacing * 1.8)))),
            ),
        )
        anchors: dict[int, tuple[int, int, int]] = {}
        for index, (head, rhythm) in enumerate(zip(noteheads, rhythms)):
            if head.staff_index != staff_index or rhythm.stem_direction not in ("up", "down"):
                continue
            anchor = _find_stem_anchor(
                vertical_ink, head, spacing, rhythm.stem_direction
            )
            if anchor is not None:
                anchors[index] = anchor

        staff_heads = sorted(anchors, key=lambda index: noteheads[index].center_x)
        for pos, first_index in enumerate(staff_heads):
            first = noteheads[first_index]
            first_rhythm = rhythms[first_index]
            stem_x1, tip_y1, _length1 = anchors[first_index]
            for second_index in staff_heads[pos + 1:]:
                second = noteheads[second_index]
                second_rhythm = rhythms[second_index]
                if first_rhythm.stem_direction != second_rhythm.stem_direction:
                    continue
                stem_x2, tip_y2, _length2 = anchors[second_index]
                dx = stem_x2 - stem_x1
                if dx <= 0 or not spacing * min_pair_spacing <= dx <= spacing * max_pair_spacing:
                    continue

                slope = (tip_y2 - tip_y1) / dx
                if abs(slope) < 0.08 or abs(slope) > max_slope:
                    continue

                support, density = _sample_line(
                    ink, stem_x1, tip_y1, stem_x2, tip_y2, half_width=1
                )
                if support < 0.82 or density < 0.68:
                    continue

                start, end = (stem_x1, tip_y1), (stem_x2, tip_y2)
                beam_count = _parallel_beam_count(ink, start, end, spacing)
                left, right = min(stem_x1, stem_x2), max(stem_x1, stem_x2)
                top, bottom = min(tip_y1, tip_y2), max(tip_y1, tip_y2)
                results.append(LocalBeamCandidate(
                    notehead_indices=(first_index, second_index),
                    start=start,
                    end=end,
                    beam_count=beam_count,
                    slope=round(slope, 4),
                    support=round(support, 3),
                    bbox=(left, top, right - left + 1, bottom - top + 1),
                ))

    # Un mismo par puede admitir varios trazos candidatos; conservar una sola
    # hipótesis y no convertir la geometría en duración musical confirmada.
    unique: dict[tuple[int, int], LocalBeamCandidate] = {}
    for candidate in results:
        previous = unique.get(candidate.notehead_indices)
        if previous is None or candidate.support > previous.support:
            unique[candidate.notehead_indices] = candidate
    return list(unique.values())
