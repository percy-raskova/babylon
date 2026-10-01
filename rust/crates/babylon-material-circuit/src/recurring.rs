//! Recurring household needs and purchases share the authoritative material close.

pub(crate) mod firms;
mod households;
mod model;

pub use firms::{
    recurring_procurement_order_id, PriceDecision, PriceReceipt, ProcurementReceipt,
    ProductionPlanReceipt,
};
pub use households::recurring_household_order_id;
pub(crate) use households::{
    admit_household_orders, complete_household_orders, consume_household_needs,
};
pub use model::*;

use crate::{
    AccountId, CircuitAccounting, MaterialCircuitError, MaterialCircuitState, MerchantRole,
    MAX_MATERIAL_CIRCUIT_ROWS,
};
use std::collections::{BTreeMap, BTreeSet};

type Result<T> = std::result::Result<T, MaterialCircuitError>;

pub(crate) fn canonicalize(rows: &mut RecurringEconomy) {
    rows.households.sort_by_key(|r| r.principal_id);
    rows.household_stocks
        .sort_by_key(|r| (r.principal_id, r.good_id, r.unit_id));
    rows.household_needs
        .sort_by_key(|r| (r.principal_id, r.good_id, r.unit_id));
    rows.household_purchases
        .sort_by_key(|r| (r.principal_id, r.good_id, r.unit_id));
    rows.offers
        .sort_by_key(|r| (r.site_id, r.good_id, r.unit_id));
    rows.replenishment
        .sort_by_key(|r| (r.buyer_site_id, r.supplier_site_id, r.good_id, r.unit_id));
    rows.production.sort_by_key(|r| r.process_id);
    rows.attendance.sort_by_key(|r| (r.site_id, r.unit_id));
}

fn unique<T, K: Ord>(rows: &[T], key: impl Fn(&T) -> K) -> Result<BTreeSet<K>> {
    let mut keys = BTreeSet::new();
    for row in rows {
        if !keys.insert(key(row)) {
            return Err(MaterialCircuitError::DuplicateRow);
        }
    }
    Ok(keys)
}

fn row_limits(rows: &RecurringEconomy) -> Result<()> {
    if [
        rows.households.len(),
        rows.household_stocks.len(),
        rows.household_needs.len(),
        rows.household_purchases.len(),
        rows.offers.len(),
        rows.replenishment.len(),
        rows.production.len(),
        rows.attendance.len(),
    ]
    .into_iter()
    .any(|n| n > MAX_MATERIAL_CIRCUIT_ROWS)
    {
        return Err(MaterialCircuitError::RowLimit);
    }
    Ok(())
}

fn validate_households(state: &MaterialCircuitState, rows: &RecurringEconomy) -> Result<()> {
    let household_ids = unique(&rows.households, |r| r.principal_id)?;
    let principals: BTreeMap<_, _> = state
        .final_demand_principals
        .iter()
        .map(|r| (r.id, r))
        .collect();
    let people: BTreeMap<_, _> = rows
        .households
        .iter()
        .map(|r| (r.principal_id, r.persons))
        .collect();
    for row in &rows.households {
        if row.households == 0
            || row.persons < row.households
            || !principals.contains_key(&row.principal_id)
        {
            return Err(MaterialCircuitError::FinalDemandInvariant);
        }
    }
    let stock_keys = unique(&rows.household_stocks, |r| {
        (r.principal_id, r.good_id, r.unit_id)
    })?;
    let need_keys = unique(&rows.household_needs, |r| {
        (r.principal_id, r.good_id, r.unit_id)
    })?;
    let purchase_keys = unique(&rows.household_purchases, |r| {
        (r.principal_id, r.good_id, r.unit_id)
    })?;
    if stock_keys != need_keys
        || purchase_keys != need_keys
        || need_keys.iter().map(|key| key.0).collect::<BTreeSet<_>>() != household_ids
    {
        return Err(MaterialCircuitError::FinalDemandInvariant);
    }
    if state.final_demand_orders.iter().any(|order| {
        household_ids.contains(&order.demand_principal_id)
            && !stock_keys.contains(&(order.demand_principal_id, order.good_id, order.unit_id))
    }) {
        return Err(MaterialCircuitError::FinalDemandInvariant);
    }
    for need in &rows.household_needs {
        if need.units_per_person == 0 {
            return Err(MaterialCircuitError::ZeroQuantity);
        }
        people
            .get(&need.principal_id)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?
            .checked_mul(need.units_per_person)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    let offers: BTreeSet<_> = rows
        .offers
        .iter()
        .map(|r| (r.site_id, r.good_id, r.unit_id))
        .collect();
    let merchants: BTreeMap<_, _> = state.merchants.iter().map(|r| (r.site_id, r)).collect();
    let handling: BTreeSet<_> = state
        .handling_coefficients
        .iter()
        .map(|r| (r.site_id, r.good_id, r.unit_id))
        .collect();
    for policy in &rows.household_purchases {
        let merchant = merchants
            .get(&policy.retailer_site_id)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let principal = principals
            .get(&policy.principal_id)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let offer_key = (policy.retailer_site_id, policy.good_id, policy.unit_id);
        if merchant.role != MerchantRole::Retail
            || merchant.county_geoid != principal.county_geoid
            || !offers.contains(&offer_key)
            || !handling.contains(&offer_key)
        {
            return Err(MaterialCircuitError::FinalDemandInvariant);
        }
    }
    Ok(())
}

fn validate_offers(state: &MaterialCircuitState, rows: &RecurringEconomy) -> Result<()> {
    unique(&rows.offers, |r| (r.site_id, r.good_id, r.unit_id))?;
    let sites: BTreeSet<_> = state
        .site_logistics_nodes
        .iter()
        .map(|r| r.site_id)
        .collect();
    let goods: BTreeSet<_> = state
        .freight_mass_coefficients
        .iter()
        .map(|r| (r.good_id, r.unit_id))
        .collect();
    for offer in &rows.offers {
        if offer.unit_price.micro_units() <= 0
            || !sites.contains(&offer.site_id)
            || !goods.contains(&(offer.good_id, offer.unit_id))
        {
            return Err(MaterialCircuitError::PurchaseInvariant);
        }
        if let PricePolicy::Responsive {
            minimum,
            maximum,
            step,
            ..
        } = offer.pricing
        {
            if minimum.micro_units() <= 0
                || step.micro_units() <= 0
                || minimum > maximum
                || offer.unit_price < minimum
                || offer.unit_price > maximum
            {
                return Err(MaterialCircuitError::PurchaseInvariant);
            }
        }
    }
    Ok(())
}

fn validate_firm_policies(state: &MaterialCircuitState, rows: &RecurringEconomy) -> Result<()> {
    unique(&rows.replenishment, |r| {
        (r.buyer_site_id, r.supplier_site_id, r.good_id, r.unit_id)
    })?;
    let routes: BTreeSet<_> = state
        .supplier_routes
        .iter()
        .map(|r| (r.buyer_site_id, r.supplier_site_id, r.good_id, r.unit_id))
        .collect();
    let offers: BTreeSet<_> = rows
        .offers
        .iter()
        .map(|r| (r.site_id, r.good_id, r.unit_id))
        .collect();
    for row in &rows.replenishment {
        if row.buyer_site_id == row.supplier_site_id
            || row.cash_floor.micro_units() < 0
            || !routes.contains(&(
                row.buyer_site_id,
                row.supplier_site_id,
                row.good_id,
                row.unit_id,
            ))
            || !offers.contains(&(row.supplier_site_id, row.good_id, row.unit_id))
        {
            return Err(MaterialCircuitError::PurchaseInvariant);
        }
    }
    let processes = unique(&rows.production, |r| r.process_id)?;
    unique(&state.process_outputs, |r| {
        (r.site_id, r.good_id, r.unit_id)
    })?;
    let outputs: BTreeMap<_, _> = state
        .process_outputs
        .iter()
        .map(|r| (r.process_id, r.site_id))
        .collect();
    if processes != outputs.keys().copied().collect()
        || rows
            .production
            .iter()
            .any(|r| outputs.get(&r.process_id) != Some(&r.site_id))
    {
        return Err(MaterialCircuitError::ProcessInvariant);
    }
    unique(&rows.attendance, |r| (r.site_id, r.unit_id))?;
    if rows.attendance.iter().any(|r| r.period != state.period) {
        return Err(MaterialCircuitError::PeriodInvariant);
    }
    Ok(())
}

/// Validate a canonical opening; intermediate household phases remain detached.
pub(crate) fn validate(state: &MaterialCircuitState) -> Result<()> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(());
    };
    let Some(rows) = &economy.recurring else {
        return Ok(());
    };
    row_limits(rows)?;
    let previous = state
        .period
        .checked_sub(1)
        .ok_or(MaterialCircuitError::PeriodInvariant)?;
    if rows.last_household_admission_period != previous
        || rows.last_household_consumption_period != previous
    {
        return Err(MaterialCircuitError::PeriodInvariant);
    }
    validate_households(state, rows)?;
    validate_offers(state, rows)?;
    validate_firm_policies(state, rows)?;
    for household in &rows.households {
        economy
            .book
            .cash(AccountId::Household(household.principal_id))?;
    }
    let employment: BTreeSet<_> = economy
        .employment
        .iter()
        .map(|r| (r.site_id, r.unit_id))
        .collect();
    if rows
        .attendance
        .iter()
        .map(|r| (r.site_id, r.unit_id))
        .collect::<BTreeSet<_>>()
        != employment
    {
        return Err(MaterialCircuitError::PayrollInvariant);
    }
    Ok(())
}

#[cfg(test)]
mod households_tests;
