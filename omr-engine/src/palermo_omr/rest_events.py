"""Conversión de silencios solo después de revisión humana explícita.

Los detectores geométricos no deciden tipo, duración, voz ni posición temporal.
Este adaptador requiere que una persona confirme esos datos antes de producir
un OrderedVoiceEvent de tipo rest.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from collections.abc import Sequence

from .rhythm_symbols import RestSymbolCandidate
from .voice_sequence_timing import OrderedVoiceEvent


@dataclass(frozen=True)
class RestReviewAssignment:
    candidate_index: int
    event_id: str
    voice_id: str
    measure_index: int
    order_index: int
    duration_quarters: Fraction | int | float
    confirmed_rest_type: str
    reviewer_confirmed: bool


def build_reviewed_rest_events(
    candidates: Sequence[RestSymbolCandidate],
    assignments: Sequence[RestReviewAssignment],
) -> tuple[OrderedVoiceEvent, ...]:
    """Crea eventos de silencio únicamente a partir de asignaciones confirmadas.

    candidate_index refiere al índice del candidato en la secuencia revisada.
    voice_id, measure_index, order_index, duración y tipo deben ser decididos
    por la revisión humana; ninguna coordenada de imagen se transforma en tiempo.
    """
    allowed_types = {
        "whole", "half", "quarter", "eighth", "sixteenth",
        "thirty_second", "sixty_fourth",
    }
    seen_candidates: set[int] = set()
    seen_event_ids: set[str] = set()
    seen_positions: set[tuple[str, int, int]] = set()
    results: list[OrderedVoiceEvent] = []

    for assignment in assignments:
        if not isinstance(assignment, RestReviewAssignment):
            raise ValueError("Todas las asignaciones deben ser RestReviewAssignment")
        if not isinstance(assignment.candidate_index, int) or isinstance(assignment.candidate_index, bool):
            raise ValueError("candidate_index debe ser entero")
        if not 0 <= assignment.candidate_index < len(candidates):
            raise ValueError("candidate_index fuera del rango de candidatos")
        if assignment.candidate_index in seen_candidates:
            raise ValueError("Un candidato de silencio no puede asignarse dos veces")
        seen_candidates.add(assignment.candidate_index)
        if not isinstance(assignment.event_id, str) or not assignment.event_id.strip():
            raise ValueError("event_id debe ser texto no vacío")
        if assignment.event_id in seen_event_ids:
            raise ValueError("event_id debe ser único")
        seen_event_ids.add(assignment.event_id)
        if not isinstance(assignment.voice_id, str) or not assignment.voice_id.strip():
            raise ValueError("voice_id debe ser explícito y no vacío")
        if not isinstance(assignment.measure_index, int) or isinstance(assignment.measure_index, bool) or assignment.measure_index < 0:
            raise ValueError("measure_index debe ser entero no negativo")
        if not isinstance(assignment.order_index, int) or isinstance(assignment.order_index, bool) or assignment.order_index < 0:
            raise ValueError("order_index debe ser entero no negativo")
        position = (assignment.voice_id, assignment.measure_index, assignment.order_index)
        if position in seen_positions:
            raise ValueError("order_index debe ser único por voz y compás")
        seen_positions.add(position)
        if assignment.confirmed_rest_type not in allowed_types:
            raise ValueError("confirmed_rest_type no reconocido")
        if assignment.reviewer_confirmed is not True:
            raise ValueError("El silencio requiere confirmación humana explícita")
        value = assignment.duration_quarters
        if isinstance(value, bool):
            raise ValueError("La duración no puede ser booleana")
        try:
            duration = value if isinstance(value, Fraction) else Fraction(str(value))
        except (ValueError, TypeError, ZeroDivisionError) as exc:
            raise ValueError("Duración musical inválida") from exc
        if duration <= 0:
            raise ValueError("La duración debe ser mayor que cero")

        candidate = candidates[assignment.candidate_index]
        if not isinstance(candidate, RestSymbolCandidate):
            raise ValueError("El candidato seleccionado no es RestSymbolCandidate")

        results.append(OrderedVoiceEvent(
            event_id=assignment.event_id,
            voice_id=assignment.voice_id,
            measure_index=assignment.measure_index,
            order_index=assignment.order_index,
            duration_quarters=duration,
            event_type="rest",
            notehead_ids=(),
        ))

    return tuple(sorted(results, key=lambda event: (event.voice_id, event.measure_index, event.order_index)))
