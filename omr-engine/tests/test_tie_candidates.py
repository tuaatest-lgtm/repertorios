from fractions import Fraction

import pytest

from palermo_omr.tie_candidates import (
    TieArcObservation,
    TieNoteObservation,
    build_tie_link_candidates,
)


def note(event_id, onset, *, pitch=60, voice="soprano", staff=0, x=40, measure=0):
    return TieNoteObservation(
        event_id=event_id,
        voice_id=voice,
        staff_index=staff,
        onset_quarters=Fraction(onset),
        duration_quarters=Fraction(1),
        pitch_midi=pitch,
        notehead_bbox=(x, 70, 12, 8),
        staff_spacing=10.0,
        measure_index=measure,
    )


def arc(arc_id="arc-1", *, x=50, y=64, w=34, h=8, staff=0):
    return TieArcObservation(arc_id, staff, (x, y, w, h))


def test_proposes_tie_for_same_pitch_contiguous_events_and_intervening_arc():
    result = build_tie_link_candidates(
        [note("a", 0, x=40), note("b", 1, x=80)],
        [arc()],
    )
    assert len(result) == 1
    assert result[0].status == "proposed_tie"
    assert result[0].source_event_id == "a"
    assert result[0].target_event_id == "b"
    assert result[0].pitch_match
    assert result[0].temporal_continuity


def test_allows_contiguous_tie_across_measure_boundary_with_global_time():
    result = build_tie_link_candidates(
        [note("a", 3, x=40, measure=0), note("b", 4, x=80, measure=1)],
        [arc()],
    )
    assert len(result) == 1
    assert result[0].status == "proposed_tie"


def test_does_not_propose_when_same_pitch_events_are_not_contiguous():
    result = build_tie_link_candidates(
        [note("a", 0, x=40), note("b", 2, x=80)],
        [arc()],
    )
    assert result == ()


def test_does_not_propose_when_pitch_differs():
    result = build_tie_link_candidates(
        [note("a", 0, x=40), note("b", 1, pitch=62, x=80)],
        [arc()],
    )
    assert result == ()


def test_does_not_propose_across_different_voices_or_staves():
    different_voice = build_tie_link_candidates(
        [note("a", 0, x=40), note("b", 1, x=80, voice="alto")],
        [arc()],
    )
    different_staff = build_tie_link_candidates(
        [note("a", 0, x=40), note("b", 1, x=80, staff=1)],
        [arc(staff=0)],
    )
    assert different_voice == ()
    assert different_staff == ()


def test_rejects_arc_outside_horizontal_gap():
    result = build_tie_link_candidates(
        [note("a", 0, x=40), note("b", 1, x=100)],
        [arc(x=150)],
    )
    assert result == ()


def test_rejects_arc_too_far_vertically():
    result = build_tie_link_candidates(
        [note("a", 0, x=40), note("b", 1, x=80)],
        [arc(y=110)],
    )
    assert result == ()


def test_ambiguous_when_multiple_arcs_match_the_same_note_pair():
    result = build_tie_link_candidates(
        [note("a", 0, x=40), note("b", 1, x=80)],
        [arc("arc-1"), arc("arc-2", x=51, y=65, w=32, h=8)],
    )
    assert len(result) == 2
    assert all(item.status == "ambiguous_tie_candidate" for item in result)


def test_validation_rejects_duplicate_ids_and_invalid_boxes():
    with pytest.raises(ValueError, match="único"):
        build_tie_link_candidates(
            [note("a", 0), note("a", 1, x=80)],
            [],
        )
    invalid = TieNoteObservation(
        "bad", "soprano", 0, Fraction(0), Fraction(1), 60,
        (40, 70, 0, 8), 10.0, 0,
    )
    with pytest.raises(ValueError, match="notehead_bbox"):
        build_tie_link_candidates([invalid], [])
