"""Agrupación geométrica preliminar de barras compartidas entre notas.

Los grupos son candidatos visuales; no constituyen una lectura rítmica validada.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .imaging import StaffCandidate
from .rhythm import RhythmCandidate
from .symbols import NoteheadCandidate


@dataclass(frozen=True)
class BeamGroupCandidate:
    staff_index: int
    notehead_indices: list[int]
    bbox: tuple[int, int, int, int]
    beam_count_candidate: int
    confidence: float
    warning: str
    connection_type_candidate: str = "shared"

    def to_dict(self) -> dict:
        return asdict(self)


def _stem_reaches_beam(
    ink: np.ndarray,
    head: NoteheadCandidate,
    beam_y: float,
    stem_x: int,
) -> bool:
    """Comprueba continuidad raster entre el extremo de la plica y la barra.

    Se tolera como máximo un píxel aislado sin tinta para absorber pequeños
    defectos de rasterización; huecos mayores no se consideran conexión.
    """
    head_y = int(round(head.center_y))
    beam_row = int(round(beam_y))
    y_start, y_end = sorted((beam_row, head_y))
    if y_end - y_start < 2:
        return False

    present = []
    for y in range(y_start, y_end + 1):
        x0 = max(0, stem_x - 1)
        x1 = min(ink.shape[1], stem_x + 2)
        present.append(bool(ink[y, x0:x1].any()))

    coverage = sum(present) / len(present)
    longest_gap = current_gap = 0
    for is_present in present:
        if is_present:
            current_gap = 0
        else:
            current_gap += 1
            longest_gap = max(longest_gap, current_gap)
    return coverage >= 0.84 and longest_gap <= 1



def _beam_y_at_x(
    ink: np.ndarray,
    segment: tuple[int, int, int, int],
    stem_x: int,
) -> float:
    """Estima la altura local del haz donde cruza la plica.

    Usar el centro global del bbox falla en haces inclinados: puede quedar
    varios píxeles separado del punto real de conexión de una plica.
    """
    x, y, width, height = segment
    x0 = max(0, stem_x - 1)
    x1 = min(ink.shape[1], stem_x + 2)
    y0 = max(0, y)
    y1 = min(ink.shape[0], y + height)
    pixels = np.argwhere(ink[y0:y1, x0:x1] > 0)
    if pixels.size == 0:
        return float(y + height / 2.0)
    return float(y0 + np.median(pixels[:, 0]))


def detect_beam_group_candidates(
    binary: np.ndarray,
    staves: list[StaffCandidate],
    noteheads: list[NoteheadCandidate],
    rhythms: list[RhythmCandidate],
    *,
    min_beam_width_spacing: float = 1.25,
    max_beam_width_spacing: float = 10.0,
    max_head_gap_spacing: float = 0.8,
) -> list[BeamGroupCandidate]:
    """Agrupa cabezas conectadas por una o varias barras horizontales.

    Primero asocia cada trazo horizontal a un conjunto de cabezas y después
    cuenta los trazos paralelos de ese mismo conjunto. No agrupa por cercanía
    solamente y no convierte el resultado en una figura confirmada.
    """
    if binary is None or binary.ndim != 2 or binary.size == 0:
        raise ValueError("Se requiere una imagen binaria monocroma no vacía")
    if min_beam_width_spacing <= 0 or max_beam_width_spacing <= min_beam_width_spacing:
        raise ValueError("Los límites de anchura de barra no son válidos")
    if max_head_gap_spacing <= 0:
        raise ValueError("max_head_gap_spacing debe ser positivo")
    if len(noteheads) != len(rhythms):
        raise ValueError("Debe existir un candidato rítmico por cada cabeza de nota")

    ink = (binary < 128).astype(np.uint8)
    results: list[BeamGroupCandidate] = []

    for staff_index, staff in enumerate(staves):
        spacing = float(staff.spacing_px)
        if spacing <= 1:
            continue
        top = max(0, int(round(float(staff.lines_y[0]) - 4.5 * spacing)))
        bottom = min(binary.shape[0] - 1, int(round(float(staff.lines_y[-1]) + 4.5 * spacing)))

        # Extrae trazos por filas. Los componentes conectados tradicionales
        # fusionan barras paralelas cuando ambas cruzan las mismas plicas.
        row_runs: list[tuple[int, int, int, int]] = []
        min_width = spacing * min_beam_width_spacing
        max_width = spacing * max_beam_width_spacing
        for y in range(top, bottom + 1):
            xs = np.flatnonzero(ink[y])
            if xs.size == 0:
                continue
            chunks = np.split(xs, np.where(np.diff(xs) > 1)[0] + 1)
            for chunk in chunks:
                x = int(chunk[0])
                width = int(chunk[-1] - chunk[0] + 1)
                if min_width <= width <= max_width:
                    row_runs.append((x, y, width, 1))

        # Reúne filas contiguas con solapamiento horizontal en un solo trazo.
        strokes: list[list[tuple[int, int, int, int]]] = []
        for run in row_runs:
            x, y, width, _height = run
            matching = None
            for stroke in reversed(strokes):
                last = stroke[-1]
                if last[1] < y - 1:
                    break
                overlap = min(x + width, last[0] + last[2]) - max(x, last[0])
                if last[1] == y - 1 and overlap >= 0.5 * min(width, last[2]):
                    matching = stroke
                    break
            if matching is None:
                strokes.append([run])
            else:
                matching.append(run)

        segments: list[tuple[int, int, int, int]] = []
        for stroke in strokes:
            left = min(item[0] for item in stroke)
            upper = min(item[1] for item in stroke)
            right = max(item[0] + item[2] for item in stroke)
            lower = max(item[1] + item[3] for item in stroke)
            width = right - left
            height = lower - upper
            # Los haces pueden tener pendiente: una altura de bbox de hasta
            # 0.95 espacios permite inclinaciones locales moderadas sin usar
            # la pendiente como valor rítmico. La duración sigue dependiendo
            # del número de trazos conectados a las plicas.
            if height <= max(2, int(round(spacing * 0.95))):
                segments.append((left, upper, width, height))

        # Complementa los trazos horizontales con segmentos inclinados
        # detectados localmente. Solo se admiten candidatos que cubran dos
        # anclajes de plica distintos; fragmentos de plica o haces parciales
        # quedan fuera de esta ruta y siguen tratándose por el detector local.
        staff_roi = ink[top:bottom + 1, :]
        diagonal_lines = cv2.HoughLinesP(
            staff_roi, rho=1, theta=np.pi / 180.0,
            threshold=max(6, int(round(spacing * 0.75))),
            minLineLength=max(8, int(round(min_width))),
            maxLineGap=max(1, int(round(spacing * 0.25))),
        )
        if diagonal_lines is not None:
            for line in diagonal_lines[:, 0, :]:
                x1, local_y1, x2, local_y2 = (int(value) for value in line)
                dx, dy = x2 - x1, local_y2 - local_y1
                if dx == 0:
                    continue
                slope = dy / dx
                if abs(slope) < 0.035 or abs(slope) > 0.22:
                    continue
                left, right = sorted((x1, x2))
                upper, lower = min(local_y1, local_y2) + top, max(local_y1, local_y2) + top
                width, height = right - left + 1, lower - upper + 1
                if not (min_width <= width <= max_width and height <= spacing * 1.25):
                    continue
                def line_y_at(anchor_x):
                    return top + local_y1 + slope * (anchor_x - x1)
                eligible = []
                for head_index, (head, rhythm) in enumerate(zip(noteheads, rhythms)):
                    if head.staff_index != staff_index or rhythm.stem_direction == 'none':
                        continue
                    stem_offset = max(1, int(round(spacing * 0.72)))
                    expected_xs = (head.center_x - stem_offset, head.center_x + stem_offset)
                    anchors = [ax for ax in expected_xs
                               if left - spacing * 0.2 <= ax <= right + spacing * 0.2
                               and spacing * 0.8 <= abs(line_y_at(ax) - head.center_y) <= spacing * 4.5]
                    if anchors:
                        eligible.append((head_index, anchors[0]))
                paired = False
                for i, (first_index, first_x) in enumerate(eligible):
                    for second_index, second_x in eligible[i + 1:]:
                        first_head, second_head = noteheads[first_index], noteheads[second_index]
                        first_rhythm, second_rhythm = rhythms[first_index], rhythms[second_index]
                        if first_rhythm.stem_direction != second_rhythm.stem_direction:
                            continue
                        if abs(first_head.center_x - second_head.center_x) < spacing * 1.5:
                            continue
                        if left - spacing * 0.2 <= min(first_x, second_x) and right + spacing * 0.2 >= max(first_x, second_x):
                            paired = True
                            break
                    if paired:
                        break
                if paired:
                    segments.append((left, upper, width, height))
        # La clave es el conjunto exacto de cabezas asociado a cada trazo.
        segments_by_heads: dict[tuple[int, ...], list[tuple[int, int, int, int]]] = {}
        for x, y, w, h in segments:
            if not (min_width <= w <= max_width):
                continue
            beam_y = y + h / 2.0

            matched: list[int] = []
            for head_index, (head, rhythm) in enumerate(zip(noteheads, rhythms)):
                if head.staff_index != staff_index or rhythm.stem_direction == "none":
                    continue
                if not (
                    x - spacing * max_head_gap_spacing
                    <= head.center_x
                    <= x + w + spacing * max_head_gap_spacing
                ):
                    continue
                vertical_distance = beam_y - head.center_y
                if abs(vertical_distance) < spacing * 0.8 or abs(vertical_distance) > spacing * 4.5:
                    continue
                expected_direction = "up" if vertical_distance < 0 else "down"
                if rhythm.stem_direction != expected_direction:
                    continue

                # Una barra debe cruzar la zona donde se espera la plica de
                # esta cabeza. La mera proximidad horizontal puede asociar una
                # barra de otro pentagrama/voz o un trazo editorial cercano.
                stem_offset = max(1, int(round(spacing * 0.72)))
                stem_tolerance = max(2, int(round(spacing * 0.20)))
                expected_stem_xs = (
                    int(round(head.center_x - stem_offset)),
                    int(round(head.center_x + stem_offset)),
                )
                intersects_expected_stem = any(
                    x - stem_tolerance <= stem_x <= x + w - 1 + stem_tolerance
                    for stem_x in expected_stem_xs
                )
                if not intersects_expected_stem:
                    continue

                # Además de cruzar la posición esperada, la plica debe llegar
                # físicamente hasta la barra en la imagen binaria. Esto evita
                # asociar segmentos cercanos separados por un hueco visible.
                connected_stem_x = next(
                    (
                        stem_x for stem_x in expected_stem_xs
                        if x - stem_tolerance <= stem_x <= x + w - 1 + stem_tolerance
                        and _stem_reaches_beam(
                            ink, head, _beam_y_at_x(ink, (x, y, w, h), stem_x), stem_x
                        )
                    ),
                    None,
                )
                if connected_stem_x is None:
                    continue

                matched.append(head_index)

            matched_tuple = tuple(sorted(set(matched), key=lambda idx: noteheads[idx].center_x))
            # Una barra corta puede ser un haz parcial unido a una sola plica.
            # Se conserva como candidato separado, nunca como grupo compartido.
            if len(matched_tuple) >= 1:
                segments_by_heads.setdefault(matched_tuple, []).append((x, y, w, h))

        for matched, segments in segments_by_heads.items():
            # Agrupa trazos paralelos por proximidad vertical. El criterio usa
            # la separación entre trazos consecutivos, no el centro móvil del bbox.
            segments.sort(key=lambda item: item[1] + item[3] / 2.0)
            clusters: list[list[tuple[int, int, int, int]]] = []
            for segment in segments:
                center_y = segment[1] + segment[3] / 2.0
                if not clusters:
                    clusters.append([segment])
                    continue
                previous = clusters[-1][-1]
                previous_y = previous[1] + previous[3] / 2.0
                if center_y - previous_y <= spacing * 0.75:
                    clusters[-1].append(segment)
                else:
                    clusters.append([segment])

            for cluster in clusters:
                left = min(item[0] for item in cluster)
                upper = min(item[1] for item in cluster)
                right = max(item[0] + item[2] for item in cluster)
                lower = max(item[1] + item[3] for item in cluster)
                beam_count = min(4, len(cluster))
                is_partial = len(matched) == 1
                confidence = min(
                    0.78,
                    (0.42 if is_partial else 0.48)
                    + 0.08 * max(0, len(matched) - 2)
                    + 0.04 * (beam_count - 1),
                )
                results.append(BeamGroupCandidate(
                    staff_index=staff_index,
                    notehead_indices=list(matched),
                    bbox=(left, upper, right - left, lower - upper),
                    beam_count_candidate=beam_count,
                    confidence=round(confidence, 3),
                    warning=(
                        "Haz parcial candidato unido a una sola plica; puede confundirse "
                        "con una bandera o trazo y requiere validación visual."
                        if is_partial else
                        "Grupo de barras compartidas candidato: el recuento geométrico "
                        "no confirma por sí solo figuras, subdivisión rítmica ni voces."
                    ),
                    connection_type_candidate="partial" if is_partial else "shared",
                ))

    results.sort(key=lambda item: (item.staff_index, item.bbox[0], item.bbox[1]))
    return results
