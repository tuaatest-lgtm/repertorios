from fractions import Fraction

import pytest

from palermo_omr.rhythmic_event_groups import RhythmicEventGroupCandidate
from palermo_omr.reviewed_timeline import build_reviewed_page_timelines
from palermo_omr.rhythm_symbols import RestSymbolCandidate
from palermo_omr.pitch import Pitch
from palermo_omr.pitch_candidates import PitchCandidate


def group(event_id, staff, center_x, duration="quarter", status="single_note_candidate", indices=(0,)):
    return RhythmicEventGroupCandidate(
        event_id=event_id,
        staff_index=staff,
        notehead_indices=indices,
        center_x=center_x,
        stem_direction_candidate="up",
        duration_candidate=duration,
        duration_quarters_candidate={"quarter": Fraction(1), "half": Fraction(2)}.get(duration),
        voice_id_candidate=None,
        status=status,
        confidence=.8,
        warnings=(),
    )


def test_builds_polyrhythmic_timeline_from_explicit_voice_review():
    groups = [
        group("s1", 0, 10, duration="half", indices=(0,)),
        group("s2", 0, 30, indices=(1,)),
        group("a1", 1, 10, indices=(0,)),
        group("a2", 1, 20, indices=(1,)),
        group("a3", 1, 30, indices=(2,)),
    ]
    result = build_reviewed_page_timelines(groups, {
        "page_number": 1,
        "measures": [{
            "measure_index": 0,
            "numerator": 4,
            "denominator": 4,
            "confirmed_event_ids": ["s1", "s2", "a1", "a2", "a3"],
            "event_voice_ids": {
                "s1": "soprano", "s2": "soprano",
                "a1": "alto", "a2": "alto", "a3": "alto",
            },
        }],
    })
    timeline = result[0]
    assert timeline["status"] == "placed_events_only"
    assert timeline["onset_groups"] == [
        {"onset_quarters": "0", "event_ids": ["a1", "s1"]},
        {"onset_quarters": "1", "event_ids": ["a2"]},
        {"onset_quarters": "2", "event_ids": ["a3", "s2"]},
    ]
    assert timeline["review_status"] == "human_confirmed_events"


def test_dot_count_changes_only_the_reviewed_event_duration():
    groups = [group("dotted", 0, 10)]
    result = build_reviewed_page_timelines(groups, {
        "page_number": 1,
        "measures": [{
            "measure_index": 0, "numerator": 4, "denominator": 4,
            "confirmed_event_ids": ["dotted"],
            "event_voice_ids": {"dotted": "tenor"},
            "event_dot_counts": {"dotted": 1},
        }],
    })
    event = result[0]["events"][0]
    assert event["duration_quarters"] == "3/2"


def test_rejects_visual_candidates_without_human_confirmation():
    groups = [group("uncertain", 0, 10)]
    with pytest.raises(ValueError, match="confirmed_event_ids"):
        build_reviewed_page_timelines(groups, {
            "page_number": 1,
            "measures": [{
                "measure_index": 0, "numerator": 4, "denominator": 4,
                "confirmed_event_ids": [],
                "event_voice_ids": {},
            }],
        })


def test_rejects_ambiguous_group_even_if_user_lists_it_as_confirmed():
    groups = [group("ambiguous", 0, 10, status="ambiguous")]
    with pytest.raises(ValueError, match="ambiguo"):
        build_reviewed_page_timelines(groups, {
            "page_number": 1,
            "measures": [{
                "measure_index": 0, "numerator": 4, "denominator": 4,
                "confirmed_event_ids": ["ambiguous"],
                "event_voice_ids": {"ambiguous": "bass"},
            }],
        })


def test_rejects_assigning_one_visual_event_to_two_measures():
    groups = [group("e1", 0, 10)]
    measure = {
        "measure_index": 0, "numerator": 4, "denominator": 4,
        "confirmed_event_ids": ["e1"], "event_voice_ids": {"e1": "soprano"},
    }
    with pytest.raises(ValueError, match="dos compases"):
        build_reviewed_page_timelines(groups, {
            "page_number": 1,
            "measures": [measure, {**measure, "measure_index": 1}],
        })


def test_rejects_unreviewed_voice_mapping_or_invalid_meter():
    groups = [group("e1", 0, 10)]
    base = {
        "page_number": 1,
        "measures": [{
            "measure_index": 0, "numerator": 4, "denominator": 4,
            "confirmed_event_ids": ["e1"], "event_voice_ids": {},
        }],
    }
    with pytest.raises(ValueError, match="voz explícita"):
        build_reviewed_page_timelines(groups, base)
    base["measures"][0]["event_voice_ids"] = {"e1": "soprano"}
    base["measures"][0]["denominator"] = 0
    with pytest.raises(ValueError, match="denominator"):
        build_reviewed_page_timelines(groups, base)



def test_reviewed_rest_is_placed_in_the_same_polyphonic_timeline():
    rest = RestSymbolCandidate(
        bbox=(20, 40, 8, 14), staff_index=0, shape_score=0.4,
        confidence=0.2, warning="requires review",
        rest_type_candidate="unclassified", type_confidence=0.0,
    )
    groups = [
        group("n1", 0, 10, indices=(0,)),
        group("n2", 0, 30, indices=(1,)),
    ]
    result = build_reviewed_page_timelines(groups, {
        "page_number": 1,
        "measures": [{
            "measure_index": 0, "numerator": 4, "denominator": 4,
            "confirmed_event_ids": ["n1", "n2"],
            "event_voice_ids": {"n1": "soprano", "n2": "soprano"},
            "event_order_indices": {"n1": 0, "n2": 2},
            "rest_assignments": [{
                "candidate_index": 0, "event_id": "r1", "voice_id": "soprano",
                "measure_index": 0, "order_index": 1, "duration_quarters": "1",
                "confirmed_rest_type": "quarter", "reviewer_confirmed": True,
            }],
        }],
    }, rest_candidates=[rest])
    timeline = result[0]
    assert [(event["event_id"], event["event_type"], event["onset_quarters"])
            for event in timeline["events"]] == [
        ("n1", "note", "0"), ("r1", "rest", "1"), ("n2", "note", "2"),
    ]


def test_reviewed_rest_cannot_be_reused_in_two_measures():
    rest = RestSymbolCandidate(
        bbox=(20, 40, 8, 14), staff_index=0, shape_score=0.4,
        confidence=0.2, warning="requires review",
        rest_type_candidate="unclassified", type_confidence=0.0,
    )
    groups = [group("n1", 0, 10, indices=(0,)), group("n2", 0, 30, indices=(1,))]
    assignment = {
        "candidate_index": 0, "event_id": "r1", "voice_id": "soprano",
        "measure_index": 0, "order_index": 1, "duration_quarters": "1",
        "confirmed_rest_type": "quarter", "reviewer_confirmed": True,
    }
    measures = [
        {"measure_index": i, "numerator": 4, "denominator": 4,
         "confirmed_event_ids": [event_id],
         "event_voice_ids": {event_id: "soprano"},
         "rest_assignments": [{**assignment, "measure_index": i}]}
        for i, event_id in enumerate(("n1", "n2"))
    ]
    with pytest.raises(ValueError, match="reutilizarse"):
        build_reviewed_page_timelines(groups, {"page_number": 1, "measures": measures},
                                      rest_candidates=[rest])



def test_event_order_indices_allow_reviewed_rest_between_notes():
    groups = [group("n1", 0, 10, indices=(0,)), group("n2", 0, 30, indices=(1,))]
    result = build_reviewed_page_timelines(groups, {
        "page_number": 1,
        "measures": [{
            "measure_index": 0, "numerator": 4, "denominator": 4,
            "confirmed_event_ids": ["n1", "n2"],
            "event_voice_ids": {"n1": "soprano", "n2": "soprano"},
            "event_order_indices": {"n1": 0, "n2": 2},
        }],
    })
    assert [(event["event_id"], event["onset_quarters"])
            for event in result[0]["events"]] == [("n1", "0"), ("n2", "1")]


def test_event_order_indices_must_cover_each_confirmed_note_exactly_once():
    groups = [group("n1", 0, 10, indices=(0,)), group("n2", 0, 30, indices=(1,))]
    with pytest.raises(ValueError, match="exactamente un orden"):
        build_reviewed_page_timelines(groups, {
            "page_number": 1,
            "measures": [{
                "measure_index": 0, "numerator": 4, "denominator": 4,
                "confirmed_event_ids": ["n1", "n2"],
                "event_voice_ids": {"n1": "soprano", "n2": "soprano"},
                "event_order_indices": {"n1": 0},
            }],
        })



def test_confirmed_pitch_is_attached_to_its_reviewed_rhythmic_event():
    groups = [group("note-c", 0, 10, indices=(0,))]
    pitches = [PitchCandidate(
        source_kind="filled", source_index=0, staff_index=0,
        diatonic_step_from_bottom=0, clef="treble", key_signature={},
        status="resolved_from_supplied_clef",
        pitch=Pitch(step="E", octave=4, alteration=0, midi=64),
    )]
    result = build_reviewed_page_timelines(groups, {
        "page_number": 1,
        "measures": [{
            "measure_index": 0, "numerator": 4, "denominator": 4,
            "confirmed_event_ids": ["note-c"],
            "event_voice_ids": {"note-c": "soprano"},
            "confirmed_pitch_candidate_indices": {"note-c": [0]},
        }],
    }, pitch_candidates=pitches)
    event = result[0]["events"][0]
    assert event["confirmed_pitches"] == [{
        "source_index": 0, "source_kind": "filled",
        "step": "E", "octave": 4, "alteration": 0, "midi": 64,
    }]


def test_unresolved_pitch_cannot_be_confirmed_as_a_musical_note():
    groups = [group("note-c", 0, 10, indices=(0,))]
    pitches = [PitchCandidate(
        source_kind="filled", source_index=0, staff_index=0,
        diatonic_step_from_bottom=0, clef=None, key_signature={},
        status="unresolved_clef", pitch=None,
    )]
    with pytest.raises(ValueError, match="sin clave"):
        build_reviewed_page_timelines(groups, {
            "page_number": 1,
            "measures": [{
                "measure_index": 0, "numerator": 4, "denominator": 4,
                "confirmed_event_ids": ["note-c"],
                "event_voice_ids": {"note-c": "soprano"},
                "confirmed_pitch_candidate_indices": {"note-c": [0]},
            }],
        }, pitch_candidates=pitches)
