import pytest

from palermo_omr.score_document import ScoreDocument
from palermo_omr.score_structure import ScoreStaff, ScoreStructure
from palermo_omr.staff_grouping import StaffGroupingMarkCandidate
from palermo_omr.staff_grouping_adapter import build_staff_grouping_evidence
from palermo_omr.staff_identity import StaffIdentityReview


def structure():
    return ScoreStructure(
        page_number=2,
        staves=(
            ScoreStaff("p2-staff-1", 2, 0),
            ScoreStaff("p2-staff-2", 2, 1),
        ),
    )


def candidate(kind="curly_brace_candidate", indices=(0, 1)):
    return StaffGroupingMarkCandidate(
        x=12.0, y_top=30, y_bottom=90, width_px=7,
        staff_indices=indices, vertical_coverage=0.9,
        kind=kind, confidence=0.62, warning="Revisión requerida",
    )


def test_curly_brace_becomes_visual_evidence_for_each_staff_only():
    score = structure()
    evidence = build_staff_grouping_evidence([candidate()], score)

    assert [item.staff_id for item in evidence] == ["p2-staff-1", "p2-staff-2"]
    assert [item.kind for item in evidence] == ["brace", "brace"]
    assert all(item.source == "visual_candidate" for item in evidence)
    assert all(item.confidence == 0.62 for item in evidence)
    review = StaffIdentityReview(evidence=evidence)
    review.validate(ScoreDocument((score,)))
    assert score.staff_assignments == ()


@pytest.mark.parametrize(
    ("mark_kind", "expected"),
    [
        ("square_bracket_candidate", "bracket"),
        ("vertical_grouping_mark_candidate", "layout"),
    ],
)
def test_maps_other_grouping_marks_to_conservative_evidence(mark_kind, expected):
    evidence = build_staff_grouping_evidence(
        [candidate(kind=mark_kind, indices=(0,))], structure()
    )
    assert len(evidence) == 1
    assert evidence[0].kind == expected


def test_rejects_missing_duplicate_or_unknown_staff_references():
    with pytest.raises(ValueError, match="inexistente"):
        build_staff_grouping_evidence([candidate(indices=(0, 8))], structure())
    with pytest.raises(ValueError, match="repetir"):
        build_staff_grouping_evidence([candidate(indices=(0, 0))], structure())
    with pytest.raises(ValueError, match="debe referenciar"):
        build_staff_grouping_evidence([candidate(indices=())], structure())


def test_rejects_unknown_mark_kind_and_duplicate_structure_indices():
    with pytest.raises(ValueError, match="Tipo de marca"):
        build_staff_grouping_evidence(
            [candidate(kind="unknown")], structure()
        )
    duplicate = ScoreStructure(
        page_number=2,
        staves=(
            ScoreStaff("a", 2, 0),
            ScoreStaff("b", 2, 0),
        ),
    )
    with pytest.raises(ValueError, match="debe ser único"):
        build_staff_grouping_evidence([candidate(indices=(0,))], duplicate)
