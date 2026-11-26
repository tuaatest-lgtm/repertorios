import json

import pytest

from palermo_omr.review_package import build_review_package, prepare_review_package


def sample_analysis():
    return {
        "version": "0.3.0",
        "source_pdf": "score.pdf",
        "pages": [{
            "page_number": 1,
            "staves": [{}, {}],
            "notehead_candidates": [{
                "bbox": [10, 20, 12, 7], "center_x": 16.0,
                "center_y": 23.0, "staff_index": 0,
                "diatonic_step_from_bottom": 2, "confidence": 0.81,
            }],
            "rhythm_candidates": [{
                "base_duration": "quarter", "confidence": 0.6,
            }],
            "rhythmic_interpretation_candidates": [{
                "duration_candidate": "quarter", "status": "local_candidate_only",
            }],
            "hollow_notehead_candidates": [{
                "bbox": [40, 20, 13, 8], "center_x": 46.0,
                "center_y": 24.0, "staff_index": 1,
                "diatonic_step_from_bottom": 3, "confidence": 0.64,
            }],
            "hollow_rhythm_candidates": [{
                "base_duration": "half", "confidence": 0.5,
            }],
            "rest_shape_candidates": [{"rest_type_candidate": "unclassified"}],
            "tie_slur_shape_candidates": [{"confidence": 0.4}],
            "augmentation_dot_candidates": [],
            "barline_candidates": [],
            "notehead_overlay": "page-001-noteheads-overlay.png",
            "hollow_notehead_overlay": "page-001-hollow-noteheads-overlay.png",
        }],
    }


def test_build_review_package_keeps_all_candidates_pending_and_unconfirmed():
    package = build_review_package(sample_analysis(), score_id="score-01")
    assert package["summary"] == {
        "page_count": 1, "notehead_candidate_count": 2,
        "other_candidate_count": 2, "pending_count": 4,
    }
    filled, hollow = package["pages"][0]["notehead_candidates"]
    assert filled["rhythm_hypothesis"]["base_duration"] == "quarter"
    assert hollow["rhythm_hypothesis"]["base_duration"] == "half"
    assert filled["review_status"] == hollow["review_status"] == "pending"
    assert filled["decision"] is hollow["decision"] is None
    assert package["pages"][0]["overlays"]["filled_noteheads"].endswith(".png")
    assert "No representan eventos" in package["review_policy"]


def test_build_review_package_rejects_invalid_staff_reference_and_duplicate_page():
    data = sample_analysis()
    data["pages"][0]["notehead_candidates"][0]["staff_index"] = 9
    with pytest.raises(ValueError, match="pentagrama inexistente"):
        build_review_package(data, score_id="score-01")
    data = sample_analysis()
    data["pages"].append(data["pages"][0])
    with pytest.raises(ValueError, match="duplicado"):
        build_review_package(data, score_id="score-01")


def test_prepare_review_package_writes_json_atomically(tmp_path):
    source = tmp_path / "analysis.json"
    output = tmp_path / "review" / "package.json"
    source.write_text(json.dumps(sample_analysis()), encoding="utf-8")
    package = prepare_review_package(source, output, score_id="score-01")
    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored == package
    assert not output.with_suffix(".json.tmp").exists()


def test_build_review_package_requires_nonempty_pages_and_score_id():
    with pytest.raises(ValueError, match="score_id"):
        build_review_package(sample_analysis(), score_id=" ")
    with pytest.raises(ValueError, match="no contiene páginas"):
        build_review_package({"pages": []}, score_id="score-01")
