"""Rule O2: withheld jobs are placed under their published parents; each group gets a wage."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import make_national_cohort_reference_v2 as cohort_v2  # type: ignore[import-not-found]  # noqa: E402
import make_national_county_reference as county  # type: ignore[import-not-found]  # noqa: E402
import make_national_qcew_function_basis_v2 as v2  # type: ignore[import-not-found]  # noqa: E402
import make_national_trade_pay as pay  # type: ignore[import-not-found]  # noqa: E402

COUNTY = "26163"


def row(
    code: str,
    role: str = "county_leaf",
    *,
    area: str = COUNTY,
    own: str = "5",
    est: int = 1,
    jobs: int | None = None,
    payroll: int | None = None,
    withheld: bool = False,
) -> v2.SourceRow:
    if withheld:
        jobs = payroll = None
    return v2.SourceRow(
        row_role=role,
        area_fips=area,
        ownership_code=own,
        naics_code=code,
        agglvl_code=v2.role_level(code, role),
        disclosure_code="N" if withheld else "",
        annual_avg_establishments=est,
        annual_avg_jobs=jobs,
        annual_payroll_usd=payroll,
        mean_weekly_wage_usd=None if withheld else 0,
    )


def leaf(code: str, **kw: object) -> v2.SourceRow:
    return row(code, "county_leaf", **kw)  # type: ignore[arg-type]


def parent(code: str, **kw: object) -> v2.SourceRow:
    return row(code, "county_parent", **kw)  # type: ignore[arg-type]


def state(code: str, **kw: object) -> v2.SourceRow:
    kw.setdefault("area", "26000")
    return row(code, "state_leaf", **kw)  # type: ignore[arg-type]


def nation(code: str, **kw: object) -> v2.SourceRow:
    kw.setdefault("area", "US000")
    return row(code, "nation_leaf", **kw)  # type: ignore[arg-type]


def placed(leaves: list[v2.SourceRow], parents: list[v2.SourceRow]) -> dict[str, tuple[int, int]]:
    return pay.place_withheld(leaves, {p.naics_code: p for p in parents})


def test_withheld_plants_share_the_published_parent() -> None:
    leaves = [
        leaf("3361", est=10, withheld=True),
        leaf("3362", est=30, withheld=True),
        leaf("3363", est=60, jobs=20_000, payroll=1_800_000_000),
    ]
    parents = [parent("336", est=100, jobs=60_000, payroll=6_000_000_000)]
    assert placed(leaves, parents) == {
        "3361": (10_000, 1_050_000_000),
        "3362": (30_000, 3_150_000_000),
    }
    mapping = v2.load_mapping_v2()
    (group,) = [
        g for g in pay.pay_rows([*leaves, *parents], mapping) if g.function_id == "consumer_goods"
    ]
    assert (group.jobs, group.payroll_usd) == (60_000, 6_000_000_000)
    assert (group.jobs_rule, group.wage_rule) == ("placed", "county")
    assert (group.wage_jobs, group.wage_payroll_usd) == (60_000, 6_000_000_000)


def test_a_withheld_parent_passes_to_the_sector() -> None:
    leaves = [
        leaf("333", jobs=300, payroll=30_000),
        leaf("3363", jobs=200, payroll=20_000),
        leaf("3361", est=1, withheld=True),
        leaf("3362", est=3, withheld=True),
    ]
    parents = [
        parent("336", withheld=True),
        parent("31-33", est=50, jobs=1_000, payroll=100_000),
    ]
    assert placed(leaves, parents) == {"3361": (125, 12_500), "3362": (375, 37_500)}


def test_a_parent_below_its_children_places_zero() -> None:
    leaves = [leaf("3363", jobs=101, payroll=10_100), leaf("3361", withheld=True)]
    parents = [parent("336", jobs=100, payroll=10_000)]
    assert placed(leaves, parents) == {"3361": (0, 0)}
    mapping = v2.load_mapping_v2()
    (group,) = pay.pay_rows([*leaves, *parents], mapping)
    assert (group.function_id, group.jobs, group.jobs_rule, group.wage_rule) == (
        "consumer_goods",
        101,
        "placed",
        "county",
    )


def test_apportion_breaks_ties_by_code() -> None:
    assert pay.apportion(7, [("3361", 0), ("3362", 0), ("3363", 0)]) == {
        "3361": 3,
        "3362": 2,
        "3363": 2,
    }
    assert pay.apportion(10, [("a", 1), ("b", 2)]) == {"a": 3, "b": 7}


def test_subtree_follows_the_parent_code() -> None:
    leaves = ["3361", "3363", "333", "3122", "3121", "21", "99", "1151", "111"]
    assert pay.subtree("336", leaves) == ("3361", "3363")
    assert pay.subtree("31-33", leaves) == ("3361", "3363", "333", "3122", "3121")
    assert pay.subtree("115", leaves) == ("1151",)
    assert pay.subtree("11", leaves) == ("1151", "111")
    assert pay.subtree("10", leaves) == tuple(leaves)


def test_the_county_total_places_a_withheld_sector() -> None:
    leaves = [
        leaf("92", own="1", jobs=400, payroll=40_000_000),
        leaf("61", own="1", est=2, withheld=True),
    ]
    parents = [parent("10", own="1", jobs=500, payroll=50_000_000)]
    assert placed(leaves, parents) == {"61": (100, 10_000_000)}


def test_a_withheld_county_takes_the_state_wage() -> None:
    rows = [
        leaf("3361", withheld=True),
        leaf("3362", withheld=True),
        state("3361", est=9, jobs=48_138, payroll=4_997_065_672),
        state("3362", withheld=True),
    ]
    (group,) = pay.pay_rows(rows, v2.load_mapping_v2())
    assert (group.jobs_rule, group.wage_rule) == ("partial", "state")
    assert (group.wage_jobs, group.wage_payroll_usd) == (48_138, 4_997_065_672)


def test_a_withheld_national_row_falls_to_all_ownerships() -> None:
    rows = [
        leaf("72", own="2", withheld=True),
        state("72", own="2", withheld=True),
        nation("72", own="2", withheld=True),
        nation("72", own="5", est=9, jobs=14_092_895, payroll=420_499_947_209),
        nation("72", own="3", est=9, jobs=105_403, payroll=5_330_928_520),
    ]
    (group,) = pay.pay_rows(rows, v2.load_mapping_v2())
    assert group.function_id == "leisure_hospitality"
    assert group.wage_rule == "nation_all_ownerships"
    assert (group.wage_jobs, group.wage_payroll_usd) == (14_198_298, 425_830_875_729)


def test_the_nation_wage_is_the_same_ownership() -> None:
    rows = [
        leaf("72", own="2", withheld=True),
        nation("72", own="2", est=9, jobs=1_000, payroll=50_000),
        nation("72", own="5", est=9, jobs=9_000, payroll=900_000),
    ]
    (group,) = pay.pay_rows(rows, v2.load_mapping_v2())
    assert (group.wage_rule, group.wage_jobs, group.wage_payroll_usd) == ("nation", 1_000, 50_000)


def test_no_wage_anywhere_is_refused() -> None:
    rows = [leaf("72", own="2", withheld=True)]
    with pytest.raises(county.ReferenceBuildError, match=r"no_wage: 26163/"):
        pay.pay_rows(rows, v2.load_mapping_v2())


def test_a_cohort_table_without_the_admitted_column_is_refused(tmp_path: Path) -> None:
    table = tmp_path / "cohorts.csv.gz"
    with gzip.open(table, "wt", newline="") as stream:
        stream.write(
            "county_geoid,function_id,ownership_code,member_count\n26163,leisure_hospitality,5,1\n"
        )
    with pytest.raises(county.ReferenceBuildError, match=r"cohort_header"):
        pay.admitted_keys(table)


def test_the_admitted_keys_are_read_by_the_header_name(tmp_path: Path) -> None:
    table = tmp_path / "cohorts.csv.gz"
    with gzip.open(table, "wt", newline="") as stream:
        stream.write(
            "member_count,admitted,ownership_code,function_id,county_geoid\n"
            "1,1,5,leisure_hospitality,26163\n2,0,5,capital_goods,26163\n"
        )
    assert pay.admitted_keys(table) == [("26163", "leisure_hospitality", "5")]


def test_the_committed_pay_table() -> None:
    path, meta_path = pay.ARTIFACT_OUT, pay.METADATA_OUT
    with gzip.open(path, "rt", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = list(reader)
    assert tuple(header) == pay.COLUMNS
    with gzip.open(cohort_v2.ARTIFACT_OUT, "rt", newline="") as stream:
        cohorts = csv.reader(stream)
        next(cohorts)
        admitted = [(r[0], r[1], r[2]) for r in cohorts if r[3] == "1"]
    assert [(r[0], r[1], r[2]) for r in rows] == admitted
    assert {r[5] for r in rows} <= set(pay.JOBS_RULES)
    assert {r[6] for r in rows} <= set(pay.WAGE_RULES)
    assert all(int(r[7]) > 0 and int(r[8]) > 0 for r in rows)
    (wayne,) = [r for r in rows if r[:3] == [COUNTY, "consumer_goods", "5"]]
    assert int(wayne[3]) >= 53_000
    assert wayne[6] == "county"

    metadata = json.loads(meta_path.read_text())
    assert metadata["contract"] == "NationalTradePay2024V1"
    assert metadata["issue"] == "PER-371"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert metadata["artifact"]["sha256"] == digest
    assert metadata["artifact"]["rows"] == len(rows)
    assert metadata["artifact"]["bytes"] == path.stat().st_size
    assert path.stat().st_size < 2_097_152
    for column, rules in ((5, pay.JOBS_RULES), (6, pay.WAGE_RULES)):
        name = "jobs_rule" if column == 5 else "wage_rule"
        counts = {rule: sum(r[column] == rule for r in rows) for rule in rules}
        assert metadata["coverage"][f"by_{name}"] == counts
    registry = yaml.safe_load((ROOT / "data-artifacts.yaml").read_text())
    (entry,) = [e for e in registry["artifacts"] if e["name"] == "national_trade_pay_2024"]
    assert entry["sha256"] == digest
    assert entry["rows"] == len(rows)
