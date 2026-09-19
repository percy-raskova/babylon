"""Evaluate historical Rust trajectories with separately pinned observations.

Fit is advisory. Incomplete execution, invalid provenance, missing committed
states, and changed source coverage fail. Run with ``--trajectory PATH --output
DIR``; an existing complete trajectory makes the report independently replayable.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import html
import math
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path
from statistics import mean
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from tools.devtools.historical_extract import (
    COHORTS,
    DEFAULT_FIXTURES,
    FREIGHT_SERIES,
    canonical_bytes,
    load_fixtures,
    starting_specs,
)

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
NonnegativeInt = Annotated[int, Field(ge=0, strict=True)]


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExperimentIdentity(StrictRecord):
    profile: Literal["historical_employment", "historical_freight"]
    epoch: date
    horizon: Annotated[int, Field(gt=0, strict=True)]
    seed: Annotated[int, Field(ge=-(2**63), le=2**63 - 1, strict=True)]
    source_snapshot_sha256: Digest
    resolved_inputs_sha256: Digest


class EmploymentState(StrictRecord):
    series_id: str
    date: date
    jobs: NonnegativeInt
    period: NonnegativeInt
    world_hash: Digest


class FreightPeriod(StrictRecord):
    series_id: Literal["detroit_canada_truck_import_hs72"]
    period_start: date
    period_end_exclusive: date
    arrived_kg: NonnegativeInt
    period: Annotated[int, Field(gt=0, strict=True)]
    world_hash: Digest


class HistoricalTrajectory(StrictRecord):
    schema_version: Literal[1]
    experiment: ExperimentIdentity
    completed_periods: NonnegativeInt
    observed_choice_count: NonnegativeInt
    employment: tuple[EmploymentState, ...]
    freight: tuple[FreightPeriod, ...]

    @model_validator(mode="after")
    def complete_grid(self) -> HistoricalTrajectory:
        identity = self.experiment
        if self.completed_periods != identity.horizon:
            raise ValueError("incomplete execution: requested/completed periods differ")
        if identity.profile == "historical_employment":
            if identity.epoch != date(2010, 1, 1) or identity.horizon != 131 or self.freight:
                raise ValueError(
                    "employment requires its frozen epoch, horizon, and stock boundary"
                )
            keys = [(row.series_id, row.period) for row in self.employment]
            expected = {(series, period) for series in COHORTS for period in range(132)}
            if len(keys) != len(expected) or set(keys) != expected:
                raise ValueError(
                    "employment requires one initial and every committed state per cohort"
                )
            for row in self.employment:
                if row.date != identity.epoch + timedelta(days=28 * row.period):
                    raise ValueError("employment date differs from native 28-day committed period")
            period_hashes: dict[int, set[str]] = defaultdict(set)
            for row in self.employment:
                period_hashes[row.period].add(row.world_hash)
            if any(len(hashes) != 1 for hashes in period_hashes.values()):
                raise ValueError("employment cohort world hashes disagree for the same period")
        else:
            if identity.epoch != date(2019, 2, 1) or identity.horizon != 78 or self.employment:
                raise ValueError("freight requires its frozen epoch, horizon, and border boundary")
            freight_keys = [item.period for item in self.freight]
            if len(freight_keys) != 78 or set(freight_keys) != set(range(1, 79)):
                raise ValueError("freight requires every committed period exactly once")
            for item in self.freight:
                if item.period_start != identity.epoch + timedelta(
                    days=28 * (item.period - 1)
                ) or item.period_end_exclusive != item.period_start + timedelta(days=28):
                    raise ValueError("freight interval differs from native 28-day period")
        return self


def allocate_months(start: date, end_exclusive: date, kilograms: int) -> dict[str, Fraction]:
    """Allocate a period total uniformly per day, preserving rational mass exactly."""
    if end_exclusive <= start or kilograms < 0:
        raise ValueError("freight allocation requires positive interval and nonnegative mass")
    duration = (end_exclusive - start).days
    result: dict[str, Fraction] = {}
    current = start
    while current < end_exclusive:
        next_month = (
            date(current.year + 1, 1, 1)
            if current.month == 12
            else date(current.year, current.month + 1, 1)
        )
        overlap_end = min(end_exclusive, next_month)
        result[current.strftime("%Y-%m")] = Fraction(
            kilograms * (overlap_end - current).days, duration
        )
        current = overlap_end
    if sum(result.values(), Fraction()) != kilograms:
        raise ValueError("calendar allocation failed mass conservation")
    return result


def sample_stock(states: Sequence[tuple[date, int]], observed_date: date) -> tuple[int, date, int]:
    if (
        not states
        or list(states) != sorted(states)
        or len({row[0] for row in states}) != len(states)
    ):
        raise ValueError("stock states must have unique dates in ascending order")
    index = bisect.bisect_right([row[0] for row in states], observed_date) - 1
    if index < 0:
        raise ValueError("no committed stock state on or before observation date")
    selected_date, value = states[index]
    return value, selected_date, (observed_date - selected_date).days


def observation_window(kind: str, observed_date: date) -> str:
    if kind == "employment":
        if observed_date < date(2010, 1, 1):
            return "baseline_history"
        return "development" if observed_date < date(2015, 1, 1) else "evaluation"
    if kind == "freight":
        if observed_date < date(2019, 2, 1):
            return "initialization"
        return "development" if observed_date < date(2020, 1, 1) else "evaluation"
    raise ValueError("unknown historical observation kind")


def _correlation(left: Sequence[float], right: Sequence[float]) -> tuple[float | None, str | None]:
    if len(left) < 2:
        return None, "insufficient_pairs"
    a, b = mean(left), mean(right)
    dx, dy = [x - a for x in left], [y - b for y in right]
    xx, yy = math.fsum(x * x for x in dx), math.fsum(y * y for y in dy)
    if xx == 0 or yy == 0:
        return None, "constant_series"
    return max(
        -1.0, min(1.0, math.fsum(x * y for x, y in zip(dx, dy, strict=True)) / math.sqrt(xx * yy))
    ), None


def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        for index in order[start:end]:
            ranks[index] = (start + 1 + end) / 2
        start = end
    return ranks


def metric_values(
    observed: Sequence[float | int | None],
    predicted: Sequence[float | int | None],
    *,
    values_are_changes: bool = False,
) -> dict[str, Any]:
    if len(observed) != len(predicted):
        raise ValueError("metric arrays must have equal coverage")
    pairs = [
        (float(x), float(y))
        for x, y in zip(observed, predicted, strict=True)
        if x is not None and y is not None
    ]
    if any(not math.isfinite(value) for pair in pairs for value in pair):
        raise ValueError("metrics refuse nonfinite values")
    actual, model = [x for x, _ in pairs], [y for _, y in pairs]
    errors = [y - x for x, y in pairs]
    pearson, pearson_reason = _correlation(actual, model)
    spearman, spearman_reason = _correlation(_ranks(actual), _ranks(model))
    direction_pairs: list[tuple[float, float]] = []
    for before, after, before_model, after_model in zip(
        observed[:-1], observed[1:], predicted[:-1], predicted[1:], strict=True
    ):
        if (
            before is not None
            and after is not None
            and before_model is not None
            and after_model is not None
        ):
            direction_pairs.append((float(after - before), float(after_model - before_model)))
    if values_are_changes:
        direction_pairs = pairs

    def sign(value: float) -> int:
        return (value > 0) - (value < 0)

    return {
        "paired_count": len(pairs),
        "missing_count": len(observed) - len(pairs),
        "bias": mean(errors) if errors else None,
        "mae": mean([abs(x) for x in errors]) if errors else None,
        "rmse": math.sqrt(mean([x * x for x in errors])) if errors else None,
        "pearson": pearson,
        "pearson_reason": pearson_reason,
        "spearman": spearman,
        "spearman_reason": spearman_reason,
        "direction_agreement": mean([sign(a) == sign(b) for a, b in direction_pairs])
        if direction_pairs
        else None,
        "direction_pairs": len(direction_pairs),
    }


def _employment_alignment(
    trajectory: HistoricalTrajectory, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    aligned = []
    observed = {
        (f"{r['county_fips']}/{r['naics_code']}", r["year"], r["quarter"]): r["employment_begin"]
        if r["status_employment_begin"] == 1
        else None
        for r in rows
    }
    for series in COHORTS:
        states = sorted(
            (r for r in trajectory.employment if r.series_id == series), key=lambda r: r.period
        )
        stock = [(r.date, r.jobs) for r in states]
        expected_initial = observed[(series, 2010, 1)]
        if states[0].jobs != expected_initial:
            raise ValueError("employment initial jobs differ from pinned starting observation")
        for row in rows:
            if f"{row['county_fips']}/{row['naics_code']}" != series or row["year"] < 2010:
                continue
            day = date(row["year"], 3 * row["quarter"] - 2, 1)
            jobs, sampled, offset = sample_stock(stock, day)
            state = states[offset_index := (sampled - trajectory.experiment.epoch).days // 28]
            if state.period != offset_index:
                raise ValueError("committed stock sequence mismatch")
            aligned.append(
                {
                    "series_id": series,
                    "date": day.isoformat(),
                    "window": observation_window("employment", day),
                    "observed": observed[(series, row["year"], row["quarter"])],
                    "observed_status": row["status_employment_begin"],
                    "predicted": jobs,
                    "no_change": expected_initial,
                    "seasonal_persistence": observed.get((series, row["year"] - 1, row["quarter"])),
                    "sample_date": sampled.isoformat(),
                    "offset_days": offset,
                    "period": state.period,
                    "world_hash": state.world_hash,
                    "units": "jobs",
                }
            )
    return aligned


def _freight_alignment(
    trajectory: HistoricalTrajectory, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    observed: dict[str, int] = defaultdict(int)
    partitions: dict[str, int] = defaultdict(int)
    predicted: dict[str, Fraction] = defaultdict(Fraction)
    for row in rows:
        month = f"{row['year']:04d}-{row['month']:02d}"
        observed[month] += row["shipwt_kg"]
        partitions[month] += 1
    for period in trajectory.freight:
        for month, value in allocate_months(
            period.period_start, period.period_end_exclusive, period.arrived_kg
        ).items():
            predicted[month] += value
    if sum(predicted.values(), Fraction()) != sum(r.arrived_kg for r in trajectory.freight):
        raise ValueError("trajectory calendar allocation changed total arrival mass")
    aligned = []
    for month, kilograms in sorted(observed.items()):
        day = date.fromisoformat(month + "-01")
        if day < trajectory.experiment.epoch:
            continue
        mass = predicted[month]
        aligned.append(
            {
                "series_id": FREIGHT_SERIES,
                "date": day.isoformat(),
                "window": observation_window("freight", day),
                "observed": kilograms,
                "observed_status": "observed_import_weight",
                "source_partitions": partitions[month],
                "predicted": float(mass),
                "predicted_numerator": mass.numerator,
                "predicted_denominator": mass.denominator,
                "no_change": observed["2019-01"],
                "seasonal_persistence": observed.get(f"{day.year - 1:04d}-{day.month:02d}"),
                "units": "kilograms",
            }
        )
    return aligned


def _changes(values: Sequence[float | int | None]) -> list[float | int | None]:
    return [
        current - previous if current is not None and previous is not None else None
        for previous, current in zip(values[:-1], values[1:], strict=True)
    ]


def evaluate(
    trajectory: HistoricalTrajectory,
    manifest: dict[str, Any],
    employment: list[dict[str, Any]],
    freight: list[dict[str, Any]],
) -> dict[str, Any]:
    if trajectory.experiment.source_snapshot_sha256 != manifest["initialization_snapshot_sha256"]:
        raise ValueError("trajectory source snapshot differs from pinned observations")
    kind = "employment" if trajectory.experiment.profile == "historical_employment" else "freight"
    aligned = (
        _employment_alignment(trajectory, employment)
        if kind == "employment"
        else _freight_alignment(trajectory, freight)
    )
    metrics, annual = [], []
    for series in sorted({r["series_id"] for r in aligned}):
        series_rows = [r for r in aligned if r["series_id"] == series]
        base = series_rows[0]["no_change"]
        for window in ("development", "evaluation"):
            group = [r for r in series_rows if r["window"] == window]
            for estimator in ("predicted", "no_change", "seasonal_persistence"):
                actual = [r["observed"] for r in group]
                predictions = [r[estimator] for r in group]
                transforms = [
                    ("levels", actual, predictions),
                    ("changes", _changes(actual), _changes(predictions)),
                ]
                if kind == "employment":
                    transforms.append(
                        (
                            "base100",
                            [100 * x / base if x is not None and base else None for x in actual],
                            [
                                100 * x / base if x is not None and base else None
                                for x in predictions
                            ],
                        )
                    )
                for transform, left, right in transforms:
                    metrics.append(
                        {
                            "series_id": series,
                            "window": window,
                            "estimator": estimator,
                            "transform": transform,
                            "zero_base_reason": "zero_initial_jobs"
                            if transform == "base100" and not base
                            else None,
                            **metric_values(left, right, values_are_changes=transform == "changes"),
                        }
                    )
        for year in sorted({r["date"][:4] for r in series_rows}):
            group = [r for r in series_rows if r["date"].startswith(year)]
            actual = [r["observed"] for r in group if r["observed"] is not None]
            predicted = [r["predicted"] for r in group]
            aggregator = mean if kind == "employment" else sum
            annual.append(
                {
                    "series_id": series,
                    "year": int(year),
                    "statistic": "mean_quarter_beginning_jobs"
                    if kind == "employment"
                    else "sum_monthly_arrival_kg",
                    "observed": aggregator(actual) if len(actual) == len(group) else None,
                    "predicted": aggregator(predicted),
                    "observed_dates": len(actual),
                    "expected_dates": len(group),
                    "partial_year": len(group) != (4 if kind == "employment" else 12),
                }
            )
    return {
        "schema": "babylon.historical-evaluation.v1",
        "fit_status": "advisory",
        "evidence_status": "complete",
        "experiment": trajectory.experiment.model_dump(mode="json"),
        "observation_snapshot_sha256": manifest["snapshot_sha256"],
        "completed_periods": trajectory.completed_periods,
        "observed_choice_count": trajectory.observed_choice_count,
        "lag": 0,
        "coverage": {
            "series": len({r["series_id"] for r in aligned}),
            "distinct_dates": len({r["date"] for r in aligned}),
            "rows": len(aligned),
            "missing_observations": sum(r["observed"] is None for r in aligned),
        },
        "assumptions": [
            "Retrospective revised observations; not forecasts available at the time.",
            "Observed initial jobs are employment slots; QWI jobs need not represent unique people.",
            "Freight period mass is allocated uniformly by exact calendar-day overlap; fractions conserve mass.",
            "No-change holds the initial observed value; seasonal persistence uses only the same period one year earlier (rolling origin).",
            "Levels and changes are distinct comparisons; repeated ticks are not independent experiments.",
            "Future outcomes are evaluator-only. Designed productivity, reserves, inventories and transport are not observed facts.",
            "Missing growth, demand and pandemic mechanisms may produce poor fit; no outcome is injected to improve it.",
        ],
        "aligned": aligned,
        "metrics": metrics,
        "annual": annual,
    }


def _csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"missing required report rows: {path.name}")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _chart(path: Path, series: str, rows: list[dict[str, Any]]) -> None:
    values = [r[key] for r in rows for key in ("observed", "predicted") if r[key] is not None]
    maximum = max(values, default=1) or 1
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="340" viewBox="0 0 960 340">',
        '<rect width="960" height="340" fill="white"/>',
        f'<text x="50" y="26" font-family="sans-serif" font-size="18">{html.escape(series)} — {html.escape(rows[0]["units"])}</text>',
        '<path d="M60 50V290H920" fill="none" stroke="#333"/>',
    ]
    for key, color in (("observed", "#2166ac"), ("predicted", "#b2182b")):
        segments: list[str] = []
        for index, row in enumerate(rows):
            if row[key] is None:
                if segments:
                    lines.append(
                        f'<polyline points="{" ".join(segments)}" fill="none" stroke="{color}" stroke-width="2"/>'
                    )
                    segments = []
                continue
            segments.append(
                f"{60 + 860 * index / max(1, len(rows) - 1):.2f},{290 - 230 * row[key] / maximum:.2f}"
            )
        if segments:
            lines.append(
                f'<polyline points="{" ".join(segments)}" fill="none" stroke="{color}" stroke-width="2"/>'
            )
    lines.extend(
        [
            f'<text x="60" y="310" font-family="sans-serif">{rows[0]["date"]}</text>',
            f'<text x="810" y="310" font-family="sans-serif">{rows[-1]["date"]}</text>',
            '<text x="350" y="330" fill="#2166ac" font-family="sans-serif">Observed</text><text x="480" y="330" fill="#b2182b" font-family="sans-serif">Simulation</text>',
            f'<text x="4" y="65" font-family="sans-serif">{maximum:.0f}</text>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def write_report(result: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "evaluation.json").write_bytes(canonical_bytes(result))
    for key in ("aligned", "metrics", "annual"):
        _csv(output / f"{key}.csv", result[key])
    lines = [
        f"# Historical comparison: {result['experiment']['profile']}",
        "",
        f"Execution complete: {result['completed_periods']} periods. Empirical fit is **advisory**.",
        "",
        f"Initialization snapshot: `{result['experiment']['source_snapshot_sha256']}`",
        f"Observation snapshot (evaluation only): `{result['observation_snapshot_sha256']}`",
        "",
        f"Coverage: {result['coverage']['series']} series, {result['coverage']['distinct_dates']} distinct dates; {result['coverage']['missing_observations']} missing observations.",
        "",
        "| Series | Window | MAE | RMSE | Pearson | Direction agreement |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in result["metrics"]:
        if row["estimator"] == "predicted" and row["transform"] == "levels":
            values = [
                f"{row[k]:.4g}"
                if row[k] is not None
                else f"unavailable ({row.get(k + '_reason') or 'insufficient pairs'})"
                for k in ("mae", "rmse", "pearson", "direction_agreement")
            ]
            lines.append(f"| {row['series_id']} | {row['window']} | " + " | ".join(values) + " |")
    lines += ["", "## Interpretation", ""] + [f"- {text}" for text in result["assumptions"]]
    lines += [
        "",
        "Complete levels, changes, base-100 indices, and no-change/seasonal benchmarks are in `metrics.csv`; calendar offsets and exact freight fractions are in `aligned.csv`.",
        "",
    ]
    for series in sorted({r["series_id"] for r in result["aligned"]}):
        filename = series.replace("/", "_") + ".svg"
        _chart(
            output / filename, series, [r for r in result["aligned"] if r["series_id"] == series]
        )
        lines += [f"![{series}]({filename})", ""]
    (output / "summary.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trajectory", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        manifest, employment, freight = load_fixtures(args.fixtures)
        trajectory = HistoricalTrajectory.model_validate_json(args.trajectory.read_bytes())
        from tools.devtools.historical_evidence import validate_capture

        kind = (
            "employment" if trajectory.experiment.profile == "historical_employment" else "freight"
        )
        spec = starting_specs(employment, freight, manifest["initialization_snapshot_sha256"])[kind]
        validate_capture(
            args.trajectory.parent,
            trajectory,
            spec,
            require_postgres=(args.trajectory.parent / "parity.json").exists(),
        )
        write_report(evaluate(trajectory, manifest, employment, freight), args.output)
    except (ValueError, OSError, KeyError) as error:
        (args.output / "summary.md").write_text(
            f"# Historical comparison failed\n\nRequired evidence failed: {error}\n"
        )
        print(f"historical comparison failed: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
