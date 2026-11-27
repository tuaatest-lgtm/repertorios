from palermo_omr.key_signature_candidates import (
    apply_accepted_key_signature_candidates,
    build_key_signature_candidates,
)


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
        glyph("sharp", 20, 16, "s2"),
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
        glyph("sharp", 10, 16, "s1"),  # C
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


def test_rejects_staff_lines_not_sorted_top_to_bottom():
    manifest = {"glyphs": [glyph("sharp", 10, 35, "s1")]}
    try:
        build_key_signature_candidates(
            manifest, page_number=1, staff_clefs={0: "treble"},
            staff_lines={0: [40, 60, 50, 70, 80]},
        )
    except ValueError as exc:
        assert "ordenadas de arriba hacia abajo" in str(exc)
    else:
        raise AssertionError("Se esperaba rechazar líneas de pentagrama desordenadas")


def test_rejects_non_finite_glyph_coordinates():
    item = glyph("sharp", 10, 35, "s1")
    item["candidate_bbox"][1] = float("inf")
    try:
        build_key_signature_candidates(
            {"glyphs": [item]}, page_number=1, staff_clefs={0: "treble"},
            staff_lines={0: [40, 50, 60, 70, 80]},
        )
    except ValueError as exc:
        assert "candidate_bbox inválido" in str(exc)
    else:
        raise AssertionError("Se esperaba rechazar coordenadas no finitas")



def test_candidate_is_not_applied_until_explicit_acceptance():
    manifest = {"glyphs": [glyph("sharp", 10, 35, "s1")]}
    candidate = build_key_signature_candidates(
        manifest, page_number=1, staff_clefs={0: "treble"},
        staff_lines={0: [40, 50, 60, 70, 80]},
    )
    assert apply_accepted_key_signature_candidates({}, []) == {}
    assert apply_accepted_key_signature_candidates({}, candidate) == {"0": {"F": 1}}


def test_does_not_apply_ambiguous_candidates():
    manifest = {"glyphs": [
        glyph("sharp", 10, 16, "s1"),
        glyph("sharp", 20, 35, "s2"),
    ]}
    candidate = build_key_signature_candidates(
        manifest, page_number=1, staff_clefs={0: "treble"},
        staff_lines={0: [40, 50, 60, 70, 80]},
    )
    assert apply_accepted_key_signature_candidates({}, candidate) == {}


def test_rejects_conflict_between_supplied_and_accepted_signature():
    manifest = {"glyphs": [glyph("sharp", 10, 35, "s1")]}
    candidate = build_key_signature_candidates(
        manifest, page_number=1, staff_clefs={0: "treble"},
        staff_lines={0: [40, 50, 60, 70, 80]},
    )
    try:
        apply_accepted_key_signature_candidates({"0": {"B": -1}}, candidate)
    except ValueError as exc:
        assert "Conflicto" in str(exc)
    else:
        raise AssertionError("Se esperaba detectar conflicto de armaduras")
