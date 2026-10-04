//! Captured resident eligibility reaches the sole material-time account.
use super::{quantity, Builder, NationalOpeningError, Result};
use crate::{
    economic_catalog::EconomicHouseholdSeed, national_household_allocation::HouseholdBudgetKey,
    national_household_time_allocation::NationalHouseholdTimeAllocation,
};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    FinalDemandPrincipalId, HouseholdKind, HouseholdNeedBasis, HouseholdTimeAccounting,
    HouseholdTimeBook, HouseholdTimeCommitment, HouseholdTimePolicy, HouseholdUnmetTimeBurden,
};
use std::collections::BTreeMap;

pub(super) fn wire(
    builder: &mut Builder<'_>,
    domestic: &NationalHouseholdTimeAllocation,
) -> Result<()> {
    let mut workforce = BTreeMap::<FinalDemandPrincipalId, u64>::new();
    for pool in &builder.opening.staffing {
        for member in &pool.members {
            let total = workforce.entry(member.member.household_id()).or_default();
            *total = total
                .checked_add(member.member.labor_force())
                .ok_or(NationalOpeningError::Arithmetic)?;
        }
    }
    let mut policies = Vec::with_capacity(builder.opening.households.len());
    for household in &builder.opening.households {
        let key = *builder
            .household_keys
            .get(&household.principal_id)
            .ok_or(NationalOpeningError::Identity)?;
        let force = workforce.get(&household.principal_id).copied().unwrap_or(0);
        let eligible = eligibility(builder, household, key, force, domestic)?;
        let (basis, protected, provisioning) = match household.kind {
            HouseholdKind::Ordinary => (
                HouseholdNeedBasis::Households,
                builder
                    .policy
                    .household_time
                    .ordinary_protected_hours_per_household,
                builder
                    .policy
                    .household_time
                    .ordinary_provisioning_hours_per_household,
            ),
            HouseholdKind::CollectiveResidence => (
                HouseholdNeedBasis::Persons,
                builder
                    .policy
                    .household_time
                    .collective_protected_hours_per_person,
                builder
                    .policy
                    .household_time
                    .collective_provisioning_hours_per_person,
            ),
        };
        let mut burdens = Vec::new();
        for (key, hours) in &builder.policy.household_time.unmet_hours_per_unit {
            let need = builder
                .policy
                .household_needs
                .iter()
                .find(|need| need.key == *key)
                .ok_or(NationalOpeningError::Policy)?;
            if household.kind == HouseholdKind::CollectiveResidence
                && need.basis == HouseholdNeedBasis::Households
            {
                continue;
            }
            let good = builder.commodity(key)?;
            burdens.push(HouseholdUnmetTimeBurden {
                good_id: good.good_id,
                unit_id: good.unit_id,
                hours_per_unmet_unit: *hours,
            });
        }
        policies.push(HouseholdTimePolicy {
            principal_id: household.principal_id,
            labor_unit_id: builder.labor_unit,
            eligible_persons: eligible,
            hours_per_eligible_person: builder.policy.household_time.hours_per_eligible_person,
            protected: HouseholdTimeCommitment {
                basis,
                hours_per_basis: protected,
            },
            routine_provisioning: HouseholdTimeCommitment {
                basis,
                hours_per_basis: provisioning,
            },
            unmet_burdens: burdens,
        });
    }
    builder.opening.policies.household_time = HouseholdTimeAccounting::Modeled(
        HouseholdTimeBook::new(policies).map_err(NationalOpeningError::TimeAccount)?,
    );
    Ok(())
}

fn eligibility(
    builder: &Builder<'_>,
    household: &EconomicHouseholdSeed,
    key: HouseholdBudgetKey,
    workforce: u64,
    domestic: &NationalHouseholdTimeAllocation,
) -> Result<u64> {
    let eligible = if let Some(eligible) = builder.eligible_overrides.get(&household.principal_id) {
        *eligible
    } else {
        match household.location {
            EconomicLocation::County(county) => {
                let rows = domestic
                    .county(county.geoid())
                    .map_err(NationalOpeningError::HouseholdTime)?
                    .budgets();
                rows.binary_search_by_key(&key, |row| row.key)
                    .map(|index| rows[index].eligible_16_plus)
                    .map_err(|_| NationalOpeningError::Identity)?
            }
            EconomicLocation::Foreign(_) | EconomicLocation::Dependency(_) => {
                if key != HouseholdBudgetKey::PooledExternal {
                    return Err(NationalOpeningError::Identity);
                }
                let designed = u64::try_from(
                    u128::from(household.persons)
                        * u128::from(builder.policy.household_time.external_eligible_persons_bps)
                        / 10_000,
                )
                .map_err(|_| NationalOpeningError::Arithmetic)?;
                designed.max(workforce)
            }
        }
    };
    if workforce > eligible || eligible > household.persons {
        return Err(NationalOpeningError::SourceScope);
    }
    quantity(
        eligible,
        builder.policy.household_time.hours_per_eligible_person,
    )?;
    Ok(eligible)
}
