//! Designed home-county workplace placement of source-controlled resident persons.
//! Each member is a counted household-residence/workplace group, never an individual agent.
//! This is opening authoring: durable employed/reserve stocks belong only to the graph.
mod weights;
use crate::{
    economic_catalog::{ResidentStaffingMemberSeed, ResidentStaffingPoolSeed},
    national_cohorts::NationalCohortReference,
    national_counties::NationalCountyReference,
    national_economy::{
        household_enterprise_target, household_principal, resident_employer_target,
        source_workplace_target, NationalGamePolicy, ResidentWorkplaceTarget,
    },
    national_resident_workforce::{NationalResidentWorkforceReference, WorkerClass},
};
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::{
    content_digest::sha256_of, economic_identity::QcewOwnership,
    economic_location::EconomicLocation, geography::CountyGeoid,
};
use babylon_material_circuit::{
    StaffingMemberBinding, StaffingMemberId, StaffingPolicy, StaffingPoolBinding,
    StaffingWorkSource, UnitId, MAX_MATERIAL_CIRCUIT_ROWS, MAX_STAFFING_MEMBERS,
};
use std::collections::BTreeMap;
pub use weights::{ImputedWeight, PeerScope, WorkforceAllocationWeight};

type Result<T> = std::result::Result<T, AllocationError>;
/// Explicit refusal of incomplete source controls or inconsistent captured placement.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum AllocationError {
    SourceScope,
    MissingObservation,
    PopulationControl,
    Identity,
    Bounds,
    Arithmetic,
    Policy,
}
impl std::fmt::Display for AllocationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "resident workplace allocation refused: {self:?}")
    }
}
impl std::error::Error for AllocationError {}
/// Runtime attendance policy, separate from source worker class and actual ownership.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ResidentAttendanceMode {
    Employee,
    WorkingOwner,
    UnpaidFamily,
}
impl ResidentAttendanceMode {
    fn tag(self) -> u8 {
        match self {
            Self::Employee => 1,
            Self::WorkingOwner => 2,
            Self::UnpaidFamily => 3,
        }
    }
}
/// One counted resident group uses the common seed DTO, not one object per person.
/// There is no parallel population codec or individual decision agent.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AssignedResidentMember {
    pub seed: ResidentStaffingMemberSeed,
    pub mode: ResidentAttendanceMode,
}
/// Every source workplace remains present, including zero-force sites.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AssignedResidentWorkplace {
    pub target: ResidentWorkplaceTarget,
    pub weight: Option<WorkforceAllocationWeight>,
    pub members: Vec<AssignedResidentMember>,
}
/// Exact source controls and the accounted people outside modeled civilian work.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResidentCountyAllocation {
    pub county: CountyGeoid,
    pub population: u64,
    pub households: u64,
    pub employed: u64,
    pub reserve: u64,
    pub inactive: u64,
    pub armed_forces: u64,
    pub younger_than_sixteen: u64,
    /// In `WorkerClass::ALL` order, retaining distinctions combined only for placement.
    pub source_classes: [u64; 8],
}
/// Source identities and deterministic opening assignments, not an additional runtime authority.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResidentWorkplaceAllocation {
    pub county_source_sha256: [u8; 32],
    pub cohort_source_sha256: [u8; 32],
    pub function_mapping_sha256: [u8; 32],
    pub classes_source_sha256: [u8; 32],
    pub workplaces: Vec<AssignedResidentWorkplace>,
    pub counties: Vec<ResidentCountyAllocation>,
}
impl ResidentWorkplaceAllocation {
    /// Bind the actual compiler's labor unit, schedule, request memory and work sources.
    /// # Errors
    /// Refuses inconsistent or over-bound native staffing declarations.
    pub fn staffing_seeds(
        &self,
        mut terms: impl FnMut(
            &ResidentWorkplaceTarget,
        ) -> Result<(UnitId, StaffingPolicy, u64, Vec<StaffingWorkSource>)>,
    ) -> Result<Vec<ResidentStaffingPoolSeed>> {
        self.workplaces
            .iter()
            .map(|row| {
                let (unit, policy, previous, work_sources) = terms(&row.target)?;
                let force = row.members.iter().try_fold(0_u64, |n, m| {
                    n.checked_add(m.seed.member.labor_force())
                        .ok_or(AllocationError::Arithmetic)
                })?;
                let pool = StaffingPoolBinding::try_new(
                    row.target.pool_id,
                    row.target.site_id,
                    unit,
                    force,
                    policy,
                    work_sources,
                )
                .map_err(|_| AllocationError::Policy)?;
                Ok(ResidentStaffingPoolSeed {
                    workplace: row.target.workplace.clone(),
                    pool,
                    previous_unretained_hours: previous,
                    members: row.members.iter().map(|m| m.seed.clone()).collect(),
                })
            })
            .collect()
    }
}

/// Allocate ACS-controlled people; QCEW contributes placement weights only.
/// # Errors
/// Refuses missing controls, inconsistent source scope, arithmetic or sparse row bounds.
pub fn allocate_home_county(
    counties: &NationalCountyReference,
    cohorts: &NationalCohortReference,
    classes: &NationalResidentWorkforceReference,
    policy: &NationalGamePolicy,
) -> Result<ResidentWorkplaceAllocation> {
    if policy.missing_peer_weight_per_establishment == 0 {
        return Err(AllocationError::Policy);
    }
    let peers = weights::Peers::new(cohorts)?;
    let mut by_county = BTreeMap::<CountyGeoid, Vec<PendingWorkplace>>::new();
    for cohort in cohorts.admitted_cohorts() {
        let key = cohort.key();
        let location = EconomicLocation::domestic_county(key.county)
            .map_err(|_| AllocationError::SourceScope)?;
        counties
            .county(key.county)
            .map_err(|_| AllocationError::SourceScope)?;
        let weight = peers.weight(cohort, policy.missing_peer_weight_per_establishment)?;
        let target = source_workplace_target(
            location,
            key.function.ok_or(AllocationError::SourceScope)?,
            key.ownership,
            weight.total,
        )
        .map_err(|_| AllocationError::SourceScope)?;
        by_county
            .entry(key.county)
            .or_default()
            .push(PendingWorkplace {
                target,
                weight: Some(weight),
                employed: 0,
                reserve: 0,
            });
    }
    let mut result = ResidentWorkplaceAllocation {
        county_source_sha256: counties.artifact_sha256(),
        cohort_source_sha256: cohorts.artifact_sha256(),
        function_mapping_sha256: cohorts.function_mapping_sha256(),
        classes_source_sha256: classes.artifact_sha256(),
        workplaces: vec![],
        counties: vec![],
    };
    for county in counties.counties() {
        let controls = county_controls(county, classes)?;
        let location = EconomicLocation::domestic_county(county.geoid())
            .map_err(|_| AllocationError::SourceScope)?;
        let sites = by_county.remove(&county.geoid()).unwrap_or_default();
        result
            .workplaces
            .extend(assign_county(sites, location, &controls)?);
        result.counties.push(controls);
    }
    if !by_county.is_empty() {
        return Err(AllocationError::SourceScope);
    }
    result
        .workplaces
        .sort_unstable_by_key(|row| row.target.site_id);
    let member_count = result.workplaces.iter().try_fold(0_usize, |n, r| {
        n.checked_add(r.members.len())
            .ok_or(AllocationError::Arithmetic)
    })?;
    if result.workplaces.len() > MAX_MATERIAL_CIRCUIT_ROWS || member_count > MAX_STAFFING_MEMBERS {
        return Err(AllocationError::Bounds);
    }
    if result
        .workplaces
        .windows(2)
        .any(|p| p[0].target.site_id == p[1].target.site_id)
    {
        return Err(AllocationError::Identity);
    }
    validate_totals(&result)?;
    Ok(result)
}

fn assign_county(
    mut sites: Vec<PendingWorkplace>,
    location: EconomicLocation,
    controls: &ResidentCountyAllocation,
) -> Result<Vec<AssignedResidentWorkplace>> {
    let mut assigned_workplaces = vec![];
    sites.sort_unstable_by_key(|row| row.target.site_id);
    allocate_employees(&mut sites, location, controls)?;
    for row in sites {
        let mut assigned = AssignedResidentWorkplace {
            target: row.target,
            weight: row.weight,
            members: vec![],
        };
        if row
            .employed
            .checked_add(row.reserve)
            .ok_or(AllocationError::Arithmetic)?
            > 0
        {
            assigned.members.push(member(
                &assigned.target,
                ResidentAttendanceMode::Employee,
                row.employed,
                row.reserve,
            )?);
        }
        assigned_workplaces.push(assigned);
    }
    let owners = controls.source_classes[1]
        .checked_add(controls.source_classes[6])
        .ok_or(AllocationError::Arithmetic)?;
    let family = controls.source_classes[7];
    if owners > 0 || family > 0 {
        let target =
            household_enterprise_target(location).map_err(|_| AllocationError::SourceScope)?;
        let mut members = vec![];
        if owners > 0 {
            members.push(member(
                &target,
                ResidentAttendanceMode::WorkingOwner,
                owners,
                0,
            )?);
        }
        if family > 0 {
            members.push(member(
                &target,
                ResidentAttendanceMode::UnpaidFamily,
                family,
                0,
            )?);
        }
        members.sort_unstable_by_key(|row| row.seed.member.member_id());
        assigned_workplaces.push(AssignedResidentWorkplace {
            target,
            weight: None,
            members,
        });
    }
    Ok(assigned_workplaces)
}

struct PendingWorkplace {
    target: ResidentWorkplaceTarget,
    weight: Option<WorkforceAllocationWeight>,
    employed: u64,
    reserve: u64,
}
fn allocate_employees(
    sites: &mut Vec<PendingWorkplace>,
    location: EconomicLocation,
    control: &ResidentCountyAllocation,
) -> Result<()> {
    let c = &control.source_classes;
    let private = c[0].checked_add(c[2]).ok_or(AllocationError::Arithmetic)?;
    for (ownership, persons) in [
        (QcewOwnership::Private, private),
        (QcewOwnership::LocalGovernment, c[3]),
        (QcewOwnership::StateGovernment, c[4]),
        (QcewOwnership::FederalGovernment, c[5]),
    ] {
        let mut indices: Vec<_> = sites
            .iter()
            .enumerate()
            .filter_map(|(i, r)| {
                (r.target.ownership == ownership && r.target.allocation_weight > 0).then_some(i)
            })
            .collect();
        if persons > 0 && indices.is_empty() {
            indices.push(add_fallback(sites, location, ownership)?);
        }
        let weights: Vec<_> = indices
            .iter()
            .map(|i| sites[*i].target.allocation_weight)
            .collect();
        for (i, amount) in indices.into_iter().zip(apportion(persons, &weights)?) {
            sites[i].employed = amount;
        }
    }
    if control.reserve > 0 {
        if !sites.iter().any(|r| r.target.allocation_weight > 0) {
            add_fallback(sites, location, QcewOwnership::Private)?;
        }
        sites.sort_unstable_by_key(|r| r.target.site_id);
        let weights: Vec<_> = sites.iter().map(|r| r.target.allocation_weight).collect();
        for (row, amount) in sites.iter_mut().zip(apportion(control.reserve, &weights)?) {
            row.reserve = amount;
        }
    }
    Ok(())
}
fn add_fallback(
    sites: &mut Vec<PendingWorkplace>,
    location: EconomicLocation,
    ownership: QcewOwnership,
) -> Result<usize> {
    let target =
        resident_employer_target(location, ownership).map_err(|_| AllocationError::SourceScope)?;
    if sites.iter().any(|r| r.target.site_id == target.site_id) {
        return Err(AllocationError::Identity);
    }
    let index = sites.len();
    sites.push(PendingWorkplace {
        target,
        weight: None,
        employed: 0,
        reserve: 0,
    });
    Ok(index)
}
fn member(
    target: &ResidentWorkplaceTarget,
    mode: ResidentAttendanceMode,
    employed: u64,
    reserve: u64,
) -> Result<AssignedResidentMember> {
    let mut bytes = b"NationalResidentMemberV1\0".to_vec();
    bytes.extend_from_slice(&target.site_id.as_bytes());
    bytes.extend_from_slice(&target.location.canonical_bytes());
    bytes.push(mode.tag());
    let identity = sha256_of(&bytes);
    let member = StaffingMemberBinding::try_new(
        StaffingMemberId::from_bytes(identity),
        household_principal(target.location),
        target.location,
        employed
            .checked_add(reserve)
            .ok_or(AllocationError::Arithmetic)?,
    )
    .map_err(|_| AllocationError::PopulationControl)?;
    let subject = StableElementKey::Node {
        scenario: crate::national_economy::NATIONAL_SCENARIO_ID.into(),
        local_name: format!("member-{}", base32(&identity)),
    };
    subject
        .canonical_bytes()
        .map_err(|_| AllocationError::Identity)?;
    Ok(AssignedResidentMember {
        seed: ResidentStaffingMemberSeed {
            subject,
            member,
            employed,
            reserve,
        },
        mode,
    })
}
fn base32(bytes: &[u8; 32]) -> String {
    const ALPHABET: &[u8; 32] = b"abcdefghijklmnopqrstuvwxyz234567";
    let mut result = String::with_capacity(52);
    let mut bits = 0_u16;
    let mut count = 0;
    for byte in bytes {
        bits = (bits << 8) | u16::from(*byte);
        count += 8;
        while count >= 5 {
            count -= 5;
            result.push(char::from(ALPHABET[usize::from((bits >> count) & 31)]));
        }
    }
    if count > 0 {
        result.push(char::from(
            ALPHABET[usize::from((bits << (5 - count)) & 31)],
        ));
    }
    result
}
fn apportion(total: u64, weights: &[u64]) -> Result<Vec<u64>> {
    let sum = weights.iter().try_fold(0_u64, |n, w| {
        n.checked_add(*w).ok_or(AllocationError::Arithmetic)
    })?;
    if total == 0 {
        return Ok(vec![0; weights.len()]);
    }
    if sum == 0 {
        return Err(AllocationError::PopulationControl);
    }
    let mut rows = Vec::with_capacity(weights.len());
    let mut remainders = Vec::with_capacity(weights.len());
    let mut assigned = 0_u64;
    for (index, weight) in weights.iter().enumerate() {
        let numerator = u128::from(total) * u128::from(*weight);
        let value =
            u64::try_from(numerator / u128::from(sum)).map_err(|_| AllocationError::Arithmetic)?;
        rows.push(value);
        assigned = assigned
            .checked_add(value)
            .ok_or(AllocationError::Arithmetic)?;
        remainders.push((numerator % u128::from(sum), index));
    }
    remainders.sort_unstable_by(|a, b| b.0.cmp(&a.0).then_with(|| a.1.cmp(&b.1)));
    for (_, index) in remainders
        .into_iter()
        .take(usize::try_from(total - assigned).map_err(|_| AllocationError::Arithmetic)?)
    {
        rows[index] += 1;
    }
    Ok(rows)
}
fn county_controls(
    county: &crate::national_counties::CountyReference,
    source: &NationalResidentWorkforceReference,
) -> Result<ResidentCountyAllocation> {
    let classes = source
        .county(county.geoid())
        .map_err(|_| AllocationError::SourceScope)?;
    let mut source_classes = [0; 8];
    for (slot, class) in source_classes.iter_mut().zip(WorkerClass::ALL) {
        *slot = classes
            .persons(class)
            .ok_or(AllocationError::MissingObservation)?;
    }
    let resident = county.residents();
    let value = |cell: &crate::national_counties::AcsEstimate| {
        cell.estimate
            .value()
            .ok_or(AllocationError::MissingObservation)
    };
    let employed = value(&resident.civilian_employed_persons)?;
    let reserve = value(&resident.civilian_unemployed_persons)?;
    let population = value(&resident.population_persons)?;
    let adults = value(&resident.age_16_plus_persons)?;
    let inactive = value(&resident.not_in_labor_force_persons)?;
    let armed = value(&resident.armed_forces_persons)?;
    if source_classes
        .iter()
        .try_fold(0_u64, |n, v| n.checked_add(*v))
        != Some(employed)
        || employed
            .checked_add(reserve)
            .and_then(|n| n.checked_add(inactive))
            .and_then(|n| n.checked_add(armed))
            != Some(adults)
    {
        return Err(AllocationError::PopulationControl);
    }
    Ok(ResidentCountyAllocation {
        county: county.geoid(),
        population,
        households: value(&resident.households)?,
        employed,
        reserve,
        inactive,
        armed_forces: armed,
        younger_than_sixteen: population
            .checked_sub(adults)
            .ok_or(AllocationError::PopulationControl)?,
        source_classes,
    })
}
fn validate_totals(result: &ResidentWorkplaceAllocation) -> Result<()> {
    let mut people = BTreeMap::<CountyGeoid, (u64, u64)>::new();
    for row in &result.workplaces {
        let EconomicLocation::County(county) = row.target.location else {
            return Err(AllocationError::SourceScope);
        };
        let entry = people.entry(county.geoid()).or_default();
        for member in &row.members {
            entry.0 = entry
                .0
                .checked_add(member.seed.employed)
                .ok_or(AllocationError::Arithmetic)?;
            entry.1 = entry
                .1
                .checked_add(member.seed.reserve)
                .ok_or(AllocationError::Arithmetic)?;
        }
    }
    for row in &result.counties {
        if people.remove(&row.county).unwrap_or_default() != (row.employed, row.reserve) {
            return Err(AllocationError::PopulationControl);
        }
    }
    if !people.is_empty() {
        return Err(AllocationError::SourceScope);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn allocation_weights_partition_people_without_equating_them_to_jobs() {
        assert_eq!(apportion(7, &[1, 1, 1]).unwrap(), [3, 2, 2]);
        assert_eq!(apportion(2, &[0, 10, 30]).unwrap(), [0, 1, 1]);
        assert_eq!(apportion(0, &[]).unwrap(), Vec::<u64>::new());
        assert!(apportion(1, &[0, 0]).is_err());
        assert!(apportion(1, &[u64::MAX, 1]).is_err());
    }
    #[test]
    fn member_local_names_preserve_the_last_identity_bit_within_the_lexical_bound() {
        let zero = [0; 32];
        let mut last = zero;
        last[31] = 1;
        assert_eq!(base32(&zero), "a".repeat(52));
        assert_eq!(base32(&last), format!("{}aq", "a".repeat(50)));
        assert_eq!(format!("member-{}", base32(&last)).len(), 59);
    }
}
