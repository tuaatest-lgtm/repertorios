"""CLI para evaluar clasificadores de glifos contra anotaciones humanas."""
from __future__ import annotations

import argparse
import sys

from .glyph_evaluation import evaluate_glyph_predictions, write_glyph_evaluation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="palermo-omr-glyph-evaluate")
    parser.add_argument("manifests", nargs="+", help="Manifiestos con etiquetas humanas")
    parser.add_argument("--predictions", required=True, help="JSON con predicciones del clasificador")
    parser.add_argument("--output", required=True, help="Informe JSON de métricas")
    args = parser.parse_args(argv)
    try:
        report = evaluate_glyph_predictions(args.manifests, args.predictions)
        write_glyph_evaluation(report, args.output)
        print(
            f"Evaluación guardada: {args.output}; "
            f"{report['correct_count']}/{report['ground_truth_count']} aciertos; "
            f"cobertura {report['coverage']:.1%}; "
            f"macro-F1 {report['macro_f1_observed_classes']:.3f}"
        )
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
