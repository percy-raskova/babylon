//! Cash-limited ordinary purchases; replacement and expansion are decision evidence.
use super::{
    get, InvestmentPolicy, InvestmentReceipt, MaterialCircuitError, MaterialCircuitState,
    ProcessId, ProductiveEquipment, Result,
};
use crate::inventory::InventoryLedger;
use crate::valuation::CostClose;
use crate::{
    AccountId, CircuitAccounting, MonetaryBook, MoneyTransferReceipt, OrderAccessMode, OrderId,
    OrderRow, OutboundOrderId, ProcessOutput, ProductionDemandPolicy, PurchaseEscrow,
};
use babylon_kernel::{content_digest::sha256_of, currency::Currency};
use std::collections::BTreeMap;
/// Stable ordinary equipment-purchase principal for one process and period.
#[must_use]
pub fn equipment_purchase_order_id(period: u64, process: ProcessId) -> OrderId {
    let mut b = b"babylon.equipment-purchase.v1\0".to_vec();
    b.extend_from_slice(&period.to_be_bytes());
    b.extend_from_slice(&process.as_bytes());
    OrderId::from_bytes(sha256_of(&b))
}
fn sum(mut rows: impl Iterator<Item = u64>) -> Result<u64> {
    rows.try_fold(0_u64, |n, v| {
        n.checked_add(v).ok_or(MaterialCircuitError::Arithmetic)
    })
}
fn add<K: Ord>(map: &mut BTreeMap<K, u64>, key: K, value: u64) -> Result<()> {
    let n = map.entry(key).or_default();
    *n = n
        .checked_add(value)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(())
}
struct Evidence {
    stock: InventoryLedger,
    observed_stock: InventoryLedger,
    inbound: InventoryLedger,
    accepted: InventoryLedger,
    pending: BTreeMap<ProcessId, u64>,
    outputs: BTreeMap<ProcessId, ProcessOutput>,
    plans: BTreeMap<ProcessId, ProductionDemandPolicy>,
    offers: BTreeMap<(crate::SiteId, crate::GoodId, crate::UnitId), Currency>,
    earnings: BTreeMap<crate::SiteId, i128>,
}
impl Evidence {
    fn new(state: &MaterialCircuitState, e: &ProductiveEquipment) -> Result<Self> {
        let stock: InventoryLedger = state
            .inventory
            .iter()
            .map(|r| ((r.site_id, r.good_id, r.unit_id), r.quantity))
            .collect();
        let CircuitAccounting::Monetary(m) = &state.accounting else {
            return Err(MaterialCircuitError::EquipmentInvariant);
        };
        let mut result = Self {
            observed_stock: stock.clone(),
            stock,
            inbound: BTreeMap::new(),
            accepted: super::choice::sale_commitments(state)?,
            pending: BTreeMap::new(),
            outputs: state
                .process_outputs
                .iter()
                .map(|r| (r.process_id, r.clone()))
                .collect(),
            plans: m
                .recurring
                .iter()
                .flat_map(|r| r.production.iter())
                .map(|r| (r.process_id, r.clone()))
                .collect(),
            offers: m
                .recurring
                .iter()
                .flat_map(|r| r.offers.iter())
                .map(|r| ((r.site_id, r.good_id, r.unit_id), r.unit_price))
                .collect(),
            earnings: BTreeMap::new(),
        };
        for pending in &e.pending {
            add(&mut result.pending, pending.process_id, pending.units)?;
        }
        for o in &state.orders {
            let pending = o
                .ordered
                .checked_sub(o.delivered)
                .and_then(|n| n.checked_sub(o.lost))
                .ok_or(MaterialCircuitError::EquipmentInvariant)?;
            add(
                &mut result.inbound,
                (o.buyer_site_id, o.good_id, o.unit_id),
                pending,
            )?;
        }
        let mut pledges = result.accepted.clone();
        super::choice::protect_sales(&mut result.stock, &mut pledges);
        super::choice::protect_sales(&mut result.inbound, &mut pledges);
        Ok(result)
    }
    fn position(&mut self, e: &ProductiveEquipment, p: &InvestmentPolicy) -> Result<Position> {
        let (b, d) = e.definition(p.process_id)?;
        let key = (b.site_id, d.equipment_good_id, d.equipment_unit_id);
        let installed = sum(e.cohorts[e.cohorts_for(p.process_id)]
            .iter()
            .map(|c| c.units))?;
        let pending = self.pending.get(&p.process_id).copied().unwrap_or(0);
        let used = installed
            .checked_add(pending)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let planned = self
            .plans
            .get(&p.process_id)
            .map_or(0, |r| r.planned_batches);
        let target = planned
            .div_ceil(d.batches_per_unit_per_period)
            .max(p.replacement_target_units)
            .min(p.maximum_installed_units);
        let need = target.saturating_sub(used);
        let stock = self.stock.entry(key).or_default();
        let on_hand = (*stock).min(need);
        *stock -= on_hand;
        let inbound = self.inbound.entry(key).or_default();
        let incoming = (*inbound).min(need - on_hand);
        *inbound -= incoming;
        let total = used
            .checked_add(on_hand)
            .and_then(|n| n.checked_add(incoming))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        Ok(Position {
            installed,
            pending,
            on_hand,
            incoming,
            total,
        })
    }
}
struct Position {
    installed: u64,
    pending: u64,
    on_hand: u64,
    incoming: u64,
    total: u64,
}
fn decision(
    e: &ProductiveEquipment,
    p: &InvestmentPolicy,
    period: u64,
    evidence: &mut Evidence,
    book: &MonetaryBook,
    costs: &CostClose,
) -> Result<InvestmentReceipt> {
    let (b, d) = e.definition(p.process_id)?;
    let price = *evidence
        .offers
        .get(&(p.supplier_site_id, d.equipment_good_id, d.equipment_unit_id))
        .ok_or(MaterialCircuitError::EquipmentInvariant)?;
    let position = evidence.position(e, p)?;
    let plan = evidence.plans.get(&p.process_id);
    let planned = plan.map_or(0, |r| r.planned_batches);
    let buffer = plan.map_or(0, |r| r.output_buffer);
    let output = evidence
        .outputs
        .get(&p.process_id)
        .ok_or(MaterialCircuitError::EquipmentInvariant)?;
    let key = (b.site_id, output.good_id, output.unit_id);
    let replacement = p
        .replacement_target_units
        .saturating_sub(position.total)
        .min(p.maximum_purchase_per_period);
    let target = planned
        .div_ceil(d.batches_per_unit_per_period)
        .max(p.replacement_target_units)
        .min(p.maximum_installed_units);
    let requested = target
        .saturating_sub(
            position
                .total
                .checked_add(replacement)
                .ok_or(MaterialCircuitError::Arithmetic)?,
        )
        .min(p.maximum_purchase_per_period - replacement);
    let eligible = costs.investment_earnings(b.site_id)?.micro_units();
    let available = evidence.earnings.entry(b.site_id).or_insert(eligible);
    // Bounded bps and positive eligible make each term and their sum <= eligible.
    let fraction = eligible / 10000 * i128::from(p.expansion_earnings_fraction_bps)
        + (eligible % 10000) * i128::from(p.expansion_earnings_fraction_bps) / 10000;
    let budget = (*available).min(fraction);
    let expansion = u64::try_from((budget / price.micro_units()).min(i128::from(requested)))
        .map_err(|_| MaterialCircuitError::Arithmetic)?;
    let cash = book
        .cash(AccountId::Site(b.site_id))?
        .micro_units()
        .saturating_sub(p.cash_floor.micro_units())
        .max(0);
    let desired = replacement
        .checked_add(expansion)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let admitted = u64::try_from((cash / price.micro_units()).min(i128::from(desired)))
        .map_err(|_| MaterialCircuitError::Arithmetic)?;
    *available = available
        .checked_sub(
            i128::from(admitted.saturating_sub(replacement))
                .checked_mul(price.micro_units())
                .ok_or(MaterialCircuitError::Arithmetic)?,
        )
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let row = InvestmentReceipt {
        period,
        order_id: equipment_purchase_order_id(period, p.process_id),
        process_id: p.process_id,
        site_id: b.site_id,
        supplier_site_id: p.supplier_site_id,
        installed_units: position.installed,
        pending_units: position.pending,
        on_hand_units: position.on_hand,
        outstanding_inbound_units: position.incoming,
        captured_plan_batches: planned,
        accepted_output_orders: evidence.accepted.get(&key).copied().unwrap_or(0),
        output_stock: evidence.observed_stock.get(&key).copied().unwrap_or(0),
        output_buffer: buffer,
        replacement_requested_units: replacement,
        expansion_requested_units: expansion,
        admitted_units: admitted,
        unit_price: price,
        free_cash: Currency::from_micro_units(cash),
        earnings_budget: Currency::from_micro_units(budget),
    };
    row.validate()?;
    Ok(row)
}
pub(crate) fn invest(
    state: &mut MaterialCircuitState,
    costs: &CostClose,
    transfers: &mut Vec<MoneyTransferReceipt>,
) -> Result<Vec<InvestmentReceipt>> {
    let Some(e) = get(state).cloned() else {
        return Ok(vec![]);
    };
    if e.investment_policies.is_empty() {
        return Ok(vec![]);
    }
    let mut evidence = Evidence::new(state, &e)?;
    let CircuitAccounting::Monetary(m) = &mut state.accounting else {
        return Err(MaterialCircuitError::EquipmentInvariant);
    };
    let mut receipts = Vec::with_capacity(e.investment_policies.len());
    for p in &e.investment_policies {
        let row = decision(&e, p, state.period, &mut evidence, &m.book, costs)?;
        if row.admitted_units > 0 {
            crate::transition::check_order_principal_limits(
                state
                    .orders
                    .len()
                    .checked_add(1)
                    .ok_or(MaterialCircuitError::Arithmetic)?,
                state.final_demand_orders.len(),
                state.service_orders.len(),
            )?;
            let (_, d) = e.definition(p.process_id)?;
            transfers.push(m.book.reserve_purchase(PurchaseEscrow::new(
                OutboundOrderId::Delivery(row.order_id),
                AccountId::Site(row.site_id),
                AccountId::Site(p.supplier_site_id),
                row.admitted_units,
                row.unit_price,
            )?)?);
            state.orders.push(OrderRow {
                order_id: row.order_id,
                access_mode: OrderAccessMode::CommoditySale,
                buyer_site_id: row.site_id,
                supplier_site_id: p.supplier_site_id,
                good_id: d.equipment_good_id,
                unit_id: d.equipment_unit_id,
                ordered: row.admitted_units,
                shipped: 0,
                lost: 0,
                delivered: 0,
                realized: 0,
            });
        }
        receipts.push(row);
    }
    state.orders.sort_by_key(|o| o.order_id);
    Ok(receipts)
}
