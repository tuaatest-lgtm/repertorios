import json

import pytest

from palermo_omr.review_package import build_review_package, prepare_review_package


def sample_analysis():
    return {
        "version": "0.3.0",
        "source_pdf": "score.pdf",
        "global_measure_sequence": {
            "global_measure_candidates": [{"global_measure_candidate": 1, "page_number": 1}],
            "global_measure_candidate_count": 1,
            "staff_measure_map": [{"page_number": 1, "staff_index": 0,
                                   "measure_index_on_staff": 1,
                                   "global_measure_candidate": 1}],
            "warning": "Provisional",
        },
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
            "rest_shape_candidates": [{"rest_type_candidate": "unclassified", "staff_index": 1}],
            "tie_slur_shape_candidates": [{"confidence": 0.4, "staff_index": 0}],
            "augmentation_dot_candidates": [{"associated_notehead_index": 0, "x": 28.0, "y": 23.0}],
            "barline_candidates": [],
            "beam_group_candidates": [{"beam_count_candidate": 2, "notehead_indices": [0]}],
            "barline_group_candidates": [{"group_type_candidate": "double", "staff_index": 0}],
            "system_barline_candidates": [{"staff_indices": [0, 1]}],
            "staff_system_candidates": [{"staff_indices": [0, 1]}],
            "measure_span_candidates": [{"staff_index": 0, "measure_index": 0}],
            "staff_grouping_mark_candidates": [{"kind": "curly_brace_candidate", "staff_indices": [0, 1]}],
            "printed_label_candidates": [{"text": "Soprano", "association_status": "associated_candidate", "staff_index": 0}],
            "staff_identity_evidence": [{"evidence_id": "label-1", "staff_id": "p1-staff-1", "kind": "printed_voice_label", "source": "visual_candidate"}],
            "notehead_overlay": "page-001-noteheads-overlay.png",
            "hollow_notehead_overlay": "page-001-hollow-noteheads-overlay.png",
            "geometry_overlay": "page-001-geometry-overlay.png",
        }],
    }


def test_build_review_package_keeps_all_candidates_pending_and_unconfirmed():
    package = build_review_package(sample_analysis(), score_id="score-01")
    assert package["summary"] == {
        "page_count": 1, "notehead_candidate_count": 2,
        "other_candidate_count": 13, "pending_count": 15,
        "global_measure_candidate_count": 1,
        "pending_global_measure_candidate_count": 1,
        "cross_staff_aligned_measure_candidate_count": 0,
        "single_staff_only_measure_candidate_count": 1,
        "global_measure_sequence_scope": "unknown",
        "system_barline_candidate_count": 1,
        "global_section_range_candidate_count": 0,
        "pending_global_section_range_candidate_count": 0,
        "section_boundary_candidate_count": 0,
        "cross_staff_aligned_section_boundary_candidate_count": 0,
        "single_staff_only_section_boundary_candidate_count": 0,
        "unmatched_section_boundary_candidate_count": 0,
        "partial_section_boundary_candidate_count": 0,
        "inside_measure_section_boundary_candidate_count": 0,
        "before_measure_section_boundary_candidate_count": 0,
        "after_measure_section_boundary_candidate_count": 0,
        "section_marker_candidate_count": 0,
        "eligible_global_section_marker_candidate_count": 0,
        "excluded_global_section_marker_candidate_count": 0,
        "unclassified_global_section_marker_candidate_count": 0,
        "staff_system_candidate_count": 1,
        "multi_staff_system_candidate_count": 1,
        "single_staff_system_candidate_count": 0,
        "staff_grouping_mark_candidate_count": 1,
        "staff_identity_evidence_count": 1,
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
    assert package["global_measure_sequence"]["global_measure_candidate_count"] == 1
    assert package["global_measure_sequence"]["global_measure_candidates"][0]["global_measure_candidate"] == 1


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
    assert package["summary"]["pending_count"] == 15
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
        "staff_system", "measure_span", "staff_grouping_mark",
        "printed_label", "staff_identity_evidence",
    } <= families
    assert all(
        item["review_status"] == "pending" and item["decision"] is None
        for item in page["other_candidates"]
    )
    beam = next(item for item in page["other_candidates"] if item["family"] == "beam_group")
    assert beam["candidate_data"]["beam_count_candidate"] == 2
    rest = next(item for item in page["other_candidates"] if item["family"] == "rest_shape")
    assert rest["related_candidate_ids"] == ["p1-staff-2"]
    arc = next(item for item in page["other_candidates"] if item["family"] == "tie_slur_shape")
    assert arc["related_candidate_ids"] == ["p1-staff-1"]
    dot = next(item for item in page["other_candidates"] if item["family"] == "augmentation_dot")
    assert dot["related_candidate_ids"] == ["p1-filled_notehead-1", "p1-staff-1"]
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
        ("augmentation_dot_candidates", {"associated_notehead_index": 1}),
        ("barline_group_candidates", {"staff_index": 4}),
        ("system_barline_candidates", {"staff_indices": [0, 4]}),
        ("system_barline_candidates", {"staff_indices": [0, 0]}),
        ("staff_system_candidates", {"staff_indices": [True]}),
        ("measure_span_candidates", {"staff_index": -1}),
        ("rest_shape_candidates", {"staff_index": True}),
        ("staff_grouping_mark_candidates", {"staff_indices": [0, 3]}),
        ("staff_grouping_mark_candidates", {"staff_indices": [0, 0]}),
        ("printed_label_candidates", {"association_status": "associated_candidate", "staff_index": 9}),
        ("printed_label_candidates", {"association_status": "unknown"}),
        ("staff_identity_evidence", {"staff_id": "missing-staff"}),
    ],
)
def test_review_package_rejects_broken_candidate_references(family_key, candidate):
    data = sample_analysis()
    data["pages"][0][family_key] = [candidate]
    with pytest.raises(ValueError, match="referencia|duplicados|cabeza rellena|estado de asociación"):
        build_review_package(data, score_id="score-invalid-references")



def test_review_summary_counts_global_section_and_measure_candidates():
    data = sample_analysis()
    data["global_section_range_candidates"] = [
        {"section_range_id": "section-1", "start": {"page_number": 1}, "end": None, "review_status": "pending"},
        {"section_range_id": "section-2", "start": {"page_number": 1}, "end": None, "review_status": "accepted"},
    ]
    package = build_review_package(data, score_id="score-section-summary")
    assert package["summary"]["global_measure_candidate_count"] == 1
    assert package["summary"]["pending_global_measure_candidate_count"] == 1
    assert package["summary"]["global_section_range_candidate_count"] == 2
    assert package["summary"]["pending_global_section_range_candidate_count"] == 1



@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("global_section_range_candidates", ["bad-range"], "rango global"),
        ("global_measure_candidates", ["bad-measure"], "compás global"),
        ("staff_measure_map", ["bad-map"], "referencia local/global"),
    ],
)
def test_review_package_rejects_malformed_global_candidates(field, value, message):
    data = sample_analysis()
    if field == "global_section_range_candidates":
        data[field] = value
    else:
        data["global_measure_sequence"][field] = value
    with pytest.raises(ValueError, match=message):
        build_review_package(data, score_id="score-invalid-global")



def test_review_package_preserves_global_section_marker_disposition():
    data = sample_analysis()
    data["pages"][0]["section_marker_candidates"] = [{
        "normalized_text": "CORO",
        "text": "Coro",
        "global_boundary_status": "excluded_repeated_page_header_candidate",
        "global_boundary_reason": "Repeated page header",
    }]
    package = build_review_package(data, score_id="score-header-review")
    marker = next(
        item for item in package["pages"][0]["other_candidates"]
        if item["family"] == "section_marker"
    )
    assert marker["candidate_data"]["global_boundary_status"] == (
        "excluded_repeated_page_header_candidate"
    )
    assert marker["candidate_data"]["global_boundary_reason"] == "Repeated page header"
    assert marker["review_status"] == "pending"



def test_review_summary_counts_eligible_excluded_and_unclassified_section_markers():
    data = sample_analysis()
    data["pages"][0]["section_marker_candidates"] = [
        {"normalized_text": "INTRO", "global_boundary_status": "eligible_candidate"},
        {"normalized_text": "CORO", "global_boundary_status": "excluded_repeated_page_header_candidate"},
        {"normalized_text": "PUENTE"},
    ]
    package = build_review_package(data, score_id="score-marker-counts")
    summary = package["summary"]
    assert summary["section_marker_candidate_count"] == 3
    assert summary["eligible_global_section_marker_candidate_count"] == 1
    assert summary["excluded_global_section_marker_candidate_count"] == 1
    assert summary["unclassified_global_section_marker_candidate_count"] == 1



def test_review_summary_reports_cross_staff_and_single_staff_measure_counts():
    data = sample_analysis()
    data["global_measure_sequence"]["cross_staff_aligned_candidate_count"] = 1
    data["global_measure_sequence"]["single_staff_only_candidate_count"] = 0
    package = build_review_package(data, score_id="score-alignment-counts")
    assert package["summary"]["cross_staff_aligned_measure_candidate_count"] == 1
    assert package["summary"]["single_staff_only_measure_candidate_count"] == 0



def test_review_summary_reports_section_boundary_alignment_support():
    data = sample_analysis()
    data["global_section_range_candidates"] = [
        {"section_range_id": "section-1",
         "start": {"page_number": 1, "musical_boundary_candidate": {
             "global_alignment_status": "cross_staff_alignment_candidate"}},
         "end": {"page_number": 1, "musical_boundary_candidate": {
             "global_alignment_status": "single_staff_only_unmatched"}}},
        {"section_range_id": "section-2",
         "start": {"page_number": 2, "musical_boundary_candidate": {
             "global_alignment_status": "single_staff_only_unmatched"}},
         "end": None},
    ]
    package = build_review_package(data, score_id="score-section-boundary-support")
    summary = package["summary"]
    assert summary["section_boundary_candidate_count"] == 3
    assert summary["cross_staff_aligned_section_boundary_candidate_count"] == 1
    assert summary["single_staff_only_section_boundary_candidate_count"] == 2
    assert summary["unmatched_section_boundary_candidate_count"] == 0



def test_review_summary_counts_staff_systems_and_identity_evidence():
    data = sample_analysis()
    data["pages"][0]["staves"].append({})
    data["pages"][0]["staff_system_candidates"] = [
        {"system_index": 0, "staff_indices": [0, 1]},
        {"system_index": 1, "staff_indices": [2]},
    ]
    data["pages"][0]["staff_grouping_mark_candidates"] = [
        {"staff_indices": [0, 1]}, {"staff_indices": [0, 1]}, {"staff_indices": [0, 1]},
    ]
    data["pages"][0]["staff_identity_evidence"].append({"evidence_id": "label-2", "staff_id": "p1-staff-2", "kind": "printed_voice_label", "source": "visual_candidate"})
    package = build_review_package(data, score_id="score-system-review")
    summary = package["summary"]
    assert summary["staff_system_candidate_count"] == 2
    assert summary["multi_staff_system_candidate_count"] == 1
    assert summary["single_staff_system_candidate_count"] == 1
    assert summary["staff_grouping_mark_candidate_count"] == 3
    assert summary["staff_identity_evidence_count"] == 2



def test_review_summary_exposes_global_measure_scope_and_system_barline_count():
    data = sample_analysis()
    data["global_measure_sequence"]["sequence_scope"] = "partially_cross_staff_aligned"
    data["pages"][0]["system_barline_candidates"] = [{"staff_indices": [0, 1]}] * 4
    package = build_review_package(data, score_id="score-measure-scope")
    assert package["summary"]["global_measure_sequence_scope"] == (
        "partially_cross_staff_aligned"
    )
    assert package["summary"]["system_barline_candidate_count"] == 4



def test_review_summary_counts_partial_and_adjacent_section_boundaries():
    data = sample_analysis()
    data["global_section_range_candidates"] = [{
        "section_range_id": "section-partial",
        "start": {"page_number": 1, "musical_boundary_candidate": {
            "position_kind": "inside_measure_candidate", "partial_measure_boundary": True,
        }},
        "end": {"page_number": 1, "musical_boundary_candidate": {
            "position_kind": "after_measure_candidate", "partial_measure_boundary": False,
        }},
    }]
    package = build_review_package(data, score_id="score-partial-boundary-counts")
    summary = package["summary"]
    assert summary["section_boundary_candidate_count"] == 2
    assert summary["partial_section_boundary_candidate_count"] == 1
    assert summary["inside_measure_section_boundary_candidate_count"] == 1
    assert summary["before_measure_section_boundary_candidate_count"] == 0
    assert summary["after_measure_section_boundary_candidate_count"] == 1



@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("staff_system_candidates", "bad", "staff_system_candidates"),
        ("staff_system_candidates", [{"system_index": 0, "staff_indices": []}], "staff_indices"),
        ("system_barline_candidates", "bad", "system_barline_candidates"),
        ("staff_grouping_mark_candidates", ["bad"], "staff_grouping_mark_candidates"),
        ("staff_identity_evidence", ["bad"], "staff_identity_evidence"),
    ],
)
def test_review_package_rejects_malformed_staff_review_evidence(field, value, message):
    data = sample_analysis()
    data["pages"][0][field] = value
    with pytest.raises(ValueError, match=message):
        build_review_package(data, score_id="score-invalid-staff-evidence")
