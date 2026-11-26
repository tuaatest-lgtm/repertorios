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
            "beam_group_candidates": [{"beam_count_candidate": 2, "notehead_indices": [0]}],
            "barline_group_candidates": [{"group_type_candidate": "double", "staff_index": 0}],
            "system_barline_candidates": [{"staff_indices": [0, 1]}],
            "staff_system_candidates": [{"staff_indices": [0, 1]}],
            "measure_span_candidates": [{"staff_index": 0, "measure_index": 0}],
            "notehead_overlay": "page-001-noteheads-overlay.png",
            "hollow_notehead_overlay": "page-001-hollow-noteheads-overlay.png",
            "geometry_overlay": "page-001-geometry-overlay.png",
        }],
    }


def test_build_review_package_keeps_all_candidates_pending_and_unconfirmed():
    package = build_review_package(sample_analysis(), score_id="score-01")
    assert package["summary"] == {
        "page_count": 1, "notehead_candidate_count": 2,
        "other_candidate_count": 9, "pending_count": 11,
    }
    filled, hollow = package["pages"][0]["notehead_candidates"]
    assert filled["rhythm_hypothesis"]["base_duration"] == "quarter"
    assert hollow["rhythm_hypothesis"]["base_duration"] == "half"
    assert filled["review_status"] == hollow["review_status"] == "pending"
    assert filled["related_candidate_ids"] == ["p1-staff-1"]
    assert hollow["related_candidate_ids"] == ["p1-staff-2"]
    assert filled["decision"] is hollow["decision"] is None
    assert package["pages"][0]["overlays"]["filled_noteheads"].endswith(".png")
    assert package["pages"][0]["overlays"]["geometry"] == "page-001-geometry-overlay.png"
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


def test_prepare_review_cli_runs_end_to_end_and_keeps_candidates_pending(tmp_path, capsys):
    from palermo_omr.annotation_cli import main

    analysis = tmp_path / "analysis.json"
    output = tmp_path / "review" / "package.json"
    analysis.write_text(json.dumps(sample_analysis()), encoding="utf-8")

    result = main([
        "prepare-review", str(analysis),
        "--score-id", "score-cli",
        "--output", str(output),
    ])

    assert result == 0
    captured = capsys.readouterr()
    assert "Candidatos de cabezas: 2" in captured.out
    assert "requieren revisión humana" in captured.out
    package = json.loads(output.read_text(encoding="utf-8"))
    assert package["score_id"] == "score-cli"
    assert package["summary"]["pending_count"] == 11
    assert all(
        candidate["review_status"] == "pending" and candidate["decision"] is None
        for page in package["pages"]
        for candidate in page["staff_candidates"] + page["notehead_candidates"] + page["other_candidates"]
    )


def test_build_review_package_rejects_boolean_staff_index():
    data = sample_analysis()
    data["pages"][0]["notehead_candidates"][0]["staff_index"] = True
    with pytest.raises(ValueError, match="pentagrama inexistente"):
        build_review_package(data, score_id="score-01")


def test_review_package_includes_relationship_and_measure_geometry_candidates():
    package = build_review_package(sample_analysis(), score_id="score-geometry")
    page = package["pages"][0]
    families = {item["family"] for item in page["other_candidates"]}
    assert {
        "beam_group", "barline_group", "system_barline",
        "staff_system", "measure_span",
    } <= families
    assert all(
        item["review_status"] == "pending" and item["decision"] is None
        for item in page["other_candidates"]
    )
    beam = next(item for item in page["other_candidates"] if item["family"] == "beam_group")
    assert beam["candidate_data"]["beam_count_candidate"] == 2
    assert beam["related_candidate_ids"] == ["p1-filled_notehead-1"]
    assert page["staff_candidates"][0]["candidate_id"] == "p1-staff-1"
    assert page["staff_candidates"][0]["review_status"] == "pending"
    bar_group = next(item for item in page["other_candidates"] if item["family"] == "barline_group")
    assert bar_group["related_candidate_ids"] == ["p1-staff-1"]
    system = next(item for item in page["other_candidates"] if item["family"] == "staff_system")
    assert system["related_candidate_ids"] == ["p1-staff-1", "p1-staff-2"]


@pytest.mark.parametrize(
    ("family_key", "candidate"),
    [
        ("beam_group_candidates", {"notehead_indices": [1]}),
        ("barline_group_candidates", {"staff_index": 4}),
        ("system_barline_candidates", {"staff_indices": [0, 4]}),
        ("system_barline_candidates", {"staff_indices": [0, 0]}),
        ("staff_system_candidates", {"staff_indices": [True]}),
        ("measure_span_candidates", {"staff_index": -1}),
    ],
)
def test_review_package_rejects_broken_candidate_references(family_key, candidate):
    data = sample_analysis()
    data["pages"][0][family_key] = [candidate]
    with pytest.raises(ValueError, match="referencia|duplicados"):
        build_review_package(data, score_id="score-invalid-references")
