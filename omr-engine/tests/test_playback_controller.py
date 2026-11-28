from palermo_omr.playback_controller import PlaybackController


class FakeSink:
    def __init__(self):
        self.calls = []

    def note_on(self, voice_id, midi, event_id):
        self.calls.append(("on", voice_id, midi, event_id))

    def note_off(self, voice_id, midi, event_id):
        self.calls.append(("off", voice_id, midi, event_id))

    def all_notes_off(self):
        self.calls.append(("panic",))


def make_stream():
    return {"status": "unconfirmed_synth_command_stream", "commands": [
        {"command": "note_on", "time_seconds": 0.0, "voice_id": "soprano", "midi": 72, "event_id": "s1"},
        {"command": "note_on", "time_seconds": 0.0, "voice_id": "alto", "midi": 60, "event_id": "a1"},
        {"command": "note_off", "time_seconds": 1.0, "voice_id": "alto", "midi": 60, "event_id": "a1"},
        {"command": "note_off", "time_seconds": 2.0, "voice_id": "soprano", "midi": 72, "event_id": "s1"},
    ]}


def test_playback_preserves_polyphony_and_finishes_after_last_voice():
    sink = FakeSink()
    player = PlaybackController(make_stream(), sink)
    player.play(10.0)
    assert sink.calls[-2:] == [("on", "alto", 60, "a1"), ("on", "soprano", 72, "s1")]
    player.tick(11.0)
    assert ("off", "alto", 60, "a1") in sink.calls
    assert player.snapshot()["active_notes"] == 1
    assert player.tick(12.0)["state"] == "finished"
    assert sink.calls[-1] == ("panic",)


def test_pause_resume_freezes_score_clock_and_restarts_sustained_notes():
    sink = FakeSink()
    player = PlaybackController(make_stream(), sink)
    player.play(100.0)
    player.pause(100.4)
    assert player.state == "paused"
    assert sink.calls[-1] == ("panic",)
    before = len(sink.calls)
    player.resume(500.0)
    assert player.state == "playing"
    assert sink.calls[before:] == [("on", "alto", 60, "a1"), ("on", "soprano", 72, "s1")]
    player.tick(500.6)
    assert player.snapshot()["current_seconds"] == 1.0


def test_stop_clears_active_notes_and_rewinds():
    sink = FakeSink()
    player = PlaybackController(make_stream(), sink)
    player.play(0)
    player.tick(0.5)
    player.stop()
    assert player.snapshot() == {
        "state": "stopped", "current_seconds": 0.0, "processed_commands": 0,
        "total_commands": 4, "active_notes": 0, "muted_voices": [],
    }
    assert sink.calls[-1] == ("panic",)


def test_voice_mute_is_independent_and_unmute_restores_only_that_voice():
    sink = FakeSink()
    player = PlaybackController(make_stream(), sink)
    player.play(0)
    player.set_voice_muted("soprano", True)
    assert sink.calls[-1] == ("off", "soprano", 72, "s1")
    player.set_voice_muted("alto", True)
    player.set_voice_muted("soprano", False)
    assert sink.calls[-1] == ("on", "soprano", 72, "s1")
    player.tick(1.0)
    assert sink.calls.count(("off", "alto", 60, "a1")) == 1


def test_muting_before_note_attack_suppresses_only_selected_voice():
    sink = FakeSink()
    player = PlaybackController(make_stream(), sink)
    player.set_voice_muted("soprano", True)
    player.play(0)
    assert ("on", "alto", 60, "a1") in sink.calls
    assert ("on", "soprano", 72, "s1") not in sink.calls


def test_rejects_invalid_clock_and_sink():
    import pytest
    sink = FakeSink()
    player = PlaybackController(make_stream(), sink)
    with pytest.raises(ValueError, match="reloj"):
        player.play(float("nan"))
    with pytest.raises(ValueError, match="sink"):
        PlaybackController(make_stream(), object())


def test_voice_mute_changes_during_pause_do_not_restart_audio_until_resume():
    sink = FakeSink()
    player = PlaybackController(make_stream(), sink)
    player.play(0)
    player.pause(0.25)
    before = len(sink.calls)
    player.set_voice_muted("soprano", True)
    player.set_voice_muted("alto", False)
    assert len(sink.calls) == before
    player.resume(10)
    assert sink.calls[before:] == [("on", "alto", 60, "a1")]


def test_pause_at_end_of_score_does_not_overwrite_finished_state():
    sink = FakeSink()
    player = PlaybackController(make_stream(), sink)
    player.play(0)
    player.pause(2.0)
    assert player.state == "finished"
