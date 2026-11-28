"""CLI para exportar un paquete provisional de reproducción a Standard MIDI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .midi_export import render_polyphonic_midi, render_score_playback_bundle_midi


def _pair(value: str, separator: str, label: str):
    parts = value.split(separator)
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"{label} debe tener formato valor{separator}valor")
    return parts[0], parts[1]


def _parse_tempo_change(value: str) -> dict:
    time_text, bpm_text = _pair(value, ":", "--tempo-change")
    try:
        return {"time_seconds": float(time_text), "tempo_bpm": float(bpm_text)}
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--tempo-change requiere SEGUNDOS:BPM") from exc


def _parse_voice_value(value: str, label: str, converter):
    voice, raw = _pair(value, ":", label)
    if not voice.strip():
        raise argparse.ArgumentTypeError(f"{label} requiere un nombre de voz")
    try:
        return voice, converter(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Valor inválido para {label}") from exc


def _parse_meter(value: str) -> tuple[int, int]:
    numerator, denominator = _pair(value, "/", "--time-signature")
    try:
        return int(numerator), int(denominator)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--time-signature requiere NUMERADOR/DENOMINADOR") from exc


def _parse_key(value: str) -> tuple[int, int]:
    alterations, mode = _pair(value, ":", "--key-signature")
    try:
        sf = int(alterations)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--key-signature requiere ALTERACIONES:major|minor") from exc
    normalized_mode = mode.lower()
    if normalized_mode not in {"major", "minor"}:
        raise argparse.ArgumentTypeError("--key-signature requiere modo major o minor")
    return sf, 0 if normalized_mode == "major" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="palermo-omr-midi",
        description="Exporta un command stream o score playback bundle provisional a MIDI tipo 1.",
    )
    parser.add_argument("input", type=Path, help="JSON de command_stream o score playback bundle")
    parser.add_argument("output", type=Path, help="Archivo .mid de salida")
    parser.add_argument("--tempo-bpm", type=float, default=120)
    parser.add_argument("--ppq", type=int, default=480)
    parser.add_argument("--velocity", type=int, default=88)
    parser.add_argument("--program", type=int, default=52, help="Programa General MIDI 0-based (52 = Choir Aahs)")
    parser.add_argument("--time-signature", type=_parse_meter)
    parser.add_argument("--key-signature", type=_parse_key, help="ALTERACIONES:major|minor; por ejemplo 5:major")
    parser.add_argument("--tempo-change", action="append", type=_parse_tempo_change, default=[])
    parser.add_argument("--event-velocity", action="append", default=[], metavar="EVENTO:VELOCIDAD")
    parser.add_argument("--voice-program", action="append", default=[], metavar="VOZ:PROGRAMA")
    parser.add_argument("--voice-channel", action="append", default=[], metavar="VOZ:CANAL")
    parser.add_argument("--voice-pan", action="append", default=[], metavar="VOZ:VALOR")
    return parser


def _mapping_options(items, label, converter):
    result = {}
    for item in items:
        voice, value = _parse_voice_value(item, label, converter)
        if voice in result:
            raise ValueError(f"{label} repite la voz {voice}")
        result[voice] = value
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("El JSON raíz debe ser un objeto")
        event_velocities = _mapping_options(args.event_velocity, "--event-velocity", int)
        voice_programs = _mapping_options(args.voice_program, "--voice-program", int)
        voice_channels = _mapping_options(args.voice_channel, "--voice-channel", int)
        voice_pan = _mapping_options(args.voice_pan, "--voice-pan", float)
        options = {
            "tempo_bpm": args.tempo_bpm,
            "ticks_per_quarter": args.ppq,
            "velocity": args.velocity,
            "default_program": args.program,
            "voice_programs": voice_programs,
            "voice_channels": voice_channels,
            "voice_pan": voice_pan,
            "time_signature": args.time_signature,
            "key_signature": args.key_signature,
            "tempo_changes": args.tempo_change,
            "event_velocities": event_velocities,
        }
        if payload.get("status") == "unconfirmed_score_playback_bundle":
            midi = render_score_playback_bundle_midi(payload, **options)
        elif payload.get("status") == "unconfirmed_synth_command_stream":
            midi = render_polyphonic_midi(payload, **options)
        else:
            raise ValueError("El JSON no contiene un command stream ni un score playback bundle reconocido")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_bytes(midi)
        temporary.replace(args.output)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"palermo-omr-midi: {exc}", file=sys.stderr)
        return 2
    print(f"MIDI exportado: {args.output} ({len(midi)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
