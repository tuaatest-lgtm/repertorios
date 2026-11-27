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


def test_explicit_accidental_persists_within_measure_and_resets_in_next_measure():
    heads = [head(step=1), head(step=1), head(step=1)]
    result = build_pitch_candidates(
        heads,
        staff_clefs={0: "treble"},
        key_signatures={0: {"F": 1}},
        explicit_accidentals=["natural", None, None],
        measure_ids=["m1", "m1", "m2"],
    )
    assert [item.pitch.alteration for item in result] == [0, 0, 1]
    assert [item.pitch.midi for item in result] == [65, 65, 66]


def test_accidental_state_is_independent_per_staff_and_measure():
    result = build_pitch_candidates(
        [head(0, 1), head(1, 1), head(0, 1)],
        staff_clefs={0: "treble", 1: "treble"},
        explicit_accidentals=["flat", None, None],
        measure_ids=[1, 1, 1],
    )
    assert [item.pitch.alteration for item in result] == [-1, 0, -1]


def test_requires_measure_ids_when_explicit_accidentals_are_provided():
    with pytest.raises(ValueError, match="deben proporcionarse juntos"):
        build_pitch_candidates(
            [head()], staff_clefs={0: "treble"}, explicit_accidentals=["sharp"]
        )


def test_rejects_noteheads_out_of_reading_order_when_accidental_state_is_used():
    heads = [
        SimpleNamespace(staff_index=0, diatonic_step_from_bottom=1, center_x=40.0),
        SimpleNamespace(staff_index=0, diatonic_step_from_bottom=1, center_x=20.0),
    ]
    with pytest.raises(ValueError, match="izquierda a derecha"):
        build_pitch_candidates(
            heads,
            staff_clefs={0: "treble"},
            explicit_accidentals=["natural", None],
            measure_ids=["m1", "m1"],
        )


def test_accidental_in_chord_applies_to_same_written_pitch_regardless_of_head_order():
    heads = [
        SimpleNamespace(staff_index=0, diatonic_step_from_bottom=1, center_x=20.0),
        SimpleNamespace(staff_index=0, diatonic_step_from_bottom=1, center_x=21.0),
        SimpleNamespace(staff_index=0, diatonic_step_from_bottom=1, center_x=35.0),
    ]
    result = build_pitch_candidates(
        heads,
        staff_clefs={0: "treble"},
        key_signatures={0: {"F": 1}},
        explicit_accidentals=[None, "natural", None],
        measure_ids=["m1", "m1", "m1"],
        simultaneous_group_ids=["chord-1", "chord-1", "note-2"],
    )
    assert [item.pitch.midi for item in result] == [65, 65, 65]
    assert [item.simultaneous_group_id for item in result] == [
        "chord-1", "chord-1", "note-2"
    ]


def test_conflicting_explicit_accidentals_for_same_chord_pitch_are_rejected():
    with pytest.raises(ValueError, match="incompatibles"):
        build_pitch_candidates(
            [head(step=1), head(step=1)],
            staff_clefs={0: "treble"},
            explicit_accidentals=["sharp", "flat"],
            measure_ids=["m1", "m1"],
            simultaneous_group_ids=["chord", "chord"],
        )


def test_simultaneous_group_must_be_contiguous():
    with pytest.raises(ValueError, match="contiguos"):
        build_pitch_candidates(
            [head(), head(step=1), head(step=2)],
            staff_clefs={0: "treble"},
            explicit_accidentals=[None, None, None],
            measure_ids=["m1", "m1", "m1"],
            simultaneous_group_ids=["chord", "other", "chord"],
        )


def test_simultaneous_group_requires_confirmed_measure_ids():
    with pytest.raises(ValueError, match="requiere measure_ids"):
        build_pitch_candidates(
            [head()],
            staff_clefs={0: "treble"},
            simultaneous_group_ids=["chord"],
        )
