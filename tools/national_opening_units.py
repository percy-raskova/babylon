#!/usr/bin/env python3
"""The builder of the rebuilt national opening, part 3 (Task 10b of stage 5).

Units, whole-number recipes, written prices, handling blocks, grams, machines, the
written taxes and trade shares, and the prices of a foreign region. Every figure is an
`int` or a `Fraction`; a `float` anywhere is a defect. Every rounding to an integer names
its rule where it is done. Every refusal is a `ReferenceBuildError` with a fixed code
before the first colon.

Keys. Products are keyed by PRODUCT (`food`, `resources`, ...); recipes, batch hours lost
and wages by TRADE (`food`, `extraction`, ...), as the solve keys them.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Final, Literal

from make_national_county_reference import ReferenceBuildError
from national_opening_recut import TWELVE, Census, Economy, Recut, Settings, half_up
from national_opening_solve import MICROS, Opening, machines_in_use

BATCHES: Final = (
    1,
    2,
    4,
    5,
    8,
    10,
    16,
    20,
    25,
    32,
    40,
    50,
    64,
    80,
    100,
    128,
    160,
    200,
    250,
    400,
    500,
    800,
    1000,
    2000,
    5000,
    10000,
    20000,
    50000,
    100000,
)
COST_ERROR: Final = Fraction(1, 200)  # a batch's cost a unit, at most this far from the exact one
HOURS_ERROR: Final = Fraction(1, 400)  # a batch's hours, at most this far from the exact ones
SUPPLIER_ERROR: Final = Fraction(1, 1000)  # each supplier's output moved by one recipe, at most
CLOSE_ERROR: Final = Fraction(
    1, 200
)  # demand moved by all buyers; wear against the equipment money
BLOCK_LIMIT: Final = 1000  # the most units in one handling block
PRICE_FLOOR_MICROS: Final = 1000  # a unit whose price rounds below this is `price_zero`
BASIS: Final = 10_000
_ZERO: Final = Fraction(0)

# The labels decision 1 gives: (label, unit label). Absent products keep the fixture's.
_LABELS: Final[Mapping[str, tuple[str, str]]] = {
    "food": ("Food for one person for a day", "person-day food"),
    "utility": ("Utility for one person for a day", "person-day utility"),
    "household_services": ("A day's care and schooling for one person", "person-day care"),
    "materials": ("Supplies for one household for a day", "household-day supplies"),
    "housing": ("Housing for one household for a day", "household-day housing"),
    "resources": ("A minute of extraction's output", "extraction minute"),
    "equipment": ("One machine", "machine"),
}
# A day's food's worth: the fixture's label with this suffix, and a unit label of its own.
_DAYS_FOOD: Final[Mapping[str, str]] = {
    "consumer_goods": "consumer goods bundle",
    "business_services": "business service unit",
    "leisure": "leisure unit",
}
DEPOSIT: Final = "resource_deposit"


def _fail(code: str, what: str = "") -> ReferenceBuildError:
    return ReferenceBuildError(f"{code}: {what}" if what else code)


@dataclass(frozen=True)
class TemplateFacts:
    """What the builder reads from the template: the fixture's labels, grams and prices.

    Task 13 reads it from the template's `#@fact` lines; Task 10b only consumes it."""

    labels: Mapping[str, tuple[str, str]]  # product -> (label, unit label)
    grams: Mapping[str, int]  # storable product -> grams a unit
    prices: Mapping[str, int]  # product -> opening price, micros


@dataclass(frozen=True)
class Product:
    key: str
    label: str
    unit_label: str
    kind: Literal["storable", "utility", "service"]
    dollars_per_unit: Fraction  # accounts dollars in one unit (u)
    price_micros: int
    minimum_micros: int
    maximum_micros: int
    step_micros: int
    grams_per_unit: int  # storable goods; 0 for services
    handling: tuple[int, int] | None  # (hours, units) for a shop good


@dataclass(frozen=True)
class Recipe:
    trade: str
    output_units_per_batch: int
    labor_hours_per_batch: int
    inputs: Mapping[str, int]
    margin_bps: int | None  # None for public provision
    exact_cost_micros: Fraction  # a unit, at written prices
    rounded_cost_micros: Fraction  # a unit, at written prices
    hours_error: Fraction = Fraction(0)  # `L / (h x n) - 1`, the batch's hours against exact
    input_errors: Mapping[str, Fraction] = field(
        default_factory=dict
    )  # share x (input / exact - 1)


@dataclass(frozen=True)
class Written:
    products: Mapping[str, Product]
    recipes: Mapping[str, Recipe]
    machine_price_micros: int
    workers_per_machine: Mapping[str, int]
    machine_life_periods: int
    wage_tax_bps: int
    operating_income_tax_bps: int
    fund_share_bps: int
    import_bps: Mapping[str, int]
    batch_hours_lost: Mapping[str, Fraction]  # an estimate, for the metadata (decision 5)
    demand_moved: Mapping[
        str, Fraction
    ]  # by product: its makers' output moved by its buyers' rounding (5b)
    machines_worn: Fraction  # a period, by use at the written recipes (decision 5b)


# --------------------------------------------------------------------------------------
# Handling blocks (decision 7).


def handling_block(hours_per_unit: Fraction) -> tuple[int, int]:
    """The smallest `units` in `1..=1000` whose hours, `half_up(exact x units)` and at least
    1, give an hours-a-unit within `exact / 200` of the exact one; none is
    `handling_rounding`."""
    if hours_per_unit <= 0:
        raise _fail("handling_rounding")
    tolerance = hours_per_unit * COST_ERROR
    for units in range(1, BLOCK_LIMIT + 1):
        # Rounding rule: a block's hours, half up.
        hours = half_up(hours_per_unit * units)
        if hours >= 1 and abs(Fraction(hours, units) - hours_per_unit) <= tolerance:
            return hours, units
    raise _fail("handling_rounding")


# --------------------------------------------------------------------------------------
# Whole-number recipes (decision 5).


def machine_life_batches(
    hours_per_person: int, workers_per_machine: int, life_periods: int, labor_hours_per_batch: int
) -> int:
    """Task 6b's rule: the batches a machine serves in its life. Its workers' hours a period
    over the life, divided by a batch's hours, half up and at least 1."""
    # Rounding rule: a machine's life in batches, half up, at least one.
    return max(
        1,
        half_up(
            Fraction(hours_per_person * workers_per_machine * life_periods, labor_hours_per_batch)
        ),
    )


def batch(
    trade: str,
    hours_per_unit: Fraction,
    inputs_per_unit: Mapping[str, Fraction],
    wage_micros: int,
    prices: Mapping[str, int],
    price_micros: int,
    wear_micros: Callable[[int], Fraction],
    shares: Mapping[str, Fraction],
    *,
    refusal: bool = True,
) -> Recipe:
    """The batch of a trade: the first `n` of `BATCHES` that is judged close on three sides
    (decision 5) and passes O5's refusal (`price x n` at least the batch's labor, its inputs
    and its wear). Its cost a unit is within 1/200 of the exact one, its hours within 1/400,
    and for each input `shares[i] x |input / exact input - 1|` is within 1/1000: how far its
    rounding moves what the input's makers are asked for. A batch with no hours or an input
    that rounds to 0 is skipped. If none, `recipe_rounding: <trade>`; there is no second rule.
    `refusal=False` leaves the refusal out (public provision: its fee is not its cost). A use
    of a product with no share given is `recipe_demand: <product>`. The margin is the caller's."""
    exact = wage_micros * hours_per_unit + sum(
        (units * prices[good] for good, units in inputs_per_unit.items()), _ZERO
    )
    if exact <= 0 or hours_per_unit <= 0:
        raise _fail("recipe_rounding", trade)
    for good in inputs_per_unit:
        if good not in shares:
            raise _fail("recipe_demand", good)
    for n in BATCHES:
        # Rounding rule: a batch's hours and each input, half up.
        hours = half_up(hours_per_unit * n)
        inputs = {good: half_up(units * n) for good, units in inputs_per_unit.items()}
        if hours == 0 or any(count == 0 for count in inputs.values()):
            continue
        batch_cost = wage_micros * hours + sum(
            (count * prices[good] for good, count in inputs.items()), _ZERO
        )
        if refusal and price_micros * n < batch_cost + wear_micros(hours):
            continue
        rounded = Fraction(batch_cost) / n
        if abs(rounded - exact) / exact > COST_ERROR:
            continue
        if abs(Fraction(hours) / (hours_per_unit * n) - 1) > HOURS_ERROR:
            continue
        if any(
            shares[good] * abs(Fraction(inputs[good]) / (units * n) - 1) > SUPPLIER_ERROR
            for good, units in inputs_per_unit.items()
        ):
            continue
        return Recipe(
            trade=trade,
            output_units_per_batch=n,
            labor_hours_per_batch=hours,
            inputs=inputs,
            margin_bps=None,
            exact_cost_micros=exact,
            rounded_cost_micros=rounded,
            hours_error=Fraction(hours) / (hours_per_unit * n) - 1,
            input_errors={
                good: shares[good] * (Fraction(inputs[good]) / (units * n) - 1)
                for good, units in sorted(inputs_per_unit.items())
            },
        )
    raise _fail("recipe_rounding", trade)


def moved_demand(
    recipes: Mapping[str, Recipe],
    exact_inputs: Mapping[str, Mapping[str, Fraction]],
    shares: Mapping[str, Mapping[str, Fraction]],
) -> dict[str, Fraction]:
    """Decision 5b: for each product, the sum over its buying trades of `shares[i] x (input /
    exact input - 1)`, signed: how far the written recipes move its makers' output. Above 1/200
    in size is `recipe_demand: <product>`."""
    moved: dict[str, Fraction] = {}
    for trade in sorted(recipes):
        for good, exact in sorted(exact_inputs[trade].items()):
            error = shares[trade][good] * (Fraction(recipes[trade].inputs[good]) / exact - 1)
            moved[good] = moved.get(good, _ZERO) + error
    for good, value in sorted(moved.items()):
        if abs(value) > CLOSE_ERROR:
            raise _fail("recipe_demand", good)
    return moved


def check_machine_wear(
    machines_worn: Fraction, machine_price_micros: int, equipment: Fraction
) -> None:
    """Decision 5b: the machines worn a period, at the machine's price, within 1/200 of the
    equipment money `E`; else `machine_wear`."""
    cost = machines_worn * machine_price_micros / MICROS
    if abs(cost / equipment - 1) > CLOSE_ERROR:
        raise _fail("machine_wear", f"{float_free(cost / equipment)}")


def float_free(value: Fraction) -> str:
    """A fraction as text, with no float: `numerator/denominator`."""
    return f"{value.numerator}/{value.denominator}"


# --------------------------------------------------------------------------------------
# Units and prices (decisions 1 to 4).


def bounds(price_micros: int, product: str) -> tuple[int, int, int]:
    """The minimum, maximum and step at the fixture's ratios: a quarter, four times and a
    fortieth, each rounded down, the step at least 1. A price under 1,000 micros is
    `price_zero: <product>`."""
    if price_micros < PRICE_FLOOR_MICROS:
        raise _fail("price_zero", product)
    return price_micros // 4, price_micros * 4, max(1, price_micros // 40)


def _trade_of(economy: Economy) -> dict[str, str]:
    return {product: trade for trade, product in economy.product.items()}


def _units(o: Opening, persons: int, settings: Settings, economy: Economy) -> dict[str, Fraction]:
    """Accounts dollars in one unit of each product (decisions 1 and 2)."""
    q = o.quantities
    trade_of = _trade_of(economy)
    p = o.prices.prices
    needs = (*economy.person_needs, *economy.household_needs)
    units: dict[str, Fraction] = {n: o.tier_quantities[n] / settings.days_per_period for n in needs}
    extraction = economy.product.get(economy.extraction_trade or "")
    capital = economy.product[economy.capital_trade]
    public = economy.product.get(economy.public_trade or "")
    if extraction is not None and economy.extraction_trade is not None:
        # A minute of extraction work: 1 / (60 x h) (decision 2).
        units[extraction] = Fraction(1) / (60 * q.hours_per_dollar[economy.extraction_trade])
    in_use = machines_in_use(q, settings)
    if in_use == 0:
        raise _fail("machines_empty")
    # One machine, sized by the machines IN USE: `NU / life` are worn and bought a period.
    units[capital] = (
        o.prices.equipment / p[economy.capital_trade] * settings.machine_life_periods / in_use
    )
    if public is not None and economy.public_trade is not None:
        units[public] = q.output[economy.public_trade] / persons
    for product, trade in sorted(trade_of.items()):
        if product in units:
            continue
        # A day's food in producer value: p[food] u[food] / p[i].
        units[product] = p[trade_of["food"]] * units["food"] / p[trade]
    return units


def _kind(
    product: str, settings: Settings, economy: Economy
) -> Literal["storable", "utility", "service"]:
    if product in economy.storable:
        return "storable"
    stage = settings.service_stage.get(product)
    if stage is None:
        raise _fail("setting", "service_stage")
    return "utility" if stage == 1 else "service"


def _labels(product: str, template: TemplateFacts) -> tuple[str, str]:
    if product in _LABELS:
        return _LABELS[product]
    if product not in template.labels:
        raise _fail("template_fact", product)
    label, unit = template.labels[product]
    if product in _DAYS_FOOD:
        return f"{label}, a day's food's worth", _DAYS_FOOD[product]
    return label, unit


def _grams(product: str, price_micros: int, template: TemplateFacts) -> int:
    """`max(1, half_up(fixture grams x price / fixture price))`: the fixture's grams per dollar."""
    if product not in template.grams or product not in template.prices:
        raise _fail("template_fact", product)
    return max(
        1, half_up(Fraction(template.grams[product] * price_micros, template.prices[product]))
    )


def _products(
    o: Opening,
    template: TemplateFacts,
    settings: Settings,
    economy: Economy,
    persons: int,
) -> dict[str, Product]:
    q = o.quantities
    trade_of = _trade_of(economy)
    units = _units(o, persons, settings, economy)
    shop = economy.shop_trade
    out: dict[str, Product] = {}
    for product in sorted(trade_of):
        trade = trade_of[product]
        if trade == economy.public_trade:
            price = settings.public_fee_micros
        else:
            # Rounding rule: a unit's price in micros, half up.
            price = half_up(o.prices.prices[trade] * units[product] * MICROS)
        low, high, step = bounds(price, product)
        handling: tuple[int, int] | None = None
        if shop is not None and product in economy.shop_goods:
            # Retail hours follow value: rho x p[i] u[i] / wage[shop] (the spike's assumption).
            exact = o.markup * o.prices.prices[trade] * units[product] / q.wage[shop]
            try:
                handling = handling_block(exact)
            except ReferenceBuildError as error:
                raise _fail("handling_rounding", product) from error
        label, unit_label = _labels(product, template)
        out[product] = Product(
            key=product,
            label=label,
            unit_label=unit_label,
            kind=_kind(product, settings, economy),
            dollars_per_unit=units[product],
            price_micros=price,
            minimum_micros=low,
            maximum_micros=high,
            step_micros=step,
            grams_per_unit=_grams(product, price, template) if product in economy.storable else 0,
            handling=handling,
        )
    return out


def _recipes(
    o: Opening,
    products: Mapping[str, Product],
    settings: Settings,
    economy: Economy,
) -> tuple[dict[str, Recipe], dict[str, Fraction], Fraction]:
    """The eleven recipes, the demand each product's makers are moved by, and the machines
    worn a period at the written recipes (decisions 5 and 5b)."""
    q = o.quantities
    machine_price = products[economy.product[economy.capital_trade]].price_micros
    written_prices = {key: product.price_micros for key, product in products.items()}
    hpp = settings.work_hours_per_person
    life = settings.machine_life_periods
    out: dict[str, Recipe] = {}
    exact_inputs: dict[str, dict[str, Fraction]] = {}
    shares_of: dict[str, dict[str, Fraction]] = {}
    for trade in economy.trades:
        if trade not in economy.product:
            continue
        product = products[economy.product[trade]]
        unit = product.dollars_per_unit
        per_unit: dict[str, Fraction] = {}
        shares: dict[str, Fraction] = {}
        for i in economy.trades:
            coefficient = q.coefficients.get(i, {}).get(trade, _ZERO)
            if coefficient > 0:
                made = products[economy.product[i]]
                if q.output.get(i, _ZERO) <= 0:
                    raise _fail("recipe_demand", made.key)
                per_unit[made.key] = coefficient * unit / made.dollars_per_unit
                # The part of product i's makers' output that this trade buys.
                shares[made.key] = coefficient * q.output[trade] / q.output[i]
        workers = settings.workers_per_machine[trade]

        def wear(hours: int, workers: int = workers) -> Fraction:
            # Wear a batch: a machine's price over the batches it serves (Task 6b).
            return Fraction(machine_price, machine_life_batches(hpp, workers, life, hours))

        public = trade == economy.public_trade
        recipe = batch(
            trade,
            q.hours_per_dollar[trade] * unit,
            per_unit,
            half_up(q.wage[trade] * MICROS),
            written_prices,
            product.price_micros,
            wear,
            shares,
            refusal=not public,
        )
        exact_inputs[trade] = {
            good: units * recipe.output_units_per_batch for good, units in per_unit.items()
        }
        shares_of[trade] = shares
        margin: int | None = None
        if not public:
            mu = o.prices.margins[trade]
            # Rounding rule: half up off the floor; up on it, so a floor is never undercut.
            margin = math.ceil(mu * BASIS) if trade in o.prices.floored else half_up(mu * BASIS)
        inputs = dict(recipe.inputs)
        if economy.extraction_trade == trade:
            inputs[DEPOSIT] = recipe.output_units_per_batch  # the deposit rule
        out[trade] = replace(recipe, margin_bps=margin, inputs=inputs)
    moved = moved_demand(out, exact_inputs, shares_of)
    worn = sum(
        (
            Fraction(q.hours[trade], recipe.labor_hours_per_batch)
            / machine_life_batches(
                hpp, settings.workers_per_machine[trade], life, recipe.labor_hours_per_batch
            )
            for trade, recipe in sorted(out.items())
        ),
        _ZERO,
    )
    check_machine_wear(worn, machine_price, o.prices.equipment)
    return out, moved, worn


def _import_bps(o: Opening, settings: Settings, economy: Economy) -> dict[str, int]:
    """Decision 8: a good's share is `half_up(10_000 x import_cover)`; a crossing service's is
    the solve's `service_import_bps`; above 10,000 is `import_coverage`."""
    q = o.quantities
    trade_of = _trade_of(economy)
    out: dict[str, int] = {}
    for product in sorted(settings.crossing):
        trade = trade_of[product]
        if product in economy.storable:
            # Rounding rule: basis points, half up.
            value = half_up(BASIS * q.import_cover.get(trade, _ZERO))
        else:
            value = q.service_import_bps.get(trade, 0)
        if value > BASIS:
            raise _fail("import_coverage", product)
        out[product] = value
    return out


def written(
    o: Opening,
    recut: Recut,
    census: Census,
    settings: Settings,
    template: TemplateFacts,
    economy: Economy = TWELVE,
) -> Written:
    """The numbers of the opening as the scenario writes them (decisions 1 to 8)."""
    del recut  # the re-cut is read through the solve; kept for the interface
    persons = sum(c.persons for c in census.households.values())
    products = _products(o, template, settings, economy, persons)
    recipes, moved, worn = _recipes(o, products, settings, economy)
    q = o.quantities
    lost = {
        trade: Fraction(census.trades[trade].sites * recipe.labor_hours_per_batch, 2)
        / q.hours[trade]
        for trade, recipe in recipes.items()
    }
    # Rounding rule: a rate in basis points, half up.
    rate = half_up(o.tax_rate * BASIS)
    return Written(
        products=products,
        recipes=recipes,
        machine_price_micros=products[economy.product[economy.capital_trade]].price_micros,
        workers_per_machine={t: settings.workers_per_machine[t] for t in sorted(recipes)},
        machine_life_periods=settings.machine_life_periods,
        wage_tax_bps=rate,
        operating_income_tax_bps=rate,
        fund_share_bps=half_up(o.fund_share * BASIS),
        import_bps=_import_bps(o, settings, economy),
        batch_hours_lost=lost,
        demand_moved=moved,
        machines_worn=worn,
    )


def deposit_grams(w: Written) -> int:
    """The deposit keeps the grams of resources."""
    return w.products["resources"].grams_per_unit


# --------------------------------------------------------------------------------------
# A region's prices (decision 9).


def own_price(
    recipe: Recipe, national_micros: int, site_wage_micros: int, national_wage_micros: int
) -> int:
    """O5's price (Task 14b): `p + floor((w_site - w_nation) x L x (10_000 + margin) / (10_000
    x n))`, the floor toward negative infinity, as the compiler's `div_euclid`."""
    margin = recipe.margin_bps or 0
    labor = (
        (site_wage_micros - national_wage_micros)
        * recipe.labor_hours_per_batch
        * (BASIS + margin)
        // (BASIS * recipe.output_units_per_batch)
    )
    return national_micros + labor


def shop_estimate(region_price: int, national_price: int, export_bps: int) -> int:
    """E7's estimate of what a shop abroad pays for a good: `ceil((region's own price x (10_000
    - export_bps) + the country's written price x export_bps) / 10_000)`."""
    return -((-(region_price * (BASIS - export_bps) + national_price * export_bps)) // BASIS)


def _region_makers(
    w: Written, o: Opening, wage_micros: Mapping[str, int], economy: Economy
) -> dict[str, int]:
    out: dict[str, int] = {}
    for product, made in sorted(w.products.items()):
        trade = _trade_of(economy)[product]
        if trade == economy.public_trade:
            out[product] = made.price_micros
            continue
        if trade not in wage_micros:
            raise _fail("region_wage", trade)
        national = half_up(o.quantities.wage[trade] * MICROS)
        price = own_price(w.recipes[trade], made.price_micros, wage_micros[trade], national)
        if price <= 0:
            raise _fail("region_price", product)
        out[product] = price
    return out


def region_maker_prices(
    w: Written, o: Opening, wage_micros: Mapping[str, int], economy: Economy = TWELVE
) -> Mapping[str, int]:
    """Each product's price at the region's census wage, as its makers post it: Task 14b's
    `own_price` on the written recipe and margin; public provision's fee as at home."""
    return _region_makers(w, o, wage_micros, economy)


def region_prices(
    w: Written,
    o: Opening,
    wage_micros: Mapping[str, int],
    census: Census,  # noqa: ARG001 (the region's wages come in `wage_micros`)
    export_bps: Mapping[str, int] | None = None,
    economy: Economy = TWELVE,
) -> Mapping[str, int]:
    """Each product's price in a region (O5; ruling 6, E7). A maker's is `region_maker_prices`.
    A shop good is as the region's retailers post it: what they pay plus the charge at the
    region's shop wage. What they pay is an ESTIMATE (the compiler's is the average over the
    makers it deals the shop): `shop_estimate` with the region's own price of the good and
    the share `export_bps` gives; with `export_bps` not given, the national price."""
    makers = _region_makers(w, o, wage_micros, economy)
    shop = economy.shop_trade
    if shop is None or shop not in wage_micros:
        return makers
    out = dict(makers)
    for product, made in w.products.items():
        if made.handling is None:
            continue
        hours, units = made.handling
        # Rounding rule: the charge a unit, up.
        charge = -((-(hours * wage_micros[shop])) // units)
        share = (export_bps or {}).get(product)
        if share is None:
            paid = made.price_micros
        else:
            paid = shop_estimate(makers[product], made.price_micros, share)
        out[product] = paid + charge
    return out
