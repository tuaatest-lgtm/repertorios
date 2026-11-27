"""Puente explícito entre posiciones de cabezas y alturas musicales.

La clave y la armadura son entradas externas revisadas; este módulo no afirma
reconocerlas visualmente. Sin clave suministrada, conserva el candidato como
pendiente y nunca inventa una altura MIDI.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from .pitch import MeasureAccidentals, Pitch, pitch_from_staff_step


@dataclass(frozen=True)
class PitchCandidate:
    source_kind: str
    source_index: int
    staff_index: int
    diatonic_step_from_bottom: int
    clef: str | None
    key_signature: dict[str, int]
    status: str
    pitch: Pitch | None
    explicit_accidental: str | None = None
    measure_id: str | int | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.pitch is not None:
            result["pitch"] = asdict(self.pitch)
        return result


def _normalize_staff_map(
    values: Mapping[int | str, Any] | None, name: str
) -> dict[int, Any]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise ValueError(f"{name} debe ser un objeto JSON indexado por pentagrama")
    normalized: dict[int, Any] = {}
    for raw_index, value in values.items():
        try:
            index = int(raw_index)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Índice de pentagrama no válido en {name}: {raw_index!r}") from exc
        if isinstance(raw_index, bool) or index < 0 or str(index) != str(raw_index):
            raise ValueError(f"Índice de pentagrama no válido en {name}: {raw_index!r}")
        if index in normalized:
            raise ValueError(f"Índice de pentagrama duplicado en {name}: {index}")
        normalized[index] = value
    return normalized


def build_pitch_candidates(
    noteheads: Sequence[Any],
    staff_clefs: Mapping[int | str, str] | None = None,
    key_signatures: Mapping[int | str, Mapping[str, int]] | None = None,
    source_kinds: Sequence[str] | None = None,
    explicit_accidentals: Sequence[str | None] | None = None,
    measure_ids: Sequence[str | int] | None = None,
) -> list[PitchCandidate]:
    """Construye alturas solo cuando la clave ha sido suministrada explícitamente."""
    clefs = _normalize_staff_map(staff_clefs, "staff_clefs")
    signatures = _normalize_staff_map(key_signatures, "key_signatures")
    if source_kinds is not None and len(source_kinds) != len(noteheads):
        raise ValueError("source_kinds debe tener un elemento por cada cabeza de nota")
    if (explicit_accidentals is None) != (measure_ids is None):
        raise ValueError("explicit_accidentals y measure_ids deben proporcionarse juntos")
    if explicit_accidentals is not None and len(explicit_accidentals) != len(noteheads):
        raise ValueError("explicit_accidentals debe tener un elemento por cada cabeza de nota")
    if measure_ids is not None and len(measure_ids) != len(noteheads):
        raise ValueError("measure_ids debe tener un elemento por cada cabeza de nota")

    # Estado independiente por pentagrama y compás. El llamador debe entregar
    # las cabezas en orden de lectura musical dentro de cada compás. Cuando las
    # coordenadas están disponibles, rechazamos un orden horizontal imposible:
    # de otro modo una alteración podría propagarse a una nota anterior.
    if measure_ids is not None:
        last_x: dict[tuple[int, str | int], float] = {}
        for index, (notehead, measure_id) in enumerate(zip(noteheads, measure_ids)):
            if measure_id is not None and (
                not isinstance(measure_id, (str, int))
                or isinstance(measure_id, bool)
                or (isinstance(measure_id, str) and not measure_id.strip())
            ):
                raise ValueError(f"measure_id no válido para la cabeza {index}")
            if measure_id is None or not hasattr(notehead, "center_x"):
                continue
            staff_index = int(notehead.staff_index)
            x = float(notehead.center_x)
            key = (staff_index, measure_id)
            if key in last_x and x < last_x[key]:
                raise ValueError(
                    "Las cabezas deben estar ordenadas de izquierda a derecha "
                    "dentro de cada pentagrama y compás"
                )
            last_x[key] = x
    accidental_states: dict[tuple[int, str | int], MeasureAccidentals] = {}
    results: list[PitchCandidate] = []
    for index, notehead in enumerate(noteheads):
        staff_index = int(notehead.staff_index)
        step = int(notehead.diatonic_step_from_bottom)
        clef = clefs.get(staff_index)
        signature = signatures.get(staff_index, {})
        if not isinstance(signature, Mapping):
            raise ValueError(f"La armadura del pentagrama {staff_index} debe ser un objeto")
        source_kind = source_kinds[index] if source_kinds is not None else "filled"
        explicit_accidental = explicit_accidentals[index] if explicit_accidentals is not None else None
        measure_id = measure_ids[index] if measure_ids is not None else None
        if source_kind not in {"filled", "hollow"}:
            raise ValueError(f"Tipo de cabeza de nota no válido: {source_kind!r}")

        if clef is None:
            pitch = None
            status = "unresolved_clef"
        else:
            accidental_state = None
            if measure_id is not None:
                state_key = (staff_index, measure_id)
                accidental_state = accidental_states.setdefault(state_key, MeasureAccidentals())
            pitch = pitch_from_staff_step(
                step, clef, dict(signature),
                explicit_accidental=explicit_accidental,
                accidental_state=accidental_state,
            )
            status = "resolved_from_supplied_clef"

        results.append(PitchCandidate(
            source_kind=source_kind,
            source_index=index,
            staff_index=staff_index,
            diatonic_step_from_bottom=step,
            clef=clef,
            key_signature=dict(signature),
            status=status,
            pitch=pitch,
            explicit_accidental=explicit_accidental,
            measure_id=measure_id,
        ))
    return results
