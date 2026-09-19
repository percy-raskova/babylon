"""Discrete dated changes must not confuse direction with magnitude or calendar length."""

from datetime import date
from fractions import Fraction

import pytest
from tools.devtools.historical_direction import calendar_points, finite_rates, rate_metrics


def points(times, values):
    return [
        (Fraction(t), Fraction(y) if y is not None else None)
        for t, y in zip(times, values, strict=True)
    ]


def test_unequal_interval_linear_and_quadratic_rates_are_exact() -> None:
    times = [0, 2, 5, 9]
    linear = finite_rates(points(times, [3 * t + 7 for t in times]))
    assert linear == points([1, Fraction(7, 2), 7], [3, 3, 3])
    assert [y for _, y in finite_rates(linear)] == [0, 0]
    quadratic = finite_rates(points(times, [t * t for t in times]))
    assert [y for _, y in quadratic] == [2, 7, 14]
    assert [y for _, y in finite_rates(quadratic)] == [2, 2]


def test_reversed_rates_and_exact_zeros_are_distinct() -> None:
    result = rate_metrics(points([0, 1, 2], [2, -3, 0]), points([0, 1, 2], [-2, 3, 0]))
    assert result["sign_agreement"] == pytest.approx(1 / 3)
    assert result["nonzero_sign_agreement"] == 0
    assert (
        result["observed_zero_count"]
        == result["predicted_zero_count"]
        == result["both_zero_count"]
        == 1
    )
    assert result["mae"] == pytest.approx(10 / 3)


def test_same_direction_does_not_hide_tiny_predicted_magnitude() -> None:
    result = rate_metrics(points([1, 2], [1000, 1000]), points([1, 2], [Fraction(1, 1000)] * 2))
    assert result["sign_agreement"] == 1
    assert result["mae"] == result["rmse"] == 999.999


def test_missing_values_never_bridge_first_or_second_differences() -> None:
    first = finite_rates(points([0, 1, 2, 3, 4], [0, 1, None, 3, 4]))
    assert [y for _, y in first] == [1, None, None, 1]
    second = finite_rates(first)
    assert [y for _, y in second] == [None, None, None]
    assert rate_metrics(second, second)["paired_count"] == 0
    assert rate_metrics(second, second)["missing_count"] == 3


def test_month_length_and_leap_year_do_not_create_freight_direction() -> None:
    rows = []
    for month, days in [(1, 31), (2, 29), (3, 31), (4, 30)]:
        mass = Fraction(days, 7)
        rows.append(
            {
                "date": f"2020-{month:02d}-01",
                "predicted": float(mass),
                "predicted_numerator": mass.numerator,
                "predicted_denominator": mass.denominator,
            }
        )
    samples = calendar_points(rows, "freight", "predicted")
    assert samples[1][0] == date(2020, 2, 1).toordinal() + Fraction(29, 2)
    assert [y for _, y in samples] == [Fraction(1, 7)] * 4
    assert [y for _, y in finite_rates(samples)] == [0, 0, 0]
    assert [y for _, y in finite_rates(finite_rates(samples))] == [0, 0]


def test_monthly_mass_baseline_uses_each_target_month_length() -> None:
    rows = [{"date": f"2020-{month:02d}-01", "no_change": 310} for month in (1, 2, 3)]
    rates = finite_rates(calendar_points(rows, "freight", "no_change"))
    assert rates[0][1] > 0 and rates[1][1] < 0


def test_unordered_or_misaligned_times_fail() -> None:
    with pytest.raises(ValueError, match="increasing"):
        finite_rates(points([2, 1], [1, 2]))
    with pytest.raises(ValueError, match="aligned"):
        rate_metrics(points([1], [1]), points([2], [1]))


def test_frozen_windows_do_not_create_derivatives_across_the_boundary() -> None:
    from tools.devtools.historical_direction import directional_metrics

    rows = []
    for year, window, value in ((2014, "development", 100), (2015, "evaluation", 1000)):
        for month in (1, 4, 7):
            rows.append(
                {
                    "date": f"{year}-{month:02d}-01",
                    "series_id": "series",
                    "window": window,
                    "observed": value,
                    "predicted": value,
                    "no_change": value,
                    "seasonal_persistence": value,
                }
            )
    result = directional_metrics(rows, "employment")
    assert all(row["paired_count"] == (2 if row["order"] == 1 else 1) for row in result)
    assert all(row["both_zero_count"] == row["paired_count"] for row in result)
    assert all(row["mae"] == row["rmse"] == 0 for row in result)
