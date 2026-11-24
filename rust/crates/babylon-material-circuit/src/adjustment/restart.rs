//! An owner restarts a stopped workplace with the owner's own money (A17, A19 of ADR314; ADR318 L1), as mended in
//! round ten: the restart sits at the very end of the close, before staffing.
//!
//! In the order they act: a price that rested under one unit's cost is raised to it; every workplace counts
//! its quiet periods; a workplace that employed nobody for three quiet periods is tested on what its buyers
//! would pay and on whether the inputs of one batch can be had; its owner puts in the money from the owner's
//! own spare; and the bound of the next period is reckoned again, so that a restarted workplace may hire at
//! once. The money is capital: never paid back, never earnings.

use std::collections::{BTreeMap, BTreeSet};
use std::result::Result as StdResult;

use babylon_kernel::currency::Currency;

use super::bound::{self, HiringBound};
use super::policy;
use super::receipts::{
    AdjustmentReceipt, OwnerSpareReceipt, RestartReceipt, RestartTest, RestingPriceReceipt,
    RestingPriceToCostReceipt,
};
use super::rest;
use super::standing::{StopHold, WorkplaceStanding, WorkplaceStandingRow};
use crate::{
    AccountId, CashTransferPurpose, CircuitAccounting, GoodId, HistoricalCostBook, MaterialCatalog,
    MaterialCircuitError, MaterialCircuitState, MaterialCircuitTransition, MonetaryBook,
    MonetaryCircuit, MoneyTransferReceipt, RecurringEconomy, SiteId, UnitId,
};

type Result<T> = StdResult<T, MaterialCircuitError>;

/// The quiet periods a workplace counts before its restart is tested.
pub const RESTART_QUIET_PERIODS: u64 = 3;

/// What one batch of a workplace costs, makes, and sells for.
struct Output {
    /// The units of one batch: the process's output, or one unit for a merchant.
    per_batch: u64,
    /// The batches its capacity runs: the nameplate, or without limit for a merchant.
    nameplate: u64,
    /// The posted price of its product.
    price: i128,
}

/// One workplace that passed the sales test, with the figures its buyer reads.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Candidate {
    pub(crate) site: SiteId,
    /// What the batches it would run cost over the periods of outlay.
    pub(crate) plan: i128,
    /// What it would earn in a period by the test's own figures.
    pub(crate) earn: i128,
    /// What its owner puts in: the plan less the cash it holds.
    pub(crate) money: i128,
}

/// What the restart's test found of one workplace.
struct Tried {
    site: SiteId,
    cost: i128,
    turned: u64,
    inputs_short: bool,
    candidate: Option<Candidate>,
}

/// The money a restart puts in: the plan less the cash the workplace holds. `None` when that is nothing.
pub(crate) fn money_to_put_in(plan: i128, cash: i128) -> Option<i128> {
    let money = plan.checked_sub(cash)?;
    (money > 0).then_some(money)
}

/// The candidates in the order of what each would earn on the money put in, highest first; ties by site.
pub(crate) fn rank(candidates: &mut [Candidate]) {
    candidates.sort_by(|a, b| {
        let left = a.earn.checked_mul(b.plan);
        let right = b.earn.checked_mul(a.plan);
        right.cmp(&left).then(a.site.cmp(&b.site))
    });
}

/// The price a resting price is raised to: one unit's cost, rounded up to the micro-unit. `None` when the price
/// stands at it or above, or the batch makes nothing.
pub(crate) fn raised_price(batch_cost: i128, per_batch: u64, price: i128) -> Option<i128> {
    let output = i128::from(per_batch);
    if output <= 0 {
        return None;
    }
    let unit = batch_cost.checked_add(output.checked_sub(1)?)? / output;
    (price < unit).then_some(unit)
}

/// Whether a workplace is tested: it offered no hours and has been quiet long enough.
pub(crate) fn is_tested(row: &WorkplaceStandingRow, offered_hours: bool) -> bool {
    !offered_hours && row.quiet_periods >= RESTART_QUIET_PERIODS
}

/// One more close of a workplace: both counters go to 0 if it made or sold anything, else up by one.
pub(crate) fn count(row: &mut WorkplaceStandingRow, made_or_sold: bool) -> Result<()> {
    if made_or_sold {
        row.periods_since_work = 0;
        row.quiet_periods = 0;
    } else {
        row.periods_since_work = row
            .periods_since_work
            .checked_add(1)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        row.quiet_periods = row
            .quiet_periods
            .checked_add(1)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(())
}

/// Seat the candidates in order: each is bought by its owner when what is left of that owner's spare covers the
/// money, and takes it out. A candidate whose owner cannot pay, or that has no owner, gets `None`.
pub(crate) fn seat(
    candidates: &[Candidate],
    owner_of: impl Fn(SiteId) -> Option<AccountId>,
    spare: &mut BTreeMap<AccountId, i128>,
) -> Vec<(SiteId, Option<AccountId>)> {
    candidates
        .iter()
        .map(|candidate| {
            let owner = owner_of(candidate.site).filter(|owner| {
                spare
                    .get(owner)
                    .is_some_and(|left| *left >= candidate.money)
            });
            if let Some(left) = owner.and_then(|owner| spare.get_mut(&owner)) {
                *left -= candidate.money;
            }
            (candidate.site, owner)
        })
        .collect()
}

/// An owner's capital paid into a workplace: the money moves with its receipt and the cost book carries it.
///
/// # Errors
/// A circuit refusal when the owner holds less than `money` or the book does not hold the accounts.
pub(crate) fn put_in(
    book: &mut MonetaryBook,
    costs: &mut HistoricalCostBook,
    owner: AccountId,
    site: SiteId,
    money: i128,
) -> Result<MoneyTransferReceipt> {
    let amount = Currency::from_micro_units(money);
    let receipt = book.transfer_cash(
        owner,
        AccountId::Site(site),
        amount,
        CashTransferPurpose::CapitalContribution,
    )?;
    costs.add_contribution(owner, site, amount)?;
    Ok(receipt)
}

fn economy_of(state: &MaterialCircuitState) -> Result<(&MonetaryCircuit, &RecurringEconomy)> {
    match &state.accounting {
        CircuitAccounting::Monetary(economy) => economy
            .recurring
            .as_deref()
            .map(|recurring| (&**economy, recurring))
            .ok_or(MaterialCircuitError::MonetaryInvariant),
        CircuitAccounting::PhysicalControl => Err(MaterialCircuitError::MonetaryInvariant),
    }
}

fn posted(recurring: &RecurringEconomy, site: SiteId, good: GoodId, unit: UnitId) -> Option<i128> {
    recurring
        .offers
        .iter()
        .find(|offer| (offer.site_id, offer.good_id, offer.unit_id) == (site, good, unit))
        .map(|offer| offer.unit_price.micro_units())
}

/// The largest `Wage` rate of a site's employment terms.
fn rate_of(economy: &MonetaryCircuit, site: SiteId) -> i128 {
    crate::recurring::spare_money::wages(economy)
        .into_iter()
        .filter(|((owner, _), _)| *owner == site)
        .map(|(_, rate)| rate)
        .max()
        .unwrap_or(0)
}

/// One batch's cost: a maker's hours at `rate` and each input at the highest posted price among its provider's
/// offers; a merchant's hours a unit at `rate` and its supplier's posted price (one unit a batch).
///
/// # Errors
/// `Arithmetic`, or `MonetaryInvariant` for a state with no recurring economy.
pub(crate) fn batch_cost(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    site: SiteId,
    rate: i128,
) -> Result<Option<i128>> {
    let (_, recurring) = economy_of(state)?;
    let arithmetic = MaterialCircuitError::Arithmetic;
    if let Some(policy) = recurring.production.iter().find(|row| row.site_id == site) {
        let hours = catalog
            .labor_coefficients
            .iter()
            .filter(|row| row.process_id == policy.process_id)
            .try_fold(0_u64, |sum, row| sum.checked_add(row.quantity_per_batch))
            .ok_or(arithmetic)?;
        let mut cost = i128::from(hours).checked_mul(rate).ok_or(arithmetic)?;
        for input in catalog
            .input_coefficients
            .iter()
            .filter(|row| row.process_id == policy.process_id)
        {
            let provider = catalog
                .service_inputs
                .iter()
                .find(|row| {
                    row.buyer_site_id == site
                        && row.good_id == input.good_id
                        && row.unit_id == input.unit_id
                })
                .map(|row| row.provider_site_id);
            let price = recurring
                .offers
                .iter()
                .filter(|offer| offer.good_id == input.good_id && offer.unit_id == input.unit_id)
                .filter(|offer| provider.is_none_or(|provider| offer.site_id == provider))
                .map(|offer| offer.unit_price.micro_units())
                .max();
            let Some(price) = price else {
                return Ok(None);
            };
            cost = i128::from(input.quantity_per_batch)
                .checked_mul(price)
                .and_then(|inputs| cost.checked_add(inputs))
                .ok_or(arithmetic)?;
        }
        return Ok(Some(cost));
    }
    let Some(handling) = catalog
        .handling_coefficients
        .iter()
        .find(|row| row.site_id == site)
    else {
        return Ok(None);
    };
    let supplier = recurring.replenishment.iter().find(|row| {
        row.buyer_site_id == site
            && row.good_id == handling.good_id
            && row.unit_id == handling.unit_id
    });
    let Some(price) = supplier.and_then(|row| {
        posted(
            recurring,
            row.supplier_site_id,
            handling.good_id,
            handling.unit_id,
        )
    }) else {
        return Ok(None);
    };
    Ok(i128::from(handling.hours_per_unit)
        .checked_mul(rate)
        .and_then(|hours| hours.checked_add(price)))
}

/// What one batch of a workplace makes, how many its capacity runs, and its posted price.
fn output_of(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    site: SiteId,
    next_period: u64,
) -> Result<Option<Output>> {
    let (_, recurring) = economy_of(state)?;
    if let Some(policy) = recurring.production.iter().find(|row| row.site_id == site) {
        let Some(out) = catalog
            .process_outputs
            .iter()
            .find(|row| row.process_id == policy.process_id)
        else {
            return Ok(None);
        };
        let nameplate = crate::capacity::process_available(
            catalog,
            state,
            policy.process_id,
            site,
            next_period,
        )?;
        return Ok(
            posted(recurring, site, out.good_id, out.unit_id).map(|price| Output {
                per_batch: out.quantity_per_batch,
                nameplate,
                price,
            }),
        );
    }
    Ok(catalog
        .handling_coefficients
        .iter()
        .find(|row| row.site_id == site)
        .and_then(|row| posted(recurring, site, row.good_id, row.unit_id))
        .map(|price| Output {
            per_batch: 1,
            nameplate: u64::MAX,
            price,
        }))
}

/// Every workplace the rules count: the sites of the employment terms, in site order.
fn workplaces(state: &MaterialCircuitState) -> Result<BTreeSet<SiteId>> {
    let (economy, _) = economy_of(state)?;
    Ok(economy.employment.iter().map(|row| row.site_id).collect())
}

/// Step (b): a price that rested at this close and stands under one unit's cost is raised to that cost. The
/// period's price and service market receipts get the new price, and each raise has a receipt. Whether any
/// price moved.
fn raise_resting_prices(
    catalog: &MaterialCatalog,
    transition: &mut MaterialCircuitTransition,
) -> Result<bool> {
    let rested: BTreeSet<SiteId> = transition
        .adjustments
        .iter()
        .filter_map(|row| match row {
            AdjustmentReceipt::RestingPrice(RestingPriceReceipt { site_id, .. }) => Some(*site_id),
            _ => None,
        })
        .collect();
    let closing = transition.state.period;
    let next_period = closing
        .checked_add(1)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let mut lifts = Vec::new();
    for site in rested {
        let (economy, _) = economy_of(&transition.state)?;
        let rate = rate_of(economy, site);
        let (Some(cost), Some(output)) = (
            batch_cost(catalog, &transition.state, site, rate)?,
            output_of(catalog, &transition.state, site, next_period)?,
        ) else {
            continue;
        };
        if let Some(unit) = raised_price(cost, output.per_batch, output.price) {
            lifts.push((site, output.price, unit));
        }
    }
    for &(site, old, unit) in &lifts {
        let raised = Currency::from_micro_units(unit);
        if let CircuitAccounting::Monetary(economy) = &mut transition.state.accounting {
            if let Some(recurring) = economy.recurring.as_mut() {
                for offer in recurring.offers.iter_mut().filter(|o| o.site_id == site) {
                    offer.unit_price = raised;
                }
            }
        }
        for row in transition.prices.iter_mut().filter(|r| r.site_id == site) {
            row.next_price = raised;
        }
        for row in transition
            .service_markets
            .iter_mut()
            .filter(|r| r.site_id == site)
        {
            row.next_price = raised;
        }
        transition
            .adjustments
            .push(AdjustmentReceipt::RestingPriceToCost(
                RestingPriceToCostReceipt {
                    period: closing,
                    site_id: site,
                    old: Currency::from_micro_units(old),
                    raised,
                },
            ));
    }
    Ok(!lifts.is_empty())
}

/// What a workplace sold and made in the closing period, as the prototype read them: it made or sold anything
/// when it sold something, or it has a recurring production row and made or took in something.
fn made_or_sold(
    catalog: &MaterialCatalog,
    transition: &MaterialCircuitTransition,
    site: SiteId,
) -> Result<bool> {
    let arithmetic = MaterialCircuitError::Arithmetic;
    let (_, recurring) = economy_of(&transition.state)?;
    let sold = transition
        .local_transfers
        .iter()
        .filter(|row| row.supplier_site_id == site)
        .map(|row| row.quantity)
        .chain(
            transition
                .local_fulfillments
                .iter()
                .filter(|row| row.retailer_site_id == site)
                .map(|row| row.quantity),
        )
        .chain(
            transition
                .service_markets
                .iter()
                .filter(|row| row.site_id == site)
                .map(|row| row.performed_quantity),
        )
        .try_fold(0_u64, u64::checked_add)
        .ok_or(arithmetic)?;
    if sold > 0 {
        return Ok(true);
    }
    if !recurring.production.iter().any(|row| row.site_id == site) {
        return Ok(false);
    }
    let mut made = 0_u64;
    for row in transition.production.iter().filter(|r| r.site_id == site) {
        let per_batch = catalog
            .process_outputs
            .iter()
            .find(|out| out.process_id == row.process_id)
            .ok_or(MaterialCircuitError::ProcessInvariant)?
            .quantity_per_batch;
        made = row
            .produced_batches
            .checked_mul(per_batch)
            .ok_or(arithmetic)?;
    }
    let taken = transition
        .local_transfers
        .iter()
        .filter(|row| row.buyer_site_id == site)
        .try_fold(0_u64, |sum, row| sum.checked_add(row.quantity))
        .ok_or(arithmetic)?;
    Ok(made.checked_add(taken).ok_or(arithmetic)? > 0)
}

/// An owner's money beyond one period of its own need at the posted prices: its cash less the goods and
/// services its household requires. Each owner of a workplace, in account order.
fn owner_spares(transition: &MaterialCircuitTransition) -> Result<BTreeMap<AccountId, i128>> {
    let arithmetic = MaterialCircuitError::Arithmetic;
    let (economy, recurring) = economy_of(&transition.state)?;
    let mut spares = BTreeMap::new();
    for owner in economy.financial.ownership.iter().map(|c| c.beneficiary) {
        let cash = economy.book.cash(owner)?.micro_units();
        let mut need = 0_i128;
        if let AccountId::Household(principal) = owner {
            let wanted = transition
                .household_consumption
                .iter()
                .filter(|row| row.principal_id == principal)
                .map(|row| (row.good_id, row.unit_id, row.required_quantity))
                .chain(
                    transition
                        .household_services
                        .iter()
                        .filter(|row| row.principal_id == principal)
                        .map(|row| (row.good_id, row.unit_id, row.required_quantity)),
                );
            for (good, unit, quantity) in wanted {
                let Some(purchase) = recurring.household_purchases.iter().find(|row| {
                    row.principal_id == principal && row.good_id == good && row.unit_id == unit
                }) else {
                    continue;
                };
                let price = posted(recurring, purchase.retailer_site_id, good, unit)
                    .ok_or(MaterialCircuitError::PurchaseInvariant)?;
                need = i128::from(quantity)
                    .checked_mul(price)
                    .and_then(|cost| need.checked_add(cost))
                    .ok_or(arithmetic)?;
            }
        }
        spares.insert(owner, cash.checked_sub(need).ok_or(arithmetic)?);
    }
    Ok(spares)
}

/// The holder of a workplace's ownership claim: the first claim of the state's rows.
fn holder_of(state: &MaterialCircuitState, site: SiteId) -> Option<AccountId> {
    match &state.accounting {
        CircuitAccounting::Monetary(economy) => economy
            .financial
            .ownership
            .iter()
            .find(|claim| claim.issuer_site_id == site)
            .map(|claim| claim.beneficiary),
        CircuitAccounting::PhysicalControl => None,
    }
}

/// Whether the inputs of one batch of `site` can be had at this close: it holds each, or each it lacks is made
/// by a supplier that employs people and made it in the period that closed, and that the bound of this close lets
/// it buy: what the supplier plans to make for the next period (capped at nameplate and at its own bound) less
/// what its other buyers took, within the policy's caps for a service. A merchant's batch is one unit of each
/// good it handles.
fn inputs_can_be_had(
    catalog: &MaterialCatalog,
    transition: &MaterialCircuitTransition,
    bound: &HiringBound,
    site: SiteId,
) -> Result<bool> {
    let state = &transition.state;
    let (_, recurring) = economy_of(state)?;
    let held = |good: GoodId, unit: UnitId| -> u64 {
        state
            .inventory
            .iter()
            .filter(|row| row.site_id == site && row.good_id == good && row.unit_id == unit)
            .map(|row| row.quantity)
            .fold(0, u64::saturating_add)
    };
    let needs: Vec<(GoodId, UnitId, u64)> =
        if let Some(policy) = recurring.production.iter().find(|row| row.site_id == site) {
            catalog
                .input_coefficients
                .iter()
                .filter(|row| row.process_id == policy.process_id && row.quantity_per_batch > 0)
                .map(|row| (row.good_id, row.unit_id, row.quantity_per_batch))
                .collect()
        } else {
            catalog
                .handling_coefficients
                .iter()
                .filter(|row| row.site_id == site)
                .map(|row| (row.good_id, row.unit_id, 1))
                .collect()
        };
    for (good, unit, per_batch) in needs {
        let have = held(good, unit);
        if have >= per_batch {
            continue;
        }
        let Some((supplier, limit)) = supplier_of(catalog, recurring, site, good, unit) else {
            return Ok(false);
        };
        let planned = planned_by(catalog, transition, bound, supplier, (good, unit))?;
        let Some(planned) = planned else {
            return Ok(false);
        };
        let service = crate::services::is_service(catalog, good, unit);
        let others = taken_by_others(transition, service, supplier, site, (good, unit))?;
        let for_me = planned.saturating_sub(others).min(limit);
        if for_me < per_batch.saturating_sub(have) {
            return Ok(false);
        }
    }
    Ok(true)
}

/// Who supplies `good` to `site`, and the most it may buy from them in a period.
fn supplier_of(
    catalog: &MaterialCatalog,
    recurring: &RecurringEconomy,
    site: SiteId,
    good: GoodId,
    unit: UnitId,
) -> Option<(SiteId, u64)> {
    if crate::services::is_service(catalog, good, unit) {
        catalog
            .service_inputs
            .iter()
            .find(|row| row.buyer_site_id == site && row.good_id == good && row.unit_id == unit)
            .map(|row| {
                (
                    row.provider_site_id,
                    row.quantity_per_period.min(row.maximum_purchase),
                )
            })
    } else {
        recurring
            .replenishment
            .iter()
            .find(|row| row.buyer_site_id == site && row.good_id == good && row.unit_id == unit)
            .map(|row| (row.supplier_site_id, u64::MAX))
    }
}

/// What a supplier plans to make of a product for the next period, when it works and made the product in the
/// period that closed; `None` when it does not.
fn planned_by(
    catalog: &MaterialCatalog,
    transition: &MaterialCircuitTransition,
    bound: &HiringBound,
    supplier: SiteId,
    (good, unit): (GoodId, UnitId),
) -> Result<Option<u64>> {
    let state = &transition.state;
    let (_, recurring) = economy_of(state)?;
    let outputs: Vec<_> = catalog
        .process_outputs
        .iter()
        .filter(|row| row.site_id == supplier && row.good_id == good && row.unit_id == unit)
        .collect();
    let made_last = transition
        .production
        .iter()
        .filter(|row| outputs.iter().any(|out| out.process_id == row.process_id))
        .try_fold(0_u64, |sum, row| sum.checked_add(row.produced_batches))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    if !rest::made_hours(state, supplier) || made_last == 0 {
        return Ok(None);
    }
    let mut planned = 0_u64;
    for out in outputs {
        let nameplate = crate::capacity::process_available(
            catalog,
            state,
            out.process_id,
            supplier,
            bound.next_period,
        )?;
        let mut batches = recurring
            .production
            .iter()
            .find(|row| row.process_id == out.process_id)
            .map_or(0, |row| row.planned_batches)
            .min(nameplate);
        if let Some(&(own, _)) = bound.process.get(&out.process_id) {
            batches = batches.min(own);
        }
        planned = batches
            .checked_mul(out.quantity_per_batch)
            .and_then(|made| planned.checked_add(made))
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(Some(planned))
}

/// What a supplier's other buyers took of a product in the period that closed: a service it performed for
/// buyers other than `site`, or goods it sold to other buyers and to households.
fn taken_by_others(
    transition: &MaterialCircuitTransition,
    service: bool,
    supplier: SiteId,
    site: SiteId,
    (good, unit): (GoodId, UnitId),
) -> Result<u64> {
    let taken: Vec<u64> = if service {
        transition
            .service_performance
            .iter()
            .filter(|row| {
                row.provider_site_id == supplier
                    && row.good_id == good
                    && row.unit_id == unit
                    && row.buyer != AccountId::Site(site)
            })
            .map(|row| row.performed_quantity)
            .collect()
    } else {
        transition
            .local_transfers
            .iter()
            .filter(|row| {
                row.supplier_site_id == supplier
                    && row.good_id == good
                    && row.unit_id == unit
                    && row.buyer_site_id != site
            })
            .map(|row| row.quantity)
            .chain(
                transition
                    .local_fulfillments
                    .iter()
                    .filter(|row| {
                        row.retailer_site_id == supplier
                            && row.good_id == good
                            && row.unit_id == unit
                    })
                    .map(|row| row.quantity),
            )
            .collect()
    };
    taken
        .into_iter()
        .try_fold(0_u64, u64::checked_add)
        .ok_or(MaterialCircuitError::Arithmetic)
}

/// The sales test of one stopped workplace, and the inputs test: what its buyers could pay for at its price and
/// were not sold must cover one batch's cost.
fn try_site(
    catalog: &MaterialCatalog,
    transition: &MaterialCircuitTransition,
    bound: &HiringBound,
    site: SiteId,
    outlay_periods: u64,
) -> Result<Option<Tried>> {
    let arithmetic = MaterialCircuitError::Arithmetic;
    let (economy, _) = economy_of(&transition.state)?;
    let rate = rate_of(economy, site);
    let (Some(cost), Some(output)) = (
        batch_cost(catalog, &transition.state, site, rate)?,
        output_of(catalog, &transition.state, site, bound.next_period)?,
    ) else {
        return Ok(None);
    };
    let turned = transition
        .market_clearings
        .iter()
        .filter(|row| row.site_id == site)
        .try_fold(0_u64, |sum, row| {
            let short = row.demand_at_quote.checked_sub(row.sold_quantity)?;
            sum.checked_add(short)
        })
        .ok_or(arithmetic)?;
    let mut tried = Tried {
        site,
        cost,
        turned,
        inputs_short: false,
        candidate: None,
    };
    let per_batch = i128::from(output.per_batch);
    let revenue = i128::from(turned.min(output.per_batch))
        .checked_mul(output.price)
        .ok_or(arithmetic)?;
    if revenue <= cost {
        return Ok(Some(tried));
    }
    if !inputs_can_be_had(catalog, transition, bound, site)? {
        tried.inputs_short = true;
        return Ok(Some(tried));
    }
    let batches = (turned / output.per_batch).min(output.nameplate).max(1);
    let made = per_batch
        .checked_mul(i128::from(batches))
        .ok_or(arithmetic)?;
    let earn = i128::from(turned)
        .min(made)
        .checked_mul(output.price)
        .and_then(|sales| {
            i128::from(batches)
                .checked_mul(cost)
                .and_then(|spent| sales.checked_sub(spent))
        })
        .ok_or(arithmetic)?;
    let plan = i128::from(batches)
        .checked_mul(cost)
        .and_then(|batch| batch.checked_mul(i128::from(outlay_periods)))
        .ok_or(arithmetic)?;
    let cash = economy.book.cash(AccountId::Site(site))?.micro_units();
    tried.candidate = money_to_put_in(plan, cash).map(|money| Candidate {
        site,
        plan,
        earn,
        money,
    });
    Ok(Some(tried))
}

/// The restart at the very end of the close, before staffing; the module's note says the order. The caller has
/// the catalog's own word that it asks for the restart; `standing` is the closed period's own and `bound` the
/// bound reckoned at this close.
///
/// # Errors
/// `MarketClearingInvariant` when the catalog does not ask for the restart; a circuit refusal for arithmetic,
/// a missing price or a transfer the book refuses.
pub(crate) fn restart_stopped(
    catalog: &MaterialCatalog,
    transition: &mut MaterialCircuitTransition,
    standing: &mut WorkplaceStanding,
    bound: &mut HiringBound,
    next_period: u64,
) -> Result<()> {
    let outlay_periods = catalog
        .market_clearing
        .as_ref()
        .and_then(|order| policy::restart_outlay_periods(&order.adjustments))
        .ok_or(MaterialCircuitError::MarketClearingInvariant)?;
    if bound.next_period != next_period {
        return Err(MaterialCircuitError::MonetaryInvariant);
    }
    let mut moved = raise_resting_prices(catalog, transition)?;
    let sites = workplaces(&transition.state)?;
    for site in &sites {
        let did = made_or_sold(catalog, transition, *site)?;
        count(standing.row_mut(*site), did)?;
    }
    let period = transition.state.period;
    let mut spares = owner_spares(transition)?;
    transition
        .adjustments
        .extend(spares.iter().map(|(owner, spare)| {
            AdjustmentReceipt::OwnerSpare(OwnerSpareReceipt {
                period,
                owner: *owner,
                spare: Currency::from_micro_units(*spare),
            })
        }));
    let mut tried = Vec::new();
    for site in &sites {
        let tested = is_tested(
            &standing.row_of(*site),
            rest::made_hours(&transition.state, *site),
        );
        if tested {
            tried.extend(try_site(catalog, transition, bound, *site, outlay_periods)?);
        }
    }
    let mut candidates: Vec<Candidate> = tried.iter().filter_map(|row| row.candidate).collect();
    rank(&mut candidates);
    let seated = seat(
        &candidates,
        |site| holder_of(&transition.state, site),
        &mut spares,
    );
    let mut receipts = Vec::new();
    for row in &tried {
        let seat = seated.iter().find(|(site, _)| *site == row.site);
        let money = candidates
            .iter()
            .find(|c| c.site == row.site)
            .map_or(0, |c| c.money);
        let (test, owner) = match seat {
            _ if row.candidate.is_none() => (RestartTest::Failed, None),
            Some((_, Some(owner))) => (RestartTest::Restarted, Some(*owner)),
            _ => (RestartTest::NoBuyer, holder_of(&transition.state, row.site)),
        };
        if test == RestartTest::Restarted {
            moved = true;
            let Some(owner) = owner else { continue };
            let CircuitAccounting::Monetary(economy) = &mut transition.state.accounting else {
                return Err(MaterialCircuitError::MonetaryInvariant);
            };
            let transfer = put_in(
                &mut economy.book,
                &mut economy.costs,
                owner,
                row.site,
                money,
            )?;
            transition.money_transfers.push(transfer);
            let kept = standing.row_mut(row.site);
            kept.hold = StopHold::Free;
            kept.quiet_periods = 0;
        }
        receipts.push(AdjustmentReceipt::Restart(RestartReceipt {
            period,
            site_id: row.site,
            test,
            inputs_short: row.inputs_short,
            owner,
            money: Currency::from_micro_units(if test == RestartTest::Restarted {
                money
            } else {
                0
            }),
            batch_cost: Currency::from_micro_units(row.cost),
            turned: row.turned,
        }));
    }
    transition.adjustments.extend(receipts);
    if moved {
        bound_again(catalog, transition, bound)?;
    }
    Ok(())
}

/// Reckon the bound of the next period again from the state as it now stands, and put its receipts where the
/// earlier ones stood.
fn bound_again(
    catalog: &MaterialCatalog,
    transition: &mut MaterialCircuitTransition,
    bound: &mut HiringBound,
) -> Result<()> {
    let again = bound::rebound(
        catalog,
        &mut transition.state,
        bound,
        &transition.service_performance,
        transition.maintenance.as_ref(),
    )?;
    let at = transition
        .adjustments
        .iter()
        .position(|row| matches!(row, AdjustmentReceipt::HiringBound(_)))
        .unwrap_or(transition.adjustments.len());
    transition
        .adjustments
        .retain(|row| !matches!(row, AdjustmentReceipt::HiringBound(_)));
    let at = at.min(transition.adjustments.len());
    let rows = again
        .rows
        .iter()
        .cloned()
        .map(AdjustmentReceipt::HiringBound);
    transition.adjustments.splice(at..at, rows);
    *bound = again;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{CashAccount, FinalDemandPrincipalId};

    fn site(byte: u8) -> SiteId {
        SiteId::from_bytes([byte; 32])
    }

    fn dollars(whole: i128) -> i128 {
        whole * 1_000_000
    }

    fn candidate(byte: u8, plan: i128, earn: i128, money: i128) -> Candidate {
        Candidate {
            site: site(byte),
            plan: dollars(plan),
            earn: dollars(earn),
            money: dollars(money),
        }
    }

    #[test]
    fn a_restart_that_puts_in_nothing_is_refused() {
        assert_eq!(money_to_put_in(dollars(40), dollars(40)), None);
        assert_eq!(money_to_put_in(dollars(40), dollars(41)), None);
        assert_eq!(money_to_put_in(dollars(40), dollars(39)), Some(dollars(1)));
    }

    #[test]
    fn candidates_rank_by_earn_over_plan() {
        // Earn $10 on a plan of $100 against earn $3 on a plan of $20: the second first.
        let mut candidates = [candidate(1, 100, 10, 50), candidate(2, 20, 3, 10)];
        rank(&mut candidates);
        assert_eq!(candidates[0].site, site(2));
        // Equal ratios: the lower site first.
        let mut candidates = [candidate(9, 100, 10, 50), candidate(4, 50, 5, 25)];
        rank(&mut candidates);
        assert_eq!(candidates[0].site, site(4));
    }

    #[test]
    fn a_resting_price_under_cost_is_raised_to_it() {
        assert_eq!(raised_price(dollars(23), 1, dollars(12)), Some(dollars(23)));
        assert_eq!(raised_price(dollars(23), 1, dollars(30)), None);
        // $230 over 9 units is $25.555555..., rounded up to the micro-unit.
        assert_eq!(raised_price(dollars(230), 9, dollars(12)), Some(25_555_556));
        assert_eq!(raised_price(dollars(23), 1, dollars(23)), None);
    }

    #[test]
    fn an_owner_puts_in_only_its_own_spare() {
        let owner = AccountId::Household(FinalDemandPrincipalId::from_bytes([7; 32]));
        let candidates = [candidate(1, 80, 20, 40), candidate(2, 80, 10, 40)];
        let mut spare = BTreeMap::from([(owner, dollars(50))]);
        let seated = seat(&candidates, |_| Some(owner), &mut spare);
        assert_eq!(seated, vec![(site(1), Some(owner)), (site(2), None)]);
        assert_eq!(spare[&owner], dollars(10));
        // A workplace with no owner has no buyer.
        let mut spare = BTreeMap::from([(owner, dollars(500))]);
        assert_eq!(seat(&candidates, |_| None, &mut spare)[0], (site(1), None));
    }

    #[test]
    fn the_restart_moves_money_with_a_receipt() -> Result<()> {
        let owner = AccountId::Household(FinalDemandPrincipalId::from_bytes([7; 32]));
        let workplace = site(3);
        let mut book = MonetaryBook::open(vec![
            CashAccount {
                id: owner,
                cash: Currency::from_micro_units(dollars(100)),
            },
            CashAccount {
                id: AccountId::Site(workplace),
                cash: Currency::from_micro_units(dollars(15)),
            },
        ])?;
        let mut costs = HistoricalCostBook::open(&book, vec![], vec![], vec![], vec![])?;
        let before = book.total_cash_and_reserves()?;
        let receipt = put_in(&mut book, &mut costs, owner, workplace, dollars(25))?;
        assert_eq!(receipt.credit.delta.micro_units(), dollars(25));
        assert_eq!(receipt.debit.delta.micro_units(), -dollars(25));
        assert_eq!(book.cash(owner)?.micro_units(), dollars(75));
        assert_eq!(
            book.cash(AccountId::Site(workplace))?.micro_units(),
            dollars(40)
        );
        assert_eq!(book.total_cash_and_reserves()?, before);
        let snapshot = costs.snapshot();
        assert_eq!(snapshot.equity.len(), 1);
        assert_eq!(snapshot.equity[0].amount.micro_units(), dollars(25));
        let capital = snapshot
            .accounts
            .iter()
            .find(|row| row.account == AccountId::Site(workplace))
            .map(|row| row.contributed_capital.micro_units());
        assert_eq!(capital, Some(dollars(25)));
        Ok(())
    }

    #[test]
    fn a_workplace_is_tested_at_its_third_quiet_close() -> Result<()> {
        let mut row = WorkplaceStandingRow::new(site(1));
        for close in 1..=4_u64 {
            count(&mut row, false)?;
            assert_eq!(
                is_tested(&row, false),
                close >= RESTART_QUIET_PERIODS,
                "close {close}"
            );
        }
        // One that offers hours is never tested; one that made or sold starts counting again.
        assert!(!is_tested(&row, true));
        count(&mut row, true)?;
        assert_eq!((row.periods_since_work, row.quiet_periods), (0, 0));
        Ok(())
    }
}
