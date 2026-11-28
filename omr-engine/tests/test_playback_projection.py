from fractions import Fraction

import pytest

from palermo_omr.event_fusion import ScoreEventCandidate
from palermo_omr.playback_projection import build_playback_projection


def candidate(event_id, midi=(60,), status="ready_for_review"):
    return ScoreEventCandidate(
        event_id=event_id, staff_index=0, notehead_candidate_ids=(event_id,),
        pitch_candidates=tuple({"pitch": {"midi": value}} for value in midi),
        voice_id_candidate="soprano", duration_candidate="quarter",
        duration_quarters_candidate=Fraction(1), status=status, warnings=(),
    )


def timeline(index, events, expected="4"):
    return {"measure_index": index, "expected_quarters": expected, "events": events}


def timed(event_id, voice="soprano", onset="0", duration="1", kind="note"):
    return {
        "event_id": event_id, "voice_id": voice, "event_type": kind,
        "onset_quarters": onset, "duration_quarters": duration,
    }


def test_projects_chords_to_midi_and_seconds_without_losing_simultaneity():
    result = build_playback_projection(
        [timeline(0, [timed("s"), timed("a", "alto")])],
        [candidate("s", (60, 64, 67)), candidate("a", (55,))],
        tempo_bpm=120,
    )
    assert len(result["events"]) == 2
    by_id = {event["event_id"]: event for event in result["events"]}
    assert by_id["a"]["midi_notes"] == [55]
    assert by_id["s"]["midi_notes"] == [60, 64, 67]
    assert {event["start_seconds"] for event in result["events"]} == {0.0}
    assert by_id["s"]["duration_seconds"] == 0.5


def test_concatenates_measures_and_keeps_independent_durations():
    result = build_playback_projection(
        [
            timeline(0, [timed("long", "soprano", "0", "3")]),
            timeline(1, [timed("short", "alto", "0", "1")]),
        ],
        [candidate("long"), candidate("short")],
        tempo_bpm=60,
    )
    by_id = {item["event_id"]: item for item in result["events"]}
    assert by_id["long"]["end_seconds"] == 3.0
    assert by_id["short"]["start_seconds"] == 4.0


def test_unknown_timing_and_unresolved_pitch_are_not_scheduled():
    result = build_playback_projection(
        [timeline(0, [timed("unknown", onset=None), timed("badpitch")])],
        [candidate("unknown"), candidate("badpitch", status="incomplete_candidate")],
        tempo_bpm=100,
    )
    assert result["events"] == []
    assert {item["reason"] for item in result["unresolved_candidates"]} == {
        "unknown_onset_or_duration", "pitch_or_candidate_unresolved"
    }


def test_rest_is_scheduled_without_pitch():
    result = build_playback_projection(
        [timeline(0, [timed("rest", kind="rest")])],
        [candidate("rest", midi=(), status="incomplete_candidate")],
        tempo_bpm=120,
    )
    assert result["events"][0]["event_type"] == "rest"
    assert result["events"][0]["midi_notes"] == []


def test_rejects_invalid_tempo_duplicate_measures_and_invalid_durations():
    with pytest.raises(ValueError, match="positivo"):
        build_playback_projection([], [], tempo_bpm=0)
    with pytest.raises(ValueError, match="repetir"):
        build_playback_projection([timeline(0, []), timeline(0, [])], [], tempo_bpm=90)
    with pytest.raises(ValueError, match="duración positiva"):
        build_playback_projection(
            [timeline(0, [timed("s", duration="0")])], [candidate("s")], tempo_bpm=90
        )


def test_rejects_duplicate_event_ids_in_candidates_and_timeline():
    with pytest.raises(ValueError, match="únicos"):
        build_playback_projection([], [candidate("x"), candidate("x")], tempo_bpm=90)
    with pytest.raises(ValueError, match="más de una vez"):
        build_playback_projection(
            [timeline(0, [timed("x"), timed("x", onset="1")])],
            [candidate("x")], tempo_bpm=90,
        )
