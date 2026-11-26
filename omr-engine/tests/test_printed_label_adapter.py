import pytest

from palermo_omr.printed_label_adapter import build_printed_label_evidence
from palermo_omr.printed_labels import PrintedLabelCandidate
from palermo_omr.score_structure import ScoreStaff, ScoreStructure
from palermo_omr.score_document import ScoreDocument
from palermo_omr.staff_identity import StaffIdentityReview


def candidate(page=1, text="Soprano", kind="vocal", index=0, status="associated_candidate"):
    return PrintedLabelCandidate(
        page_number=page,
        text=text,
        normalized_text=text.upper(),
        label_kind=kind,
        bbox_pdf=(10.0, 20.0, 50.0, 30.0),
        staff_index=index if status == "associated_candidate" else None,
        association_status=status,
        vertical_distance_px=2.0,
        confidence=0.72,
        warning="Candidata geométrica",
    )


def structure():
    return ScoreStructure(
        page_number=1,
        staves=(
            ScoreStaff("p1-staff-1", 1, 0),
            ScoreStaff("p1-staff-2", 1, 1),
        ),
    )


def test_converts_vocal_and_instrument_labels_to_visual_evidence_only():
    score = structure()
    evidence = build_printed_label_evidence(
        [candidate(), candidate(text="Piano", kind="instrument", index=1)],
        score,
    )

    assert [item.staff_id for item in evidence] == [
        "p1-staff-1", "p1-staff-2"
    ]
    assert [item.kind for item in evidence] == [
        "printed_voice_label", "printed_part_label"
    ]
    assert all(item.source == "visual_candidate" for item in evidence)
    assert all(item.confidence == 0.72 for item in evidence)
    assert all(item.staff_id for item in evidence)
    assert score.staff_assignments == ()


def test_omits_ambiguous_and_unassigned_labels():
    evidence = build_printed_label_evidence(
        [
            candidate(status="ambiguous"),
            candidate(status="unassigned"),
            candidate(text="Alto"),
        ],
        structure(),
    )
    assert len(evidence) == 1
    assert evidence[0].staff_id == "p1-staff-1"


def test_rejects_page_mismatch_and_unknown_staff_index():
    with pytest.raises(ValueError, match="misma página"):
        build_printed_label_evidence([candidate(page=2)], structure())
    with pytest.raises(ValueError, match="inexistente"):
        build_printed_label_evidence([candidate(index=8)], structure())


def test_rejects_duplicate_detected_staff_indices():
    duplicate = ScoreStructure(
        page_number=1,
        staves=(
            ScoreStaff("staff-a", 1, 0),
            ScoreStaff("staff-b", 1, 0),
        ),
    )
    with pytest.raises(ValueError, match="debe ser único"):
        build_printed_label_evidence([candidate()], duplicate)


def test_evidence_can_be_validated_without_creating_identity_proposal():
    score = structure()
    evidence = build_printed_label_evidence([candidate()], score)
    review = StaffIdentityReview(evidence=evidence)
    review.validate(ScoreDocument((score,)))
    assert review.proposals == ()
