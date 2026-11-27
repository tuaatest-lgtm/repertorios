"""Preparación de corpus sin fuga de información entre partituras."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from .glyph_labeling import validate_glyph_manifest_data


def build_score_group_split(
    manifest_paths: list[str | Path],
    *,
    validation_fraction: float = 0.2,
    seed: str = "palermo-omr-v1",
) -> dict:
    """Divide partituras completas; ninguna página de una partitura cruza particiones."""
    if not 0.0 < validation_fraction < 1.0:
        raise ValueError("validation_fraction debe estar entre 0 y 1")
    if not isinstance(seed, str) or not seed:
        raise ValueError("seed no puede estar vacío")
    score_records: dict[str, list[dict]] = {}
    for path in manifest_paths:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
        validate_glyph_manifest_data(manifest)
        score_id = manifest["score_id"]
        if score_id in score_records:
            raise ValueError(f"score_id duplicado en manifiestos: {score_id}")
        labeled = [g for g in manifest["glyphs"] if g["label_status"] == "labeled_by_human"]
        if not labeled:
            raise ValueError(f"La partitura {score_id} no tiene etiquetas humanas")
        score_records[score_id] = [
            {
                "score_id": score_id,
                "candidate_id": glyph["candidate_id"],
                "page_number": glyph["page_number"],
                "staff_index": glyph["staff_index"],
                "crop_file": glyph["crop_file"],
                "label": glyph["label"],
                "annotator": glyph["annotator"],
            }
            for glyph in labeled
        ]
    if len(score_records) < 2:
        raise ValueError("Se requieren al menos dos partituras distintas para evitar fuga entre entrenamiento y validación")
    ordered = sorted(
        score_records,
        key=lambda score_id: hashlib.sha256(f"{seed}:{score_id}".encode("utf-8")).hexdigest(),
    )
    validation_count = max(1, min(len(ordered) - 1, round(len(ordered) * validation_fraction)))
    validation_ids = set(ordered[:validation_count])
    train_ids = set(ordered[validation_count:])
    train_records = [row for score_id in sorted(train_ids) for row in score_records[score_id]]
    validation_records = [row for score_id in sorted(validation_ids) for row in score_records[score_id]]
    if {r["score_id"] for r in train_records} & {r["score_id"] for r in validation_records}:
        raise RuntimeError("Fuga de partituras detectada entre particiones")
    return {
        "schema_version": "1.0",
        "split_method": "deterministic_group_by_score",
        "seed": seed,
        "validation_fraction": validation_fraction,
        "train_score_ids": sorted(train_ids),
        "validation_score_ids": sorted(validation_ids),
        "train_count": len(train_records),
        "validation_count": len(validation_records),
        "train_label_counts": dict(sorted(Counter(r["label"] for r in train_records).items())),
        "validation_label_counts": dict(sorted(Counter(r["label"] for r in validation_records).items())),
        "train": train_records,
        "validation": validation_records,
    }


def write_score_group_split(split: dict, output_path: str | Path) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(split, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    temporary.replace(destination)
