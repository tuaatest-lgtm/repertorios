"""CLI para auditar cobertura geométrica y candidatos de análisis OMR."""
from __future__ import annotations

import argparse
import csv
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
    parser.add_argument("--queue-csv", type=Path, help="Exporta la cola rítmica priorizada a CSV")
    parser.add_argument("--symbol-queue-csv", type=Path, help="Exporta la cola de silencios, ligaduras y haces a CSV")
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
        if args.queue_csv is not None:
            args.queue_csv.parent.mkdir(parents=True, exist_ok=True)
            queue_temporary = args.queue_csv.with_suffix(args.queue_csv.suffix + ".tmp")
            fields = [
                "candidate_id", "page_number", "candidate_index", "staff_index",
                "center_x", "center_y", "confidence", "stem_direction",
                "base_duration", "beam_count", "interpretation_status",
                "review_reasons", "priority",
            ]
            with queue_temporary.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for item in report["rhythm_review_queue"]:
                    row = {key: item.get(key) for key in fields}
                    row["review_reasons"] = ";".join(item["review_reasons"])
                    writer.writerow(row)
            queue_temporary.replace(args.queue_csv)
        if args.symbol_queue_csv is not None:
            args.symbol_queue_csv.parent.mkdir(parents=True, exist_ok=True)
            symbol_temporary = args.symbol_queue_csv.with_suffix(args.symbol_queue_csv.suffix + ".tmp")
            symbol_fields = [
                "candidate_id", "page_number", "family", "candidate_index",
                "staff_index", "confidence", "candidate_type",
                "review_reasons", "priority",
            ]
            with symbol_temporary.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=symbol_fields)
                writer.writeheader()
                for item in report["symbol_review_queue"]:
                    row = {key: item.get(key) for key in symbol_fields}
                    row["review_reasons"] = ";".join(item["review_reasons"])
                    writer.writerow(row)
            symbol_temporary.replace(args.symbol_queue_csv)
    except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"palermo-omr-audit: {exc}", file=sys.stderr)
        return 2
    totals = report["totals"]
    coverage = totals["measure_span_unique_coverage"]
    percentage = f"{coverage * 100:.2f}%" if coverage is not None else "n/a"
    print(
        f"Auditoría exportada: {args.output}; "
        f"{totals['filled_notehead_candidates']} cabezas; "
        f"ubicación única en compás: {percentage}; "
        f"pendientes rítmicos: {report['rhythm_review_queue_count']}; "
        f"símbolos: {report['symbol_review_queue_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
