#!/usr/bin/env python3
"""The builder of the rebuilt national opening, part 6: the scenario (Task 13 of stage 5).

Reads the accounts table, the pay table and the census of the twelve-trade opening, solves
the opening's numbers with exact fractions (the five `tools/national_opening_*.py` parts),
checks the four balances of O6 at the numbers AS WRITTEN, and writes the scenario
`content/scenarios/national-rebuilt/defines.toml` (schema 8) and its metadata, the builder's
balance sheet. The scenario is text from `tools/national_opening_v13_defines.toml.in` with
each `#@builder <name>` marker line replaced by TOML this module writes.

Every figure is an `int` or a `Fraction`; a `float` anywhere is a defect. Every rounding to an
integer names its rule where it is done. Every refusal is a `ReferenceBuildError` with a fixed
code before the first colon. Output is deterministic: sorted keys, `\\n` line ends.

Usage::

    UV_PROJECT_ENVIRONMENT=.venv mise exec -- uv run --frozen python tools/make_national_opening_numbers.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from fractions import Fraction
from pathlib import Path
from typing import Any, Final

from make_national_county_reference import ROOT, ReferenceBuildError
from national_opening_abroad import RegionOpening, regions, scale_rows
from national_opening_recut import (
    ACCOUNTS_PATH,
    BUDGET_LABEL,
    CENSUS_PATH,
    HOUSEHOLD_KEYS,
    PRODUCT,
    TWELVE,
    Census,
    Economy,
    HouseholdKey,
    Place,
    Recut,
    Settings,
    check_ruled,
    half_up,
    read_accounts,
    read_census,
    recut,
)
from national_opening_solve import MICROS, Opening, solve
from national_opening_tiers import (
    SHOP_HOURS,
    WANT_BOTH,
    WANT_LATE,
    Account,
    Bought,
    Tiers,
    buy,
    households_buy,
    place_incomes,
    service_shares,
    shape_of,
    tier_one_rows,
    tiers,
    want_rows,
)
from national_opening_units import TemplateFacts, Written, written

TEMPLATE: Final = ROOT / "tools/national_opening_v13_defines.toml.in"
SCENARIO_OUT: Final = ROOT / "content/scenarios/national-rebuilt/defines.toml"
METADATA_OUT: Final = ROOT / "content/scenarios/national-rebuilt/defines.metadata.json"
PAY_PATH: Final = ROOT / "src/babylon/data/reference/economy/national_trade_pay_2024.csv.gz"
# The five builder parts and this file (the plan's "six"): the metadata pins each one's digest.
BUILDER_SOURCES: Final[tuple[Path, ...]] = (
    ROOT / "tools/national_opening_recut.py",
    ROOT / "tools/national_opening_solve.py",
    ROOT / "tools/national_opening_units.py",
    ROOT / "tools/national_opening_tiers.py",
    ROOT / "tools/national_opening_abroad.py",
    ROOT / "tools/make_national_opening_numbers.py",
)
# The compiler's bound on a policy of schema 8 (`admission.rs` `parse`, raised by Task 1b, E4).
POLICY_BOUND: Final = 262_144
REGENERATE: Final = (
    "UV_PROJECT_ENVIRONMENT=.venv mise exec -- uv run --frozen python "
    "tools/make_national_opening_numbers.py"
)
BASIS: Final = 10_000
BALANCE_BOUND: Final = Fraction(1, 100)  # each residual over its flow, at most
PRIVATE_DISTRIBUTION_BPS: Final = 10_000  # balance 4 holds only at a full payout (the spike)
RESERVE_FOOD_SUPPORT_PERIODS: Final = 1
OWN_NEEDS_SHARE_BPS: Final = 10_000  # E8: the needs in full; politics may cut or raise it
UNMET_FOOD_HOURS: Final = 20  # today's hours for a person's period of food (call 18)
GRAIN_BASIS: Final = (16, 16, 1, 14_000)  # the shipped food figures (O15), in the template
_ZERO: Final = Fraction(0)

# The order the fixture lists its tables in; a table's own keys are sorted.
PRODUCT_ORDER: Final[tuple[str, ...]] = (
    "food",
    "resources",
    "materials",
    "equipment",
    "utility",
    "housing",
    "household_services",
    "business_services",
    "public_provision",
    "consumer_goods",
    "leisure",
)
TRADE_ORDER: Final[tuple[str, ...]] = (
    "food",
    "extraction",
    "energy_utilities",
    "manufacturing",
    "capital_goods",
    "construction_housing",
    "household_services",
    "business_services",
    "public_provisioning",
    "consumer_goods",
    "leisure_hospitality",
)
# The six needs, in the fixture's order: (good, basis, units a basis).
NEED_ROWS: Final[tuple[tuple[str, str], ...]] = (
    ("food", "persons"),
    ("materials", "households"),
    ("utility", "persons"),
    ("housing", "households"),
    ("household_services", "persons"),
    ("public_provision", "persons"),
)
# The ruling that set each choice (26 November 2026), for the metadata.
RULINGS: Final[Mapping[str, str]] = {
    "service_stage": "26 November, ruling 1 (V6, D7): regrouped, no engine change",
    "paying_order": "26 November, ruling 1 (V6, D7)",
    "crossing": "26 November, ruling 2 (V8, K1, E2): business services cross",
    "benefit_rule": "26 November, ruling 3 (V3 road (b), E8): each account's own needs",
    "place_body": "26 November, ruling 4 (V1 with V2 road (b), K4, K5): every place opens even",
    "country_services": "26 November, ruling 5 (V9, K2, D5)",
    "shop_import_saving": "26 November, ruling 6 (V10, D6): households, in the price",
}

_LABEL_OF: Final[Mapping[str, str]] = {str(key): BUDGET_LABEL[key] for key in HOUSEHOLD_KEYS}
_MARKER: Final = re.compile(r"^#@builder (\S+)$")
_FACT: Final = re.compile(r"^#@fact (\S+) \| (.+) \| (.+) \| (\d+) \| (\d+)$")
_CARGO: Final = re.compile(r"^#@cargo (\S+) \| (\S+)$")
_TREASURY: Final = re.compile(r"^opening_treasury_bps\s*=\s*(\d+)\s*(?:#.*)?$", re.M)


def _fail(code: str, what: str = "") -> ReferenceBuildError:
    return ReferenceBuildError(f"{code}: {what}" if what else code)


# --------------------------------------------------------------------------------------
# The template.


def template_facts(template: str) -> TemplateFacts:
    """The fixture's labels, grams and opening prices from the template's fact lines
    (`#@fact <key> | <label> | <unit label> | <grams> | <price micros>`). A product with a
    price of 0 (the deposit) has a label only; a unit with no grams has none."""
    labels: dict[str, tuple[str, str]] = {}
    grams: dict[str, int] = {}
    prices: dict[str, int] = {}
    for line in template.split("\n"):
        match = _FACT.match(line)
        if match is None:
            continue
        key, label, unit_label, gram, price = match.groups()
        labels[key] = (label, unit_label)
        if int(gram) > 0:
            grams[key] = int(gram)
        if int(price) > 0:
            prices[key] = int(price)
    return TemplateFacts(labels=labels, grams=grams, prices=prices)


def template_cargo(template: str) -> dict[str, str]:
    """Each storable priced product's cargo class, from the template's `#@cargo` lines."""
    return {m.group(1): m.group(2) for line in template.split("\n") if (m := _CARGO.match(line))}


# --------------------------------------------------------------------------------------
# TOML text. Integers only; keys sorted inside a table; `\n` line ends.


def _int(value: object, what: str) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _fail("scenario_shape", what)
    return str(value)


def _text(value: str) -> str:
    # A JSON string with ASCII escapes is a valid TOML basic string.
    return json.dumps(value, ensure_ascii=True)


def _inline(rows: Mapping[str, int], what: str) -> str:
    inner = ", ".join(f"{key} = {_int(rows[key], what)}" for key in sorted(rows))
    return "{ " + inner + " }" if inner else "{}"


def _table(header: str, rows: Mapping[str, str]) -> str:
    """A table: the header, then each key sorted, its value already written."""
    return "\n".join([header, *(f"{key} = {rows[key]}" for key in sorted(rows))])


def _list(items: Sequence[str]) -> str:
    return "[" + ", ".join(_text(item) for item in items) + "]"


def _commodity(w: Written, key: str, cargo: Mapping[str, str]) -> str:
    product = w.products[key]
    rows = {
        "grams_per_unit": _int(product.grams_per_unit, key),
        "kind": _text(product.kind),
        "label": _text(product.label),
        "maximum_price_micros": _int(product.maximum_micros, key),
        "minimum_price_micros": _int(product.minimum_micros, key),
        "opening_price_micros": _int(product.price_micros, key),
        "price_step_micros": _int(product.step_micros, key),
        "unit_label": _text(product.unit_label),
    }
    if product.kind == "storable":
        if key not in cargo:
            raise _fail("template_fact", key)
        rows["cargo_class"] = _text(cargo[key])
    if product.handling is not None:
        rows["handling_hours"] = _int(product.handling[0], key)
        rows["handling_units"] = _int(product.handling[1], key)
    return _table(f"[commodity.{key}]", rows)


def _deposit(w: Written, facts: TemplateFacts) -> str:
    """The deposit keeps the grams and the unit of resources (the deposit rule)."""
    if "resource_deposit" not in facts.labels:
        raise _fail("template_fact", "resource_deposit")
    resources = w.products["resources"]
    rows = {
        "grams_per_unit": _int(resources.grams_per_unit, "resource_deposit"),
        "kind": _text("storable"),
        "label": _text(facts.labels["resource_deposit"][0]),
        "unit_label": _text(resources.unit_label),
    }
    return _table("[commodity.resource_deposit]", rows)


def _process(w: Written, trade: str) -> str:
    recipe = w.recipes[trade]
    rows = {
        "inputs": _inline(recipe.inputs, trade),
        "labor_hours_per_batch": _int(recipe.labor_hours_per_batch, trade),
        "output": _text(TWELVE.product[trade]),
        "output_units_per_batch": _int(recipe.output_units_per_batch, trade),
    }
    if recipe.margin_bps is not None:
        rows["margin_bps"] = _int(recipe.margin_bps, trade)
    return _table(f"[process.{trade}]", rows)


def _wants(t: Tiers, settings: Settings) -> str:
    """The want rows, comfort then luxury, each in product order; each product the census
    scenario gives a want row keeps at least one, else `wants_cover: <product>` (E3)."""
    blocks: list[str] = []
    covered: set[str] = set()
    for tier, units in (("comfort", t.comfort), ("luxury", t.luxury)):
        for good in sorted(units):
            count = units[good]
            if count <= 0:
                continue
            if good not in settings.paying_order:
                raise _fail("scenario_shape", f"want {good}")
            covered.add(good)
            blocks.append(
                _table(
                    "[[household_wants]]",
                    {
                        "basis": _text("persons"),
                        "good": _text(good),
                        "tier": _text(tier),
                        "units_per_basis": _int(count, good),
                    },
                )
            )
    for good in (*WANT_BOTH, WANT_LATE):
        if good not in covered:
            raise _fail("wants_cover", good)
    return "\n\n".join(blocks)


def _needs(settings: Settings) -> str:
    blocks = []
    for good, basis in NEED_ROWS:
        count = 1 if good == "public_provision" else settings.days_per_period
        blocks.append(
            _table(
                "[[household_needs]]",
                {
                    "basis": _text(basis),
                    "good": _text(good),
                    "units_per_basis": _int(count, good),
                },
            )
        )
    return "\n\n".join(blocks)


def _programs(settings: Settings) -> str:
    rows = [
        {
            "half_periods": _int(settings.laid_off_half_periods, "laid_off"),
            "key": _text("laid_off"),
            "kind": _text("after_layoff"),
            "rank": "0",
            "recipients": _text("earning_or_residence_at_opening"),
            "wage_share_bps": _int(settings.laid_off_wage_share_bps, "laid_off"),
        },
        {
            "key": _text("no_earner"),
            "kind": _text("own_needs"),
            "rank": "0",
            "recipients": _text("no_earner_at_opening"),
            "share_bps": _int(OWN_NEEDS_SHARE_BPS, "no_earner"),
        },
        {
            "key": _text("residence"),
            "kind": _text("own_needs"),
            "rank": "0",
            "recipients": _text("collective_residence_at_opening"),
            "share_bps": _int(OWN_NEEDS_SHARE_BPS, "residence"),
        },
    ]
    return "\n\n".join(_table("[[programs]]", row) for row in rows)


def _region_block(key: str, region: RegionOpening, settings: Settings) -> str:
    if set(region.export_bps) != set(settings.crossing):
        raise _fail("scenario_shape", f"export_bps/{key}")
    rows = {
        "export_bps": _inline(region.export_bps, key),
        "function_weights_bps": "[" + ", ".join(str(n) for n in region.function_weights_bps) + "]",
        "price_scale_bps": "10000",
    }
    return "\n".join(f"{name} = {rows[name]}" for name in sorted(rows))


def _luxury(t: Tiers, abroad: Mapping[str, RegionOpening]) -> str:
    accounts: dict[str, int] = {}
    for (part, key), bps in t.luxury_scale_bps.items():
        accounts[f"{part}:{BUDGET_LABEL[key]}"] = bps
    for account, bps in scale_rows(abroad).items():
        if account in accounts:
            raise _fail("scenario_shape", f"luxury_scale {account}")
        accounts[account] = bps
    lines = [
        f"{_text(account)} = {_int(bps, account)}" for account, bps in sorted(accounts.items())
    ]
    return "\n".join(["[luxury_scale.by_account]", *lines])


def _blocks(
    w: Written,
    t: Tiers,
    abroad: Mapping[str, RegionOpening],
    settings: Settings,
    facts: TemplateFacts,
    cargo: Mapping[str, str],
) -> dict[str, str]:
    if set(w.products) != set(PRODUCT_ORDER) or set(w.recipes) != set(TRADE_ORDER):
        raise _fail("scenario_shape", "products")
    if w.wage_tax_bps != w.operating_income_tax_bps:
        raise _fail("scenario_shape", "rates")  # one rate, the same on both (call 5)
    if set(w.import_bps) != set(settings.crossing):
        raise _fail("scenario_shape", "import_bps")
    crossing = sorted(p for p in settings.crossing if w.products[p].kind != "storable")
    grants = "\n\n".join(
        _table(
            "[[place_grants]]",
            {
                "amount_per_period_micros": _int(micros, part),
                "part": _text(part),
            },
        )
        for part, micros in sorted(t.place_grant_micros.items())
    )
    share = ", ".join(
        f"{_text(part)} = {_int(bps, part)}" for part, bps in sorted(t.share_by_part_bps.items())
    )
    food_hours = max(1, half_up(Fraction(UNMET_FOOD_HOURS, settings.days_per_period)))
    blocks = {
        "import_bps": f"import_bps = {_inline(w.import_bps, 'import_bps')}",
        "crossing_services": f"crossing_services = {_list(crossing)}",
        "country_services": f"country_services = {_list(sorted(settings.country_services))}",
        "paying_order": f"paying_order = {_list(settings.paying_order)}",
        "financial": "\n".join(
            [
                f"operating_income_tax_bps = {_int(w.operating_income_tax_bps, 'rate')}",
                f"private_distribution_bps = {PRIVATE_DISTRIBUTION_BPS}",
                f"reserve_food_support_periods = {RESERVE_FOOD_SUPPORT_PERIODS}",
                f"wage_tax_bps = {_int(w.wage_tax_bps, 'rate')}",
            ]
        ),
        "fund": "\n".join(
            [
                f"operating_income_tax_share_bps = {_int(w.fund_share_bps, 'fund')}",
                f"reserve_periods = {_int(settings.fund_reserve_periods, 'fund')}",
                f"wage_tax_share_bps = {_int(w.fund_share_bps, 'fund')}",
            ]
        ),
        "share_by_part": "share_by_part = { " + share + " }" if share else "share_by_part = {}",
        "place_grants": grants,
        "programs": _programs(settings),
        "unmet_hours": f"unmet_hours_per_unit = {{ food = {food_hours} }}",
        "equipment": "\n".join(
            [
                f"machine_life_periods = {_int(w.machine_life_periods, 'equipment')}",
                f"workers_per_machine = {_inline(w.workers_per_machine, 'equipment')}",
            ]
        ),
        "commodities": "\n\n".join(
            [*(_commodity(w, p, cargo) for p in PRODUCT_ORDER), _deposit(w, facts)]
        ),
        "processes": "\n\n".join(_process(w, trade) for trade in TRADE_ORDER),
        "household_needs": _needs(settings),
        "household_wants": _wants(t, settings),
        "luxury_scale": _luxury(t, abroad),
    }
    for key, region in sorted(abroad.items()):
        blocks[f"region:{key}"] = _region_block(key, region, settings)
    return blocks


def render(
    template: str,
    w: Written,
    t: Tiers,
    regions: Mapping[str, RegionOpening],
    settings: Settings,
) -> str:
    """The scenario's text: the template with each marker line replaced by the TOML written here.
    An unknown marker, one left over, or a computed block with no marker is `template_marker:
    <name>`; a template that does not open every company without working capital is
    `template_marker: opening_treasury_bps`; a text past `POLICY_BOUND` is `scenario_size`."""
    treasury = _TREASURY.search(template)
    if treasury is None or int(treasury.group(1)) != 0:
        raise _fail("template_marker", "opening_treasury_bps")
    facts = template_facts(template)
    cargo = template_cargo(template)
    blocks = _blocks(w, t, regions, settings, facts, cargo)
    used: set[str] = set()
    out: list[str] = []
    for line in template.split("\n"):
        if _FACT.match(line) or _CARGO.match(line):
            continue
        marker = _MARKER.match(line)
        if marker is not None:
            name = marker.group(1)
            if name not in blocks or name in used:
                raise _fail("template_marker", name)
            used.add(name)
            out.append(blocks[name])
            continue
        if "#@" in line:
            raise _fail("template_marker", line.strip())
        out.append(line)
    unused = sorted(set(blocks) - used)
    if unused:
        raise _fail("template_marker", unused[0])
    text = "\n".join(out)
    if len(text.encode("utf-8")) > POLICY_BOUND:
        raise _fail("scenario_size", str(len(text.encode("utf-8"))))
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise _fail("scenario_toml", str(error)) from error
    if document.get("schema_version") != 8:
        raise _fail("scenario_toml", "schema_version")
    return text


# --------------------------------------------------------------------------------------
# What the accounts buy, and the jobs the written recipes need.


def purchases(
    t: Tiers, settings: Settings, economy: Economy = TWELVE
) -> dict[tuple[str, HouseholdKey], Bought]:
    """What each account buys by R4 at the written contents, its scale and its own prices (as
    Task 11 evaluates them)."""
    shape = shape_of(settings, economy)
    rows = want_rows(
        shape,
        {g: Fraction(v) for g, v in t.comfort.items()},
        {g: Fraction(v) for g, v in t.luxury.items()},
        drop_zero=True,
    )
    ones = {key: tier_one_rows(key, shape, economy) for key in HOUSEHOLD_KEYS}
    out: dict[tuple[str, HouseholdKey], Bought] = {}
    for account in t.accounts:
        bps = t.luxury_scale_bps.get((account.place, account.key))
        scale = Fraction(bps, BASIS) if bps is not None else None
        out[(account.place, account.key)] = buy(
            account, (*ones[account.key], *rows), account.own_prices, scale
        )
    return out


def household_units(
    o: Opening, w: Written, t: Tiers, economy: Economy = TWELVE
) -> dict[str, Fraction]:
    """What households buy at the written figures and the national prices (Task 11's `demand_gap`
    basis): each product's `D` times one more than its gap; public provision, 1 a person."""
    need = households_buy(o, w, economy)
    units = {good: need[good] * (1 + t.demand_gap[good]) for good in need}
    if economy.public_trade is not None:
        units[economy.product[economy.public_trade]] = Fraction(sum(a.persons for a in t.accounts))
    return units


def bought_units(bought: Mapping[tuple[str, HouseholdKey], Bought]) -> dict[str, Fraction]:
    """What the accounts buy at their own prices, by product."""
    units: dict[str, Fraction] = {}
    for got in bought.values():
        for good, count in got.units.items():
            units[good] = units.get(good, _ZERO) + count
    return units


def jobs_needed(
    o: Opening,
    w: Written,
    households: Mapping[str, Fraction],
    economy: Economy = TWELVE,
) -> dict[str, tuple[Fraction, int]]:
    """For each trade, `(hours the written recipes need, census hours)`: the units its product is
    asked for (businesses at the census hours, the households' units given, exports, the machines
    worn by use) less what is bought abroad, over the recipe's output a batch, times its hours a
    batch; the shop's hours through the handling blocks."""
    q = o.quantities
    demand: dict[str, Fraction] = dict.fromkeys(w.products, _ZERO)
    for trade, recipe in sorted(w.recipes.items()):
        batches = Fraction(q.hours[trade], recipe.labor_hours_per_batch)
        for good, count in recipe.inputs.items():
            if good in demand:
                demand[good] += count * batches
    shop_hours = _ZERO
    for good, units in households.items():
        demand[good] += units
        handling = w.products[good].handling
        if handling is not None:
            shop_hours += units * Fraction(handling[0], handling[1])
    trade_of = {product: trade for trade, product in economy.product.items()}
    for trade, dollars in o.exports.items():
        product = economy.product[trade]
        demand[product] += dollars / w.products[product].dollars_per_unit
    demand[economy.product[economy.capital_trade]] += w.machines_worn
    out: dict[str, tuple[Fraction, int]] = {}
    for product, units in sorted(demand.items()):
        trade = trade_of[product]
        imported = q.imports.get(trade, _ZERO) / w.products[product].dollars_per_unit
        recipe = w.recipes[trade]
        hours = (units - imported) * recipe.labor_hours_per_batch / recipe.output_units_per_batch
        out[trade] = (hours, q.hours[trade])
    if economy.shop_trade is not None:
        out[economy.shop_trade] = (shop_hours, q.hours[economy.shop_trade])
    return out


# --------------------------------------------------------------------------------------
# The four balances at the numbers as written (design 8.1, decision 5).


@dataclass(frozen=True)
class PartBalance:
    taxes: Fraction  # at the written rates, dollars a period
    payout: Fraction
    payments: Fraction
    to_fund: Fraction  # what the fund collects of its taxes at its split rates
    grant: Fraction  # the fund's grant to its providers
    residual: Fraction  # (taxes - to_fund) + payout + grant - payments


def part_balances(o: Opening, census: Census, w: Written, t: Tiers) -> dict[str, PartBalance]:
    """Each part's body at the written rates, the split `floor(rate x share / 10_000)` of Task 4
    and its grant (decision 5)."""
    incomes = place_incomes(o, census)
    out: dict[str, PartBalance] = {}
    for place in census.places:
        income = incomes[place.label]
        share = t.share_by_part_bps[place.label]
        # Rounding rule: the fund's rate, in whole basis points, down (`split_rate`).
        fund_wage = w.wage_tax_bps * share // BASIS
        fund_income = w.operating_income_tax_bps * share // BASIS
        operating = income.private + income.public_owned
        taxes = (
            Fraction(w.wage_tax_bps, BASIS) * income.wages
            + Fraction(w.operating_income_tax_bps, BASIS) * operating
        )
        to_fund = (
            Fraction(fund_wage, BASIS) * income.wages + Fraction(fund_income, BASIS) * operating
        )
        payout = (1 - Fraction(w.operating_income_tax_bps, BASIS)) * income.public_owned
        payments = t.place_bodies[place.label][2]
        grant = Fraction(t.place_grant_micros.get(place.label, 0), MICROS)
        out[place.label] = PartBalance(
            taxes=taxes,
            payout=payout,
            payments=payments,
            to_fund=to_fund,
            grant=grant,
            residual=taxes - to_fund + payout + grant - payments,
        )
    return out


def written_balances(
    o: Opening,
    census: Census,
    w: Written,
    t: Tiers,
    regs: Mapping[str, RegionOpening],
    bought: Mapping[tuple[str, HouseholdKey], Bought],
) -> dict[str, tuple[Fraction, Fraction]]:
    """O6 at the written figures, each as `(flow, residual)` in dollars a period (decision 5):

    - `1`: the accounts' money against what they buy by R4 (`left` is what they keep);
    - `2`: the nation's receipts (taxes at the written rates and the public-owned payout) against
      its payments (the parts' payments and the benefits as the builder estimates them);
    - `2_fund`: the fund's receipts (its split of the taxes) against the estimated benefits and
      the sum of the place grants;
    - `3`: exports at written prices and shares against imports at the regions' prices;
    - `4`: the machines worn by use at the machine's written price against the equipment money."""
    parts = part_balances(o, census, w, t)
    money = Fraction(sum(a.money_micros for a in t.accounts), MICROS)
    kept = sum((got.left_micros for got in bought.values()), _ZERO) / MICROS
    benefits = Fraction(t.estimated_payments_micros, MICROS)
    receipts = sum((p.taxes + p.payout for p in parts.values()), _ZERO)
    payments = sum((p.payments for p in parts.values()), _ZERO) + benefits
    fund_in = sum((p.to_fund for p in parts.values()), _ZERO)
    fund_out = benefits + sum((p.grant for p in parts.values()), _ZERO)
    sales = Fraction(sum(r.sales_micros for r in regs.values()))
    exported = Fraction(sum(r.purchases_written_micros for r in regs.values()))
    worn = w.machines_worn * w.machine_price_micros / MICROS
    return {
        "1": (money, kept),
        "2": (payments, receipts - payments),
        "2_fund": (fund_out, fund_in - fund_out),
        "3": (sales / MICROS, (exported - sales) / MICROS),
        "4": (o.prices.equipment, worn - o.prices.equipment),
    }


def check_balances(balances: Mapping[str, tuple[Fraction, Fraction]]) -> None:
    """Each residual at most 1/100 of its flow, else `balance: <n>`."""
    for name, (flow, residual) in sorted(balances.items()):
        if flow <= 0 or abs(residual) > BALANCE_BOUND * flow:
            raise _fail("balance", name)


# --------------------------------------------------------------------------------------
# The metadata.


def decimal(value: Fraction) -> str:
    """A fraction as a decimal string to 9 places, half up (for reading only)."""
    scaled = half_up(value * 10**9)
    sign = "-" if scaled < 0 else ""
    whole, rest = divmod(abs(scaled), 10**9)
    return f"{sign}{whole}.{rest:09d}"


EXACT_LIMIT_BITS: Final = 256  # a fraction of more bits than this is not written whole


def fr(value: Fraction | int) -> dict[str, str]:
    """A fraction written as the string `n/d` and beside it its decimal. The solve's fractions
    sit on grids of 2^64 and have thousands of digits; one whose numerator and denominator
    pass `EXACT_LIMIT_BITS` is written as its two sizes in bits, `long: <n> over <d> bits`."""
    exact = Fraction(value)
    bits = (exact.numerator.bit_length(), exact.denominator.bit_length())
    if max(bits) > EXACT_LIMIT_BITS:
        text = f"long: {bits[0]} over {bits[1]} bits"
    else:
        text = f"{exact.numerator}/{exact.denominator}"
    return {"decimal": decimal(exact), "exact": text}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _setting(value: object) -> object:
    if isinstance(value, Fraction):
        return fr(value)
    if isinstance(value, Mapping):
        return {str(k): _setting(v) for k, v in sorted(value.items())}
    if isinstance(value, (set, frozenset)):
        return sorted(str(v) for v in value)
    if isinstance(value, (tuple, list)):
        return [_setting(v) for v in value]
    return value


def _trade_oi(o: Opening, census: Census, place: Place, trade: str) -> tuple[Fraction, Fraction]:
    """A part's operating income of one trade and its public-owned part (the rule of
    `place_incomes`, for one trade)."""
    site = census.trades[trade]
    row = place.trades[trade]
    mu = o.prices.margins.get(trade, _ZERO)
    if site.employee_persons <= 0 or trade not in o.operating_income:
        return _ZERO, _ZERO
    of = site.employee_persons
    value = o.operating_income[trade]
    total = (
        value * Fraction(row.employee_persons, of)
        + mu
        * (row.payroll_micros - Fraction(site.payroll_micros * row.employee_persons, of))
        / MICROS
    )
    public = (
        value * Fraction(row.public_employee_persons, of)
        + mu
        * (
            row.public_payroll_micros
            - Fraction(site.payroll_micros * row.public_employee_persons, of)
        )
        / MICROS
    )
    return total, public


def _claims(o: Opening, census: Census, w: Written) -> dict[str, Any]:
    """The two designed cross-border claims, which the solve leaves out (`financial.rs`
    `foreign_claim`): `cross_border_ownership_bps` of Wayne's private consumer goods plants to
    Japan. Canada's plants to Wayne are not solved (the regions carry no operating income)."""
    del w
    wayne = next((p for p in census.places if p.label == "26163"), None)
    claim: dict[str, Any] = {
        "canada_plants_to_wayne": "not_solved",
        "cross_border_ownership_bps": 2000,
    }
    if wayne is not None:
        total, public = _trade_oi(o, census, wayne, "consumer_goods")
        claim["wayne_private_plants_operating_income_dollars"] = fr(total - public)
        claim["wayne_to_japan_dollars"] = fr((total - public) * 2000 / BASIS)
    return claim


def _trades(o: Opening, census: Census, w: Written, cut: Recut, economy: Economy) -> dict[str, Any]:
    q = o.quantities
    rate = Fraction(w.wage_tax_bps, BASIS)
    out: dict[str, Any] = {}
    for trade in TRADE_ORDER:
        count = census.trades[trade]
        recipe = w.recipes[trade]
        product = economy.product[trade]
        share = (
            Fraction(count.public_employee_persons, count.employee_persons)
            if count.employee_persons > 0
            else _ZERO
        )
        income = o.operating_income.get(trade, _ZERO)
        firms = sum(
            (
                q.coefficients.get(trade, {}).get(j, _ZERO) * q.output[j]
                for j in economy.trades
                if j in q.output and j != economy.public_trade
            ),
            _ZERO,
        )
        public_takes = q.coefficients.get(trade, {}).get(
            economy.public_trade or "", _ZERO
        ) * q.output.get(economy.public_trade or "", _ZERO)
        out[trade] = {
            "accounts_margin": fr(cut.accounts_margin[trade]),
            "batch_hours_lost": fr(w.batch_hours_lost[trade]),
            "exports": fr(o.exports.get(trade, _ZERO)),
            "firms_take": fr(firms),
            "households_take": fr(o.household_purchases.get(product, _ZERO)),
            "hours": q.hours[trade],
            "import_saving": fr(o.import_saving.get(trade, _ZERO)),
            "inputs": dict(sorted(recipe.inputs.items())),
            "labor_hours_per_batch": recipe.labor_hours_per_batch,
            "machines": q.machines.get(trade, 0),
            "margin_written_bps": recipe.margin_bps,
            "operating_income": fr(income),
            "output": fr(q.output[trade]),
            "output_units_per_batch": recipe.output_units_per_batch,
            "payout": fr((1 - rate) * income),
            "persons_at_work": {
                "employees": count.employee_persons,
                "unpaid_family": count.unpaid_family_persons,
                "working_owners": count.working_owner_persons,
            },
            "public_bodies_take": fr(public_takes),
            "public_owned_part": fr(income * share),
            "recipe_cost_exact_micros": fr(recipe.exact_cost_micros),
            "recipe_cost_rounded_micros": fr(recipe.rounded_cost_micros),
            "recipe_cost_error": fr(
                recipe.rounded_cost_micros / recipe.exact_cost_micros - 1
                if recipe.exact_cost_micros > 0
                else _ZERO
            ),
            "tax": fr(rate * income),
            "wage": fr(q.wage[trade]),
            "wear": fr(o.wear.get(trade, _ZERO)),
        }
    return out


def _by_key(t: Tiers, bought: Mapping[tuple[str, HouseholdKey], Bought]) -> dict[str, Any]:
    persons: dict[str, int] = dict.fromkeys(HOUSEHOLD_KEYS, 0)
    money: dict[str, int] = dict.fromkeys(HOUSEHOLD_KEYS, 0)
    spent: dict[str, list[Fraction]] = {k: [_ZERO, _ZERO, _ZERO] for k in HOUSEHOLD_KEYS}
    by_place: dict[str, dict[str, str]] = {}
    account_of: dict[tuple[str, str], Account] = {(a.place, a.key): a for a in t.accounts}
    for (part, key), got in sorted(bought.items()):
        account = account_of[(part, key)]
        persons[key] += account.persons
        money[key] += account.money_micros
        for tier in range(3):
            spent[key][tier] += got.reach[tier] * account.persons
        # Rounding rule: a person's money in micros, down.
        reach = " ".join(decimal(r) for r in got.reach)
        by_place.setdefault(part, {})[BUDGET_LABEL[key]] = (
            f"{account.money_micros // account.persons} micros a person; reach {reach}"
        )
    nation: dict[str, Any] = {}
    for key in HOUSEHOLD_KEYS:
        if persons[key] == 0:
            continue
        nation[BUDGET_LABEL[key]] = {
            "money_per_person_micros": money[key] // persons[key],
            "persons": persons[key],
            "reach_mean": [decimal(spent[key][i] / persons[key]) for i in range(3)],
        }
    return {"by_part": by_place, "national": nation}


def _jobs_meta(jobs: Mapping[str, tuple[Fraction, int]]) -> dict[str, Any]:
    return {
        trade: {
            "census_hours": census_hours,
            "needed_hours": fr(needed),
            "ratio": fr(needed / census_hours if census_hours else _ZERO),
        }
        for trade, (needed, census_hours) in sorted(jobs.items())
    }


def metadata(
    *,
    cut: Recut,
    o: Opening,
    w: Written,
    t: Tiers,
    regs: Mapping[str, RegionOpening],
    census: Census,
    settings: Settings,
    balances: Mapping[str, tuple[Fraction, Fraction]],
    jobs: Mapping[str, tuple[Fraction, int]],
    jobs_own: Mapping[str, tuple[Fraction, int]],
    bought: Mapping[tuple[str, HouseholdKey], Bought],
    inputs: Mapping[str, Any],
    scenario_bytes: int,
    economy: Economy = TWELVE,
) -> dict[str, Any]:
    """The builder's balance sheet (decision 6)."""
    parts = part_balances(o, census, w, t)
    parts_meta: dict[str, Any] = {}
    for label, p in sorted(parts.items()):
        taxes_exact, payout_exact, payments_exact = t.place_bodies[label]
        parts_meta[label] = {
            "grant_micros": t.place_grant_micros.get(label, 0),
            "payments": decimal(payments_exact),
            "payout": decimal(payout_exact),
            "residual": decimal(p.residual),
            "share_bps": t.share_by_part_bps[label],
            "taxes": decimal(taxes_exact),
            "taxes_written": decimal(p.taxes),
        }
    largest = max(parts.items(), key=lambda kv: (abs(kv[1].residual), kv[0]))
    sends = sum(1 for bps in t.share_by_part_bps.values() if bps > 0)
    dues: dict[str, dict[str, int]] = {"no_earner": {}, "residence": {}}
    persons_of = {(a.place, a.key): a.persons for a in t.accounts}
    for (part, key), estimate in sorted(t.no_earner_estimate.items()):
        dues["no_earner"][part] = (
            dues["no_earner"].get(part, 0) + estimate * persons_of[(part, key)]
        )
    for part, estimate in sorted(t.residence_estimate.items()):
        dues["residence"][part] = estimate * persons_of[(part, "collective_residence")]
    amounts = sorted([*t.no_earner_estimate.values(), *t.residence_estimate.values()])
    moved: dict[str, dict[str, dict[str, str]]] = {}
    for (reason, trade), value in sorted(cut.moved.items()):
        moved.setdefault(reason, {})[PRODUCT.get(trade, trade)] = fr(value)
    shop_goods = sorted(p for p, made in w.products.items() if made.handling is not None)
    estimated: dict[str, dict[str, dict[str, int]]] = {}
    for account in t.accounts:
        row = estimated.setdefault(account.place, {}).setdefault(BUDGET_LABEL[account.key], {})
        for good in shop_goods:
            row[good] = account.own_prices[good]
    wants = {
        good: {
            "comfort_units": t.comfort.get(good, 0),
            "exact": decimal(t.exact[good]) if good in t.exact else None,
            "luxury_units": t.luxury.get(good, 0),
        }
        for good in sorted(set(t.comfort) | set(t.luxury))
    }
    states: dict[str, Any] = {}
    for service in sorted({*economy.place_services, SHOP_HOURS}):
        idle, unserved = service_shares(t.state_services, service)
        states[service] = {"idle": fr(idle), "unserved": fr(unserved)}
    meta: dict[str, Any] = {
        "balances": {
            "as_written": {
                name: {"flow": fr(flow), "residual": fr(residual)}
                for name, (flow, residual) in sorted(balances.items())
            },
            "exact_solve": {
                name: {"flow": fr(flow), "residual": fr(residual)}
                for name, (flow, residual) in sorted(o.balances.items())
            },
        },
        "benefits": {
            "amount_a_person_micros": {
                "highest": amounts[-1] if amounts else 0,
                "lowest": amounts[0] if amounts else 0,
                "median": amounts[len(amounts) // 2] if amounts else 0,
            },
            "estimated_dues_micros": dues,
            "estimated_total_micros": t.estimated_payments_micros,
            "gap_to_solve_micros": t.estimated_payments_micros - half_up(o.benefits * MICROS),
            "note": "an estimate: the compiler works each amount out (Task 4, E8)",
            "solve_benefits": fr(o.benefits),
        },
        "business_services": {
            "export_bps_by_region": {
                key: region.export_bps.get("business_services", 0)
                for key, region in sorted(regs.items())
            },
            "import_bps": w.import_bps.get("business_services", 0),
            "import_weights": {
                trade: fr(v)
                for trade, v in sorted(
                    o.quantities.import_buyers.get("business_services", {}).items()
                )
            },
        },
        "claims": _claims(o, census, w),
        "contract": "NationalOpeningNumbersV1",
        "country_services": {
            service: {"capacity": fr(cap), "use": fr(use)}
            for service, (cap, use) in sorted(t.country_services.items())
        },
        "demand_gap": {g: fr(v) for g, v in sorted(t.demand_gap.items())},
        "demand_moved": {g: fr(v) for g, v in sorted(w.demand_moved.items())},
        "fund": {
            "grant_rows": len(t.place_grant_micros),
            "grant_sum_micros": sum(t.place_grant_micros.values()),
            "national_share_bps": w.fund_share_bps,
            "parts_sending_a_share": sends,
        },
        "inputs": dict(inputs),
        "issue": "PER-371",
        "jobs_as_written": _jobs_meta(jobs),
        "jobs_at_own_prices": _jobs_meta(jobs_own),
        "keys": _by_key(t, bought),
        "machines": {
            "cost_against_equipment": fr(
                w.machines_worn * w.machine_price_micros / MICROS / o.prices.equipment
            ),
            "in_use": fr(
                sum(
                    (
                        Fraction(o.quantities.hours[tr], settings.work_hours_per_person * wk)
                        for tr, wk in sorted(settings.workers_per_machine.items())
                    ),
                    _ZERO,
                )
            ),
            "price_micros": w.machine_price_micros,
            "worn_a_period": fr(w.machines_worn),
        },
        "moved_and_dropped": {
            "dropped": {
                f"{reason}/{trade}": fr(v) for (reason, trade), v in sorted(cut.dropped.items())
            },
            "moved": {
                f"{reason}/{trade}": fr(v) for (reason, trade), v in sorted(cut.moved.items())
            },
        },
        "notes": (
            "Every Fraction is written as an object with its exact `n/d` string and a decimal "
            "string to 9 places, half up, for reading only; a figure by part is a decimal string "
            "or an integer of micros."
        ),
        "own_price_gap": {g: fr(v) for g, v in sorted(t.own_price_gap.items())},
        "parts": {
            "largest_residual": {
                "dollars": decimal(largest[1].residual),
                "part": largest[0],
            },
            "over_even": {k: decimal(v) for k, v in sorted(t.over_even.items())},
            "rows": parts_meta,
        },
        "rate": {
            "exact": fr(o.tax_rate),
            "written_bps": w.wage_tax_bps,
        },
        "recut": {
            "moved": moved,
        },
        "regenerate": REGENERATE,
        "regions": {
            key: {
                "export_bps": dict(sorted(region.export_bps.items())),
                "function_weights_bps": list(region.function_weights_bps),
                "luxury_scale_bps": region.luxury_scale_bps,
                "money_per_person_micros": region.money_per_person_micros,
                "purchases_micros": region.purchases_micros,
                "purchases_written_micros": region.purchases_written_micros,
                "rounds": region.rounds,
                "sales_micros": region.sales_micros,
            }
            for key, region in sorted(regs.items())
        },
        "scale": {
            "scaled_accounts": [
                {"account": f"{part}:{BUDGET_LABEL[key]}", "scale_bps": bps}
                for (part, key), bps in sorted(t.luxury_scale_bps.items())
            ],
        },
        "scenario_bytes": scenario_bytes,
        "settings": {
            "choices": {
                field.name: {
                    "ruling": RULINGS.get(field.name, "the design's figure"),
                    "value": _setting(getattr(settings, field.name)),
                }
                for field in fields(settings)
            },
        },
        "shops": {
            "estimated_price_micros": estimated,
            "saving_by_good": {g: fr(v) for g, v in sorted(o.shop_saving.items())},
        },
        "short_accounts": [
            {"gap_micros": gap, "key": _LABEL_OF[key], "part": part}
            for part, key, gap in t.short_accounts
        ],
        "solve": {
            "C": fr(o.spending),
            "cbar": fr(o.tier_unit),
            "export_factor": fr(o.export_factor),
            "fund_share": fr(o.fund_share),
            "lam": fr(o.lam),
        },
        "state_services": states,
        "tiers": {
            "comfort_cost_micros": fr(t.tier_costs[0]),
            "luxury_cost_micros": fr(t.tier_costs[1]),
            "starts": t.starts,
            "steps": t.steps,
            "wants": wants,
            "zero_rows": [{"good": good, "tier": tier} for tier, good in t.zero_rows],
        },
        "trades": _trades(o, census, w, cut, economy),
    }
    return meta


# --------------------------------------------------------------------------------------
# The build.


def _inputs(accounts: Path, pay: Path, census: Census, template: Path) -> dict[str, Any]:
    return {
        "accounts_sha256": _digest(accounts),
        "builder_sources_sha256": {
            str(path.relative_to(ROOT)): _digest(path) for path in BUILDER_SOURCES
        },
        "census_text_sha256": census.sha256,
        "pay_sha256": _digest(pay),
        "template_sha256": _digest(template),
    }


def build(
    *,
    accounts: Path,
    pay: Path,
    census: Path,
    settings: Settings = Settings(),  # noqa: B008
    scenario_out: Path = SCENARIO_OUT,
    metadata_out: Path = METADATA_OUT,
) -> dict[str, Any]:
    """Read the tables, solve, check the four balances as written and write the scenario and
    its metadata. Every choice at a value other than the ruled one is `setting_not_ruled:
    <field>` before any file is read; a residual over 1/100 of its flow is `balance: <n>`."""
    check_ruled(settings)
    template_text = TEMPLATE.read_text(encoding="utf-8")
    facts = template_facts(template_text)
    cut = recut(read_accounts(accounts), settings)
    cen = read_census(census)
    o = solve(cut, cen, settings)
    w = written(o, cut, cen, settings, facts)
    t = tiers(o, cen, w, settings)
    regs = dict(regions(o, cen, w, t, settings))
    text = render(template_text, w, t, regs, settings)
    bought = purchases(t, settings)
    balances = written_balances(o, cen, w, t, regs, bought)
    check_balances(balances)
    jobs = jobs_needed(o, w, household_units(o, w, t))
    jobs_own = jobs_needed(o, w, bought_units(bought))
    meta = metadata(
        cut=cut,
        o=o,
        w=w,
        t=t,
        regs=regs,
        census=cen,
        settings=settings,
        balances=balances,
        jobs=jobs,
        jobs_own=jobs_own,
        bought=bought,
        inputs=_inputs(accounts, pay, cen, TEMPLATE),
        scenario_bytes=len(text.encode("utf-8")),
    )
    scenario_out.parent.mkdir(parents=True, exist_ok=True)
    metadata_out.parent.mkdir(parents=True, exist_ok=True)
    scenario_out.write_bytes(text.encode("utf-8"))
    metadata_out.write_bytes((json.dumps(meta, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return meta


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    scenario_out, metadata_out = SCENARIO_OUT, METADATA_OUT
    if len(args) == 2:
        scenario_out, metadata_out = Path(args[0]), Path(args[1])
    elif args:
        print("usage: make_national_opening_numbers.py [SCENARIO_OUT METADATA_OUT]")  # noqa: T201
        return 2
    try:
        meta = build(
            accounts=ACCOUNTS_PATH,
            pay=PAY_PATH,
            census=CENSUS_PATH,
            scenario_out=scenario_out,
            metadata_out=metadata_out,
        )
    except ReferenceBuildError as error:
        print(f"refused: {error}")  # noqa: T201
        return 1
    print(f"wrote {scenario_out} ({meta['scenario_bytes']} bytes) and {metadata_out}")  # noqa: T201
    for name, row in sorted(meta["balances"]["as_written"].items()):
        print(  # noqa: T201
            f"balance {name}: flow {row['flow']['decimal']}, residual {row['residual']['decimal']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
