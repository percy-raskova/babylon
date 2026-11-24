use super::GoodId;
use super::MaterialCircuitError;
use super::MaterialCircuitState;
use super::Result;
use super::ServiceOrder;
use super::ServicePerformanceReceipt;
use super::UnitId;
use super::MAX_SERVICE_RECEIPTS_PER_PERIOD;
use crate::clearing::{self, MarketMoment, MarketTable};
use crate::inventory::InventoryLedger;
use crate::tiers::HouseholdLists;
use crate::valuation::CostClose;
use crate::MaterialCatalog;
use crate::OrderId;
use crate::{
    AccountId, CircuitAccounting, MoneyTransferReceipt, OutboundOrderId, PurchaseEscrow, SiteId,
};
use crate::{
    CommodityKind, MarketBid, MarketClearingPolicy, RecurringEconomy, ServiceStage, WantTier,
};
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;
use std::collections::BTreeSet;

/// Exact identity of a generated current-period service request.
#[must_use]
pub fn recurring_service_order_id(
    period: u64,
    buyer: AccountId,
    provider: SiteId,
    good: GoodId,
    unit: UnitId,
) -> OrderId {
    let (tag, id) = buyer.wire_parts();
    let mut bytes = b"babylon.recurring-service-order.v1\0".to_vec();
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.push(tag);
    bytes.extend_from_slice(&id);
    bytes.extend_from_slice(&provider.as_bytes());
    bytes.extend_from_slice(&good.as_bytes());
    bytes.extend_from_slice(&unit.as_bytes());
    OrderId::from_bytes(content_digest::sha256_of(&bytes))
}
/// Exact identity of a top-up against captured, accepted service commitments.
/// `due` is the strictly order-ID-sorted `(order, quantity, accepted price)` slice.
#[must_use]
pub fn recurring_service_topup_order_id(
    base: OrderId,
    due: &[(OrderId, u64, Currency)],
) -> OrderId {
    let mut bytes = b"babylon.recurring-service-topup.v1\0".to_vec();
    bytes.extend_from_slice(&base.as_bytes());
    for (order, quantity, price) in due {
        bytes.extend_from_slice(&order.as_bytes());
        bytes.extend_from_slice(&quantity.to_be_bytes());
        bytes.extend_from_slice(&price.micro_units().to_be_bytes());
    }
    OrderId::from_bytes(content_digest::sha256_of(&bytes))
}
pub(crate) struct Request {
    pub(crate) order_id: OrderId,
    pub(crate) buyer: AccountId,
    pub(crate) provider: SiteId,
    pub(crate) good: GoodId,
    pub(crate) unit: UnitId,
    pub(crate) requested: u64,
    pub(crate) floor: Currency,
    /// The tier of a want; `None` for a need and for a business.
    pub(crate) tier: Option<WantTier>,
}
pub(crate) fn requests(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
) -> Result<Vec<Request>> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(vec![]);
    };
    let Some(r) = &e.recurring else {
        return Ok(vec![]);
    };
    let requirements = super::input_requirements(catalog, state, false)?;
    let mut result = Vec::new();
    for p in &catalog.service_inputs {
        result.push(Request {
            order_id: recurring_service_order_id(
                state.period,
                AccountId::Site(p.buyer_site_id),
                p.provider_site_id,
                p.good_id,
                p.unit_id,
            ),
            buyer: AccountId::Site(p.buyer_site_id),
            provider: p.provider_site_id,
            good: p.good_id,
            unit: p.unit_id,
            requested: super::required_input(&requirements, p),
            floor: p.cash_floor,
            tier: None,
        });
    }
    for p in &r.household_purchases {
        if !super::is_service(catalog, p.good_id, p.unit_id) {
            continue;
        }
        let cohort = r
            .households
            .binary_search_by_key(&p.principal_id, |r| r.principal_id)
            .ok()
            .map(|i| &r.households[i])
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let Ok(need) = catalog
            .household_needs
            .binary_search_by_key(&(p.principal_id, p.good_id, p.unit_id), |r| {
                (r.principal_id, r.good_id, r.unit_id)
            })
            .map(|i| &catalog.household_needs[i])
        else {
            // A want alone: no need request; its wants are requested below.
            continue;
        };
        let required = need.required_quantity(cohort)?;
        result.push(Request {
            order_id: recurring_service_order_id(
                state.period,
                AccountId::Household(p.principal_id),
                p.retailer_site_id,
                p.good_id,
                p.unit_id,
            ),
            buyer: AccountId::Household(p.principal_id),
            provider: p.retailer_site_id,
            good: p.good_id,
            unit: p.unit_id,
            requested: if p.enabled {
                required.min(p.maximum_purchase)
            } else {
                0
            },
            floor: Currency::from_micro_units(0),
            tier: None,
        });
    }
    want_requests(catalog, state, r, &mut result)?;
    deduct_due_commitments(state, &mut result)?;
    result.sort_by_key(|r| (r.buyer, r.good, r.unit, r.provider));
    Ok(result)
}
/// One request for each want of a service: its own order, the purchase row's provider, no floor.
fn want_requests(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    rows: &RecurringEconomy,
    result: &mut Vec<Request>,
) -> Result<()> {
    let Some(policy) = &catalog.market_clearing else {
        return Ok(());
    };
    // Each purchase row by its key, the first of a key as a scan would find it.
    let mut purchases = BTreeMap::new();
    for p in &rows.household_purchases {
        purchases
            .entry((p.principal_id, p.good_id, p.unit_id))
            .or_insert(p);
    }
    for want in &policy.household_wants {
        if !super::is_service(catalog, want.good_id, want.unit_id) {
            continue;
        }
        let key = (want.principal_id, want.good_id, want.unit_id);
        let purchase = purchases
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let cohort = rows
            .households
            .binary_search_by_key(&want.principal_id, |r| r.principal_id)
            .ok()
            .map(|i| &rows.households[i])
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        result.push(Request {
            order_id: crate::recurring_service_want_order_id(
                state.period,
                want.principal_id,
                purchase.retailer_site_id,
                want.good_id,
                want.unit_id,
                want.tier,
            ),
            buyer: AccountId::Household(want.principal_id),
            provider: purchase.retailer_site_id,
            good: want.good_id,
            unit: want.unit_id,
            requested: if purchase.enabled {
                want.quantity(cohort)?
            } else {
                0
            },
            floor: Currency::from_micro_units(0),
            tier: Some(want.tier),
        });
    }
    Ok(())
}
type DueKey = (AccountId, SiteId, GoodId, UnitId);
fn deduct_due_commitments(state: &MaterialCircuitState, requests: &mut [Request]) -> Result<()> {
    let mut due = BTreeMap::<DueKey, (u64, Vec<&ServiceOrder>)>::new();
    for order in state
        .service_orders
        .iter()
        .filter(|o| o.performance_period == state.period)
    {
        let entry = due
            .entry((
                order.buyer,
                order.provider_site_id,
                order.good_id,
                order.unit_id,
            ))
            .or_default();
        entry.0 = entry
            .0
            .checked_add(order.quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        entry.1.push(order);
    }
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(());
    };
    for request in requests.iter_mut().filter(|r| r.tier.is_none()) {
        if let Some((quantity, orders)) =
            due.get(&(request.buyer, request.provider, request.good, request.unit))
        {
            request.requested = request.requested.saturating_sub(*quantity);
            // Preserve accepted reserves; a remaining requirement is a separate current-price purchase.
            let accepted = orders
                .iter()
                .map(|order| {
                    let reserve = e.book.purchase(OutboundOrderId::Service(order.order_id))?;
                    Ok((order.order_id, order.quantity, reserve.unit_price))
                })
                .collect::<Result<Vec<_>>>()?;
            request.order_id = recurring_service_topup_order_id(request.order_id, &accepted);
        }
    }
    Ok(())
}
pub(super) fn admit(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    movements: &mut Vec<MoneyTransferReceipt>,
) -> Result<Vec<ServicePerformanceReceipt>> {
    let requests = requests(catalog, state)?;
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        return Ok(vec![]);
    };
    let mut result = Vec::new();
    // New orders append until the final sort; index only actual positive admissions.
    let mut order_ids: BTreeSet<_> = state
        .service_orders
        .iter()
        .map(|row| row.order_id)
        .collect();
    for order in &state.service_orders {
        if order.performance_period == state.period {
            let price = e
                .book
                .purchase(OutboundOrderId::Service(order.order_id))?
                .unit_price;
            result.push(receipt(order, order.quantity, price));
        }
    }
    for request in requests {
        let recurring = e
            .recurring
            .as_ref()
            .ok_or(MaterialCircuitError::ServiceInvariant)?;
        let price = recurring
            .offers
            .binary_search_by_key(&(request.provider, request.good, request.unit), |o| {
                (o.site_id, o.good_id, o.unit_id)
            })
            .ok()
            .map(|i| &recurring.offers[i])
            .ok_or(MaterialCircuitError::PurchaseInvariant)?
            .unit_price;
        let cash = e
            .book
            .cash(request.buyer)?
            .micro_units()
            .saturating_sub(request.floor.micro_units())
            .max(0);
        let quantity =
            u64::try_from((cash / price.micro_units()).min(i128::from(request.requested)))
                .map_err(|_| MaterialCircuitError::Arithmetic)?;
        let order = ServiceOrder {
            order_id: request.order_id,
            performance_period: state.period,
            provider_site_id: request.provider,
            buyer: request.buyer,
            good_id: request.good,
            unit_id: request.unit,
            quantity,
        };
        if order_ids.contains(&order.order_id) {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        if quantity > 0 {
            crate::transition::check_order_principal_limits(
                state.orders.len(),
                state.final_demand_orders.len(),
                state
                    .service_orders
                    .len()
                    .checked_add(1)
                    .ok_or(MaterialCircuitError::Arithmetic)?,
            )?;
            movements.push(e.book.reserve_purchase(PurchaseEscrow::new(
                OutboundOrderId::Service(order.order_id),
                order.buyer,
                AccountId::Site(order.provider_site_id),
                quantity,
                price,
            )?)?);
            order_ids.insert(order.order_id);
            state.service_orders.push(order.clone());
        }
        result.push(receipt(&order, request.requested, price));
    }
    result.sort_by_key(|r| r.order_id);
    state.service_orders.sort_by_key(|r| r.order_id);
    if result.len() > MAX_SERVICE_RECEIPTS_PER_PERIOD {
        return Err(MaterialCircuitError::RowLimit);
    }
    if result.windows(2).any(|r| r[0].order_id == r[1].order_id) {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    Ok(result)
}
fn receipt(order: &ServiceOrder, requested: u64, price: Currency) -> ServicePerformanceReceipt {
    ServicePerformanceReceipt {
        period: order.performance_period,
        order_id: order.order_id,
        provider_site_id: order.provider_site_id,
        buyer: order.buyer,
        good_id: order.good_id,
        unit_id: order.unit_id,
        requested_quantity: requested,
        admitted_quantity: order.quantity,
        performed_quantity: 0,
        used_quantity: 0,
        unused_quantity: 0,
        expired_quantity: 0,
        unit_price: price,
    }
}

/// A phase's markets: the place in the order of paying, then the seller's product. A product left
/// out of the order is last, and is shared in proportion as it always was.
type StageKey = (usize, SiteId, GoodId, UnitId);

fn phase_of(catalog: &MaterialCatalog, good: GoodId, unit: UnitId) -> Result<ServiceStage> {
    match super::kind(catalog, good, unit)? {
        CommodityKind::PeriodService { stage: found } => Ok(found),
        CommodityKind::Storable { .. } => Err(MaterialCircuitError::ServiceInvariant),
    }
}

fn market_policy(catalog: &MaterialCatalog) -> Result<&MarketClearingPolicy> {
    catalog
        .market_clearing
        .as_ref()
        .ok_or(MaterialCircuitError::MarketClearingInvariant)
}

/// What each provider's product owes for the period to orders funded before its stage: the
/// admitted quantity of every performance row that is not one of this close's requests.
pub(super) fn owed_quantities(
    performance: &[ServicePerformanceReceipt],
    requests: &[Request],
) -> Result<BTreeMap<(SiteId, GoodId, UnitId), u64>> {
    let asked: BTreeSet<OrderId> = requests.iter().map(|r| r.order_id).collect();
    let mut owed = BTreeMap::new();
    for row in performance.iter().filter(|r| !asked.contains(&r.order_id)) {
        let total: &mut u64 = owed
            .entry((row.provider_site_id, row.good_id, row.unit_id))
            .or_default();
        *total = total
            .checked_add(row.admitted_quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(owed)
}

/// The requests of one phase, by market, each market's buyers in order identity.
fn phase_markets<'a>(
    catalog: &MaterialCatalog,
    requests: &'a [Request],
    phase: ServiceStage,
) -> Result<BTreeMap<StageKey, Vec<&'a Request>>> {
    let policy = market_policy(catalog)?;
    let mut markets = BTreeMap::<StageKey, Vec<&Request>>::new();
    for request in requests {
        if phase_of(catalog, request.good, request.unit)? != phase {
            continue;
        }
        let place = policy
            .place(request.good, request.unit)
            .unwrap_or(usize::MAX);
        markets
            .entry((place, request.provider, request.good, request.unit))
            .or_default()
            .push(request);
    }
    for members in markets.values_mut() {
        members.sort_by_key(|request| request.order_id);
    }
    Ok(markets)
}

pub(super) fn quote(
    state: &MaterialCircuitState,
    provider: SiteId,
    good: GoodId,
    unit: UnitId,
) -> Result<Currency> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Err(MaterialCircuitError::MonetaryInvariant);
    };
    let recurring = e
        .recurring
        .as_ref()
        .ok_or(MaterialCircuitError::ServiceInvariant)?;
    recurring
        .offers
        .binary_search_by_key(&(provider, good, unit), |o| {
            (o.site_id, o.good_id, o.unit_id)
        })
        .ok()
        .map(|i| recurring.offers[i].unit_price)
        .ok_or(MaterialCircuitError::PurchaseInvariant)
}

/// The funded orders of the period whose product belongs to this phase.
fn funded_orders<'a>(
    catalog: &MaterialCatalog,
    state: &'a MaterialCircuitState,
    phase: ServiceStage,
) -> Result<Vec<&'a ServiceOrder>> {
    let mut rows = vec![];
    for order in state
        .service_orders
        .iter()
        .filter(|o| o.performance_period == state.period)
    {
        if phase_of(catalog, order.good_id, order.unit_id)? == phase {
            rows.push(order);
        }
    }
    Ok(rows)
}

fn add_quantity(
    ledger: &mut InventoryLedger,
    key: (SiteId, GoodId, UnitId),
    quantity: u64,
) -> Result<()> {
    let value = ledger.entry(key).or_default();
    *value = value
        .checked_add(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(())
}

/// What buyers could fund at the posted prices, by seller's product: the orders already funded for
/// the period in this phase, and each phase request in the order of paying, each buyer spending
/// from a scratch copy of its cash.
pub(super) fn funded_at_quotes(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    requests: &[Request],
    phase: ServiceStage,
    lists: &HouseholdLists,
) -> Result<InventoryLedger> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(InventoryLedger::new());
    };
    let mut funded = InventoryLedger::new();
    for order in funded_orders(catalog, state, phase)? {
        add_quantity(
            &mut funded,
            (order.provider_site_id, order.good_id, order.unit_id),
            order.quantity,
        )?;
    }
    let mut scratch = BTreeMap::<AccountId, i128>::new();
    // With wants, each market is read through the households' rungs, in a scratch clone of the lists.
    let mut scratch_lists = lists.clone();
    for ((_, provider, good, unit), members) in phase_markets(catalog, requests, phase)? {
        if !lists.is_empty() {
            let quantity =
                super::tiers::fund_market(state, &members, &mut scratch, &mut scratch_lists)?;
            add_quantity(&mut funded, (provider, good, unit), quantity)?;
            continue;
        }
        let price = quote(state, provider, good, unit)?.micro_units();
        for request in members {
            let cash = match scratch.get(&request.buyer) {
                Some(&cash) => cash,
                None => e.book.cash(request.buyer)?.micro_units(),
            };
            let usable = cash.saturating_sub(request.floor.micro_units()).max(0);
            let quantity = u64::try_from((usable / price).min(i128::from(request.requested)))
                .map_err(|_| MaterialCircuitError::Arithmetic)?;
            scratch.insert(
                request.buyer,
                cash.saturating_sub(price.saturating_mul(i128::from(quantity))),
            );
            add_quantity(&mut funded, (provider, good, unit), quantity)?;
        }
    }
    Ok(funded)
}

/// What a market's buyers get, and the price they pay.
fn price_stage_market(
    books: (&MaterialCatalog, &MaterialCircuitState, &CostClose),
    moment: MarketMoment,
    members: &[&Request],
    supply: Option<u64>,
    markets: &mut MarketTable,
) -> Result<(Currency, Vec<u64>)> {
    let (catalog, state, costs) = books;
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Err(MaterialCircuitError::MonetaryInvariant);
    };
    let first = members
        .first()
        .ok_or(MaterialCircuitError::MarketClearingInvariant)?;
    let posted = quote(state, first.provider, first.good, first.unit)?;
    let purse = |request: &Request| -> Result<Currency> {
        Ok(Currency::from_micro_units(
            e.book
                .cash(request.buyer)?
                .micro_units()
                .saturating_sub(request.floor.micro_units())
                .max(0),
        ))
    };
    let Some(supply) = supply else {
        // Public provision: admitted at the posted price for what each buyer can pay for.
        let mut quantities = vec![];
        for request in members {
            let affordable = purse(request)?.micro_units() / posted.micro_units();
            quantities.push(
                u64::try_from(affordable.min(i128::from(request.requested)))
                    .map_err(|_| MaterialCircuitError::Arithmetic)?,
            );
        }
        return Ok((posted, quantities));
    };
    let mut bids = vec![];
    let mut bidders = vec![];
    for (index, request) in members.iter().enumerate() {
        let money = purse(request)?;
        if request.requested > 0 && money.micro_units() > 0 {
            // A business stops at its limit (P5); a household pays up to its purse.
            let limit = match request.buyer {
                AccountId::Site(site) => Some(clearing::limit_price(
                    catalog,
                    state,
                    costs,
                    site,
                    request.good,
                    request.unit,
                    posted,
                )?),
                _ => None,
            };
            bids.push(MarketBid {
                wanted: request.requested,
                purse: money,
                limit,
            });
            bidders.push(index);
        }
    }
    let outcome = clearing::clear_market(supply, posted, &bids)?;
    markets.record(
        state.period,
        moment,
        (first.provider, first.good, first.unit),
        posted,
        supply,
        bids.len(),
        &outcome,
        Vec::new(),
    )?;
    let mut quantities = vec![0; members.len()];
    for (&index, &quantity) in bidders.iter().zip(&outcome.quantities) {
        quantities[index] = quantity;
    }
    Ok((outcome.price, quantities))
}

/// Fund one order of a request, or only its receipt when nothing was bought.
fn book_order(
    state: &mut MaterialCircuitState,
    order_ids: &mut BTreeSet<OrderId>,
    request: &Request,
    sale: (u64, u64, Currency),
    movements: &mut Vec<MoneyTransferReceipt>,
) -> Result<ServicePerformanceReceipt> {
    let (requested, quantity, price) = sale;
    let order = ServiceOrder {
        order_id: request.order_id,
        performance_period: state.period,
        provider_site_id: request.provider,
        buyer: request.buyer,
        good_id: request.good,
        unit_id: request.unit,
        quantity,
    };
    if order_ids.contains(&order.order_id) {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    if quantity > 0 {
        crate::transition::check_order_principal_limits(
            state.orders.len(),
            state.final_demand_orders.len(),
            state
                .service_orders
                .len()
                .checked_add(1)
                .ok_or(MaterialCircuitError::Arithmetic)?,
        )?;
        let CircuitAccounting::Monetary(e) = &mut state.accounting else {
            return Err(MaterialCircuitError::MonetaryInvariant);
        };
        movements.push(e.book.reserve_purchase(PurchaseEscrow::new(
            OutboundOrderId::Service(order.order_id),
            order.buyer,
            AccountId::Site(order.provider_site_id),
            quantity,
            price,
        )?)?);
        order_ids.insert(order.order_id);
        state.service_orders.push(order.clone());
    }
    Ok(receipt(&order, requested, price))
}

/// The receipts of the orders already funded for the period in this phase, and what they owe of
/// each product.
fn funded_receipts(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    phase: ServiceStage,
    performance: &mut Vec<ServicePerformanceReceipt>,
) -> Result<InventoryLedger> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(InventoryLedger::new());
    };
    let mut owed = InventoryLedger::new();
    for order in funded_orders(catalog, state, phase)? {
        let price = e
            .book
            .purchase(OutboundOrderId::Service(order.order_id))?
            .unit_price;
        performance.push(receipt(order, order.quantity, price));
        add_quantity(
            &mut owed,
            (order.provider_site_id, order.good_id, order.unit_id),
            order.quantity,
        )?;
    }
    Ok(owed)
}

/// Bid for, price and fund the service orders of one phase. The potential output of the phase is
/// what its providers can supply once the funded orders of the period are served first.
pub(super) fn admit_stage(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    requests: &[Request],
    phase: (ServiceStage, &InventoryLedger),
    performance: &mut Vec<ServicePerformanceReceipt>,
    movements: &mut Vec<MoneyTransferReceipt>,
    books: (&mut MarketTable, &CostClose, &mut HouseholdLists),
) -> Result<()> {
    let (phase, potential) = phase;
    let (markets, costs, lists) = books;
    let owed = funded_receipts(catalog, state, phase, performance)?;
    let moment = match phase {
        ServiceStage::UtilityProvision => MarketMoment::Utility,
        ServiceStage::LocalServiceProvision => MarketMoment::LocalService,
    };
    let mut order_ids: BTreeSet<_> = state.service_orders.iter().map(|r| r.order_id).collect();
    for ((place, provider, good, unit), members) in phase_markets(catalog, requests, phase)? {
        let key = (provider, good, unit);
        let supply = (place != usize::MAX).then(|| {
            potential
                .get(&key)
                .copied()
                .unwrap_or(0)
                .saturating_sub(owed.get(&key).copied().unwrap_or(0))
        });
        if lists.is_empty() {
            let (price, quantities) =
                price_stage_market((catalog, state, costs), moment, &members, supply, markets)?;
            for (request, quantity) in members.into_iter().zip(quantities) {
                performance.push(book_order(
                    state,
                    &mut order_ids,
                    request,
                    (request.requested, quantity, price),
                    movements,
                )?);
            }
            continue;
        }
        let cleared = super::tiers::price_market(
            (catalog, state, costs),
            moment,
            &members,
            supply,
            (&mut *markets, &mut *lists),
        )?;
        for taken in cleared.taken {
            performance.push(book_order(
                state,
                &mut order_ids,
                taken.request,
                (taken.requested, taken.quantity, cleared.price),
                movements,
            )?);
        }
    }
    performance.sort_by_key(|r| r.order_id);
    state.service_orders.sort_by_key(|r| r.order_id);
    if performance.len() > MAX_SERVICE_RECEIPTS_PER_PERIOD {
        return Err(MaterialCircuitError::RowLimit);
    }
    if performance
        .windows(2)
        .any(|r| r[0].order_id == r[1].order_id)
    {
        return Err(MaterialCircuitError::DuplicateRow);
    }
    Ok(())
}
