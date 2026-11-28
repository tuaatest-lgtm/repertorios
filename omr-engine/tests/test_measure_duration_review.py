from fractions import Fraction

import pytest

from palermo_omr.measure_duration_review import build_measure_duration_completion_candidates


def event(event_id, voice="soprano", duration=1, kind="note"):
    return {
        "event_id": event_id,
        "voice_id": voice,
        "duration_quarters": duration,
        "event_type": kind,
    }


def test_suggests_one_missing_quarter_from_complete_four_four_voice():
    result = build_measure_duration_completion_candidates(
        [event("a", duration=1), event("b", duration=1), event("c", duration=1),
         event("unknown", duration=None)],
        4, 4, measure_complete_confirmed=True, ties_and_tuplets_resolved=True,
    )
    assert len(result) == 1
    candidate = result[0]
    assert candidate.status == "single_unknown_duration_candidate"
    assert candidate.event_id == "unknown"
    assert candidate.candidate_duration_quarters == Fraction(1)
    assert candidate.candidate_base_duration == "quarter"
    assert candidate.candidate_dots == 0


def test_suggests_dotted_value_using_exact_fraction():
    result = build_measure_duration_completion_candidates(
        [event("a", duration=1), event("b", duration=Fraction(3, 2)),
         event("unknown", duration=None)],
        4, 4, measure_complete_confirmed=True, ties_and_tuplets_resolved=True,
    )[0]
    assert result.candidate_duration_quarters == Fraction(3, 2)
    assert result.candidate_base_duration == "quarter"
    assert result.candidate_dots == 1


def test_does_not_suggest_when_review_prerequisites_are_missing():
    result = build_measure_duration_completion_candidates(
        [event("a", duration=1), event("unknown", duration=None)],
        4, 4, measure_complete_confirmed=False, ties_and_tuplets_resolved=True,
    )[0]
    assert result.status == "review_prerequisites_not_confirmed"
    assert result.candidate_duration_quarters is None


def test_does_not_split_remainder_between_multiple_unknown_events():
    result = build_measure_duration_completion_candidates(
        [event("a", duration=1), event("x", duration=None), event("y", duration=None)],
        4, 4, measure_complete_confirmed=True, ties_and_tuplets_resolved=True,
    )[0]
    assert result.status == "multiple_unknown_durations"
    assert result.candidate_duration_quarters is None


def test_does_not_infer_unknown_rest_or_nonstandard_remainder():
    rest = build_measure_duration_completion_candidates(
        [event("rest", duration=None, kind="rest"), event("note", duration=1)],
        4, 4, measure_complete_confirmed=True, ties_and_tuplets_resolved=True,
    )[0]
    assert rest.status == "unknown_rest_not_inferred"

    unsupported = build_measure_duration_completion_candidates(
        [event("a", duration=Fraction(1, 3)), event("unknown", duration=None)],
        4, 4, measure_complete_confirmed=True, ties_and_tuplets_resolved=True,
    )[0]
    assert unsupported.status == "unsupported_metric_remainder"
    assert unsupported.candidate_duration_quarters is None


def test_reports_overfull_measure_without_inference():
    result = build_measure_duration_completion_candidates(
        [event("a", duration=3), event("b", duration=2), event("unknown", duration=None)],
        4, 4, measure_complete_confirmed=True, ties_and_tuplets_resolved=True,
    )[0]
    assert result.status == "overfull"
    assert result.remaining_quarters == -1
    assert result.candidate_duration_quarters is None


def test_keeps_voice_completion_independent_for_polyphonic_measure():
    result = build_measure_duration_completion_candidates(
        [event("s1", "soprano", 2), event("s2", "soprano", 1),
         event("s3", "soprano", None),
         event("a1", "alto", 1), event("a2", "alto", 1),
         event("a3", "alto", 1), event("a4", "alto", 1)],
        4, 4, measure_complete_confirmed=True, ties_and_tuplets_resolved=True,
    )
    by_voice = {item.voice_id: item for item in result}
    assert by_voice["soprano"].candidate_duration_quarters == 1
    assert by_voice["alto"].status == "no_unknown_duration"


def test_serializes_exact_rational_candidate_values():
    result = build_measure_duration_completion_candidates(
        [event("a", duration=1), event("unknown", duration=None)],
        4, 4, measure_complete_confirmed=True, ties_and_tuplets_resolved=True,
    )[0].to_dict()
    assert result["expected_quarters"] == "4"
    assert result["remaining_quarters"] == "3"
    assert result["candidate_duration_quarters"] == "3"
