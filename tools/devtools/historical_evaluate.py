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
from tools.devtools.historical_direction import directional_metrics
from tools.devtools.historical_extract import (
    COHORTS,
    DEFAULT_FIXTURES,
    FREIGHT_SERIES,
    canonical_bytes,
    load_fixtures,
    starting_specs,
)
from tools.devtools.historical_warning_bands import load_warning_policy, warning_assessments

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


def _benchmark_coverage(
    trajectory: HistoricalTrajectory, verified_setup: dict[str, Any]
) -> dict[str, Any]:
    """Describe these admitted profiles, without assigning causes to empirical errors.

    Scope follows simulation_experiment::{regional,freight} and the closed
    intervention validator. Merchant/final-demand and maintenance execution
    exists in material-circuit; these profiles do not connect those mechanisms.
    """
    wiring = verified_setup["wiring"]
    employment = trajectory.experiment.profile == "historical_employment"
    unconnected = [
        "merchant handling",
        "final-demand fulfillment",
        "maintenance",
    ]
    evidence = {"governed_choice_receipts": trajectory.observed_choice_count}
    if employment:
        relationships = (
            "Five regional recipes connect production plans, input inventories, finite supplier "
            "orders, capacity-limited freight, transit arrivals and staffing. Observed beginning "
            "jobs initialize employed slots; the closed workforce pools redistribute employed "
            "and reserve slots."
        )
        omissions = (
            "Not represented in this profile: workforce entry, firm entry/exit, investment, "
            "productivity growth or a changing historical demand process. Each county/industry "
            "group is represented by one recipe and starts with zero reserve. The engine-wide "
            "status of these broader systems is not established by this report."
        )
        evidence["employment_series_with_changes"] = sum(
            len({row.jobs for row in trajectory.employment if row.series_id == series}) > 1
            for series in COHORTS
        )
        trajectory_note = (
            f"{evidence['employment_series_with_changes']} of {len(COHORTS)} employment series "
            "change during this captured trajectory. This describes outcomes, not their causes."
        )
    else:
        relationships = (
            "A finite Canadian HS72 inventory and import order connect a capacity-limited truck "
            "route, one-period transit and arrivals at Detroit port entry; mass includes transit. "
            "January 2019 fixes the opening scale. Calendar-month allocation is a reporting "
            "assumption, not a seasonal demand mechanism."
        )
        omissions = (
            "No production or employment is connected to this profile. A changing monthly demand "
            "process, order replenishment, pandemic or trade-policy events are not represented "
            "here. HS72 is one portwide aggregate, without county destinations or bridge attribution. "
            "The engine-wide status of broader historical drivers is not established by this report."
        )
        unconnected = ["production recipes", "staffing", *unconnected]
        evidence["arrival_active_periods"] = sum(row.arrived_kg > 0 for row in trajectory.freight)
        trajectory_note = (
            f"{evidence['arrival_active_periods']} of {trajectory.completed_periods} modeled "
            "periods record arrivals at the declared border endpoint."
        )
    return {
        "profile": trajectory.experiment.profile,
        "captured_wiring": wiring,
        "modeled_relationships": relationships,
        "bsl_execution": (
            "The captured material/period BSL rule declares a Designed mechanic and invokes "
            "native material-cycle through normal tick execution. Rust owns the material "
            "transition and subsequent staffing/planning. Its after-metabolism anchor is a "
            "schedule position; it does not execute the separate metabolism BSL pack. "
            "The ported production, metabolism and lifecycle packs are not selected here. "
            "They are not drop-in material mechanisms: ADR261 explicitly preserves this "
            "composition instead of bulk-loading unrelated historical graph economics. "
            + (
                "This profile uses production staffing."
                if employment
                else "This inventory-only profile selects no staffing composition and refuses production, merchant and maintenance labor."
            )
        ),
        "existing_engine_not_connected": unconnected,
        "current_planning_boundary": (
            "Production plans use physical inputs, capacity and labor, without a sales or "
            "unsold-stock response. Closed workforce pools cannot exceed their initial total. "
            "Connecting final demand alone would not supply those missing causal links."
            if employment
            else "Finite orders and fixed transport capacity do not implement changing demand."
        ),
        "known_omissions": omissions
        + " Do not stretch existing parameters to substitute for missing integration or systems.",
        "admitted_controls": ["transport_capacity_permille: 250–2000"],
        "tuning_status": "historical_response_not_yet_qualified",
        "tuning_readiness": (
            "Admitted does not yet mean tunable for historical fit. Transport capacity is the "
            "only admitted numeric intervention for this profile; delivery and opening-stock "
            "interventions are unavailable. Starting observations remain fixed evidence. "
            "A controlled historical sensitivity run must show a reproducible response in the "
            "scored series before calling this input demonstrably tunable. The separate "
            "16-period delivery/stock comparison does not establish that response here. Review "
            "system coverage and interactions before optimization; use development outcomes only."
        ),
        "unexplained_mismatches": (
            "Remaining level, change and direction errors are unexplained until supported by "
            "receipt traces and controlled comparisons. Known omissions are not a causal "
            "attribution for a particular series' residuals."
        ),
        "trajectory_evidence": evidence,
        "trajectory_note": trajectory_note
        + f" Captured governed choice receipts: {trajectory.observed_choice_count}; a seed alone does not justify sampled ensembles.",
    }


def evaluate(
    trajectory: HistoricalTrajectory,
    manifest: dict[str, Any],
    employment: list[dict[str, Any]],
    freight: list[dict[str, Any]],
    *,
    verified_setup: dict[str, Any],
) -> dict[str, Any]:
    kind = "employment" if trajectory.experiment.profile == "historical_employment" else "freight"
    if (
        trajectory.experiment.source_snapshot_sha256
        != manifest["initialization_snapshot_sha256"][kind]
    ):
        raise ValueError(
            "trajectory source snapshot differs from its profile's pinned observations"
        )
    aligned = (
        _employment_alignment(trajectory, employment)
        if kind == "employment"
        else _freight_alignment(trajectory, freight)
    )
    warning_policy = load_warning_policy()
    warnings = warning_assessments(aligned, kind, warning_policy)
    rates = directional_metrics(aligned, kind)
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
        "benchmark_coverage": _benchmark_coverage(trajectory, verified_setup),
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
            "Profile coverage gaps and unexplained mismatches are reported separately; no outcome is injected to improve fit.",
        ],
        "aligned": aligned,
        "metrics": metrics,
        "warning_policy": warning_policy.model_dump(mode="json", by_alias=True),
        "warning_assessments": warnings,
        "directional_metrics": rates,
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


def _number(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.6g}"


def _warning_summary(result: dict[str, Any]) -> list[str]:
    policy = result["warning_policy"]
    warnings = result["warning_assessments"]
    candidate = [row for row in warnings if row["estimator"] == "predicted"]
    lines = [
        "",
        "## Provisional level warning bands",
        "",
        f"**{sum(row['status'] == 'warning' for row in candidate)} of {len(candidate)} simulation series/window comparisons warn.** Designed policy v{policy['version']}, approved by the Director on {policy['approved_on']}. Warnings are advisory and do not relax execution or evidence checks.",
        "",
        "MAE warns only above 10%, and absolute signed bias only above 5%, of each series' frozen observed development mean. Equality does not warn. These are Designed diagnostic targets, not empirical confidence intervals or accepted fit. Missing, suppressed, zero or changed development bases require explicit review; held-out outcomes never reset these bands.",
        "",
        "| Series | Window | Estimator | Unit | Frozen mean | MAE ceiling | Current MAE | Absolute bias ceiling | Current signed bias | Status / breaches |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in warnings:
        values = [
            _number(row[key])
            for key in (
                "development_scale",
                "mae_warning_above",
                "mae",
                "absolute_bias_warning_above",
                "bias",
            )
        ]
        status = row["status"] + (": " + ", ".join(row["breaches"]) if row["breaches"] else "")
        if row["missing_count"]:
            status += f"; {row['missing_count']} missing pairs"
        lines.append(
            f"| {row['series_id']} | {row['window']} | {row['estimator']} | {row['units']} | "
            + " | ".join(values)
            + f" | {status} |"
        )
    return lines


def _directional_summary(result: dict[str, Any]) -> list[str]:
    lines = [
        "",
        "## Discrete first and second rates",
        "",
        "Employment uses jobs at observed civil dates. Freight uses monthly kilograms divided by actual days in that month, placed at the calendar-month midpoint. Baselines retain their reported monthly masses before this day normalization. First rates divide adjacent differences by elapsed days and sit at interval midpoints; second rates divide adjacent first-rate differences by their midpoint distance. Each development/evaluation window stands alone: no boundary or missing-value bridging, smoothing, fitting, lag selection, or deadband. Exact rational zeros are reported separately. These are descriptive discrete estimates, with no derivative warning bands or jerk qualification. Direction agreement alone cannot establish magnitude accuracy.",
    ]
    for order, label in ((1, "First rate"), (2, "Second rate")):
        lines += [
            "",
            f"### {label}",
            "",
            "| Series | Window | Estimator | Units | Pairs / missing | Sign agreement | Nonzero agreement / pairs | Zeros observed / predicted / both | MAE | RMSE |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
        for row in result["directional_metrics"]:
            if row["order"] == order:
                lines.append(
                    f"| {row['series_id']} | {row['window']} | {row['estimator']} | {row['units']} | {row['paired_count']} / {row['missing_count']} | {_number(row['sign_agreement'])} | {_number(row['nonzero_sign_agreement'])} / {row['nonzero_pairs']} | {row['observed_zero_count']} / {row['predicted_zero_count']} / {row['both_zero_count']} | {_number(row['mae'])} | {_number(row['rmse'])} |"
                )
    return lines


def _wiring_summary(wiring: dict[str, Any]) -> list[str]:
    lines = [
        "",
        "### Verified captured wiring",
        "",
        "Selection comes from the captured rule and material inventories. The BSL family roster describes governed selection, not a claim that every family is fully implemented. Native compositions are not additional BSL invocations.",
        "",
        "| Captured rule / native composition | Kind | Role | Evidence | Effects |",
        "|---|---|---|---|---|",
    ]
    for key, kind in (("rules", "BSL rule"), ("native_compositions", "native composition")):
        for rule in wiring[key]:
            lines.append(
                f"| {rule['rule_id']} | {kind} | {rule['role']} | {rule['evidence']} | {', '.join(rule['effects'])} |"
            )
    lines += ["", "| Material family | Selected | Captured rows |", "|---|---|---:|"]
    for family in wiring["material_families"]:
        lines.append(f"| {family['family']} | {family['selected']} | {family['captured_rows']} |")
    lines += ["", "| BSL family | Selected | Captured rule IDs |", "|---|---|---|"]
    for family in wiring["bsl_families"]:
        lines.append(
            f"| {family['family']} | {family['selected']} | {', '.join(family['rule_ids']) or 'none'} |"
        )
    lines += [
        "",
        "Captured staffing subjects: " + (", ".join(wiring["staffing_subjects"]) or "none") + ".",
    ]
    return lines


def write_report(result: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "evaluation.json").write_bytes(canonical_bytes(result))
    for key in ("aligned", "metrics", "annual", "warning_assessments", "directional_metrics"):
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
    lines += _warning_summary(result)
    lines += _directional_summary(result)
    coverage = result["benchmark_coverage"]
    lines += [
        "",
        "## Benchmark coverage and tuning readiness",
        "",
        "Historically dated profiles are development benchmarks alongside playable scenarios. Review system coverage and interactions before optimization. Empirical misses remain advisory; engineering integrity remains required.",
        "",
        f"- **Modeled relationships:** {coverage['modeled_relationships']}",
        f"- **BSL execution:** {coverage['bsl_execution']}",
        "- **Existing engine mechanisms not connected here:** "
        + ", ".join(coverage["existing_engine_not_connected"])
        + ". These bounded profiles omit them; their presence elsewhere does not establish a connection here.",
        f"- **Current planning boundary:** {coverage['current_planning_boundary']}",
        f"- **Known omissions:** {coverage['known_omissions']}",
        "- **Admitted controls:** " + "; ".join(coverage["admitted_controls"]) + ".",
        f"- **Tuning readiness:** {coverage['tuning_readiness']}",
        f"- **Unexplained mismatches:** {coverage['unexplained_mismatches']}",
        f"- **Observed trajectory:** {coverage['trajectory_note']}",
    ]
    lines += _wiring_summary(coverage["captured_wiring"])
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
        setup = validate_capture(
            args.trajectory.parent,
            trajectory,
            spec,
            require_postgres=(args.trajectory.parent / "parity.json").exists(),
        )
        write_report(
            evaluate(trajectory, manifest, employment, freight, verified_setup=setup), args.output
        )
    except (ValueError, OSError, KeyError) as error:
        (args.output / "summary.md").write_text(
            f"# Historical comparison failed\n\nRequired evidence failed: {error}\n"
        )
        print(f"historical comparison failed: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
