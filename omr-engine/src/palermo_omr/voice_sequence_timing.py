"""Reconstrucción conservadora de inicios por secuencia rítmica de voz.

El orden horizontal identifica el orden de lectura, pero la distancia en píxeles
nunca se convierte directamente en tiempo. Los inicios se calculan sumando
duraciones musicales conocidas dentro de cada flujo independiente.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from collections.abc import Iterable

from .rhythmic_timeline import TimedRhythmicEvent, _fraction


@dataclass(frozen=True)
class OrderedVoiceEvent:
    event_id: str
    voice_id: str
    measure_index: int
    order_index: int
    duration_quarters: Fraction | int | float | None
    event_type: str = "note"
    notehead_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class VoiceSequenceTiming:
    voice_id: str
    measure_index: int
    events: tuple[TimedRhythmicEvent, ...]
    unresolved_onset_event_ids: tuple[str, ...]
    status: str


def derive_voice_sequence_timing(
    events: Iterable[OrderedVoiceEvent],
    *,
    voice_id: str,
    measure_index: int,
) -> VoiceSequenceTiming:
    """Asigna inicios acumulando duraciones, sin usar distancias horizontales.

    La entrada debe representar ataques/eventos ya agrupados en orden de
    lectura para una sola voz y compás. Las cabezas de un acorde se agrupan en
    un mismo OrderedVoiceEvent mediante notehead_ids. Si una duración es
    desconocida, los inicios posteriores quedan desconocidos, no estimados.
    """
    if not isinstance(voice_id, str) or not voice_id.strip():
        raise ValueError("voice_id debe ser un texto no vacío")
    if not isinstance(measure_index, int) or isinstance(measure_index, bool) or measure_index < 0:
        raise ValueError("measure_index debe ser un entero no negativo")

    selected = list(events)
    seen_ids: set[str] = set()
    seen_order: set[int] = set()
    for event in selected:
        if not isinstance(event, OrderedVoiceEvent):
            raise ValueError("Todos los elementos deben ser OrderedVoiceEvent")
        if event.voice_id != voice_id or event.measure_index != measure_index:
            raise ValueError("La secuencia no puede mezclar voces ni compases")
        if not isinstance(event.event_id, str) or not event.event_id.strip():
            raise ValueError("event_id debe ser un texto no vacío")
        if event.event_id in seen_ids:
            raise ValueError("Los identificadores de evento deben ser únicos")
        seen_ids.add(event.event_id)
        if (
            not isinstance(event.order_index, int)
            or isinstance(event.order_index, bool)
            or event.order_index < 0
        ):
            raise ValueError("order_index debe ser un entero no negativo")
        if event.order_index in seen_order:
            raise ValueError("order_index debe ser único dentro de la secuencia")
        seen_order.add(event.order_index)
        if event.event_type not in {"note", "rest"}:
            raise ValueError("event_type debe ser 'note' o 'rest'")
        if len(set(event.notehead_ids)) != len(event.notehead_ids):
            raise ValueError("Un acorde no puede repetir notehead_ids")
        if event.duration_quarters is not None and _fraction(event.duration_quarters) <= 0:
            raise ValueError("duration_quarters debe ser mayor que cero")

    ordered = sorted(selected, key=lambda item: item.order_index)
    cursor: Fraction | None = Fraction(0, 1)
    timed: list[TimedRhythmicEvent] = []
    unresolved: list[str] = []

    for event in ordered:
        onset = cursor
        if onset is None:
            unresolved.append(event.event_id)
        timed.append(TimedRhythmicEvent(
            event_id=event.event_id,
            voice_id=voice_id,
            measure_index=measure_index,
            onset_quarters=onset,
            duration_quarters=event.duration_quarters,
            event_type=event.event_type,
        ))
        if cursor is not None:
            if event.duration_quarters is None:
                cursor = None
            else:
                cursor += _fraction(event.duration_quarters)

    status = "incomplete_sequence" if unresolved or any(
        event.duration_quarters is None for event in ordered
    ) else "sequence_timed"
    return VoiceSequenceTiming(
        voice_id=voice_id,
        measure_index=measure_index,
        events=tuple(timed),
        unresolved_onset_event_ids=tuple(unresolved),
        status=status,
    )


def derive_measure_voice_sequences(
    sequences: Iterable[tuple[str, int, Iterable[OrderedVoiceEvent]]],
) -> tuple[TimedRhythmicEvent, ...]:
    """Combina secuencias independientes sin sincronizarlas por píxeles."""
    combined: list[TimedRhythmicEvent] = []
    seen_voices: set[tuple[str, int]] = set()
    for voice_id, measure_index, events in sequences:
        key = (voice_id, measure_index)
        if key in seen_voices:
            raise ValueError("No se puede repetir una secuencia de voz y compás")
        seen_voices.add(key)
        result = derive_voice_sequence_timing(
            events, voice_id=voice_id, measure_index=measure_index
        )
        combined.extend(result.events)
    return tuple(combined)
