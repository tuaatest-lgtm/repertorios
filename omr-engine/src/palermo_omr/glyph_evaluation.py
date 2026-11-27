"""Evaluación de predicciones de glifos contra etiquetas humanas verificadas."""
from __future__ import annotations

import json
from pathlib import Path
from collections import Counter

from .glyph_labeling import GLYPH_LABELS, validate_glyph_manifest_data


def _read_json(path: str | Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer {path}: {exc}") from exc


def _write_json(path: str | Path, value: dict) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    temporary.replace(destination)


def evaluate_glyph_predictions(manifest_paths: list[str | Path], predictions_path: str | Path) -> dict:
    """Evalúa predicciones; la ausencia de predicción cuenta como abstención, nunca como acierto."""
    truth: dict[tuple[str, str], str] = {}
    for path in manifest_paths:
        manifest = _read_json(path)
        validate_glyph_manifest_data(manifest)
        score_id = manifest["score_id"]
        for glyph in manifest["glyphs"]:
            if glyph["label_status"] != "labeled_by_human":
                continue
            key = (score_id, glyph["candidate_id"])
            if key in truth:
                raise ValueError(f"Glifo duplicado en manifiestos: {key}")
            truth[key] = glyph["label"]
    if not truth:
        raise ValueError("No hay etiquetas humanas para evaluar")

    payload = _read_json(predictions_path)
    predictions = payload.get("predictions") if isinstance(payload, dict) else payload
    if not isinstance(predictions, list):
        raise ValueError("El archivo de predicciones debe contener una lista 'predictions'")
    predicted: dict[tuple[str, str], str | None] = {}
    for item in predictions:
        if not isinstance(item, dict):
            raise ValueError("Cada predicción debe ser un objeto")
        score_id, candidate_id = item.get("score_id"), item.get("candidate_id")
        if not isinstance(score_id, str) or not score_id or not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("Cada predicción requiere score_id y candidate_id")
        key = (score_id, candidate_id)
        if key in predicted:
            raise ValueError(f"Predicción duplicada: {key}")
        if key not in truth:
            raise ValueError(f"Predicción sin etiqueta humana correspondiente: {key}")
        label = item.get("label")
        if label in (None, "abstain", "unclassified"):
            label = None
        elif label not in GLYPH_LABELS:
            raise ValueError(f"Clase predicha no permitida para {key}: {label}")
        confidence = item.get("confidence")
        if confidence is not None and (
            isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1
        ):
            raise ValueError(f"confidence debe estar entre 0 y 1 para {key}")
        predicted[key] = label

    labels = sorted(set(truth.values()))
    matrix_labels = sorted(set(labels) | {label for label in predicted.values() if label is not None})
    matrix = {actual: {guess: 0 for guess in matrix_labels + ["abstain"]} for actual in labels}
    support = Counter(truth.values())
    correct = 0
    covered = 0
    per_class = {}
    for key, actual in truth.items():
        guess = predicted.get(key)
        matrix[actual]["abstain" if guess is None else guess] += 1
        if guess is not None:
            covered += 1
            correct += int(guess == actual)
    for label in labels:
        tp = matrix[label].get(label, 0)
        fp = sum(matrix[other].get(label, 0) for other in labels if other != label)
        fn = sum(matrix[label].values()) - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / support[label] if support[label] else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "support": support[label],
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1": round(f1, 6),
        }
    macro_f1 = sum(item["f1"] for item in per_class.values()) / len(per_class)
    total = len(truth)
    return {
        "schema_version": "1.0",
        "evaluation_method": "human_labeled_glyphs",
        "ground_truth_count": total,
        "prediction_count": len(predicted),
        "covered_count": covered,
        "abstained_count": total - covered,
        "coverage": round(covered / total, 6),
        "correct_count": correct,
        "accuracy_all": round(correct / total, 6),
        "accuracy_covered": round(correct / covered, 6) if covered else 0.0,
        "macro_f1_observed_classes": round(macro_f1, 6),
        "class_metrics": per_class,
        "confusion_matrix": matrix,
        "unpredicted_count": total - len(predicted),
        "note": "Las métricas describen solo este conjunto etiquetado; no garantizan generalización a otras partituras.",
    }


def write_glyph_evaluation(report: dict, output_path: str | Path) -> None:
    _write_json(output_path, report)
