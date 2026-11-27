"""Task 10b: units, whole-number recipes, written prices, handling blocks and a region's prices."""

from __future__ import annotations

import ast
import math
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
import national_opening_recut as r  # type: ignore[import-not-found]  # noqa: E402
import national_opening_solve as s  # type: ignore[import-not-found]  # noqa: E402
import national_opening_units as u  # type: ignore[import-not-found]  # noqa: E402

ReferenceBuildError = county.ReferenceBuildError
F = Fraction
ECONOMY_DIR = ROOT / "src/babylon/data/reference/economy"
ACCOUNTS = ECONOMY_DIR / "national_trade_accounts_2024.csv.gz"
CENSUS = ECONOMY_DIR / "national_opening_census_v13.json.gz"
FIXTURE = (
    ROOT / "rust/crates/babylon-persistence/tests/fixtures/national_twelve_trades.defines.toml"
)


# ---- the recipe's batch ------------------------------------------------------------


def never_worn(_hours: int) -> Fraction:
    return F(0)


HALF = {"i": F(1, 2)}


def test_a_recipe_takes_the_smallest_batch_within_half_a_percent() -> None:
    recipe = u.batch(
        "t", F(7, 1000), {"i": F(1, 3)}, 20_000_000, {"i": 2_000_000}, 1_000_000, never_worn, HALF
    )
    assert recipe.output_units_per_batch == 1000
    assert recipe.labor_hours_per_batch == 7
    assert recipe.inputs == {"i": 333}
    assert recipe.exact_cost_micros == F(2_420_000_000, 3000)
    assert recipe.rounded_cost_micros == 806_000
    assert abs(recipe.rounded_cost_micros / recipe.exact_cost_micros - 1) < F(1, 1000)


def test_the_batches_before_it_are_the_errors_the_task_names() -> None:
    exact = F(121, 150) * 10**6
    for hours, count, n, low, high in (
        (3, 133, 400, F(103, 10_000), F(104, 10_000)),
        (6, 267, 800, F(134, 10_000), F(135, 10_000)),
    ):
        cost = F(20_000_000 * hours + count * 2_000_000, n)
        assert low < (cost - exact) / exact < high, n


def test_a_recipe_under_cost_is_refused() -> None:
    with pytest.raises(ReferenceBuildError, match=r"^recipe_rounding: t"):
        u.batch(
            "t", F(7, 1000), {"i": F(1, 3)}, 20_000_000, {"i": 2_000_000}, 805_860, never_worn, HALF
        )


def test_a_trade_that_cannot_round_is_refused() -> None:
    with pytest.raises(ReferenceBuildError, match=r"^recipe_rounding: t"):
        u.batch(
            "t",
            F(7, 1000),
            {"i": F(1, 10**7)},
            20_000_000,
            {"i": 2_000_000},
            10**9,
            never_worn,
            HALF,
        )


def test_wear_is_part_of_the_refusal() -> None:
    # 1,000,000 a unit covers 806,000 a unit; wear a batch of 10^12 micros is more than any batch earns.
    ok = u.batch(
        "t", F(7, 1000), {"i": F(1, 3)}, 20_000_000, {"i": 2_000_000}, 1_000_000, never_worn, HALF
    )
    assert ok.output_units_per_batch == 1000
    with pytest.raises(ReferenceBuildError, match=r"^recipe_rounding: t"):
        u.batch(
            "t",
            F(7, 1000),
            {"i": F(1, 3)},
            20_000_000,
            {"i": 2_000_000},
            1_000_000,
            lambda _hours: F(10**12),
            HALF,
        )


def test_a_batch_waits_for_its_hours() -> None:
    recipe = u.batch(
        "t",
        F(1, 300),
        {"i": F(1)},
        30_000_000,
        {"i": 10_000_000},
        20_000_000,
        never_worn,
        {"i": F(0)},
    )
    assert (recipe.output_units_per_batch, recipe.labor_hours_per_batch) == (50_000, 167)
    assert recipe.inputs == {"i": 50_000}


def test_a_batch_waits_for_its_supplier() -> None:
    def pick(share: Fraction) -> tuple[int, int, int]:
        recipe = u.batch(
            "t",
            F(1, 10),
            {"i": F(3, 1000)},
            20_000_000,
            {"i": 1_000_000},
            5_000_000,
            never_worn,
            {"i": share},
        )
        return recipe.output_units_per_batch, recipe.labor_hours_per_batch, recipe.inputs["i"]

    assert pick(F(1, 2)) == (1000, 100, 3)
    assert pick(F(1, 1000)) == (200, 20, 1)


def test_a_use_of_a_product_with_no_makers_is_refused() -> None:
    with pytest.raises(ReferenceBuildError, match=r"^recipe_demand: i"):
        u.batch(
            "t", F(1, 10), {"i": F(1, 100)}, 20_000_000, {"i": 10**6}, 5_000_000, never_worn, {}
        )


def test_a_machine_s_life_is_its_workers_hours() -> None:
    assert u.machine_life_batches(160, 4, 100, 16) == 4000
    assert u.machine_life_batches(160, 4, 100, 126) == 508
    assert u.machine_life_batches(160, 4, 100, 7724) == 8
    assert u.machine_life_batches(160, 4, 100, 100_000) == 1
    assert u.machine_life_batches(160, 40, 100, 410) == 1561


def test_recipes_that_move_a_product_are_refused() -> None:
    def moved(errors: list[F]) -> dict[str, F]:
        """Six buying trades, each with 1/6 of product `p`'s output, each input off by `error`."""
        recipes = {}
        exact = {}
        shares = {}
        for index, error in enumerate(errors):
            trade = f"t{index}"
            recipes[trade] = u.Recipe(trade, 1, 1, {"p": int(1000 * (1 + error))}, 0, F(1), F(1))
            exact[trade] = {"p": F(1000)}
            shares[trade] = {"p": F(1, 6)}
        return u.moved_demand(recipes, exact, shares)

    six = F(6, 1000)
    with pytest.raises(ReferenceBuildError, match=r"^recipe_demand: p"):
        moved([six] * 6)
    assert moved([six] * 5 + [F(0)])["p"] == F(5, 1000)


def test_machines_worn_that_cost_more_than_the_money_are_refused() -> None:
    price = 2_000_000_000  # micros: $2,000
    equipment = F(1_000_000)  # worn: 500 machines
    u.check_machine_wear(F(500), price, equipment)
    u.check_machine_wear(F(5025, 10), price, equipment)  # exactly 1/200 over
    with pytest.raises(ReferenceBuildError, match=r"^machine_wear"):
        u.check_machine_wear(F(505), price, equipment)  # 1% over
    with pytest.raises(ReferenceBuildError, match=r"^machine_wear"):
        u.check_machine_wear(F(495), price, equipment)  # 1% under


def test_a_block_takes_the_fewest_units_within_half_a_percent() -> None:
    assert u.handling_block(F(7, 60)) == (5, 43)
    with pytest.raises(ReferenceBuildError, match=r"^handling_rounding"):
        u.handling_block(F(1, 3000))


# ---- a hand world ------------------------------------------------------------------

FOOD, EXT, ENERGY, CAP, HOUSE, HS, BS, LEIS, PUB, SHOP = (
    "food",
    "extraction",
    "energy_utilities",
    "capital_goods",
    "construction_housing",
    "household_services",
    "business_services",
    "leisure_hospitality",
    "public_provisioning",
    "distribution_transport",
)
TRADES = (FOOD, EXT, ENERGY, CAP, HOUSE, HS, BS, LEIS, PUB, SHOP)
PRODUCT = {
    FOOD: "food",
    EXT: "resources",
    ENERGY: "utility",
    CAP: "equipment",
    HOUSE: "housing",
    HS: "household_services",
    BS: "business_services",
    LEIS: "leisure",
    PUB: "public_provision",
}
ECONOMY = r.Economy(
    trades=TRADES,
    product=PRODUCT,
    storable=frozenset({"food", "resources", "equipment"}),
    shop_trade=SHOP,
    public_trade=PUB,
    capital_trade=CAP,
    extraction_trade=EXT,
    shop_goods=frozenset({"food"}),
    person_needs=("food", "utility", "household_services"),
    household_needs=("housing",),
    place_services=frozenset({"housing", "household_services", "public_provision"}),
)
SETTINGS = replace(
    r.Settings(),
    service_stage={
        "utility": 1,
        "business_services": 1,
        "housing": 1,
        "household_services": 2,
        "leisure": 2,
        "public_provision": 2,
    },
    paying_order=(
        "food",
        "utility",
        "housing",
        "business_services",
        "household_services",
        "leisure",
        "resources",
    ),
    crossing=frozenset({"food", "resources", "equipment", "business_services"}),
    country_services=frozenset({"business_services", "leisure", "utility"}),
    workers_per_machine={t: 4 for t in TRADES if t != SHOP},
)
MACHINES = {FOOD: 10, EXT: 5, ENERGY: 5, CAP: 5, HOUSE: 5, HS: 10, BS: 3, LEIS: 2, PUB: 5, SHOP: 0}
FACTS = u.TemplateFacts(
    labels={
        "business_services": ("Business support", "business service unit"),
        "leisure": ("Leisure and hospitality", "person-period leisure"),
        "public_provision": ("Public provisioning", "person-period provision"),
    },
    grams={"food": 14000, "resources": 10000, "equipment": 250000},
    prices={"food": 280_000_000, "resources": 40_000_000, "equipment": 4_000_000_000},
)


def hand_census() -> r.Census:
    trade = r.TradeCount(0, 0, 0, 0, 0, 10, 0, 0, 0)
    return r.Census(
        trades={t: replace(trade, machines=MACHINES[t]) for t in TRADES},
        households={"earning_owner": r.KeyCount(1, 400, 1000, 500, 0, 0)},
        places=(),
        abroad={},
        firm_assignment={},
        retail_assignment={},
        crossing_force={},
        workers_per_machine={},
        sha256="",
    )


def hand_opening(**more: Any) -> s.Opening:
    h = {t: F(1, 100) for t in TRADES}
    h[EXT] = F(1, 40)
    output = {t: F(1000) for t in TRADES}
    a = {
        ENERGY: {FOOD: F(1, 20), HS: F(1, 20)},
        BS: {FOOD: F(1, 50)},
        EXT: {CAP: F(1, 10)},
    }
    q = s.Quantities(
        output=output,
        coefficients=a,
        hours_per_dollar=h,
        hours={t: h[t] * output[t] for t in TRADES},
        wage={t: F(20) for t in TRADES} | {HS: F(25)},
        unpaid_labor={t: F(0) for t in TRADES},
        export_share={},
        imports={t: F(0) for t in TRADES},
        final={},
        machines=MACHINES,
        import_sources={},
        import_buyers={},
        import_cover={FOOD: F(2345, 10_000), EXT: F(1, 10), CAP: F(4104, 10_000)},
        business_demand={},
        service_import_bps={BS: 1234},
        wages_abroad={},
    )
    private = [t for t in TRADES if t in PRODUCT and t != PUB]
    prices = s.Prices(
        prices={t: F(1) for t in private},
        margins={t: F(1, 10) for t in private} | {FOOD: F(12344, 100_000), EXT: F(12344, 100_000)},
        floored=frozenset({EXT}),
        equipment=F(1000),
        rounds=1,
    )
    fields: dict[str, Any] = {
        "lam": F(0),
        "prices": prices,
        "quantities": q,
        "export_factor": F(0),
        "exports": {},
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
        "tax_rate": F(123_456, 1_000_000),
        "fund_share": F(27, 100),
        "payout": F(0),
        "household_purchases": {},
        "shop_charge": F(0),
        "markup": F(1, 100),
        "spending": F(0),
        "tier_unit": F(0),
        "tier_one": {},
        "bands": {},
        "kept": F(0),
        "balances": {},
        "tier_quantities": {
            "food": F(28 * 280),
            "utility": F(28 * 75),
            "household_services": F(28 * 600),
            "housing": F(28 * 1450),
        },
    }
    fields.update(more)
    return s.Opening(**fields)


def hand_written(o: s.Opening | None = None) -> u.Written:
    return u.written(
        o or hand_opening(),
        r.Recut({}, {}, {}, F(0), {}, {}, {}, {}, {}, {}, {}),
        hand_census(),
        SETTINGS,
        FACTS,
        ECONOMY,
    )


def test_prices_and_their_bounds_follow_the_fixture_ratios() -> None:
    assert u.bounds(280_000_000, "food") == (70_000_000, 1_120_000_000, 7_000_000)
    with pytest.raises(ReferenceBuildError, match=r"^price_zero: food"):
        u.bounds(39, "food")
    w = hand_written()
    food = w.products["food"]
    assert (food.price_micros, food.minimum_micros, food.maximum_micros, food.step_micros) == (
        280_000_000,
        70_000_000,
        1_120_000_000,
        7_000_000,
    )
    tiny = hand_opening(
        tier_quantities={
            "food": F(28 * 39, 10**6),
            "utility": F(2100),
            "household_services": F(16800),
            "housing": F(40600),
        }
    )
    with pytest.raises(ReferenceBuildError, match=r"^price_zero: "):
        hand_written(tiny)


def test_tier_one_holds_28_of_each_need() -> None:
    o = hand_opening()
    w = hand_written(o)
    for need in ("food", "utility", "household_services", "housing"):
        made = w.products[need]
        assert o.tier_quantities[need] / made.dollars_per_unit == 28
    assert w.products["food"].price_micros * 28 == 28 * 280_000_000
    assert w.products["household_services"].price_micros == 600_000_000
    assert w.products["housing"].price_micros == 1_450_000_000


def test_the_other_units_follow_their_rules() -> None:
    w = hand_written()
    # A day's food in producer value (p = 1 everywhere): the same price in micros.
    for product in ("business_services", "leisure"):
        assert w.products[product].dollars_per_unit == 280
        assert w.products[product].price_micros == 280_000_000
    # Resources: a minute of extraction's output, 1 / (60 h) = 40 / 60 accounts dollars.
    assert w.products["resources"].dollars_per_unit == F(2, 3)
    # One machine: E / p x life / NU, NU = 105 / 640 (hours at work over 160 x 4 a machine).
    assert w.products["equipment"].dollars_per_unit == F(1000 * 100 * 640, 105)
    assert w.machine_price_micros == half_up_micros(F(1000 * 100 * 640, 105))
    # Public provision: its output over the domestic persons, at the fee.
    assert w.products["public_provision"].dollars_per_unit == 1
    assert w.products["public_provision"].price_micros == 1_000_000


def half_up_micros(dollars: Fraction) -> int:
    return u.half_up(dollars * s.MICROS)


def test_the_machine_is_sized_by_the_machines_in_use() -> None:
    q = hand_opening().quantities
    two = replace(
        q,
        hours={FOOD: 6400, CAP: 64000},
        machines={FOOD: 11, CAP: 11},
    )
    o = replace(
        hand_opening(),
        quantities=two,
        prices=replace(
            hand_opening().prices,
            equipment=F(1100),
            prices={**hand_opening().prices.prices, CAP: F(1, 2)},
        ),
    )
    settings = replace(SETTINGS, workers_per_machine={FOOD: 4, CAP: 40})
    assert u.machines_in_use(o, settings) == 20
    units = u._units(o, 1, settings, ECONOMY)
    assert units["equipment"] == 11_000
    more = replace(o, quantities=replace(two, machines={FOOD: 1, CAP: 99}))
    assert u._units(more, 1, settings, ECONOMY)["equipment"] == 11_000


def test_grams_follow_value() -> None:
    w = hand_written()
    assert w.products["food"].grams_per_unit == 14000
    twice = hand_opening(
        tier_quantities={
            "food": F(2 * 28 * 280),
            "utility": F(2100),
            "household_services": F(16800),
            "housing": F(40600),
        }
    )
    assert hand_written(twice).products["food"].grams_per_unit == 28000
    assert u.deposit_grams(w) == w.products["resources"].grams_per_unit
    assert w.products["utility"].grams_per_unit == 0


def test_a_crossing_service_s_share_is_over_its_business_buyers() -> None:
    w = hand_written()
    assert w.import_bps["business_services"] == 1234
    assert set(w.import_bps) == {"food", "resources", "equipment", "business_services"}
    assert w.import_bps["food"] == 2345
    assert w.import_bps["equipment"] == 4104
    o = hand_opening()
    bad = replace(o, quantities=replace(o.quantities, service_import_bps={BS: 10_001}))
    with pytest.raises(ReferenceBuildError, match=r"^import_coverage: business_services"):
        hand_written(bad)


def test_the_kinds_follow_the_stages() -> None:
    w = hand_written()
    kinds = {k: p.kind for k, p in w.products.items()}
    assert kinds["utility"] == kinds["business_services"] == kinds["housing"] == "utility"
    assert kinds["household_services"] == kinds["leisure"] == kinds["public_provision"] == "service"
    assert kinds["food"] == kinds["resources"] == kinds["equipment"] == "storable"


def test_the_written_rates_and_margins_round_by_their_rules() -> None:
    w = hand_written()
    assert w.wage_tax_bps == w.operating_income_tax_bps == 1235  # 1234.56 half up
    assert w.fund_share_bps == 2700
    assert w.recipes[FOOD].margin_bps == 1234  # 1234.4 half up, off the floor
    assert w.recipes[EXT].margin_bps == 1235  # 1234.4 up, on the floor
    assert w.recipes[PUB].margin_bps is None
    assert w.recipes[EXT].inputs["resource_deposit"] == w.recipes[EXT].output_units_per_batch


def test_every_recipe_is_whole_and_close() -> None:
    w = hand_written()
    assert set(w.recipes) == set(TRADES) - {SHOP}
    for recipe in w.recipes.values():
        assert recipe.labor_hours_per_batch >= 1
        assert all(count >= 1 for count in recipe.inputs.values())
        error = (
            abs(recipe.rounded_cost_micros - recipe.exact_cost_micros) / recipe.exact_cost_micros
        )
        assert error <= F(1, 100), recipe.trade
    food = w.recipes[FOOD]
    assert set(food.inputs) == {"utility", "business_services"}
    assert (
        w.batch_hours_lost[FOOD] == F(10 * food.labor_hours_per_batch, 2) / 10
    )  # sites 10, hours 10


def test_the_shop_handles_what_households_buy() -> None:
    w = hand_written()
    hours, units = w.products["food"].handling or (0, 0)
    exact = F(1, 100) * 280 / 20  # rho x p u / shop wage
    assert hours >= 1 and abs(F(hours, units) - exact) <= exact / 200
    assert all(p.handling is None for k, p in w.products.items() if k != "food")


def test_a_region_s_prices_follow_its_wage() -> None:
    o = hand_opening()
    w = hand_written(o)
    census = hand_census()
    national = {t: u.half_up(o.quantities.wage[t] * s.MICROS) for t in TRADES}
    region = dict(national)
    region[HS] = national[HS] // 2
    region[SHOP] = 10_000_000
    makers = u.region_maker_prices(w, o, region, ECONOMY)
    recipe = w.recipes[HS]
    expected = w.products["household_services"].price_micros + (
        (region[HS] - national[HS])
        * recipe.labor_hours_per_batch
        * (10_000 + (recipe.margin_bps or 0))
        // (10_000 * recipe.output_units_per_batch)
    )
    assert makers["household_services"] == expected < w.products["household_services"].price_micros
    assert makers["public_provision"] == 1_000_000
    # A shop good, with and without the share sold to the region (E7's estimate).
    hours, units = w.products["food"].handling or (0, 1)
    charge = math.ceil(F(hours * region[SHOP], units))
    plain = u.region_prices(w, o, region, census, None, ECONOMY)
    assert plain["food"] == w.products["food"].price_micros + charge
    shared = u.region_prices(w, o, region, census, {"food": 2000}, ECONOMY)
    assert (
        shared["food"]
        == u.shop_estimate(makers["food"], w.products["food"].price_micros, 2000) + charge
    )
    assert shared["household_services"] == makers["household_services"]


def test_a_shop_abroad_pays_the_estimate() -> None:
    assert u.shop_estimate(600_001, 1_000_000, 2000) == 680_001


# ---- the committed tables (slow) ---------------------------------------------------


def fixture_facts() -> u.TemplateFacts:
    commodities = tomllib.loads(FIXTURE.read_text(encoding="utf-8"))["commodity"]
    labels: dict[str, tuple[str, str]] = {}
    grams: dict[str, int] = {}
    prices: dict[str, int] = {}
    for key, row in commodities.items():
        if "opening_price_micros" not in row:
            continue
        labels[key] = (row["label"], row["unit_label"])
        grams[key] = row["grams_per_unit"]
        prices[key] = row["opening_price_micros"]
    return u.TemplateFacts(labels=labels, grams=grams, prices=prices)


@pytest.fixture(scope="module")
def committed() -> tuple[r.Recut, r.Census, r.Settings, s.Opening, u.Written]:
    settings = r.Settings()
    cut = r.recut(r.read_accounts(ACCOUNTS), settings)
    census = r.read_census(CENSUS)
    opening = s.solve(cut, census, settings)
    return (
        cut,
        census,
        settings,
        opening,
        u.written(opening, cut, census, settings, fixture_facts()),
    )


@pytest.mark.slow
def test_rounded_recipes_keep_three_sides(committed: Any) -> None:
    cut, _, settings, o, w = committed
    q = o.quantities
    machine = w.machine_price_micros
    hpp = settings.work_hours_per_person
    lines = []
    for trade, recipe in w.recipes.items():
        product = w.products[r.TWELVE.product[trade]]
        error = (
            abs(recipe.rounded_cost_micros - recipe.exact_cost_micros) / recipe.exact_cost_micros
        )
        hours = recipe.labor_hours_per_batch
        n = recipe.output_units_per_batch
        hours_error = abs(F(hours) / (q.hours_per_dollar[trade] * product.dollars_per_unit * n) - 1)
        assert error <= F(1, 200), trade
        assert hours_error <= F(1, 400), trade
        assert all(count > 0 for count in recipe.inputs.values()), trade
        life = u.machine_life_batches(
            hpp, w.workers_per_machine[trade], w.machine_life_periods, hours
        )
        if trade != r.TWELVE.public_trade:
            wage = u.half_up(q.wage[trade] * s.MICROS)
            cost = wage * hours + F(machine, life)
            for good, count in recipe.inputs.items():
                if good in w.products:
                    cost += count * w.products[good].price_micros
            assert product.price_micros * n >= cost, trade
        lines.append(
            f"{trade}: n={n} L={hours} life_batches={life} "
            f"cost_error_ppm={(error * 10**6).__floor__()} "
            f"hours_error_ppm={(hours_error * 10**6).__floor__()} "
            f"lost={(w.batch_hours_lost[trade] * 10**6).__floor__()}ppm"
        )
    assert all(abs(moved) <= F(1, 200) for moved in w.demand_moved.values())
    in_use = u.machines_in_use(o, settings)
    cost = w.machines_worn * machine / s.MICROS
    assert abs(cost / o.prices.equipment - 1) <= F(1, 200)
    lines.append(
        f"demand_moved_ppm={ {k: (v * 10**6).__floor__() for k, v in sorted(w.demand_moved.items())} }"
    )
    lines.append(
        f"machine_price_micros={machine} in_use={in_use} worn={w.machines_worn} "
        f"cost={cost} equipment={o.prices.equipment} ratio_ppm={(cost / o.prices.equipment * 10**6).__floor__()}"
    )
    lines.append(f"kinds={ {k: p.kind for k, p in sorted(w.products.items())} }")
    print("\n".join(lines))  # noqa: T201


@pytest.mark.slow
def test_handling_blocks_are_close(committed: Any) -> None:
    _, _, _, o, w = committed
    shop = r.TWELVE.shop_trade
    assert shop is not None
    for good in sorted(r.TWELVE.shop_goods):
        made = w.products[good]
        assert made.handling is not None
        hours, units = made.handling
        trade = next(t for t, p in r.TWELVE.product.items() if p == good)
        exact = o.markup * o.prices.prices[trade] * made.dollars_per_unit / o.quantities.wage[shop]
        assert abs(F(hours, units) - exact) <= exact / 200, good
        print(good, hours, units, (exact * 10**6).__floor__())  # noqa: T201


@pytest.mark.slow
def test_the_import_shares_written_meet_the_accounts(committed: Any) -> None:
    cut, _, settings, o, w = committed
    q = o.quantities
    assert set(w.import_bps) == {
        "food",
        "resources",
        "materials",
        "consumer_goods",
        "equipment",
        "business_services",
    }
    for product, bps in w.import_bps.items():
        trade = next(t for t, p in r.TWELVE.product.items() if p == product)
        if product == "business_services":
            assert abs(F(bps, 10_000) - q.imports[trade] / q.business_demand[trade]) <= F(1, 10_000)
            continue
        cover = q.import_cover[trade]
        # import_bps x foreign weight / total weight = IMP: the weights' ratio is IMP / cover.
        implied = F(bps, 10_000) * cut.import_share[trade] / cover
        assert abs(implied - cut.import_share[trade]) <= F(1, 10_000), product
    print(w.import_bps, settings.crossing == frozenset(w.import_bps))  # noqa: T201


def test_no_float_in_the_module() -> None:
    tree = ast.parse((ROOT / "tools/national_opening_units.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            assert not isinstance(node.value, float), node.lineno
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"float", "round"}, node.lineno
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = [a.name for a in node.names] + [getattr(node, "module", None) or ""]
            assert "statistics" not in names
