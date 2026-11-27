"""Predice clases de glifos nuevos con un modelo experimental."""
from __future__ import annotations

import argparse
import sys

from .glyph_inference import predict_unlabeled_glyphs, write_json_atomic


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="palermo-omr-glyph-predict")
    parser.add_argument("--model", required=True)
    parser.add_argument("--features", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        result = predict_unlabeled_glyphs(args.model, args.features)
        write_json_atomic(result, args.output)
        print(f"Predicciones experimentales guardadas: {args.output}; {result['prediction_count']} glifos")
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
