import pytest

from palermo_omr.identity_evidence import build_page_identity_evidence
from palermo_omr.printed_labels import PrintedLabelCandidate
from palermo_omr.score_structure import ScoreStaff, ScoreStructure
from palermo_omr.staff_grouping import StaffGroupingMarkCandidate
from palermo_omr.staff_identity import StaffIdentityReview
from palermo_omr.score_document import ScoreDocument


def structure():
    return ScoreStructure(
        page_number=1,
        staves=(
            ScoreStaff("staff-s", 1, 0),
            ScoreStaff("staff-a", 1, 1),
        ),
    )


def label(text="Soprano", kind="vocal", index=0, status="associated_candidate"):
    return PrintedLabelCandidate(
        page_number=1, text=text, normalized_text=text.upper(),
        label_kind=kind, bbox_pdf=(1.0, 2.0, 3.0, 4.0),
        staff_index=index if status == "associated_candidate" else None,
        association_status=status, vertical_distance_px=2.0,
        confidence=0.72, warning="Candidata",
    )


def brace(indices=(0, 1)):
    return StaffGroupingMarkCandidate(
        x=8.0, y_top=20, y_bottom=80, width_px=6,
        staff_indices=indices, vertical_coverage=0.9,
        kind="curly_brace_candidate", confidence=0.62,
        warning="Requiere revisión",
    )


def test_combines_printed_labels_and_grouping_marks_as_unconfirmed_evidence():
    score = structure()
    evidence = build_page_identity_evidence(
        score,
        printed_labels=[label(), label("Alto", index=1)],
        grouping_marks=[brace()],
    )
    assert [item.staff_id for item in evidence] == [
        "staff-s", "staff-a", "staff-s", "staff-a"
    ]
    assert [item.kind for item in evidence] == [
        "printed_voice_label", "printed_voice_label", "brace", "brace"
    ]
    assert all(item.source == "visual_candidate" for item in evidence)
    review = StaffIdentityReview(evidence=evidence)
    review.validate(ScoreDocument((score,)))
    assert score.staff_assignments == ()


def test_omits_ambiguous_labels_but_keeps_grouping_evidence():
    evidence = build_page_identity_evidence(
        structure(),
        printed_labels=[label(status="ambiguous")],
        grouping_marks=[brace()],
    )
    assert len(evidence) == 2
    assert all(item.kind == "brace" for item in evidence)


def test_empty_inputs_return_empty_evidence():
    assert build_page_identity_evidence(structure()) == ()


def test_rejects_page_mismatch_from_label_adapter():
    with pytest.raises(ValueError, match="misma página"):
        build_page_identity_evidence(
            structure(),
            printed_labels=[PrintedLabelCandidate(
                page_number=2, text="Soprano", normalized_text="SOPRANO",
                label_kind="vocal", bbox_pdf=(1, 2, 3, 4), staff_index=0,
                association_status="associated_candidate",
                vertical_distance_px=1.0, confidence=0.7, warning="",
            )],
        )


def test_rejects_invalid_grouping_reference():
    with pytest.raises(ValueError, match="inexistente"):
        build_page_identity_evidence(structure(), grouping_marks=[brace((0, 9))])
