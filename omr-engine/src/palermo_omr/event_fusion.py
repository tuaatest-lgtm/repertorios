"""Fusiona candidatos de ritmo, voz y altura en eventos musicales auditables.

Este módulo no confirma notas ni duraciones: conserva la procedencia geométrica,
los estados de altura y las incertidumbres antes de construir una línea temporal.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import Any, Sequence


@dataclass(frozen=True)
class ScoreEventCandidate:
    event_id: str
    staff_index: int
    notehead_candidate_ids: tuple[str, ...]
    pitch_candidates: tuple[dict[str, Any], ...]
    voice_id_candidate: str | None
    duration_candidate: str
    duration_quarters_candidate: Fraction | None
    status: str
    warnings: tuple[str, ...]
    event_type: str = "note"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.duration_quarters_candidate is not None:
            result["duration_quarters_candidate"] = str(self.duration_quarters_candidate)
        result["notehead_candidate_ids"] = list(self.notehead_candidate_ids)
        result["pitch_candidates"] = list(self.pitch_candidates)
        result["warnings"] = list(self.warnings)
        return result


def _pitch_payload(candidate: Any) -> dict[str, Any]:
    if hasattr(candidate, "to_dict"):
        return candidate.to_dict()
    if isinstance(candidate, dict):
        return dict(candidate)
    raise ValueError("Cada candidato de altura debe ser serializable mediante to_dict()")


def fuse_score_event_candidates(
    rhythmic_groups: Sequence[Any],
    pitch_candidates: Sequence[Any],
    notehead_candidate_ids: Sequence[str],
) -> tuple[ScoreEventCandidate, ...]:
    """Une grupos rítmicos con sus alturas sin promover hipótesis a hechos.

    Los índices de notehead_indices deben referirse al mismo orden usado para
    producir pitch_candidates y notehead_candidate_ids. Un evento queda
    ready_for_review solo cuando tiene voz, duración y todas sus alturas
    resueltas; aun así sigue siendo candidato, nunca evento confirmado.
    """
    if len(pitch_candidates) != len(notehead_candidate_ids):
        raise ValueError("Debe existir un ID de procedencia por cada candidato de altura")
    if any(not isinstance(item, str) or not item.strip() for item in notehead_candidate_ids):
        raise ValueError("Los IDs de cabezas deben ser textos no vacíos")
    if len(set(notehead_candidate_ids)) != len(notehead_candidate_ids):
        raise ValueError("Los IDs de cabezas deben ser únicos")

    output: list[ScoreEventCandidate] = []
    seen_event_ids: set[str] = set()
    seen_heads: set[int] = set()

    for group in rhythmic_groups:
        event_id = getattr(group, "event_id", None)
        if not isinstance(event_id, str) or not event_id.strip() or event_id in seen_event_ids:
            raise ValueError("Cada grupo debe tener un event_id único y no vacío")
        seen_event_ids.add(event_id)

        event_type = getattr(group, "event_type", "note")
        if event_type not in {"note", "rest"}:
            raise ValueError(f"{event_id}: event_type debe ser 'note' o 'rest'")
        indices = tuple(getattr(group, "notehead_indices", ()))
        if (event_type == "note" and not indices) or len(set(indices)) != len(indices):
            raise ValueError(f"{event_id}: notehead_indices debe ser no vacío para notas y sin duplicados")
        if event_type == "rest" and indices:
            raise ValueError(f"{event_id}: un silencio no puede apropiarse de cabezas de nota")
        if any(not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= len(pitch_candidates) for index in indices):
            raise ValueError(f"{event_id}: índice de cabeza fuera del rango de candidatos")
        if any(index in seen_heads for index in indices):
            raise ValueError("Una cabeza no puede pertenecer a más de un evento fusionado")
        seen_heads.update(indices)

        staff_index = getattr(group, "staff_index", None)
        selected = [pitch_candidates[index] for index in indices]
        if any(getattr(item, "staff_index", None) != staff_index for item in selected):
            raise ValueError(f"{event_id}: grupo y altura pertenecen a pentagramas distintos")

        payloads = tuple(_pitch_payload(item) for item in selected)
        pitch_resolved = event_type == "rest" or bool(selected) and all(
            getattr(item, "status", None) == "resolved_from_supplied_clef"
            and getattr(item, "pitch", None) is not None
            for item in selected
        )
        voice_id = getattr(group, "voice_id_candidate", None)
        duration_name = getattr(group, "duration_candidate", "unknown")
        duration = getattr(group, "duration_quarters_candidate", None)
        group_status = getattr(group, "status", "ambiguous")
        warnings = list(getattr(group, "warnings", ()))

        allowed_statuses = {"single_rest_candidate"} if event_type == "rest" else {"single_note_candidate", "proposed_chord"}
        if group_status not in allowed_statuses:
            warnings.append("El evento rítmico no está resuelto; se conserva como candidato ambiguo.")
        if event_type == "note" and not pitch_resolved:
            warnings.append("Una o más alturas siguen sin resolver por falta de contexto notacional confirmado.")
        if voice_id is None:
            warnings.append("No existe asignación explícita de voz para este evento.")
        if duration is None:
            warnings.append("La duración no está resuelta; no se asigna posición temporal.")

        ready = (
            group_status in allowed_statuses
            and pitch_resolved
            and isinstance(voice_id, str) and bool(voice_id.strip())
            and duration is not None
        )
        output.append(ScoreEventCandidate(
            event_id=event_id,
            staff_index=staff_index,
            notehead_candidate_ids=tuple(notehead_candidate_ids[index] for index in indices),
            pitch_candidates=payloads,
            voice_id_candidate=voice_id,
            duration_candidate=duration_name,
            duration_quarters_candidate=duration,
            status="ready_for_review" if ready else "incomplete_candidate",
            warnings=tuple(dict.fromkeys(warnings)),
            event_type=event_type,
        ))

    return tuple(output)
