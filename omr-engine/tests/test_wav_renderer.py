import io
import wave

import pytest

from palermo_omr.wav_renderer import render_polyphonic_wav


def stream(commands):
    return {"status": "unconfirmed_synth_command_stream", "commands": commands}


def cmd(kind, event, voice, midi, when):
    return {
        "command": kind, "event_id": event, "voice_id": voice,
        "midi": midi, "time_seconds": when,
    }


def read_wav(data):
    with wave.open(io.BytesIO(data), "rb") as wav:
        params = wav.getparams()
        frames = wav.readframes(wav.getnframes())
    return params, frames


def test_renders_stereo_pcm_audio_for_overlapping_polyphonic_notes():
    commands = [
        cmd("note_on", "s1", "soprano", 72, 0.0),
        cmd("note_on", "a1", "alto", 60, 0.0),
        cmd("note_off", "a1", "alto", 60, 0.25),
        cmd("note_off", "s1", "soprano", 72, 0.5),
    ]
    params, frames = read_wav(render_polyphonic_wav(stream(commands), sample_rate=8000))
    assert params.nchannels == 2
    assert params.sampwidth == 2
    assert params.framerate == 8000
    assert params.nframes == 4000
    assert any(frames)


def test_voice_pan_changes_stereo_balance():
    commands = [
        cmd("note_on", "left", "soprano", 69, 0.0),
        cmd("note_off", "left", "soprano", 69, 0.1),
    ]
    _, frames = read_wav(render_polyphonic_wav(stream(commands), sample_rate=8000))
    left_energy = sum(abs(int.from_bytes(frames[i:i+2], "little", signed=True)) for i in range(0, len(frames), 4))
    right_energy = sum(abs(int.from_bytes(frames[i:i+2], "little", signed=True)) for i in range(2, len(frames), 4))
    assert left_energy > right_energy


def test_rejects_unclosed_or_unmatched_notes_and_bad_parameters():
    with pytest.raises(ValueError, match="sin note_on"):
        render_polyphonic_wav(stream([cmd("note_off", "x", "alto", 60, 1)]))
    with pytest.raises(ValueError, match="sin note_off"):
        render_polyphonic_wav(stream([cmd("note_on", "x", "alto", 60, 0)]))
    with pytest.raises(ValueError, match="sample_rate"):
        render_polyphonic_wav(stream([]), sample_rate=1000)


def test_rests_or_empty_command_stream_render_valid_silence():
    params, frames = read_wav(render_polyphonic_wav(stream([]), sample_rate=8000))
    assert params.nframes == 1
    assert set(frames) == {0}


def test_rejects_excessive_render_duration_and_invalid_voice_pan():
    commands = [
        cmd("note_on", "x", "alto", 60, 0),
        cmd("note_off", "x", "alto", 60, 2),
    ]
    with pytest.raises(ValueError, match="límite"):
        render_polyphonic_wav(stream(commands), max_duration_seconds=1)
    with pytest.raises(ValueError, match="voice_pan"):
        render_polyphonic_wav(stream([]), voice_pan={"soprano": 2})
