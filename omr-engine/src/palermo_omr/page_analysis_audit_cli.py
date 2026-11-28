"""CLI para auditar cobertura geométrica y candidatos de análisis OMR."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .page_analysis_audit import audit_page_analysis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="palermo-omr-audit",
        description="Resume candidatos geométricos y rítmicos sin atribuirles precisión musical.",
    )
    parser.add_argument("analysis", type=Path, help="Archivo JSON de análisis multipágina")
    parser.add_argument("output", type=Path, help="Archivo JSON de auditoría")
    parser.add_argument("--low-confidence", type=float, default=0.60)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        analysis = json.loads(args.analysis.read_text(encoding="utf-8"))
        report = audit_page_analysis(
            analysis, low_confidence_threshold=args.low_confidence
        )
        encoded = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_bytes(encoded)
        temporary.replace(args.output)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"palermo-omr-audit: {exc}", file=sys.stderr)
        return 2
    totals = report["totals"]
    coverage = totals["measure_span_unique_coverage"]
    percentage = f"{coverage * 100:.2f}%" if coverage is not None else "n/a"
    print(
        f"Auditoría exportada: {args.output}; "
        f"{totals['filled_notehead_candidates']} cabezas; "
        f"ubicación única en compás: {percentage}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
