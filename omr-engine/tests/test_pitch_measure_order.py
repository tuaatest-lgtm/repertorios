from types import SimpleNamespace

import pytest

from palermo_omr.pitch_candidates import build_pitch_candidates


def head(staff, step, x):
    return SimpleNamespace(
        staff_index=staff,
        diatonic_step_from_bottom=step,
        center_x=x,
    )


def test_rejects_a_measure_that_reappears_after_the_next_measure_on_same_staff():
    heads = [
        head(0, 1, 10.0),
        head(0, 1, 20.0),
        head(0, 1, 30.0),
    ]
    with pytest.raises(ValueError, match="orden continuo"):
        build_pitch_candidates(
            heads,
            staff_clefs={0: "treble"},
            explicit_accidentals=["natural", None, None],
            measure_ids=["measure-1", "measure-2", "measure-1"],
        )


def test_measure_order_is_tracked_independently_for_each_staff():
    heads = [
        head(0, 1, 10.0),
        head(1, 1, 10.0),
        head(0, 1, 20.0),
        head(1, 1, 20.0),
    ]
    result = build_pitch_candidates(
        heads,
        staff_clefs={0: "treble", 1: "bass"},
        explicit_accidentals=[None, None, None, None],
        measure_ids=["staff0-m1", "staff1-m1", "staff0-m2", "staff1-m2"],
    )
    assert len(result) == 4


def test_unassigned_measure_does_not_close_a_confirmed_measure_sequence():
    heads = [
        head(0, 1, 10.0),
        head(0, 2, 20.0),
        head(0, 1, 30.0),
    ]
    result = build_pitch_candidates(
        heads,
        staff_clefs={0: "treble"},
        explicit_accidentals=["natural", None, None],
        measure_ids=["measure-1", None, "measure-1"],
    )
    assert [item.pitch.alteration for item in result] == [0, 0, 0]
