import json

import pytest

from palermo_omr.glyph_features import FEATURE_SCHEMA
from palermo_omr.glyph_inference import (
    predict_unlabeled_glyphs,
    train_glyph_model,
    write_json_atomic,
)


def put(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_train_model_and_predict_unlabeled_candidates_without_using_labels(tmp_path):
    features = {
        "feature_schema": FEATURE_SCHEMA,
        "records": [
            {"score_id": "train-a", "candidate_id": "a", "label": "sharp", "feature_vector": [0.0, 0.0]},
            {"score_id": "train-b", "candidate_id": "b", "label": "flat", "feature_vector": [10.0, 10.0]},
        ],
    }
    split = {
        "split_method": "deterministic_group_by_score",
        "train_score_ids": ["train-a", "train-b"],
        "validation_score_ids": ["held-out"],
        "train": [
            {"score_id": "train-a", "candidate_id": "a", "label": "sharp"},
            {"score_id": "train-b", "candidate_id": "b", "label": "flat"},
        ],
        "validation": [{"score_id": "held-out", "candidate_id": "truth", "label": "sharp"}],
    }
    model = train_glyph_model(
        put(tmp_path / "features.json", features),
        put(tmp_path / "split.json", split),
    )
    model_path = tmp_path / "model.json"
    write_json_atomic(model, model_path)
    unseen = {
        "feature_schema": FEATURE_SCHEMA,
        "records": [
            {"score_id": "new-score", "candidate_id": "new-1", "label": None, "feature_vector": [0.1, 0.0]},
            {"score_id": "new-score", "candidate_id": "new-2", "label": None, "feature_vector": [9.9, 10.0]},
        ],
    }
    result = predict_unlabeled_glyphs(
        model_path,
        put(tmp_path / "unseen.json", unseen),
    )
    assert [row["label"] for row in result["predictions"]] == ["sharp", "flat"]
    assert all("reference_label" not in row for row in result["predictions"])


def test_training_rejects_overlap_between_score_partitions(tmp_path):
    features = {"feature_schema": FEATURE_SCHEMA, "records": [
        {"score_id": "same", "candidate_id": "a", "label": "sharp", "feature_vector": [1.0]},
    ]}
    split = {
        "split_method": "deterministic_group_by_score",
        "train_score_ids": ["same"], "validation_score_ids": ["same"],
        "train": [{"score_id": "same", "candidate_id": "a", "label": "sharp"}],
        "validation": [{"score_id": "same", "candidate_id": "b", "label": "sharp"}],
    }
    with pytest.raises(ValueError, match="Fuga"):
        train_glyph_model(
            put(tmp_path / "features.json", features),
            put(tmp_path / "split.json", split),
        )


def test_inference_rejects_feature_dimension_mismatch(tmp_path):
    model = {
        "model_type": "palermo_standardized_nearest_centroid",
        "feature_schema": FEATURE_SCHEMA,
        "feature_dimension": 2,
        "means": [0.0, 0.0],
        "scales": [1.0, 1.0],
        "centroids": {"sharp": [0.0, 0.0]},
    }
    features = {"feature_schema": FEATURE_SCHEMA, "records": [
        {"score_id": "s", "candidate_id": "a", "label": None, "feature_vector": [0.0]},
    ]}
    with pytest.raises(ValueError, match="Dimensión"):
        predict_unlabeled_glyphs(
            put(tmp_path / "model.json", model),
            put(tmp_path / "features.json", features),
        )
