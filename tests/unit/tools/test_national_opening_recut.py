"""Task 9: the builder's settings, the census reader and the accounts re-cut."""

from __future__ import annotations

import gzip
import json
import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import make_national_county_reference as county  # type: ignore[import-not-found]  # noqa: E402
import national_opening_recut as r  # type: ignore[import-not-found]  # noqa: E402

ReferenceBuildError = county.ReferenceBuildError

ECONOMY_DIR = ROOT / "src/babylon/data/reference/economy"
ACCOUNTS = ECONOMY_DIR / "national_trade_accounts_2024.csv.gz"
CENSUS = ECONOMY_DIR / "national_opening_census_v13.json.gz"
CENSUS_TEXT_SHA256 = "efa195be9d8da65cd0d28ae5967639833c41cba94d1118e6c0896aeeb1b2b215"

FOOD, CAPITAL, HS, SHOP, PUBLIC = (
    "food",
    "capital_goods",
    "household_services",
    "distribution_transport",
    "public_provisioning",
)
SMALL = r.Economy(
    trades=(FOOD, CAPITAL, HS, SHOP, PUBLIC),
    product={
        FOOD: "food",
        CAPITAL: "equipment",
        HS: "household_services",
        PUBLIC: "public_provision",
    },
    storable=frozenset({"food", "equipment"}),
    shop_trade=SHOP,
    public_trade=PUBLIC,
    capital_trade=CAPITAL,
    extraction_trade=None,
    shop_goods=frozenset({"food"}),
    person_needs=("food", "household_services"),
    household_needs=(),
    place_services=frozenset({"household_services", "public_provision"}),
)
SMALL_SETTINGS = replace(
    r.Settings(),
    service_stage={"household_services": 2, "public_provision": 2},
    paying_order=("food", "household_services"),
    crossing=frozenset({"food", "equipment"}),
    country_services=frozenset(),
)


def small_accounts(*, food_surplus: int = 30) -> dict[str, dict[str, dict[str, int]]]:
    """The five-trade fixture; `phi = 1` everywhere (total supply = output + imports)."""
    return {
        "use": {
            FOOD: {
                FOOD: 10,
                HS: 20,
                SHOP: 5,
                "households": 100,
                "state_local_consumption": 15,
                "exports": 10,
                "inventories": 5,
            },
            HS: {
                FOOD: 8,
                CAPITAL: 4,
                HS: 6,
                SHOP: 2,
                "households": 50,
                "state_local_consumption": 30,
                "investment_structures": 12,
            },
            CAPITAL: {
                FOOD: 3,
                HS: 2,
                SHOP: 1,
                "investment_equipment": 40,
                "households": 4,
                "state_local_consumption": 5,
                "exports": 6,
            },
        },
        "supply": {
            FOOD: {"commodity_output": 120, "imports": 20, "total_supply": 140},
            HS: {"commodity_output": 100, "imports": 0, "total_supply": 100},
            CAPITAL: {"commodity_output": 90, "imports": 10, "total_supply": 100},
        },
        "industry": {
            FOOD: {"gross_operating_surplus": food_surplus},
            CAPITAL: {"gross_operating_surplus": 10},
            HS: {"gross_operating_surplus": 20},
            SHOP: {"gross_operating_surplus": 5},
            PUBLIC: {"gross_operating_surplus": 0},
        },
        "jobs": {
            FOOD: {"jobs": 5, "annual_payroll_usd": 50_000},
            CAPITAL: {"jobs": 2, "annual_payroll_usd": 20_000},
            HS: {"jobs": 4, "annual_payroll_usd": 40_000},
            SHOP: {"jobs": 1, "annual_payroll_usd": 10_000},
            PUBLIC: {"jobs": 3, "annual_payroll_usd": 30_000},
        },
    }


def test_the_recut_of_five_trades() -> None:
    cut = r.recut(small_accounts(), SMALL_SETTINGS, SMALL)
    assert cut.inputs[HS][FOOD] == Fraction(2544, 109)
    assert cut.inputs[HS][CAPITAL] == Fraction(1060, 109)
    assert cut.households[HS] == Fraction(7950, 109)
    assert cut.inputs[FOOD][HS] == Fraction(620, 29)
    assert cut.inputs[FOOD][PUBLIC] == Fraction(465, 29)
    assert cut.households[FOOD] == Fraction(3100, 29)
    assert cut.exports[FOOD] == Fraction(310, 29)
    assert cut.equipment == 55
    assert cut.exports[CAPITAL] == 6
    assert cut.inputs[CAPITAL] == {}
    assert cut.import_share[FOOD] == Fraction(1, 7)
    assert cut.import_share[CAPITAL] == Fraction(1, 10)
    assert cut.domestic_output[FOOD] == Fraction(930, 7)
    assert cut.domestic_output[CAPITAL] == Fraction(549, 10)
    assert cut.domestic_output[HS] == 106
    assert cut.domestic_output[PUBLIC] == Fraction(1335, 29)
    assert cut.domestic_output[SHOP] == 10
    assert cut.accounts_margin[FOOD] == Fraction(22706, 27979)
    assert cut.accounts_margin[CAPITAL] == Fraction(3049, 3600)
    assert cut.accounts_margin[HS] == Fraction(647, 890)
    assert cut.accounts_margin[SHOP] == 0
    assert cut.accounts_margin[PUBLIC] == 0
    assert cut.moved[("R1", HS)] == 30
    assert cut.moved[("R3", HS)] == Fraction(10, 3)
    assert cut.moved[("R3", FOOD)] == 5
    assert cut.moved[("O4_inventories", FOOD)] == 5
    assert cut.accounts_payroll[FOOD] == 50
    assert cut.accounts_jobs[HS] == 4


def test_the_spread_keeps_each_row_whole() -> None:
    cut = r.recut(small_accounts(), SMALL_SETTINGS, SMALL)

    def row(trade: str) -> Fraction:
        return (
            sum(cut.inputs[trade].values(), Fraction(0))
            + cut.households.get(trade, 0)
            + cut.exports.get(trade, 0)
        )

    assert row(HS) == 106
    assert row(FOOD) == 155
    assert row(CAPITAL) + cut.equipment == 61


def test_a_negative_surplus_takes_no_investment() -> None:
    cut = r.recut(small_accounts(food_surplus=-30), SMALL_SETTINGS, SMALL)
    # Household services' structures (12) go 8 to capital goods and 4 to the shop's spread.
    assert cut.moved[("R3", HS)] == 2 + 4
    kept = Fraction(8 + (4 + 8) + 50)  # food 8, capital 4 + 8, households 50
    k = 1 + Fraction(30 + 6) / kept
    assert cut.inputs[HS].get(FOOD) == 8 * k
    assert cut.inputs[HS][CAPITAL] == 12 * k


def test_a_stage_rule_follows_the_setting() -> None:
    staged = replace(SMALL_SETTINGS, service_stage={"household_services": 1, "public_provision": 2})
    cut = r.recut(small_accounts(), staged, SMALL)
    assert PUBLIC in cut.inputs[HS]
    assert ("R1", HS) not in cut.moved
    assert r.allowed(staged, SMALL, "household_services", PUBLIC)
    assert not r.allowed(SMALL_SETTINGS, SMALL, "household_services", PUBLIC)
    assert not r.allowed(staged, SMALL, "food", SHOP)


def test_the_import_shares_of_the_committed_table() -> None:
    cut = r.recut(r.read_accounts(ACCOUNTS), r.Settings())
    bps = {trade: (share * 10_000).__floor__() for trade, share in cut.import_share.items()}
    assert bps["food"] == 1_102
    assert bps["extraction"] == 2_294
    assert bps["manufacturing"] == 2_221
    assert bps["consumer_goods"] == 4_277
    assert bps["capital_goods"] == 4_104
    assert bps["business_services"] == 233
    for trade in r.TRADES:
        if trade not in {
            "food",
            "extraction",
            "manufacturing",
            "consumer_goods",
            "capital_goods",
            "business_services",
        }:
            assert bps[trade] == 0, trade


def test_the_committed_recut_keeps_the_rules() -> None:
    settings = r.Settings()
    cut = r.recut(r.read_accounts(ACCOUNTS), settings)
    for trade, row in cut.inputs.items():
        assert trade not in row
        for other in row:
            assert r.allowed(settings, r.TWELVE, r.PRODUCT[trade], other), (trade, other)
        assert "owner_occupied_housing" not in row
    assert cut.inputs["capital_goods"] == {}
    business = cut.inputs["business_services"]
    for buyer in ("household_services", "leisure_hospitality", "public_provisioning"):
        assert business[buyer] > 0
    assert business.get("construction_housing", 0) == 0
    assert cut.exports["business_services"] > 0
    r1 = sum((v for (reason, _), v in cut.moved.items() if reason == "R1"), Fraction(0))
    r2 = sum((v for (reason, _), v in cut.moved.items() if reason == "R2"), Fraction(0))
    # A period's dollars: USD thousands a year x 1000 / 13, in thousand millions.
    assert 150 < r1 * 1000 / 13 / 10**9 < 400
    assert 5 < r2 * 1000 / 13 / 10**9 < 30


def test_bad_settings_are_refused() -> None:
    swapped = replace(
        r.Settings(),
        service_stage={**r.Settings().service_stage, "housing": 2},
        paying_order=(
            "food",
            "materials",
            "consumer_goods",
            "housing",
            "utility",
            "business_services",
            "household_services",
            "leisure",
            "resources",
        ),
    )
    with pytest.raises(ReferenceBuildError, match=r"^setting: paying_order"):
        r.check_settings(swapped)
    with pytest.raises(ReferenceBuildError, match=r"^setting: crossing"):
        r.check_settings(replace(r.Settings(), crossing=frozenset({"food", "public_provision"})))
    with pytest.raises(ReferenceBuildError, match=r"^setting: country_services"):
        r.check_settings(replace(r.Settings(), country_services=frozenset({"housing"})))
    r.check_settings(r.Settings())
    with pytest.raises(ReferenceBuildError, match=r"^setting: paying_order"):
        r.recut(small_accounts(), r.Settings(), SMALL)


def test_only_the_ruled_settings_pass() -> None:
    r.check_ruled(r.Settings())
    base = r.Settings()
    cases: dict[str, Any] = {
        "service_stage": replace(
            base, service_stage={**base.service_stage, "business_services": 2}
        ),
        "crossing": replace(base, crossing=base.crossing - {"business_services"}),
        "benefit_rule": replace(base, benefit_rule="dearest_place"),  # type: ignore[arg-type]
        "place_body": replace(base, place_body="one_share"),  # type: ignore[arg-type]
        "country_services": replace(base, country_services=frozenset()),
        "shop_import_saving": replace(base, shop_import_saving="shop"),  # type: ignore[arg-type]
    }
    for name, bad in cases.items():
        with pytest.raises(ReferenceBuildError, match=rf"^setting_not_ruled: {name}$"):
            r.check_ruled(bad)
    # A design figure is not a choice.
    r.check_ruled(replace(base, margin_halvings=41))


def _census_text() -> str:
    return gzip.decompress(CENSUS.read_bytes()).decode("utf-8")


def _write(tmp_path: Path, document: Any) -> Path:
    path = tmp_path / "census.json.gz"
    path.write_bytes(gzip.compress(json.dumps(document, sort_keys=True).encode("utf-8"), mtime=0))
    return path


def test_the_committed_census_is_read() -> None:
    first = r.read_census(CENSUS)
    second = r.read_census(CENSUS)
    assert first.sha256 == second.sha256 == CENSUS_TEXT_SHA256
    assert len(first.places) == 316
    assert [place.label for place in first.places] == sorted(place.label for place in first.places)
    assert sum(place.public_persons_served for place in first.places) == 334_922_499
    assert sum(place.public_machines for place in first.places) == 245_105
    assert sum(t.payroll_micros for t in first.trades.values()) == 802_516_596_548_058_080
    assert first.trades["distribution_transport"].machines == 0
    wayne = next(place for place in first.places if place.label == "26163")
    assert wayne.state == "26" and wayne.hub == "26163" and wayne.label == "26163"
    seller = wayne.sellers["earning_owner"]["food"]
    assert seller.abroad is not None
    assert wayne.sellers["earning_owner"]["utility"].abroad is None
    assert "materials" not in wayne.sellers["collective_residence"]
    assert first.crossing_force[("business_services", "canada", "food")] > 0
    assert first.firm_assignment[("food", "canada", "food")] >= 0
    assert first.retail_assignment[("food", "canada")] >= 0


def mend(document: dict[str, Any], what: str) -> None:
    place = document["places"]["26163"]
    if what == "unknown_key":
        document["extra"] = 1
    elif what == "missing_trade":
        del document["trades"]["food"]
    elif what == "float":
        document["households"]["earning-owner"]["persons"] = 1.5
    elif what == "wages":
        document["households"]["earning-owner"]["wage_income_micros_per_period"] += 1
    elif what == "place_over":
        place["trades"]["food"]["employee_persons"] += 1
    elif what == "key_over":
        place["keys"]["earning-owner"]["persons"] += 1
    elif what == "machines":
        document["workers_per_machine"]["food"] = 5
    elif what == "public_machines":
        place["trades"]["public_provisioning"]["machines"] += 1
    elif what == "short_force":
        document["crossing_force"]["business_services"]["canada"]["food"] -= 1
    elif what == "unknown_region":
        document["crossing_force"]["business_services"]["atlantis"] = dict(
            document["crossing_force"]["business_services"]["canada"]
        )
    elif what == "served":
        place["public_persons_served"] += 1
    elif what == "sources":
        document["sources"]["country_services"] = ["utility"]
    elif what == "unknown_seller_region":
        place["abroad"]["earning-owner"]["food"] = "atlantis"
    else:  # pragma: no cover
        raise AssertionError(what)


@pytest.mark.parametrize(
    ("what", "code"),
    [
        ("unknown_key", "census_shape: extra"),
        ("missing_trade", "census_shape: trades.food"),
        ("float", "census_shape: households.earning-owner.persons"),
        ("wages", "census_wages"),
        ("place_over", "census_places: food"),
        ("key_over", "census_places: earning_owner"),
        ("machines", "census_machines: food"),
        ("public_machines", "census_machines: public_provisioning"),
        ("short_force", "census_sites: business_services/food"),
        ("unknown_region", "census_shape: crossing_force.business_services.atlantis"),
        ("served", "census_places: public_persons_served"),
        ("sources", "census_shape: sources.country_services"),
        ("unknown_seller_region", "census_shape: places.26163.abroad.earning-owner.food"),
    ],
)
def test_the_census_reader_refuses_a_bad_census(tmp_path: Path, what: str, code: str) -> None:
    document = json.loads(_census_text())
    mend(document, what)
    with pytest.raises(ReferenceBuildError) as error:
        r.read_census(_write(tmp_path, document))
    assert str(error.value) == code


def test_a_float_is_never_used() -> None:
    source = (ROOT / "tools/national_opening_recut.py").read_text(encoding="utf-8")
    import ast

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            assert not isinstance(node.value, float)
        if isinstance(node, ast.Name):
            assert node.id != "float"


def test_rounding_rules() -> None:
    assert r.half_up(Fraction(5, 2)) == 3
    assert r.half_up(Fraction(-5, 2)) == -2
    assert r.half_up(Fraction(7, 3)) == 2
    assert r.to_grid(Fraction(1, 3), 100) == Fraction(33, 100)
    assert r.to_grid(Fraction(1, 200), 100) == Fraction(1, 100)
    assert r.up_to_grid(Fraction(1, 3), 100) == Fraction(34, 100)
    assert r.up_to_grid(Fraction(1, 5), 5) == Fraction(1, 5)
