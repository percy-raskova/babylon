"""Task 10: quantities, prices, margins, trade and taxes of the rebuilt opening."""

from __future__ import annotations

import sys
from collections.abc import Mapping
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

ReferenceBuildError = county.ReferenceBuildError
F = Fraction
ECONOMY_DIR = ROOT / "src/babylon/data/reference/economy"
ACCOUNTS = ECONOMY_DIR / "national_trade_accounts_2024.csv.gz"
CENSUS = ECONOMY_DIR / "national_opening_census_v13.json.gz"

FOOD, CAP, HS, SHOP, PUB = (
    "food",
    "capital_goods",
    "household_services",
    "distribution_transport",
    "public_provisioning",
)


def economy_of(trades: tuple[str, ...], product: dict[str, str], **kw: Any) -> r.Economy:
    base: dict[str, Any] = {
        "trades": trades,
        "product": product,
        "storable": frozenset({"food", "equipment"}),
        "shop_trade": None,
        "public_trade": None,
        "capital_trade": CAP,
        "extraction_trade": None,
        "shop_goods": frozenset(),
        "person_needs": (),
        "household_needs": (),
        "place_services": frozenset(),
    }
    base.update(kw)
    return r.Economy(**base)


THREE = economy_of((FOOD, CAP, HS), {FOOD: "food", CAP: "equipment", HS: "household_services"})
THREE_SETTINGS = replace(
    r.Settings(),
    service_stage={"household_services": 2},
    paying_order=("food", "household_services"),
    crossing=frozenset(),
    country_services=frozenset(),
)


def hand_q(
    trades: tuple[str, ...],
    *,
    output: Mapping[str, Any],
    a: Mapping[str, Mapping[str, Any]],
    h: Mapping[str, Any],
    wage: Mapping[str, Any],
    machines: Mapping[str, int] | None = None,
    final: Mapping[str, Any] | None = None,
    **more: Any,
) -> s.Quantities:
    z = {t: F(0) for t in trades}
    fields: dict[str, Any] = {
        "output": {t: F(output[t]) for t in trades},
        "coefficients": {i: {j: F(v) for j, v in row.items()} for i, row in a.items()},
        "hours_per_dollar": {t: F(h[t]) for t in trades},
        "hours": dict.fromkeys(trades, 0),
        "wage": {t: F(wage[t]) for t in trades},
        "unpaid_labor": dict(z),
        "export_share": {},
        "imports": dict(z),
        "final": {t: F((final or {}).get(t, 0)) for t in trades},
        "machines": {t: (machines or {}).get(t, 0) for t in trades},
        "import_sources": {},
        "import_buyers": {},
        "import_cover": {},
        "business_demand": {},
        "service_import_bps": {},
        "wages_abroad": {},
    }
    fields.update(more)
    return s.Quantities(**fields)


def three_q(**kw: Any) -> s.Quantities:
    return hand_q(
        (FOOD, CAP, HS),
        output=kw.pop("output", {FOOD: 1000, CAP: 500, HS: 2000}),
        a=kw.pop("a", {HS: {FOOD: F(1, 5), CAP: F(1, 5)}, FOOD: {HS: F(1, 10)}}),
        h={FOOD: F(1, 100), CAP: F(1, 50), HS: F(1, 40)},
        wage={FOOD: 20, CAP: 30, HS: 25},
        **kw,
    )


def test_prices_solve_the_system_exactly() -> None:
    margin = {FOOD: F(1, 10), CAP: F(1, 10), HS: F(1, 5)}
    out = s.solve_prices(three_q(), F(1), margin, THREE_SETTINGS, THREE)
    assert out.prices[FOOD] == F(1925, 4868)
    assert out.prices[CAP] == F(101673, 121700)
    assert out.prices[HS] == F(1941, 2434)
    assert out.floored == frozenset()


def test_the_floor_holds_at_the_solution() -> None:
    q = three_q(
        output={FOOD: 1000, CAP: 500, HS: 2000},
        machines={FOOD: 10, CAP: 10, HS: 1},
        final={CAP: 100},
    )
    margin = {FOOD: F(1, 10), CAP: F(1, 10), HS: F(1, 5)}
    out = s.solve_prices(q, F(0), margin, THREE_SETTINGS, THREE)
    assert out.floored == frozenset({FOOD, CAP, HS})
    p, mu = out.prices, out.margins
    equipment = p[CAP] * 100
    assert abs(out.equipment - s.to_grid(equipment, s.MICROS)) <= F(1, s.MICROS)
    nm = 21
    for j in (FOOD, CAP, HS):
        cost = q.wage[j] * q.hours_per_dollar[j] + sum(
            (q.coefficients.get(i, {}).get(j, F(0)) * p[i] for i in (FOOD, CAP, HS)), F(0)
        )
        profit = q.output[j] * cost * mu[j]
        wear = out.equipment * q.machines[j] / nm
        # Exact up to the equipment money's own rounding onto the micro grid: the prices are
        # solved at the previous round's equipment (shortfall here 1.8e-7, under one micro).
        assert profit >= THREE_SETTINGS.wear_cover * wear - F(1, s.MICROS), j
        assert profit <= F(5, 4) * wear + F(1, s.MICROS) * 10, j


def test_a_singular_system_is_refused() -> None:
    q = three_q(a={HS: {FOOD: F(10)}, FOOD: {HS: F(1, 10)}})
    margin = {FOOD: F(0), CAP: F(0), HS: F(0)}
    with pytest.raises(ReferenceBuildError, match=r"^prices_singular"):
        s.solve_prices(q, F(0), margin, THREE_SETTINGS, THREE)


# ---- a hand world with a shop, a public provider and a region abroad -----------------

SMALL = economy_of(
    (FOOD, CAP, HS, SHOP, PUB),
    {FOOD: "food", CAP: "equipment", HS: "household_services", PUB: "public_provision"},
    shop_trade=SHOP,
    public_trade=PUB,
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
TRADES5 = SMALL.trades
OUTPUT = {FOOD: 10000, CAP: 2000, HS: 8000, SHOP: 1000, PUB: 3000}
HOURS = {FOOD: 100, CAP: 40, HS: 100, SHOP: 20, PUB: 50}
WAGE = {FOOD: 20, CAP: 30, HS: 25, SHOP: 20, PUB: 30}
COEF = {
    FOOD: {HS: F(1, 20), PUB: F(1, 30), CAP: F(1, 40)},
    HS: {FOOD: F(1, 10), CAP: F(1, 10), PUB: F(1, 60)},
}
MACHINES = {FOOD: 10, CAP: 5, HS: 2, PUB: 3}
PRIVATE5 = (FOOD, CAP, HS)


def world_q(
    *,
    coef: Mapping[str, Mapping[str, Fraction]] = COEF,
    unpaid: Mapping[str, Fraction] | None = None,
    xs: Mapping[str, Fraction] | None = None,
    sources: Mapping[str, Mapping[str, Fraction]] | None = None,
    buyers: Mapping[str, Mapping[str, Fraction]] | None = None,
    cover: Mapping[str, Fraction] | None = None,
    abroad: Mapping[str, Mapping[str, Fraction]] | None = None,
) -> s.Quantities:
    imports = {t: F(0) for t in TRADES5}
    imports[FOOD], imports[CAP] = F(1000), F(100)
    final = {}
    for i in (FOOD, CAP, HS, PUB):
        used = sum((coef.get(i, {}).get(j, F(0)) * OUTPUT[j] for j in TRADES5), F(0))
        final[i] = OUTPUT[i] + imports[i] - used
    return s.Quantities(
        output={t: F(OUTPUT[t]) for t in TRADES5},
        coefficients={i: dict(row) for i, row in coef.items()},
        hours_per_dollar={t: F(HOURS[t], OUTPUT[t]) for t in TRADES5},
        hours=dict(HOURS),
        wage={t: F(WAGE[t]) for t in TRADES5},
        unpaid_labor={t: F(5) for t in TRADES5} | dict(unpaid or {}),
        export_share=dict({FOOD: F(1, 10), CAP: F(1, 5)} if xs is None else xs),
        imports=imports,
        final=final,
        machines={t: MACHINES.get(t, 0) for t in TRADES5},
        import_sources=dict(sources or {FOOD: {"r1": F(1)}, CAP: {"r1": F(1)}}),
        import_buyers=dict(
            buyers
            or {FOOD: {HS: F(1, 2), PUB: F(1, 4), SHOP: F(1, 4)}, CAP: {FOOD: F(1, 2), HS: F(1, 2)}}
        ),
        import_cover=dict(cover or {FOOD: F(1, 2)}),
        business_demand={},
        service_import_bps={},
        wages_abroad=dict(
            abroad or {"r1": {t: F(WAGE[t]) for t in TRADES5} | {FOOD: F(10), CAP: F(15)}}
        ),
    )


def count_of(trade: str, **more: int) -> r.TradeCount:
    payroll = (WAGE[trade] * HOURS[trade] - 5) * 10**6
    fields = {
        "employee_persons": 10,
        "working_owner_persons": 0,
        "unpaid_family_persons": 0,
        "payroll_micros": payroll,
        "force": 10,
        "sites": 1,
        "machines": MACHINES.get(trade, 0),
        "public_employee_persons": 0,
        "public_payroll_micros": 0,
    }
    fields.update(more)
    return r.TradeCount(**fields)


def place_of(
    label: str,
    keys: Mapping[str, r.PlaceKeyCount],
    sellers: Mapping[str, Mapping[str, r.Seller]],
) -> r.Place:
    zero = r.PlaceKeyCount(0, 0, 0, 0, 0)
    return r.Place(
        label=label,
        hub=label[:5],
        state=label[:2],
        keys={k: keys.get(k, zero) for k in r.HOUSEHOLD_KEYS},
        trades={},
        owner_households=0,
        sellers={k: dict(sellers.get(k, {})) for k in r.HOUSEHOLD_KEYS},
        public_persons_served=0,
        public_machines=0,
    )


def census_of(places: tuple[r.Place, ...]) -> r.Census:
    trades = {t: count_of(t) for t in TRADES5}
    payroll = sum(c.payroll_micros for c in trades.values())
    households: dict[Any, r.KeyCount] = {}
    for key in r.HOUSEHOLD_KEYS:
        rows = [p.keys[key] for p in places]
        households[key] = r.KeyCount(
            accounts=len(rows),
            households=sum(x.households for x in rows),
            persons=sum(x.persons for x in rows),
            employed=sum(x.employed for x in rows),
            reserve=sum(x.reserve for x in rows),
            wage_income_micros=0,
        )
    # Every wage goes to the two lower earning keys, in proportion to their persons.
    lower, better = households["earning_lower_paid_half"], households["earning_better_paid_forty"]
    first = payroll * lower.persons // (lower.persons + better.persons)
    households["earning_lower_paid_half"] = replace(lower, wage_income_micros=first)
    households["earning_better_paid_forty"] = replace(better, wage_income_micros=payroll - first)
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


def keys_of(**counts: tuple[int, int, int, int]) -> dict[str, r.PlaceKeyCount]:
    """key -> (persons, households, employed, reserve)"""
    return {
        k: r.PlaceKeyCount(
            households=v[1], persons=v[0], employed=v[2], reserve=v[3], wage_income_micros=0
        )
        for k, v in counts.items()
    }


BASE_KEYS = {
    "earning_lower_paid_half": (60, 30, 30, 0),
    "earning_better_paid_forty": (30, 15, 15, 0),
    "earning_owner": (10, 5, 5, 0),
    "no_earner_nonowner": (100, 50, 0, 0),
    "no_earner_owner": (40, 20, 0, 0),
    "collective_residence": (10, 1, 4, 0),
}


def seller_row(wage_hs: int, wage_food: int = 20, abroad: str | None = None) -> dict[str, r.Seller]:
    return {
        "food": r.Seller(wage_food * 10**6, abroad),
        "household_services": r.Seller(wage_hs * 10**6, None),
    }


def one_place(
    *,
    wage_hs: int = 25,
    wage_food: int = 20,
    abroad: str | None = None,
    keys: Mapping[str, Any] | None = None,
) -> r.Census:
    counts = {**BASE_KEYS, **(keys or {})}
    sellers = {k: seller_row(wage_hs, wage_food, abroad) for k in r.HOUSEHOLD_KEYS}
    return census_of((place_of("10001", keys_of(**counts), sellers),))


def run(q: s.Quantities, census: r.Census, lam: Fraction = Fraction(1, 2)) -> s.Opening:
    margin = {t: F(3, 10) for t in TRADES5}
    cut = r.Recut(
        inputs={},
        households={},
        exports={},
        equipment=F(0),
        import_share={},
        domestic_output={},
        accounts_payroll={},
        accounts_jobs={},
        accounts_margin=margin,
        moved={},
        dropped={},
    )
    return s.opening(cut, census, q, lam, SMALL_SETTINGS, SMALL)


def test_imports_are_paid_at_their_sellers_prices() -> None:
    q = world_q()
    o = run(q, one_place())
    p, mu = o.prices.prices, o.prices.margins
    paid = p[FOOD] - (q.wage[FOOD] / 2) * q.hours_per_dollar[FOOD] * (1 + mu[FOOD])
    assert o.import_prices[FOOD] == paid
    saving = q.imports[FOOD] * (p[FOOD] - paid)
    assert o.import_saving[HS] == saving / 2 + q.imports[CAP] * (p[CAP] - o.import_prices[CAP]) / 2
    assert o.import_saving[PUB] == saving / 4
    assert o.shop_saving[FOOD] == saving / 4
    # A firm's part is the operating income of the trade that buys it.
    capital_saving = q.imports[CAP] * (p[CAP] - o.import_prices[CAP])
    expected = (
        p[HS] * q.output[HS] * mu[HS] / (1 + mu[HS])
        + q.unpaid_labor[HS]
        + saving / 2
        + capital_saving / 2
        - o.wear[HS]
    )
    assert o.operating_income[HS] == expected


def test_the_shop_passes_on_what_it_saves() -> None:
    q = world_q()
    o = run(q, one_place())
    p = o.prices.prices
    left = q.final[FOOD] - o.exports[FOOD]
    saving = o.shop_saving[FOOD]
    assert saving == q.imports[FOOD] * (p[FOOD] - o.import_prices[FOOD]) / 4
    assert o.household_purchases[FOOD] == p[FOOD] * left - saving
    assert o.operating_income[SHOP] == q.unpaid_labor[SHOP]
    assert o.posted["food"] == (o.household_purchases[FOOD] + o.markup * p[FOOD] * left) / left
    assert p[FOOD] * (1 + o.markup) - o.posted["food"] == saving / left
    assert abs(o.balances["1"][1]) <= 1


def test_a_shop_good_s_own_price_is_what_its_shop_pays() -> None:
    q = world_q()
    places = (
        place_of(
            "10001",
            keys_of(**BASE_KEYS),
            {k: seller_row(25, 20, "r1") for k in r.HOUSEHOLD_KEYS},
        ),
        place_of(
            "20002",
            keys_of(**{**BASE_KEYS, "collective_residence": (0, 0, 0, 0)}),
            {k: seller_row(25, 20, None) for k in r.HOUSEHOLD_KEYS},
        ),
    )
    o = run(q, census_of(places))
    p, mu = o.prices.prices, o.prices.margins
    cover = q.import_cover[FOOD]
    p_r = p[FOOD] + (q.wages_abroad["r1"][FOOD] - q.wage[FOOD]) * q.hours_per_dollar[FOOD] * (
        1 + mu[FOOD]
    )
    rho = o.markup
    first = o.own_cost[("10001", "no_earner_nonowner")]
    second = o.own_cost[("20002", "no_earner_nonowner")]
    t1q = o.tier_quantities["food"]
    assert second - first == t1q * (p[FOOD] - p_r) * cover
    own_abroad = p[FOOD] * (1 - cover) + p_r * cover + rho * p[FOOD]
    own_home = p[FOOD] * (1 + rho)
    assert own_home - own_abroad == (p[FOOD] - p_r) * cover


def test_the_benefit_is_estimated_at_each_account_s_own_cost() -> None:
    q = world_q()
    nonowner = (100, 50, 0, 0)
    residence = (10, 1, 4, 0)
    places = (
        place_of(
            "10001",
            keys_of(
                **{
                    **BASE_KEYS,
                    "no_earner_nonowner": nonowner,
                    "no_earner_owner": (0, 0, 0, 0),
                    "collective_residence": residence,
                }
            ),
            {k: seller_row(20) for k in r.HOUSEHOLD_KEYS},
        ),
        place_of(
            "20002",
            keys_of(
                **{
                    **BASE_KEYS,
                    "no_earner_nonowner": nonowner,
                    "no_earner_owner": (0, 0, 0, 0),
                    "collective_residence": (0, 0, 0, 0),
                }
            ),
            {k: seller_row(30) for k in r.HOUSEHOLD_KEYS},
        ),
    )
    o = run(q, census_of(places))
    p, mu = o.prices.prices, o.prices.margins
    rho, fee = o.markup, F(1)

    def own(wage_hs: int) -> Fraction:
        pown_food = p[FOOD] * (1 + rho * F(20) / q.wage[SHOP])
        pown_hs = p[HS] + (F(wage_hs) - q.wage[HS]) * q.hours_per_dollar[HS] * (1 + mu[HS])
        return (
            o.tier_quantities["food"] * pown_food
            + o.tier_quantities["household_services"] * pown_hs
            + fee
        )

    cheap, dear = (
        o.own_cost[("10001", "no_earner_nonowner")],
        o.own_cost[("20002", "no_earner_nonowner")],
    )
    assert cheap == own(20)
    assert dear == own(30)
    assert dear > cheap
    assert o.own_cost[("10001", "collective_residence")] == own(20)
    assert ("20002", "collective_residence") not in o.own_cost
    assert o.benefits == cheap * 100 + dear * 100 + own(20) * 6


def test_every_key_gets_its_support() -> None:
    q = world_q()
    census = one_place(keys={"no_earner_nonowner": (20, 10, 0, 10)})
    o = run(q, census)
    c1 = o.own_cost[("10001", "no_earner_nonowner")]
    support = o.tier_quantities["food"] * o.prices.prices[FOOD]
    key = "no_earner_nonowner"
    assert o.bands[key] == c1 * 20  # support 10 x s plus the benefit of the rest
    assert o.ben_by_account[("10001", key)] == c1 * 20 - 10 * support
    # With the support above the account's needs the benefit is one micro a person.
    high = run(q, one_place(keys={key: (20, 10, 0, 100)}))
    assert high.ben_by_account[("10001", key)] == F(20, 10**6)
    # The keys' money sums to wages after tax, the payout, support and benefits.
    wages = sum((F(c.payroll_micros, 10**6) for c in census.trades.values()), F(0))
    total = (1 - o.tax_rate) * wages + o.payout + o.support + sum(o.ben_by_account.values(), F(0))
    assert sum(o.bands.values(), F(0)) == total


def test_refusals_have_their_codes() -> None:
    census = one_place()
    greedy = {**COEF, FOOD: {HS: F(3, 2), PUB: F(1, 30), CAP: F(1, 40)}}
    with pytest.raises(ReferenceBuildError, match=r"^negative_residual: food"):
        run(world_q(coef=greedy), census)
    with pytest.raises(ReferenceBuildError, match=r"^negative_exports"):
        run(world_q(xs={}), census)
    # Imports worth less than extraction's exports: the export factor would be below zero.
    mining = replace(SMALL, extraction_trade=FOOD)
    one = {t: F(1) for t in TRADES5}
    zero = {t: F(0) for t in TRADES5}
    with pytest.raises(ReferenceBuildError, match=r"^negative_exports"):
        s._trade(world_q(), one, zero, SMALL_SETTINGS, mining)
    with pytest.raises(ReferenceBuildError, match=r"^tax_rate"):
        run(world_q(), one_place(keys={"no_earner_nonowner": (100, 50, 0, 10**9)}))
    with pytest.raises(ReferenceBuildError, match=r"^negative_operating_income: "):
        run(world_q(unpaid={FOOD: F(-(10**9))}), census)


def test_largest_with_nothing_kept_is_exact() -> None:
    answer = s.largest_with_nothing_kept(lambda x: max(F(0), x - F(3, 10)), 40)
    assert answer == F(329853488332, 2**40)
    with pytest.raises(ReferenceBuildError, match=r"^margin_scale_none"):
        s.largest_with_nothing_kept(lambda _x: F(1), 40)
    assert s.largest_with_nothing_kept(lambda _x: F(0), 40) == 1


# ---- a crossing service -------------------------------------------------------------

SVC, A, B = "business_services", "alpha", "beta"
SERVICE_ECONOMY = economy_of(
    (SVC, A, B),
    {SVC: "business_services", A: "alpha", B: "beta"},
    storable=frozenset(),
    capital_trade=A,
)


def service_world(m_share: Fraction) -> tuple[r.Recut, r.Census, r.Settings]:
    settings = replace(
        r.Settings(),
        periods_per_year=1000,
        work_hours_per_person=1,
        crossing=frozenset({"business_services"}),
    )
    cut = r.Recut(
        inputs={SVC: {A: F(30), B: F(30)}},
        households={},
        exports={},
        equipment=F(0),
        import_share={SVC: m_share, A: F(0), B: F(0)},
        domestic_output={SVC: F(60), A: F(300), B: F(300)},
        accounts_payroll={SVC: F(1), A: F(1), B: F(1)},
        accounts_jobs={SVC: 60, A: 30, B: 30},
        accounts_margin={SVC: F(1, 10), A: F(1, 10), B: F(1, 10)},
        moved={},
        dropped={},
    )
    persons = {SVC: 60, A: 30, B: 30}

    def count(t: str, force: int) -> r.TradeCount:
        return r.TradeCount(persons[t], 0, 0, 10**9, force, 1, 0, 0, 0)

    region = lambda key: r.Region(  # noqa: E731
        key, 1, 1, 1, 1, {SVC: 10**6, A: 10**6, B: 10**6}
    )
    census = r.Census(
        trades={SVC: count(SVC, 60), A: count(A, 100), B: count(B, 100)},
        households={},
        places=(),
        abroad={"r1": region("r1"), "r2": region("r2")},
        firm_assignment={},
        retail_assignment={},
        crossing_force={
            (SVC, "r1", A): 70,
            (SVC, "r2", A): 30,
            (SVC, "r1", B): 60,
            (SVC, "r2", B): 40,
        },
        workers_per_machine={},
        sha256="",
    )
    return cut, census, settings


def test_a_crossing_service_is_imported_by_businesses_only() -> None:
    cut, census, settings = service_world(F(1, 3))
    q = s.quantities(cut, census, settings, SERVICE_ECONOMY)
    tol = F(1, 2**50)  # a, h and sigma are on the 2^-64 grid
    assert q.imports[SVC] == 30
    assert abs(q.business_demand[SVC] - 60) <= tol  # a is on the 2^-64 grid
    assert abs(q.import_cover[SVC] - F(1, 2)) <= tol
    assert q.service_import_bps[SVC] == 5_000
    assert abs(q.import_sources[SVC]["r1"] - F(13, 20)) <= tol
    assert abs(q.import_sources[SVC]["r2"] - F(7, 20)) <= tol
    assert sum(q.import_sources[SVC].values()) == 1  # on the grid, exactly
    assert q.import_buyers[SVC].keys() == {A, B}
    assert abs(q.import_buyers[SVC][A] - F(1, 2)) <= tol
    assert sum(q.import_buyers[SVC].values()) == 1
    cut, census, settings = service_world(F(61, 121))
    with pytest.raises(ReferenceBuildError, match=r"^import_coverage: business_services"):
        s.quantities(cut, census, settings, SERVICE_ECONOMY)


# ---- a shop good's import weights ---------------------------------------------------

GOODS_ECONOMY = economy_of(
    (FOOD, HS, SHOP),
    {FOOD: "food", HS: "household_services", SHOP: "distribution_transport"},
    storable=frozenset({"food"}),
    shop_trade=SHOP,
    capital_trade=HS,
    shop_goods=frozenset({"food"}),
)


def test_a_shop_good_s_import_weights_share_one_scale() -> None:
    """H0 is USD thousands a year, the firms' weights are dollars a period: both on the period."""
    settings = replace(
        r.Settings(),
        periods_per_year=13,
        work_hours_per_person=1,
        crossing=frozenset({"food"}),
    )
    cut = r.Recut(
        inputs={FOOD: {HS: F(39, 10)}},
        households={FOOD: F(13)},
        exports={},
        equipment=F(0),
        import_share={FOOD: F(1, 2), HS: F(0), SHOP: F(0)},
        domestic_output={FOOD: F(13), HS: F(39), SHOP: F(13)},
        accounts_payroll={FOOD: F(1), HS: F(1), SHOP: F(1)},
        accounts_jobs={FOOD: 30, HS: 30, SHOP: 30},
        accounts_margin={FOOD: F(1, 10), HS: F(1, 10), SHOP: F(1, 10)},
        moved={},
        dropped={},
    )

    def count(force: int) -> r.TradeCount:
        return r.TradeCount(30, 0, 0, 10**9, force, 1, 0, 0, 0)

    region = lambda key: r.Region(key, 1, 1, 1, 1, {FOOD: 10**6})  # noqa: E731
    census = r.Census(
        trades={FOOD: count(100), HS: count(100), SHOP: count(100)},
        households={"k": r.KeyCount(1, 1, 200, 0, 0, 0)},
        places=(),
        abroad={"r1": region("r1"), "r2": region("r2")},
        firm_assignment={(FOOD, "r1", HS): 40, (FOOD, "r2", HS): 60},
        retail_assignment={(FOOD, "r1"): 50},
        crossing_force={},
        workers_per_machine={},
        sha256="",
    )
    q = s.quantities(cut, census, settings, GOODS_ECONOMY)
    tol = F(1, 2**50)
    # Firms: x[HS] = 3000 dollars a period, so force x 10: r1 400, r2 600. The shop: 50 of
    # 200 persons served times H0 13 x 1000/13 = 250 in r1. Foreign 1250, all buyers 2000.
    assert abs(q.import_cover[FOOD] - F(4, 5)) <= tol
    assert abs(q.import_sources[FOOD]["r1"] - F(13, 25)) <= tol
    assert abs(q.import_sources[FOOD]["r2"] - F(12, 25)) <= tol
    assert abs(q.import_buyers[FOOD][HS] - F(4, 5)) <= tol
    assert abs(q.import_buyers[FOOD][SHOP] - F(1, 5)) <= tol


# ---- the committed tables (slow) ---------------------------------------------------


@pytest.fixture(scope="module")
def committed() -> tuple[r.Recut, r.Census, r.Settings, s.Opening]:
    settings = r.Settings()
    cut = r.recut(r.read_accounts(ACCOUNTS), settings)
    census = r.read_census(CENSUS)
    return cut, census, settings, s.solve(cut, census, settings)


@pytest.mark.slow
def test_the_margin_factor_leaves_nothing_kept(committed: Any) -> None:
    cut, census, settings, o = committed
    assert o.kept == 0
    above = s.opening(cut, census, o.quantities, o.lam + F(1, 2**40), settings)
    assert above.kept > 0


@pytest.mark.slow
def test_every_margin_covers_its_wear(committed: Any) -> None:
    _, _, settings, o = committed
    q, p, mu = o.quantities, o.prices.prices, o.prices.margins
    private = [t for t in r.TWELVE.trades if t in r.TWELVE.product and t != PUB]
    for j in private:
        if j not in o.wear:
            continue
        cost = q.wage[j] * q.hours_per_dollar[j] + sum(
            (q.coefficients.get(i, {}).get(j, F(0)) * p[i] for i in private), F(0)
        )
        profit = q.output[j] * cost * mu[j]
        assert profit >= settings.wear_cover * o.wear[j], j


@pytest.mark.slow
def test_the_four_balances_close_at_the_exact_solve(committed: Any) -> None:
    *_, o = committed
    for name, (flow, residual) in o.balances.items():
        assert abs(residual) <= flow / 10**9, name


@pytest.mark.slow
def test_every_job_is_needed_at_the_exact_solve(committed: Any) -> None:
    *_, o = committed
    q = o.quantities
    for j, hours in q.hours.items():
        # `h` is held on the 2^-64 grid, so the product is the hours to within x / 2^65.
        assert abs(q.hours_per_dollar[j] * q.output[j] - hours) <= q.output[j] / 2**65, j


@pytest.mark.slow
def test_the_business_services_imports_meet_the_accounts(committed: Any) -> None:
    *_, o = committed
    q = o.quantities
    t = "business_services"
    written = F(q.service_import_bps[t], 10_000) * q.business_demand[t]
    assert abs(written - q.imports[t]) <= q.business_demand[t] / 10_000
    figures = {
        "lam": o.lam,
        "t": o.tax_rate,
        "f": o.fund_share,
        "kx": o.export_factor,
        "BEN": o.benefits,
        "cbar": o.tier_unit,
        "C": o.spending,
        "G": o.grant,
        "E": o.balances["4"][0],
    }
    print({k: f"{(v * 10**6).__floor__()}e-6" for k, v in figures.items()})  # noqa: T201
    print(  # noqa: T201
        "service_import_bps",
        q.service_import_bps,
        "rounds",
        o.prices.rounds,
        "floored",
        sorted(o.prices.floored),
        "shop_saving",
        {k: (v * 10**3).__floor__() for k, v in o.shop_saving.items()},
    )
