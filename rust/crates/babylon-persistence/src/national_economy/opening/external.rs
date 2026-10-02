//! Bounded world cohorts. Trade dollars create neither people nor capacity.
use super::{actors, quantity, ActorContext, Builder, NationalOpeningError, Result, FUNCTIONS};
use crate::{
    economic_catalog::{EconomicSiteSource, ResidentStaffingMemberSeed, ResidentStaffingPoolSeed},
    national_economy::{household_principal, GameProfile},
    national_household_allocation::HouseholdBudgetKey,
    world_reference::WorldReference,
};
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::{
    content_digest::sha256_of,
    economic_location::{EconomicLocation, ForeignCounterpart, UsDependency},
};
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
    let employed = partition(counts.employed, &profile.function_weights_bps)?;
    let reserve = partition(counts.reserve, &profile.function_weights_bps)?;
    for (index, function) in FUNCTIONS.into_iter().enumerate() {
        let mut identity = b"NationalExternalSiteV1\0".to_vec();
        identity.extend_from_slice(&location.canonical_bytes());
        identity.extend_from_slice(function.source_key().as_bytes());
        let site_id = SiteId::from_bytes(sha256_of(&identity));
        let workforce = employed[index]
            .checked_add(reserve[index])
            .ok_or(NationalOpeningError::Arithmetic)?;
        let context = ActorContext {
            site_id,
            function,
            source_ownership: None,
            location,
            employed: employed[index],
            employee_persons: employed[index],
            force: workforce,
            wage: profile.wage_per_hour,
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
                key: "bounded-counterpart-function".into(),
            },
            format!("{label}: {}", function.source_key()),
        )?;
        staffing(builder, site_id, subject, employed[index], reserve[index])?;
    }
    Ok(())
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
        StaffingPoolId::from_bytes(sha256_of(&pool_bytes)),
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
        let principal = household_principal(context.location, HouseholdBudgetKey::PooledExternal);
        let mut bytes = b"NationalExternalWorkforceV2\0".to_vec();
        bytes.extend_from_slice(&site.as_bytes());
        bytes.extend_from_slice(&principal.as_bytes());
        let identity = sha256_of(&bytes);
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
            local_name: format!("member-{}", base32(&identity)),
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
        previous_unretained_hours: quantity(employed, builder.policy.work_hours_per_person)?,
        members,
    });
    Ok(())
}

/// Exact ten-function apportionment. Remainder ties follow the captured source-key order.
fn partition(persons: u64, weights: &[u16; 10]) -> Result<[u64; 10]> {
    if weights.iter().map(|w| u64::from(*w)).sum::<u64>() != 10_000 {
        return Err(NationalOpeningError::Policy);
    }
    let mut allocated = [0_u64; 10];
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

fn base32(bytes: &[u8; 32]) -> String {
    const ALPHABET: &[u8; 32] = b"abcdefghijklmnopqrstuvwxyz234567";
    let mut result = String::with_capacity(52);
    let mut accumulator = 0_u16;
    let mut bits = 0_u8;
    for byte in bytes {
        accumulator = (accumulator << 8) | u16::from(*byte);
        bits += 8;
        while bits >= 5 {
            bits -= 5;
            result.push(char::from(
                ALPHABET[usize::from((accumulator >> bits) & 31)],
            ));
        }
        accumulator &= (1_u16 << bits) - 1;
    }
    if bits > 0 {
        result.push(char::from(
            ALPHABET[usize::from((accumulator << (5 - bits)) & 31)],
        ));
    }
    result
}
