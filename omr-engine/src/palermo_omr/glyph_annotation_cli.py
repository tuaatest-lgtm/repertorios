"""CLI para crear, etiquetar y validar el corpus de glifos musicales."""
from __future__ import annotations

import argparse
import sys

from .glyph_labeling import (
    GLYPH_LABELS,
    initialize_glyph_manifest,
    label_glyph,
    validate_glyph_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="palermo-omr-glyphs",
        description="Gestiona etiquetas humanas de claves y alteraciones candidatas.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="Crea un manifiesto desde analysis.json")
    init.add_argument("analysis")
    init.add_argument("--score-id", required=True)
    init.add_argument("--output", required=True)

    label = commands.add_parser("label", help="Etiqueta un glifo tras revisión visual")
    label.add_argument("manifest")
    label.add_argument("--candidate-id", required=True)
    label.add_argument("--label", required=True, choices=sorted(GLYPH_LABELS))
    label.add_argument("--annotator", required=True)
    label.add_argument("--confirm-human-label", action="store_true")

    validate = commands.add_parser("validate", help="Valida el manifiesto y sus contadores")
    validate.add_argument("manifest")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            manifest = initialize_glyph_manifest(
                args.analysis, args.output, score_id=args.score_id
            )
            print(f"Manifiesto creado: {args.output}")
            print(f"Glifos: {manifest['glyph_count']} (pendientes: {manifest['pending_count']})")
        elif args.command == "label":
            manifest = label_glyph(
                args.manifest, args.candidate_id, args.label,
                annotator=args.annotator,
                human_label_confirmed=args.confirm_human_label,
            )
            print(f"Etiqueta humana registrada: {args.candidate_id} = {args.label}")
            print(f"Pendientes: {manifest['pending_count']}")
        elif args.command == "validate":
            manifest = validate_glyph_manifest(args.manifest)
            print(
                f"Manifiesto válido: {manifest['glyph_count']} glifos, "
                f"{manifest['labeled_count']} etiquetados, "
                f"{manifest['pending_count']} pendientes"
            )
        return 0
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
