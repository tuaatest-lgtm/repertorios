import struct

import pytest

from palermo_omr.midi_export import render_polyphonic_midi


def stream(commands):
    return {"status": "unconfirmed_synth_command_stream", "commands": commands}


def cmd(kind, event, voice, midi, when):
    return {
        "command": kind, "event_id": event, "voice_id": voice,
        "midi": midi, "time_seconds": when,
    }


def chunks(data):
    assert data[:4] == b"MThd"
    header_length, fmt, count, ppq = struct.unpack(">IHHH", data[4:14])
    assert header_length == 6
    pos = 14
    result = []
    for _ in range(count):
        assert data[pos:pos + 4] == b"MTrk"
        length = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        result.append(data[pos + 8:pos + 8 + length])
        pos += 8 + length
    assert pos == len(data)
    return fmt, count, ppq, result


def parse_track(track):
    events = []
    pos = 0
    tick = 0
    while pos < len(track):
        delta = 0
        while True:
            byte = track[pos]
            pos += 1
            delta = (delta << 7) | (byte & 0x7F)
            if not byte & 0x80:
                break
        tick += delta
        status = track[pos]
        pos += 1
        if status == 0xFF:
            kind = track[pos]
            pos += 1
            length = track[pos]
            pos += 1
            payload = track[pos:pos + length]
            pos += length
            events.append((tick, "meta", kind, payload))
            if kind == 0x2F:
                break
        elif status & 0xF0 in (0x80, 0x90, 0xB0, 0xC0):
            command = status & 0xF0
            channel = status & 0x0F
            first = track[pos]
            pos += 1
            second = None
            if command != 0xC0:
                second = track[pos]
                pos += 1
            events.append((tick, command, channel, first, second))
        else:
            raise AssertionError(f"Unsupported MIDI status byte {status:#x}")
    return events


def test_exports_type_one_midi_with_independent_tracks_and_simultaneous_voices():
    commands = [
        cmd("note_on", "s1", "soprano", 72, 0.0),
        cmd("note_on", "a1", "alto", 60, 0.0),
        cmd("note_off", "a1", "alto", 60, 0.5),
        cmd("note_off", "s1", "soprano", 72, 1.0),
    ]
    data = render_polyphonic_midi(stream(commands), tempo_bpm=120)
    fmt, count, ppq, tracks = chunks(data)
    assert (fmt, count, ppq) == (1, 3, 480)
    soprano = parse_track(tracks[1])
    alto = parse_track(tracks[2])
    soprano_notes = [event for event in soprano if isinstance(event[1], int) and event[1] in (0x80, 0x90)]
    alto_notes = [event for event in alto if isinstance(event[1], int) and event[1] in (0x80, 0x90)]
    assert [(e[0], e[1], e[3]) for e in soprano_notes] == [(0, 0x90, 72), (960, 0x80, 72)]
    assert [(e[0], e[1], e[3]) for e in alto_notes] == [(0, 0x90, 60), (480, 0x80, 60)]


def test_chord_expands_to_simultaneous_midi_note_events():
    commands = [
        cmd("note_on", "chord", "tenor", 60, 0),
        cmd("note_on", "chord", "tenor", 64, 0),
        cmd("note_on", "chord", "tenor", 67, 0),
        cmd("note_off", "chord", "tenor", 60, 1),
        cmd("note_off", "chord", "tenor", 64, 1),
        cmd("note_off", "chord", "tenor", 67, 1),
    ]
    _, _, _, tracks = chunks(render_polyphonic_midi(stream(commands)))
    note_events = [e for e in parse_track(tracks[1]) if isinstance(e[1], int) and e[1] in (0x80, 0x90)]
    assert [(e[0], e[1], e[3]) for e in note_events] == [
        (0, 0x90, 60), (0, 0x90, 64), (0, 0x90, 67),
        (960, 0x80, 60), (960, 0x80, 64), (960, 0x80, 67),
    ]


def test_note_off_precedes_repeated_same_pitch_note_on_at_same_tick():
    commands = [
        cmd("note_on", "first", "alto", 60, 0),
        cmd("note_off", "first", "alto", 60, 1),
        cmd("note_on", "second", "alto", 60, 1),
        cmd("note_off", "second", "alto", 60, 2),
    ]
    _, _, _, tracks = chunks(render_polyphonic_midi(stream(commands)))
    notes = [e for e in parse_track(tracks[1]) if isinstance(e[1], int) and e[1] in (0x80, 0x90)]
    assert [(e[0], e[1]) for e in notes] == [(0, 0x90), (960, 0x80), (960, 0x90), (1920, 0x80)]


def test_assigns_distinct_channels_and_general_midi_choir_program():
    commands = [
        cmd("note_on", "s", "soprano", 72, 0),
        cmd("note_off", "s", "soprano", 72, 1),
        cmd("note_on", "a", "alto", 60, 0),
        cmd("note_off", "a", "alto", 60, 1),
    ]
    _, _, _, tracks = chunks(render_polyphonic_midi(stream(commands)))
    soprano = parse_track(tracks[1])
    alto = parse_track(tracks[2])
    soprano_program = next(e for e in soprano if isinstance(e[1], int) and e[1] == 0xC0)
    alto_program = next(e for e in alto if isinstance(e[1], int) and e[1] == 0xC0)
    assert soprano_program[3] == alto_program[3] == 52
    assert soprano_program[2] != alto_program[2]
    assert soprano_program[2] != 9 and alto_program[2] != 9


def test_conductor_track_contains_tempo_meta_event():
    data = render_polyphonic_midi(stream([]), tempo_bpm=100)
    _, count, _, tracks = chunks(data)
    assert count == 1
    tempo = next(e for e in parse_track(tracks[0]) if e[1] == "meta" and e[2] == 0x51)
    assert int.from_bytes(tempo[3], "big") == 600000


def test_voice_program_channel_and_pan_overrides_are_applied():
    commands = [
        cmd("note_on", "n", "soprano", 72, 0),
        cmd("note_off", "n", "soprano", 72, 1),
    ]
    _, _, _, tracks = chunks(render_polyphonic_midi(
        stream(commands), voice_programs={"soprano": 40},
        voice_channels={"soprano": 3}, voice_pan={"soprano": 1.0},
    ))
    events = parse_track(tracks[1])
    assert (0, 0xC0, 3, 40, None) in events
    assert (0, 0xB0, 3, 10, 127) in events


@pytest.mark.parametrize("commands", [
    [cmd("note_off", "x", "alto", 60, 1)],
    [cmd("note_on", "x", "alto", 60, 0)],
    [cmd("note_on", "x", "alto", 60, 0), cmd("note_on", "y", "alto", 60, 0)],
    [cmd("note_on", "x", "alto", 60, 0), cmd("note_off", "x", "alto", 60, 0)],
])
def test_rejects_unmatched_or_unrepresentable_note_lifecycles(commands):
    with pytest.raises(ValueError):
        render_polyphonic_midi(stream(commands))


def test_rejects_reserved_or_duplicate_voice_channels_and_bad_options():
    commands = [
        cmd("note_on", "s", "soprano", 72, 0),
        cmd("note_off", "s", "soprano", 72, 1),
        cmd("note_on", "a", "alto", 60, 0),
        cmd("note_off", "a", "alto", 60, 1),
    ]
    with pytest.raises(ValueError, match="canal 10"):
        render_polyphonic_midi(stream(commands), voice_channels={"soprano": 9})
    with pytest.raises(ValueError, match="distinto"):
        render_polyphonic_midi(stream(commands), voice_channels={"soprano": 2, "alto": 2})
    with pytest.raises(ValueError, match="tempo_bpm"):
        render_polyphonic_midi(stream(commands), tempo_bpm=0)
    with pytest.raises(ValueError, match="velocity"):
        render_polyphonic_midi(stream(commands), velocity=0)
