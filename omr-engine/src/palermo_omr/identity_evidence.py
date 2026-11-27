"""Unifica evidencia visual de etiquetas impresas y marcas de agrupación.

Este módulo reúne observaciones ya extraídas en una página. No interpreta la
identidad musical ni crea propuestas o asignaciones de partes y voces.
"""
from __future__ import annotations

from .printed_label_adapter import build_printed_label_evidence
from .printed_labels import PrintedLabelCandidate
from .score_structure import ScoreStructure
from .staff_grouping import StaffGroupingMarkCandidate
from .staff_grouping_adapter import build_staff_grouping_evidence
from .staff_identity import StaffIdentityEvidence


def build_page_identity_evidence(
    structure: ScoreStructure,
    *,
    printed_labels: list[PrintedLabelCandidate] | None = None,
    grouping_marks: list[StaffGroupingMarkCandidate] | None = None,
) -> tuple[StaffIdentityEvidence, ...]:
    """Combina evidencias de etiquetas y agrupaciones para una sola página.

    Las etiquetas ambiguas/no asignadas siguen excluidas por el adaptador
    específico. Las marcas de agrupación se enlazan a cada pentagrama afectado.
    Se rechazan identificadores duplicados y no se muta la estructura.
    """
    label_evidence = build_printed_label_evidence(
        printed_labels or [], structure
    )
    grouping_evidence = build_staff_grouping_evidence(
        grouping_marks or [], structure
    )
    combined = (*label_evidence, *grouping_evidence)
    evidence_ids = [item.evidence_id for item in combined]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("Los identificadores de evidencia combinada deben ser únicos")
    return tuple(combined)
