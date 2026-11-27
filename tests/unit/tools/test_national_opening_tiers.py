"""Task 11: each place's accounts, the tiers, the benefit and each part's body."""

from __future__ import annotations

import ast
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

KEY: r.HouseholdKey = "earning_lower_paid_half"


def account(
    place: str = "P",
    persons: int = 2,
    households: int = 1,
    money: int = 0,
    own: dict[str, int] | None = None,
    key: r.HouseholdKey = KEY,
    **more: Any,
) -> t.Account:
    return t.Account(place, key, persons, households, persons, money, own or {}, **more)


def row(good: str, tier: int, units: int | Fraction, basis: str = "persons") -> t.Row:
    return t.Row(good, tier, basis, F(units))  # type: ignore[arg-type]


# ---- R4 -------------------------------------------------------------------------------


def test_buying_goes_tier_by_tier_and_row_by_row() -> None:
    prices = {"food": M, "materials": M // 2, "consumer_goods": M, "business_services": M}
    rows = [
        row("food", 1, 28),
        row("materials", 1, 28, "households"),
        row("food", 2, 5),
        row("consumer_goods", 2, 10),
        row("business_services", 2, 10),
    ]
    got = t.buy(account(money=95 * M), rows, prices)
    assert got.units == {
        "food": F(66),
        "materials": F(28),
        "consumer_goods": F(15),
    }
    assert got.units.get("business_services", F(0)) == 0
    assert got.reach == (1, F(1, 2), 0)
    assert got.left_micros == 0
    assert got.pattern == (2, 1, False)


def test_an_account_above_its_tiers_scales_its_luxuries() -> None:
    prices = {"food": M, "materials": M // 2, "consumer_goods": M, "business_services": M}
    prices["leisure"] = M
    rows = [
        row("food", 1, 28),
        row("materials", 1, 28, "households"),
        row("food", 2, 5),
        row("consumer_goods", 2, 10),
        row("business_services", 2, 10),
        row("leisure", 3, 10),
    ]
    got = t.buy(account(money=150 * M), rows, prices, F(3, 2))
    assert got.units["leisure"] == 30
    assert got.left_micros == 0
    assert got.pattern == (3, 1, True)
    kept = t.buy(account(money=150 * M), rows, prices)
    assert kept.units["leisure"] == 20 and kept.left_micros == 10 * M
    assert kept.pattern == (3, 1, False)


# ---- the tier solve -------------------------------------------------------------------

PRODUCTS = (
    "food",
    "materials",
    "consumer_goods",
    "utility",
    "housing",
    "business_services",
    "household_services",
    "leisure",
)
NEEDS_ECONOMY = r.Economy(
    trades=(),
    product={},
    storable=frozenset(),
    shop_trade=None,
    public_trade=None,
    capital_trade="capital_goods",
    extraction_trade=None,
    shop_goods=frozenset(),
    person_needs=("food", "utility", "household_services"),
    household_needs=("materials", "housing"),
    place_services=frozenset(),
)
SHAPE = t.shape_of(r.Settings(), NEEDS_ECONOMY)
POSTED = {p: F((i + 1) * M) for i, p in enumerate(PRODUCTS)}
# Contents on the grid chosen so that the first start (`z0`, half of tier 1) is dearer in tier 2 than the
# nine unknowns' own size and the accounts reach leisure at it: the solve from `z0` is then regular.
ZSTAR = [F(20), F(8), F(6), F(18), F(8), F(4), F(20), F(5, 4), F(40)]


def hand_problem() -> tuple[t.TierProblem, dict[str, F]]:
    """Forty-eight accounts of three persons and a household, whose money runs from tier 1 alone to
    a third above the three tiers at `ZSTAR` (the richest are scaled), and the demand that buying
    `ZSTAR` makes."""
    comfort, luxury = t.contents_of(SHAPE, ZSTAR)
    c2 = sum((comfort[g] * POSTED[g] for g in SHAPE.tier2), F(0))
    c3 = sum((luxury[g] * POSTED[g] for g in SHAPE.tier3), F(0))
    cbar = c2 / F(3, 5)
    sizes = (c2 / cbar, c3 / cbar)
    empty = t.TierProblem(
        [], POSTED, dict.fromkeys(SHAPE.tier2, F(1)), cbar, sizes, SHAPE, NEEDS_ECONOMY
    )
    ones = t._Evaluator(empty).ones[KEY]
    tier_one = t._cost(account("P", 3, 1, 0, {}), ones, POSTED)
    accts = [
        account(f"P{k}", 3, 1, int(tier_one + 3 * (c2 + c3) * F(k, 36)), {}) for k in range(48)
    ]
    blank = replace(empty, accounts=accts)
    ev = t._Evaluator(blank)
    rows = t.want_rows(SHAPE, comfort, luxury, drop_zero=False)
    t2 = [x for x in rows if x.tier == 2]
    t3 = [x for x in rows if x.tier == 3]
    demand: dict[str, F] = {}
    for a, scale in zip(accts, ev.scale, strict=True):
        got = t._buy_tiers(a, (list(ev.ones[a.key]), t2, t3), POSTED, scale)
        for good, units in got.units.items():
            demand[good] = demand.get(good, F(0)) + units
    problem = replace(blank, demand={p: demand[p] for p in SHAPE.tier2})
    return problem, {p: POSTED[p] * demand[p] for p in SHAPE.tier2}


def test_the_tier_solve_recovers_known_contents() -> None:
    problem, spending = hand_problem()
    start = t.start_one(problem, spending)
    assert len(start) == 9 and all(v > 0 for v in start)
    # At z0 some accounts reach leisure (the last row of tier 3), so leisure has a column.
    _, patterns = t._Evaluator(problem).numeric(start)
    late = SHAPE.tier3.index("leisure")
    assert any(p[2] or (p[0] == 3 and p[1] >= late) for p in patterns)
    for first in (start, t.start_two(problem, spending), [v * F(9, 10) for v in ZSTAR]):
        z, steps = t.solve_contents(problem, first)
        assert steps <= 10
        assert all(abs(a - b) <= F(1, 2**30) for a, b in zip(z, ZSTAR, strict=True))
        residual, _ = t._Evaluator(problem).numeric(z)
        assert all(v == 0 for v in residual)


def test_the_held_patterns_give_the_true_residual() -> None:
    problem, spending = hand_problem()
    evaluator = t._Evaluator(problem)
    start = [v * F(9, 10) for v in ZSTAR]
    residual, patterns = evaluator.numeric(start)
    polys = evaluator.held(patterns)
    assert [t._value(poly, start) for poly in polys] == residual


def test_a_singular_system_is_refused() -> None:
    with pytest.raises(ReferenceBuildError, match=r"^tiers_singular"):
        t._gauss([[F(1), F(2)], [F(2), F(4)]], [F(1), F(1)])


def test_two_solutions_are_refused() -> None:
    base = [F(8), F(3), F(4), F(6), F(2), F(3), F(7), F(1), F(5, 2)]
    eight_four = [F(84, 10), *base[1:]]
    nine = [F(9), *base[1:]]
    with pytest.raises(ReferenceBuildError, match=r"^tiers_not_unique: food$"):
        t.check_unique(SHAPE, base, nine)
    t.check_unique(SHAPE, base, eight_four)


# ---- accounts and the benefit ---------------------------------------------------------

FOOD_T, UTIL_T, HS_T, MAT_T, HOUSING_T, PUB_T = (
    "food",
    "energy_utilities",
    "household_services",
    "manufacturing",
    "construction_housing",
    "public_provisioning",
)
ECON = r.TWELVE


def product(key: str, price: int, kind: str = "service") -> u.Product:
    return u.Product(key, key, key, kind, F(1), price, price // 4, price * 4, 1, 0, None)  # type: ignore[arg-type]


def recipe(trade: str, margin: int | None = 0) -> u.Recipe:
    return u.Recipe(trade, 1, 1, {}, margin, F(0), F(0))


OWN_PRICES = {
    "food": 1_000_000,
    "utility": 500_000,
    "materials": 250_000,
    "housing": 2_000_001,
    "public_provision": 1_000_000,
}


def own_with(hs: int) -> dict[str, int]:
    return {**OWN_PRICES, "household_services": hs}


def test_the_benefit_is_estimated_at_each_account_s_own_cost() -> None:
    support = 28 * 1_000_000
    own1, own3 = own_with(3_000_000), own_with(4_500_000)
    nonowner = "no_earner_nonowner"
    assert t.needs_cost_micros(own1, 3, 2, nonowner, ECON) == 507_000_056
    estimate = t.own_need_estimate(own1, 3, 2, 1, 0, nonowner, ECON, support)
    assert estimate == 159_666_686  # ceil(479,000,056 / 3)
    assert estimate * 3 == 479_000_058
    assert t.own_need_estimate(own1, 3, 2, 0, 0, nonowner, ECON, support) == 169_000_019
    # Support above the needs: one micro.
    cheap = {
        **own1,
        "food": 20_000_000 // 28,
        "utility": 0,
        "household_services": 0,
        "materials": 0,
        "housing": 0,
        "public_provision": 0,
    }
    assert t.own_need_estimate(cheap, 1, 1, 1, 0, nonowner, ECON, support) == 1
    owner = t.own_need_estimate(own3, 2, 1, 0, 0, "no_earner_owner", ECON, support)
    assert t.needs_cost_micros(own3, 2, 1, "no_earner_owner", ECON) == 401_000_028
    assert owner == 200_500_014
    resident = t.own_need_estimate(own1, 10, 4, 0, 4, "collective_residence", ECON, support)
    assert resident == 76_200_000
    assert t.needs_cost_micros(own1, 10, 4, "collective_residence", ECON) == 1_270_000_000
    assert t.own_need_estimate(own3, 10, 4, 0, 10, "collective_residence", ECON, support) is None
    assert 479_000_058 + 401_000_028 + 76_200_000 * 10 == 1_642_000_086


def test_a_shop_posts_what_it_pays() -> None:
    estimate = t.shop_own_price(1_000_000, 600_001, 2_500, (1, 10), 20_000_000)
    assert estimate == 2_900_001
    assert t.shop_own_price(1_000_000, None, 2_500, (1, 10), 20_000_000) == 3_000_000


def hand_written(**more: Any) -> u.Written:
    products = {
        "food": product("food", 1_000_000, "storable"),
        "utility": product("utility", 500_000, "utility"),
        "materials": product("materials", 250_000, "storable"),
        "housing": product("housing", 2_000_001, "utility"),
        "household_services": product("household_services", 3_000_000),
        "public_provision": product("public_provision", 1_000_000),
    }
    recipes = {
        FOOD_T: recipe(FOOD_T),
        MAT_T: recipe(MAT_T),
        UTIL_T: recipe(UTIL_T),
        HS_T: recipe(HS_T),
        HOUSING_T: recipe(HOUSING_T),
        PUB_T: recipe(PUB_T, None),
    }
    fields: dict[str, Any] = {
        "products": products,
        "recipes": recipes,
        "machine_price_micros": 1_000_000,
        "workers_per_machine": {},
        "machine_life_periods": 100,
        "wage_tax_bps": 2000,
        "operating_income_tax_bps": 2000,
        "fund_share_bps": 0,
        "import_bps": {},
        "batch_hours_lost": {},
        "demand_moved": {},
        "machines_worn": F(0),
    }
    fields.update(more)
    return u.Written(**fields)


def hand_trade(**more: Any) -> r.TradeCount:
    fields = dict.fromkeys(
        (
            "employee_persons",
            "working_owner_persons",
            "unpaid_family_persons",
            "payroll_micros",
            "force",
            "sites",
            "machines",
            "public_employee_persons",
            "public_payroll_micros",
        ),
        0,
    )
    fields.update(more)
    return r.TradeCount(**fields)


def hand_place(
    label: str,
    keys: dict[str, tuple[int, int, int, int, int]],
    hs_wage: int,
    trades: dict[str, r.PlaceTrade] | None = None,
    **more: Any,
) -> r.Place:
    """`keys`: key -> (households, persons, employed, reserve, wage income micros)."""
    counts = {k: r.PlaceKeyCount(*keys.get(k, (0, 0, 0, 0, 0))) for k in r.HOUSEHOLD_KEYS}
    national = 20_000_000
    sellers: dict[r.HouseholdKey, dict[str, r.Seller]] = {}
    for key in r.HOUSEHOLD_KEYS:
        sellers[key] = {
            "household_services": r.Seller(hs_wage, None),
            "utility": r.Seller(national, None),
            "food": r.Seller(national, None),
            "public_provision": r.Seller(national, None),
            "housing": r.Seller(national, None),
            "materials": r.Seller(national, None),
        }
    fields: dict[str, Any] = {
        "label": label,
        "hub": label[:5],
        "state": label[:2],
        "keys": counts,
        "trades": trades or {},
        "owner_households": counts["earning_owner"].households
        + counts["no_earner_owner"].households,
        "sellers": sellers,
        "public_persons_served": 0,
        "public_machines": 0,
    }
    fields.update(more)
    return r.Place(**fields)


def hand_quantities(**more: Any) -> s.Quantities:
    trades = (FOOD_T, UTIL_T, HS_T, MAT_T, HOUSING_T, PUB_T, "distribution_transport")
    zero = {t_: F(0) for t_ in trades}
    fields: dict[str, Any] = {
        "output": {t_: F(1) for t_ in trades},
        "coefficients": {},
        "hours_per_dollar": dict.fromkeys(trades, F(1)),
        "hours": dict.fromkeys(trades, 0),
        "wage": dict.fromkeys(trades, F(20)),
        "unpaid_labor": zero,
        "export_share": {},
        "imports": zero,
        "final": {},
        "machines": dict.fromkeys(trades, 0),
        "import_sources": {},
        "import_buyers": {},
        "import_cover": {},
        "business_demand": {},
        "service_import_bps": {},
        "wages_abroad": {},
    }
    fields.update(more)
    return s.Quantities(**fields)


def hand_opening(**more: Any) -> s.Opening:
    trades = (FOOD_T, UTIL_T, HS_T, MAT_T, HOUSING_T)
    prices = s.Prices(
        prices=dict.fromkeys(trades, F(1)),
        margins={FOOD_T: F(1, 10), HS_T: F(1, 5)},
        floored=frozenset(),
        equipment=F(0),
        rounds=1,
    )
    fields: dict[str, Any] = {
        "lam": F(0),
        "prices": prices,
        "quantities": hand_quantities(),
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
        "tier_quantities": {"food": F(28)},
    }
    fields.update(more)
    return s.Opening(**fields)


def hand_census(places: tuple[r.Place, ...], trades: dict[str, r.TradeCount]) -> r.Census:
    households: dict[r.HouseholdKey, r.KeyCount] = {}
    for key in r.HOUSEHOLD_KEYS:
        rows = [p.keys[key] for p in places]
        households[key] = r.KeyCount(
            0,
            sum(x.households for x in rows),
            sum(x.persons for x in rows),
            sum(x.employed for x in rows),
            sum(x.reserve for x in rows),
            sum(x.wage_income_micros for x in rows),
        )
    return r.Census(
        trades=trades,
        households=households,
        places=places,
        abroad={},
        firm_assignment={},
        retail_assignment={},
        crossing_force={},
        workers_per_machine={},
        sha256="",
    )


def two_places() -> tuple[r.Census, s.Opening, u.Written]:
    place_trade = r.PlaceTrade
    one = hand_place(
        "01001",
        {
            "earning_lower_paid_half": (10, 25, 20, 2, 900 * M),
            "earning_owner": (3, 7, 7, 0, 600 * M),
            "no_earner_nonowner": (2, 3, 0, 1, 0),
            "no_earner_owner": (1, 2, 0, 0, 0),
            "collective_residence": (4, 10, 4, 0, 100 * M),
        },
        20_000_000,
        {
            FOOD_T: place_trade(60, 36 * M, 0, 0),
            HS_T: place_trade(10, 8 * M, 4, 3 * M),
        },
    )
    two = hand_place(
        "01003",
        {
            "earning_lower_paid_half": (8, 20, 18, 1, 700 * M),
            "earning_owner": (2, 4, 4, 0, 300 * M),
            "no_earner_nonowner": (1, 2, 0, 0, 0),
        },
        21_500_000,
        {
            FOOD_T: place_trade(40, 14 * M, 0, 0),
            HS_T: place_trade(30, 12 * M, 6, 3 * M),
        },
    )
    trades = {
        FOOD_T: hand_trade(employee_persons=100, payroll_micros=50 * M),
        HS_T: hand_trade(
            employee_persons=40,
            payroll_micros=20 * M,
            public_employee_persons=10,
            public_payroll_micros=6 * M,
        ),
    }
    census = hand_census((one, two), trades)
    o = hand_opening(
        operating_income={FOOD_T: F(100), HS_T: F(60)},
        tax_rate=F(1, 5),
    )
    return census, o, hand_written()


def test_a_part_s_account_pays_its_own_sellers_prices() -> None:
    census, o, w = two_places()
    accts = {(a.place, a.key): a for a in t.accounts(o, census, w, ECON)}
    assert accts[("01001", KEY)].own_prices["household_services"] == 3_000_000
    assert accts[("01003", KEY)].own_prices["household_services"] == 4_500_000
    assert accts[("01001", "no_earner_owner")].own_prices["food"] == 1_000_000
    assert ("01003", "no_earner_owner") not in accts  # no persons, no account


def test_place_money_sums_to_the_nation() -> None:
    census, o, w = two_places()
    tax = o.tax_rate
    # The places' incomes are the nation's: private + public-owned operating income sums to OI,
    # and the O5 margin terms sum to 0.
    incomes = t.place_incomes(o, census)
    oi = sum((i.private + i.public_owned for i in incomes.values()), F(0))
    assert oi == sum(o.operating_income.values(), F(0))
    # The places pay unlike wages (food 0.6 against 0.35 million an employee; the public workers of
    # household services 0.75 against 0.5), so each O5 margin term is not 0, and the public-owned
    # part follows the public workers (10 of 40 persons) while its terms sum to 0 as well.
    assert sum((i.public_owned for i in incomes.values()), F(0)) == F(60) * 10 / 40
    plain = F(100) * 60 / 100 + F(60) * 10 / 40  # place 01001's share of OI with no margin term
    first = incomes["01001"]
    assert first.private + first.public_owned != plain
    accts = t.accounts(o, census, w, ECON)
    support = t.support_micros(w)
    by_key: dict[r.HouseholdKey, F] = dict.fromkeys(r.HOUSEHOLD_KEYS, F(0))
    for a in accts:
        est = t.own_need_estimate(
            a.own_prices, a.persons, a.households, a.reserve, a.employed, a.key, ECON, support
        )
        if a.key in ("no_earner_nonowner", "no_earner_owner", "collective_residence"):
            by_key[a.key] += F((est or 0) * a.persons, M)
    # The households' payout is the private part: the public-owned part goes to the part's body.
    payout = (1 - tax) * (oi - sum((i.public_owned for i in incomes.values()), F(0)))
    bands = s._bands(census, tax, payout, F(support, M), by_key)
    nation = sum(bands.values(), F(0)) * M
    money = sum(a.money_micros for a in accts)
    assert 0 <= nation - money <= len(accts)
    # Wayne-style detail: one account is one place and key.
    assert len({(a.place, a.key) for a in accts}) == len(accts)


# ---- own prices -----------------------------------------------------------------------


def hand_tiers_rows() -> tuple[list[t.Row], list[t.Row], list[t.Row]]:
    tier1 = [row("food", 1, 28), row("household_services", 1, 28)]
    tier2 = [row("food", 2, 5), row("household_services", 2, 5)]
    tier3 = [row("leisure", 3, 10)]
    return tier1, tier2, tier3


def test_a_scale_is_set_at_the_account_s_own_prices() -> None:
    own = {"food": M, "household_services": 2 * M, "leisure": 16 * M}  # leisure at twice 8
    a = account(persons=2, money=2000 * M, own=own)
    tiers = hand_tiers_rows()
    c1, c2, c3 = (t._cost(a, rows, own) for rows in tiers)
    assert (c1, c2, c3) == (168 * M, 30 * M, 320 * M)
    bps = t.luxury_scale_bps(a, tiers)
    assert bps == (2000 * M - c1 - c2) * 10_000 // c3
    got = t.buy(a, [*tiers[0], *tiers[1], *tiers[2]], own, F(bps or 0, 10_000))
    assert got.left_micros < 16 * M  # less than one unit of its dearest luxury
    # An account whose money does not pass its tiers is not scaled.
    assert t.luxury_scale_bps(account(persons=2, money=400 * M, own=own), tiers) is None
    # The compiler refuses a scale above 1,000,000.
    rich = account(persons=2, money=10**12 * M, own=own)
    with pytest.raises(ReferenceBuildError, match=r"^luxury_scale_bound: P/earning_lower"):
        t.luxury_scale_bps(rich, tiers)


def test_own_prices_move_what_accounts_buy() -> None:
    national = {"household_services": 4 * M}
    cheap = {"household_services": 2 * M}
    dear = {"household_services": 8 * M}
    rows = [row("household_services", 1, 28)]
    tier = (rows, [row("household_services", 2, 10)], [])
    money = 1000 * M
    units = {}
    for name, prices in (("national", national), ("cheap", cheap), ("dear", dear)):
        a = account(persons=2, money=money, own=prices)
        units[name] = t._buy_tiers(a, (list(tier[0]), tier[1], tier[2]), prices, None).units[
            "household_services"
        ]
    # 56 units are tier 1 and 20 are tier 2: all bought at the national price.
    assert units["national"] == 76
    assert units["cheap"] == 76  # same units, less money spent: money is kept
    assert units["dear"] == 76
    # With less money the cheap seller's account buys more and the dear one's less.
    tight = 200 * M
    tight_units = {
        name: t._buy_tiers(
            account(persons=2, money=tight, own=prices),
            (list(tier[0]), tier[1], tier[2]),
            prices,
            None,
        ).units["household_services"]
        for name, prices in (("national", national), ("cheap", cheap), ("dear", dear))
    }
    assert tight_units == {"national": 50, "cheap": 76, "dear": 25}
    demand = {"household_services": F(2 * 50)}
    gaps = t._gaps({"household_services": tight_units["cheap"] + tight_units["dear"]}, demand)
    assert gaps["household_services"] == F(1, 100)


# ---- the places' bodies and the counts -------------------------------------------------


def test_every_part_opens_even() -> None:
    d = F
    assert t.body_split("01001", d(100), d(0), d(80), d(80)) == (2000, 0, d(0))
    assert t.body_split("01003", d(50), d(5), d(75), d(75)) == (0, 20_000_000, d(0))
    # The fund's receipts equal its grants with no benefit.
    assert 2000 * 100 // 10_000 == 20
    share, grant, _ = t.body_split("01005", d(3), d(0), d(1), d(1))
    assert share == 6667 and grant == 0
    assert d(3) * (10_000 - share) / 10_000 == d(9999, 10_000)
    assert t.body_split("01009", d(25), d(30), d(50), d(50)) == (2000, 0, d(0))
    assert t.body_split("01011", d(10), d(60), d(50), d(50)) == (10_000, 0, d(10))
    with pytest.raises(ReferenceBuildError, match=r"^place_grant_over_providers: 01007"):
        t.body_split("01007", d(10), d(0), d(50), d(30))
    # No taxes at all: the grant is the whole gap.
    assert t.body_split("01013", d(0), d(0), d(2), d(2)) == (0, 2_000_000, d(0))


def test_a_part_s_body_follows_its_incomes() -> None:
    """Part `01009` at `t = 1/4`: residents' wages $30, private operating income $30, public-owned
    operating income $40, payments $50: taxes $25, payout $30, share 2,000, no grant."""
    place = hand_place(
        "01009",
        {"earning_lower_paid_half": (5, 12, 12, 0, 30 * M)},
        20_000_000,
        {
            FOOD_T: r.PlaceTrade(7, 0, 4, 0),
            PUB_T: r.PlaceTrade(5, 50 * M, 5, 50 * M),
        },
    )
    trades = {
        FOOD_T: hand_trade(employee_persons=7, public_employee_persons=4),
        PUB_T: hand_trade(employee_persons=5, payroll_micros=50 * M, public_employee_persons=5),
    }
    census = hand_census((place,), trades)
    o = hand_opening(operating_income={FOOD_T: F(70)}, tax_rate=F(1, 4))
    settings = replace(r.Settings(), public_fee_micros=0)
    bodies = t.place_bodies(o, census, hand_written(), settings, ECON)
    taxes, payout, payments = bodies.taxes["01009"]
    assert (taxes, payout, payments) == (F(25), F(30), F(50))
    assert bodies.share_bps["01009"] == 2000
    assert bodies.grant_micros == {}


def hand_recipe(trade: str, n: int, hours: int, inputs: dict[str, int]) -> u.Recipe:
    return u.Recipe(trade, n, hours, inputs, 0, F(0), F(0))


def test_a_state_s_services_are_counted() -> None:
    economy = r.Economy(
        trades=(HS_T, "leisure_hospitality"),
        product={HS_T: "household_services", "leisure_hospitality": "leisure"},
        storable=frozenset(),
        shop_trade=None,
        public_trade=None,
        capital_trade="capital_goods",
        extraction_trade=None,
        shop_goods=frozenset(),
        person_needs=("household_services",),
        household_needs=(),
        place_services=frozenset({"household_services"}),
    )
    w = hand_written(
        products={
            "household_services": product("household_services", M),
            "leisure": product("leisure", M),
        },
        recipes={
            HS_T: hand_recipe(HS_T, 7, 2, {}),
            "leisure_hospitality": hand_recipe("leisure_hospitality", 7, 2, {}),
        },
    )
    settings = replace(r.Settings(), country_services=frozenset({"leisure"}))

    def place(label: str, hs_workers: int, leisure_workers: int, persons: int) -> r.Place:
        return hand_place(
            label,
            {KEY: (persons, persons, persons, 0, 0)} if persons else {},
            20_000_000,
            {
                HS_T: r.PlaceTrade(hs_workers, 0, 0, 0),
                "leisure_hospitality": r.PlaceTrade(leisure_workers, 0, 0, 0),
            },
        )

    north = place("01001", 10, 5, 10)
    south = place("02001", 0, 0, 190)
    census = hand_census(
        (north, south),
        {
            HS_T: hand_trade(employee_persons=10),
            "leisure_hospitality": hand_trade(employee_persons=5),
        },
    )
    # Hours at work are the employees' 160 each (no working owners in the hand world).
    o = hand_opening(quantities=hand_quantities(hours={HS_T: 1600, "leisure_hospitality": 800}))
    bought: dict[tuple[str, r.HouseholdKey], t.Bought] = {}
    for label, persons in (("01001", 10), ("02001", 190)):
        a = account(label, persons, persons, 10**15, {"household_services": M, "leisure": M})
        rows = [row("household_services", 1, 28), row("leisure", 2, 14)]
        bought[(label, KEY)] = t.buy(a, rows, a.own_prices)
    counts = t._count_services(o, census, w, settings, economy, bought)
    north_cap, north_use = counts.state_services[("01", "household_services")]
    south_cap, south_use = counts.state_services[("02", "household_services")]
    assert (north_cap, north_use) == (5600, 280)
    assert (south_cap, south_use) == (0, 5320)
    assert north_cap + south_cap == north_use + south_use
    idle, unserved = t.service_shares(counts.state_services, "household_services")
    assert idle == F(5600 - 280, 5600)
    assert unserved == F(5320, 5600)
    assert all(name != "leisure" for _, name in counts.state_services)
    # Leisure is a country service: its capacity equals its use at national prices.
    assert counts.country_services["leisure"] == (2800, 2800)


# ---- hygiene --------------------------------------------------------------------------


def test_no_float_in_the_module() -> None:
    tree = ast.parse((ROOT / "tools/national_opening_tiers.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            assert not isinstance(node.value, float), node.lineno
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"float", "round"}, node.lineno
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = [a.name for a in node.names] + [getattr(node, "module", None) or ""]
            assert "statistics" not in names


# ---- the committed tables (slow) -------------------------------------------------------


def fixture_facts() -> u.TemplateFacts:
    import tomllib

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
def committed() -> tuple[s.Opening, u.Written, r.Census, r.Settings, t.Tiers]:
    settings = r.Settings()
    cut = r.recut(r.read_accounts(ACCOUNTS), settings)
    census = r.read_census(CENSUS)
    opening = s.solve(cut, census, settings)
    written = u.written(opening, cut, census, settings, fixture_facts())
    return opening, written, census, settings, t.tiers(opening, census, written, settings)


def median(values: list[Any]) -> Any:
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def decimal(value: F, places: int = 4) -> str:
    """A fraction as a decimal string, with no float."""
    scaled = (abs(value) * 10**places).__floor__()
    return f"{'-' if value < 0 else ''}{scaled // 10**places}.{scaled % 10**places:0{places}d}"


# Counted on the committed tables (27 November): 8 of 1,896 accounts cannot reach their own tier 1,
# six collective residences and two earning accounts (02158/at, 04019/above). The plan (Task 11,
# Step 1) asks that none fail; the lead or the Director rules whether the residence or earning
# rule changes or the plan's text is amended. Until then the assertion stands as the plan has it
# and the test is an expected failure that names them: it is strict, so it turns red the day the
# accounts open and the mark must be removed.
@pytest.mark.slow
@pytest.mark.xfail(
    strict=True,
    reason="8 accounts of the committed tables (6 residences, 02158/at, 04019/above) cannot reach"
    " their own tier 1: awaiting the lead's ruling (change the rule or amend the plan)",
)
def test_no_account_opens_without_its_tier_one(committed: Any) -> None:
    _, _, _, settings, tiers = committed
    shape = t.shape_of(settings, r.TWELVE)
    short = []
    for a in tiers.accounts:
        rows = t.tier_one_rows(a.key, shape, r.TWELVE)
        cost = t._cost(a, rows, a.own_prices)
        if a.money_micros < cost:
            short.append((a.place, a.key, cost - a.money_micros))
    print(f"accounts short of tier 1: {len(short)} of {len(tiers.accounts)}")  # noqa: T201
    for place, key, gap in short:
        print(f"  {place}/{key}: short {gap} micros")  # noqa: T201
    assert not short


@pytest.mark.slow
def test_nothing_is_kept(committed: Any) -> None:
    _, _, _, _, tiers = committed
    by_account = {(a.place, a.key): a for a in tiers.accounts}
    worst = F(0)
    for (place, key), left in tiers.kept_micros.items():
        a = by_account[(place, key)]
        dearest = max(
            a.own_prices[g] for g in tiers.luxury if tiers.luxury[g] > 0 and g in a.own_prices
        )
        assert left <= a.persons * dearest, (place, key, left)
        worst = max(worst, left / (a.persons * dearest))
    print(f"largest kept money over one unit of the dearest luxury a person: {decimal(worst)}")  # noqa: T201


@pytest.mark.slow
def test_the_tiers_buy_what_households_must(committed: Any) -> None:
    _, _, _, _, tiers = committed
    print("demand_gap:", {k: decimal(v) for k, v in tiers.demand_gap.items()})  # noqa: T201
    assert all(abs(v) <= F(1, 100) for v in tiers.demand_gap.values())


@pytest.mark.slow
def test_tier_money_has_its_sizes(committed: Any) -> None:
    o, _, _, settings, tiers = committed
    cbar = o.tier_unit * s.MICROS
    for cost, size in zip(tiers.tier_costs, settings.tier_sizes[1:], strict=True):
        assert abs(cost / (size * cbar) - 1) <= F(1, 100)
    scaled = sorted(bps for bps in tiers.luxury_scale_bps.values())
    print(  # noqa: T201
        f"tier costs {[decimal(c) for c in tiers.tier_costs]} micros a person; cbar {decimal(cbar)};"
        f" steps {tiers.steps}; starts {tiers.starts}"
    )
    print(  # noqa: T201
        f"scaled accounts {len(scaled)} of {len(tiers.accounts)}; median scale "
        f"{median(scaled) if scaled else 0} bps"
    )
    print("comfort", dict(tiers.comfort), "luxury", dict(tiers.luxury))  # noqa: T201
    print("zero rows", tiers.zero_rows, "exact", {k: decimal(v, 6) for k, v in tiers.exact.items()})  # noqa: T201
    for key in r.HOUSEHOLD_KEYS:
        rows = [a for a in tiers.accounts if a.key == key]
        persons = sum(a.persons for a in rows)
        money = sum(a.money_micros for a in rows)
        reach = [tiers.reach[(a.place, a.key)] for a in rows]
        print(  # noqa: T201
            f"{key}: accounts {len(rows)} money a person {money // max(persons, 1)} micros; "
            f"reach (first, median, last tier) "
            f"{[decimal(median([x[i] for x in reach])) for i in range(3)]}"
        )
    estimates = sorted(tiers.no_earner_estimate.values())
    residences = sorted(tiers.residence_estimate.values())
    print(  # noqa: T201
        f"no_earner_estimate lowest {estimates[0]} median {median(estimates)} highest {estimates[-1]};"
        f" residence_estimate lowest {residences[0]} median {median(residences)} "
        f"highest {residences[-1]}"
    )
    print("own_price_gap:", {k: decimal(v) for k, v in tiers.own_price_gap.items()})  # noqa: T201


@pytest.mark.slow
def test_the_services_of_the_places_are_counted(committed: Any) -> None:
    _, _, _, _, tiers = committed
    services = sorted({name for _, name in tiers.state_services})
    for service in services:
        idle, unserved = t.service_shares(tiers.state_services, service)
        ratios = sorted(
            (use / cap if cap > 0 else F(10**6), state)
            for (state, name), (cap, use) in tiers.state_services.items()
            if name == service
        )
        low = [(st, decimal(x, 2)) for x, st in ratios[:3]]
        high = [(st, decimal(x, 2)) for x, st in ratios[-3:]]
        print(  # noqa: T201
            f"{service}: idle {decimal(idle)} unserved {decimal(unserved)} "
            f"lowest use/capacity {low} highest {high}"
        )
    for service, (cap, use) in tiers.country_services.items():
        print(f"country {service}: capacity {decimal(cap)} use {decimal(use)}")  # noqa: T201


@pytest.mark.slow
@pytest.mark.xfail(
    strict=True,
    reason="the fund's receipts fall short of BEN + grants by the public wear the compiler sizes on"
    " the written machine price (Task 10 sizes the grant on the solve's wear share): awaiting the"
    " lead's ruling (size the grant and tax on the written wear, or amend the plan's bound)",
)
def test_the_fund_closes_with_its_grants(committed: Any) -> None:
    o, w, census, settings, tiers = committed
    receipts = sum(
        (
            F(tiers.share_by_part_bps[part]) * taxes / 10_000
            for part, (taxes, _payout, _payments) in tiers.place_bodies.items()
        ),
        F(0),
    )
    grants = F(sum(tiers.place_grant_micros.values()), s.MICROS)
    long_parts = sum(
        (
            taxes / 10_000
            for part, (taxes, _p, _q) in tiers.place_bodies.items()
            if tiers.share_by_part_bps[part] > 0
        ),
        F(0),
    )
    # The compiler's wear of a public provider's machines (written machine price, every machine
    # of the part) is above the solve's `wear[public]` share (27 November, Task 11 decision 11).
    # The plan's bound has no term for it: the difference is printed, not added to the bound.
    wear = sum(
        (
            F(
                -(-(place.public_machines * w.machine_price_micros) // w.machine_life_periods),
                s.MICROS,
            )
            for place in census.places
        ),
        F(0),
    )
    wear_gap = wear - o.wear[r.TWELVE.public_trade or ""]
    estimated = F(tiers.estimated_payments_micros, s.MICROS)
    shares = sorted(tiers.share_by_part_bps.values())
    sending = sum(1 for v in shares if v > 0)
    print(  # noqa: T201
        f"fund receipts {decimal(receipts)} benefits (solve) {decimal(o.benefits)} grants "
        f"{decimal(grants)} gap {decimal(receipts - o.benefits - grants)}; public wear, written "
        f"{decimal(wear)} against the solve's {decimal(o.wear[r.TWELVE.public_trade or ''])} "
        f"(difference {decimal(wear_gap)}); allowance {decimal(long_parts + 1)}; estimated "
        f"benefits {decimal(estimated)} against the solve's {decimal(o.benefits)}; over even "
        f"{dict(tiers.over_even)}"
    )
    print(  # noqa: T201
        f"parts sending a share {sending} paid by the fund {len(tiers.place_grant_micros)} of "
        f"{len(shares)}; lowest share {shares[0]} highest {shares[-1]}"
    )
    assert abs(receipts - o.benefits - grants) <= long_parts + 1


@pytest.mark.slow
def test_no_payout_is_dropped(committed: Any) -> None:
    """A part with private operating income and no owner households would drop its payout from
    the accounts' money (`_drafts`); on the committed tables none does."""
    o, _, census, _, _ = committed
    incomes = t.place_incomes(o, census)
    dropped = [
        p.label for p in census.places if p.owner_households <= 0 and incomes[p.label].private > 0
    ]
    print(f"parts whose payout has no owner household: {dropped}")  # noqa: T201
    assert dropped == []
