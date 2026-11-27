"""Task 12: foreign regions in balance (O11): their mix of jobs, their shares of trade, their money."""

from __future__ import annotations

import ast
import sys
import tomllib
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import make_national_county_reference as county  # type: ignore[import-not-found]  # noqa: E402
import national_opening_abroad as ab  # type: ignore[import-not-found]  # noqa: E402
import national_opening_recut as r  # type: ignore[import-not-found]  # noqa: E402
import national_opening_solve as s  # type: ignore[import-not-found]  # noqa: E402
import national_opening_tiers as t  # type: ignore[import-not-found]  # noqa: E402
import national_opening_units as u  # type: ignore[import-not-found]  # noqa: E402

ReferenceBuildError = county.ReferenceBuildError
F = Fraction
M = 10**6
ECONOMY_DIR = ROOT / "src/babylon/data/reference/economy"
ACCOUNTS = ECONOMY_DIR / "national_trade_accounts_2024.csv.gz"
CENSUS = ECONOMY_DIR / "national_opening_census_v13.json.gz"
FIXTURE = (
    ROOT / "rust/crates/babylon-persistence/tests/fixtures/national_twelve_trades.defines.toml"
)

# ---- a hand economy ---------------------------------------------------------------------
# Food (a shop good, 1 hour for 10 units at the shop) and household services, one shop.


def product(key: str, price: int, kind: str, handling: tuple[int, int] | None = None) -> u.Product:
    return u.Product(key, key, key, kind, F(1), price, price // 4, price * 4, 1, 0, handling)  # type: ignore[arg-type]


def recipe(trade: str, n: int, hours: int, inputs: dict[str, int]) -> u.Recipe:
    return u.Recipe(trade, n, hours, inputs, 0, F(0), F(0))


def hand_written(products: dict[str, u.Product], recipes: dict[str, u.Recipe]) -> u.Written:
    return u.Written(
        products=products,
        recipes=recipes,
        machine_price_micros=1_000_000,
        workers_per_machine={},
        machine_life_periods=100,
        wage_tax_bps=2000,
        operating_income_tax_bps=2000,
        fund_share_bps=0,
        import_bps={},
        batch_hours_lost={},
        demand_moved={},
        machines_worn=F(0),
    )


def hand_tiers(comfort: dict[str, int], luxury: dict[str, int]) -> t.Tiers:
    return t.Tiers(
        comfort=comfort,
        luxury=luxury,
        exact={},
        luxury_scale_bps={},
        no_earner_estimate={},
        residence_estimate={},
        reach={},
        demand_gap={},
        own_price_gap={},
        state_services={},
        country_services={},
        place_bodies={},
        share_by_part_bps={},
        place_grant_micros={},
    )


def hand_opening(
    trades: tuple[str, ...],
    imports: dict[str, Fraction],
    sources: dict[str, dict[str, Fraction]],
    exports: dict[str, Fraction],
) -> s.Opening:
    zero = {t_: F(0) for t_ in trades}
    quantities = s.Quantities(
        output=dict.fromkeys(trades, F(1)),
        coefficients={},
        hours_per_dollar=dict.fromkeys(trades, F(1)),
        hours=dict.fromkeys(trades, 0),
        wage=dict.fromkeys(trades, F(20)),
        unpaid_labor=zero,
        export_share={},
        imports={**zero, **imports},
        final={},
        machines=dict.fromkeys(trades, 0),
        import_sources=sources,
        import_buyers={},
        import_cover={},
        business_demand={},
        service_import_bps={},
        wages_abroad={},
    )
    prices = s.Prices(
        prices=dict.fromkeys(trades, F(1)),
        margins={},
        floored=frozenset(),
        equipment=F(0),
        rounds=1,
    )
    fields: dict[str, Any] = {
        "lam": F(0),
        "prices": prices,
        "quantities": quantities,
        "export_factor": F(0),
        "exports": exports,
        "import_prices": {},
        "import_saving": {},
        "shop_saving": {},
        "wear": {},
        "operating_income": {},
        "public_owned_income": F(0),
        "grant": F(0),
        "support": F(0),
        "benefits": F(0),
        "own_cost": {},
        "tax_rate": F(1, 5),
        "fund_share": F(0),
        "payout": F(0),
        "household_purchases": {},
        "shop_charge": F(0),
        "markup": F(0),
        "spending": F(0),
        "tier_unit": F(0),
        "tier_one": {},
        "bands": {},
        "kept": F(0),
        "balances": {},
        "tier_quantities": {},
    }
    return s.Opening(**fields)


def hand_census(abroad: dict[str, r.Region]) -> r.Census:
    return r.Census(
        trades={},
        households={},
        places=(),
        abroad=abroad,
        firm_assignment={},
        retail_assignment={},
        crossing_force={},
        workers_per_machine={},
        sha256="",
    )


def region(key: str, persons: int, households: int, employed: int, wage: int = 20 * M) -> r.Region:
    return r.Region(
        key, persons, households, employed * 2, employed, {"food": wage, "hs": wage, "shop": wage}
    )


FOOD_HS = replace(
    r.TWELVE,
    trades=("food", "hs", "shop"),
    product={"food": "food", "hs": "household_services"},
    storable=frozenset({"food"}),
    shop_trade="shop",
    public_trade=None,
    capital_trade="food",
    extraction_trade=None,
    shop_goods=frozenset({"food"}),
    person_needs=("food", "household_services"),
    household_needs=(),
    place_services=frozenset(),
)
FOOD_HS_SETTINGS = replace(
    r.Settings(),
    paying_order=("food", "household_services"),
    crossing=frozenset({"food"}),
)


def food_hs_written() -> u.Written:
    return hand_written(
        {
            "food": product("food", 1_000_000, "storable", (1, 10)),
            "household_services": product("household_services", 2_000_000, "service"),
        },
        {
            # 0.1 hour a unit, and a unit of care for every ten units of food.
            "food": recipe("food", 10, 1, {"household_services": 1}),
            "hs": recipe("hs", 5, 1, {}),  # 0.2 hour a unit
        },
    )


FOOD_HS_TIERS = hand_tiers(
    {"food": 2, "household_services": 1}, {"food": 3, "household_services": 2}
)
HS_HOURS = F(1, 5)
FOOD_HOURS = F(1, 10)


def food_hs_hours(mpp: int, persons: int = 100) -> Fraction:
    """The hours of the hand region at `mpp` in tier 1 only (food 3,000,000 a unit at its shop,
    care 2,000,000), worked here by hand."""
    money = F(mpp * persons)
    cap = 28 * persons
    f_food = min(F(cap), money / 3_000_000)
    f_hs = min(F(cap), (money - f_food * 3_000_000) / 2_000_000)
    y_hs = f_hs + f_food / 10
    return f_food * FOOD_HOURS + y_hs * HS_HOURS + f_food * FOOD_HOURS


def test_a_region_s_workers_are_needed() -> None:
    abroad = {"r1": region("r1", 100, 40, 5)}
    o = hand_opening(("food", "hs", "shop"), {}, {}, {})
    out = ab.regions(
        o,
        hand_census(abroad),
        food_hs_written(),
        FOOD_HS_TIERS,
        FOOD_HS_SETTINGS,
        FOOD_HS,
    )
    got = out["r1"]
    target = 5 * 160
    assert got.money_per_person_micros == 102_400_000
    assert food_hs_hours(got.money_per_person_micros) >= target
    assert food_hs_hours(got.money_per_person_micros - 1) < target
    # Food 280 hours, care 240, the shop 280: sorted trades are food, hs, shop.
    assert got.function_weights_bps == (3500, 3000, 3500)
    assert sum(got.function_weights_bps) == 10_000
    assert min(got.function_weights_bps) >= 1
    assert got.luxury_scale_bps is None
    assert got.sales_micros == 0
    assert got.purchases_micros == 0
    assert got.export_bps == {"food": 0}


def test_each_region_balances_by_construction() -> None:
    trades = ("food", "hs", "shop")
    abroad = {"r1": region("r1", 100, 40, 5), "r2": region("r2", 50, 20, 3)}
    o = hand_opening(
        trades,
        {"food": F(200)},
        {"food": {"r1": F(1, 2), "r2": F(1, 2)}},
        {"food": F(200)},
    )
    out = ab.regions(
        o, hand_census(abroad), food_hs_written(), FOOD_HS_TIERS, FOOD_HS_SETTINGS, FOOD_HS
    )
    for key in ("r1", "r2"):
        got = out[key]
        assert got.sales_micros == 100 * M  # 100 units at the region's own price of 1,000,000
        assert abs(got.purchases_micros - got.sales_micros) <= 100  # one micro a unit bought
    bought = sum((out[k].buys_units["food"] for k in out), F(0))
    assert abs(bought - 200) < F(1, 1000)
    # The smaller region is requires less, so it takes a larger share of it.
    assert out["r2"].export_bps["food"] > out["r1"].export_bps["food"]


def test_an_impossible_region_is_refused() -> None:
    # Ten employed (1,600 hours) that make 10,000 units of food at an hour a unit.
    written = hand_written(
        {
            "food": product("food", 1_000_000, "storable", (1, 10)),
            "household_services": product("household_services", 2_000_000, "service"),
        },
        {"food": recipe("food", 1, 1, {}), "hs": recipe("hs", 5, 1, {})},
    )
    o = hand_opening(
        ("food", "hs", "shop"), {"food": F(10_000)}, {"food": {"r1": F(1)}}, {"food": F(10_000)}
    )
    with pytest.raises(ReferenceBuildError, match=r"^abroad_unbalanced: r1$"):
        ab.regions(
            o,
            hand_census({"r1": region("r1", 100, 40, 10)}),
            written,
            FOOD_HS_TIERS,
            FOOD_HS_SETTINGS,
            FOOD_HS,
        )


def test_weights_are_whole_and_positive() -> None:
    got = ab.function_weights({"a": F(2), "b": F(0), "c": F(1)}, ["a", "b", "c"])
    assert got == (6666, 1, 3333)
    assert sum(got) == 10_000
    with pytest.raises(ReferenceBuildError, match=r"^abroad_unbalanced"):
        ab.function_weights({}, ["a"])


def test_the_weights_follow_the_policy_order() -> None:
    assert sorted(r.TRADES) == [
        "business_services",
        "capital_goods",
        "construction_housing",
        "consumer_goods",
        "distribution_transport",
        "energy_utilities",
        "extraction",
        "food",
        "household_services",
        "leisure_hospitality",
        "manufacturing",
        "public_provisioning",
    ]


def opening_row(key: str, scale: int | None) -> ab.RegionOpening:
    return ab.RegionOpening(key, (1,) * 12, {}, 0, 0, 0, scale)


def test_a_scale_abroad_is_written_where_the_compiler_admits_it() -> None:
    rows = ab.scale_rows(
        {"canada": opening_row("canada", 12_500), "dependency": opening_row("dependency", 11_000)}
    )
    assert rows == {
        "016:pooled-external": 11_000,
        "316:pooled-external": 11_000,
        "580:pooled-external": 11_000,
        "581:pooled-external": 11_000,
        "630:pooled-external": 11_000,
        "850:pooled-external": 11_000,
        "canada:pooled-external": 12_500,
    }
    assert ab.scale_rows({"china": opening_row("china", None)}) == {}


def test_a_region_past_its_three_tiers_has_a_scale() -> None:
    o = hand_opening(("food", "hs", "shop"), {}, {}, {})
    out = ab.regions(
        o,
        hand_census({"r1": region("r1", 100, 40, 40)}),
        food_hs_written(),
        FOOD_HS_TIERS,
        FOOD_HS_SETTINGS,
        FOOD_HS,
    )
    got = out["r1"]
    mpp = got.money_per_person_micros
    # Tier 1 140M, tier 2 8M, tier 3 13M a person at 3,000,000 and 2,000,000 a unit.
    assert got.luxury_scale_bps == (10_000 * (mpp - 148 * M)) // (13 * M)
    assert got.luxury_scale_bps is not None
    assert got.luxury_scale_bps > 10_000
    assert got.reach[2] == 1


def test_a_scale_past_the_compilers_bound_is_refused() -> None:
    o = hand_opening(("food", "hs", "shop"), {}, {}, {})
    with pytest.raises(ReferenceBuildError, match=r"^luxury_scale_bound: r1$"):
        ab.regions(
            o,
            hand_census({"r1": region("r1", 100, 40, 100_000)}),
            food_hs_written(),
            FOOD_HS_TIERS,
            FOOD_HS_SETTINGS,
            FOOD_HS,
        )


# ---- business services cross between businesses only (ruling 2, E2) -----------------------
# Food (a shop good) whose makers buy 3 units of business services for every 28 units; ten
# people whose households want 20 units of business services in tier 2 and, at the money that
# makes their workers needed, buy 10 (the second 10 keeps the closure off a knife edge).

BS_ECONOMY = replace(
    FOOD_HS,
    trades=("food", "business_services", "shop"),
    product={"food": "food", "business_services": "business_services"},
    person_needs=("food",),
    capital_trade="food",
)
BS_SETTINGS = replace(
    r.Settings(),
    paying_order=("food", "business_services"),
    crossing=frozenset({"business_services"}),
)
BS_TIERS = hand_tiers({"business_services": 2}, {})
BS_TRADES = ("food", "business_services", "shop")


def bs_written() -> u.Written:
    return hand_written(
        {
            "food": product("food", 1_000_000, "storable", (1, 10)),
            "business_services": product("business_services", 4_000_000, "service"),
        },
        {
            "food": recipe("food", 28, 2, {"business_services": 3}),
            "business_services": recipe("business_services", 5, 14, {}),
        },
    )


def bs_region(key: str, employed: int = 1) -> r.Region:
    wages = {"food": 20 * M, "business_services": 20 * M, "shop": 20 * M}
    return r.Region(key, 10, 4, employed * 2, employed, wages)


def test_a_region_buys_business_services_for_its_businesses_only() -> None:
    """Its sites need 30 units, its households 10: R is 30 and the households' 10 are made by its
    own workers. It sells 6 and the country takes 6, so it buys 6, a share of 2,000."""
    o = hand_opening(
        BS_TRADES,
        {"business_services": F(6)},
        {"business_services": {"r1": F(1)}},
        {"business_services": F(6)},
    )
    out = ab.regions(
        o, hand_census({"r1": bs_region("r1")}), bs_written(), BS_TIERS, BS_SETTINGS, BS_ECONOMY
    )
    got = out["r1"]
    assert got.export_bps == {"business_services": 2000}
    assert abs(got.buys_units["business_services"] - 6) < F(1, 1000)
    # Food 280 hours of 2/28, business services 40 units of 14/5, the shop 28: 160 hours at 88M.
    assert abs(got.money_per_person_micros - 88_000_000) <= 1
    assert got.sales_micros == 24 * M
    assert abs(got.purchases_micros - 24 * M) <= 6


def test_a_region_s_business_services_sales_follow_the_census() -> None:
    economy = BS_ECONOMY
    census = replace(
        hand_census({"r1": bs_region("r1"), "r2": bs_region("r2")}),
        crossing_force={
            ("business_services", "r1", "food"): 3,
            ("business_services", "r2", "food"): 1,
        },
    )
    weights, _ = s._imports_of_service(
        "business_services",
        "business_services",
        census,
        {"business_services": {"food": F(1, 10)}},
        {"food": F(1)},
        BS_SETTINGS,
        economy,
    )
    sigma = s._shares_on_grid(weights)
    o = hand_opening(
        BS_TRADES,
        {"business_services": F(40)},
        {"business_services": sigma},
        {"business_services": F(40)},
    )
    out = ab.regions(
        o,
        hand_census({"r1": bs_region("r1"), "r2": bs_region("r2")}),
        bs_written(),
        BS_TIERS,
        BS_SETTINGS,
        economy,
    )
    assert out["r1"].sells_units == {"business_services": 30}
    assert out["r2"].sells_units == {"business_services": 10}
    assert out["r1"].export_bps == {"business_services": 10_000}
    assert out["r2"].export_bps == {"business_services": 3333}


def test_a_share_above_the_whole_is_refused() -> None:
    o = hand_opening(
        BS_TRADES,
        {"business_services": F(36)},
        {"business_services": {"r1": F(1)}},
        {"business_services": F(36)},
    )
    with pytest.raises(ReferenceBuildError, match=r"^export_share: r1/business_services$"):
        ab.regions(
            o, hand_census({"r1": bs_region("r1")}), bs_written(), BS_TIERS, BS_SETTINGS, BS_ECONOMY
        )


# ---- hygiene ---------------------------------------------------------------------------


def test_no_float_in_the_module() -> None:
    tree = ast.parse((ROOT / "tools/national_opening_abroad.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            assert not isinstance(node.value, float), node.lineno
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"float", "round"}, node.lineno
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = [a.name for a in node.names] + [getattr(node, "module", None) or ""]
            assert "statistics" not in names
            assert "math" not in names


# ---- the committed tables (slow) -------------------------------------------------------


def fixture_facts() -> u.TemplateFacts:
    commodities = tomllib.loads(FIXTURE.read_text(encoding="utf-8"))["commodity"]
    labels: dict[str, tuple[str, str]] = {}
    grams: dict[str, int] = {}
    prices: dict[str, int] = {}
    for key, row_ in commodities.items():
        if "opening_price_micros" not in row_:
            continue
        labels[key] = (row_["label"], row_["unit_label"])
        grams[key] = row_["grams_per_unit"]
        prices[key] = row_["opening_price_micros"]
    return u.TemplateFacts(labels=labels, grams=grams, prices=prices)


@pytest.fixture(scope="module")
def committed() -> tuple[s.Opening, u.Written, r.Census, t.Tiers, dict[str, ab.RegionOpening]]:
    settings = r.Settings()
    cut = r.recut(r.read_accounts(ACCOUNTS), settings)
    census = r.read_census(CENSUS)
    opening = s.solve(cut, census, settings)
    written = u.written(opening, cut, census, settings, fixture_facts())
    tiers = t.tiers(opening, census, written, settings)
    regions = dict(ab.regions(opening, census, written, tiers, settings))
    return opening, written, census, tiers, regions


def fixed(value: Fraction, places: int = 4) -> str:
    """A fraction as a decimal string (a float would be a defect; so would printing its digits)."""
    scaled = (abs(value) * 10**places).__floor__()
    return f"{'-' if value < 0 else ''}{scaled // 10**places}.{scaled % 10**places:0{places}d}"


def percent(part: Fraction, whole: Fraction) -> str:
    scaled = (abs(part / whole) * 10_000).__floor__() if whole else 0
    return f"{scaled // 100}.{scaled % 100:02d}%"


@pytest.mark.slow
def test_the_nation_balances_by_the_regions(committed: Any) -> None:
    """The country's exports at its written prices equal its imports at the regions' prices,
    within 1% (the rounding of shares and of prices to micros)."""
    _, _, _, _, regions = committed
    sales = sum(x.sales_micros for x in regions.values())
    purchases = sum(x.purchases_micros for x in regions.values())
    written = sum(x.purchases_written_micros for x in regions.values())
    print(  # noqa: T201
        f"imports {sales} micros, exports at exact shares {purchases}, "
        f"exports at written shares {written}"
    )
    assert sales > 0
    # The written shares (basis points, as the compiler applies them), not the exact solve.
    assert abs(written - sales) * 100 <= sales


@pytest.mark.slow
def test_every_region_balances(committed: Any) -> None:
    _, _, _, _, regions = committed
    for key, x in sorted(regions.items()):
        print(  # noqa: T201
            f"{key}: rounds {x.rounds}, mpp {x.money_per_person_micros}, "
            f"sales {x.sales_micros}, purchases {x.purchases_micros}, "
            f"written {x.purchases_written_micros}, "
            f"scale {x.luxury_scale_bps}, reach {[percent(v, F(1)) for v in x.reach]}"
        )
        print(f"  weights {x.function_weights_bps}, shares {dict(x.export_bps)}")  # noqa: T201
        assert abs(x.purchases_micros - x.sales_micros) * 100 <= max(x.sales_micros, 1), key
        assert sum(x.function_weights_bps) == 10_000
        assert min(x.function_weights_bps) >= 1
        assert max(x.export_bps.values()) <= 10_000


@pytest.mark.slow
def test_the_regions_take_the_exports_and_need_their_workers(committed: Any) -> None:
    opening, written, census, _, regions = committed
    for trade, exported in sorted(opening.exports.items()):
        if exported == 0:
            continue
        product_key = r.TWELVE.product[trade]
        units = exported / written.products[product_key].dollars_per_unit
        taken = sum((x.buys_units[product_key] for x in regions.values()), F(0))
        print(f"{product_key}: exports {fixed(units)}, regions take {fixed(taken)}")  # noqa: T201
        assert abs(taken - units) * 1000 <= units
    services = opening.exports.get("business_services", F(0))
    over = services / opening.quantities.output["business_services"]
    print(f"business services exports over output: {percent(over, F(1))}")  # noqa: T201
    assert set(regions) == set(census.abroad)
