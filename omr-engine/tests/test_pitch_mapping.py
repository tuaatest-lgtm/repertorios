import pytest

from palermo_omr.pitch import MeasureAccidentals, pitch_from_staff_step


@pytest.mark.parametrize(
    "clef, expected",
    [
        ("treble", ("E", 4, 64)),
        ("bass", ("G", 2, 43)),
        ("alto", ("F", 3, 53)),
        ("tenor", ("D", 3, 50)),
    ],
)
def test_bottom_staff_line_for_each_clef(clef, expected):
    pitch = pitch_from_staff_step(0, clef)
    assert (pitch.step, pitch.octave, pitch.midi) == expected


def test_key_signature_and_explicit_natural():
    state = MeasureAccidentals()
    sharp_f = pitch_from_staff_step(1, "treble", {"F": 1}, accidental_state=state)
    natural_f = pitch_from_staff_step(
        1, "treble", {"F": 1}, "natural", state
    )
    repeated_f = pitch_from_staff_step(1, "treble", {"F": 1}, accidental_state=state)

    assert sharp_f.midi == 66
    assert natural_f.midi == 65
    assert repeated_f.midi == 65


def test_accidental_state_resets_at_barline():
    state = MeasureAccidentals()
    altered = pitch_from_staff_step(1, "treble", explicit_accidental="flat", accidental_state=state)
    assert altered.midi == 64
    state.reset()
    restored = pitch_from_staff_step(1, "treble", accidental_state=state)
    assert restored.midi == 65


def test_unknown_clef_is_rejected():
    with pytest.raises(ValueError):
        pitch_from_staff_step(0, "unknown")
