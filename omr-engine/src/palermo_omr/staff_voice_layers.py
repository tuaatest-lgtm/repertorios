"""Propuestas conservadoras de capas de voz en un mismo pentagrama.

Las direcciones de plica opuestas pueden ser evidencia de voces independientes,
pero no bastan para asignar voces ni para reconstruir sus secuencias.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from collections.abc import Sequence

from .imaging import StaffCandidate
from .rhythm import RhythmCandidate
from .symbols import NoteheadCandidate


@dataclass(frozen=True)
class StaffVoiceLayerCandidate:
    layer_id: str
    staff_index: int
    upward_notehead_indices: tuple[int, ...]
    downward_notehead_indices: tuple[int, ...]
    horizontal_span_spacing: float
    status: str
    confidence: float
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def detect_staff_voice_layer_candidates(
    staves: Sequence[StaffCandidate],
    noteheads: Sequence[NoteheadCandidate],
    rhythms: Sequence[RhythmCandidate],
    *,
    max_horizontal_span_spacing: float = 2.0,
) -> tuple[StaffVoiceLayerCandidate, ...]:
    """Propone zonas con plicas opuestas en un mismo pentagrama.

    La ventana horizontal solo detecta coexistencia local de direcciones de
    plica. No separa notas en voces, no asigna soprano/alto ni mano derecha/
    izquierda, y no genera eventos temporales.
    """
    if len(noteheads) != len(rhythms):
        raise ValueError("Debe existir un análisis rítmico por cada cabeza")
    if max_horizontal_span_spacing <= 0:
        raise ValueError("max_horizontal_span_spacing debe ser positivo")

    by_staff: dict[int, list[int]] = {}
    for index, (head, rhythm) in enumerate(zip(noteheads, rhythms)):
        if head.staff_index != rhythm.staff_index:
            raise ValueError(f"La cabeza y el ritmo {index} pertenecen a pentagramas distintos")
        if not 0 <= head.staff_index < len(staves):
            raise ValueError("Una cabeza referencia un pentagrama inexistente")
        by_staff.setdefault(head.staff_index, []).append(index)

    proposals: list[StaffVoiceLayerCandidate] = []
    for staff_index, indices in sorted(by_staff.items()):
        spacing = float(staves[staff_index].spacing_px)
        if spacing <= 1:
            raise ValueError("El espaciado del pentagrama debe ser mayor que 1 píxel")
        ordered = sorted(indices, key=lambda i: (noteheads[i].center_x, noteheads[i].center_y))
        windows: list[list[int]] = []
        for left_position, left_index in enumerate(ordered):
            left_x = noteheads[left_index].center_x
            window = [
                index for index in ordered[left_position:]
                if noteheads[index].center_x - left_x <= spacing * max_horizontal_span_spacing
            ]
            directions = {rhythms[index].stem_direction for index in window}
            if "up" in directions and "down" in directions:
                windows.append(window)

        # Merge overlapping windows so one continuous passage yields one proposal.
        merged: list[list[int]] = []
        for window in windows:
            members = set(window)
            if merged and members.intersection(merged[-1]):
                merged[-1] = sorted(set(merged[-1]).union(members))
            else:
                merged.append(window)

        for ordinal, members in enumerate(merged, start=1):
            upward = tuple(i for i in members if rhythms[i].stem_direction == "up")
            downward = tuple(i for i in members if rhythms[i].stem_direction == "down")
            if not upward or not downward:
                continue
            span = (
                max(noteheads[i].center_x for i in members)
                - min(noteheads[i].center_x for i in members)
            ) / spacing
            proposals.append(StaffVoiceLayerCandidate(
                layer_id=f"staff-{staff_index + 1}-layer-proposal-{ordinal}",
                staff_index=staff_index,
                upward_notehead_indices=upward,
                downward_notehead_indices=downward,
                horizontal_span_spacing=round(span, 3),
                status="proposed_independent_layers",
                confidence=0.5,
                warnings=(
                    "Coexisten plicas hacia arriba y abajo en una zona horizontal cercana.",
                    "Esto podría indicar voces independientes, pero también puede deberse a notación, "
                    "acordes o detecciones erróneas.",
                    "No se asignan voces ni se generan secuencias temporales; requiere revisión musical.",
                ),
            ))

    return tuple(proposals)
