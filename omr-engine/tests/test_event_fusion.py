from fractions import Fraction
from types import SimpleNamespace

import pytest

from palermo_omr.event_fusion import fuse_score_event_candidates


def pitch(staff=0, status="resolved_from_supplied_clef", midi=60):
    return SimpleNamespace(
        staff_index=staff,
        status=status,
        pitch=SimpleNamespace(midi=midi),
        to_dict=lambda: {"staff_index": staff, "status": status, "midi": midi},
    )


def group(**overrides):
    values = dict(
        event_id="event-1",
        staff_index=0,
        notehead_indices=(0, 1),
        voice_id_candidate="soprano",
        duration_candidate="quarter",
        duration_quarters_candidate=Fraction(1),
        status="proposed_chord",
        warnings=(),
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_fuses_chord_heads_with_pitch_provenance_without_confirming_event():
    result = fuse_score_event_candidates(
        [group()], [pitch(midi=60), pitch(midi=64)], ["head-a", "head-b"]
    )
    event = result[0]
    assert event.notehead_candidate_ids == ("head-a", "head-b")
    assert [item["midi"] for item in event.pitch_candidates] == [60, 64]
    assert event.duration_quarters_candidate == Fraction(1)
    assert event.status == "ready_for_review"
    assert event.status != "confirmed"


def test_unresolved_pitch_keeps_event_incomplete_and_auditable():
    event = fuse_score_event_candidates(
        [group()], [pitch(status="unresolved_clef"), pitch()], ["head-a", "head-b"]
    )[0]
    assert event.status == "incomplete_candidate"
    assert any("alturas siguen sin resolver" in warning for warning in event.warnings)


def test_missing_voice_or_duration_never_creates_review_ready_event():
    event = fuse_score_event_candidates(
        [group(voice_id_candidate=None, duration_quarters_candidate=None)],
        [pitch(), pitch()], ["head-a", "head-b"]
    )[0]
    assert event.status == "incomplete_candidate"
    assert event.duration_quarters_candidate is None


def test_ambiguous_rhythmic_group_is_not_promoted():
    event = fuse_score_event_candidates(
        [group(status="ambiguous")], [pitch(), pitch()], ["head-a", "head-b"]
    )[0]
    assert event.status == "incomplete_candidate"
    assert any("ambiguo" in warning for warning in event.warnings)


def test_rejects_duplicate_or_out_of_range_notehead_indices():
    with pytest.raises(ValueError, match="fuera del rango"):
        fuse_score_event_candidates(
            [group(notehead_indices=(0, 2))], [pitch(), pitch()], ["a", "b"]
        )
    with pytest.raises(ValueError, match="no vacío y sin duplicados"):
        fuse_score_event_candidates(
            [group(notehead_indices=(0, 0))], [pitch()], ["a"]
        )


def test_rejects_cross_staff_pitch_assignment_and_duplicate_ownership():
    with pytest.raises(ValueError, match="pentagramas distintos"):
        fuse_score_event_candidates(
            [group()], [pitch(0), pitch(1)], ["a", "b"]
        )
    with pytest.raises(ValueError, match="más de un evento"):
        fuse_score_event_candidates(
            [group(), group(event_id="event-2", notehead_indices=(1,))],
            [pitch(), pitch()], ["a", "b"]
        )


def test_requires_unique_source_ids_and_serializes_fraction_exactly():
    with pytest.raises(ValueError, match="únicos"):
        fuse_score_event_candidates([group()], [pitch(), pitch()], ["a", "a"])
    event = fuse_score_event_candidates(
        [group(duration_quarters_candidate=Fraction(3, 2))],
        [pitch(), pitch()], ["a", "b"]
    )[0]
    assert event.to_dict()["duration_quarters_candidate"] == "3/2"


def test_fuses_rest_without_noteheads_or_pitch_candidates():
    rest = group(
        event_id="rest-1",
        notehead_indices=(),
        event_type="rest",
        status="single_rest_candidate",
    )
    event = fuse_score_event_candidates([rest], [], [])[0]
    assert event.event_type == "rest"
    assert event.notehead_candidate_ids == ()
    assert event.pitch_candidates == ()
    assert event.status == "ready_for_review"


def test_rejects_rest_that_claims_noteheads_or_unknown_event_type():
    with pytest.raises(ValueError, match="no puede apropiarse"):
        fuse_score_event_candidates(
            [group(event_type="rest", status="single_rest_candidate")],
            [pitch(), pitch()], ["a", "b"]
        )
    with pytest.raises(ValueError, match="event_type"):
        fuse_score_event_candidates([group(event_type="unknown")], [pitch(), pitch()], ["a", "b"])
