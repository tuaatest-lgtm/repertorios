"""Paquete provisional de reproducción que reúne audio y mapa visual multipágina."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .playback_projection import build_playback_projection
from .polyphonic_command_stream import build_polyphonic_command_stream
from .score_document import ScoreDocument
from .visual_anchor_map import build_visual_anchor_map_from_score_structure


def build_score_playback_bundle(
    timelines: Sequence[Mapping[str, Any]],
    event_candidates: Sequence[Any],
    score_document: ScoreDocument,
    *,
    event_page_numbers: Mapping[str, int],
    notehead_geometry_by_id: Mapping[str, Any],
    event_geometry_by_id: Mapping[str, Any] | None = None,
    tempo_bpm: int | float,
    padding_px: float = 2.0,
) -> dict[str, Any]:
    """Construye agenda de audio y anclajes de cursor para un ScoreDocument.

    La página de cada evento debe ser explícita en event_page_numbers. Los
    compases se resuelven contra MeasureRegion del mismo pentagrama/página;
    geometría o contexto ausentes quedan reportados, nunca inferidos.
    """
    if not isinstance(score_document, ScoreDocument):
        raise ValueError("Se requiere un ScoreDocument")
    score_document.validate()
    if not isinstance(event_page_numbers, Mapping):
        raise ValueError("event_page_numbers debe ser un mapa explícito")

    candidates_by_id: dict[str, Any] = {}
    for event in event_candidates:
        payload = event.to_dict() if hasattr(event, "to_dict") else event
        if not isinstance(payload, Mapping):
            raise ValueError("Cada evento candidato debe ser serializable")
        event_id = payload.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in candidates_by_id:
            raise ValueError("Los event_id deben ser únicos y no vacíos")
        candidates_by_id[event_id] = event

    known_pages = {page.page_number: page for page in score_document.pages}
    anchors: list[dict[str, Any]] = []
    unresolved_visual: dict[str, dict[str, str]] = {}
    geometry_by_event = event_geometry_by_id or {}

    for event_id, event in sorted(candidates_by_id.items()):
        page_number = event_page_numbers.get(event_id)
        if not isinstance(page_number, int) or isinstance(page_number, bool):
            unresolved_visual[event_id] = {"event_id": event_id, "reason": "missing_page_mapping"}
            continue
        page = known_pages.get(page_number)
        if page is None:
            unresolved_visual[event_id] = {"event_id": event_id, "reason": "unknown_page_mapping"}
            continue
        payload = event.to_dict() if hasattr(event, "to_dict") else dict(event)
        result = build_visual_anchor_map_from_score_structure(
            [event],
            notehead_geometry_by_id,
            page,
            event_geometry_by_id={event_id: geometry_by_event[event_id]}
            if event_id in geometry_by_event else {},
            padding_px=padding_px,
        )
        anchors.extend(result["anchors"])
        for item in result["unresolved"]:
            unresolved_visual[event_id] = item

    projection = build_playback_projection(
        timelines, list(candidates_by_id.values()), tempo_bpm=tempo_bpm
    )
    command_stream = build_polyphonic_command_stream(projection)
    visual_map = {
        "status": "unconfirmed_visual_anchor_map",
        "anchors": sorted(anchors, key=lambda item: item["event_id"]),
        "unresolved": sorted(unresolved_visual.values(), key=lambda item: item["event_id"]),
    }
    playable_ids = {event["event_id"] for event in projection["events"]}
    anchored_ids = {item["event_id"] for item in anchors}
    return {
        "status": "unconfirmed_score_playback_bundle",
        "playback_projection": projection,
        "command_stream": command_stream,
        "visual_anchor_map": visual_map,
        "coverage": {
            "candidate_events": len(candidates_by_id),
            "playable_events": len(playable_ids),
            "anchored_events": len(anchored_ids),
            "playable_without_visual_anchor": sorted(playable_ids - anchored_ids),
            "visual_without_playback_event": sorted(anchored_ids - playable_ids),
        },
        "warning": (
            "Paquete provisional: solo combina candidatos temporales, comandos "
            "de audio y geometría explícita. No confirma reconocimiento musical."
        ),
    }
