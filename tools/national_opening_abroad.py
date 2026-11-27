#!/usr/bin/env python3
"""The builder of the rebuilt national opening, part 5 (Task 12 of stage 5).

Each foreign region's mix of jobs and its share of trade (O11). A region sells to the country
what the census says it sells, needs the recipes' inputs, machines and shop hours to make it and
to feed its own households, and buys from the country one figure a region times one a good, so
that each region's trade with the United States balances, the regions together take the
country's exports of each good, and the region's employed are needed.

Every figure is an `int` or a `Fraction`; a `float` anywhere is a defect. Every rounding to an
integer names its rule where it is done. Every refusal is a `ReferenceBuildError` with a fixed
code before the first colon.

Keys. Products are keyed by PRODUCT (`food`, `resources`, ...); trades by TRADE; regions by the
census's key (`canada`, ..., `dependency`).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Final

from make_national_county_reference import ReferenceBuildError
from national_opening_recut import TWELVE, Census, Economy, HouseholdKey, Region, Settings, half_up
from national_opening_solve import Opening
from national_opening_tiers import (
    SCALE_LIMIT_BPS,
    Account,
    Row,
    Tiers,
    buy,
    luxury_scale_bps,
    shape_of,
    tier_one_rows,
    want_rows,
)
from national_opening_units import (
    DEPOSIT,
    Written,
    machine_life_batches,
    region_maker_prices,
    region_prices,
)

SHARE_GRID: Final = 2**40  # beta_r and c_i: rounded to the nearest 1/SHARE_GRID, a half up
BASIS: Final = 10_000
MAX_ROUNDS: Final = 100
MAX_MICROS_BITS: Final = 70  # the closure searches money a person below 2^70 micros
DEPENDENCY: Final = "dependency"
# `UsDependency::m49` in wire order: the compiler admits a dependency's place by these codes.
DEPENDENCY_CODES: Final[tuple[str, ...]] = ("016", "316", "580", "630", "581", "850")
POOLED_EXTERNAL: Final = "pooled-external"  # `HouseholdBudgetKey::PooledExternal`'s label
# The region's households are one account of a non-residence key (household needs included).
_KEY: Final[HouseholdKey] = "earning_lower_paid_half"
_ZERO: Final = Fraction(0)
_ONE: Final = Fraction(1)


def _fail(code: str, what: str = "") -> ReferenceBuildError:
    return ReferenceBuildError(f"{code}: {what}" if what else code)


@dataclass(frozen=True)
class RegionOpening:
    key: str
    function_weights_bps: tuple[int, ...]  # twelve, in the policy's Ord order: business, capital,
    # housing, consumer goods, distribution, energy, extraction, food, household services,
    # leisure, manufacturing, public; each >= 1, sum 10,000
    export_bps: Mapping[
        str, int
    ]  # by crossing product: the five priced goods and business services
    money_per_person_micros: int
    sales_micros: int  # a period, to the United States
    purchases_micros: int  # a period, from it, at the exact shares of the solve
    luxury_scale_bps: int | None
    # Beyond the interface of the task, for the metadata.
    reach: tuple[Fraction, Fraction, Fraction] = (
        _ZERO,
        _ZERO,
        _ZERO,
    )  # money spent over cost, by tier
    rounds: int = 0
    # A period's purchases at the WRITTEN shares (`export_bps`, as the compiler applies them).
    purchases_written_micros: int = 0
    sells_units: Mapping[str, Fraction] = field(default_factory=dict)  # to the country, by product
    buys_units: Mapping[str, Fraction] = field(default_factory=dict)  # from the country, by product


# --------------------------------------------------------------------------------------
# Weights (decision 7).


def function_weights(hours: Mapping[str, Fraction], trades: Sequence[str]) -> tuple[int, ...]:
    """A region's hours by trade shared over 10,000 by largest remainder (ties: the trade first in
    `trades`), then each trade at 0 takes 1 from the trade with most (the policy refuses 0). The
    answer is in the order of `trades`; no hours at all is `abroad_unbalanced: weights`."""
    total = sum((hours.get(t, _ZERO) for t in trades), _ZERO)
    if total <= 0:
        raise _fail("abroad_unbalanced", "weights")
    exact = [BASIS * hours.get(t, _ZERO) / total for t in trades]
    # Rounding rule: the floor of each share, then one each to the largest remainders.
    shares = [x.__floor__() for x in exact]
    order = sorted(range(len(trades)), key=lambda i: (-(exact[i] - shares[i]), i))
    for i in order[: BASIS - sum(shares)]:
        shares[i] += 1
    for i, share in enumerate(shares):
        if share == 0:
            largest = max(range(len(trades)), key=lambda j: (shares[j], -j))
            shares[largest] -= 1
            shares[i] = 1
    return tuple(shares)


# --------------------------------------------------------------------------------------
# The model every region shares: recipes, machines, the inverse, the tiers' rows.


@dataclass(frozen=True)
class _Model:
    products: tuple[str, ...]
    trade_of: Mapping[str, str]
    a: Mapping[str, Mapping[str, Fraction]]  # a[i][j]: units of i a unit of j
    hours_per_unit: Mapping[str, Fraction]  # by product
    k: Mapping[str, Mapping[str, Fraction]]  # (I - A)^-1
    g: Mapping[str, Fraction]  # hours one more unit of net demand of j needs: sum_i h_i K[i][j]
    shop_hours: Mapping[str, Fraction]  # shop goods: hours a unit at the shop
    rows: tuple[Row, ...]
    tiers: tuple[list[Row], list[Row], list[Row]]
    hpp: int


def _invert(matrix: list[list[Fraction]]) -> list[list[Fraction]]:
    """The inverse by Gauss-Jordan in `Fraction`s, the first non-zero pivot of each column."""
    n = len(matrix)
    work = [[*row, *(_ONE if i == j else _ZERO for j in range(n))] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if work[r][col] != 0), None)
        if pivot is None:
            raise _fail("abroad_singular")
        work[col], work[pivot] = work[pivot], work[col]
        scale = work[col][col]
        work[col] = [x / scale for x in work[col]]
        for r in range(n):
            if r != col and work[r][col] != 0:
                factor = work[r][col]
                work[r] = [x - factor * y for x, y in zip(work[r], work[col], strict=True)]
    return [row[n:] for row in work]


def _model(w: Written, t: Tiers, settings: Settings, economy: Economy) -> _Model:
    trade_of = {product: trade for trade, product in economy.product.items()}
    products = tuple(sorted(economy.product[trade] for trade in w.recipes))
    hpp = settings.work_hours_per_person
    a: dict[str, dict[str, Fraction]] = {i: {} for i in products}
    hours: dict[str, Fraction] = {}
    equipment = economy.product.get(economy.capital_trade)
    for trade, recipe in sorted(w.recipes.items()):
        j = economy.product[trade]
        n = recipe.output_units_per_batch
        hours[j] = Fraction(recipe.labor_hours_per_batch, n)
        for good, count in recipe.inputs.items():
            if good == DEPOSIT:
                continue  # the deposit is the extraction site's own, not a product
            a[good][j] = a[good].get(j, _ZERO) + Fraction(count, n)
        workers = w.workers_per_machine.get(trade)
        if workers is not None and equipment is not None:
            # Task 6b: a machine serves `machine_life_batches` batches, a batch makes `n` units.
            life = machine_life_batches(
                hpp, workers, w.machine_life_periods, recipe.labor_hours_per_batch
            )
            a[equipment][j] = a[equipment].get(j, _ZERO) + Fraction(1, n * life)
    size = len(products)
    identity_minus_a = [
        [(_ONE if i == j else _ZERO) - a[products[i]].get(products[j], _ZERO) for j in range(size)]
        for i in range(size)
    ]
    inverse = _invert(identity_minus_a)
    k = {products[i]: {products[j]: inverse[i][j] for j in range(size)} for i in range(size)}
    g = {j: sum((hours[i] * k[i][j] for i in products), _ZERO) for j in products}
    shop_hours = {
        product: Fraction(made.handling[0], made.handling[1])
        for product, made in sorted(w.products.items())
        if made.handling is not None
    }
    shape = shape_of(settings, economy)
    rows = (
        *tier_one_rows(_KEY, shape, economy),
        *want_rows(
            shape,
            {p: Fraction(v) for p, v in t.comfort.items()},
            {p: Fraction(v) for p, v in t.luxury.items()},
            drop_zero=True,
        ),
    )
    tiers: tuple[list[Row], list[Row], list[Row]] = ([], [], [])
    for row in rows:
        tiers[row.tier - 1].append(row)
    return _Model(products, trade_of, a, hours, k, g, shop_hours, rows, tiers, hpp)


# --------------------------------------------------------------------------------------
# One region at given sales and purchases: its closure (decision 5).


@dataclass(frozen=True)
class _Solved:
    mpp: int
    final: Mapping[str, Fraction]  # f: what its households buy, units a period
    output: Mapping[str, Fraction]  # y
    required: Mapping[str, Fraction]  # R for each crossing product
    hours_by_trade: Mapping[str, Fraction]
    scale_bps: int | None
    reach: tuple[Fraction, Fraction, Fraction]


def _scale_bps(account: Account, tiers: tuple[list[Row], list[Row], list[Row]]) -> int | None:
    """Task 11, decision 10 (the one rule, in `national_opening_tiers`) without its bound, which
    `_finish` checks."""
    return luxury_scale_bps(account, tiers, bounded=False)


class _Region:
    """The closure of one region: `hours(mpp)` rises with the money a person."""

    def __init__(
        self,
        model: _Model,
        region: Region,
        prices: Mapping[str, int],
        sells: Mapping[str, Fraction],
        buys: Mapping[str, Fraction],
    ) -> None:
        self.model = model
        self.region = region
        self.prices = prices
        self.sells = sells
        self.buys = buys

    def _bought(self, mpp: int) -> tuple[Mapping[str, Fraction], int | None, tuple[Fraction, ...]]:
        region = self.region
        account = Account(
            region.key,
            _KEY,
            region.persons,
            region.households,
            region.employed,
            mpp * region.persons,
            self.prices,
        )
        bps = _scale_bps(account, self.model.tiers)
        scale = None if bps is None else Fraction(bps, BASIS)
        got = buy(account, self.model.rows, self.prices, scale)
        return got.units, bps, got.reach

    def _net(self, final: Mapping[str, Fraction]) -> dict[str, Fraction]:
        return {
            p: final.get(p, _ZERO) + self.sells.get(p, _ZERO) - self.buys.get(p, _ZERO)
            for p in self.model.products
        }

    def hours(self, mpp: int) -> Fraction:
        """The hours its output needs: the recipes' and the shop's."""
        final = self._bought(mpp)[0]
        net = self._net(final)
        work = sum((self.model.g[p] * net[p] for p in self.model.products), _ZERO)
        retail = sum((final.get(p, _ZERO) * h for p, h in self.model.shop_hours.items()), _ZERO)
        return work + retail

    def solve(self, hint: int, services: frozenset[str], economy: Economy) -> _Solved:
        target = self.region.employed * self.model.hpp
        mpp = _smallest(self.hours, target, hint, self.region.key)
        final, bps, reach = self._bought(mpp)
        net = self._net(final)
        model = self.model
        y = {
            i: sum((model.k[i][j] * net[j] for j in model.products), _ZERO) for i in model.products
        }
        used = {
            i: sum((model.a[i].get(j, _ZERO) * y[j] for j in model.products), _ZERO)
            for i in model.products
        }
        required = {
            i: used[i] + (_ZERO if i in services else final.get(i, _ZERO)) for i in model.products
        }
        by_trade = {model.trade_of[i]: y[i] * model.hours_per_unit[i] for i in model.products}
        if economy.shop_trade is not None:
            by_trade[economy.shop_trade] = sum(
                (final.get(p, _ZERO) * h for p, h in model.shop_hours.items()), _ZERO
            )
        return _Solved(mpp, final, y, required, by_trade, bps, (reach[0], reach[1], reach[2]))


def _smallest(hours: Callable[[int], Fraction], target: int, hint: int, region: str) -> int:
    """The smallest whole number of micros a person whose hours are at least `target`. The hours
    at 0 already past `target` is `abroad_unbalanced: <region>`; so is no such number below
    2^MAX_MICROS_BITS. Found by galloping out from `hint` and then bisecting."""
    if hours(0) > target:
        raise _fail("abroad_unbalanced", region)
    if hours(0) == target:
        return 0
    limit = 1 << MAX_MICROS_BITS
    lo, hi = 0, max(1, hint)  # hours(lo) < target
    if hours(hi) >= target:
        step = 1
        while hi - step > 0 and hours(hi - step) >= target:
            hi -= step
            step *= 2
        lo = max(0, hi - step)
    else:
        step = 1
        lo = hi
        while True:
            hi = lo + step
            if hi > limit:
                raise _fail("abroad_unbalanced", region)
            if hours(hi) >= target:
                break
            lo = hi
            step *= 2
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if hours(mid) >= target:
            hi = mid
        else:
            lo = mid
    return hi


# --------------------------------------------------------------------------------------
# What each region sells and the countries' exports in units.


def _crossing_trades(settings: Settings, economy: Economy) -> list[str]:
    return [t for t in economy.trades if economy.product.get(t) in settings.crossing]


def _sells(
    o: Opening, w: Written, region: str, settings: Settings, economy: Economy
) -> dict[str, Fraction]:
    """`s[r][i] = sigma[i][r] x m[i] / u[i]` units a period (decision 2)."""
    q = o.quantities
    out: dict[str, Fraction] = {}
    for trade in _crossing_trades(settings, economy):
        product = economy.product[trade]
        share = q.import_sources.get(trade, {}).get(region, _ZERO)
        if share > 0 and q.imports.get(trade, _ZERO) > 0:
            out[product] = share * q.imports[trade] / w.products[product].dollars_per_unit
    return out


def _grid(value: Fraction) -> Fraction:
    # Rounding rule: the nearest 1/SHARE_GRID, a half up.
    return Fraction(half_up(value * SHARE_GRID), SHARE_GRID)


def _report(units: Fraction) -> Fraction:
    """Units for the record: the nearest millionth of a unit, a half up (the exact figure holds
    thousands of digits)."""
    return Fraction(half_up(units * 10**6), 10**6)


def _written(
    solved: _Solved,
    export_bps: Mapping[str, int],
    trades: Sequence[str],
) -> tuple[tuple[int, ...], tuple[tuple[str, int], ...], int | None]:
    return (
        function_weights(solved.hours_by_trade, trades),
        tuple(sorted(export_bps.items())),
        solved.scale_bps,
    )


def regions(
    o: Opening,
    census: Census,
    w: Written,
    t: Tiers,
    settings: Settings,
    economy: Economy = TWELVE,
) -> Mapping[str, RegionOpening]:
    """Each foreign region's opening (decisions 1 to 9), the twelve counterparts and the
    dependency: its weights, its shares of what it buys from the country, its money a person,
    its sales and purchases, and its luxury scale."""
    model = _model(w, t, settings, economy)
    trades = sorted(economy.trades)
    goods = sorted(economy.product[tr] for tr in _crossing_trades(settings, economy))
    services = frozenset(p for p in goods if p not in economy.storable)
    keys = sorted(census.abroad)
    sells = {k: _sells(o, w, k, settings, economy) for k in keys}
    exports = {
        p: o.exports.get(model.trade_of[p], _ZERO) / w.products[p].dollars_per_unit for p in goods
    }
    us_price = {p: w.products[p].price_micros for p in goods}
    zero_bps = dict.fromkeys(goods, 0)

    def solve_all(
        bps: Mapping[str, Mapping[str, int]],
        buys: Mapping[str, Mapping[str, Fraction]],
        hints: Mapping[str, int],
    ) -> dict[str, _Solved]:
        out: dict[str, _Solved] = {}
        for k in keys:
            prices = region_prices(w, o, census.abroad[k].wage_micros, census, bps[k], economy)
            region = _Region(model, census.abroad[k], prices, sells[k], buys[k])
            out[k] = region.solve(hints.get(k, 0), services, economy)
        return out

    maker_prices = {
        k: region_maker_prices(w, o, census.abroad[k].wage_micros, economy) for k in keys
    }
    sales_value = {
        k: sum((sells[k].get(p, _ZERO) * maker_prices[k][p] for p in goods), _ZERO) for k in keys
    }

    # Round 0: b = 0 gives R0 and the start of c.
    none = {k: dict(zero_bps) for k in keys}
    solved = solve_all(none, {k: {} for k in keys}, {})
    beta = dict.fromkeys(keys, _ONE)
    c: dict[str, Fraction] = {}
    for p in goods:
        total = sum((solved[k].required[p] for k in keys), _ZERO)
        if exports[p] > 0 and total == 0:
            raise _fail("abroad_unbalanced", p)
        c[p] = _grid(exports[p] / total) if total > 0 else _ZERO
    previous: dict[str, tuple[tuple[int, ...], tuple[tuple[str, int], ...], int | None]] = {}
    rounds = 0
    while rounds < MAX_ROUNDS:
        rounds += 1
        # The balance and the mix, on the last round's requirements (decision 6).
        for k in keys:
            bought = sum((us_price[p] * c[p] * solved[k].required[p] for p in goods), _ZERO)
            if sales_value[k] > 0 and bought == 0:
                raise _fail("abroad_unbalanced", k)
            beta[k] = _grid(sales_value[k] / bought) if sales_value[k] > 0 else _ZERO
        for p in goods:
            total = sum((beta[k] * solved[k].required[p] for k in keys), _ZERO)
            if exports[p] > 0 and total == 0:
                raise _fail("abroad_unbalanced", p)
            c[p] = _grid(exports[p] / total) if total > 0 else _ZERO
        buys = {k: {p: beta[k] * c[p] * solved[k].required[p] for p in goods} for k in keys}
        # Rounding rule: a share in basis points, half up.
        bps = {k: {p: half_up(BASIS * beta[k] * c[p]) for p in goods} for k in keys}
        solved = solve_all(bps, buys, {k: solved[k].mpp for k in keys})
        now = {k: _written(solved[k], bps[k], trades) for k in keys}
        if now == previous:
            break
        previous = now
    else:
        raise _fail("abroad_unsettled")
    return _finish(solved, sells, beta, c, goods, us_price, sales_value, trades, rounds)


def _finish(
    solved: Mapping[str, _Solved],
    sells: Mapping[str, Mapping[str, Fraction]],
    beta: Mapping[str, Fraction],
    c: Mapping[str, Fraction],
    goods: Sequence[str],
    us_price: Mapping[str, int],
    sales_value: Mapping[str, Fraction],
    trades: Sequence[str],
    rounds: int,
) -> dict[str, RegionOpening]:
    out: dict[str, RegionOpening] = {}
    for k in sorted(solved):
        s = solved[k]
        bps = {p: half_up(BASIS * beta[k] * c[p]) for p in goods}
        for p, share in bps.items():
            if share > BASIS:
                raise _fail("export_share", f"{k}/{p}")
        if any(y < 0 for y in s.output.values()):
            raise _fail("abroad_unbalanced", k)
        if s.scale_bps is not None and s.scale_bps > SCALE_LIMIT_BPS:
            raise _fail("luxury_scale_bound", k)
        buys = {p: beta[k] * c[p] * s.required[p] for p in goods}
        out[k] = RegionOpening(
            key=k,
            function_weights_bps=function_weights(s.hours_by_trade, trades),
            export_bps=bps,
            money_per_person_micros=s.mpp,
            # Rounding rule: a period's money, half up.
            sales_micros=half_up(sales_value[k]),
            purchases_micros=half_up(sum((us_price[p] * buys[p] for p in goods), _ZERO)),
            purchases_written_micros=half_up(
                sum((us_price[p] * Fraction(bps[p], BASIS) * s.required[p] for p in goods), _ZERO)
            ),
            luxury_scale_bps=s.scale_bps,
            reach=s.reach,
            rounds=rounds,
            sells_units={p: _report(sells[k][p]) for p in sorted(sells[k])},
            buys_units={p: _report(buys[p]) for p in goods},
        )
    return out


def scale_rows(opening: Mapping[str, RegionOpening]) -> dict[str, int]:
    """The luxury scales abroad as the compiler admits them (decision 9): a counterpart is
    `<key>:pooled-external`; the dependency, whose places the compiler admits by M49 code, is six
    rows at the same scale. Sorted by account."""
    rows: dict[str, int] = {}
    for key, region in sorted(opening.items()):
        if region.luxury_scale_bps is None:
            continue
        places = DEPENDENCY_CODES if key == DEPENDENCY else (key,)
        for place in places:
            rows[f"{place}:{POOLED_EXTERNAL}"] = region.luxury_scale_bps
    return dict(sorted(rows.items()))


__all__ = [
    "DEPENDENCY",
    "DEPENDENCY_CODES",
    "POOLED_EXTERNAL",
    "SHARE_GRID",
    "RegionOpening",
    "function_weights",
    "regions",
    "scale_rows",
]
