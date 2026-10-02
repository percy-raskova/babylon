//! Household service needs remain visible without inventing a pantry stock.
use super::{
    digest_hex, lifecycle, EconomicLocation, GoodId, MaterialCircuitState, MaterialTickReceipts,
    ProductionProjectionError, Result, UnitId,
};
use babylon_material_circuit::AccountId;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProductionHouseholdServiceAccount {
    pub demand_principal_id: String,
    pub location: EconomicLocation,
    pub good_id: String,
    pub unit_id: String,
    pub good: String,
    pub unit: String,
    pub household_count: u64,
    pub person_count: u64,
    pub provider_site_ids: Vec<String>,
    pub required_per_period: u64,
    pub completed: Option<CompletedHouseholdService>,
}
#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CompletedHouseholdService {
    pub period: u64,
    pub required: u64,
    pub requested: u64,
    pub admitted: u64,
    pub performed: u64,
    pub satisfied: u64,
    pub unmet: u64,
    pub unused: u64,
    pub expired: u64,
}

pub(crate) fn project_with_labels(
    current: &MaterialCircuitState,
    prior: Option<&MaterialCircuitState>,
    receipt: Option<&MaterialTickReceipts>,
    labels: impl Fn(GoodId, UnitId) -> Option<(String, String)>,
) -> Result<Vec<ProductionHouseholdServiceAccount>> {
    match (prior, receipt) {
        (None, None) if current.period == 1 => {}
        (Some(prior), Some(receipt))
            if prior.period.checked_add(1) == Some(current.period)
                && receipt.resolve_tick == prior.period =>
        {
            super::super::services::validate(prior, current, receipt)?;
        }
        _ => return Err(ProductionProjectionError::History),
    }
    let Some(r) = lifecycle::recurring(current) else {
        return Ok(Vec::new());
    };
    let kinds = super::super::services::service_kinds(current);
    let cohorts: BTreeMap<_, _> = r.households.iter().map(|r| (r.principal_id, r)).collect();
    let principals: BTreeMap<_, _> = current
        .final_demand_principals
        .iter()
        .map(|r| (r.id, r.location))
        .collect();
    let policies: BTreeMap<_, _> = r
        .household_purchases
        .iter()
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r))
        .collect();
    let completed: BTreeMap<_, _> = receipt
        .into_iter()
        .flat_map(|r| &r.household_services)
        .map(|r| ((r.principal_id, r.good_id, r.unit_id), r))
        .collect();
    let mut purchases = purchase_totals(receipt)?;
    let mut result = Vec::new();
    for need in r
        .household_needs
        .iter()
        .filter(|r| kinds.contains(&(r.good_id, r.unit_id)))
    {
        let key = (need.principal_id, need.good_id, need.unit_id);
        let cohort = cohorts
            .get(&key.0)
            .ok_or(ProductionProjectionError::State)?;
        let location = *principals
            .get(&key.0)
            .ok_or(ProductionProjectionError::State)?;
        let policy = policies.get(&key).ok_or(ProductionProjectionError::State)?;
        let (good, unit) = labels(key.1, key.2).ok_or(ProductionProjectionError::Content)?;
        let mut purchases = purchases.remove(&key).unwrap_or_default();
        purchases
            .3
            .insert(digest_hex(&policy.retailer_site_id.as_bytes()));
        let done = completed.get(&key).map(|r| CompletedHouseholdService {
            period: r.period,
            required: r.required_quantity,
            requested: purchases.0,
            admitted: purchases.1,
            performed: r.performed_quantity,
            satisfied: r.satisfied_quantity,
            unmet: r.unmet_quantity,
            unused: r.unused_quantity,
            expired: purchases.2,
        });
        result.push(ProductionHouseholdServiceAccount {
            demand_principal_id: digest_hex(&key.0.as_bytes()),
            location,
            good_id: digest_hex(&key.1.as_bytes()),
            unit_id: digest_hex(&key.2.as_bytes()),
            good,
            unit,
            household_count: cohort.households,
            person_count: cohort.persons,
            provider_site_ids: purchases.3.into_iter().collect(),
            required_per_period: need
                .required_quantity(cohort)
                .map_err(|_| ProductionProjectionError::State)?,
            completed: done,
        });
    }
    Ok(result)
}

type PurchaseTotals = (u64, u64, u64, BTreeSet<String>);
type PurchaseKey = (
    babylon_material_circuit::FinalDemandPrincipalId,
    GoodId,
    UnitId,
);
fn purchase_totals(
    receipt: Option<&MaterialTickReceipts>,
) -> Result<BTreeMap<PurchaseKey, PurchaseTotals>> {
    let mut purchases = BTreeMap::<_, PurchaseTotals>::new();
    for row in receipt.into_iter().flat_map(|r| &r.service_performance) {
        let AccountId::Household(principal) = row.buyer else {
            continue;
        };
        let values = purchases
            .entry((principal, row.good_id, row.unit_id))
            .or_default();
        for (total, value) in [
            (&mut values.0, row.requested_quantity),
            (&mut values.1, row.admitted_quantity),
            (&mut values.2, row.expired_quantity),
        ] {
            *total = total
                .checked_add(value)
                .ok_or(ProductionProjectionError::Arithmetic)?;
        }
        values
            .3
            .insert(digest_hex(&row.provider_site_id.as_bytes()));
    }
    Ok(purchases)
}
