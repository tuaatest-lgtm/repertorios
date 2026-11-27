import json
import pytest

from palermo_omr.glyph_dataset import build_score_group_split, write_score_group_split


def make_manifest(path, score_id, labels):
    glyphs = []
    for index, label in enumerate(labels):
        glyphs.append({
            "candidate_id": f"{score_id}-glyph-{index}",
            "page_number": 1 if index == 0 else 2,
            "staff_index": 0,
            "crop_file": f"crops/{score_id}-glyph-{index}.png",
            "label": label,
            "label_status": "labeled_by_human",
            "annotator": "reviewer",
            "labeled_at": "2026-11-27T00:00:00+00:00",
        })
    path.write_text(json.dumps({
        "schema_version": "1.0",
        "score_id": score_id,
        "label_vocabulary": sorted({"treble_clef", "sharp"}),
        "glyph_count": len(glyphs),
        "labeled_count": len(glyphs),
        "pending_count": 0,
        "glyphs": glyphs,
    }), encoding="utf-8")
    return path


def test_split_keeps_all_pages_of_each_score_together_and_is_deterministic(tmp_path):
    paths = [
        make_manifest(tmp_path / "a.json", "score-a", ["treble_clef", "sharp"]),
        make_manifest(tmp_path / "b.json", "score-b", ["sharp"]),
        make_manifest(tmp_path / "c.json", "score-c", ["treble_clef"]),
        make_manifest(tmp_path / "d.json", "score-d", ["sharp"]),
    ]
    first = build_score_group_split(paths, seed="fixed")
    second = build_score_group_split(paths, seed="fixed")
    assert first == second
    train = set(first["train_score_ids"])
    validation = set(first["validation_score_ids"])
    assert train and validation and train.isdisjoint(validation)
    assert {r["score_id"] for r in first["train"]} == train
    assert {r["score_id"] for r in first["validation"]} == validation
    assert first["train_count"] + first["validation_count"] == 4


def test_split_rejects_single_score_and_duplicate_score_ids(tmp_path):
    one = make_manifest(tmp_path / "one.json", "same", ["sharp"])
    with pytest.raises(ValueError, match="al menos dos"):
        build_score_group_split([one])
    two = make_manifest(tmp_path / "two.json", "same", ["treble_clef"])
    with pytest.raises(ValueError, match="duplicado"):
        build_score_group_split([one, two])


def test_split_requires_human_labels_and_valid_fraction(tmp_path):
    path = make_manifest(tmp_path / "a.json", "score-a", ["sharp"])
    data = json.loads(path.read_text())
    data["glyphs"][0]["label_status"] = "pending_human_review"
    data["glyphs"][0]["label"] = None
    data["glyphs"][0]["annotator"] = None
    data["glyphs"][0]["labeled_at"] = None
    data["labeled_count"] = 0
    data["pending_count"] = 1
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="no tiene etiquetas humanas"):
        build_score_group_split([path])
    with pytest.raises(ValueError, match="validation_fraction"):
        build_score_group_split([path], validation_fraction=1.0)


def test_write_split_creates_json(tmp_path):
    paths = [
        make_manifest(tmp_path / "a.json", "score-a", ["sharp"]),
        make_manifest(tmp_path / "b.json", "score-b", ["treble_clef"]),
    ]
    result = build_score_group_split(paths)
    output = tmp_path / "nested" / "split.json"
    write_score_group_split(result, output)
    assert json.loads(output.read_text()) == result
