use super::{
    is_service, kind, CommodityKind, GoodId, HouseholdServiceReceipt, MaterialCircuitError,
    MaterialCircuitState, Result, ServiceMarketReceipt, ServiceOrder, ServiceOutputReceipt,
    ServicePerformanceReceipt, ServiceStage, UnitId,
};
use crate::inventory::{
    credit_inventory, debit_inventory, publish_inventory, take_inventory, InventoryLedger,
};
use crate::valuation::CostClose;
use crate::{
    AccountId, CircuitAccounting, MoneyTransferReceipt, OutboundOrderId, ProductionCommitment,
};
use std::collections::BTreeMap;
type GrantKey = (AccountId, GoodId, UnitId);

/// Transient current-period grants. No field can be captured as durable service stock.
pub(crate) struct ServiceClose {
    pub(crate) performance: Vec<ServicePerformanceReceipt>,
    pub(crate) household: Vec<HouseholdServiceReceipt>,
    pub(crate) markets: Vec<ServiceMarketReceipt>,
    pub(crate) outputs: Vec<ServiceOutputReceipt>,
    households: BTreeMap<GrantKey, u64>,
}
impl ServiceClose {
    pub(crate) fn new(
        state: &mut MaterialCircuitState,
        movements: &mut Vec<MoneyTransferReceipt>,
    ) -> Result<Self> {
        let performance = super::admission::admit(state, movements)?;
        Ok(Self {
            markets: super::market::capture(state)?,
            performance,
            outputs: vec![],
            household: vec![],
            households: BTreeMap::new(),
        })
    }
    pub(crate) fn allocate(
        &mut self,
        state: &MaterialCircuitState,
        commitments: &[ProductionCommitment],
        allocations: &mut [u64],
    ) -> Result<()> {
        let mut potential = InventoryLedger::new();
        for (c, q) in commitments.iter().zip(allocations.iter()) {
            let output = state
                .process_outputs
                .binary_search_by_key(&c.process_id, |o| o.process_id)
                .ok()
                .map(|i| &state.process_outputs[i])
                .ok_or(MaterialCircuitError::ProcessInvariant)?;
            potential.insert(
                (output.site_id, output.good_id, output.unit_id),
                q.checked_mul(output.quantity_per_batch)
                    .ok_or(MaterialCircuitError::Arithmetic)?,
            );
        }
        let due: Vec<_> = self
            .performance
            .iter()
            .filter(|r| potential.contains_key(&(r.provider_site_id, r.good_id, r.unit_id)))
            .map(|r| ServiceOrder {
                order_id: r.order_id,
                performance_period: r.period,
                provider_site_id: r.provider_site_id,
                buyer: r.buyer,
                good_id: r.good_id,
                unit_id: r.unit_id,
                quantity: r.admitted_quantity,
            })
            .collect();
        let granted = crate::transition::outbound::allocate_services(state, &due, &potential)?;
        for (order, quantity) in due.iter().zip(granted) {
            let i = self
                .performance
                .binary_search_by_key(&order.order_id, |r| r.order_id)
                .map_err(|_| MaterialCircuitError::ServiceInvariant)?;
            self.performance[i].performed_quantity = quantity;
        }
        Ok(())
    }
    pub(crate) fn handoff(
        &mut self,
        state: &mut MaterialCircuitState,
        phase: ServiceStage,
        costs: &mut CostClose,
        movements: &mut Vec<MoneyTransferReceipt>,
    ) -> Result<()> {
        let first = self.outputs.len();
        self.capture_outputs(state, phase, costs)?;
        let mut quantities = take_inventory(state);
        self.sell_grants(state, phase, costs, movements, &mut quantities)?;
        self.expire_outputs(first, costs, &mut quantities)?;
        self.credit_grants(state, phase, costs, &mut quantities)?;
        self.outputs
            .sort_by_key(|r| (r.site_id, r.good_id, r.unit_id));
        publish_inventory(state, quantities);
        Ok(())
    }
    fn capture_outputs(
        &mut self,
        state: &MaterialCircuitState,
        phase: ServiceStage,
        costs: &CostClose,
    ) -> Result<()> {
        let outputs: Vec<_> = state
            .process_outputs
            .iter()
            .filter_map(|r| match super::stage(state, r) {
                Ok(Some(s)) if s == phase => Some(Ok(r.clone())),
                Err(e) => Some(Err(e)),
                _ => None,
            })
            .collect::<Result<_>>()?;
        for output in outputs {
            let direct_cost = costs.service_carrying((
                AccountId::Site(output.site_id),
                output.good_id,
                output.unit_id,
            ));
            let produced_quantity = state
                .inventory
                .iter()
                .find(|r| {
                    (r.site_id, r.good_id, r.unit_id)
                        == (output.site_id, output.good_id, output.unit_id)
                })
                .map_or(0, |r| r.quantity);
            self.outputs.push(ServiceOutputReceipt {
                period: state.period,
                process_id: output.process_id,
                site_id: output.site_id,
                good_id: output.good_id,
                unit_id: output.unit_id,
                produced_quantity,
                allocated_quantity: 0,
                expired_quantity: 0,
                direct_cost,
                expired_cost: babylon_kernel::currency::Currency::from_micro_units(0),
            });
            if let Some(market) = self
                .markets
                .iter_mut()
                .find(|r| r.process_id == output.process_id)
            {
                market.direct_cost = direct_cost;
            }
        }
        Ok(())
    }
    fn sell_grants(
        &mut self,
        state: &mut MaterialCircuitState,
        phase: ServiceStage,
        costs: &mut CostClose,
        movements: &mut Vec<MoneyTransferReceipt>,
        quantities: &mut InventoryLedger,
    ) -> Result<()> {
        for row in &mut self.performance {
            if !matches!(kind(state,row.good_id,row.unit_id)?,CommodityKind::PeriodService{stage:s} if s==phase)
            {
                continue;
            }
            let key = (row.provider_site_id, row.good_id, row.unit_id);
            let available = quantities.get(&key).copied().unwrap_or(0);
            costs.service_handoff(row, available)?;
            debit_inventory(
                quantities,
                key,
                row.performed_quantity,
                MaterialCircuitError::ServiceInvariant,
            )?;
            row.expired_quantity = row
                .admitted_quantity
                .checked_sub(row.performed_quantity)
                .ok_or(MaterialCircuitError::ServiceInvariant)?;
            if row.admitted_quantity > 0 {
                let CircuitAccounting::Monetary(e) = &mut state.accounting else {
                    return Err(MaterialCircuitError::MonetaryInvariant);
                };
                let id = OutboundOrderId::Service(row.order_id);
                if row.performed_quantity > 0 {
                    movements.push(e.book.settle_purchase(id, row.performed_quantity)?.transfer);
                }
                if row.expired_quantity > 0 {
                    movements.push(e.book.refund_purchase(id, row.expired_quantity)?.transfer);
                }
                e.book.retire_purchase(id)?;
            }
        }
        Ok(())
    }
    fn expire_outputs(
        &mut self,
        first: usize,
        costs: &mut CostClose,
        quantities: &mut InventoryLedger,
    ) -> Result<()> {
        // Finish every seller withdrawal before any buyer basis joins the same pool.
        for output in &mut self.outputs[first..] {
            let key = (output.site_id, output.good_id, output.unit_id);
            output.expired_quantity = quantities.remove(&key).unwrap_or(0);
            output.allocated_quantity = output
                .produced_quantity
                .checked_sub(output.expired_quantity)
                .ok_or(MaterialCircuitError::ServiceInvariant)?;
            let cost_key = (
                AccountId::Site(output.site_id),
                output.good_id,
                output.unit_id,
            );
            output.expired_cost = costs.service_carrying(cost_key);
            costs.expire_service(cost_key, output.expired_quantity)?;
            output.validate()?;
        }
        Ok(())
    }
    fn credit_grants(
        &mut self,
        state: &MaterialCircuitState,
        phase: ServiceStage,
        costs: &mut CostClose,
        quantities: &mut InventoryLedger,
    ) -> Result<()> {
        for row in &self.performance {
            if !matches!(kind(state,row.good_id,row.unit_id)?,CommodityKind::PeriodService{stage:s} if s==phase)
            {
                continue;
            }
            costs.receive_service(row)?;
            match row.buyer {
                AccountId::Site(site) => credit_inventory(
                    quantities,
                    (site, row.good_id, row.unit_id),
                    row.performed_quantity,
                )?,
                AccountId::Household(_) => {
                    let quantity = self
                        .households
                        .entry((row.buyer, row.good_id, row.unit_id))
                        .or_default();
                    *quantity = quantity
                        .checked_add(row.performed_quantity)
                        .ok_or(MaterialCircuitError::Arithmetic)?;
                }
                _ => return Err(MaterialCircuitError::ServiceInvariant),
            }
        }
        Ok(())
    }
    pub(crate) fn finish(
        &mut self,
        state: &mut MaterialCircuitState,
        costs: &mut CostClose,
    ) -> Result<()> {
        let mut remaining: BTreeMap<GrantKey, u64> = state
            .inventory
            .iter()
            .filter(|r| is_service(state, r.good_id, r.unit_id))
            .map(|r| {
                (
                    (AccountId::Site(r.site_id), r.good_id, r.unit_id),
                    r.quantity,
                )
            })
            .collect();
        self.consume_households(state, costs, &mut remaining)?;
        for row in &self.performance {
            remaining
                .entry((row.buyer, row.good_id, row.unit_id))
                .or_default();
        }
        // Canonical order attributes used quantities while carrying costs remain a pooled exact basis.
        let mut performed = BTreeMap::<GrantKey, u64>::new();
        for r in &self.performance {
            let q = performed
                .entry((r.buyer, r.good_id, r.unit_id))
                .or_default();
            *q = q
                .checked_add(r.performed_quantity)
                .ok_or(MaterialCircuitError::Arithmetic)?;
        }
        let mut used = BTreeMap::new();
        for (key, total) in performed {
            let unused = remaining.get(&key).copied().unwrap_or(0);
            used.insert(
                key,
                total
                    .checked_sub(unused)
                    .ok_or(MaterialCircuitError::ServiceInvariant)?,
            );
            costs.expire_service(key, unused)?;
        }
        for r in &mut self.performance {
            let q = used
                .get_mut(&(r.buyer, r.good_id, r.unit_id))
                .ok_or(MaterialCircuitError::ServiceInvariant)?;
            r.used_quantity = (*q).min(r.performed_quantity);
            *q -= r.used_quantity;
            r.unused_quantity = r.performed_quantity - r.used_quantity;
        }
        let services: std::collections::BTreeSet<_> = state
            .commodities
            .iter()
            .filter(|r| matches!(r.kind, CommodityKind::PeriodService { .. }))
            .map(|r| (r.good_id, r.unit_id))
            .collect();
        state
            .inventory
            .retain(|r| !services.contains(&(r.good_id, r.unit_id)));
        costs.clear_service_rows(&services)?;
        state
            .service_orders
            .retain(|r| r.performance_period != state.period);
        Ok(())
    }
    fn consume_households(
        &mut self,
        state: &MaterialCircuitState,
        costs: &mut CostClose,
        remaining: &mut BTreeMap<GrantKey, u64>,
    ) -> Result<()> {
        let CircuitAccounting::Monetary(e) = &state.accounting else {
            return Ok(());
        };
        let mut controlled = std::collections::BTreeSet::new();
        if let Some(r) = &e.recurring {
            for need in &r.household_needs {
                if !is_service(state, need.good_id, need.unit_id) {
                    continue;
                }
                let people = r
                    .households
                    .iter()
                    .find(|r| r.principal_id == need.principal_id)
                    .ok_or(MaterialCircuitError::FinalDemandInvariant)?
                    .persons;
                let required = people
                    .checked_mul(need.units_per_person)
                    .ok_or(MaterialCircuitError::Arithmetic)?;
                let key = (
                    AccountId::Household(need.principal_id),
                    need.good_id,
                    need.unit_id,
                );
                let available = self.households.get(&key).copied().unwrap_or(0);
                let used = available.min(required);
                costs.consume_service(key, available, used, false)?;
                remaining.insert(key, available - used);
                controlled.insert(key);
                self.household.push(HouseholdServiceReceipt {
                    period: state.period,
                    principal_id: need.principal_id,
                    good_id: need.good_id,
                    unit_id: need.unit_id,
                    required_quantity: required,
                    performed_quantity: available,
                    satisfied_quantity: used,
                    unmet_quantity: required - used,
                    unused_quantity: available - used,
                });
            }
        }
        for (&key, &available) in &self.households {
            if !controlled.contains(&key) {
                costs.consume_service(key, available, available, true)?;
                remaining.insert(key, 0);
            }
        }
        self.household
            .sort_by_key(|r| (r.principal_id, r.good_id, r.unit_id));
        Ok(())
    }
    pub(crate) fn plan(
        &mut self,
        state: &mut MaterialCircuitState,
        next_period: u64,
    ) -> Result<()> {
        super::market::update(state, &self.performance, &mut self.markets, next_period)
    }
}
