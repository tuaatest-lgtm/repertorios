import pytest

from palermo_omr.accidental_attachment import (
    attach_reviewed_accidentals,
    build_accepted_explicit_accidentals,
)


def _head(head_id, x, y, measure="m1", staff=0):
    return {"candidate_id": head_id, "staff_index": staff, "measure_id": measure,
            "bbox": [x, y, 10, 8]}


def _glyph(glyph_id, kind, x, y, measure="m1", staff=0, status="human_confirmed"):
    return {"candidate_id": glyph_id, "staff_index": staff, "measure_id": measure,
            "kind": kind, "status": status, "bbox": [x, y, 8, 12]}


def test_attaches_reviewed_accidental_to_nearest_head_on_same_staff_and_measure():
    result = attach_reviewed_accidentals(
        [_glyph("sharp-1", "sharp", 20, 48)],
        [_head("head-a", 34, 50), _head("head-b", 34, 80)],
        {0: 10},
    )
    assert result["attachments"][0]["notehead_id"] == "head-a"
    assert result["attachments"][0]["status"] == "pending_human_attachment_review"


def test_does_not_attach_unreviewed_or_cross_measure_glyphs():
    result = attach_reviewed_accidentals(
        [_glyph("pending", "flat", 20, 48, status="pending_human_review"),
         _glyph("other-bar", "natural", 20, 48, measure="m2")],
        [_head("head-a", 34, 50, measure="m1")],
        {0: 10},
    )
    assert result["attachments"] == []
    assert {item["reason"] for item in result["unresolved"]} == {
        "glyph_not_human_confirmed", "no_compatible_notehead",
    }


def test_keeps_near_tied_notehead_targets_ambiguous():
    result = attach_reviewed_accidentals(
        [_glyph("natural-1", "natural", 20, 48)],
        [_head("head-a", 34, 46), _head("head-b", 34, 50)],
        {0: 10},
    )
    assert result["attachments"] == []
    assert result["unresolved"] == [
        {"candidate_id": "natural-1", "reason": "ambiguous_notehead_attachment"},
    ]


def test_conflicting_glyphs_for_one_head_are_not_applied():
    result = attach_reviewed_accidentals(
        [_glyph("sharp", "sharp", 20, 48), _glyph("flat", "flat", 22, 48)],
        [_head("head-a", 36, 50)],
        {0: 10},
    )
    assert result["attachments"] == []
    assert {item["reason"] for item in result["unresolved"]} == {
        "multiple_accidentals_target_same_notehead",
    }


def test_only_explicitly_accepted_attachments_become_pitch_inputs():
    mapping = attach_reviewed_accidentals(
        [_glyph("sharp-1", "sharp", 20, 48)],
        [_head("head-a", 34, 50), _head("head-b", 34, 80)],
        {0: 10},
    )
    assert build_accepted_explicit_accidentals(
        ["head-a", "head-b"], mapping, ["sharp-1"]
    ) == ["sharp", None]
    assert build_accepted_explicit_accidentals(
        ["head-a", "head-b"], mapping, []
    ) == [None, None]
    with pytest.raises(ValueError, match="sin adjunción resuelta"):
        build_accepted_explicit_accidentals(["head-a"], mapping, ["missing"])


def test_rejects_invalid_geometry_and_measure_context():
    with pytest.raises(ValueError, match="measure_id"):
        attach_reviewed_accidentals(
            [_glyph("sharp-1", "sharp", 20, 48)],
            [{"candidate_id": "head", "staff_index": 0, "bbox": [34, 50, 10, 8]}],
            {0: 10},
        )
    with pytest.raises(ValueError, match="positivas"):
        attach_reviewed_accidentals(
            [], [_head("head", 10, 10)], {0: 0},
        )
