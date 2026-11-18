//! Carve Wayne's independently accounted support claim from observed source controls.
use super::actors::HouseholdEndowment;
use super::{actors, Builder, NationalOpeningError as Error, Result};
use crate::national_economy::{self, GameHouseholdSupportClaimant, NATIONAL_SCENARIO_ID};
use crate::national_household_allocation::{HouseholdBudgetKey, NationalHouseholdAllocation};
use crate::national_household_refinement::{
    self, HouseholdLeafMargins, HouseholdRefinementSpec, NationalHouseholdLeafRoster,
};
use crate::national_household_time_allocation::NationalHouseholdTimeAllocation;

use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::content_digest;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::FinalDemandPrincipalId;

const SUBJECT: &str = "wayne-household-support-claimants";
const BUDGET: HouseholdBudgetKey = HouseholdBudgetKey::NoEarnerNonowner;

/// Exact counted opening identity behind the separate county support claim.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalSupportClaimant {
    pub principal: FinalDemandPrincipalId,
    pub parent: FinalDemandPrincipalId,
    pub location: EconomicLocation,
    pub subject: StableElementKey,
    pub source_hash: [u8; 32],
    pub margins: HouseholdLeafMargins,
}

pub(super) fn refine(
    budgets: &NationalHouseholdAllocation,
    time: &NationalHouseholdTimeAllocation,
    policy: Option<GameHouseholdSupportClaimant>,
    source_hash: [u8; 32],
) -> Result<(NationalHouseholdLeafRoster, Option<NationalSupportClaimant>)> {
    let Some(policy) = policy else {
        let roster = national_household_refinement::refine_households(budgets, time, &[])
            .map_err(Error::HouseholdRefinement)?;
        return Ok((roster, None));
    };
    if source_hash == [0; 32] {
        return Err(Error::Identity);
    }
    let location =
        EconomicLocation::domestic_county(policy.county).map_err(|_| Error::SourceScope)?;
    let spec = HouseholdRefinementSpec {
        county: policy.county,
        parent_key: BUDGET,
        child_tag: content_digest::sha256_of(SUBJECT.as_bytes()),
        margins: HouseholdLeafMargins {
            persons: policy.reserve_persons,
            households: policy.households,
            employed: 0,
            reserve: policy.reserve_persons,
            eligible_16_plus: policy.reserve_persons,
            armed_forces: 0,
            inactive: 0,
            under_16: 0,
        },
    };
    let roster = national_household_refinement::refine_households(
        budgets,
        time,
        std::slice::from_ref(&spec),
    )
    .map_err(Error::HouseholdRefinement)?;
    let leaf = roster
        .parent_leaves(spec.county, spec.parent_key)
        .iter()
        .find(|leaf| leaf.child_tag == Some(spec.child_tag))
        .ok_or(Error::Identity)?;
    let claimant = NationalSupportClaimant {
        principal: leaf.principal_id,
        parent: national_economy::household_principal(location, spec.parent_key),
        location,
        subject: StableElementKey::Node {
            scenario: NATIONAL_SCENARIO_ID.into(),
            local_name: SUBJECT.into(),
        },
        source_hash,
        margins: leaf.margins,
    };
    Ok((roster, Some(claimant)))
}

pub(super) fn household(builder: &mut Builder<'_>) -> Result<()> {
    let Some(claimant) = builder.support_claimant.as_ref() else {
        return Ok(());
    };
    // The same source parent has an inactive aid recipient. Reserve people and
    // their eligibility are independently debited from the post-aid remainder.
    let remaining = builder
        .eligible_overrides
        .get_mut(&claimant.parent)
        .ok_or(Error::Identity)?;
    *remaining = remaining
        .checked_sub(claimant.margins.eligible_16_plus)
        .ok_or(Error::SourceScope)?;
    builder
        .eligible_overrides
        .insert(claimant.principal, claimant.margins.eligible_16_plus);
    let location = claimant.location;
    let parent = claimant.parent;
    let margins = claimant.margins;
    let identity = (claimant.principal, claimant.subject.clone());
    actors::household_identity(
        builder,
        location,
        BUDGET,
        margins.persons,
        margins.households,
        10_000,
        identity,
    )?;
    actors::debit_household_parent(builder, parent, HouseholdEndowment::Transfer)
}
