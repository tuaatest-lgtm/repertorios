"""Adaptación conservadora de etiquetas PDF a evidencias de identidad.

Solo convierte asociaciones geométricas explícitas en evidencia visual.
No crea partes, voces ni asignaciones automáticas.
"""
from __future__ import annotations

from .printed_labels import PrintedLabelCandidate
from .score_structure import ScoreStructure
from .staff_identity import StaffIdentityEvidence


def build_printed_label_evidence(
    candidates: list[PrintedLabelCandidate],
    structure: ScoreStructure,
) -> tuple[StaffIdentityEvidence, ...]:
    """Convierte etiquetas asociadas a evidencia visual de un pentagrama.

    Se omiten las etiquetas ambiguas o no asignadas. La función exige que la
    página coincida y que el índice detectado identifique un único pentagrama.
    Las evidencias resultantes no modifican `staff_assignments`.
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
        if candidate.page_number != structure.page_number:
            raise ValueError("La etiqueta y la estructura deben pertenecer a la misma página")
        if candidate.association_status != "associated_candidate":
            continue
        if candidate.staff_index is None:
            raise ValueError("Una etiqueta asociada debe indicar staff_index")
        staff_id = by_detected_index.get(candidate.staff_index)
        if staff_id is None:
            raise ValueError("La etiqueta referencia un índice de pentagrama inexistente")
        if candidate.label_kind not in {"vocal", "instrument"}:
            raise ValueError("label_kind debe ser vocal o instrument")

        kind = (
            "printed_voice_label"
            if candidate.label_kind == "vocal"
            else "printed_part_label"
        )
        evidence.append(StaffIdentityEvidence(
            evidence_id=f"printed-label-p{candidate.page_number}-{candidate_index + 1}",
            staff_id=staff_id,
            kind=kind,
            description=(
                f"Etiqueta PDF reconocida: {candidate.text!r}; "
                "asociación geométrica candidata, pendiente de revisión humana."
            ),
            source="visual_candidate",
            confidence=candidate.confidence,
        ))
    return tuple(evidence)
