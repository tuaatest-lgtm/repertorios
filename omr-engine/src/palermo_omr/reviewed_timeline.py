"""Línea temporal por compás a partir de grupos rítmicos revisados por una persona.

La geometría solo genera candidatos. Este adaptador exige confirmación explícita
de cada evento, asignación explícita de voz y compás/métrica suministrados.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .rhythmic_event_groups import (
    RhythmicEventGroupCandidate,
    build_reviewed_voice_events_by_voice,
)
from .rhythmic_timeline import analyze_ordered_measure_voices
from .rest_events import RestReviewAssignment, build_reviewed_rest_events
from .rhythm_symbols import RestSymbolCandidate


def build_reviewed_page_timelines(
    groups: Sequence[RhythmicEventGroupCandidate],
    page_manifest: Mapping[str, Any],
    *,
    rest_candidates: Sequence[RestSymbolCandidate] = (),
) -> list[dict[str, Any]]:
    """Construye líneas temporales por compás sin aceptar inferencias visuales.

    Esquema: {"page_number": 1, "measures": [{"measure_index": 0,
    "numerator": 4, "denominator": 4, "confirmed_event_ids": [...],
    "event_voice_ids": {"staff-1-event-1": "soprano"},
    "event_dot_counts": {"staff-1-event-1": 1}}]}.
    """
    if not isinstance(page_manifest, Mapping):
        raise ValueError("Cada página del manifiesto revisado debe ser un objeto")
    page_number = page_manifest.get("page_number")
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
        raise ValueError("page_number debe ser un entero positivo")
    measures = page_manifest.get("measures")
    if not isinstance(measures, list):
        raise ValueError("measures debe ser una lista")

    known_group_ids = {group.event_id for group in groups}
    if len(known_group_ids) != len(groups):
        raise ValueError("Los grupos rítmicos deben tener event_id únicos")
    used_event_ids: set[str] = set()
    used_rest_candidate_indices: set[int] = set()
    results: list[dict[str, Any]] = []
    seen_measure_indices: set[int] = set()

    for measure in measures:
        if not isinstance(measure, Mapping):
            raise ValueError("Cada compás revisado debe ser un objeto")
        measure_index = measure.get("measure_index")
        numerator = measure.get("numerator")
        denominator = measure.get("denominator")
        if not isinstance(measure_index, int) or isinstance(measure_index, bool) or measure_index < 0:
            raise ValueError("measure_index debe ser un entero no negativo")
        if measure_index in seen_measure_indices:
            raise ValueError("No se puede repetir measure_index en una página")
        seen_measure_indices.add(measure_index)
        for name, value in (("numerator", numerator), ("denominator", denominator)):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} debe ser un entero positivo")

        confirmed = measure.get("confirmed_event_ids")
        voice_map = measure.get("event_voice_ids")
        if not isinstance(confirmed, list) or not confirmed:
            raise ValueError("Cada compás debe incluir confirmed_event_ids no vacío")
        if any(not isinstance(item, str) or not item.strip() for item in confirmed):
            raise ValueError("confirmed_event_ids solo puede contener IDs de texto no vacíos")
        if len(confirmed) != len(set(confirmed)):
            raise ValueError("confirmed_event_ids no puede repetir IDs")
        if not isinstance(voice_map, Mapping) or set(voice_map) != set(confirmed):
            raise ValueError("Debe existir exactamente una voz explícita por evento confirmado")
        if set(confirmed) - known_group_ids:
            raise ValueError("La revisión referencia grupos rítmicos inexistentes")
        if used_event_ids.intersection(confirmed):
            raise ValueError("Un grupo confirmado no puede pertenecer a dos compases")
        used_event_ids.update(confirmed)

        dot_counts = measure.get("event_dot_counts", {})
        if not isinstance(dot_counts, Mapping):
            raise ValueError("event_dot_counts debe ser un objeto")
        events = build_reviewed_voice_events_by_voice(
            groups,
            measure_index=measure_index,
            event_voice_ids=voice_map,
            confirmed_event_ids=set(confirmed),
            event_dot_counts=dot_counts,
        )
        # Los silencios también ocupan tiempo dentro de una voz. Se integran
        # solo si la revisión aporta candidato, tipo, voz, orden y duración.
        raw_rest_assignments = measure.get("rest_assignments", [])
        if not isinstance(raw_rest_assignments, list):
            raise ValueError("rest_assignments debe ser una lista")
        rest_assignments = []
        for item in raw_rest_assignments:
            if not isinstance(item, Mapping):
                raise ValueError("Cada rest_assignment debe ser un objeto")
            try:
                rest_assignments.append(RestReviewAssignment(**item))
            except TypeError as exc:
                raise ValueError("rest_assignment contiene campos ausentes o desconocidos") from exc
        rest_events = build_reviewed_rest_events(rest_candidates, rest_assignments)
        rest_indices = {item.candidate_index for item in rest_assignments}
        if used_rest_candidate_indices.intersection(rest_indices):
            raise ValueError("Un candidato de silencio no puede reutilizarse en dos compases")
        used_rest_candidate_indices.update(rest_indices)

        by_voice: dict[str, list] = {}
        for event in (*events, *rest_events):
            by_voice.setdefault(event.voice_id, []).append(event)
        for voice_id, voice_events in by_voice.items():
            event_ids = [event.event_id for event in voice_events]
            order_indices = [event.order_index for event in voice_events]
            if len(event_ids) != len(set(event_ids)):
                raise ValueError("Los IDs de notas y silencios deben ser únicos en la voz")
            if len(order_indices) != len(set(order_indices)):
                raise ValueError(
                    f"Notas y silencios tienen order_index repetido en la voz {voice_id}"
                )
        timeline = analyze_ordered_measure_voices(
            [
                (voice_id, measure_index, voice_events)
                for voice_id, voice_events in sorted(by_voice.items())
            ],
            numerator,
            denominator,
            measure_index=measure_index,
        )
        results.append({
            "page_number": page_number,
            "time_signature": {"numerator": numerator, "denominator": denominator},
            **timeline.to_dict(),
            "review_status": "human_confirmed_events",
            "warning": (
                "La línea temporal usa únicamente eventos confirmados en el manifiesto. "
                "No implica que la detección visual automática haya sido validada."
            ),
        })
    return results
