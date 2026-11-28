import pytest

from palermo_omr.polyphonic_command_stream import build_polyphonic_command_stream


def projection(events):
    return {"status": "unconfirmed_playback_projection", "events": events}


def event(event_id, voice="soprano", start=0.0, duration=1.0, pitches=(60,), kind="note"):
    return {
        "event_id": event_id, "voice_id": voice, "event_type": kind,
        "start_seconds": start, "duration_seconds": duration,
        "midi_notes": list(pitches),
    }


def test_emits_simultaneous_chord_notes_and_independent_voice_release():
    result = build_polyphonic_command_stream(projection([
        event("chord", pitches=(60, 64, 67), duration=2),
        event("alto-1", "alto", start=0, duration=0.5, pitches=(55,)),
        event("alto-2", "alto", start=0.5, duration=0.5, pitches=(57,)),
    ]))
    commands = result["commands"]
    starts = [c for c in commands if c["command"] == "note_on" and c["time_seconds"] == 0]
    assert {(c["voice_id"], c["midi"]) for c in starts} == {
        ("soprano", 60), ("soprano", 64), ("soprano", 67), ("alto", 55)
    }
    assert any(c["command"] == "note_off" and c["voice_id"] == "soprano"
               and c["time_seconds"] == 2 for c in commands)
    assert any(c["command"] == "note_off" and c["voice_id"] == "alto"
               and c["time_seconds"] == 0.5 for c in commands)


def test_note_off_precedes_new_note_on_at_same_timestamp():
    result = build_polyphonic_command_stream(projection([
        event("first", start=0, duration=1, pitches=(60,)),
        event("second", start=1, duration=1, pitches=(60,)),
    ]))
    at_one = [c["command"] for c in result["commands"] if c["time_seconds"] == 1]
    assert at_one == ["note_off", "note_on"]


def test_same_pitch_in_two_voices_keeps_voice_identity():
    result = build_polyphonic_command_stream(projection([
        event("s", "soprano", pitches=(60,)),
        event("a", "alto", pitches=(60,)),
    ]))
    active = [c for c in result["commands"] if c["command"] == "note_on"]
    assert {(c["voice_id"], c["midi"]) for c in active} == {
        ("soprano", 60), ("alto", 60)
    }


def test_rests_generate_no_sound_commands():
    result = build_polyphonic_command_stream(projection([
        event("rest", kind="rest", pitches=(), duration=2),
        event("note", start=2, pitches=(67,)),
    ]))
    assert len(result["commands"]) == 2
    assert {c["event_id"] for c in result["commands"]} == {"note"}


def test_incomplete_events_are_reported_not_played():
    result = build_polyphonic_command_stream(projection([
        event("no-voice", voice=None),
        event("no-pitch", pitches=()),
        event("bad-time", start=float("nan")),
    ]))
    assert result["commands"] == []
    assert {item["reason"] for item in result["skipped_events"]} == {
        "missing_voice", "missing_pitch", "invalid_timing"
    }


def test_rejects_untrusted_projection_and_duplicate_event_ids():
    with pytest.raises(ValueError, match="provisional"):
        build_polyphonic_command_stream({"status": "confirmed", "events": []})
    with pytest.raises(ValueError, match="únicos"):
        build_polyphonic_command_stream(projection([event("x"), event("x")]))
