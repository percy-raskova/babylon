//! The pushed runs: the same opening with one change, 34 periods, and the class of its end.
//! Each test names the rules that carry the movement; the record traces them line by line.

use super::support::{self, Snapshot, World, CARE, CLINIC, FARM, SHOP, UTILITY};

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

/// P2 under the market policy: settles in a depressed band, nothing stops. Period 1 is P2's own.
/// A service plans from what its buyers could pay for, not from what they asked
/// (`services/market.rs` `planned_quantity`), so the clinic no longer staffs hours it is not paid
/// for; it makes 38 units at period 2 and from period 16 holds between 5 and 11 units, with its
/// cash never under $755 (it stopped at period 13 before). The sellers still plan from what was
/// wanted (`recurring/firms.rs` `handling_quantities`, `recurring/prices.rs` `update_prices`): the
/// shop's food market is short from period 9 and clears above its posted price, its plan follows
/// what was wanted, and its hours stay between 31 and 40. The farm stops at no period.
#[test]
fn less_supply_under_a_market_policy_settles_in_a_depressed_band_with_no_site_stopping() {
    let rows = support::run(&World::less_supply().with_market());
    let first = at(&rows, 1);
    assert_eq!(
        (first.output[FARM], first.planned[FARM], first.asked[FARM]),
        (36, 5, 50)
    );
    assert_eq!(at(&rows, 2).output[CLINIC], 38);
    for period in 16..=34 {
        let clinic = at(&rows, period).output[CLINIC];
        assert!((5..=11).contains(&clinic), "period {period}: {clinic}");
    }
    for row in &rows {
        assert!(row.cash["clinic"] >= 755, "period {}", row.period);
        assert!(row.output[FARM] >= 27, "period {}", row.period);
        assert!(row.hours_attended[SHOP] >= 31, "period {}", row.period);
    }
    let shop_hours: Vec<_> = (7..=14).map(|p| at(&rows, p).planned[SHOP]).collect();
    assert_eq!(shop_hours, [38, 35, 37, 38, 37, 35, 35, 36]);
    let plans: Vec<_> = [21, 30, 34].map(|p| at(&rows, p).planned[SHOP]).to_vec();
    assert_eq!(plans, [32, 37, 35]);
    let hours: Vec<_> = [21, 30, 34]
        .map(|p| at(&rows, p).hours_attended[SHOP])
        .to_vec();
    assert_eq!(hours, [34, 36, 35]);
    assert_eq!(at(&rows, 8).price_cents[SHOP], 3_800);
    assert_eq!(at(&rows, 9).price_cents[SHOP], 3_900);
    assert_eq!(at(&rows, 10).price_cents[SHOP], 4_000);
    assert_eq!(at(&rows, 34).price_cents[SHOP], 4_900);
    assert_eq!(at(&rows, 9).cleared_cents[SHOP], 4_220);
    for period in 7..=34 {
        let quote = at(&rows, period).price_cents[CLINIC];
        assert!((2_200..=2_600).contains(&quote), "period {period}: {quote}");
    }
    assert_eq!(at(&rows, 29).planned[FARM], 7);
    let last = at(&rows, 34);
    assert_eq!(last.unmet, [4, 21, 34]);
    assert_eq!(last.output[UTILITY], 65);
    assert_eq!((last.cash["clinic"], last.cash["farm"]), (851, 1_258));
}

/// P1 under the market policy: runs away slowly, nothing stops. Through period 1 it is P1's own
/// run. A service plans from what its buyers could pay for (`services/market.rs`
/// `planned_quantity`), so the clinic no longer pays idle hours and its cash never falls under
/// $719 (it ran out at period 27 before). Its output still slides from 35 to 12 units as the
/// households' care goes unfunded, so care unmet grows from 0 to 23, while the farm's plan climbs
/// from 4 batches to 8.
#[test]
fn less_demand_under_a_market_policy_runs_away_slowly_with_no_site_stopping() {
    let rows = support::run(&World::less_demand().with_market());
    let first = at(&rows, 1);
    assert_eq!(first.price_cents, [1_100, 2_400, 2_900, 3_800]);
    assert_eq!(first.stock[FARM], 45);
    let plans: Vec<_> = (1..=12).map(|p| at(&rows, p).planned[FARM]).collect();
    assert_eq!(plans, [3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]);
    assert_eq!(at(&rows, 34).planned[FARM], 8);
    let clinic: Vec<_> = [1, 2, 13, 21, 34]
        .map(|p| at(&rows, p).output[CLINIC])
        .to_vec();
    assert_eq!(clinic, [35, 26, 20, 18, 12]);
    for row in &rows {
        assert!(row.output[CLINIC] > 0, "period {}", row.period);
        assert!(row.cash["clinic"] >= 719, "period {}", row.period);
    }
    let last = at(&rows, 34);
    assert_eq!(last.unmet, [2, 19, 23]);
    assert_eq!((last.cash["owner"], last.cash["w_farm"]), (883, 27));
}

/// P3 under the market policy: settles at once with the shop at half its cash, exactly as P3
/// does, and exactly as it did before Task 6b. No market is ever short, so the rule has nothing to
/// price and every period equals the first.
#[test]
fn less_money_under_a_market_policy_settles_with_the_shop_at_half_its_cash() {
    let world = World::less_money().with_market();
    let rows = support::run(&world);
    let first = at(&rows, 1).clone();
    assert_eq!(first.cash, support::opening_cash(&world));
    assert_eq!(first.cash["shop"], 700);
    for row in &rows {
        let mut same = row.clone();
        same.period = first.period;
        assert_eq!(same, first, "period {} moved", row.period);
    }
    let plain = at(&support::run(&World::plain().with_market()), 1).clone();
    assert_eq!(plain.total_money - first.total_money, 700_000_000);
    assert_eq!(first.unmet, [0, 0, 0]);
    assert_eq!(first.cleared_cents, [0; 4]);
}

/// P4 under the market policy: cycles in a depressed band, nothing stops for good. In period 1
/// the clinic's cash buys 36 units of utility, so four households go without care and the clinic's
/// market clears at its posted price with its buyers priced out; the workers keep their surplus
/// wage as in P4. A service plans from what its buyers could pay for (`services/market.rs`
/// `planned_quantity`), so no site runs dry: the clinic's output slides from 36 to 6, makes
/// nothing in periods 18, 27, 28 and 29 and is back at 11 at period 30, and the farm and the shop
/// swing between 20 and 40 units and between 24 and 40 hours. The clinic stopped at period 12,
/// the farm at period 21 and the shop at period 30 before.
#[test]
fn higher_pay_under_a_market_policy_cycles_in_a_depressed_band_with_no_site_stopping() {
    let rows = support::run(&World::higher_pay().with_market());
    let first = at(&rows, 1);
    assert_eq!(first.output[CLINIC], 36);
    assert_eq!(first.unmet[CARE], 4);
    assert_eq!(first.cash["w_clinic"], 39);
    assert_eq!(first.cleared_cents[CLINIC], 3_000);
    let none: Vec<_> = rows
        .iter()
        .filter(|row| row.output[CLINIC] == 0)
        .map(|row| row.period)
        .collect();
    assert_eq!(none, [18, 27, 28, 29]);
    for row in &rows {
        assert!(row.cash["clinic"] >= 320, "period {}", row.period);
        assert!(row.output[FARM] >= 20, "period {}", row.period);
        assert!(row.hours_attended[SHOP] >= 24, "period {}", row.period);
    }
    let last = at(&rows, 34);
    assert_eq!((last.cash["farm"], last.cash["shop"]), (1_588, 1_299));
    assert_eq!(last.unmet, [4, 12, 33]);
}
