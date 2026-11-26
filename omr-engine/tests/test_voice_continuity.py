from fractions import Fraction

import pytest

from palermo_omr.voice_continuity import (
    VoiceEventObservation,
    build_melodic_transition_candidates,
)


def _event(event_id, onset, pitch, *, duration=1, staff=0, stem="up"):
    return VoiceEventObservation(
        event_id=event_id,
        staff_index=staff,
        onset_quarters=Fraction(onset),
        duration_quarters=Fraction(duration),
        pitches_midi=(pitch,),
        stem_direction=stem,
    )


def test_proposes_nearby_melodic_transition_using_musical_time():
    result = build_melodic_transition_candidates([
        _event("a", 0, 60, duration=1),
        _event("b", 1, 62, duration=1),
    ])
    assert len(result) == 1
    assert result[0].source_event_id == "a"
    assert result[0].target_event_id == "b"
    assert result[0].pitch_interval_semitones == 2
    assert result[0].temporal_gap_quarters == 0
    assert result[0].status == "proposed_transition"


def test_does_not_link_events_from_different_staves():
    result = build_melodic_transition_candidates([
        _event("a", 0, 60, staff=0),
        _event("b", 1, 62, staff=1),
    ])
    assert result == ()


def test_does_not_link_same_onset_as_sequential_melody():
    result = build_melodic_transition_candidates([
        _event("a", 0, 60),
        _event("b", 0, 64),
    ])
    assert result == ()


def test_does_not_link_when_pitch_leap_exceeds_limit():
    result = build_melodic_transition_candidates([
        _event("a", 0, 48),
        _event("b", 1, 72),
    ], max_pitch_interval_semitones=12)
    assert result == ()


def test_does_not_link_when_temporal_gap_exceeds_limit():
    result = build_melodic_transition_candidates([
        _event("a", 0, 60, duration=1),
        _event("b", 5, 62),
    ], max_temporal_gap_quarters=2)
    assert result == ()


def test_competing_successors_are_marked_ambiguous():
    result = build_melodic_transition_candidates([
        _event("a", 0, 60),
        _event("b", 1, 62),
        _event("c", 1, 58),
    ])
    outgoing = [item for item in result if item.source_event_id == "a"]
    assert len(outgoing) == 2
    assert all(item.status == "ambiguous_competing_successors" for item in outgoing)


def test_different_stem_direction_is_only_weak_evidence():
    result = build_melodic_transition_candidates([
        _event("a", 0, 60, stem="up"),
        _event("b", 1, 62, stem="down"),
    ])
    assert len(result) == 1
    assert result[0].stem_direction_match is False
    assert result[0].status == "proposed_transition"
    assert any("no se usa como regla" in warning for warning in result[0].warnings)


def test_chords_are_not_forced_into_single_pitch_melodic_links():
    a = VoiceEventObservation("a", 0, Fraction(0), Fraction(1), (60, 64), "up")
    b = _event("b", 1, 62)
    assert build_melodic_transition_candidates([a, b]) == ()


def test_overlapping_events_are_flagged_for_review_not_silently_discarded():
    result = build_melodic_transition_candidates([
        _event("a", 0, 60, duration=2),
        _event("b", 1, 62),
    ])
    assert len(result) == 1
    assert result[0].overlaps_source
    assert result[0].temporal_gap_quarters == -1
    assert any("se solapan" in warning for warning in result[0].warnings)


def test_rejects_invalid_event_data_and_parameters():
    with pytest.raises(ValueError, match="único"):
        build_melodic_transition_candidates([_event("x", 0, 60), _event("x", 1, 62)])
    with pytest.raises(ValueError, match="altura MIDI"):
        build_melodic_transition_candidates([
            VoiceEventObservation("x", 0, Fraction(0), Fraction(1), (), "up")
        ])
    with pytest.raises(ValueError, match="entero no negativo"):
        build_melodic_transition_candidates([_event("x", 0, 60)], max_pitch_interval_semitones=-1)
    with pytest.raises(ValueError, match="no puede ser negativo"):
        build_melodic_transition_candidates([_event("x", 0, 60)], max_temporal_gap_quarters=-1)
