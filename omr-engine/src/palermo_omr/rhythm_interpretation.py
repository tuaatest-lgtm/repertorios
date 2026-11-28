"""Interpretación rítmica conservadora a partir de grupos de barras candidatos.

Relaciona evidencia geométrica con una duración candidata, sin producir
eventos musicales confirmados ni resolver compases o voces.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .beam_groups import BeamGroupCandidate
from .rhythm import RhythmCandidate


_BEAM_DURATIONS = {
    1: "eighth",
    2: "sixteenth",
    3: "thirty_second",
    4: "sixty_fourth",
}


@dataclass(frozen=True)
class RhythmicInterpretationCandidate:
    notehead_index: int
    staff_index: int
    duration_candidate: str
    beam_count_candidate: int
    beam_group_indices: tuple[int, ...]
    confidence: float
    status: str
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def interpret_rhythm_from_beam_groups(
    rhythms: list[RhythmCandidate],
    beam_groups: list[BeamGroupCandidate],
) -> list[RhythmicInterpretationCandidate]:
    """Produce una duración candidata por cabeza, usando evidencia de grupos.

    Las barras compartidas tienen prioridad sobre el recuento local por cabeza.
    Si una cabeza participa en segmentos con niveles de barra distintos, se
    conserva el máximo nivel local observado. Las notas sin grupo conservan
    solo la hipótesis local previa.
    """
    memberships: dict[int, list[tuple[int, BeamGroupCandidate]]] = {}
    for group_index, group in enumerate(beam_groups):
        if group.beam_count_candidate not in _BEAM_DURATIONS:
            continue
        for notehead_index in group.notehead_indices:
            if not 0 <= notehead_index < len(rhythms):
                raise ValueError("Un grupo referencia un índice de cabeza inexistente")
            if rhythms[notehead_index].staff_index != group.staff_index:
                raise ValueError("El grupo y la cabeza pertenecen a pentagramas distintos")
            memberships.setdefault(notehead_index, []).append((group_index, group))

    results = []
    for index, rhythm in enumerate(rhythms):
        linked = memberships.get(index, [])
        warnings = list(rhythm.warnings)
        group_indices = tuple(item[0] for item in linked)

        if linked:
            counts = {item[1].beam_count_candidate for item in linked}
            if rhythm.notehead_fill != "filled" or rhythm.stem_direction == "none":
                duration = "unknown"
                beam_count = max(counts)
                confidence = 0.0
                status = "insufficient_note_evidence"
                warnings.append("Hay barras candidatas, pero falta una cabeza rellena y una plica compatibles.")
            else:
                # Una misma nota puede tener una barra completa hacia un lado
                # y una barra secundaria parcial hacia el otro. El valor de la
                # figura depende del máximo nivel de barra que alcanza su plica,
                # no de exigir que todos los tramos vecinos tengan igual recuento.
                beam_count = max(counts)
                duration = _BEAM_DURATIONS[beam_count]
                if len(counts) > 1:
                    warnings.append(
                        "La nota participa en tramos con distintos niveles de barras; "
                        "se conserva el máximo nivel local observado."
                    )
                if any(item[1].connection_type_candidate == "partial" for item in linked):
                    confidence = min(0.55, max(0.25, rhythm.confidence * 0.55))
                    status = "candidate_from_partial_beam"
                    warnings.append(
                        "Haz parcial asociado a una sola plica; podría ser una bandera "
                        "u otro trazo, por lo que la duración es de confianza reducida."
                    )
                else:
                    confidence = min(0.78, max(0.35, rhythm.confidence * 0.75))
                    status = "candidate_from_shared_beam"
                    warnings.append("Duración sugerida por barras compartidas; requiere validación visual.")
        else:
            beam_count = rhythm.beam_count
            duration = rhythm.base_duration
            confidence = rhythm.confidence if duration != "unknown" else 0.0
            status = "local_candidate_only" if duration != "unknown" else "unclassified"
            if duration != "unknown":
                warnings.append("No hay grupo compartido asociado; se conserva la hipótesis local.")

        results.append(RhythmicInterpretationCandidate(
            notehead_index=index,
            staff_index=rhythm.staff_index,
            duration_candidate=duration,
            beam_count_candidate=beam_count,
            beam_group_indices=group_indices,
            confidence=round(confidence, 3),
            status=status,
            warnings=tuple(dict.fromkeys(warnings)),
        ))
    return results
