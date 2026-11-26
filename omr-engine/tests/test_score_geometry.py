import pytest
from palermo_omr.imaging import StaffCandidate
from palermo_omr.measure_layout import MeasureSpanCandidate, StaffSystemCandidate
from palermo_omr.score_geometry import build_geometric_score_structure


def staff():
    return StaffCandidate([10, 20, 30, 40, 50], 10.0, 0.95)


def system(index, members):
    return StaffSystemCandidate(index, members, 10, 50, 0.65, "candidate")


def span(staff_index, measure_index=1, start=20, end=100):
    return MeasureSpanCandidate(staff_index, measure_index, start, end, end-start, True, True, 0.6, "candidate")


def test_builds_page_systems_and_regions_without_guessing_musical_roles():
    result = build_geometric_score_structure(
        2, [staff(), staff(), staff()], [system(0, [0, 1]), system(1, [2])],
        [span(0), span(1), span(2)],
    )
    result.validate()
    assert [s.staff_ids for s in result.systems] == [
        ("p2-staff-1", "p2-staff-2"), ("p2-staff-3",)
    ]
    assert len(result.measure_regions) == 3
    assert all(a.status == "unassigned" for a in result.staff_assignments)
    assert result.parts == () and result.voices == ()


def test_keeps_staff_without_system_but_does_not_invent_membership():
    result = build_geometric_score_structure(1, [staff(), staff()], [system(0, [0])], [span(1)])
    assert len(result.staves) == 2
    assert result.measure_regions == ()


def test_rejects_unknown_staff_index_in_system():
    with pytest.raises(ValueError, match="inexistente"):
        build_geometric_score_structure(1, [staff()], [system(0, [2])], [])


def test_rejects_duplicate_system_membership():
    with pytest.raises(ValueError, match="dos sistemas"):
        build_geometric_score_structure(1, [staff()], [system(0, [0]), system(1, [0])], [])


def test_rejects_unknown_staff_index_in_measure_span():
    with pytest.raises(ValueError, match="inexistente"):
        build_geometric_score_structure(1, [staff()], [system(0, [0])], [span(3)])


def test_rejects_invalid_page_number():
    with pytest.raises(ValueError, match="page_number"):
        build_geometric_score_structure(0, [staff()], [system(0, [0])], [])
