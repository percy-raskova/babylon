//! Terminal-window production evidence over authenticated state and receipts.
//! Bounds describe fungible custody in aggregate, never FIFO or individual lots.
use babylon_material_circuit::{
    AccountId, AidOutcome, CapacitySupply, CircuitAccounting, CommodityKind,
    FinalDemandPrincipalId, GoodId, HouseholdConsumptionReceipt, HouseholdDemandReceipt,
    MaterialCircuitState, MoneyLocation, MoneyTransferPurpose, MoneyTransferReceipt, OrderId,
    OutboundOrderId, ProcessId, ProcurementReceipt, ProductionReceipt, RollingProcessSupply,
    SiteId, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write;
use std::result::Result as StdResult;

const MAX_PRODUCERS: usize = 8;
const MAX_OUTPUT_RECIPES: usize = 8;
const MAX_HOUSEHOLDS: usize = 64;
const MAX_PENDING: usize = 4096;
type Native = (GoodId, UnitId);
type Group = (SiteId, GoodId, UnitId);
type Result<T> = StdResult<T, Refusal>;
#[derive(Debug, PartialEq, Eq)]
pub enum Refusal {
    SeedPeriod,
    Period,
    Duplicate,
    Identity,
    Quantity,
    Unit,
    Payment,
    Overflow,
    PendingLimit,
}
fn add(n: &mut u64, q: u64) -> Result<()> {
    *n = n.checked_add(q).ok_or(Refusal::Overflow)?;
    Ok(())
}
fn amount(q: u64, p: i128) -> Result<i128> {
    i128::from(q).checked_mul(p).ok_or(Refusal::Overflow)
}
fn hex(bytes: &[u8]) -> String {
    let mut encoded = String::with_capacity(bytes.len().saturating_mul(2));
    for byte in bytes {
        write!(&mut encoded, "{byte:02x}").expect("writing to String cannot fail");
    }
    encoded
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct OutputBasis {
    pub site_id: String,
    pub process_id: String,
    pub quantity_per_batch: u64,
}
#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
pub struct Selection {
    pub retailer: String,
    pub producers: Vec<String>,
    pub households: Vec<String>,
    pub good_id: String,
    pub unit_id: String,
    pub direct_producer_retailer: bool,
    pub output_basis: Vec<OutputBasis>,
}
#[derive(Debug, Serialize, PartialEq, Eq)]
pub struct Evidence {
    pub version: u8,
    pub seed_period: u64,
    pub seed_register_sha256: String,
    pub through_period: u64,
    pub selection: Option<Selection>,
    pub status: &'static str,
    pub produced: u64,
    pub producer_paid_deliveries: u64,
    pub proven_producer_supply: u64,
    pub paid_retail_handoffs: u64,
    pub proven_retail_handoffs: u64,
    pub consumed: u64,
    pub proven_consumed: u64,
    pub supplier_unproven_allowance: u64,
    pub retailer_unproven_allowance: u64,
    pub household_unproven_allowance: u64,
    pub pending_orders: usize,
}
#[derive(Clone, Default)]
struct Producer {
    outputs: BTreeMap<ProcessId, u64>,
    unknown: u64,
    produced: u64,
    paid: u64,
}
#[derive(Clone)]
struct Order {
    supplier: SiteId,
    buyer: SiteId,
    remaining: u64,
    price: i128,
    renewed: bool,
    seeded_transit: u64,
}
#[derive(Clone)]
struct Chain {
    retailer: SiteId,
    native: Native,
    households: BTreeSet<FinalDemandPrincipalId>,
    producers: BTreeMap<SiteId, Producer>,
    direct: bool,
    retailer_unknown: u64,
    incoming: u64,
    retail_paid: u64,
    household_unknown: u64,
    other_household: u64,
    consumed: u64,
}
#[derive(Clone)]
pub struct Audit {
    seed_period: u64,
    hash: [u8; 32],
    period: u64,
    chain: Option<Chain>,
    orders: BTreeMap<OrderId, Order>,
}

impl Audit {
    /// The caller binds this state to the supplied authenticated completed period/hash.
    /// # Errors
    /// Refuses a mismatched seed period, invalid custody units or quantities,
    /// incomplete order identities and arithmetic overflow.
    pub fn seed(state: &MaterialCircuitState, seed_period: u64, hash: [u8; 32]) -> Result<Self> {
        if seed_period.checked_add(1) != Some(state.period) {
            return Err(Refusal::SeedPeriod);
        }
        let mut audit = Self {
            seed_period,
            hash,
            period: seed_period,
            chain: select(state)?,
            orders: BTreeMap::new(),
        };
        if audit.chain.is_some() {
            audit.seed_stock(state)?;
            audit.seed_orders(state)?;
        }
        Ok(audit)
    }
    /// Candidate state publishes only after every checked join succeeds.
    /// # Errors
    /// Refuses noncontiguous receipts, inconsistent custody, unmatched purchases
    /// or payments, arithmetic overflow and a pending join beyond its bound.
    pub fn read(&mut self, r: &MaterialTickReceipts) -> Result<Evidence> {
        let mut next = self.clone();
        next.extend(r)?;
        let evidence = next.evidence()?;
        *self = next;
        Ok(evidence)
    }
    /// # Errors
    /// Refuses an inconsistent conservative custody bound or arithmetic overflow.
    pub fn evidence(&self) -> Result<Evidence> {
        let mut e = Evidence {
            version: 1,
            seed_period: self.seed_period,
            seed_register_sha256: hex(&self.hash),
            through_period: self.period,
            selection: None,
            status: "no_usable_chain",
            produced: 0,
            producer_paid_deliveries: 0,
            proven_producer_supply: 0,
            paid_retail_handoffs: 0,
            proven_retail_handoffs: 0,
            consumed: 0,
            proven_consumed: 0,
            supplier_unproven_allowance: 0,
            retailer_unproven_allowance: 0,
            household_unproven_allowance: 0,
            pending_orders: self.orders.len(),
        };
        let Some(c) = &self.chain else {
            return Ok(e);
        };
        e.selection = Some(c.selection());
        for p in c.producers.values() {
            add(&mut e.produced, p.produced)?;
            add(&mut e.producer_paid_deliveries, p.paid)?;
            add(&mut e.supplier_unproven_allowance, p.unknown)?;
            add(
                &mut e.proven_producer_supply,
                p.paid.saturating_sub(p.unknown).min(p.produced),
            )?;
        }
        e.paid_retail_handoffs = c.retail_paid;
        e.consumed = c.consumed;
        e.retailer_unproven_allowance = if c.direct {
            e.supplier_unproven_allowance
        } else {
            c.retailer_unknown
                .checked_add(c.incoming.saturating_sub(e.proven_producer_supply))
                .ok_or(Refusal::Overflow)?
        };
        e.proven_retail_handoffs = if c.direct {
            e.proven_producer_supply.min(c.retail_paid)
        } else {
            c.retail_paid
                .saturating_sub(e.retailer_unproven_allowance)
                .min(e.proven_producer_supply)
        };
        e.household_unproven_allowance = c
            .household_unknown
            .checked_add(c.other_household)
            .and_then(|v| v.checked_add(c.retail_paid.saturating_sub(e.proven_retail_handoffs)))
            .ok_or(Refusal::Overflow)?;
        e.proven_consumed = c
            .consumed
            .saturating_sub(e.household_unproven_allowance)
            .min(e.proven_retail_handoffs);
        e.status = if e.proven_consumed > 0 {
            "observed"
        } else {
            "incomplete"
        };
        Ok(e)
    }
    fn seed_stock(&mut self, state: &MaterialCircuitState) -> Result<()> {
        let c = self.chain.as_mut().ok_or(Refusal::Identity)?;
        for s in &state.inventory {
            if (s.good_id, s.unit_id) == c.native {
                c.unknown_site(s.site_id, s.quantity)?;
            }
        }
        for f in &state.freight {
            if (f.good_id, f.unit_id) == c.native {
                c.unknown_site(f.destination_site_id, f.quantity)?;
            }
        }
        let CircuitAccounting::Monetary(book) = &state.accounting else {
            return Err(Refusal::Identity);
        };
        let recurring = book.recurring.as_ref().ok_or(Refusal::Identity)?;
        for s in &recurring.household_stocks {
            if c.households.contains(&s.principal_id) && (s.good_id, s.unit_id) == c.native {
                add(&mut c.household_unknown, s.quantity)?;
            }
        }
        Ok(())
    }
    fn seed_orders(&mut self, state: &MaterialCircuitState) -> Result<()> {
        let c = self.chain.as_ref().ok_or(Refusal::Identity)?;
        let CircuitAccounting::Monetary(book) = &state.accounting else {
            return Err(Refusal::Identity);
        };
        let mut transit = BTreeMap::<OrderId, u64>::new();
        for f in &state.freight {
            if (f.good_id, f.unit_id) == c.native {
                add(transit.entry(f.order_id).or_default(), f.quantity)?;
            }
        }
        for o in &state.orders {
            if (o.good_id, o.unit_id) != c.native || !c.relevant(o.buyer_site_id) {
                continue;
            }
            let remaining = o
                .ordered
                .checked_sub(o.delivered)
                .and_then(|q| q.checked_sub(o.lost))
                .ok_or(Refusal::Quantity)?;
            if remaining == 0 {
                continue;
            }
            let escrow = book
                .book
                .purchase(OutboundOrderId::Delivery(o.order_id))
                .map_err(|_| Refusal::Payment)?;
            if escrow.unit_price.micro_units() <= 0
                || escrow.quantity != o.ordered
                || escrow.buyer != AccountId::Site(o.buyer_site_id)
                || escrow.seller != AccountId::Site(o.supplier_site_id)
            {
                return Err(Refusal::Payment);
            }
            let row = Order {
                supplier: o.supplier_site_id,
                buyer: o.buyer_site_id,
                remaining,
                price: escrow.unit_price.micro_units(),
                renewed: false,
                seeded_transit: transit.get(&o.order_id).copied().unwrap_or(0),
            };
            if self.orders.insert(o.order_id, row).is_some() {
                return Err(Refusal::Duplicate);
            }
        }
        if self.orders.len() > MAX_PENDING {
            return Err(Refusal::PendingLimit);
        }
        Ok(())
    }
    fn extend(&mut self, r: &MaterialTickReceipts) -> Result<()> {
        if self.period.checked_add(1) != Some(r.resolve_tick) {
            return Err(Refusal::Period);
        }
        if self.chain.is_some() {
            let c = self.chain.as_ref().ok_or(Refusal::Identity)?;
            let ids = self.period_orders(r, c);
            let index = Index::read(r, c, &ids)?;
            let new = self.admit(&r.procurement, r.resolve_tick, &index)?;
            self.production(&r.production)?;
            self.deliveries(&index, &new)?;
            self.households(r, &index)?;
            if self.orders.len() > MAX_PENDING {
                return Err(Refusal::PendingLimit);
            }
        }
        self.period = r.resolve_tick;
        Ok(())
    }
    fn period_orders(&self, r: &MaterialTickReceipts, c: &Chain) -> BTreeSet<OutboundOrderId> {
        let mut ids: BTreeSet<_> = self
            .orders
            .keys()
            .copied()
            .map(OutboundOrderId::Delivery)
            .collect();
        for p in &r.procurement {
            if (p.good_id, p.unit_id) == c.native && c.relevant(p.buyer_site_id) {
                ids.insert(OutboundOrderId::Delivery(p.order_id));
            }
        }
        for d in &r.household_demand {
            if c.households.contains(&d.principal_id) && (d.good_id, d.unit_id) == c.native {
                ids.insert(OutboundOrderId::LocalFinalDemand(d.order_id));
            }
        }
        ids
    }
    fn admit(
        &mut self,
        rows: &[ProcurementReceipt],
        period: u64,
        index: &Index,
    ) -> Result<BTreeSet<OrderId>> {
        let c = self.chain.as_ref().ok_or(Refusal::Identity)?;
        let mut new = BTreeSet::new();
        for p in rows {
            if self.orders.contains_key(&p.order_id) {
                return Err(Refusal::Duplicate);
            }
            if (p.good_id, p.unit_id) != c.native || !c.relevant(p.buyer_site_id) {
                continue;
            }
            if p.period != period
                || p.order_id
                    != babylon_material_circuit::recurring_procurement_order_id(
                        period,
                        p.buyer_site_id,
                        p.supplier_site_id,
                        p.good_id,
                        p.unit_id,
                    )
                || p.admitted_quantity > p.desired_quantity
            {
                return Err(Refusal::Identity);
            }
            if p.admitted_quantity == 0 {
                continue;
            }
            if p.unit_price.micro_units() <= 0 || !new.insert(p.order_id) {
                return Err(Refusal::Duplicate);
            }
            let row = Order {
                supplier: p.supplier_site_id,
                buyer: p.buyer_site_id,
                remaining: p.admitted_quantity,
                price: p.unit_price.micro_units(),
                renewed: true,
                seeded_transit: 0,
            };
            let id = OutboundOrderId::Delivery(p.order_id);
            index.payment(
                0,
                id,
                MoneyLocation::Cash(AccountId::Site(row.buyer)),
                MoneyLocation::PurchaseReserve(id),
                amount(row.remaining, row.price)?,
            )?;
            self.orders.insert(p.order_id, row);
        }
        Ok(new)
    }
    fn production(&mut self, rows: &[ProductionReceipt]) -> Result<()> {
        let c = self.chain.as_mut().ok_or(Refusal::Identity)?;
        let mut seen = BTreeSet::new();
        for r in rows {
            let Some(p) = c.producers.get_mut(&r.site_id) else {
                continue;
            };
            let Some(coefficient) = p.outputs.get(&r.process_id) else {
                continue;
            };
            if !seen.insert(r.process_id) || r.produced_batches > r.planned_batches {
                return Err(Refusal::Quantity);
            }
            add(
                &mut p.produced,
                r.produced_batches
                    .checked_mul(*coefficient)
                    .ok_or(Refusal::Overflow)?,
            )?;
        }
        Ok(())
    }
    fn deliveries(&mut self, index: &Index, new: &BTreeSet<OrderId>) -> Result<()> {
        let c = self.chain.as_mut().ok_or(Refusal::Identity)?;
        for (order_id, o) in &mut self.orders {
            let f = index.movements.get(order_id).cloned().unwrap_or_default();
            if let Some((supplier, buyer, good, unit)) = f.local_identity {
                if (supplier, buyer) != (o.supplier, o.buyer) || (good, unit) != c.native {
                    return Err(Refusal::Unit);
                }
            }
            let physical = f.arrival.checked_add(f.local).ok_or(Refusal::Overflow)?;
            if f.arrival > 0 && f.local > 0 {
                return Err(Refusal::Duplicate);
            }
            if f.arrival != f.delivered || f.delivered != f.realized {
                return Err(Refusal::Quantity);
            }
            let id = OutboundOrderId::Delivery(*order_id);
            let reserve = MoneyLocation::PurchaseReserve(id);
            if !new.contains(order_id) {
                index.payment(
                    0,
                    id,
                    MoneyLocation::Cash(AccountId::Site(o.buyer)),
                    reserve,
                    0,
                )?;
            }
            index.payment(
                1,
                id,
                reserve,
                MoneyLocation::Cash(AccountId::Site(o.supplier)),
                amount(physical, o.price)?,
            )?;
            index.payment(
                2,
                id,
                reserve,
                MoneyLocation::Cash(AccountId::Site(o.buyer)),
                amount(f.lost, o.price)?,
            )?;
            o.remaining = o
                .remaining
                .checked_sub(physical.checked_add(f.lost).ok_or(Refusal::Overflow)?)
                .ok_or(Refusal::Quantity)?;
            let prepaid = physical.min(o.seeded_transit);
            o.seeded_transit -= prepaid;
            let added = physical.checked_sub(prepaid).ok_or(Refusal::Quantity)?;
            c.incoming_site(o.buyer, added)?;
            if !c.direct && o.buyer == c.retailer && o.renewed {
                if let Some(p) = c.producers.get_mut(&o.supplier) {
                    add(&mut p.paid, physical)?;
                }
            }
        }
        self.orders.retain(|_, o| o.remaining > 0);
        Ok(())
    }
    fn households(&mut self, r: &MaterialTickReceipts, index: &Index) -> Result<()> {
        let c = self.chain.as_mut().ok_or(Refusal::Identity)?;
        let mut seen = BTreeSet::new();
        let mut matched = BTreeSet::new();
        for d in &r.household_demand {
            if !c.households.contains(&d.principal_id) || (d.good_id, d.unit_id) != c.native {
                continue;
            }
            if d.period != r.resolve_tick
                || d.order_id
                    != babylon_material_circuit::recurring_household_order_id(
                        d.period,
                        (d.principal_id, d.good_id, d.unit_id),
                    )
                || !seen.insert(d.principal_id)
                || d.unit_price.micro_units() <= 0
                || d.admitted_quantity > d.requested_quantity
                || d.fulfilled_quantity.checked_add(d.expired_quantity) != Some(d.admitted_quantity)
            {
                return Err(Refusal::Identity);
            }
            Self::household_payment(d, index)?;
            let key = (
                d.order_id,
                d.principal_id,
                d.retailer_site_id,
                d.good_id,
                d.unit_id,
            );
            matched.insert(key);
            let handed = index.handoffs.get(&key).copied().unwrap_or(0);
            if handed != d.fulfilled_quantity {
                return Err(Refusal::Unit);
            }
            if d.retailer_site_id == c.retailer {
                add(&mut c.retail_paid, handed)?;
                if c.direct {
                    add(
                        &mut c
                            .producers
                            .get_mut(&c.retailer)
                            .ok_or(Refusal::Identity)?
                            .paid,
                        handed,
                    )?;
                }
            } else {
                add(&mut c.other_household, handed)?;
            }
        }
        for (key, q) in &index.handoffs {
            if c.households.contains(&key.1) && (key.3, key.4) == c.native && !matched.contains(key)
            {
                add(&mut c.other_household, *q)?;
            }
        }
        Self::household_consumption(c, &r.household_consumption, r.resolve_tick)?;
        for a in &r.aid {
            if a.outcome == AidOutcome::Granted
                && c.households.contains(&a.recipient)
                && (a.good_id, a.unit_id) == c.native
            {
                add(&mut c.other_household, a.quantity)?;
            }
        }
        Ok(())
    }
    fn household_payment(d: &HouseholdDemandReceipt, index: &Index) -> Result<()> {
        let id = OutboundOrderId::LocalFinalDemand(d.order_id);
        let reserve = MoneyLocation::PurchaseReserve(id);
        index.payment(
            0,
            id,
            MoneyLocation::Cash(AccountId::Household(d.principal_id)),
            reserve,
            amount(d.admitted_quantity, d.unit_price.micro_units())?,
        )?;
        index.payment(
            1,
            id,
            reserve,
            MoneyLocation::Cash(AccountId::Site(d.retailer_site_id)),
            amount(d.fulfilled_quantity, d.unit_price.micro_units())?,
        )?;
        index.payment(
            2,
            id,
            reserve,
            MoneyLocation::Cash(AccountId::Household(d.principal_id)),
            amount(d.expired_quantity, d.unit_price.micro_units())?,
        )?;
        Ok(())
    }
    fn household_consumption(
        c: &mut Chain,
        rows: &[HouseholdConsumptionReceipt],
        period: u64,
    ) -> Result<()> {
        let mut seen = BTreeSet::new();
        for r in rows {
            if !c.households.contains(&r.principal_id) || (r.good_id, r.unit_id) != c.native {
                continue;
            }
            if r.period != period
                || !seen.insert(r.principal_id)
                || r.consumed_quantity.checked_add(r.unmet_quantity) != Some(r.required_quantity)
                || r.consumed_quantity.checked_add(r.closing_quantity) != Some(r.available_quantity)
            {
                return Err(Refusal::Quantity);
            }
            add(&mut c.consumed, r.consumed_quantity)?;
        }
        Ok(())
    }
}

impl Chain {
    fn relevant(&self, site: SiteId) -> bool {
        site == self.retailer || self.producers.contains_key(&site)
    }
    fn unknown_site(&mut self, site: SiteId, q: u64) -> Result<()> {
        if let Some(p) = self.producers.get_mut(&site) {
            add(&mut p.unknown, q)?;
        }
        if !self.direct && site == self.retailer {
            add(&mut self.retailer_unknown, q)?;
        }
        Ok(())
    }
    fn incoming_site(&mut self, site: SiteId, q: u64) -> Result<()> {
        if let Some(p) = self.producers.get_mut(&site) {
            add(&mut p.unknown, q)?;
        }
        if !self.direct && site == self.retailer {
            add(&mut self.incoming, q)?;
        }
        Ok(())
    }
    fn selection(&self) -> Selection {
        Selection {
            retailer: hex(&self.retailer.as_bytes()),
            producers: self.producers.keys().map(|v| hex(&v.as_bytes())).collect(),
            households: self.households.iter().map(|v| hex(&v.as_bytes())).collect(),
            good_id: hex(&self.native.0.as_bytes()),
            unit_id: hex(&self.native.1.as_bytes()),
            direct_producer_retailer: self.direct,
            output_basis: self
                .producers
                .iter()
                .flat_map(|(site, p)| {
                    p.outputs.iter().map(move |(process, q)| OutputBasis {
                        site_id: hex(&site.as_bytes()),
                        process_id: hex(&process.as_bytes()),
                        quantity_per_batch: *q,
                    })
                })
                .collect(),
        }
    }
}
type Outputs = BTreeMap<Group, BTreeMap<ProcessId, u64>>;
fn eligible(state: &MaterialCircuitState) -> BTreeSet<Native> {
    let mut natives: BTreeSet<_> = state
        .commodities
        .iter()
        .filter(|v| matches!(v.kind, CommodityKind::Storable { .. }))
        .map(|v| (v.good_id, v.unit_id))
        .collect();
    if let CapacitySupply::Rolling(s) = &state.capacity_supply {
        if let RollingProcessSupply::Equipment(e) = &s.processes {
            for d in &e.definitions {
                natives.remove(&(d.equipment_good_id, d.equipment_unit_id));
            }
        }
    }
    natives
}
fn outputs(state: &MaterialCircuitState, natives: &BTreeSet<Native>) -> Result<Outputs> {
    let mut out = Outputs::new();
    for p in &state.process_outputs {
        if !natives.contains(&(p.good_id, p.unit_id)) {
            continue;
        }
        if p.quantity_per_batch == 0 {
            return Err(Refusal::Quantity);
        }
        if out
            .entry((p.site_id, p.good_id, p.unit_id))
            .or_default()
            .insert(p.process_id, p.quantity_per_batch)
            .is_some()
        {
            return Err(Refusal::Duplicate);
        }
    }
    Ok(out)
}
fn select(state: &MaterialCircuitState) -> Result<Option<Chain>> {
    let CircuitAccounting::Monetary(book) = &state.accounting else {
        return Ok(None);
    };
    let Some(recurring) = &book.recurring else {
        return Ok(None);
    };
    let natives = eligible(state);
    let outputs = outputs(state, &natives)?;
    let mut groups = BTreeMap::<Group, BTreeSet<FinalDemandPrincipalId>>::new();
    for p in &recurring.household_purchases {
        if p.enabled && natives.contains(&(p.good_id, p.unit_id)) {
            groups
                .entry((p.retailer_site_id, p.good_id, p.unit_id))
                .or_default()
                .insert(p.principal_id);
        }
    }
    let mut suppliers = BTreeMap::<Group, BTreeSet<SiteId>>::new();
    for p in &recurring.replenishment {
        if outputs.contains_key(&(p.supplier_site_id, p.good_id, p.unit_id)) {
            suppliers
                .entry((p.buyer_site_id, p.good_id, p.unit_id))
                .or_default()
                .insert(p.supplier_site_id);
        }
    }
    for direct in [true, false] {
        for (key, households) in &groups {
            let Some(selected) = selected_sites(*key, direct, &outputs, &suppliers) else {
                continue;
            };
            if selected
                .iter()
                .any(|site| outputs[&(*site, key.1, key.2)].len() > MAX_OUTPUT_RECIPES)
            {
                continue;
            }
            let producers = selected
                .into_iter()
                .map(|site| {
                    (
                        site,
                        Producer {
                            outputs: outputs[&(site, key.1, key.2)].clone(),
                            ..Producer::default()
                        },
                    )
                })
                .collect();
            return Ok(Some(Chain {
                retailer: key.0,
                native: (key.1, key.2),
                households: households.iter().copied().take(MAX_HOUSEHOLDS).collect(),
                producers,
                direct,
                retailer_unknown: 0,
                incoming: 0,
                retail_paid: 0,
                household_unknown: 0,
                other_household: 0,
                consumed: 0,
            }));
        }
    }
    Ok(None)
}
#[derive(Clone, Default)]
struct Movement {
    arrival: u64,
    local: u64,
    delivered: u64,
    realized: u64,
    lost: u64,
    local_identity: Option<(SiteId, SiteId, GoodId, UnitId)>,
}
struct Payment {
    debit: MoneyLocation,
    credit: MoneyLocation,
    amount: i128,
}
type PaymentKey = (u8, OutboundOrderId);
type Handoff = (OrderId, FinalDemandPrincipalId, SiteId, GoodId, UnitId);
#[derive(Default)]
struct Index {
    payments: BTreeMap<PaymentKey, Payment>,
    movements: BTreeMap<OrderId, Movement>,
    handoffs: BTreeMap<Handoff, u64>,
}
impl Index {
    fn read(r: &MaterialTickReceipts, c: &Chain, ids: &BTreeSet<OutboundOrderId>) -> Result<Self> {
        let mut i = Self::default();
        i.payments(&r.money_transfers, ids)?;
        i.movements(r, ids)?;
        for f in &r.local_fulfillments {
            if !c.households.contains(&f.demand_principal_id) || (f.good_id, f.unit_id) != c.native
            {
                continue;
            }
            add(
                i.handoffs
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
        Ok(i)
    }
    fn payments(
        &mut self,
        rows: &[MoneyTransferReceipt],
        ids: &BTreeSet<OutboundOrderId>,
    ) -> Result<()> {
        for r in rows {
            let key = match r.purpose {
                MoneyTransferPurpose::PurchaseReservation(id) => (0, id),
                MoneyTransferPurpose::DeliverySettlement(id) => (1, id),
                MoneyTransferPurpose::PurchaseRefund(id) => (2, id),
                _ => continue,
            };
            if !ids.contains(&key.1) {
                continue;
            }
            let value = r.credit.delta.micro_units();
            if value <= 0 || value.checked_neg() != Some(r.debit.delta.micro_units()) {
                return Err(Refusal::Payment);
            }
            let p = self.payments.entry(key).or_insert(Payment {
                debit: r.debit.location,
                credit: r.credit.location,
                amount: 0,
            });
            if (p.debit, p.credit) != (r.debit.location, r.credit.location) {
                return Err(Refusal::Payment);
            }
            p.amount = p.amount.checked_add(value).ok_or(Refusal::Overflow)?;
        }
        Ok(())
    }
    fn payment(
        &self,
        kind: u8,
        id: OutboundOrderId,
        debit: MoneyLocation,
        credit: MoneyLocation,
        value: i128,
    ) -> Result<()> {
        match self.payments.get(&(kind, id)) {
            Some(p) if (p.debit, p.credit, p.amount) == (debit, credit, value) => Ok(()),
            None if value == 0 => Ok(()),
            _ => Err(Refusal::Payment),
        }
    }
    fn movements(
        &mut self,
        r: &MaterialTickReceipts,
        ids: &BTreeSet<OutboundOrderId>,
    ) -> Result<()> {
        for f in &r.arrivals {
            if !ids.contains(&OutboundOrderId::Delivery(f.order_id)) {
                continue;
            }
            add(
                &mut self.movements.entry(f.order_id).or_default().arrival,
                f.quantity,
            )?;
        }
        for f in &r.deliveries {
            if !ids.contains(&OutboundOrderId::Delivery(f.order_id)) {
                continue;
            }
            add(
                &mut self.movements.entry(f.order_id).or_default().delivered,
                f.quantity,
            )?;
        }
        for f in &r.realizations {
            if !ids.contains(&OutboundOrderId::Delivery(f.order_id)) {
                continue;
            }
            add(
                &mut self.movements.entry(f.order_id).or_default().realized,
                f.quantity,
            )?;
        }
        for f in &r.losses {
            if !ids.contains(&OutboundOrderId::Delivery(f.order_id)) {
                continue;
            }
            add(
                &mut self.movements.entry(f.order_id).or_default().lost,
                f.quantity,
            )?;
        }
        for f in &r.local_transfers {
            if !ids.contains(&OutboundOrderId::Delivery(f.order_id)) {
                continue;
            }
            let m = self.movements.entry(f.order_id).or_default();
            let identity = (f.supplier_site_id, f.buyer_site_id, f.good_id, f.unit_id);
            if m.local_identity.is_some_and(|prior| prior != identity) {
                return Err(Refusal::Unit);
            }
            m.local_identity = Some(identity);
            add(&mut m.local, f.quantity)?;
        }
        Ok(())
    }
}

fn selected_sites(
    key: Group,
    direct: bool,
    outputs: &Outputs,
    suppliers: &BTreeMap<Group, BTreeSet<SiteId>>,
) -> Option<BTreeSet<SiteId>> {
    if direct {
        return outputs.contains_key(&key).then(|| BTreeSet::from([key.0]));
    }
    suppliers
        .get(&key)
        .map(|sites| sites.iter().copied().take(MAX_PRODUCERS).collect())
}
