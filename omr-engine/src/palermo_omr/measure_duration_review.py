"""Candidatos de duración por resto métrico, sin modificar eventos revisados.

Solo sugiere una duración cuando una persona confirma que el compás está
completo y que ligaduras/grupos irregulares ya fueron resueltos. La sugerencia
nunca altera la línea temporal ni habilita reproducción automáticamente.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from fractions import Fraction

from .duration_completion import infer_single_unknown_duration
from .duration_math import BASE_DURATIONS, duration_in_quarters


@dataclass(frozen=True)
class MeasureDurationCompletionCandidate:
    voice_id: str
    event_id: str | None
    expected_quarters: Fraction
    known_total_quarters: Fraction
    remaining_quarters: Fraction
    status: str
    candidate_duration_quarters: Fraction | None
    candidate_base_duration: str | None
    candidate_dots: int | None
    warning: str

    def to_dict(self) -> dict:
        result = asdict(self)
        for key in (
            "expected_quarters", "known_total_quarters", "remaining_quarters",
            "candidate_duration_quarters",
        ):
            value = result[key]
            result[key] = str(value) if value is not None else None
        return result


def _as_positive_fraction(value, label: str) -> Fraction:
    if isinstance(value, bool):
        raise ValueError(f"{label} debe ser una duración positiva")
    try:
        result = value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        raise ValueError(f"{label} debe ser una duración válida") from exc
    if result <= 0:
        raise ValueError(f"{label} debe ser una duración positiva")
    return result


def _standard_notation(duration: Fraction) -> tuple[str | None, int | None]:
    matches = [
        (name, dots)
        for name in BASE_DURATIONS
        for dots in range(5)
        if duration_in_quarters(name, dots) == duration
    ]
    return matches[0] if matches else (None, None)


def build_measure_duration_completion_candidates(
    events: Sequence[Mapping],
    numerator: int,
    denominator: int,
    *,
    measure_complete_confirmed: bool,
    ties_and_tuplets_resolved: bool,
) -> tuple[MeasureDurationCompletionCandidate, ...]:
    """Sugiere la única duración faltante por voz usando el resto del compás.

    La persona revisora debe confirmar que el compás está completo (incluidos
    silencios) y que ligaduras/tupletos ya están resueltos. No se infiere si hay
    más de un evento desconocido, si el compás está sobrellenado o si el resto
    no corresponde a una figura estándar con hasta cuatro puntillos.
    """
    if not isinstance(numerator, int) or isinstance(numerator, bool) or numerator <= 0:
        raise ValueError("numerator debe ser un entero positivo")
    if not isinstance(denominator, int) or isinstance(denominator, bool) or denominator <= 0:
        raise ValueError("denominator debe ser un entero positivo")
    if denominator & (denominator - 1):
        raise ValueError("denominator debe ser una potencia de dos")
    if not isinstance(measure_complete_confirmed, bool) or not isinstance(ties_and_tuplets_resolved, bool):
        raise ValueError("Las confirmaciones de revisión deben ser booleanas")

    by_voice: dict[str, list[Mapping]] = {}
    seen_ids: set[str] = set()
    for event in events:
        if not isinstance(event, Mapping):
            raise ValueError("Cada evento debe ser un objeto")
        event_id = event.get("event_id")
        voice_id = event.get("voice_id")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in seen_ids:
            raise ValueError("Los event_id deben ser textos únicos y no vacíos")
        if not isinstance(voice_id, str) or not voice_id.strip():
            raise ValueError("Cada evento requiere una voz explícita")
        if event.get("event_type", "note") not in {"note", "rest"}:
            raise ValueError("event_type debe ser note o rest")
        seen_ids.add(event_id)
        by_voice.setdefault(voice_id, []).append(event)

    expected = Fraction(numerator * 4, denominator)
    results = []
    for voice_id, voice_events in sorted(by_voice.items()):
        unknown = [event for event in voice_events if event.get("duration_quarters") is None]
        known = [
            _as_positive_fraction(event["duration_quarters"], "duration_quarters")
            for event in voice_events if event.get("duration_quarters") is not None
        ]
        known_total = sum(known, Fraction(0))
        remaining = expected - known_total
        event_id = unknown[0]["event_id"] if len(unknown) == 1 else None
        status = "no_unknown_duration"
        candidate = base = dots = None

        if not measure_complete_confirmed or not ties_and_tuplets_resolved:
            status = "review_prerequisites_not_confirmed"
        elif not unknown:
            status = "no_unknown_duration"
        elif len(unknown) > 1:
            status = "multiple_unknown_durations"
        elif unknown[0].get("event_type", "note") != "note":
            status = "unknown_rest_not_inferred"
        else:
            completion = infer_single_unknown_duration(
                known, numerator, denominator, unknown_event_count=1
            )
            status = completion.status
            if completion.status == "inferred_single_unknown":
                base, dots = _standard_notation(completion.inferred_duration_quarters)
                if base is None:
                    status = "unsupported_metric_remainder"
                else:
                    candidate = completion.inferred_duration_quarters
                    status = "single_unknown_duration_candidate"

        results.append(MeasureDurationCompletionCandidate(
            voice_id=voice_id,
            event_id=event_id,
            expected_quarters=expected,
            known_total_quarters=known_total,
            remaining_quarters=remaining,
            status=status,
            candidate_duration_quarters=candidate,
            candidate_base_duration=base,
            candidate_dots=dots,
            warning=(
                "Candidato aritmético, no reconocimiento visual. La persona revisora "
                "debe confirmar la figura y volver a generar la línea temporal; "
                "el motor no modifica ni reproduce este evento automáticamente."
            ),
        ))
    return tuple(results)
