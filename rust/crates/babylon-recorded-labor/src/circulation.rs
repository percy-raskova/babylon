//! Recorded commercial lots and retail deliveries; destination credits follow the physical phases.
use crate::book::{Frame, Handed, Result};
use crate::model::{
    LaborBasis, LaborDisposition, LaborNode, LaborReceiptFamily, ReceiptRef, RecordedLaborError,
};
use crate::view::{PeriodView, ReceiptView};
use babylon_material_circuit::{
    CircuitAccounting, MaterialCatalog, MerchantHandlingReceipt, OrderId, OutboundOrderId, SiteId,
    UnitId,
};
use std::collections::{BTreeMap, BTreeSet};

/// Freight lots whose stage ends this period are lost in part, or arrive.
///
/// # Errors
/// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
pub fn freight_arrivals(frame: &mut Frame, view: &PeriodView<'_>) -> Result<()> {
    let closing: BTreeSet<_> = view.after.freight.iter().map(|lot| lot.lot_id).collect();
    let mut losses: BTreeMap<_, _> = view
        .receipts
        .losses
        .iter()
        .enumerate()
        .map(|(i, loss)| (loss.lot_id, (i, loss)))
        .collect();
    let mut arrivals = view.receipts.arrivals.iter().enumerate();
    if losses.len() != view.receipts.losses.len() {
        return Err(RecordedLaborError::ReceiptMismatch("losses"));
    }
    for lot in &view.before.freight {
        if lot.stage_arrival_period != view.period {
            continue;
        }
        let node = LaborNode::freight(lot.lot_id);
        if let Some((i, loss)) = losses.remove(&lot.lot_id) {
            if loss.order_id != lot.order_id
                || loss.route_id != lot.route_id
                || loss.stage_index != lot.current_stage_index
            {
                return Err(RecordedLaborError::ReceiptMismatch("losses"));
            }
            frame.release(
                node,
                LaborNode::sink(LaborDisposition::FreightLoss),
                loss.quantity,
                ReceiptRef::new(LaborReceiptFamily::Losses, i),
            )?;
        }
        let retained = frame.quantity(node);
        if retained == 0 || closing.contains(&lot.lot_id) {
            continue;
        }
        let (i, arrival) = arrivals
            .next()
            .ok_or(RecordedLaborError::ReceiptMismatch("arrivals"))?;
        if arrival.order_id != lot.order_id || arrival.quantity != retained {
            return Err(RecordedLaborError::ReceiptMismatch("arrivals"));
        }
        frame.move_units(
            node,
            LaborNode::site(lot.destination_site_id, lot.good_id, lot.unit_id),
            retained,
            ReceiptRef::new(LaborReceiptFamily::Arrivals, i),
        )?;
    }
    if !losses.is_empty() || arrivals.next().is_some() {
        return Err(RecordedLaborError::ReceiptMismatch("freight"));
    }
    Ok(())
}

/// One move out of a site: `to` is where the fold books it, `receiver` is the node that receives the stock.
#[derive(Clone, Copy)]
pub(crate) struct Handoff {
    pub(crate) order: OutboundOrderId,
    pub(crate) site: SiteId,
    pub(crate) from: LaborNode,
    pub(crate) to: LaborNode,
    pub(crate) receiver: LaborNode,
    pub(crate) qty: u64,
    pub(crate) reference: ReceiptRef,
}
impl Handoff {
    /// The basis of the move, with the handling hours added, written as handed over.
    pub(crate) fn debit(
        self,
        frame: &mut Frame,
        handling: &mut Handling<'_>,
    ) -> Result<LaborBasis> {
        let basis = self.take(frame, handling)?;
        if self.qty > 0 {
            frame.handed.push(Handed {
                receipt: self.reference,
                from: self.from,
                to: self.receiver,
                quantity: self.qty,
                basis,
            });
        }
        Ok(basis)
    }

    fn take(self, frame: &mut Frame, handling: &mut Handling<'_>) -> Result<LaborBasis> {
        let basis = frame.take(self.from, self.qty)?;
        frame.edge(self.from, self.to, self.qty, basis, self.reference);
        let Some((ordinal, row)) = handling.rows.remove(&self.order) else {
            if handling.units.contains_key(&self.site) {
                return Err(RecordedLaborError::ReceiptMismatch("missing handling"));
            }
            return Ok(basis);
        };
        if row.handled_quantity != self.qty || row.site_id != self.site {
            return Err(RecordedLaborError::ReceiptMismatch("handling"));
        }
        let unit = handling
            .units
            .get(&row.site_id)
            .ok_or(RecordedLaborError::InvalidAttendance)?;
        let direct = frame.direct(
            LaborNode::work(row.site_id, *unit),
            self.to,
            row.used_hours,
            ReceiptRef::new(LaborReceiptFamily::Handling, ordinal),
        )?;
        basis.add(direct)
    }
}

pub(crate) struct Handling<'a> {
    pub(crate) units: BTreeMap<SiteId, UnitId>,
    pub(crate) rows: BTreeMap<OutboundOrderId, (usize, &'a MerchantHandlingReceipt)>,
}
impl<'a> Handling<'a> {
    fn new(catalog: &MaterialCatalog, receipts: &ReceiptView<'a>) -> Result<Self> {
        let units = catalog
            .merchants
            .iter()
            .map(|row| (row.site_id, row.labor_unit_id))
            .collect();
        let mut rows = BTreeMap::new();
        for (ordinal, row) in receipts.handling.iter().enumerate() {
            if row.handled_quantity == 0 {
                if row.used_hours != 0 {
                    return Err(RecordedLaborError::InvalidAttendance);
                }
            } else if rows.insert(row.order, (ordinal, row)).is_some() {
                return Err(RecordedLaborError::ReceiptMismatch("duplicate handling"));
            }
        }
        Ok(Self { units, rows })
    }
}

fn suppliers(view: &PeriodView<'_>) -> Result<BTreeMap<OrderId, Handoff>> {
    let lots: BTreeMap<_, _> = view.after.freight.iter().map(|l| (l.lot_id, l)).collect();
    let mut supplies = BTreeMap::new();
    for (i, row) in view.receipts.dispatches.iter().enumerate() {
        let lot = lots
            .get(&row.lot_id)
            .ok_or(RecordedLaborError::ReceiptMismatch("dispatches"))?;
        if lot.dispatch_period != view.period
            || lot.order_id != row.order_id
            || lot.quantity != row.quantity
            || lot.route_id != row.route_id
        {
            return Err(RecordedLaborError::ReceiptMismatch("dispatches"));
        }
        let m = Handoff {
            order: OutboundOrderId::Delivery(row.order_id),
            site: lot.source_site_id,
            from: LaborNode::site(lot.source_site_id, lot.good_id, lot.unit_id),
            to: LaborNode::freight(lot.lot_id),
            receiver: LaborNode::freight(lot.lot_id),
            qty: row.quantity,
            reference: ReceiptRef::new(LaborReceiptFamily::Dispatches, i),
        };
        if supplies.insert(row.order_id, m).is_some() {
            return Err(RecordedLaborError::ReceiptMismatch("dispatches"));
        }
    }
    for (i, row) in view.receipts.local_transfers.iter().enumerate() {
        let m = Handoff {
            order: OutboundOrderId::Delivery(row.order_id),
            site: row.supplier_site_id,
            from: LaborNode::site(row.supplier_site_id, row.good_id, row.unit_id),
            to: LaborNode::site(row.buyer_site_id, row.good_id, row.unit_id),
            receiver: LaborNode::site(row.buyer_site_id, row.good_id, row.unit_id),
            qty: row.quantity,
            reference: ReceiptRef::new(LaborReceiptFamily::LocalTransfers, i),
        };
        if supplies.insert(row.order_id, m).is_some() {
            return Err(RecordedLaborError::ReceiptMismatch("local_transfers"));
        }
    }
    Ok(supplies)
}
/// Deliveries, local transfers and retail fulfillments leave their sites, with their handling hours.
///
/// # Errors
/// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
pub fn outbound(frame: &mut Frame, catalog: &MaterialCatalog, view: &PeriodView<'_>) -> Result<()> {
    let supplies = suppliers(view)?;
    let mut handling = Handling::new(catalog, &view.receipts)?;
    let new: BTreeSet<_> = view
        .receipts
        .procurement
        .iter()
        .filter(|p| p.admitted_quantity > 0)
        .map(|p| p.order_id)
        .collect();
    let mut credits = Vec::with_capacity(supplies.len());
    let mut later = Vec::new();
    for (order, handoff) in supplies {
        if new.contains(&order) {
            later.push(handoff);
        } else {
            credits.push((handoff, handoff.debit(frame, &mut handling)?));
        }
    }
    let mut pantry = BTreeSet::new();
    if let CircuitAccounting::Monetary(e) = &view.before.accounting {
        if let Some(recurring) = &e.recurring {
            pantry.extend(
                recurring
                    .household_stocks
                    .iter()
                    .map(|s| LaborNode::household(s.principal_id, s.good_id, s.unit_id)),
            );
        }
    }
    for (i, row) in view.receipts.local_fulfillments.iter().enumerate() {
        let source = LaborNode::site(row.retailer_site_id, row.good_id, row.unit_id);
        let target = LaborNode::household(row.demand_principal_id, row.good_id, row.unit_id);
        let receipt = ReceiptRef::new(LaborReceiptFamily::LocalFulfillments, i);
        let tracked = pantry.contains(&target);
        let dest = if tracked {
            target
        } else {
            LaborNode::sink(LaborDisposition::FinalDemandOutlay)
        };
        let handoff = Handoff {
            order: OutboundOrderId::LocalFinalDemand(row.order_id),
            site: row.retailer_site_id,
            from: source,
            to: dest,
            receiver: target,
            qty: row.quantity,
            reference: receipt,
        };
        let basis = handoff.debit(frame, &mut handling)?;
        if tracked {
            frame.credit(dest, row.quantity, basis)?;
        } else {
            frame.release_basis(basis)?;
        }
    }
    for handoff in later {
        credits.push((handoff, handoff.debit(frame, &mut handling)?));
    }
    if !handling.rows.is_empty() {
        return Err(RecordedLaborError::ReceiptMismatch("unassigned handling"));
    }
    for (handoff, basis) in credits {
        frame.credit(handoff.to, handoff.qty, basis)?;
    }
    Ok(())
}

/// Households consume their stock.
///
/// # Errors
/// A receipt that does not match the stock, or an arithmetic overflow: `RecordedLaborError`.
pub fn consume(frame: &mut Frame, view: &PeriodView<'_>) -> Result<()> {
    for (i, row) in view.receipts.household_consumption.iter().enumerate() {
        let stock = LaborNode::household(row.principal_id, row.good_id, row.unit_id);
        if row.period != view.period || frame.quantity(stock) != row.available_quantity {
            return Err(RecordedLaborError::ReceiptMismatch("household_consumption"));
        }
        frame.release(
            stock,
            LaborNode::sink(LaborDisposition::HouseholdConsumption),
            row.consumed_quantity,
            ReceiptRef::new(LaborReceiptFamily::HouseholdConsumption, i),
        )?;
        if frame.quantity(stock) != row.closing_quantity {
            return Err(RecordedLaborError::ReceiptMismatch("household_consumption"));
        }
    }
    Ok(())
}
