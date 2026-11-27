from fractions import Fraction

import pytest

from palermo_omr.duration_math import duration_in_quarters, sum_tied_durations


@pytest.mark.parametrize(
    "figure,expected",
    [
        ("whole", Fraction(4)),
        ("half", Fraction(2)),
        ("quarter", Fraction(1)),
        ("eighth", Fraction(1, 2)),
        ("sixteenth", Fraction(1, 4)),
        ("thirty_second", Fraction(1, 8)),
        ("sixty_fourth", Fraction(1, 16)),
    ],
)
def test_base_figure_values_in_quarters(figure, expected):
    assert duration_in_quarters(figure) == expected


def test_single_dotted_quarter_is_three_halves():
    assert duration_in_quarters("quarter", 1) == Fraction(3, 2)


def test_double_dotted_half_is_seven_quarters():
    assert duration_in_quarters("half", 2) == Fraction(7, 2)


def test_triple_dotted_eighth_is_fifteen_sixteenths():
    assert duration_in_quarters("eighth", 3) == Fraction(15, 16)


def test_tied_notes_sum_exactly_without_float_drift():
    assert sum_tied_durations([Fraction(1, 2), Fraction(1, 4), Fraction(1, 4)]) == 1


@pytest.mark.parametrize("figure,dots", [("unknown", 0), ("quarter", -1), ("quarter", 5), ("quarter", 1.5)])
def test_rejects_invalid_figure_or_dot_count(figure, dots):
    with pytest.raises(ValueError):
        duration_in_quarters(figure, dots)


@pytest.mark.parametrize("values", [[], [0], [-1], [float("nan")]])
def test_rejects_invalid_tie_duration_lists(values):
    with pytest.raises(ValueError):
        sum_tied_durations(values)

@pytest.mark.parametrize("figure", [None, [], {}, 1])
def test_rejects_non_string_base_figure(figure):
    with pytest.raises(ValueError, match="Figura base desconocida"):
        duration_in_quarters(figure)


@pytest.mark.parametrize("values", [[True], ["1"], [None], [object()]])
def test_rejects_non_numeric_tied_durations(values):
    with pytest.raises(ValueError, match="números válidos"):
        sum_tied_durations(values)
