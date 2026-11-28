"""Proyección temporal de eventos musicales hacia una agenda de reproducción.

No genera audio ni inventa notas: convierte únicamente eventos con inicio,
duración y altura MIDI explícitos en instantes relativos al tempo indicado.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence


def _fraction(value: Any, field: str) -> Fraction:
    if value is None:
        raise ValueError(f"{field} no puede ser desconocido")
    try:
        result = value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError(f"{field} debe ser una fracción numérica válida") from exc
    return result


def _midi_pitches(candidate: Mapping[str, Any]) -> list[int]:
    pitches: list[int] = []
    for item in candidate.get("pitch_candidates", []):
        pitch = item.get("pitch") if isinstance(item, Mapping) else None
        midi = pitch.get("midi") if isinstance(pitch, Mapping) else (
            item.get("midi") if isinstance(item, Mapping) else None
        )
        if not isinstance(midi, int) or isinstance(midi, bool) or not 0 <= midi <= 127:
            return []
        pitches.append(midi)
    return pitches


def build_playback_projection(
    timelines: Sequence[Mapping[str, Any]],
    event_candidates: Sequence[Any],
    *,
    tempo_bpm: int | float,
) -> dict[str, Any]:
    """Convierte una línea temporal provisional en eventos relativos al tempo.

    Los compases se concatenan en orden por su índice, usando su duración
    métrica esperada. Los eventos incompletos se devuelven en unresolved y
    nunca se convierten en notas reproducibles.
    """
    if isinstance(tempo_bpm, bool) or not isinstance(tempo_bpm, (int, float)) or tempo_bpm <= 0:
        raise ValueError("tempo_bpm debe ser un número positivo")
    seconds_per_quarter = 60.0 / float(tempo_bpm)

    candidates: dict[str, dict[str, Any]] = {}
    for event in event_candidates:
        payload = event.to_dict() if hasattr(event, "to_dict") else event
        if not isinstance(payload, Mapping):
            raise ValueError("Cada candidato debe ser un objeto o implementar to_dict()")
        event_id = payload.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in candidates:
            raise ValueError("Los event_id deben ser únicos y no vacíos")
        candidates[event_id] = dict(payload)

    normalized: dict[int, Mapping[str, Any]] = {}
    for timeline in timelines:
        if not isinstance(timeline, Mapping):
            raise ValueError("Cada línea temporal debe ser un objeto")
        measure_index = timeline.get("measure_index")
        if not isinstance(measure_index, int) or isinstance(measure_index, bool) or measure_index < 0:
            continue
        if measure_index in normalized:
            raise ValueError("No se puede repetir un índice de compás")
        normalized[measure_index] = timeline

    measure_offsets: dict[int, Fraction] = {}
    cursor = Fraction(0)
    for measure_index, timeline in sorted(normalized.items()):
        measure_offsets[measure_index] = cursor
        expected = _fraction(timeline.get("expected_quarters"), "expected_quarters")
        if expected <= 0:
            raise ValueError("La duración esperada del compás debe ser positiva")
        cursor += expected

    scheduled: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    seen_timed_ids: set[str] = set()

    for measure_index, timeline in sorted(normalized.items()):
        for event in timeline.get("events", []):
            event_id = event.get("event_id")
            if not isinstance(event_id, str) or event_id not in candidates:
                unresolved.append({"event_id": str(event_id), "reason": "missing_event_candidate"})
                continue
            if event_id in seen_timed_ids:
                raise ValueError(f"El evento {event_id} aparece más de una vez en la línea temporal")
            seen_timed_ids.add(event_id)
            onset_raw = event.get("onset_quarters")
            duration_raw = event.get("duration_quarters")
            if onset_raw is None or duration_raw is None:
                unresolved.append({"event_id": event_id, "reason": "unknown_onset_or_duration"})
                continue
            onset = _fraction(onset_raw, "onset_quarters")
            duration = _fraction(duration_raw, "duration_quarters")
            if onset < 0 or duration <= 0:
                raise ValueError(f"{event_id}: inicio no negativo y duración positiva requeridos")
            candidate = candidates[event_id]
            event_type = event.get("event_type", "note")
            midi_notes = [] if event_type == "rest" else _midi_pitches(candidate)
            if event_type != "rest" and (
                candidate.get("status") != "ready_for_review" or not midi_notes
            ):
                unresolved.append({"event_id": event_id, "reason": "pitch_or_candidate_unresolved"})
                continue

            absolute_onset = measure_offsets[measure_index] + onset
            absolute_end = absolute_onset + duration
            scheduled.append({
                "event_id": event_id,
                "voice_id": event.get("voice_id"),
                "event_type": event_type,
                "midi_notes": midi_notes,
                "onset_quarters": str(absolute_onset),
                "duration_quarters": str(duration),
                "start_seconds": float(absolute_onset) * seconds_per_quarter,
                "duration_seconds": float(duration) * seconds_per_quarter,
                "end_seconds": float(absolute_end) * seconds_per_quarter,
                "status": "playback_candidate",
            })

    scheduled.sort(key=lambda item: (item["start_seconds"], item["voice_id"] or "", item["event_id"]))
    return {
        "status": "unconfirmed_playback_projection",
        "tempo_bpm": float(tempo_bpm),
        "seconds_per_quarter": seconds_per_quarter,
        "events": scheduled,
        "unresolved_candidates": sorted(unresolved, key=lambda item: item["event_id"]),
        "warning": (
            "Agenda de reproducción provisional; no genera sonido ni confirma "
            "el reconocimiento musical. Los eventos no resueltos se excluyen."
        ),
    }


def merge_page_timelines_by_global_measure_map(
    page_timelines: Sequence[Mapping[str, Any]],
    page_measure_global_indices: Mapping[int, Mapping[int, int]],
) -> dict[str, Any]:
    """Concatena medidas de varias páginas solo con un mapa global explícito.

    Los índices locales son cero-based. Si falta un mapeo o hay un salto en la
    secuencia global, se conserva únicamente el prefijo contiguo; las medidas
    posteriores no se compactan ni reciben tiempos inventados.
    """
    if not isinstance(page_measure_global_indices, Mapping):
        raise ValueError("page_measure_global_indices debe ser un mapa")
    normalized_map: dict[int, dict[int, int]] = {}
    used_global: set[int] = set()
    for page_number, local_map in page_measure_global_indices.items():
        if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
            raise ValueError("Los números de página deben ser enteros positivos")
        if not isinstance(local_map, Mapping):
            raise ValueError("Cada mapa de página debe ser un objeto")
        normalized_map[page_number] = {}
        for local_index, global_index in local_map.items():
            if (not isinstance(local_index, int) or isinstance(local_index, bool) or local_index < 0
                    or not isinstance(global_index, int) or isinstance(global_index, bool) or global_index < 0):
                raise ValueError("Los índices locales/globales deben ser enteros no negativos")
            if global_index in used_global:
                raise ValueError("No se puede asignar dos medidas al mismo índice global")
            used_global.add(global_index)
            normalized_map[page_number][local_index] = global_index

    ordered = []
    for timeline in page_timelines:
        if not isinstance(timeline, Mapping):
            raise ValueError("Cada línea temporal de página debe ser un objeto")
        page_number = timeline.get("page_number")
        local_index = timeline.get("measure_index")
        if (not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1
                or not isinstance(local_index, int) or isinstance(local_index, bool) or local_index < 0):
            raise ValueError("Cada timeline requiere page_number y measure_index locales válidos")
        global_index = normalized_map.get(page_number, {}).get(local_index)
        ordered.append((page_number, local_index, global_index, dict(timeline)))

    ordered.sort(key=lambda item: (item[0], item[1]))
    mapped_values = [item[2] for item in ordered if item[2] is not None]
    if mapped_values != sorted(mapped_values):
        raise ValueError("El mapa global debe respetar el orden de páginas y medidas")
    accepted = []
    unresolved = []
    expected_global = 0
    gap_started = False
    missing_global: list[int] = []
    for page_number, local_index, global_index, timeline in ordered:
        if gap_started:
            unresolved.append({
                "page_number": page_number, "local_measure_index": local_index,
                "global_measure_index": global_index,
                "reason": "after_unresolved_measure_gap",
            })
            continue
        if global_index is None:
            gap_started = True
            unresolved.append({
                "page_number": page_number, "local_measure_index": local_index,
                "global_measure_index": None, "reason": "missing_global_measure_mapping",
            })
            continue
        if global_index != expected_global:
            gap_started = True
            missing_global.extend(range(expected_global, global_index))
            unresolved.append({
                "page_number": page_number, "local_measure_index": local_index,
                "global_measure_index": global_index, "reason": "global_measure_index_gap",
            })
            continue
        timeline["measure_index"] = global_index
        timeline["page_number"] = page_number
        timeline["local_measure_index"] = local_index
        accepted.append(timeline)
        expected_global += 1

    return {
        "status": "unconfirmed_document_timeline",
        "timelines": accepted,
        "unresolved_measures": unresolved,
        "missing_global_measure_indices": missing_global,
        "warning": (
            "Las medidas se concatenan solo cuando existe un mapeo global "
            "explícito y contiguo; no se comprimen huecos ni se inventan compases."
        ),
    }
