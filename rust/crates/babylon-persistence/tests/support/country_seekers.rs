//! The seekers' member rows of the country bench: so that people looking for work can move to any
//! workplace of their place, each household holds one member at each pool of its place.
use super::country_bench::{BenchError, BenchStage};
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::{
    EmploymentTerms, FinalDemandPrincipalId, LaborCompensation, MemberLaborCapacityRow,
    StaffingMemberBinding, StaffingMemberId, StaffingMemberState, StaffingPlace, StaffingPoolId,
};
use babylon_persistence::economic_catalog::{
    EconomicCatalogError, EconomicOpening, ResidentStaffingPoolSeed,
};
use std::collections::{BTreeMap, BTreeSet};

/// The wage of a pool that has no wage term: the policy's default, $24 an hour, in millionths.
const DEFAULT_WAGE_MICROS: i128 = 24_000_000;

/// The wage a pool offers its seekers when it has no member paid a wage.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Wages {
    /// The policy's default, $24 an hour: the shipped scenario.
    Default,
    /// The average wage of the place's members paid a wage: the sum of wage times employed persons
    /// over the sum of those persons, rounded down.
    PlaceAverage,
}

/// The id of the member a household holds at a pool it has none at: the first 32 bytes of
/// `sha256_of(b"CountryBenchSeekerMemberV1\0" ++ pool_id bytes ++ household_id bytes)`.
pub fn seeker_member_id(
    pool: StaffingPoolId,
    household: FinalDemandPrincipalId,
) -> StaffingMemberId {
    let mut bytes = b"CountryBenchSeekerMemberV1\0".to_vec();
    bytes.extend_from_slice(&pool.as_bytes());
    bytes.extend_from_slice(&household.as_bytes());
    StaffingMemberId::from_bytes(content_digest::sha256_of(&bytes))
}

/// What the opening gains: for each place, each household of the place at each pool of the place where it
/// has no member, one member of nobody, one `EmploymentTerms` and one 0-hour `MemberLaborCapacityRow` of
/// period 1.
pub struct SeekerRows {
    pub members: Vec<(StaffingPoolId, StaffingMemberState)>,
    pub terms: Vec<EmploymentTerms>,
    pub hours: Vec<MemberLaborCapacityRow>,
}

fn refused(what: &'static str) -> BenchError {
    BenchError::Opening(EconomicCatalogError::Opening(what))
}

/// The highest wage among a pool's existing wage terms, else the place's offer.
fn pool_wage(
    seed: &ResidentStaffingPoolSeed,
    terms: &BTreeMap<StaffingMemberId, i128>,
    otherwise: i128,
) -> Currency {
    let highest = seed
        .members
        .iter()
        .filter_map(|member| terms.get(&member.member.member_id()).copied())
        .max()
        .unwrap_or(otherwise);
    Currency::from_micro_units(highest)
}

/// What a place's pools offer when a pool has no wage term of its own.
fn place_offer(
    wages: Wages,
    place: &StaffingPlace,
    seeds: &BTreeMap<StaffingPoolId, &ResidentStaffingPoolSeed>,
    terms: &BTreeMap<StaffingMemberId, i128>,
) -> Result<i128, BenchError> {
    if wages == Wages::Default {
        return Ok(DEFAULT_WAGE_MICROS);
    }
    let (mut paid, mut persons) = (0_i128, 0_i128);
    for pool in &place.pools {
        let seed = seeds
            .get(pool)
            .ok_or_else(|| refused("a place names a pool the opening does not hold"))?;
        for member in &seed.members {
            if let Some(rate) = terms.get(&member.member.member_id()) {
                let employed = i128::from(member.employed);
                paid = rate
                    .checked_mul(employed)
                    .and_then(|pay| paid.checked_add(pay))
                    .ok_or_else(|| refused("a place's wage sum overflowed"))?;
                persons += employed;
            }
        }
    }
    if persons == 0 {
        return Err(refused(
            "a place has no employed person paid a wage to set its seekers' offer",
        ));
    }
    Ok(paid / persons)
}

/// The wage of each member that has a wage term.
fn wage_terms(opening: &EconomicOpening) -> BTreeMap<StaffingMemberId, i128> {
    opening
        .employment
        .iter()
        .filter_map(|term| match term.compensation {
            LaborCompensation::Wage(rate) => Some((term.member_id, rate.micro_units())),
            LaborCompensation::WorkingOwner | LaborCompensation::UnpaidFamily => None,
        })
        .collect()
}

/// A place's households, each with the residence of its first member in pool and member order.
fn place_households(
    place: &StaffingPlace,
    seeds: &BTreeMap<StaffingPoolId, &ResidentStaffingPoolSeed>,
) -> Result<BTreeMap<FinalDemandPrincipalId, EconomicLocation>, BenchError> {
    let mut households = BTreeMap::new();
    for pool in &place.pools {
        let seed = seeds
            .get(pool)
            .ok_or_else(|| refused("a place names a pool the opening does not hold"))?;
        for member in &seed.members {
            households
                .entry(member.member.household_id())
                .or_insert_with(|| member.member.residence());
        }
    }
    Ok(households)
}

/// The rows one pool gains: a member for each household of its place that has none, by household id.
fn pool_rows(
    seed: &ResidentStaffingPoolSeed,
    households: &BTreeMap<FinalDemandPrincipalId, EconomicLocation>,
    wage: Currency,
    rows: &mut SeekerRows,
) -> Result<(), BenchError> {
    let held: BTreeSet<_> = seed
        .members
        .iter()
        .map(|member| member.member.household_id())
        .collect();
    let pool = seed.pool.pool_id();
    for (household, residence) in households {
        if held.contains(household) {
            continue;
        }
        let member_id = seeker_member_id(pool, *household);
        let binding =
            StaffingMemberBinding::from_living_force(member_id, *household, *residence, 0);
        let state =
            StaffingMemberState::try_new(binding, 0, 0).map_err(|error| BenchError::Staffing {
                period: 0,
                stage: BenchStage::Open,
                error,
            })?;
        rows.members.push((pool, state));
        rows.terms.push(EmploymentTerms {
            member_id,
            site_id: seed.pool.site_id(),
            unit_id: seed.pool.unit_id(),
            payee: *household,
            compensation: LaborCompensation::Wage(wage),
        });
        rows.hours.push(MemberLaborCapacityRow {
            member_id,
            period: 1,
            available_hours: 0,
        });
    }
    Ok(())
}

/// The seekers' rows of an opening, place by place.
///
/// # Errors
/// `BenchError::Opening` when a place names a pool the opening does not hold, or (with
/// `Wages::PlaceAverage`) holds no employed person paid a wage; `BenchError::Staffing` when the engine
/// refuses a member.
pub fn seeker_rows(
    opening: &EconomicOpening,
    places: &[StaffingPlace],
    offered: Wages,
) -> Result<SeekerRows, BenchError> {
    let seeds: BTreeMap<StaffingPoolId, &ResidentStaffingPoolSeed> = opening
        .staffing
        .iter()
        .map(|seed| (seed.pool.pool_id(), seed))
        .collect();
    let wages = wage_terms(opening);
    let mut rows = SeekerRows {
        members: Vec::new(),
        terms: Vec::new(),
        hours: Vec::new(),
    };
    for place in places {
        let households = place_households(place, &seeds)?;
        let otherwise = place_offer(offered, place, &seeds, &wages)?;
        for pool in &place.pools {
            let seed = seeds
                .get(pool)
                .ok_or_else(|| refused("a place names a pool the opening does not hold"))?;
            pool_rows(
                seed,
                &households,
                pool_wage(seed, &wages, otherwise),
                &mut rows,
            )?;
        }
    }
    Ok(rows)
}
