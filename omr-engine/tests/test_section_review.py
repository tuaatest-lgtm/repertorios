import copy

import pytest

from palermo_omr.section_review import apply_section_range_decisions


def sample_package():
    return {
        "global_section_range_candidates": [
            {
                "section_range_id": "section-1",
                "start": {"musical_boundary_candidate": {"page_number": 1}},
                "end": {"musical_boundary_candidate": {"page_number": 2}},
                "review_status": "pending",
            },
            {
                "section_range_id": "section-2",
                "start": {"musical_boundary_candidate": {"page_number": 2}},
                "end": None,
                "review_status": "pending",
            },
            {
                "section_range_id": "section-3",
                "start": {"musical_boundary_candidate": {"page_number": 3}},
                "end": {"musical_boundary_candidate": {"page_number": 3}},
                "review_status": "pending",
            },
        ],
        "summary": {
            "global_section_range_candidate_count": 3,
            "pending_global_section_range_candidate_count": 3,
        },
    }


def test_apply_section_range_decision_requires_and_records_human_confirmation():
    package = sample_package()
    original = copy.deepcopy(package)
    updated = apply_section_range_decisions(
        package,
        [{"section_range_id": "section-1", "decision": "accepted", "notes": "Revisado"}],
        human_review_confirmed=True,
    )
    assert package == original
    assert updated["global_section_range_candidates"][0]["review_status"] == "accepted"
    assert updated["global_section_range_candidates"][0]["review_decision"] == {
        "decision": "accepted",
        "notes": "Revisado",
        "human_review_confirmed": True,
    }
    assert updated["summary"]["pending_global_section_range_candidate_count"] == 2
    assert updated["summary"]["accepted_global_section_range_candidate_count"] == 1


def test_apply_section_range_decisions_rejects_without_human_confirmation():
    with pytest.raises(ValueError, match="confirmación humana"):
        apply_section_range_decisions(
            sample_package(),
            [{"section_range_id": "section-1", "decision": "accepted"}],
            human_review_confirmed=False,
        )


def test_open_ended_range_requires_explicit_allowance():
    package = sample_package()
    decision = [{"section_range_id": "section-2", "decision": "accepted"}]
    with pytest.raises(ValueError, match="rango section-2 es abierto"):
        apply_section_range_decisions(
            package, decision, human_review_confirmed=True
        )
    updated = apply_section_range_decisions(
        package, decision, human_review_confirmed=True, allow_open_ended=True
    )
    assert updated["global_section_range_candidates"][1]["review_status"] == "accepted"


@pytest.mark.parametrize(
    ("decisions", "message"),
    [
        (
            [
                {"section_range_id": "section-1", "decision": "rejected"},
                {"section_range_id": "section-1", "decision": "accepted"},
            ],
            "decisiones duplicadas",
        ),
        ([{"section_range_id": "missing", "decision": "rejected"}], "No existe el rango"),
        ([{"section_range_id": "section-1", "decision": "pending"}], "decision debe ser"),
        ([{"section_range_id": "section-1", "decision": "rejected", "notes": 7}], "notes debe ser"),
    ],
)
def test_apply_section_range_decisions_rejects_invalid_decision_sets(decisions, message):
    with pytest.raises(ValueError, match=message):
        apply_section_range_decisions(
            sample_package(), decisions, human_review_confirmed=True
        )


def test_apply_section_range_decisions_does_not_overwrite_previous_decision():
    package = sample_package()
    package["global_section_range_candidates"][0]["review_status"] = "accepted"
    with pytest.raises(ValueError, match="decisión previa"):
        apply_section_range_decisions(
            package,
            [{"section_range_id": "section-1", "decision": "rejected"}],
            human_review_confirmed=True,
        )


def test_acceptance_requires_both_reviewable_boundaries():
    package = sample_package()
    package["global_section_range_candidates"][0]["end"] = None
    with pytest.raises(ValueError, match="rango section-1 es abierto"):
        apply_section_range_decisions(
            package,
            [{"section_range_id": "section-1", "decision": "accepted"}],
            human_review_confirmed=True,
        )



def test_section_review_rejects_non_boolean_confirmation_and_invalid_status_type():
    with pytest.raises(ValueError, match="human_review_confirmed debe ser booleano"):
        apply_section_range_decisions(
            sample_package(), [], human_review_confirmed="yes"
        )
    with pytest.raises(ValueError, match="decision debe ser"):
        apply_section_range_decisions(
            sample_package(),
            [{"section_range_id": "section-1", "decision": []}],
            human_review_confirmed=True,
        )


def test_section_review_requires_summary_object():
    package = sample_package()
    package["summary"] = None
    with pytest.raises(ValueError, match="resumen de revisión"):
        apply_section_range_decisions(
            package,
            [{"section_range_id": "section-1", "decision": "rejected"}],
            human_review_confirmed=True,
        )



def test_section_review_rejects_unknown_existing_review_status():
    package = sample_package()
    package["global_section_range_candidates"][0]["review_status"] = "maybe"
    with pytest.raises(ValueError, match="estado de revisión inválido"):
        apply_section_range_decisions(
            package,
            [{"section_range_id": "section-1", "decision": "rejected"}],
            human_review_confirmed=True,
        )
