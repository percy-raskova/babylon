//! Designed source pushforward before economic actors and relations are expanded.
use crate::economic_catalog::{CommodityAmount, OpeningCommodityStock};
use crate::national_counties::{CountyReference, NationalCountyReference};
use crate::national_economy::GameCommodity;
use crate::national_economy::GameRecipe;
use crate::national_economy::{
    self, NationalAidCapture, NationalGamePolicy, ResidentWorkplaceSource,
};
use crate::national_household_allocation::{
    CountyHouseholdAllocation, HouseholdBudgetAllocation, HouseholdBudgetKey,
    NationalHouseholdAllocation,
};
use crate::national_household_time_allocation::{
    HouseholdTimeAllocation, NationalHouseholdTimeAllocation,
};
use crate::national_resident_allocation::{
    self, AssignedResidentWorkplace, ResidentAttendanceMode, ResidentCountyAllocation,
    ResidentWorkplaceAllocation, WorkforceAllocationWeight,
};
use crate::national_transport::{
    CargoClass, NationalTransportReference, TransportMode, TransportNodeKind,
};
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::{
    AccountId, CommodityKind, FinalDemandPrincipalId, HouseholdNeedBasis, PublicAccountId, SiteId,
    StaffingMemberId,
};
use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Formatter;

/// The single current generation algorithm; unsupported captures are refused.
#[derive(Clone, Copy, Debug, PartialEq, Eq, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum NationalGrainGeneration {
    StateFafReservePositions,
}
/// Captured Designed generation authority, independent of mutable game state.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalGrainPolicy {
    pub generation: NationalGrainGeneration,
    pub protected_counties: BTreeSet<CountyGeoid>,
}
/// Immutable authoring identity for a real-hub catchment.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct CatchmentId(pub [u8; 32]);
/// Complete subgroup key, including its canonical county membership.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CatchmentKey {
    pub state: [u8; 2],
    pub faf_zone: [u8; 3],
    pub hub: CountyGeoid,
    pub membership_digest: [u8; 32],
}
/// Relative reserve exposure within the final, capacity-refined membership.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum ReservePosition {
    NoLaborForce,
    BelowCellReserveRate,
    AtCellReserveRate,
    AboveCellReserveRate,
}
/// Distinguishes source-QCEW, fallback and household-enterprise contributions.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum ResidentWorkplaceSourceKind {
    Qcew,
    HouseholdEnterprise,
    ResidentEmployerFallback,
}
/// Occupied productive key; no source ownership distinctions are merged.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct RepresentativeWorkplaceKey {
    pub catchment: CatchmentId,
    pub position: ReservePosition,
    pub function: EconomicFunction,
    pub ownership: QcewOwnership,
    pub source_kind: ResidentWorkplaceSourceKind,
}
/// Occupied household key; budget and reserve exposure retain independent owners.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct RepresentativeHouseholdKey {
    pub catchment: CatchmentId,
    pub position: ReservePosition,
    pub budget: HouseholdBudgetKey,
}
/// Budget ownership is independent of physical hub location.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub struct FinancialDomainId {
    pub location: EconomicLocation,
    pub representative: Option<(CatchmentId, ReservePosition)>,
}
impl FinancialDomainId {
    /// Preserve the exact existing detailed and external budget identity.
    #[must_use]
    pub const fn detailed(location: EconomicLocation) -> Self {
        Self {
            location,
            representative: None,
        }
    }
    /// The provisioning account belongs to this domain alone.
    #[must_use]
    pub fn public_account(self) -> PublicAccountId {
        let mut bytes = b"NationalPublicProvisioningV1\0".to_vec();
        bytes.extend_from_slice(&self.location.canonical_bytes());
        if let Some((catchment, position)) = self.representative {
            bytes.extend_from_slice(b"RepresentativeV1\0");
            bytes.extend_from_slice(&catchment.0);
            bytes.push(position as u8);
        }
        PublicAccountId::from_bytes(content_digest::sha256_of(&bytes))
    }
}
/// Why the finite screening rule retained a particular cell.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CatchmentReason {
    FitsCapturedHubAccess,
    CapacitySubdivision,
    Protected,
    NotSingleRoadAccess,
    SpecialAccess,
    PreExistingEssentialAccessDeficit,
}
/// The finite lower-bound calculation is a screening witness, not a viability claim.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CapturedCatchment {
    pub id: CatchmentId,
    pub key: CatchmentKey,
    pub members: Vec<CountyGeoid>,
    pub demand: u128,
    pub food_labor_hours: u128,
    pub optimistic_output: u128,
    pub essential_import_grams: u128,
    pub capacity_grams: Option<u128>,
    pub reason: CatchmentReason,
}
/// Every source county has exactly one destination.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ContributionDestination {
    Detailed(CountyGeoid),
    Representative {
        catchment: CatchmentId,
        position: ReservePosition,
    },
}
/// Original eight-class controls remain evidence, independent of the live hub.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountyContribution {
    pub controls: ResidentCountyAllocation,
    pub destination: ContributionDestination,
}
/// Per-source rounded productive quantities; all other stocks/cash are linear in these counts.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct OpeningProductiveEndowment {
    pub batches: u64,
    pub opening_stock: Vec<OpeningCommodityStock>,
    pub opening_cash_micros: i128,
    pub equipment_units: u64,
    pub workforce_equipment_units: u64,
    pub equipment_service_batches: u64,
    pub equipment_carrying_micros: i128,
}
/// Provenance does not create a second live site or balance.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SourceRepresentativeIncidence {
    pub source_site: SiteId,
    pub destination_site: SiteId,
    pub source_county: CountyGeoid,
    pub source: ResidentWorkplaceSource,
    pub weight: Option<WorkforceAllocationWeight>,
    pub endowment: OpeningProductiveEndowment,
}
/// Counted staffing pushforward retains exact source payees and quantities.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MemberIncidence {
    pub source: StaffingMemberId,
    pub destination: StaffingMemberId,
    pub employed: u64,
    pub reserve: u64,
}
/// Source household contribution, before exact protected child subtraction.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HouseholdIncidence {
    pub county: CountyGeoid,
    pub source: FinalDemandPrincipalId,
    pub destination: FinalDemandPrincipalId,
    pub margins: HouseholdBudgetAllocation,
    pub time: HouseholdTimeAllocation,
}
/// Immutable opening evidence, retained once by admitted source content.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalGenerationWitness {
    pub source_digest: [u8; 32],
    pub policy_digest: [u8; 32],
    pub catchments: Vec<CapturedCatchment>,
    pub counties: Vec<CountyContribution>,
    pub source_incidence: Vec<SourceRepresentativeIncidence>,
    pub member_incidence: Vec<MemberIncidence>,
    pub household_incidence: Vec<HouseholdIncidence>,
}
/// Captured partition before any live economic expansion.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CapturedNationalMembership {
    pub witness: NationalGenerationWitness,
}
/// Explicit household totals and eligibility, never inferred from hub population.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OpeningHouseholdAllocation {
    pub principal: FinalDemandPrincipalId,
    pub subject: StableElementKey,
    pub domain: FinancialDomainId,
    pub margins: HouseholdBudgetAllocation,
    pub time: HouseholdTimeAllocation,
}
/// The sole current domestic roster consumed by the ordinary compiler.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalOpeningRoster {
    pub workplaces: ResidentWorkplaceAllocation,
    pub households: Vec<OpeningHouseholdAllocation>,
    pub workplace_endowments: BTreeMap<SiteId, OpeningProductiveEndowment>,
    pub financial_domains: BTreeMap<AccountId, FinancialDomainId>,
    pub representation: NationalGenerationWitness,
}
/// Specific source-capture refusals; absence is never converted to zero.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum NationalGrainError {
    IncompleteCountyMembership,
    UnexpectedAccess(CountyGeoid),
    ProtectedContributionOverlap(CountyGeoid),
    SourceIncidenceMismatch,
    HouseholdMargin(CountyGeoid),
    ClassMargin(CountyGeoid),
    TimeMargin(CountyGeoid),
    UnsupportedGeneration,
    UnsupportedEssentialFoodRecipe,
    CatchmentIdentityCollision,
    MissingOwnerBudget(FinancialDomainId),
    MissingFinancialDomain(AccountId),
    Arithmetic,
}
impl std::fmt::Display for NationalGrainError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(f, "national grain refused: {self:?}")
    }
}
impl std::error::Error for NationalGrainError {}
type Result<T> = std::result::Result<T, NationalGrainError>;
fn add(a: u64, b: u64) -> Result<u64> {
    a.checked_add(b).ok_or(NationalGrainError::Arithmetic)
}
fn plus(a: u128, b: u128) -> Result<u128> {
    a.checked_add(b).ok_or(NationalGrainError::Arithmetic)
}
fn product(a: u128, b: u128) -> Result<u128> {
    a.checked_mul(b).ok_or(NationalGrainError::Arithmetic)
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct Screen {
    pub(super) county: CountyGeoid,
    pub(super) population: u64,
    pub(super) demand: u128,
    pub(super) hours: u128,
    pub(super) capacity: u128,
}
pub(super) fn bound(
    rows: &[Screen],
    labor: u128,
    output: u128,
    mass: u128,
) -> Result<(u128, u128, u128, u128)> {
    let (d, h) = rows.iter().try_fold((0, 0), |(d, h), r| {
        Ok((plus(d, r.demand)?, plus(h, r.hours)?))
    })?;
    let u = product(
        h.checked_div(labor)
            .ok_or(NationalGrainError::UnsupportedEssentialFoodRecipe)?,
        output,
    )?;
    Ok((d, h, u, product(d.saturating_sub(u), mass)?))
}
pub(super) fn refine(
    mut rows: Vec<Screen>,
    labor: u128,
    output: u128,
    mass: u128,
) -> Result<Vec<Vec<Screen>>> {
    rows.sort_by_key(|row| (std::cmp::Reverse(row.population), row.county));
    let mut scarce = Vec::new();
    let mut bins: Vec<Vec<Screen>> = Vec::new();
    for row in rows {
        if bound(std::slice::from_ref(&row), labor, output, mass)?.3 > row.capacity {
            scarce.push(vec![row]);
            continue;
        }
        let mut selected = None;
        for (index, bin) in bins.iter().enumerate() {
            let (d, h, _, _) = bound(bin, labor, output, mass)?;
            let u = product(plus(h, row.hours)? / labor, output)?;
            if product(plus(d, row.demand)?.saturating_sub(u), mass)? <= bin[0].capacity {
                selected = Some(index);
                break;
            }
        }
        if let Some(index) = selected {
            bins[index].push(row);
        } else {
            bins.push(vec![row]);
        }
    }
    scarce.extend(bins);
    Ok(scarce)
}
fn food(policy: &NationalGamePolicy) -> Result<(EconomicFunction, u128, u128, u128)> {
    let mut recipes = policy
        .recipes
        .iter()
        .filter(|(_, recipe)| recipe.output == "food");
    let (function, recipe) = recipes
        .next()
        .ok_or(NationalGrainError::UnsupportedEssentialFoodRecipe)?;
    if recipes.next().is_some() || recipe.labor_hours_per_batch == 0 {
        return Err(NationalGrainError::UnsupportedEssentialFoodRecipe);
    }
    let commodity = policy
        .commodities
        .get("food")
        .ok_or(NationalGrainError::UnsupportedEssentialFoodRecipe)?;
    let CommodityKind::Storable { grams_per_unit } = commodity.kind else {
        return Err(NationalGrainError::UnsupportedEssentialFoodRecipe);
    };
    if commodity.cargo != Some(CargoClass::General) {
        return Err(NationalGrainError::UnsupportedEssentialFoodRecipe);
    }
    Ok((
        *function,
        u128::from(recipe.labor_hours_per_batch),
        u128::from(recipe.output_units_per_batch),
        u128::from(grams_per_unit),
    ))
}
fn access(
    transport: &NationalTransportReference,
    county: CountyGeoid,
    zone: &str,
    airport: bool,
) -> Result<(Option<u128>, bool)> {
    let node = format!("county:{county}");
    let faf = format!("faf:{zone}");
    let incident: Vec<_> = transport
        .links()
        .iter()
        .filter(|l| {
            let (a, b) = l.endpoints();
            a == node || b == node
        })
        .collect();
    let out: Vec<_> = incident
        .iter()
        .filter(|l| l.endpoints() == (node.as_str(), faf.as_str()))
        .collect();
    let incoming: Vec<_> = incident
        .iter()
        .filter(|l| l.endpoints() == (faf.as_str(), node.as_str()))
        .collect();
    let special = airport
        || transport.nodes().iter().any(|n| {
            matches!(n.location(),EconomicLocation::County(c) if c.geoid()==county)
                && matches!(
                    n.kind(),
                    TransportNodeKind::Airport
                        | TransportNodeKind::Border
                        | TransportNodeKind::Bulk
                        | TransportNodeKind::Liquid
                        | TransportNodeKind::Marine
                        | TransportNodeKind::Trunk
                )
        });
    if airport && out.is_empty() && incoming.is_empty() {
        return Ok((None, true));
    }
    if out.len() != 1 || incoming.len() != 1 {
        return Err(NationalGrainError::UnexpectedAccess(county));
    }
    let (out, incoming) = (out[0], incoming[0]);
    if [out, incoming].iter().any(|l| {
        l.profile() != "local_road"
            || l.mode() != TransportMode::Truck
            || !l.cargo().contains(&CargoClass::General)
            || l.pools().is_empty()
    }) || out.pools() != incoming.pools()
    {
        return Err(NationalGrainError::UnexpectedAccess(county));
    }
    let mut capacity = u128::MAX;
    for id in out.pools() {
        let pool = transport
            .pools()
            .iter()
            .find(|p| p.id == *id)
            .ok_or(NationalGrainError::UnexpectedAccess(county))?;
        if pool.capacity_grams == 0 {
            return Err(NationalGrainError::UnexpectedAccess(county));
        }
        capacity = capacity.min(u128::from(pool.capacity_grams));
    }
    Ok((Some(capacity), special || incident.len() != 2))
}
/// Capture complete membership, deterministic first-fit refinement and final reserve labels.
/// # Errors
/// Refuses incomplete source coverage, corrupt access, unsupported food recipes and overflow.
#[allow(
    clippy::too_many_lines,
    reason = "The finite partition transaction keeps source coverage, first-fit refinement and final reserve-label validation in one auditable boundary"
)]
pub fn capture_membership(
    counties: &NationalCountyReference,
    transport: &NationalTransportReference,
    source: &ResidentWorkplaceAllocation,
    households: &NationalHouseholdAllocation,
    aid: &NationalAidCapture,
    policy: &NationalGamePolicy,
) -> Result<CapturedNationalMembership> {
    let expected: BTreeSet<_> = counties
        .counties()
        .iter()
        .map(CountyReference::geoid)
        .collect();
    let controls: BTreeMap<_, _> = source.counties.iter().map(|c| (c.county, c)).collect();
    let access_rows: BTreeMap<_, _> = transport
        .county_access()
        .iter()
        .map(|a| (a.county, a))
        .collect();
    let household_counties: BTreeSet<_> = households
        .counties()
        .iter()
        .map(CountyHouseholdAllocation::county)
        .collect();
    if expected != controls.keys().copied().collect()
        || controls.len() != source.counties.len()
        || expected != access_rows.keys().copied().collect()
        || access_rows.len() != transport.county_access().len()
        || expected != household_counties
    {
        return Err(NationalGrainError::IncompleteCountyMembership);
    }
    for control in &source.counties {
        if control
            .source_classes
            .iter()
            .try_fold(0_u64, |total, value| add(total, *value))?
            != control.employed
        {
            return Err(NationalGrainError::ClassMargin(control.county));
        }
        let margins = households
            .county(control.county)
            .map_err(|_| NationalGrainError::HouseholdMargin(control.county))?;
        let counts = margins
            .budgets()
            .iter()
            .try_fold((0, 0, 0, 0), |(p, h, e, r), row| {
                Ok((
                    add(p, row.persons)?,
                    add(h, row.households)?,
                    add(e, row.employed)?,
                    add(r, row.reserve)?,
                ))
            })?;
        if counts
            != (
                control.population,
                control.households,
                control.employed,
                control.reserve,
            )
        {
            return Err(NationalGrainError::HouseholdMargin(control.county));
        }
    }
    let mut protected = policy.grain.protected_counties.clone();
    for child in &aid.children {
        let EconomicLocation::County(county) = child.location else {
            return Err(NationalGrainError::SourceIncidenceMismatch);
        };
        protected.insert(county.geoid());
    }
    if !protected.is_subset(&expected) {
        return Err(NationalGrainError::IncompleteCountyMembership);
    }
    let (food_function, labor, output, mass) = food(policy)?;
    let need = policy
        .household_needs
        .iter()
        .find(|n| n.key == "food")
        .ok_or(NationalGrainError::UnsupportedEssentialFoodRecipe)?;
    let mut hours = BTreeMap::<CountyGeoid, u128>::new();
    for workplace in &source.workplaces {
        let EconomicLocation::County(county) = workplace.target.location else {
            return Err(NationalGrainError::SourceIncidenceMismatch);
        };
        if !expected.contains(&county.geoid()) {
            return Err(NationalGrainError::SourceIncidenceMismatch);
        }
        if workplace.target.function == food_function {
            for member in &workplace.members {
                let value = hours.entry(county.geoid()).or_default();
                *value = plus(
                    *value,
                    product(
                        u128::from(member.seed.member.labor_force()),
                        u128::from(policy.work_hours_per_person),
                    )?,
                )?;
            }
        }
    }
    let mut groups = BTreeMap::<([u8; 2], [u8; 3]), Vec<Screen>>::new();
    let mut cells = Vec::new();
    for county in &expected {
        let control = controls[county];
        let row = access_rows[county];
        let zone: [u8; 3] = row
            .zone
            .as_bytes()
            .try_into()
            .map_err(|_| NationalGrainError::UnexpectedAccess(*county))?;
        if !zone.iter().all(u8::is_ascii_digit) {
            return Err(NationalGrainError::UnexpectedAccess(*county));
        }
        let bytes = county.as_bytes();
        let state = [bytes[0], bytes[1]];
        let (capacity, special) = access(transport, *county, &row.zone, row.airport.is_some())?;
        let household = households
            .county(*county)
            .map_err(|_| NationalGrainError::HouseholdMargin(*county))?;
        let basis = household.budgets().iter().try_fold(0_u128, |n, b| {
            plus(
                n,
                u128::from(match need.basis {
                    HouseholdNeedBasis::Persons => b.persons,
                    HouseholdNeedBasis::Households => b.households,
                }),
            )
        })?;
        let screen = Screen {
            county: *county,
            population: control.population,
            demand: product(basis, u128::from(need.units_per_basis))?,
            hours: hours.get(county).copied().unwrap_or(0),
            capacity: capacity.unwrap_or(0),
        };
        if protected.contains(county) || special {
            let reason = if protected.contains(county) {
                CatchmentReason::Protected
            } else if capacity.is_none() {
                CatchmentReason::NotSingleRoadAccess
            } else {
                CatchmentReason::SpecialAccess
            };
            cells.push(cell(
                &[screen],
                state,
                zone,
                capacity,
                reason,
                policy.source_digest,
                (labor, output, mass),
            )?);
        } else {
            groups.entry((state, zone)).or_default().push(screen);
        }
    }
    for ((state, zone), rows) in groups {
        let bins = refine(rows, labor, output, mass)?;
        let subdivided = bins.len() > 1;
        for bin in bins {
            let capacity = bin[0].capacity;
            let reason = if bound(&bin, labor, output, mass)?.3 > capacity {
                CatchmentReason::PreExistingEssentialAccessDeficit
            } else if subdivided {
                CatchmentReason::CapacitySubdivision
            } else {
                CatchmentReason::FitsCapturedHubAccess
            };
            cells.push(cell(
                &bin,
                state,
                zone,
                Some(capacity),
                reason,
                policy.source_digest,
                (labor, output, mass),
            )?);
        }
    }
    cells.sort_by_key(|c| c.id);
    if cells.windows(2).any(|c| c[0].id == c[1].id) {
        return Err(NationalGrainError::CatchmentIdentityCollision);
    }
    let mut contributions = Vec::new();
    for cell in &cells {
        let (reserve, force) = cell
            .members
            .iter()
            .try_fold((0_u128, 0_u128), |(r, f), c| {
                Ok((
                    plus(r, u128::from(controls[c].reserve))?,
                    plus(
                        f,
                        plus(
                            u128::from(controls[c].employed),
                            u128::from(controls[c].reserve),
                        )?,
                    )?,
                ))
            })?;
        for county in &cell.members {
            let control = controls[county];
            let county_force = add(control.employed, control.reserve)?;
            let position = if county_force == 0 {
                ReservePosition::NoLaborForce
            } else {
                match product(u128::from(control.reserve), force)?
                    .cmp(&product(reserve, u128::from(county_force))?)
                {
                    Ordering::Less => ReservePosition::BelowCellReserveRate,
                    Ordering::Equal => ReservePosition::AtCellReserveRate,
                    Ordering::Greater => ReservePosition::AboveCellReserveRate,
                }
            };
            contributions.push(CountyContribution {
                controls: control.clone(),
                destination: if protected.contains(county) {
                    ContributionDestination::Detailed(*county)
                } else {
                    ContributionDestination::Representative {
                        catchment: cell.id,
                        position,
                    }
                },
            });
        }
    }
    contributions.sort_by_key(|c| c.controls.county);
    let mut source_bytes = b"NationalGrainSourcesV1\0".to_vec();
    for digest in [
        source.county_source_sha256,
        source.cohort_source_sha256,
        source.function_mapping_sha256,
        source.classes_source_sha256,
        source.household_source_sha256,
        transport.artifact_sha256(),
        policy.source_digest,
    ] {
        source_bytes.extend_from_slice(&digest);
    }
    Ok(CapturedNationalMembership {
        witness: NationalGenerationWitness {
            source_digest: content_digest::sha256_of(&source_bytes),
            policy_digest: policy.source_digest,
            catchments: cells,
            counties: contributions,
            source_incidence: Vec::new(),
            member_incidence: Vec::new(),
            household_incidence: Vec::new(),
        },
    })
}
pub(super) fn cell(
    rows: &[Screen],
    state: [u8; 2],
    faf_zone: [u8; 3],
    capacity_grams: Option<u128>,
    reason: CatchmentReason,
    policy_digest: [u8; 32],
    food_terms: (u128, u128, u128),
) -> Result<CapturedCatchment> {
    let (labor, output, mass) = food_terms;
    let hub = rows
        .first()
        .ok_or(NationalGrainError::IncompleteCountyMembership)?
        .county;
    let (demand, food_labor_hours, optimistic_output, essential_import_grams) =
        bound(rows, labor, output, mass)?;
    let mut members: Vec<_> = rows.iter().map(|r| r.county).collect();
    members.sort_unstable();
    if members.windows(2).any(|c| c[0] == c[1]) {
        return Err(NationalGrainError::IncompleteCountyMembership);
    }
    let mut bytes = b"NationalCatchmentMembershipV1\0".to_vec();
    bytes.extend_from_slice(&policy_digest);
    bytes.extend_from_slice(
        &u32::try_from(members.len())
            .map_err(|_| NationalGrainError::Arithmetic)?
            .to_be_bytes(),
    );
    for member in &members {
        bytes.extend_from_slice(&member.as_bytes());
    }
    let membership_digest = content_digest::sha256_of(&bytes);
    let key = CatchmentKey {
        state,
        faf_zone,
        hub,
        membership_digest,
    };
    let mut bytes = b"NationalCatchmentKeyV1\0".to_vec();
    bytes.extend_from_slice(&state);
    bytes.extend_from_slice(&faf_zone);
    bytes.extend_from_slice(&hub.as_bytes());
    bytes.extend_from_slice(&membership_digest);
    Ok(CapturedCatchment {
        id: CatchmentId(content_digest::sha256_of(&bytes)),
        key,
        members,
        demand,
        food_labor_hours,
        optimistic_output,
        essential_import_grams,
        capacity_grams,
        reason,
    })
}
impl OpeningProductiveEndowment {
    pub(super) fn source(
        row: &AssignedResidentWorkplace,
        policy: &NationalGamePolicy,
    ) -> Result<Self> {
        let employee_persons = row
            .members
            .iter()
            .filter(|m| m.mode == ResidentAttendanceMode::Employee)
            .try_fold(0, |n, m| add(n, m.seed.employed))?;
        let wages = i128::from(employee_persons)
            .checked_mul(i128::from(policy.work_hours_per_person))
            .and_then(|hours| hours.checked_mul(policy.default_wage.micro_units()))
            .ok_or(NationalGrainError::Arithmetic)?;
        if row.target.function == EconomicFunction::DistributionTransport {
            return Ok(Self {
                opening_cash_micros: wages
                    .checked_mul(i128::from(policy.working_capital_periods))
                    .ok_or(NationalGrainError::Arithmetic)?,
                ..Self::default()
            });
        }
        let recipe = policy
            .recipes
            .get(&row.target.function)
            .ok_or(NationalGrainError::SourceIncidenceMismatch)?;
        let employed = row
            .members
            .iter()
            .try_fold(0, |n, m| add(n, m.seed.employed))?;
        let hours = employed
            .checked_mul(policy.work_hours_per_person)
            .ok_or(NationalGrainError::Arithmetic)?;
        let batches = hours
            .checked_div(recipe.labor_hours_per_batch)
            .ok_or(NationalGrainError::Arithmetic)?;
        let units = batches.div_ceil(policy.equipment.batches_per_unit_per_period);
        let force = row
            .members
            .iter()
            .try_fold(0, |n, m| add(n, m.seed.member.labor_force()))?;
        let force_hours = force
            .checked_mul(policy.work_hours_per_person)
            .ok_or(NationalGrainError::Arithmetic)?;
        let workforce_equipment_units = (force_hours / recipe.labor_hours_per_batch)
            .div_ceil(policy.equipment.batches_per_unit_per_period);
        let fraction = policy.equipment.opening_remaining_service_bps
            [usize::from(row.target.site_id.as_bytes()[0]) % 4];
        let life = product(
            u128::from(units),
            u128::from(policy.equipment.service_batches_per_unit),
        )?;
        let remaining = u64::try_from(product(life, u128::from(fraction))? / 10_000)
            .map_err(|_| NationalGrainError::Arithmetic)?;
        let price = policy
            .commodities
            .get("equipment")
            .and_then(|g| g.price.as_ref())
            .ok_or(NationalGrainError::SourceIncidenceMismatch)?
            .opening
            .micro_units();
        let original = price
            .checked_mul(i128::from(units))
            .ok_or(NationalGrainError::Arithmetic)?;
        let carrying = (original / 10_000)
            .checked_mul(i128::from(fraction))
            .and_then(|n| n.checked_add((original % 10_000) * i128::from(fraction) / 10_000))
            .ok_or(NationalGrainError::Arithmetic)?;
        let (opening_stock, inputs_cost) = source_stocks(policy, recipe, batches)?;
        let opening_cash_micros = wages
            .checked_add(inputs_cost)
            .and_then(|cost| cost.checked_mul(i128::from(policy.working_capital_periods)))
            .ok_or(NationalGrainError::Arithmetic)?;
        Ok(Self {
            batches,
            opening_stock,
            opening_cash_micros,
            equipment_units: units,
            workforce_equipment_units,
            equipment_service_batches: remaining,
            equipment_carrying_micros: carrying,
        })
    }
    pub(super) fn accumulate(&mut self, source: &Self) -> Result<()> {
        self.batches = add(self.batches, source.batches)?;
        self.opening_cash_micros = self
            .opening_cash_micros
            .checked_add(source.opening_cash_micros)
            .ok_or(NationalGrainError::Arithmetic)?;
        for stock in &source.opening_stock {
            if let Some(existing) = self.opening_stock.iter_mut().find(|s| {
                (s.amount.good_id, s.amount.unit_id) == (stock.amount.good_id, stock.amount.unit_id)
            }) {
                existing.amount.quantity = add(existing.amount.quantity, stock.amount.quantity)?;
                existing.total_cost = existing
                    .total_cost
                    .checked_add(stock.total_cost)
                    .map_err(|_| NationalGrainError::Arithmetic)?;
            } else {
                self.opening_stock.push(stock.clone());
            }
        }
        self.opening_stock
            .sort_by_key(|s| (s.amount.good_id, s.amount.unit_id));
        self.equipment_units = add(self.equipment_units, source.equipment_units)?;
        self.workforce_equipment_units = add(
            self.workforce_equipment_units,
            source.workforce_equipment_units,
        )?;
        self.equipment_service_batches = add(
            self.equipment_service_batches,
            source.equipment_service_batches,
        )?;
        self.equipment_carrying_micros = self
            .equipment_carrying_micros
            .checked_add(source.equipment_carrying_micros)
            .ok_or(NationalGrainError::Arithmetic)?;
        Ok(())
    }
}
fn source_stocks(
    policy: &NationalGamePolicy,
    recipe: &GameRecipe,
    batches: u64,
) -> Result<(Vec<OpeningCommodityStock>, i128)> {
    let mut stocks = Vec::new();
    let mut input_cost = 0_i128;
    for (key, coefficient) in &recipe.inputs {
        let good = policy
            .commodities
            .get(key)
            .ok_or(NationalGrainError::SourceIncidenceMismatch)?;
        let needed = batches
            .checked_mul(*coefficient)
            .ok_or(NationalGrainError::Arithmetic)?;
        if let Some(price) = &good.price {
            input_cost = input_cost
                .checked_add(
                    price
                        .opening
                        .micro_units()
                        .checked_mul(i128::from(needed))
                        .ok_or(NationalGrainError::Arithmetic)?,
                )
                .ok_or(NationalGrainError::Arithmetic)?;
        }
        if matches!(good.kind, CommodityKind::Storable { .. }) {
            let periods = if key == "resource_deposit" {
                policy.resource_reserve_output_periods
            } else {
                policy.opening_input_periods
            };
            stocks.push(source_stock(
                good,
                needed
                    .checked_mul(periods)
                    .ok_or(NationalGrainError::Arithmetic)?,
            )?);
        }
    }
    let output = policy
        .commodities
        .get(&recipe.output)
        .ok_or(NationalGrainError::SourceIncidenceMismatch)?;
    if matches!(output.kind, CommodityKind::Storable { .. }) {
        stocks.push(source_stock(
            output,
            batches
                .checked_mul(recipe.output_units_per_batch)
                .ok_or(NationalGrainError::Arithmetic)?,
        )?);
    }
    stocks.sort_by_key(|s| (s.amount.good_id, s.amount.unit_id));
    Ok((stocks, input_cost))
}
fn source_stock(good: &GameCommodity, quantity: u64) -> Result<OpeningCommodityStock> {
    let cost = good
        .price
        .as_ref()
        .map_or(0, |p| p.opening.micro_units())
        .checked_mul(i128::from(quantity))
        .ok_or(NationalGrainError::Arithmetic)?;
    Ok(OpeningCommodityStock {
        amount: CommodityAmount {
            good_id: good.good_id,
            unit_id: good.unit_id,
            quantity,
        },
        total_cost: Currency::from_micro_units(cost),
    })
}
fn source_kind(source: &ResidentWorkplaceSource) -> Result<ResidentWorkplaceSourceKind> {
    match source {
        ResidentWorkplaceSource::Qcew(_) => Ok(ResidentWorkplaceSourceKind::Qcew),
        ResidentWorkplaceSource::HouseholdEnterprise => {
            Ok(ResidentWorkplaceSourceKind::HouseholdEnterprise)
        }
        ResidentWorkplaceSource::ResidentEmployerFallback => {
            Ok(ResidentWorkplaceSourceKind::ResidentEmployerFallback)
        }
        ResidentWorkplaceSource::Representative(_) => {
            Err(NationalGrainError::SourceIncidenceMismatch)
        }
    }
}
fn domain(
    destination: ContributionDestination,
    membership: &CapturedNationalMembership,
) -> Result<FinancialDomainId> {
    let (county, representative) = match destination {
        ContributionDestination::Detailed(county) => (county, None),
        ContributionDestination::Representative {
            catchment,
            position,
        } => (
            membership
                .witness
                .catchments
                .iter()
                .find(|c| c.id == catchment)
                .ok_or(NationalGrainError::SourceIncidenceMismatch)?
                .key
                .hub,
            Some((catchment, position)),
        ),
    };
    Ok(FinancialDomainId {
        location: EconomicLocation::domestic_county(county)
            .map_err(|_| NationalGrainError::SourceIncidenceMismatch)?,
        representative,
    })
}
/// Fold each source seed immediately; no fine `EconomicOpening` or site vector is built.
/// # Errors
/// Refuses lost county/payee membership, contradictory protected closure and checked overflow.
#[allow(
    clippy::too_many_lines,
    reason = "This sole source-to-live transaction checks both household and staffing pushforwards before returning any roster"
)]
pub(crate) fn coarsen_source_allocation(
    mut source: ResidentWorkplaceAllocation,
    households: &NationalHouseholdAllocation,
    time: &NationalHouseholdTimeAllocation,
    aid: &NationalAidCapture,
    policy: &NationalGamePolicy,
    membership: &CapturedNationalMembership,
) -> Result<NationalOpeningRoster> {
    let mut witness = membership.witness.clone();
    let destinations: BTreeMap<_, _> = witness
        .counties
        .iter()
        .map(|c| (c.controls.county, c.destination))
        .collect();
    let mut principal_map = BTreeMap::new();
    let mut household_rows = BTreeMap::<FinalDemandPrincipalId, OpeningHouseholdAllocation>::new();
    let mut domains = BTreeMap::new();
    for county in households.counties() {
        let destination = *destinations
            .get(&county.county())
            .ok_or(NationalGrainError::IncompleteCountyMembership)?;
        let domain = domain(destination, membership)?;
        let location = EconomicLocation::domestic_county(county.county())
            .map_err(|_| NationalGrainError::HouseholdMargin(county.county()))?;
        for budget in county.budgets() {
            let source_principal = national_economy::household_principal(location, budget.key);
            let (principal, subject) = if let Some((catchment, position)) = domain.representative {
                national_economy::identity::representative_household(RepresentativeHouseholdKey {
                    catchment,
                    position,
                    budget: budget.key,
                })
            } else {
                (
                    source_principal,
                    national_economy::identity::principal_subject(source_principal),
                )
            };
            principal_map.insert(source_principal, principal);
            domains.insert(AccountId::Household(principal), domain);
            let ages = time
                .county(county.county())
                .map_err(|_| NationalGrainError::TimeMargin(county.county()))?
                .budgets()
                .iter()
                .find(|t| t.key == budget.key)
                .ok_or(NationalGrainError::TimeMargin(county.county()))?;
            witness.household_incidence.push(HouseholdIncidence {
                county: county.county(),
                source: source_principal,
                destination: principal,
                margins: budget.clone(),
                time: ages.clone(),
            });
            if let Some(row) = household_rows.get_mut(&principal) {
                row.margins.persons = add(row.margins.persons, budget.persons)?;
                row.margins.households = add(row.margins.households, budget.households)?;
                row.margins.employed = add(row.margins.employed, budget.employed)?;
                row.margins.reserve = add(row.margins.reserve, budget.reserve)?;
                row.time.eligible_16_plus = add(row.time.eligible_16_plus, ages.eligible_16_plus)?;
                row.time.armed_forces = add(row.time.armed_forces, ages.armed_forces)?;
                row.time.inactive = add(row.time.inactive, ages.inactive)?;
                row.time.under_16 = add(row.time.under_16, ages.under_16)?;
            } else {
                household_rows.insert(
                    principal,
                    OpeningHouseholdAllocation {
                        principal,
                        subject,
                        domain,
                        margins: budget.clone(),
                        time: ages.clone(),
                    },
                );
            }
        }
    }
    for child in &aid.children {
        let EconomicLocation::County(county) = child.location else {
            return Err(NationalGrainError::SourceIncidenceMismatch);
        };
        if destinations.get(&county.geoid())
            != Some(&ContributionDestination::Detailed(county.geoid()))
            || principal_map.get(&child.parent) != Some(&child.parent)
        {
            return Err(NationalGrainError::ProtectedContributionOverlap(
                county.geoid(),
            ));
        }
        principal_map.insert(child.principal, child.principal);
        domains.insert(
            AccountId::Household(child.principal),
            FinancialDomainId::detailed(child.location),
        );
    }
    let mut endowments = BTreeMap::<SiteId, OpeningProductiveEndowment>::new();
    let mut sites = BTreeMap::<SiteId, AssignedResidentWorkplace>::new();
    let mut members =
        BTreeMap::<(SiteId, FinalDemandPrincipalId, u8), (ResidentAttendanceMode, u64, u64)>::new();
    let mut pending_incidence = Vec::new();
    for row in std::mem::take(&mut source.workplaces) {
        let EconomicLocation::County(county) = row.target.location else {
            return Err(NationalGrainError::SourceIncidenceMismatch);
        };
        let destination = *destinations
            .get(&county.geoid())
            .ok_or(NationalGrainError::IncompleteCountyMembership)?;
        let domain = domain(destination, membership)?;
        let endowment = OpeningProductiveEndowment::source(&row, policy)?;
        let target = if let Some((catchment, position)) = domain.representative {
            national_economy::identity::representative_workplace(
                RepresentativeWorkplaceKey {
                    catchment,
                    position,
                    function: row.target.function,
                    ownership: row.target.ownership,
                    source_kind: source_kind(&row.target.source)?,
                },
                domain.location,
            )
        } else {
            row.target.clone()
        };
        domains.insert(AccountId::Site(target.site_id), domain);
        witness
            .source_incidence
            .push(SourceRepresentativeIncidence {
                source_site: row.target.site_id,
                destination_site: target.site_id,
                source_county: county.geoid(),
                source: row.target.source.clone(),
                weight: row.weight.clone(),
                endowment: endowment.clone(),
            });
        if domain.representative.is_some() {
            endowments
                .entry(target.site_id)
                .or_default()
                .accumulate(&endowment)?;
        }
        if domain.representative.is_none() {
            for m in &row.members {
                witness.member_incidence.push(MemberIncidence {
                    source: m.seed.member.member_id(),
                    destination: m.seed.member.member_id(),
                    employed: m.seed.employed,
                    reserve: m.seed.reserve,
                });
            }
            if sites.insert(target.site_id, row).is_some() {
                return Err(NationalGrainError::SourceIncidenceMismatch);
            }
            continue;
        }
        let site_id = target.site_id;
        sites.entry(site_id).or_insert(AssignedResidentWorkplace {
            target,
            weight: None,
            members: Vec::new(),
        });
        for m in row.members {
            let principal = *principal_map
                .get(&m.seed.member.household_id())
                .ok_or(NationalGrainError::SourceIncidenceMismatch)?;
            let mode = match m.mode {
                ResidentAttendanceMode::Employee => 0,
                ResidentAttendanceMode::WorkingOwner => 1,
                ResidentAttendanceMode::UnpaidFamily => 2,
            };
            let key = (site_id, principal, mode);
            let entry = members.entry(key).or_insert((m.mode, 0, 0));
            entry.1 = add(entry.1, m.seed.employed)?;
            entry.2 = add(entry.2, m.seed.reserve)?;
            pending_incidence.push((
                key,
                m.seed.member.member_id(),
                m.seed.employed,
                m.seed.reserve,
            ));
        }
    }
    let mut member_ids = BTreeMap::new();
    for (key, (mode, employed, reserve)) in members {
        let row = sites
            .get_mut(&key.0)
            .ok_or(NationalGrainError::SourceIncidenceMismatch)?;
        let member =
            national_resident_allocation::member(&row.target, mode, key.1, employed, reserve)
                .map_err(|_| NationalGrainError::SourceIncidenceMismatch)?;
        member_ids.insert(key, member.seed.member.member_id());
        row.members.push(member);
    }
    for (key, source, employed, reserve) in pending_incidence {
        witness.member_incidence.push(MemberIncidence {
            source,
            destination: *member_ids
                .get(&key)
                .ok_or(NationalGrainError::SourceIncidenceMismatch)?,
            employed,
            reserve,
        });
    }
    for site in sites.values_mut() {
        site.members.sort_by_key(|m| m.seed.member.member_id());
    }
    source.workplaces = sites.into_values().collect();
    witness.household_incidence.sort_by_key(|i| i.source);
    witness.source_incidence.sort_by_key(|i| i.source_site);
    witness.member_incidence.sort_by_key(|i| i.source);
    if witness
        .source_incidence
        .windows(2)
        .any(|i| i[0].source_site == i[1].source_site)
        || witness
            .member_incidence
            .windows(2)
            .any(|i| i[0].source == i[1].source)
    {
        return Err(NationalGrainError::SourceIncidenceMismatch);
    }
    let source_totals = witness.counties.iter().try_fold((0, 0), |(e, r), c| {
        Ok((add(e, c.controls.employed)?, add(r, c.controls.reserve)?))
    })?;
    let live_totals = source
        .workplaces
        .iter()
        .flat_map(|w| &w.members)
        .try_fold((0, 0), |(e, r), m| {
            Ok((add(e, m.seed.employed)?, add(r, m.seed.reserve)?))
        })?;
    if source_totals != live_totals {
        return Err(NationalGrainError::SourceIncidenceMismatch);
    }
    Ok(NationalOpeningRoster {
        workplaces: source,
        households: household_rows.into_values().collect(),
        workplace_endowments: endowments,
        financial_domains: domains,
        representation: witness,
    })
}
