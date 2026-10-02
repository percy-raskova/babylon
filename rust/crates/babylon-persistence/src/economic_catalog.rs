//! Shared immutable initialization inputs for the captured economic campaign.
//!
//! Source observations, Designed policy and regenerated opening assignments are
//! distinct. These input rows never own a second mutable material world.

mod model;
mod sources;

pub use model::{
    CatalogAccounting, CatalogCapacity, CatalogGeography, CatalogLogistics, CatalogMaintenance,
    CatalogOpeningOrders, CatalogPolicies, CommodityAmount, CommodityLabel, EconomicCatalogInput,
    EconomicHouseholdSeed, EconomicOpening, EconomicSiteSeed, EconomicSiteSource,
    HandlingRequirement, HouseholdNeedCoefficient, HouseholdTemplate, HouseholdTemplateId,
    LaborRequirement, MerchantSeed, OpeningCommodityStock, ProcessInstallation, RecipeTemplate,
    RecipeTemplateId, ResidentStaffingMemberSeed, ResidentStaffingPoolSeed,
};
pub use sources::{SourceArtifact, SourceArtifactKind};
