#!/usr/bin/env python3
"""The builder of the rebuilt national opening, part 4 (Task 11 of stage 5).

Each part's accounts and their money, the three tiers of wants that make what the accounts buy
under R4 equal what households must buy, the luxury scales, the benefit estimated at each
account's own cost, each part's body (its share to the fund or the fund's grant to it), and
the two counts of what own prices and where a service is bought move.

Every figure is an `int` or a `Fraction`; a `float` anywhere is a defect. Every rounding to an
integer names its rule where it is done. Every refusal is a `ReferenceBuildError` with a fixed
code before the first colon. Money is in micros of a dollar unless a name says dollars.

Keys. `Account.own_prices`, `Tiers.comfort`, `Tiers.luxury` and every figure by good are keyed by
PRODUCT (`food`, `household_services`, ...); `Tiers.state_services` is keyed by (state, service),
the shop's hours as `SHOP_HOURS`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Final, Literal

from make_national_county_reference import ReferenceBuildError
from national_opening_recut import (
    HOUSEHOLD_KEYS,
    TWELVE,
    Census,
    Economy,
    HouseholdKey,
    Place,
    Seller,
    Settings,
    half_up,
    to_grid,
)
from national_opening_solve import MICROS, Opening
from national_opening_units import Written, own_price, region_maker_prices, shop_estimate

TIER_GRID: Final = 2**32  # contents, units a person; prices of the solve: to_grid(., TIER_GRID)
BASIS: Final = 10_000
SCALE_LIMIT_BPS: Final = 1_000_000  # the compiler refuses a luxury scale above this (Task 1)
TIER_ONE_DAYS: Final = 28  # tier 1 holds 28 of each need: a day's of it for a period
MAX_STEPS: Final = 60
MAX_HALVINGS: Final = 30
TINY: Final = Fraction(1, 10**12)
WANT_BOTH: Final = ("consumer_goods", "business_services")  # the same in tiers 2 and 3
WANT_LATE: Final = "leisure"  # tier 3 only
SHOP_HOURS: Final = "shop_hours"
_ZERO: Final = Fraction(0)
_ONE: Final = Fraction(1)
_RESIDENCE: Final[HouseholdKey] = "collective_residence"
_NO_EARNER: Final[tuple[HouseholdKey, ...]] = ("no_earner_nonowner", "no_earner_owner")
_OWNER: Final[tuple[HouseholdKey, ...]] = ("earning_owner", "no_earner_owner")

Price = int | Fraction
Pattern = tuple[int, int, bool]
Mono = tuple[int, ...]
Poly = dict[Mono, Fraction]


def _fail(code: str, what: str = "") -> ReferenceBuildError:
    return ReferenceBuildError(f"{code}: {what}" if what else code)


def _ceil(value: Fraction) -> int:
    """Round up to a whole number (the rule of every `ceil` below)."""
    return math.ceil(value)


# --------------------------------------------------------------------------------------
# Accounts, rows and buying.


@dataclass(frozen=True)
class Account:
    place: str
    key: HouseholdKey
    persons: int
    households: int
    employed: int
    money_micros: int
    own_prices: Mapping[str, int]  # its own sellers' posted price of each product's unit, micros
    reserve: int = 0  # persons looking for work at the opening (county support), beyond the task


@dataclass(frozen=True)
class Row:
    good: str
    tier: Literal[1, 2, 3]
    basis: Literal["persons", "households"]
    units: Fraction


@dataclass(frozen=True)
class Bought:
    units: Mapping[str, Fraction]
    reach: tuple[Fraction, Fraction, Fraction]
    left_micros: Fraction
    pattern: Pattern  # (tier, row index in the tier where money ended, scaled)


def _split(rows: Sequence[Row]) -> tuple[list[Row], list[Row], list[Row]]:
    """The rows by tier, each tier in the order given (the order of paying)."""
    tiers: tuple[list[Row], list[Row], list[Row]] = ([], [], [])
    for row in rows:
        tiers[row.tier - 1].append(row)
    return tiers


def _buy_tiers(
    account: Account,
    tiers: tuple[list[Row], list[Row], list[Row]],
    prices: Mapping[str, Price],
    scale: Fraction | None,
) -> Bought:
    left = Fraction(account.money_micros)
    units: dict[str, Fraction] = {}
    cost = [_ZERO, _ZERO, _ZERO]
    spent = [_ZERO, _ZERO, _ZERO]
    ended: tuple[int, int] | None = None
    for tier, rows in enumerate(tiers, start=1):
        times = scale if tier == 3 and scale is not None else _ONE
        for index, row in enumerate(rows):
            if row.good not in prices:
                raise _fail("account_price", f"{account.place}/{account.key}/{row.good}")
            price = Fraction(prices[row.good])
            count = account.persons if row.basis == "persons" else account.households
            wanted = row.units * count * times
            full = wanted * price
            cost[tier - 1] += full
            if ended is not None:
                continue
            if full <= left:
                got = wanted
                spent[tier - 1] += full
                left -= full
            else:
                got = left / price
                spent[tier - 1] += left
                left = _ZERO
                ended = (tier, index)
            units[row.good] = units.get(row.good, _ZERO) + got
    reach = (
        spent[0] / cost[0] if cost[0] > 0 else _ZERO,
        spent[1] / cost[1] if cost[1] > 0 else _ZERO,
        spent[2] / cost[2] if cost[2] > 0 else _ZERO,
    )
    pattern: Pattern = (
        (ended[0], ended[1], False) if ended is not None else (3, len(tiers[2]), scale is not None)
    )
    return Bought(units=units, reach=reach, left_micros=left, pattern=pattern)


def buy(
    account: Account,
    rows: Sequence[Row],
    prices: Mapping[str, Price],
    scale: Fraction | None = None,
) -> Bought:
    """R4 (model-spec 10): tier 1, 2, 3 in turn and inside a tier the rows in the order given (the
    order of paying), each row whole while the money lasts; the row where it ends takes the rest in
    fractional units. What is left after tier 3 is kept unless `scale` is given, when tier 3's rows
    are bought times `scale` (call 20). `reach[t]` is the money spent in tier `t` over its cost."""
    return _buy_tiers(account, _split(rows), prices, scale)


# --------------------------------------------------------------------------------------
# Prices an account pays.


def shop_own_price(
    written_micros: int,
    region_price_micros: int | None,
    import_bps: int,
    handling: tuple[int, int],
    retailer_wage_micros: int,
) -> int:
    """What an account pays for a shop good (ruling 6, E7): what its shop pays plus the shop's
    charge. With a foreign second supplier the shop pays `ceil((written x (10_000 - import_bps) +
    the region's price x import_bps) / 10_000)`; with a domestic one, the written price. The
    charge is `ceil(hours x the retailer's wage / units)`. An ESTIMATE of the compiled price."""
    hours, units = handling
    # Rounding rule: the charge a unit, up.
    charge = -((-(hours * retailer_wage_micros)) // units)
    if region_price_micros is None:
        return written_micros + charge
    # `shop_estimate(a, b, bps)` weights `a` by `10_000 - bps`: here the written price.
    return shop_estimate(written_micros, region_price_micros, import_bps) + charge


def _trade_of(economy: Economy) -> dict[str, str]:
    return {product: trade for trade, product in economy.product.items()}


class _Prices:
    """An account's own price of each product, by its sellers (decision 2)."""

    def __init__(self, o: Opening, census: Census, w: Written, economy: Economy) -> None:
        self.o, self.census, self.w, self.economy = o, census, w, economy
        self.trade_of = _trade_of(economy)
        self.regions: dict[str, Mapping[str, int]] = {}
        shop = economy.shop_trade
        self.shop_wage = half_up(o.quantities.wage[shop] * MICROS) if shop is not None else 0
        out_of_reach = {economy.capital_trade, economy.extraction_trade}
        self.products = tuple(
            product for product in sorted(w.products) if self.trade_of[product] not in out_of_reach
        )

    def region(self, name: str) -> Mapping[str, int]:
        if name not in self.regions:
            self.regions[name] = region_maker_prices(
                self.w, self.o, self.census.abroad[name].wage_micros, self.economy
            )
        return self.regions[name]

    def one(self, product: str, seller: Seller | None) -> int:
        made = self.w.products[product]
        trade = self.trade_of[product]
        if trade == self.economy.public_trade:
            return made.price_micros
        if made.handling is not None and self.economy.shop_trade is not None:
            retailer = seller.wage_micros if seller is not None else self.shop_wage
            region = None
            if seller is not None and seller.abroad is not None:
                region = self.region(seller.abroad)[product]
            return shop_own_price(
                made.price_micros,
                region,
                self.w.import_bps.get(product, 0),
                made.handling,
                retailer,
            )
        if seller is None:
            return made.price_micros
        # Rounding rule: the national wage in micros an hour, half up (as `region_maker_prices`).
        national = half_up(self.o.quantities.wage[trade] * MICROS)
        return own_price(self.w.recipes[trade], made.price_micros, seller.wage_micros, national)

    def of(self, place: Place, key: HouseholdKey) -> dict[str, int]:
        sellers = place.sellers[key]
        return {product: self.one(product, sellers.get(product)) for product in self.products}


# --------------------------------------------------------------------------------------
# The benefit estimated (decision 6) and each account's money (decision 1).


def support_micros(w: Written, days: int = TIER_ONE_DAYS) -> int:
    """County support a person a period (Task 4, decision 9): one period of one person's food need,
    `1 x days x the food price`, whole micros."""
    return days * w.products["food"].price_micros


def needs_cost_micros(
    own_prices: Mapping[str, int],
    persons: int,
    households: int,
    key: HouseholdKey,
    economy: Economy,
    days: int = TIER_ONE_DAYS,
) -> int:
    """What an account's tier 1 costs a period at its own sellers' prices: `days` of each person
    need a person, `days` of each household need a household (none for a residence) and public
    provision's fee a person."""
    person = sum(days * own_prices[n] for n in economy.person_needs)
    if economy.public_trade is not None:
        person += own_prices[economy.product[economy.public_trade]]
    household = 0
    if key != _RESIDENCE:
        household = sum(days * own_prices[n] for n in economy.household_needs)
    return persons * person + households * household


def own_need_estimate(
    own_prices: Mapping[str, int],
    persons: int,
    households: int,
    reserve: int,
    employed: int,
    key: HouseholdKey,
    economy: Economy,
    support: int,
    days: int = TIER_ONE_DAYS,
) -> int | None:
    """The compiler's own-needs rule at the builder's estimate of the posted prices (decision 6): a
    no-earner account's amount a person is `max(1, ceil((cost - reserve x support) / persons))`; a
    residence's, over its residents with no job, `max(1, ceil((cost x (persons - employed) /
    persons - reserve x support) / persons))`; none for a residence with no resident out of work
    or an account of no persons. Rounding rule: up, to a whole micro, at least 1."""
    if persons <= 0:
        return None
    cost = needs_cost_micros(own_prices, persons, households, key, economy, days)
    if key == _RESIDENCE:
        jobless = persons - employed
        if jobless <= 0:
            return None
        exact = Fraction(cost * jobless, persons) - reserve * support
    else:
        exact = Fraction(cost - reserve * support)
    return max(1, _ceil(exact / persons))


@dataclass(frozen=True)
class _Income:
    wages: Fraction  # residents' wage income, dollars a period
    private: Fraction  # the part's private operating income
    public_owned: Fraction  # the part's public-owned operating income


def place_incomes(o: Opening, census: Census) -> dict[str, _Income]:
    """Each part's incomes at the exact solve (decision 1): `OI_c = sum_j (OI[j] emp_c,j / emp_j +
    mu[j] (payroll_c,j - wexact[j] x 160 x emp_c,j))`, with `wexact x 160 x emp_c = payroll_j x
    emp_c / emp_j`; its public-owned part `PO_c` by the same rule over public employee persons
    (`OI[j] pub_emp_c,j / emp_j`), with the TRADE's wage `wexact[j]` as the reference of its margin
    term (`mu[j] (pub_payroll_c,j - wexact[j] x 160 x pub_emp_c,j)`, the trade's payroll x
    pub_emp_c / emp_j), so that `sum PO_c` is Task 10's `PO` (`public_owned_income`); its private
    part is the rest. Both sum over parts to the nation's."""
    out: dict[str, _Income] = {}
    for place in census.places:
        total = _ZERO
        public = _ZERO
        for trade, value in sorted(o.operating_income.items()):
            site = census.trades[trade]
            if site.employee_persons <= 0:
                continue
            mu = o.prices.margins.get(trade, _ZERO)
            row = place.trades[trade]
            of = site.employee_persons
            total += value * Fraction(row.employee_persons, of)
            total += (
                mu
                * (row.payroll_micros - Fraction(site.payroll_micros * row.employee_persons, of))
                / MICROS
            )
            public += value * Fraction(row.public_employee_persons, of)
            public += (
                mu
                * (
                    row.public_payroll_micros
                    - Fraction(site.payroll_micros * row.public_employee_persons, of)
                )
                / MICROS
            )
        wages = sum((Fraction(c.wage_income_micros, MICROS) for c in place.keys.values()), _ZERO)
        out[place.label] = _Income(wages=wages, private=total - public, public_owned=public)
    return out


@dataclass(frozen=True)
class _Drafts:
    accounts: tuple[Account, ...]
    no_earner: Mapping[tuple[str, HouseholdKey], int]
    residence: Mapping[str, int]


def _drafts(o: Opening, census: Census, w: Written, economy: Economy) -> _Drafts:
    prices = _Prices(o, census, w, economy)
    support = support_micros(w)
    incomes = place_incomes(o, census)
    tax = o.tax_rate
    accounts_out: list[Account] = []
    no_earner: dict[tuple[str, HouseholdKey], int] = {}
    residence: dict[str, int] = {}
    for place in census.places:
        payout = (1 - tax) * incomes[place.label].private
        for key in HOUSEHOLD_KEYS:
            count = place.keys[key]
            if count.persons <= 0:
                continue
            own = prices.of(place, key)
            money = Fraction(count.reserve * support)
            if key in ("earning_lower_paid_half", "earning_better_paid_forty", "earning_owner"):
                money += (1 - tax) * count.wage_income_micros
            if key == _RESIDENCE:
                money += (1 - tax) * count.wage_income_micros
            if key in _OWNER and place.owner_households > 0:
                money += payout * MICROS * count.households / place.owner_households
            if key in _NO_EARNER or key == _RESIDENCE:
                estimate = own_need_estimate(
                    own,
                    count.persons,
                    count.households,
                    count.reserve,
                    count.employed,
                    key,
                    economy,
                    support,
                )
                if estimate is not None:
                    money += estimate * count.persons
                    if key == _RESIDENCE:
                        residence[place.label] = estimate
                    else:
                        no_earner[(place.label, key)] = estimate
            accounts_out.append(
                Account(
                    place=place.label,
                    key=key,
                    persons=count.persons,
                    households=count.households,
                    employed=count.employed,
                    # Rounding rule: an account's money a period, down to a whole micro.
                    money_micros=math.floor(money),
                    own_prices=own,
                    reserve=count.reserve,
                )
            )
    return _Drafts(tuple(accounts_out), no_earner, residence)


def accounts(
    o: Opening, census: Census, w: Written, economy: Economy = TWELVE
) -> tuple[Account, ...]:
    """One account per part and key with persons (decision 1), money a period at the exact solve,
    rounded down to whole micros: an earning key's and the residence's `wage income (1 - t) +
    reserve x support`; the two owner keys share the part's payout by households over its owner
    households; a no-earner key its estimated amount x persons plus its support; the residence its
    estimated amount x persons beside its wages."""
    return _drafts(o, census, w, economy).accounts


# --------------------------------------------------------------------------------------
# The rows of the tiers.


@dataclass(frozen=True)
class Shape:
    """Which products stand in which tier (decision 4): tier 2 holds the needs and the two wants
    that are in both tiers; tier 3 those and the late want. The nine unknowns are tier 2's units
    a person, `rho3` (tier 3's need products over tier 2's) and the late want's units."""

    order: tuple[str, ...]
    needs: tuple[str, ...]
    tier2: tuple[str, ...]
    tier3: tuple[str, ...]
    public: str | None
    days: int

    @property
    def names(self) -> tuple[str, ...]:
        return (*self.tier2, "rho3", WANT_LATE)

    @property
    def rho(self) -> int:
        return len(self.tier2)

    @property
    def late(self) -> int:
        return len(self.tier2) + 1


def shape_of(settings: Settings, economy: Economy) -> Shape:
    needs = (*economy.person_needs, *economy.household_needs)
    both = tuple(p for p in WANT_BOTH if p in settings.paying_order)
    tier2 = tuple(p for p in settings.paying_order if p in needs or p in both)
    tier3 = tuple(p for p in settings.paying_order if p in needs or p in both or p == WANT_LATE)
    public = economy.product[economy.public_trade] if economy.public_trade is not None else None
    return Shape(
        order=settings.paying_order,
        needs=needs,
        tier2=tier2,
        tier3=tier3,
        public=public,
        days=settings.days_per_period,
    )


def tier_one_rows(key: HouseholdKey, shape: Shape, economy: Economy) -> tuple[Row, ...]:
    """Tier 1 (decision 2): `days` a person of each person need, `days` a household of each
    household need (none for a residence), public provision, 1 a person, last."""
    rows = [
        Row(p, 1, "persons", Fraction(shape.days)) for p in shape.order if p in economy.person_needs
    ]
    if key != _RESIDENCE:
        rows += [
            Row(p, 1, "households", Fraction(shape.days))
            for p in shape.order
            if p in economy.household_needs
        ]
    if shape.public is not None:
        rows.append(Row(shape.public, 1, "persons", _ONE))
    return tuple(rows)


def want_rows(
    shape: Shape,
    comfort: Mapping[str, Fraction],
    luxury: Mapping[str, Fraction],
    *,
    drop_zero: bool,
) -> tuple[Row, ...]:
    """Tier 2 and tier 3 rows by person, each tier in the order of paying; with `drop_zero` a row at
    0 is left out."""
    rows: list[Row] = []
    for tier, products, units in ((2, shape.tier2, comfort), (3, shape.tier3, luxury)):
        for product in products:
            count = units.get(product, _ZERO)
            if count > 0 or not drop_zero:
                rows.append(Row(product, 2 if tier == 2 else 3, "persons", count))
    return tuple(rows)


def contents_of(
    shape: Shape, z: Sequence[Fraction]
) -> tuple[dict[str, Fraction], dict[str, Fraction]]:
    """Tier 2's and tier 3's units a person from the unknowns: tier 3 holds `rho3` times tier 2 of
    the need products, the same as tier 2 of the two wants in both tiers, and the late want."""
    comfort = {p: z[j] for j, p in enumerate(shape.tier2)}
    luxury: dict[str, Fraction] = {}
    for j, p in enumerate(shape.tier2):
        luxury[p] = z[shape.rho] * z[j] if p in shape.needs else z[j]
    luxury[WANT_LATE] = z[shape.late]
    return comfort, {p: luxury[p] for p in shape.tier3}


# --------------------------------------------------------------------------------------
# Polynomials in the unknowns (degree 2 through `rho3` only).


def _padd(into: Poly, other: Mapping[Mono, Fraction], factor: Fraction) -> None:
    for mono, coefficient in other.items():
        into[mono] = into.get(mono, _ZERO) + coefficient * factor


def _value(poly: Mapping[Mono, Fraction], z: Sequence[Fraction]) -> Fraction:
    total = _ZERO
    for mono, coefficient in poly.items():
        term = coefficient
        for index in mono:
            term *= z[index]
        total += term
    return total


def _derivative(poly: Mapping[Mono, Fraction], k: int, z: Sequence[Fraction]) -> Fraction:
    total = _ZERO
    for mono, coefficient in poly.items():
        count = mono.count(k)
        if count == 0:
            continue
        term = coefficient * count
        rest = list(mono)
        rest.remove(k)
        for index in rest:
            term *= z[index]
        total += term
    return total


def _gauss(matrix: list[list[Fraction]], rhs: list[Fraction]) -> list[Fraction]:
    """Gaussian elimination in Fractions, the first non-zero pivot of each column; none is
    `tiers_singular`."""
    n = len(rhs)
    rows = [[*matrix[r], rhs[r]] for r in range(n)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if rows[r][col] != 0), None)
        if pivot is None:
            raise _fail("tiers_singular")
        rows[col], rows[pivot] = rows[pivot], rows[col]
        lead = rows[col][col]
        rows[col] = [v / lead for v in rows[col]]
        for r in range(n):
            if r != col and rows[r][col] != 0:
                factor = rows[r][col]
                rows[r] = [v - factor * x for v, x in zip(rows[r], rows[col], strict=True)]
    return [rows[r][n] for r in range(n)]


# --------------------------------------------------------------------------------------
# The tier solve (decisions 4, 5 and 7).


@dataclass(frozen=True)
class TierProblem:
    accounts: Sequence[Account]
    prices: Mapping[str, Fraction]  # national posted price of a unit, micros (every product bought)
    demand: Mapping[str, Fraction]  # D[i], units a period, for every tier-2 product
    cbar_micros: Fraction  # spending a person a period, micros
    sizes: tuple[Fraction, Fraction]  # tier 2's and tier 3's sizes, in cbar
    shape: Shape
    economy: Economy


class _Evaluator:
    def __init__(self, problem: TierProblem) -> None:
        self.p = problem
        shape = problem.shape
        self.ones = {key: tier_one_rows(key, shape, problem.economy) for key in HOUSEHOLD_KEYS}
        s2, s3 = problem.sizes
        self.scale: list[Fraction | None] = []
        for account in problem.accounts:
            t1 = _cost(account, self.ones[account.key], problem.prices)
            cbar_persons = problem.cbar_micros * account.persons
            if account.money_micros >= t1 + (s2 + s3) * cbar_persons:
                self.scale.append(
                    (account.money_micros - t1 - s2 * cbar_persons) / (s3 * cbar_persons)
                )
            else:
                self.scale.append(None)
        n = len(shape.tier2)
        self.expr2: list[Poly] = [{(j,): _ONE} for j in range(n)]
        self.expr3: list[Poly] = []
        for p in shape.tier3:
            if p == WANT_LATE:
                self.expr3.append({(shape.late,): _ONE})
            elif p in shape.needs:
                self.expr3.append({(shape.tier2.index(p), shape.rho): _ONE})
            else:
                self.expr3.append({(shape.tier2.index(p),): _ONE})

    def numeric(self, z: Sequence[Fraction]) -> tuple[list[Fraction], list[Pattern]]:
        p = self.p
        comfort, luxury = contents_of(p.shape, z)
        rows = want_rows(p.shape, comfort, luxury, drop_zero=False)
        t2 = [r for r in rows if r.tier == 2]
        t3 = [r for r in rows if r.tier == 3]
        bought: dict[str, Fraction] = {}
        patterns: list[Pattern] = []
        for account, scale in zip(p.accounts, self.scale, strict=True):
            result = _buy_tiers(account, (list(self.ones[account.key]), t2, t3), p.prices, scale)
            patterns.append(result.pattern)
            for good, count in result.units.items():
                bought[good] = bought.get(good, _ZERO) + count
        residual = [(bought.get(g, _ZERO) - p.demand[g]) / p.demand[g] for g in p.shape.tier2]
        residual += self.sizes_residual(z)
        return residual, patterns

    def sizes_residual(self, z: Sequence[Fraction]) -> list[Fraction]:
        p = self.p
        comfort, luxury = contents_of(p.shape, z)
        c2 = sum((comfort[g] * p.prices[g] for g in p.shape.tier2), _ZERO)
        c3 = sum((luxury[g] * p.prices[g] for g in p.shape.tier3), _ZERO)
        s2, s3 = p.sizes
        return [c2 / p.cbar_micros - s2, c3 / p.cbar_micros - s3]

    def held(self, patterns: Sequence[Pattern]) -> list[Poly]:
        """The residuals as polynomials, every account's pattern held."""
        p = self.p
        shape = p.shape
        agg: dict[str, Poly] = {g: {} for g in shape.tier2}
        for account, scale, pattern in zip(p.accounts, self.scale, patterns, strict=True):
            end = (pattern[0], pattern[1])
            cost: Poly = {}
            stop: tuple[str, Fraction] | None = None
            for tier, rows, exprs in (
                (1, self.ones[account.key], None),
                (2, [Row(g, 2, "persons", _ONE) for g in shape.tier2], self.expr2),
                (3, [Row(g, 3, "persons", _ONE) for g in shape.tier3], self.expr3),
            ):
                for index, row in enumerate(rows):
                    here = (tier, index)
                    if here > end:
                        break
                    count = account.persons if row.basis == "persons" else account.households
                    times = scale if tier == 3 and scale is not None else _ONE
                    price = p.prices[row.good]
                    expr: Poly = {(): row.units} if exprs is None else exprs[index]
                    if here == end:
                        stop = (row.good, price)
                        break
                    weight = count * times
                    if row.good in agg:
                        _padd(agg[row.good], expr, weight)
                    _padd(cost, expr, weight * price)
                if stop is not None:
                    break
            if stop is not None:
                good, price = stop
                if good in agg:
                    agg[good][()] = (
                        agg[good].get((), _ZERO) + Fraction(account.money_micros) / price
                    )
                    _padd(agg[good], cost, -_ONE / price)
        residual: list[Poly] = []
        for g in shape.tier2:
            poly: Poly = {}
            _padd(poly, agg[g], _ONE / p.demand[g])
            poly[()] = poly.get((), _ZERO) - _ONE
            residual.append(poly)
        for products, exprs, size in (
            (shape.tier2, self.expr2, p.sizes[0]),
            (shape.tier3, self.expr3, p.sizes[1]),
        ):
            poly = {}
            for g, expr in zip(products, exprs, strict=True):
                _padd(poly, expr, p.prices[g] / p.cbar_micros)
            poly[()] = poly.get((), _ZERO) - size
            residual.append(poly)
        return residual


def _cost(account: Account, rows: Sequence[Row], prices: Mapping[str, Price]) -> Fraction:
    total = _ZERO
    for row in rows:
        count = account.persons if row.basis == "persons" else account.households
        if row.good not in prices:
            raise _fail("account_price", f"{account.place}/{account.key}/{row.good}")
        total += row.units * count * Fraction(prices[row.good])
    return total


def _ssr(values: Sequence[Fraction]) -> Fraction:
    return sum((v * v for v in values), _ZERO)


def solve_contents(problem: TierProblem, start: Sequence[Fraction]) -> tuple[list[Fraction], int]:
    """Newton's method on the nine equations (decision 7). Each step takes every account's pattern
    at `z`, builds the residuals as polynomials with the patterns held (exact), solves `J dz = -r`
    exactly (`tiers_singular`), tries `z + dz` halving `dz` while an unknown is below 0 or the sum
    of squared residuals (patterns re-taken) does not fall (at most 30 times, then
    `tiers_unsolved`), and puts the new `z` on `TIER_GRID` (round to nearest, half up). It stops
    when two successive `z` are equal, or every residual is at most 10^-12 and no pattern changed
    in the step; after 60 steps, `tiers_unsolved`. Returns `z` and the steps taken."""
    evaluator = _Evaluator(problem)
    z = [to_grid(v, TIER_GRID) for v in start]
    residual, patterns = evaluator.numeric(z)
    for step in range(1, MAX_STEPS + 1):
        polys = evaluator.held(patterns)
        n = len(z)
        jacobian = [[_derivative(polys[i], k, z) for k in range(n)] for i in range(n)]
        dz = _gauss(jacobian, [-r for r in residual])
        before = _ssr(residual)
        moved = False
        scale = _ONE
        candidate = list(z)
        new_residual: list[Fraction] = []
        new_patterns: list[Pattern] = []
        for _ in range(MAX_HALVINGS + 1):
            candidate = [to_grid(z[k] + dz[k] * scale, TIER_GRID) for k in range(n)]
            if candidate == z:
                # A step that rounds back to `z` has converged only when it was the whole step, or
                # when every residual is within TINY; a halved one that does so is another halving.
                if scale == _ONE or all(abs(r) <= TINY for r in residual):
                    return z, step
                scale /= 2
                continue
            if all(v >= 0 for v in candidate):
                new_residual, new_patterns = evaluator.numeric(candidate)
                if _ssr(new_residual) < before:
                    moved = True
                    break
            scale /= 2
        if not moved:
            raise _fail("tiers_unsolved")
        same = new_patterns == patterns
        z, residual, patterns = candidate, new_residual, new_patterns
        if same and all(abs(r) <= TINY for r in residual):
            return z, step
    raise _fail("tiers_unsolved")


# --------------------------------------------------------------------------------------
# The solve's inputs: national posted prices, what households must buy, the starts.


def national_prices(o: Opening, w: Written, economy: Economy) -> dict[str, Fraction]:
    """The national posted price of a unit of each product households buy, micros, at the WRITTEN
    figures (decision 2): any product but a shop good at its written price (`Product.price_micros`,
    public provision its fee); a shop good as households pay it on average (ruling 6): the written
    price less the shops' saving a unit, plus the charge `ceil(hours x wage[shop] / units)`. A price
    of the solve only (nothing is written from it). Rounding rules: the shop's wage in micros an
    hour, half up (as `_Prices`); the charge a unit, up; the saving a unit exact, and the price
    on `TIER_GRID` (to the nearest 1/TIER_GRID, a half up) only where the saving makes it
    fractional. A shop good with no handling block is refused (`tiers_price: <product>`)."""
    q = o.quantities
    out: dict[str, Fraction] = {}
    trade_of = _trade_of(economy)
    shop = economy.shop_trade
    for product, trade in sorted(trade_of.items()):
        if (
            shop is not None
            and product in economy.shop_goods
            and trade not in (economy.capital_trade, economy.extraction_trade)
            and w.products[product].handling is None
        ):
            # A shop good with no handling block has no shop price to post: refused, never passed
            # at its written price.
            raise _fail("tiers_price", product)
    shop_wage = half_up(q.wage[shop] * MICROS) if shop is not None else 0
    for product, trade in sorted(trade_of.items()):
        made = w.products[product]
        if trade in (economy.capital_trade, economy.extraction_trade):
            continue
        if shop is not None and product in economy.shop_goods and made.handling is not None:
            res = q.final[trade] - o.exports.get(trade, _ZERO)
            saving = (
                o.shop_saving.get(trade, _ZERO) / res * made.dollars_per_unit * MICROS
                if res > 0
                else _ZERO
            )
            hours, units = made.handling
            charge = -((-(hours * shop_wage)) // units)
            out[product] = to_grid(Fraction(made.price_micros + charge) - saving, TIER_GRID)
        else:
            out[product] = Fraction(made.price_micros)
    return out


def households_buy(o: Opening, w: Written, economy: Economy) -> dict[str, Fraction]:
    """`D[i] = (fin[i] - X[i]) / u[i]`, units a period, of every product households buy but
    public provision, on `TIER_GRID` (rounding rule: to the nearest, a half up). A product with
    nothing for households is `tiers_demand: <product>`."""
    q = o.quantities
    out: dict[str, Fraction] = {}
    for product, trade in sorted(_trade_of(economy).items()):
        if trade in (economy.capital_trade, economy.extraction_trade, economy.public_trade):
            continue
        res = q.final[trade] - o.exports.get(trade, _ZERO)
        if res <= 0:
            raise _fail("tiers_demand", product)
        out[product] = to_grid(res / w.products[product].dollars_per_unit, TIER_GRID)
    return out


def households_spending(o: Opening, economy: Economy) -> dict[str, Fraction]:
    """`Hs[i]`: what households pay for each product they buy, shop goods at posted prices."""
    q = o.quantities
    out: dict[str, Fraction] = {}
    for product, trade in sorted(_trade_of(economy).items()):
        if trade in (economy.capital_trade, economy.extraction_trade, economy.public_trade):
            continue
        res = q.final[trade] - o.exports.get(trade, _ZERO)
        value = o.household_purchases[trade]
        if product in economy.shop_goods and economy.shop_trade is not None:
            value += o.markup * o.prices.prices[trade] * res
        out[product] = value
    return out


def start_one(problem: TierProblem, spending: Mapping[str, Fraction]) -> list[Fraction]:
    """The prototype's start (decision 7): half of tier 1 a person for the need products, consumer
    goods and business services sharing `cbar / 5` by `Hs`, `rho3` 13/10, leisure `4/5 cbar`."""
    shape, prices, cbar = problem.shape, problem.prices, problem.cbar_micros
    persons = sum(a.persons for a in problem.accounts if a.key != _RESIDENCE)
    households = sum(a.households for a in problem.accounts if a.key != _RESIDENCE)
    both = [p for p in shape.tier2 if p not in shape.needs]
    both_total = sum((spending[p] for p in both), _ZERO)
    z: list[Fraction] = []
    for p in shape.tier2:
        if p in shape.needs:
            per = Fraction(shape.days) * (
                _ONE if p in problem.economy.person_needs else Fraction(households, persons)
            )
            z.append(per / 2)
        else:
            z.append(cbar / 5 * spending[p] / both_total / prices[p])
    z += [Fraction(13, 10), Fraction(4, 5) * cbar / prices[WANT_LATE]]
    return z


def start_two(problem: TierProblem, spending: Mapping[str, Fraction]) -> list[Fraction]:
    """The second start (decision 8): each tier's products in proportion to households' spending,
    `rho3` 1, leisure what is left of tier 3's size."""
    shape, prices, cbar = problem.shape, problem.prices, problem.cbar_micros
    total = sum((spending[p] for p in shape.tier2), _ZERO)
    z = [problem.sizes[0] * cbar * spending[p] / total / prices[p] for p in shape.tier2]
    z += [_ONE, _ZERO]
    _, luxury = contents_of(shape, z)
    used = sum((luxury[p] * prices[p] for p in shape.tier3 if p != WANT_LATE), _ZERO)
    z[shape.late] = max(_ZERO, (problem.sizes[1] * cbar - used) / prices[WANT_LATE])
    return z


def whole_by_half_up(shape: Shape, z: Sequence[Fraction]) -> tuple[dict[str, int], dict[str, int]]:
    """Whole units a person from the unknowns, each half up (decision 9's first step)."""
    comfort, luxury = contents_of(shape, z)
    return (
        {p: half_up(v) for p, v in comfort.items()},
        {p: half_up(v) for p, v in luxury.items()},
    )


def check_unique(shape: Shape, first: Sequence[Fraction], second: Sequence[Fraction]) -> None:
    """Decision 8: two converged `z` whose whole-unit contents (each half up) differ are
    `tiers_not_unique: <products>`, the products sorted."""
    a_comfort, a_luxury = whole_by_half_up(shape, first)
    b_comfort, b_luxury = whole_by_half_up(shape, second)
    differ = {p for p in a_comfort if a_comfort[p] != b_comfort[p]}
    differ |= {p for p in a_luxury if a_luxury[p] != b_luxury[p]}
    if differ:
        raise _fail("tiers_not_unique", ", ".join(sorted(differ)))


def exact_spend(
    account: Account,
    tiers: tuple[list[Row], list[Row], list[Row]],
    prices: Mapping[str, Price],
) -> Bought:
    """R4 for an account that spends all (call 20, at a solution): bought without a scale, and
    when every row is bought with money left and a tier 3 to scale, bought again with the scale
    `(tier 3 cost + left) / tier 3 cost`."""
    first = _buy_tiers(account, tiers, prices, None)
    if first.pattern == (3, len(tiers[2]), False) and first.left_micros > 0:
        cost3 = _cost(account, tiers[2], prices)
        if cost3 > 0:
            return _buy_tiers(account, tiers, prices, (cost3 + first.left_micros) / cost3)
    return first


def _units_at(
    problem: TierProblem,
    comfort: Mapping[str, Fraction],
    luxury: Mapping[str, Fraction],
) -> dict[str, Fraction]:
    rows = want_rows(problem.shape, comfort, luxury, drop_zero=True)
    t2 = [r for r in rows if r.tier == 2]
    t3 = [r for r in rows if r.tier == 3]
    ones = {key: list(tier_one_rows(key, problem.shape, problem.economy)) for key in HOUSEHOLD_KEYS}
    total: dict[str, Fraction] = {}
    for account in problem.accounts:
        got = exact_spend(account, (ones[account.key], t2, t3), problem.prices)
        for good, count in got.units.items():
            total[good] = total.get(good, _ZERO) + count
    return total


def whole_contents(
    problem: TierProblem,
    z: Sequence[Fraction],
    demand: Mapping[str, Fraction],
) -> tuple[dict[str, int], dict[str, int]]:
    """Whole units (decision 9): each want half up, then for each product in the order of paying
    the floor or ceiling of each of its rows, whichever combination makes the product's bought
    units (at national prices, every other row held) nearest `D`; a tie goes to the combination
    with more units (a half up)."""
    shape = problem.shape
    comfort_x, luxury_x = contents_of(shape, z)
    comfort = {p: Fraction(half_up(v)) for p, v in comfort_x.items()}
    luxury = {p: Fraction(half_up(v)) for p, v in luxury_x.items()}
    for product in shape.order:
        rows: list[tuple[str, Fraction]] = []
        if product in comfort_x:
            rows.append(("comfort", comfort_x[product]))
        if product in luxury_x:
            rows.append(("luxury", luxury_x[product]))
        if not rows:
            continue
        options = [sorted({Fraction(math.floor(v)), Fraction(math.ceil(v))}) for _, v in rows]
        best: tuple[Fraction, Fraction, tuple[Fraction, ...]] | None = None
        for combo in _product(options):
            trial_c, trial_l = dict(comfort), dict(luxury)
            for (kind, _), units in zip(rows, combo, strict=True):
                (trial_c if kind == "comfort" else trial_l)[product] = units
            bought = _units_at(problem, trial_c, trial_l).get(product, _ZERO)
            score = (abs(bought - demand[product]), -sum(combo, _ZERO), combo)
            if best is None or score[:2] < best[:2]:
                best = score
        if best is None:
            raise _fail("tiers_unsolved", f"whole units: {product}")
        for (kind, _), units in zip(rows, best[2], strict=True):
            (comfort if kind == "comfort" else luxury)[product] = units
    return (
        {p: int(v) for p, v in comfort.items()},
        {p: int(v) for p, v in luxury.items()},
    )


def _product(options: Sequence[Sequence[Fraction]]) -> list[tuple[Fraction, ...]]:
    combos: list[tuple[Fraction, ...]] = [()]
    for choices in options:
        combos = [(*done, c) for done in combos for c in choices]
    return combos


# --------------------------------------------------------------------------------------
# Luxury scales (decision 10).


def luxury_scale_bps(
    account: Account,
    tiers: tuple[list[Row], list[Row], list[Row]],
    *,
    bounded: bool = True,
) -> int | None:
    """`floor(10_000 x (money - tier 1 - tier 2) / tier 3)`, each tier at the account's own prices
    and the written contents (rounding rule: down); None unless above 10,000. Above 1,000,000 is
    `luxury_scale_bound: <part>/<key>` (the compiler refuses it) unless `bounded` is False, when the
    caller checks the bound."""
    prices = account.own_prices
    c1, c2, c3 = (_cost(account, rows, prices) for rows in tiers)
    if c3 <= 0 or account.money_micros - c1 - c2 <= c3:
        return None
    bps = math.floor(BASIS * (account.money_micros - c1 - c2) / c3)
    if bps <= BASIS:
        return None
    if bounded and bps > SCALE_LIMIT_BPS:
        raise _fail("luxury_scale_bound", f"{account.place}/{account.key}")
    return bps


# --------------------------------------------------------------------------------------
# Every part's body opens even (decision 11).


def body_split(
    part: str, taxes: Fraction, payout: Fraction, payments: Fraction, providers: Fraction
) -> tuple[int, int, Fraction]:
    """A part's `(share to the fund in basis points, the fund's grant to it in micros, what it
    keeps above even)` from its taxes `T`, the public-owned payout `Q`, its payments `P` and its
    public providers' own grants (dollars a period). With `T > 0` and `T + Q >= P` the share is
    `10_000 - floor(10_000 (P - Q) / T)` (rounding rule: down), at least 0 and at most 10,000; a part
    whose payout alone passes its payments keeps `Q - P` above even. A part with `T + Q < P`, or
    with no taxes, keeps all its taxes and has the grant `ceil((P - Q - T) x 10^6)` (rounding rule:
    up) when above 0; one over its providers' grants is `place_grant_over_providers: <part>`."""
    if taxes > 0 and taxes + payout >= payments:
        kept_bps = math.floor(BASIS * (payments - payout) / taxes)
        share = min(BASIS, max(0, BASIS - kept_bps))
        return share, 0, max(_ZERO, payout - payments)
    gap = payments - payout - taxes
    if gap <= 0:
        return 0, 0, _ZERO
    grant = _ceil(gap * MICROS)
    if grant > providers * MICROS:
        raise _fail("place_grant_over_providers", part)
    return 0, grant, _ZERO


@dataclass(frozen=True)
class Bodies:
    taxes: Mapping[str, tuple[Fraction, Fraction, Fraction]]  # part -> taxes, payout, payments
    providers: Mapping[str, Fraction]  # part -> its public providers' own grants
    share_bps: Mapping[str, int]
    grant_micros: Mapping[str, int]
    over_even: Mapping[str, Fraction]


def place_bodies(
    o: Opening,
    census: Census,
    w: Written,
    settings: Settings,
    economy: Economy,
) -> Bodies:
    """Taxes `T_c = t (wages_c + OI_c + PO_c)`, the public-owned payout `Q_c = (1 - t) PO_c` and
    payments `P_c = grant_c + reserve_c x s` of every part at the exact solve, then each part's
    share and grant by `body_split`. `grant_c` is the compiler's: payroll + inputs at the part's
    share of the public workers + the wear of its public machines (rounded up to a micro, at the
    written machine price) - fee x persons served, at least 0."""
    incomes = place_incomes(o, census)
    q = o.quantities
    pub = economy.public_trade
    fee = Fraction(settings.public_fee_micros, MICROS)
    trade_of = _trade_of(economy)
    support = o.tier_quantities["food"] * o.prices.prices[trade_of["food"]]
    inputs = _ZERO
    emp_public = 0
    if pub is not None:
        inputs = sum(
            (
                q.coefficients.get(i, {}).get(pub, _ZERO) * o.prices.prices[i] * q.output[pub]
                for i in o.prices.prices
            ),
            _ZERO,
        ) - o.import_saving.get(pub, _ZERO)
        emp_public = census.trades[pub].employee_persons
    taxes_by: dict[str, tuple[Fraction, Fraction, Fraction]] = {}
    providers: dict[str, Fraction] = {}
    share: dict[str, int] = {}
    grants: dict[str, int] = {}
    over: dict[str, Fraction] = {}
    for place in census.places:
        income = incomes[place.label]
        taxes = o.tax_rate * (income.wages + income.private + income.public_owned)
        payout = (1 - o.tax_rate) * income.public_owned
        grant = _ZERO
        if pub is not None and emp_public > 0:
            row = place.trades[pub]
            # Rounding rule: a public provider's wear a period, up to a micro (Task 4).
            wear = _ceil(
                Fraction(place.public_machines * w.machine_price_micros, w.machine_life_periods)
            )
            grant = (
                Fraction(row.payroll_micros, MICROS)
                + inputs * row.employee_persons / emp_public
                + Fraction(wear, MICROS)
                - fee * place.public_persons_served
            )
            grant = max(_ZERO, grant)
        reserve = sum(c.reserve for c in place.keys.values())
        payments = grant + reserve * support
        taxes_by[place.label] = (taxes, payout, payments)
        providers[place.label] = grant
        kept = body_split(place.label, taxes, payout, payments, grant)
        share[place.label] = kept[0]
        if kept[1] > 0:
            grants[place.label] = kept[1]
        if kept[2] > 0:
            over[place.label] = kept[2]
    return Bodies(taxes_by, providers, share, grants, over)


# --------------------------------------------------------------------------------------
# What own prices and where a service is bought move: counted, not solved (decision 12).


def service_shares(
    counts: Mapping[tuple[str, str], tuple[Fraction, Fraction]], service: str
) -> tuple[Fraction, Fraction]:
    """`(idle, unserved)` of one service across the places that count it: the share of capacity in
    states that use less than they can make (what they leave unused over all capacity), and the
    share of use in states that want more than they can make (the excess over all use)."""
    rows = [cap_use for (_, name), cap_use in counts.items() if name == service]
    capacity = sum((c for c, _ in rows), _ZERO)
    use = sum((u for _, u in rows), _ZERO)
    idle = sum((c - u for c, u in rows if u < c), _ZERO)
    unserved = sum((u - c for c, u in rows if u > c), _ZERO)
    return (
        idle / capacity if capacity > 0 else _ZERO,
        unserved / use if use > 0 else _ZERO,
    )


@dataclass(frozen=True)
class _Counts:
    state_services: Mapping[tuple[str, str], tuple[Fraction, Fraction]]
    country_services: Mapping[str, tuple[Fraction, Fraction]]


def _count_services(
    o: Opening,
    census: Census,
    w: Written,
    settings: Settings,
    economy: Economy,
    bought: Mapping[tuple[str, HouseholdKey], Bought],
) -> _Counts:
    states = {place.label: place.state for place in census.places}
    # A trade's hours at work (employees, working owners and unpaid family, the solve's `hours`)
    # over its employee persons: the census's places hold employees only, so a part's hours are its
    # employee persons times this.
    per_employee = {
        trade: Fraction(o.quantities.hours[trade], count.employee_persons)
        for trade, count in census.trades.items()
        if count.employee_persons > 0 and trade in o.quantities.hours
    }
    capacity: dict[tuple[str, str], Fraction] = {}
    site_use: dict[tuple[str, str], Fraction] = {}
    shop_hours: dict[str, Fraction] = {}
    shop = economy.shop_trade
    for place in census.places:
        if shop is not None:
            shop_hours[place.state] = shop_hours.get(place.state, _ZERO) + (
                place.trades[shop].employee_persons * per_employee.get(shop, _ZERO)
            )
        for trade, recipe in sorted(w.recipes.items()):
            hours = place.trades[trade].employee_persons * per_employee.get(trade, _ZERO)
            key = (place.state, economy.product[trade])
            capacity[key] = capacity.get(key, _ZERO) + Fraction(
                hours * recipe.output_units_per_batch, recipe.labor_hours_per_batch
            )
            for good, count in recipe.inputs.items():
                if good in w.products:
                    use_key = (place.state, good)
                    site_use[use_key] = site_use.get(use_key, _ZERO) + Fraction(
                        hours * count, recipe.labor_hours_per_batch
                    )
    accounts_use: dict[tuple[str, str], Fraction] = {}
    shop_use: dict[str, Fraction] = {}
    for (place_label, _key), got in sorted(bought.items()):
        state = states[place_label]
        for good, units in got.units.items():
            k = (state, good)
            accounts_use[k] = accounts_use.get(k, _ZERO) + units
            made = w.products[good]
            if made.handling is not None:
                block_hours, block_units = made.handling
                shop_use[state] = shop_use.get(state, _ZERO) + units * Fraction(
                    block_hours, block_units
                )
    state_counts: dict[tuple[str, str], tuple[Fraction, Fraction]] = {}
    for state in sorted(set(states.values())):
        for service in sorted(economy.place_services):
            if service not in w.products:
                continue
            k = (state, service)
            state_counts[k] = (
                capacity.get(k, _ZERO),
                accounts_use.get(k, _ZERO) + site_use.get(k, _ZERO),
            )
        if shop is not None:
            state_counts[(state, SHOP_HOURS)] = (
                shop_hours.get(state, _ZERO),
                shop_use.get(state, _ZERO),
            )
    trade_of = _trade_of(economy)
    country: dict[str, tuple[Fraction, Fraction]] = {}
    for service in sorted(settings.country_services):
        if service not in w.products:
            continue
        trade = trade_of[service]
        unit = w.products[service].dollars_per_unit
        cap = sum((v for (_, name), v in capacity.items() if name == service), _ZERO)
        use = sum((v for (_, name), v in accounts_use.items() if name == service), _ZERO)
        use += sum((v for (_, name), v in site_use.items() if name == service), _ZERO)
        use += o.exports.get(trade, _ZERO) / unit
        use -= o.quantities.imports.get(trade, _ZERO) / unit
        country[service] = (cap, use)
    return _Counts(state_counts, country)


# --------------------------------------------------------------------------------------
# The whole of it.


@dataclass(frozen=True)
class Tiers:
    comfort: Mapping[str, int]
    luxury: Mapping[str, int]  # whole units a person a period, rows that round to 0 out
    exact: Mapping[str, Fraction]  # the solve's z, for the metadata
    luxury_scale_bps: Mapping[tuple[str, HouseholdKey], int]
    no_earner_estimate: Mapping[tuple[str, HouseholdKey], int]
    residence_estimate: Mapping[str, int]
    reach: Mapping[tuple[str, HouseholdKey], tuple[Fraction, Fraction, Fraction]]
    demand_gap: Mapping[str, Fraction]
    own_price_gap: Mapping[str, Fraction]
    state_services: Mapping[tuple[str, str], tuple[Fraction, Fraction]]
    country_services: Mapping[str, tuple[Fraction, Fraction]]
    place_bodies: Mapping[str, tuple[Fraction, Fraction, Fraction]]
    share_by_part_bps: Mapping[str, int]
    place_grant_micros: Mapping[str, int]
    # Beyond the interface of the task, for the metadata and the later parts.
    zero_rows: tuple[tuple[int, str], ...] = ()
    steps: int = 0
    starts: str = "both converged"
    over_even: Mapping[str, Fraction] = field(default_factory=dict)
    estimated_payments_micros: int = 0
    tier_costs: tuple[Fraction, Fraction] = (_ZERO, _ZERO)  # at written contents, micros a person
    accounts: tuple[Account, ...] = ()
    kept_micros: Mapping[tuple[str, HouseholdKey], Fraction] = field(default_factory=dict)
    # Every account whose money does not reach its own tier 1 at its own posted prices, as
    # (part label, key, gap in micros), sorted by part then key, for the metadata. A no-earner
    # account is promised its needs (O12, ruling 3): the slow test asserts none is here.
    short_accounts: tuple[tuple[str, str, int], ...] = ()


def _check_tier_money(
    problem: TierProblem, comfort: Mapping[str, int], luxury: Mapping[str, int]
) -> tuple[Fraction, Fraction]:
    shape, prices, cbar = problem.shape, problem.prices, problem.cbar_micros
    c2 = sum((comfort.get(g, 0) * prices[g] for g in shape.tier2), _ZERO)
    c3 = sum((luxury.get(g, 0) * prices[g] for g in shape.tier3), _ZERO)
    for name, cost, size in (("2", c2, problem.sizes[0]), ("3", c3, problem.sizes[1])):
        if abs(cost / (size * cbar) - 1) > Fraction(1, 100):
            raise _fail("want_rounding", name)
    return c2, c3


def _gaps(totals: Mapping[str, Fraction], demand: Mapping[str, Fraction]) -> dict[str, Fraction]:
    return {g: totals.get(g, _ZERO) / d - 1 for g, d in sorted(demand.items())}


def tiers(
    o: Opening,
    census: Census,
    w: Written,
    settings: Settings,
    economy: Economy = TWELVE,
) -> Tiers:
    """The tiers of wants and everything the builder estimates around them (decisions 1 to 12)."""
    shape = shape_of(settings, economy)
    drafts = _drafts(o, census, w, economy)
    accts = drafts.accounts
    prices = national_prices(o, w, economy)
    demand_all = households_buy(o, w, economy)
    demand = {p: demand_all[p] for p in shape.tier2}
    cbar = to_grid(o.tier_unit * MICROS, TIER_GRID)
    problem = TierProblem(
        accts,
        prices,
        demand,
        cbar,
        (settings.tier_sizes[1], settings.tier_sizes[2]),
        shape,
        economy,
    )
    spending = households_spending(o, economy)
    solved: list[tuple[list[Fraction], int]] = []
    unsolved: list[str] = []
    for label, start in (
        ("start_one", start_one(problem, spending)),
        ("start_two", start_two(problem, spending)),
    ):
        try:
            solved.append(solve_contents(problem, start))
        except ReferenceBuildError as error:
            if not str(error).startswith(("tiers_unsolved", "tiers_singular")):
                raise
            unsolved.append(f"{label}: {error}")
    if not solved:
        raise _fail("tiers_unsolved", "; ".join(unsolved))
    z, steps = solved[0]
    if len(solved) == 2:
        check_unique(shape, z, solved[1][0])
    starts = "both converged" if not unsolved else f"not converged: {'; '.join(unsolved)}"
    for name, value in zip(shape.names, z, strict=True):
        if value < 0:
            raise _fail("tiers_negative", name)
    comfort, luxury = whole_contents(problem, z, demand_all)
    c2, c3 = _check_tier_money(problem, comfort, luxury)
    zero_rows = tuple(
        sorted(
            [(2, g) for g in shape.tier2 if comfort.get(g, 0) == 0]
            + [(3, g) for g in shape.tier3 if luxury.get(g, 0) == 0]
        )
    )
    written_rows = want_rows(
        shape,
        {g: Fraction(v) for g, v in comfort.items()},
        {g: Fraction(v) for g, v in luxury.items()},
        drop_zero=True,
    )
    t2 = [r for r in written_rows if r.tier == 2]
    t3 = [r for r in written_rows if r.tier == 3]
    ones = {key: list(tier_one_rows(key, shape, economy)) for key in HOUSEHOLD_KEYS}
    national_totals = _units_at(
        problem,
        {g: Fraction(v) for g, v in comfort.items()},
        {g: Fraction(v) for g, v in luxury.items()},
    )
    scales: dict[tuple[str, HouseholdKey], int] = {}
    final: dict[tuple[str, HouseholdKey], Bought] = {}
    own_totals: dict[str, Fraction] = {}
    for account in accts:
        bps = luxury_scale_bps(account, (ones[account.key], t2, t3))
        scale = None
        if bps is not None:
            scales[(account.place, account.key)] = bps
            scale = Fraction(bps, BASIS)
        got = _buy_tiers(account, (ones[account.key], t2, t3), account.own_prices, scale)
        final[(account.place, account.key)] = got
        for good, units in got.units.items():
            own_totals[good] = own_totals.get(good, _ZERO) + units
    counts = _count_services(o, census, w, settings, economy, final)
    bodies = place_bodies(o, census, w, settings, economy)
    short: list[tuple[str, str, int]] = []
    for account in accts:
        need = _cost(account, ones[account.key], account.own_prices)
        if account.money_micros < need:
            # Rounding rule: the gap a period, up to a whole micro.
            short.append((account.place, account.key, _ceil(need - account.money_micros)))
    payments = sum(
        (est * a.persons for a in accts for est in [_estimate_of(drafts, a)] if est is not None), 0
    )
    return Tiers(
        comfort=comfort,
        luxury=luxury,
        exact=dict(zip(shape.names, z, strict=True)),
        luxury_scale_bps=scales,
        no_earner_estimate=drafts.no_earner,
        residence_estimate=drafts.residence,
        reach={k: v.reach for k, v in final.items()},
        demand_gap=_gaps(national_totals, demand_all),
        own_price_gap=_gaps(own_totals, demand_all),
        state_services=counts.state_services,
        country_services=counts.country_services,
        place_bodies=bodies.taxes,
        share_by_part_bps=bodies.share_bps,
        place_grant_micros=bodies.grant_micros,
        zero_rows=zero_rows,
        steps=steps,
        starts=starts,
        over_even=bodies.over_even,
        estimated_payments_micros=payments,
        tier_costs=(c2, c3),
        accounts=accts,
        kept_micros={k: v.left_micros for k, v in final.items()},
        short_accounts=tuple(sorted(short)),
    )


def _estimate_of(drafts: _Drafts, account: Account) -> int | None:
    if account.key == _RESIDENCE:
        return drafts.residence.get(account.place)
    return drafts.no_earner.get((account.place, account.key))


__all__ = [
    "SHOP_HOURS",
    "TIER_GRID",
    "Account",
    "Bought",
    "Row",
    "Tiers",
    "accounts",
    "body_split",
    "buy",
    "own_need_estimate",
    "service_shares",
    "tiers",
]
