from fractions import Fraction

import pytest

from palermo_omr.reviewed_tie_chains import build_reviewed_tie_chains
from palermo_omr.tie_candidates import TieLinkCandidate, TieReviewConfirmation


def link(source, target, *, status="proposed_tie"):
    return TieLinkCandidate(
        arc_id=f"arc-{source}-{target}",
        source_event_id=source,
        target_event_id=target,
        status=status,
        pitch_match=True,
        temporal_continuity=True,
        geometry_score=0.9,
        warnings=(),
    )


def confirm(index):
    return TieReviewConfirmation(index, True, True, True)


def test_chain_combines_three_notated_notes_into_one_sustained_event():
    result = build_reviewed_tie_chains(
        [link("a", "b"), link("b", "c")],
        [confirm(0), confirm(1)],
        {"a": Fraction(1), "b": Fraction(1, 2), "c": Fraction(2)},
    )
    assert len(result) == 1
    assert result[0].event_ids == ("a", "b", "c")
    assert result[0].combined_duration_quarters == Fraction(7, 2)


def test_disjoint_tie_chains_remain_separate_and_deterministic():
    result = build_reviewed_tie_chains(
        [link("c", "d"), link("a", "b")],
        [confirm(0), confirm(1)],
        {"a": 1, "b": 1, "c": 2, "d": 2},
    )
    assert [item.event_ids for item in result] == [("a", "b"), ("c", "d")]
    assert [item.combined_duration_quarters for item in result] == [2, 4]


def test_unlinked_events_are_not_invented_as_tie_chains():
    assert build_reviewed_tie_chains([], [], {"ordinary-note": 1}) == ()


def test_rejects_branching_or_merging_tie_graphs():
    with pytest.raises(ValueError, match="dos sucesoras"):
        build_reviewed_tie_chains(
            [link("a", "b"), link("a", "c")],
            [confirm(0), confirm(1)],
            {"a": 1, "b": 1, "c": 1},
        )
    with pytest.raises(ValueError, match="dos predecesoras"):
        build_reviewed_tie_chains(
            [link("a", "c"), link("b", "c")],
            [confirm(0), confirm(1)],
            {"a": 1, "b": 1, "c": 1},
        )


def test_rejects_ambiguous_or_unreviewed_ties():
    with pytest.raises(ValueError, match="ambigua"):
        build_reviewed_tie_chains(
            [link("a", "b", status="ambiguous_tie_candidate")],
            [confirm(0)],
            {"a": 1, "b": 1},
        )
    with pytest.raises(ValueError, match="revisión humana"):
        build_reviewed_tie_chains(
            [link("a", "b")],
            [TieReviewConfirmation(0, False, True, True)],
            {"a": 1, "b": 1},
        )


def test_requires_duration_for_every_linked_event():
    with pytest.raises(ValueError, match="Faltan duraciones"):
        build_reviewed_tie_chains(
            [link("a", "b")],
            [confirm(0)],
            {"a": 1},
        )
