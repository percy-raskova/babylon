//! Pure conserved staffing with one preceding unretained work request.
//!
//! Requests are explicit exact labor-time, not inferred headcount or wages.
//! This module does not derive requests, allocate production, or publish a tick.

mod members;
mod model;
mod transition;

pub(crate) use members::proportional_shares;
pub use members::{
    distribute_staffing_members, MemberLaborCapacityRow, StaffingMemberBinding, StaffingMemberId,
    StaffingMemberReceipt, StaffingMemberState, MAX_STAFFING_MEMBERS,
};

pub use model::{
    StaffingError, StaffingPolicy, StaffingPoolBinding, StaffingPoolId, StaffingPoolState,
    StaffingReceipt, StaffingState, StaffingTransition, StaffingWorkRequest, StaffingWorkSource,
};
pub use transition::advance_staffing;

#[cfg(test)]
mod tests;
