from fractions import Fraction

import pytest

from palermo_omr.rhythmic_timeline import (
    TimedRhythmicEvent,
    analyze_measure_timeline,
)


def test_groups_simultaneous_attacks_across_independent_satb_voices():
    events = [
        TimedRhythmicEvent("s1", "soprano", 0, 0, 2),
        TimedRhythmicEvent("a1", "alto", 0, 0, 1),
        TimedRhythmicEvent("t1", "tenor", 0, Fraction(1, 1), Fraction(1, 2)),
        TimedRhythmicEvent("b1", "bass", 0, 0, 4),
    ]
    result = analyze_measure_timeline(events, 4, 4, measure_index=0)

    assert result.onset_groups == (
        type(result.onset_groups[0])(Fraction(0), ("a1", "b1", "s1")),
        type(result.onset_groups[0])(Fraction(1), ("t1",)),
    )
    assert result.maximum_known_end_quarters == Fraction(4)
    assert result.status == "placed_events_only"
    assert result.out_of_measure_event_ids == ()


def test_preserves_overlapping_events_with_independent_durations():
    events = [
        TimedRhythmicEvent("long", "piano_right", 1, 0, 2),
        TimedRhythmicEvent("short1", "piano_left", 1, 0, 1),
        TimedRhythmicEvent("short2", "piano_left", 1, 1, 1),
    ]
    result = analyze_measure_timeline(events, 4, 4, measure_index=1)

    durations = {event.event_id: event.duration_quarters for event in result.events}
    assert durations == {"long": 2, "short1": 1, "short2": 1}
    assert result.onset_groups[0].event_ids == ("long", "short1")
    assert result.onset_groups[1].event_ids == ("short2",)
    assert result.status == "placed_events_only"


def test_keeps_unknown_onsets_and_durations_explicit():
    events = [
        TimedRhythmicEvent("unknown_onset", "alto", 0, None, 1),
        TimedRhythmicEvent("unknown_duration", "alto", 0, 1, None),
    ]
    result = analyze_measure_timeline(events, 3, 4, measure_index=0)

    assert result.unknown_onset_event_ids == ("unknown_onset",)
    assert result.unknown_duration_event_ids == ("unknown_duration",)
    assert result.status == "incomplete_data"


def test_detects_event_extending_beyond_measure():
    events = [TimedRhythmicEvent("late", "tenor", 2, 3, Fraction(3, 2))]
    result = analyze_measure_timeline(events, 4, 4, measure_index=2)

    assert result.out_of_measure_event_ids == ("late",)
    assert result.status == "overfull"


def test_rejects_mixed_measures_and_duplicate_ids():
    with pytest.raises(ValueError, match="distintos compases"):
        analyze_measure_timeline(
            [TimedRhythmicEvent("a", "s", 0, 0, 1),
             TimedRhythmicEvent("b", "s", 1, 1, 1)],
            4, 4, measure_index=0,
        )
    with pytest.raises(ValueError, match="únicos"):
        analyze_measure_timeline(
            [TimedRhythmicEvent("a", "s", 0, 0, 1),
             TimedRhythmicEvent("a", "a", 0, 1, 1)],
            4, 4, measure_index=0,
        )


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [(4, 4, Fraction(4)), (3, 4, Fraction(3)), (6, 8, Fraction(3))],
)
def test_uses_exact_measure_length_in_quarter_note_units(numerator, denominator, expected):
    result = analyze_measure_timeline([], numerator, denominator, measure_index=0)
    assert result.expected_quarters == expected


def test_rejects_nonpositive_duration_and_negative_onset():
    with pytest.raises(ValueError, match="mayor que cero"):
        analyze_measure_timeline(
            [TimedRhythmicEvent("a", "s", 0, 0, 0)], 4, 4, measure_index=0
        )
    with pytest.raises(ValueError, match="no puede ser negativo"):
        analyze_measure_timeline(
            [TimedRhythmicEvent("a", "s", 0, -1, 1)], 4, 4, measure_index=0
        )


def test_serializes_exact_times_without_float_rounding():
    event = TimedRhythmicEvent("e1", "soprano", 0, Fraction(1, 3), Fraction(2, 3))
    result = analyze_measure_timeline([event], 4, 4, measure_index=0)
    data = result.to_dict()

    assert data["expected_quarters"] == "4"
    assert data["events"][0]["onset_quarters"] == "1/3"
    assert data["events"][0]["duration_quarters"] == "2/3"
    assert data["onset_groups"][0]["onset_quarters"] == "1/3"


@pytest.mark.parametrize("event_measure", [-1, True, 0.5])
def test_rejects_invalid_event_measure_index(event_measure):
    event = TimedRhythmicEvent("e1", "alto", event_measure, 0, 1)
    with pytest.raises(ValueError, match="measure_index"):
        analyze_measure_timeline([event], 4, 4, measure_index=0)

@pytest.mark.parametrize("bad_value", [True, "1/2", "1", [], {}, object()])
def test_rejects_non_numeric_time_values(bad_value):
    with pytest.raises(ValueError, match="número válido"):
        analyze_measure_timeline(
            [TimedRhythmicEvent("bad", "alto", 0, bad_value, 1)],
            4, 4, measure_index=0,
        )
