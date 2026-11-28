from fractions import Fraction

import pytest

from palermo_omr.event_fusion import ScoreEventCandidate
from palermo_omr.candidate_timeline import build_candidate_measure_timelines


def candidate(event_id, voice, duration, heads=("head-1",), status="ready_for_review", measure=0):
    return ScoreEventCandidate(
        event_id=event_id,
        staff_index=0,
        notehead_candidate_ids=heads,
        pitch_candidates=(),
        voice_id_candidate=voice,
        duration_candidate="quarter" if duration else "unknown",
        duration_quarters_candidate=duration,
        status=status,
        warnings=(),
    )


def test_builds_independent_voice_timelines_and_groups_simultaneous_attacks():
    events = [
        candidate("s1", "soprano", Fraction(2), ("s-head",)),
        candidate("a1", "alto", Fraction(1), ("a-head",)),
        candidate("a2", "alto", Fraction(1), ("a-head-2",)),
    ]
    timelines = build_candidate_measure_timelines(
        events, {0: (4, 4)}, {"s1": 0, "a1": 0, "a2": 1}, {"s1": 0, "a1": 0, "a2": 0}
    )
    timeline = timelines[0]
    assert timeline["candidate_status"] == "unconfirmed_timeline"
    assert timeline["onset_groups"][0]["event_ids"] == ["a1", "s1"]
    by_id = {event["event_id"]: event for event in timeline["events"]}
    assert by_id["s1"]["duration_quarters"] == "2"
    assert by_id["s1"]["onset_quarters"] == "0"
    assert by_id["a1"]["onset_quarters"] == "0"
    assert by_id["a2"]["onset_quarters"] == "1"


def test_unknown_duration_stops_only_its_own_voice_onset_propagation():
    events = [
        candidate("s1", "soprano", None, status="incomplete_candidate"),
        candidate("s2", "soprano", Fraction(1)),
        candidate("a1", "alto", Fraction(1)),
        candidate("a2", "alto", Fraction(1)),
    ]
    timelines = build_candidate_measure_timelines(
        events, {0: (4, 4)}, {"s1": 0, "s2": 1, "a1": 0, "a2": 1}, {"s1": 0, "s2": 0, "a1": 0, "a2": 0}
    )
    timeline = timelines[0]
    by_id = {event["event_id"]: event for event in timeline["events"]}
    assert by_id["s1"]["onset_quarters"] == "0"
    assert by_id["s2"]["onset_quarters"] is None
    assert by_id["a2"]["onset_quarters"] == "1"
    assert {item["event_id"] for item in timeline["unresolved_candidates"]} == {"s1"}


def test_keeps_events_without_voice_or_order_out_of_timeline():
    events = [
        candidate("no-voice", None, Fraction(1)),
        candidate("no-order", "tenor", Fraction(1)),
    ]
    timelines = build_candidate_measure_timelines(
        events, {0: (3, 4)}, {"no-voice": 0}, {"no-voice": 0, "no-order": 0}
    )
    unresolved = {item["event_id"]: item["reason"] for item in timelines[0]["unresolved_candidates"]}
    assert unresolved == {"no-order": "missing_order", "no-voice": "missing_voice"}
    assert timelines[0]["events"] == []


def test_rejects_duplicate_order_within_voice_but_allows_across_voices():
    events = [
        candidate("s1", "soprano", Fraction(1)),
        candidate("s2", "soprano", Fraction(1)),
    ]
    with pytest.raises(ValueError, match="único"):
        build_candidate_measure_timelines(events, {0: (4, 4)}, {"s1": 0, "s2": 0}, {"s1": 0, "s2": 0})
    # The same onset order across independent voices is legitimate.
    result = build_candidate_measure_timelines(
        [events[0], candidate("a1", "alto", Fraction(1))],
        {0: (4, 4)}, {"s1": 0, "a1": 0}, {"s1": 0, "a1": 0}
    )
    assert result[0]["onset_groups"][0]["event_ids"] == ["a1", "s1"]


def test_rejects_invalid_meter_and_order_reference():
    with pytest.raises(ValueError, match="positivos"):
        build_candidate_measure_timelines([], {0: (4, 0)}, {}, {})
    with pytest.raises(ValueError, match="inexistentes"):
        build_candidate_measure_timelines([], {0: (4, 4)}, {"ghost": 0}, {})
