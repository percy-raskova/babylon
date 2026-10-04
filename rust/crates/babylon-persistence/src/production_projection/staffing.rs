//! Worker accounts from authenticated adjacent graph states and native event rows.
//! This projection checks receipt/end-point agreement; it never runs hiring policy.

use std::collections::BTreeMap;

use babylon_bsl::identity_codec::StableBslValue;
use babylon_graph::{stable_element::StableElementKey, stable_state::StableGraphState};
use babylon_tick::{
    material_staffing::{StaffingComposition, STAFFING_COMPOSITION_ID},
    material_world::{MaterialTickReceipts, MaterialWorldRegister},
};

use super::ProductionProjectionError;
use crate::{
    michigan_economy::digest_hex, production_observation::CompletedProductionStaffing,
    production_observation::ProductionStaffingAccount,
    production_observation::ProductionStaffingSubject, stored_tick::StoredEvent,
};

mod members;
use members::{StaffingGraph, StaffingWitnesses};

type Result<T> = std::result::Result<T, ProductionProjectionError>;
const EVENT: &str = "WORKFORCE_STAFFING";
const INTEGER_FIELDS: [&str; 12] = [
    "period",
    "opening-employed",
    "opening-reserve",
    "previous-unretained-hours",
    "current-unretained-hours",
    "retained-hours",
    "target-employed",
    "hires",
    "separations",
    "closing-employed",
    "closing-reserve",
    "next-opening-hours",
];

pub(crate) fn project_staffing_accounts(
    composition: &StaffingComposition,
    graph: &StableGraphState,
    register: &MaterialWorldRegister,
    opening: Option<&StableGraphState>,
    events: &[StoredEvent],
    period_receipts: Option<&MaterialTickReceipts>,
) -> Result<Vec<ProductionStaffingAccount>> {
    let tick = register.completed_tick();
    if (tick == 0) != opening.is_none()
        || (tick == 0) != period_receipts.is_none()
        || (tick == 0 && !events.is_empty())
        || tick.checked_add(1) != Some(register.state().period)
        || opening.is_some_and(|prior| prior.scenario_scope() != graph.scenario_scope())
    {
        return Err(ProductionProjectionError::History);
    }
    let mut receipts = event_receipts(events)?;
    let current_graph = StaffingGraph::new(graph)?;
    let prior_graph = opening.map(StaffingGraph::new).transpose()?;
    let mut witnesses = StaffingWitnesses::new(register, period_receipts)?;
    let mut labor = current_labor(register)?;
    let mut accounts = Vec::with_capacity(composition.bindings().len());
    for binding in composition.bindings() {
        let StableElementKey::Node {
            scenario,
            local_name,
        } = binding.subject()
        else {
            return Err(ProductionProjectionError::Content);
        };
        if scenario != graph.scenario_scope() {
            return Err(ProductionProjectionError::State);
        }
        let closing = current_graph.stocks(binding)?;
        let pool = binding.pool();
        let next_hours = closing
            .employed
            .checked_mul(pool.policy().hours_per_person())
            .ok_or(ProductionProjectionError::Arithmetic)?;
        if labor.remove(&(pool.site_id(), pool.unit_id())) != Some(next_hours) {
            return Err(ProductionProjectionError::State);
        }
        let completed = if opening.is_some() {
            let key = binding
                .subject()
                .canonical_bytes()
                .map_err(|_| ProductionProjectionError::State)?;
            let values = receipts
                .remove(&key)
                .ok_or(ProductionProjectionError::History)?;
            Some(completed_account(
                tick,
                prior_graph
                    .as_ref()
                    .ok_or(ProductionProjectionError::History)?
                    .stocks(binding)?,
                closing,
                next_hours,
                values,
            )?)
        } else {
            None
        };
        let members = witnesses.project_members(binding, &current_graph, prior_graph.as_ref())?;
        reconcile_member_changes(completed.as_ref(), &members)?;
        accounts.push(ProductionStaffingAccount {
            pool_id: digest_hex(&pool.pool_id().as_bytes()),
            site_id: digest_hex(&pool.site_id().as_bytes()),
            unit_id: digest_hex(&pool.unit_id().as_bytes()),
            subject: ProductionStaffingSubject {
                scenario: scenario.clone(),
                local_name: local_name.clone(),
            },
            hours_per_person: pool.policy().hours_per_person(),
            labor_force: pool.labor_force(),
            employed: closing.employed,
            reserve: closing.reserve,
            previous_unretained_hours: closing.previous,
            next_opening_period: register.state().period,
            next_opening_hours: next_hours,
            members,
            completed,
        });
    }
    witnesses.finish()?;
    if !receipts.is_empty() || !labor.is_empty() {
        return Err(ProductionProjectionError::History);
    }
    Ok(accounts)
}

fn event_receipts(events: &[StoredEvent]) -> Result<BTreeMap<Vec<u8>, [u64; 12]>> {
    let mut receipts = BTreeMap::new();
    for event in events {
        if event.event_type != EVENT && event.emitting_rule != STAFFING_COMPOSITION_ID {
            continue;
        }
        if event.event_type != EVENT
            || event.emitting_rule != STAFFING_COMPOSITION_ID
            || event.choice_receipt_ordinal.is_some()
        {
            return Err(ProductionProjectionError::History);
        }
        let (subject, values) = event_fields(event)?;
        if receipts
            .insert(
                subject
                    .canonical_bytes()
                    .map_err(|_| ProductionProjectionError::State)?,
                values,
            )
            .is_some()
        {
            return Err(ProductionProjectionError::History);
        }
    }
    Ok(receipts)
}

fn current_labor(
    register: &MaterialWorldRegister,
) -> Result<
    BTreeMap<
        (
            babylon_material_circuit::SiteId,
            babylon_material_circuit::UnitId,
        ),
        u64,
    >,
> {
    let mut labor = BTreeMap::new();
    for row in register
        .state()
        .labor
        .iter()
        .filter(|row| row.period == register.state().period)
    {
        if labor
            .insert((row.site_id, row.unit_id), row.available)
            .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(labor)
}

fn reconcile_member_changes(
    completed: Option<&CompletedProductionStaffing>,
    members: &[crate::production_observation::ProductionStaffingMemberAccount],
) -> Result<()> {
    if completed.is_some_and(|done| {
        members
            .iter()
            .filter_map(|row| row.completed.as_ref())
            .try_fold((0_u64, 0_u64), |(hires, separations), row| {
                Some((
                    hires.checked_add(row.hires)?,
                    separations.checked_add(row.separations)?,
                ))
            })
            != Some((done.hires, done.separations))
    }) {
        return Err(ProductionProjectionError::History);
    }
    Ok(())
}

#[derive(Clone, Copy)]
struct Stocks {
    employed: u64,
    reserve: u64,
    previous: u64,
}

fn integer(value: &StableBslValue) -> Result<u64> {
    let StableBslValue::Int(value) = value else {
        return Err(ProductionProjectionError::State);
    };
    let value = u64::try_from(*value).map_err(|_| ProductionProjectionError::State)?;
    Ok(value)
}

fn event_fields(event: &StoredEvent) -> Result<(&StableElementKey, [u64; 12])> {
    if event.fields.len() != INTEGER_FIELDS.len() + 1 {
        return Err(ProductionProjectionError::History);
    }
    let fields: BTreeMap<_, _> = event
        .fields
        .iter()
        .map(|(name, value)| (name.as_str(), value))
        .collect();
    if fields.len() != event.fields.len() {
        return Err(ProductionProjectionError::History);
    }
    let Some(StableBslValue::Node(subject @ StableElementKey::Node { .. })) = fields.get("subject")
    else {
        return Err(ProductionProjectionError::History);
    };
    let mut values = [0; 12];
    for (index, name) in INTEGER_FIELDS.iter().enumerate() {
        values[index] = integer(fields.get(name).ok_or(ProductionProjectionError::History)?)?;
    }
    Ok((subject, values))
}

fn completed_account(
    tick: u64,
    opening: Stocks,
    closing: Stocks,
    next_hours: u64,
    values: [u64; 12],
) -> Result<CompletedProductionStaffing> {
    let [period, opening_employed, opening_reserve, previous_unretained_hours, current_unretained_hours, retained_hours, target_employed, hires, separations, closing_employed, closing_reserve, next_opening_hours] =
        values;
    if period != tick
        || opening_employed != opening.employed
        || opening_reserve != opening.reserve
        || previous_unretained_hours != opening.previous
        || current_unretained_hours != closing.previous
        || closing_employed != closing.employed
        || closing_reserve != closing.reserve
        || target_employed != closing.employed
        || next_opening_hours != next_hours
        || (hires > 0 && separations > 0)
        || hires > opening.reserve
        || separations > opening.employed
        || opening
            .employed
            .checked_add(hires)
            .and_then(|n| n.checked_sub(separations))
            != Some(closing.employed)
        || opening
            .reserve
            .checked_add(separations)
            .and_then(|n| n.checked_sub(hires))
            != Some(closing.reserve)
    {
        return Err(ProductionProjectionError::History);
    }
    Ok(CompletedProductionStaffing {
        period,
        opening_employed,
        opening_reserve,
        previous_unretained_hours,
        current_unretained_hours,
        retained_hours,
        target_employed,
        hires,
        separations,
    })
}

#[cfg(test)]
mod tests;

#[cfg(test)]
mod paid_tests;
