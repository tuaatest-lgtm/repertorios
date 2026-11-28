import pytest

from palermo_omr.voice_assignment import apply_reviewed_voice_assignments


def _event(event_id, staff=0, status="incomplete_candidate", pitch_status="resolved_from_supplied_clef",
           event_type="note", voice=None):
    pitches = [] if event_type == "rest" else [{
        "status": pitch_status, "pitch": {"midi": 60},
    }]
    return {
        "event_id": event_id, "staff_index": staff,
        "notehead_candidate_ids": [] if event_type == "rest" else [event_id],
        "pitch_candidates": pitches, "voice_id_candidate": voice,
        "duration_candidate": "quarter", "duration_quarters_candidate": "1",
        "status": status, "warnings": [], "event_type": event_type,
    }


def test_confirmed_staff_context_resolves_voice_and_promotes_complete_event_for_review():
    result = apply_reviewed_voice_assignments(
        [_event("soprano-note")],
        {0: {"voice_id": "soprano", "status": "human_confirmed"}},
    )
    event = result["event_candidates"][0]
    assert event["voice_id_candidate"] == "soprano"
    assert event["status"] == "ready_for_review"
    assert result["assignments"][0]["source"] == "staff_context"


def test_event_override_separates_polyphonic_voices_on_same_staff():
    result = apply_reviewed_voice_assignments(
        [_event("upper", voice="soprano"), _event("lower")],
        {0: {"voice_id": "soprano", "status": "human_confirmed"}},
        event_voice_overrides={
            "lower": {"voice_id": "alto", "status": "human_confirmed"},
        },
    )
    assert [item["voice_id_candidate"] for item in result["event_candidates"]] == [
        "soprano", "alto",
    ]
    assert result["assignments"][1]["source"] == "event_override"


def test_pending_event_override_does_not_fallback_to_staff_voice():
    result = apply_reviewed_voice_assignments(
        [_event("ambiguous")],
        {0: {"voice_id": "soprano", "status": "human_confirmed"}},
        event_voice_overrides={
            "ambiguous": {"voice_id": "alto", "status": "pending_human_review"},
        },
    )
    assert result["event_candidates"][0]["voice_id_candidate"] is None
    assert result["event_candidates"][0]["status"] == "incomplete_candidate"
    assert result["unresolved"] == [
        {"event_id": "ambiguous", "reason": "voice_context_not_human_confirmed"},
    ]


def test_unresolved_pitch_or_duration_does_not_promote_event():
    result = apply_reviewed_voice_assignments(
        [_event("unknown-pitch", pitch_status="unresolved_clef"),
         {**_event("unknown-duration"), "duration_quarters_candidate": None}],
        {0: {"voice_id": "tenor", "status": "human_confirmed"}},
    )
    assert all(item["status"] == "incomplete_candidate" for item in result["event_candidates"])
    assert all(item["voice_id_candidate"] == "tenor" for item in result["event_candidates"])


def test_rest_can_receive_voice_without_pitch_candidates():
    result = apply_reviewed_voice_assignments(
        [_event("rest", event_type="rest")],
        {0: {"voice_id": "bass", "status": "human_confirmed"}},
    )
    assert result["event_candidates"][0]["status"] == "ready_for_review"
    assert result["event_candidates"][0]["voice_id_candidate"] == "bass"


def test_rejects_invalid_context_and_duplicate_event_ids():
    with pytest.raises(ValueError, match="únicos"):
        apply_reviewed_voice_assignments(
            [_event("same"), _event("same")],
            {0: {"voice_id": "soprano", "status": "human_confirmed"}},
        )
    with pytest.raises(ValueError, match="Contexto de voz"):
        apply_reviewed_voice_assignments([_event("x")], {0: "soprano"})


def test_applies_confirmed_voice_ids_to_timeline_and_clears_unreviewed_values():
    from palermo_omr.voice_assignment import apply_voice_assignments_to_timelines

    assignment = apply_reviewed_voice_assignments(
        [_event("a"), _event("b")],
        {0: {"voice_id": "soprano", "status": "human_confirmed"}},
        event_voice_overrides={
            "b": {"voice_id": "alto", "status": "pending_human_review"},
        },
    )
    result = apply_voice_assignments_to_timelines(
        [{"measure_index": 0, "events": [
            {"event_id": "a", "voice_id": "unreviewed"},
            {"event_id": "b", "voice_id": "tenor"},
        ]}],
        assignment,
    )
    assert [item["voice_id"] for item in result[0]["events"]] == ["soprano", None]
