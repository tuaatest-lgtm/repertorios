"""Construye grupos rítmicos y eventos fusionados desde el JSON de página."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any

from .beam_groups import BeamGroupCandidate
from .event_fusion import fuse_score_event_candidates
from .imaging import StaffCandidate
from .rhythm import RhythmCandidate
from .rhythm_interpretation import RhythmicInterpretationCandidate
from .rhythmic_event_groups import build_rhythmic_event_group_candidates
from .page_pitch_adapter import build_pitch_candidates_from_page_analysis
from .symbols import NoteheadCandidate


def build_event_candidates_from_page_analysis(
    page_analysis: Mapping[str, Any],
    pitch_candidates: Sequence[Any],
    notehead_candidate_ids: Sequence[str],
    *,
    max_chord_spread_spacing: float = 1.10,
) -> dict[str, Any]:
    """Fusiona ritmo, alturas y cabezas conservando ambigüedades por página.

    Todos los arrays se alinean por el índice original de notehead_candidates.
    El ID del evento recibe prefijo de página para mantener unicidad
    multipágina. No asigna voces ni inventa duraciones.
    """
    if not isinstance(page_analysis, Mapping):
        raise ValueError("page_analysis debe ser un objeto")
    page_number = page_analysis.get("page_number")
    if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 1:
        raise ValueError("page_number debe ser un entero positivo")

    raw_staves = page_analysis.get("staves")
    raw_heads = page_analysis.get("notehead_candidates")
    raw_rhythms = page_analysis.get("rhythm_candidates")
    raw_interpretations = page_analysis.get("rhythmic_interpretation_candidates")
    raw_beams = page_analysis.get("beam_group_candidates", [])
    if not all(isinstance(items, list) for items in (
        raw_staves, raw_heads, raw_rhythms, raw_interpretations, raw_beams
    )):
        raise ValueError("El análisis debe incluir staves, noteheads, rhythms e interpretations")
    count = len(raw_heads)
    if len(raw_rhythms) != count or len(raw_interpretations) != count:
        raise ValueError("Ritmo e interpretación deben alinearse con cada cabeza")
    if len(pitch_candidates) != count or len(notehead_candidate_ids) != count:
        raise ValueError("Alturas e IDs deben alinearse con cada cabeza")
    if len(set(notehead_candidate_ids)) != count or any(
        not isinstance(value, str) or not value.strip() for value in notehead_candidate_ids
    ):
        raise ValueError("Los IDs de cabezas deben ser únicos y no vacíos")

    staves = [StaffCandidate(
        lines_y=list(item["lines_y"]),
        spacing_px=float(item["spacing_px"]),
        confidence=float(item.get("confidence", 0.0)),
    ) for item in raw_staves]
    noteheads = [NoteheadCandidate(
        bbox=tuple(item["bbox"]),
        center_x=float(item["center_x"]),
        center_y=float(item["center_y"]),
        staff_index=int(item["staff_index"]),
        diatonic_step_from_bottom=int(item["diatonic_step_from_bottom"]),
        fill_ratio=float(item.get("fill_ratio", 0.0)),
        notehead_shape_score=float(item.get("notehead_shape_score", 0.0)),
        confidence=float(item.get("confidence", 0.0)),
    ) for item in raw_heads]
    rhythms = [RhythmCandidate(
        notehead_bbox=tuple(item["notehead_bbox"]),
        staff_index=int(item["staff_index"]),
        notehead_fill=str(item["notehead_fill"]),
        notehead_fill_score=float(item["notehead_fill_score"]),
        stem_direction=str(item["stem_direction"]),
        stem_length_px=int(item["stem_length_px"]),
        beam_count=int(item["beam_count"]),
        base_duration=str(item["base_duration"]),
        confidence=float(item["confidence"]),
        warnings=tuple(item.get("warnings", ())),
    ) for item in raw_rhythms]
    interpretations = [RhythmicInterpretationCandidate(
        notehead_index=int(item["notehead_index"]),
        staff_index=int(item["staff_index"]),
        duration_candidate=str(item["duration_candidate"]),
        beam_count_candidate=int(item["beam_count_candidate"]),
        beam_group_indices=tuple(item.get("beam_group_indices", ())),
        confidence=float(item["confidence"]),
        status=str(item["status"]),
        warnings=tuple(item.get("warnings", ())),
    ) for item in raw_interpretations]
    beams = [BeamGroupCandidate(
        staff_index=int(item["staff_index"]),
        notehead_indices=list(item["notehead_indices"]),
        bbox=tuple(item["bbox"]),
        beam_count_candidate=int(item["beam_count_candidate"]),
        confidence=float(item["confidence"]),
        warning=str(item["warning"]),
        connection_type_candidate=str(item.get("connection_type_candidate", "shared")),
    ) for item in raw_beams]

    groups = build_rhythmic_event_group_candidates(
        staves, noteheads, rhythms, interpretations,
        max_chord_spread_spacing=max_chord_spread_spacing,
    )
    page_groups = tuple(
        replace(group, event_id=f"p{page_number}-{group.event_id}")
        for group in groups
    )
    events = fuse_score_event_candidates(
        page_groups, pitch_candidates, notehead_candidate_ids
    )
    return {
        "status": "unconfirmed_page_event_candidates",
        "page_number": page_number,
        "rhythmic_event_groups": [group.to_dict() for group in page_groups],
        "event_candidates": [event.to_dict() for event in events],
        "warning": (
            "Los grupos rítmicos y eventos fusionados siguen siendo candidatos. "
            "Plicas, haces, alturas y ataques no se consideran confirmados."
        ),
    }


def build_page_score_candidates(
    page_analysis: Mapping[str, Any],
    staff_contexts: Mapping[int | str, Mapping[str, Any]],
    notehead_candidate_ids: Sequence[str],
    *,
    measure_ids: Sequence[str | int | None] | None = None,
    simultaneous_group_ids: Sequence[str | int] | None = None,
    explicit_accidentals: Sequence[str | None] | None = None,
    notehead_ids: Sequence[str] | None = None,
    accidental_attachment_map: Mapping[str, Any] | None = None,
    accepted_accidental_ids: Sequence[str] = (),
    max_chord_spread_spacing: float = 1.10,
) -> dict[str, Any]:
    """Une contexto de altura y grupos rítmicos en eventos candidatos de página."""
    pitch_result = build_pitch_candidates_from_page_analysis(
        page_analysis, staff_contexts,
        measure_ids=measure_ids,
        simultaneous_group_ids=simultaneous_group_ids,
        explicit_accidentals=explicit_accidentals,
        notehead_ids=notehead_ids,
        accidental_attachment_map=accidental_attachment_map,
        accepted_accidental_ids=accepted_accidental_ids,
    )
    event_result = build_event_candidates_from_page_analysis(
        page_analysis, pitch_result["pitch_candidates"], notehead_candidate_ids,
        max_chord_spread_spacing=max_chord_spread_spacing,
    )
    return {
        "status": "unconfirmed_page_score_candidates",
        "page_number": page_analysis["page_number"],
        "pitch_candidates": pitch_result["pitch_candidates"],
        "rhythmic_event_groups": event_result["rhythmic_event_groups"],
        "event_candidates": event_result["event_candidates"],
        "unresolved_staff_contexts": pitch_result["unresolved_staff_contexts"],
        "warning": (
            "Salida integrada de candidatos geométricos, ritmo y altura. "
            "No confirma claves, armaduras, cabezas, figuras, voces ni notas."
        ),
    }
