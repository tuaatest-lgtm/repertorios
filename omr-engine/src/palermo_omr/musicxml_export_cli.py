"""CLI para exportar líneas temporales revisadas a MusicXML."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .musicxml_export import render_reviewed_timelines_musicxml


def _key_signature(value: str) -> tuple[int, str]:
    parts = value.split(":")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("--key-signature requiere ALTERACIONES:major|minor")
    try:
        fifths = int(parts[0])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("ALTERACIONES debe ser un entero entre -7 y 7") from exc
    mode = parts[1].lower()
    if mode not in {"major", "minor"}:
        raise argparse.ArgumentTypeError("El modo debe ser major o minor")
    return fifths, mode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="palermo-omr-musicxml",
        description="Exporta líneas temporales musicales revisadas a MusicXML 4.0.",
    )
    parser.add_argument("input", type=Path, help="JSON con una lista de líneas temporales o un objeto {timelines: [...]}")
    parser.add_argument("output", type=Path, help="Archivo .musicxml de salida")
    parser.add_argument("--title", default="Palermo Music score")
    parser.add_argument("--tempo-bpm", type=float)
    parser.add_argument("--key-signature", type=_key_signature)
    parser.add_argument("--global-measure-numbers", type=Path, help="JSON que mapea 'pagina:indice' a número global")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            timelines = payload.get("timelines")
        else:
            timelines = payload
        if not isinstance(timelines, list):
            raise ValueError("La entrada debe ser una lista o contener la propiedad timelines")
        measure_numbers = None
        if args.global_measure_numbers is not None:
            measure_numbers = json.loads(args.global_measure_numbers.read_text(encoding="utf-8"))
            if not isinstance(measure_numbers, dict):
                raise ValueError("global-measure-numbers debe contener un objeto JSON")
        musicxml = render_reviewed_timelines_musicxml(
            timelines,
            title=args.title,
            tempo_bpm=args.tempo_bpm,
            key_signature=args.key_signature,
            global_measure_numbers=measure_numbers,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_bytes(musicxml)
        temporary.replace(args.output)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"palermo-omr-musicxml: {exc}", file=sys.stderr)
        return 2
    print(f"MusicXML exportado: {args.output} ({len(musicxml)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
