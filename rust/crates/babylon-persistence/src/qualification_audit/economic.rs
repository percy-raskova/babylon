//! Compact evidence from already authenticated receipts; never simulation authority.
use babylon_material_circuit::{
    AccountId, AidOutcome, CapitalContributionReceipt, CashTransferPurpose, DistributionReceipt,
    EquipmentWearReceipt, FinalDemandPrincipalId, GoodId, HouseholdConsumptionReceipt,
    HouseholdDemandReceipt, InstallationId, InstallationReceipt, InvestmentReceipt, MoneyLocation,
    MoneyTransferPurpose, MoneyTransferReceipt, OrderId, OutboundOrderId, PriceDecision,
    PriceReceipt, ProcessId, ProcurementReceipt, ProductionReceipt, ShiftId, SiteId, UnitId,
    WageAccrualReceipt, MAX_DELIVERY_ORDERS,
};
use babylon_tick::material_world::MaterialTickReceipts;
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};
use std::result::Result as StdResult;

const WITNESSES: usize = 8;
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Refusal {
    Period,
    Duplicate,
    Quantity,
    Unit,
    Payment,
    Wage,
    Procurement,
    Ownership,
    Equipment,
    Price,
    Overflow,
    PendingLimit,
}
type Result<T> = StdResult<T, Refusal>;
fn add(a: &mut u64, b: u64) -> Result<()> {
    *a = a.checked_add(b).ok_or(Refusal::Overflow)?;
    Ok(())
}
fn cash(a: &mut i128, b: i128) -> Result<()> {
    *a = a.checked_add(b).ok_or(Refusal::Overflow)?;
    Ok(())
}
fn value(q: u64, p: i128) -> Result<i128> {
    i128::from(q).checked_mul(p).ok_or(Refusal::Overflow)
}
fn hex(bytes: &[u8]) -> String {
    use std::fmt::Write;
    let mut result = String::with_capacity(
        bytes
            .len()
            .checked_mul(2)
            .expect("the hex length fits the host address space"),
    );
    for byte in bytes {
        write!(&mut result, "{byte:02x}").expect("writing to a String cannot fail");
    }
    result
}

type QuantityTotals = BTreeMap<(GoodId, UnitId), NativeQuantity>;
type DemandIndex<'a> =
    BTreeMap<(FinalDemandPrincipalId, GoodId, UnitId), &'a HouseholdDemandReceipt>;
type PaymentKey = (u8, u8, [u8; 32]);
fn payment_key(purpose: MoneyTransferPurpose) -> Option<PaymentKey> {
    let (tag, order) = match purpose {
        MoneyTransferPurpose::PurchaseReservation(id) => (0, id),
        MoneyTransferPurpose::DeliverySettlement(id) => (1, id),
        MoneyTransferPurpose::PurchaseRefund(id) => (2, id),
        _ => return None,
    };
    match order {
        OutboundOrderId::Delivery(id) => Some((tag, 0, id.as_bytes())),
        OutboundOrderId::LocalFinalDemand(id) => Some((tag, 1, id.as_bytes())),
        OutboundOrderId::Service(_) => None,
    }
}
struct PaymentTotal {
    from: MoneyLocation,
    to: MoneyLocation,
    amount: i128,
}
#[derive(Default)]
struct PeriodIndex {
    payments: BTreeMap<PaymentKey, PaymentTotal>,
    handoffs: BTreeMap<(OrderId, FinalDemandPrincipalId, SiteId, GoodId, UnitId), u64>,
    aid: BTreeMap<(FinalDemandPrincipalId, GoodId, UnitId), u64>,
    arrivals: BTreeMap<OrderId, u64>,
    deliveries: BTreeMap<OrderId, u64>,
    realizations: BTreeMap<OrderId, u64>,
    losses: BTreeMap<OrderId, u64>,
    local: BTreeMap<OrderId, (SiteId, SiteId, GoodId, UnitId, u64)>,
    production: BTreeMap<(SiteId, ProcessId), u64>,
}
impl PeriodIndex {
    fn read(r: &MaterialTickReceipts) -> Result<Self> {
        let mut index = Self::default();
        index.index_payments(&r.money_transfers)?;
        index.index_household(r)?;
        index.index_physical(r)?;
        index.index_production(&r.production)?;
        Ok(index)
    }
    fn index_payments(&mut self, rows: &[MoneyTransferReceipt]) -> Result<()> {
        for t in rows {
            let amount = t.credit.delta.micro_units();
            if amount <= 0
                || t.debit.delta.micro_units() != amount.checked_neg().ok_or(Refusal::Overflow)?
            {
                return Err(Refusal::Payment);
            }
            if let Some(key) = payment_key(t.purpose) {
                let total = self.payments.entry(key).or_insert(PaymentTotal {
                    from: t.debit.location,
                    to: t.credit.location,
                    amount: 0,
                });
                if (total.from, total.to) != (t.debit.location, t.credit.location) {
                    return Err(Refusal::Payment);
                }
                cash(&mut total.amount, amount)?;
            }
        }
        Ok(())
    }
    fn index_household(&mut self, r: &MaterialTickReceipts) -> Result<()> {
        for f in &r.local_fulfillments {
            if f.quantity == 0 {
                return Err(Refusal::Quantity);
            }
            add(
                self.handoffs
                    .entry((
                        f.order_id,
                        f.demand_principal_id,
                        f.retailer_site_id,
                        f.good_id,
                        f.unit_id,
                    ))
                    .or_default(),
                f.quantity,
            )?;
        }
        for a in &r.aid {
            if a.outcome == AidOutcome::Granted {
                add(
                    self.aid
                        .entry((a.recipient, a.good_id, a.unit_id))
                        .or_default(),
                    a.quantity,
                )?;
            }
        }
        Ok(())
    }
    fn index_physical(&mut self, r: &MaterialTickReceipts) -> Result<()> {
        for a in &r.arrivals {
            add(self.arrivals.entry(a.order_id).or_default(), a.quantity)?;
        }
        for a in &r.deliveries {
            add(self.deliveries.entry(a.order_id).or_default(), a.quantity)?;
        }
        for a in &r.realizations {
            add(self.realizations.entry(a.order_id).or_default(), a.quantity)?;
        }
        for a in &r.losses {
            add(self.losses.entry(a.order_id).or_default(), a.quantity)?;
        }
        for a in &r.local_transfers {
            let total = self.local.entry(a.order_id).or_insert((
                a.supplier_site_id,
                a.buyer_site_id,
                a.good_id,
                a.unit_id,
                0,
            ));
            if (total.0, total.1, total.2, total.3)
                != (a.supplier_site_id, a.buyer_site_id, a.good_id, a.unit_id)
            {
                return Err(Refusal::Unit);
            }
            add(&mut total.4, a.quantity)?;
        }
        Ok(())
    }
    fn index_production(&mut self, rows: &[ProductionReceipt]) -> Result<()> {
        for p in rows {
            if p.produced_batches > p.planned_batches {
                return Err(Refusal::Quantity);
            }
            add(
                self.production
                    .entry((p.site_id, p.process_id))
                    .or_default(),
                p.produced_batches,
            )?;
        }
        Ok(())
    }
    fn payment(
        &self,
        purpose: MoneyTransferPurpose,
        from: MoneyLocation,
        to: MoneyLocation,
    ) -> Result<i128> {
        let key = payment_key(purpose).ok_or(Refusal::Payment)?;
        match self.payments.get(&key) {
            None => Ok(0),
            Some(total) if (total.from, total.to) == (from, to) => Ok(total.amount),
            Some(_) => Err(Refusal::Payment),
        }
    }
}
#[derive(Clone, Debug, Default, Serialize, PartialEq, Eq)]
pub struct NativeQuantity {
    pub good_id: String,
    pub unit_id: String,
    pub purchased: u64,
    pub consumed: u64,
    pub unmet: u64,
    pub purchased_consumption_lower_bound: u64,
}
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct PriceWitness {
    pub site_id: String,
    pub good_id: String,
    pub unit_id: String,
    pub reason: &'static str,
    pub old_micros: String,
    pub next_micros: String,
}
#[derive(Clone, Debug, Default, Serialize, PartialEq, Eq)]
pub struct Boundary {
    pub period: u64,
    pub households: Vec<NativeQuantity>,
    pub funded_wages_paid_micros: String,
    pub settled_procurement_orders: u64,
    /// Matched earnings distributions, excluding capital funding into issuers.
    pub ownership_paid_micros: String,
    pub price_reasons: BTreeMap<&'static str, u64>,
    pub responsive_quotes: u64,
    pub price_examples: Vec<PriceWitness>,
    pub completed_equipment_paths: u64,
    pub pending_procurement: usize,
    pub pending_wages: usize,
    pub pending_equipment: usize,
}
#[derive(Debug, Serialize)]
pub struct Summary {
    pub version: u8,
    pub periods: u64,
    pub purchase_consumption_periods: u64,
    pub funded_wage_periods: u64,
    pub procurement_settlement_periods: u64,
    pub responsive_price_periods: u64,
    pub ownership_payment_periods: u64,
    pub equipment_paths: u64,
    pub renewal_status: &'static str,
    pub equipment_status: &'static str,
    pub pending_procurement: usize,
    pub pending_wages: usize,
    pub pending_equipment: usize,
}
#[derive(Clone)]
struct Purchase {
    supplier: SiteId,
    buyer: SiteId,
    native: Option<(GoodId, UnitId)>,
    remaining: u64,
    price: i128,
    equipment: Option<(SiteId, ProcessId)>,
}
#[derive(Clone, Default)]
struct Payroll {
    employer: Option<AccountId>,
    reserve: i128,
    due: i128,
    payee: Option<AccountId>,
}
#[derive(Clone, Default)]
struct Equipment {
    acquired: u64,
}
type AcquiredEquipment = BTreeMap<(SiteId, ProcessId), Equipment>;
#[derive(Clone)]
struct InstallationPath {
    key: (SiteId, ProcessId),
    units: u64,
    remaining: u64,
    worked: u64,
    usable: u64,
}
#[derive(Clone, Default)]
pub struct Audit {
    period: u64,
    purchases: BTreeMap<OrderId, Purchase>,
    payroll: BTreeMap<ShiftId, Payroll>,
    equipment: AcquiredEquipment,
    installations: BTreeMap<InstallationId, InstallationPath>,
    purchase_periods: u64,
    wage_periods: u64,
    procurement_periods: u64,
    price_periods: u64,
    ownership_periods: u64,
    equipment_paths: u64,
}

impl Audit {
    /// Refusal is atomic. Only bounded pending joins are copied, never receipts.
    /// # Errors
    /// Refuses noncontiguous periods, invalid quantities, unmatched payments,
    /// wages, procurement, ownership or equipment, and arithmetic overflow.
    pub fn read(&mut self, rows: &MaterialTickReceipts) -> Result<Boundary> {
        let mut candidate = self.clone();
        let fact = candidate.extend(rows)?;
        *self = candidate;
        Ok(fact)
    }
    #[must_use]
    pub fn summary(&self) -> Summary {
        Summary {
            version: 1,
            periods: self.period,
            purchase_consumption_periods: self.purchase_periods,
            funded_wage_periods: self.wage_periods,
            procurement_settlement_periods: self.procurement_periods,
            responsive_price_periods: self.price_periods,
            ownership_payment_periods: self.ownership_periods,
            equipment_paths: self.equipment_paths,
            renewal_status: if self.purchase_periods > 1
                && self.wage_periods > 1
                && self.procurement_periods > 1
            {
                "observed"
            } else {
                "incomplete"
            },
            equipment_status: if self.equipment_paths > 0 {
                "observed"
            } else {
                "not_observed"
            },
            pending_procurement: self.purchases.len(),
            pending_wages: self.payroll.len(),
            pending_equipment: self.equipment.len() + self.installations.len(),
        }
    }
    fn extend(&mut self, r: &MaterialTickReceipts) -> Result<Boundary> {
        if self.period.checked_add(1) != Some(r.resolve_tick) {
            return Err(Refusal::Period);
        }
        let tick = r.resolve_tick;
        let index = PeriodIndex::read(r)?;
        let mut fact = Boundary {
            period: tick,
            ..Boundary::default()
        };
        self.households(r, &index, &mut fact)?;
        let mut new = BTreeSet::new();
        self.admit_procurement(&r.procurement, tick, &mut new)?;
        self.admit_investment(&r.investment, tick, &mut new)?;
        self.reserve_payroll(&r.money_transfers)?;
        self.accrue_payroll(&r.wage_accruals, tick)?;
        self.pay_payroll(&r.money_transfers, &mut fact)?;
        let local_equipment = self.settle_purchases(&index, &new, &mut fact)?;
        self.ownership(r, &mut fact)?;
        self.prices(&r.prices, tick, &mut fact)?;
        self.install_equipment(&r.installation, tick)?;
        self.use_equipment(&r.equipment_wear, tick, &index, &mut fact)?;
        // Outbound local handoffs occur after production and installation.
        self.credit_equipment(local_equipment)?;
        self.pending_counts(&mut fact)?;
        self.period = tick;
        Ok(fact)
    }
    fn household_orders<'a>(
        rows: &'a [HouseholdDemandReceipt],
        tick: u64,
        index: &PeriodIndex,
        quantities: &mut QuantityTotals,
    ) -> Result<DemandIndex<'a>> {
        let mut demand = BTreeMap::new();
        for row in rows {
            if row.period != tick
                || row.order_id
                    != babylon_material_circuit::recurring_household_order_id(
                        tick,
                        (row.principal_id, row.good_id, row.unit_id),
                    )
                || row.admitted_quantity > row.requested_quantity
                || row.fulfilled_quantity > row.admitted_quantity
                || row.unit_price.micro_units() <= 0
            {
                return Err(Refusal::Quantity);
            }
            if demand
                .insert((row.principal_id, row.good_id, row.unit_id), row)
                .is_some()
            {
                return Err(Refusal::Duplicate);
            }
            let order = OutboundOrderId::LocalFinalDemand(row.order_id);
            let reserve = MoneyLocation::PurchaseReserve(order);
            for (purpose, from, to, quantity) in [
                (
                    MoneyTransferPurpose::PurchaseReservation(order),
                    MoneyLocation::Cash(AccountId::Household(row.principal_id)),
                    reserve,
                    row.admitted_quantity,
                ),
                (
                    MoneyTransferPurpose::DeliverySettlement(order),
                    reserve,
                    MoneyLocation::Cash(AccountId::Site(row.retailer_site_id)),
                    row.fulfilled_quantity,
                ),
                (
                    MoneyTransferPurpose::PurchaseRefund(order),
                    reserve,
                    MoneyLocation::Cash(AccountId::Household(row.principal_id)),
                    row.expired_quantity,
                ),
            ] {
                let actual = index.payment(purpose, from, to)?;
                if actual != value(quantity, row.unit_price.micro_units())? {
                    return Err(Refusal::Payment);
                }
            }
            let q = quantities.entry((row.good_id, row.unit_id)).or_default();
            add(&mut q.purchased, row.fulfilled_quantity)?;
        }
        Ok(demand)
    }
    fn household_consumption(
        rows: &[HouseholdConsumptionReceipt],
        tick: u64,
        index: &PeriodIndex,
        demand: &DemandIndex<'_>,
        quantities: &mut QuantityTotals,
    ) -> Result<()> {
        let mut seen = BTreeSet::new();
        for row in rows {
            if row.period != tick || !seen.insert((row.principal_id, row.good_id, row.unit_id)) {
                return Err(Refusal::Duplicate);
            }
            if row.consumed_quantity.checked_add(row.unmet_quantity) != Some(row.required_quantity)
                || row.consumed_quantity.checked_add(row.closing_quantity)
                    != Some(row.available_quantity)
            {
                return Err(Refusal::Quantity);
            }
            let q = quantities.entry((row.good_id, row.unit_id)).or_default();
            add(&mut q.consumed, row.consumed_quantity)?;
            add(&mut q.unmet, row.unmet_quantity)?;
            if let Some(d) = demand.get(&(row.principal_id, row.good_id, row.unit_id)) {
                // Conservative lower bound: opening stock is consumed before purchases.
                // Aid may also supply goods, so count only matching actual retail handoffs.
                let actual = index
                    .handoffs
                    .get(&(
                        d.order_id,
                        d.principal_id,
                        d.retailer_site_id,
                        d.good_id,
                        d.unit_id,
                    ))
                    .copied()
                    .unwrap_or(0);
                if actual != d.fulfilled_quantity {
                    return Err(Refusal::Unit);
                }
                let aid = index
                    .aid
                    .get(&(row.principal_id, row.good_id, row.unit_id))
                    .copied()
                    .unwrap_or(0);
                let preexisting = d.opening_stock.checked_add(aid).ok_or(Refusal::Overflow)?;
                add(
                    &mut q.purchased_consumption_lower_bound,
                    row.consumed_quantity
                        .saturating_sub(preexisting)
                        .min(actual),
                )?;
            }
        }
        Ok(())
    }
    fn households(
        &mut self,
        r: &MaterialTickReceipts,
        index: &PeriodIndex,
        fact: &mut Boundary,
    ) -> Result<()> {
        let tick = r.resolve_tick;
        let mut quantities = QuantityTotals::new();
        let demand = Self::household_orders(&r.household_demand, tick, index, &mut quantities)?;
        Self::household_consumption(
            &r.household_consumption,
            tick,
            index,
            &demand,
            &mut quantities,
        )?;
        for ((g, u), mut q) in quantities {
            q.good_id = hex(&g.as_bytes());
            q.unit_id = hex(&u.as_bytes());
            fact.households.push(q);
        }
        if fact
            .households
            .iter()
            .any(|q| q.purchased_consumption_lower_bound > 0)
        {
            add(&mut self.purchase_periods, 1)?;
        }

        Ok(())
    }
    fn admit_procurement(
        &mut self,
        rows: &[ProcurementReceipt],
        tick: u64,
        new: &mut BTreeSet<OrderId>,
    ) -> Result<()> {
        for row in rows {
            if row.period != tick
                || row.order_id
                    != babylon_material_circuit::recurring_procurement_order_id(
                        tick,
                        row.buyer_site_id,
                        row.supplier_site_id,
                        row.good_id,
                        row.unit_id,
                    )
                || row.admitted_quantity > row.desired_quantity
            {
                return Err(Refusal::Procurement);
            }
            if row.admitted_quantity == 0 {
                continue;
            }
            if !new.insert(row.order_id)
                || self.purchases.contains_key(&row.order_id)
                || row.unit_price.micro_units() <= 0
            {
                return Err(Refusal::Duplicate);
            }
            self.purchases.insert(
                row.order_id,
                Purchase {
                    supplier: row.supplier_site_id,
                    buyer: row.buyer_site_id,
                    native: Some((row.good_id, row.unit_id)),
                    remaining: row.admitted_quantity,
                    price: row.unit_price.micro_units(),
                    equipment: None,
                },
            );
        }
        Ok(())
    }
    fn admit_investment(
        &mut self,
        rows: &[InvestmentReceipt],
        tick: u64,
        new: &mut BTreeSet<OrderId>,
    ) -> Result<()> {
        for row in rows {
            if row.validate().is_err() {
                return Err(Refusal::Equipment);
            }
            if row.period != tick {
                return Err(Refusal::Period);
            }
            if row.admitted_units == 0 {
                continue;
            }
            if !new.insert(row.order_id)
                || self.purchases.contains_key(&row.order_id)
                || row.unit_price.micro_units() <= 0
            {
                return Err(Refusal::Equipment);
            }
            self.purchases.insert(
                row.order_id,
                Purchase {
                    supplier: row.supplier_site_id,
                    buyer: row.site_id,
                    native: None,
                    remaining: row.admitted_units,
                    price: row.unit_price.micro_units(),
                    equipment: Some((row.site_id, row.process_id)),
                },
            );
        }
        Ok(())
    }
    fn reserve_payroll(&mut self, rows: &[MoneyTransferReceipt]) -> Result<()> {
        for t in rows {
            let amount = t.credit.delta.micro_units();
            if amount <= 0
                || t.debit.delta.micro_units() != amount.checked_neg().ok_or(Refusal::Overflow)?
            {
                return Err(Refusal::Payment);
            }
            match t.purpose {
                MoneyTransferPurpose::ShiftReservation(id) => {
                    let (MoneyLocation::Cash(employer), MoneyLocation::PayrollReserve(target)) =
                        (t.debit.location, t.credit.location)
                    else {
                        return Err(Refusal::Wage);
                    };
                    if id != target {
                        return Err(Refusal::Wage);
                    }
                    let p = self.payroll.entry(id).or_default();
                    if p.employer.is_some_and(|e| e != employer) {
                        return Err(Refusal::Wage);
                    }
                    p.employer = Some(employer);
                    cash(&mut p.reserve, amount)?;
                }
                MoneyTransferPurpose::Cash(kind)
                    if matches!(
                        kind,
                        CashTransferPurpose::OwnershipDistribution
                            | CashTransferPurpose::CapitalContribution
                    ) =>
                {
                    let (MoneyLocation::Cash(from), MoneyLocation::Cash(to)) =
                        (t.debit.location, t.credit.location)
                    else {
                        return Err(Refusal::Ownership);
                    };
                    // CashTransferPurpose lacks Ord; use separate reconciliation below.
                    let _ = (kind, from, to);
                }
                _ => {}
            }
        }
        Ok(())
    }
    fn accrue_payroll(&mut self, rows: &[WageAccrualReceipt], tick: u64) -> Result<()> {
        // Reconcile accruals before payments regardless of receipt-vector ordering.
        let mut accrued = BTreeSet::new();
        for a in rows {
            if !accrued.insert(a.shift) {
                return Err(Refusal::Duplicate);
            }
            if a.period != tick || a.amount.micro_units() <= 0 {
                return Err(Refusal::Wage);
            }
            let p = self.payroll.get_mut(&a.shift).ok_or(Refusal::Wage)?;
            if p.employer != Some(a.employer) || p.payee.is_some_and(|v| v != a.payee) {
                return Err(Refusal::Wage);
            }
            p.payee = Some(a.payee);
            cash(&mut p.due, a.amount.micro_units())?;
            if p.due > p.reserve {
                return Err(Refusal::Wage);
            }
        }
        Ok(())
    }
    fn pay_payroll(&mut self, rows: &[MoneyTransferReceipt], fact: &mut Boundary) -> Result<()> {
        let mut wage_paid = 0i128;
        for t in rows {
            let (id, payment) = match t.purpose {
                MoneyTransferPurpose::WagePayment(id) => (id, true),
                MoneyTransferPurpose::ShiftCancellation(id) => (id, false),
                _ => continue,
            };
            let p = self.payroll.get_mut(&id).ok_or(Refusal::Wage)?;
            let target = if payment { p.payee } else { p.employer }.ok_or(Refusal::Wage)?;
            if t.debit.location != MoneyLocation::PayrollReserve(id)
                || t.credit.location != MoneyLocation::Cash(target)
            {
                return Err(Refusal::Wage);
            }
            let amount = t.credit.delta.micro_units();
            p.reserve = p
                .reserve
                .checked_sub(amount)
                .filter(|v| *v >= 0)
                .ok_or(Refusal::Wage)?;
            if payment {
                p.due = p
                    .due
                    .checked_sub(amount)
                    .filter(|v| *v >= 0)
                    .ok_or(Refusal::Wage)?;
                cash(&mut wage_paid, amount)?;
            } else if p.reserve < p.due {
                return Err(Refusal::Wage);
            }
        }
        self.payroll.retain(|_, p| p.reserve != 0 || p.due != 0);
        fact.funded_wages_paid_micros = wage_paid.to_string();
        if wage_paid > 0 {
            add(&mut self.wage_periods, 1)?;
        }
        Ok(())
    }
    fn settle_purchases(
        &mut self,
        index: &PeriodIndex,
        new: &BTreeSet<OrderId>,
        fact: &mut Boundary,
    ) -> Result<AcquiredEquipment> {
        let mut local_equipment = AcquiredEquipment::new();
        let ids: Vec<_> = self.purchases.keys().copied().collect();
        for id in ids {
            let p = self.purchases.get_mut(&id).ok_or(Refusal::Procurement)?;
            let local = index.local.get(&id);
            if let Some((supplier, buyer, good, unit, _)) = local {
                if (*supplier, *buyer) != (p.supplier, p.buyer)
                    || p.native.is_some_and(|native| native != (*good, *unit))
                {
                    return Err(Refusal::Unit);
                }
            }
            let arrived = index.arrivals.get(&id).copied().unwrap_or(0);
            let routed_delivered = index.deliveries.get(&id).copied().unwrap_or(0);
            let realized = index.realizations.get(&id).copied().unwrap_or(0);
            let lost = index.losses.get(&id).copied().unwrap_or(0);
            if arrived != routed_delivered || routed_delivered != realized {
                return Err(Refusal::Procurement);
            }
            let local_delivered = local.map_or(0, |row| row.4);
            let delivered = routed_delivered
                .checked_add(local_delivered)
                .ok_or(Refusal::Overflow)?;
            let order = OutboundOrderId::Delivery(id);
            let reserve = MoneyLocation::PurchaseReserve(order);
            if index.payment(
                MoneyTransferPurpose::PurchaseReservation(order),
                MoneyLocation::Cash(AccountId::Site(p.buyer)),
                reserve,
            )? != if new.contains(&id) {
                value(p.remaining, p.price)?
            } else {
                0
            } || index.payment(
                MoneyTransferPurpose::DeliverySettlement(order),
                reserve,
                MoneyLocation::Cash(AccountId::Site(p.supplier)),
            )? != value(delivered, p.price)?
                || index.payment(
                    MoneyTransferPurpose::PurchaseRefund(order),
                    reserve,
                    MoneyLocation::Cash(AccountId::Site(p.buyer)),
                )? != value(lost, p.price)?
            {
                return Err(Refusal::Payment);
            }
            p.remaining = p
                .remaining
                .checked_sub(delivered.checked_add(lost).ok_or(Refusal::Overflow)?)
                .ok_or(Refusal::Quantity)?;
            if delivered > 0 {
                if let Some(key) = p.equipment {
                    if routed_delivered > 0 {
                        add(
                            &mut self.equipment.entry(key).or_default().acquired,
                            routed_delivered,
                        )?;
                    }
                    if local_delivered > 0 {
                        add(
                            &mut local_equipment.entry(key).or_default().acquired,
                            local_delivered,
                        )?;
                    }
                } else {
                    add(&mut fact.settled_procurement_orders, 1)?;
                }
            }
        }
        self.purchases.retain(|_, p| p.remaining > 0);
        if fact.settled_procurement_orders > 0 {
            add(&mut self.procurement_periods, 1)?;
        }
        Ok(local_equipment)
    }
    fn credit_equipment(&mut self, rows: AcquiredEquipment) -> Result<()> {
        for (key, row) in rows {
            add(
                &mut self.equipment.entry(key).or_default().acquired,
                row.acquired,
            )?;
        }
        Ok(())
    }
    fn ownership(&mut self, r: &MaterialTickReceipts, fact: &mut Boundary) -> Result<()> {
        let tick = r.resolve_tick;
        babylon_material_circuit::validate_distribution_receipts(&r.distributions)
            .map_err(|_| Refusal::Ownership)?;
        let mut ownership = 0i128;
        // Aggregate exact parties; neither row order nor split payments confer evidence.
        for kind in [
            CashTransferPurpose::OwnershipDistribution,
            CashTransferPurpose::CapitalContribution,
        ] {
            let expected = if kind == CashTransferPurpose::OwnershipDistribution {
                Self::distribution_payments(&r.distributions, tick)?
            } else {
                Self::contribution_payments(&r.contributions, tick)?
            };
            let mut actual = BTreeMap::<(AccountId, AccountId), i128>::new();
            for t in r
                .money_transfers
                .iter()
                .filter(|t| t.purpose == MoneyTransferPurpose::Cash(kind))
            {
                let (MoneyLocation::Cash(from), MoneyLocation::Cash(to)) =
                    (t.debit.location, t.credit.location)
                else {
                    return Err(Refusal::Ownership);
                };
                cash(
                    actual.entry((from, to)).or_default(),
                    t.credit.delta.micro_units(),
                )?;
            }
            if expected != actual {
                return Err(Refusal::Ownership);
            }
            if kind == CashTransferPurpose::OwnershipDistribution {
                for n in actual.values() {
                    cash(&mut ownership, *n)?;
                }
            }
        }
        fact.ownership_paid_micros = ownership.to_string();
        if ownership > 0 {
            add(&mut self.ownership_periods, 1)?;
        }
        Ok(())
    }
    fn distribution_payments(
        rows: &[DistributionReceipt],
        tick: u64,
    ) -> Result<BTreeMap<(AccountId, AccountId), i128>> {
        let mut expected = BTreeMap::new();
        for d in rows {
            if d.period != tick
                || d.shares == 0
                || d.shares > d.total_shares
                || d.paid.micro_units() < 0
                || d.paid.micro_units() > d.declared_total.micro_units()
            {
                return Err(Refusal::Ownership);
            }
            if d.paid.micro_units() > 0 {
                cash(
                    expected
                        .entry((AccountId::Site(d.issuer_site_id), d.beneficiary))
                        .or_default(),
                    d.paid.micro_units(),
                )?;
            }
        }
        Ok(expected)
    }
    fn contribution_payments(
        rows: &[CapitalContributionReceipt],
        tick: u64,
    ) -> Result<BTreeMap<(AccountId, AccountId), i128>> {
        let mut expected = BTreeMap::new();
        for c in rows {
            c.validate().map_err(|_| Refusal::Ownership)?;
            if c.period != tick
                || c.paid.micro_units() < 0
                || c.unfunded.micro_units() < 0
                || c.paid.micro_units().checked_add(c.unfunded.micro_units())
                    != Some(c.requested.micro_units())
            {
                return Err(Refusal::Ownership);
            }
            if c.paid.micro_units() > 0 {
                cash(
                    expected
                        .entry((c.contributor, AccountId::Site(c.issuer_site_id)))
                        .or_default(),
                    c.paid.micro_units(),
                )?;
            }
        }
        Ok(expected)
    }
    fn prices(&mut self, rows: &[PriceReceipt], tick: u64, fact: &mut Boundary) -> Result<()> {
        let mut responsive = false;
        for p in rows {
            if p.period != tick
                || p.old_price.micro_units() <= 0
                || p.next_price.micro_units() <= 0
                || p.cost.unit_cost().is_err()
            {
                return Err(Refusal::Price);
            }
            let reason = match p.reason {
                PriceDecision::Fixed => "fixed",
                PriceDecision::Hold => "hold",
                PriceDecision::UnservedDemand => "unserved_demand",
                PriceDecision::ExcessStock => "excess_stock",
                PriceDecision::CostPressure => "cost_pressure",
            };
            if matches!(p.reason, PriceDecision::Fixed | PriceDecision::Hold)
                && p.old_price != p.next_price
            {
                return Err(Refusal::Price);
            }
            match p.reason {
                PriceDecision::UnservedDemand
                    if p.unserved_quantity == 0 || p.next_price < p.old_price =>
                {
                    return Err(Refusal::Price)
                }
                PriceDecision::ExcessStock if p.next_price > p.old_price => {
                    return Err(Refusal::Price)
                }
                PriceDecision::CostPressure
                    if p.cost
                        .unit_cost()
                        .map_err(|_| Refusal::Price)?
                        .is_none_or(|c| c <= p.old_price)
                        || p.next_price < p.old_price =>
                {
                    return Err(Refusal::Price)
                }
                _ => {}
            }
            if p.old_price != p.next_price {
                responsive = true;
                add(&mut fact.responsive_quotes, 1)?;
            }
            add(fact.price_reasons.entry(reason).or_default(), 1)?;
            if fact.price_examples.len() < WITNESSES {
                fact.price_examples.push(PriceWitness {
                    site_id: hex(&p.site_id.as_bytes()),
                    good_id: hex(&p.good_id.as_bytes()),
                    unit_id: hex(&p.unit_id.as_bytes()),
                    reason,
                    old_micros: p.old_price.micro_units().to_string(),
                    next_micros: p.next_price.micro_units().to_string(),
                });
            }
        }
        if responsive {
            add(&mut self.price_periods, 1)?;
        }
        Ok(())
    }
    fn install_equipment(&mut self, rows: &[InstallationReceipt], tick: u64) -> Result<()> {
        for i in rows {
            if i.validate().is_err() {
                return Err(Refusal::Equipment);
            }
            if i.period != tick
                || i.used_hours.checked_add(i.remaining_hours) != Some(i.opening_hours)
                || (i.remaining_hours == 0
                    && i.usable_from_period != tick.checked_add(1).ok_or(Refusal::Overflow)?)
            {
                return Err(Refusal::Equipment);
            }
            let key = (i.site_id, i.process_id);
            if i.started {
                if self.installations.contains_key(&i.id) {
                    return Err(Refusal::Duplicate);
                }
                // Only post-opening acquired units enter this selected witness set.
                if let Some(e) = self.equipment.get_mut(&key) {
                    if e.acquired >= i.units && i.units > 0 {
                        e.acquired -= i.units;
                        self.installations.insert(
                            i.id,
                            InstallationPath {
                                key,
                                units: i.units,
                                remaining: i.opening_hours,
                                worked: 0,
                                usable: 0,
                            },
                        );
                    }
                }
            }
            if let Some(path) = self.installations.get_mut(&i.id) {
                if path.key != key || path.units != i.units || path.remaining != i.opening_hours {
                    return Err(Refusal::Equipment);
                }
                path.remaining = i.remaining_hours;
                add(&mut path.worked, i.used_hours)?;
                path.usable = i.usable_from_period;
            }
        }
        self.equipment.retain(|_, e| e.acquired > 0);
        Ok(())
    }
    fn use_equipment(
        &mut self,
        rows: &[EquipmentWearReceipt],
        tick: u64,
        index: &PeriodIndex,
        fact: &mut Boundary,
    ) -> Result<()> {
        for wear in rows {
            if wear.period != tick || wear.validate().is_err() {
                return Err(Refusal::Equipment);
            }
            let id = InstallationId::from_bytes(wear.cohort_id.as_bytes());
            if let Some(path) = self.installations.get(&id) {
                if path.key != (wear.site_id, wear.process_id)
                    || path.remaining != 0
                    || path.worked == 0
                    || tick < path.usable
                {
                    return Err(Refusal::Equipment);
                }
                if wear.used_batches > 0 {
                    let production = index
                        .production
                        .get(&(wear.site_id, wear.process_id))
                        .copied()
                        .unwrap_or(0);
                    if production < wear.used_batches {
                        return Err(Refusal::Equipment);
                    }
                    self.installations.remove(&id);
                    add(&mut fact.completed_equipment_paths, 1)?;
                    add(&mut self.equipment_paths, 1)?;
                }
            }
        }
        Ok(())
    }
    fn pending_counts(&self, fact: &mut Boundary) -> Result<()> {
        if self.purchases.len() > MAX_DELIVERY_ORDERS
            || self.payroll.len() > MAX_DELIVERY_ORDERS
            || self.equipment.len() > MAX_DELIVERY_ORDERS
            || self.installations.len() > MAX_DELIVERY_ORDERS
        {
            return Err(Refusal::PendingLimit);
        }
        fact.pending_procurement = self.purchases.len();
        fact.pending_wages = self.payroll.len();
        fact.pending_equipment = self
            .equipment
            .len()
            .checked_add(self.installations.len())
            .ok_or(Refusal::Overflow)?;
        Ok(())
    }
}
