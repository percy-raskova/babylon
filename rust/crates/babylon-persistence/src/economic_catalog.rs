//! Shared immutable initialization inputs for the captured economic campaign.
//!
//! Source observations, Designed policy and regenerated opening assignments are
//! distinct. These input rows never own a second mutable material world.

mod capture;
mod codec;
mod compile;
mod control;
mod error;
mod foundation;
mod graph;
mod michigan;
mod model;
mod national;
mod preset;

pub use preset::national_catalog_input;
mod session;
mod sources;
mod view;

pub use model::{
    CatalogAccounting, CatalogCapacity, CatalogGeography, CatalogLogistics, CatalogMaintenance,
    CatalogOpeningOrders, CatalogPolicies, CommodityAmount, CommodityLabel, EconomicCatalogInput,
    EconomicHouseholdSeed, EconomicOpening, EconomicSiteSeed, EconomicSiteSource,
    HandlingRequirement, HouseholdNeedCoefficient, HouseholdTemplate, HouseholdTemplateId,
    LaborRequirement, MerchantSeed, OpeningCommodityStock, ProcessInstallation, RecipeTemplate,
    RecipeTemplateId, ResidentStaffingMemberSeed, ResidentStaffingPoolSeed,
};
pub use sources::{SourceArtifact, SourceArtifactKind};

pub use view::{EconomicProjectionView, EconomicSourceView};

pub use error::EconomicCatalogError;

pub use compile::CompiledEconomicOpening;
pub use michigan::import_michigan_opening;

pub use capture::CapturedEconomicCatalog;
