import json
import pytest

from palermo_omr.glyph_evaluation import evaluate_glyph_predictions, write_glyph_evaluation


def manifest(path):
    glyphs = [
        ("a", "treble_clef"),
        ("b", "sharp"),
        ("c", "sharp"),
        ("d", "flat"),
    ]
    records = [{
        "candidate_id": candidate,
        "page_number": 1,
        "staff_index": 0,
        "crop_file": f"crops/{candidate}.png",
        "label": label,
        "label_status": "labeled_by_human",
        "annotator": "reviewer",
        "labeled_at": "2026-11-27T00:00:00+00:00",
    } for candidate, label in glyphs]
    path.write_text(json.dumps({
        "schema_version": "1.0",
        "score_id": "score-a",
        "label_vocabulary": ["treble_clef", "sharp", "flat"],
        "glyph_count": 4,
        "labeled_count": 4,
        "pending_count": 0,
        "glyphs": records,
    }), encoding="utf-8")
    return path


def predictions(path, items):
    path.write_text(json.dumps({"predictions": items}), encoding="utf-8")
    return path


def test_evaluation_reports_accuracy_coverage_and_abstention(tmp_path):
    truth = manifest(tmp_path / "truth.json")
    preds = predictions(tmp_path / "preds.json", [
        {"score_id": "score-a", "candidate_id": "a", "label": "treble_clef", "confidence": 0.99},
        {"score_id": "score-a", "candidate_id": "b", "label": "sharp"},
        {"score_id": "score-a", "candidate_id": "c", "label": "flat"},
        {"score_id": "score-a", "candidate_id": "d", "label": None},
    ])
    report = evaluate_glyph_predictions([truth], preds)
    assert report["ground_truth_count"] == 4
    assert report["covered_count"] == 3
    assert report["abstained_count"] == 1
    assert report["correct_count"] == 2
    assert report["accuracy_all"] == 0.5
    assert report["accuracy_covered"] == round(2 / 3, 6)
    assert report["coverage"] == 0.75
    assert report["confusion_matrix"]["sharp"]["flat"] == 1
    assert report["confusion_matrix"]["flat"]["abstain"] == 1


def test_missing_predictions_count_as_abstentions(tmp_path):
    truth = manifest(tmp_path / "truth.json")
    preds = predictions(tmp_path / "preds.json", [
        {"score_id": "score-a", "candidate_id": "a", "label": "treble_clef"},
    ])
    report = evaluate_glyph_predictions([truth], preds)
    assert report["unpredicted_count"] == 3
    assert report["abstained_count"] == 3
    assert report["accuracy_all"] == 0.25
    assert report["coverage"] == 0.25


def test_rejects_duplicate_unknown_and_invalid_predictions(tmp_path):
    truth = manifest(tmp_path / "truth.json")
    duplicate = predictions(tmp_path / "duplicate.json", [
        {"score_id": "score-a", "candidate_id": "a", "label": "treble_clef"},
        {"score_id": "score-a", "candidate_id": "a", "label": "treble_clef"},
    ])
    with pytest.raises(ValueError, match="duplicada"):
        evaluate_glyph_predictions([truth], duplicate)
    unknown = predictions(tmp_path / "unknown.json", [
        {"score_id": "score-a", "candidate_id": "missing", "label": "sharp"},
    ])
    with pytest.raises(ValueError, match="sin etiqueta humana"):
        evaluate_glyph_predictions([truth], unknown)
    invalid = predictions(tmp_path / "invalid.json", [
        {"score_id": "score-a", "candidate_id": "a", "label": "nota_inventada"},
    ])
    with pytest.raises(ValueError, match="no permitida"):
        evaluate_glyph_predictions([truth], invalid)


def test_rejects_bad_confidence_and_writes_report(tmp_path):
    truth = manifest(tmp_path / "truth.json")
    preds = predictions(tmp_path / "preds.json", [
        {"score_id": "score-a", "candidate_id": "a", "label": "treble_clef", "confidence": 1.5},
    ])
    with pytest.raises(ValueError, match="confidence"):
        evaluate_glyph_predictions([truth], preds)
    valid = predictions(tmp_path / "valid.json", [
        {"score_id": "score-a", "candidate_id": "a", "label": "treble_clef"},
    ])
    report = evaluate_glyph_predictions([truth], valid)
    output = tmp_path / "out" / "report.json"
    write_glyph_evaluation(report, output)
    assert json.loads(output.read_text()) == report
