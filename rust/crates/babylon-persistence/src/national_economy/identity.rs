//! Material actor identities; location, technical function and ownership are separate.

use super::NationalGamePolicyError;
use crate::national_cohorts::CohortKey;
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::{
    content_digest::sha256_of,
    economic_identity::{EconomicFunction, QcewOwnership},
    economic_location::EconomicLocation,
};
use babylon_material_circuit::{FinalDemandPrincipalId, SiteId, StaffingPoolId};

/// Qualified BSCN scope shared by every national graph subject.
pub const NATIONAL_SCENARIO_ID: &str = "economy/national-world";

/// The observation supporting activity, or a named Designed placement.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ResidentWorkplaceSource {
    Qcew(CohortKey),
    HouseholdEnterprise,
    ResidentEmployerFallback,
}

/// One allocation target, not an allocation of additional persons from jobs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResidentWorkplaceTarget {
    pub site_id: SiteId,
    pub pool_id: StaffingPoolId,
    pub workplace: StableElementKey,
    pub location: EconomicLocation,
    pub function: EconomicFunction,
    pub ownership: QcewOwnership,
    pub allocation_weight: u64,
    pub source: ResidentWorkplaceSource,
}

/// One explicitly named counted budget at a fixed location; no current income
/// or employment changes this identity.
#[must_use]
pub fn household_principal(
    location: EconomicLocation,
    budget: crate::national_household_allocation::HouseholdBudgetKey,
) -> FinalDemandPrincipalId {
    let mut bytes = b"NationalHouseholdV2\0".to_vec();
    bytes.extend_from_slice(&location.canonical_bytes());
    bytes.push(budget as u8);
    FinalDemandPrincipalId::from_bytes(sha256_of(&bytes))
}

/// Declare a source-supported county workplace; the compiler separately admits
/// its county and cohort against the exact captured source tables.
/// # Errors
/// Refuses a non-county location, which cannot claim a domestic QCEW observation.
pub fn source_workplace_target(
    location: EconomicLocation,
    function: EconomicFunction,
    ownership: QcewOwnership,
    allocation_weight: u64,
) -> Result<ResidentWorkplaceTarget, NationalGamePolicyError> {
    let EconomicLocation::County(county) = location else {
        return Err(NationalGamePolicyError::Location);
    };
    let mut bytes = b"NationalSiteV1\0".to_vec();
    bytes.extend_from_slice(&location.canonical_bytes());
    bytes.extend_from_slice(function.source_key().as_bytes());
    bytes.push(0);
    bytes.extend_from_slice(ownership.source_code().as_bytes());
    Ok(target(
        location,
        function,
        ownership,
        allocation_weight,
        &bytes,
        format!(
            "site-{}-{}-{}",
            county.geoid(),
            function.source_key().replace('_', "-"),
            ownership.source_code()
        ),
        ResidentWorkplaceSource::Qcew(CohortKey {
            county: county.geoid(),
            function: Some(function),
            ownership,
        }),
    ))
}

/// The explicit Designed activity of resident working owners and unpaid family.
/// # Errors
/// Refuses foreign scope: domestic source workforce classes do not authorize it.
pub fn household_enterprise_target(
    location: EconomicLocation,
) -> Result<ResidentWorkplaceTarget, NationalGamePolicyError> {
    let EconomicLocation::County(county) = location else {
        return Err(NationalGamePolicyError::Location);
    };
    let mut bytes = b"NationalHouseholdEnterpriseV1\0".to_vec();
    bytes.extend_from_slice(&location.canonical_bytes());
    Ok(target(
        location,
        EconomicFunction::HouseholdServices,
        QcewOwnership::Private,
        1,
        &bytes,
        format!("enterprise-{}", county.geoid()),
        ResidentWorkplaceSource::HouseholdEnterprise,
    ))
}

/// Explicit placement when source resident employees have no matching admitted
/// home-county workplace. The absence remains in the captured observations.
/// # Errors
/// Refuses non-county scope; does not claim a commuting or QCEW observation.
pub fn resident_employer_target(
    location: EconomicLocation,
    ownership: QcewOwnership,
) -> Result<ResidentWorkplaceTarget, NationalGamePolicyError> {
    let EconomicLocation::County(county) = location else {
        return Err(NationalGamePolicyError::Location);
    };
    let function = if ownership == QcewOwnership::Private {
        EconomicFunction::HouseholdServices
    } else {
        EconomicFunction::PublicProvisioning
    };
    let mut bytes = b"NationalResidentEmployerV1\0".to_vec();
    bytes.extend_from_slice(&location.canonical_bytes());
    bytes.extend_from_slice(ownership.source_code().as_bytes());
    Ok(target(
        location,
        function,
        ownership,
        1,
        &bytes,
        format!(
            "resident-employer-{}-{}",
            county.geoid(),
            ownership.source_code()
        ),
        ResidentWorkplaceSource::ResidentEmployerFallback,
    ))
}

fn target(
    location: EconomicLocation,
    function: EconomicFunction,
    ownership: QcewOwnership,
    allocation_weight: u64,
    identity: &[u8],
    local_name: String,
    source: ResidentWorkplaceSource,
) -> ResidentWorkplaceTarget {
    let site_id = SiteId::from_bytes(sha256_of(identity));
    let mut pool = b"NationalStaffingPoolV1\0".to_vec();
    pool.extend_from_slice(&site_id.as_bytes());
    ResidentWorkplaceTarget {
        site_id,
        pool_id: StaffingPoolId::from_bytes(sha256_of(&pool)),
        workplace: StableElementKey::Node {
            scenario: NATIONAL_SCENARIO_ID.to_owned(),
            local_name,
        },
        location,
        function,
        ownership,
        allocation_weight,
        source,
    }
}
