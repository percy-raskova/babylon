"""Designed warning bounds stay frozen, exact, advisory, and evaluator-only."""

from collections import defaultdict
from fractions import Fraction

import pytest
from tools.devtools.historical_extract import DEFAULT_FIXTURES, FREIGHT_SERIES, load_fixtures
from tools.devtools.historical_warning_bands import (
    assess_errors,
    load_warning_policy,
    warning_assessments,
)


def aligned_observations(kind):
    _, employment, freight = load_fixtures(DEFAULT_FIXTURES)
    result = []
    if kind == "employment":
        for row in employment:
            if row["year"] < 2010:
                continue
            result.append(
                {
                    "series_id": f"{row['county_fips']}/{row['naics_code']}",
                    "date": f"{row['year']}-{row['quarter'] * 3 - 2:02d}-01",
                    "window": "development" if row["year"] < 2015 else "evaluation",
                    "observed": row["employment_begin"],
                    "observed_status": row["status_employment_begin"],
                }
            )
    else:
        monthly = defaultdict(int)
        for row in freight:
            monthly[f"{row['year']}-{row['month']:02d}-01"] += row["shipwt_kg"]
        for day, mass in sorted(monthly.items()):
            if day > "2019-01-01":
                result.append(
                    {
                        "series_id": FREIGHT_SERIES,
                        "date": day,
                        "window": "development" if day < "2020-01-01" else "evaluation",
                        "observed": mass,
                        "observed_status": "observed_import_weight",
                    }
                )
    for row in result:
        row.update(
            predicted=0,
            predicted_numerator=0,
            predicted_denominator=1,
            no_change=0,
            seasonal_persistence=0,
        )
    return result


def test_strict_boundaries_and_signed_bias_use_exact_arithmetic() -> None:
    assert assess_errors([Fraction(-10), Fraction(10)], Fraction(100))["status"] == "within_band"
    assert assess_errors([Fraction(5)], Fraction(100))["status"] == "within_band"
    assert assess_errors([Fraction(-5)], Fraction(100))["status"] == "within_band"
    epsilon = Fraction(1, 10**20)
    assert assess_errors([Fraction(5) + epsilon], Fraction(100))["breaches"] == ["absolute_bias"]
    assert assess_errors([Fraction(-5) - epsilon], Fraction(100))["breaches"] == ["absolute_bias"]
    assert assess_errors([Fraction(-10) - epsilon, Fraction(10) + epsilon], Fraction(100))[
        "breaches"
    ] == ["mae"]
    assert assess_errors([], Fraction(100))["status"] == "unavailable"
    with pytest.raises(ValueError, match="positive"):
        assess_errors([Fraction(1)], Fraction(0))


@pytest.mark.parametrize("kind", ["employment", "freight"])
def test_heldout_changes_cannot_reset_warning_scales_or_bands(kind) -> None:
    policy = load_warning_policy()
    rows = aligned_observations(kind)
    before = warning_assessments(rows, kind, policy)
    policy_bytes = policy.model_dump_json()
    for row in rows:
        if row["window"] == "evaluation":
            row["observed"] *= 10
    after = warning_assessments(rows, kind, policy)
    assert before != after
    assert policy.model_dump_json() == policy_bytes
    for first, second in zip(before, after, strict=True):
        for key in ("development_scale", "mae_warning_above", "absolute_bias_warning_above"):
            assert first[key] == second[key]
        if first["window"] == "development":
            assert first == second


@pytest.mark.parametrize(
    "mutation", ["changed", "missing", "suppressed", "zero", "duplicate_date", "boolean"]
)
def test_changed_or_unusable_development_basis_fails_instead_of_resetting(mutation) -> None:
    rows = aligned_observations("employment")
    if mutation == "changed":
        rows[1]["observed"] += 1
    elif mutation == "missing":
        rows[1]["observed"] = None
    elif mutation == "suppressed":
        rows[1]["observed_status"] = 5
    elif mutation == "zero":
        for row in rows:
            row["observed"] = 0
    elif mutation == "duplicate_date":
        rows[1]["date"] = rows[0]["date"]
    else:
        rows[1]["observed"] = True
    with pytest.raises(ValueError):
        warning_assessments(rows, "employment", load_warning_policy())


def test_policy_rejects_unknown_fields_and_inexact_counts() -> None:
    from tools.devtools.historical_warning_bands import HistoricalWarningPolicy

    value = load_warning_policy().model_dump(mode="json", by_alias=True)
    value["arbitrary_override"] = 1
    with pytest.raises(ValueError):
        HistoricalWarningPolicy.model_validate(value)
    del value["arbitrary_override"]
    value["series"][0]["observation_count"] = True
    with pytest.raises(ValueError):
        HistoricalWarningPolicy.model_validate(value)
