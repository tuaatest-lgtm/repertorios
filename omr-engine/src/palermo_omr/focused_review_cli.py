"""CLI para extraer un fragmento acotado de un paquete de revisión."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .focused_review import build_focused_review_package


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="palermo-omr-focus-review",
        description="Selecciona una página y pentagramas para revisión humana.",
    )
    parser.add_argument("review_package")
    parser.add_argument("--page", type=int, required=True)
    parser.add_argument(
        "--staff-indices", required=True,
        help="Índices de pentagrama separados por coma, empezando en cero.",
    )
    parser.add_argument("--label", default="Fragmento seleccionado")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        raw = json.loads(Path(args.review_package).read_text(encoding="utf-8"))
        try:
            indices = [int(value.strip()) for value in args.staff_indices.split(",")]
        except ValueError as exc:
            raise ValueError("--staff-indices debe ser una lista de enteros separados por coma") from exc
        focused = build_focused_review_package(
            raw,
            page_number=args.page,
            staff_indices=indices,
            scope_label=args.label,
        )
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(
            json.dumps(focused, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(destination)
        print("Fragmento de revisión creado: {}".format(destination))
        print("Candidatos pendientes: {}".format(focused["summary"]["pending_candidate_count"]))
        print("Eventos confirmados: 0; no es ground truth.")
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print("Error: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
