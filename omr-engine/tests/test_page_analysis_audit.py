import json

import pytest

from palermo_omr.page_analysis_audit import audit_page_analysis, build_rhythm_review_queue
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
    assert report["rhythm_review_queue_count"] == 1
    assert report["rhythm_review_queue"][0]["candidate_id"] == "p1-filled_notehead-2"
    assert "missing_stem_direction" in report["rhythm_review_queue"][0]["review_reasons"]


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
    page["rhythm_candidates"] = [{}, {}]
    with pytest.raises(ValueError, match="alinearse"):
        audit_page_analysis({"pages": [page]})
    with pytest.raises(ValueError, match="único"):
        audit_page_analysis({"pages": [_page(), _page()]})


def test_audit_cli_writes_json_and_reports_geometry_coverage(tmp_path, capsys):
    source = tmp_path / "analysis.json"
    output = tmp_path / "report" / "audit.json"
    queue_csv = tmp_path / "report" / "rhythm-queue.csv"
    source.write_text(json.dumps({"source_pdf": "fixture.pdf", "pages": [_page()]}), encoding="utf-8")
    assert main([str(source), str(output), "--queue-csv", str(queue_csv)]) == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["totals"]["filled_notehead_candidates"] == 3
    captured = capsys.readouterr().out
    assert "66.67%" in captured
    assert "pendientes rítmicos: 1" in captured
    import csv
    with queue_csv.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["candidate_id"] == "p1-filled_notehead-2"
    assert "missing_stem_direction" in rows[0]["review_reasons"]


def test_audit_rejects_empty_or_invalid_analysis(tmp_path, capsys):
    source = tmp_path / "bad.json"
    output = tmp_path / "audit.json"
    source.write_text(json.dumps({"pages": []}), encoding="utf-8")
    assert main([str(source), str(output)]) == 2
    assert "no vacía" in capsys.readouterr().err



def test_rhythm_review_queue_prioritizes_missing_stems_then_low_confidence():
    page = _page()
    page["rhythm_candidates"][2]["stem_direction"] = "none"
    page["rhythm_candidates"][2]["base_duration"] = "unknown"
    page["rhythm_candidates"][2]["confidence"] = .2
    page["rhythmic_interpretation_candidates"][2]["status"] = "unclassified"
    queue = build_rhythm_review_queue({"pages": [page]})
    assert [item["candidate_id"] for item in queue] == [
        "p1-filled_notehead-3", "p1-filled_notehead-2",
    ]
    assert queue[0]["priority"] == 1
    assert queue[1]["priority"] == 1
    assert queue[0]["confidence"] <= queue[1]["confidence"]


def test_rhythm_review_queue_allows_pages_without_rhythm_data_and_rejects_misalignment():
    page = {
        "page_number": 1,
        "notehead_candidates": [{"staff_index": 0}],
        "rhythm_candidates": [],
        "rhythmic_interpretation_candidates": [],
    }
    assert build_rhythm_review_queue({"pages": [page]}) == []
    page["rhythm_candidates"] = [{}]
    with pytest.raises(ValueError, match="alineados"):
        build_rhythm_review_queue({"pages": [page]})
