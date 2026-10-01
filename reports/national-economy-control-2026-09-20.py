#!/usr/bin/env python3
"""One-off arithmetic oracle, not a Babylon implementation or economic forecast."""

# ruff: noqa: S101
# Assertions are the independent arithmetic witness, not runtime input guards.
import argparse
import json
from collections import defaultdict
from pathlib import Path

ACTORS = ("supplier", "factory", "distributor", "household")
S, F, D, H = ACTORS
CAPACITY_HOURS = {S: 4, F: 8, D: 4}
REQUESTS = [4, 4, 0, 0, 4, 4, 4, 4]
balances = {actor: defaultdict(int) for actor in ACTORS}
journal = []
periods = []
lots = []
stock = {
    "supplier_raw": 0,
    "factory_raw": 4,
    "factory_finished": 0,
    "distributor_finished": 4,
    "household_finished": 8,
}
reserve = 40
consumed = 0
unmet_consumption = 0
plans = {S: 4, F: 4, D: 4}


def event(period, label, postings):
    """Post an atomic event; every actor posting has equal debits and credits."""
    clean = []
    for actor, legs in postings:
        legs = {account: amount for account, amount in legs.items() if amount}
        if not legs:
            continue
        assert sum(legs.values()) == 0, (actor, label, legs)
        for account, amount in legs.items():
            balances[actor][account] += amount
        clean.append({"actor": actor, "debit_positive_legs": legs})
    if clean:
        journal.append(
            {"event_id": len(journal) + 1, "period": period, "label": label, "postings": clean}
        )
    for actor in ACTORS:
        assert sum(balances[actor].values()) == 0
        for account in ("cash", "trade_escrow", "payroll_escrow"):
            assert balances[actor][account] >= 0, (period, label, actor, account)


def money():
    return sum(
        balances[a][account]
        for a in ACTORS
        for account in ("cash", "trade_escrow", "payroll_escrow")
    )


def physical():
    return reserve + sum(stock.values()) + sum(lot["quantity"] for lot in lots) + consumed


def snapshot():
    return {
        "cash": {a: balances[a]["cash"] for a in ACTORS},
        "trade_escrow": {a: balances[a]["trade_escrow"] for a in ACTORS},
        "payroll_escrow": {a: balances[a]["payroll_escrow"] for a in ACTORS},
        "stocks": dict(stock),
        "unextracted_resource": reserve,
        "in_transit": [dict(lot) for lot in lots],
        "cumulative_consumption": consumed,
        "cumulative_unmet_consumption": unmet_consumption,
    }


def arrive(period):
    arrived = []
    for lot in list(lots):
        if lot["arrival_period"] != period:
            continue
        seller, buyer = lot["seller"], lot["buyer"]
        quantity, payment = lot["quantity"], lot["escrow_amount"]
        carrying = quantity * lot["seller_unit_cost"]
        buyer_account = "raw_inventory" if buyer == F else "finished_inventory"
        buyer_stock = "factory_raw" if buyer == F else "distributor_finished"
        event(
            period,
            "final arrival, title transfer, and escrow settlement",
            [
                (
                    seller,
                    {
                        "trade_receivable": payment,
                        "sales": -payment,
                        "cost_of_goods_sold": carrying,
                        "seller_owned_transit": -carrying,
                    },
                ),
                (buyer, {buyer_account: payment, "trade_payable": -payment}),
                (buyer, {"trade_payable": payment, "trade_escrow": -payment}),
                (seller, {"cash": payment, "trade_receivable": -payment}),
            ],
        )
        stock[buyer_stock] += quantity
        lots.remove(lot)
        arrived.append(dict(lot))
        assert money() == 24
    return arrived


def fund_shift(period, actor, hours):
    assert 0 <= hours <= CAPACITY_HOURS[actor]
    assert balances[actor]["cash"] >= hours
    event(
        period,
        "fund committed shift before production or retail orders",
        [(actor, {"payroll_escrow": hours, "cash": -hours})],
    )


def payroll(period, actor, hours, actual_output):
    if actor == S:
        costs = {"raw_inventory": actual_output, "idle_labor_expense": hours - actual_output}
    elif actor == F:
        costs = {
            "finished_inventory": 2 * actual_output,
            "idle_labor_expense": hours - 2 * actual_output,
        }
    else:
        costs = {"handling_expense": hours}
    # Attendance to an admitted shift earns its full wage, regardless of output/sales.
    event(
        period,
        "committed attendance earns wages; obligation is distinct from payment",
        [
            (actor, {**costs, "wages_payable": -hours}),
            (H, {"wages_receivable": hours, "wage_income": -hours}),
        ],
    )
    event(
        period,
        "pay earned wages out of previously funded payroll escrow",
        [
            (actor, {"wages_payable": hours, "payroll_escrow": -hours}),
            (H, {"cash": hours, "wages_receivable": -hours}),
        ],
    )
    assert money() == 24


def dispatch(period, seller, buyer, quantity, unit_price, unit_cost):
    if not quantity:
        return None
    payment, carrying = quantity * unit_price, quantity * unit_cost
    assert quantity <= 4  # Explicit, free, Designed route capacity.
    assert balances[buyer]["cash"] >= payment
    seller_stock = "supplier_raw" if seller == S else "factory_finished"
    seller_account = "raw_inventory" if seller == S else "finished_inventory"
    assert stock[seller_stock] >= quantity
    # Seller retains title. Buyer has only escrow, not purchased goods or a payable yet.
    event(
        period,
        "reserve buyer money and dispatch seller-owned goods",
        [
            (buyer, {"trade_escrow": payment, "cash": -payment}),
            (seller, {"seller_owned_transit": carrying, seller_account: -carrying}),
        ],
    )
    stock[seller_stock] -= quantity
    lot = {
        "order_id": f"{seller}-{buyer}-{period}",
        "dispatch_period": period,
        "arrival_period": period + 1,
        "seller": seller,
        "buyer": buyer,
        "quantity": quantity,
        "seller_unit_cost": unit_cost,
        "unit_price": unit_price,
        "escrow_amount": payment,
        "title_owner": seller,
        "custody": "carrier",
        "seller_delivery_obligation_units": quantity,
    }
    lots.append(lot)
    assert money() == 24
    return dict(lot)


def retail(period, requested, funded_hours):
    actual = min(requested, funded_hours, stock["distributor_finished"], balances[H]["cash"] // 4)
    payment, carrying = 4 * actual, 3 * actual
    event(
        period,
        "local retail handoff, title transfer, and immediate settlement",
        [
            (
                D,
                {
                    "trade_receivable": payment,
                    "sales": -payment,
                    "cost_of_goods_sold": carrying,
                    "finished_inventory": -carrying,
                },
            ),
            (H, {"food_inventory": payment, "trade_payable": -payment}),
            (H, {"trade_payable": payment, "cash": -payment}),
            (D, {"cash": payment, "trade_receivable": -payment}),
        ],
    )
    stock["distributor_finished"] -= actual
    stock["household_finished"] += actual
    assert money() == 24
    return actual


def assert_period_accounts():
    assert money() == 24
    assert physical() == 56
    assert all(quantity >= 0 for quantity in stock.values())
    assert balances[S]["raw_inventory"] == stock["supplier_raw"]
    assert balances[F]["raw_inventory"] == stock["factory_raw"]
    assert balances[F]["finished_inventory"] == 3 * stock["factory_finished"]
    assert balances[D]["finished_inventory"] == 3 * stock["distributor_finished"]
    assert balances[H]["food_inventory"] == 4 * stock["household_finished"]
    for actor in ACTORS:
        assert balances[actor]["trade_escrow"] == sum(
            lot["escrow_amount"] for lot in lots if lot["buyer"] == actor
        )
        assert balances[actor]["seller_owned_transit"] == sum(
            lot["quantity"] * lot["seller_unit_cost"] for lot in lots if lot["seller"] == actor
        )
        for account in (
            "trade_payable",
            "trade_receivable",
            "wages_payable",
            "wages_receivable",
            "payroll_escrow",
        ):
            assert balances[actor][account] == 0


event(
    0,
    "explicit opening assets and equity",
    [
        (S, {"cash": 4, "equity": -4}),
        (F, {"cash": 12, "raw_inventory": 4, "equity": -16}),
        (D, {"cash": 8, "finished_inventory": 12, "equity": -20}),
        (H, {"food_inventory": 32, "equity": -32}),
    ],
)
opening = snapshot()

for period, requested in enumerate(REQUESTS, 1):
    first_event = len(journal) + 1
    arrivals = arrive(period)
    opening_after_arrivals = snapshot()
    current_plans = dict(plans)
    hours = {S: plans[S], F: 2 * plans[F], D: plans[D]}
    # All three shifts are funded before anyone works, requests retail goods, or sells.
    for actor in (S, F, D):
        fund_shift(period, actor, hours[actor])
    supplier_output = min(plans[S], reserve)
    factory_output = min(plans[F], stock["factory_raw"])
    reserve -= supplier_output
    stock["supplier_raw"] += supplier_output
    stock["factory_raw"] -= factory_output
    stock["factory_finished"] += factory_output
    event(
        period,
        "factory transforms opening raw material",
        [(F, {"finished_inventory": factory_output, "raw_inventory": -factory_output})],
    )
    payroll(period, S, hours[S], supplier_output)
    payroll(period, F, hours[F], factory_output)
    payroll(period, D, hours[D], 0)
    # Request is revealed only now; it cannot resize the already funded shift.
    eligible_request = min(requested, balances[H]["cash"] // 4)
    sold = retail(period, requested, hours[D])
    new_orders = [
        dispatch(period, F, D, sold, 3, 3),
        dispatch(period, S, F, factory_output, 1, 1),
    ]
    actual_consumption = min(4, stock["household_finished"])
    stock["household_finished"] -= actual_consumption
    consumed += actual_consumption
    unmet_consumption += 4 - actual_consumption
    event(
        period,
        "household consumes available provisions",
        [
            (
                H,
                {
                    "consumption_expense": 4 * actual_consumption,
                    "food_inventory": -4 * actual_consumption,
                },
            )
        ],
    )
    # Feasible but unfilled household requests can restore a zero handling plan.
    plans = {S: factory_output, F: sold, D: eligible_request}
    used_hours = {S: supplier_output, F: 2 * factory_output, D: sold}
    labor = {
        actor: {
            "available": CAPACITY_HOURS[actor],
            "funded": hours[actor],
            "used": used_hours[actor],
            "paid_idle": hours[actor] - used_hours[actor],
            "uncommitted": CAPACITY_HOURS[actor] - hours[actor],
            "wages_obligated": hours[actor],
            "wages_paid": hours[actor],
            "wages_unpaid": 0,
        }
        for actor in (S, F, D)
    }
    for row in labor.values():
        assert row["available"] == row["used"] + row["paid_idle"] + row["uncommitted"]
    assert_period_accounts()
    periods.append(
        {
            "period": period,
            "opening_after_arrivals": opening_after_arrivals,
            "arrivals_and_settlements": arrivals,
            "opening_plans": current_plans,
            "household_request": requested,
            "household_purchase": sold,
            "unfilled_purchase_request": requested - sold,
            "supplier_output": supplier_output,
            "factory_output": factory_output,
            "labor": labor,
            "new_orders": [x for x in new_orders if x],
            "household_consumption": actual_consumption,
            "unmet_consumption": 4 - actual_consumption,
            "next_plans": dict(plans),
            "closing": snapshot(),
            "first_journal_event": first_event,
            "last_journal_event": len(journal),
        }
    )

expected = {
    "household_requests": [4, 4, 0, 0, 4, 4, 4, 4],
    "household_purchases": [4, 4, 0, 0, 0, 4, 4, 4],
    "supplier_output": [4, 4, 4, 4, 0, 0, 0, 4],
    "factory_output": [4, 4, 4, 0, 0, 0, 4, 4],
    "distributor_funded_hours": [4, 4, 4, 0, 0, 4, 4, 4],
    "wages_obligated_and_paid": [16, 16, 16, 4, 0, 4, 12, 16],
    "household_consumption": [4, 4, 4, 4, 0, 4, 4, 4],
}
for key, field in [
    ("household_requests", "household_request"),
    ("household_purchases", "household_purchase"),
    ("supplier_output", "supplier_output"),
    ("factory_output", "factory_output"),
    ("household_consumption", "household_consumption"),
]:
    assert [row[field] for row in periods] == expected[key]
assert [row["labor"][D]["funded"] for row in periods] == expected["distributor_funded_hours"]
assert [sum(x["wages_paid"] for x in row["labor"].values()) for row in periods] == expected[
    "wages_obligated_and_paid"
]
income_accounts = (
    "sales",
    "wage_income",
    "cost_of_goods_sold",
    "idle_labor_expense",
    "handling_expense",
    "consumption_expense",
)
net_income = {actor: -sum(balances[actor][a] for a in income_accounts) for actor in ACTORS}
assert net_income == {S: 0, F: 0, D: -4, H: -28}
result = {
    "schema": "OneOffEightPeriodEscrowControlV1",
    "status": "arithmetic_assertions_passed",
    "scope": "Fixed prices and population, financed shifts, renewed orders, title retained by seller until final arrival; not a production engine.",
    "assumptions": {
        "period_days": 28,
        "periods": 8,
        "workers": {S: 1, F: 2, D: 1},
        "hours_per_worker_per_period": 4,
        "wage_per_hour": 1,
        "prices": {"raw": 1, "factory_finished": 3, "retail_finished": 4},
        "household_need_per_period": 4,
        "production_recipe": "One raw unit becomes one finished unit.",
        "transport": "Two dedicated routes, capacity four native units per period each, one-period transit; free Designed capacity, no carrier financial actor.",
        "ownership": "Seller retains title and inventory-in-transit until final arrival. Buyer holds funded escrow only. Sale, purchase, title transfer and escrow settlement coincide at arrival.",
        "seller_delivery_obligation": "Each transit lot records the seller quantity obligation. It is not a seller cash liability because the buyer escrow is not seller cash.",
        "payroll": "Previous signals set opening shift plans. After prior arrival settlements, all shifts reserve actual cash before work or current retail requests. Attendance earns the full funded wage even if idle; payment is a separate event.",
        "planning": "Next supplier plan equals current factory replenishment; next factory plan equals current distributor replenishment. Next distributor plan equals current household request affordable after committed payroll, including unfilled requests. Unfilled retail requests expire, without becoming repeat arrears orders.",
        "needs": "Unmet period consumption is recorded; no automatic next-period catch-up demand.",
        "excluded": [
            "price formation",
            "taxation",
            "credit",
            "dividends",
            "transport charges",
            "resource regeneration",
            "loss and refund cases",
            "population change",
            "organizer effects",
        ],
        "money_supply": 24,
        "initial_resource_equivalent": 56,
    },
    "opening": opening,
    "expected": expected,
    "periods": periods,
    "journal": journal,
    "final_accounts_debit_positive": {
        a: {k: v for k, v in b.items() if v} for a, b in balances.items()
    },
    "net_income": net_income,
    "totals": {
        "household_purchases": sum(row["household_purchase"] for row in periods),
        "supplier_output": sum(row["supplier_output"] for row in periods),
        "factory_output": sum(row["factory_output"] for row in periods),
        "wages_obligated": sum(
            sum(x["wages_obligated"] for x in row["labor"].values()) for row in periods
        ),
        "wages_paid": sum(sum(x["wages_paid"] for x in row["labor"].values()) for row in periods),
        "wages_unpaid": 0,
        "consumption": consumed,
        "unmet_consumption": unmet_consumption,
        "final_cash_plus_escrow": money(),
        "physical_stock_plus_consumption": physical(),
    },
}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
path = parser.parse_args().output
path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
print(path)
print(
    "period request buy S_output F_output D_funded wages consumption cash[S,F,D,H] trade_escrow[S,F,D,H]"
)
for row in periods:
    print(
        row["period"],
        row["household_request"],
        row["household_purchase"],
        row["supplier_output"],
        row["factory_output"],
        row["labor"][D]["funded"],
        sum(x["wages_paid"] for x in row["labor"].values()),
        row["household_consumption"],
        [row["closing"]["cash"][a] for a in ACTORS],
        [row["closing"]["trade_escrow"][a] for a in ACTORS],
    )
print(json.dumps(result["totals"], sort_keys=True))
print("net income:", net_income)
