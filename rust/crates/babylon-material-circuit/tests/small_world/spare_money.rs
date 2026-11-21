//! The small world with rule A6 (ADR314): a workplace holding more money than one period of what it
//! pays out plans for what was asked of it, as far as that money carries. The record is
//! `reports/economy-repair-2026-11-20/small-world.md`.

use super::support::{self, Push, Snapshot, World, CLINIC, UTILITY};
use babylon_material_circuit::{
    CircuitAccounting, MaterialCircuitTransition, ProcessId, ProductionPlanReceipt,
    ServiceMarketReceipt, SiteId,
};
use std::collections::BTreeSet;

/// The batches the state plans for a process at the next close.
fn state_batches(closed: &MaterialCircuitTransition, process: ProcessId) -> u64 {
    let CircuitAccounting::Monetary(economy) = &closed.state.accounting else {
        panic!("the small world is monetary")
    };
    economy
        .recurring
        .as_ref()
        .expect("the small world plans recurring production")
        .production
        .iter()
        .find(|row| row.process_id == process)
        .map_or(0, |row| row.planned_batches)
}

/// The two runs that push the economy below full work, asking for the rule.
fn asking_runs() -> [World; 2] {
    [
        World::higher_pay().with_tiers().with_spare_money(),
        World::benefits()
            .with_tiers()
            .pushed(Push::LowerFundTaxes)
            .with_spare_money(),
    ]
}

/// At the opening every workplace holds exactly one period of what it pays out, and in a quiet
/// world nothing is asked and left unpaid, so the rule changes nothing.
#[test]
fn asking_changes_nothing_in_a_quiet_world() {
    for (asking, not_asking) in [
        (
            World::plain().with_market().with_spare_money(),
            World::plain().with_market(),
        ),
        (
            World::plain().with_tiers().with_spare_money(),
            World::plain().with_tiers(),
        ),
        (
            World::benefits().with_tiers().with_spare_money(),
            World::benefits().with_tiers(),
        ),
    ] {
        let rows = support::run(&asking);
        support::assert_still_rows(&asking, &rows);
        assert_eq!(rows, support::run(&not_asking));
    }
}

/// The first period and provider at which the state plans more than the market receipt's paid-for
/// plan, in a run.
fn first_raise(world: &World) -> Option<(u64, SiteId)> {
    let mut first = None;
    support::run_observed(world, &mut |period, closed| {
        for market in &closed.service_markets {
            if first.is_none() && state_batches(closed, market.process_id) > market.planned_quantity
            {
                first = Some((period, market.site_id));
            }
        }
    });
    first
}

/// Under the pay rise the buyers ask for more than they can pay for at the posted price, and the
/// first workplace holding more than one period of its outlay to plan for the difference is the
/// utility (see `a_maker_with_a_service_input_is_raised_too` for the clinic).
#[test]
fn spare_money_extends_a_plan_under_the_pay_rise() {
    let asking = World::higher_pay().with_tiers().with_spare_money();
    assert_eq!(
        first_raise(&asking),
        Some((FIRST_RAISE.0, support::site(FIRST_RAISE.1)))
    );
    let not_asking = World::higher_pay().with_tiers();
    assert_eq!(first_raise(&not_asking), None);
}

/// A maker whose only input is a service is raised too: the clinic, which takes POWER, plans for
/// the difference in some period of the pay-rise run.
#[test]
fn a_maker_with_a_service_input_is_raised_too() {
    let mut raised = BTreeSet::new();
    support::run_observed(
        &World::higher_pay().with_tiers().with_spare_money(),
        &mut |_, closed| {
            for market in &closed.service_markets {
                if state_batches(closed, market.process_id) > market.planned_quantity {
                    raised.insert(market.site_id);
                }
            }
        },
    );
    assert!(
        raised.contains(&support::site(CLINIC)),
        "the clinic is never raised: {raised:?}"
    );
}

/// The paid-for plans and service markets of period 1 of a run.
fn first_period_plans(
    world: &World,
    check: &mut dyn FnMut(u64, &MaterialCircuitTransition),
) -> Option<(Vec<ProductionPlanReceipt>, Vec<ServiceMarketReceipt>)> {
    let mut first = None;
    support::run_observed(world, &mut |period, closed| {
        check(period, closed);
        if period == 1 {
            first = Some((
                closed.production_plans.clone(),
                closed.service_markets.clone(),
            ));
        }
    });
    first
}

/// The receipts record the paid-for plan; only the state carries the extension.
#[test]
fn the_receipts_keep_the_paid_for_plan() {
    for world in asking_runs() {
        let asked = first_period_plans(&world, &mut |period, closed| {
            for plan in &closed.production_plans {
                let wanted =
                    (plan.dispatched_quantity + plan.unshipped_quantity + plan.output_buffer)
                        .saturating_sub(plan.closing_output_stock);
                assert!(
                    plan.planned_batches <= wanted,
                    "period {period}: a paid-for plan of {} batches for {wanted} units",
                    plan.planned_batches
                );
                assert_eq!(plan.planned_batches == 0, wanted == 0, "period {period}");
            }
        });
        let mut not_asking = world.clone();
        not_asking.spare_money = false;
        let plain = first_period_plans(&not_asking, &mut |_, _| {});
        assert!(asked.is_some());
        assert_eq!(asked, plain, "period 1");
    }
}

/// The market receipts of each period of a run, with the hours asked of each site after it.
fn markets_and_asked(world: &World) -> Vec<PeriodMarkets> {
    let mut markets = Vec::new();
    let rows = support::run_observed(world, &mut |_, closed| {
        let batches = closed
            .service_markets
            .iter()
            .map(|market| (market.process_id, state_batches(closed, market.process_id)))
            .collect();
        markets.push((closed.service_markets.clone(), batches));
    });
    markets
        .into_iter()
        .zip(rows)
        .map(|((receipts, batches), row)| (receipts, batches, row.asked))
        .collect()
}

/// A period's service markets, the state's batches by process, and the hours asked of each site.
type PeriodMarkets = (Vec<ServiceMarketReceipt>, Vec<(ProcessId, u64)>, [u64; 4]);

/// An extension is hours only through today's planning, which stops at nameplate.
#[test]
fn the_extension_asks_no_hours_beyond_nameplate() {
    for world in asking_runs() {
        for (n, (receipts, _, asked)) in markets_and_asked(&world).iter().enumerate() {
            for (site, name) in [(UTILITY, "utility"), (CLINIC, "clinic")] {
                let capacity: u64 = receipts
                    .iter()
                    .filter(|market| market.site_id == support::site(site))
                    .map(|market| market.available_capacity)
                    .sum();
                assert!(
                    asked[site] <= capacity,
                    "period {}: {name} is asked for {} hours of {capacity}",
                    n + 1,
                    asked[site]
                );
            }
        }
    }
}

/// A raise never grows the workplace: the state's plan is at most the larger of the paid-for plan
/// and nameplate.
#[test]
fn a_raise_stops_at_nameplate() {
    for world in asking_runs() {
        for (n, (receipts, batches, _)) in markets_and_asked(&world).iter().enumerate() {
            for market in receipts {
                let planned = batches
                    .iter()
                    .find(|(process, _)| *process == market.process_id)
                    .map_or(0, |&(_, b)| b);
                assert!(
                    planned <= market.planned_quantity.max(market.available_capacity),
                    "period {}: {planned} batches planned, {} paid for, {} nameplate",
                    n + 1,
                    market.planned_quantity,
                    market.available_capacity
                );
            }
        }
    }
}

/// The first raise under the pay rise, read from the run: its period and its site's index.
const FIRST_RAISE: (u64, usize) = (1, UTILITY);

/// Hours attended in a period, all four sites.
fn hours(row: &Snapshot) -> u64 {
    row.hours_attended.iter().sum()
}

/// Full work: 240 hours attended in every period from 25 to 34, no site's output 0 in any of them.
fn is_full_work(rows: &[Snapshot]) -> bool {
    rows.iter()
        .filter(|row| (25..=34).contains(&row.period))
        .all(|row| hours(row) == 240 && row.output.iter().all(|&out| out > 0))
}

/// The hours of every period of a run.
fn hours_by_period(world: &World) -> Vec<u64> {
    support::run(world).iter().map(hours).collect()
}

/// Whole dollars in the accounts a record pins, in the order given.
fn cash_of(row: &Snapshot, accounts: &[&str]) -> Vec<i128> {
    accounts.iter().map(|name| row.cash[name]).collect()
}

/// The pay rise with the tiers and the rule: full work from the first period to the last of 34, and
/// the same world not asking does not return.
#[test]
fn p4_with_tiers_and_spare_money_returns_to_full_work() {
    let asking = World::higher_pay().with_tiers().with_spare_money();
    let rows = support::run(&asking);
    assert!(is_full_work(&rows), "decision 1 does not hold");
    for row in &rows {
        assert_eq!(hours(row), 240, "period {}", row.period);
    }
    let last = &rows[33];
    assert_eq!(last.unmet, [0, 0, 4]);
    assert_eq!(last.output, [120, 40, 39, 40]);
    assert_eq!(
        cash_of(last, &["utility", "farm", "clinic", "shop", "owner"]),
        [1_200, 919, 880, 1_400, 679]
    );
    let not_asking = support::run(&World::higher_pay().with_tiers());
    assert_eq!(hours(&not_asking[33]), 179);
}

/// The tax cut on the fund with the rule: full work does not come back alone. In four periods the
/// rule's hours are below the same world's without it, and in 23 above.
#[test]
fn p5_on_the_fund_with_tiers_and_spare_money_does_not_return_alone() {
    let base = World::benefits().with_tiers().pushed(Push::LowerFundTaxes);
    let asking = support::run(&base.clone().with_spare_money());
    let not_asking = support::run(&base);
    assert!(!is_full_work(&asking), "decision 1 holds");
    assert_eq!(hours(&asking[33]), 234);
    assert_eq!(hours(&not_asking[33]), 225);
    let below: Vec<u64> = (0..34)
        .filter(|&n| hours(&asking[n]) < hours(&not_asking[n]))
        .map(|n| n as u64 + 1)
        .collect();
    let above = (0..34)
        .filter(|&n| hours(&asking[n]) > hours(&not_asking[n]))
        .count();
    assert_eq!(below, [17, 24, 25, 26]);
    assert_eq!(above, 23);
    let last = &asking[33];
    assert_eq!(last.unmet, [1, 7, 8]);
    assert_eq!(last.output, [114, 40, 40, 40]);
    assert_eq!(
        cash_of(
            last,
            &["utility", "farm", "clinic", "shop", "owner", "fund", "public"]
        ),
        [1_140, 997, 880, 1_400, 1_072, 179, 447]
    );
}

/// The long look: a quiet world still does not move in 400 periods.
#[test]
fn asking_changes_nothing_in_a_quiet_world_for_400_periods() {
    for world in [World::plain().with_tiers(), World::benefits().with_tiers()] {
        let asking = world.for_periods(400).with_spare_money();
        support::assert_still_rows(&asking, &support::run(&asking));
    }
}

/// `unmet_by_account` at the last period holds the owner's shortfall only.
fn only_the_owner_is_short(row: &Snapshot) -> bool {
    row.unmet_by_account
        .iter()
        .all(|(name, unmet)| *name == "owner" || *unmet == [0, 0, 0])
}

#[test]
fn the_pay_rise_holds_full_work_for_400_periods() {
    let world = World::higher_pay().with_tiers().for_periods(400);
    let asking = support::run(&world.clone().with_spare_money());
    assert!(asking.iter().all(|row| hours(row) == 240));
    assert_eq!(asking[399].unmet, [0, 0, 3]);
    assert!(only_the_owner_is_short(&asking[399]));
    assert_eq!(hours(&support::run(&world)[399]), 15);
}

#[test]
fn the_poor_harvest_holds_most_work_for_400_periods() {
    let world = World::plain()
        .with_tiers()
        .pushed(Push::LessSupply)
        .for_periods(400);
    let asking = support::run(&world.clone().with_spare_money());
    assert!(asking.iter().all(|row| hours(row) >= 230));
    assert_eq!(asking[399].unmet, [6, 10, 10]);
    assert!(only_the_owner_is_short(&asking[399]));
    assert_eq!(hours(&support::run(&world)[399]), 15);
}

/// With the fund and its taxes the rule alone saves none of the three pushed runs: each ends below
/// 120 hours at period 400, with the rule and without it.
#[test]
fn spare_money_alone_does_not_save_the_fund_world() {
    // (push, hours without the rule, hours with it) at period 400.
    let expected = [
        (Push::LessSupply, 80, 66),
        (Push::HigherPay, 63, 70),
        (Push::LowerFundTaxes, 58, 16),
    ];
    for (push, without, with) in expected {
        let world = World::benefits().with_tiers().pushed(push).for_periods(400);
        let plain = hours_by_period(&world)[399];
        let asking = hours_by_period(&world.with_spare_money())[399];
        assert_eq!((plain, asking), (without, with), "{push:?}");
        assert!(plain < 120 && asking < 120, "{push:?}");
    }
}
