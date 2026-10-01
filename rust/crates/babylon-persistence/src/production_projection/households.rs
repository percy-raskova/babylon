//! Resident stocks and explicit consumption, separate from merchant stock exits.
use super::{lifecycle, ProductionProjectionError};
use crate::{michigan_economy::digest_hex, michigan_material::MichiganMaterialCatalog};
use babylon_material_circuit::{FinalDemandPrincipalId, GoodId, MaterialCircuitState, UnitId};
use babylon_tick::material_world::MaterialTickReceipts;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

type Result<T> = std::result::Result<T, ProductionProjectionError>;
type Key = (FinalDemandPrincipalId, GoodId, UnitId);

/// One resident cohort and native good. People and households have separate units.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProductionHouseholdAccount {
    pub demand_principal_id: String,
    pub county_geoid: String,
    pub good_id: String,
    pub unit_id: String,
    pub good: String,
    pub unit: String,
    pub household_count: u64,
    pub person_count: u64,
    pub retailer_site_id: String,
    pub stock_on_hand: u64,
    pub required_per_period: u64,
    pub completed: Option<CompletedHouseholdBalance>,
}

/// Purchases transfer title into resident stock; consumption subsequently uses it.
/// Expired orders refund money and never consume or create goods.
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CompletedHouseholdBalance {
    pub period: u64,
    pub opening_stock: u64,
    pub received: u64,
    pub required: u64,
    pub consumed: u64,
    pub unmet: u64,
    pub closing_stock: u64,
    pub desired: u64,
    pub requested: u64,
    pub admitted: u64,
    pub fulfilled: u64,
    pub expired: u64,
}

pub(super) fn project_households(
    catalog: &MichiganMaterialCatalog,
    current: &MaterialCircuitState,
    prior: Option<&MaterialCircuitState>,
    receipts: Option<&MaterialTickReceipts>,
) -> Result<Vec<ProductionHouseholdAccount>> {
    project_with_labels(current, prior, receipts, |good, unit| {
        catalog
            .goods()
            .iter()
            .find(|row| row.id() == good && row.unit_id() == unit)
            .map(|row| (row.label.clone(), row.unit_key.clone()))
    })
}

pub(super) fn project_with_labels(
    current: &MaterialCircuitState,
    prior: Option<&MaterialCircuitState>,
    receipts: Option<&MaterialTickReceipts>,
    labels: impl Fn(GoodId, UnitId) -> Option<(String, String)>,
) -> Result<Vec<ProductionHouseholdAccount>> {
    let Some(rows) = lifecycle::recurring(current) else {
        if prior.is_some_and(|state| lifecycle::recurring(state).is_some())
            || receipts.is_some_and(|rows| {
                !rows.household_demand.is_empty() || !rows.household_consumption.is_empty()
            })
        {
            return Err(ProductionProjectionError::State);
        }
        return Ok(Vec::new());
    };
    let completed = match (prior, receipts) {
        (None, None) if current.period == 1 => BTreeMap::new(),
        (Some(prior), Some(receipts)) => completed_balances(prior, current, receipts)?,
        _ => return Err(ProductionProjectionError::History),
    };
    let cohorts: BTreeMap<_, _> = rows
        .households
        .iter()
        .map(|row| (row.principal_id, row))
        .collect();
    let needs: BTreeMap<_, _> = rows
        .household_needs
        .iter()
        .map(|row| ((row.principal_id, row.good_id, row.unit_id), row))
        .collect();
    let policies: BTreeMap<_, _> = rows
        .household_purchases
        .iter()
        .map(|row| ((row.principal_id, row.good_id, row.unit_id), row))
        .collect();
    let principals: BTreeMap<_, _> = current
        .final_demand_principals
        .iter()
        .map(|row| (row.id, row))
        .collect();
    let mut result = Vec::new();
    for stock in &rows.household_stocks {
        let key = (stock.principal_id, stock.good_id, stock.unit_id);
        let household = cohorts
            .get(&key.0)
            .ok_or(ProductionProjectionError::State)?;
        let need = needs.get(&key).ok_or(ProductionProjectionError::State)?;
        let policy = policies.get(&key).ok_or(ProductionProjectionError::State)?;
        let principal = principals
            .get(&key.0)
            .ok_or(ProductionProjectionError::State)?;
        let (good, unit) = labels(key.1, key.2).ok_or(ProductionProjectionError::Content)?;
        result.push(ProductionHouseholdAccount {
            demand_principal_id: digest_hex(&key.0.as_bytes()),
            county_geoid: String::from_utf8(principal.county_geoid.to_vec())
                .map_err(|_| ProductionProjectionError::State)?,
            good_id: digest_hex(&key.1.as_bytes()),
            unit_id: digest_hex(&key.2.as_bytes()),
            good,
            unit,
            household_count: household.households,
            person_count: household.persons,
            retailer_site_id: digest_hex(&policy.retailer_site_id.as_bytes()),
            stock_on_hand: stock.quantity,
            required_per_period: household
                .persons
                .checked_mul(need.units_per_person)
                .ok_or(ProductionProjectionError::Arithmetic)?,
            completed: completed.get(&key).cloned(),
        });
    }
    Ok(result)
}

pub(super) fn completed_balances(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
) -> Result<BTreeMap<Key, CompletedHouseholdBalance>> {
    if prior.period.checked_add(1) != Some(current.period) || receipt.resolve_tick != prior.period {
        return Err(ProductionProjectionError::History);
    }
    let before = lifecycle::recurring(prior).ok_or(ProductionProjectionError::State)?;
    let after = lifecycle::recurring(current).ok_or(ProductionProjectionError::State)?;
    if before.households != after.households || before.household_needs != after.household_needs {
        return Err(ProductionProjectionError::State);
    }
    let people: BTreeMap<_, _> = before
        .households
        .iter()
        .map(|row| (row.principal_id, row.persons))
        .collect();
    let needs: BTreeMap<_, _> = before
        .household_needs
        .iter()
        .map(|row| {
            (
                (row.principal_id, row.good_id, row.unit_id),
                row.units_per_person,
            )
        })
        .collect();
    let mut opening: BTreeMap<_, _> = before
        .household_stocks
        .iter()
        .map(|row| ((row.principal_id, row.good_id, row.unit_id), row.quantity))
        .collect();
    let closing: BTreeMap<_, _> = after
        .household_stocks
        .iter()
        .map(|row| ((row.principal_id, row.good_id, row.unit_id), row.quantity))
        .collect();
    let mut demand: BTreeMap<_, _> = receipt
        .household_demand
        .iter()
        .map(|row| ((row.principal_id, row.good_id, row.unit_id), row))
        .collect();
    if opening.len() != before.household_stocks.len()
        || closing.len() != after.household_stocks.len()
        || opening.keys().ne(closing.keys())
        || demand.len() != receipt.household_demand.len()
    {
        return Err(ProductionProjectionError::State);
    }
    let mut received = received_stock(receipt, &opening)?;
    let mut result = BTreeMap::new();
    for row in &receipt.household_consumption {
        let key = (row.principal_id, row.good_id, row.unit_id);
        let stock = opening
            .remove(&key)
            .ok_or(ProductionProjectionError::State)?;
        let purchase = demand
            .remove(&key)
            .ok_or(ProductionProjectionError::State)?;
        let received = received.remove(&key).unwrap_or(0);
        let persons = *people.get(&key.0).ok_or(ProductionProjectionError::State)?;
        let need = *needs.get(&key).ok_or(ProductionProjectionError::State)?;
        let required = persons
            .checked_mul(need)
            .ok_or(ProductionProjectionError::Arithmetic)?;
        if row.period != prior.period
            || purchase.period != prior.period
            || row.required_quantity != required
            || purchase.required_quantity != required
            || purchase.opening_stock != stock
            || stock.checked_add(received) != Some(row.available_quantity)
            || row.consumed_quantity != row.available_quantity.min(required)
            || row.consumed_quantity.checked_add(row.unmet_quantity) != Some(required)
            || row.available_quantity.checked_sub(row.consumed_quantity)
                != Some(row.closing_quantity)
            || closing.get(&key) != Some(&row.closing_quantity)
        {
            return Err(ProductionProjectionError::State);
        }
        result.insert(
            key,
            CompletedHouseholdBalance {
                period: prior.period,
                opening_stock: stock,
                received,
                required,
                consumed: row.consumed_quantity,
                unmet: row.unmet_quantity,
                closing_stock: row.closing_quantity,
                desired: purchase.desired_quantity,
                requested: purchase.requested_quantity,
                admitted: purchase.admitted_quantity,
                fulfilled: purchase.fulfilled_quantity,
                expired: purchase.expired_quantity,
            },
        );
    }
    if !opening.is_empty() || !demand.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    Ok(result)
}

fn received_stock(
    receipt: &MaterialTickReceipts,
    opening: &BTreeMap<Key, u64>,
) -> Result<BTreeMap<Key, u64>> {
    let mut received = BTreeMap::<Key, u64>::new();
    for row in &receipt.local_fulfillments {
        let key = (row.demand_principal_id, row.good_id, row.unit_id);
        if opening.contains_key(&key) {
            let sum = received.entry(key).or_default();
            *sum = sum
                .checked_add(row.quantity)
                .ok_or(ProductionProjectionError::Arithmetic)?;
        }
    }
    Ok(received)
}
