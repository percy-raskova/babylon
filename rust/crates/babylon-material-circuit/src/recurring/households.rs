//! Admission spends existing cash; physical handoff and period consumption differ.

use super::{HouseholdConsumptionReceipt, HouseholdDemandReceipt, RecurringEconomy, Result};
use crate::clearing::{self, LadderBid, MarketMoment, MarketTable, Offer};
use crate::tiers::HouseholdLists;
use crate::transition::outbound::HandOver;
use crate::valuation::CostClose;
use crate::MaterialCatalog;
use crate::{
    AccountId, CircuitAccounting, FinalDemandOrder, FinalDemandPrincipalId, GoodId,
    LocalRetailFulfillmentReceipt, MarketBid, MaterialCircuitError, MaterialCircuitState,
    MerchantHandlingReceipt, MonetaryBook, MonetaryCircuit, MoneyTransferReceipt, OrderId,
    OutboundOrderId, PurchaseEscrow, SiteId, UnitId, MAX_MATERIAL_CIRCUIT_ROWS,
};
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use std::collections::{BTreeMap, BTreeSet};

type HouseholdKey = (FinalDemandPrincipalId, GoodId, UnitId);

/// Stable per-period household intent key used by admission and evidence joins.
#[must_use]
pub fn recurring_household_order_id(
    period: u64,
    key: (FinalDemandPrincipalId, GoodId, UnitId),
) -> OrderId {
    let mut bytes = b"babylon.recurring-household-order.v1\0".to_vec();
    bytes.extend_from_slice(&period.to_be_bytes());
    bytes.extend_from_slice(&key.0.as_bytes());
    bytes.extend_from_slice(&key.1.as_bytes());
    bytes.extend_from_slice(&key.2.as_bytes());
    OrderId::from_bytes(content_digest::sha256_of(&bytes))
}

fn desired(required: u64, buffer: u64, stock: u64) -> Result<u64> {
    if required == 0 {
        return Ok(0);
    }
    required
        .checked_add(buffer)
        .map(|target| target.saturating_sub(stock))
        .ok_or(MaterialCircuitError::Arithmetic)
}

fn requirements(
    catalog: &MaterialCatalog,
    rows: &RecurringEconomy,
) -> Result<BTreeMap<HouseholdKey, u64>> {
    let households: BTreeMap<_, _> = rows
        .households
        .iter()
        .map(|r| (r.principal_id, r))
        .collect();
    catalog
        .household_needs
        .iter()
        .map(|need| {
            let cohort = households
                .get(&need.principal_id)
                .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
            let quantity = need.required_quantity(cohort)?;
            Ok(((need.principal_id, need.good_id, need.unit_id), quantity))
        })
        .collect()
}

fn household_phase(rows: &RecurringEconomy, period: u64) -> Result<()> {
    let previous = period
        .checked_sub(1)
        .ok_or(MaterialCircuitError::PeriodInvariant)?;
    if rows.last_household_admission_period != period
        || rows.last_household_consumption_period != previous
    {
        return Err(MaterialCircuitError::PeriodInvariant);
    }
    Ok(())
}

/// Admit once after payroll, sharing real cash in household/good/unit order.
/// Only completed staging is installed, including its admission cursor.
pub(crate) fn admit_household_orders(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    transfers: &mut Vec<MoneyTransferReceipt>,
) -> Result<Vec<HouseholdDemandReceipt>> {
    super::validate(catalog, state)?;
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(vec![]);
    };
    let Some(rows) = &mut economy.recurring else {
        return Ok(vec![]);
    };
    let required = requirements(catalog, rows)?;
    let stock: BTreeMap<_, _> = rows
        .household_stocks
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r.quantity))
        .collect();
    let offers: BTreeMap<_, _> = rows
        .offers
        .iter()
        .map(|r| ((r.site_id, r.good_id, r.unit_id), r.unit_price))
        .collect();
    let existing: BTreeSet<_> = state
        .final_demand_orders
        .iter()
        .map(|r| r.order_id)
        .collect();
    let mut policies: Vec<_> = rows.household_purchases.iter().collect();
    policies.sort_by_key(|r| (r.principal_id, r.good_id, r.unit_id));
    let mut book = economy.book.clone();
    let mut orders = vec![];
    let mut movements = vec![];
    let mut receipts = vec![];
    for policy in policies {
        let key = (policy.principal_id, policy.good_id, policy.unit_id);
        let Some(&opening_stock) = stock.get(&key) else {
            continue;
        };
        let id = recurring_household_order_id(state.period, key);
        if existing.contains(&id) {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        let required_quantity = *required
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let desired_quantity = desired(
            required_quantity,
            policy.target_closing_stock,
            opening_stock,
        )?;
        let requested_quantity = if policy.enabled {
            desired_quantity.min(policy.maximum_purchase)
        } else {
            0
        };
        let unit_price = *offers
            .get(&(policy.retailer_site_id, policy.good_id, policy.unit_id))
            .ok_or(MaterialCircuitError::PurchaseInvariant)?;
        let buyer = AccountId::Household(policy.principal_id);
        let affordable = book.cash(buyer)?.micro_units() / unit_price.micro_units();
        let admitted_quantity = u64::try_from(affordable.min(i128::from(requested_quantity)))
            .map_err(|_| MaterialCircuitError::Arithmetic)?;
        let demand = HouseholdDemandReceipt {
            period: state.period,
            principal_id: policy.principal_id,
            retailer_site_id: policy.retailer_site_id,
            good_id: policy.good_id,
            unit_id: policy.unit_id,
            order_id: id,
            opening_stock,
            required_quantity,
            desired_quantity,
            requested_quantity,
            admitted_quantity,
            fulfilled_quantity: 0,
            expired_quantity: 0,
            unit_price,
        };
        if admitted_quantity > 0 {
            let retail = state
                .final_demand_orders
                .len()
                .checked_add(orders.len())
                .and_then(|n| n.checked_add(1))
                .ok_or(MaterialCircuitError::Arithmetic)?;
            crate::transition::check_order_principal_limits(
                state.orders.len(),
                retail,
                state.service_orders.len(),
            )?;
            let (order, movement) = fund_order(&mut book, &demand)?;
            orders.push(order);
            movements.push(movement);
        }
        receipts.push(demand);
    }
    economy.book = book;
    rows.last_household_admission_period = state.period;
    state.final_demand_orders.extend(orders);
    state.final_demand_orders.sort_by_key(|r| r.order_id);
    transfers.extend(movements);
    Ok(receipts)
}

/// What selling goods to households at the market's price leaves behind.
pub(crate) struct HouseholdGoodsSale {
    /// Final: fulfilled equals admitted and nothing is expired.
    pub demand: Vec<HouseholdDemandReceipt>,
    pub fulfillments: Vec<LocalRetailFulfillmentReceipt>,
    pub handling: Vec<MerchantHandlingReceipt>,
}

/// A household's plan to buy one good at its retailer in this period.
pub(crate) struct Intent {
    pub(crate) principal_id: FinalDemandPrincipalId,
    pub(crate) retailer_site_id: SiteId,
    pub(crate) good_id: GoodId,
    pub(crate) unit_id: UnitId,
    pub(crate) order_id: OrderId,
    opening_stock: u64,
    required_quantity: u64,
    desired_quantity: u64,
    pub(crate) requested_quantity: u64,
    quote: Currency,
}

/// The plans of every household with a stock row, in household, good and unit order.
pub(crate) fn household_intents(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    rows: &RecurringEconomy,
) -> Result<Vec<Intent>> {
    let required = requirements(catalog, rows)?;
    let stock: BTreeMap<_, _> = rows
        .household_stocks
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r.quantity))
        .collect();
    let offers: BTreeMap<_, _> = rows
        .offers
        .iter()
        .map(|r| ((r.site_id, r.good_id, r.unit_id), r.unit_price))
        .collect();
    let existing: BTreeSet<_> = state
        .final_demand_orders
        .iter()
        .map(|r| r.order_id)
        .collect();
    let mut policies: Vec<_> = rows.household_purchases.iter().collect();
    policies.sort_by_key(|r| (r.principal_id, r.good_id, r.unit_id));
    let mut intents = vec![];
    for policy in policies {
        let key = (policy.principal_id, policy.good_id, policy.unit_id);
        let Some(&opening_stock) = stock.get(&key) else {
            continue;
        };
        let order_id = recurring_household_order_id(state.period, key);
        if existing.contains(&order_id) {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        let required_quantity = *required
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let desired_quantity = desired(
            required_quantity,
            policy.target_closing_stock,
            opening_stock,
        )?;
        let requested_quantity = if policy.enabled {
            desired_quantity.min(policy.maximum_purchase)
        } else {
            0
        };
        let quote = *offers
            .get(&(policy.retailer_site_id, policy.good_id, policy.unit_id))
            .ok_or(MaterialCircuitError::PurchaseInvariant)?;
        intents.push(Intent {
            principal_id: policy.principal_id,
            retailer_site_id: policy.retailer_site_id,
            good_id: policy.good_id,
            unit_id: policy.unit_id,
            order_id,
            opening_stock,
            required_quantity,
            desired_quantity,
            requested_quantity,
            quote,
        });
    }
    Ok(intents)
}

fn economy_mut(state: &mut MaterialCircuitState) -> Result<&mut MonetaryCircuit> {
    match &mut state.accounting {
        CircuitAccounting::Monetary(economy) => Ok(economy),
        CircuitAccounting::PhysicalControl => Err(MaterialCircuitError::MonetaryInvariant),
    }
}

/// Sell goods to households at the market's price, where `admit_household_orders` admits them at
/// the posted price. Each retailer's markets clear in the campaign's order of paying, and the
/// buyers of one market in order identity. A household's purchase is handed over, paid and retired
/// at once, so nothing the seller does later in the period can take it back.
///
/// # Errors
/// `MarketClearingInvariant` for a catalog without a market policy, or for a household that still
/// holds an order of an earlier period; the refusals of the rule, the hand-over and the book.
pub(crate) fn sell_household_goods(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    costs: &mut CostClose,
    transfers: &mut Vec<MoneyTransferReceipt>,
    markets: &mut MarketTable,
    lists: &mut HouseholdLists,
) -> Result<HouseholdGoodsSale> {
    super::validate(catalog, state)?;
    let policy = catalog
        .market_clearing
        .as_ref()
        .ok_or(MaterialCircuitError::MarketClearingInvariant)?;
    let mut sale = HouseholdGoodsSale {
        demand: vec![],
        fulfillments: vec![],
        handling: vec![],
    };
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(sale);
    };
    let Some(rows) = &economy.recurring else {
        return Ok(sale);
    };
    let households: BTreeSet<_> = rows.households.iter().map(|r| r.principal_id).collect();
    if state
        .final_demand_orders
        .iter()
        .any(|order| households.contains(&order.demand_principal_id))
    {
        return Err(MaterialCircuitError::MarketClearingInvariant);
    }
    let mut intents = household_intents(catalog, state, rows)?;
    let stocked = intents.len();
    intents.extend(bare_want_intents(catalog, state, rows, &intents)?);
    let mut by_market: BTreeMap<_, Vec<usize>> = BTreeMap::new();
    for (index, intent) in intents.iter().enumerate() {
        let place = policy
            .place(intent.good_id, intent.unit_id)
            .unwrap_or(usize::MAX);
        by_market
            .entry((
                place,
                intent.retailer_site_id,
                intent.good_id,
                intent.unit_id,
            ))
            .or_default()
            .push(index);
    }
    let mut offer = Offer::new(catalog, state)?;
    let mut paid = vec![(Currency::from_micro_units(0), 0_u64); intents.len()];
    let mut selling = Selling {
        offer: &mut offer,
        costs,
        transfers,
        markets,
        lists,
    };
    for mut members in by_market.into_values() {
        members.sort_by_key(|&index| intents[index].order_id);
        let cleared = sell_market((catalog, &mut *state), &intents, &members, &mut selling)?;
        sale.fulfillments.extend(cleared.hand_over.fulfillments);
        sale.handling.extend(cleared.hand_over.handling);
        for &index in &members {
            paid[index] = (
                cleared.price,
                cleared.sold.get(&index).copied().unwrap_or(0),
            );
        }
    }
    sale.demand = intents
        .iter()
        .take(stocked)
        .zip(&paid)
        .map(|(intent, &(unit_price, sold))| HouseholdDemandReceipt {
            period: state.period,
            principal_id: intent.principal_id,
            retailer_site_id: intent.retailer_site_id,
            good_id: intent.good_id,
            unit_id: intent.unit_id,
            order_id: intent.order_id,
            opening_stock: intent.opening_stock,
            required_quantity: intent.required_quantity,
            desired_quantity: intent.desired_quantity,
            requested_quantity: intent.requested_quantity,
            admitted_quantity: sold,
            fulfilled_quantity: sold,
            expired_quantity: 0,
            unit_price,
        })
        .collect();
    let period = state.period;
    let economy = economy_mut(state)?;
    let rows = economy
        .recurring
        .as_mut()
        .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
    rows.last_household_admission_period = period;
    Ok(sale)
}

/// The accumulators that every market of one moment of sale shares.
struct Selling<'a, 'c> {
    offer: &'a mut Offer<'c>,
    costs: &'a mut CostClose,
    transfers: &'a mut Vec<MoneyTransferReceipt>,
    markets: &'a mut MarketTable,
    lists: &'a mut HouseholdLists,
}

struct ClearedMarket {
    price: Currency,
    /// What each buyer, by intent index, bought to meet its need.
    sold: BTreeMap<usize, u64>,
    hand_over: HandOver,
}

/// One household's purchase in one market: its need, or one of its wants.
struct Sale {
    order_id: OrderId,
    principal_id: FinalDemandPrincipalId,
    retailer_site_id: SiteId,
    good_id: GoodId,
    unit_id: UnitId,
    quantity: u64,
    /// A want is used at its purchase and never reaches the household's stock.
    want: bool,
}

impl Sale {
    fn of(intent: &Intent, order_id: OrderId, quantity: u64, want: bool) -> Self {
        Self {
            order_id,
            principal_id: intent.principal_id,
            retailer_site_id: intent.retailer_site_id,
            good_id: intent.good_id,
            unit_id: intent.unit_id,
            quantity,
            want,
        }
    }
}

/// The price of one market and what each buyer's rungs bought at it.
struct Priced {
    price: Currency,
    /// What each buyer, by intent index, bought to meet its need.
    sold: BTreeMap<usize, u64>,
    /// What each buyer, by intent index, bought of its wants: the want's order and quantity.
    wants: Vec<(usize, OrderId, u64)>,
}

/// The plans of the accounts that want a goods product they do not need, in household, good and
/// unit order. They plan to buy none of it as a need, so a catalog without wants has none.
fn bare_want_intents(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    rows: &RecurringEconomy,
    intents: &[Intent],
) -> Result<Vec<Intent>> {
    let Some(policy) = &catalog.market_clearing else {
        return Ok(vec![]);
    };
    let keys: BTreeSet<HouseholdKey> = policy
        .household_wants
        .iter()
        .map(|want| (want.principal_id, want.good_id, want.unit_id))
        .filter(|&(_, good, unit)| !crate::services::is_service(catalog, good, unit))
        .filter(|key| {
            !intents
                .iter()
                .any(|i| (i.principal_id, i.good_id, i.unit_id) == *key)
        })
        .collect();
    let mut bare = vec![];
    for key in keys {
        let purchase = rows
            .household_purchases
            .iter()
            .find(|p| (p.principal_id, p.good_id, p.unit_id) == key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let quote = rows
            .offers
            .iter()
            .find(|o| {
                (o.site_id, o.good_id, o.unit_id) == (purchase.retailer_site_id, key.1, key.2)
            })
            .map(|o| o.unit_price)
            .ok_or(MaterialCircuitError::PurchaseInvariant)?;
        bare.push(Intent {
            principal_id: key.0,
            retailer_site_id: purchase.retailer_site_id,
            good_id: key.1,
            unit_id: key.2,
            order_id: recurring_household_order_id(state.period, key),
            opening_stock: 0,
            required_quantity: 0,
            desired_quantity: 0,
            requested_quantity: 0,
            quote,
        });
    }
    Ok(bare)
}

/// Clear one market: find its price, then complete each household's purchase.
fn sell_market(
    context: (&MaterialCatalog, &mut MaterialCircuitState),
    intents: &[Intent],
    members: &[usize],
    selling: &mut Selling<'_, '_>,
) -> Result<ClearedMarket> {
    let (catalog, state) = context;
    let first = &intents[members[0]];
    let seller = (first.retailer_site_id, first.good_id, first.unit_id);
    let supply = selling.offer.supply(seller.0, seller.1, seller.2)?;
    let priced = if selling.lists.is_empty() {
        price_needs(state, intents, members, supply, selling)?
    } else {
        price_rungs(state, intents, members, supply, selling)?
    };
    let total = priced
        .sold
        .values()
        .chain(priced.wants.iter().map(|(_, _, quantity)| quantity))
        .try_fold(0_u64, |sum, &quantity| sum.checked_add(quantity))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    selling.offer.take(seller.0, seller.1, seller.2, total)?;
    let mut sales: Vec<Sale> = priced
        .sold
        .iter()
        .map(|(&index, &quantity)| {
            Sale::of(&intents[index], intents[index].order_id, quantity, false)
        })
        .collect();
    sales.extend(
        priced
            .wants
            .iter()
            .map(|&(index, order, quantity)| Sale::of(&intents[index], order, quantity, true)),
    );
    let hand_over = complete_purchases(catalog, state, &sales, priced.price, selling)?;
    Ok(ClearedMarket {
        price: priced.price,
        sold: priced.sold,
        hand_over,
    })
}

/// A market of households that only need: every bid has one rung, as the price rule first priced it.
fn price_needs(
    state: &MaterialCircuitState,
    intents: &[Intent],
    members: &[usize],
    supply: u64,
    selling: &mut Selling<'_, '_>,
) -> Result<Priced> {
    let first = &intents[members[0]];
    let seller = (first.retailer_site_id, first.good_id, first.unit_id);
    let mut bids = vec![];
    let mut bidders = vec![];
    for &index in members {
        let intent = &intents[index];
        let purse = household_cash(state, intent.principal_id)?;
        if intent.requested_quantity > 0 && purse.micro_units() > 0 {
            bids.push(MarketBid {
                wanted: intent.requested_quantity,
                purse,
                limit: None,
            });
            bidders.push(index);
        }
    }
    let outcome = clearing::clear_market(supply, first.quote, &bids)?;
    selling.markets.record(
        state.period,
        MarketMoment::HouseholdGoods,
        seller,
        first.quote,
        supply,
        bids.len(),
        &outcome,
    )?;
    let sold = bidders
        .iter()
        .zip(&outcome.quantities)
        .filter(|(_, &quantity)| quantity > 0)
        .map(|(&index, &quantity)| (index, quantity))
        .collect();
    Ok(Priced {
        price: outcome.price,
        sold,
        wants: vec![],
    })
}

/// A market in a catalog with wants: each household bids a rung for its need and one for each want
/// of the product, and the market prices the bids' totals as it does one-rung bids.
fn price_rungs(
    state: &MaterialCircuitState,
    intents: &[Intent],
    members: &[usize],
    supply: u64,
    selling: &mut Selling<'_, '_>,
) -> Result<Priced> {
    let first = &intents[members[0]];
    let seller = (first.retailer_site_id, first.good_id, first.unit_id);
    let mut bids = vec![];
    let mut bidders = vec![];
    for &index in members {
        let intent = &intents[index];
        let purse = household_cash(state, intent.principal_id)?;
        let rungs = selling.lists.rungs(
            intent.principal_id,
            intent.good_id,
            intent.unit_id,
            intent.requested_quantity,
        )?;
        let wanted = rungs
            .iter()
            .try_fold(0_u64, |sum, r| sum.checked_add(r.rung.wanted))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        if wanted > 0 && purse.micro_units() > 0 {
            bids.push(LadderBid {
                rungs: rungs.iter().map(|r| r.rung).collect(),
                purse,
                limit: None,
            });
            bidders.push((index, rungs));
        }
    }
    let outcome = clearing::clear_ladder_market(supply, first.quote, &bids)?;
    selling.markets.record(
        state.period,
        MarketMoment::HouseholdGoods,
        seller,
        first.quote,
        supply,
        bids.len(),
        &outcome.totals()?,
    )?;
    let mut priced = Priced {
        price: outcome.price,
        sold: BTreeMap::new(),
        wants: vec![],
    };
    let mut bought: BTreeMap<usize, Vec<(OrderId, u64)>> = BTreeMap::new();
    for ((index, rungs), quantities) in bidders.iter().zip(&outcome.quantities) {
        for (rung, &quantity) in rungs.iter().zip(quantities) {
            bought
                .entry(*index)
                .or_default()
                .push((rung.order_id, quantity));
            if quantity == 0 {
                continue;
            }
            if selling.lists.is_want_order(rung.order_id) {
                priced.wants.push((*index, rung.order_id, quantity));
            } else {
                priced.sold.insert(*index, quantity);
            }
        }
    }
    for &index in members {
        let intent = &intents[index];
        let rungs = bought.get(&index).map_or(&[][..], Vec::as_slice);
        selling.lists.settle(
            intent.principal_id,
            intent.good_id,
            intent.unit_id,
            rungs,
            outcome.price,
        )?;
    }
    Ok(priced)
}

fn household_cash(
    state: &MaterialCircuitState,
    principal: FinalDemandPrincipalId,
) -> Result<Currency> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Err(MaterialCircuitError::MonetaryInvariant);
    };
    Ok(economy.book.cash(AccountId::Household(principal))?)
}

/// Fund, hand over, pay and retire each purchase of one market: the needs in order identity, then
/// the wants. A want is used at its purchase, so it is never credited to the household's stock.
fn complete_purchases(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    sales: &[Sale],
    price: Currency,
    selling: &mut Selling<'_, '_>,
) -> Result<HandOver> {
    let mut handed_over = vec![];
    for sale in sales {
        let retail = state
            .final_demand_orders
            .len()
            .checked_add(1)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        crate::transition::check_order_principal_limits(
            state.orders.len(),
            retail,
            state.service_orders.len(),
        )?;
        let movement = economy_mut(state)?
            .book
            .reserve_purchase(PurchaseEscrow::new(
                OutboundOrderId::LocalFinalDemand(sale.order_id),
                AccountId::Household(sale.principal_id),
                AccountId::Site(sale.retailer_site_id),
                sale.quantity,
                price,
            )?)?;
        selling.transfers.push(movement);
        state.final_demand_orders.push(FinalDemandOrder {
            order_id: sale.order_id,
            retailer_site_id: sale.retailer_site_id,
            demand_principal_id: sale.principal_id,
            good_id: sale.good_id,
            unit_id: sale.unit_id,
            ordered: sale.quantity,
            fulfilled: 0,
        });
        if sale.want {
            selling.costs.use_at_purchase(sale.order_id);
        }
        handed_over.push((sale.order_id, sale.quantity));
    }
    state.final_demand_orders.sort_by_key(|row| row.order_id);
    let mut inventory = crate::inventory::take_inventory(state);
    let handed = crate::transition::outbound::hand_over_household_goods(
        catalog,
        state,
        &mut inventory,
        &handed_over,
        selling.costs,
    );
    crate::inventory::publish_inventory(state, inventory);
    let handed = handed?;
    for sale in sales {
        let id = OutboundOrderId::LocalFinalDemand(sale.order_id);
        let economy = economy_mut(state)?;
        if !sale.want {
            let rows = economy
                .recurring
                .as_mut()
                .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
            let stock = rows
                .household_stocks
                .iter_mut()
                .find(|row| {
                    (row.principal_id, row.good_id, row.unit_id)
                        == (sale.principal_id, sale.good_id, sale.unit_id)
                })
                .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
            stock.quantity = stock
                .quantity
                .checked_add(sale.quantity)
                .ok_or(MaterialCircuitError::Arithmetic)?;
        }
        selling
            .transfers
            .push(economy.book.settle_purchase(id, sale.quantity)?.transfer);
        economy.book.retire_purchase(id)?;
    }
    let done: BTreeSet<_> = handed_over.iter().map(|&(id, _)| id).collect();
    state
        .final_demand_orders
        .retain(|row| !done.contains(&row.order_id));
    Ok(handed)
}

fn fund_order(
    book: &mut MonetaryBook,
    demand: &HouseholdDemandReceipt,
) -> Result<(FinalDemandOrder, MoneyTransferReceipt)> {
    let movement = book.reserve_purchase(PurchaseEscrow::new(
        OutboundOrderId::LocalFinalDemand(demand.order_id),
        AccountId::Household(demand.principal_id),
        AccountId::Site(demand.retailer_site_id),
        demand.admitted_quantity,
        demand.unit_price,
    )?)?;
    Ok((
        FinalDemandOrder {
            order_id: demand.order_id,
            retailer_site_id: demand.retailer_site_id,
            demand_principal_id: demand.principal_id,
            good_id: demand.good_id,
            unit_id: demand.unit_id,
            ordered: demand.admitted_quantity,
            fulfilled: 0,
        },
        movement,
    ))
}

fn validate_demand_receipts(
    catalog: &MaterialCatalog,
    rows: &RecurringEconomy,
    period: u64,
    demands: &[HouseholdDemandReceipt],
) -> Result<()> {
    if demands.len() != rows.household_stocks.len() {
        return Err(MaterialCircuitError::FinalDemandInvariant);
    }
    let policies: BTreeMap<_, _> = rows
        .household_purchases
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r))
        .collect();
    let required = requirements(catalog, rows)?;
    let stocks: BTreeMap<_, _> = rows
        .household_stocks
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r.quantity))
        .collect();
    let offers: BTreeMap<_, _> = rows
        .offers
        .iter()
        .map(|r| ((r.site_id, r.good_id, r.unit_id), r.unit_price))
        .collect();
    let mut seen = BTreeSet::new();
    for demand in demands {
        let key = (demand.principal_id, demand.good_id, demand.unit_id);
        let policy = policies
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let required_quantity = *required
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let opening_stock = *stocks
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let desired_quantity = desired(
            required_quantity,
            policy.target_closing_stock,
            opening_stock,
        )?;
        let requested_quantity = if policy.enabled {
            desired_quantity.min(policy.maximum_purchase)
        } else {
            0
        };
        let unit_price = offers
            .get(&(policy.retailer_site_id, policy.good_id, policy.unit_id))
            .ok_or(MaterialCircuitError::PurchaseInvariant)?;
        if (
            demand.required_quantity,
            demand.opening_stock,
            demand.desired_quantity,
            demand.requested_quantity,
            demand.unit_price,
        ) != (
            required_quantity,
            opening_stock,
            desired_quantity,
            requested_quantity,
            *unit_price,
        ) {
            return Err(MaterialCircuitError::FinalDemandInvariant);
        }
        if !seen.insert(key)
            || demand.period != period
            || demand.order_id != recurring_household_order_id(period, key)
            || demand.retailer_site_id != policy.retailer_site_id
            || demand.unit_price.micro_units() <= 0
            || demand.admitted_quantity > demand.requested_quantity
            || demand.requested_quantity > demand.desired_quantity
            || demand.fulfilled_quantity != 0
            || demand.expired_quantity != 0
        {
            return Err(MaterialCircuitError::FinalDemandInvariant);
        }
    }
    Ok(())
}

fn validate_handoff(
    order: &FinalDemandOrder,
    receipt: &LocalRetailFulfillmentReceipt,
) -> Result<()> {
    if receipt.quantity == 0
        || receipt.retailer_site_id != order.retailer_site_id
        || receipt.demand_principal_id != order.demand_principal_id
        || receipt.good_id != order.good_id
        || receipt.unit_id != order.unit_id
        || order.fulfilled > order.ordered
    {
        return Err(MaterialCircuitError::FinalDemandInvariant);
    }
    Ok(())
}

/// Credit and settle new handoffs once, then expire only generated principals.
/// A prior finite household order remains open for its undelivered remainder.
pub(crate) fn complete_household_orders(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
    demands: &mut [HouseholdDemandReceipt],
    handoffs: &[LocalRetailFulfillmentReceipt],
    transfers: &mut Vec<MoneyTransferReceipt>,
) -> Result<()> {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(());
    };
    let Some(rows) = &mut economy.recurring else {
        return Ok(());
    };
    household_phase(rows, state.period)?;
    validate_demand_receipts(catalog, rows, state.period, demands)?;
    if handoffs.len() > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(MaterialCircuitError::RowLimit);
    }
    let household_ids: BTreeSet<_> = rows.households.iter().map(|r| r.principal_id).collect();
    let physical: BTreeMap<_, _> = state
        .final_demand_orders
        .iter()
        .map(|r| (r.order_id, r))
        .collect();
    let mut stock: BTreeMap<_, _> = rows
        .household_stocks
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r.quantity))
        .collect();
    let mut book = economy.book.clone();
    let mut movements = vec![];
    let mut seen = BTreeSet::new();
    let mut ordered: Vec<_> = handoffs.iter().collect();
    ordered.sort_by_key(|receipt| receipt.order_id);
    for receipt in ordered {
        if !seen.insert(receipt.order_id) {
            return Err(MaterialCircuitError::DuplicateRow);
        }
        let order = physical
            .get(&receipt.order_id)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        validate_handoff(order, receipt)?;
        if !household_ids.contains(&receipt.demand_principal_id) {
            continue;
        }
        let id = OutboundOrderId::LocalFinalDemand(receipt.order_id);
        let purchase = book.purchase(id)?;
        if purchase.buyer != AccountId::Household(receipt.demand_principal_id)
            || purchase.seller != AccountId::Site(receipt.retailer_site_id)
            || purchase.quantity != order.ordered
            || purchase.refunded != 0
            || purchase.delivered.checked_add(receipt.quantity) != Some(order.fulfilled)
        {
            return Err(MaterialCircuitError::PurchaseInvariant);
        }
        let quantity = stock
            .get_mut(&(
                receipt.demand_principal_id,
                receipt.good_id,
                receipt.unit_id,
            ))
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        *quantity = quantity
            .checked_add(receipt.quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        movements.push(book.settle_purchase(id, order.fulfilled)?.transfer);
    }
    let mut resolved = demands.to_vec();
    let mut retired = BTreeSet::new();
    for demand in &mut resolved {
        if let Some(id) =
            resolve_generated_order(&mut book, &physical, demand, &seen, &mut movements)?
        {
            retired.insert(id);
        }
    }
    let mut next_stocks = rows.household_stocks.clone();
    for row in &mut next_stocks {
        row.quantity = *stock
            .get(&(row.principal_id, row.good_id, row.unit_id))
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
    }
    rows.household_stocks = next_stocks;
    economy.book = book;
    state
        .final_demand_orders
        .retain(|row| !retired.contains(&row.order_id));
    demands.clone_from_slice(&resolved);
    transfers.extend(movements);
    Ok(())
}

fn resolve_generated_order(
    book: &mut MonetaryBook,
    physical: &BTreeMap<OrderId, &FinalDemandOrder>,
    demand: &mut HouseholdDemandReceipt,
    seen: &BTreeSet<OrderId>,
    movements: &mut Vec<MoneyTransferReceipt>,
) -> Result<Option<OrderId>> {
    let id = OutboundOrderId::LocalFinalDemand(demand.order_id);
    if demand.admitted_quantity == 0 {
        if physical.contains_key(&demand.order_id) || book.purchase(id).is_ok() {
            return Err(MaterialCircuitError::PurchaseInvariant);
        }
        return Ok(None);
    }
    let order = physical
        .get(&demand.order_id)
        .ok_or(MaterialCircuitError::PurchaseInvariant)?;
    let purchase = book.purchase(id)?;
    if order.ordered != demand.admitted_quantity
        || order.demand_principal_id != demand.principal_id
        || order.retailer_site_id != demand.retailer_site_id
        || order.good_id != demand.good_id
        || order.unit_id != demand.unit_id
        || purchase.quantity != demand.admitted_quantity
        || purchase.unit_price != demand.unit_price
        || purchase.buyer != AccountId::Household(demand.principal_id)
        || purchase.seller != AccountId::Site(demand.retailer_site_id)
        || purchase.delivered != order.fulfilled
        || purchase.refunded != 0
        || (order.fulfilled > 0 && !seen.contains(&demand.order_id))
    {
        return Err(MaterialCircuitError::PurchaseInvariant);
    }
    demand.fulfilled_quantity = order.fulfilled;
    demand.expired_quantity = demand
        .admitted_quantity
        .checked_sub(order.fulfilled)
        .ok_or(MaterialCircuitError::PurchaseInvariant)?;
    if demand.expired_quantity > 0 {
        movements.push(book.refund_purchase(id, demand.expired_quantity)?.transfer);
    }
    book.retire_purchase(id)?;
    Ok(Some(demand.order_id))
}

/// Consume this period's need from actual stock; unmet units are evidence, not debt.
pub(crate) fn consume_household_needs(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
) -> Result<Vec<HouseholdConsumptionReceipt>> {
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        return Ok(vec![]);
    };
    let Some(rows) = &mut economy.recurring else {
        return Ok(vec![]);
    };
    household_phase(rows, state.period)?;
    let existing: BTreeSet<_> = state
        .final_demand_orders
        .iter()
        .map(|r| r.order_id)
        .collect();
    for policy in &rows.household_purchases {
        let id = recurring_household_order_id(
            state.period,
            (policy.principal_id, policy.good_id, policy.unit_id),
        );
        if existing.contains(&id)
            || economy
                .book
                .purchase(OutboundOrderId::LocalFinalDemand(id))
                .is_ok()
        {
            return Err(MaterialCircuitError::PurchaseInvariant);
        }
    }
    refuse_open_want_orders(
        catalog,
        &economy.book,
        &state.final_demand_orders,
        state.period,
    )?;
    let receipts = preview_household_needs(catalog, rows, state.period)?;
    let closing: BTreeMap<_, _> = receipts
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r.closing_quantity))
        .collect();
    let mut next_stocks = rows.household_stocks.clone();
    for row in &mut next_stocks {
        row.quantity = *closing
            .get(&(row.principal_id, row.good_id, row.unit_id))
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
    }
    rows.household_stocks = next_stocks;
    rows.last_household_consumption_period = state.period;
    Ok(receipts)
}

/// A want is bought and retired inside the household moment: no order or reserve of the period may
/// still carry a want's order identity.
fn refuse_open_want_orders(
    catalog: &MaterialCatalog,
    book: &MonetaryBook,
    orders: &[FinalDemandOrder],
    period: u64,
) -> Result<()> {
    let Some(policy) = &catalog.market_clearing else {
        return Ok(());
    };
    let ids: BTreeSet<OrderId> = policy
        .household_wants
        .iter()
        .map(|want| {
            crate::tiers::recurring_household_want_order_id(
                period,
                (want.principal_id, want.good_id, want.unit_id),
                want.tier,
            )
        })
        .collect();
    if orders.iter().any(|r| ids.contains(&r.order_id))
        || ids
            .iter()
            .any(|&id| book.purchase(OutboundOrderId::LocalFinalDemand(id)).is_ok())
    {
        return Err(MaterialCircuitError::PurchaseInvariant);
    }
    Ok(())
}

pub(crate) fn preview_household_needs(
    catalog: &MaterialCatalog,
    rows: &RecurringEconomy,
    period: u64,
) -> Result<Vec<HouseholdConsumptionReceipt>> {
    let needed = requirements(catalog, rows)?;
    let stocks: BTreeMap<_, _> = rows
        .household_stocks
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r.quantity))
        .collect();
    let mut receipts = vec![];
    for (key, required_quantity) in needed {
        if !stocks.contains_key(&key) {
            continue;
        }
        let available_quantity = *stocks
            .get(&key)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let consumed_quantity = available_quantity.min(required_quantity);
        receipts.push(HouseholdConsumptionReceipt {
            period,
            principal_id: key.0,
            good_id: key.1,
            unit_id: key.2,
            required_quantity,
            available_quantity,
            consumed_quantity,
            unmet_quantity: required_quantity - consumed_quantity,
            closing_quantity: available_quantity - consumed_quantity,
        });
    }
    Ok(receipts)
}

#[cfg(test)]
mod open_want_order_tests {
    use super::*;
    use crate::{
        CapacitySupply, CommodityDefinition, CommodityKind, HouseholdNeed, HouseholdNeedBasis,
        HouseholdWant, MarketClearingPolicy, MaterialCatalogDefinition, WantTier,
    };

    fn principal() -> FinalDemandPrincipalId {
        FinalDemandPrincipalId::from_bytes([9; 32])
    }
    fn good(n: u8) -> GoodId {
        GoodId::from_bytes([n; 32])
    }
    fn unit(n: u8) -> UnitId {
        UnitId::from_bytes([n; 32])
    }

    fn want(n: u8, tier: WantTier) -> HouseholdWant {
        HouseholdWant {
            principal_id: principal(),
            tier,
            good_id: good(n),
            unit_id: unit(n),
            basis: HouseholdNeedBasis::Persons,
            units_per_basis: 1,
        }
    }

    /// Two wants, a comfort of good 2 and a luxury of good 3, over a need of good 1.
    fn catalog() -> MaterialCatalog {
        let commodity = |n: u8| CommodityDefinition {
            good_id: good(n),
            unit_id: unit(n),
            kind: CommodityKind::Storable { grams_per_unit: 1 },
        };
        MaterialCatalog::try_new(MaterialCatalogDefinition {
            company_portfolios: None,
            company_payouts: vec![],
            capacity_policy: CapacitySupply::FiniteSchedule,
            site_logistics_nodes: vec![],
            process_outputs: vec![],
            input_coefficients: vec![],
            labor_coefficients: vec![],
            commodities: vec![commodity(1), commodity(2), commodity(3)],
            supplier_routes: vec![],
            route_stages: vec![],
            merchants: vec![],
            handling_coefficients: vec![],
            maintenance_binding: None,
            aid_mandates: vec![],
            household_time_policy: vec![],
            service_inputs: vec![],
            household_needs: vec![HouseholdNeed {
                principal_id: principal(),
                good_id: good(1),
                unit_id: unit(1),
                basis: HouseholdNeedBasis::Persons,
                units_per_basis: 1,
            }],
            market_clearing: Some(MarketClearingPolicy {
                paying_order: vec![(good(1), unit(1)), (good(2), unit(2)), (good(3), unit(3))],
                household_wants: vec![want(2, WantTier::Comfort), want(3, WantTier::Luxury)],
            }),
        })
        .expect("the fixture catalog is valid")
    }

    fn order(id: OrderId) -> FinalDemandOrder {
        FinalDemandOrder {
            order_id: id,
            retailer_site_id: SiteId::from_bytes([5; 32]),
            demand_principal_id: principal(),
            good_id: good(2),
            unit_id: unit(2),
            ordered: 1,
            fulfilled: 0,
        }
    }

    fn id_of(n: u8, tier: WantTier, period: u64) -> OrderId {
        crate::tiers::recurring_household_want_order_id(
            period,
            (principal(), good(n), unit(n)),
            tier,
        )
    }

    #[test]
    fn the_second_wants_open_order_is_refused_among_three_orders() {
        let catalog = catalog();
        let book = MonetaryBook::open(vec![]).expect("an empty book opens");
        let others = [OrderId::from_bytes([1; 32]), OrderId::from_bytes([2; 32])];
        let open = id_of(3, WantTier::Luxury, 4);
        let orders = [order(others[0]), order(open), order(others[1])];
        assert_eq!(
            refuse_open_want_orders(&catalog, &book, &orders, 4),
            Err(MaterialCircuitError::PurchaseInvariant)
        );
        // The same orders of another period carry no want's identity of this one.
        assert_eq!(refuse_open_want_orders(&catalog, &book, &orders, 5), Ok(()));
    }
}
