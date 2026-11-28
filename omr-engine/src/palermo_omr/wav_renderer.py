"""Renderizador WAV polifónico mínimo, sin dependencias externas.

Sintetiza cada nota MIDI como senoide con envolvente corta anti-clic y paneo
por voz. Está pensado como backend de verificación y no como instrumento final.
"""
from __future__ import annotations

import io
import math
import struct
import wave
from collections.abc import Mapping
from typing import Any


_DEFAULT_PAN = {
    "soprano": -0.72,
    "alto": -0.24,
    "tenor": 0.24,
    "bass": 0.72,
    "bajo": 0.72,
}


def render_polyphonic_wav(
    command_stream: Mapping[str, Any],
    *,
    sample_rate: int = 22050,
    gain: float = 0.22,
    voice_pan: Mapping[str, float] | None = None,
    max_duration_seconds: float = 180.0,
) -> bytes:
    """Devuelve bytes WAV estéreo PCM16 desde un flujo note_on/note_off."""
    if not isinstance(command_stream, Mapping) or command_stream.get("status") != "unconfirmed_synth_command_stream":
        raise ValueError("Se requiere un flujo provisional de comandos de síntesis")
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, int) or not 8000 <= sample_rate <= 96000:
        raise ValueError("sample_rate debe estar entre 8000 y 96000 Hz")
    if isinstance(gain, bool) or not isinstance(gain, (int, float)) or not math.isfinite(gain) or not 0 < gain <= 1:
        raise ValueError("gain debe estar entre 0 y 1")
    if not math.isfinite(max_duration_seconds) or not 0 < max_duration_seconds <= 600:
        raise ValueError("max_duration_seconds debe estar entre 0 y 600")

    pans = dict(_DEFAULT_PAN)
    if voice_pan:
        for voice, pan in voice_pan.items():
            if not isinstance(voice, str) or not voice.strip() or isinstance(pan, bool) or not isinstance(pan, (int, float)) or not math.isfinite(pan) or not -1 <= pan <= 1:
                raise ValueError("voice_pan requiere voces válidas y paneo entre -1 y 1")
            pans[voice] = float(pan)

    active: dict[tuple[str, str, int], float] = {}
    notes: list[tuple[str, str, int, float, float]] = []
    for command in command_stream.get("commands", []):
        if not isinstance(command, Mapping):
            raise ValueError("Cada comando debe ser un objeto")
        kind = command.get("command")
        event_id, voice, midi = command.get("event_id"), command.get("voice_id"), command.get("midi")
        when = command.get("time_seconds")
        if kind not in {"note_on", "note_off"}:
            raise ValueError("Comando no soportado")
        if not isinstance(event_id, str) or not event_id or not isinstance(voice, str) or not voice:
            raise ValueError("Cada comando necesita event_id y voice_id")
        if not isinstance(midi, int) or isinstance(midi, bool) or not 0 <= midi <= 127:
            raise ValueError("Nota MIDI fuera de rango")
        if isinstance(when, bool) or not isinstance(when, (int, float)) or not math.isfinite(when) or when < 0:
            raise ValueError("Tiempo de comando inválido")
        key = (event_id, voice, midi)
        when = float(when)
        if kind == "note_on":
            if key in active:
                raise ValueError(f"note_on duplicado para {key}")
            active[key] = when
        else:
            if key not in active:
                raise ValueError(f"note_off sin note_on para {key}")
            start = active.pop(key)
            if when <= start:
                raise ValueError("note_off debe ocurrir después de note_on")
            notes.append((event_id, voice, midi, start, when))
    if active:
        raise ValueError("Hay notas sin note_off")
    end_time = max((note[4] for note in notes), default=0.0)
    if end_time > max_duration_seconds:
        raise ValueError("La duración excede el límite del renderizador")
    frame_count = max(1, math.ceil(end_time * sample_rate))
    if frame_count > sample_rate * max_duration_seconds:
        raise ValueError("El audio excede el límite de muestras")

    left = [0.0] * frame_count
    right = [0.0] * frame_count
    attack_frames = max(1, int(sample_rate * 0.004))
    release_frames = max(1, int(sample_rate * 0.008))
    per_note_gain = float(gain) / math.sqrt(max(1, len(notes)))

    for _, voice, midi, start, end in notes:
        first = max(0, int(round(start * sample_rate)))
        last = min(frame_count, int(math.ceil(end * sample_rate)))
        if last <= first:
            continue
        pan = float(pans.get(voice, 0.0))
        left_gain = math.sqrt((1.0 - pan) / 2.0) * per_note_gain
        right_gain = math.sqrt((1.0 + pan) / 2.0) * per_note_gain
        frequency = 440.0 * (2.0 ** ((midi - 69) / 12.0))
        phase_step = 2.0 * math.pi * frequency / sample_rate
        for frame in range(first, last):
            elapsed = frame - first
            remaining = last - frame
            envelope = min(1.0, elapsed / attack_frames, remaining / release_frames)
            sample = math.sin(phase_step * elapsed) * max(0.0, envelope)
            left[frame] += sample * left_gain
            right[frame] += sample * right_gain

    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        pcm = bytearray()
        for l_sample, r_sample in zip(left, right):
            l_int = int(max(-1.0, min(1.0, l_sample)) * 32767)
            r_int = int(max(-1.0, min(1.0, r_sample)) * 32767)
            pcm.extend(struct.pack("<hh", l_int, r_int))
        wav.writeframes(bytes(pcm))
    return output.getvalue()
