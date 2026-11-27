from fractions import Fraction

from palermo_omr.rhythmic_timeline import analyze_ordered_measure_voices
from palermo_omr.voice_sequence_timing import OrderedVoiceEvent


def test_integrates_independent_satb_sequences_into_one_poliphonic_measure():
    soprano = [
        OrderedVoiceEvent("s1", "soprano", 0, 0, 2),
        OrderedVoiceEvent("s2", "soprano", 0, 1, 1),
    ]
    alto = [
        OrderedVoiceEvent("a1", "alto", 0, 0, 1),
        OrderedVoiceEvent("a2", "alto", 0, 1, 1),
        OrderedVoiceEvent("a3", "alto", 0, 2, 1),
    ]
    result = analyze_ordered_measure_voices(
        [("soprano", 0, soprano), ("alto", 0, alto)],
        4, 4, measure_index=0,
    )
    onsets = {event.event_id: event.onset_quarters for event in result.events}
    assert onsets == {
        "s1": Fraction(0), "s2": Fraction(2),
        "a1": Fraction(0), "a2": Fraction(1), "a3": Fraction(2),
    }
    assert result.onset_groups[0].event_ids == ("a1", "s1")
    assert result.onset_groups[1].event_ids == ("a2",)
    assert result.onset_groups[2].event_ids == ("a3", "s2")
    assert result.status == "placed_events_only"


def test_unknown_duration_in_one_voice_does_not_block_other_voice_timing():
    soprano = [
        OrderedVoiceEvent("s1", "soprano", 0, 0, None),
        OrderedVoiceEvent("s2", "soprano", 0, 1, 1),
    ]
    bass = [
        OrderedVoiceEvent("b1", "bass", 0, 0, 1),
        OrderedVoiceEvent("b2", "bass", 0, 1, 1),
    ]
    result = analyze_ordered_measure_voices(
        [("soprano", 0, soprano), ("bass", 0, bass)],
        4, 4, measure_index=0,
    )
    onsets = {event.event_id: event.onset_quarters for event in result.events}
    assert onsets == {
        "s1": Fraction(0), "s2": None,
        "b1": Fraction(0), "b2": Fraction(1),
    }
    assert result.unknown_onset_event_ids == ("s2",)
    assert result.status == "incomplete_data"


def test_rejects_repeated_voice_measure_sequence():
    events = [OrderedVoiceEvent("s1", "soprano", 0, 0, 1)]
    try:
        analyze_ordered_measure_voices(
            [("soprano", 0, events), ("soprano", 0, events)],
            4, 4, measure_index=0,
        )
    except ValueError as exc:
        assert "repetir" in str(exc)
    else:
        raise AssertionError("Expected duplicate voice/measure sequence to fail")
