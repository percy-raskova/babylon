//! The small world with rule A6 (ADR314): a workplace holding more money than one period of what it
//! pays out plans for what was asked of it, as far as that money carries. The record is
//! `reports/economy-repair-2026-11-20/small-world.md`.

use super::support::{self, Push, World, CLINIC, UTILITY};
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
