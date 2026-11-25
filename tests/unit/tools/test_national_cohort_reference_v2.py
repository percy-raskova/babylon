"""The twelve-trade cohort table keeps version 1's columns and groups only county leaf cells."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import make_national_cohort_reference as cohort  # type: ignore[import-not-found]  # noqa: E402
import make_national_cohort_reference_v2 as builder  # type: ignore[import-not-found]  # noqa: E402
import make_national_qcew_function_basis as basis  # type: ignore[import-not-found]  # noqa: E402
import make_national_qcew_function_basis_v2 as v2  # type: ignore[import-not-found]  # noqa: E402


def source_row(
    code: str,
    *,
    role: str = "county_leaf",
    area: str = "26163",
    establishments: int = 4,
    jobs: int | None = 10,
    payroll: int | None = 1000,
    disclosure: str = "",
) -> v2.SourceRow:
    return v2.SourceRow(
        row_role=role,
        area_fips=area,
        ownership_code="5",
        naics_code=code,
        agglvl_code=basis.aggregation_level(code),
        disclosure_code=disclosure,
        annual_avg_establishments=establishments,
        annual_avg_jobs=jobs,
        annual_payroll_usd=payroll,
        mean_weekly_wage_usd=None if jobs is None else 0,
    )


def test_the_car_plants_and_the_machines_are_separate_groups() -> None:
    mapping = v2.load_mapping_v2()
    rows = builder.county_observations(
        (
            source_row("3361"),
            source_row("333", establishments=2, jobs=5, payroll=700),
        )
    )
    groups = builder.capture_cohorts_v2(rows, {"26163"}, mapping)
    assert [(g.function_id, g.admitted) for g in groups] == [
        ("capital_goods", True),
        ("consumer_goods", True),
    ]
    assert [g.jobs.complete_total for g in groups] == [5, 10]


def test_only_county_leaves_become_members() -> None:
    rows = (
        source_row("336", role="county_parent"),
        source_row("3361", role="state_leaf", area="26000"),
        source_row("3361", role="nation_leaf", area="US000"),
    )
    assert list(builder.county_observations(rows)) == []


def test_restaurants_join_leisure() -> None:
    mapping = v2.load_mapping_v2()
    rows = builder.county_observations((source_row("72"), source_row("71")))
    (group,) = builder.capture_cohorts_v2(rows, {"26163"}, mapping)
    assert group.function_id == "leisure_hospitality"
    assert re.fullmatch(r"71~P[^;]*;72~P[^;]*", cohort.fields(group)[-1])


def test_the_committed_v2_cohorts() -> None:
    mapping = v2.load_mapping_v2()
    path, meta_path = builder.ARTIFACT_OUT, builder.METADATA_OUT
    assert path.stat().st_size < 2_097_152
    raw = gzip.decompress(path.read_bytes())
    assert len(raw) < 8_388_608
    with gzip.open(path, "rt", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = list(reader)
    with gzip.open(cohort.ARTIFACT_OUT, "rt", newline="") as stream:
        assert header == next(csv.reader(stream))
    assert tuple(header) == cohort.COLUMNS
    assert {r[1] for r in rows if r[1]} == set(v2.FUNCTION_IDS_V2)
    members = 0
    for row in rows:
        assert int(row[4]) <= 13
        parts = row[11].split(";")
        assert len(parts) == int(row[4])
        members += len(parts)
        for member in parts:
            assert member.split("~")[0] in mapping.source_codes
    assert members == 151_199
    (wayne,) = [r for r in rows if r[:3] == ["26163", "consumer_goods", "5"]]
    assert 53_000 <= int(wayne[7]) < 54_000

    metadata = json.loads(meta_path.read_text())
    assert metadata["contract"] == "NationalCohortReference2024V2"
    assert metadata["issue"] == "PER-371"
    assert metadata["native_readers"] == []
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert metadata["artifact"]["sha256"] == digest
    assert metadata["artifact"]["rows"] == len(rows)
    assert metadata["artifact"]["bytes"] == path.stat().st_size
    assert metadata["artifact"]["decoded_bytes"] == len(raw)
    coverage = metadata["coverage"]
    assert coverage["source_members"] == members
    assert coverage["mapped_groups"] == sum(1 for r in rows if r[1])
    assert coverage["admitted_groups"] == sum(1 for r in rows if r[3] == "1")
    assert coverage["unclassified_groups"] == sum(1 for r in rows if not r[1])
    assert coverage["known_totals"] == {
        "establishments": sum(int(r[5] or 0) for r in rows),
        "jobs": sum(int(r[7] or 0) for r in rows),
        "payroll": sum(int(r[9] or 0) for r in rows),
    }
    assert (
        metadata["sources"]["leaf_basis"]["sha256"]
        == hashlib.sha256(v2.ARTIFACT_OUT.read_bytes()).hexdigest()
    )
    assert (
        metadata["sources"]["function_mapping"]["sha256"]
        == hashlib.sha256(v2.MAPPING_V2_PATH.read_bytes()).hexdigest()
    )

    registry = yaml.safe_load((ROOT / "data-artifacts.yaml").read_text())
    (entry,) = [
        e for e in registry["artifacts"] if e["name"] == "national_cohort_reference_v2_2024"
    ]
    assert entry["sha256"] == digest
    assert entry["rows"] == len(rows)
