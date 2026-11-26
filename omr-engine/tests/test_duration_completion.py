from fractions import Fraction

import pytest

from palermo_omr.duration_completion import infer_single_unknown_duration


def test_infers_one_missing_quarter_note_from_four_four_measure():
    result = infer_single_unknown_duration([1, 1, 1], 4, 4)
    assert result.status == "inferred_single_unknown"
    assert result.remaining_quarters == Fraction(1, 1)
    assert result.inferred_duration_quarters == Fraction(1, 1)


def test_infers_dotted_quarter_value_exactly():
    result = infer_single_unknown_duration([1, Fraction(3, 2)], 4, 4)
    assert result.inferred_duration_quarters == Fraction(3, 2)


def test_does_not_assign_remainder_when_multiple_events_are_unknown():
    result = infer_single_unknown_duration([1, 1], 4, 4, unknown_event_count=2)
    assert result.status == "remainder_shared_by_multiple_unknowns"
    assert result.remaining_quarters == Fraction(2, 1)
    assert result.inferred_duration_quarters is None


def test_reports_overfull_measure_without_inference():
    result = infer_single_unknown_duration([2, 2, Fraction(1, 2)], 4, 4)
    assert result.status == "overfull"
    assert result.remaining_quarters == Fraction(-1, 2)
    assert result.inferred_duration_quarters is None


def test_does_not_infer_zero_duration():
    result = infer_single_unknown_duration([1, 1, 1, 1], 4, 4)
    assert result.status == "no_positive_remainder"
    assert result.inferred_duration_quarters is None


def test_supports_compound_meter():
    result = infer_single_unknown_duration([Fraction(1, 2)] * 5, 6, 8)
    assert result.inferred_duration_quarters == Fraction(1, 2)


@pytest.mark.parametrize(
    "known,numerator,denominator,unknown",
    [
        ([1], 0, 4, 1),
        ([1], 4, 3, 1),
        ([1], 4, 4, -1),
        ([-1], 4, 4, 1),
        ([float("nan")], 4, 4, 1),
    ],
)
def test_rejects_invalid_inputs(known, numerator, denominator, unknown):
    with pytest.raises(ValueError):
        infer_single_unknown_duration(
            known, numerator, denominator, unknown_event_count=unknown
        )
