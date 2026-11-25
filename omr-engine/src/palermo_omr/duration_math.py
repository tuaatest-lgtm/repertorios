"""Aritmética exacta de duraciones escritas, puntillos y prolongaciones.

Este módulo opera sobre valores musicales ya identificados. No reconoce
símbolos en imágenes ni decide si un arco es una ligadura de prolongación.
Las unidades son negras (quarter notes) y se representan con Fraction.
"""
from __future__ import annotations

from fractions import Fraction
from collections.abc import Iterable


BASE_DURATIONS: dict[str, Fraction] = {
    "whole": Fraction(4, 1),
    "half": Fraction(2, 1),
    "quarter": Fraction(1, 1),
    "eighth": Fraction(1, 2),
    "sixteenth": Fraction(1, 4),
    "thirty_second": Fraction(1, 8),
    "sixty_fourth": Fraction(1, 16),
}


def duration_in_quarters(base_duration: str, dots: int = 0) -> Fraction:
    """Devuelve duración exacta en negras, aplicando uno o más puntillos.

    Un puntillo multiplica por 3/2; dos por 7/4; tres por 15/8.
    """
    if base_duration not in BASE_DURATIONS:
        raise ValueError(f"Figura base desconocida: {base_duration}")
    if not isinstance(dots, int) or isinstance(dots, bool) or dots < 0 or dots > 4:
        raise ValueError("dots debe ser un entero entre 0 y 4")
    multiplier = Fraction(2 ** (dots + 1) - 1, 2 ** dots)
    return BASE_DURATIONS[base_duration] * multiplier


def sum_tied_durations(durations: Iterable[Fraction | int | float]) -> Fraction:
    """Suma duraciones de notas enlazadas por una ligadura ya confirmada.

    La confirmación de los extremos y de la igualdad de altura corresponde
    a una etapa posterior de reconocimiento; esta función solo hace la suma.
    """
    values = []
    for value in durations:
        try:
            exact = value if isinstance(value, Fraction) else Fraction(str(value))
        except (ValueError, ZeroDivisionError, TypeError) as exc:
            raise ValueError("Todas las duraciones deben ser números válidos") from exc
        if exact <= 0:
            raise ValueError("Las duraciones deben ser mayores que cero")
        values.append(exact)
    if not values:
        raise ValueError("Se requiere al menos una duración")
    return sum(values, Fraction(0, 1))
