//! Active order witnesses and bounded cumulative totals from authenticated periods.
//! This index is presentation evidence, never retained simulation state.
use super::ProductionProjectionError;
use babylon_material_circuit::{
    FinalDemandOrder, FinalDemandPrincipalId, GoodId, MaterialCircuitState, OrderId, RouteId,
    SiteId, UnitId,
};
use std::collections::{BTreeMap, BTreeSet};

type Result<T> = std::result::Result<T, ProductionProjectionError>;
#[derive(Clone, PartialEq, Eq)]
pub(crate) struct Delivery {
    pub route: RouteId,
    pub supplier: SiteId,
    pub buyer: SiteId,
    pub good: GoodId,
    pub unit: UnitId,
    pub ordered: u64,
    pub shipped: u64,
    pub delivered: u64,
    pub lost: u64,
    pub realized: u64,
}
#[derive(Clone)]
pub(crate) struct FinalOrder {
    pub order: FinalDemandOrder,
    pub expired: u64,
}
#[derive(Clone, Default)]
pub(crate) struct FinalTotals {
    pub ordered: u64,
    pub fulfilled: u64,
    pub expired: u64,
    pub count: u64,
    pub retailers: BTreeSet<SiteId>,
}
#[derive(Clone, Default)]
pub(crate) struct OrderHistory {
    pub deliveries: BTreeMap<OrderId, Delivery>,
    pub final_orders: BTreeMap<OrderId, FinalOrder>,
    pub retired_deliveries: BTreeMap<(RouteId, SiteId, SiteId, GoodId, UnitId), Delivery>,
    pub retired_final: BTreeMap<(FinalDemandPrincipalId, GoodId, UnitId), FinalTotals>,
}
impl OrderHistory {
    pub fn from_opening(state: &MaterialCircuitState) -> Result<Self> {
        if state.period != 1 {
            return Err(ProductionProjectionError::History);
        }
        let mut routes = BTreeMap::new();
        for row in &state.supplier_routes {
            if routes
                .insert(
                    (
                        row.buyer_site_id,
                        row.supplier_site_id,
                        row.good_id,
                        row.unit_id,
                    ),
                    row.route_id,
                )
                .is_some()
            {
                return Err(ProductionProjectionError::State);
            }
        }
        let mut result = Self::default();
        for row in &state.orders {
            let route = *routes
                .get(&(
                    row.buyer_site_id,
                    row.supplier_site_id,
                    row.good_id,
                    row.unit_id,
                ))
                .ok_or(ProductionProjectionError::State)?;
            if result
                .deliveries
                .insert(row.order_id, delivery(row, route))
                .is_some()
            {
                return Err(ProductionProjectionError::State);
            }
        }
        for row in &state.final_demand_orders {
            if result
                .final_orders
                .insert(
                    row.order_id,
                    FinalOrder {
                        order: row.clone(),
                        expired: 0,
                    },
                )
                .is_some()
            {
                return Err(ProductionProjectionError::State);
            }
        }
        Ok(result)
    }

    /// Drop only principals already absent from the authenticated opening register.
    /// Aggregate counters keep stable relation identities, never retired order IDs.
    pub fn retire(&mut self, opening: &MaterialCircuitState) -> Result<()> {
        let delivery_ids: BTreeSet<_> = opening.orders.iter().map(|row| row.order_id).collect();
        let retired: Vec<_> = self
            .deliveries
            .keys()
            .copied()
            .filter(|id| !delivery_ids.contains(id))
            .collect();
        for id in retired {
            let row = self
                .deliveries
                .remove(&id)
                .ok_or(ProductionProjectionError::State)?;
            if row.delivered.checked_add(row.lost) != Some(row.ordered) {
                return Err(ProductionProjectionError::State);
            }
            if let Some(total) = self.retired_deliveries.get_mut(&(
                row.route,
                row.supplier,
                row.buyer,
                row.good,
                row.unit,
            )) {
                if (total.supplier, total.buyer, total.good, total.unit)
                    != (row.supplier, row.buyer, row.good, row.unit)
                {
                    return Err(ProductionProjectionError::State);
                }
                for (sum, value) in [
                    (&mut total.ordered, row.ordered),
                    (&mut total.shipped, row.shipped),
                    (&mut total.delivered, row.delivered),
                    (&mut total.lost, row.lost),
                    (&mut total.realized, row.realized),
                ] {
                    *sum = sum
                        .checked_add(value)
                        .ok_or(ProductionProjectionError::Arithmetic)?;
                }
            } else {
                self.retired_deliveries.insert(
                    (row.route, row.supplier, row.buyer, row.good, row.unit),
                    row,
                );
            }
        }
        let final_ids: BTreeSet<_> = opening
            .final_demand_orders
            .iter()
            .map(|row| row.order_id)
            .collect();
        let retired: Vec<_> = self
            .final_orders
            .keys()
            .copied()
            .filter(|id| !final_ids.contains(id))
            .collect();
        for id in retired {
            let known = self
                .final_orders
                .remove(&id)
                .ok_or(ProductionProjectionError::State)?;
            let row = known.order;
            if row.fulfilled.checked_add(known.expired) != Some(row.ordered) {
                return Err(ProductionProjectionError::State);
            }
            let total = self
                .retired_final
                .entry((row.demand_principal_id, row.good_id, row.unit_id))
                .or_default();
            for (sum, value) in [
                (&mut total.ordered, row.ordered),
                (&mut total.fulfilled, row.fulfilled),
                (&mut total.expired, known.expired),
                (&mut total.count, 1),
            ] {
                *sum = sum
                    .checked_add(value)
                    .ok_or(ProductionProjectionError::Arithmetic)?;
            }
            total.retailers.insert(row.retailer_site_id);
        }
        Ok(())
    }

    /// Retain only the single lifecycle validator's completed witnesses.
    pub fn record(
        &mut self,
        prior: &MaterialCircuitState,
        period: &super::lifecycle::PeriodOrders,
    ) -> Result<()> {
        self.retire(prior)?;
        let prior_delivery: BTreeSet<_> = prior.orders.iter().map(|r| r.order_id).collect();
        let prior_final: BTreeSet<_> = prior
            .final_demand_orders
            .iter()
            .map(|r| r.order_id)
            .collect();
        if self.deliveries.keys().copied().collect::<BTreeSet<_>>() != prior_delivery
            || self.final_orders.keys().copied().collect::<BTreeSet<_>>() != prior_final
        {
            return Err(ProductionProjectionError::History);
        }
        let routes: BTreeMap<_, _> = prior
            .supplier_routes
            .iter()
            .map(|r| {
                (
                    (r.buyer_site_id, r.supplier_site_id, r.good_id, r.unit_id),
                    r.route_id,
                )
            })
            .collect();
        if routes.len() != prior.supplier_routes.len() {
            return Err(ProductionProjectionError::State);
        }
        for (&id, (before, after)) in &period.deliveries {
            let route = *routes
                .get(&(
                    before.buyer_site_id,
                    before.supplier_site_id,
                    before.good_id,
                    before.unit_id,
                ))
                .ok_or(ProductionProjectionError::State)?;
            let opening = delivery(before, route);
            if self
                .deliveries
                .get(&id)
                .is_some_and(|known| known != &opening)
            {
                return Err(ProductionProjectionError::History);
            }
            self.deliveries.insert(id, delivery(after, route));
        }
        for (&id, (before, after)) in &period.final_orders {
            if self
                .final_orders
                .get(&id)
                .is_some_and(|known| known.order != *before || known.expired != 0)
            {
                return Err(ProductionProjectionError::History);
            }
            self.final_orders.insert(
                id,
                FinalOrder {
                    order: after.clone(),
                    expired: period.expired.get(&id).copied().unwrap_or(0),
                },
            );
        }
        Ok(())
    }

    #[cfg(test)]
    pub fn final_from_state(state: &MaterialCircuitState) -> Self {
        Self {
            retired_deliveries: BTreeMap::new(),
            retired_final: BTreeMap::new(),
            deliveries: BTreeMap::new(),
            final_orders: state
                .final_demand_orders
                .iter()
                .map(|row| {
                    (
                        row.order_id,
                        FinalOrder {
                            order: row.clone(),
                            expired: 0,
                        },
                    )
                })
                .collect(),
        }
    }
}
fn delivery(row: &babylon_material_circuit::OrderRow, route: RouteId) -> Delivery {
    Delivery {
        route,
        supplier: row.supplier_site_id,
        buyer: row.buyer_site_id,
        good: row.good_id,
        unit: row.unit_id,
        ordered: row.ordered,
        shipped: row.shipped,
        delivered: row.delivered,
        lost: row.lost,
        realized: row.realized,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn distinct_supplier_relations_can_retire_on_the_same_physical_route() {
        let state = super::super::services_fixture::opening();
        let mut history = OrderHistory::default();
        for n in 1..=2 {
            history.deliveries.insert(
                OrderId::from_bytes([n; 32]),
                Delivery {
                    route: RouteId::from_bytes([1; 32]),
                    supplier: SiteId::from_bytes([n; 32]),
                    buyer: SiteId::from_bytes([3; 32]),
                    good: GoodId::from_bytes([n; 32]),
                    unit: UnitId::from_bytes([n; 32]),
                    ordered: 3,
                    shipped: 3,
                    delivered: 2,
                    lost: 1,
                    realized: 2,
                },
            );
        }
        history.retire(&state).unwrap();
        assert!(history.deliveries.is_empty());
        assert_eq!(history.retired_deliveries.len(), 2);
        assert_eq!(
            history
                .retired_deliveries
                .values()
                .map(|r| r.ordered)
                .sum::<u64>(),
            6
        );
    }
}
