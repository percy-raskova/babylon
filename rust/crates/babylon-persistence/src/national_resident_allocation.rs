//! Designed home-county workplace placement of source-controlled resident persons.
//! Each member is a counted household-residence/workplace group, never an individual agent.
//! This is opening authoring: durable employed/reserve stocks belong only to the graph.
mod households;

mod weights;

pub use weights::{ImputedWeight, PeerScope, WorkforceAllocationWeight};

#[path = "national_resident_allocation/allocation.rs"]
mod allocation;

pub(crate) use allocation::apportion;
pub use allocation::{
    allocate_home_county, AllocationError, AssignedResidentMember, AssignedResidentWorkplace,
    ResidentAttendanceMode, ResidentCountyAllocation, ResidentWorkplaceAllocation,
};
use allocation::{member, PendingAssignedWorkplace, PendingResidentMember, Result};

use crate::national_household_allocation::CountyHouseholdAllocation;
