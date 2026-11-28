import json
import wave

from palermo_omr.wav_export_cli import main


def test_wav_cli_exports_command_stream(tmp_path, capsys):
    source = tmp_path / "commands.json"
    output = tmp_path / "audio" / "score.wav"
    source.write_text(json.dumps({
        "status": "unconfirmed_synth_command_stream",
        "commands": [
            {"command": "note_on", "event_id": "n", "voice_id": "soprano", "midi": 72, "time_seconds": 0},
            {"command": "note_off", "event_id": "n", "voice_id": "soprano", "midi": 72, "time_seconds": .1},
        ],
    }), encoding="utf-8")
    assert main([str(source), str(output), "--sample-rate", "8000"]) == 0
    with wave.open(str(output), "rb") as wav:
        assert wav.getnchannels() == 2
        assert wav.getframerate() == 8000
    assert "WAV exportado" in capsys.readouterr().out


def test_wav_cli_exports_score_playback_bundle_and_pan_options(tmp_path):
    source = tmp_path / "bundle.json"
    output = tmp_path / "score.wav"
    source.write_text(json.dumps({
        "status": "unconfirmed_score_playback_bundle",
        "command_stream": {
            "status": "unconfirmed_synth_command_stream",
            "commands": [
                {"command": "note_on", "event_id": "a", "voice_id": "alto", "midi": 60, "time_seconds": 0},
                {"command": "note_off", "event_id": "a", "voice_id": "alto", "midi": 60, "time_seconds": .1},
            ],
        },
    }), encoding="utf-8")
    assert main([str(source), str(output), "--voice-pan", "alto:-1"]) == 0
    assert output.read_bytes().startswith(b"RIFF")


def test_wav_cli_rejects_unknown_status_and_duplicate_voice_pan(tmp_path, capsys):
    source = tmp_path / "bad.json"
    output = tmp_path / "score.wav"
    source.write_text(json.dumps({"status": "unknown"}), encoding="utf-8")
    assert main([str(source), str(output)]) == 2
    assert "no contiene" in capsys.readouterr().err
    source.write_text(json.dumps({
        "status": "unconfirmed_synth_command_stream", "commands": [],
    }), encoding="utf-8")
    assert main([
        str(source), str(output),
        "--voice-pan", "alto:-1", "--voice-pan", "alto:1",
    ]) == 2
    assert "repite la voz" in capsys.readouterr().err
