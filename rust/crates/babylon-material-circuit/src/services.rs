//! Finite native services in the same resource and monetary authority as goods.
mod admission;
mod close;
mod market;
mod model;
mod validation;
use crate::{GoodId, MaterialCircuitError, MaterialCircuitState, ProcessOutput, UnitId};
pub use admission::{recurring_service_order_id, recurring_service_topup_order_id};
pub(crate) use close::ServiceClose;
pub use model::*;
pub(crate) use validation::{canonicalize, validate};
pub(crate) type Result<T> = std::result::Result<T, MaterialCircuitError>;

impl CommodityDefinition {
    /// Positive shipment mass exists only for stored commodities.
    /// # Errors
    /// Refuses service units and nonpositive captured mass.
    pub fn grams_per_unit(&self) -> Result<u64> {
        match self.kind {
            CommodityKind::Storable { grams_per_unit } if grams_per_unit > 0 => Ok(grams_per_unit),
            _ => Err(MaterialCircuitError::MassInvariant),
        }
    }
}
pub(crate) fn kind(
    state: &MaterialCircuitState,
    good: GoodId,
    unit: UnitId,
) -> Result<CommodityKind> {
    state
        .commodities
        .binary_search_by_key(&(good, unit), |r| (r.good_id, r.unit_id))
        .ok()
        .map(|i| state.commodities[i].kind)
        .ok_or(MaterialCircuitError::MassInvariant)
}
pub(crate) fn stage(
    state: &MaterialCircuitState,
    output: &ProcessOutput,
) -> Result<Option<ServiceStage>> {
    Ok(match kind(state, output.good_id, output.unit_id)? {
        CommodityKind::Storable { .. } => None,
        CommodityKind::PeriodService { stage } => Some(stage),
    })
}
pub(crate) fn is_service(state: &MaterialCircuitState, good: GoodId, unit: UnitId) -> bool {
    matches!(
        kind(state, good, unit),
        Ok(CommodityKind::PeriodService { .. })
    )
}

/// Planning may count a finite requested grant; actual work must obtain it anew.
pub(crate) fn planning_grants(
    state: &MaterialCircuitState,
    period: u64,
    inventory: &mut crate::inventory::InventoryLedger,
) -> Result<()> {
    let requirements = input_requirements(state, true)?;
    let mut future = std::collections::BTreeMap::new();
    for order in &state.service_orders {
        if order.performance_period == period {
            if let crate::AccountId::Site(site) = order.buyer {
                crate::inventory::credit_inventory(
                    &mut future,
                    (site, order.good_id, order.unit_id),
                    order.quantity,
                )?;
            }
        }
    }
    if let crate::CircuitAccounting::Monetary(e) = &state.accounting {
        if let Some(r) = &e.recurring {
            for policy in &r.service_inputs {
                crate::inventory::credit_inventory(
                    &mut future,
                    (policy.buyer_site_id, policy.good_id, policy.unit_id),
                    required_input(&requirements, policy),
                )?;
            }
        }
    }
    for (key, q) in future {
        crate::inventory::credit_inventory(inventory, key, q)?;
    }
    Ok(())
}

type InputRequirements = std::collections::BTreeMap<(crate::SiteId, GoodId, UnitId), u128>;
/// Build once per planning boundary; coefficients preserve their declared native units.
pub(crate) fn input_requirements(
    state: &MaterialCircuitState,
    next_plan: bool,
) -> Result<InputRequirements> {
    let owners: std::collections::BTreeMap<_, _> = state
        .process_outputs
        .iter()
        .map(|o| (o.process_id, o.site_id))
        .collect();
    let plans: std::collections::BTreeMap<_, _> = if next_plan {
        match &state.accounting {
            crate::CircuitAccounting::Monetary(e) => e
                .recurring
                .as_ref()
                .map(|r| {
                    r.production
                        .iter()
                        .map(|p| (p.process_id, p.planned_batches))
                        .collect()
                })
                .unwrap_or_default(),
            crate::CircuitAccounting::PhysicalControl => std::collections::BTreeMap::new(),
        }
    } else {
        state
            .production_commitments
            .iter()
            .filter(|p| p.period == state.period)
            .map(|p| (p.process_id, p.planned_batches))
            .collect()
    };
    let mut result = InputRequirements::new();
    for coefficient in &state.input_coefficients {
        if !is_service(state, coefficient.good_id, coefficient.unit_id) {
            continue;
        }
        let site = *owners
            .get(&coefficient.process_id)
            .ok_or(MaterialCircuitError::ProcessInvariant)?;
        let batches = plans.get(&coefficient.process_id).copied().unwrap_or(0);
        let requested = u128::from(batches) * u128::from(coefficient.quantity_per_batch);
        let quantity = result
            .entry((site, coefficient.good_id, coefficient.unit_id))
            .or_default();
        *quantity = quantity
            .checked_add(requested)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(result)
}
/// Captured policy quantities cap the recipe-derived requirement; they do not create demand.
pub(crate) fn required_input(requirements: &InputRequirements, policy: &ServiceInputPolicy) -> u64 {
    u64::try_from(
        requirements
            .get(&(policy.buyer_site_id, policy.good_id, policy.unit_id))
            .copied()
            .unwrap_or(0)
            .min(u128::from(policy.quantity_per_period))
            .min(u128::from(policy.maximum_purchase)),
    )
    .expect("requirement capped by a u64 policy")
}
