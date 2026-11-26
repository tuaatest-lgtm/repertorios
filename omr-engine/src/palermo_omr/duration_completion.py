"""Infer one missing event duration from a measure's remaining metric value.

This module operates only on events already assigned to the same voice and
measure. It does not detect notes, rests, ties, tuplets, or voice boundaries.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from collections.abc import Iterable


@dataclass(frozen=True)
class DurationCompletion:
    expected_quarters: Fraction
    known_total_quarters: Fraction
    remaining_quarters: Fraction
    unknown_event_count: int
    status: str
    inferred_duration_quarters: Fraction | None

    def to_dict(self) -> dict:
        """Return a JSON-friendly representation with exact rational values."""
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, Fraction):
                data[key] = {"numerator": value.numerator, "denominator": value.denominator}
        return data


def _as_fraction(value: Fraction | int | float) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (Fraction, int, float)):
        raise ValueError("Las duraciones deben ser números")
    try:
        result = value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise ValueError("La duración debe ser un número válido") from exc
    if result < 0:
        raise ValueError("Las duraciones conocidas no pueden ser negativas")
    return result


def infer_single_unknown_duration(
    known_durations: Iterable[Fraction | int | float],
    numerator: int,
    denominator: int,
    *,
    unknown_event_count: int = 1,
) -> DurationCompletion:
    """Calculate the remainder and infer it only when exactly one event is unknown.

    All events must belong to the same voice/independent rhythmic stream and
    the same measure. Tied notes must already be combined, dots and tuplets
    already accounted for, and rests included as known events where applicable.
    If multiple events are unknown, the remainder is shared and cannot identify
    any one event's duration.
    """
    if not isinstance(numerator, int) or isinstance(numerator, bool) or numerator <= 0:
        raise ValueError("El numerador debe ser un entero positivo")
    if not isinstance(denominator, int) or isinstance(denominator, bool) or denominator <= 0:
        raise ValueError("El denominador debe ser un entero positivo")
    if denominator & (denominator - 1):
        raise ValueError("El denominador debe ser una potencia de dos")
    if (
        not isinstance(unknown_event_count, int)
        or isinstance(unknown_event_count, bool)
        or unknown_event_count < 0
    ):
        raise ValueError("unknown_event_count debe ser un entero no negativo")

    expected = Fraction(numerator * 4, denominator)
    known_total = sum((_as_fraction(item) for item in known_durations), Fraction(0))
    remaining = expected - known_total

    if remaining < 0:
        status = "overfull"
        inferred = None
    elif unknown_event_count == 0:
        status = "complete" if remaining == 0 else "unaccounted_remainder"
        inferred = None
    elif remaining == 0:
        status = "no_positive_remainder"
        inferred = None
    elif unknown_event_count == 1:
        status = "inferred_single_unknown"
        inferred = remaining
    else:
        status = "remainder_shared_by_multiple_unknowns"
        inferred = None

    return DurationCompletion(
        expected_quarters=expected,
        known_total_quarters=known_total,
        remaining_quarters=remaining,
        unknown_event_count=unknown_event_count,
        status=status,
        inferred_duration_quarters=inferred,
    )
