//! Bounded world cohorts. Trade dollars create neither people nor capacity.
use super::{actors, ActorContext, Builder, NationalOpeningError, Result};
use crate::economic_catalog::{
    EconomicSiteSource, ResidentStaffingMemberSeed, ResidentStaffingPoolSeed,
};
use crate::national_economy::{GameProfile, GameProfileWage};
use crate::national_household_allocation::HouseholdBudgetKey;
use crate::world_reference::WorldReference;

use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart, UsDependency};

use crate::national_economy;
use babylon_kernel::content_digest;
use babylon_material_circuit::{
    EmploymentTerms, LaborCompensation, SiteId, StaffingMemberBinding, StaffingMemberId,
    StaffingPolicy, StaffingPoolBinding, StaffingPoolId,
};

pub(super) fn world(builder: &mut Builder<'_>, source: &WorldReference) -> Result<()> {
    for counterpart in ForeignCounterpart::ALL {
        let profile = builder
            .policy
            .counterparts
            .get(&counterpart)
            .ok_or(NationalOpeningError::Policy)?
            .clone();
        let persons = source.counterpart(counterpart).population().known_persons();
        add(
            builder,
            EconomicLocation::Foreign(counterpart),
            persons,
            &profile,
            counterpart.as_str(),
        )?;
    }
    for dependency in UsDependency::ALL {
        let persons = source
            .dependency(dependency)
            .population()
            .persons()
            .unwrap_or(builder.policy.dependency.missing_population_game_persons);
        let profile = builder.policy.dependency.profile.clone();
        add(
            builder,
            EconomicLocation::Dependency(dependency),
            persons,
            &profile,
            source.dependency(dependency).name(),
        )?;
    }
    Ok(())
}

fn add(
    builder: &mut Builder<'_>,
    location: EconomicLocation,
    persons: u64,
    profile: &GameProfile,
    label: &str,
) -> Result<()> {
    let counts = profile
        .opening_counts(persons)
        .map_err(|_| NationalOpeningError::Policy)?;
    actors::household(
        builder,
        location,
        HouseholdBudgetKey::PooledExternal,
        counts.persons,
        counts.households,
        profile.price_scale_bps,
    )?;
    let functions = builder.policy.trades.functions();
    let weights = profile.function_weights_bps.as_slice();
    if weights.len() != functions.len() {
        return Err(NationalOpeningError::Policy);
    }
    let employed = partition(counts.employed, weights)?;
    let reserve = partition(counts.reserve, weights)?;
    for (index, function) in functions.iter().copied().enumerate() {
        let mut identity = b"NationalExternalSiteV1\0".to_vec();
        identity.extend_from_slice(&location.canonical_bytes());
        identity.extend_from_slice(function.source_key().as_bytes());
        let site_id = SiteId::from_bytes(content_digest::sha256_of(&identity));
        let workforce = employed[index]
            .checked_add(reserve[index])
            .ok_or(NationalOpeningError::Arithmetic)?;
        let wage = foreign_wage(builder, profile, function)?;
        let context = ActorContext {
            site_id,
            function,
            source_ownership: None,
            location,
            employed: employed[index],
            employee_persons: employed[index],
            force: workforce,
            wage,
            price_scale_bps: profile.price_scale_bps,
            planned_batches: 0,
            process_id: None,
        };
        let subject = actors::subject(location, function.source_key());
        actors::site(
            builder,
            context,
            subject.clone(),
            EconomicSiteSource::Designed {
                source_ownership: None,
                key: "bounded-counterpart-function".into(),
            },
            format!("{label}: {}", function.source_key()),
        )?;
        staffing(builder, site_id, subject, employed[index], reserve[index])?;
    }
    Ok(())
}

/// A foreign region or dependency pays a designed wage per hour (schema 7 and earlier), or, in
/// trade `f`, `floor(national_wage(f) x bps / 10_000)` (schema 8); a result of 0 is refused.
fn foreign_wage(
    builder: &Builder<'_>,
    profile: &GameProfile,
    function: EconomicFunction,
) -> Result<Currency> {
    match profile.wage {
        GameProfileWage::PerHour(wage) => Ok(wage),
        GameProfileWage::FractionOfUnitedStates { bps } => {
            let national = builder
                .pay
                .ok_or(NationalOpeningError::Policy)?
                .national_wage(function);
            let micro = national
                .micro_units()
                .checked_mul(i128::from(bps))
                .ok_or(NationalOpeningError::Arithmetic)?
                / 10_000;
            if micro <= 0 {
                return Err(NationalOpeningError::Policy);
            }
            Ok(Currency::from_micro_units(micro))
        }
    }
}

fn staffing(
    builder: &mut Builder<'_>,
    site: SiteId,
    workplace: StableElementKey,
    employed: u64,
    reserve: u64,
) -> Result<()> {
    let context = builder
        .actors
        .get(&site)
        .ok_or(NationalOpeningError::Identity)?;
    let mut pool_bytes = b"NationalStaffingPoolV1\0".to_vec();
    pool_bytes.extend_from_slice(&site.as_bytes());
    let pool = StaffingPoolBinding::try_new(
        StaffingPoolId::from_bytes(content_digest::sha256_of(&pool_bytes)),
        site,
        builder.labor_unit,
        context.force,
        StaffingPolicy::one_period(builder.policy.work_hours_per_person)
            .map_err(|_| NationalOpeningError::Policy)?,
        actors::sources(context),
    )
    .map_err(|_| NationalOpeningError::Policy)?;
    let mut members = vec![];
    if context.force > 0 {
        let principal = national_economy::household_principal(
            context.location,
            HouseholdBudgetKey::PooledExternal,
        );
        let mut bytes = b"NationalExternalWorkforceV2\0".to_vec();
        bytes.extend_from_slice(&site.as_bytes());
        bytes.extend_from_slice(&principal.as_bytes());
        let identity = content_digest::sha256_of(&bytes);
        let member = StaffingMemberBinding::try_new(
            StaffingMemberId::from_bytes(identity),
            principal,
            context.location,
            context.force,
        )
        .map_err(|_| NationalOpeningError::Policy)?;
        // A full base32 identity preserves every digest bit within the graph's name bound.
        let subject = StableElementKey::Node {
            scenario: crate::national_economy::NATIONAL_SCENARIO_ID.into(),
            local_name: format!("member-{}", content_digest::base32(&identity)),
        };
        builder.opening.employment.push(EmploymentTerms {
            member_id: member.member_id(),
            site_id: site,
            unit_id: builder.labor_unit,
            payee: member.household_id(),
            compensation: LaborCompensation::Wage(context.wage),
        });
        members.push(ResidentStaffingMemberSeed {
            subject,
            member,
            employed,
            reserve,
        });
    }
    builder.opening.staffing.push(ResidentStaffingPoolSeed {
        workplace,
        pool,
        previous_unretained_hours: super::quantity(employed, builder.policy.work_hours_per_person)?,
        members,
    });
    Ok(())
}

/// Exact apportionment over any number of trades. Remainder ties follow the captured source-key order.
fn partition(persons: u64, weights: &[u16]) -> Result<Vec<u64>> {
    if weights.iter().map(|w| u64::from(*w)).sum::<u64>() != 10_000 {
        return Err(NationalOpeningError::Policy);
    }
    let mut allocated = vec![0_u64; weights.len()];
    let mut residuals = Vec::with_capacity(10);
    let mut assigned = 0_u64;
    for (i, weight) in weights.iter().enumerate() {
        let numerator = u128::from(persons) * u128::from(*weight);
        allocated[i] =
            u64::try_from(numerator / 10_000).map_err(|_| NationalOpeningError::Arithmetic)?;
        assigned = assigned
            .checked_add(allocated[i])
            .ok_or(NationalOpeningError::Arithmetic)?;
        residuals.push((i, numerator % 10_000));
    }
    residuals.sort_unstable_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
    let missing = persons
        .checked_sub(assigned)
        .ok_or(NationalOpeningError::Arithmetic)?;
    let missing = usize::try_from(missing).map_err(|_| NationalOpeningError::Arithmetic)?;
    if missing > residuals.len() {
        return Err(NationalOpeningError::Arithmetic);
    }
    for (i, _) in residuals.into_iter().take(missing) {
        allocated[i] = allocated[i]
            .checked_add(1)
            .ok_or(NationalOpeningError::Arithmetic)?;
    }
    Ok(allocated)
}

#[cfg(test)]
mod tests {
    use super::partition;

    #[test]
    fn partition_keeps_its_rule() {
        let ten = [1200, 300, 1000, 1200, 800, 1800, 800, 2000, 600, 300];
        assert_eq!(
            partition(1000, &ten),
            Ok(vec![120, 30, 100, 120, 80, 180, 80, 200, 60, 30])
        );
        // One person over: the largest remainder (2,000 of the eighth weight) takes it.
        assert_eq!(
            partition(1001, &ten),
            Ok(vec![120, 30, 100, 120, 80, 180, 80, 201, 60, 30])
        );
        let twelve = [
            1200, 300, 1000, 1000, 200, 800, 1800, 800, 1800, 600, 300, 200,
        ];
        for persons in [0_u64, 1, 7, 1000, 123_457] {
            let parts = partition(persons, &twelve).expect("twelve weights sum to 10,000");
            assert_eq!(parts.len(), 12);
            assert_eq!(parts.iter().sum::<u64>(), persons);
        }
        assert!(partition(10, &[5_000, 4_000]).is_err());
    }
}
