"""Conversión de posiciones diatónicas a alturas según clave y alteraciones.

Este módulo no reconoce visualmente la clave: recibe una clave ya identificada
por una etapa futura o por corrección humana.
"""

from __future__ import annotations

from dataclasses import dataclass


_LETTERS = ("C", "D", "E", "F", "G", "A", "B")
_NATURAL_SEMITONES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Nota natural de la línea inferior de cada clave, en notación científica.
_BOTTOM_LINE = {
    "treble": ("E", 4),
    "bass": ("G", 2),
    "alto": ("F", 3),
    "tenor": ("D", 3),
}

_ACCIDENTALS = {
    None: 0,
    "natural": 0,
    "sharp": 1,
    "flat": -1,
    "double_sharp": 2,
    "double_flat": -2,
}


@dataclass(frozen=True)
class Pitch:
    step: str
    octave: int
    alteration: int
    midi: int


class MeasureAccidentals:
    """Mantiene alteraciones explícitas durante un compás.

    La clave del estado es (letra, octava), de modo que una alteración
    accidental afecta a la misma altura escrita durante ese compás.
    """

    def __init__(self) -> None:
        self._state: dict[tuple[str, int], int] = {}

    def reset(self) -> None:
        self._state.clear()

    def resolve(
        self,
        letter: str,
        octave: int,
        key_signature: dict[str, int] | None = None,
        explicit_accidental: str | None = None,
    ) -> int:
        key = (letter, octave)
        if explicit_accidental is not None:
            if explicit_accidental not in _ACCIDENTALS:
                raise ValueError(f"Alteración no reconocida: {explicit_accidental}")
            alteration = _ACCIDENTALS[explicit_accidental]
            self._state[key] = alteration
            return alteration

        if key in self._state:
            return self._state[key]
        return int((key_signature or {}).get(letter, 0))


def pitch_from_staff_step(
    diatonic_step_from_bottom: int,
    clef: str,
    key_signature: dict[str, int] | None = None,
    explicit_accidental: str | None = None,
    accidental_state: MeasureAccidentals | None = None,
) -> Pitch:
    """Convierte una posición (0 = línea inferior) a una altura MIDI.

    key_signature usa alteraciones por letra, por ejemplo {"F": 1, "B": -1}.
    explicit_accidental acepta natural, sharp, flat, double_sharp o double_flat.
    """
    if clef not in _BOTTOM_LINE:
        raise ValueError(f"Clave no soportada: {clef}")

    base_letter, base_octave = _BOTTOM_LINE[clef]
    base_index = _LETTERS.index(base_letter)
    absolute_index = base_index + int(diatonic_step_from_bottom)
    octave = base_octave + (absolute_index // 7)
    letter = _LETTERS[absolute_index % 7]

    if accidental_state is not None:
        alteration = accidental_state.resolve(
            letter, octave, key_signature, explicit_accidental
        )
    elif explicit_accidental is not None:
        if explicit_accidental not in _ACCIDENTALS:
            raise ValueError(f"Alteración no reconocida: {explicit_accidental}")
        alteration = _ACCIDENTALS[explicit_accidental]
    else:
        alteration = int((key_signature or {}).get(letter, 0))

    midi = 12 * (octave + 1) + _NATURAL_SEMITONES[letter] + alteration
    return Pitch(step=letter, octave=octave, alteration=alteration, midi=midi)
