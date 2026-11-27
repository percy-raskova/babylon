#!/usr/bin/env python3
"""The builder of the rebuilt national opening, part 2 (Task 10 of stage 5).

Quantities, prices, margins, trade and taxes: the national opening at one margin
factor, and the factor itself. Every figure is an `int` or a `Fraction`; a `float`
anywhere is a defect. Every rounding to an integer names its rule where it is done.
Every refusal is a `ReferenceBuildError` with a fixed code before the first colon.

Keys. Everything the solve holds is keyed by TRADE (`food`, `energy_utilities`, ...),
the buyer or the maker, except `Opening.tier_one`, `Opening.posted` and
`Opening.tier_quantities`, which are keyed by the PRODUCT of a need (`food`, `utility`,
...), as the economy names its needs.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Final

from make_national_county_reference import ReferenceBuildError
from national_opening_recut import (
    HOUSEHOLD_KEYS,
    TWELVE,
    Census,
    Economy,
    HouseholdKey,
    Place,
    Recut,
    Seller,
    Settings,
    TradeCount,
    half_up,
    to_grid,
    up_to_grid,
)

GRID: Final = 2**64  # coefficients a, h, xs, IMP, sigma: to_grid(., GRID)
FLOOR_GRID: Final = 2**48  # floored margins: up_to_grid(., FLOOR_GRID)
MICROS: Final = 10**6  # equipment money e: to_grid(., MICROS) dollars
MAX_ROUNDS: Final = 100
_ZERO: Final = Fraction(0)
_ONE: Final = Fraction(1)
_NO_EARNER: Final[tuple[HouseholdKey, ...]] = ("no_earner_nonowner", "no_earner_owner")
_RESIDENCE: Final[HouseholdKey] = "collective_residence"
_EARNING: Final[tuple[HouseholdKey, ...]] = (
    "earning_lower_paid_half",
    "earning_better_paid_forty",
    "earning_owner",
)


def _fail(code: str, what: str = "") -> ReferenceBuildError:
    return ReferenceBuildError(f"{code}: {what}" if what else code)


def _private(economy: Economy) -> list[str]:
    """The trades with a price: every trade with a product but public provision."""
    return [t for t in economy.trades if t in economy.product and t != economy.public_trade]


def _trade_of(economy: Economy) -> dict[str, str]:
    return {product: trade for trade, product in economy.product.items()}


def _shares_on_grid(weights: Mapping[str, Fraction]) -> dict[str, Fraction]:
    """Shares of `weights` on GRID (each `to_grid`, half up), the drift of the rounding put on
    the largest share (the first in key order on a tie) so that the sum is exactly 1."""
    total = sum(weights.values(), _ZERO)
    out = {k: to_grid(w / total, GRID) for k, w in sorted(weights.items()) if w > 0}
    drift = _ONE - sum(out.values(), _ZERO)
    if drift != 0:
        largest = max(sorted(out), key=lambda k: out[k])
        out[largest] += drift
    return out


# --------------------------------------------------------------------------------------
# Quantities.


@dataclass(frozen=True)
class Quantities:
    output: Mapping[str, Fraction]
    coefficients: Mapping[str, Mapping[str, Fraction]]
    hours_per_dollar: Mapping[str, Fraction]
    hours: Mapping[str, int]
    wage: Mapping[str, Fraction]
    unpaid_labor: Mapping[str, Fraction]
    export_share: Mapping[str, Fraction]
    imports: Mapping[str, Fraction]
    final: Mapping[str, Fraction]
    machines: Mapping[str, int]
    import_sources: Mapping[str, Mapping[str, Fraction]]
    import_buyers: Mapping[str, Mapping[str, Fraction]]
    import_cover: Mapping[str, Fraction]
    business_demand: Mapping[str, Fraction]
    service_import_bps: Mapping[str, int]
    wages_abroad: Mapping[str, Mapping[str, Fraction]]


def _imports_of_goods(
    trade: str,
    product: str,
    recut: Recut,
    census: Census,
    a: Mapping[str, Mapping[str, Fraction]],
    h: Mapping[str, Fraction],
    machines: Mapping[str, int],
    persons: int,
    settings: Settings,
    economy: Economy,
) -> tuple[dict[str, Fraction], dict[str, Fraction], Fraction]:
    """Who sells the imports of a stored good (decision 3): per region the weights by buying
    trade (the shop's part under the shop trade), and the cover `IMP x total / foreign`."""
    hpp = settings.work_hours_per_person
    buyers = [t for t in economy.trades if t != economy.shop_trade]
    shop_good = product in economy.shop_goods and economy.shop_trade is not None
    is_equipment = trade == economy.capital_trade
    # H0 is USD thousands a year; the firms' weights are accounts dollars a period: x1000/periods.
    household_scale = Fraction(1000, settings.periods_per_year)

    def firm_weight(region: str, j: str) -> Fraction:
        force = census.firm_assignment.get((product, region, j), 0)
        if force == 0:
            return _ZERO
        if is_equipment:  # machines are the buyers' volume
            of = census.trades[j].force
            return Fraction(force * machines.get(j, 0), of) if of > 0 else _ZERO
        coefficient = a.get(trade, {}).get(j, _ZERO)
        if coefficient == 0 or h.get(j, _ZERO) == 0:
            return _ZERO
        return force * hpp * coefficient / h[j]

    by_region: dict[str, dict[str, Fraction]] = {}
    for region in sorted(census.abroad):
        row: dict[str, Fraction] = {}
        for j in buyers:
            w = firm_weight(region, j)
            if w > 0:
                row[j] = w
        if shop_good and economy.shop_trade is not None:
            served = census.retail_assignment.get((product, region), 0)
            w = Fraction(served) * household_scale * recut.households.get(trade, _ZERO) / persons
            if w > 0:
                row[economy.shop_trade] = w
        if row:
            by_region[region] = row
    foreign = sum((w for row in by_region.values() for w in row.values()), _ZERO)
    total = _ZERO
    for j in buyers:
        if is_equipment:
            total += machines.get(j, 0)
        else:
            coefficient = a.get(trade, {}).get(j, _ZERO)
            if coefficient > 0 and h.get(j, _ZERO) > 0:
                total += census.trades[j].force * hpp * coefficient / h[j]
    if shop_good:
        total += household_scale * recut.households.get(trade, _ZERO)
    if foreign == 0 or total == 0:
        raise _fail("import_weights", product)
    region_weight = {r: sum(row.values(), _ZERO) for r, row in by_region.items()}
    buyer_weight: dict[str, Fraction] = {}
    for row in by_region.values():
        for j, w in row.items():
            buyer_weight[j] = buyer_weight.get(j, _ZERO) + w
    cover = recut.import_share[trade] * total / foreign
    return region_weight, buyer_weight, cover


def _imports_of_service(
    trade: str,
    product: str,
    census: Census,
    a: Mapping[str, Mapping[str, Fraction]],
    h: Mapping[str, Fraction],
    settings: Settings,
    economy: Economy,
) -> tuple[dict[str, Fraction], dict[str, Fraction]]:
    """A crossing service is bought abroad by businesses only (E2): the weights of a region
    are `crossing_force x hours per person x a / h` over the trades that buy it."""
    hpp = settings.work_hours_per_person
    region_weight: dict[str, Fraction] = {}
    buyer_weight: dict[str, Fraction] = {}
    for region in sorted(census.abroad):
        for j in economy.trades:
            if j == economy.shop_trade:
                continue
            force = census.crossing_force.get((product, region, j), 0)
            coefficient = a.get(trade, {}).get(j, _ZERO)
            if force == 0 or coefficient == 0 or h.get(j, _ZERO) == 0:
                continue
            w = force * hpp * coefficient / h[j]
            region_weight[region] = region_weight.get(region, _ZERO) + w
            buyer_weight[j] = buyer_weight.get(j, _ZERO) + w
    if not region_weight:
        raise _fail("import_weights", product)
    return region_weight, buyer_weight


def quantities(
    recut: Recut, census: Census, settings: Settings, economy: Economy = TWELVE
) -> Quantities:
    """The quantities of the opening (decisions 1 to 3): hours and wages from the census,
    output and coefficients from the re-cut, imports and who sells them."""
    hpp = settings.work_hours_per_person
    hours: dict[str, int] = {}
    wage: dict[str, Fraction] = {}
    unpaid: dict[str, Fraction] = {}
    for j in economy.trades:
        count = census.trades[j]
        at_work = count.employee_persons + count.working_owner_persons + count.unpaid_family_persons
        if count.employee_persons <= 0 or recut.accounts_jobs[j] <= 0:
            raise _fail("quantities_empty", j)
        hours[j] = at_work * hpp
        # Rounding rule: the wage is the integer floor of micros an hour (the compiler's).
        wage_micros = count.payroll_micros // (count.employee_persons * hpp)
        wage[j] = Fraction(wage_micros, MICROS)
        unpaid[j] = wage[j] * hours[j] - Fraction(count.payroll_micros, MICROS)
    output: dict[str, Fraction] = {}
    for j in economy.trades:
        kappa = Fraction(hours[j], hpp) / recut.accounts_jobs[j]
        # Rounding rule: accounts dollars a period, half up.
        output[j] = Fraction(
            half_up(recut.domestic_output[j] * 1000 / settings.periods_per_year * kappa)
        )
    coefficients: dict[str, dict[str, Fraction]] = {}
    for i, row in recut.inputs.items():
        for j, value in row.items():
            if value != 0 and recut.domestic_output[j] != 0:
                coefficients.setdefault(i, {})[j] = to_grid(value / recut.domestic_output[j], GRID)
    hpd: dict[str, Fraction] = {}
    for j in economy.trades:
        if output[j] == 0:
            raise _fail("quantities_empty", j)
        hpd[j] = to_grid(Fraction(hours[j]) / output[j], GRID)
    xs = {
        i: to_grid(value / recut.domestic_output[i], GRID)
        for i, value in recut.exports.items()
        if recut.domestic_output[i] != 0
    }
    crossing_trades = [t for t in economy.trades if economy.product.get(t) in settings.crossing]
    imp = {t: to_grid(recut.import_share[t], GRID) for t in crossing_trades}
    imports = dict.fromkeys(economy.trades, _ZERO)
    for t in crossing_trades:
        # Rounding rule: imports a period, half up.
        imports[t] = Fraction(half_up(output[t] * imp[t] / (1 - imp[t])))
    final: dict[str, Fraction] = {}
    for i in economy.trades:
        if i not in economy.product:
            continue
        used = sum(
            (coefficients.get(i, {}).get(j, _ZERO) * output[j] for j in economy.trades), _ZERO
        )
        final[i] = output[i] + imports[i] - used
    machines = {
        j: (0 if j == economy.shop_trade else census.trades[j].machines) for j in economy.trades
    }
    persons = sum(c.persons for c in census.households.values())
    sources: dict[str, dict[str, Fraction]] = {}
    buyers: dict[str, dict[str, Fraction]] = {}
    cover: dict[str, Fraction] = {}
    demand: dict[str, Fraction] = {}
    bps: dict[str, int] = {}
    # The coefficients and hours are on their grids: the weights read them as held.
    recut_on_grid = Recut(
        inputs=recut.inputs,
        households=recut.households,
        exports=recut.exports,
        equipment=recut.equipment,
        import_share=imp,
        domestic_output=recut.domestic_output,
        accounts_payroll=recut.accounts_payroll,
        accounts_jobs=recut.accounts_jobs,
        accounts_margin=recut.accounts_margin,
        moved=recut.moved,
        dropped=recut.dropped,
    )
    for t in crossing_trades:
        if imp[t] == 0:
            continue
        product = economy.product[t]
        if product in economy.storable:
            region_w, buyer_w, cover[t] = _imports_of_goods(
                t,
                product,
                recut_on_grid,
                census,
                coefficients,
                hpd,
                machines,
                persons,
                settings,
                economy,
            )
        else:
            region_w, buyer_w = _imports_of_service(
                t, product, census, coefficients, hpd, settings, economy
            )
            demand[t] = sum(
                (
                    coefficients.get(t, {}).get(j, _ZERO) * output[j]
                    for j in economy.trades
                    if j != economy.shop_trade
                ),
                _ZERO,
            )
            if demand[t] == 0:
                raise _fail("import_weights", product)
            cover[t] = imports[t] / demand[t]
            if cover[t] > 1:
                raise _fail("import_coverage", product)
            # Rounding rule: basis points written, half up.
            bps[t] = half_up(10_000 * cover[t])
        sources[t] = _shares_on_grid(region_w)
        buyers[t] = _shares_on_grid(buyer_w)
    wages_abroad = {
        region: {
            t: Fraction(r.wage_micros[t], MICROS) for t in economy.trades if t in r.wage_micros
        }
        for region, r in sorted(census.abroad.items())
    }
    return Quantities(
        output=output,
        coefficients=coefficients,
        hours_per_dollar=hpd,
        hours=hours,
        wage=wage,
        unpaid_labor=unpaid,
        export_share=xs,
        imports=imports,
        final=final,
        machines=machines,
        import_sources=sources,
        import_buyers=buyers,
        import_cover=cover,
        business_demand=demand,
        service_import_bps=bps,
        wages_abroad=wages_abroad,
    )


# --------------------------------------------------------------------------------------
# Prices.


@dataclass(frozen=True)
class Prices:
    prices: Mapping[str, Fraction]
    margins: Mapping[str, Fraction]
    floored: frozenset[str]
    equipment: Fraction
    rounds: int


def _gauss(matrix: list[list[Fraction]], rhs: list[Fraction]) -> list[Fraction]:
    """Gaussian elimination in Fractions, rows and columns in order, the first non-zero pivot
    of each column; no pivot is `prices_singular`."""
    n = len(rhs)
    rows = [[*matrix[r], rhs[r]] for r in range(n)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if rows[r][col] != 0), None)
        if pivot is None:
            raise _fail("prices_singular")
        rows[col], rows[pivot] = rows[pivot], rows[col]
        lead = rows[col][col]
        rows[col] = [v / lead for v in rows[col]]
        for r in range(n):
            if r != col and rows[r][col] != 0:
                factor = rows[r][col]
                rows[r] = [v - factor * w for v, w in zip(rows[r], rows[col], strict=True)]
    return [rows[r][n] for r in range(n)]


def _prices_at(
    q: Quantities, mu: Mapping[str, Fraction], private: list[str]
) -> dict[str, Fraction]:
    """`p[j] = (1 + mu[j]) (wage[j] h[j] + sum_i a[i][j] p[i])`, solved exactly (decision 4)."""
    index = {t: n for n, t in enumerate(private)}
    matrix: list[list[Fraction]] = []
    rhs: list[Fraction] = []
    for j in private:
        factor = 1 + mu[j]
        row = [_ZERO] * len(private)
        for i in private:
            row[index[i]] -= factor * q.coefficients.get(i, {}).get(j, _ZERO)
        row[index[j]] += 1
        matrix.append(row)
        rhs.append(factor * q.wage[j] * q.hours_per_dollar[j])
    solved = _gauss(matrix, rhs)
    return {t: solved[index[t]] for t in private}


def _region_price(
    q: Quantities, p: Mapping[str, Fraction], mu: Mapping[str, Fraction], i: str, region: str
) -> Fraction:
    """`p_r[i] = p[i] + (w_r[i] - wage[i]) h[i] (1 + mu[i])`: a good is paid at its seller's
    own price (decision 6)."""
    return p[i] + (q.wages_abroad[region][i] - q.wage[i]) * q.hours_per_dollar[i] * (1 + mu[i])


@dataclass(frozen=True)
class _Trade:
    kx: Fraction
    exports: Mapping[str, Fraction]
    p_tilde: Mapping[str, Fraction]
    imports_money: Fraction
    equipment: Fraction


def _trade(
    q: Quantities,
    p: Mapping[str, Fraction],
    mu: Mapping[str, Fraction],
    settings: Settings,
    economy: Economy,
) -> _Trade:
    """Trade at given prices (decision 6)."""
    p_tilde: dict[str, Fraction] = {}
    money = _ZERO
    for i, shares in sorted(q.import_sources.items()):
        p_tilde[i] = sum(
            (share * _region_price(q, p, mu, i, region) for region, share in shares.items()), _ZERO
        )
        money += q.imports[i] * p_tilde[i]
    private = _private(economy)
    crossing = [t for t in private if economy.product[t] in settings.crossing]
    ext = economy.extraction_trade
    exports = dict.fromkeys(private, _ZERO)
    ext_value = _ZERO
    if ext is not None and ext in crossing:
        exports[ext] = q.final[ext]
        ext_value = p[ext] * exports[ext]
    others = [t for t in crossing if t != ext]
    base = sum((p[t] * q.export_share.get(t, _ZERO) * q.output[t] for t in others), _ZERO)
    numerator = money - ext_value
    if base == 0:
        if numerator != 0:
            raise _fail("negative_exports")
        kx = _ZERO
    else:
        kx = numerator / base
        if kx < 0:
            raise _fail("negative_exports")
    for t in others:
        exports[t] = q.export_share.get(t, _ZERO) * q.output[t] * kx
    capital = economy.capital_trade
    left = q.final[capital] - exports[capital]
    if left < 0:
        raise _fail("negative_residual", economy.product[capital])
    return _Trade(kx, exports, p_tilde, money, p[capital] * left)


def solve_prices(
    q: Quantities,
    lam: Fraction,
    accounts_margin: Mapping[str, Fraction],
    settings: Settings,
    economy: Economy = TWELVE,
) -> Prices:
    """The price solve with its wear floors (decisions 4 and 5)."""
    private = _private(economy)
    nm = sum(q.machines.get(t, 0) for t in economy.trades)
    floored: frozenset[str] = frozenset()
    phi: dict[str, Fraction] = {}
    e = _ZERO

    def margins(on: frozenset[str], floors: Mapping[str, Fraction]) -> dict[str, Fraction]:
        return {t: (floors[t] if t in on else lam * accounts_margin[t]) for t in private}

    for rounds in range(1, MAX_ROUNDS + 1):
        mu = margins(floored, phi)
        p = _prices_at(q, mu, private)
        equipment = _trade(q, p, mu, settings, economy).equipment
        new_floored = set(floored)
        need: dict[str, Fraction] = {}
        for j in private:
            if q.machines.get(j, 0) == 0 or nm == 0:
                continue
            wear = equipment * q.machines[j] / nm
            cost = q.wage[j] * q.hours_per_dollar[j] + sum(
                (q.coefficients.get(i, {}).get(j, _ZERO) * p[i] for i in private), _ZERO
            )
            need[j] = settings.wear_cover * wear / (q.output[j] * cost)
            if lam * accounts_margin[j] < need[j]:
                new_floored.add(j)
        # Rounding rules: a floored margin up to FLOOR_GRID; equipment money to the micro, half up.
        new_phi = {j: up_to_grid(need.get(j, _ZERO), FLOOR_GRID) for j in new_floored}
        new_e = to_grid(equipment, MICROS)
        settled = (
            new_floored == set(floored)
            and abs(new_e - e) <= Fraction(1, MICROS)
            and all(
                abs(new_phi[j] - phi.get(j, new_phi[j])) <= Fraction(1, FLOOR_GRID) for j in new_phi
            )
        )
        floored, phi, e = frozenset(new_floored), new_phi, new_e
        if settled:
            mu = margins(floored, phi)
            return Prices(
                prices=_prices_at(q, mu, private),
                margins=mu,
                floored=floored,
                equipment=e,
                rounds=rounds,
            )
    raise _fail("prices_unsettled")


# --------------------------------------------------------------------------------------
# The opening.


@dataclass(frozen=True)
class Opening:
    lam: Fraction
    prices: Prices
    quantities: Quantities
    export_factor: Fraction
    exports: Mapping[str, Fraction]
    import_prices: Mapping[str, Fraction]
    import_saving: Mapping[str, Fraction]
    shop_saving: Mapping[str, Fraction]
    wear: Mapping[str, Fraction]
    operating_income: Mapping[str, Fraction]
    public_owned_income: Fraction
    grant: Fraction
    support: Fraction
    benefits: Fraction
    own_cost: Mapping[tuple[str, HouseholdKey], Fraction]
    tax_rate: Fraction
    fund_share: Fraction
    payout: Fraction
    household_purchases: Mapping[str, Fraction]
    shop_charge: Fraction
    markup: Fraction
    spending: Fraction
    tier_unit: Fraction
    tier_one: Mapping[str, Fraction]
    bands: Mapping[HouseholdKey, Fraction]
    kept: Fraction
    balances: Mapping[str, tuple[Fraction, Fraction]]
    # Beyond the interface of the task, so that later parts need not recompute them (by PRODUCT).
    posted: Mapping[str, Fraction] = field(default_factory=dict)
    tier_quantities: Mapping[str, Fraction] = field(default_factory=dict)
    ben_by_account: Mapping[tuple[str, HouseholdKey], Fraction] = field(default_factory=dict)


def _own_price(
    trade: str,
    seller: Seller | None,
    o_p: Mapping[str, Fraction],
    mu: Mapping[str, Fraction],
    q: Quantities,
    economy: Economy,
    rho: Fraction,
) -> Fraction:
    """An account's own price of a need at its seller's wage (decision 10)."""
    p = o_p[trade]
    shop = economy.shop_trade
    if economy.product[trade] in economy.shop_goods and shop is not None:
        if seller is None:
            return p * (1 + rho)
        w = Fraction(seller.wage_micros, MICROS)
        charge = rho * p * w / q.wage[shop]
        if seller.abroad is None:
            return p + charge
        cover = q.import_cover.get(trade, _ZERO)
        p_r = _region_price(q, o_p, mu, trade, seller.abroad)
        return p * (1 - cover) + p_r * cover + charge
    if seller is None:
        return p
    w = Fraction(seller.wage_micros, MICROS)
    return p + (w - q.wage[trade]) * q.hours_per_dollar[trade] * (1 + mu[trade])


@dataclass(frozen=True)
class _Needs:
    rho: Fraction
    shop_charge: Fraction
    household: dict[str, Fraction]
    shop_saving: dict[str, Fraction]
    spending: Fraction
    cbar: Fraction
    avg: Fraction
    posted: dict[str, Fraction]
    t1: dict[str, Fraction]
    tier_one: dict[str, Fraction]
    t1q: dict[str, Fraction]
    persons: int


def _needs(
    census: Census,
    q: Quantities,
    p: Mapping[str, Fraction],
    tr: _Trade,
    saving_by_good: Mapping[str, Fraction],
    settings: Settings,
    economy: Economy,
) -> _Needs:
    """Households' purchases, the shop's charge, spending and tier 1 (decisions 7 and 9)."""
    trade_of = _trade_of(economy)
    shop = economy.shop_trade
    persons = sum(c.persons for c in census.households.values())
    shop_trades = [trade_of[g] for g in sorted(economy.shop_goods) if g in trade_of]
    residual = {i: q.final[i] - tr.exports.get(i, _ZERO) for i in _private(economy)}
    for i, left in residual.items():
        if left < 0:
            raise _fail("negative_residual", economy.product[i])
    household: dict[str, Fraction] = {}
    for product in settings.paying_order:
        i = trade_of[product]
        value = p[i] * residual[i]
        if i in shop_trades:
            value -= saving_by_good.get(i, _ZERO)
        if value < 0:
            raise _fail("negative_residual", product)
        household[i] = value
    charge = q.wage[shop] * q.hours[shop] if shop is not None else _ZERO
    shop_value = sum((p[i] * residual[i] for i in shop_trades), _ZERO)
    rho = charge / shop_value if shop_value > 0 else _ZERO
    hs = {
        i: household[i] + (rho * p[i] * residual[i] if i in shop_trades else _ZERO)
        for i in household
    }
    spending = sum(household.values(), _ZERO) + charge
    cbar = spending / persons
    needs = (*economy.person_needs, *economy.household_needs)
    need_total = sum((hs[trade_of[n]] for n in needs), _ZERO)
    if need_total == 0:
        raise _fail("spending_empty")
    keys = [k for k in HOUSEHOLD_KEYS if k != _RESIDENCE]
    avg = Fraction(
        sum(census.households[k].persons for k in keys),
        sum(census.households[k].households for k in keys),
    )
    t1: dict[str, Fraction] = {}
    tier_one: dict[str, Fraction] = {}
    t1q: dict[str, Fraction] = {}
    posted: dict[str, Fraction] = {}
    for n in needs:
        i = trade_of[n]
        t1[n] = settings.tier_sizes[0] * cbar * hs[i] / need_total
        left = residual[i]
        if i in shop_trades:
            posted[n] = hs[i] / left if left > 0 else p[i] * (1 + rho)
        else:
            posted[n] = p[i]
        scale = avg if n in economy.household_needs else _ONE
        tier_one[n] = t1[n] * scale
        t1q[n] = t1[n] * scale / posted[n]
    return _Needs(
        rho=rho,
        shop_charge=charge,
        household=household,
        shop_saving=dict(saving_by_good),
        spending=spending,
        cbar=cbar,
        avg=avg,
        posted=posted,
        t1=t1,
        tier_one=tier_one,
        t1q=t1q,
        persons=persons,
    )


def _account_cost(
    place: Place,
    key: HouseholdKey,
    n: _Needs,
    o_p: Mapping[str, Fraction],
    mu: Mapping[str, Fraction],
    q: Quantities,
    economy: Economy,
    rho: Fraction,
    fee: Fraction,
) -> Fraction:
    """`c1own`: the account's tier 1 a person at its own sellers' prices, plus the fee."""
    trade_of = _trade_of(economy)
    count = place.keys[key]

    def price(product: str) -> Fraction:
        seller = place.sellers[key].get(product)
        return _own_price(trade_of[product], seller, o_p, mu, q, economy, rho)

    person_cost = sum((n.t1q[x] * price(x) for x in economy.person_needs), _ZERO)
    household_cost = _ZERO
    if key != _RESIDENCE:
        household_cost = sum((n.t1q[x] * price(x) for x in economy.household_needs), _ZERO)
    return (count.persons * person_cost + count.households * household_cost) / count.persons + fee


def machines_in_use(q: Quantities, settings: Settings) -> Fraction:
    """`NU`, the sum over the trades with machines of `hours[j] / (work hours a person x workers
    a machine[j])`: the machines the people at work wear (decision 2). Exact."""
    return sum(
        (
            Fraction(q.hours[trade], settings.work_hours_per_person * workers)
            for trade, workers in sorted(settings.workers_per_machine.items())
            if trade in q.hours
        ),
        _ZERO,
    )


def grant_wear(
    equipment: Fraction, q: Quantities, settings: Settings, economy: Economy = TWELVE
) -> Fraction:
    """The public trade's wear in the grant, the compiler's own: `equipment x machines[public]
    / NU`, `NU` the machines in use (decision 8). Public machines with `NU` of 0: `machines_empty`."""
    pub = economy.public_trade
    machines = q.machines.get(pub, 0) if pub is not None else 0
    if machines == 0:
        return _ZERO
    in_use = machines_in_use(q, settings)
    if in_use == 0:
        raise _fail("machines_empty")
    return equipment * machines / in_use


def public_owned_income(
    oi: Mapping[str, Fraction], mu: Mapping[str, Fraction], trades: Mapping[str, TradeCount]
) -> Fraction:
    """`PO`: each trade's operating income over its public employees' share of persons, plus the
    margin on the public payroll above that share of the trade's payroll (decision 8). A trade
    with no margin (the shop, public provision) has no second term. Payrolls in dollars."""
    total = _ZERO
    for j, value in oi.items():
        site = trades[j]
        if site.employee_persons <= 0:
            continue
        share = Fraction(site.public_employee_persons, site.employee_persons)
        total += value * share
        if j in mu:
            payroll = Fraction(site.payroll_micros, MICROS)
            public = Fraction(site.public_payroll_micros, MICROS)
            total += mu[j] * (public - payroll * share)
    return total


def opening(
    recut: Recut,
    census: Census,
    q: Quantities,
    lam: Fraction,
    settings: Settings,
    economy: Economy = TWELVE,
) -> Opening:
    """The national opening at the margin factor `lam` (decisions 6 to 11 and 13)."""
    fee = Fraction(settings.public_fee_micros, MICROS)
    prices = solve_prices(q, lam, recut.accounts_margin, settings, economy)
    p, mu = prices.prices, prices.margins
    private = _private(economy)
    tr = _trade(q, p, mu, settings, economy)
    nm = sum(q.machines.get(t, 0) for t in economy.trades)
    wear = {
        t: prices.equipment * q.machines[t] / nm
        for t in economy.trades
        if nm > 0 and q.machines.get(t, 0) > 0
    }
    # What buyers save abroad (decision 7): dealt over the buying trades by `import_buyers`.
    shop = economy.shop_trade
    saving: dict[str, Fraction] = {}
    shop_saving: dict[str, Fraction] = {}
    for i, buyers in sorted(q.import_buyers.items()):
        total = q.imports[i] * (p[i] - tr.p_tilde[i])
        for j, share in buyers.items():
            if j == shop:
                shop_saving[i] = shop_saving.get(i, _ZERO) + total * share
            else:
                saving[j] = saving.get(j, _ZERO) + total * share
    needs = _needs(census, q, p, tr, shop_saving, settings, economy)
    rho = needs.rho
    trade_of = _trade_of(economy)
    # The county support a person: one period of the food need at the producer's price.
    food = trade_of["food"]
    support_unit = needs.t1q["food"] * p[food]
    support = sum((c.reserve for c in census.households.values()), 0) * support_unit
    # The benefit: each account's own cost, net of its support (decision 10).
    own_cost: dict[tuple[str, HouseholdKey], Fraction] = {}
    ben_by_account: dict[tuple[str, HouseholdKey], Fraction] = {}
    ben_by_key: dict[HouseholdKey, Fraction] = dict.fromkeys(HOUSEHOLD_KEYS, _ZERO)
    micro = Fraction(1, MICROS)
    for place in census.places:
        for key in (*_NO_EARNER, _RESIDENCE):
            count = place.keys[key]
            if count.persons <= 0:
                continue
            c1 = _account_cost(place, key, needs, p, mu, q, economy, rho, fee)
            own_cost[(place.label, key)] = c1
            paid = count.persons if key != _RESIDENCE else count.persons - count.employed
            if paid <= 0:
                ben = _ZERO
            else:
                floor = count.persons * micro
                ben = max(c1 * paid - count.reserve * support_unit, floor)
            ben_by_account[(place.label, key)] = ben
            ben_by_key[key] += ben
    benefits = sum(ben_by_key.values(), _ZERO)
    # Operating income, public money and one tax rate (decision 8).
    oi: dict[str, Fraction] = {}
    for j in private:
        margin = mu[j]
        profit = p[j] * q.output[j] * margin / (1 + margin)
        value = profit + q.unpaid_labor[j] + saving.get(j, _ZERO) - wear.get(j, _ZERO)
        if value < 0:
            raise _fail("negative_operating_income", j)
        oi[j] = value
    if shop is not None:
        oi[shop] = q.unpaid_labor[shop]
    # The shop's income is its unpaid labor, with no margin: no second term for it.
    po = public_owned_income(oi, {j: mu[j] for j in private if j != shop}, census.trades)
    wages = sum((Fraction(c.payroll_micros, MICROS) for c in census.trades.values()), _ZERO)
    oi_total = sum(oi.values(), _ZERO)
    persons = needs.persons
    grant = _ZERO
    pub = economy.public_trade
    gwear = grant_wear(prices.equipment, q, settings, economy)
    if pub is not None:
        inputs = sum(
            (q.coefficients.get(i, {}).get(pub, _ZERO) * p[i] * q.output[pub] for i in private),
            _ZERO,
        )
        grant = (
            Fraction(census.trades[pub].payroll_micros, MICROS)
            + inputs
            + gwear
            - saving.get(pub, _ZERO)
            - fee * persons
        )
    denominator = wages + oi_total - po
    if denominator <= 0:
        raise _fail("tax_rate")
    tax = (grant + support + benefits - po) / denominator
    if not (0 <= tax < 1):
        raise _fail("tax_rate")
    if tax == 0 and benefits > 0:
        raise _fail("tax_rate")
    fund_share = benefits / (tax * (wages + oi_total)) if tax > 0 else _ZERO
    if not (0 <= fund_share < 1):
        raise _fail("tax_rate")
    payout = (1 - tax) * (oi_total - po)
    # The grant pays the public trade's wear on the machines in use; the trades' own wear is on the
    # census machines. What the grant pays above `wear[public]` reaches the makers of equipment as
    # revenue that no operating income counts.
    extra_wear = gwear - wear.get(pub, _ZERO) if pub is not None else _ZERO
    bands = _bands(census, tax, payout, support_unit, ben_by_key)
    kept = _kept(census, bands, needs, settings, economy, fee)
    flows = _balances(
        bands,
        needs,
        fee,
        persons,
        grant,
        support,
        benefits,
        tax,
        wages,
        oi_total,
        po,
        tr,
        p,
        wear,
        extra_wear,
    )
    if abs(flows["1"][1]) > 1:
        raise _fail("income_identity")
    return Opening(
        lam=lam,
        prices=prices,
        quantities=q,
        export_factor=tr.kx,
        exports=tr.exports,
        import_prices=tr.p_tilde,
        import_saving=saving,
        shop_saving=shop_saving,
        wear=wear,
        operating_income=oi,
        public_owned_income=po,
        grant=grant,
        support=support,
        benefits=benefits,
        own_cost=own_cost,
        tax_rate=tax,
        fund_share=fund_share,
        payout=payout,
        household_purchases=needs.household,
        shop_charge=needs.shop_charge,
        markup=rho,
        spending=needs.spending,
        tier_unit=needs.cbar,
        tier_one=needs.tier_one,
        bands=bands,
        kept=kept,
        balances=flows,
        posted=needs.posted,
        tier_quantities=needs.t1q,
        ben_by_account=ben_by_account,
    )


def _bands(
    census: Census,
    tax: Fraction,
    payout: Fraction,
    support_unit: Fraction,
    ben_by_key: Mapping[HouseholdKey, Fraction],
) -> dict[HouseholdKey, Fraction]:
    """The national accounts' money a period, one for each key (decision 11)."""
    owners = (
        census.households["earning_owner"].households
        + census.households["no_earner_owner"].households
    )
    bands: dict[HouseholdKey, Fraction] = {}
    for key in HOUSEHOLD_KEYS:
        count = census.households[key]
        money = count.reserve * support_unit + ben_by_key.get(key, _ZERO)
        if key in (*_EARNING, _RESIDENCE):
            money += (1 - tax) * Fraction(count.wage_income_micros, MICROS)
        if key in ("earning_owner", "no_earner_owner") and owners > 0:
            money += payout * count.households / owners
        bands[key] = money
    return bands


def _kept(
    census: Census,
    bands: Mapping[HouseholdKey, Fraction],
    n: _Needs,
    settings: Settings,
    economy: Economy,
    fee: Fraction,
) -> Fraction:
    """What the national accounts keep above their full cost (decision 11)."""
    person_cost = sum((n.t1[x] for x in economy.person_needs), _ZERO)
    household_cost = sum((n.tier_one[x] for x in economy.household_needs), _ZERO)
    upper = settings.tier_sizes[1] + settings.tier_sizes[2]
    kept = _ZERO
    for key in HOUSEHOLD_KEYS:
        count = census.households[key]
        cost = count.persons * (person_cost + fee + upper * n.cbar)
        if key != _RESIDENCE:
            cost += count.households * household_cost
        kept += max(_ZERO, bands[key] - cost)
    return kept


def _balances(
    bands: Mapping[HouseholdKey, Fraction],
    n: _Needs,
    fee: Fraction,
    persons: int,
    grant: Fraction,
    support: Fraction,
    benefits: Fraction,
    tax: Fraction,
    wages: Fraction,
    oi_total: Fraction,
    po: Fraction,
    tr: _Trade,
    p: Mapping[str, Fraction],
    wear: Mapping[str, Fraction],
    extra_wear: Fraction,
) -> dict[str, tuple[Fraction, Fraction]]:
    """O6's four balances, each as `(flow, residual)` (decision 13)."""
    spent = n.spending + fee * persons
    receipts = tax * (wages + oi_total) + (1 - tax) * po
    exported = sum((p[t] * x for t, x in tr.exports.items()), _ZERO)
    return {
        "1": (spent, sum(bands.values(), _ZERO) + extra_wear - spent),
        "2": (grant + support + benefits, receipts - (grant + support + benefits)),
        "3": (tr.imports_money, exported - tr.imports_money),
        "4": (tr.equipment, sum(wear.values(), _ZERO) - tr.equipment),
    }


def largest_with_nothing_kept(kept_at: Callable[[Fraction], Fraction], halvings: int) -> Fraction:
    """The largest multiple of `2^-halvings` in [0, 1] at which nothing is kept (decision 12):
    kept at 0 above 0 is `margin_scale_none`; kept at 1 equal to 0 gives 1."""
    if kept_at(_ZERO) > 0:
        raise _fail("margin_scale_none")
    if kept_at(_ONE) == 0:
        return _ONE
    lo, hi = _ZERO, _ONE
    for _ in range(halvings):
        mid = (lo + hi) / 2
        if kept_at(mid) == 0:
            lo = mid
        else:
            hi = mid
    return lo


def solve(recut: Recut, census: Census, settings: Settings, economy: Economy = TWELVE) -> Opening:
    """The margin factor, then the opening at it."""
    q = quantities(recut, census, settings, economy)
    lam = largest_with_nothing_kept(
        lambda x: opening(recut, census, q, x, settings, economy).kept, settings.margin_halvings
    )
    return opening(recut, census, q, lam, settings, economy)


__all__ = [
    "FLOOR_GRID",
    "GRID",
    "MICROS",
    "Opening",
    "Prices",
    "Quantities",
    "largest_with_nothing_kept",
    "opening",
    "quantities",
    "solve",
    "solve_prices",
]
