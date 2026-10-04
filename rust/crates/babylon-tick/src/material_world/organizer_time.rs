//! Actual residual household time, shared by every organizational alias.
use super::MaterialWorldError;
use babylon_kernel::content_digest::sha256_of;
use babylon_material_circuit::{
    CircuitAccounting, FinalDemandPrincipalId, HouseholdContributionUse, HouseholdTimeAccounting,
    HouseholdTimeBook, MaterialCircuitState,
};
use babylon_practice_contract::{
    OrganizerConfig, OrganizerError, OrganizerPeriodTimeResources, OrganizerState,
    OrganizerTimeBinding, OrganizerTimeBindingMode, PracticeResourceAllocationMode,
    PracticeResourceCapacity, PracticeResourceId, PracticeResourceOwner, PracticeUnitId,
};
use std::collections::BTreeMap;

fn book(state: &MaterialCircuitState) -> Result<&HouseholdTimeBook, MaterialWorldError> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Err(MaterialWorldError::Organizer(
            OrganizerError::TimeBindingMismatch,
        ));
    };
    let HouseholdTimeAccounting::Modeled(book) = &economy.household_time else {
        return Err(MaterialWorldError::Organizer(
            OrganizerError::TimeBindingMismatch,
        ));
    };
    Ok(book)
}

pub(super) fn resources(
    state: &MaterialCircuitState,
    config: &OrganizerConfig,
    period: u64,
) -> Result<OrganizerPeriodTimeResources, MaterialWorldError> {
    let OrganizerTimeBindingMode::Household { bindings } = &config.time_binding else {
        return Err(MaterialWorldError::Organizer(
            OrganizerError::TimeBindingMismatch,
        ));
    };
    let time = book(state)?;
    let rows: BTreeMap<_, _> = time
        .receipts
        .iter()
        .map(|row| (row.principal_id, row))
        .collect();
    let mut spent = BTreeMap::<_, u64>::new();
    for receipt in &time.contributions {
        if receipt.period != period {
            return Err(MaterialWorldError::PeriodMismatch);
        }
        let value = spent.entry(receipt.contribution.principal_id).or_default();
        *value = value
            .checked_add(receipt.contribution.hours)
            .ok_or(MaterialWorldError::Arithmetic)?;
    }
    let mut capacities = BTreeMap::new();
    let mut linked = Vec::with_capacity(bindings.len());
    let mut unit = None;
    for binding in bindings {
        let principal = FinalDemandPrincipalId::from_bytes(binding.principal_id);
        let row = rows.get(&principal).ok_or(MaterialWorldError::Organizer(
            OrganizerError::TimeCapacityMissing,
        ))?;
        if row.period != period || unit.is_some_and(|value| value != row.labor_unit_id) {
            return Err(MaterialWorldError::Organizer(
                OrganizerError::TimeUnitMismatch,
            ));
        }
        unit = Some(row.labor_unit_id);
        let mut identity = b"babylon.household-organizer-budget.v1\0".to_vec();
        identity.extend_from_slice(&principal.as_bytes());
        identity.extend_from_slice(&row.labor_unit_id.as_bytes());
        let resource_id = PracticeResourceId::from_bytes(sha256_of(&identity));
        let available = row
            .contribution_available_hours
            .checked_sub(*spent.get(&principal).unwrap_or(&0))
            .ok_or(MaterialWorldError::Arithmetic)?;
        capacities.insert(
            resource_id,
            PracticeResourceCapacity {
                resource_id,
                owner: PracticeResourceOwner::Shared,
                unit_id: PracticeUnitId::from_bytes(row.labor_unit_id.as_bytes()),
                mode: PracticeResourceAllocationMode::DivisibleProRata,
                available,
            },
        );
        linked.push(OrganizerTimeBinding {
            contributor_id: binding.contributor_id,
            budget_id: resource_id,
        });
    }
    let unit = unit.ok_or(MaterialWorldError::Organizer(
        OrganizerError::TimeCapacityMissing,
    ))?;
    Ok(OrganizerPeriodTimeResources {
        period,
        unit_id: PracticeUnitId::from_bytes(unit.as_bytes()),
        bindings: linked,
        capacities: capacities.into_values().collect(),
    })
}

pub(super) fn uses(
    config: &OrganizerConfig,
    organizer: &OrganizerState,
    period: u64,
    material: &MaterialCircuitState,
) -> Result<Vec<HouseholdContributionUse>, MaterialWorldError> {
    let OrganizerTimeBindingMode::Household { bindings } = &config.time_binding else {
        return Err(MaterialWorldError::Organizer(
            OrganizerError::TimeBindingMismatch,
        ));
    };
    babylon_practice_contract::validate_organizer_pair(config, organizer)?;
    let principals: BTreeMap<_, _> = bindings
        .iter()
        .map(|binding| {
            (
                binding.contributor_id,
                FinalDemandPrincipalId::from_bytes(binding.principal_id),
            )
        })
        .collect();
    let mut result = Vec::new();
    for receipt in babylon_practice_contract::organizer_period_receipts(organizer, period) {
        if receipt.choice == babylon_practice_contract::OrganizerChoice::Collect {
            let row = organizer
                .collection_receipts
                .iter()
                .find(|row| row.practice == *receipt)
                .ok_or(MaterialWorldError::Wire)?;
            babylon_practice_contract::validate_organizer_collection_fact(
                config,
                &row.commitment,
                &row.fact,
            )?;
            if row.fact.performed_hours > 0 {
                let time = book(material)?;
                if time
                    .receipts
                    .iter()
                    .filter(|actual| {
                        actual.period == period
                            && actual.principal_id.as_bytes() == row.fact.household_principal_id
                            && actual.labor_unit_id.as_bytes() == row.fact.labor_unit_id
                    })
                    .count()
                    != 1
                {
                    return Err(MaterialWorldError::Wire);
                }
                if time
                    .contributions
                    .iter()
                    .filter(|actual| {
                        actual.period == period
                            && actual.contribution.use_id == row.fact.contribution_use_id
                            && actual.contribution.principal_id.as_bytes()
                                == row.fact.household_principal_id
                            && actual.contribution.actor_id == row.fact.actor_id
                            && actual.contribution.contributor_id == row.fact.contributor_id
                            && actual.contribution.hours == row.fact.performed_hours
                    })
                    .count()
                    != 1
                {
                    return Err(MaterialWorldError::Wire);
                }
            }
            continue;
        }
        for usage in &receipt.time_use {
            let principal_id =
                *principals
                    .get(&usage.contributor_id)
                    .ok_or(MaterialWorldError::Organizer(
                        OrganizerError::TimeBindingMismatch,
                    ))?;
            let mut identity = b"babylon.organizer-household-contribution.v1\0".to_vec();
            identity.extend_from_slice(&receipt.receipt_id);
            identity.extend_from_slice(&usage.actor_id.to_be_bytes());
            identity.extend_from_slice(&usage.contributor_id.to_be_bytes());
            result.push(HouseholdContributionUse {
                use_id: sha256_of(&identity),
                principal_id,
                actor_id: usage.actor_id,
                contributor_id: usage.contributor_id,
                hours: usage.hours,
            });
        }
    }
    result.sort_by_key(|usage| usage.use_id);
    Ok(result)
}
