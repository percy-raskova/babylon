"""The accounts' sources, sheet reader, industry mapping and owner-occupied shares."""

from __future__ import annotations

import copy
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

import openpyxl
import pytest

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
