import xml.etree.ElementTree as ET

import pytest

from palermo_omr.musicxml_export import render_reviewed_timelines_musicxml


def timeline(events, **extra):
    return {
        "page_number": 1,
        "measure_index": 0,
        "numerator": 4,
        "denominator": 4,
        "status": "placed_events_only",
        "unknown_onset_event_ids": [],
        "unknown_duration_event_ids": [],
        "out_of_measure_event_ids": [],
        "overlapping_event_ids": [],
        "underfilled_voice_ids": [],
        "events": events,
        **extra,
    }


def note(event_id, voice, onset, duration, pitches, **extra):
    return {
        "event_id": event_id,
        "voice_id": voice,
        "onset_quarters": str(onset),
        "duration_quarters": str(duration),
        "event_type": "note",
        "confirmed_pitches": pitches,
        **extra,
    }


def pitch(step, octave, alteration=0):
    return {"step": step, "octave": octave, "alteration": alteration}


def parse(data):
    assert data.startswith(b"<?xml")
    return ET.fromstring(data)


def test_exports_independent_voice_parts_chords_and_tempo_key_meter():
    measure = timeline([
        note("s-chord", "soprano", 0, 1, [pitch("C", 5), pitch("E", 5)]),
        note("s-next", "soprano", 1, 1, [pitch("G", 5)]),
        note("a-long", "alto", 0, 2, [pitch("A", 3)]),
    ])
    root = parse(render_reviewed_timelines_musicxml(
        [measure], title="Clamaré", tempo_bpm=96,
        key_signature=(5, "major"),
    ))
    assert root.attrib == {"version": "4.0"}
    parts = root.findall("part")
    assert len(parts) == 2
    part_names = [part.findtext("part-name") for part in root.findall("part-list/score-part")]
    assert part_names == ["alto", "soprano"]
    soprano = next(part for part in parts if part.attrib["id"] == "P2")
    notes = soprano.findall("measure/note")
    assert len(notes) == 3
    assert notes[0].find("chord") is None
    assert notes[1].find("chord") is not None
    assert notes[0].findtext("pitch/step") == "C"
    assert notes[1].findtext("pitch/step") == "E"
    assert soprano.findtext("measure/attributes/time/beats") == "4"
    assert soprano.findtext("measure/attributes/time/beat-type") == "4"
    assert soprano.findtext("measure/attributes/key/fifths") == "5"
    alto = next(part for part in parts if part.attrib["id"] == "P1")
    assert alto.findtext("measure/direction/direction-type/metronome/per-minute") == "96"


def test_exports_rests_dotted_durations_and_tuplet_time_modification():
    measure = timeline([
        note("dotted", "tenor", 0, "3/2", [pitch("D", 4)]),
        {
            "event_id": "triplet", "voice_id": "tenor",
            "onset_quarters": "3/2", "duration_quarters": "1/3",
            "event_type": "note", "confirmed_pitches": [pitch("E", 4)],
        },
        {
            "event_id": "rest", "voice_id": "tenor",
            "onset_quarters": "11/6", "duration_quarters": "1/2",
            "event_type": "rest", "confirmed_pitches": [],
        },
    ])
    root = parse(render_reviewed_timelines_musicxml([measure]))
    notes = root.findall("part/measure/note")
    assert notes[0].findtext("type") == "quarter"
    assert len(notes[0].findall("dot")) == 1
    assert notes[1].findtext("type") == "eighth"
    assert notes[1].findtext("time-modification/actual-notes") == "3"
    assert notes[1].findtext("time-modification/normal-notes") == "2"
    assert notes[2].find("rest") is not None


def test_exports_tie_start_and_stop_notations():
    measure = timeline([
        note("tie-start", "bass", 0, 1, [pitch("G", 2)], tie_start=True),
        note("tie-stop", "bass", 1, 1, [pitch("G", 2)], tie_stop=True),
    ])
    root = parse(render_reviewed_timelines_musicxml([measure]))
    notes = root.findall("part/measure/note")
    assert notes[0].find("tie").attrib["type"] == "start"
    assert notes[0].find("notations/tied").attrib["type"] == "start"
    assert notes[1].find("tie").attrib["type"] == "stop"


def test_uses_explicit_global_measure_numbers_across_pages():
    first = timeline([note("a", "alto", 0, 4, [pitch("C", 4)])])
    second = timeline([note("b", "alto", 0, 4, [pitch("D", 4)])], page_number=2, measure_index=0)
    root = parse(render_reviewed_timelines_musicxml(
        [first, second], global_measure_numbers={"1:0": 8, "2:0": 9}
    ))
    assert [m.attrib["number"] for m in root.findall("part/measure")] == ["8", "9"]


def test_rejects_unreviewed_pitch_or_incomplete_timeline():
    missing_pitch = timeline([note("a", "alto", 0, 4, [])])
    with pytest.raises(ValueError, match="alturas confirmadas"):
        render_reviewed_timelines_musicxml([missing_pitch])
    incomplete = timeline([note("a", "alto", 0, 4, [pitch("C", 4)])], status="incomplete_data")
    with pytest.raises(ValueError, match="completas"):
        render_reviewed_timelines_musicxml([incomplete])


def test_rejects_overfull_underfilled_and_overlapping_voice_measures():
    event = note("a", "alto", 0, 4, [pitch("C", 4)])
    overfull = timeline([event], out_of_measure_event_ids=["a"])
    with pytest.raises(ValueError, match="desbordes"):
        render_reviewed_timelines_musicxml([overfull])
    underfilled = timeline([event], underfilled_voice_ids=["alto"])
    with pytest.raises(ValueError, match="incompletos"):
        render_reviewed_timelines_musicxml([underfilled])
    overlap = timeline([event], overlapping_event_ids=["a"])
    with pytest.raises(ValueError, match="desbordes"):
        render_reviewed_timelines_musicxml([overlap])


def test_rejects_incompatible_simultaneous_events_and_invalid_pitches():
    simultaneous = timeline([
        note("a", "soprano", 0, 1, [pitch("C", 4)]),
        note("b", "soprano", 0, 2, [pitch("E", 4)]),
    ])
    with pytest.raises(ValueError, match="simultáneos"):
        render_reviewed_timelines_musicxml([simultaneous])
    invalid = timeline([note("a", "alto", 0, 4, [pitch("H", 4)])])
    with pytest.raises(ValueError, match="step"):
        render_reviewed_timelines_musicxml([invalid])


def test_rejects_invalid_measure_numbers_and_key_signature():
    measure = timeline([note("a", "alto", 0, 4, [pitch("C", 4)])])
    with pytest.raises(ValueError, match="global_measure_numbers"):
        render_reviewed_timelines_musicxml([measure], global_measure_numbers={"1:0": 0})
    with pytest.raises(ValueError, match="fifths"):
        render_reviewed_timelines_musicxml([measure], key_signature=(8, "major"))


def test_rejects_voice_without_explicit_note_or_rest_in_a_measure():
    first = timeline([note("alto", "alto", 0, 4, [pitch("C", 4)])])
    second = timeline(
        [note("soprano", "soprano", 0, 4, [pitch("G", 5)])],
        page_number=2, measure_index=0,
    )
    with pytest.raises(ValueError, match="evento o silencio explícito"):
        render_reviewed_timelines_musicxml([first, second])


def test_rejects_non_boolean_tie_flags_and_ties_on_rests():
    invalid_flag = timeline([
        note("n", "alto", 0, 4, [pitch("C", 4)], tie_start="yes")
    ])
    with pytest.raises(ValueError, match="tie_start debe ser booleano"):
        render_reviewed_timelines_musicxml([invalid_flag])

    tied_rest = timeline([{
        "event_id": "r", "voice_id": "alto", "onset_quarters": "0",
        "duration_quarters": "4", "event_type": "rest",
        "confirmed_pitches": [], "tie_start": True,
    }])
    with pytest.raises(ValueError, match="silencio no puede"):
        render_reviewed_timelines_musicxml([tied_rest])



def test_preserves_leading_silence_and_exact_onset_with_forward_element():
    measure = timeline([
        note("late", "soprano", 1, 1, [pitch("C", 5)]),
        note("after-gap", "soprano", 2, 2, [pitch("D", 5)]),
        note("alto-long", "alto", 0, 2, [pitch("A", 3)]),
        {
            "event_id": "alto-rest", "voice_id": "alto",
            "onset_quarters": "2", "duration_quarters": "2",
            "event_type": "rest", "confirmed_pitches": [],
        },
    ])
    root = parse(render_reviewed_timelines_musicxml([measure]))
    soprano_id = next(item.attrib["id"] for item in root.findall("part-list/score-part") if item.findtext("part-name") == "soprano")
    soprano = next(part for part in root.findall("part") if part.attrib["id"] == soprano_id)
    forward = soprano.find("measure/forward")
    assert forward is not None
    assert forward.findtext("duration") == "480"
    assert [item.findtext("pitch/step") for item in soprano.findall("measure/note")] == ["C", "D"]


def test_musicxml_cli_exports_timeline_json(tmp_path, capsys):
    import json
    from palermo_omr.musicxml_export_cli import main

    measure = timeline([note("whole", "alto", 0, 4, [pitch("C", 4)])])
    source = tmp_path / "reviewed.json"
    output = tmp_path / "out" / "reviewed.musicxml"
    source.write_text(json.dumps({"timelines": [measure]}), encoding="utf-8")
    assert main([str(source), str(output), "--title", "Reviewed score"]) == 0
    assert output.read_bytes().startswith(b"<?xml")
    assert "MusicXML exportado" in capsys.readouterr().out
