import json
import xml.etree.ElementTree as ET

from palermo_omr.musicxml_export_cli import main


def test_musicxml_cli_exports_reviewed_timeline(tmp_path, capsys):
    source = tmp_path / "timeline.json"
    output = tmp_path / "exports" / "score.musicxml"
    source.write_text(json.dumps({
        "timelines": [{
            "page_number": 1, "measure_index": 0,
            "numerator": 4, "denominator": 4,
            "status": "placed_events_only",
            "unknown_onset_event_ids": [], "unknown_duration_event_ids": [],
            "out_of_measure_event_ids": [], "overlapping_event_ids": [],
            "underfilled_voice_ids": [],
            "events": [{
                "event_id": "n", "voice_id": "soprano",
                "onset_quarters": "0", "duration_quarters": "4",
                "event_type": "note",
                "confirmed_pitches": [{"step": "C", "octave": 5, "alteration": 0}],
            }],
        }],
    }), encoding="utf-8")
    code = main([
        str(source), str(output), "--title", "Test",
        "--tempo-bpm", "96", "--key-signature", "5:major",
    ])
    assert code == 0
    root = ET.fromstring(output.read_bytes())
    assert root.findtext("work/work-title") == "Test"
    assert "MusicXML exportado" in capsys.readouterr().out


def test_musicxml_cli_accepts_timeline_list_and_global_measure_map(tmp_path):
    source = tmp_path / "timeline-list.json"
    mapping = tmp_path / "numbers.json"
    output = tmp_path / "score.musicxml"
    source.write_text(json.dumps([{
        "page_number": 1, "measure_index": 0,
        "numerator": 4, "denominator": 4,
        "status": "placed_events_only",
        "unknown_onset_event_ids": [], "unknown_duration_event_ids": [],
        "out_of_measure_event_ids": [], "overlapping_event_ids": [],
        "underfilled_voice_ids": [],
        "events": [{
            "event_id": "n", "voice_id": "alto",
            "onset_quarters": "0", "duration_quarters": "4",
            "event_type": "note",
            "confirmed_pitches": [{"step": "A", "octave": 3}],
        }],
    }]), encoding="utf-8")
    mapping.write_text(json.dumps({"1:0": 7}), encoding="utf-8")
    assert main([str(source), str(output), "--global-measure-numbers", str(mapping)]) == 0
    root = ET.fromstring(output.read_bytes())
    assert root.find("part/measure").attrib["number"] == "7"


def test_musicxml_cli_rejects_invalid_input_without_writing_output(tmp_path, capsys):
    source = tmp_path / "bad.json"
    output = tmp_path / "score.musicxml"
    source.write_text(json.dumps({"status": "unknown"}), encoding="utf-8")
    assert main([str(source), str(output)]) == 2
    assert "timelines" in capsys.readouterr().err
    assert not output.exists()
