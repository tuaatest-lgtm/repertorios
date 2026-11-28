"""Paquete provisional de reproducción que reúne audio y mapa visual multipágina."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .playback_projection import (
    build_playback_projection,
    merge_page_timelines_by_global_measure_map,
)
from .polyphonic_command_stream import build_polyphonic_command_stream
from .score_document import ScoreDocument
from .page_analysis_visual_adapter import build_score_structure_from_page_analysis
from .visual_anchor_map import build_visual_anchor_map_from_score_structure
from .voice_assignment import (
    apply_reviewed_voice_assignments,
    apply_voice_assignments_to_timelines,
)


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
    staff_voice_contexts: Mapping[int | str, Mapping[str, Any]] | None = None,
    event_voice_overrides: Mapping[str, Mapping[str, Any]] | None = None,
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

    voice_assignment = None
    projection_candidates: Sequence[Any] = event_candidates
    projection_timelines: Sequence[Mapping[str, Any]] = timelines
    if staff_voice_contexts is not None:
        voice_assignment = apply_reviewed_voice_assignments(
            event_candidates, staff_voice_contexts,
            event_voice_overrides=event_voice_overrides,
        )
        projection_candidates = voice_assignment["event_candidates"]
        projection_timelines = apply_voice_assignments_to_timelines(
            timelines, voice_assignment
        )
    elif event_voice_overrides is not None:
        raise ValueError("event_voice_overrides requiere staff_voice_contexts")

    candidates_by_id: dict[str, Any] = {}
    for event in projection_candidates:
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
        projection_timelines, list(candidates_by_id.values()), tempo_bpm=tempo_bpm
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
        **({"voice_assignment": voice_assignment} if voice_assignment is not None else {}),
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


def build_score_playback_bundle_from_page_analyses(
    timelines: Sequence[Mapping[str, Any]],
    event_candidates: Sequence[Any],
    page_analyses: Sequence[Mapping[str, Any]],
    *,
    event_page_numbers: Mapping[str, int],
    event_notehead_indices: Mapping[str, Sequence[int]],
    page_measure_global_indices: Mapping[int, Mapping[int, int]] | None = None,
    event_geometry_by_id: Mapping[str, Any] | None = None,
    tempo_bpm: int | float,
    padding_px: float = 2.0,
    staff_voice_contexts: Mapping[int | str, Mapping[str, Any]] | None = None,
    event_voice_overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Construye el bundle desde los JSON de análisis multipágina originales.

    Los índices de cabezas son locales a la página indicada por evento_page_numbers.
    La relación se valida contra IDs de cabezas ya asociados en event_candidates;
    cualquier desacuerdo se conserva como geometría no resuelta.
    """
    if not isinstance(page_analyses, (list, tuple)) or not page_analyses:
        raise ValueError("page_analyses debe contener al menos una página")
    if not isinstance(event_page_numbers, Mapping) or not isinstance(event_notehead_indices, Mapping):
        raise ValueError("event_page_numbers y event_notehead_indices deben ser mapas")
    structures = [build_score_structure_from_page_analysis(page) for page in page_analyses]
    structures.sort(key=lambda page: page.page_number)
    document = ScoreDocument(pages=tuple(structures))
    document.validate()
    pages_by_number = {page["page_number"]: page for page in page_analyses}
    if len(pages_by_number) != len(page_analyses):
        raise ValueError("page_analyses no puede repetir page_number")

    timeline_result = None
    timelines_for_projection = timelines
    timeline_pages = {item.get("page_number") for item in timelines if isinstance(item, Mapping) and item.get("page_number") is not None}
    if len(timeline_pages) > 1 and page_measure_global_indices is None:
        raise ValueError("La reproducción multipágina requiere page_measure_global_indices explícito")
    if page_measure_global_indices is not None:
        timeline_result = merge_page_timelines_by_global_measure_map(
            timelines, page_measure_global_indices
        )
        timelines_for_projection = timeline_result["timelines"]

    geometry: dict[str, Any] = {}
    overrides: dict[str, dict[str, str]] = {}
    seen_head_ids: set[str] = set()
    for candidate in event_candidates:
        payload = candidate.to_dict() if hasattr(candidate, "to_dict") else candidate
        if not isinstance(payload, Mapping):
            raise ValueError("Cada evento candidato debe ser serializable")
        event_id = payload.get("event_id")
        page_number = event_page_numbers.get(event_id)
        if page_number not in pages_by_number:
            continue
        page = pages_by_number[page_number]
        heads = page.get("notehead_candidates", [])
        indices = event_notehead_indices.get(event_id, ())
        head_ids = payload.get("notehead_candidate_ids", ())
        if not isinstance(indices, (list, tuple)) or not isinstance(head_ids, (list, tuple)):
            overrides[event_id] = {"event_id": event_id, "reason": "invalid_notehead_index_mapping"}
            continue
        if len(indices) != len(head_ids):
            if indices or head_ids:
                overrides[event_id] = {"event_id": event_id, "reason": "notehead_index_mapping_mismatch"}
            continue
        selected = []
        invalid = False
        for index, head_id in zip(indices, head_ids):
            if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(heads):
                overrides[event_id] = {"event_id": event_id, "reason": "notehead_index_out_of_range"}
                invalid = True
                break
            if not isinstance(head_id, str) or not head_id:
                overrides[event_id] = {"event_id": event_id, "reason": "invalid_notehead_id"}
                invalid = True
                break
            if head_id in seen_head_ids:
                raise ValueError("Una cabeza geométrica no puede pertenecer a dos eventos")
            seen_head_ids.add(head_id)
            selected.append((index, head_id, heads[index]))
        if invalid:
            continue
        staff_indices = {item[2].get("staff_index") for item in selected}
        if len(staff_indices) > 1 or (selected and payload.get("staff_index") not in staff_indices):
            overrides[event_id] = {"event_id": event_id, "reason": "cross_staff_or_mismatched_noteheads"}
            continue
        for _, head_id, head in selected:
            geometry[head_id] = {"bbox": head.get("bbox")}

    result = build_score_playback_bundle(
        timelines_for_projection, event_candidates, document,
        event_page_numbers=event_page_numbers,
        notehead_geometry_by_id=geometry,
        event_geometry_by_id=event_geometry_by_id,
        tempo_bpm=tempo_bpm,
        padding_px=padding_px,
        staff_voice_contexts=staff_voice_contexts,
        event_voice_overrides=event_voice_overrides,
    )
    unresolved = {item["event_id"]: item for item in result["visual_anchor_map"]["unresolved"]}
    unresolved.update(overrides)
    result["visual_anchor_map"]["unresolved"] = sorted(
        unresolved.values(), key=lambda item: item["event_id"]
    )
    anchored = {item["event_id"] for item in result["visual_anchor_map"]["anchors"]}
    playable = {item["event_id"] for item in result["playback_projection"]["events"]}
    result["coverage"]["anchored_events"] = len(anchored)
    result["coverage"]["playable_without_visual_anchor"] = sorted(playable - anchored)
    result["coverage"]["visual_without_playback_event"] = sorted(anchored - playable)
    if timeline_result is not None:
        result["document_timeline"] = timeline_result
    return result
