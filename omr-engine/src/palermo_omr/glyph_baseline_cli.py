"""CLI del clasificador experimental de glifos."""
from __future__ import annotations

import argparse
import sys

from .glyph_baseline import predict_glyphs_nearest_centroid, write_glyph_predictions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="palermo-omr-glyph-baseline")
    parser.add_argument("--features", required=True, help="JSON generado por palermo-omr-glyph-features")
    parser.add_argument("--split", required=True, help="Split por partitura generado por glyph-dataset")
    parser.add_argument("--output", required=True, help="JSON de predicciones para evaluación")
    args = parser.parse_args(argv)
    try:
        result = predict_glyphs_nearest_centroid(args.features, args.split)
        write_glyph_predictions(result, args.output)
        print(
            f"Predicciones experimentales guardadas: {args.output}; "
            f"{result['validation_record_count']} glifos; "
            f"{result['class_centroid_count']} centroides"
        )
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
