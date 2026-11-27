"""Manifiestos auditables para etiquetado humano de glifos del preámbulo."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath

GLYPH_LABELS = frozenset({
    "treble_clef", "bass_clef", "alto_clef", "tenor_clef",
    "sharp", "flat", "natural", "double_sharp", "double_flat",
    "other", "unreadable",
})


def _read_json(path: str | Path) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("El documento JSON debe ser un objeto")
    return value


def _write_json(path: str | Path, value: dict) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)


def _safe_crop_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Cada glifo debe incluir crop_file")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("crop_file debe ser una ruta relativa sin '..'")
    return path.as_posix()


def initialize_glyph_manifest(
    analysis_path: str | Path,
    output_path: str | Path,
    *,
    score_id: str,
) -> dict:
    """Crea un manifiesto de glifos pendientes desde analysis.json."""
    if not isinstance(score_id, str) or not score_id.strip():
        raise ValueError("score_id no puede estar vacío")
    output = Path(output_path)
    if output.exists():
        raise ValueError(f"El manifiesto ya existe y no se sobrescribirá: {output}")
    analysis = _read_json(analysis_path)
    pages = analysis.get("pages")
    if not isinstance(pages, list):
        raise ValueError("analysis.json debe contener una lista 'pages'")
    glyphs = []
    seen = set()
    for page_index, page in enumerate(pages, start=1):
        if not isinstance(page, dict):
            raise ValueError("Cada página de analysis.json debe ser un objeto")
        page_number = page.get("page_number", page_index)
        exports = page.get("notation_preamble_crop_exports", [])
        if not isinstance(exports, list):
            raise ValueError("notation_preamble_crop_exports debe ser una lista")
        for item in exports:
            if not isinstance(item, dict):
                raise ValueError("Cada recorte exportado debe ser un objeto")
            crop_file = _safe_crop_path(item.get("crop_file"))
            candidate_id = PurePosixPath(crop_file).stem
            if candidate_id in seen:
                raise ValueError(f"candidate_id duplicado: {candidate_id}")
            seen.add(candidate_id)
            bbox = item.get("candidate_bbox")
            if not isinstance(bbox, list) or len(bbox) != 4 or any(
                not isinstance(number, int) or number < 0 for number in bbox
            ):
                raise ValueError(f"Bounding box inválido para {candidate_id}")
            staff_index = item.get("staff_index")
            if not isinstance(staff_index, int) or staff_index < 0:
                raise ValueError(f"staff_index inválido para {candidate_id}")
            glyphs.append({
                "candidate_id": candidate_id,
                "page_number": page_number,
                "staff_index": staff_index,
                "candidate_bbox": bbox,
                "crop_file": crop_file,
                "label": None,
                "label_status": "pending_human_review",
                "annotator": None,
                "labeled_at": None,
            })
    manifest = {
        "schema_version": "1.0",
        "score_id": score_id,
        "source_pdf": analysis.get("source_pdf"),
        "engine_status": analysis.get("status"),
        "label_vocabulary": sorted(GLYPH_LABELS),
        "glyph_count": len(glyphs),
        "labeled_count": 0,
        "pending_count": len(glyphs),
        "glyphs": glyphs,
    }
    validate_glyph_manifest_data(manifest)
    _write_json(output, manifest)
    return manifest


def validate_glyph_manifest_data(manifest: dict) -> dict:
    if manifest.get("schema_version") != "1.0":
        raise ValueError("schema_version debe ser 1.0")
    if not isinstance(manifest.get("score_id"), str) or not manifest["score_id"].strip():
        raise ValueError("score_id no puede estar vacío")
    glyphs = manifest.get("glyphs")
    if not isinstance(glyphs, list):
        raise ValueError("glyphs debe ser una lista")
    seen = set()
    labeled = 0
    for glyph in glyphs:
        if not isinstance(glyph, dict):
            raise ValueError("Cada glifo debe ser un objeto")
        candidate_id = glyph.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id.strip() or candidate_id in seen:
            raise ValueError("candidate_id ausente o duplicado")
        seen.add(candidate_id)
        _safe_crop_path(glyph.get("crop_file"))
        if not isinstance(glyph.get("page_number"), int) or glyph["page_number"] < 1:
            raise ValueError(f"page_number inválido en {candidate_id}")
        if not isinstance(glyph.get("staff_index"), int) or glyph["staff_index"] < 0:
            raise ValueError(f"staff_index inválido en {candidate_id}")
        status = glyph.get("label_status")
        label = glyph.get("label")
        if status == "pending_human_review":
            if label is not None or glyph.get("annotator") is not None or glyph.get("labeled_at") is not None:
                raise ValueError(f"Glifo pendiente con datos de etiqueta: {candidate_id}")
        elif status == "labeled_by_human":
            if label not in GLYPH_LABELS:
                raise ValueError(f"Etiqueta no permitida en {candidate_id}: {label}")
            if not isinstance(glyph.get("annotator"), str) or not glyph["annotator"].strip():
                raise ValueError(f"Falta annotator en {candidate_id}")
            if not isinstance(glyph.get("labeled_at"), str) or not glyph["labeled_at"]:
                raise ValueError(f"Falta labeled_at en {candidate_id}")
            labeled += 1
        else:
            raise ValueError(f"label_status inválido en {candidate_id}")
    if manifest.get("glyph_count") != len(glyphs):
        raise ValueError("glyph_count no coincide con glyphs")
    if manifest.get("labeled_count") != labeled:
        raise ValueError("labeled_count no coincide con etiquetas humanas")
    if manifest.get("pending_count") != len(glyphs) - labeled:
        raise ValueError("pending_count no coincide con glifos pendientes")
    return manifest


def label_glyph(
    manifest_path: str | Path,
    candidate_id: str,
    label: str,
    *,
    annotator: str,
    human_label_confirmed: bool,
) -> dict:
    """Aplica una etiqueta solo con confirmación humana explícita."""
    if not human_label_confirmed:
        raise ValueError("Se requiere --confirm-human-label para registrar una etiqueta humana")
    if label not in GLYPH_LABELS:
        raise ValueError(f"Etiqueta no permitida: {label}")
    if not isinstance(annotator, str) or not annotator.strip():
        raise ValueError("annotator no puede estar vacío")
    manifest = _read_json(manifest_path)
    validate_glyph_manifest_data(manifest)
    matches = [item for item in manifest["glyphs"] if item["candidate_id"] == candidate_id]
    if len(matches) != 1:
        raise ValueError(f"No existe un único glifo con candidate_id={candidate_id}")
    glyph = matches[0]
    if glyph["label_status"] != "pending_human_review":
        raise ValueError(f"El glifo ya tiene etiqueta humana: {candidate_id}")
    glyph.update({
        "label": label,
        "label_status": "labeled_by_human",
        "annotator": annotator.strip(),
        "labeled_at": datetime.now(timezone.utc).isoformat(),
    })
    manifest["labeled_count"] += 1
    manifest["pending_count"] -= 1
    validate_glyph_manifest_data(manifest)
    _write_json(manifest_path, manifest)
    return manifest


def validate_glyph_manifest(path: str | Path) -> dict:
    manifest = _read_json(path)
    return validate_glyph_manifest_data(manifest)
