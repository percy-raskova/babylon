//! Designed sparse child margins subtract from source-controlled parent budgets.
use crate::{
    national_economy::household_principal,
    national_household_allocation::{HouseholdBudgetKey, NationalHouseholdAllocation},
    national_household_time_allocation::NationalHouseholdTimeAllocation,
};
use babylon_kernel::{
    content_digest::sha256_of, economic_location::EconomicLocation, geography::CountyGeoid,
};
use babylon_material_circuit::{FinalDemandPrincipalId, MAX_MATERIAL_CIRCUIT_ROWS};
use std::collections::{BTreeMap, BTreeSet};

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
    fn values(self) -> [u64; 8] {
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
    fn validate(self, collective: bool) -> Result<(), HouseholdRefinementError> {
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
#[derive(Clone, Debug, PartialEq, Eq)]
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
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
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
fn refine_parent(
    county: CountyGeoid,
    key: HouseholdBudgetKey,
    margins: HouseholdLeafMargins,
    mut children: Vec<&HouseholdRefinementSpec>,
) -> Result<Vec<HouseholdLeaf>, HouseholdRefinementError> {
    margins.validate(key == HouseholdBudgetKey::CollectiveResidence)?;
    let location = EconomicLocation::domestic_county(county)
        .map_err(|_| HouseholdRefinementError::SourceRoster)?;
    let principal = household_principal(location, key);
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
            principal_id: FinalDemandPrincipalId::from_bytes(sha256_of(&identity)),
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
#[cfg(test)]
mod tests;
