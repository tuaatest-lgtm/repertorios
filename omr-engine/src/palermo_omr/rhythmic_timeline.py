"""Línea temporal exacta de eventos ya reconocidos en un compás.

Conserva inicios y duraciones independientes, y agrupa ataques simultáneos
sin asumir que las voces distintas deban tener la misma duración.
No deduce posiciones temporales a partir de coordenadas gráficas.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from collections.abc import Iterable


@dataclass(frozen=True)
class TimedRhythmicEvent:
    event_id: str
    voice_id: str
    measure_index: int
    onset_quarters: Fraction | int | float | None
    duration_quarters: Fraction | int | float | None
    event_type: str = "note"


@dataclass(frozen=True)
class OnsetGroup:
    onset_quarters: Fraction
    event_ids: tuple[str, ...]


@dataclass(frozen=True)
class MeasureTimelineAnalysis:
    measure_index: int
    voice_ids: tuple[str, ...]
    expected_quarters: Fraction
    events: tuple[TimedRhythmicEvent, ...]
    onset_groups: tuple[OnsetGroup, ...]
    unknown_onset_event_ids: tuple[str, ...]
    unknown_duration_event_ids: tuple[str, ...]
    out_of_measure_event_ids: tuple[str, ...]
    maximum_known_end_quarters: Fraction
    status: str

    def to_dict(self) -> dict:
        return {
            "measure_index": self.measure_index,
            "voice_ids": list(self.voice_ids),
            "expected_quarters": str(self.expected_quarters),
            "events": [
                {
                    **asdict(event),
                    "onset_quarters": (
                        str(_fraction(event.onset_quarters))
                        if event.onset_quarters is not None else None
                    ),
                    "duration_quarters": (
                        str(_fraction(event.duration_quarters))
                        if event.duration_quarters is not None else None
                    ),
                }
                for event in self.events
            ],
            "onset_groups": [
                {
                    "onset_quarters": str(group.onset_quarters),
                    "event_ids": list(group.event_ids),
                }
                for group in self.onset_groups
            ],
            "unknown_onset_event_ids": list(self.unknown_onset_event_ids),
            "unknown_duration_event_ids": list(self.unknown_duration_event_ids),
            "out_of_measure_event_ids": list(self.out_of_measure_event_ids),
            "maximum_known_end_quarters": str(self.maximum_known_end_quarters),
            "status": self.status,
        }


def _fraction(value: Fraction | int | float) -> Fraction:
    if isinstance(value, bool):
        raise ValueError("Los tiempos musicales no pueden ser booleanos")
    try:
        result = value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise ValueError("El tiempo musical debe ser un número válido") from exc
    return result


def analyze_measure_timeline(
    events: Iterable[TimedRhythmicEvent],
    numerator: int,
    denominator: int,
    *,
    measure_index: int,
) -> MeasureTimelineAnalysis:
    """Organiza eventos de varias voces por inicio exacto dentro de un compás.

    Los eventos de voces distintas pueden solaparse y conservar duraciones
    independientes. Los eventos sin inicio o duración conocidos permanecen
    explícitamente pendientes; nunca se les asigna un tiempo por proximidad.
    """
    if not isinstance(numerator, int) or isinstance(numerator, bool) or numerator <= 0:
        raise ValueError("numerator debe ser un entero positivo")
    if not isinstance(denominator, int) or isinstance(denominator, bool) or denominator <= 0:
        raise ValueError("denominator debe ser un entero positivo")
    if not isinstance(measure_index, int) or isinstance(measure_index, bool) or measure_index < 0:
        raise ValueError("measure_index debe ser un entero no negativo")

    expected = Fraction(numerator * 4, denominator)
    selected = list(events)
    seen_ids: set[str] = set()
    voices: set[str] = set()
    unknown_onsets: list[str] = []
    unknown_durations: list[str] = []
    overflow: list[str] = []
    grouped: dict[Fraction, list[str]] = {}
    maximum_end = Fraction(0, 1)

    for event in selected:
        if not isinstance(event, TimedRhythmicEvent):
            raise ValueError("Todos los elementos deben ser TimedRhythmicEvent")
        if not isinstance(event.event_id, str) or not event.event_id.strip():
            raise ValueError("Cada evento debe tener event_id no vacío")
        if event.event_id in seen_ids:
            raise ValueError("Los identificadores de evento deben ser únicos")
        seen_ids.add(event.event_id)
        if not isinstance(event.voice_id, str) or not event.voice_id.strip():
            raise ValueError("Cada evento debe tener voice_id no vacío")
        if (
            not isinstance(event.measure_index, int)
            or isinstance(event.measure_index, bool)
            or event.measure_index < 0
        ):
            raise ValueError("El measure_index de cada evento debe ser un entero no negativo")
        if event.measure_index != measure_index:
            raise ValueError("No se pueden mezclar eventos de distintos compases")
        if event.event_type not in {"note", "rest"}:
            raise ValueError("event_type debe ser 'note' o 'rest'")
        voices.add(event.voice_id)

        onset = None if event.onset_quarters is None else _fraction(event.onset_quarters)
        duration = None if event.duration_quarters is None else _fraction(event.duration_quarters)
        if onset is not None and onset < 0:
            raise ValueError("onset_quarters no puede ser negativo")
        if duration is not None and duration <= 0:
            raise ValueError("duration_quarters debe ser mayor que cero")

        if onset is None:
            unknown_onsets.append(event.event_id)
        else:
            grouped.setdefault(onset, []).append(event.event_id)
            if onset >= expected:
                overflow.append(event.event_id)

        if duration is None:
            unknown_durations.append(event.event_id)
        elif onset is not None:
            end = onset + duration
            maximum_end = max(maximum_end, end)
            if end > expected and event.event_id not in overflow:
                overflow.append(event.event_id)

    onset_groups = tuple(
        OnsetGroup(onset, tuple(sorted(event_ids)))
        for onset, event_ids in sorted(grouped.items())
    )
    ordered_events = tuple(sorted(
        selected,
        key=lambda event: (
            _fraction(event.onset_quarters) if event.onset_quarters is not None else expected,
            event.voice_id,
            event.event_id,
        ),
    ))
    status = (
        "overfull" if overflow
        else "incomplete_data" if unknown_onsets or unknown_durations
        else "placed_events_only"
    )
    return MeasureTimelineAnalysis(
        measure_index=measure_index,
        voice_ids=tuple(sorted(voices)),
        expected_quarters=expected,
        events=ordered_events,
        onset_groups=onset_groups,
        unknown_onset_event_ids=tuple(unknown_onsets),
        unknown_duration_event_ids=tuple(unknown_durations),
        out_of_measure_event_ids=tuple(overflow),
        maximum_known_end_quarters=maximum_end,
        status=status,
    )
