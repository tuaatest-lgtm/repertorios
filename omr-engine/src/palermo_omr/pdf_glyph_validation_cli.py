"""CLI de evaluación geométrica contra glifos vectoriales del PDF."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from .pdf_glyph_validation import evaluate_pdf_glyph_noteheads

def main() -> int:
    parser = argparse.ArgumentParser(prog="palermo-omr-pdf-glyph-evaluate")
    parser.add_argument("pdf")
    parser.add_argument("analysis")
    parser.add_argument("--output", default="pdf-glyph-evaluation.json")
    parser.add_argument("--font", default="RepriseStd")
    parser.add_argument("--glyph", default="œ")
    parser.add_argument("--tolerance-points", type=float, default=3.0)
    args = parser.parse_args()
    result = evaluate_pdf_glyph_noteheads(
        args.pdf, args.analysis, tolerance_points=args.tolerance_points,
        font_name=args.font, glyph_char=args.glyph,
    )
    output = Path(args.output)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Evaluación guardada: {output}")
    print(f"Cabezas: {result['true_positive']} TP, {result['false_positive']} FP, {result['false_negative']} FN; precision={result['precision']}, recall={result['recall']}, F1={result['f1']}")
    print("Aviso: métrica geométrica de cabezas; no es precisión musical global.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
