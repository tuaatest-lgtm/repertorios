import pytest

from palermo_omr.clef_candidates import build_staff_clef_candidates


def _manifest():
    return {
        "schema_version": "1.0",
        "score_id": "score-clefs",
        "glyph_count": 4,
        "labeled_count": 2,
        "pending_count": 2,
        "glyphs": [
            {"candidate_id": "treble-0", "page_number": 1, "staff_index": 0,
             "crop_file": "treble.png", "label": "treble_clef",
             "label_status": "labeled_by_human", "annotator": "reviewer", "labeled_at": "2026-01-01T00:00:00Z"},
            {"candidate_id": "pending-1", "page_number": 1, "staff_index": 1,
             "crop_file": "pending.png", "label": None,
             "label_status": "pending_human_review", "annotator": None, "labeled_at": None},
            {"candidate_id": "other-page", "page_number": 2, "staff_index": 1,
             "crop_file": "other.png", "label": "bass_clef",
             "label_status": "labeled_by_human", "annotator": "reviewer", "labeled_at": "2026-01-01T00:00:00Z"},
            {"candidate_id": "pending-0", "page_number": 1, "staff_index": 0,
             "crop_file": "pending0.png", "label": None,
             "label_status": "pending_human_review", "annotator": None, "labeled_at": None},
        ],
    }


def test_clef_context_preserves_confirmed_pending_and_missing_states():
    result = build_staff_clef_candidates(
        _manifest(), page_number=1, staff_indices=[0, 1, 2]
    )
    assert [(x.staff_index, x.status, x.clef) for x in result] == [
        (0, "human_confirmed", "treble"),
        (1, "pending_human_review", None),
        (2, "no_clef_evidence", None),
    ]
    assert result[0].glyph_ids == ("treble-0",)
    assert result[0].pending_glyph_ids == ("pending-0",)
    assert result[1].pending_glyph_ids == ("pending-1",)


def test_clef_context_detects_conflicting_human_labels():
    manifest = _manifest()
    manifest["glyphs"].append({
        "candidate_id": "bass-0", "page_number": 1, "staff_index": 0,
        "crop_file": "bass.png", "label": "bass_clef",
        "label_status": "labeled_by_human", "annotator": "reviewer",
        "labeled_at": "2026-01-01T00:00:00Z",
    })
    manifest["glyph_count"] += 1
    manifest["labeled_count"] += 1
    result = build_staff_clef_candidates(manifest, page_number=1, staff_indices=[0])
    assert result[0].status == "conflicting_human_labels"
    assert result[0].clef is None
    assert set(result[0].glyph_ids) == {"treble-0", "bass-0"}


@pytest.mark.parametrize("page,staffs", [(0, [0]), (1, []), (1, [True]), (1, [0, 0])])
def test_clef_context_rejects_invalid_scope(page, staffs):
    with pytest.raises(ValueError):
        build_staff_clef_candidates(_manifest(), page_number=page, staff_indices=staffs)


def test_non_clef_labels_do_not_become_clef_evidence():
    manifest = _manifest()
    glyph = manifest["glyphs"][0]
    glyph.update({"label": "sharp"})
    result = build_staff_clef_candidates(manifest, page_number=1, staff_indices=[0])
    assert result[0].status == "pending_human_review"
    assert result[0].clef is None
