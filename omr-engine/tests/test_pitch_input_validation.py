import pytest

from palermo_omr.pitch import MeasureAccidentals, pitch_from_staff_step


def test_pitch_from_staff_step_rejects_non_integer_steps():
    for value in (True, 1.5, "2"):
        with pytest.raises(ValueError, match="entero"):
            pitch_from_staff_step(value, "treble")


def test_pitch_from_staff_step_rejects_invalid_key_signature_letters():
    with pytest.raises(ValueError, match="Letra no válida"):
        pitch_from_staff_step(0, "treble", {"H": 1})


@pytest.mark.parametrize("alteration", [True, 1.5, "1", 3, -3])
def test_pitch_from_staff_step_rejects_invalid_key_signature_values(alteration):
    with pytest.raises(ValueError):
        pitch_from_staff_step(0, "treble", {"F": alteration})


def test_pitch_from_staff_step_applies_valid_key_signature_and_explicit_natural():
    assert pitch_from_staff_step(1, "treble", {"F": 1}).midi == 66
    assert pitch_from_staff_step(1, "treble", {"F": 1}, "natural").midi == 65


def test_accidental_state_is_scoped_to_letter_and_octave_and_can_reset():
    state = MeasureAccidentals()
    assert state.resolve("F", 5, {"F": 1}, "natural") == 0
    assert state.resolve("F", 5, {"F": 1}) == 0
    assert state.resolve("F", 4, {"F": 1}) == 1
    state.reset()
    assert state.resolve("F", 5, {"F": 1}) == 1


def test_accidental_state_rejects_invalid_pitch_coordinates():
    state = MeasureAccidentals()
    with pytest.raises(ValueError, match="Letra musical"):
        state.resolve("H", 4)
    with pytest.raises(ValueError, match="octava"):
        state.resolve("C", True)

@pytest.mark.parametrize("clef", [None, [], {}])
def test_pitch_rejects_non_string_clef(clef):
    with pytest.raises(ValueError, match="Clave no soportada"):
        pitch_from_staff_step(0, clef)


@pytest.mark.parametrize("accidental", [[], {}, 1])
def test_pitch_rejects_non_string_accidental(accidental):
    with pytest.raises(ValueError, match="Alteración no reconocida"):
        pitch_from_staff_step(0, "treble", explicit_accidental=accidental)


def test_pitch_rejects_wrong_accidental_state_type():
    with pytest.raises(ValueError, match="accidental_state"):
        pitch_from_staff_step(0, "treble", accidental_state={})


def test_natural_cancellation_persists_for_same_octave_only():
    state = MeasureAccidentals()
    assert state.resolve("F", 4, {"F": 1}, "natural") == 0
    assert state.resolve("F", 4, {"F": 1}) == 0
    assert state.resolve("F", 5, {"F": 1}) == 1
