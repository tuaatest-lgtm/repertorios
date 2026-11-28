import pytest

from palermo_omr.beam_groups import BeamGroupCandidate
from palermo_omr.rhythm import RhythmCandidate
from palermo_omr.rhythm_interpretation import interpret_rhythm_from_beam_groups


def _rhythm(staff=0, fill="filled", stem="up", duration="quarter", beams=0):
    return RhythmCandidate((10, 10, 12, 8), staff, fill, .9, stem, 30,
                           beams, duration, .8, ())


@pytest.mark.parametrize(
    ("beam_count", "expected"),
    [(1, "eighth"), (2, "sixteenth"), (3, "thirty_second"), (4, "sixty_fourth")],
)
def test_shared_beam_count_maps_to_candidate_duration(beam_count, expected):
    rhythms = [_rhythm(), _rhythm()]
    group = BeamGroupCandidate(0, [0, 1], (10, 10, 40, 4), beam_count,
                               .7, "candidato")
    result = interpret_rhythm_from_beam_groups(rhythms, [group])
    assert [item.duration_candidate for item in result] == [expected, expected]
    assert all(item.status == "candidate_from_shared_beam" for item in result)
    assert all(item.beam_group_indices == (0,) for item in result)


def test_partial_beam_produces_lower_confidence_candidate():
    rhythms = [_rhythm()]
    group = BeamGroupCandidate(
        0, [0], (10, 10, 20, 3), 1, .42, "haz parcial candidato",
        connection_type_candidate="partial",
    )
    result = interpret_rhythm_from_beam_groups(rhythms, [group])[0]
    assert result.duration_candidate == "eighth"
    assert result.status == "candidate_from_partial_beam"
    assert result.confidence <= .55
    assert any("confianza reducida" in warning for warning in result.warnings)


def test_note_uses_maximum_beam_level_across_full_and_partial_segments():
    rhythms = [_rhythm()]
    groups = [
        BeamGroupCandidate(0, [0], (10, 10, 20, 3), 1, .7, "candidato"),
        BeamGroupCandidate(0, [0], (10, 15, 20, 3), 2, .7, "candidato"),
    ]
    result = interpret_rhythm_from_beam_groups(rhythms, groups)[0]
    assert result.duration_candidate == "sixteenth"
    assert result.beam_count_candidate == 2
    assert result.status == "candidate_from_shared_beam"
    assert any("máximo nivel local" in warning for warning in result.warnings)


def test_unfilled_notehead_does_not_receive_beamed_duration():
    rhythm = _rhythm(fill="hollow", duration="half")
    group = BeamGroupCandidate(0, [0], (10, 10, 20, 3), 1, .7, "candidato")
    result = interpret_rhythm_from_beam_groups([rhythm], [group])[0]
    assert result.duration_candidate == "unknown"
    assert result.status == "insufficient_note_evidence"


def test_note_without_group_keeps_only_local_hypothesis():
    result = interpret_rhythm_from_beam_groups([_rhythm()], [])[0]
    assert result.duration_candidate == "quarter"
    assert result.status == "local_candidate_only"


def test_rejects_group_with_invalid_notehead_index():
    group = BeamGroupCandidate(0, [2], (10, 10, 20, 3), 1, .7, "candidato")
    with pytest.raises(ValueError):
        interpret_rhythm_from_beam_groups([_rhythm()], [group])


def test_rejects_group_from_different_staff():
    group = BeamGroupCandidate(1, [0], (10, 10, 20, 3), 1, .7, "candidato")
    with pytest.raises(ValueError):
        interpret_rhythm_from_beam_groups([_rhythm(staff=0)], [group])
