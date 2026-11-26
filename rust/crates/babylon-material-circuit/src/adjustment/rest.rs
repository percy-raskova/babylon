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
#[cfg(test)]
pub(crate) fn rests(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    site: SiteId,
    offered: u64,
) -> bool {
    rests_with(catalog, offered, || made_hours(state, site))
}

/// `rests`, with the test of the workplace's hours left to `made`, which is asked only when the catalog asks
/// and nothing was offered.
fn rests_with(catalog: &MaterialCatalog, offered: u64, made: impl FnOnce() -> bool) -> bool {
    if offered > 0 || !asks_resting(catalog) {
        return false;
    }
    !made()
}

/// Whether the catalog asks for the resting price.
fn asks_resting(catalog: &MaterialCatalog) -> bool {
    catalog
        .market_clearing
        .as_ref()
        .is_some_and(|order| policy::asks(&order.adjustments, AdjustmentRule::RestingPrice))
}

/// Whether a workplace's people made available any hours in the closing period: the members' labor rows of
/// that period, through the employment terms that name the workplace.
#[cfg(test)]
pub(crate) fn made_hours(state: &MaterialCircuitState, site: SiteId) -> bool {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return false;
    };
    let members: BTreeSet<_> = economy
        .employment
        .iter()
        .filter(|terms| terms.site_id == site)
        .map(|terms| terms.member_id)
        .collect();
    economy.member_labor.iter().any(|row| {
        row.period == state.period && row.available_hours > 0 && members.contains(&row.member_id)
    })
}

/// The sites for which `made_hours` is true, found once: a site is among them when one of its employment terms
/// names a member whose labor row of the closing period offers hours. For a state that is not monetary, none.
pub(crate) fn sites_with_hours(state: &MaterialCircuitState) -> BTreeSet<SiteId> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return BTreeSet::new();
    };
    let offering: BTreeSet<_> = economy
        .member_labor
        .iter()
        .filter(|row| row.period == state.period && row.available_hours > 0)
        .map(|row| row.member_id)
        .collect();
    economy
        .employment
        .iter()
        .filter(|terms| offering.contains(&terms.member_id))
        .map(|terms| terms.site_id)
        .collect()
}

/// The products among `products` whose sellers rest at this close, with what each offered at its markets. A
/// service that the market shares in proportion never rests (ADR325, N3): its provider lives on its public
/// body's money, not on sales.
pub(crate) fn resting_among(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    products: impl Iterator<Item = (Product, u64)>,
) -> BTreeSet<Product> {
    // The sites with hours are found once, and only when a seller that offered nothing is asked of.
    let mut with_hours: Option<BTreeSet<SiteId>> = None;
    products
        .filter(|((site, good, unit), offered)| {
            rests_with(catalog, *offered, || {
                with_hours
                    .get_or_insert_with(|| sites_with_hours(state))
                    .contains(site)
            }) && !policy::is_shared_service(catalog, *good, *unit)
        })
        .map(|(product, _)| product)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::policy::fixture;
    use super::*;
    use crate::CapacityReservations;

    fn state() -> MaterialCircuitState {
        MaterialCircuitState {
            period: 1,
            accounting: CircuitAccounting::PhysicalControl,
            service_connections: vec![],
            service_orders: vec![],
            route_stage_capacities: vec![],
            inventory: vec![],
            orders: vec![],
            freight: vec![],
            corridor_capacities: vec![],
            capacities: vec![],
            labor: vec![],
            production_commitments: vec![],
            final_demand_principals: vec![],
            final_demand_orders: vec![],
            maintenance_service: None,
            capacity_reservations: CapacityReservations::default(),
        }
    }

    fn seller(site: u8, product: u8) -> Product {
        (
            SiteId::from_bytes([site; 32]),
            fixture::good(product),
            fixture::unit(product),
        )
    }

    /// Of the products, those that rest: each offered nothing and its seller made no hours.
    fn resting(order: &[u8], products: &[Product]) -> BTreeSet<Product> {
        resting_among(
            &fixture::catalog_with(Some(order)),
            &state(),
            products.iter().map(|product| (*product, 0)),
        )
    }

    #[test]
    fn a_shared_service_never_rests() {
        // Service 3 is in the order, service 4 is left out of it.
        let in_order = seller(1, 3);
        let left_out = seller(2, 4);
        assert_eq!(
            resting(&[1, 3], &[in_order, left_out]),
            BTreeSet::from([in_order])
        );
    }

    #[test]
    fn a_good_outside_the_order_rests_as_before() {
        // Storable good 2 is left out of the order, as equipment is: its seller rests.
        let equipment = seller(3, 2);
        assert_eq!(resting(&[1, 3], &[equipment]), BTreeSet::from([equipment]));
    }
}
