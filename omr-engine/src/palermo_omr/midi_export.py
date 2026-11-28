"""Exporta comandos polifónicos a Standard MIDI File (SMF) tipo 1.

Usa únicamente la biblioteca estándar. Conserva una pista/canal por voz,
ataques simultáneos y duraciones independientes. No sintetiza audio: el archivo
MIDI puede abrirse en un reproductor o sintetizador externo con soundfont.
"""
from __future__ import annotations

import math
import struct
from collections.abc import Mapping
from typing import Any


_DEFAULT_PROGRAM = 52  # GM Choir Aahs (numeración MIDI 0-based)
_DEFAULT_PAN = {
    "soprano": -0.72,
    "alto": -0.24,
    "tenor": 0.24,
    "bass": 0.72,
    "bajo": 0.72,
}
_DEFAULT_CHANNELS = tuple(channel for channel in range(16) if channel != 9)


def _vlq(value: int) -> bytes:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or value > 0x0FFFFFFF:
        raise ValueError("El delta MIDI debe estar entre 0 y 0x0FFFFFFF")
    buffer = value & 0x7F
    encoded = bytearray()
    while (value := value >> 7):
        buffer <<= 8
        buffer |= ((value & 0x7F) | 0x80)
    while True:
        encoded.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break
    return bytes(encoded)


def _meta(kind: int, payload: bytes) -> bytes:
    return bytes((0xFF, kind)) + _vlq(len(payload)) + payload


def _track_chunk(events: list[tuple[int, int, bytes]]) -> bytes:
    events.sort(key=lambda item: (item[0], item[1]))
    body = bytearray()
    previous_tick = 0
    for tick, _priority, message in events:
        body.extend(_vlq(tick - previous_tick))
        body.extend(message)
        previous_tick = tick
    body.extend(b"\x00\xFF\x2F\x00")
    return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def render_polyphonic_midi(
    command_stream: Mapping[str, Any],
    *,
    tempo_bpm: int | float = 120,
    ticks_per_quarter: int = 480,
    velocity: int = 88,
    default_program: int = _DEFAULT_PROGRAM,
    voice_programs: Mapping[str, int] | None = None,
    voice_channels: Mapping[str, int] | None = None,
    voice_pan: Mapping[str, float] | None = None,
) -> bytes:
    """Devuelve un archivo MIDI tipo 1 desde note_on/note_off en segundos.

    Cada voz obtiene canal y pista independientes. Se reserva el canal 10
    (índice 9) para percusión. Las notas repetidas de la misma altura dentro
    de una voz no pueden solaparse porque MIDI no permite emparejarlas por ID.
    """
    if not isinstance(command_stream, Mapping) or command_stream.get("status") != "unconfirmed_synth_command_stream":
        raise ValueError("Se requiere un flujo provisional de comandos de síntesis")
    if isinstance(tempo_bpm, bool) or not isinstance(tempo_bpm, (int, float)) or not math.isfinite(tempo_bpm) or not 20 <= tempo_bpm <= 300:
        raise ValueError("tempo_bpm debe estar entre 20 y 300")
    if isinstance(ticks_per_quarter, bool) or not isinstance(ticks_per_quarter, int) or not 24 <= ticks_per_quarter <= 9600:
        raise ValueError("ticks_per_quarter debe estar entre 24 y 9600")
    if isinstance(velocity, bool) or not isinstance(velocity, int) or not 1 <= velocity <= 127:
        raise ValueError("velocity debe estar entre 1 y 127")
    if isinstance(default_program, bool) or not isinstance(default_program, int) or not 0 <= default_program <= 127:
        raise ValueError("default_program debe estar entre 0 y 127")

    commands = command_stream.get("commands")
    if not isinstance(commands, (list, tuple)):
        raise ValueError("commands debe ser una lista")
    voices = set()
    active: dict[tuple[str, str, int], float] = {}
    active_pitch: set[tuple[str, int]] = set()
    intervals: list[tuple[str, int, int, int]] = []
    seen_commands: set[tuple[str, str, int, str]] = set()

    for command in commands:
        if not isinstance(command, Mapping):
            raise ValueError("Cada comando debe ser un objeto")
        kind = command.get("command")
        event_id = command.get("event_id")
        voice = command.get("voice_id")
        midi = command.get("midi")
        when = command.get("time_seconds")
        if kind not in {"note_on", "note_off"}:
            raise ValueError("Comando MIDI no soportado")
        if not isinstance(event_id, str) or not event_id.strip() or not isinstance(voice, str) or not voice.strip():
            raise ValueError("Cada comando necesita event_id y voice_id")
        if not isinstance(midi, int) or isinstance(midi, bool) or not 0 <= midi <= 127:
            raise ValueError("Nota MIDI fuera de rango")
        if isinstance(when, bool) or not isinstance(when, (int, float)) or not math.isfinite(when) or when < 0:
            raise ValueError("Tiempo de comando inválido")
        identity = (event_id, voice, midi, kind)
        if identity in seen_commands:
            raise ValueError("Comando duplicado")
        seen_commands.add(identity)
        voices.add(voice)
        key = (event_id, voice, midi)
        pitch_key = (voice, midi)
        when = float(when)
        if kind == "note_on":
            if key in active:
                raise ValueError("note_on duplicado para el mismo evento")
            if pitch_key in active_pitch:
                raise ValueError("Notas MIDI de igual altura se solapan dentro de una voz")
            active[key] = when
            active_pitch.add(pitch_key)
        else:
            if key not in active:
                raise ValueError("note_off sin note_on correspondiente")
            start = active.pop(key)
            active_pitch.remove(pitch_key)
            if when <= start:
                raise ValueError("note_off debe ocurrir después de note_on")
            start_tick = round(start * float(tempo_bpm) / 60.0 * ticks_per_quarter)
            end_tick = round(when * float(tempo_bpm) / 60.0 * ticks_per_quarter)
            if end_tick <= start_tick:
                raise ValueError("La duración es inferior a la resolución MIDI")
            intervals.append((voice, midi, start_tick, end_tick))

    if active:
        raise ValueError("Hay notas sin note_off")
    ordered_voices = sorted(voices)
    if len(ordered_voices) > len(_DEFAULT_CHANNELS):
        raise ValueError("MIDI admite como máximo 15 voces con canales separados")

    channels = {voice: _DEFAULT_CHANNELS[index] for index, voice in enumerate(ordered_voices)}
    if voice_channels is not None:
        if not isinstance(voice_channels, Mapping) or set(voice_channels) - voices:
            raise ValueError("voice_channels solo puede asignar voces existentes")
        used = set()
        for voice, channel in voice_channels.items():
            if not isinstance(channel, int) or isinstance(channel, bool) or channel not in _DEFAULT_CHANNELS:
                raise ValueError("Los canales deben estar entre 0 y 15, excepto el canal 10")
            if channel in used:
                raise ValueError("Cada voz debe usar un canal MIDI distinto")
            used.add(channel)
            channels[voice] = channel
        if len(set(channels.values())) != len(channels):
            raise ValueError("Dos voces no pueden compartir canal MIDI")

    programs = dict(voice_programs or {})
    if set(programs) - voices:
        raise ValueError("voice_programs solo puede configurar voces existentes")
    for program in programs.values():
        if not isinstance(program, int) or isinstance(program, bool) or not 0 <= program <= 127:
            raise ValueError("Los programas General MIDI deben estar entre 0 y 127")

    pans = dict(_DEFAULT_PAN)
    if voice_pan is not None:
        if not isinstance(voice_pan, Mapping) or set(voice_pan) - voices:
            raise ValueError("voice_pan solo puede configurar voces existentes")
        pans.update(voice_pan)
    for pan in (pans.get(voice, 0.0) for voice in ordered_voices):
        if isinstance(pan, bool) or not isinstance(pan, (int, float)) or not math.isfinite(pan) or not -1 <= pan <= 1:
            raise ValueError("El paneo de voz debe estar entre -1 y 1")

    micros_per_quarter = round(60_000_000 / float(tempo_bpm))
    conductor = [(0, 0, _meta(0x51, micros_per_quarter.to_bytes(3, "big")))]
    tracks = [_track_chunk(conductor)]
    intervals_by_voice: dict[str, list[tuple[int, int, int]]] = {voice: [] for voice in ordered_voices}
    for voice, midi, start_tick, end_tick in intervals:
        intervals_by_voice[voice].append((start_tick, end_tick, midi))

    for voice in ordered_voices:
        channel = channels[voice]
        name = voice.encode("utf-8")[:127]
        pan_value = round((pans.get(voice, 0.0) + 1.0) * 63.5)
        program = programs.get(voice, default_program)
        events = [
            (0, -3, _meta(0x03, name)),
            (0, -2, bytes((0xC0 | channel, program))),
            (0, -1, bytes((0xB0 | channel, 10, pan_value))),
        ]
        for start_tick, end_tick, midi in intervals_by_voice[voice]:
            events.append((start_tick, 1, bytes((0x90 | channel, midi, velocity))))
            events.append((end_tick, 0, bytes((0x80 | channel, midi, 0))))
        tracks.append(_track_chunk(events))

    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), ticks_per_quarter)
    return header + b"".join(tracks)
