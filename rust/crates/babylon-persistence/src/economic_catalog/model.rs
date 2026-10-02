//! Immutable authoring inputs for one shared economic campaign compiler.
//!
//! These rows describe opening content. They are never a second mutable world.
//! Source observations bind identity and scale; recipe and opening assignments
//! require their captured Designed policy evidence.

use crate::{michigan_sectors::MichiganSectorCode, national_cohorts::CohortKey};
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::{
    currency::Currency, economic_identity::EconomicFunction, economic_location::EconomicLocation,
    geography::CountyGeoid,
};
use babylon_material_circuit::{
    CorridorId, FinalDemandPrincipalId, GoodId, HouseholdNeedBasis, HouseholdPurchasePolicy,
    LogisticsNodeId, MerchantRole, ProcessId, ReplenishmentPolicy, RouteStage, RouteStageCapacity,
    SellerOffer, ServiceConnection, ServiceInputPolicy, SharedCapacitySupply, SiteId,
    SupplierRoute, UnitId,
};

/// A catalog-local recipe identity, unique inside the captured template table.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct RecipeTemplateId(pub u16);

/// A catalog-local household need profile, independent of resident account identity.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct HouseholdTemplateId(pub u16);

/// One exact native quantity; the good and unit must exist in the commodity table.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CommodityAmount {
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub quantity: u64,
}

/// Required labor time per batch, never an inference of persons from workplace jobs.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LaborRequirement {
    pub unit_id: UnitId,
    pub hours_per_batch: u64,
}

/// A shared physical recipe. Site assignments instantiate its process identity.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RecipeTemplate {
    pub id: RecipeTemplateId,
    pub output: CommodityAmount,
    pub inputs: Vec<CommodityAmount>,
    pub labor: Option<LaborRequirement>,
}

/// One process assignment and its first production plan. Capacity has one
/// separate owner in `CatalogCapacity`, including captured nameplate controls.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ProcessInstallation {
    pub process_id: ProcessId,
    pub recipe: RecipeTemplateId,
    pub planned_batches: u64,
    pub output_buffer: u64,
}

/// Exact opening stock and its explicit assigned carrying amount.
/// The captured policy establishes the amount; it is not an observed past payment.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OpeningCommodityStock {
    pub amount: CommodityAmount,
    pub total_cost: Currency,
}

/// A preserved source identity or an explicit Designed actor assignment.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum EconomicSiteSource {
    Qcew(CohortKey),
    /// Observed context shared by explicitly Designed Michigan control worksites.
    /// It is not a national function/ownership cohort or a duplicated observation.
    MichiganSector {
        county_geoid: CountyGeoid,
        sector_code: MichiganSectorCode,
    },
    Designed {
        key: String,
    },
}

/// Staffed distribution of one native commodity unit.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HandlingRequirement {
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub hours_per_unit: u64,
}

/// Circulation role; its capacity principal is supplied in the shared capacity table.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct MerchantSeed {
    pub role: MerchantRole,
    pub capacity_id: CorridorId,
    pub labor_unit_id: UnitId,
    pub handling: Vec<HandlingRequirement>,
}

/// One admitted workplace or Designed provider, bound to common geography.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EconomicSiteSeed {
    pub site_id: SiteId,
    /// Readable captured-source cohort description or authored Designed provider label.
    pub label: String,
    pub subject: StableElementKey,
    pub location: EconomicLocation,
    pub logistics_node_id: LogisticsNodeId,
    pub source: EconomicSiteSource,
    /// Explicit technical function; validated against QCEW mapping when source-derived.
    pub function: EconomicFunction,
    pub processes: Vec<ProcessInstallation>,
    pub merchant: Option<MerchantSeed>,
    pub opening_stock: Vec<OpeningCommodityStock>,
    pub opening_cash: Currency,
}

/// Person and household bases remain explicit and are evaluated by the engine.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HouseholdNeedCoefficient {
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub basis: HouseholdNeedBasis,
    pub units_per_basis: u64,
}

/// Shared needs; purchases, production and consumption remain distinct operations.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HouseholdTemplate {
    pub id: HouseholdTemplateId,
    pub needs: Vec<HouseholdNeedCoefficient>,
}

/// A resident principal, with persons and households independent of workplace jobs.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EconomicHouseholdSeed {
    pub kind: babylon_material_circuit::HouseholdKind,
    pub principal_id: FinalDemandPrincipalId,
    pub subject: StableElementKey,
    pub location: EconomicLocation,
    pub persons: u64,
    pub households: u64,
    pub template: HouseholdTemplateId,
    pub opening_stock: Vec<OpeningCommodityStock>,
    pub opening_cash: Currency,
}

/// An explicit physical accounting control or a funded monetary economy.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CatalogAccounting {
    PhysicalControl,
    Monetary,
}

/// Opening policies reuse the engine's exact types without retaining dynamic cursors.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CatalogPolicies {
    pub offers: Vec<SellerOffer>,
    pub replenishment: Vec<ReplenishmentPolicy>,
    pub household_purchases: Vec<HouseholdPurchasePolicy>,
    pub service_inputs: Vec<ServiceInputPolicy>,
    pub service_connections: Vec<ServiceConnection>,
}

/// Directed route authority and finite shared installed throughput, captured once.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CatalogLogistics {
    pub supplier_routes: Vec<SupplierRoute>,
    pub route_stages: Vec<RouteStage>,
    pub memberships: Vec<RouteStageCapacity>,
    pub shared_capacity: Vec<SharedCapacitySupply>,
}

/// One exact opening member principal. After initialization, its employed and
/// reserve counts live only on the bound `SOCIAL_CLASS` graph node.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResidentStaffingMemberSeed {
    pub subject: StableElementKey,
    pub member: babylon_material_circuit::StaffingMemberBinding,
    pub employed: u64,
    pub reserve: u64,
}

/// One BUSINESS workplace and its disjoint resident member assignments.
/// The workplace graph node owns prior-request memory after initialization.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResidentStaffingPoolSeed {
    pub workplace: StableElementKey,
    pub pool: babylon_material_circuit::StaffingPoolBinding,
    pub previous_unretained_hours: u64,
    pub members: Vec<ResidentStaffingMemberSeed>,
}

/// Explicit finite supply controls remain available beside installed rolling
/// supply. Missing finite dates supply nothing; they never become rolling supply.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum CatalogCapacity {
    Rolling(babylon_material_circuit::RollingProcessSupply),
    Finite {
        process: Vec<babylon_material_circuit::CapacityRow>,
        freight: Vec<babylon_material_circuit::CorridorCapacity>,
    },
}

/// Opening physical orders are separate from recurring purchase policies.
/// Every counter must describe an unshipped, unrealized opening obligation.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CatalogOpeningOrders {
    /// Explicit finite-control buyers without an invented recurring household count.
    /// Counted household principals are instead derived from the household seed table.
    pub principals: Vec<babylon_material_circuit::FinalDemandPrincipal>,
    pub goods: Vec<babylon_material_circuit::OrderRow>,
    pub final_demand: Vec<babylon_material_circuit::FinalDemandOrder>,
}

/// The currently executable explicitly bound maintenance relation, if authored.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CatalogMaintenance {
    pub binding: babylon_material_circuit::MaintenanceBinding,
    pub opening_enabled_batches: u64,
}

/// Output of a Designed recipe/allocation generator. This is initialization
/// content, without runtime freight, payment, consumption or staffing cursors.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EconomicOpening {
    pub commodity_labels: Vec<CommodityLabel>,
    pub commodities: Vec<babylon_material_circuit::CommodityDefinition>,
    pub recipes: Vec<RecipeTemplate>,
    pub household_templates: Vec<HouseholdTemplate>,
    pub sites: Vec<EconomicSiteSeed>,
    pub households: Vec<EconomicHouseholdSeed>,
    pub staffing: Vec<ResidentStaffingPoolSeed>,
    pub employment: Vec<babylon_material_circuit::EmploymentTerms>,
    pub accounting: CatalogAccounting,
    /// Organization/public opening cash only; site and household seeds own theirs.
    pub institutional_cash: Vec<babylon_material_circuit::CashAccount>,
    pub institutions: babylon_material_circuit::FinancialInstitutions,
    pub equity: Vec<babylon_material_circuit::EquityCarryingValue>,
    /// Exact carrying amounts for installed equipment and pending installation.
    pub equipment: Vec<babylon_material_circuit::EquipmentCarryingValue>,
    pub capacity: CatalogCapacity,
    pub policies: CatalogPolicies,
    pub logistics: CatalogLogistics,
    pub orders: CatalogOpeningOrders,
    pub maintenance: Option<CatalogMaintenance>,
}

/// Fixed geographic coverage, separate from mutable economic stocks.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CatalogGeography {
    /// Full captured 2024 county roster, with no implied fine H3 coverage.
    NationalCounties,
    /// The full county roster plus an explicitly captured Michigan local detail.
    NationalCountiesWithMichiganDetail,
    /// Intentional Michigan control geography, imported through the same runtime.
    MichiganControl,
}

/// Complete immutable input to current catalog admission. Rules, declaration
/// text, policy and reference blobs appear once in the singular source table.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EconomicCatalogInput {
    pub scenario_id: String,
    pub preset_id: String,
    pub duration: babylon_kernel::clock::CampaignDuration,
    pub sources: Vec<super::sources::SourceArtifact>,
    pub geography: CatalogGeography,
    pub organizer: Option<babylon_practice_contract::OrganizerConfig>,
}

/// Captured user-facing commodity identity; labels never come from guessing a hash.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CommodityLabel {
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub key: String,
    pub label: String,
    pub unit_label: String,
}
