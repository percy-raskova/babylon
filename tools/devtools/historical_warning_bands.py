"""Frozen Designed historical warning bands; integrity errors remain failures."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from fractions import Fraction
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from tools.devtools.historical_extract import COHORTS, FREIGHT_SERIES, canonical_bytes

POLICY_PATH = Path(__file__).resolve().parents[2] / "tests/baselines/historical_warning_bands.json"
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
PositiveInt = Annotated[int, Field(strict=True, gt=0)]


class SeriesWarningBand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    profile: Literal["employment", "freight"]
    series_id: str
    units: Literal["jobs", "kilograms"]
    development_start: date
    development_end: date
    observation_count: PositiveInt
    observed_sum: PositiveInt
    development_rows_sha256: Digest

    @property
    def scale(self) -> Fraction:
        return Fraction(self.observed_sum, self.observation_count)


class HistoricalWarningPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_id: Literal["HistoricalWarningBandsV1"] = Field(alias="schema")
    version: Annotated[int, Field(strict=True, ge=1, le=1)]
    status: Literal["provisional"]
    evidence_class: Literal["Designed"]
    approved_on: Literal["2026-09-19"]
    approved_by: Literal["Director"]
    source_observation_snapshot_sha256: Digest
    mae_fraction: Literal["1/10"]
    absolute_bias_fraction: Literal["1/20"]
    comparison: Literal["strictly_greater_than"]
    series: tuple[SeriesWarningBand, ...]

    @model_validator(mode="after")
    def admitted_series(self) -> HistoricalWarningPolicy:
        expected = {("employment", series) for series in COHORTS} | {("freight", FREIGHT_SERIES)}
        if len(self.series) != 6 or {(r.profile, r.series_id) for r in self.series} != expected:
            raise ValueError("warning policy must pin exactly the six admitted historical series")
        for band in self.series:
            expected_window = (
                (date(2010, 1, 1), date(2014, 10, 1), 20, "jobs")
                if band.profile == "employment"
                else (date(2019, 2, 1), date(2019, 12, 1), 11, "kilograms")
            )
            if (
                band.development_start,
                band.development_end,
                band.observation_count,
                band.units,
            ) != expected_window:
                raise ValueError("warning policy changed its frozen development window or units")
        return self


def load_warning_policy(path: Path = POLICY_PATH) -> HistoricalWarningPolicy:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate warning policy field: {key}")
            result[key] = value
        return result

    return HistoricalWarningPolicy.model_validate(
        json.loads(path.read_bytes(), object_pairs_hook=unique)
    )


def development_fingerprint(rows: list[dict[str, Any]]) -> str:
    selected = [
        {key: row[key] for key in ("date", "observed", "observed_status")}
        for row in sorted(rows, key=lambda row: row["date"])
    ]
    return hashlib.sha256(canonical_bytes(selected)).hexdigest()


def validate_development(band: SeriesWarningBand, rows: list[dict[str, Any]]) -> None:
    expected_status: int | str = 1 if band.profile == "employment" else "observed_import_weight"
    if len(rows) != band.observation_count or any(
        type(row["observed"]) is not int
        or row["observed"] < 0
        or row["observed_status"] != expected_status
        for row in rows
    ):
        raise ValueError(
            f"{band.series_id}: warning scale requires complete unsuppressed development observations"
        )
    total = sum(row["observed"] for row in rows)
    if total <= 0:
        raise ValueError(
            f"{band.series_id}: zero development scale cannot define relative warning bands"
        )
    if total != band.observed_sum or development_fingerprint(rows) != band.development_rows_sha256:
        raise ValueError(
            f"{band.series_id}: development observations changed; governed warning bands require explicit review, not automatic reset"
        )


def assess_errors(errors: list[Fraction], scale: Fraction) -> dict[str, Any]:
    if scale <= 0:
        raise ValueError("warning scale must be positive")
    mae_ceiling, bias_ceiling = scale / 10, scale / 20
    mae = sum(map(abs, errors), Fraction()) / len(errors) if errors else None
    bias = sum(errors, Fraction()) / len(errors) if errors else None
    breaches = []
    if mae is not None and mae > mae_ceiling:
        breaches.append("mae")
    if bias is not None and abs(bias) > bias_ceiling:
        breaches.append("absolute_bias")
    return {
        "mae": float(mae) if mae is not None else None,
        "bias": float(bias) if bias is not None else None,
        "mae_warning_above": float(mae_ceiling),
        "absolute_bias_warning_above": float(bias_ceiling),
        "status": "unavailable" if not errors else "warning" if breaches else "within_band",
        "breaches": breaches,
        "paired_count": len(errors),
    }


def warning_assessments(
    aligned: list[dict[str, Any]], kind: str, policy: HistoricalWarningPolicy
) -> list[dict[str, Any]]:
    bands = [band for band in policy.series if band.profile == kind]
    if {row["series_id"] for row in aligned} != {band.series_id for band in bands}:
        raise ValueError("historical warning series differ from the frozen policy")
    assessments = []
    for band in bands:
        selected = [row for row in aligned if row["series_id"] == band.series_id]
        validate_development(band, [row for row in selected if row["window"] == "development"])
        for window in ("development", "evaluation"):
            rows = [row for row in selected if row["window"] == window]
            for estimator in ("predicted", "no_change", "seasonal_persistence"):
                errors = []
                for row in rows:
                    if row["observed"] is None or row[estimator] is None:
                        continue
                    predicted = (
                        Fraction(row["predicted_numerator"], row["predicted_denominator"])
                        if kind == "freight" and estimator == "predicted"
                        else Fraction(row[estimator])
                    )
                    errors.append(predicted - Fraction(row["observed"]))
                assessments.append(
                    {
                        "series_id": band.series_id,
                        "window": window,
                        "estimator": estimator,
                        "units": band.units,
                        "development_scale": float(band.scale),
                        "missing_count": len(rows) - len(errors),
                        **assess_errors(errors, band.scale),
                    }
                )
    return assessments
