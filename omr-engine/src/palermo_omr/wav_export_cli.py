"""CLI para renderizar paquetes de reproducción a WAV estéreo."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .wav_renderer import render_polyphonic_wav, render_score_playback_bundle_wav


def _voice_pan(value: str) -> tuple[str, float]:
    parts = value.split(":")
    if len(parts) != 2 or not parts[0].strip():
        raise argparse.ArgumentTypeError("--voice-pan requiere VOZ:VALOR")
    try:
        return parts[0], float(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--voice-pan requiere VOZ:VALOR numérico") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="palermo-omr-wav",
        description="Renderiza un command stream o score playback bundle a WAV PCM16 estéreo.",
    )
    parser.add_argument("input", type=Path, help="JSON de command stream o score playback bundle")
    parser.add_argument("output", type=Path, help="Archivo WAV de salida")
    parser.add_argument("--sample-rate", type=int, default=22050)
    parser.add_argument("--gain", type=float, default=0.22)
    parser.add_argument("--max-duration", type=float, default=180.0)
    parser.add_argument("--voice-pan", action="append", type=_voice_pan, default=[], metavar="VOZ:VALOR")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("El JSON raíz debe ser un objeto")
        pans = {}
        for voice, pan in args.voice_pan:
            if voice in pans:
                raise ValueError(f"--voice-pan repite la voz {voice}")
            pans[voice] = pan
        options = {
            "sample_rate": args.sample_rate,
            "gain": args.gain,
            "voice_pan": pans,
            "max_duration_seconds": args.max_duration,
        }
        if payload.get("status") == "unconfirmed_score_playback_bundle":
            wav_data = render_score_playback_bundle_wav(payload, **options)
        elif payload.get("status") == "unconfirmed_synth_command_stream":
            wav_data = render_polyphonic_wav(payload, **options)
        else:
            raise ValueError("El JSON no contiene un command stream ni un score playback bundle reconocido")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_bytes(wav_data)
        temporary.replace(args.output)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"palermo-omr-wav: {exc}", file=sys.stderr)
        return 2
    print(f"WAV exportado: {args.output} ({len(wav_data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
