"""Exact, descriptive civil-time finite differences for historical comparisons.

Each frozen window is independent. Missing adjacent values remain missing; no
smoothing, fitting, deadband, derivative tolerance, or jerk qualification occurs.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date
from fractions import Fraction
from typing import Any

Point = tuple[Fraction, Fraction | None]


def finite_rates(points: Sequence[Point]) -> list[Point]:
    """First divided differences at interval midpoints, retaining missing gaps."""
    result: list[Point] = []
    for (ta, a), (tb, b) in zip(points[:-1], points[1:], strict=True):
        if tb <= ta:
            raise ValueError("directional diagnostics require strictly increasing civil dates")
        result.append(
            ((ta + tb) / 2, (b - a) / (tb - ta) if a is not None and b is not None else None)
        )
    return result


def calendar_points(rows: Sequence[dict[str, Any]], kind: str, estimator: str) -> list[Point]:
    if kind not in {"employment", "freight"}:
        raise ValueError("unknown directional historical profile")
    points = []
    for row in rows:
        day = date.fromisoformat(row["date"])
        moment = Fraction(day.toordinal())
        value = row[estimator]
        exact = (
            None
            if value is None
            else (
                Fraction(row["predicted_numerator"], row["predicted_denominator"])
                if kind == "freight" and estimator == "predicted"
                else Fraction(value)
            )
        )
        if kind == "freight":
            if day.day != 1:
                raise ValueError("freight diagnostics require calendar-month source dates")
            next_month = (
                date(day.year + 1, 1, 1) if day.month == 12 else date(day.year, day.month + 1, 1)
            )
            days = (next_month - day).days
            moment += Fraction(days, 2)
            exact = exact / days if exact is not None else None
        points.append((moment, exact))
    return points


def rate_metrics(observed: Sequence[Point], predicted: Sequence[Point]) -> dict[str, Any]:
    if len(observed) != len(predicted) or any(
        a[0] != b[0] for a, b in zip(observed, predicted, strict=True)
    ):
        raise ValueError("directional diagnostics require aligned civil times")
    pairs = [
        (a, b)
        for (_, a), (_, b) in zip(observed, predicted, strict=True)
        if a is not None and b is not None
    ]
    errors = [b - a for a, b in pairs]
    nonzero = [(a, b) for a, b in pairs if a != 0 and b != 0]

    def sign(value: Fraction) -> int:
        return (value > 0) - (value < 0)

    return {
        "paired_count": len(pairs),
        "missing_count": len(observed) - len(pairs),
        "sign_agreement": sum(sign(a) == sign(b) for a, b in pairs) / len(pairs) if pairs else None,
        "sign_agreement_reason": None if pairs else "insufficient_pairs",
        "nonzero_pairs": len(nonzero),
        "nonzero_sign_agreement": sum(sign(a) == sign(b) for a, b in nonzero) / len(nonzero)
        if nonzero
        else None,
        "observed_zero_count": sum(a == 0 for a, _ in pairs),
        "predicted_zero_count": sum(b == 0 for _, b in pairs),
        "both_zero_count": sum(a == b == 0 for a, b in pairs),
        "mae": float(sum(map(abs, errors), Fraction()) / len(errors)) if errors else None,
        "rmse": math.sqrt(float(sum((e * e for e in errors), Fraction()) / len(errors)))
        if errors
        else None,
    }


def directional_metrics(aligned: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    result = []
    for series in sorted({row["series_id"] for row in aligned}):
        for window in ("development", "evaluation"):
            rows = sorted(
                (row for row in aligned if row["series_id"] == series and row["window"] == window),
                key=lambda row: row["date"],
            )
            for estimator in ("predicted", "no_change", "seasonal_persistence"):
                observed = calendar_points(rows, kind, "observed")
                predicted = calendar_points(rows, kind, estimator)
                for order in (1, 2):
                    observed, predicted = finite_rates(observed), finite_rates(predicted)
                    result.append(
                        {
                            "series_id": series,
                            "window": window,
                            "estimator": estimator,
                            "order": order,
                            "units": ("jobs/day" if order == 1 else "jobs/day^2")
                            if kind == "employment"
                            else ("kg/day^2" if order == 1 else "kg/day^3"),
                            **rate_metrics(observed, predicted),
                        }
                    )
    return result
