from fractions import Fraction

import pytest

from palermo_omr.voice_measure import RhythmicEvent, analyze_voice_measure


def test_infers_one_unknown_event_inside_one_voice_measure():
    events = [
        RhythmicEvent("s1", "soprano", 0, 1),
        RhythmicEvent("s2", "soprano", 0, 1),
        RhythmicEvent("s3", "soprano", 0, None),
        RhythmicEvent("s4", "soprano", 0, 1),
    ]
    result = analyze_voice_measure(
        events, 4, 4, voice_id="soprano", measure_index=0
    )
    assert result.unknown_event_ids == ("s3",)
    assert result.completion.inferred_duration_quarters == Fraction(1, 1)


def test_rest_is_counted_as_known_time():
    events = [
        RhythmicEvent("n1", "alto", 2, 1),
        RhythmicEvent("r1", "alto", 2, Fraction(1, 2), "rest"),
        RhythmicEvent("n2", "alto", 2, None),
    ]
    result = analyze_voice_measure(
        events, 3, 4, voice_id="alto", measure_index=2
    )
    assert result.completion.remaining_quarters == Fraction(3, 2)
    assert result.completion.inferred_duration_quarters == Fraction(3, 2)


def test_multiple_unknown_events_are_not_arbitrarily_split():
    events = [
        RhythmicEvent("n1", "tenor", 1, 1),
        RhythmicEvent("n2", "tenor", 1, None),
        RhythmicEvent("n3", "tenor", 1, None),
    ]
    result = analyze_voice_measure(
        events, 4, 4, voice_id="tenor", measure_index=1
    )
    assert result.completion.status == "remainder_shared_by_multiple_unknowns"
    assert result.completion.inferred_duration_quarters is None


def test_rejects_mixing_different_voices_or_measures():
    events = [
        RhythmicEvent("s1", "soprano", 0, 1),
        RhythmicEvent("a1", "alto", 0, 1),
    ]
    with pytest.raises(ValueError, match="No se pueden mezclar"):
        analyze_voice_measure(
            events, 4, 4, voice_id="soprano", measure_index=0
        )


def test_rejects_duplicate_event_ids():
    events = [
        RhythmicEvent("n1", "bass", 0, 1),
        RhythmicEvent("n1", "bass", 0, None),
    ]
    with pytest.raises(ValueError, match="únicos"):
        analyze_voice_measure(
            events, 4, 4, voice_id="bass", measure_index=0
        )


def test_rejects_unknown_event_types():
    events = [RhythmicEvent("x1", "bass", 0, 1, "tie")]
    with pytest.raises(ValueError, match="event_type"):
        analyze_voice_measure(
            events, 4, 4, voice_id="bass", measure_index=0
        )
