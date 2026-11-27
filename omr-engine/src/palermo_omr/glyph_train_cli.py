"""Entrena y exporta el modelo visual experimental de glifos."""
from __future__ import annotations

import argparse
import sys

from .glyph_inference import train_glyph_model, write_json_atomic


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="palermo-omr-glyph-train")
    parser.add_argument("--features", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        model = train_glyph_model(args.features, args.split)
        write_json_atomic(model, args.output)
        print(f"Modelo experimental guardado: {args.output}; {model['training_sample_count']} muestras; {len(model['centroids'])} clases")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
