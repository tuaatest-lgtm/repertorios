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

    def to_dict(self) -> dict:
        return asdict(self)


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
            if height <= max(2, int(round(spacing * 0.55))):
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
                matched.append(head_index)

            matched_tuple = tuple(sorted(set(matched), key=lambda idx: noteheads[idx].center_x))
            if len(matched_tuple) >= 2:
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
                confidence = min(0.78, 0.48 + 0.08 * (len(matched) - 2) + 0.04 * (beam_count - 1))
                results.append(BeamGroupCandidate(
                    staff_index=staff_index,
                    notehead_indices=list(matched),
                    bbox=(left, upper, right - left, lower - upper),
                    beam_count_candidate=beam_count,
                    confidence=round(confidence, 3),
                    warning=(
                        "Grupo de barras compartidas candidato: el recuento geométrico "
                        "no confirma por sí solo figuras, subdivisión rítmica ni voces."
                    ),
                ))

    results.sort(key=lambda item: (item.staff_index, item.bbox[0], item.bbox[1]))
    return results
