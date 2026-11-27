"""The accounts' sources, sheet reader, industry mapping and owner-occupied shares."""

from __future__ import annotations

import copy
import csv
import gzip
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

import openpyxl
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import make_national_county_reference as county  # type: ignore[import-not-found]  # noqa: E402
import make_national_qcew_function_basis_v2 as v2  # type: ignore[import-not-found]  # noqa: E402
import make_national_trade_accounts as accounts  # type: ignore[import-not-found]  # noqa: E402

SHARE_FIGURES = {
    "intermediate_inputs": Fraction(212560, 238323),
    "compensation": Fraction(0, 18920),
    "production_taxes": Fraction(178599, 254103),
    "gross_operating_surplus": Fraction(1164524, 1541039),
    "households": Fraction(1553178, 2020853),
    "product_subsidies": Fraction(2441, 38219),
}


def document() -> dict[str, Any]:
    return copy.deepcopy(json.loads(accounts.ACCOUNTS_MAPPING.read_bytes()))


def write_sheet(
    path: Path,
    sheet: str,
    columns: list[object],
    rows: list[list[object]],
    *,
    code_row: int = 5,
    first_row: int = 6,
) -> None:
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    assert worksheet is not None
    worksheet.title = sheet
    for index in range(first_row):
        worksheet.append(
            [None] * (len(columns) + 2) if index != code_row else [None, "Code", *columns]
        )
    for number, row in enumerate(rows):
        for offset, value in enumerate(row):
            worksheet.cell(row=first_row + number + 1, column=offset + 1, value=value)
    workbook.save(path)


def test_only_integers_and_the_dots_are_read(tmp_path: Path) -> None:
    target = tmp_path / "book.xlsx"
    write_sheet(
        target,
        "2024",
        ["F010", "T001", "V001"],
        [["111CA", "Farms", 5, None, "..."], [None]],
        code_row=5,
        first_row=7,
    )
    sheet = accounts.read_sheet(target, "2024", code_row=5, first_row=7)
    assert sheet.rows == ("111CA",)
    assert sheet.columns == ("F010", "T001", "V001")
    assert sheet.get("111CA", "F010") == 5
    assert sheet.get("111CA", "T001") == 0
    assert sheet.get("111CA", "V001") == 0
    assert sheet.get("111CA", "missing") == 0
    for bad in ("(D)", 1.5):
        write_sheet(target, "2024", ["F010"], [["111CA", "Farms", bad]], first_row=7)
        with pytest.raises(county.ReferenceBuildError, match=r"bea_cell: 2024/111CA/F010"):
            accounts.read_sheet(target, "2024", code_row=5, first_row=7)
    write_sheet(target, "2024", ["F010"], [["111CA", "A", 1], ["111CA", "B", 2]], first_row=7)
    with pytest.raises(county.ReferenceBuildError, match="bea_duplicate_code"):
        accounts.read_sheet(target, "2024", code_row=5, first_row=7)
    write_sheet(target, "2024", ["F010", "F010"], [["111CA", "A", 1, 2]], first_row=7)
    with pytest.raises(county.ReferenceBuildError, match="bea_duplicate_code"):
        accounts.read_sheet(target, "2024", code_row=5, first_row=7)


def test_codes_are_read_as_stripped_text(tmp_path: Path) -> None:
    target = tmp_path / "book.xlsx"
    write_sheet(
        target, "2017", [111200, "TRADE ", None, "late"], [[111200, "x", 7, 8], ["", "end"]]
    )
    sheet = accounts.read_sheet(target, "2017", code_row=5, first_row=6)
    assert sheet.columns == ("111200", "TRADE")
    assert sheet.rows == ("111200",)
    assert sheet.get("111200", "TRADE") == 8


def test_every_summary_industry_is_placed_once() -> None:
    functions = v2.load_mapping_v2()
    mapping = accounts.load_accounts_mapping(accounts.ACCOUNTS_MAPPING, functions)
    assert len(mapping.whole) == 66
    assert len(mapping.splits) == 5
    assert [e["code"] for e in mapping.document["whole"] if e.get("owner_occupied")] == ["HS"]
    assert mapping.whole["HS"] == "construction_housing"
    assert mapping.whole["GSLE"] == "public_provisioning"
    assert mapping.splits["334"]["consumer_goods"] == ("3343",)
    assert set(mapping.whole.values()) | {t for s in mapping.splits.values() for t in s} == set(
        accounts.TRADES
    )
    assert len(mapping.document["industry_codes"]) == 71
    assert mapping.document["residual_rows"] == {"Used": "scrap_used", "Other": "noncomparable"}

    def refused(edit: Any, message: str) -> None:
        doc = document()
        edit(doc)
        with pytest.raises(county.ReferenceBuildError, match=message):
            accounts.validate_accounts_mapping(doc, functions)

    refused(
        lambda d: d["whole"].remove(next(e for e in d["whole"] if e["code"] == "GSLE")),
        "accounts_mapping_coverage",
    )
    refused(
        lambda d: next(s for s in d["splits"] if s["code"] == "334")["parts"][
            "consumer_goods"
        ].append("3361"),
        "accounts_split_naics: 334/3361",
    )
    refused(
        lambda d: next(s for s in d["splits"] if s["code"] == "113FF")["parts"]["food"].remove(
            "1151"
        ),
        "accounts_split_naics: 113FF/1151",
    )
    refused(
        lambda d: next(s for s in d["splits"] if s["code"] == "313TT")["parts"][
            "manufacturing"
        ].append("3121"),
        "accounts_split_naics: 313TT/3121",
    )
    refused(
        lambda d: next(e for e in d["whole"] if e["code"] == "111CA").update(trade="steel"),
        "accounts_mapping_trade: 111CA",
    )


def test_the_summary_sheet_must_hold_the_same_industries(tmp_path: Path) -> None:
    functions = v2.load_mapping_v2()
    mapping = accounts.load_accounts_mapping(accounts.ACCOUNTS_MAPPING, functions)
    codes = list(mapping.document["industry_codes"])
    target = tmp_path / "use.xlsx"
    write_sheet(target, "2024", [*codes, "Used"], [[codes[0], "Farms", 1]], code_row=5, first_row=7)
    accounts.check_summary_coverage(
        mapping, accounts.read_sheet(target, "2024", code_row=5, first_row=7)
    )
    write_sheet(
        target, "2024", [*codes[:-1], "Used"], [[codes[0], "Farms", 1]], code_row=5, first_row=7
    )
    with pytest.raises(county.ReferenceBuildError, match="accounts_mapping_coverage"):
        accounts.check_summary_coverage(
            mapping, accounts.read_sheet(target, "2024", code_row=5, first_row=7)
        )


def detail_pair(tmp_path: Path, *, households: int = 1_553_178) -> tuple[Any, Any]:
    use = tmp_path / "use.xlsx"
    supply = tmp_path / "supply.xlsx"
    write_sheet(
        use,
        "2017",
        ["531HSO", "531HST", "F01000"],
        [
            ["T005", "x", 212_560, 25_763, 0],
            ["V00100", "x", None, 18_920, 0],
            ["T00OTOP", "x", 178_599, 75_504, 0],
            ["V00300", "x", 1_164_524, 376_515, 0],
            ["531HSO", "x", 0, 0, households],
            ["531HST", "x", 0, 0, 467_675],
        ],
    )
    write_sheet(
        supply,
        "2017",
        ["SUB"],
        [["531HSO", "x", -2_441], ["531HST", "x", -35_778]],
    )
    return (
        accounts.read_sheet(use, "2017", code_row=5, first_row=6),
        accounts.read_sheet(supply, "2017", code_row=5, first_row=6),
    )


def test_owner_shares_are_the_2017_figures(tmp_path: Path) -> None:
    mapping = accounts.load_accounts_mapping(accounts.ACCOUNTS_MAPPING, v2.load_mapping_v2())
    assert mapping.owner_shares == SHARE_FIGURES
    use, supply = detail_pair(tmp_path)
    assert accounts.owner_occupied_shares(use, supply) == SHARE_FIGURES
    use, supply = detail_pair(tmp_path, households=1_553_179)
    with pytest.raises(county.ReferenceBuildError, match="owner_occupied_share: households"):
        accounts.owner_occupied_shares(use, supply)


def test_changed_accounts_sources_are_refused(tmp_path: Path) -> None:
    target = tmp_path / "input-output/supply-use/Use_Summary.xlsx"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"short")
    with pytest.raises(county.ReferenceBuildError, match="source_digest: use_summary"):
        accounts.verify_accounts_sources(tmp_path)


def test_a_missing_accounts_workbook_is_a_digest_refusal(tmp_path: Path) -> None:
    with pytest.raises(county.ReferenceBuildError, match="source_digest: use_summary"):
        accounts.verify_accounts_sources(tmp_path)


def test_a_malformed_owner_share_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for bad in ([212_560], [212_560, "238323"], [1.5, 2], "x", None):
        doc = document()
        doc["owner_occupied_basis"]["shares"]["compensation"]["figures"] = bad
        with pytest.raises(county.ReferenceBuildError, match="accounts_mapping_owner_shares"):
            accounts._documented_figures(doc)
    use, supply = detail_pair(tmp_path)
    for key in ("sheet", "column_owner", "column_tenant", "row"):
        doc = document()
        del doc["owner_occupied_basis"]["shares"]["intermediate_inputs"][key]
        target = tmp_path / f"mapping_{key}.json"
        target.write_text(json.dumps(doc))
        monkeypatch.setattr(accounts, "ACCOUNTS_MAPPING", target)
        with pytest.raises(county.ReferenceBuildError, match="accounts_mapping_owner_shares"):
            accounts.owner_occupied_shares(use, supply)


def test_the_sources_manifest_pins_the_four_workbooks() -> None:
    manifest = json.loads(accounts.SOURCES.read_bytes())
    assert manifest["contract"] == "NationalTradeAccounts2024SourcesV1"
    assert {s["id"]: (s["bytes"], s["sha256"]) for s in manifest["sources"]} == {
        "use_summary": (
            1161293,
            "98dd61d7c2a8df7c9678b1ebff9015372ac5ed082df33f9b15e8d7bf9408f341",
        ),
        "supply_summary": (
            822838,
            "286c42547ff83b7756aae893829d8cb54825ec4ed9bdae60fda23ec7bdc634d9",
        ),
        "use_detail": (
            2121639,
            "07aa2a21151e78ec1462c8f48142d274c153d90aff07bd797e07c6bc8486911e",
        ),
        "supply_detail": (
            1610518,
            "7a3a403f7a7e8335e61776c1da6c423409d54090acaee597bbae738fa9a6703e",
        ),
    }
    assert all(
        set(s) == {"id", "path", "url", "bytes", "sha256", "note"} for s in manifest["sources"]
    )


def nation_row(naics: str, jobs: int | None, payroll: int | None, ownership: str = "5") -> Any:
    return v2.SourceRow(
        "nation_leaf",
        v2.NATION_AREA,
        ownership,
        naics,
        14,
        "" if jobs is not None else "N",
        1,
        jobs,
        payroll,
        None,
    )


def even_shares(mapping: Any) -> dict[str, dict[str, Fraction]]:
    return {
        code: {trade: Fraction(1, len(parts)) for trade in parts}
        for code, parts in mapping.splits.items()
    }


def test_split_cell_parts_add_up() -> None:
    thirds = [("a", Fraction(1, 3)), ("b", Fraction(2, 3))]
    assert accounts.split_cell(7000, thirds) == {"a": 2333, "b": 4667}
    assert accounts.split_cell(-5000, thirds) == {"a": -1667, "b": -3333}
    assert accounts.split_cell(0, thirds) == {"a": 0, "b": 0}
    halves = [("y", Fraction(1, 2)), ("x", Fraction(1, 2))]
    assert accounts.split_cell(3, halves) == {"x": 2, "y": 1}
    with pytest.raises(county.ReferenceBuildError, match="accounts_split_shares"):
        accounts.split_cell(1, [("a", Fraction(1, 3))])


def housing_fixture(tmp_path: Path) -> tuple[Any, Any]:
    use = tmp_path / "use24.xlsx"
    supply = tmp_path / "supply24.xlsx"
    write_sheet(
        use,
        "2024",
        ["HS", "T001", "F010"],
        [
            ["521CI", "x", 200_000, 0, 0],
            ["23", "x", 38_323, 0, 0],
            ["HS", "x", 0, 0, 2_020_853],
            ["T005", "x", 238_323, 0, 0],
            ["V001", "x", 18_920, 0, 0],
            ["T00OTOP", "x", 254_103, 0, 0],
            ["T00OSUB", "x", 0, 0, 0],
            ["V003", "x", 1_541_039, 0, 0],
            ["VABAS", "x", 1_814_062, 0, 0],
            ["T018", "x", 2_052_385, 0, 0],
        ],
        first_row=7,
    )
    write_sheet(
        supply,
        "2024",
        ["HS", "23", "T007", "SUB", "T016"],
        [
            ["HS", "x", 3_162_745, 0, 3_162_745, -62_510, 3_143_691],
            ["23", "x", 29_504, 0, 0, 0, 0],
        ],
        first_row=7,
    )
    return (
        accounts.read_sheet(use, "2024", code_row=5, first_row=7),
        accounts.read_sheet(supply, "2024", code_row=5, first_row=7),
    )


def folded(tmp_path: Path) -> dict[tuple[str, str, str], int]:
    mapping = accounts.load_accounts_mapping(accounts.ACCOUNTS_MAPPING, v2.load_mapping_v2())
    use, supply = housing_fixture(tmp_path)
    cells = accounts.fold(use, supply, mapping, even_shares(mapping))
    return {(c.block, c.row_key, c.column_key): c.value for c in cells}


def test_owner_and_tenant_housing_add_up(tmp_path: Path) -> None:
    got = folded(tmp_path)
    owner, home = accounts.OWNER, "construction_housing"
    assert got[("industry", owner, "intermediate_inputs")] == 212_560_000
    assert got[("industry", owner, "compensation")] == 0
    assert got[("industry", owner, "production_taxes_less_subsidies")] == 178_599_000
    assert got[("industry", owner, "gross_operating_surplus")] == 1_164_524_000
    assert got[("use", owner, "households")] == 1_553_178_000
    for measure, source in (
        ("intermediate_inputs", 238_323),
        ("compensation", 18_920),
        ("production_taxes_less_subsidies", 254_103),
        ("gross_operating_surplus", 1_541_039),
        ("value_added_basic", 1_814_062),
        ("gross_output", 2_052_385),
    ):
        both = got[("industry", owner, measure)] + got[("industry", home, measure)]
        assert both == 1000 * source, measure
    rows = ("business_services", "construction_housing")
    both_use = sum(got[("use", row, column)] for row in rows for column in (owner, home))
    assert both_use == 238_323_000
    # Each product row splits by the same share (212,560 of 238,323), largest remainder.
    assert (got[("use", "business_services", owner)], got[("use", "business_services", home)]) == (
        178_379_762,
        21_620_238,
    )
    assert (
        got[("use", "construction_housing", owner)],
        got[("use", "construction_housing", home)],
    ) == (
        34_180_238,
        4_142_762,
    )
    assert got[("use", owner, "households")] + got[("use", home, "households")] == 2_020_853_000
    expected = {
        "commodity_output": 3_162_745_000,
        "total_supply": 3_143_691_000,
        "product_subsidies": -62_510_000,
    }
    for column in accounts.SUPPLY:
        both = got[("supply", owner, column)] + got[("supply", home, column)]
        assert both == expected.get(column, 0), column
    assert got[("supply", owner, "total_supply")] == got[("use", owner, "households")]
    assert (
        got[("supply", owner, "commodity_output")]
        == got[("supply", owner, "total_supply")] - got[("supply", owner, "product_subsidies")]
    )


def test_the_owner_makes_only_housing(tmp_path: Path) -> None:
    got = folded(tmp_path)
    owner, home = accounts.OWNER, "construction_housing"
    made = got[("supply", owner, "commodity_output")]
    nonzero = [k for k, v in got.items() if k[0] == "make" and k[1] == owner and v]
    assert nonzero == [("make", owner, owner)]
    assert got[("make", owner, owner)] == made
    assert got[("make", home, home)] == 3_162_745_000 + 29_504_000 - made


def test_split_codes_follow_national_jobs() -> None:
    functions = v2.load_mapping_v2()
    mapping = accounts.load_accounts_mapping(accounts.ACCOUNTS_MAPPING, functions)
    nation = [
        nation_row("113", 74_846, 1),
        nation_row("114", 375_931, 1),
        *(nation_row(code, 2, 1) for code in ("311", "3122", "313", "314")),
        *(nation_row(code, 2, 1) for code in ("3343", "3341", "3352", "3351")),
    ]
    shares = accounts.split_shares(nation, mapping)
    assert shares["113FF"] == {
        "extraction": Fraction(74_846, 450_777),
        "food": Fraction(375_931, 450_777),
    }
    sheet = accounts.BeaSheet(("113FF",), ("111CA",), {("113FF", "111CA"): 450_777})
    cells = accounts.fold(sheet, accounts.BeaSheet((), (), {}), mapping, shares)
    got = {(c.block, c.row_key, c.column_key): c.value for c in cells}
    assert got[("use", "extraction", "food")] == 74_846_000
    assert got[("use", "food", "food")] == 375_931_000
    assert accounts.split_cells(nation, mapping)[0] == accounts.AccountCell(
        "split", "113FF", "extraction", "jobs", 74_846
    )
    with pytest.raises(county.ReferenceBuildError, match="accounts_split_jobs: 113FF"):
        accounts.split_shares([nation_row("113", 0, 0)], mapping)


def test_jobs_sum_the_ownerships_and_the_public_three() -> None:
    functions = v2.load_mapping_v2()
    nation = [
        nation_row("311", 10, 100, "5"),
        nation_row("311", 4, 40, "1"),
        nation_row("311", 6, 60, "3"),
        nation_row("311", None, None, "2"),
    ]
    got = {
        (c.row_key, c.column_key): (c.value, c.unit) for c in accounts.jobs_cells(nation, functions)
    }
    assert got[("food", "jobs")] == (20, "jobs")
    assert got[("food", "annual_payroll_usd")] == (200, "usd")
    assert got[("food", "jobs_public")] == (10, "jobs")
    assert got[("food", "annual_payroll_public_usd")] == (100, "usd")
    assert got[("extraction", "jobs")] == (0, "jobs")
    assert len(got) == 48


def identity_cells(output: int) -> tuple[list[Any], Any, Any]:
    """One farm industry whose output differs from inputs plus value added by `output - 110`."""
    use = accounts.BeaSheet(
        ("111CA", "T005", "V001", "T00OTOP", "V003", "VABAS", "T018", "VAPRO"),
        ("111CA", "T001", "F010", "T019"),
        {
            ("111CA", "111CA"): 40,
            ("111CA", "T001"): 40,
            ("111CA", "F010"): output - 40,
            ("111CA", "T019"): output,
            ("T005", "111CA"): 40,
            ("V001", "111CA"): 40,
            ("T00OTOP", "111CA"): 10,
            ("V003", "111CA"): 20,
            ("VABAS", "111CA"): 70,
            ("T018", "111CA"): output,
            ("VAPRO", "111CA"): output - 40,
        },
    )
    supply = accounts.BeaSheet(
        ("111CA", "T017"),
        ("111CA", "T007", "T016"),
        {
            ("111CA", "111CA"): output,
            ("111CA", "T007"): output,
            ("111CA", "T016"): output,
            ("T017", "111CA"): output,
        },
    )
    mapping = accounts.load_accounts_mapping(accounts.ACCOUNTS_MAPPING, v2.load_mapping_v2())
    return list(accounts.fold(use, supply, mapping, even_shares(mapping))), use, supply


def test_a_gap_beyond_its_bound_is_refused() -> None:
    cells, use, supply = identity_cells(120)
    result = accounts.check(cells, use, supply)
    assert result["checks"]["industry_output"] == 10
    assert set(result["checks"]) == set(accounts.CHECK_NAMES)
    assert result["source_controls"] == {"T018": 120, "T005": 40, "VABAS": 70, "T019": 120}
    cells, use, supply = identity_cells(121)
    with pytest.raises(
        county.ReferenceBuildError, match=r"accounts_identity: industry_output/111CA"
    ):
        accounts.check(cells, use, supply)
    cells, use, supply = identity_cells(110)
    assert accounts.check(cells, use, supply)["checks"]["industry_output"] == 0


def committed_cells() -> dict[tuple[str, str, str], tuple[str, int]]:
    with gzip.open(accounts.ARTIFACT_OUT, "rt", newline="") as stream:
        reader = csv.reader(stream)
        assert tuple(next(reader)) == accounts.COLUMNS
        return {(r[0], r[1], r[2]): (r[3], int(r[4])) for r in reader}


def test_the_committed_accounts() -> None:
    cells = committed_cells()
    counts = {b: sum(k[0] == b for k in cells) for b in accounts.BLOCK_ORDER}
    # The plan pins 796 rows with 345 in `use` (15 x 23), but its own INDUSTRIES (13) and
    # FINAL_USES (11) make 24 columns: 15 x 24 = 360 and 811 rows in all.
    assert counts == {
        "use": 360,
        "supply": 120,
        "make": 195,
        "industry": 78,
        "jobs": 48,
        "split": 10,
    }
    assert len(cells) == 811
    metadata = json.loads(accounts.METADATA_OUT.read_bytes())
    assert metadata["checks"] == {
        "use_total": 2,
        "use_row": 6,
        "use_column": 8,
        "supply_parts": 2,
        "use_supply": 1,
        "industry_output": 1,
        "value_added": 1,
        "make_row": 4,
        "make_column": 4,
        "make_use_output": 0,
    }
    split = {(k[1], k[2]): v[1] for k, v in cells.items() if k[0] == "split"}
    assert split == {
        ("113FF", "extraction"): 74_846,
        ("113FF", "food"): 375_931,
        ("311FT", "food"): 2_090_409,
        ("311FT", "manufacturing"): 10_634,
        ("313TT", "manufacturing"): 84_975,
        ("313TT", "consumer_goods"): 96_972,
        ("334", "consumer_goods"): 18_851,
        ("334", "capital_goods"): 1_001_166,
        ("335", "consumer_goods"): 60_010,
        ("335", "capital_goods"): 360_166,
    }
    jobs = {
        trade: (cells[("jobs", trade, "jobs")][1], cells[("jobs", trade, "annual_payroll_usd")][1])
        for trade in accounts.TRADES
    }
    assert jobs == {
        "food": (3_276_552, 182_524_887_785),
        "extraction": (661_997, 81_101_049_742),
        "energy_utilities": (966_571, 120_557_836_752),
        "manufacturing": (5_061_467, 408_360_829_124),
        "consumer_goods": (2_239_990, 168_955_584_595),
        "capital_goods": (3_282_239, 372_473_890_208),
        "construction_housing": (10_164_182, 815_427_986_577),
        "distribution_transport": (29_169_333, 1_789_433_399_662),
        "household_services": (42_212_557, 2_712_539_847_517),
        "leisure_hospitality": (17_159_014, 572_592_943_503),
        "business_services": (32_695_640, 3_809_815_227_073),
        "public_provisioning": (7_846_751, 662_040_421_314),
    }
    assert sum(jobs_pair[0] for jobs_pair in jobs.values()) == 154_736_293
    assert metadata["coverage"] == {
        "block_rows": counts,
        "rows_in_all": 811,
        "jobs_in_all": 154_736_293,
    }
    owner = accounts.OWNER
    made = sum(cells[("make", owner, p)][1] for p in accounts.PRODUCTS)
    assert made - cells[("industry", owner, "gross_output")][1] == 5_702_525
    assert metadata["housing"]["owner_make_less_gross_output_usd_thousands"] == 5_702_525
    housing = sum(
        cells[("use", row, "households")][1]
        for row in ("owner_occupied_housing", "construction_housing")
    )
    assert housing == 3_151_785_000
    gross = sum(cells[("industry", i, "gross_output")][1] for i in accounts.INDUSTRIES)
    assert gross == 1000 * metadata["source_controls"]["T018"]
    assert metadata["artifact"]["rows"] == len(cells)
    assert metadata["artifact"]["sha256"] == county.sha256(accounts.ARTIFACT_OUT)
    assert metadata["artifact"]["bytes"] == accounts.ARTIFACT_OUT.stat().st_size
    registered = {
        entry["name"]: entry
        for entry in yaml.safe_load((ROOT / "data-artifacts.yaml").read_text())["artifacts"]
    }["national_trade_accounts_2024"]
    assert registered["sha256"] == metadata["artifact"]["sha256"]
    assert registered["rows"] == len(cells)


def test_every_block_is_dense_and_signed_as_the_source() -> None:
    cells = committed_cells()
    for row in accounts.PRODUCTS:
        for column in (*accounts.INDUSTRIES, *accounts.FINAL_USES):
            assert ("use", row, column) in cells
    assert cells[("use", "scrap_used", "households")][0] == "usd_thousands"
    assert cells[("jobs", "food", "jobs")][0] == "jobs"
    assert cells[("jobs", "food", "annual_payroll_usd")][0] == "usd"
    assert cells[("split", "113FF", "food")][0] == "jobs"
    assert cells[("supply", "distribution_transport", "trade_margins")][1] < 0
    assert cells[("supply", "food", "trade_margins")][1] > 0
    assert cells[("supply", "food", "product_subsidies")][1] <= 0
