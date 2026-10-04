//! Native quantities are authenticated separately from the carrying-cost witness.
use super::{
    lifecycle, Key, MaterialCircuitState, MaterialTickReceipts, PriceReceipt,
    ProductionProjectionError, Result,
};
use babylon_material_circuit::{CommodityKind, GoodsPriceCostBasis, OutboundOrderId, SiteId};
use std::collections::{BTreeMap, BTreeSet};
#[derive(Default)]
pub(super) struct Flows {
    produced: BTreeMap<Key, u64>,
    released: BTreeMap<Key, u64>,
    handled: BTreeMap<Key, u64>,
    pub waiting: BTreeMap<Key, u64>,
}
fn add<K: Ord>(rows: &mut BTreeMap<K, u64>, key: K, quantity: u64) -> Result<()> {
    let value = rows.entry(key).or_default();
    *value = value
        .checked_add(quantity)
        .ok_or(ProductionProjectionError::Arithmetic)?;
    Ok(())
}
fn add_money(rows: &mut BTreeMap<SiteId, i128>, site: SiteId, amount: i128) -> Result<()> {
    if amount < 0 {
        return Err(ProductionProjectionError::State);
    }
    let value = rows.entry(site).or_default();
    *value = value
        .checked_add(amount)
        .ok_or(ProductionProjectionError::Arithmetic)?;
    Ok(())
}
impl Flows {
    pub(super) fn new(
        prior: &MaterialCircuitState,
        current: &MaterialCircuitState,
        receipt: &MaterialTickReceipts,
        orders: &lifecycle::PeriodOrders,
    ) -> Result<Self> {
        let mut result = Self::default();
        result.production(prior, receipt)?;
        for (before, after) in orders.deliveries.values() {
            add(
                &mut result.released,
                (before.supplier_site_id, before.good_id, before.unit_id),
                after
                    .shipped
                    .checked_sub(before.shipped)
                    .ok_or(ProductionProjectionError::State)?,
            )?;
        }
        for (before, after) in orders.final_orders.values() {
            add(
                &mut result.released,
                (before.retailer_site_id, before.good_id, before.unit_id),
                after
                    .fulfilled
                    .checked_sub(before.fulfilled)
                    .ok_or(ProductionProjectionError::State)?,
            )?;
        }
        for row in &receipt.handling {
            let key = match row.order {
                OutboundOrderId::Delivery(id) => {
                    let (order, _) = orders
                        .deliveries
                        .get(&id)
                        .ok_or(ProductionProjectionError::State)?;
                    (order.supplier_site_id, order.good_id, order.unit_id)
                }
                OutboundOrderId::LocalFinalDemand(id) => {
                    let (order, _) = orders
                        .final_orders
                        .get(&id)
                        .ok_or(ProductionProjectionError::State)?;
                    (order.retailer_site_id, order.good_id, order.unit_id)
                }
                OutboundOrderId::Service(_) => return Err(ProductionProjectionError::State),
            };
            if key.0 != row.site_id {
                return Err(ProductionProjectionError::State);
            }
            add(&mut result.handled, key, row.handled_quantity)?;
        }
        result.waiting(current, receipt)?;
        Ok(result)
    }
    fn production(
        &mut self,
        prior: &MaterialCircuitState,
        receipt: &MaterialTickReceipts,
    ) -> Result<()> {
        let goods: BTreeSet<_> = prior
            .commodities
            .iter()
            .filter(|r| matches!(r.kind, CommodityKind::Storable { .. }))
            .map(|r| (r.good_id, r.unit_id))
            .collect();
        let outputs: BTreeMap<_, _> = prior
            .process_outputs
            .iter()
            .map(|r| (r.process_id, r))
            .collect();
        let mut seen = BTreeSet::new();
        for row in &receipt.production {
            let output = outputs
                .get(&row.process_id)
                .ok_or(ProductionProjectionError::State)?;
            if row.site_id != output.site_id || !seen.insert(row.process_id) {
                return Err(ProductionProjectionError::State);
            }
            if goods.contains(&(output.good_id, output.unit_id)) {
                let quantity = row
                    .produced_batches
                    .checked_mul(output.quantity_per_batch)
                    .ok_or(ProductionProjectionError::Arithmetic)?;
                add(
                    &mut self.produced,
                    (output.site_id, output.good_id, output.unit_id),
                    quantity,
                )?;
            }
        }
        Ok(())
    }
    fn waiting(
        &mut self,
        current: &MaterialCircuitState,
        receipt: &MaterialTickReceipts,
    ) -> Result<()> {
        for row in &receipt.household_demand {
            add(
                &mut self.waiting,
                (row.retailer_site_id, row.good_id, row.unit_id),
                row.expired_quantity,
            )?;
        }
        for row in &current.orders {
            add(
                &mut self.waiting,
                (row.supplier_site_id, row.good_id, row.unit_id),
                row.ordered
                    .checked_sub(row.shipped)
                    .ok_or(ProductionProjectionError::State)?,
            )?;
        }
        for row in &current.final_demand_orders {
            add(
                &mut self.waiting,
                (row.retailer_site_id, row.good_id, row.unit_id),
                row.ordered
                    .checked_sub(row.fulfilled)
                    .ok_or(ProductionProjectionError::State)?,
            )?;
        }
        Ok(())
    }
    pub(super) fn validate_cost(&self, row: &PriceReceipt) -> Result<()> {
        row.cost
            .unit_cost()
            .map_err(|_| ProductionProjectionError::State)?;
        let key = (row.site_id, row.good_id, row.unit_id);
        let produced = self.produced.get(&key).copied().unwrap_or(0);
        let released = self.released.get(&key).copied().unwrap_or(0);
        let handled = self.handled.get(&key).copied().unwrap_or(0);
        let (basis, quantity) = if handled > 0 {
            if handled != released {
                return Err(ProductionProjectionError::State);
            }
            (GoodsPriceCostBasis::Released, released)
        } else if produced > 0 {
            (GoodsPriceCostBasis::Produced, produced)
        } else if released > 0 {
            (GoodsPriceCostBasis::Released, released)
        } else {
            (GoodsPriceCostBasis::Unavailable, 0)
        };
        if row.cost.basis != basis
            || row.cost.quantity != quantity
            || (handled == 0 && row.cost.handling_wages.micro_units() != 0)
        {
            return Err(ProductionProjectionError::State);
        }
        Ok(())
    }
    pub(super) fn validate_handling_wages(&self, receipt: &MaterialTickReceipts) -> Result<()> {
        let quoted: BTreeSet<_> = receipt
            .prices
            .iter()
            .map(|r| (r.site_id, r.good_id, r.unit_id))
            .collect();
        let mut amounts = BTreeMap::new();
        for row in &receipt.prices {
            add_money(
                &mut amounts,
                row.site_id,
                row.cost.handling_wages.micro_units(),
            )?;
        }
        let mut actual = BTreeMap::new();
        for row in &receipt.member_labor_use {
            add_money(&mut actual, row.site_id, row.handling_wages.micro_units())?;
        }
        let partial: BTreeSet<_> = self
            .handled
            .iter()
            .filter(|(key, quantity)| **quantity > 0 && !quoted.contains(key))
            .map(|(key, _)| key.0)
            .collect();
        for site in actual
            .keys()
            .chain(amounts.keys())
            .copied()
            .collect::<BTreeSet<_>>()
        {
            let claimed = amounts.get(&site).copied().unwrap_or(0);
            let total = actual.get(&site).copied().unwrap_or(0);
            // A site's unquoted commodities may legitimately own the remaining wages.
            if claimed > total || (!partial.contains(&site) && claimed != total) {
                return Err(ProductionProjectionError::State);
            }
        }
        Ok(())
    }
}
