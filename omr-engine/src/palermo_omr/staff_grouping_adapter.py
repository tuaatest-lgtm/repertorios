"""Adaptación de marcas de agrupación a evidencia de identidad revisable.

Una marca que abarca varios pentagramas se registra como evidencia separada
para cada pentagrama referenciado. No crea partes, voces ni asignaciones.
"""
from __future__ import annotations

from .score_structure import ScoreStructure
from .staff_grouping import StaffGroupingMarkCandidate
from .staff_identity import StaffIdentityEvidence


_KIND_MAP = {
    "curly_brace_candidate": "brace",
    "square_bracket_candidate": "bracket",
    "vertical_grouping_mark_candidate": "layout",
}


def build_staff_grouping_evidence(
    candidates: list[StaffGroupingMarkCandidate],
    structure: ScoreStructure,
) -> tuple[StaffIdentityEvidence, ...]:
    """Convierte candidatos válidos en evidencia visual pendiente de revisión.

    Los índices de candidato se resuelven contra detected_staff_index de la
    estructura. Una marca que agrupa dos pentagramas produce dos evidencias
    enlazables, una por pentagrama. No se infiere el tipo de parte.
    """
    structure.validate()
    by_detected_index = {}
    for staff in structure.staves:
        if staff.detected_staff_index in by_detected_index:
            raise ValueError(
                "detected_staff_index debe ser único dentro de la estructura"
            )
        by_detected_index[staff.detected_staff_index] = staff.staff_id

    evidence = []
    for candidate_index, candidate in enumerate(candidates):
        if not candidate.staff_indices:
            raise ValueError("Una marca de agrupación debe referenciar pentagramas")
        if len(set(candidate.staff_indices)) != len(candidate.staff_indices):
            raise ValueError("Una marca de agrupación no puede repetir pentagramas")
        kind = _KIND_MAP.get(candidate.kind)
        if kind is None:
            raise ValueError(f"Tipo de marca de agrupación no válido: {candidate.kind}")
        for staff_index in candidate.staff_indices:
            staff_id = by_detected_index.get(staff_index)
            if staff_id is None:
                raise ValueError("La marca referencia un índice de pentagrama inexistente")
            evidence.append(StaffIdentityEvidence(
                evidence_id=(
                    f"staff-grouping-p{structure.page_number}-"
                    f"c{candidate_index + 1}-s{staff_index + 1}"
                ),
                staff_id=staff_id,
                kind=kind,
                description=(
                    f"Marca gráfica candidata ({candidate.kind}) en la página "
                    f"{structure.page_number}; evidencia visual pendiente de "
                    "revisión humana. No identifica instrumento, parte ni voz."
                ),
                source="visual_candidate",
                confidence=candidate.confidence,
            ))
    return tuple(evidence)
