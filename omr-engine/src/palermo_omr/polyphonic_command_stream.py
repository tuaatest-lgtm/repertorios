"""Conversión de agenda temporal en comandos polifónicos de síntesis.

Este módulo no abre dispositivos ni produce audio: genera comandos ordenados
note_on/note_off para que un backend de síntesis los ejecute. La identidad de
voz se conserva para que el backend pueda aislar canales o instancias.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


def build_polyphonic_command_stream(projection: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(projection, Mapping):
        raise ValueError("projection debe ser un objeto")
    if projection.get("status") != "unconfirmed_playback_projection":
        raise ValueError("La proyección debe proceder del constructor provisional de reproducción")

    commands: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for event in projection.get("events", []):
        if not isinstance(event, Mapping):
            raise ValueError("Cada evento de reproducción debe ser un objeto")
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip() or event_id in seen_ids:
            raise ValueError("Los event_id de reproducción deben ser únicos y no vacíos")
        seen_ids.add(event_id)
        kind = event.get("event_type", "note")
        voice_id = event.get("voice_id")
        start = event.get("start_seconds")
        duration = event.get("duration_seconds")
        if not isinstance(voice_id, str) or not voice_id.strip():
            skipped.append({"event_id": event_id, "reason": "missing_voice"})
            continue
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
               for value in (start, duration)) or start < 0 or duration <= 0:
            skipped.append({"event_id": event_id, "reason": "invalid_timing"})
            continue
        if kind == "rest":
            continue
        if kind != "note":
            skipped.append({"event_id": event_id, "reason": "unsupported_event_type"})
            continue
        pitches = event.get("midi_notes")
        if not isinstance(pitches, (list, tuple)) or not pitches:
            skipped.append({"event_id": event_id, "reason": "missing_pitch"})
            continue
        if any(not isinstance(pitch, int) or isinstance(pitch, bool) or not 0 <= pitch <= 127
               for pitch in pitches):
            skipped.append({"event_id": event_id, "reason": "invalid_midi_pitch"})
            continue

        end = float(start) + float(duration)
        for pitch in pitches:
            common = {
                "event_id": event_id,
                "voice_id": voice_id,
                "midi": pitch,
            }
            commands.append({
                **common, "command": "note_off", "time_seconds": end,
                "sort_priority": 0,
            })
            commands.append({
                **common, "command": "note_on", "time_seconds": float(start),
                "sort_priority": 1,
            })

    commands.sort(key=lambda item: (
        item["time_seconds"], item["sort_priority"], item["voice_id"],
        item["midi"], item["event_id"]
    ))
    for index, command in enumerate(commands):
        command["sequence"] = index
        command.pop("sort_priority")
    return {
        "status": "unconfirmed_synth_command_stream",
        "commands": commands,
        "skipped_events": sorted(skipped, key=lambda item: item["event_id"]),
        "warning": (
            "Comandos de síntesis provisionales; requieren un backend de audio. "
            "La voz se conserva para separar instancias/canales y evitar que "
            "una voz silencie accidentalmente otra."
        ),
    }
