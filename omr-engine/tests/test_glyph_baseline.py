import json
import pytest

from palermo_omr.glyph_baseline import predict_glyphs_nearest_centroid, write_glyph_predictions
from palermo_omr.glyph_features import FEATURE_SCHEMA


def write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_nearest_centroid_trains_only_on_train_scores_and_predicts_validation(tmp_path):
    features = {
        "feature_schema": FEATURE_SCHEMA,
        "records": [
            {"score_id": "s1", "candidate_id": "a", "label": "sharp", "feature_vector": [0.0, 0.0]},
            {"score_id": "s1", "candidate_id": "b", "label": "sharp", "feature_vector": [0.2, 0.0]},
            {"score_id": "s2", "candidate_id": "c", "label": "flat", "feature_vector": [10.0, 10.0]},
            {"score_id": "s2", "candidate_id": "d", "label": "flat", "feature_vector": [9.8, 10.0]},
            {"score_id": "s3", "candidate_id": "e", "label": "sharp", "feature_vector": [0.1, 0.0]},
        ],
    }
    split = {
        "split_method": "deterministic_group_by_score",
        "train_score_ids": ["s1", "s2"],
        "validation_score_ids": ["s3"],
        "train": [
            {"score_id": "s1", "candidate_id": "a", "label": "sharp"},
            {"score_id": "s2", "candidate_id": "c", "label": "flat"},
        ],
        "validation": [
            {"score_id": "s3", "candidate_id": "e", "label": "sharp"},
        ],
    }
    fp = write(tmp_path / "features.json", features)
    sp = write(tmp_path / "split.json", split)
    result = predict_glyphs_nearest_centroid(fp, sp)
    assert result["training_score_ids"] == ["s1", "s2"]
    assert result["validation_score_ids"] == ["s3"]
    assert result["predictions"][0]["label"] == "sharp"
    assert result["predictions"][0]["reference_label_for_offline_evaluation"] == "sharp"
    out = tmp_path / "predictions.json"
    write_glyph_predictions(result, out)
    assert json.loads(out.read_text())["classifier"] == "standardized_nearest_centroid_experimental"


def test_rejects_score_leakage_and_label_mismatch(tmp_path):
    features = {"feature_schema": FEATURE_SCHEMA, "records": [
        {"score_id": "s1", "candidate_id": "a", "label": "sharp", "feature_vector": [1.0]},
        {"score_id": "s2", "candidate_id": "b", "label": "flat", "feature_vector": [2.0]},
    ]}
    split = {
        "split_method": "deterministic_group_by_score",
        "train_score_ids": ["s1"], "validation_score_ids": ["s2"],
        "train": [{"score_id": "s1", "candidate_id": "a", "label": "natural"}],
        "validation": [{"score_id": "s2", "candidate_id": "b", "label": "flat"}],
    }
    with pytest.raises(ValueError, match="no coincide"):
        predict_glyphs_nearest_centroid(
            write(tmp_path / "features.json", features),
            write(tmp_path / "split.json", split),
        )


def test_rejects_invalid_feature_values(tmp_path):
    features = {"feature_schema": FEATURE_SCHEMA, "records": [
        {"score_id": "s1", "candidate_id": "a", "label": "sharp", "feature_vector": [float("nan")]},
    ]}
    split = {
        "split_method": "deterministic_group_by_score",
        "train_score_ids": ["s1"], "validation_score_ids": ["s2"],
        "train": [{"score_id": "s1", "candidate_id": "a", "label": "sharp"}],
        "validation": [{"score_id": "s2", "candidate_id": "b", "label": "sharp"}],
    }
    with pytest.raises(ValueError, match="no finito"):
        predict_glyphs_nearest_centroid(
            write(tmp_path / "features.json", features),
            write(tmp_path / "split.json", split),
        )
