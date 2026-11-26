from fractions import Fraction

import pytest

from palermo_omr.imaging import StaffCandidate
from palermo_omr.rhythm import RhythmCandidate
from palermo_omr.rhythm_interpretation import RhythmicInterpretationCandidate
from palermo_omr.rhythmic_event_groups import (\n    build_rhythmic_event_group_candidates,\n    build_reviewed_voice_events,\n)
from palermo_omr.symbols import NoteheadCandidate


def _inputs(xs, directions=None, durations=None, staff_indices=None):
    directions = directions or ["up"] * len(xs)
    durations = durations or ["quarter"] * len(xs)
    staff_indices = staff_indices or [0] * len(xs)
    heads, rhythms, interpretations = [], [], []
    for index, (x, direction, duration, staff) in enumerate(
        zip(xs, directions, durations, staff_indices)
    ):
        heads.append(NoteheadCandidate(
            bbox=(int(x - 6), 70, 12, 8), center_x=float(x), center_y=80.0,
            staff_index=staff, diatonic_step_from_bottom=index,
            fill_ratio=.8, notehead_shape_score=.9, confidence=.9,
        ))
        rhythms.append(RhythmCandidate(
            (int(x - 6), 70, 12, 8), staff, "filled", .9, direction, 30,
            0, duration, .8, (),
        ))
        interpretations.append(RhythmicInterpretationCandidate(
            index, staff, duration, 0, (), .7,
            "local_candidate_only" if duration != "unknown" else "unclassified", (),
        ))
    return heads, rhythms, interpretations


def _staffs(count=1):
    return [StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0) for _ in range(count)]


def test_nearby_heads_with_matching_stems_form_only_a_proposed_chord():
    values = _inputs([100, 108])
    result = build_rhythmic_event_group_candidates(_staffs(), *values)
    assert len(result) == 1
    assert result[0].notehead_indices == (0, 1)
    assert result[0].status == "proposed_chord"
    assert result[0].duration_quarters_candidate == Fraction(1)
    assert result[0].voice_id_candidate is None
    assert any("requiere confirmación" in warning for warning in result[0].warnings)


def test_opposite_stems_are_not_split_into_guessed_voices():
    values = _inputs([100, 107], directions=["up", "down"])
    result = build_rhythmic_event_group_candidates(_staffs(), *values)
    assert len(result) == 1
    assert result[0].status == "ambiguous"
    assert result[0].stem_direction_candidate == "mixed"
    assert result[0].voice_id_candidate is None
    assert result[0].duration_quarters_candidate is None


def test_distant_heads_become_separate_attack_candidates():
    values = _inputs([100, 130])
    result = build_rhythmic_event_group_candidates(_staffs(), *values)
    assert len(result) == 2
    assert [item.notehead_indices for item in result] == [(0,), (1,)]


def test_duration_conflict_makes_possible_chord_ambiguous():
    values = _inputs([100, 108], durations=["quarter", "half"])
    result = build_rhythmic_event_group_candidates(_staffs(), *values)
    assert result[0].status == "ambiguous"
    assert result[0].duration_candidate == "unknown"
    assert result[0].duration_quarters_candidate is None


def test_explicit_voice_assignment_is_preserved_but_not_inferred():
    values = _inputs([100, 108])
    result = build_rhythmic_event_group_candidates(
        _staffs(), *values, staff_voice_ids={0: "soprano"}
    )
    assert result[0].voice_id_candidate == "soprano"


def test_heads_from_different_staves_are_never_grouped():
    values = _inputs([100, 103], staff_indices=[0, 1])
    result = build_rhythmic_event_group_candidates(_staffs(2), *values)
    assert len(result) == 2
    assert {item.staff_index for item in result} == {0, 1}


def test_rejects_mismatched_input_lengths_and_invalid_staff_voice_map():
    heads, rhythms, interpretations = _inputs([100])
    with pytest.raises(ValueError, match="por cada cabeza"):
        build_rhythmic_event_group_candidates(_staffs(), heads, [], interpretations)
    with pytest.raises(ValueError, match="índice"):
        build_rhythmic_event_group_candidates(
            _staffs(), heads, rhythms, interpretations, staff_voice_ids={2: "alto"}
        )



def test_only_explicitly_reviewed_groups_enter_voice_sequence():
    values = _inputs([100, 130])
    groups = build_rhythmic_event_group_candidates(
        _staffs(), *values, staff_voice_ids={0: "alto"}
    )
    events = build_reviewed_voice_events(
        groups, voice_id="alto", measure_index=3,
        confirmed_event_ids={groups[0].event_id, groups[1].event_id},
    )
    assert [event.order_index for event in events] == [0, 1]
    assert [event.duration_quarters for event in events] == [Fraction(1), Fraction(1)]
    assert events[0].notehead_ids == ("staff-1-head-0",)


def test_unreviewed_groups_do_not_enter_voice_sequence():
    values = _inputs([100])
    groups = build_rhythmic_event_group_candidates(
        _staffs(), *values, staff_voice_ids={0: "alto"}
    )
    assert build_reviewed_voice_events(
        groups, voice_id="alto", measure_index=0, confirmed_event_ids=set()
    ) == ()


def test_ambiguous_group_cannot_be_confirmed_for_timing():
    values = _inputs([100, 107], directions=["up", "down"])
    groups = build_rhythmic_event_group_candidates(
        _staffs(), *values, staff_voice_ids={0: "alto"}
    )
    with pytest.raises(ValueError, match="ambiguo"):
        build_reviewed_voice_events(
            groups, voice_id="alto", measure_index=0,
            confirmed_event_ids={groups[0].event_id},
        )


def test_reviewed_group_requires_matching_explicit_voice_and_known_duration():
    values = _inputs([100])
    groups = build_rhythmic_event_group_candidates(_staffs(), *values)
    with pytest.raises(ValueError, match="asignación explícita"):
        build_reviewed_voice_events(
            groups, voice_id="alto", measure_index=0,
            confirmed_event_ids={groups[0].event_id},
        )
