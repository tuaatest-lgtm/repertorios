import pytest

from palermo_omr.score_document import ScoreDocument
from palermo_omr.score_structure import ScoreStaff, ScoreStructure
from palermo_omr.staff_identity import (
    StaffIdentityEvidence, StaffIdentityProposal, StaffIdentityReview,
)


def document():
    return ScoreDocument((ScoreStructure(
        page_number=1,
        staves=(ScoreStaff("p1-staff-1", 1, 0),),
    ),))


def test_proposal_requires_evidence_and_does_not_confirm_identity():
    review = StaffIdentityReview(
        evidence=(StaffIdentityEvidence(
            "e1", "p1-staff-1", "printed_part_label",
            "Texto visible: Piano", confidence=0.8,
        ),),
        proposals=(StaffIdentityProposal(
            "proposal-1", "p1-staff-1",
            proposed_part_id="piano", proposed_part_name="Piano",
            proposed_part_kind="instrument", evidence_ids=("e1",),
        ),),
    )
    review.validate(document())
    assert review.proposals[0].status == "proposed"
    assert review.proposals[0].reviewer_confirmed is False


def test_confirmed_identity_requires_human_review_evidence():
    review = StaffIdentityReview(
        evidence=(StaffIdentityEvidence(
            "e1", "p1-staff-1", "printed_part_label",
            "Etiqueta Piano",
        ),),
        proposals=(StaffIdentityProposal(
            "proposal-1", "p1-staff-1", "piano", "Piano",
            "instrument", status="confirmed", evidence_ids=("e1",),
            reviewer_confirmed=True,
        ),),
    )
    with pytest.raises(ValueError, match="revisión humana"):
        review.validate(document())


def test_human_review_can_confirm_part_and_voice_label():
    review = StaffIdentityReview(
        evidence=(
            StaffIdentityEvidence(
                "e1", "p1-staff-1", "printed_voice_label",
                "Etiqueta visible: Soprano",
            ),
            StaffIdentityEvidence(
                "e2", "p1-staff-1", "human_review",
                "Revisor verificó la etiqueta y la clave", "human_review",
            ),
        ),
        proposals=(StaffIdentityProposal(
            "proposal-1", "p1-staff-1", "choir", "Coro",
            "vocal", "Soprano", "confirmed", ("e1", "e2"), True,
        ),),
    )
    review.validate(document())


def test_rejects_evidence_for_unknown_staff_or_invalid_confidence():
    with pytest.raises(ValueError, match="inexistente"):
        StaffIdentityReview(evidence=(
            StaffIdentityEvidence("e1", "missing", "brace", "Llave"),
        )).validate(document())
    with pytest.raises(ValueError, match="entre 0 y 1"):
        StaffIdentityReview(evidence=(
            StaffIdentityEvidence(
                "e1", "p1-staff-1", "clef_symbol", "Clave", confidence=1.2,
            ),
        )).validate(document())


def test_rejects_proposal_linking_evidence_from_another_staff():
    two_staff_doc = ScoreDocument((ScoreStructure(
        page_number=1,
        staves=(
            ScoreStaff("p1-staff-1", 1, 0),
            ScoreStaff("p1-staff-2", 1, 1),
        ),
    ),))
    review = StaffIdentityReview(
        evidence=(StaffIdentityEvidence(
            "e1", "p1-staff-2", "bracket", "Corchete lateral",
        ),),
        proposals=(StaffIdentityProposal(
            "p1", "p1-staff-1", evidence_ids=("e1",),
        ),),
    )
    with pytest.raises(ValueError, match="mismo pentagrama"):
        review.validate(two_staff_doc)


def test_rejects_unknown_evidence_kind_and_ambiguous_confirmed_flag():
    bad_kind = StaffIdentityReview(evidence=(
        StaffIdentityEvidence("e1", "p1-staff-1", "guess", "Suposición"),
    ))
    with pytest.raises(ValueError, match="Tipo de evidencia"):
        bad_kind.validate(document())
    ambiguous = StaffIdentityReview(proposals=(
        StaffIdentityProposal(
            "p1", "p1-staff-1", status="ambiguous", reviewer_confirmed=True,
        ),
    ))
    with pytest.raises(ValueError, match="ambigua"):
        ambiguous.validate(document())
