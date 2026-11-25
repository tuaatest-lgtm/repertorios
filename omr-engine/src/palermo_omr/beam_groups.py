"""Agrupación geométrica preliminar de barras compartidas entre notas.

Los grupos son candidatos visuales; no constituyen una lectura rítmica validada.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np

from .imaging import StaffCandidate
from .symbols import NoteheadCandidate
from .rhythm import RhythmCandidate


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
    """Agrupa dos o más cabezas cuando una barra horizontal parece unirlas.

    La detección exige evidencia de trazo horizontal en la imagen y plicas
    candidatas orientadas hacia ese trazo. No agrupa notas solo por proximidad.
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
        kernel_width = max(3, int(round(spacing * min_beam_width_spacing)))
        horizontal = cv2.morphologyEx(
            ink,
            cv2.MORPH_OPEN,
            cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1)),
        )
        count, _, stats, _ = cv2.connectedComponentsWithStats(horizontal, 8)
        segments: list[tuple[int, int, int, int]] = []
        top = float(staff.lines_y[0]) - 4.5 * spacing
        bottom = float(staff.lines_y[-1]) + 4.5 * spacing

        for label in range(1, count):
            x, y, w, h, area = (int(v) for v in stats[label])
            if not (spacing * min_beam_width_spacing <= w <= spacing * max_beam_width_spacing):
                continue
            if h > max(2, int(round(spacing * 0.55))):
                continue
            cy = y + h / 2.0
            if not top <= cy <= bottom:
                continue
            segments.append((x, y, w, h))

        for x, y, w, h in segments:
            beam_y = y + h / 2.0
            matched: list[int] = []
            for head_index, (head, rhythm) in enumerate(zip(noteheads, rhythms)):
                if head.staff_index != staff_index or rhythm.stem_direction == "none":
                    continue
                if not (x - spacing * max_head_gap_spacing <= head.center_x <=
                        x + w + spacing * max_head_gap_spacing):
                    continue
                vertical_distance = beam_y - head.center_y
                if abs(vertical_distance) < spacing * 0.8 or abs(vertical_distance) > spacing * 4.5:
                    continue
                expected_direction = "up" if vertical_distance < 0 else "down"
                if rhythm.stem_direction != expected_direction:
                    continue
                matched.append(head_index)

            matched = sorted(set(matched), key=lambda idx: noteheads[idx].center_x)
            if len(matched) < 2:
                continue

            # Evita que un mismo grupo se emita repetidamente por segmentos
            # paralelos que representan varias barras del mismo haz.
            existing = next(
                (item for item in results
                 if item.staff_index == staff_index
                 and item.notehead_indices == matched
                 and abs((item.bbox[1] + item.bbox[3] / 2.0) - beam_y) <= spacing * 0.75),
                None,
            )
            if existing is not None:
                pos = results.index(existing)
                old_x, old_y, old_w, old_h = existing.bbox
                new_left = min(old_x, x)
                new_top = min(old_y, y)
                new_right = max(old_x + old_w, x + w)
                new_bottom = max(old_y + old_h, y + h)
                results[pos] = BeamGroupCandidate(
                    staff_index, matched,
                    (new_left, new_top, new_right - new_left, new_bottom - new_top),
                    min(4, existing.beam_count_candidate + 1),
                    max(existing.confidence, 0.72),
                    existing.warning,
                )
                continue

            confidence = min(0.72, 0.48 + 0.08 * (len(matched) - 2))
            results.append(BeamGroupCandidate(
                staff_index=staff_index,
                notehead_indices=matched,
                bbox=(x, y, w, h),
                beam_count_candidate=1,
                confidence=round(confidence, 3),
                warning=(
                    "Grupo de barras compartidas candidato: la geometría no confirma "
                    "figuras, subdivisión rítmica ni pertenencia musical definitiva."
                ),
            ))

    results.sort(key=lambda item: (item.staff_index, item.bbox[0], item.bbox[1]))
    return results
