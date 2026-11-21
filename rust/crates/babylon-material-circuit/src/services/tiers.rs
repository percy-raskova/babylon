//! A stage's markets when households have wants: each household brings one bid per market, a rung
//! for its need and one for each want of the product, and the market prices the bids' totals.

use super::admission::{self, Request};
use super::{MaterialCircuitError, MaterialCircuitState, Result};
use crate::clearing::{self, BidRung, LadderBid, MarketMoment, MarketTable};
use crate::tiers::{HouseholdLists, ListRung};
use crate::valuation::CostClose;
use crate::{AccountId, CircuitAccounting, MaterialCatalog, OrderId};
use babylon_kernel::currency::Currency;
use std::collections::BTreeMap;

/// One buyer of a market: its need request, if it has one, and its want requests in tier order.
pub(super) struct Buyer<'a> {
    key: OrderId,
    account: AccountId,
    need: Option<&'a Request>,
    wants: Vec<&'a Request>,
    first: &'a Request,
}

/// One order to fund: what the buyer could pay for at the posted price, and what it bought.
pub(super) struct Taken<'a> {
    pub(super) request: &'a Request,
    pub(super) requested: u64,
    pub(super) quantity: u64,
}

/// The price of a market and the orders its buyers fund, in booking order.
pub(super) struct Cleared<'a> {
    pub(super) price: Currency,
    pub(super) taken: Vec<Taken<'a>>,
}

/// A market's requests, one buyer each, in the order of the need's identity; an account that only
/// wants the product sorts by the identity its need would have.
pub(super) fn buyers<'a>(period: u64, members: &[&'a Request]) -> Vec<Buyer<'a>> {
    let mut by_account = BTreeMap::<AccountId, Vec<&'a Request>>::new();
    for request in members {
        by_account.entry(request.buyer).or_default().push(request);
    }
    let mut buyers: Vec<Buyer<'a>> = by_account
        .into_iter()
        .map(|(account, mut requests)| {
            requests.sort_by_key(|r| (r.tier.is_some(), r.tier, r.order_id));
            let first = requests[0];
            let need = requests.iter().copied().find(|r| r.tier.is_none());
            Buyer {
                key: need.map_or_else(
                    || {
                        admission::recurring_service_order_id(
                            period,
                            account,
                            first.provider,
                            first.good,
                            first.unit,
                        )
                    },
                    |r| r.order_id,
                ),
                account,
                need,
                wants: requests.into_iter().filter(|r| r.tier.is_some()).collect(),
                first,
            }
        })
        .collect();
    buyers.sort_by_key(|b| b.key);
    buyers
}

/// What a buyer's bid is, with the order each rung is bought under.
struct Seat {
    bid: LadderBid,
    orders: Vec<OrderId>,
}

fn household_seat(lists: &HouseholdLists, buyer: &Buyer<'_>, cash: i128) -> Result<Option<Seat>> {
    let AccountId::Household(principal) = buyer.account else {
        return Ok(None);
    };
    let rungs: Vec<ListRung> = lists.rungs(
        principal,
        buyer.first.good,
        buyer.first.unit,
        buyer.need.map_or(0, |r| r.requested),
    )?;
    Ok(Some(Seat {
        bid: LadderBid {
            rungs: rungs.iter().map(|r| r.rung).collect(),
            purse: Currency::from_micro_units(cash.max(0)),
            limit: None,
        },
        orders: rungs.iter().map(|r| r.order_id).collect(),
    }))
}

fn business_seat(request: &Request, cash: i128, limit: Option<Currency>) -> Seat {
    Seat {
        bid: LadderBid {
            rungs: vec![BidRung {
                wanted: request.requested,
                reserve: Currency::from_micro_units(0),
            }],
            purse: Currency::from_micro_units(
                cash.saturating_sub(request.floor.micro_units()).max(0),
            ),
            limit,
        },
        orders: vec![request.order_id],
    }
}

fn wanted(seat: &Seat) -> Result<u64> {
    seat.bid
        .rungs
        .iter()
        .try_fold(0_u64, |sum, r| sum.checked_add(r.wanted))
        .ok_or(MaterialCircuitError::Arithmetic)
}

/// What each rung of a bid could pay for at the posted price: the market at that price with
/// everything on offer.
fn at_posted(seat: &Seat, posted: Currency) -> Result<Vec<u64>> {
    if wanted(seat)? == 0 || seat.bid.purse.micro_units() <= 0 {
        return Ok(vec![0; seat.bid.rungs.len()]);
    }
    let mut outcome =
        clearing::clear_ladder_market(u64::MAX, posted, std::slice::from_ref(&seat.bid))?;
    outcome
        .quantities
        .pop()
        .ok_or(MaterialCircuitError::MarketClearingInvariant)
}

fn lookup(rows: &[(OrderId, u64)], order: OrderId) -> u64 {
    rows.iter()
        .find(|(id, _)| *id == order)
        .map_or(0, |(_, quantity)| *quantity)
}

/// The bid of one buyer at a market: a household's rungs, or a business's one rung and its limit.
fn seat_of(
    books: (&MaterialCatalog, &MaterialCircuitState, &CostClose),
    lists: &HouseholdLists,
    buyer: &Buyer<'_>,
    pricing: (Currency, bool),
) -> Result<Seat> {
    let (catalog, state, costs) = books;
    let (posted, limited) = pricing;
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Err(MaterialCircuitError::MonetaryInvariant);
    };
    let cash = e.book.cash(buyer.account)?.micro_units();
    if let Some(seat) = household_seat(lists, buyer, cash)? {
        return Ok(seat);
    }
    let AccountId::Site(site) = buyer.account else {
        return Err(MaterialCircuitError::ServiceInvariant);
    };
    let request = buyer.need.ok_or(MaterialCircuitError::ServiceInvariant)?;
    // A business stops at its limit (P5); public provision has none.
    let limit = if limited {
        Some(clearing::limit_price(
            catalog,
            state,
            costs,
            site,
            request.good,
            request.unit,
            posted,
        )?)
    } else {
        None
    };
    Ok(business_seat(request, cash, limit))
}

/// Each seat's quantities per rung at the market's price, and the price. Records the market.
fn clear_seats(
    context: (&MaterialCircuitState, MarketMoment, &Request),
    seats: &[Seat],
    reachable: &[Vec<u64>],
    supply: Option<u64>,
    markets: &mut MarketTable,
) -> Result<(Currency, Vec<Vec<u64>>)> {
    let (state, moment, first) = context;
    let posted = admission::quote(state, first.provider, first.good, first.unit)?;
    let Some(supply) = supply else {
        return Ok((posted, reachable.to_vec()));
    };
    let bidding: Vec<usize> = (0..seats.len())
        .filter(|&i| wanted(&seats[i]).is_ok_and(|w| w > 0) && seats[i].bid.purse.micro_units() > 0)
        .collect();
    let bids: Vec<LadderBid> = bidding.iter().map(|&i| seats[i].bid.clone()).collect();
    let outcome = clearing::clear_ladder_market(supply, posted, &bids)?;
    markets.record(
        state.period,
        moment,
        (first.provider, first.good, first.unit),
        posted,
        supply,
        bids.len(),
        &outcome.totals()?,
    )?;
    let mut quantities: Vec<Vec<u64>> = seats.iter().map(|s| vec![0; s.orders.len()]).collect();
    for (&i, got) in bidding.iter().zip(outcome.quantities) {
        quantities[i] = got;
    }
    Ok((outcome.price, quantities))
}

fn paired(orders: &[OrderId], quantities: &[u64]) -> Vec<(OrderId, u64)> {
    orders
        .iter()
        .copied()
        .zip(quantities.iter().copied())
        .collect()
}

/// What a market's buyers get, the price they pay and the orders they fund. A want that money
/// cannot reach at the posted price leaves no order.
pub(super) fn price_market<'a>(
    books: (&MaterialCatalog, &MaterialCircuitState, &CostClose),
    moment: MarketMoment,
    members: &[&'a Request],
    supply: Option<u64>,
    tables: (&mut MarketTable, &mut HouseholdLists),
) -> Result<Cleared<'a>> {
    let state = books.1;
    let (markets, lists) = tables;
    let buyers = buyers(state.period, members);
    let first = buyers
        .first()
        .map(|b| b.first)
        .ok_or(MaterialCircuitError::MarketClearingInvariant)?;
    let posted = admission::quote(state, first.provider, first.good, first.unit)?;
    let seats = buyers
        .iter()
        .map(|buyer| seat_of(books, lists, buyer, (posted, supply.is_some())))
        .collect::<Result<Vec<_>>>()?;
    let reachable = seats
        .iter()
        .map(|seat| at_posted(seat, posted))
        .collect::<Result<Vec<_>>>()?;
    let (price, quantities) =
        clear_seats((state, moment, first), &seats, &reachable, supply, markets)?;
    let mut taken = vec![];
    for (i, buyer) in buyers.iter().enumerate() {
        let bought = paired(&seats[i].orders, &quantities[i]);
        let could = paired(&seats[i].orders, &reachable[i]);
        if let AccountId::Household(principal) = buyer.account {
            lists.settle(
                principal,
                buyer.first.good,
                buyer.first.unit,
                &bought,
                price,
            )?;
        }
        if let Some(request) = buyer.need {
            taken.push(Taken {
                request,
                requested: request.requested,
                quantity: lookup(&bought, request.order_id),
            });
        }
        for request in &buyer.wants {
            let requested = lookup(&could, request.order_id);
            let quantity = lookup(&bought, request.order_id);
            if quantity > requested {
                return Err(MaterialCircuitError::MarketClearingInvariant);
            }
            if requested > 0 {
                taken.push(Taken {
                    request,
                    requested,
                    quantity,
                });
            }
        }
    }
    Ok(Cleared { price, taken })
}

/// What a market's buyers could fund at the posted price, each spending from its scratch cash and
/// closing the items it buys in a scratch list. Returns the quantity.
pub(super) fn fund_market(
    state: &MaterialCircuitState,
    members: &[&Request],
    scratch: &mut BTreeMap<AccountId, i128>,
    lists: &mut HouseholdLists,
) -> Result<u64> {
    let CircuitAccounting::Monetary(e) = &state.accounting else {
        return Ok(0);
    };
    let buyers = buyers(state.period, members);
    let first = buyers
        .first()
        .map(|b| b.first)
        .ok_or(MaterialCircuitError::MarketClearingInvariant)?;
    let posted = admission::quote(state, first.provider, first.good, first.unit)?;
    let mut total = 0_u64;
    for buyer in &buyers {
        let cash = match scratch.get(&buyer.account) {
            Some(&cash) => cash,
            None => e.book.cash(buyer.account)?.micro_units(),
        };
        let seat = if let Some(seat) = household_seat(lists, buyer, cash)? {
            seat
        } else {
            business_seat(
                buyer.need.ok_or(MaterialCircuitError::ServiceInvariant)?,
                cash,
                None,
            )
        };
        let got = at_posted(&seat, posted)?;
        let bought: u64 = got
            .iter()
            .try_fold(0_u64, |sum, &q| sum.checked_add(q))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        scratch.insert(
            buyer.account,
            cash.saturating_sub(posted.micro_units().saturating_mul(i128::from(bought))),
        );
        if let AccountId::Household(principal) = buyer.account {
            let rows: Vec<(OrderId, u64)> = seat.orders.iter().copied().zip(got).collect();
            lists.settle(principal, buyer.first.good, buyer.first.unit, &rows, posted)?;
        }
        total = total
            .checked_add(bought)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(total)
}
