import pytest

from palermo_omr.score_document import (
    GlobalMeasureNumber,
    ScoreDocument,
    StaffContinuation,
)
from palermo_omr.score_structure import (
    MeasureRegion, ScoreStaff, ScoreStructure, ScoreSystem,
)


def page(number, prefix):
    staff_id = f"{prefix}-staff"
    system_id = f"{prefix}-system"
    region_id = f"{prefix}-measure"
    return ScoreStructure(
        page_number=number,
        systems=(ScoreSystem(system_id, number, (staff_id,)),),
        staves=(ScoreStaff(staff_id, number, 0),),
        measure_regions=(MeasureRegion(region_id, system_id, staff_id, 1, 0, 100),),
    )


def test_orders_pages_and_systems_without_reordering_source_objects():
    document = ScoreDocument((page(1, "p1"), page(2, "p2")))
    assert document.ordered_system_refs == (
        (1, "p1-system"), (2, "p2-system")
    )


def test_rejects_pages_out_of_order_or_repeated():
    with pytest.raises(ValueError, match="ordenadas"):
        ScoreDocument((page(2, "p2"), page(1, "p1"))).validate()
    with pytest.raises(ValueError, match="repetir números"):
        ScoreDocument((page(1, "a"), page(1, "b"))).validate()


def test_continuity_is_explicit_and_does_not_assign_part_or_voice():
    first, second = page(1, "p1"), page(2, "p2")
    link = StaffContinuation("p1-staff", "p2-staff", "proposed", "Altura y formato similares")
    document = ScoreDocument((first, second), (link,))
    document.validate()
    assert first.staff_assignments == ()
    assert second.staff_assignments == ()


def test_confirmed_continuity_requires_evidence_and_advances_page():
    with pytest.raises(ValueError, match="evidencia"):
        ScoreDocument(
            (page(1, "p1"), page(2, "p2")),
            (StaffContinuation("p1-staff", "p2-staff", "confirmed"),),
        ).validate()
    with pytest.raises(ValueError, match="posterior"):
        ScoreDocument(
            (page(1, "p1"), page(2, "p2")),
            (StaffContinuation("p2-staff", "p1-staff", "proposed"),),
        ).validate()


def test_rejects_missing_or_duplicate_continuity_references():
    missing = StaffContinuation("absent", "p2-staff", "proposed")
    with pytest.raises(ValueError, match="inexistente"):
        ScoreDocument((page(1, "p1"), page(2, "p2")), (missing,)).validate()
    repeated = StaffContinuation("p1-staff", "p2-staff", "proposed")
    with pytest.raises(ValueError, match="repetir una continuidad"):
        ScoreDocument(
            (page(1, "p1"), page(2, "p2")), (repeated, repeated)
        ).validate()


def test_global_measure_number_is_optional_and_explicit():
    document = ScoreDocument(
        (page(1, "p1"), page(2, "p2")),
        global_measure_numbers=(
            GlobalMeasureNumber("p1-measure", 12),
            GlobalMeasureNumber("p2-measure", 13),
        ),
    )
    document.validate()
    assert document.to_dict()["global_measure_numbers"][1]["global_measure_number"] == 13


def test_rejects_unknown_or_repeated_global_measure_region():
    unknown = GlobalMeasureNumber("not-a-region", 1)
    with pytest.raises(ValueError, match="región inexistente"):
        ScoreDocument((page(1, "p1"),), global_measure_numbers=(unknown,)).validate()
    duplicate = GlobalMeasureNumber("p1-measure", 1)
    with pytest.raises(ValueError, match="dos números globales"):
        ScoreDocument((page(1, "p1"),), global_measure_numbers=(duplicate, duplicate)).validate()


def test_rejects_duplicate_staff_ids_across_pages():
    one = page(1, "same")
    two = ScoreStructure(
        page_number=2,
        systems=(ScoreSystem("other-system", 2, ("same-staff",)),),
        staves=(ScoreStaff("same-staff", 2, 0),),
    )
    with pytest.raises(ValueError, match="únicos en el documento"):
        ScoreDocument((one, two)).validate()
