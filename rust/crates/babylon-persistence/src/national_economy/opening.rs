//! Regenerate one national opening from supplied source captures and Designed policy.
//! This module owns no mutable runtime or filesystem fallback.

mod actors;

pub mod aid;

mod equipment;

mod external;

mod financial;

mod household_time;

mod markets;

mod routes;

mod templates;

#[path = "opening/build.rs"]
mod build;

#[allow(unused_imports)]
pub(super) use build::FUNCTIONS;
#[allow(unused_imports)]
use build::{amount, quantity, sum_amount, ActorContext, Builder, Result};
pub use build::{
    build_national_opening, NationalOpening, NationalOpeningError, NationalOpeningPolicy,
};

#[allow(unused_imports)]
use super::{GameCommodity, NationalGamePolicy};
#[allow(unused_imports)]
use crate::{
    economic_catalog::{
        CatalogAccounting, CatalogCapacity, CatalogLogistics, CatalogOpeningOrders,
        CatalogPolicies, EconomicOpening, EconomicSiteSeed,
    },
    national_cohorts::NationalCohortReference,
    national_counties::NationalCountyReference,
    national_household_allocation::{
        allocate_households, HouseholdAllocationError, HouseholdBudgetKey,
    },
    national_household_time_allocation::allocate_household_time,
    national_households::NationalHouseholdReference,
    national_resident_allocation::{allocate_home_county, AllocationError},
    national_resident_workforce::NationalResidentWorkforceReference,
    national_transport::NationalTransportReference,
    world_reference::WorldReference,
};
#[allow(unused_imports)]
use babylon_kernel::{
    currency::Currency,
    economic_identity::{EconomicFunction, QcewOwnership},
    economic_location::EconomicLocation,
};
#[allow(unused_imports)]
use babylon_material_circuit::{
    FinancialInstitutions, GoodId, LogisticsNodeId, ProcessId, ReplenishmentPolicy,
    RollingProcessSupply, SellerOffer, SiteId, UnitId,
};
#[allow(unused_imports)]
use std::collections::BTreeMap;
