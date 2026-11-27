from palermo_omr.key_signature_candidates import build_key_signature_candidates


def glyph(label, x, y, candidate_id):
    return {
        "candidate_id": candidate_id,
        "page_number": 1,
        "staff_index": 0,
        "candidate_bbox": [x, y, 4, 8],
        "label": label,
        "label_status": "labeled_by_human",
    }


def test_builds_reviewable_sharp_signature_from_human_labels_and_staff_positions():
    # Treble staff bottom E4; F5 is five diatonic steps above bottom line.
    manifest = {"glyphs": [
        glyph("sharp", 10, 35, "s1"),
        glyph("sharp", 20, 20, "s2"),
    ]}
    result = build_key_signature_candidates(
        manifest, page_number=1, staff_clefs={0: "treble"},
        staff_lines={0: [40, 50, 60, 70, 80]},
    )
    assert result[0].status == "candidate_requires_human_acceptance"
    assert result[0].key_signature == {"F": 1, "C": 1}
    assert result[0].observed_letters == ["F", "C"]


def test_rejects_nonconventional_accidental_order():
    manifest = {"glyphs": [
        glyph("sharp", 10, 20, "s1"),  # C
        glyph("sharp", 20, 35, "s2"),  # F
    ]}
    result = build_key_signature_candidates(
        manifest, page_number=1, staff_clefs={0: "treble"},
        staff_lines={0: [40, 50, 60, 70, 80]},
    )
    assert result[0].status == "ambiguous_order_or_position"
    assert result[0].key_signature is None


def test_ignores_unconfirmed_glyph_suggestions():
    item = glyph("sharp", 10, 35, "s1")
    item["label_status"] = "pending_human_review"
    result = build_key_signature_candidates(
        {"glyphs": [item]}, page_number=1, staff_clefs={0: "treble"},
        staff_lines={0: [40, 50, 60, 70, 80]},
    )
    assert result == []
