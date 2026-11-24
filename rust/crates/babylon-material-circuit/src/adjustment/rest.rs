//! A workplace that employs nobody and offered nothing holds its price (A17, A19; ADR318 L1).

use crate::{GoodId, MaterialCatalog, MaterialCircuitState, SiteId, UnitId};
use std::collections::BTreeSet;

use super::{policy, AdjustmentRule};
use crate::CircuitAccounting;

/// One product of one seller.
pub(crate) type Product = (SiteId, GoodId, UnitId);

/// Whether a workplace rests at this close: the catalog asks, its people offered 0 hours in the closing period,
/// and it offered nothing at its markets (`offered`).
///
/// The hours are read from the members' labor rows of the closing period, which the last staffing wrote as
/// each member's persons employed times the hours of a person, and the employment terms that name the
/// workplace. They stay as the staffing wrote them through the whole close.
pub(crate) fn rests(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    site: SiteId,
    offered: u64,
) -> bool {
    if offered > 0
        || !catalog
            .market_clearing
            .as_ref()
            .is_some_and(|order| policy::asks(&order.adjustments, AdjustmentRule::RestingPrice))
    {
        return false;
    }
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return false;
    };
    let members: BTreeSet<_> = economy
        .employment
        .iter()
        .filter(|terms| terms.site_id == site)
        .map(|terms| terms.member_id)
        .collect();
    !economy.member_labor.iter().any(|row| {
        row.period == state.period && row.available_hours > 0 && members.contains(&row.member_id)
    })
}

/// The products among `products` whose sellers rest at this close, with what each offered at its markets.
pub(crate) fn resting_among(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    products: impl Iterator<Item = (Product, u64)>,
) -> BTreeSet<Product> {
    products
        .filter(|((site, _, _), offered)| rests(catalog, state, *site, *offered))
        .map(|(product, _)| product)
        .collect()
}
