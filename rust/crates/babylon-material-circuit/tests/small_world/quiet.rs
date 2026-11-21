//! The quiet runs: the balanced opening, left alone for 34 periods, does not move at all.
//!
//! Nothing moves because every rule that could move it is at its fixed point: each household's
//! wages buy exactly its need (`recurring/households.rs`, `desired` and the cash bound of
//! admission); the farm plans what it shipped plus its buffer less its stock
//! (`recurring/firms.rs` `plan_production`); each service plans what was requested
//! (`services/market.rs` `update`); staffing retains the larger of this and the last request
//! (`staffing/transition.rs` `advance_pool`); the goods quote holds when nothing waits and stock
//! is at target (`recurring/prices.rs` `quote`); the service quote holds when what was performed
//! fills the capacity and covers its direct cost (`services/market.rs` `quote`); and every site
//! pays out exactly its period's earnings (`financial/close.rs` `distribute`).

use super::support::{self, Snapshot, World, CARE, FOOD, PERIODS, POWER};

/// Every period's measures equal the first period's, and the first period's cash is the opening's.
fn assert_still(world: &World) -> Snapshot {
    let rows = support::run(world);
    assert_eq!(rows.len(), usize::try_from(PERIODS).expect("few periods"));
    let first = rows[0].clone();
    assert_eq!(
        first.cash,
        support::opening_cash(world),
        "period 1 closes with the opening cash"
    );
    for row in &rows {
        let mut same = row.clone();
        same.period = first.period;
        assert_eq!(same, first, "period {} moved", row.period);
    }
    assert_eq!(first.planned, [120, 4, 40, 40]);
    assert_eq!(first.hours_attended, [120, 40, 40, 40]);
    assert_eq!(first.output, [120, 40, 40, 40]);
    assert_eq!(first.stock, [0, 40, 0, 40]);
    assert_eq!(first.price_cents, [1_200, 2_500, 3_000, 3_800]);
    assert_eq!(first.sales, [120, 40, 40, 40]);
    for good in [FOOD, POWER, CARE] {
        assert_eq!(first.required[good], 40);
        assert_eq!(first.consumed[good], 40);
        assert_eq!(first.unmet[good], 0);
    }
    first
}

#[test]
fn the_balanced_opening_without_taxes_is_still_for_34_periods() {
    let first = assert_still(&World::plain());
    assert_eq!(first.employed, [15, 5, 5, 5]);
    assert_eq!((first.public_receipts, first.public_payments), (0, 0));
}

/// The wage tax and the operating-income tax collect exactly the support payment each period.
#[test]
fn the_balanced_opening_with_a_public_account_is_still_for_34_periods() {
    let first = assert_still(&World::taxed());
    assert_eq!(first.employed, [12, 4, 4, 4]);
    assert_eq!((first.public_receipts, first.public_payments), (640, 640));
    assert_eq!(first.cash["public"], 640);
}

/// With the market policy households buy at the market's price; no market is short, so it is
/// the posted price, and no clearing is recorded. Restocking between businesses is the old rule.
#[test]
fn the_balanced_opening_under_a_market_policy_is_still_for_34_periods() {
    let first = assert_still(&World::plain().with_market());
    assert_eq!(first.cleared_cents, [0; 4]);
}
