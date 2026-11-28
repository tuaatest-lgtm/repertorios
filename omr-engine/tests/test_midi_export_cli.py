import json

from palermo_omr.midi_export_cli import main


def test_cli_exports_command_stream_to_midi_file(tmp_path, capsys):
    source = tmp_path / "commands.json"
    output = tmp_path / "exports" / "score.mid"
    source.write_text(json.dumps({
        "status": "unconfirmed_synth_command_stream",
        "commands": [
            {"command": "note_on", "event_id": "n", "voice_id": "soprano", "midi": 72, "time_seconds": 0},
            {"command": "note_off", "event_id": "n", "voice_id": "soprano", "midi": 72, "time_seconds": 1},
        ],
    }), encoding="utf-8")

    code = main([
        str(source), str(output),
        "--tempo-bpm", "96",
        "--time-signature", "4/4",
        "--key-signature", "5:major",
        "--event-velocity", "n:104",
    ])

    assert code == 0
    data = output.read_bytes()
    assert data[:4] == b"MThd"
    assert "MIDI exportado" in capsys.readouterr().out


def test_cli_exports_score_playback_bundle(tmp_path):
    source = tmp_path / "bundle.json"
    output = tmp_path / "score.mid"
    source.write_text(json.dumps({
        "status": "unconfirmed_score_playback_bundle",
        "command_stream": {
            "status": "unconfirmed_synth_command_stream",
            "commands": [
                {"command": "note_on", "event_id": "a", "voice_id": "alto", "midi": 60, "time_seconds": 0},
                {"command": "note_off", "event_id": "a", "voice_id": "alto", "midi": 60, "time_seconds": 1},
            ],
        },
    }), encoding="utf-8")

    assert main([str(source), str(output)]) == 0
    assert output.read_bytes().startswith(b"MThd")


def test_cli_rejects_unknown_json_status_and_missing_input(tmp_path, capsys):
    source = tmp_path / "bad.json"
    output = tmp_path / "score.mid"
    source.write_text(json.dumps({"status": "unknown"}), encoding="utf-8")
    assert main([str(source), str(output)]) == 2
    assert "no contiene" in capsys.readouterr().err
    assert main([str(tmp_path / "missing.json"), str(output)]) == 2
    assert "No such file" in capsys.readouterr().err


def test_cli_rejects_duplicate_voice_option(tmp_path, capsys):
    source = tmp_path / "commands.json"
    output = tmp_path / "score.mid"
    source.write_text(json.dumps({
        "status": "unconfirmed_synth_command_stream",
        "commands": [
            {"command": "note_on", "event_id": "n", "voice_id": "alto", "midi": 60, "time_seconds": 0},
            {"command": "note_off", "event_id": "n", "voice_id": "alto", "midi": 60, "time_seconds": 1},
        ],
    }), encoding="utf-8")
    assert main([
        str(source), str(output),
        "--voice-program", "alto:52",
        "--voice-program", "alto:53",
    ]) == 2
    assert "repite la voz" in capsys.readouterr().err
