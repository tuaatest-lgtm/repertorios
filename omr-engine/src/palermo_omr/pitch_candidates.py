"""Puente explícito entre posiciones de cabezas y alturas musicales.

La clave, armadura, alteraciones detectadas y grupos de simultaneidad son
entradas externas revisadas; este módulo no afirma reconocerlas visualmente.
Sin clave suministrada, conserva el candidato como pendiente y nunca inventa
una altura MIDI.
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
    simultaneous_group_id: str | int | None = None

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


def _validate_group_ids(
    noteheads: Sequence[Any],
    measure_ids: Sequence[str | int] | None,
    simultaneous_group_ids: Sequence[str | int] | None,
) -> list[str | int | None]:
    if simultaneous_group_ids is None:
        return [None] * len(noteheads)
    if measure_ids is None:
        raise ValueError("simultaneous_group_ids requiere measure_ids")
    if len(simultaneous_group_ids) != len(noteheads):
        raise ValueError("simultaneous_group_ids debe tener un elemento por cabeza")
    closed: set[tuple[int, str | int, str | int]] = set()
    previous: tuple[int, str | int, str | int] | None = None
    for index, (head, measure_id, group_id) in enumerate(
        zip(noteheads, measure_ids, simultaneous_group_ids)
    ):
        if not isinstance(group_id, (str, int)) or isinstance(group_id, bool):
            raise ValueError(f"simultaneous_group_id no válido para la cabeza {index}")
        if isinstance(group_id, str) and not group_id.strip():
            raise ValueError(f"simultaneous_group_id vacío para la cabeza {index}")
        if measure_id is None:
            raise ValueError("Un grupo simultáneo necesita un measure_id confirmado")
        key = (int(head.staff_index), measure_id, group_id)
        if key != previous:
            if key in closed:
                raise ValueError("Los miembros de un grupo simultáneo deben ser contiguos")
            if previous is not None:
                closed.add(previous)
            previous = key
    return list(simultaneous_group_ids)


def build_pitch_candidates(
    noteheads: Sequence[Any],
    staff_clefs: Mapping[int | str, str] | None = None,
    key_signatures: Mapping[int | str, Mapping[str, int]] | None = None,
    source_kinds: Sequence[str] | None = None,
    explicit_accidentals: Sequence[str | None] | None = None,
    measure_ids: Sequence[str | int] | None = None,
    simultaneous_group_ids: Sequence[str | int] | None = None,
    source_indices: Sequence[int] | None = None,
) -> list[PitchCandidate]:
    """Construye alturas con claves suministradas y alteraciones revisadas.

    Con simultaneous_group_ids, todos los miembros de un ataque/acorde
    revisado se procesan como un bloque: primero se registran sus alteraciones
    explícitas y luego se resuelven las demás cabezas. Así, una alteración
    también afecta a notas simultáneas de la misma letra y octava, sin depender
    del orden de las cabezas dentro del acorde.
    """
    clefs = _normalize_staff_map(staff_clefs, "staff_clefs")
    signatures = _normalize_staff_map(key_signatures, "key_signatures")
    count = len(noteheads)
    if source_kinds is not None and len(source_kinds) != count:
        raise ValueError("source_kinds debe tener un elemento por cada cabeza de nota")
    if source_indices is not None and (
        len(source_indices) != count
        or any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in source_indices)
        or len(set(source_indices)) != count
    ):
        raise ValueError("source_indices debe contener índices enteros únicos y no negativos")
    if (explicit_accidentals is None) != (measure_ids is None):
        raise ValueError("explicit_accidentals y measure_ids deben proporcionarse juntos")
    if explicit_accidentals is not None and len(explicit_accidentals) != count:
        raise ValueError("explicit_accidentals debe tener un elemento por cada cabeza de nota")
    if explicit_accidentals is not None:
        allowed_accidentals = {
            "natural", "sharp", "flat", "double_sharp", "double_flat"
        }
        for index, accidental in enumerate(explicit_accidentals):
            if accidental is not None and (
                not isinstance(accidental, str) or accidental not in allowed_accidentals
            ):
                raise ValueError(
                    f"Alteración no reconocida para la cabeza {index}: {accidental!r}"
                )
    if source_kinds is not None:
        for index, source_kind in enumerate(source_kinds):
            if source_kind not in ("filled", "hollow"):
                raise ValueError(f"Tipo de cabeza de nota no válido: {source_kind!r}")
    for staff_index, clef in clefs.items():
        if not isinstance(clef, str) or clef not in {"treble", "bass", "alto", "tenor"}:
            raise ValueError(f"Clave no soportada en pentagrama {staff_index}: {clef!r}")
    if measure_ids is not None and len(measure_ids) != count:
        raise ValueError("measure_ids debe tener un elemento por cada cabeza de nota")

    if measure_ids is not None:
        for index, measure_id in enumerate(measure_ids):
            if measure_id is not None and (
                not isinstance(measure_id, (str, int))
                or isinstance(measure_id, bool)
                or (isinstance(measure_id, str) and not measure_id.strip())
            ):
                raise ValueError(f"measure_id no válido para la cabeza {index}")
    group_ids = _validate_group_ids(noteheads, measure_ids, simultaneous_group_ids)

    # El orden de lectura debe ser monótono dentro de cada pentagrama/compás.
    if measure_ids is not None:
        last_x: dict[tuple[int, str | int], float] = {}
        for index, (notehead, measure_id) in enumerate(zip(noteheads, measure_ids)):
            if measure_id is None or not hasattr(notehead, "center_x"):
                continue
            key = (int(notehead.staff_index), measure_id)
            x = float(notehead.center_x)
            if key in last_x and x < last_x[key]:
                raise ValueError(
                    "Las cabezas deben estar ordenadas de izquierda a derecha "
                    "dentro de cada pentagrama y compás"
                )
            last_x[key] = x

    states: dict[tuple[int, str | int], MeasureAccidentals] = {}
    results: list[PitchCandidate | None] = [None] * count
    start = 0
    while start < count:
        staff_index = int(noteheads[start].staff_index)
        measure_id = measure_ids[start] if measure_ids is not None else None
        group_id = group_ids[start]
        end = start + 1
        if simultaneous_group_ids is not None:
            while end < count and (
                int(noteheads[end].staff_index), measure_ids[end], group_ids[end]
            ) == (staff_index, measure_id, group_id):
                end += 1

        clef = clefs.get(staff_index)
        signature = signatures.get(staff_index, {})
        if not isinstance(signature, Mapping):
            raise ValueError(f"La armadura del pentagrama {staff_index} debe ser un objeto")
        state = (
            states.setdefault((staff_index, measure_id), MeasureAccidentals())
            if measure_id is not None else None
        )

        # Rechazar dos alteraciones incompatibles para una misma nota escrita
        # en el mismo ataque antes de cambiar el estado accidental del compás.
        explicit_by_pitch: dict[tuple[str, int], str] = {}
        if clef is not None and explicit_accidentals is not None:
            for index in range(start, end):
                accidental = explicit_accidentals[index]
                if accidental is None:
                    continue
                probe = pitch_from_staff_step(
                    int(noteheads[index].diatonic_step_from_bottom), clef,
                    dict(signature), explicit_accidental=accidental,
                )
                key = (probe.step, probe.octave)
                prior = explicit_by_pitch.get(key)
                if prior is not None and prior != accidental:
                    raise ValueError(
                        "Un mismo acorde contiene alteraciones explícitas incompatibles "
                        f"para {probe.step}{probe.octave}"
                    )
                explicit_by_pitch[key] = accidental

        # Primera pasada del acorde: registrar todas las alteraciones explícitas.
        group_pitches: dict[int, Pitch] = {}
        if clef is not None and state is not None and explicit_accidentals is not None:
            for index in range(start, end):
                accidental = explicit_accidentals[index]
                if accidental is not None:
                    group_pitches[index] = pitch_from_staff_step(
                        int(noteheads[index].diatonic_step_from_bottom), clef,
                        dict(signature), explicit_accidental=accidental,
                        accidental_state=state,
                    )

        for index in range(start, end):
            notehead = noteheads[index]
            step = int(notehead.diatonic_step_from_bottom)
            source_kind = source_kinds[index] if source_kinds is not None else "filled"
            if source_kind not in {"filled", "hollow"}:
                raise ValueError(f"Tipo de cabeza de nota no válido: {source_kind!r}")
            accidental = explicit_accidentals[index] if explicit_accidentals is not None else None
            if clef is None:
                pitch = None
                status = "unresolved_clef"
            else:
                pitch = group_pitches.get(index)
                if pitch is None:
                    pitch = pitch_from_staff_step(
                        step, clef, dict(signature),
                        explicit_accidental=accidental,
                        accidental_state=state,
                    )
                status = "resolved_from_supplied_clef"
            results[index] = PitchCandidate(
                source_kind=source_kind,
                source_index=source_indices[index] if source_indices is not None else index,
                staff_index=staff_index,
                diatonic_step_from_bottom=step,
                clef=clef,
                key_signature=dict(signature),
                status=status,
                pitch=pitch,
                explicit_accidental=accidental,
                measure_id=measure_id,
                simultaneous_group_id=group_id,
            )
        start = end

    return [item for item in results if item is not None]
