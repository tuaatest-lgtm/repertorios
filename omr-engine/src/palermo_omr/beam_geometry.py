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
    notehead_indices: tuple[int, ...]
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
    # Limitar el recorrido a la imagen: los extremos de plica pueden quedar
    # parcialmente recortados en el borde de una página o de un recorte.
    image_height = vertical_ink.shape[0]
    y_start = min(image_height - 1, max(0, y_start))
    if sign < 0:
        y_stop = min(image_height - 1, max(-1, y_stop))
    else:
        y_stop = min(image_height, max(0, y_stop))

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


def _fit_beam_centerline(
    ink: np.ndarray,
    x1: int,
    tip_y1: int,
    x2: int,
    tip_y2: int,
    spacing: float,
) -> tuple[float, float, float, float, float] | None:
    """Ajusta la línea central de la barra dentro de la banda entre dos plicas.

    Los extremos de las plicas solo acotan la búsqueda: no se asume que el
    extremo raster de cada plica coincida exactamente con el centro de la barra.
    El ajuste sigue el centro de los trazos gruesos y rechaza líneas finas del
    pentagrama.
    """
    dx = x2 - x1
    if dx < 5:
        return None
    tolerance = max(4, int(round(spacing * 0.65)))
    min_thickness = max(3, int(round(spacing * 0.22)))
    sample_x: list[int] = []
    sample_y: list[float] = []

    for x in range(x1 + 2, x2 - 1):
        ratio = (x - x1) / dx
        predicted_y = tip_y1 + (tip_y2 - tip_y1) * ratio
        top = max(0, int(math.floor(predicted_y - tolerance)))
        bottom = min(
            ink.shape[0],
            int(math.ceil(predicted_y + tolerance)) + 1,
        )
        column = ink[top:bottom, x]
        runs: list[list[int]] = []
        run: list[int] = []
        for offset, present in enumerate(column):
            if present:
                run.append(offset)
            elif run:
                runs.append(run)
                run = []
        if run:
            runs.append(run)

        options: list[tuple[float, float]] = []
        for stroke in runs:
            thickness = len(stroke)
            if thickness < min_thickness:
                continue
            center_y = top + (stroke[0] + stroke[-1]) / 2.0
            distance = abs(center_y - predicted_y)
            if distance > tolerance:
                continue
            options.append((thickness - distance * 0.35, center_y))
        if options:
            _score, center_y = max(options, key=lambda item: item[0])
            sample_x.append(x)
            sample_y.append(center_y)

    if len(sample_x) < dx * 0.72:
        return None
    slope, intercept = np.polyfit(
        np.asarray(sample_x, dtype=np.float64),
        np.asarray(sample_y, dtype=np.float64),
        1,
    )
    fitted_y = slope * np.asarray(sample_x) + intercept
    residual = float(np.median(np.abs(np.asarray(sample_y) - fitted_y)))
    if residual > 2.0:
        return None

    y1 = float(slope * x1 + intercept)
    y2 = float(slope * x2 + intercept)
    support, density = _sample_line(
        ink, x1, y1, x2, y2, half_width=2
    )
    if support < 0.82 or density < 0.80:
        return None
    return float(slope), y1, y2, support, density


def _parallel_beam_count(
    ink: np.ndarray,
    start: tuple[int, int],
    end: tuple[int, int],
    spacing: float,
) -> int:
    """Cuenta trazos gruesos paralelos; descarta líneas de pentagrama finas."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = max(math.hypot(dx, dy), 1.0)
    nx, ny = -dy / length, dx / length
    middle_x = (start[0] + end[0]) / 2.0
    middle_y = (start[1] + end[1]) / 2.0
    max_offset = int(round(spacing * 3.6))

    profile: list[int] = []
    offsets = list(range(-max_offset, max_offset + 1))
    for offset in offsets:
        px = int(round(middle_x + nx * offset))
        py = int(round(middle_y + ny * offset))
        profile.append(
            int(0 <= px < ink.shape[1] and 0 <= py < ink.shape[0] and ink[py, px])
        )

    runs: list[list[int]] = []
    run: list[int] = []
    for offset, present in zip(offsets, profile):
        if present:
            if run and offset > run[-1] + 1:
                runs.append(run)
                run = []
            run.append(offset)
        elif run:
            runs.append(run)
            run = []
    if run:
        runs.append(run)

    # En la escala local, una barra suele ser sensiblemente más gruesa que
    # una línea del pentagrama. El umbral es proporcional al interlineado.
    min_thickness = max(3, int(round(spacing * 0.22)))
    count = 0
    for stroke in runs:
        if len(stroke) < min_thickness:
            continue
        center_offset = float(np.mean(stroke))
        support, density = _sample_line(
            ink,
            start[0] + nx * center_offset,
            start[1] + ny * center_offset,
            end[0] + nx * center_offset,
            end[1] + ny * center_offset,
            half_width=1,
        )
        if support >= 0.78 and density >= 0.62:
            count += 1
    return max(1, min(4, count))


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
        # Cabezas de un mismo acorde pueden compartir una plica. Agrupamos
        # por extremo detectado para no crear pares duplicados ni separar acordes.
        heads_by_stem: dict[tuple[int, int, str], list[int]] = {}
        for index, (head, rhythm) in enumerate(zip(noteheads, rhythms)):
            if head.staff_index != staff_index or rhythm.stem_direction not in ("up", "down"):
                continue
            anchor = _find_stem_anchor(
                vertical_ink, head, spacing, rhythm.stem_direction
            )
            if anchor is None:
                continue
            stem_x, tip_y, _stem_length = anchor
            key = (stem_x, tip_y, rhythm.stem_direction)
            heads_by_stem.setdefault(key, []).append(index)

        stem_keys = sorted(
            heads_by_stem,
            key=lambda key: (key[0], key[1]),
        )
        for pos, first_key in enumerate(stem_keys):
            stem_x1, tip_y1, direction1 = first_key
            first_indices = heads_by_stem[first_key]
            for second_key in stem_keys[pos + 1:]:
                stem_x2, tip_y2, direction2 = second_key
                if direction1 != direction2:
                    continue
                dx = stem_x2 - stem_x1
                if dx <= 0 or not spacing * min_pair_spacing <= dx <= spacing * max_pair_spacing:
                    continue

                fitted = _fit_beam_centerline(
                    ink, stem_x1, tip_y1, stem_x2, tip_y2, spacing
                )
                if fitted is None:
                    continue
                slope, beam_y1, beam_y2, support, _density = fitted
                if abs(slope) < 0.04 or abs(slope) > max_slope:
                    continue

                second_indices = heads_by_stem[second_key]
                linked_indices = list(first_indices + second_indices)
                intercept = beam_y1 - slope * stem_x1
                # Incluye plicas intermedias que descansan sobre la misma
                # trayectoria, no solo las dos cabezas de los extremos.
                for middle_key in stem_keys:
                    middle_x, middle_tip_y, middle_direction = middle_key
                    if middle_direction != direction1 or not stem_x1 < middle_x < stem_x2:
                        continue
                    distance = abs(
                        middle_tip_y - (slope * middle_x + intercept)
                    ) / math.sqrt(1.0 + slope * slope)
                    if distance <= max(2.0, spacing * 0.20):
                        linked_indices.extend(heads_by_stem[middle_key])
                linked_heads = tuple(sorted(
                    set(linked_indices),
                    key=lambda index: (noteheads[index].center_x, noteheads[index].center_y),
                ))
                start = (stem_x1, int(round(beam_y1)))
                end = (stem_x2, int(round(beam_y2)))
                beam_count = _parallel_beam_count(ink, start, end, spacing)
                left, right = min(stem_x1, stem_x2), max(stem_x1, stem_x2)
                top, bottom = sorted((start[1], end[1]))
                results.append(LocalBeamCandidate(
                    notehead_indices=linked_heads,
                    start=start,
                    end=end,
                    beam_count=beam_count,
                    slope=round(slope, 4),
                    support=round(support, 3),
                    bbox=(left, top, right - left + 1, bottom - top + 1),
                ))

    # Colapsa parejas redundantes cuando una hipótesis más larga ya contiene
    # las plicas intermedias de la misma trayectoria y el mismo nivel de barra.
    filtered: list[LocalBeamCandidate] = []
    for candidate in results:
        candidate_set = set(candidate.notehead_indices)
        candidate_slope = (
            (candidate.end[1] - candidate.start[1])
            / max(1, candidate.end[0] - candidate.start[0])
        )
        candidate_intercept = candidate.start[1] - candidate_slope * candidate.start[0]
        is_subset = False
        for other in results:
            if other is candidate or other.beam_count != candidate.beam_count:
                continue
            if not candidate_set < set(other.notehead_indices):
                continue
            other_slope = (
                (other.end[1] - other.start[1])
                / max(1, other.end[0] - other.start[0])
            )
            other_intercept = other.start[1] - other_slope * other.start[0]
            if abs(candidate_slope - other_slope) > 0.025:
                continue
            if abs(candidate_intercept - other_intercept) > 3.0:
                continue
            if other.bbox[0] <= candidate.bbox[0] and (
                other.bbox[0] + other.bbox[2]
                >= candidate.bbox[0] + candidate.bbox[2]
            ):
                is_subset = True
                break
        if not is_subset:
            filtered.append(candidate)

    unique: dict[tuple[int, ...], LocalBeamCandidate] = {}
    for candidate in filtered:
        previous = unique.get(candidate.notehead_indices)
        if previous is None or candidate.support > previous.support:
            unique[candidate.notehead_indices] = candidate
    return list(unique.values())
