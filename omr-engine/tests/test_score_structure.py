import pytest

from palermo_omr.score_structure import (
    MeasureRegion,
    ScorePart,
    ScoreStaff,
    ScoreStructure,
    ScoreSystem,
    ScoreVoice,
    StaffAssignment,
)


def _valid_structure():
    return ScoreStructure(
        page_number=1,
        systems=(ScoreSystem("sys-1", 1, ("staff-upper", "staff-lower")),),
        staves=(
            ScoreStaff("staff-upper", 1, 0),
            ScoreStaff("staff-lower", 1, 1),
        ),
        parts=(ScorePart("piano", "Piano", "instrument"),),
        voices=(ScoreVoice("piano-flow", "piano", "Flujo instrumental"),),
        staff_assignments=(
            StaffAssignment("staff-upper", "confirmed", "piano", ("piano-flow",), "Llave y brace revisados"),
            StaffAssignment("staff-lower", "confirmed", "piano", ("piano-flow",), "Mismo gran pentagrama"),
        ),
        measure_regions=(
            MeasureRegion("m1-upper", "sys-1", "staff-upper", 1, 10, 100),
            MeasureRegion("m1-lower", "sys-1", "staff-lower", 1, 10, 100),
        ),
    )


def test_valid_structure_allows_two_staves_for_one_instrumental_flow():
    structure = _valid_structure()
    structure.validate()
    data = structure.to_dict()
    assert data["staff_assignments"][0]["part_id"] == "piano"
    assert data["staff_assignments"][1]["voice_ids"] == ("piano-flow",)


def test_unassigned_staff_does_not_guess_part_or_voice():
    structure = ScoreStructure(
        page_number=1,
        systems=(ScoreSystem("sys", 1, ("s1",)),),
        staves=(ScoreStaff("s1", 1, 0),),
        staff_assignments=(StaffAssignment("s1", "unassigned"),),
    )
    structure.validate()


def test_ambiguous_staff_cannot_claim_part_or_voice():
    structure = ScoreStructure(
        page_number=1,
        systems=(ScoreSystem("sys", 1, ("s1",)),),
        staves=(ScoreStaff("s1", 1, 0),),
        parts=(ScorePart("choir", "Coro", "vocal"),),
        staff_assignments=(StaffAssignment("s1", "ambiguous", "choir"),),
    )
    with pytest.raises(ValueError, match="sin resolver"):
        structure.validate()


def test_rejects_voice_from_a_different_part():
    structure = _valid_structure()
    broken = ScoreStructure(
        page_number=1,
        systems=structure.systems,
        staves=structure.staves,
        parts=(ScorePart("piano", "Piano", "instrument"), ScorePart("choir", "Coro", "vocal")),
        voices=(ScoreVoice("soprano", "choir", "Soprano"),),
        staff_assignments=(StaffAssignment("staff-upper", "confirmed", "piano", ("soprano",)),),
    )
    with pytest.raises(ValueError, match="pertenecer a la parte"):
        broken.validate()


def test_rejects_measure_region_outside_its_system():
    structure = ScoreStructure(
        page_number=1,
        systems=(ScoreSystem("sys", 1, ("s1",)),),
        staves=(ScoreStaff("s1", 1, 0), ScoreStaff("s2", 1, 1)),
        measure_regions=(MeasureRegion("m1", "sys", "s2", 1, 0, 100),),
    )
    with pytest.raises(ValueError, match="no pertenece al sistema"):
        structure.validate()


def test_rejects_non_positive_measure_width():
    structure = ScoreStructure(
        page_number=1,
        systems=(ScoreSystem("sys", 1, ("s1",)),),
        staves=(ScoreStaff("s1", 1, 0),),
        measure_regions=(MeasureRegion("m1", "sys", "s1", 1, 50, 50),),
    )
    with pytest.raises(ValueError, match="x_end"):
        structure.validate()


def test_rejects_duplicate_staff_membership_across_systems():
    structure = ScoreStructure(
        page_number=1,
        systems=(ScoreSystem("sys-a", 1, ("s1",)), ScoreSystem("sys-b", 1, ("s1",))),
        staves=(ScoreStaff("s1", 1, 0),),
    )
    with pytest.raises(ValueError, match="dos sistemas"):
        structure.validate()
