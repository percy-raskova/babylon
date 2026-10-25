//! Leaf implementation for the parent module; public paths stay on the parent.

use super::PricePolicy;
use super::RecurringEconomy;

use crate::{
    AccountId, CircuitAccounting, MaterialCircuitError, MaterialCircuitState, MerchantRole,
    MAX_MATERIAL_CIRCUIT_ROWS,
};

use crate::MaterialCatalog;
use crate::MonetaryCircuit;
use std::collections::{BTreeMap, BTreeSet};
use std::result::Result as StdResult;

pub(crate) type Result<T> = StdResult<T, MaterialCircuitError>;

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

pub(crate) fn unique<T, K: Ord>(rows: &[T], key: impl Fn(&T) -> K) -> Result<BTreeSet<K>> {
    let mut keys = BTreeSet::new();
    for row in rows {
        if !keys.insert(key(row)) {
            return Err(MaterialCircuitError::DuplicateRow);
        }
    }
    Ok(keys)
}

pub(crate) fn row_limits(rows: &RecurringEconomy) -> Result<()> {
    if rows.replenishment.len() > crate::MAX_REPLENISHMENT_POLICIES
        || rows.household_needs.len() > crate::MAX_HOUSEHOLD_NEEDS
        || rows.household_purchases.len() > crate::MAX_HOUSEHOLD_NEEDS
    {
        return Err(MaterialCircuitError::RowLimit);
    }
    if [
        rows.households.len(),
        rows.household_stocks.len(),
        rows.offers.len(),
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

pub(crate) fn validate_households(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    rows: &RecurringEconomy,
) -> Result<()> {
    let household_ids = unique(&rows.households, |r| r.principal_id)?;
    let principals: BTreeMap<_, _> = state
        .final_demand_principals
        .iter()
        .map(|r| (r.id, r))
        .collect();
    let households: BTreeMap<_, _> = rows
        .households
        .iter()
        .map(|r| (r.principal_id, r))
        .collect();
    for row in &rows.households {
        if !row.kind.admits_counts(row.persons, row.households)
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
    let stored_need_keys: BTreeSet<_> = need_keys
        .iter()
        .filter(|key| !crate::services::is_service(catalog, key.1, key.2))
        .copied()
        .collect();
    if stock_keys != stored_need_keys
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
        let cohort = households
            .get(&need.principal_id)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        need.required_quantity(cohort)?;
    }
    let offers: BTreeSet<_> = rows
        .offers
        .iter()
        .map(|r| (r.site_id, r.good_id, r.unit_id))
        .collect();
    let merchants: BTreeMap<_, _> = catalog.merchants.iter().map(|r| (r.site_id, r)).collect();
    let handling: BTreeSet<_> = catalog
        .handling_coefficients
        .iter()
        .map(|r| (r.site_id, r.good_id, r.unit_id))
        .collect();
    for policy in &rows.household_purchases {
        if crate::services::is_service(catalog, policy.good_id, policy.unit_id) {
            let connection = crate::ServiceConnection {
                provider_site_id: policy.retailer_site_id,
                buyer: AccountId::Household(policy.principal_id),
                good_id: policy.good_id,
                unit_id: policy.unit_id,
            };
            if policy.target_closing_stock != 0
                || state
                    .service_connections
                    .binary_search(&connection)
                    .is_err()
                || !offers.contains(&(policy.retailer_site_id, policy.good_id, policy.unit_id))
            {
                return Err(MaterialCircuitError::ServiceInvariant);
            }
            continue;
        }
        let merchant = merchants
            .get(&policy.retailer_site_id)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let principal = principals
            .get(&policy.principal_id)
            .ok_or(MaterialCircuitError::FinalDemandInvariant)?;
        let offer_key = (policy.retailer_site_id, policy.good_id, policy.unit_id);
        if merchant.role != MerchantRole::Retail
            || merchant.location != principal.location
            || !offers.contains(&offer_key)
            || !handling.contains(&offer_key)
        {
            return Err(MaterialCircuitError::FinalDemandInvariant);
        }
    }
    Ok(())
}

pub(crate) fn validate_offers(catalog: &MaterialCatalog, rows: &RecurringEconomy) -> Result<()> {
    unique(&rows.offers, |r| (r.site_id, r.good_id, r.unit_id))?;
    let sites: BTreeSet<_> = catalog
        .site_logistics_nodes
        .iter()
        .map(|r| r.site_id)
        .collect();
    let goods: BTreeSet<_> = catalog
        .commodities
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

pub(crate) fn validate_firm_policies(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    rows: &RecurringEconomy,
) -> Result<()> {
    unique(&rows.replenishment, |r| {
        (r.buyer_site_id, r.supplier_site_id, r.good_id, r.unit_id)
    })?;
    let routes: BTreeSet<_> = catalog
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
    unique(&catalog.process_outputs, |r| {
        (r.site_id, r.good_id, r.unit_id)
    })?;
    let outputs: BTreeMap<_, _> = catalog
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
pub(crate) fn validate(catalog: &MaterialCatalog, state: &MaterialCircuitState) -> Result<()> {
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
    validate_households(catalog, state, rows)?;
    validate_offers(catalog, rows)?;
    validate_firm_policies(catalog, state, rows)?;
    for household in &rows.households {
        economy
            .book
            .cash(AccountId::Household(household.principal_id))?;
    }
    validate_attendance(state, economy, rows)
}

pub(crate) fn validate_attendance(
    state: &MaterialCircuitState,
    economy: &MonetaryCircuit,
    rows: &RecurringEconomy,
) -> Result<()> {
    let employment: BTreeSet<_> = economy
        .employment
        .iter()
        .map(|r| (r.site_id, r.unit_id))
        .collect();
    let available: BTreeMap<_, _> = state
        .labor
        .iter()
        .filter(|r| r.period == state.period)
        .map(|r| ((r.site_id, r.unit_id), r.available))
        .collect();
    let required: BTreeSet<_> = employment.iter().chain(available.keys()).copied().collect();
    if rows
        .attendance
        .iter()
        .map(|r| (r.site_id, r.unit_id))
        .collect::<BTreeSet<_>>()
        != required
        || rows.attendance.iter().any(|r| {
            let key = (r.site_id, r.unit_id);
            !employment.contains(&key) && (r.planned_hours != 0 || available.get(&key) != Some(&0))
        })
    {
        return Err(MaterialCircuitError::PayrollInvariant);
    }
    Ok(())
}
