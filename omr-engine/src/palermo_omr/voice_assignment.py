"""Aplica asignaciones de voz revisadas a eventos polifónicos candidatos."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass, replace
from fractions import Fraction
from typing import Any


def _payload(event: Any) -> dict[str, Any]:
    if hasattr(event, "to_dict"):
        result = event.to_dict()
    elif isinstance(event, Mapping):
        result = dict(event)
    else:
        raise ValueError("Cada evento debe ser serializable")
    return result


def _normalize_staff_contexts(values: Mapping[Any, Any]) -> dict[int, Mapping[str, Any]]:
    if not isinstance(values, Mapping):
        raise ValueError("staff_voice_contexts debe ser un mapa")
    result: dict[int, Mapping[str, Any]] = {}
    for raw_index, context in values.items():
        if isinstance(raw_index, bool):
            raise ValueError("Índice de pentagrama no válido")
        try:
            index = int(raw_index)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Índice de pentagrama no válido: {raw_index!r}") from exc
        if index < 0 or str(index) != str(raw_index) or index in result:
            raise ValueError(f"Índice de pentagrama no válido o duplicado: {raw_index!r}")
        if not isinstance(context, Mapping):
            raise ValueError(f"Contexto de voz del pentagrama {index} debe ser un objeto")
        result[index] = context
    return result


def _confirmed_voice(context: Mapping[str, Any], label: str) -> tuple[str | None, str | None]:
    status = context.get("status", "pending_human_review")
    if status != "human_confirmed":
        return None, "voice_context_not_human_confirmed"
    voice_id = context.get("voice_id")
    if not isinstance(voice_id, str) or not voice_id.strip():
        return None, "missing_voice_id"
    return voice_id.strip(), None


def _musically_complete(payload: Mapping[str, Any]) -> bool:
    event_type = payload.get("event_type", "note")
    if event_type == "rest":
        pitches_resolved = True
    elif event_type == "note":
        pitches = payload.get("pitch_candidates")
        pitches_resolved = isinstance(pitches, (list, tuple)) and bool(pitches) and all(
            isinstance(item, Mapping)
            and item.get("status") == "resolved_from_supplied_clef"
            and isinstance(item.get("pitch"), Mapping)
            and isinstance(item["pitch"].get("midi"), int)
            for item in pitches
        )
    else:
        return False
    duration = payload.get("duration_quarters_candidate")
    try:
        duration_value = Fraction(str(duration))
    except (TypeError, ValueError, ZeroDivisionError):
        return False
    return (
        pitches_resolved
        and isinstance(payload.get("duration_candidate"), str)
        and bool(payload["duration_candidate"].strip())
        and duration_value > 0
    )


def apply_reviewed_voice_assignments(
    event_candidates: Sequence[Any],
    staff_voice_contexts: Mapping[int | str, Mapping[str, Any]],
    *,
    event_voice_overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aplica voz solo desde contexto de pentagrama o evento confirmado.

    Un override de evento pendiente bloquea deliberadamente el fallback al
    pentagrama: una división polifónica dentro del mismo pentagrama no debe
    heredarse a otra voz por proximidad.
    """
    contexts = _normalize_staff_contexts(staff_voice_contexts)
    overrides = event_voice_overrides or {}
    if not isinstance(overrides, Mapping):
        raise ValueError("event_voice_overrides debe ser un mapa")
    payloads: list[dict[str, Any]] = []
    seen: set[str] = set()
    assignments: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []

    for event in event_candidates:
        payload = _payload(event)
        event_id = payload.get("event_id")
        staff = payload.get("staff_index")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in seen:
            raise ValueError("Los event_id deben ser únicos y no vacíos")
        seen.add(event_id)
        if not isinstance(staff, int) or isinstance(staff, bool) or staff < 0:
            raise ValueError(f"{event_id}: staff_index no válido")

        if event_id in overrides:
            voice_id, reason = _confirmed_voice(overrides[event_id], event_id)
            source = "event_override"
        else:
            voice_id, reason = _confirmed_voice(
                contexts.get(staff, {}), f"staff {staff}"
            )
            source = "staff_context"

        if reason is not None:
            payload["voice_id_candidate"] = None
            payload["status"] = "incomplete_candidate"
            unresolved.append({"event_id": event_id, "reason": reason})
            assignments.append({
                "event_id": event_id, "voice_id": None,
                "source": source, "status": "unresolved",
            })
        else:
            payload["voice_id_candidate"] = voice_id
            payload["status"] = (
                "ready_for_review" if _musically_complete(payload)
                and payload.get("status") in {"incomplete_candidate", "ready_for_review"}
                else "incomplete_candidate"
            )
            assignments.append({
                "event_id": event_id, "voice_id": voice_id,
                "source": source, "status": "resolved_from_human_confirmed_context",
            })
        payloads.append(payload)

    return {
        "status": "unconfirmed_voice_assignment_map",
        "event_candidates": payloads,
        "assignments": assignments,
        "unresolved": unresolved,
        "warning": (
            "Las voces proceden de etiquetas humanas confirmadas; las "
            "asignaciones siguen siendo candidatas y no validan la detección "
            "automática de partes ni de líneas polifónicas."
        ),
    }


def apply_voice_assignments_to_timelines(
    timelines: Sequence[Mapping[str, Any]],
    voice_assignment_map: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Propaga IDs de voz confirmados a los eventos temporales por event_id."""
    if not isinstance(voice_assignment_map, Mapping) or voice_assignment_map.get("status") != "unconfirmed_voice_assignment_map":
        raise ValueError("Se requiere un mapa de asignación de voz Palermo provisional")
    voice_by_event = {
        item["event_id"]: item["voice_id"]
        for item in voice_assignment_map.get("assignments", [])
        if item.get("status") == "resolved_from_human_confirmed_context"
        and isinstance(item.get("voice_id"), str) and item["voice_id"].strip()
    }
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for timeline in timelines:
        if not isinstance(timeline, Mapping):
            raise ValueError("Cada timeline debe ser un objeto")
        copied = dict(timeline)
        events = timeline.get("events", [])
        if not isinstance(events, list):
            raise ValueError("timeline.events debe ser una lista")
        copied_events = []
        for event in events:
            if not isinstance(event, Mapping):
                raise ValueError("Cada evento temporal debe ser un objeto")
            event_id = event.get("event_id")
            if not isinstance(event_id, str) or not event_id:
                raise ValueError("Cada evento temporal requiere event_id")
            if event_id in seen:
                raise ValueError(f"El evento {event_id} aparece más de una vez")
            seen.add(event_id)
            copied_event = dict(event)
            # No conservar una voz no revisada que viniera en el timeline.
            copied_event["voice_id"] = voice_by_event.get(event_id)
            copied_events.append(copied_event)
        copied["events"] = copied_events
        result.append(copied)
    return result
