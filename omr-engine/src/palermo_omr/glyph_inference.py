"""Entrenamiento e inferencia experimental de glifos con centroides."""
from __future__ import annotations

import json
import math
from pathlib import Path

from .glyph_features import FEATURE_SCHEMA


def _read(path: str | Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No se pudo leer {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"El documento {path} debe ser un objeto")
    return data


def _records(features: dict) -> dict:
    if features.get("feature_schema") != FEATURE_SCHEMA:
        raise ValueError("Esquema de características incompatible")
    records = features.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("No hay registros de características")
    result = {}
    dimension = None
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("Registro de características inválido")
        key = (row.get("score_id"), row.get("candidate_id"))
        if not all(isinstance(v, str) and v for v in key):
            raise ValueError("Cada registro requiere score_id y candidate_id")
        if key in result:
            raise ValueError(f"Registro duplicado: {key}")
        vector = row.get("feature_vector")
        if not isinstance(vector, list) or not vector:
            raise ValueError(f"Vector vacío para {key}")
        if dimension is None:
            dimension = len(vector)
        if len(vector) != dimension:
            raise ValueError("Dimensiones de características inconsistentes")
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in vector):
            raise ValueError(f"Vector no numérico o no finito para {key}")
        result[key] = (row.get("label"), [float(v) for v in vector])
    return result


def train_glyph_model(features_path: str | Path, split_path: str | Path) -> dict:
    """Ajusta normalización y centroides usando exclusivamente la partición train."""
    features = _records(_read(features_path))
    split = _read(split_path)
    if split.get("split_method") != "deterministic_group_by_score":
        raise ValueError("Se requiere split agrupado por partitura")
    train = split.get("train")
    train_scores = set(split.get("train_score_ids", []))
    validation_scores = set(split.get("validation_score_ids", []))
    if not isinstance(train, list) or not train or not train_scores or not validation_scores:
        raise ValueError("El split debe contener entrenamiento y validación")
    if train_scores & validation_scores:
        raise ValueError("Fuga entre partituras de entrenamiento y validación")
    vectors = []
    seen = set()
    for row in train:
        key = (row.get("score_id"), row.get("candidate_id"))
        if key in seen:
            raise ValueError(f"Glifo duplicado en entrenamiento: {key}")
        seen.add(key)
        if key[0] not in train_scores or key not in features:
            raise ValueError(f"Registro de entrenamiento fuera del split o sin descriptor: {key}")
        label, vector = features[key]
        if not isinstance(label, str) or not label or label != row.get("label"):
            raise ValueError(f"Etiqueta de entrenamiento inválida o inconsistente: {key}")
        vectors.append((label, vector))
    dimension = len(vectors[0][1])
    means = [sum(vector[i] for _, vector in vectors) / len(vectors) for i in range(dimension)]
    variances = [
        sum((vector[i] - means[i]) ** 2 for _, vector in vectors) / len(vectors)
        for i in range(dimension)
    ]
    scales = [math.sqrt(value) if value > 1e-12 else 1.0 for value in variances]

    def normalize(vector):
        return [(vector[i] - means[i]) / scales[i] for i in range(dimension)]

    grouped: dict[str, list[list[float]]] = {}
    for label, vector in vectors:
        grouped.setdefault(label, []).append(normalize(vector))
    centroids = {
        label: [
            sum(vector[i] for vector in samples) / len(samples)
            for i in range(dimension)
        ]
        for label, samples in sorted(grouped.items())
    }
    return {
        "schema_version": "1.0",
        "model_type": "palermo_standardized_nearest_centroid",
        "feature_schema": FEATURE_SCHEMA,
        "feature_dimension": dimension,
        "training_score_ids": sorted(train_scores),
        "training_sample_count": len(vectors),
        "class_sample_counts": {label: len(samples) for label, samples in sorted(grouped.items())},
        "means": means,
        "scales": scales,
        "centroids": centroids,
        "warning": "Modelo experimental. Requiere corpus musical real y evaluación independiente. Distancias no calibradas; no son probabilidades.",
    }


def predict_unlabeled_glyphs(model_path: str | Path, features_path: str | Path) -> dict:
    """Clasifica recortes nuevos; no requiere ni consulta etiquetas de esos recortes."""
    model = _read(model_path)
    if model.get("model_type") != "palermo_standardized_nearest_centroid":
        raise ValueError("Tipo de modelo incompatible")
    if model.get("feature_schema") != FEATURE_SCHEMA:
        raise ValueError("Esquema de características del modelo incompatible")
    centroids = model.get("centroids")
    means, scales = model.get("means"), model.get("scales")
    dimension = model.get("feature_dimension")
    if (
        not isinstance(centroids, dict) or not centroids
        or not isinstance(means, list) or not isinstance(scales, list)
        or not isinstance(dimension, int) or dimension < 1
        or len(means) != dimension or len(scales) != dimension
    ):
        raise ValueError("Modelo incompleto o mal formado")
    for label, centroid in centroids.items():
        if (
            not isinstance(label, str) or not label
            or not isinstance(centroid, list) or len(centroid) != dimension
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in centroid)
        ):
            raise ValueError("Centroide inválido")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in means + scales):
        raise ValueError("Normalización del modelo inválida")
    if any(v <= 0 for v in scales):
        raise ValueError("Escalas del modelo deben ser positivas")
    records = _records(_read(features_path))
    predictions = []
    for (score_id, candidate_id), (_, vector) in sorted(records.items()):
        if len(vector) != dimension:
            raise ValueError(f"Dimensión incorrecta para {(score_id, candidate_id)}")
        normalized = [(vector[i] - means[i]) / scales[i] for i in range(dimension)]
        distances = {
            label: math.sqrt(sum((normalized[i] - center[i]) ** 2 for i in range(dimension)))
            for label, center in centroids.items()
        }
        ranked = sorted(distances.items(), key=lambda item: (item[1], item[0]))
        candidate_label, nearest_distance = ranked[0]
        second_distance = ranked[1][1] if len(ranked) > 1 else None
        predictions.append({
            "score_id": score_id,
            "candidate_id": candidate_id,
            # "label" se conserva como candidato para compatibilidad con el evaluador;
            # nunca representa una decisión musical confirmada.
            "label": candidate_label,
            "candidate_label": candidate_label,
            "decision_status": "unverified_candidate_requires_review",
            "recognized_label": None,
            "nearest_centroid_distance": round(nearest_distance, 8),
            "second_nearest_centroid_distance": round(second_distance, 8) if second_distance is not None else None,
            "distance_margin": round(second_distance - nearest_distance, 8) if second_distance is not None else None,
        })
    return {
        "schema_version": "1.0",
        "classifier": model["model_type"],
        "feature_schema": FEATURE_SCHEMA,
        "prediction_count": len(predictions),
        "predictions": predictions,
        "warning": "Los labels son candidatos experimentales, no reconocimientos confirmados. Toda predicción requiere revisión humana; las distancias y márgenes no son probabilidades ni umbrales calibrados.",
    }


def write_json_atomic(value: dict, output_path: str | Path) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)
