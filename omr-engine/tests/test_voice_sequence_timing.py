from fractions import Fraction

import pytest

from palermo_omr.voice_sequence_timing import (
    OrderedVoiceEvent,
    derive_measure_voice_sequences,
    derive_voice_sequence_timing,
)


def test_derives_onsets_from_durations_not_pixel_spacing():
    # order_index representa el orden visual. No hay coordenadas ni conversión px/tiempo.
    events = [
        OrderedVoiceEvent("long", "piano_right", 0, 0, 2),
        OrderedVoiceEvent("short_a", "piano_right", 0, 1, 1),
        OrderedVoiceEvent("short_b", "piano_right", 0, 2, 1),
    ]
    result = derive_voice_sequence_timing(
        events, voice_id="piano_right", measure_index=0
    )
    assert [event.onset_quarters for event in result.events] == [
        Fraction(0), Fraction(2), Fraction(3)
    ]
    assert result.status == "sequence_timed"


def test_simultaneous_chord_heads_share_one_attack_event():
    event = OrderedVoiceEvent(
        "chord", "alto", 0, 0, Fraction(2), notehead_ids=("n1", "n2", "n3")
    )
    result = derive_voice_sequence_timing(
        [event], voice_id="alto", measure_index=0
    )
    assert len(result.events) == 1
    assert result.events[0].onset_quarters == 0
    assert result.events[0].duration_quarters == 2


def test_unknown_duration_blocks_only_subsequent_onset_inference():
    events = [
        OrderedVoiceEvent("known", "tenor", 1, 0, 1),
        OrderedVoiceEvent("unknown", "tenor", 1, 1, None),
        OrderedVoiceEvent("after", "tenor", 1, 2, 1),
    ]
    result = derive_voice_sequence_timing(
        events, voice_id="tenor", measure_index=1
    )
    assert [event.onset_quarters for event in result.events] == [
        Fraction(0), Fraction(1), None
    ]
    assert result.unresolved_onset_event_ids == ("after",)
    assert result.status == "incomplete_sequence"


def test_rests_advance_the_same_voice_timeline():
    events = [
        OrderedVoiceEvent("note", "soprano", 0, 0, 1),
        OrderedVoiceEvent("rest", "soprano", 0, 1, 2, "rest"),
        OrderedVoiceEvent("next", "soprano", 0, 2, 1),
    ]
    result = derive_voice_sequence_timing(
        events, voice_id="soprano", measure_index=0
    )
    assert [event.onset_quarters for event in result.events] == [
        Fraction(0), Fraction(1), Fraction(3)
    ]


def test_combines_independent_voices_with_true_simultaneity():
    soprano = [
        OrderedVoiceEvent("s1", "soprano", 0, 0, 2),
        OrderedVoiceEvent("s2", "soprano", 0, 1, 1),
    ]
    bass = [
        OrderedVoiceEvent("b1", "bass", 0, 0, 1),
        OrderedVoiceEvent("b2", "bass", 0, 1, 1),
        OrderedVoiceEvent("b3", "bass", 0, 2, 1),
    ]
    events = derive_measure_voice_sequences([
        ("soprano", 0, soprano), ("bass", 0, bass)
    ])
    by_id = {event.event_id: event.onset_quarters for event in events}
    assert by_id == {
        "s1": Fraction(0), "s2": Fraction(2),
        "b1": Fraction(0), "b2": Fraction(1), "b3": Fraction(2),
    }


def test_rejects_duplicate_order_and_mixed_voices():
    with pytest.raises(ValueError, match="order_index"):
        derive_voice_sequence_timing(
            [OrderedVoiceEvent("a", "alto", 0, 0, 1),
             OrderedVoiceEvent("b", "alto", 0, 0, 1)],
            voice_id="alto", measure_index=0,
        )
    with pytest.raises(ValueError, match="no puede mezclar"):
        derive_voice_sequence_timing(
            [OrderedVoiceEvent("a", "alto", 0, 0, 1),
             OrderedVoiceEvent("b", "tenor", 0, 1, 1)],
            voice_id="alto", measure_index=0,
        )


def test_rejects_invalid_duration_and_duplicate_chord_heads():
    with pytest.raises(ValueError, match="mayor que cero"):
        derive_voice_sequence_timing(
            [OrderedVoiceEvent("a", "alto", 0, 0, 0)],
            voice_id="alto", measure_index=0,
        )
    with pytest.raises(ValueError, match="notehead_ids"):
        derive_voice_sequence_timing(
            [OrderedVoiceEvent("a", "alto", 0, 0, 1, notehead_ids=("n1", "n1"))],
            voice_id="alto", measure_index=0,
        )
