"""Clasificador experimental nearest-centroid para glifos; no es un OMR completo."""
from __future__ import annotations

import json
import math
from pathlib import Path

from .glyph_features import FEATURE_SCHEMA


def _load(path: str | Path) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"El documento {path} debe ser un objeto JSON")
    return value


def _feature_index(features: dict) -> dict:
    if features.get("feature_schema") != FEATURE_SCHEMA:
        raise ValueError("Esquema de características incompatible")
    records = features.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("No hay registros de características")
    index = {}
    dimension = None
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Cada registro de características debe ser un objeto")
        key = (record.get("score_id"), record.get("candidate_id"))
        if not all(isinstance(part, str) and part for part in key):
            raise ValueError("Cada registro requiere score_id y candidate_id")
        if key in index:
            raise ValueError(f"Registro de características duplicado: {key}")
        vector = record.get("feature_vector")
        if not isinstance(vector, list) or not vector:
            raise ValueError(f"Vector ausente o vacío para {key}")
        if dimension is None:
            dimension = len(vector)
        if len(vector) != dimension:
            raise ValueError("Los vectores tienen dimensiones diferentes")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector):
            raise ValueError(f"Vector no numérico o no finito para {key}")
        index[key] = (record.get("label"), [float(v) for v in vector])
    return index


def predict_glyphs_nearest_centroid(features_path: str | Path, split_path: str | Path) -> dict:
    """Ajusta centroides solo con partituras de entrenamiento y predice validación."""
    features = _load(features_path)
    split = _load(split_path)
    index = _feature_index(features)
    if split.get("split_method") != "deterministic_group_by_score":
        raise ValueError("El split debe agrupar partituras completas")
    train = split.get("train")
    validation = split.get("validation")
    if not isinstance(train, list) or not isinstance(validation, list) or not train or not validation:
        raise ValueError("El split requiere registros train y validation no vacíos")
    train_scores = set(split.get("train_score_ids", []))
    validation_scores = set(split.get("validation_score_ids", []))
    if not train_scores or not validation_scores or train_scores & validation_scores:
        raise ValueError("Partituras de entrenamiento y validación inválidas o solapadas")

    def get_vectors(rows, expected_scores):
        result = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Cada registro del split debe ser un objeto")
            key = (row.get("score_id"), row.get("candidate_id"))
            if key in seen:
                raise ValueError(f"Glifo duplicado en split: {key}")
            seen.add(key)
            if key[0] not in expected_scores:
                raise ValueError(f"Registro fuera de su partición: {key}")
            if key not in index:
                raise ValueError(f"Falta descriptor para {key}")
            label, vector = index[key]
            if label != row.get("label"):
                raise ValueError(f"Etiqueta no coincide entre split y descriptor para {key}")
            result.append((key, label, vector))
        return result

    train_rows = get_vectors(train, train_scores)
    validation_rows = get_vectors(validation, validation_scores)
    train_keys = {row[0] for row in train_rows}
    validation_keys = {row[0] for row in validation_rows}
    if train_keys & validation_keys:
        raise ValueError("Un mismo glifo aparece en entrenamiento y validación")

    dimension = len(train_rows[0][2])
    means = [sum(row[2][i] for row in train_rows) / len(train_rows) for i in range(dimension)]
    variances = [
        sum((row[2][i] - means[i]) ** 2 for row in train_rows) / len(train_rows)
        for i in range(dimension)
    ]
    scales = [math.sqrt(value) if value > 1e-12 else 1.0 for value in variances]

    def normalize(vector):
        return [(vector[i] - means[i]) / scales[i] for i in range(dimension)]

    by_class: dict[str, list[list[float]]] = {}
    for _, label, vector in train_rows:
        if not isinstance(label, str) or not label:
            raise ValueError("Etiqueta de entrenamiento ausente")
        by_class.setdefault(label, []).append(normalize(vector))
    centroids = {
        label: [sum(vector[i] for vector in vectors) / len(vectors) for i in range(dimension)]
        for label, vectors in sorted(by_class.items())
    }
    predictions = []
    for key, _, vector in validation_rows:
        normalized = normalize(vector)
        distances = {
            label: math.sqrt(sum((normalized[i] - centroid[i]) ** 2 for i in range(dimension)))
            for label, centroid in centroids.items()
        }
        predicted_label = min(distances, key=distances.get)
        predictions.append({
            "score_id": key[0],
            "candidate_id": key[1],
            "label": predicted_label,
            "nearest_centroid_distance": round(distances[predicted_label], 8),
        })
    return {
        "schema_version": "1.0",
        "classifier": "standardized_nearest_centroid_experimental",
        "feature_schema": FEATURE_SCHEMA,
        "training_score_ids": sorted(train_scores),
        "validation_score_ids": sorted(validation_scores),
        "training_record_count": len(train_rows),
        "validation_record_count": len(validation_rows),
        "class_centroid_count": len(centroids),
        "predictions": predictions,
        "warning": "Prototipo experimental. La distancia no es una probabilidad ni una confianza calibrada. Validar con corpus musical real antes de cualquier uso.",
    }


def write_glyph_predictions(predictions: dict, output_path: str | Path) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(predictions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
