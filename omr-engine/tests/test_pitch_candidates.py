from types import SimpleNamespace

import pytest

from palermo_omr.pitch_candidates import build_pitch_candidates


def head(staff=0, step=0):
    return SimpleNamespace(
        staff_index=staff,
        diatonic_step_from_bottom=step,
    )


def test_keeps_pitch_unresolved_when_visual_clef_is_not_supplied():
    result = build_pitch_candidates([head(step=2)])
    assert result[0].status == "unresolved_clef"
    assert result[0].pitch is None
    assert result[0].diatonic_step_from_bottom == 2


def test_maps_position_to_pitch_only_with_explicit_staff_clef():
    result = build_pitch_candidates(
        [head(step=0), head(step=1)],
        staff_clefs={"0": "treble"},
        key_signatures={"0": {"F": 1}},
    )
    assert [item.status for item in result] == [
        "resolved_from_supplied_clef", "resolved_from_supplied_clef"
    ]
    assert result[0].pitch.midi == 64
    assert result[1].pitch.midi == 66
    assert result[1].to_dict()["pitch"]["step"] == "F"


def test_keeps_other_staff_unresolved_when_only_one_clef_is_known():
    result = build_pitch_candidates(
        [head(staff=0), head(staff=1)],
        staff_clefs={0: "bass"},
    )
    assert result[0].pitch.midi == 43
    assert result[1].pitch is None
    assert result[1].status == "unresolved_clef"


def test_preserves_filled_and_hollow_source_kinds():
    result = build_pitch_candidates(
        [head(), head(step=2)],
        staff_clefs={0: "treble"},
        source_kinds=["filled", "hollow"],
    )
    assert [item.source_kind for item in result] == ["filled", "hollow"]


@pytest.mark.parametrize("clefs", [{"x": "treble"}, {"-1": "treble"}, {"0": "soprano"}])
def test_rejects_invalid_staff_indices_or_unsupported_clefs(clefs):
    with pytest.raises(ValueError):
        build_pitch_candidates([head()], staff_clefs=clefs)


def test_rejects_mismatched_source_kinds():
    with pytest.raises(ValueError, match="source_kinds"):
        build_pitch_candidates([head()], source_kinds=[])
