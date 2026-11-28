import pytest

from palermo_omr.focused_review import build_focused_review_package


def _package():
    return {
        "review_package_version": "1.0",
        "score_id": "clamare-dios-coro",
        "source_pdf": "Clamaré a Dios - Coro.pdf",
        "analysis_version": "0.3.0",
        "pages": [{
            "page_number": 1,
            "staff_count": 3,
            "staff_candidates": [
                {"candidate_id": f"p1-staff-{i+1}", "staff_index": i,
                 "candidate_data": {"lines_y": [100+i*100, 110+i*100, 120+i*100, 130+i*100, 140+i*100]},
                 "review_status": "pending", "decision": None}
                for i in range(3)
            ],
            "overlays": {"geometry": "page-001-geometry.png"},
            "notehead_candidates": [
                {"candidate_id": "p1-filled_notehead-1", "staff_index": 0,
                 "review_status": "pending", "decision": None},
                {"candidate_id": "p1-filled_notehead-2", "staff_index": 1,
                 "review_status": "pending", "decision": None},
                {"candidate_id": "p1-filled_notehead-3", "staff_index": 2,
                 "review_status": "pending", "decision": None},
            ],
            "other_candidates": [
                {"candidate_id": "p1-beam_group-1",
                 "related_candidate_ids": ["p1-filled_notehead-1", "p1-filled_notehead-2"],
                 "review_status": "pending", "decision": None},
                {"candidate_id": "p1-rest_shape-1",
                 "related_candidate_ids": ["p1-staff-2"],
                 "review_status": "pending", "decision": None},
                {"candidate_id": "p1-barline-1",
                 "related_candidate_ids": ["p1-staff-3"],
                 "review_status": "pending", "decision": None},
            ],
        }],
    }


def test_focus_keeps_stable_ids_and_only_selected_staff_candidates():
    result = build_focused_review_package(
        _package(), page_number=1, staff_indices=[0, 1],
        scope_label="Primer sistema, página 1",
    )
    assert result["scope"]["staff_indices"] == [0, 1]
    assert result["scope"]["review_status"] == "pending"
    assert [x["candidate_id"] for x in result["pages"][0]["notehead_candidates"]] == [
        "p1-filled_notehead-1", "p1-filled_notehead-2"
    ]
    assert {x["candidate_id"] for x in result["pages"][0]["other_candidates"]} == {
        "p1-beam_group-1", "p1-rest_shape-1"
    }
    assert "p1-filled_notehead-1" in result["candidate_ids"]
    assert result["summary"]["event_count"] == 0
    assert result["ground_truth_eligible"] is False
    assert result["annotation_status"] == "draft"


def test_focus_does_not_change_original_candidate_decisions():
    package = _package()
    result = build_focused_review_package(package, page_number=1, staff_indices=[1])
    assert result["pages"][0]["notehead_candidates"][0]["review_status"] == "pending"
    assert result["pages"][0]["notehead_candidates"][0]["decision"] is None
    assert package["pages"][0]["notehead_candidates"][1]["review_status"] == "pending"


@pytest.mark.parametrize("page,indices", [(0, [0]), (2, [0]), (1, []), (1, [3]), (1, [0, 0]), (1, [True])])
def test_focus_rejects_invalid_page_or_staff_selection(page, indices):
    with pytest.raises(ValueError):
        build_focused_review_package(_package(), page_number=page, staff_indices=indices)


def test_focus_rejects_missing_staff_candidate_and_duplicate_ids():
    package = _package()
    package["pages"][0]["staff_candidates"].pop()
    with pytest.raises(ValueError, match="Faltan candidatos"):
        build_focused_review_package(package, page_number=1, staff_indices=[2])
    package = _package()
    package["pages"][0]["notehead_candidates"][1]["candidate_id"] = "p1-filled_notehead-1"
    with pytest.raises(ValueError, match="IDs"):
        build_focused_review_package(package, page_number=1, staff_indices=[0, 1])



def test_focus_excludes_relations_that_cross_outside_selected_staff_scope():
    package = _package()
    package["pages"][0]["other_candidates"].append({
        "candidate_id": "p1-cross-staff-1",
        "related_candidate_ids": ["p1-filled_notehead-1", "p1-filled_notehead-3"],
        "review_status": "pending",
        "decision": None,
    })
    result = build_focused_review_package(
        package, page_number=1, staff_indices=[0, 1]
    )
    ids = {item["candidate_id"] for item in result["pages"][0]["other_candidates"]}
    assert "p1-cross-staff-1" not in ids



def test_focus_review_cli_writes_pending_fragment_and_keeps_original_ids(tmp_path):
    import json
    from palermo_omr.focused_review_cli import main

    source = tmp_path / "review.json"
    destination = tmp_path / "fragment.json"
    source.write_text(json.dumps(_package()), encoding="utf-8")
    result = main([
        str(source), "--page", "1", "--staff-indices", "0,1",
        "--label", "Primer sistema", "--output", str(destination),
    ])
    assert result == 0
    focused = json.loads(destination.read_text(encoding="utf-8"))
    assert focused["scope"]["label"] == "Primer sistema"
    assert focused["summary"]["event_count"] == 0
    assert focused["ground_truth_eligible"] is False
    assert "p1-filled_notehead-1" in focused["candidate_ids"]


def test_focus_review_cli_rejects_invalid_staff_indices(tmp_path):
    import json
    from palermo_omr.focused_review_cli import main

    source = tmp_path / "review.json"
    destination = tmp_path / "fragment.json"
    source.write_text(json.dumps(_package()), encoding="utf-8")
    result = main([
        str(source), "--page", "1", "--staff-indices", "0,99",
        "--output", str(destination),
    ])
    assert result == 2
    assert not destination.exists()
