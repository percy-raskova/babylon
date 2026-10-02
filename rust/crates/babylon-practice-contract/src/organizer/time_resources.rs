//! Period-specific finite time; aliases bind one shared supply exactly once.
use super::transition::response_intent;
use super::{
    validate_organizer_config, OrganizerConfig, OrganizerError, OrganizerPartner, OrganizerTimeUse,
};
use crate::{
    allocate_practice_resources, derive_practice_resource_request, PracticeIntent,
    PracticeResourceAllocationContract, PracticeResourceAllocationMode, PracticeResourceCapacity,
    PracticeResourceId, PracticeResourceLocator, PracticeResourceOwner,
    PracticeResourceRequirement, PracticeUnitId,
};
use babylon_kernel::content_digest::sha256_of;
use std::collections::{BTreeMap, BTreeSet};

/// An organizational alias draws only from this explicitly bound time budget.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OrganizerTimeBinding {
    pub contributor_id: u64,
    pub budget_id: PracticeResourceId,
}

/// Caller-supplied opening capacity for exactly one resolving period and unit.
/// Capacities contain one row per shared budget, never one copy per alias.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OrganizerPeriodTimeResources {
    pub period: u64,
    pub unit_id: PracticeUnitId,
    pub bindings: Vec<OrganizerTimeBinding>,
    pub capacities: Vec<PracticeResourceCapacity>,
}

/// Named unit for explicit fixed-time controls. Captured material resources use
/// their supplied physical unit without conversion to this control identity.
#[must_use]
pub fn organizer_time_unit_id() -> PracticeUnitId {
    PracticeUnitId::from_bytes(sha256_of(b"babylon.organizer-whole-hour.v1"))
}

/// Explicit fixed-time control inputs, separate from the real resource path.
/// # Errors
/// Refuses invalid captured commitments or a zero resolving period.
pub fn organizer_fixed_time_resources(
    config: &OrganizerConfig,
    period: u64,
) -> Result<OrganizerPeriodTimeResources, OrganizerError> {
    validate_organizer_config(config)?;
    if period == 0 {
        return Err(OrganizerError::TimePeriodMismatch);
    }
    let unit_id = organizer_time_unit_id();
    let mut bindings = Vec::with_capacity(config.participants.len());
    let mut capacities = Vec::with_capacity(config.participants.len());
    for participant in &config.participants {
        let mut bytes = b"babylon.organizer-contributor.v1".to_vec();
        bytes.extend_from_slice(&participant.contributor_id.to_be_bytes());
        let budget_id = PracticeResourceId::from_bytes(sha256_of(&bytes));
        bindings.push(OrganizerTimeBinding {
            contributor_id: participant.contributor_id,
            budget_id,
        });
        capacities.push(PracticeResourceCapacity {
            owner: PracticeResourceOwner::Shared,
            resource_id: budget_id,
            unit_id,
            mode: PracticeResourceAllocationMode::DivisibleProRata,
            available: participant.available_hours,
        });
    }
    Ok(OrganizerPeriodTimeResources {
        period,
        unit_id,
        bindings,
        capacities,
    })
}

pub(super) fn validate_resources(
    config: &OrganizerConfig,
    period: u64,
    resources: &OrganizerPeriodTimeResources,
) -> Result<(), OrganizerError> {
    if resources.period != period || resources.period == 0 {
        return Err(OrganizerError::TimePeriodMismatch);
    }
    if resources.unit_id.as_bytes() == [0; 32] {
        return Err(OrganizerError::TimeUnitMismatch);
    }
    if resources.bindings.len() != config.participants.len() {
        return Err(OrganizerError::TimeBindingMismatch);
    }
    if resources.capacities.len() > 16 {
        return Err(OrganizerError::SizeLimit);
    }
    let mut capacities = BTreeSet::new();
    for capacity in &resources.capacities {
        if !capacities.insert(capacity.resource_id) {
            return Err(OrganizerError::TimeCapacityDuplicate);
        }
        if capacity.unit_id != resources.unit_id {
            return Err(OrganizerError::TimeUnitMismatch);
        }
        if capacity.owner != PracticeResourceOwner::Shared
            || capacity.mode != PracticeResourceAllocationMode::DivisibleProRata
            || capacity.resource_id.as_bytes() == [0; 32]
        {
            return Err(OrganizerError::TimeCapacityScope);
        }
    }
    if resources.capacities.len() > config.participants.len() {
        return Err(OrganizerError::TimeCapacityScope);
    }
    let participants: BTreeSet<_> = config
        .participants
        .iter()
        .map(|row| row.contributor_id)
        .collect();
    let mut contributors = BTreeSet::new();
    let mut bound = BTreeSet::new();
    for binding in &resources.bindings {
        if !participants.contains(&binding.contributor_id)
            || !contributors.insert(binding.contributor_id)
        {
            return Err(OrganizerError::TimeBindingMismatch);
        }
        if !capacities.contains(&binding.budget_id) {
            return Err(OrganizerError::TimeCapacityMissing);
        }
        bound.insert(binding.budget_id);
    }
    if bound != capacities {
        return Err(OrganizerError::TimeCapacityScope);
    }
    Ok(())
}

type Selected = BTreeMap<(u64, PracticeResourceId), Vec<OrganizerTimeUse>>;

fn select_contributions(
    config: &OrganizerConfig,
    resources: &OrganizerPeriodTimeResources,
    actor_id: u64,
    cost: u64,
    selected: &mut Selected,
) -> Result<(), OrganizerError> {
    let bindings: BTreeMap<_, _> = resources
        .bindings
        .iter()
        .map(|row| (row.contributor_id, row.budget_id))
        .collect();
    let mut remaining = cost;
    for participant in &config.participants {
        let offered = participant
            .commitments
            .iter()
            .find(|row| row.actor_id == actor_id)
            .map_or(0, |row| row.hours);
        let hours = remaining.min(offered);
        if hours == 0 {
            continue;
        }
        remaining -= hours;
        let budget = *bindings
            .get(&participant.contributor_id)
            .ok_or(OrganizerError::TimeBindingMismatch)?;
        selected
            .entry((actor_id, budget))
            .or_default()
            .push(OrganizerTimeUse {
                contributor_id: participant.contributor_id,
                actor_id,
                hours,
            });
    }
    if remaining != 0 {
        return Err(OrganizerError::ResourceAllocation);
    }
    Ok(())
}

/// A valid short allocation is ordinary incompletion: return no actual debit.
pub(super) fn allocate_hours(
    config: &OrganizerConfig,
    intent: &PracticeIntent,
    partner: Option<&OrganizerPartner>,
    own_hours: u64,
    resources: &OrganizerPeriodTimeResources,
) -> Result<Option<Vec<OrganizerTimeUse>>, OrganizerError> {
    let contract = PracticeResourceAllocationContract::conservation_first();
    let mut actors = vec![(intent.clone(), own_hours)];
    if let Some(partner) = partner {
        actors.push((
            response_intent(intent, config, partner)?,
            config.partner_response_hours,
        ));
    }
    let mut selected = Selected::new();
    let mut requests = Vec::new();
    for (actor_intent, cost) in actors {
        let actor_id = u64::from_be_bytes(actor_intent.actor_org_id.to_bytes());
        select_contributions(config, resources, actor_id, cost, &mut selected)?;
        for ((actor, budget), aliases) in &selected {
            if *actor != actor_id {
                continue;
            }
            let quantity = aliases.iter().try_fold(0_u64, |n, row| {
                n.checked_add(row.hours).ok_or(OrganizerError::Arithmetic)
            })?;
            requests.push(
                derive_practice_resource_request(
                    &contract,
                    &actor_intent,
                    &PracticeResourceRequirement {
                        practice_id: actor_intent.practice_id,
                        locator: PracticeResourceLocator::Shared,
                        resource_id: *budget,
                        unit_id: resources.unit_id,
                        quantity,
                    },
                )
                .map_err(|_| OrganizerError::ResourceAllocation)?,
            );
        }
    }
    let allocation = allocate_practice_resources(&contract, &requests, &resources.capacities)
        .map_err(|_| OrganizerError::ResourceAllocation)?;
    if allocation
        .allocations()
        .iter()
        .any(|row| row.allocated() != row.requested())
    {
        return Ok(None);
    }
    let mut time_use: Vec<_> = selected.into_values().flatten().collect();
    time_use.sort_by_key(|row| (row.contributor_id, row.actor_id));
    Ok(Some(time_use))
}
