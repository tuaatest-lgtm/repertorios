"""Evidencia y propuestas revisables para identificar pentagramas.

Este módulo no reconoce automáticamente nombres, claves ni funciones.
Separa observaciones visuales de propuestas y exige revisión humana explícita
antes de considerar confirmada una identidad musical.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .score_document import ScoreDocument

_EVIDENCE_KINDS = {
    "printed_part_label", "printed_voice_label", "clef_symbol",
    "brace", "bracket", "shared_barline", "instrumentation_text",
    "layout", "human_review",
}
_EVIDENCE_SOURCES = {"visual_candidate", "human_review"}
_PART_KINDS = {"instrument", "vocal", "unknown"}
_PROPOSAL_STATUSES = {"proposed", "confirmed", "ambiguous"}


@dataclass(frozen=True)
class StaffIdentityEvidence:
    evidence_id: str
    staff_id: str
    kind: str
    description: str
    source: str = "visual_candidate"
    confidence: float | None = None


@dataclass(frozen=True)
class StaffIdentityProposal:
    proposal_id: str
    staff_id: str
    proposed_part_id: str | None = None
    proposed_part_name: str | None = None
    proposed_part_kind: str = "unknown"
    proposed_voice_name: str | None = None
    status: str = "proposed"
    evidence_ids: tuple[str, ...] = ()
    reviewer_confirmed: bool = False


@dataclass(frozen=True)
class StaffIdentityReview:
    evidence: tuple[StaffIdentityEvidence, ...] = ()
    proposals: tuple[StaffIdentityProposal, ...] = ()

    def validate(self, document: ScoreDocument) -> None:
        document.validate()
        staff_ids = {
            staff.staff_id for page in document.pages for staff in page.staves
        }
        evidence_by_id = {}
        for item in self.evidence:
            if not item.evidence_id.strip() or item.evidence_id in evidence_by_id:
                raise ValueError("Los identificadores de evidencia deben ser únicos y no vacíos")
            if item.staff_id not in staff_ids:
                raise ValueError("La evidencia referencia un pentagrama inexistente")
            if item.kind not in _EVIDENCE_KINDS:
                raise ValueError(f"Tipo de evidencia no válido: {item.kind}")
            if item.source not in _EVIDENCE_SOURCES:
                raise ValueError(f"Origen de evidencia no válido: {item.source}")
            if not item.description.strip():
                raise ValueError("La evidencia debe describir lo observado")
            if item.confidence is not None and not 0 <= item.confidence <= 1:
                raise ValueError("La confianza debe estar entre 0 y 1")
            if item.source == "human_review" and item.kind != "human_review":
                raise ValueError("La revisión humana debe usar kind='human_review'")
            evidence_by_id[item.evidence_id] = item

        proposal_ids = set()
        for proposal in self.proposals:
            if not proposal.proposal_id.strip() or proposal.proposal_id in proposal_ids:
                raise ValueError("Los identificadores de propuesta deben ser únicos y no vacíos")
            proposal_ids.add(proposal.proposal_id)
            if proposal.staff_id not in staff_ids:
                raise ValueError("La propuesta referencia un pentagrama inexistente")
            if proposal.status not in _PROPOSAL_STATUSES:
                raise ValueError(f"Estado de propuesta no válido: {proposal.status}")
            if proposal.proposed_part_kind not in _PART_KINDS:
                raise ValueError("Tipo de parte propuesto no válido")
            if proposal.proposed_part_name is not None and not proposal.proposed_part_name.strip():
                raise ValueError("El nombre de parte propuesto no puede estar vacío")
            if proposal.proposed_voice_name is not None and not proposal.proposed_voice_name.strip():
                raise ValueError("El nombre de voz propuesto no puede estar vacío")
            if len(set(proposal.evidence_ids)) != len(proposal.evidence_ids):
                raise ValueError("Una propuesta no puede repetir evidencias")
            linked = []
            for evidence_id in proposal.evidence_ids:
                item = evidence_by_id.get(evidence_id)
                if item is None:
                    raise ValueError("Una propuesta referencia evidencia inexistente")
                if item.staff_id != proposal.staff_id:
                    raise ValueError("La evidencia debe pertenecer al mismo pentagrama")
                linked.append(item)
            if proposal.status == "proposed" and not linked:
                raise ValueError("Una propuesta debe incluir evidencia")
            if proposal.status == "confirmed":
                if not proposal.reviewer_confirmed:
                    raise ValueError("Una identidad confirmada requiere revisión humana explícita")
                if not any(item.source == "human_review" for item in linked):
                    raise ValueError("Una identidad confirmada requiere evidencia de revisión humana")
                if not proposal.proposed_part_id or not proposal.proposed_part_name:
                    raise ValueError("Una identidad confirmada debe identificar la parte")
            if proposal.status == "ambiguous" and proposal.reviewer_confirmed:
                raise ValueError("Una propuesta ambigua no puede marcarse como confirmada")

    def to_dict(self) -> dict:
        return asdict(self)
