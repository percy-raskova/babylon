//! What the rules of ADR314 did at one close.

use crate::{FinalDemandPrincipalId, StaffingMemberId, StaffingPoolId};

/// What the rules of ADR314 did at one close, in the order they acted.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum AdjustmentReceipt {
    /// Persons moved from one workplace's people looking for work to another that needed hands (A14).
    PlaceMove(PlaceMoveReceipt),
}

/// Persons of one household who left the people looking for work at one workplace of their place and were
/// taken on at another.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlaceMoveReceipt {
    /// The period whose staffing moved them.
    pub period: u64,
    /// The pool that took them on.
    pub host_pool: StaffingPoolId,
    /// The host's member of their household.
    pub host_member: StaffingMemberId,
    /// The pool they left.
    pub from_pool: StaffingPoolId,
    /// The member of their household they left.
    pub from_member: StaffingMemberId,
    /// Their household.
    pub household_id: FinalDemandPrincipalId,
    /// How many persons.
    pub persons: u64,
    /// `None`: no record of layoffs covered them. `Some(age)`: from the cohort laid off `age` periods before.
    pub covered_age: Option<u8>,
}
