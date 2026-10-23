//! Designed home-county workplace placement of source-controlled resident persons.
//! Each member is a counted household-residence/workplace group, never an individual agent.
//! This is opening authoring: durable employed/reserve stocks belong only to the graph.
mod households;

mod weights;

pub use weights::{ImputedWeight, PeerScope, WorkforceAllocationWeight};

#[path = "national_resident_allocation/allocation.rs"]
mod allocation;

#[allow(unused_imports)]
pub(crate) use allocation::apportion;
#[allow(unused_imports)]
use allocation::{
    add_fallback, allocate_employees, assign_county, base32, county_controls, member,
    validate_totals, PendingAssignedWorkplace, PendingResidentMember, PendingWorkplace, Result,
};
pub use allocation::{
    allocate_home_county, AllocationError, AssignedResidentMember, AssignedResidentWorkplace,
    ResidentAttendanceMode, ResidentCountyAllocation, ResidentWorkplaceAllocation,
};

#[allow(unused_imports)]
use crate::{
    economic_catalog::{ResidentStaffingMemberSeed, ResidentStaffingPoolSeed},
    national_cohorts::NationalCohortReference,
    national_counties::NationalCountyReference,
    national_economy::{
        household_enterprise_target, resident_employer_target, source_workplace_target,
        NationalGamePolicy, ResidentWorkplaceTarget,
    },
    national_household_allocation::{CountyHouseholdAllocation, NationalHouseholdAllocation},
    national_household_refinement::NationalHouseholdLeafRoster,
    national_resident_workforce::{NationalResidentWorkforceReference, WorkerClass},
};
#[allow(unused_imports)]
use babylon_graph::stable_element::StableElementKey;
#[allow(unused_imports)]
use babylon_kernel::{
    content_digest::sha256_of, economic_identity::QcewOwnership,
    economic_location::EconomicLocation, geography::CountyGeoid,
};
#[allow(unused_imports)]
use babylon_material_circuit::{
    StaffingMemberBinding, StaffingMemberId, StaffingPolicy, StaffingPoolBinding,
    StaffingWorkSource, UnitId, MAX_MATERIAL_CIRCUIT_ROWS, MAX_STAFFING_MEMBERS,
};
#[allow(unused_imports)]
use std::collections::BTreeMap;
