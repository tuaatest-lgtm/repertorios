"""CLI de preparación de particiones de corpus por partitura."""
from __future__ import annotations

import argparse
import sys

from .glyph_dataset import build_score_group_split, write_score_group_split


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="palermo-omr-glyph-dataset")
    sub = parser.add_subparsers(dest="command", required=True)
    split = sub.add_parser("split", help="Divide corpus por partitura, sin fuga de páginas")
    split.add_argument("manifests", nargs="+")
    split.add_argument("--validation-fraction", type=float, default=0.2)
    split.add_argument("--seed", default="palermo-omr-v1")
    split.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        result = build_score_group_split(
            args.manifests,
            validation_fraction=args.validation_fraction,
            seed=args.seed,
        )
        write_score_group_split(result, args.output)
        print(
            f"Partición guardada: {args.output}; "
            f"{len(result['train_score_ids'])} partituras de entrenamiento, "
            f"{len(result['validation_score_ids'])} de validación; "
            f"{result['train_count']} y {result['validation_count']} glifos etiquetados"
        )
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
