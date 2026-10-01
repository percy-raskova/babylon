//! Read-only lifetime identities derived from the captured catalog and receipt prefix.
//! This index is presentation evidence, never retained simulation state.
use super::ProductionProjectionError;
use crate::michigan_material::MichiganMaterialCatalog;
use babylon_material_circuit::{
    recurring_household_order_id, recurring_procurement_order_id, FinalDemandOrder, GoodId,
    MaterialCircuitState, OrderId, RouteId, SiteId, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::BTreeMap;

type Result<T> = std::result::Result<T, ProductionProjectionError>;
#[derive(Clone)]
pub(super) struct Delivery {
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
pub(super) struct FinalOrder {
    pub order: FinalDemandOrder,
    pub expired: u64,
}
#[derive(Default)]
pub(super) struct OrderHistory {
    pub deliveries: BTreeMap<OrderId, Delivery>,
    pub final_orders: BTreeMap<OrderId, FinalOrder>,
}
impl OrderHistory {
    pub fn from_catalog(catalog: &MichiganMaterialCatalog) -> Result<Self> {
        let mut result = Self::default();
        for route in catalog.routes() {
            let supplier = catalog
                .site(&route.supplier_site_key)
                .ok_or(ProductionProjectionError::Content)?
                .id();
            let buyer = catalog
                .site(&route.buyer_site_key)
                .ok_or(ProductionProjectionError::Content)?
                .id();
            let good = catalog
                .good(&route.good_key)
                .ok_or(ProductionProjectionError::Content)?;
            result.deliveries.insert(
                route.order_id(),
                Delivery {
                    route: route.id(),
                    supplier,
                    buyer,
                    good: good.id(),
                    unit: good.unit_id(),
                    ordered: route.ordered_quantity,
                    shipped: 0,
                    delivered: 0,
                    lost: 0,
                    realized: 0,
                },
            );
        }
        for row in catalog.final_demands() {
            let retailer = catalog
                .site(&row.retailer_site_key)
                .ok_or(ProductionProjectionError::Content)?
                .id();
            let good = catalog
                .good(&row.good_key)
                .ok_or(ProductionProjectionError::Content)?;
            result.final_orders.insert(
                row.order_id(),
                FinalOrder {
                    order: FinalDemandOrder {
                        order_id: row.order_id(),
                        demand_principal_id: row.principal_id(),
                        retailer_site_id: retailer,
                        good_id: good.id(),
                        unit_id: good.unit_id(),
                        ordered: row.ordered_quantity,
                        fulfilled: 0,
                    },
                    expired: 0,
                },
            );
        }
        Ok(result)
    }

    pub fn admit(
        &mut self,
        state: &MaterialCircuitState,
        receipts: &MaterialTickReceipts,
    ) -> Result<()> {
        let routes: BTreeMap<_, _> = state
            .supplier_routes
            .iter()
            .map(|route| {
                (
                    (
                        route.buyer_site_id,
                        route.supplier_site_id,
                        route.good_id,
                        route.unit_id,
                    ),
                    route,
                )
            })
            .collect();
        if routes.len() != state.supplier_routes.len() {
            return Err(ProductionProjectionError::State);
        }
        for row in &receipts.procurement {
            if row.period != receipts.resolve_tick
                || row.order_id
                    != recurring_procurement_order_id(
                        row.period,
                        row.buyer_site_id,
                        row.supplier_site_id,
                        row.good_id,
                        row.unit_id,
                    )
            {
                return Err(ProductionProjectionError::State);
            }
            if row.admitted_quantity == 0 {
                continue;
            }
            let route = routes
                .get(&(
                    row.buyer_site_id,
                    row.supplier_site_id,
                    row.good_id,
                    row.unit_id,
                ))
                .ok_or(ProductionProjectionError::State)?;
            if self
                .deliveries
                .insert(
                    row.order_id,
                    Delivery {
                        route: route.route_id,
                        supplier: row.supplier_site_id,
                        buyer: row.buyer_site_id,
                        good: row.good_id,
                        unit: row.unit_id,
                        ordered: row.admitted_quantity,
                        shipped: 0,
                        delivered: 0,
                        lost: 0,
                        realized: 0,
                    },
                )
                .is_some()
            {
                return Err(ProductionProjectionError::State);
            }
        }
        for row in &receipts.household_demand {
            if row.period != receipts.resolve_tick
                || row.order_id
                    != recurring_household_order_id(
                        row.period,
                        (row.principal_id, row.good_id, row.unit_id),
                    )
            {
                return Err(ProductionProjectionError::State);
            }
            if row.admitted_quantity == 0 {
                continue;
            }
            if self
                .final_orders
                .insert(
                    row.order_id,
                    FinalOrder {
                        order: FinalDemandOrder {
                            order_id: row.order_id,
                            demand_principal_id: row.principal_id,
                            retailer_site_id: row.retailer_site_id,
                            good_id: row.good_id,
                            unit_id: row.unit_id,
                            ordered: row.admitted_quantity,
                            fulfilled: 0,
                        },
                        expired: row.expired_quantity,
                    },
                )
                .is_some()
            {
                return Err(ProductionProjectionError::State);
            }
        }
        Ok(())
    }

    pub fn movements(&mut self, receipts: &MaterialTickReceipts) -> Result<()> {
        for row in &receipts.dispatches {
            let value = self.delivery_mut(row.order_id)?;
            if row.route_id != value.route {
                return Err(ProductionProjectionError::State);
            }
            add(&mut value.shipped, row.quantity)?;
        }
        for row in &receipts.arrivals {
            add(
                &mut self.delivery_mut(row.order_id)?.delivered,
                row.quantity,
            )?;
        }
        for row in &receipts.losses {
            add(&mut self.delivery_mut(row.order_id)?.lost, row.quantity)?;
        }
        for row in &receipts.realizations {
            add(&mut self.delivery_mut(row.order_id)?.realized, row.quantity)?;
        }
        for row in &receipts.local_transfers {
            let value = self.delivery_mut(row.order_id)?;
            if (value.supplier, value.buyer, value.good, value.unit)
                != (
                    row.supplier_site_id,
                    row.buyer_site_id,
                    row.good_id,
                    row.unit_id,
                )
            {
                return Err(ProductionProjectionError::State);
            }
            add(&mut value.shipped, row.quantity)?;
            add(&mut value.delivered, row.quantity)?;
            add(&mut value.realized, row.quantity)?;
        }
        for row in &receipts.local_fulfillments {
            let value = &mut self
                .final_orders
                .get_mut(&row.order_id)
                .ok_or(ProductionProjectionError::State)?
                .order;
            if (
                value.demand_principal_id,
                value.retailer_site_id,
                value.good_id,
                value.unit_id,
            ) != (
                row.demand_principal_id,
                row.retailer_site_id,
                row.good_id,
                row.unit_id,
            ) {
                return Err(ProductionProjectionError::State);
            }
            add(&mut value.fulfilled, row.quantity)?;
        }
        for row in self.deliveries.values() {
            if row.shipped > row.ordered
                || row
                    .delivered
                    .checked_add(row.lost)
                    .is_none_or(|n| n > row.shipped)
                || row.realized > row.delivered
            {
                return Err(ProductionProjectionError::State);
            }
        }
        for row in self.final_orders.values() {
            if row
                .order
                .fulfilled
                .checked_add(row.expired)
                .is_none_or(|n| n > row.order.ordered)
            {
                return Err(ProductionProjectionError::State);
            }
        }
        Ok(())
    }

    fn delivery_mut(&mut self, id: OrderId) -> Result<&mut Delivery> {
        self.deliveries
            .get_mut(&id)
            .ok_or(ProductionProjectionError::State)
    }

    #[cfg(test)]
    pub fn final_from_state(state: &MaterialCircuitState) -> Self {
        Self {
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
fn add(total: &mut u64, quantity: u64) -> Result<()> {
    if quantity == 0 {
        return Err(ProductionProjectionError::State);
    }
    *total = total
        .checked_add(quantity)
        .ok_or(ProductionProjectionError::Arithmetic)?;
    Ok(())
}
