"""Exporta descriptores de glifos etiquetados para experimentación reproducible."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .glyph_features import FEATURE_SCHEMA, extract_glyph_features, resolve_crop_path
from .glyph_labeling import validate_glyph_manifest_data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="palermo-omr-glyph-features")
    parser.add_argument("manifests", nargs="+", help="Manifiestos de glifos")
    parser.add_argument("--crop-root", required=True, help="Raíz que contiene las rutas crop_file")
    parser.add_argument("--output", required=True, help="JSON de descriptores")
    args = parser.parse_args(argv)
    try:
        records = []
        seen = set()
        for manifest_path in args.manifests:
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
            validate_glyph_manifest_data(manifest)
            for glyph in manifest["glyphs"]:
                if glyph["label_status"] != "labeled_by_human":
                    continue
                key = (manifest["score_id"], glyph["candidate_id"])
                if key in seen:
                    raise ValueError(f"Glifo duplicado entre manifiestos: {key}")
                seen.add(key)
                crop_path = resolve_crop_path(args.crop_root, glyph["crop_file"])
                descriptor = extract_glyph_features(crop_path)
                records.append({
                    "score_id": manifest["score_id"],
                    "candidate_id": glyph["candidate_id"],
                    "page_number": glyph["page_number"],
                    "staff_index": glyph["staff_index"],
                    "label": glyph["label"],
                    "crop_file": glyph["crop_file"],
                    **descriptor,
                })
        if not records:
            raise ValueError("No hay glifos etiquetados para extraer descriptores")
        output = {
            "schema_version": "1.0",
            "feature_schema": FEATURE_SCHEMA,
            "record_count": len(records),
            "records": records,
            "note": "Descriptores geométricos experimentales; no son clases musicales ni predicciones.",
        }
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(destination)
        print(f"Descriptores guardados: {destination}; {len(records)} glifos")
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
