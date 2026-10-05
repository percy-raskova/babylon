//! Independent trade evidence over the complete authenticated national boundary.
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    recurring_procurement_order_id, AccountId, MoneyLocation, MoneyTransferPurpose,
    MoneyTransferReceipt, OrderId, OutboundOrderId, SiteId, MAX_DELIVERY_ORDERS,
};
use babylon_persistence::production_observation::ProductionSite;
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, PartialEq, Eq)]
pub(super) enum Refusal {
    Period,
    SiteIdentity,
    MissingSite,
    ProcurementIdentity,
    DuplicateOrder,
    Quantity,
    Reservation,
    Settlement,
    Refund,
    Overflow,
    PendingLimit,
}

#[derive(Clone, Copy)]
enum Direction {
    Import,
    Export,
}

#[derive(Clone)]
struct Terms {
    supplier: SiteId,
    buyer: SiteId,
    direction: Direction,
    price: i128,
    remaining: u64,
}

#[derive(Clone, Default)]
struct Totals {
    deliveries: u64,
    cash: i128,
}
impl Totals {
    fn add(&mut self, cash: i128) -> Result<(), Refusal> {
        self.deliveries = self.deliveries.checked_add(1).ok_or(Refusal::Overflow)?;
        self.cash = self.cash.checked_add(cash).ok_or(Refusal::Overflow)?;
        Ok(())
    }
    fn value(&self) -> serde_json::Value {
        serde_json::json!({"settled_deliveries":self.deliveries,"settled_cash_micros":self.cash.to_string()})
    }
}

#[derive(Default)]
struct Movement {
    delivered: u64,
    realized: u64,
    lost: u64,
    reserved: i128,
    settled: i128,
    refunded: i128,
}

enum Payment {
    Reservation,
    Settlement,
    Refund,
}

type Locations<'a> = BTreeMap<&'a str, EconomicLocation>;
type Orders = BTreeMap<OrderId, Terms>;

#[derive(Default)]
pub(super) struct Audit {
    period: u64,
    pending: Orders,
    imports: Totals,
    exports: Totals,
    foreign_production: u64,
    foreign_sites: BTreeSet<SiteId>,
}

impl Audit {
    /// The caller has already admitted the complete committed receipt identity.
    /// A refusal leaves the accumulated proof unchanged; no whole-world cache is added.
    pub(super) fn read(
        &mut self,
        receipts: &MaterialTickReceipts,
        sites: &[ProductionSite],
    ) -> Result<serde_json::Value, Refusal> {
        if self.period.checked_add(1) != Some(receipts.resolve_tick) {
            return Err(Refusal::Period);
        }
        let locations = locations(sites)?;
        let admitted = new_orders(receipts, &locations, &self.pending)?;
        let movements = movements(receipts, &self.pending, &admitted)?;
        let (changes, imports, exports) = reconcile(&self.pending, &admitted, &movements)?;
        let (production, productive_sites) = production(receipts, &locations)?;
        let retired = changes
            .values()
            .filter(|remaining| **remaining == 0)
            .count();
        let pending_count = self
            .pending
            .len()
            .checked_add(admitted.len())
            .and_then(|total| total.checked_sub(retired))
            .ok_or(Refusal::Overflow)?;
        if pending_count > MAX_DELIVERY_ORDERS {
            return Err(Refusal::PendingLimit);
        }
        let next_imports = accumulated(&self.imports, &imports)?;
        let next_exports = accumulated(&self.exports, &exports)?;
        let next_production = self
            .foreign_production
            .checked_add(production)
            .ok_or(Refusal::Overflow)?;
        let fact = serde_json::json!({"period":receipts.resolve_tick,
            "imports":imports.value(),"exports":exports.value(),
            "positive_foreign_production_receipts":production,
            "productive_foreign_sites":productive_sites.len(),"unresolved_trade_orders":pending_count});
        self.pending.extend(admitted);
        for (id, remaining) in changes {
            if remaining == 0 {
                self.pending.remove(&id);
            } else {
                self.pending.get_mut(&id).unwrap().remaining = remaining;
            }
        }
        self.imports = next_imports;
        self.exports = next_exports;
        self.foreign_production = next_production;
        self.foreign_sites.extend(productive_sites);
        self.period = receipts.resolve_tick;
        Ok(fact)
    }

    pub(super) fn report(&self) -> serde_json::Value {
        let passed = self.imports.deliveries > 0
            && self.exports.deliveries > 0
            && self.foreign_production > 0;
        serde_json::json!({"version":1,"status":if passed {"passed"} else {"incomplete"},
            "periods":self.period,"basis":"committed_recurring_procurement_delivery_realization_and_exact_settlement",
            "imports":self.imports.value(),"exports":self.exports.value(),
            "positive_foreign_production_receipts":self.foreign_production,
            "productive_foreign_sites":self.foreign_sites.len(),"unresolved_trade_orders":self.pending.len()})
    }
}

fn accumulated(before: &Totals, delta: &Totals) -> Result<Totals, Refusal> {
    Ok(Totals {
        deliveries: before
            .deliveries
            .checked_add(delta.deliveries)
            .ok_or(Refusal::Overflow)?,
        cash: before
            .cash
            .checked_add(delta.cash)
            .ok_or(Refusal::Overflow)?,
    })
}

fn locations(sites: &[ProductionSite]) -> Result<Locations<'_>, Refusal> {
    let mut result = BTreeMap::new();
    for site in sites {
        if site.id.len() != 64
            || !site
                .id
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
            || result.insert(site.id.as_str(), site.location).is_some()
        {
            return Err(Refusal::SiteIdentity);
        }
    }
    Ok(result)
}

fn location(locations: &Locations<'_>, site: SiteId) -> Result<EconomicLocation, Refusal> {
    locations
        .get(hex(&site.as_bytes()).as_str())
        .copied()
        .ok_or(Refusal::MissingSite)
}

fn direction(supplier: EconomicLocation, buyer: EconomicLocation) -> Option<Direction> {
    match (supplier, buyer) {
        (EconomicLocation::County(_), EconomicLocation::Foreign(_)) => Some(Direction::Export),
        (EconomicLocation::Foreign(_), EconomicLocation::County(_)) => Some(Direction::Import),
        _ => None,
    }
}

fn new_orders(
    receipts: &MaterialTickReceipts,
    sites: &Locations<'_>,
    pending: &Orders,
) -> Result<Orders, Refusal> {
    let mut result = Orders::new();
    let mut seen = BTreeSet::new();
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
            return Err(Refusal::ProcurementIdentity);
        }
        if !seen.insert(row.order_id) || pending.contains_key(&row.order_id) {
            return Err(Refusal::DuplicateOrder);
        }
        if row.admitted_quantity > row.desired_quantity {
            return Err(Refusal::Quantity);
        }
        let relation = direction(
            location(sites, row.supplier_site_id)?,
            location(sites, row.buyer_site_id)?,
        );
        let Some(direction) = relation.filter(|_| row.admitted_quantity > 0) else {
            continue;
        };
        let price = row.unit_price.micro_units();
        if price <= 0 {
            return Err(Refusal::Reservation);
        }
        result.insert(
            row.order_id,
            Terms {
                supplier: row.supplier_site_id,
                buyer: row.buyer_site_id,
                direction,
                price,
                remaining: row.admitted_quantity,
            },
        );
    }
    Ok(result)
}

fn terms<'a>(pending: &'a Orders, admitted: &'a Orders, id: &OrderId) -> Option<&'a Terms> {
    admitted.get(id).or_else(|| pending.get(id))
}

fn add_quantity(target: &mut u64, quantity: u64) -> Result<(), Refusal> {
    if quantity == 0 {
        return Err(Refusal::Quantity);
    }
    *target = target.checked_add(quantity).ok_or(Refusal::Overflow)?;
    Ok(())
}

fn movements(
    receipts: &MaterialTickReceipts,
    pending: &Orders,
    admitted: &Orders,
) -> Result<BTreeMap<OrderId, Movement>, Refusal> {
    let mut result: BTreeMap<OrderId, Movement> = BTreeMap::new();
    for id in admitted.keys() {
        result.entry(*id).or_default();
    }
    for row in &receipts.deliveries {
        if terms(pending, admitted, &row.order_id).is_some() {
            add_quantity(
                &mut result.entry(row.order_id).or_default().delivered,
                row.quantity,
            )?;
        }
    }
    for row in &receipts.realizations {
        if terms(pending, admitted, &row.order_id).is_some() {
            add_quantity(
                &mut result.entry(row.order_id).or_default().realized,
                row.quantity,
            )?;
        }
    }
    for row in &receipts.losses {
        if terms(pending, admitted, &row.order_id).is_some() {
            add_quantity(
                &mut result.entry(row.order_id).or_default().lost,
                row.quantity,
            )?;
        }
    }
    for row in &receipts.money_transfers {
        money(row, pending, admitted, &mut result)?;
    }
    Ok(result)
}

fn money(
    row: &MoneyTransferReceipt,
    pending: &Orders,
    admitted: &Orders,
    movements: &mut BTreeMap<OrderId, Movement>,
) -> Result<(), Refusal> {
    let (id, kind) = match row.purpose {
        MoneyTransferPurpose::PurchaseReservation(OutboundOrderId::Delivery(id)) => {
            (id, Payment::Reservation)
        }
        MoneyTransferPurpose::DeliverySettlement(OutboundOrderId::Delivery(id)) => {
            (id, Payment::Settlement)
        }
        MoneyTransferPurpose::PurchaseRefund(OutboundOrderId::Delivery(id)) => {
            (id, Payment::Refund)
        }
        _ => return Ok(()),
    };
    let Some(order) = terms(pending, admitted, &id) else {
        return Ok(());
    };
    let reserve = MoneyLocation::PurchaseReserve(OutboundOrderId::Delivery(id));
    let (debit, credit, refusal) = match kind {
        Payment::Reservation => (
            MoneyLocation::Cash(AccountId::Site(order.buyer)),
            reserve,
            Refusal::Reservation,
        ),
        Payment::Settlement => (
            reserve,
            MoneyLocation::Cash(AccountId::Site(order.supplier)),
            Refusal::Settlement,
        ),
        Payment::Refund => (
            reserve,
            MoneyLocation::Cash(AccountId::Site(order.buyer)),
            Refusal::Refund,
        ),
    };
    let amount = row.credit.delta.micro_units();
    if amount <= 0
        || row.debit.location != debit
        || row.credit.location != credit
        || row.debit.delta.micro_units() != amount.checked_neg().ok_or(Refusal::Overflow)?
    {
        return Err(refusal);
    }
    let movement = movements.entry(id).or_default();
    let target = match kind {
        Payment::Reservation => &mut movement.reserved,
        Payment::Settlement => &mut movement.settled,
        Payment::Refund => &mut movement.refunded,
    };
    *target = target.checked_add(amount).ok_or(Refusal::Overflow)?;
    Ok(())
}

type Reconciliation = (BTreeMap<OrderId, u64>, Totals, Totals);
fn reconcile(
    pending: &Orders,
    admitted: &Orders,
    movements: &BTreeMap<OrderId, Movement>,
) -> Result<Reconciliation, Refusal> {
    let mut changes = BTreeMap::new();
    let mut imports = Totals::default();
    let mut exports = Totals::default();
    for (id, movement) in movements {
        let order = terms(pending, admitted, id).unwrap();
        let reservation = if admitted.contains_key(id) {
            value(order.remaining, order.price)?
        } else {
            0
        };
        if movement.reserved != reservation {
            return Err(Refusal::Reservation);
        }
        if movement.delivered != movement.realized {
            return Err(Refusal::Quantity);
        }
        if movement.settled != value(movement.delivered, order.price)? {
            return Err(Refusal::Settlement);
        }
        if movement.refunded != value(movement.lost, order.price)? {
            return Err(Refusal::Refund);
        }
        let closed = movement
            .delivered
            .checked_add(movement.lost)
            .ok_or(Refusal::Overflow)?;
        let remaining = order
            .remaining
            .checked_sub(closed)
            .ok_or(Refusal::Quantity)?;
        changes.insert(*id, remaining);
        if movement.delivered > 0 {
            match order.direction {
                Direction::Import => imports.add(movement.settled)?,
                Direction::Export => exports.add(movement.settled)?,
            }
        }
    }
    Ok((changes, imports, exports))
}

fn value(quantity: u64, price: i128) -> Result<i128, Refusal> {
    i128::from(quantity)
        .checked_mul(price)
        .ok_or(Refusal::Overflow)
}

fn production(
    receipts: &MaterialTickReceipts,
    sites: &Locations<'_>,
) -> Result<(u64, BTreeSet<SiteId>), Refusal> {
    let mut count = 0_u64;
    let mut productive_sites = BTreeSet::new();
    for row in &receipts.production {
        if row.produced_batches > row.planned_batches {
            return Err(Refusal::Quantity);
        }
        if matches!(location(sites, row.site_id)?, EconomicLocation::Foreign(_))
            && row.produced_batches > 0
        {
            count = count.checked_add(1).ok_or(Refusal::Overflow)?;
            productive_sites.insert(row.site_id);
        }
    }
    Ok((count, productive_sites))
}

pub(super) fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    let mut result = String::with_capacity(bytes.len().checked_mul(2).unwrap());
    for byte in bytes {
        write!(&mut result, "{byte:02x}").unwrap();
    }
    result
}
