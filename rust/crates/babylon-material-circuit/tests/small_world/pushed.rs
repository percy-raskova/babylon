//! The pushed runs: the same opening with one change, 34 periods, and the class of its end.
//! Each test names the rules that carry the movement; the record traces them line by line.

use super::support::{self, Snapshot, World, CARE, CLINIC, FARM, FOOD, SHOP, UTILITY};

fn at(rows: &[Snapshot], period: u64) -> &Snapshot {
    &rows[usize::try_from(period - 1).expect("a small period")]
}

/// P1, less demand: runs away. The owner buys half, so the utility and the clinic perform less
/// than their capacity and their quotes fall (`services/market.rs` `quote`, spare capacity), the
/// farm's stock rises above its target and its quote falls (`recurring/prices.rs` `quote`).
/// Wages never fall, so workers keep cash they have no need to spend. The clinic still plans and
/// staffs for what households request, not what they fund (`services/market.rs` `update`), pays
/// idle hours, and runs out of cash; with less than one hour's wage it can never staff again
/// (`payments/attendance.rs` `fund_member_attendance`), so its output stays at zero.
#[test]
fn less_demand_runs_away_until_the_clinic_cannot_pay_one_hour() {
    let rows = support::run(&World::less_demand());
    let first = at(&rows, 1);
    assert_eq!(first.price_cents, [1_100, 2_400, 2_900, 3_800]);
    assert_eq!(first.stock[FARM], 45);
    // Whole batches with a one-period buffer: the farm's plan cycles between 3 and 4 batches.
    let plans: Vec<_> = (1..=12).map(|p| at(&rows, p).planned[FARM]).collect();
    assert_eq!(plans, [3, 4, 4, 4, 3, 4, 4, 4, 3, 4, 4, 4]);
    for period in 17..=34 {
        let row = at(&rows, period);
        assert_eq!(row.cash["clinic"], 0, "period {period}");
        assert_eq!(row.output[CLINIC], 0, "period {period}");
    }
    let last = at(&rows, 34);
    assert_eq!(last.unmet, [10, 24, 35]);
    assert_eq!((last.cash["owner"], last.cash["w_farm"]), (222, 1_484));
}

/// P2, less supply: runs away. The farm plans more batches than its workforce can staff, sells
/// its buffer down, and the owner's lower distributions leave clinic capacity unsold; the clinic
/// stops at period 13, the farm at period 30, and the shop has no food from period 33.
#[test]
fn less_supply_runs_away_until_the_clinic_and_the_farm_stop() {
    let rows = support::run(&World::less_supply());
    let first = at(&rows, 1);
    assert_eq!(
        (first.output[FARM], first.planned[FARM], first.asked[FARM]),
        (36, 5, 50)
    );
    assert_eq!(
        first.employed[FARM], 5,
        "the farm's whole workforce is already employed"
    );
    for period in 13..=34 {
        assert_eq!(at(&rows, period).output[CLINIC], 0, "period {period}");
        assert_eq!(at(&rows, period).cash["clinic"], 5, "period {period}");
    }
    for period in 30..=34 {
        assert_eq!(at(&rows, period).output[FARM], 0, "period {period}");
    }
    let last = at(&rows, 34);
    assert_eq!(last.unmet, [40, 28, 40]);
    assert_eq!(last.cash["farm"], 5);
}

/// P3, less money: settles at once in a different steady state, the shop holding half its cash.
/// Nothing in the period needs the shop's other half: it pays its wages from 700 and buys its
/// food after it has sold. Distributions pay out earnings only (`financial/close.rs`
/// `distribute`), so the missing 700 is never rebuilt and nothing else moves.
#[test]
fn less_money_settles_with_the_shop_at_half_its_cash() {
    let world = World::less_money();
    let rows = support::run(&world);
    let first = at(&rows, 1).clone();
    assert_eq!(first.cash, support::opening_cash(&world));
    assert_eq!(first.cash["shop"], 700);
    for row in &rows {
        let mut same = row.clone();
        same.period = first.period;
        assert_eq!(same, first, "period {} moved", row.period);
    }
    let plain = at(&support::run(&World::plain()), 1).clone();
    assert_eq!(plain.total_money - first.total_money, 700_000_000);
    assert_eq!(first.unmet, [0, 0, 0]);
}

/// P4, higher pay: runs away. At the clinic's higher wage its opening cash, after wages, buys
/// only 36 units of utility (`services/admission.rs`, the cash bound of a request), so four
/// households go without care in period 1; the clinic's quote falls with spare capacity, its
/// workers keep the surplus wage, the owner's income falls, and the clinic stops at period 12,
/// the farm at period 21 and the shop at period 30.
#[test]
fn higher_pay_runs_away_until_the_clinic_farm_and_shop_stop() {
    let rows = support::run(&World::higher_pay());
    let first = at(&rows, 1);
    assert_eq!(first.output[CLINIC], 36);
    assert_eq!(first.unmet[CARE], 4);
    assert_eq!(first.cash["w_clinic"], 70);
    for period in 12..=34 {
        assert_eq!(at(&rows, period).output[CLINIC], 0, "period {period}");
        assert_eq!(at(&rows, period).cash["clinic"], 6, "period {period}");
    }
    let last = at(&rows, 34);
    assert_eq!((last.cash["farm"], last.cash["shop"]), (4, 4));
    assert_eq!(last.hours_attended[SHOP], 0);
    assert_eq!(last.unmet, [40, 15, 40]);
}

/// P2 under the market policy: runs away, and the sellers plan from what was wanted. Through
/// period 8 it is P2's own run. At period 9 the shop's hours make its food market short and it
/// clears above the posted price; what the buyers could pay for at the posted price and did not
/// get is added to the shop's next hours (`recurring/firms.rs` `handling_quantities`), so its plan
/// follows what was wanted, not only what it sold, and its posted price steps up
/// (`recurring/prices.rs` `update_prices`). The dead clinic's buyers are priced out of an empty
/// market, so its quote rises a step a period instead of falling to its minimum
/// (`services/market.rs` `quote`, `PricedOut`). The farm plans 9 batches from period 29 for what
/// was wanted and stops at period 28 all the same.
#[test]
fn less_supply_under_a_market_policy_runs_away_with_the_sellers_planning_from_what_was_wanted() {
    let rows = support::run(&World::less_supply().with_market());
    let shop_hours: Vec<_> = (7..=14).map(|p| at(&rows, p).planned[SHOP]).collect();
    assert_eq!(shop_hours, [33, 33, 34, 40, 38, 35, 35, 35]);
    assert_eq!(at(&rows, 8).price_cents[SHOP], 3_800);
    assert_eq!(at(&rows, 9).price_cents[SHOP], 3_900);
    assert_eq!(at(&rows, 10).price_cents[SHOP], 4_000);
    assert_eq!(at(&rows, 34).price_cents[SHOP], 4_700);
    for period in 11..=34 {
        assert_eq!(at(&rows, period).output[CLINIC], 0, "period {period}");
        assert_eq!(
            at(&rows, period).price_cents[CLINIC],
            2_100 + 100 * i128::from(period - 10),
            "period {period}"
        );
    }
    for period in 28..=34 {
        assert_eq!(at(&rows, period).output[FARM], 0, "period {period}");
    }
    assert_eq!(at(&rows, 29).planned[FARM], 9);
    assert!(at(&rows, 10).cleared_cents[SHOP] > at(&rows, 10).price_cents[SHOP]);
    let last = at(&rows, 34);
    assert_eq!(last.unmet[FOOD], 40);
    assert_eq!(last.output[UTILITY], 30);
}
