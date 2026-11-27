from fractions import Fraction

import pytest

from palermo_omr.rhythmic_event_groups import RhythmicEventGroupCandidate
from palermo_omr.reviewed_timeline import build_reviewed_page_timelines


def group(event_id, staff, center_x, duration="quarter", status="single_note_candidate", indices=(0,)):
    return RhythmicEventGroupCandidate(
        event_id=event_id,
        staff_index=staff,
        notehead_indices=indices,
        center_x=center_x,
        stem_direction_candidate="up",
        duration_candidate=duration,
        duration_quarters_candidate=Fraction(1) if duration == "quarter" else None,
        voice_id_candidate=None,
        status=status,
        confidence=.8,
        warnings=(),
    )


def test_builds_polyrhythmic_timeline_from_explicit_voice_review():
    groups = [
        group("s1", 0, 10),
        group("s2", 0, 30),
        group("a1", 1, 10),
        group("a2", 1, 20),
        group("a3", 1, 30),
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
