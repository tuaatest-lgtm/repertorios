import pytest

from palermo_omr.imaging import StaffCandidate
from palermo_omr.rhythm import RhythmCandidate
from palermo_omr.staff_voice_layers import detect_staff_voice_layer_candidates
from palermo_omr.symbols import NoteheadCandidate


def _inputs(xs, directions, staff_indices=None):
    staff_indices = staff_indices or [0] * len(xs)
    heads, rhythms = [], []
    for index, (x, direction, staff) in enumerate(zip(xs, directions, staff_indices)):
        heads.append(NoteheadCandidate(
            bbox=(int(x - 5), 70, 10, 8), center_x=float(x), center_y=80.0,
            staff_index=staff, diatonic_step_from_bottom=index,
            fill_ratio=.8, notehead_shape_score=.9, confidence=.9,
        ))
        rhythms.append(RhythmCandidate(
            (int(x - 5), 70, 10, 8), staff, "filled", .9, direction, 30,
            0, "quarter", .8, (),
        ))
    return heads, rhythms


def _staves(count=1):
    return [StaffCandidate([60, 70, 80, 90, 100], 10.0, 1.0) for _ in range(count)]


def test_opposite_stems_nearby_in_same_staff_propose_layers_without_assigning_voices():
    heads, rhythms = _inputs([100, 108, 118], ["up", "down", "up"])
    result = detect_staff_voice_layer_candidates(_staves(), heads, rhythms)
    assert len(result) == 1
    proposal = result[0]
    assert proposal.upward_notehead_indices == (0, 2)
    assert proposal.downward_notehead_indices == (1,)
    assert proposal.status == "proposed_independent_layers"
    assert proposal.confidence == .5
    assert any("No se asignan voces" in warning for warning in proposal.warnings)


def test_same_stem_direction_does_not_propose_independent_layers():
    heads, rhythms = _inputs([100, 108, 118], ["up", "up", "up"])
    assert detect_staff_voice_layer_candidates(_staves(), heads, rhythms) == ()


def test_opposite_stems_far_apart_do_not_form_one_local_layer_proposal():
    heads, rhythms = _inputs([100, 140], ["up", "down"])
    result = detect_staff_voice_layer_candidates(
        _staves(), heads, rhythms, max_horizontal_span_spacing=2.0
    )
    assert result == ()


def test_different_staves_are_never_combined_as_two_voices_of_one_staff():
    heads, rhythms = _inputs([100, 103], ["up", "down"], [0, 1])
    result = detect_staff_voice_layer_candidates(_staves(2), heads, rhythms)
    assert result == ()


def test_unknown_stem_direction_is_not_used_as_a_voice_layer():
    heads, rhythms = _inputs([100, 105, 110], ["up", "none", "down"])
    result = detect_staff_voice_layer_candidates(_staves(), heads, rhythms)
    assert len(result) == 1
    assert result[0].upward_notehead_indices == (0,)
    assert result[0].downward_notehead_indices == (2,)
    assert 1 not in result[0].upward_notehead_indices + result[0].downward_notehead_indices


def test_rejects_mismatched_inputs_and_invalid_window():
    heads, rhythms = _inputs([100], ["up"])
    with pytest.raises(ValueError, match="por cada cabeza"):
        detect_staff_voice_layer_candidates(_staves(), heads, [])
    with pytest.raises(ValueError, match="positivo"):
        detect_staff_voice_layer_candidates(
            _staves(), heads, rhythms, max_horizontal_span_spacing=0
        )
