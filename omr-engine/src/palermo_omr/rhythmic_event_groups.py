"""Agrupación conservadora de cabezas en ataques rítmicos candidatos.

La coordenada x solo propone qué cabezas podrían compartir ataque; nunca se
convierte en tiempo. Ningún grupo se considera acorde confirmado ni se asigna
automáticamente a una voz.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from collections.abc import Mapping, Sequence

from .duration_math import BASE_DURATIONS
from .imaging import StaffCandidate
from .rhythm import RhythmCandidate
from .rhythm_interpretation import RhythmicInterpretationCandidate
from .symbols import NoteheadCandidate


@dataclass(frozen=True)
class RhythmicEventGroupCandidate:
    event_id: str
    staff_index: int
    notehead_indices: tuple[int, ...]
    center_x: float
    stem_direction_candidate: str
    duration_candidate: str
    duration_quarters_candidate: Fraction | None
    voice_id_candidate: str | None
    status: str
    confidence: float
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        result = asdict(self)
        if self.duration_quarters_candidate is not None:
            result["duration_quarters_candidate"] = str(self.duration_quarters_candidate)
        return result


def build_rhythmic_event_group_candidates(
    staves: Sequence[StaffCandidate],
    noteheads: Sequence[NoteheadCandidate],
    rhythms: Sequence[RhythmCandidate],
    interpretations: Sequence[RhythmicInterpretationCandidate],
    *,
    staff_voice_ids: Mapping[int, str] | None = None,
    max_chord_spread_spacing: float = 1.10,
) -> tuple[RhythmicEventGroupCandidate, ...]:
    """Agrupa posibles cabezas de un ataque dentro del mismo pentagrama.

    Se exige proximidad horizontal normalizada y coherencia de dirección de
    plica. Plicas opuestas, duraciones incompatibles o evidencia incompleta
    producen un grupo ambiguo, no una separación automática en voces.
    staff_voice_ids solo debe contener asignaciones explícitas ya revisadas.
    """
    if len(noteheads) != len(rhythms) or len(noteheads) != len(interpretations):
        raise ValueError("Debe existir ritmo e interpretación por cada cabeza")
    if max_chord_spread_spacing <= 0:
        raise ValueError("max_chord_spread_spacing debe ser positivo")

    for index, (head, rhythm, interpretation) in enumerate(
        zip(noteheads, rhythms, interpretations)
    ):
        if head.staff_index != rhythm.staff_index:
            raise ValueError(f"La cabeza y el ritmo {index} pertenecen a pentagramas distintos")
        if head.staff_index != interpretation.staff_index:
            raise ValueError(f"La cabeza y la interpretación {index} pertenecen a pentagramas distintos")
        if interpretation.notehead_index != index:
            raise ValueError("Los índices de interpretación deben corresponder al orden de cabezas")
        if not 0 <= head.staff_index < len(staves):
            raise ValueError("Una cabeza referencia un pentagrama inexistente")

    assignments = dict(staff_voice_ids or {})
    for staff_index, voice_id in assignments.items():
        if not isinstance(staff_index, int) or not 0 <= staff_index < len(staves):
            raise ValueError("staff_voice_ids contiene un índice de pentagrama inválido")
        if not isinstance(voice_id, str) or not voice_id.strip():
            raise ValueError("Cada voice_id explícito debe ser texto no vacío")

    by_staff: dict[int, list[int]] = {}
    for index, head in enumerate(noteheads):
        by_staff.setdefault(head.staff_index, []).append(index)

    groups: list[RhythmicEventGroupCandidate] = []
    for staff_index, indices in sorted(by_staff.items()):
        spacing = float(staves[staff_index].spacing_px)
        if spacing <= 1:
            raise ValueError("El espaciado del pentagrama debe ser mayor que 1 píxel")
        ordered = sorted(indices, key=lambda idx: (noteheads[idx].center_x, noteheads[idx].center_y))
        clusters: list[list[int]] = []
        for index in ordered:
            if not clusters:
                clusters.append([index])
                continue
            current = clusters[-1]
            left = noteheads[current[0]].center_x
            if noteheads[index].center_x - left <= spacing * max_chord_spread_spacing:
                current.append(index)
            else:
                clusters.append([index])

        for ordinal, cluster in enumerate(clusters, start=1):
            directions = {rhythms[index].stem_direction for index in cluster}
            durations = {interpretations[index].duration_candidate for index in cluster}
            stem_direction = next(iter(directions)) if len(directions) == 1 else "mixed"
            duration = next(iter(durations)) if len(durations) == 1 else "unknown"
            duration_quarters = (
                BASE_DURATIONS[duration]
                if duration in BASE_DURATIONS
                and all(interpretations[index].status not in {"ambiguous", "unclassified", "insufficient_note_evidence"} for index in cluster)
                else None
            )
            warnings: list[str] = []
            status = "single_note_candidate" if len(cluster) == 1 else "proposed_chord"
            confidence = min(noteheads[index].confidence for index in cluster)

            if len(cluster) > 1 and len(directions) != 1:
                status = "ambiguous"
                duration = "unknown"
                duration_quarters = None
                warnings.append(
                    "El grupo contiene direcciones de plica distintas; podría mezclar voces "
                    "independientes en un mismo pentagrama."
                )
            elif "none" in directions:
                status = "ambiguous" if len(cluster) > 1 else "single_note_candidate"
                if len(cluster) > 1:
                    duration = "unknown"
                    duration_quarters = None
                warnings.append("No hay dirección de plica suficiente para resolver el ataque.")
            if len(durations) > 1:
                status = "ambiguous"
                duration = "unknown"
                duration_quarters = None
                warnings.append("Las cabezas del posible acorde tienen duraciones candidatas incompatibles.")
            elif duration_quarters is None:
                warnings.append("La duración no está suficientemente clasificada; no se asigna tiempo.")
            if len(cluster) > 1:
                warnings.append(
                    "Acorde geométrico propuesto por alineación horizontal; requiere confirmación visual."
                )
                confidence = min(confidence, 0.68)
            else:
                warnings.append("Nota individual candidata; su ataque y figura aún no están confirmados.")

            voice_id = assignments.get(staff_index)
            if voice_id is None:
                warnings.append("El pentagrama no tiene una voz asignada explícitamente.")
            groups.append(RhythmicEventGroupCandidate(
                event_id=f"staff-{staff_index + 1}-event-{ordinal}",
                staff_index=staff_index,
                notehead_indices=tuple(cluster),
                center_x=round(
                    sum(noteheads[index].center_x for index in cluster) / len(cluster), 3
                ),
                stem_direction_candidate=stem_direction,
                duration_candidate=duration,
                duration_quarters_candidate=duration_quarters,
                voice_id_candidate=voice_id,
                status=status,
                confidence=round(max(0.0, min(1.0, confidence)), 3),
                warnings=tuple(dict.fromkeys(warnings)),
            ))

    return tuple(sorted(groups, key=lambda group: (group.staff_index, group.center_x, group.event_id)))
