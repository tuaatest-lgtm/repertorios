import json

import pytest

from palermo_omr.page_analysis_audit import audit_page_analysis
from palermo_omr.page_analysis_audit_cli import main


def _page(number=1):
    return {
        "page_number": number,
        "staves": [{}, {}],
        "staff_system_candidates": [
            {"system_index": 0, "staff_indices": [0]},
            {"system_index": 1, "staff_indices": [1]},
        ],
        "notehead_candidates": [
            {"staff_index": 0, "center_x": 10},
            {"staff_index": 0, "center_x": 20},
            {"staff_index": 1, "center_x": 50},
        ],
        "hollow_notehead_candidates": [{}],
        "rhythm_candidates": [
            {"stem_direction": "up", "base_duration": "quarter", "beam_count": 0, "confidence": .9},
            {"stem_direction": "none", "base_duration": "unknown", "beam_count": 0, "confidence": .4},
            {"stem_direction": "down", "base_duration": "eighth", "beam_count": 1, "confidence": .7},
        ],
        "rhythmic_interpretation_candidates": [
            {"status": "local_candidate_only"},
            {"status": "unclassified"},
            {"status": "local_candidate_only"},
        ],
        "beam_group_candidates": [{}],
        "measure_span_candidates": [
            {"staff_index": 0, "x_start": 0, "x_end": 20},
            {"staff_index": 0, "x_start": 20, "x_end": 30},
            {"staff_index": 1, "x_start": 40, "x_end": 60},
        ],
        "rest_shape_candidates": [{}, {}],
        "tie_slur_shape_candidates": [{}],
        "augmentation_dot_candidates": [],
    }


def test_audit_counts_geometry_and_candidate_distributions_without_claiming_accuracy():
    report = audit_page_analysis({"source_pdf": "fixture.pdf", "pages": [_page()]})
    assert report["status"] == "candidate_geometry_audit"
    assert report["totals"]["filled_notehead_candidates"] == 3
    assert report["totals"]["one_measure_span"] == 2
    assert report["totals"]["multiple_measure_spans"] == 1
    assert report["totals"]["no_measure_span"] == 0
    assert report["totals"]["measure_span_unique_coverage"] == pytest.approx(2 / 3)
    page = report["pages"][0]
    assert page["rhythm_candidate_distribution"]["stem_direction"] == {"down": 1, "none": 1, "up": 1}
    assert page["rhythm_candidate_distribution"]["base_duration"]["unknown"] == 1
    assert page["geometry_coverage"]["staves_in_exactly_one_system_candidate"] == 2
    assert "no equivale" in page["interpretation"]
    assert len(report["limitations"]) >= 4


def test_audit_handles_missing_optional_arrays_and_unknown_staff_links():
    page = {
        "page_number": 1,
        "staves": [{}],
        "notehead_candidates": [{"staff_index": 4, "center_x": 12}],
    }
    report = audit_page_analysis({"pages": [page]})
    assert report["pages"][0]["geometry_coverage"]["noteheads_with_invalid_staff_index"] == 1
    assert report["totals"]["measure_span_unique_coverage"] == 0


def test_audit_rejects_misaligned_rhythm_and_duplicate_pages():
    page = _page()
    page["rhythm_candidates"] = []
    with pytest.raises(ValueError, match="alinearse"):
        audit_page_analysis({"pages": [page]})
    with pytest.raises(ValueError, match="único"):
        audit_page_analysis({"pages": [_page(), _page()]})


def test_audit_cli_writes_json_and_reports_geometry_coverage(tmp_path, capsys):
    source = tmp_path / "analysis.json"
    output = tmp_path / "report" / "audit.json"
    source.write_text(json.dumps({"source_pdf": "fixture.pdf", "pages": [_page()]}), encoding="utf-8")
    assert main([str(source), str(output)]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["totals"]["filled_notehead_candidates"] == 3
    assert "66.67%" in capsys.readouterr().out


def test_audit_rejects_empty_or_invalid_analysis(tmp_path, capsys):
    source = tmp_path / "bad.json"
    output = tmp_path / "audit.json"
    source.write_text(json.dumps({"pages": []}), encoding="utf-8")
    assert main([str(source), str(output)]) == 2
    assert "no vacía" in capsys.readouterr().err
