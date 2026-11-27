#!/usr/bin/env python3
"""The builder of the rebuilt national opening, part 1 (Task 9 of stage 5).

This module holds three things that every later part reads: the builder's settings
(the Director's rulings of 26 November as named values, and the design's figures),
the census of the twelve-trade opening (Task 8) as typed Python, and the accounts
re-cut to the buyers the game has (rules R1 to R3 and O4).

The arithmetic of Part II is exact. Every figure is an `int` or a `Fraction`; a
`float` anywhere is a defect. Every rounding to an integer names its rule where it
is done: `half_up` (to the nearest, a half up), `floor` (down) or `ceil` (up). Every
refusal is a `ReferenceBuildError` whose message starts with a fixed code.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal

from make_national_county_reference import ROOT, ReferenceBuildError

ACCOUNTS_PATH: Final = (
    ROOT / "src/babylon/data/reference/economy/national_trade_accounts_2024.csv.gz"
)
CENSUS_PATH: Final = ROOT / "src/babylon/data/reference/economy/national_opening_census_v13.json.gz"

TRADES: Final[tuple[str, ...]] = (
    "food",
    "extraction",
    "energy_utilities",
    "manufacturing",
    "consumer_goods",
    "capital_goods",
    "construction_housing",
    "distribution_transport",
    "household_services",
    "leisure_hospitality",
    "business_services",
    "public_provisioning",
)
PRODUCT: Final[Mapping[str, str]] = MappingProxyType(
    {
        "food": "food",
        "extraction": "resources",
        "energy_utilities": "utility",
        "manufacturing": "materials",
        "consumer_goods": "consumer_goods",
        "capital_goods": "equipment",
        "construction_housing": "housing",
        "household_services": "household_services",
        "leisure_hospitality": "leisure",
        "business_services": "business_services",
        "public_provisioning": "public_provision",
    }
)

HouseholdKey = Literal[
    "earning_lower_paid_half",
    "earning_better_paid_forty",
    "earning_owner",
    "no_earner_nonowner",
    "no_earner_owner",
    "collective_residence",
]
HOUSEHOLD_KEYS: Final[tuple[HouseholdKey, ...]] = (
    "earning_lower_paid_half",
    "earning_better_paid_forty",
    "earning_owner",
    "no_earner_nonowner",
    "no_earner_owner",
    "collective_residence",
)
# `HouseholdBudgetKey::label()`: a luxury scale's account is `<part label>:<this>`.
BUDGET_LABEL: Final[Mapping[HouseholdKey, str]] = MappingProxyType(
    {
        "earning_lower_paid_half": "EarningLowerPaidHalf",
        "earning_better_paid_forty": "EarningBetterPaidForty",
        "earning_owner": "EarningOwner",
        "no_earner_nonowner": "NoEarnerNonowner",
        "no_earner_owner": "NoEarnerOwner",
        "collective_residence": "CollectiveResidence",
    }
)
# The census spells a household key as `HouseholdBudgetKey`'s serde label.
_CENSUS_KEY: Final[Mapping[str, HouseholdKey]] = MappingProxyType(
    {key.replace("_", "-"): key for key in HOUSEHOLD_KEYS}
)
BenefitRule = Literal["each_account_own"]
PlaceBody = Literal["every_place_even"]
ShopImportSaving = Literal["households"]


@dataclass(frozen=True)
class Economy:
    """Which trades exist and what each is. TWELVE is the game's; tests build small ones."""

    trades: tuple[str, ...]
    product: Mapping[str, str]
    storable: frozenset[str]
    shop_trade: str | None
    public_trade: str | None
    capital_trade: str
    extraction_trade: str | None
    shop_goods: frozenset[str]
    person_needs: tuple[str, ...]
    household_needs: tuple[str, ...]
    place_services: frozenset[str]


TWELVE: Final = Economy(
    trades=TRADES,
    product=PRODUCT,
    storable=frozenset({"food", "resources", "materials", "consumer_goods", "equipment"}),
    shop_trade="distribution_transport",
    public_trade="public_provisioning",
    capital_trade="capital_goods",
    extraction_trade="extraction",
    shop_goods=frozenset({"food", "materials", "consumer_goods"}),
    person_needs=("food", "utility", "household_services"),
    household_needs=("materials", "housing"),
    place_services=frozenset({"housing", "household_services", "public_provision"}),
)

_WORKERS_PER_MACHINE: Final[Mapping[str, int]] = MappingProxyType(
    {
        "food": 4,
        "extraction": 4,
        "energy_utilities": 4,
        "manufacturing": 4,
        "consumer_goods": 4,
        "capital_goods": 4,
        "construction_housing": 4,
        "household_services": 40,
        "leisure_hospitality": 40,
        "business_services": 40,
        "public_provisioning": 40,
    }
)


def _default_service_stage() -> Mapping[str, int]:
    return MappingProxyType(
        {
            "utility": 1,
            "business_services": 1,
            "housing": 1,
            "household_services": 2,
            "leisure": 2,
            "public_provision": 2,
        }
    )


@dataclass(frozen=True)
class Settings:
    """The Director's choices that change the builder's numbers ("Ruled by the Director on
    26 November", items 1 to 6), each at the ruled value, and the design's figures. A later
    ruling changes a value here and the branch it needs."""

    # 1. Services' stages and the order of paying (ruling 1: V6, D7).
    service_stage: Mapping[str, int] = field(default_factory=_default_service_stage)
    paying_order: tuple[str, ...] = (
        "food",
        "materials",
        "consumer_goods",
        "utility",
        "housing",
        "business_services",
        "household_services",
        "leisure",
        "resources",
    )
    # 2. The products that cross a border (ruling 2: V8, K1, E2). A service crosses between
    # businesses only.
    crossing: frozenset[str] = frozenset(
        {"food", "resources", "materials", "consumer_goods", "equipment", "business_services"}
    )
    # 3. The benefit's rule (ruling 3: V3 by its road (b), E8, D2): the compiler works the
    # amounts out.
    benefit_rule: BenefitRule = "each_account_own"
    # 4. Each part's public body (ruling 4: V1 with V2's road (b), K4, K5, D4).
    place_body: PlaceBody = "every_place_even"
    # 5. The services sold across the country (ruling 5: V9, K2, D5).
    country_services: frozenset[str] = frozenset({"business_services", "leisure", "utility"})
    # 6. Who gets what the shop saves on imports (ruling 6: V10, D6).
    shop_import_saving: ShopImportSaving = "households"
    # The design's figures, never solved.
    tier_sizes: tuple[Fraction, Fraction, Fraction] = (
        Fraction(2, 5),
        Fraction(3, 5),
        Fraction(3, 2),
    )
    wear_cover: Fraction = Fraction(5, 4)
    accounts_margin_floor: Fraction = Fraction(1, 20)
    periods_per_year: int = 13
    work_hours_per_person: int = 160
    workers_per_machine: Mapping[str, int] = field(default_factory=lambda: _WORKERS_PER_MACHINE)
    machine_life_periods: int = 100
    days_per_period: int = 28
    public_fee_micros: int = 1_000_000
    laid_off_wage_share_bps: int = 5_000
    laid_off_half_periods: int = 13
    fund_reserve_periods: int = 2
    margin_halvings: int = 40


# The fields that are the Director's choices: `check_ruled` holds each at its ruled value.
CHOICE_FIELDS: Final[tuple[str, ...]] = (
    "service_stage",
    "paying_order",
    "crossing",
    "benefit_rule",
    "place_body",
    "country_services",
    "shop_import_saving",
)


@dataclass(frozen=True)
class TradeCount:
    employee_persons: int
    working_owner_persons: int
    unpaid_family_persons: int
    payroll_micros: int
    force: int
    sites: int
    machines: int
    public_employee_persons: int
    public_payroll_micros: int


@dataclass(frozen=True)
class KeyCount:
    accounts: int
    households: int
    persons: int
    employed: int
    reserve: int
    wage_income_micros: int


@dataclass(frozen=True)
class PlaceKeyCount:
    """A part's row of one key: Task 8's `places` have no `accounts`."""

    households: int
    persons: int
    employed: int
    reserve: int
    wage_income_micros: int


@dataclass(frozen=True)
class PlaceTrade:
    employee_persons: int
    payroll_micros: int
    public_employee_persons: int
    public_payroll_micros: int


@dataclass(frozen=True)
class Seller:
    """Who sells one product to a part's accounts of one key (Task 8)."""

    wage_micros: int
    abroad: str | None


@dataclass(frozen=True)
class Place:
    """ONE PART of a pooled place: the game's unit of accounts (Task 8)."""

    label: str
    hub: str
    state: str
    keys: Mapping[HouseholdKey, PlaceKeyCount]
    trades: Mapping[str, PlaceTrade]
    owner_households: int
    sellers: Mapping[HouseholdKey, Mapping[str, Seller]]
    public_persons_served: int
    public_machines: int


@dataclass(frozen=True)
class Region:
    key: str
    persons: int
    households: int
    labor_force: int
    employed: int
    wage_micros: Mapping[str, int]


@dataclass(frozen=True)
class Census:
    trades: Mapping[str, TradeCount]
    households: Mapping[HouseholdKey, KeyCount]
    places: tuple[Place, ...]
    abroad: Mapping[str, Region]
    firm_assignment: Mapping[tuple[str, str, str], int]
    retail_assignment: Mapping[tuple[str, str], int]
    crossing_force: Mapping[tuple[str, str, str], int]
    workers_per_machine: Mapping[str, int]
    sha256: str


Accounts = Mapping[str, Mapping[str, Mapping[str, int]]]

# --------------------------------------------------------------------------------------
# Rounding, each rule named.


def half_up(value: Fraction) -> int:
    """Round to the nearest whole number, a half going up: floor(value + 1/2)."""
    return math.floor(value + Fraction(1, 2))


def to_grid(value: Fraction, denominator: int) -> Fraction:
    """Round to the nearest 1/denominator, a half going up: half_up(value x d) / d."""
    return Fraction(half_up(value * denominator), denominator)


def up_to_grid(value: Fraction, denominator: int) -> Fraction:
    """Round up to a 1/denominator: ceil(value x d) / d."""
    return Fraction(math.ceil(value * denominator), denominator)


# --------------------------------------------------------------------------------------
# The settings.


def _services(economy: Economy) -> frozenset[str]:
    return frozenset(p for p in economy.product.values() if p not in economy.storable)


def _priced(economy: Economy) -> frozenset[str]:
    unpriced = economy.product.get(economy.public_trade) if economy.public_trade else None
    return frozenset(p for p in economy.product.values() if p != unpriced)


def _refuse_setting(name: str) -> ReferenceBuildError:
    return ReferenceBuildError(f"setting: {name}")


def _check_paying_order(settings: Settings, economy: Economy) -> None:
    order = settings.paying_order
    capital = economy.product.get(economy.capital_trade)
    wanted = frozenset(p for p in _priced(economy) if p != capital)
    if len(set(order)) != len(order) or frozenset(order) != wanted:
        raise _refuse_setting("paying_order")
    index = {product: at for at, product in enumerate(order)}
    services = _services(economy)
    first_service = min((index[p] for p in order if p in services), default=None)
    needs = (*economy.person_needs, *economy.household_needs)
    if first_service is not None:
        for need in needs:
            if need in economy.storable and need in index and index[need] > first_service:
                raise _refuse_setting("paying_order")
    stage = settings.service_stage
    for early in (p for p in order if p in services):
        for late in (p for p in order if p in services):
            if stage[early] < stage[late] and index[early] > index[late]:
                raise _refuse_setting("paying_order")


def check_settings(settings: Settings, economy: Economy = TWELVE) -> None:
    """The settings' shape, for any economy (the tests' small economies take other stages
    and other crossing sets): else `setting: <field>`."""
    services = _services(economy)
    if any(settings.service_stage.get(p, 0) < 1 for p in services):
        raise _refuse_setting("service_stage")
    _check_paying_order(settings, economy)
    if not settings.crossing <= _priced(economy):
        raise _refuse_setting("crossing")
    if (
        not settings.country_services <= services
        or settings.country_services & economy.place_services
    ):
        raise _refuse_setting("country_services")
    sizes = settings.tier_sizes
    positive_figures = (
        *sizes,
        settings.wear_cover,
        settings.accounts_margin_floor,
        settings.periods_per_year,
        settings.work_hours_per_person,
        settings.machine_life_periods,
        settings.days_per_period,
        settings.margin_halvings,
    )
    if not all(
        isinstance(item, (int, Fraction)) and not isinstance(item, bool) and item > 0
        for item in positive_figures
    ):
        raise _refuse_setting("figures")
    if any(count <= 0 for count in settings.workers_per_machine.values()):
        raise _refuse_setting("workers_per_machine")


def check_ruled(settings: Settings) -> None:
    """Every choice at its ruled value (the value of `Settings()`): else
    `setting_not_ruled: <field>`. The design's figures are not choices and are not checked."""
    ruled = Settings()
    for name in CHOICE_FIELDS:
        have, want = getattr(settings, name), getattr(ruled, name)
        if isinstance(want, Mapping):
            same = dict(have) == dict(want)
        else:
            same = bool(have == want)
        if not same:
            raise ReferenceBuildError(f"setting_not_ruled: {name}")


def allowed(settings: Settings, economy: Economy, product_in: str, trade_out: str) -> bool:
    """May the product `product_in` be an input of the trade `trade_out`?

    False when the buyer is the shop (the shop buys through its charge, R3), and false when
    both products have a stage and the input's stage is at least the output's
    (`admission.rs` `validate_recipe`); storable goods have no stage."""
    if trade_out == economy.shop_trade:
        return False
    product_out = economy.product.get(trade_out)
    if product_out is None:
        return False
    stage_in = (
        settings.service_stage.get(product_in) if product_in not in economy.storable else None
    )
    stage_out = (
        settings.service_stage.get(product_out) if product_out not in economy.storable else None
    )
    if stage_in is not None and stage_out is not None and stage_in >= stage_out:
        return False
    return True


# --------------------------------------------------------------------------------------
# The accounts.

_ACCOUNT_COLUMNS: Final = ("block", "row_key", "column_key", "unit", "value")
USE_FINAL_COLUMNS: Final = (
    "households",
    "investment_structures",
    "investment_equipment",
    "investment_intellectual_property",
    "investment_residential",
    "inventories",
    "exports",
    "federal_consumption",
    "federal_investment",
    "state_local_consumption",
    "state_local_investment",
)
GOVERNMENT_COLUMNS: Final = (
    "federal_consumption",
    "federal_investment",
    "state_local_consumption",
    "state_local_investment",
)
INVESTMENT_COLUMNS: Final = (
    "investment_structures",
    "investment_equipment",
    "investment_intellectual_property",
)
OWNER: Final = "owner_occupied_housing"
DROPPED_ROWS: Final = (OWNER, "scrap_used", "noncomparable")


def read_accounts(path: Path) -> Accounts:
    """The accounts table as `block -> row -> column -> value` (USD thousands, jobs or USD)."""
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.reader(io.StringIO(handle.read()))
        rows = list(reader)
    if not rows or tuple(rows[0]) != _ACCOUNT_COLUMNS:
        raise ReferenceBuildError("accounts_shape: header")
    table: dict[str, dict[str, dict[str, int]]] = {}
    for number, row in enumerate(rows[1:], start=2):
        if len(row) != len(_ACCOUNT_COLUMNS):
            raise ReferenceBuildError(f"accounts_shape: line {number}")
        block, row_key, column_key, _unit, text = row
        try:
            value = int(text)
        except ValueError as error:
            raise ReferenceBuildError(f"accounts_shape: line {number}") from error
        cells = table.setdefault(block, {}).setdefault(row_key, {})
        if column_key in cells:
            raise ReferenceBuildError(f"accounts_shape: line {number}")
        cells[column_key] = value
    return table


# --------------------------------------------------------------------------------------
# The census.


def _fail_shape(path: str) -> ReferenceBuildError:
    return ReferenceBuildError(f"census_shape: {path}")


def _int(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _fail_shape(path)
    return value


def _object(
    value: object, path: str, required: Sequence[str], optional: Sequence[str] = ()
) -> dict[str, object]:
    """A JSON object holding every `required` key and no key but the `required` and `optional`."""
    if not isinstance(value, dict):
        raise _fail_shape(path)
    known = {*required, *optional}
    for key in value:
        if key not in known:
            raise _fail_shape(f"{path}.{key}" if path else str(key))
    for key in required:
        if key not in value:
            raise _fail_shape(f"{path}.{key}" if path else key)
    return value


def _ints(value: object, path: str, names: Sequence[str]) -> dict[str, int]:
    block = _object(value, path, names)
    return {name: _int(block[name], f"{path}.{name}") for name in names}


_TRADE_FIELDS: Final = (
    "employee_persons",
    "force",
    "machines",
    "national_wage_micros",
    "payroll_micros_per_period",
    "public_employee_persons",
    "public_payroll_micros_per_period",
    "sites",
    "unpaid_family_persons",
    "working_owner_persons",
)
_KEY_FIELDS: Final = (
    "accounts",
    "employed",
    "households",
    "persons",
    "reserve",
    "wage_income_micros_per_period",
)
_PLACE_KEY_FIELDS: Final = (
    "employed",
    "households",
    "persons",
    "reserve",
    "wage_income_micros_per_period",
)
_PLACE_TRADE_FIELDS: Final = (
    "employee_persons",
    "payroll_micros_per_period",
    "public_employee_persons",
    "public_payroll_micros_per_period",
)
_REGION_FIELDS: Final = ("employed", "households", "labor_force", "persons", "wage_micros")
_SHOP_GOODS: Final = ("consumer_goods", "food", "materials")
_ASSIGNED_GOODS: Final = ("consumer_goods", "equipment", "food", "materials", "resources")
_SELLER_PRODUCTS: Final = (
    "business_services",
    "consumer_goods",
    "food",
    "household_services",
    "housing",
    "leisure",
    "materials",
    "public_provision",
    "utility",
)
_SELLERS_NEEDED: Final = tuple(p for p in _SELLER_PRODUCTS if p not in ("housing", "materials"))
_PLACE_FIELDS: Final = (
    "abroad",
    "hub",
    "keys",
    "owner_households",
    "public_persons_served",
    "sellers",
    "trades",
)
_SOURCE_FIELDS: Final = (
    "cohorts_sha256",
    "counties_sha256",
    "country_services",
    "households_sha256",
    "pay_sha256",
)
_CENSUS_FIELDS: Final = (
    "abroad",
    "assignment",
    "crossing_force",
    "households",
    "places",
    "sources",
    "trades",
    "workers_per_machine",
)
_RECIPE_TRADES: Final = tuple(t for t in TRADES if t != "distribution_transport")
_CROSSING_SERVICES: Final = ("business_services",)


def _read_trade(value: object, path: str) -> TradeCount:
    got = _ints(value, path, _TRADE_FIELDS)
    # `national_wage_micros` is written for reading only (Task 14b); it is not a field.
    return TradeCount(
        employee_persons=got["employee_persons"],
        working_owner_persons=got["working_owner_persons"],
        unpaid_family_persons=got["unpaid_family_persons"],
        payroll_micros=got["payroll_micros_per_period"],
        force=got["force"],
        sites=got["sites"],
        machines=got["machines"],
        public_employee_persons=got["public_employee_persons"],
        public_payroll_micros=got["public_payroll_micros_per_period"],
    )


def _read_region(key: str, value: object, path: str) -> Region:
    block = _object(value, path, _REGION_FIELDS)
    wages = _ints(block["wage_micros"], f"{path}.wage_micros", TRADES)
    return Region(
        key=key,
        persons=_int(block["persons"], f"{path}.persons"),
        households=_int(block["households"], f"{path}.households"),
        labor_force=_int(block["labor_force"], f"{path}.labor_force"),
        employed=_int(block["employed"], f"{path}.employed"),
        wage_micros=wages,
    )


def _read_place(label: str, value: object, regions: Mapping[str, Region]) -> Place:
    path = f"places.{label}"
    block = _object(value, path, _PLACE_FIELDS)
    hub = block["hub"]
    if (
        not isinstance(hub, str)
        or len(hub) != 5
        or not (label == hub or label.startswith(f"{hub}/"))
    ):
        raise _fail_shape(f"{path}.hub")
    trades_block = _object(block["trades"], f"{path}.trades", TRADES)
    trades: dict[str, PlaceTrade] = {}
    machines = 0
    for trade in TRADES:
        optional = ("machines",) if trade == "public_provisioning" else ()
        tpath = f"{path}.trades.{trade}"
        obj = _object(trades_block[trade], tpath, _PLACE_TRADE_FIELDS, optional)
        got = {name: _int(obj[name], f"{tpath}.{name}") for name in _PLACE_TRADE_FIELDS}
        if trade == "public_provisioning":
            machines = _int(obj.get("machines"), f"{tpath}.machines")
        trades[trade] = PlaceTrade(
            employee_persons=got["employee_persons"],
            payroll_micros=got["payroll_micros_per_period"],
            public_employee_persons=got["public_employee_persons"],
            public_payroll_micros=got["public_payroll_micros_per_period"],
        )
    keys_block = _object(block["keys"], f"{path}.keys", list(_CENSUS_KEY))
    sellers_block = _object(block["sellers"], f"{path}.sellers", list(_CENSUS_KEY))
    abroad_block = _object(block["abroad"], f"{path}.abroad", list(_CENSUS_KEY))
    keys: dict[HouseholdKey, PlaceKeyCount] = {}
    sellers: dict[HouseholdKey, dict[str, Seller]] = {}
    for census_key, key in _CENSUS_KEY.items():
        kpath = f"{path}.keys.{census_key}"
        got = _ints(keys_block[census_key], kpath, _PLACE_KEY_FIELDS)
        keys[key] = PlaceKeyCount(
            households=got["households"],
            persons=got["persons"],
            employed=got["employed"],
            reserve=got["reserve"],
            wage_income_micros=got["wage_income_micros_per_period"],
        )
        spath = f"{path}.sellers.{census_key}"
        wages = _object(sellers_block[census_key], spath, _SELLERS_NEEDED, _SELLER_PRODUCTS)
        apath = f"{path}.abroad.{census_key}"
        regions_of = _object(
            abroad_block[census_key], apath, ("consumer_goods", "food"), _SHOP_GOODS
        )
        row: dict[str, Seller] = {}
        for product in _SELLER_PRODUCTS:
            if product not in wages:
                continue
            region = regions_of.get(product)
            if region is not None and (not isinstance(region, str) or region not in regions):
                raise _fail_shape(f"{apath}.{product}")
            row[product] = Seller(
                wage_micros=_int(wages[product], f"{spath}.{product}"), abroad=region
            )
        sellers[key] = row
    return Place(
        label=label,
        hub=hub,
        state=hub[:2],
        keys=keys,
        trades=trades,
        owner_households=_int(block["owner_households"], f"{path}.owner_households"),
        sellers=sellers,
        public_persons_served=_int(block["public_persons_served"], f"{path}.public_persons_served"),
        public_machines=machines,
    )


def _read_assignment(
    value: object, regions: Mapping[str, Region]
) -> tuple[dict[tuple[str, str, str], int], dict[tuple[str, str], int]]:
    block = _object(value, "assignment", ("households", "sites"))
    households = _object(block["households"], "assignment.households", _ASSIGNED_GOODS)
    sites = _object(block["sites"], "assignment.sites", _ASSIGNED_GOODS)
    retail: dict[tuple[str, str], int] = {}
    firm: dict[tuple[str, str, str], int] = {}
    for good in _ASSIGNED_GOODS:
        by_region = _object(households[good], f"assignment.households.{good}", [], list(regions))
        for region, count in by_region.items():
            retail[(good, region)] = _int(count, f"assignment.households.{good}.{region}")
        site_regions = _object(sites[good], f"assignment.sites.{good}", [], list(regions))
        for region, trades in site_regions.items():
            got = _ints(trades, f"assignment.sites.{good}.{region}", _RECIPE_TRADES)
            for trade in _RECIPE_TRADES:
                firm[(good, region, trade)] = got[trade]
    return firm, retail


def _read_crossing(value: object, regions: Mapping[str, Region]) -> dict[tuple[str, str, str], int]:
    block = _object(value, "crossing_force", _CROSSING_SERVICES)
    rows: dict[tuple[str, str, str], int] = {}
    for service in _CROSSING_SERVICES:
        by_region = _object(block[service], f"crossing_force.{service}", [], list(regions))
        for region, trades in by_region.items():
            got = _ints(trades, f"crossing_force.{service}.{region}", _RECIPE_TRADES)
            for trade in _RECIPE_TRADES:
                rows[(service, region, trade)] = got[trade]
    return rows


def _check_census(census: Census, settings: Settings) -> None:
    wages = sum(count.wage_income_micros for count in census.households.values())
    if wages != sum(count.payroll_micros for count in census.trades.values()):
        raise ReferenceBuildError("census_wages")
    for trade, national in census.trades.items():
        rows = [place.trades[trade] for place in census.places]
        same = (
            sum(r.employee_persons for r in rows) == national.employee_persons
            and sum(r.payroll_micros for r in rows) == national.payroll_micros
            and sum(r.public_employee_persons for r in rows) == national.public_employee_persons
            and sum(r.public_payroll_micros for r in rows) == national.public_payroll_micros
        )
        if not same:
            raise ReferenceBuildError(f"census_places: {trade}")
    for key, count in census.households.items():
        krows = [place.keys[key] for place in census.places]
        same = (
            sum(r.households for r in krows) == count.households
            and sum(r.persons for r in krows) == count.persons
            and sum(r.employed for r in krows) == count.employed
            and sum(r.reserve for r in krows) == count.reserve
            and sum(r.wage_income_micros for r in krows) == count.wage_income_micros
        )
        if not same:
            raise ReferenceBuildError(f"census_places: {key}")
    for trade in sorted(set(census.workers_per_machine) | set(settings.workers_per_machine)):
        if census.workers_per_machine.get(trade) != settings.workers_per_machine.get(trade):
            raise ReferenceBuildError(f"census_machines: {trade}")
    if (
        sum(place.public_machines for place in census.places)
        != census.trades["public_provisioning"].machines
    ):
        raise ReferenceBuildError("census_machines: public_provisioning")
    for service in _CROSSING_SERVICES:
        for trade in _RECIPE_TRADES:
            force = sum(
                n
                for (s, _region, t), n in census.crossing_force.items()
                if s == service and t == trade
            )
            if force != census.trades[trade].force:
                raise ReferenceBuildError(f"census_sites: {service}/{trade}")
    persons = sum(count.persons for count in census.households.values())
    if sum(place.public_persons_served for place in census.places) != persons:
        raise ReferenceBuildError("census_places: public_persons_served")


def read_census(path: Path) -> Census:
    """The census of Task 8, read exactly: an unknown key, a missing key or a non-integer value
    is `census_shape: <json path>`; its five checks are `census_wages`, `census_places`,
    `census_machines`, `census_sites`. Its `sha256` is of the decompressed JSON text."""
    text = gzip.decompress(path.read_bytes())
    try:
        document = json.loads(text)
    except ValueError as error:
        raise ReferenceBuildError("census_shape: <text>") from error
    top = _object(document, "", _CENSUS_FIELDS)
    settings = Settings()
    trades_block = _object(top["trades"], "trades", TRADES)
    trades = {t: _read_trade(trades_block[t], f"trades.{t}") for t in TRADES}
    abroad_block = top["abroad"]
    if not isinstance(abroad_block, dict) or not abroad_block:
        raise _fail_shape("abroad")
    regions = {key: _read_region(key, obj, f"abroad.{key}") for key, obj in abroad_block.items()}
    households_block = _object(top["households"], "households", list(_CENSUS_KEY))
    households: dict[HouseholdKey, KeyCount] = {}
    for census_key, key in _CENSUS_KEY.items():
        got = _ints(households_block[census_key], f"households.{census_key}", _KEY_FIELDS)
        households[key] = KeyCount(
            accounts=got["accounts"],
            households=got["households"],
            persons=got["persons"],
            employed=got["employed"],
            reserve=got["reserve"],
            wage_income_micros=got["wage_income_micros_per_period"],
        )
    places_block = top["places"]
    if not isinstance(places_block, dict) or not places_block:
        raise _fail_shape("places")
    places = tuple(
        _read_place(label, places_block[label], regions) for label in sorted(places_block)
    )
    firm, retail = _read_assignment(top["assignment"], regions)
    crossing = _read_crossing(top["crossing_force"], regions)
    wpm_block = _ints(
        top["workers_per_machine"], "workers_per_machine", sorted(settings.workers_per_machine)
    )
    sources = _object(top["sources"], "sources", _SOURCE_FIELDS)
    for name in _SOURCE_FIELDS:
        if name != "country_services" and not isinstance(sources[name], str):
            raise _fail_shape(f"sources.{name}")
    listed = sources["country_services"]
    if (
        not isinstance(listed, list)
        or not all(isinstance(item, str) for item in listed)
        or len(set(listed)) != len(listed)
        or frozenset(listed) != settings.country_services
    ):
        raise _fail_shape("sources.country_services")
    census = Census(
        trades=trades,
        households=households,
        places=places,
        abroad=regions,
        firm_assignment=firm,
        retail_assignment=retail,
        crossing_force=crossing,
        workers_per_machine=wpm_block,
        sha256=hashlib.sha256(text).hexdigest(),
    )
    _check_census(census, settings)
    return census


# --------------------------------------------------------------------------------------
# The re-cut.


@dataclass(frozen=True)
class Recut:
    inputs: Mapping[str, Mapping[str, Fraction]]
    households: Mapping[str, Fraction]
    exports: Mapping[str, Fraction]
    equipment: Fraction
    import_share: Mapping[str, Fraction]
    domestic_output: Mapping[str, Fraction]
    accounts_payroll: Mapping[str, Fraction]
    accounts_jobs: Mapping[str, int]
    accounts_margin: Mapping[str, Fraction]
    moved: Mapping[tuple[str, str], Fraction]
    dropped: Mapping[tuple[str, str], Fraction]


def _cell(accounts: Accounts, block: str, row: str, column: str) -> int:
    try:
        return accounts[block][row][column]
    except KeyError as error:
        raise ReferenceBuildError(f"accounts_shape: {block}/{row}/{column}") from error


@dataclass
class _Row:
    """One product row while it is cut: kept cells and the spread, before the factor `k`."""

    inputs: dict[str, Fraction] = field(default_factory=dict)
    households: Fraction = Fraction(0)
    exports: Fraction = Fraction(0)
    equipment: Fraction = Fraction(0)
    spread: dict[str, Fraction] = field(default_factory=dict)
    dropped: dict[str, Fraction] = field(default_factory=dict)

    def add_input(self, trade: str, value: Fraction) -> None:
        self.inputs[trade] = self.inputs.get(trade, Fraction(0)) + value

    def spread_to(self, reason: str, value: Fraction) -> None:
        self.spread[reason] = self.spread.get(reason, Fraction(0)) + value

    def drop(self, reason: str, value: Fraction) -> None:
        self.dropped[reason] = self.dropped.get(reason, Fraction(0)) + value

    def kept(self) -> Fraction:
        return (
            sum(self.inputs.values(), Fraction(0)) + self.households + self.exports + self.equipment
        )


class _Cutter:
    def __init__(self, accounts: Accounts, settings: Settings, economy: Economy) -> None:
        self.accounts = accounts
        self.settings = settings
        self.economy = economy
        self.surplus: dict[str, Fraction] = {
            trade: Fraction(max(_cell(accounts, "industry", trade, "gross_operating_surplus"), 0))
            for trade in economy.trades
            if trade != economy.public_trade
        }

    def route(self, row: _Row, product: str, trade: str, value: Fraction) -> None:
        """A cell of the product used by `trade`: the shop's to R3, a stage-barred one to R1."""
        if value == 0:
            return
        if trade == self.economy.shop_trade:
            row.spread_to("R3", value)
        elif not allowed(self.settings, self.economy, product, trade):
            row.spread_to("R1", value)
        else:
            row.add_input(trade, value)

    def invest(self, row: _Row, trade: str, product: str, value: Fraction) -> None:
        """Investment in structures, equipment or IP, dealt over every trade but the row's own
        and public provision by max(gross operating surplus, 0) (exact shares)."""
        if value == 0:
            return
        targets = [t for t in self.economy.trades if t not in (trade, self.economy.public_trade)]
        total = sum((self.surplus[t] for t in targets), Fraction(0))
        if total == 0:
            raise ReferenceBuildError("accounts_empty: surplus")
        for target in targets:
            self.route(row, product, target, value * self.surplus[target] / total)

    def cut(self, trade: str, phi: Fraction) -> _Row:
        economy, settings = self.economy, self.settings
        product = economy.product[trade]
        row = _Row()

        def cell(column: str) -> Fraction:
            return Fraction(self.accounts["use"][trade].get(column, 0)) * phi

        is_capital = trade == economy.capital_trade
        for other in economy.trades:
            value = cell(other)
            if other == trade:
                row.drop("own_use", value)
            elif is_capital:
                row.equipment += value
            else:
                self.route(row, product, other, value)
        row.drop("owner_column", cell(OWNER))
        for column in GOVERNMENT_COLUMNS:
            value = cell(column)
            if is_capital:
                row.equipment += value
            elif economy.public_trade is not None and allowed(
                settings, economy, product, economy.public_trade
            ):
                row.add_input(economy.public_trade, value)
            else:
                row.spread_to("R1", value)
        for column in ("households", "investment_residential"):
            if is_capital:
                row.equipment += cell(column)
            else:
                row.households += cell(column)
        for column in INVESTMENT_COLUMNS:
            if is_capital:
                row.equipment += cell(column)
            else:
                self.invest(row, trade, product, cell(column))
        if product in settings.crossing:
            row.exports += cell("exports")
        else:
            row.spread_to("R2", cell("exports"))
        row.spread_to("O4_inventories", cell("inventories"))
        return row


def _phi(accounts: Accounts, trade_product_row: str) -> Fraction | None:
    """(commodity output + imports) / total supply, or None for a row with no supply."""
    total = _cell(accounts, "supply", trade_product_row, "total_supply")
    if total == 0:
        return None
    output = _cell(accounts, "supply", trade_product_row, "commodity_output")
    imports = _cell(accounts, "supply", trade_product_row, "imports")
    return Fraction(output + imports, total)


def recut(accounts: Accounts, settings: Settings, economy: Economy = TWELVE) -> Recut:
    """The accounts re-cut to the game's buyers (model-spec 3). The settings are checked
    before a cell is read."""
    check_settings(settings, economy)
    cutter = _Cutter(accounts, settings, economy)
    rows = [t for t in economy.trades if t in economy.product and t != economy.public_trade]
    inputs: dict[str, dict[str, Fraction]] = {}
    households: dict[str, Fraction] = {}
    exports: dict[str, Fraction] = {}
    imp: dict[str, Fraction] = {trade: Fraction(0) for trade in economy.trades}
    dom: dict[str, Fraction] = {}
    moved: dict[tuple[str, str], Fraction] = {}
    dropped: dict[tuple[str, str], Fraction] = {}
    equipment = Fraction(0)
    for trade in rows:
        phi = _phi(accounts, trade)
        if phi is None:
            inputs[trade], households[trade], dom[trade] = {}, Fraction(0), Fraction(0)
            continue
        row = cutter.cut(trade, phi)
        spread = sum(row.spread.values(), Fraction(0))
        kept = row.kept()
        if kept == 0 and spread != 0:
            raise ReferenceBuildError(f"accounts_empty: {trade}")
        k = Fraction(1) if kept == 0 else 1 + spread / kept
        inputs[trade] = {t: v * k for t, v in row.inputs.items() if v != 0}
        households[trade] = row.households * k
        if economy.product[trade] in settings.crossing:
            exports[trade] = row.exports * k
            output = _cell(accounts, "supply", trade, "commodity_output")
            imports = _cell(accounts, "supply", trade, "imports")
            if output + imports == 0:
                raise ReferenceBuildError(f"accounts_empty: {trade}")
            imp[trade] = Fraction(imports, output + imports)
        equipment += row.equipment * k
        dom[trade] = kept * k * (1 - imp[trade])
        for reason, value in row.spread.items():
            if value != 0:
                moved[(reason, trade)] = value
        for reason, value in row.dropped.items():
            if value != 0:
                dropped[(reason, trade)] = value
    payroll = {
        trade: Fraction(_cell(accounts, "jobs", trade, "annual_payroll_usd"), 1000)
        for trade in economy.trades
    }
    jobs = {trade: _cell(accounts, "jobs", trade, "jobs") for trade in economy.trades}
    if economy.public_trade is not None:
        into_public = sum(
            (inputs[t].get(economy.public_trade, Fraction(0)) for t in rows), Fraction(0)
        )
        dom[economy.public_trade] = into_public + payroll[economy.public_trade]
    if economy.shop_trade is not None:
        dom[economy.shop_trade] = payroll[economy.shop_trade]
    margin: dict[str, Fraction] = {}
    for trade in economy.trades:
        if trade in (economy.shop_trade, economy.public_trade):
            margin[trade] = Fraction(0)
            continue
        cost = sum((inputs[i].get(trade, Fraction(0)) for i in rows), Fraction(0)) + payroll[trade]
        if cost == 0:
            raise ReferenceBuildError(f"accounts_empty: {trade}")
        margin[trade] = max((dom[trade] - cost) / cost, settings.accounts_margin_floor)
    shop_row = (economy.shop_trade,) if economy.shop_trade is not None else ()
    for name in (*shop_row, *DROPPED_ROWS):
        row_cells = accounts.get("use", {}).get(name)
        if row_cells is not None:
            dropped[("row", name)] = Fraction(sum(row_cells.values()))
    return Recut(
        inputs=inputs,
        households=households,
        exports=exports,
        equipment=equipment,
        import_share=imp,
        domestic_output=dom,
        accounts_payroll=payroll,
        accounts_jobs=jobs,
        accounts_margin=margin,
        moved=moved,
        dropped=dropped,
    )


__all__ = [
    "Accounts",
    "Census",
    "Economy",
    "Place",
    "Recut",
    "Region",
    "Seller",
    "Settings",
    "TWELVE",
    "allowed",
    "check_ruled",
    "check_settings",
    "half_up",
    "read_accounts",
    "read_census",
    "recut",
    "to_grid",
    "up_to_grid",
]
