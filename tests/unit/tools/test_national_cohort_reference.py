"""Sparse source admission cannot create workers or treat suppressed jobs as zero."""

from __future__ import annotations

import csv
import gzip
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import make_national_cohort_reference as builder  # type: ignore[import-not-found]  # noqa: E402


def observation(
    naics: str = "311",
    *,
    establishments: int = 0,
    jobs: int | None = 1,
    payroll: int | None = 2000,
    wage: int | None = 40,
    disclosure: str = "",
) -> dict[str, object]:
    return {
        "county_geoid": "01017",
        "ownership_code": "5",
        "naics_code": naics,
        "agglvl_code": builder.basis.aggregation_level(naics),
        "disclosure_code": disclosure,
        "annual_avg_establishments": establishments,
        "annual_avg_jobs": jobs,
        "annual_payroll_usd": payroll,
        "mean_weekly_wage_usd": wage,
    }


def test_rounded_zero_establishments_with_positive_jobs_or_payroll_remain_admitted() -> None:
    rows = (observation(), observation("111", jobs=0, payroll=7))
    (group,) = builder.capture(rows, {"01017"})
    assert group.admitted
    assert group.establishments.known_subtotal == 0
    assert group.jobs.complete_total == 1
    assert group.payroll.complete_total == 2007
    assert len(group.members) == 2


def test_suppression_preserves_establishments_and_field_completeness() -> None:
    rows = (
        observation(establishments=2),
        observation("111", establishments=5, jobs=None, payroll=None, wage=None, disclosure="N"),
    )
    (group,) = builder.capture(rows, {"01017"})
    assert group.admitted
    assert group.establishments.complete_total == 7
    assert group.jobs.known_subtotal == 1 and group.jobs.complete_total is None
    assert group.payroll.known_subtotal == 2000 and group.payroll.complete_total is None
    assert group.members[1].mean_weekly_wage_usd == 40


def test_zero_and_unclassified_groups_remain_evidence_without_admission() -> None:
    rows = (observation(jobs=0, payroll=0, wage=0), observation("99", establishments=1, jobs=2))
    groups = builder.capture(rows, {"01017", "15005"})
    assert len(groups) == 2
    assert not any(group.admitted for group in groups)
    assert groups[0].function_id is None
    assert all(group.county_geoid == "01017" for group in groups)


def test_duplicate_unknown_county_and_contradictory_suppression_refused() -> None:
    row = observation()
    with pytest.raises(builder.ReferenceBuildError, match="duplicate"):
        builder.capture((row, row), {"01017"})
    with pytest.raises(builder.ReferenceBuildError, match="county"):
        builder.capture((row,), {"15005"})
    with pytest.raises(builder.ReferenceBuildError, match="suppression"):
        builder.capture((observation(disclosure="N"),), {"01017"})


def test_committed_capture_keeps_every_source_member_once_and_exact_admission() -> None:
    with gzip.open(builder.ARTIFACT_OUT, "rt", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 59058
    assert sum(row["admitted"] == "1" for row in rows) == 57238
    assert sum(row["function_id"] != "" for row in rows) == 57347
    assert len({row["county_geoid"] for row in rows}) == 3143
    assert not any(row["county_geoid"] == "15005" for row in rows)
    keys = [(row["county_geoid"], row["function_id"], row["ownership_code"]) for row in rows]
    assert keys == sorted(set(keys))
    members = [
        (row["county_geoid"], row["ownership_code"], part.split("~")[0])
        for row in rows
        for part in row["members"].split(";")
    ]
    assert len(members) == len(set(members)) == 144881
    metadata = json.loads(builder.METADATA_OUT.read_text())
    assert metadata["native_readers"] == ["babylon-persistence::national_cohorts"]
    assert metadata["runtime_consumers"] == []


def test_unknown_activity_is_not_sufficient_for_executable_admission() -> None:
    (group,) = builder.capture(
        (observation(jobs=None, payroll=None, wage=None, disclosure="N"),), {"01017"}
    )
    assert not group.admitted
    assert group.establishments.complete_total == 0
    assert group.jobs.complete_total is None
    assert group.jobs.known_subtotal == 0


def test_checked_subtotals_refuse_overflow_and_noninteger_source_values() -> None:
    with pytest.raises(builder.ReferenceBuildError, match="source_integer"):
        builder.subtotal((builder.MAX_I64, 1))
    for value in (-1, True, 1.0):
        with pytest.raises(builder.ReferenceBuildError, match="source_integer"):
            builder.source_integer(value)


def test_compact_member_quantities_equal_the_pinned_leaf_basis() -> None:
    import pyarrow.parquet as pq

    expected = {
        (raw["county_geoid"], raw["ownership_code"], raw["naics_code"]): (
            raw["disclosure_code"],
            raw["annual_avg_establishments"],
            raw["annual_avg_jobs"],
            raw["annual_payroll_usd"],
            raw["mean_weekly_wage_usd"],
        )
        for raw in pq.read_table(builder.basis.ARTIFACT_OUT).to_pylist()
    }
    with gzip.open(builder.ARTIFACT_OUT, "rt", newline="") as stream:
        for row in csv.DictReader(stream):
            for member in row["members"].split(";"):
                code, disclosure, establishments, jobs, payroll, wage = member.split("~")
                assert disclosure in {"P", "N"}
                actual = (
                    "" if disclosure == "P" else "N",
                    int(establishments),
                    *(None if value == "" else int(value) for value in (jobs, payroll, wage)),
                )
                assert expected.pop((row["county_geoid"], row["ownership_code"], code)) == actual
    assert expected == {}
