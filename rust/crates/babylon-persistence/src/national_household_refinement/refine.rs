//! Leaf implementation for the parent module; public paths stay on the parent.

use crate::national_household_allocation::{
    HouseholdBudgetKey, HouseholdCohortKey, NationalHouseholdAllocation,
};
use crate::national_household_time_allocation::NationalHouseholdTimeAllocation;
use babylon_material_circuit::HouseholdTimePolicy;

use babylon_kernel::currency::Currency;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;

use babylon_material_circuit::{
    FinalDemandPrincipalId, GoodId, HouseholdTimeAccounting, OrganizationAccountId, SiteId, UnitId,
    MAX_MATERIAL_CIRCUIT_ROWS,
};

use crate::economic_catalog::{
    EconomicHouseholdSeed, EconomicOpening, EconomicSiteSeed, EconomicSiteSource,
    OpeningCommodityStock, ResidentStaffingMemberSeed,
};
use crate::national_cohorts::WorkplaceCohortKey;
use crate::national_economy;
use babylon_kernel::content_digest;
use babylon_material_circuit::AccountId;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;

/// Joint counted quantities; these rows never create individual agents.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct HouseholdLeafMargins {
    pub persons: u64,
    pub households: u64,
    pub employed: u64,
    pub reserve: u64,
    pub eligible_16_plus: u64,
    pub armed_forces: u64,
    pub inactive: u64,
    pub under_16: u64,
}

impl HouseholdLeafMargins {
    pub(super) fn values(self) -> [u64; 8] {
        [
            self.persons,
            self.households,
            self.employed,
            self.reserve,
            self.eligible_16_plus,
            self.armed_forces,
            self.inactive,
            self.under_16,
        ]
    }
    fn from_values(v: [u64; 8]) -> Self {
        Self {
            persons: v[0],
            households: v[1],
            employed: v[2],
            reserve: v[3],
            eligible_16_plus: v[4],
            armed_forces: v[5],
            inactive: v[6],
            under_16: v[7],
        }
    }
    pub(super) fn validate(self, collective: bool) -> Result<(), HouseholdRefinementError> {
        if self.persons == 0
            || (collective && self.households != 0)
            || (!collective && (self.households == 0 || self.households > self.persons))
            || self
                .employed
                .checked_add(self.reserve)
                .and_then(|n| n.checked_add(self.armed_forces))
                .and_then(|n| n.checked_add(self.inactive))
                != Some(self.eligible_16_plus)
            || self.eligible_16_plus.checked_add(self.under_16) != Some(self.persons)
        {
            return Err(HouseholdRefinementError::Margin);
        }
        Ok(())
    }
    fn subtract(self, child: Self) -> Result<Self, HouseholdRefinementError> {
        let mut values = self.values();
        for (remaining, taken) in values.iter_mut().zip(child.values()) {
            *remaining = remaining
                .checked_sub(taken)
                .ok_or(HouseholdRefinementError::Excess)?;
        }
        Ok(Self::from_values(values))
    }
}

/// Explicit Designed child quantities; the tag is stable independently of counts.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HouseholdRefinementSpec {
    pub county: CountyGeoid,
    pub parent_key: HouseholdBudgetKey,
    pub child_tag: [u8; 32],
    pub margins: HouseholdLeafMargins,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HouseholdLeaf {
    pub county: CountyGeoid,
    pub parent_key: HouseholdBudgetKey,
    /// None retains the original parent principal as the residual leaf.
    pub child_tag: Option<[u8; 32]>,
    pub principal_id: FinalDemandPrincipalId,
    pub margins: HouseholdLeafMargins,
}

/// Immutable derived roster joined to exactly the household and age sources.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalHouseholdLeafRoster {
    private_owner_households_bps: u16,
    county_source_sha256: [u8; 32],
    household_source_sha256: [u8; 32],
    workforce_source_sha256: [u8; 32],
    leaves: Vec<HouseholdLeaf>,
}

impl NationalHouseholdLeafRoster {
    #[must_use]
    pub fn leaves(&self) -> &[HouseholdLeaf] {
        &self.leaves
    }
    #[must_use]
    pub fn parent_leaves(&self, county: CountyGeoid, key: HouseholdBudgetKey) -> &[HouseholdLeaf] {
        let start = self
            .leaves
            .partition_point(|row| (row.county, row.parent_key) < (county, key));
        let end = self
            .leaves
            .partition_point(|row| (row.county, row.parent_key) <= (county, key));
        &self.leaves[start..end]
    }
    #[must_use]
    pub const fn county_source_sha256(&self) -> [u8; 32] {
        self.county_source_sha256
    }
    #[must_use]
    pub const fn household_source_sha256(&self) -> [u8; 32] {
        self.household_source_sha256
    }
    #[must_use]
    pub const fn workforce_source_sha256(&self) -> [u8; 32] {
        self.workforce_source_sha256
    }
    pub(crate) fn matches_sources(&self, budgets: &NationalHouseholdAllocation) -> bool {
        self.private_owner_households_bps == budgets.private_owner_households_bps
            && self.county_source_sha256 == budgets.county_source_sha256
            && self.household_source_sha256 == budgets.household_source_sha256()
            && self.workforce_source_sha256 == budgets.classes_source_sha256
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum HouseholdRefinementError {
    SourceDigest,
    SourceRoster,
    ParentScope,
    Duplicate,
    Identity,
    Margin,
    Excess,
    Bounds,
}

impl std::fmt::Display for HouseholdRefinementError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "household refinement refused: {self:?}")
    }
}

impl std::error::Error for HouseholdRefinementError {}

/// Refine only ordinary nonowner parents; explicit empty specifications use this same path.
/// # Errors
/// Refuses source joins, invalid/duplicate specifications, infeasible residuals or row bounds.
pub fn refine_households(
    budgets: &NationalHouseholdAllocation,
    time: &NationalHouseholdTimeAllocation,
    specs: &[HouseholdRefinementSpec],
) -> Result<NationalHouseholdLeafRoster, HouseholdRefinementError> {
    if budgets.county_source_sha256 != time.county_source_sha256()
        || budgets.household_source_sha256() != time.household_source_sha256()
        || budgets.classes_source_sha256 != time.resident_workforce_source_sha256()
    {
        return Err(HouseholdRefinementError::SourceDigest);
    }
    if specs.len() > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(HouseholdRefinementError::Bounds);
    }
    let mut grouped = BTreeMap::<_, Vec<&HouseholdRefinementSpec>>::new();
    let mut identities = BTreeSet::new();
    for spec in specs {
        if spec.child_tag == [0; 32] {
            return Err(HouseholdRefinementError::Identity);
        }
        if !identities.insert((spec.county, spec.parent_key, spec.child_tag)) {
            return Err(HouseholdRefinementError::Duplicate);
        }
        if !matches!(
            spec.parent_key,
            HouseholdBudgetKey::EarningNonowner | HouseholdBudgetKey::NoEarnerNonowner
        ) {
            return Err(HouseholdRefinementError::ParentScope);
        }
        spec.margins.validate(false)?;
        grouped
            .entry((spec.county, spec.parent_key))
            .or_default()
            .push(spec);
    }
    if budgets.counties().len() != time.counties().len() {
        return Err(HouseholdRefinementError::SourceRoster);
    }
    let mut leaves = Vec::new();
    for county in budgets.counties() {
        let age = time
            .county(county.county())
            .map_err(|_| HouseholdRefinementError::SourceRoster)?;
        if county.budgets().len() != age.budgets().len() {
            return Err(HouseholdRefinementError::SourceRoster);
        }
        for (parent, age) in county.budgets().iter().zip(age.budgets()) {
            if parent.key != age.key || parent.key == HouseholdBudgetKey::PooledExternal {
                return Err(HouseholdRefinementError::SourceRoster);
            }
            let margins = HouseholdLeafMargins {
                persons: parent.persons,
                households: parent.households,
                employed: parent.employed,
                reserve: parent.reserve,
                eligible_16_plus: age.eligible_16_plus,
                armed_forces: age.armed_forces,
                inactive: age.inactive,
                under_16: age.under_16,
            };
            let children = grouped
                .remove(&(county.county(), parent.key))
                .unwrap_or_default();
            leaves.extend(refine_parent(
                county.county(),
                parent.key,
                margins,
                children,
            )?);
        }
    }
    if !grouped.is_empty() {
        return Err(HouseholdRefinementError::SourceRoster);
    }
    if leaves.len() > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(HouseholdRefinementError::Bounds);
    }
    let unique: BTreeSet<_> = leaves.iter().map(|row| row.principal_id).collect();
    if unique.len() != leaves.len() {
        return Err(HouseholdRefinementError::Identity);
    }
    Ok(NationalHouseholdLeafRoster {
        private_owner_households_bps: budgets.private_owner_households_bps,
        county_source_sha256: budgets.county_source_sha256,
        household_source_sha256: budgets.household_source_sha256(),
        workforce_source_sha256: budgets.classes_source_sha256,
        leaves,
    })
}

pub(crate) fn refine_parent(
    county: CountyGeoid,
    key: HouseholdBudgetKey,
    margins: HouseholdLeafMargins,
    mut children: Vec<&HouseholdRefinementSpec>,
) -> Result<Vec<HouseholdLeaf>, HouseholdRefinementError> {
    margins.validate(key == HouseholdBudgetKey::CollectiveResidence)?;
    let location = EconomicLocation::domestic_county(county)
        .map_err(|_| HouseholdRefinementError::SourceRoster)?;
    let principal = national_economy::household_principal(location, key);
    children.sort_by_key(|spec| spec.child_tag);
    let mut remaining = margins;
    let mut leaves = Vec::with_capacity(children.len() + 1);
    for child in children {
        remaining = remaining.subtract(child.margins)?;
        let mut identity = b"NationalHouseholdLeafV1\0".to_vec();
        identity.extend_from_slice(&principal.as_bytes());
        identity.extend_from_slice(&child.child_tag);
        leaves.push(HouseholdLeaf {
            county,
            parent_key: key,
            child_tag: Some(child.child_tag),
            principal_id: FinalDemandPrincipalId::from_bytes(content_digest::sha256_of(&identity)),
            margins: child.margins,
        });
    }
    remaining.validate(key == HouseholdBudgetKey::CollectiveResidence)?;
    leaves.push(HouseholdLeaf {
        county,
        parent_key: key,
        child_tag: None,
        principal_id: principal,
        margins: remaining,
    });
    Ok(leaves)
}

/// Authored foreground identities; the engine never infers them from a read.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct ForegroundSelection {
    /// Controlled or actionable organization accounts.
    pub organizations: BTreeSet<OrganizationAccountId>,
    /// Household principals that keep separately addressable identities.
    pub household_principals: BTreeSet<FinalDemandPrincipalId>,
    /// Workplaces owned by a foreground household or organization.
    pub workplaces: BTreeSet<SiteId>,
    /// Independently actionable partner workplaces.
    pub partner_workplaces: BTreeSet<SiteId>,
    /// Active shipment or commitment identities involving the foreground.
    pub commitments: BTreeSet<[u8; 32]>,
}

/// Resolved foreground identities; every entry exists in the admitted opening.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct ForegroundIdentities {
    organizations: Vec<OrganizationAccountId>,
    household_principals: Vec<FinalDemandPrincipalId>,
    workplaces: Vec<SiteId>,
    partner_workplaces: Vec<SiteId>,
    commitments: Vec<[u8; 32]>,
}
impl ForegroundIdentities {
    /// Organization accounts that keep separate authority.
    #[must_use]
    pub fn organizations(&self) -> &[OrganizationAccountId] {
        &self.organizations
    }
    /// Household principals that keep separate wealth and time.
    #[must_use]
    pub fn household_principals(&self) -> &[FinalDemandPrincipalId] {
        &self.household_principals
    }
    /// Workplaces owned by the controlled organization or household.
    #[must_use]
    pub fn workplaces(&self) -> &[SiteId] {
        &self.workplaces
    }
    /// Independently actionable partner workplaces.
    #[must_use]
    pub fn partner_workplaces(&self) -> &[SiteId] {
        &self.partner_workplaces
    }
    /// Active shipment and commitment identities.
    #[must_use]
    pub fn commitments(&self) -> &[[u8; 32]] {
        &self.commitments
    }
}

/// One retained commitment; in-flight goods with different terms never merge.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AuthoredCommitment {
    /// Stable commitment identity.
    pub id: [u8; 32],
    /// Donor or buyer principal.
    pub donor: FinalDemandPrincipalId,
    /// Recipient or seller principal.
    pub recipient: FinalDemandPrincipalId,
    /// Fixed destination location.
    pub location: EconomicLocation,
    /// Good retained in transit.
    pub good_id: GoodId,
    /// Unit retained in transit.
    pub unit_id: UnitId,
    /// Maximum commitment quantity.
    pub maximum_quantity: u64,
}

/// Counted background household quantities; counts never imply individuals.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct HouseholdCohortCounts {
    /// Resident persons.
    pub persons: u64,
    /// Occupied households, zero for collective residence.
    pub households: u64,
    /// Employed residents.
    pub employed: u64,
    /// Employed residents held in reserve.
    pub reserve: u64,
    /// Age-eligible residents.
    pub eligible_persons: u64,
    /// Gross household endowment before attendance, protected and routine-
    /// provisioning commitments. The last closed receipt's
    /// `contribution_available_hours` is the spendable remainder, not this value.
    pub endowment_hours: u64,
}
impl HouseholdCohortCounts {
    fn checked_add(self, other: Self) -> Result<Self, ConsolidationError> {
        Ok(Self {
            persons: self
                .persons
                .checked_add(other.persons)
                .ok_or(ConsolidationError::Arithmetic)?,
            households: self
                .households
                .checked_add(other.households)
                .ok_or(ConsolidationError::Arithmetic)?,
            employed: self
                .employed
                .checked_add(other.employed)
                .ok_or(ConsolidationError::Arithmetic)?,
            reserve: self
                .reserve
                .checked_add(other.reserve)
                .ok_or(ConsolidationError::Arithmetic)?,
            eligible_persons: self
                .eligible_persons
                .checked_add(other.eligible_persons)
                .ok_or(ConsolidationError::Arithmetic)?,
            endowment_hours: self
                .endowment_hours
                .checked_add(other.endowment_hours)
                .ok_or(ConsolidationError::Arithmetic)?,
        })
    }
}

/// One counted background household row; its exact causal key never blends.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct BackgroundHouseholdCohort {
    /// Exact owner, location and causal axes.
    pub key: HouseholdCohortKey,
    /// Counted margins and gross endowment.
    pub counts: HouseholdCohortCounts,
    /// Opening cash owned by this principal.
    pub opening_cash: Currency,
    /// Pantry stock merged only within one (good, unit).
    pub opening_stock: Vec<OpeningCommodityStock>,
}
impl BackgroundHouseholdCohort {
    fn absorb(&mut self, other: Self) -> Result<(), ConsolidationError> {
        self.counts = self.counts.checked_add(other.counts)?;
        self.opening_cash = Currency::from_micro_units(
            self.opening_cash
                .micro_units()
                .checked_add(other.opening_cash.micro_units())
                .ok_or(ConsolidationError::Arithmetic)?,
        );
        self.opening_stock.extend(other.opening_stock);
        self.opening_stock = merge_stock(std::mem::take(&mut self.opening_stock))?;
        Ok(())
    }
}

/// One counted background workplace; equivalent sites share one row.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct BackgroundWorkplaceCohort {
    /// Exact location, function and ownership axes.
    pub key: WorkplaceCohortKey,
    /// Number of admitted source sites coalesced into this counted workplace.
    pub sites: u64,
    /// Employee residents assigned to the coalesced sites.
    pub employed: u64,
    /// Assigned residents held in reserve.
    pub reserve: u64,
    /// Assigned resident labor force.
    pub labor_force: u64,
    /// Opening cash owned by the coalesced sites.
    pub opening_cash: Currency,
    /// Stock merged only within one (good, unit).
    pub opening_stock: Vec<OpeningCommodityStock>,
}
impl BackgroundWorkplaceCohort {
    fn absorb(&mut self, other: Self) -> Result<(), ConsolidationError> {
        self.sites = self
            .sites
            .checked_add(other.sites)
            .ok_or(ConsolidationError::Arithmetic)?;
        self.employed = self
            .employed
            .checked_add(other.employed)
            .ok_or(ConsolidationError::Arithmetic)?;
        self.reserve = self
            .reserve
            .checked_add(other.reserve)
            .ok_or(ConsolidationError::Arithmetic)?;
        self.labor_force = self
            .labor_force
            .checked_add(other.labor_force)
            .ok_or(ConsolidationError::Arithmetic)?;
        self.opening_cash = Currency::from_micro_units(
            self.opening_cash
                .micro_units()
                .checked_add(other.opening_cash.micro_units())
                .ok_or(ConsolidationError::Arithmetic)?,
        );
        self.opening_stock.extend(other.opening_stock);
        self.opening_stock = merge_stock(std::mem::take(&mut self.opening_stock))?;
        Ok(())
    }
}

/// Exact conserved totals of one background population.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct CohortConservation {
    /// Resident persons.
    pub persons: u64,
    /// Occupied households.
    pub households: u64,
    /// Employed residents.
    pub employed: u64,
    /// Employed residents held in reserve.
    pub reserve: u64,
    /// Assigned resident labor force.
    pub labor_force: u64,
    /// Gross household endowment hours before attendance and commitments.
    pub endowment_hours: u64,
    /// Physical stock quantity.
    pub stock_quantity: u64,
    /// Stock carrying cost in micro-units.
    pub stock_cost_micros: i128,
    /// Cash in micro-units.
    pub cash_micros: i128,
}
impl CohortConservation {
    /// Add two independent totals without wrapping.
    /// # Errors
    /// Refuses checked overflow in any counted or monetary axis.
    pub fn checked_add(self, other: Self) -> Result<Self, ConsolidationError> {
        Ok(Self {
            persons: self
                .persons
                .checked_add(other.persons)
                .ok_or(ConsolidationError::Arithmetic)?,
            households: self
                .households
                .checked_add(other.households)
                .ok_or(ConsolidationError::Arithmetic)?,
            employed: self
                .employed
                .checked_add(other.employed)
                .ok_or(ConsolidationError::Arithmetic)?,
            reserve: self
                .reserve
                .checked_add(other.reserve)
                .ok_or(ConsolidationError::Arithmetic)?,
            labor_force: self
                .labor_force
                .checked_add(other.labor_force)
                .ok_or(ConsolidationError::Arithmetic)?,
            endowment_hours: self
                .endowment_hours
                .checked_add(other.endowment_hours)
                .ok_or(ConsolidationError::Arithmetic)?,
            stock_quantity: self
                .stock_quantity
                .checked_add(other.stock_quantity)
                .ok_or(ConsolidationError::Arithmetic)?,
            stock_cost_micros: self
                .stock_cost_micros
                .checked_add(other.stock_cost_micros)
                .ok_or(ConsolidationError::Arithmetic)?,
            cash_micros: self
                .cash_micros
                .checked_add(other.cash_micros)
                .ok_or(ConsolidationError::Arithmetic)?,
        })
    }
}

/// Conserved household and workplace totals of one authored partition.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub struct DetailConservation {
    /// Household population, work, stock and cash.
    pub households: CohortConservation,
    /// Workplace employment, stock and cash.
    pub workplaces: CohortConservation,
}
impl DetailConservation {
    /// Add two independent totals without wrapping.
    /// # Errors
    /// Refuses checked overflow in either population.
    pub fn checked_add(self, other: Self) -> Result<Self, ConsolidationError> {
        Ok(Self {
            households: self.households.checked_add(other.households)?,
            workplaces: self.workplaces.checked_add(other.workplaces)?,
        })
    }
}

/// Authored uneven national detail fixed at campaign initialization.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalDetailPartition {
    foreground: ForegroundIdentities,
    background_households: Vec<BackgroundHouseholdCohort>,
    background_workplaces: Vec<BackgroundWorkplaceCohort>,
    commitments: Vec<AuthoredCommitment>,
    conservation: DetailConservation,
}
impl NationalDetailPartition {
    /// Separately addressable foreground identities.
    #[must_use]
    pub const fn foreground(&self) -> &ForegroundIdentities {
        &self.foreground
    }
    /// Counted background households, one row per retained owner.
    #[must_use]
    pub fn background_households(&self) -> &[BackgroundHouseholdCohort] {
        &self.background_households
    }
    /// Counted background workplaces, one row per retained owner site.
    #[must_use]
    pub fn background_workplaces(&self) -> &[BackgroundWorkplaceCohort] {
        &self.background_workplaces
    }
    /// Active foreground shipments and commitments.
    #[must_use]
    pub fn commitments(&self) -> &[AuthoredCommitment] {
        &self.commitments
    }
    /// Exact totals the partition retains.
    #[must_use]
    pub const fn conservation(&self) -> DetailConservation {
        self.conservation
    }
}

/// Specific partition refusals; no inferred actor fills a missing identity.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ConsolidationError {
    /// A foreground identity is absent from the admitted opening.
    UnknownForeground,
    /// A foreground identity was named twice under conflicting meaning.
    DuplicateForeground,
    /// A household row has no captured budget identity.
    MissingBudget,
    /// A household row has no captured time policy.
    MissingTime,
    /// The opening has no complete household or workplace roster.
    SourceRoster,
    /// An authored commitment is unselected or names a non-foreground principal.
    Commitment,
    /// Background and foreground rows do not reconstruct the source total.
    Conservation,
    /// A counted or monetary sum overflowed.
    Arithmetic,
}
impl std::fmt::Display for ConsolidationError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        write!(formatter, "national detail partition refused: {self:?}")
    }
}
impl std::error::Error for ConsolidationError {}

/// Split one admitted opening into authored foreground identities and counted background rows.
/// Household rows coalesce only when owner, location and budget agree; workplace rows
/// coalesce only when location, function and source ownership agree. In-flight goods with
/// different principals, units or terms never blend.
/// # Errors
/// Refuses unknown or duplicate foreground identities, missing source rows, and any partition
/// whose background and foreground totals do not reproduce the admitted source exactly.
pub fn consolidate_background(
    opening: &EconomicOpening,
    household_budgets: &BTreeMap<FinalDemandPrincipalId, HouseholdBudgetKey>,
    time: &HouseholdTimeAccounting,
    foreground: ForegroundSelection,
    commitments: &[AuthoredCommitment],
) -> Result<NationalDetailPartition, ConsolidationError> {
    let HouseholdTimeAccounting::Modeled(_) = time else {
        return Err(ConsolidationError::MissingTime);
    };
    let households = unique_households(opening)?;
    let sites = unique_sites(opening)?;
    let work = work_indexes(opening)?;
    let time_rows = time_index(&opening.policies.household_time_policy)?;
    if time_rows.len() != households.len() {
        return Err(ConsolidationError::MissingTime);
    }
    validate_foreground(&foreground, opening, &households, &sites, commitments)?;
    let expected = DetailConservation {
        households: household_totals(&households, &work.households, &time_rows)?,
        workplaces: workplace_totals(&sites, &work.workplaces)?,
    };
    let (background_households, foreground_households) = partition_households(
        opening,
        household_budgets,
        &work.households,
        &time_rows,
        &foreground,
    )?;
    let (background_workplaces, foreground_workplaces) =
        partition_workplaces(opening, &work.workplaces, &foreground)?;
    let retained = DetailConservation {
        households: foreground_households
            .checked_add(background_household_total(&background_households)?)?,
        workplaces: foreground_workplaces
            .checked_add(background_workplace_total(&background_workplaces)?)?,
    };
    if retained != expected {
        return Err(ConsolidationError::Conservation);
    }
    let mut authored = commitments.to_vec();
    authored.sort_unstable_by_key(|row| row.id);
    Ok(NationalDetailPartition {
        foreground: ForegroundIdentities {
            organizations: foreground.organizations.into_iter().collect(),
            household_principals: foreground.household_principals.into_iter().collect(),
            workplaces: foreground.workplaces.into_iter().collect(),
            partner_workplaces: foreground.partner_workplaces.into_iter().collect(),
            commitments: foreground.commitments.into_iter().collect(),
        },
        background_households,
        background_workplaces,
        commitments: authored,
        conservation: expected,
    })
}

struct WorkIndex {
    households: BTreeMap<FinalDemandPrincipalId, (u64, u64, u64)>,
    workplaces: BTreeMap<SiteId, (u64, u64, u64)>,
}

fn work_indexes(opening: &EconomicOpening) -> Result<WorkIndex, ConsolidationError> {
    let mut households = BTreeMap::new();
    let mut workplaces = BTreeMap::new();
    for pool in &opening.staffing {
        let site = workplaces.entry(pool.pool.site_id()).or_default();
        for member in &pool.members {
            let household = households.entry(member.member.household_id()).or_default();
            add_work(household, member)?;
            add_work(site, member)?;
        }
    }
    Ok(WorkIndex {
        households,
        workplaces,
    })
}

fn add_work(
    totals: &mut (u64, u64, u64),
    member: &ResidentStaffingMemberSeed,
) -> Result<(), ConsolidationError> {
    totals.0 = totals
        .0
        .checked_add(member.employed)
        .ok_or(ConsolidationError::Arithmetic)?;
    totals.1 = totals
        .1
        .checked_add(member.reserve)
        .ok_or(ConsolidationError::Arithmetic)?;
    totals.2 = totals
        .2
        .checked_add(member.member.labor_force())
        .ok_or(ConsolidationError::Arithmetic)?;
    Ok(())
}

fn time_index(
    policies: &[HouseholdTimePolicy],
) -> Result<BTreeMap<FinalDemandPrincipalId, (u64, u64)>, ConsolidationError> {
    policies
        .iter()
        .map(|policy| {
            let hours = policy
                .eligible_persons
                .checked_mul(policy.hours_per_eligible_person)
                .ok_or(ConsolidationError::Arithmetic)?;
            Ok((policy.principal_id, (policy.eligible_persons, hours)))
        })
        .collect()
}

fn partition_households(
    opening: &EconomicOpening,
    household_budgets: &BTreeMap<FinalDemandPrincipalId, HouseholdBudgetKey>,
    work: &BTreeMap<FinalDemandPrincipalId, (u64, u64, u64)>,
    time: &BTreeMap<FinalDemandPrincipalId, (u64, u64)>,
    foreground: &ForegroundSelection,
) -> Result<(Vec<BackgroundHouseholdCohort>, CohortConservation), ConsolidationError> {
    let mut rows = Vec::new();
    let mut foreground_total = CohortConservation::default();
    for household in &opening.households {
        let counts = household_counts(
            household.persons,
            household.households,
            work.get(&household.principal_id)
                .copied()
                .unwrap_or_default(),
            time.get(&household.principal_id).copied(),
        )?;
        let stock = merge_stock(household.opening_stock.clone())?;
        let row_total =
            household_conservation(counts, household.opening_cash.micro_units(), &stock)?;
        if foreground
            .household_principals
            .contains(&household.principal_id)
        {
            foreground_total = foreground_total.checked_add(row_total)?;
            continue;
        }
        let budget = *household_budgets
            .get(&household.principal_id)
            .ok_or(ConsolidationError::MissingBudget)?;
        rows.push(BackgroundHouseholdCohort {
            key: HouseholdCohortKey {
                principal: household.principal_id,
                location: household.location,
                budget,
            },
            counts,
            opening_cash: household.opening_cash,
            opening_stock: stock,
        });
    }
    let background = consolidate_household_rows(rows)?;
    if background
        .iter()
        .any(|row| foreground.household_principals.contains(&row.key.principal))
    {
        return Err(ConsolidationError::DuplicateForeground);
    }
    let expected_background = opening
        .households
        .len()
        .checked_sub(foreground.household_principals.len())
        .ok_or(ConsolidationError::Conservation)?;
    if background.len() != expected_background {
        return Err(ConsolidationError::Conservation);
    }
    Ok((background, foreground_total))
}

fn partition_workplaces(
    opening: &EconomicOpening,
    work: &BTreeMap<SiteId, (u64, u64, u64)>,
    foreground: &ForegroundSelection,
) -> Result<(Vec<BackgroundWorkplaceCohort>, CohortConservation), ConsolidationError> {
    let mut rows = Vec::new();
    let mut foreground_total = CohortConservation::default();
    for site in &opening.sites {
        let row = workplace_row(site, work)?;
        if foreground.workplaces.contains(&site.site_id)
            || foreground.partner_workplaces.contains(&site.site_id)
        {
            foreground_total = foreground_total.checked_add(workplace_conservation(&row)?)?;
            continue;
        }
        rows.push(row);
    }
    let background = consolidate_workplace_rows(rows)?;
    let background_sites = background.iter().try_fold(0_u64, |total, row| {
        total
            .checked_add(row.sites)
            .ok_or(ConsolidationError::Arithmetic)
    })?;
    let expected_sites = opening
        .sites
        .iter()
        .filter(|site| {
            !foreground.workplaces.contains(&site.site_id)
                && !foreground.partner_workplaces.contains(&site.site_id)
        })
        .count();
    if background_sites
        != u64::try_from(expected_sites).map_err(|_| ConsolidationError::Arithmetic)?
    {
        return Err(ConsolidationError::Conservation);
    }
    Ok((background, foreground_total))
}

fn workplace_row(
    site: &EconomicSiteSeed,
    work: &BTreeMap<SiteId, (u64, u64, u64)>,
) -> Result<BackgroundWorkplaceCohort, ConsolidationError> {
    let (employed, reserve, labor_force) = work.get(&site.site_id).copied().unwrap_or_default();
    Ok(BackgroundWorkplaceCohort {
        key: workplace_key(site)?,
        sites: 1,
        employed,
        reserve,
        labor_force,
        opening_cash: site.opening_cash,
        opening_stock: merge_stock(site.opening_stock.clone())?,
    })
}

/// Coalesce rows that share one household causal key. The authored opening has
/// one seed per owner, location and budget, so a valid partition normally keeps
/// every row separate; a repeated equivalent owner would merge under checked
/// arithmetic rather than publishing two rows for one causal key.
pub(super) fn consolidate_household_rows(
    mut rows: Vec<BackgroundHouseholdCohort>,
) -> Result<Vec<BackgroundHouseholdCohort>, ConsolidationError> {
    rows.sort_unstable_by_key(|row| row.key);
    let mut merged: Vec<BackgroundHouseholdCohort> = Vec::with_capacity(rows.len());
    for row in rows {
        match merged.last_mut() {
            Some(last) if last.key.equivalent_for_consolidation(&row.key) => last.absorb(row)?,
            _ => merged.push(row),
        }
    }
    Ok(merged)
}

/// Coalesce sites that share one counted background workplace key. The site
/// identity itself is not part of this key: a background workplace is the
/// county/function/ownership actor chapter 05 requires, and the retained `sites`
/// count plus the key set conserve every admitted source site.
pub(super) fn consolidate_workplace_rows(
    mut rows: Vec<BackgroundWorkplaceCohort>,
) -> Result<Vec<BackgroundWorkplaceCohort>, ConsolidationError> {
    rows.sort_unstable_by_key(|row| row.key);
    let mut merged: Vec<BackgroundWorkplaceCohort> = Vec::with_capacity(rows.len());
    for row in rows {
        match merged.last_mut() {
            Some(last) if last.key.equivalent_for_consolidation(&row.key) => last.absorb(row)?,
            _ => merged.push(row),
        }
    }
    Ok(merged)
}

fn workplace_conservation(
    row: &BackgroundWorkplaceCohort,
) -> Result<CohortConservation, ConsolidationError> {
    let (stock_quantity, stock_cost_micros) = stock_totals(&row.opening_stock)?;
    Ok(CohortConservation {
        employed: row.employed,
        reserve: row.reserve,
        labor_force: row.labor_force,
        stock_quantity,
        stock_cost_micros,
        cash_micros: row.opening_cash.micro_units(),
        ..CohortConservation::default()
    })
}

fn background_household_total(
    rows: &[BackgroundHouseholdCohort],
) -> Result<CohortConservation, ConsolidationError> {
    let mut totals = CohortConservation::default();
    for row in rows {
        totals = totals.checked_add(household_conservation(
            row.counts,
            row.opening_cash.micro_units(),
            &row.opening_stock,
        )?)?;
    }
    Ok(totals)
}

fn background_workplace_total(
    rows: &[BackgroundWorkplaceCohort],
) -> Result<CohortConservation, ConsolidationError> {
    let mut totals = CohortConservation::default();
    for row in rows {
        totals = totals.checked_add(workplace_conservation(row)?)?;
    }
    Ok(totals)
}

fn unique_households(
    opening: &EconomicOpening,
) -> Result<BTreeMap<FinalDemandPrincipalId, &EconomicHouseholdSeed>, ConsolidationError> {
    let mut rows = BTreeMap::new();
    for household in &opening.households {
        if rows.insert(household.principal_id, household).is_some() {
            return Err(ConsolidationError::SourceRoster);
        }
    }
    Ok(rows)
}
fn unique_sites(
    opening: &EconomicOpening,
) -> Result<BTreeMap<SiteId, &EconomicSiteSeed>, ConsolidationError> {
    let mut rows = BTreeMap::new();
    for site in &opening.sites {
        if rows.insert(site.site_id, site).is_some() {
            return Err(ConsolidationError::SourceRoster);
        }
    }
    Ok(rows)
}
fn validate_foreground(
    selection: &ForegroundSelection,
    opening: &EconomicOpening,
    households: &BTreeMap<FinalDemandPrincipalId, &EconomicHouseholdSeed>,
    sites: &BTreeMap<SiteId, &EconomicSiteSeed>,
    commitments: &[AuthoredCommitment],
) -> Result<(), ConsolidationError> {
    let organizations: BTreeSet<_> = opening
        .institutional_cash
        .iter()
        .filter_map(|row| match row.id {
            AccountId::Organization(account) => Some(account),
            AccountId::Site(_) | AccountId::Household(_) | AccountId::Public(_) => None,
        })
        .collect();
    if selection
        .organizations
        .iter()
        .any(|account| !organizations.contains(account))
        || selection
            .household_principals
            .iter()
            .any(|principal| !households.contains_key(principal))
        || selection
            .workplaces
            .iter()
            .chain(&selection.partner_workplaces)
            .any(|site| !sites.contains_key(site))
    {
        return Err(ConsolidationError::UnknownForeground);
    }
    let authored: BTreeMap<_, _> = commitments.iter().map(|row| (row.id, row)).collect();
    if authored.len() != commitments.len() {
        return Err(ConsolidationError::DuplicateForeground);
    }
    if selection.commitments.len() != authored.len() {
        return Err(ConsolidationError::Commitment);
    }
    for id in &selection.commitments {
        let row = authored.get(id).ok_or(ConsolidationError::Commitment)?;
        if !selection.household_principals.contains(&row.donor)
            || !selection.household_principals.contains(&row.recipient)
        {
            return Err(ConsolidationError::Commitment);
        }
    }
    Ok(())
}
fn household_counts(
    persons: u64,
    households: u64,
    (employed, reserve, _labor_force): (u64, u64, u64),
    time: Option<(u64, u64)>,
) -> Result<HouseholdCohortCounts, ConsolidationError> {
    let (eligible_persons, endowment_hours) = time.ok_or(ConsolidationError::MissingTime)?;
    Ok(HouseholdCohortCounts {
        persons,
        households,
        employed,
        reserve,
        eligible_persons,
        endowment_hours,
    })
}
fn stock_totals(rows: &[OpeningCommodityStock]) -> Result<(u64, i128), ConsolidationError> {
    let quantity = rows.iter().try_fold(0_u64, |total, row| {
        total
            .checked_add(row.amount.quantity)
            .ok_or(ConsolidationError::Arithmetic)
    })?;
    let cost = rows.iter().try_fold(0_i128, |total, row| {
        total
            .checked_add(row.total_cost.micro_units())
            .ok_or(ConsolidationError::Arithmetic)
    })?;
    Ok((quantity, cost))
}
fn household_conservation(
    counts: HouseholdCohortCounts,
    cash_micros: i128,
    stock: &[OpeningCommodityStock],
) -> Result<CohortConservation, ConsolidationError> {
    let (stock_quantity, stock_cost_micros) = stock_totals(stock)?;
    Ok(CohortConservation {
        persons: counts.persons,
        households: counts.households,
        employed: counts.employed,
        reserve: counts.reserve,
        labor_force: counts
            .employed
            .checked_add(counts.reserve)
            .ok_or(ConsolidationError::Arithmetic)?,
        endowment_hours: counts.endowment_hours,
        stock_quantity,
        stock_cost_micros,
        cash_micros,
    })
}
fn household_totals(
    households: &BTreeMap<FinalDemandPrincipalId, &EconomicHouseholdSeed>,
    work: &BTreeMap<FinalDemandPrincipalId, (u64, u64, u64)>,
    time: &BTreeMap<FinalDemandPrincipalId, (u64, u64)>,
) -> Result<CohortConservation, ConsolidationError> {
    let mut totals = CohortConservation::default();
    for household in households.values() {
        let counts = household_counts(
            household.persons,
            household.households,
            work.get(&household.principal_id)
                .copied()
                .unwrap_or_default(),
            time.get(&household.principal_id).copied(),
        )?;
        totals = totals.checked_add(household_conservation(
            counts,
            household.opening_cash.micro_units(),
            &household.opening_stock,
        )?)?;
    }
    Ok(totals)
}
fn workplace_totals(
    sites: &BTreeMap<SiteId, &EconomicSiteSeed>,
    work: &BTreeMap<SiteId, (u64, u64, u64)>,
) -> Result<CohortConservation, ConsolidationError> {
    let mut totals = CohortConservation::default();
    for site in sites.values() {
        let (employed, reserve, labor_force) = work.get(&site.site_id).copied().unwrap_or_default();
        let (stock_quantity, stock_cost_micros) = stock_totals(&site.opening_stock)?;
        totals = totals.checked_add(CohortConservation {
            employed,
            reserve,
            labor_force,
            stock_quantity,
            stock_cost_micros,
            cash_micros: site.opening_cash.micro_units(),
            ..CohortConservation::default()
        })?;
    }
    Ok(totals)
}
fn workplace_key(site: &EconomicSiteSeed) -> Result<WorkplaceCohortKey, ConsolidationError> {
    match &site.source {
        EconomicSiteSource::Qcew(key) => WorkplaceCohortKey::source_backed(*key, site.location)
            .ok_or(ConsolidationError::SourceRoster),
        EconomicSiteSource::MichiganSector { .. } | EconomicSiteSource::Designed { .. } => {
            Ok(WorkplaceCohortKey::designed(site.location, site.function))
        }
    }
}
pub(super) fn merge_stock(
    mut rows: Vec<OpeningCommodityStock>,
) -> Result<Vec<OpeningCommodityStock>, ConsolidationError> {
    rows.sort_unstable_by_key(|row| (row.amount.good_id, row.amount.unit_id));
    let mut merged: Vec<OpeningCommodityStock> = Vec::with_capacity(rows.len());
    for row in rows {
        if let Some(last) = merged.last_mut() {
            if (last.amount.good_id, last.amount.unit_id)
                == (row.amount.good_id, row.amount.unit_id)
            {
                last.amount.quantity = last
                    .amount
                    .quantity
                    .checked_add(row.amount.quantity)
                    .ok_or(ConsolidationError::Arithmetic)?;
                last.total_cost = Currency::from_micro_units(
                    last.total_cost
                        .micro_units()
                        .checked_add(row.total_cost.micro_units())
                        .ok_or(ConsolidationError::Arithmetic)?,
                );
                continue;
            }
        }
        merged.push(row);
    }
    Ok(merged)
}
