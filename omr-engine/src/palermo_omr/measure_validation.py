"""Validación métrica independiente para duraciones ya interpretadas.

Este módulo no detecta notas ni barras de compás en imágenes. Recibe duraciones
propuestas por una etapa anterior y comprueba si su suma es compatible con el
indicador de compás. Las duraciones se expresan en unidades de negra.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class MeasureRhythmValidation:
    numerator: int
    denominator: int
    expected_quarter_notes: float
    observed_quarter_notes: float
    difference_quarter_notes: float
    status: str
    is_pickup: bool
    tolerance: float

    def to_dict(self) -> dict:
        return asdict(self)


def validate_measure_duration(
    durations_quarter_notes: list[float],
    numerator: int,
    denominator: int,
    *,
    is_pickup: bool = False,
    tolerance: float = 0.02,
) -> MeasureRhythmValidation:
    """Compara la suma de duraciones con el valor métrico esperado.

    Ejemplos:
    - 4/4 espera 4 negras.
    - 3/4 espera 3 negras.
    - 6/8 espera 3 negras (seis corcheas).

    Una anacrusa puede ser menor que el compás completo, pero nunca excederlo.
    Esta función no determina por sí sola si una anacrusa es editorialmente válida.
    """
    if not isinstance(numerator, int) or isinstance(numerator, bool) or numerator <= 0:
        raise ValueError("El numerador debe ser un entero positivo")
    if not isinstance(denominator, int) or isinstance(denominator, bool) or denominator <= 0:
        raise ValueError("El denominador debe ser un entero positivo")
    if denominator & (denominator - 1):
        raise ValueError("El denominador debe ser una potencia de dos")
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("La tolerancia debe ser un número finito no negativo")

    observed = 0.0
    for duration in durations_quarter_notes:
        if not isinstance(duration, (int, float)) or isinstance(duration, bool):
            raise ValueError("Cada duración debe ser numérica")
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("Cada duración debe ser finita y mayor que cero")
        observed += float(duration)

    expected = numerator * 4.0 / denominator
    difference = observed - expected
    if abs(difference) <= tolerance:
        status = "complete"
    elif difference < 0 and is_pickup:
        status = "pickup_incomplete"
    elif difference < 0:
        status = "underfull"
    else:
        status = "overfull"

    return MeasureRhythmValidation(
        numerator=numerator,
        denominator=denominator,
        expected_quarter_notes=round(expected, 6),
        observed_quarter_notes=round(observed, 6),
        difference_quarter_notes=round(difference, 6),
        status=status,
        is_pickup=is_pickup,
        tolerance=tolerance,
    )
