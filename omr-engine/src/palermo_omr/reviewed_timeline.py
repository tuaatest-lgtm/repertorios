"""Línea temporal por compás a partir de grupos rítmicos revisados por una persona.

La geometría solo genera candidatos. Este adaptador exige confirmación explícita
de cada evento, asignación explícita de voz y compás/métrica suministrados.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from .rhythmic_event_groups import (
    RhythmicEventGroupCandidate,
    build_reviewed_voice_events_by_voice,
)
from .rhythmic_timeline import analyze_ordered_measure_voices
from .rest_events import RestReviewAssignment, build_reviewed_rest_events
from .rhythm_symbols import DotCandidate, RestSymbolCandidate
from .tie_candidates import TieLinkCandidate, TieReviewConfirmation
from .reviewed_tie_chains import (
    apply_reviewed_tie_chains_to_timeline,
    apply_reviewed_tie_chains_to_page_timelines,
)
from .measure_duration_review import build_measure_duration_completion_candidates


def build_reviewed_page_timelines(
    groups: Sequence[RhythmicEventGroupCandidate],
    page_manifest: Mapping[str, Any],
    *,
    rest_candidates: Sequence[RestSymbolCandidate] = (),
    pitch_candidates: Sequence[Any] = (),
    dot_candidates: Sequence[DotCandidate] = (),
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
    used_pitch_candidate_indices: set[int] = set()
    used_dot_candidate_indices: set[int] = set()
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

        # La revisión puede confirmar puntillos por conteo manual o enlazando
        # candidatos visuales concretos. Los candidatos solo afectan duración
        # cuando el manifiesto los asocia explícitamente a un evento confirmado.
        dot_counts = measure.get("event_dot_counts", {})
        if not isinstance(dot_counts, Mapping):
            raise ValueError("event_dot_counts debe ser un objeto")
        raw_dot_links = measure.get("event_dot_candidate_indices", {})
        if not isinstance(raw_dot_links, Mapping):
            raise ValueError("event_dot_candidate_indices debe ser un objeto")
        if set(raw_dot_links) - set(confirmed):
            raise ValueError("Los puntillos visuales solo pueden enlazarse a eventos confirmados")
        if set(raw_dot_links).intersection(dot_counts):
            raise ValueError("No se puede mezclar conteo manual y candidatos visuales para el mismo evento")
        linked_dot_counts = {}
        for event_id, indices in raw_dot_links.items():
            if not isinstance(indices, list):
                raise ValueError("Cada enlace de puntillos debe ser una lista de índices")
            if len(indices) > 4 or any(
                not isinstance(index, int) or isinstance(index, bool)
                for index in indices
            ):
                raise ValueError("Cada evento debe enlazar entre cero y cuatro índices enteros")
            if len(indices) != len(set(indices)):
                raise ValueError("Un evento no puede repetir el mismo candidato de puntillo")
            group = next(item for item in groups if item.event_id == event_id)
            for candidate_index in indices:
                if not 0 <= candidate_index < len(dot_candidates):
                    raise ValueError("Índice de candidato de puntillo fuera de rango")
                if candidate_index in used_dot_candidate_indices:
                    raise ValueError("Un candidato de puntillo no puede reutilizarse en dos eventos")
                candidate = dot_candidates[candidate_index]
                if candidate.associated_notehead_index not in group.notehead_indices:
                    raise ValueError("El puntillo visual no corresponde a una cabeza del evento confirmado")
                used_dot_candidate_indices.add(candidate_index)
            linked_dot_counts[event_id] = len(indices)
        effective_dot_counts = {**dot_counts, **linked_dot_counts}
        raw_duration_review = measure.get("duration_completion_review")
        if raw_duration_review is None:
            duration_review = None
            allow_unknown_duration_ids = frozenset()
        else:
            if not isinstance(raw_duration_review, Mapping):
                raise ValueError("duration_completion_review debe ser un objeto")
            allowed_review_keys = {
                "allow_unknown_duration_candidates",
                "measure_complete_confirmed",
                "ties_and_tuplets_resolved",
            }
            if set(raw_duration_review) - allowed_review_keys:
                raise ValueError("duration_completion_review contiene campos desconocidos")
            for key in allowed_review_keys:
                if key in raw_duration_review and not isinstance(raw_duration_review[key], bool):
                    raise ValueError(f"{key} debe ser booleano")
            duration_review = {
                "measure_complete_confirmed": raw_duration_review.get("measure_complete_confirmed", False),
                "ties_and_tuplets_resolved": raw_duration_review.get("ties_and_tuplets_resolved", False),
            }
            allow_unknown_duration_ids = (
                frozenset(
                    event_id for event_id in confirmed
                    if next(group for group in groups if group.event_id == event_id).duration_quarters_candidate is None
                )
                if raw_duration_review.get("allow_unknown_duration_candidates", False)
                else frozenset()
            )
        events = build_reviewed_voice_events_by_voice(
            groups,
            measure_index=measure_index,
            event_voice_ids=voice_map,
            confirmed_event_ids=set(confirmed),
            event_dot_counts=effective_dot_counts,
            allow_unknown_duration_event_ids=allow_unknown_duration_ids,
        )
        order_map = measure.get("event_order_indices")
        if order_map is not None:
            if not isinstance(order_map, Mapping) or set(order_map) != set(confirmed):
                raise ValueError(
                    "event_order_indices debe asignar exactamente un orden a cada nota confirmada"
                )
            normalized_order = {}
            for event_id, order_index in order_map.items():
                if not isinstance(order_index, int) or isinstance(order_index, bool) or order_index < 0:
                    raise ValueError("Cada event_order_index debe ser un entero no negativo")
                normalized_order[event_id] = order_index
            events = tuple(
                replace(event, order_index=normalized_order[event.event_id])
                for event in events
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
        timeline_data = timeline.to_dict()
        pitch_map = measure.get("confirmed_pitch_candidate_indices")
        if pitch_map is not None:
            note_ids = set(confirmed)
            if not isinstance(pitch_map, Mapping) or set(pitch_map) != note_ids:
                raise ValueError(
                    "confirmed_pitch_candidate_indices debe cubrir exactamente cada evento de nota"
                )
            event_pitch_data = {}
            for event_id, indices in pitch_map.items():
                group = next(item for item in groups if item.event_id == event_id)
                if not isinstance(indices, list) or len(indices) != len(group.notehead_indices):
                    raise ValueError("Cada evento debe confirmar una altura por cabeza de nota")
                if any(
                    not isinstance(index, int) or isinstance(index, bool)
                    or not 0 <= index < len(pitch_candidates)
                    for index in indices
                ):
                    raise ValueError("Índice de candidato de altura fuera de rango")
                if len(indices) != len(set(indices)):
                    raise ValueError("Un evento no puede repetir candidatos de altura")
                if used_pitch_candidate_indices.intersection(indices):
                    raise ValueError("Un candidato de altura no puede reutilizarse en dos eventos")
                used_pitch_candidate_indices.update(indices)
                selected_pitches = []
                for notehead_index, pitch_index in zip(group.notehead_indices, indices):
                    candidate = pitch_candidates[pitch_index]
                    if candidate.source_index != notehead_index or candidate.staff_index != group.staff_index:
                        raise ValueError("La altura confirmada no corresponde a la cabeza del evento")
                    if candidate.status != "resolved_from_supplied_clef" or candidate.pitch is None:
                        raise ValueError("No se puede confirmar una altura sin clave y altura resueltas")
                    selected_pitches.append({
                        "source_index": candidate.source_index,
                        "source_kind": candidate.source_kind,
                        "step": candidate.pitch.step,
                        "octave": candidate.pitch.octave,
                        "alteration": candidate.pitch.alteration,
                        "midi": candidate.pitch.midi,
                    })
                event_pitch_data[event_id] = selected_pitches
            for event in timeline_data["events"]:
                if event["event_id"] in event_pitch_data:
                    event["confirmed_pitches"] = event_pitch_data[event["event_id"]]
        raw_tie_candidates = measure.get("tie_candidates", [])
        raw_tie_confirmations = measure.get("tie_confirmations", [])
        if not isinstance(raw_tie_candidates, list) or not isinstance(raw_tie_confirmations, list):
            raise ValueError("tie_candidates y tie_confirmations deben ser listas")
        try:
            tie_candidates = [
                TieLinkCandidate(
                    **{**item, "warnings": tuple(item.get("warnings", ()))}
                )
                for item in raw_tie_candidates
            ]
            tie_confirmations = [
                TieReviewConfirmation(**item) for item in raw_tie_confirmations
            ]
        except (TypeError, AttributeError) as exc:
            raise ValueError("La revisión de ligaduras contiene campos inválidos") from exc
        if tie_candidates or tie_confirmations:
            timeline_data = apply_reviewed_tie_chains_to_timeline(
                timeline_data, tie_candidates, tie_confirmations
            )
        if duration_review is not None:
            timeline_data["duration_completion_candidates"] = [
                item.to_dict()
                for item in build_measure_duration_completion_candidates(
                    timeline_data["events"],
                    numerator,
                    denominator,
                    **duration_review,
                )
            ]
        results.append({
            "page_number": page_number,
            "time_signature": {"numerator": numerator, "denominator": denominator},
            **timeline_data,
            "review_status": "human_confirmed_events",
            "warning": (
                "La línea temporal usa únicamente eventos confirmados en el manifiesto. "
                "No implica que la detección visual automática haya sido validada."
            ),
        })
    raw_page_tie_candidates = page_manifest.get("tie_candidates", [])
    raw_page_tie_confirmations = page_manifest.get("tie_confirmations", [])
    if not isinstance(raw_page_tie_candidates, list) or not isinstance(raw_page_tie_confirmations, list):
        raise ValueError("Las ligaduras de página deben ser listas")
    if raw_page_tie_candidates or raw_page_tie_confirmations:
        try:
            page_tie_candidates = [
                TieLinkCandidate(**{**item, "warnings": tuple(item.get("warnings", ()))})
                for item in raw_page_tie_candidates
            ]
            page_tie_confirmations = [
                TieReviewConfirmation(**item) for item in raw_page_tie_confirmations
            ]
        except (TypeError, AttributeError) as exc:
            raise ValueError("La revisión de ligaduras de página contiene campos inválidos") from exc
        results = apply_reviewed_tie_chains_to_page_timelines(
            results, page_tie_candidates, page_tie_confirmations
        )
    return results
