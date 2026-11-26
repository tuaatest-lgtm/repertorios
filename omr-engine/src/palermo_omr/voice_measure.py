"""Balance rítmico de un compás dentro de una voz o flujo independiente.

Este módulo organiza eventos previamente identificados y delega el cálculo
exacto del residuo a duration_completion. No detecta ni asigna voces desde imágenes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from collections.abc import Iterable

from .duration_completion import DurationCompletion, infer_single_unknown_duration


@dataclass(frozen=True)
class RhythmicEvent:
    event_id: str
    voice_id: str
    measure_index: int
    duration_quarters: Fraction | int | float | None
    event_type: str = "note"


@dataclass(frozen=True)
class VoiceMeasureAnalysis:
    voice_id: str
    measure_index: int
    event_count: int
    known_event_count: int
    unknown_event_ids: tuple[str, ...]
    completion: DurationCompletion

    def to_dict(self) -> dict:
        data = asdict(self)
        data["unknown_event_ids"] = list(self.unknown_event_ids)
        data["completion"] = self.completion.to_dict()
        return data


def analyze_voice_measure(
    events: Iterable[RhythmicEvent],
    numerator: int,
    denominator: int,
    *,
    voice_id: str,
    measure_index: int,
) -> VoiceMeasureAnalysis:
    """Analiza exclusivamente eventos de una voz y un compás.

    Los silencios se incluyen como eventos normales. Un evento sin duración
    cuenta como desconocido. Las notas ligadas deben llegar ya consolidadas
    como una duración total, para no confundir prolongación con nuevo ataque.
    """
    if not isinstance(voice_id, str) or not voice_id.strip():
        raise ValueError("voice_id debe ser un identificador no vacío")
    if not isinstance(measure_index, int) or isinstance(measure_index, bool) or measure_index < 0:
        raise ValueError("measure_index debe ser un entero no negativo")

    selected = list(events)
    seen_ids: set[str] = set()
    known: list[Fraction | int | float] = []
    unknown_ids: list[str] = []

    for event in selected:
        if not isinstance(event, RhythmicEvent):
            raise ValueError("Todos los elementos deben ser RhythmicEvent")
        if event.voice_id != voice_id or event.measure_index != measure_index:
            raise ValueError("No se pueden mezclar voces ni compases en un mismo balance")
        if not isinstance(event.event_id, str) or not event.event_id.strip():
            raise ValueError("Cada evento debe tener event_id no vacío")
        if event.event_id in seen_ids:
            raise ValueError("Los identificadores de evento deben ser únicos")
        seen_ids.add(event.event_id)
        if event.event_type not in {"note", "rest"}:
            raise ValueError("event_type debe ser 'note' o 'rest'")
        if event.duration_quarters is None:
            unknown_ids.append(event.event_id)
        else:
            known.append(event.duration_quarters)

    completion = infer_single_unknown_duration(
        known,
        numerator,
        denominator,
        unknown_event_count=len(unknown_ids),
    )
    return VoiceMeasureAnalysis(
        voice_id=voice_id,
        measure_index=measure_index,
        event_count=len(selected),
        known_event_count=len(known),
        unknown_event_ids=tuple(unknown_ids),
        completion=completion,
    )
