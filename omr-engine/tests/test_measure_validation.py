import pytest

from palermo_omr.measure_validation import validate_measure_duration


def test_validates_common_time():
    result = validate_measure_duration([1, 1, 1, 1], 4, 4)
    assert result.status == "complete"
    assert result.expected_quarter_notes == 4


def test_validates_compound_six_eight_as_three_quarters():
    result = validate_measure_duration([0.5] * 6, 6, 8)
    assert result.status == "complete"
    assert result.expected_quarter_notes == 3


def test_detects_underfull_measure():
    result = validate_measure_duration([1, 1, 1], 4, 4)
    assert result.status == "underfull"
    assert result.difference_quarter_notes == -1


def test_allows_short_pickup_as_provisional():
    result = validate_measure_duration([1, 1], 4, 4, is_pickup=True)
    assert result.status == "pickup_incomplete"


def test_detects_overfull_measure():
    result = validate_measure_duration([1, 1, 1, 1, 0.5], 4, 4)
    assert result.status == "overfull"


@pytest.mark.parametrize(
    "durations,numerator,denominator",
    [
        ([0], 4, 4),
        ([-1], 4, 4),
        ([float("nan")], 4, 4),
        ([1], 0, 4),
        ([1], 4, 3),
    ],
)
def test_rejects_invalid_measure_inputs(durations, numerator, denominator):
    with pytest.raises(ValueError):
        validate_measure_duration(durations, numerator, denominator)
