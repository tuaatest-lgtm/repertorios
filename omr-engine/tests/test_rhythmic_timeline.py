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


def test_flags_overlapping_events_inside_the_same_voice_but_not_simultaneous_chord_attacks():
    events = [
        TimedRhythmicEvent("held", "soprano", 0, 0, 2),
        TimedRhythmicEvent("chord-tone", "alto", 0, 0, 1),
        TimedRhythmicEvent("next", "soprano", 0, 1, 1),
    ]
    result = analyze_measure_timeline(events, 4, 4, measure_index=0)

    assert result.overlapping_event_ids == ("held", "next")
    assert result.status == "overlapping_events"
    assert result.onset_groups[0].event_ids == ("chord-tone", "held")


def test_allows_independent_simultaneous_attacks_and_overlapping_durations_across_voices():
    events = [
        TimedRhythmicEvent("s-long", "soprano", 0, 0, 3),
        TimedRhythmicEvent("a-short", "alto", 0, 0, 1),
        TimedRhythmicEvent("a-next", "alto", 0, 1, 1),
    ]
    result = analyze_measure_timeline(events, 4, 4, measure_index=0)

    assert result.overlapping_event_ids == ()
    assert result.status == "placed_events_only"


def test_serializes_overlapping_event_diagnostics():
    events = [
        TimedRhythmicEvent("first", "tenor", 0, 0, 2),
        TimedRhythmicEvent("second", "tenor", 0, 1, 1),
    ]
    data = analyze_measure_timeline(events, 4, 4, measure_index=0).to_dict()
    assert data["overlapping_event_ids"] == ["first", "second"]
    assert data["status"] == "overlapping_events"



def test_reports_underfilled_voices_independently_instead_of_using_global_maximum():
    events = [
        TimedRhythmicEvent("s1", "soprano", 0, 0, 2),
        TimedRhythmicEvent("a1", "alto", 0, 0, 4),
    ]
    result = analyze_measure_timeline(events, 4, 4, measure_index=0)
    assert result.maximum_known_end_quarters == Fraction(4)
    assert result.underfilled_voice_ids == ("soprano",)
    assert result.to_dict()["underfilled_voice_ids"] == ["soprano"]


def test_does_not_claim_underfilled_when_voice_timing_is_unknown():
    events = [
        TimedRhythmicEvent("known", "tenor", 0, 0, 1),
        TimedRhythmicEvent("unknown", "tenor", 0, None, 1),
    ]
    result = analyze_measure_timeline(events, 4, 4, measure_index=0)
    assert result.underfilled_voice_ids == ()


def test_does_not_flag_a_voice_that_fills_the_measure_exactly():
    events = [
        TimedRhythmicEvent("first", "bass", 0, 0, 2),
        TimedRhythmicEvent("second", "bass", 0, 2, 2),
    ]
    result = analyze_measure_timeline(events, 4, 4, measure_index=0)
    assert result.underfilled_voice_ids == ()
