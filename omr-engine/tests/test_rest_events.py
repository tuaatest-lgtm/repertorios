from fractions import Fraction

import pytest

from palermo_omr.rhythm_symbols import RestSymbolCandidate
from palermo_omr.rest_events import RestReviewAssignment, build_reviewed_rest_events


def candidate(staff=0):
    return RestSymbolCandidate(
        bbox=(20, 40, 8, 14),
        staff_index=staff,
        shape_score=0.4,
        confidence=0.2,
        warning="candidato no confirmado",
        rest_type_candidate="unclassified",
        type_confidence=0.0,
    )


def assignment(**overrides):
    values = dict(
        candidate_index=0,
        event_id="rest-1",
        voice_id="alto",
        measure_index=2,
        order_index=1,
        duration_quarters=Fraction(1),
        confirmed_rest_type="quarter",
        reviewer_confirmed=True,
    )
    values.update(overrides)
    return RestReviewAssignment(**values)


def test_only_human_reviewed_rest_becomes_timed_voice_event():
    result = build_reviewed_rest_events([candidate()], [assignment()])
    assert len(result) == 1
    assert result[0].event_type == "rest"
    assert result[0].voice_id == "alto"
    assert result[0].duration_quarters == Fraction(1)
    assert result[0].order_index == 1


def test_rejects_unconfirmed_rest_candidate():
    with pytest.raises(ValueError, match="confirmación humana"):
        build_reviewed_rest_events(
            [candidate()],
            [assignment(reviewer_confirmed=False)],
        )


def test_does_not_infer_duration_from_visual_candidate_type():
    with pytest.raises(ValueError, match="duración"):
        build_reviewed_rest_events(
            [candidate()],
            [assignment(duration_quarters=0)],
        )


def test_requires_explicit_voice_and_recognized_rest_type():
    with pytest.raises(ValueError, match="voice_id"):
        build_reviewed_rest_events([candidate()], [assignment(voice_id=" ")])
    with pytest.raises(ValueError, match="tipo"):
        build_reviewed_rest_events([candidate()], [assignment(confirmed_rest_type="unknown")])


def test_rejects_duplicate_candidate_and_duplicate_voice_position():
    with pytest.raises(ValueError, match="asignarse dos veces"):
        build_reviewed_rest_events(
            [candidate()],
            [assignment(), assignment(event_id="rest-2", order_index=2)],
        )
    with pytest.raises(ValueError, match="order_index"):
        build_reviewed_rest_events(
            [candidate(), candidate()],
            [
                assignment(),
                assignment(candidate_index=1, event_id="rest-2"),
            ],
        )


def test_multiple_rest_events_can_be_assigned_to_distinct_voices_on_same_staff():
    result = build_reviewed_rest_events(
        [candidate(), candidate()],
        [
            assignment(event_id="soprano-rest", voice_id="soprano", order_index=0),
            assignment(candidate_index=1, event_id="alto-rest", voice_id="alto", order_index=0),
        ],
    )
    assert {event.voice_id for event in result} == {"soprano", "alto"}


def test_rejects_invalid_candidate_index_and_duplicate_event_id():
    with pytest.raises(ValueError, match="rango"):
        build_reviewed_rest_events([candidate()], [assignment(candidate_index=3)])
    with pytest.raises(ValueError, match="event_id debe ser único"):
        build_reviewed_rest_events(
            [candidate(), candidate()],
            [
                assignment(),
                assignment(candidate_index=1, order_index=2),
            ],
        )
