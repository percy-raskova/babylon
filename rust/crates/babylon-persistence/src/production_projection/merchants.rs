//! Committed merchant handling and finite county demand, without allocation.

use super::{
    outbound::{completed_facts, identity, mass, OutboundFact},
    ProductionProjectionError,
};
use crate::{
    michigan_economy::digest_hex, michigan_material::MichiganMaterialCatalog,
    production_observation::CompletedProductionFinalDemand,
    production_observation::CompletedProductionMerchantHandling,
    production_observation::ProductionFinalDemandAccount,
    production_observation::ProductionFinalDemandOrder,
    production_observation::ProductionHandlingCoefficient,
    production_observation::ProductionMerchantHandlingAccount,
    production_observation::ProductionMerchantHandlingOrder,
};
use babylon_material_circuit::{
    FinalDemandPrincipalId, GoodId, MaterialCircuitState, OrderId, OutboundOrderId, SiteId, UnitId,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::{BTreeMap, BTreeSet};

type Result<T> = std::result::Result<T, ProductionProjectionError>;
type DemandKey = (FinalDemandPrincipalId, GoodId, UnitId);

pub(super) fn project_merchants(
    catalog: &MichiganMaterialCatalog,
    current: &MaterialCircuitState,
    prior: Option<&MaterialCircuitState>,
    receipt: Option<&MaterialTickReceipts>,
    history: &super::history::OrderHistory,
) -> Result<(
    Vec<ProductionMerchantHandlingAccount>,
    Vec<ProductionFinalDemandAccount>,
)> {
    let completed = match (prior, receipt) {
        (None, None) if current.period == 1 => None,
        (Some(prior), Some(receipt)) => {
            Some((prior, receipt, completed_facts(prior, current, receipt)?))
        }
        _ => return Err(ProductionProjectionError::History),
    };
    let handling = handling_accounts(
        current,
        completed
            .as_ref()
            .map(|(prior, receipt, facts)| (*prior, *receipt, facts.as_slice())),
    )?;
    let demand = final_demand_accounts(
        catalog,
        current,
        completed
            .as_ref()
            .map(|(prior, _, facts)| (*prior, facts.as_slice())),
        history,
    )?;
    Ok((handling, demand))
}

fn handling_accounts(
    current: &MaterialCircuitState,
    completed: Option<(
        &MaterialCircuitState,
        &MaterialTickReceipts,
        &[OutboundFact],
    )>,
) -> Result<Vec<ProductionMerchantHandlingAccount>> {
    let complete_rows = completed
        .map(|(prior, receipt, facts)| handling_rows(prior, receipt, facts))
        .transpose()?;
    current
        .merchants
        .iter()
        .map(|merchant| {
            let coefficients = current
                .handling_coefficients
                .iter()
                .filter(|row| row.site_id == merchant.site_id)
                .map(|row| {
                    if row.hours_per_unit == 0 {
                        return Err(ProductionProjectionError::State);
                    }
                    Ok(ProductionHandlingCoefficient {
                        good_id: digest_hex(&row.good_id.as_bytes()),
                        unit_id: digest_hex(&row.unit_id.as_bytes()),
                        grams_per_unit: mass(current, row.good_id, row.unit_id)?,
                        hours_per_unit: row.hours_per_unit,
                    })
                })
                .collect::<Result<Vec<_>>>()?;
            let completed = complete_rows
                .as_ref()
                .map(|all| {
                    let orders = all.get(&merchant.site_id).cloned().unwrap_or_default();
                    let needed_hours = sum(orders.iter().map(|row| row.needed_hours))?;
                    let used_hours = sum(orders.iter().map(|row| row.used_hours))?;
                    let handled_grams = sum(orders
                        .iter()
                        .map(|row| {
                            let coefficient = coefficients
                                .iter()
                                .find(|coefficient| {
                                    coefficient.good_id == row.good_id
                                        && coefficient.unit_id == row.unit_id
                                })
                                .ok_or(ProductionProjectionError::State)?;
                            row.handled_quantity
                                .checked_mul(coefficient.grams_per_unit)
                                .ok_or(ProductionProjectionError::Arithmetic)
                        })
                        .collect::<Result<Vec<_>>>()?)?;
                    Ok(CompletedProductionMerchantHandling {
                        period: current.period - 1,
                        needed_hours,
                        used_hours,
                        handled_grams,
                        orders,
                    })
                })
                .transpose()?;
            Ok(ProductionMerchantHandlingAccount {
                site_id: digest_hex(&merchant.site_id.as_bytes()),
                capacity_id: digest_hex(&merchant.capacity_id.as_bytes()),
                labor_unit_id: digest_hex(&merchant.labor_unit_id.as_bytes()),
                coefficients,
                completed,
            })
        })
        .collect()
}

fn handling_rows(
    prior: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
    facts: &[OutboundFact],
) -> Result<BTreeMap<SiteId, Vec<ProductionMerchantHandlingOrder>>> {
    let merchants: BTreeSet<_> = prior.merchants.iter().map(|row| row.site_id).collect();
    let mut expected = BTreeMap::new();
    for fact in facts.iter().filter(|fact| merchants.contains(&fact.site)) {
        if expected.insert((fact.site, fact.id), fact).is_some() {
            return Err(ProductionProjectionError::State);
        }
    }
    let mut result = BTreeMap::<SiteId, Vec<ProductionMerchantHandlingOrder>>::new();
    for row in &receipt.handling {
        let fact = expected
            .remove(&(row.site_id, row.order))
            .ok_or(ProductionProjectionError::State)?;
        let mut coefficients = prior.handling_coefficients.iter().filter(|coefficient| {
            coefficient.site_id == row.site_id
                && coefficient.good_id == fact.good
                && coefficient.unit_id == fact.unit
        });
        let coefficient = coefficients
            .next()
            .ok_or(ProductionProjectionError::State)?;
        if coefficients.next().is_some()
            || coefficient.hours_per_unit == 0
            || row.handled_quantity != fact.quantity
            || row.handled_quantity > row.feasible_quantity
            || row.feasible_quantity > fact.requested
            || row
                .feasible_quantity
                .checked_mul(coefficient.hours_per_unit)
                != Some(row.needed_hours)
            || row.handled_quantity.checked_mul(coefficient.hours_per_unit) != Some(row.used_hours)
        {
            return Err(ProductionProjectionError::State);
        }
        let (id, kind) = identity(row.order);
        result
            .entry(row.site_id)
            .or_default()
            .push(ProductionMerchantHandlingOrder {
                order_id: digest_hex(&id.as_bytes()),
                kind,
                good_id: digest_hex(&fact.good.as_bytes()),
                unit_id: digest_hex(&fact.unit.as_bytes()),
                requested: fact.requested,
                feasible_quantity: row.feasible_quantity,
                handled_quantity: row.handled_quantity,
                needed_hours: row.needed_hours,
                used_hours: row.used_hours,
                remaining_unshipped: fact.remaining,
            });
    }
    if !expected.is_empty() {
        return Err(ProductionProjectionError::State);
    }
    for rows in result.values_mut() {
        rows.sort_unstable();
    }
    Ok(result)
}

fn final_demand_accounts(
    catalog: &MichiganMaterialCatalog,
    current: &MaterialCircuitState,
    completed: Option<(&MaterialCircuitState, &[OutboundFact])>,
    history: &super::history::OrderHistory,
) -> Result<Vec<ProductionFinalDemandAccount>> {
    project_final_with_labels(current, completed, history, |good, unit| {
        catalog
            .goods()
            .iter()
            .find(|row| row.id() == good && row.unit_id() == unit)
            .map(|row| (row.label.clone(), row.unit_key.clone()))
    })
}

pub(super) fn project_final_with_labels(
    current: &MaterialCircuitState,
    completed: Option<(&MaterialCircuitState, &[OutboundFact])>,
    history: &super::history::OrderHistory,
    labels: impl Fn(GoodId, UnitId) -> Option<(String, String)>,
) -> Result<Vec<ProductionFinalDemandAccount>> {
    let mut groups = BTreeMap::<DemandKey, Vec<_>>::new();
    for row in history.final_orders.values() {
        let order = &row.order;
        groups
            .entry((order.demand_principal_id, order.good_id, order.unit_id))
            .or_default()
            .push(row);
    }
    let mut configured = BTreeMap::<DemandKey, BTreeSet<SiteId>>::new();
    if let Some(rows) = super::lifecycle::recurring(current) {
        for policy in &rows.household_purchases {
            let key = (policy.principal_id, policy.good_id, policy.unit_id);
            groups.entry(key).or_default();
            configured
                .entry(key)
                .or_default()
                .insert(policy.retailer_site_id);
        }
    }
    let actual = active_final_orders(current, history)?;
    let latest: BTreeSet<_> = completed
        .into_iter()
        .flat_map(|(_, facts)| facts.iter())
        .filter_map(|fact| match fact.id {
            OutboundOrderId::LocalFinalDemand(id) => Some(id),
            OutboundOrderId::Delivery(_) => None,
        })
        .collect();
    let principals: BTreeMap<_, _> = current
        .final_demand_principals
        .iter()
        .map(|row| (row.id, row))
        .collect();
    let inventory: BTreeMap<_, _> = current
        .inventory
        .iter()
        .map(|row| ((row.site_id, row.good_id, row.unit_id), row.quantity))
        .collect();
    let quantities: BTreeMap<_, _> = completed
        .into_iter()
        .flat_map(|(_, facts)| facts.iter())
        .filter_map(|fact| match fact.id {
            OutboundOrderId::LocalFinalDemand(id) => Some((id, fact.quantity)),
            OutboundOrderId::Delivery(_) => None,
        })
        .collect();
    groups
        .into_iter()
        .map(|(key @ (principal, good, unit), orders)| {
            let county = principals
                .get(&principal)
                .ok_or(ProductionProjectionError::State)?;
            let (good_label, unit_label) =
                labels(good, unit).ok_or(ProductionProjectionError::Content)?;
            let mut retailers = configured.remove(&key).unwrap_or_default();
            retailers.extend(orders.iter().map(|row| row.order.retailer_site_id));
            let ordered = sum(orders.iter().map(|row| row.order.ordered))?;
            let fulfilled = sum(orders.iter().map(|row| row.order.fulfilled))?;
            let expired = sum(orders.iter().map(|row| row.expired))?;
            let outstanding = ordered
                .checked_sub(fulfilled)
                .and_then(|value| value.checked_sub(expired))
                .ok_or(ProductionProjectionError::State)?;
            let retail_stock_on_hand = sum(retailers
                .iter()
                .map(|site| inventory.get(&(*site, good, unit)).copied().unwrap_or(0)))?;
            let completed = completed
                .map(|(prior, _)| completed_final(prior.period, fulfilled, &orders, &quantities))
                .transpose()?;
            Ok(ProductionFinalDemandAccount {
                demand_principal_id: digest_hex(&principal.as_bytes()),
                county_geoid: String::from_utf8(county.county_geoid.to_vec())
                    .map_err(|_| ProductionProjectionError::State)?,
                good_id: digest_hex(&good.as_bytes()),
                unit_id: digest_hex(&unit.as_bytes()),
                good: good_label,
                unit: unit_label,
                ordered,
                fulfilled,
                expired,
                outstanding,
                retail_stock_on_hand,
                retailer_site_ids: retailers
                    .iter()
                    .map(|id| digest_hex(&id.as_bytes()))
                    .collect(),
                total_order_count: u64::try_from(orders.len())
                    .map_err(|_| ProductionProjectionError::Arithmetic)?,
                orders: listed_orders(&orders, &actual, &latest)?,
                completed,
            })
        })
        .collect()
}

fn active_final_orders(
    current: &MaterialCircuitState,
    history: &super::history::OrderHistory,
) -> Result<BTreeSet<OrderId>> {
    let actual: BTreeMap<_, _> = current
        .final_demand_orders
        .iter()
        .map(|row| (row.order_id, row))
        .collect();
    for (id, row) in &actual {
        if history
            .final_orders
            .get(id)
            .is_none_or(|known| known.order != **row || known.expired != 0)
        {
            return Err(ProductionProjectionError::State);
        }
    }
    for (id, known) in &history.final_orders {
        let done = known
            .order
            .fulfilled
            .checked_add(known.expired)
            .ok_or(ProductionProjectionError::Arithmetic)?;
        if done > known.order.ordered || (done < known.order.ordered && !actual.contains_key(id)) {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(actual.into_keys().collect())
}

fn completed_final(
    period: u64,
    fulfilled: u64,
    orders: &[&super::history::FinalOrder],
    quantities: &BTreeMap<OrderId, u64>,
) -> Result<CompletedProductionFinalDemand> {
    let newly_fulfilled = sum(orders
        .iter()
        .map(|row| quantities.get(&row.order.order_id).copied().unwrap_or(0)))?;
    let opening_fulfilled = fulfilled
        .checked_sub(newly_fulfilled)
        .ok_or(ProductionProjectionError::State)?;
    Ok(CompletedProductionFinalDemand {
        period,
        opening_fulfilled,
        newly_fulfilled,
        closing_fulfilled: fulfilled,
    })
}

fn listed_orders(
    orders: &[&super::history::FinalOrder],
    actual: &BTreeSet<OrderId>,
    latest: &BTreeSet<OrderId>,
) -> Result<Vec<ProductionFinalDemandOrder>> {
    orders
        .iter()
        .filter(|known| {
            actual.contains(&known.order.order_id) || latest.contains(&known.order.order_id)
        })
        .map(|known| {
            let row = &known.order;
            Ok(ProductionFinalDemandOrder {
                order_id: digest_hex(&row.order_id.as_bytes()),
                retailer_site_id: digest_hex(&row.retailer_site_id.as_bytes()),
                ordered: row.ordered,
                fulfilled: row.fulfilled,
                expired: known.expired,
                outstanding: row
                    .ordered
                    .checked_sub(row.fulfilled)
                    .and_then(|value| value.checked_sub(known.expired))
                    .ok_or(ProductionProjectionError::State)?,
            })
        })
        .collect()
}

fn sum(values: impl IntoIterator<Item = u64>) -> Result<u64> {
    values.into_iter().try_fold(0_u64, |sum, value| {
        sum.checked_add(value)
            .ok_or(ProductionProjectionError::Arithmetic)
    })
}
