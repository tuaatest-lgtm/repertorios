import pytest

from palermo_omr.page_pitch_adapter import build_pitch_candidates_from_page_analysis


def _page():
    return {
        "page_number": 1,
        "notehead_candidates": [
            {"bbox": [20, 50, 10, 8], "center_x": 25, "center_y": 54,
             "staff_index": 0, "diatonic_step_from_bottom": 1},
            {"bbox": [80, 50, 10, 8], "center_x": 85, "center_y": 54,
             "staff_index": 0, "diatonic_step_from_bottom": 1},
            {"bbox": [20, 150, 10, 8], "center_x": 25, "center_y": 154,
             "staff_index": 1, "diatonic_step_from_bottom": 1},
        ],
    }


def test_page_pitch_adapter_uses_only_confirmed_clef_and_key_signature():
    result = build_pitch_candidates_from_page_analysis(
        _page(),
        {
            0: {"clef": "treble", "clef_status": "human_confirmed",
                "key_signature": {"F": 1}, "key_signature_status": "human_confirmed"},
            1: {"clef": "bass", "clef_status": "human_confirmed",
                "key_signature": {}, "key_signature_status": "human_confirmed"},
        },
    )
    pitches = result["pitch_candidates"]
    assert [item["pitch"]["midi"] for item in pitches] == [66, 66, 45]
    assert all(item["status"] == "resolved_from_supplied_clef" for item in pitches)
    assert result["unresolved_staff_contexts"] == []


def test_page_pitch_adapter_never_defaults_missing_clef_or_pending_key_signature():
    result = build_pitch_candidates_from_page_analysis(
        _page(),
        {
            0: {"clef": "treble", "clef_status": "human_confirmed",
                "key_signature": {"F": 1}, "key_signature_status": "pending_human_review"},
        },
    )
    assert [item["status"] for item in result["pitch_candidates"]] == [
        "unresolved_key_signature", "unresolved_key_signature", "unresolved_clef",
    ]
    assert all(item["pitch"] is None for item in result["pitch_candidates"])
    assert result["unresolved_staff_contexts"] == [
        {"staff_index": "0", "reason": "unresolved_key_signature"},
        {"staff_index": "1", "reason": "unresolved_clef"},
    ]


def test_page_pitch_adapter_preserves_explicit_accidental_measure_state():
    page = {
        "page_number": 2,
        "notehead_candidates": [
            {"center_x": 20, "staff_index": 0, "diatonic_step_from_bottom": 1},
            {"center_x": 50, "staff_index": 0, "diatonic_step_from_bottom": 1},
            {"center_x": 20, "staff_index": 0, "diatonic_step_from_bottom": 1},
        ],
    }
    result = build_pitch_candidates_from_page_analysis(
        page,
        {0: {"clef": "treble", "clef_status": "human_confirmed",
             "key_signature": {"F": 1}, "key_signature_status": "human_confirmed"}},
        measure_ids=["m1", "m1", "m2"],
        explicit_accidentals=["natural", None, None],
    )
    assert [item["pitch"]["midi"] for item in result["pitch_candidates"]] == [65, 65, 66]


def test_page_pitch_adapter_rejects_invalid_staff_context_and_alignment():
    page = _page()
    with pytest.raises(ValueError, match="Clave confirmada"):
        build_pitch_candidates_from_page_analysis(
            page,
            {0: {"clef": "unknown", "clef_status": "human_confirmed",
                 "key_signature": {}, "key_signature_status": "human_confirmed"}},
        )
    with pytest.raises(ValueError, match="explicit_accidentals"):
        build_pitch_candidates_from_page_analysis(
            page,
            {0: {"clef": "treble", "clef_status": "human_confirmed",
                 "key_signature": {}, "key_signature_status": "human_confirmed"},
             1: {"clef": "bass", "clef_status": "human_confirmed",
                 "key_signature": {}, "key_signature_status": "human_confirmed"}},
            explicit_accidentals=["natural"],
        )
