from types import SimpleNamespace
import pytest
from palermo_omr.notation_context import build_pitch_candidates_with_notation_context


def glyph(cid, label, bbox=None, status="labeled_by_human"):
    return {"candidate_id": cid, "page_number": 1, "staff_index": 0,
            "candidate_bbox": bbox or [5, 5, 8, 8], "crop_file": cid + ".png",
            "label": label, "label_status": status,
            "annotator": "reviewer" if status == "labeled_by_human" else None,
            "labeled_at": "2026-01-01T00:00:00Z" if status == "labeled_by_human" else None}


def manifest(glyphs):
    n = sum(g["label_status"] == "labeled_by_human" for g in glyphs)
    return {"schema_version": "1.0", "score_id": "score", "glyph_count": len(glyphs),
            "labeled_count": n, "pending_count": len(glyphs)-n, "glyphs": glyphs}


def head(staff=0, step=1):
    return SimpleNamespace(staff_index=staff, diatonic_step_from_bottom=step, center_x=100)


def test_confirmed_clef_and_accepted_key_signature_resolve_pitch():
    m = manifest([glyph("clef", "treble_clef"), glyph("fsharp", "sharp", [100, 6, 8, 8])])
    r = build_pitch_candidates_with_notation_context(
        [head()], m, page_number=1, staff_indices=[0], staff_lines={0:[10,20,30,40,50]},
        accepted_key_signature_staff_indices={0})
    assert r.clef_context[0].status == "human_confirmed"
    assert r.key_signature_candidates[0].status == "candidate_requires_human_acceptance"
    assert r.applied_key_signatures == {0:{"F":1}}
    assert r.pitch_candidates[0].pitch.midi == 66


def test_unaccepted_key_signature_does_not_change_pitch():
    m = manifest([glyph("clef", "treble_clef"), glyph("fsharp", "sharp", [100, 6, 8, 8])])
    r = build_pitch_candidates_with_notation_context(
        [head()], m, page_number=1, staff_indices=[0], staff_lines={0:[10,20,30,40,50]})
    assert r.applied_key_signatures == {}
    assert r.pitch_candidates[0].pitch.midi == 65


def test_pending_clef_keeps_pitch_unresolved():
    m = manifest([glyph("clef-pending", None, status="pending_human_review")])
    r = build_pitch_candidates_with_notation_context(
        [head()], m, page_number=1, staff_indices=[0], staff_lines={0:[10,20,30,40,50]})
    assert r.pitch_candidates[0].status == "unresolved_clef"
    assert r.pitch_candidates[0].pitch is None


def test_rejects_acceptance_outside_scope():
    m = manifest([glyph("clef", "treble_clef"), glyph("fsharp", "sharp", [100,6,8,8])])
    with pytest.raises(ValueError, match="fuera del alcance"):
        build_pitch_candidates_with_notation_context(
            [head()], m, page_number=1, staff_indices=[0], staff_lines={0:[10,20,30,40,50]},
            accepted_key_signature_staff_indices={1})


def test_rejects_pitch_heads_outside_staff_scope_without_inventing_clef():
    m = manifest([glyph("clef", "treble_clef")])
    r = build_pitch_candidates_with_notation_context(
        [head(1)], m, page_number=1, staff_indices=[0], staff_lines={0:[10,20,30,40,50]})
    assert r.pitch_candidates[0].status == "unresolved_clef"
