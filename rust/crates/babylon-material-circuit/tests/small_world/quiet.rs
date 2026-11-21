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

use super::support::{self, World};

#[test]
fn the_balanced_opening_without_taxes_is_still_for_34_periods() {
    let first = support::assert_still(&World::plain());
    assert_eq!(first.employed, [15, 5, 5, 5]);
    assert_eq!((first.public_receipts, first.public_payments), (0, 0));
}

/// The wage tax and the operating-income tax collect exactly the support payment each period.
#[test]
fn the_balanced_opening_with_a_public_account_is_still_for_34_periods() {
    let first = support::assert_still(&World::taxed());
    assert_eq!(first.employed, [12, 4, 4, 4]);
    assert_eq!((first.public_receipts, first.public_payments), (640, 640));
    assert_eq!(first.cash["public"], 640);
}

/// With the market policy households buy at the market's price; no market is short, so it is
/// the posted price, and no clearing is recorded. Restocking between businesses is the old rule.
#[test]
fn the_balanced_opening_under_a_market_policy_is_still_for_34_periods() {
    let first = support::assert_still(&World::plain().with_market());
    assert_eq!(first.cleared_cents, [0; 4]);
}
