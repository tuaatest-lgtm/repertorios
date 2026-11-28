"""Controlador determinista de reproducción para un backend de audio externo.

El host llama tick() desde su reloj/scheduler. El controlador no crea hilos ni
bloquea la interfaz: conserva el tiempo musical absoluto entre páginas y
gestiona lifecycle y mute por voz. El sink implementa note_on/off/all_notes_off.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, Protocol


class AudioCommandSink(Protocol):
    def note_on(self, voice_id: str, midi: int, event_id: str) -> None: ...
    def note_off(self, voice_id: str, midi: int, event_id: str) -> None: ...
    def all_notes_off(self) -> None: ...


class PlaybackController:
    """Reproductor por ticks con pausa/reanudación y aislamiento de voces."""

    def __init__(self, command_stream: Mapping[str, Any], sink: AudioCommandSink):
        if not isinstance(command_stream, Mapping) or command_stream.get("status") != "unconfirmed_synth_command_stream":
            raise ValueError("Se requiere un flujo provisional de comandos")
        if not all(callable(getattr(sink, name, None)) for name in ("note_on", "note_off", "all_notes_off")):
            raise ValueError("El sink debe implementar note_on, note_off y all_notes_off")
        commands = command_stream.get("commands")
        if not isinstance(commands, list):
            raise ValueError("commands debe ser una lista")
        normalized: list[dict[str, Any]] = []
        last_key: tuple[float, int] | None = None
        for command in commands:
            if not isinstance(command, Mapping):
                raise ValueError("Cada comando debe ser un objeto")
            kind = command.get("command")
            when = command.get("time_seconds")
            voice, event_id, midi = command.get("voice_id"), command.get("event_id"), command.get("midi")
            if kind not in {"note_on", "note_off"}:
                raise ValueError("Comando no soportado")
            if isinstance(when, bool) or not isinstance(when, (int, float)) or not math.isfinite(when) or when < 0:
                raise ValueError("time_seconds inválido")
            if not isinstance(voice, str) or not voice or not isinstance(event_id, str) or not event_id:
                raise ValueError("voice_id y event_id son obligatorios")
            if isinstance(midi, bool) or not isinstance(midi, int) or not 0 <= midi <= 127:
                raise ValueError("MIDI fuera de rango")
            item = dict(command)
            item["time_seconds"] = float(when)
            normalized.append(item)
        normalized.sort(key=lambda c: (
            c["time_seconds"], 0 if c["command"] == "note_off" else 1,
            c["voice_id"], c["midi"], c["event_id"]
        ))
        self._commands = normalized
        self._sink = sink
        self._index = 0
        self._elapsed = 0.0
        self._anchor: float | None = None
        self._state = "stopped"
        self._muted: set[str] = set()
        self._active: dict[tuple[str, str, int], dict[str, Any]] = {}

    @property
    def state(self) -> str:
        return self._state

    @property
    def current_seconds(self) -> float:
        if self._state == "playing" and self._anchor is not None:
            return max(0.0, self._anchor)
        return self._elapsed

    @property
    def muted_voices(self) -> tuple[str, ...]:
        return tuple(sorted(self._muted))

    def play(self, now: float = 0.0) -> None:
        self._validate_clock(now)
        self.stop()
        self._elapsed = 0.0
        self._anchor = float(now)
        self._state = "playing"
        self.tick(now)

    def pause(self, now: float) -> None:
        self._validate_clock(now)
        if self._state != "playing":
            return
        self.tick(now)
        self._elapsed = max(0.0, float(now) - float(self._anchor))
        self._anchor = None
        self._state = "paused"
        self._sink.all_notes_off()

    def resume(self, now: float) -> None:
        self._validate_clock(now)
        if self._state != "paused":
            return
        self._anchor = float(now) - self._elapsed
        self._state = "playing"
        for note in self._active.values():
            if note["voice_id"] not in self._muted:
                self._sink.note_on(note["voice_id"], note["midi"], note["event_id"])

    def stop(self) -> None:
        self._sink.all_notes_off()
        self._index = 0
        self._elapsed = 0.0
        self._anchor = None
        self._active.clear()
        self._state = "stopped"

    def set_voice_muted(self, voice_id: str, muted: bool) -> None:
        if not isinstance(voice_id, str) or not voice_id.strip() or not isinstance(muted, bool):
            raise ValueError("voice_id y muted inválidos")
        if muted:
            if voice_id in self._muted:
                return
            self._muted.add(voice_id)
            for note in self._active.values():
                if note["voice_id"] == voice_id:
                    self._sink.note_off(voice_id, note["midi"], note["event_id"])
        else:
            if voice_id not in self._muted:
                return
            self._muted.remove(voice_id)
            if self._state in {"playing", "paused"}:
                for note in self._active.values():
                    if note["voice_id"] == voice_id:
                        self._sink.note_on(voice_id, note["midi"], note["event_id"])

    def tick(self, now: float) -> dict[str, Any]:
        self._validate_clock(now)
        if self._state != "playing":
            return self.snapshot()
        elapsed = max(0.0, float(now) - float(self._anchor))
        while self._index < len(self._commands) and self._commands[self._index]["time_seconds"] <= elapsed:
            command = self._commands[self._index]
            key = (command["event_id"], command["voice_id"], command["midi"])
            if command["command"] == "note_on":
                if key in self._active:
                    raise ValueError("note_on duplicado en el flujo")
                self._active[key] = command
                if command["voice_id"] not in self._muted:
                    self._sink.note_on(command["voice_id"], command["midi"], command["event_id"])
            else:
                note = self._active.pop(key, None)
                if note is None:
                    raise ValueError("note_off sin note_on activo")
                if command["voice_id"] not in self._muted:
                    self._sink.note_off(command["voice_id"], command["midi"], command["event_id"])
            self._index += 1
        self._elapsed = elapsed
        if self._index == len(self._commands) and not self._active:
            self._state = "finished"
            self._anchor = None
            self._sink.all_notes_off()
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self._state,
            "current_seconds": self._elapsed,
            "processed_commands": self._index,
            "total_commands": len(self._commands),
            "active_notes": len(self._active),
            "muted_voices": list(self.muted_voices),
        }

    @staticmethod
    def _validate_clock(now: float) -> None:
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
            raise ValueError("El reloj debe ser un número finito")
