//! Captured productive instruments, finite installation work and purchase intent.
use crate::{GoodId, ProcessId, SiteId, UnitId};
use babylon_kernel::currency::Currency;

crate::model::identity_type!(EquipmentDefinitionId);
crate::model::identity_type!(EquipmentCohortId);
crate::model::identity_type!(InstallationId);

/// A deliberately fixed control or the actual equipment owner, never both.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RollingProcessSupply {
    CapturedNameplate(Vec<crate::InstalledProcessCapacity>),
    Equipment(Box<ProductiveEquipment>),
}

/// All numeric coefficients are captured Designed content, not engine defaults.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EquipmentDefinition {
    pub id: EquipmentDefinitionId,
    pub equipment_good_id: GoodId,
    pub equipment_unit_id: UnitId,
    pub batches_per_unit_per_period: u64,
    pub service_batches_per_unit: u64,
    pub installation_labor_unit_id: UnitId,
    pub installation_hours_per_unit: u64,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EquipmentBinding {
    pub process_id: ProcessId,
    pub site_id: SiteId,
    pub definition_id: EquipmentDefinitionId,
}
/// Initial installation uses explicit storable complementary materials.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstallationInput {
    pub definition_id: EquipmentDefinitionId,
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub quantity_per_equipment_unit: u64,
}
/// A homogeneous cohort with finite remaining productive use.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstalledEquipmentCohort {
    pub id: EquipmentCohortId,
    pub process_id: ProcessId,
    pub units: u64,
    pub remaining_service_batches: u64,
    pub usable_from_period: u64,
}
/// Equipment/materials have entered WIP; only actual work reduces remaining hours.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PendingInstallation {
    pub id: InstallationId,
    pub process_id: ProcessId,
    pub units: u64,
    pub started_period: u64,
    pub remaining_hours: u64,
}
/// Explicit desired installed position, independent of purchase admission ceilings.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InstallationTarget {
    FixedUnits(u64),
    ProductionPlan { replacement_units: u64 },
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstallationPolicy {
    pub process_id: ProcessId,
    pub target: InstallationTarget,
    pub maximum_started_units_per_period: u64,
    pub maximum_hours_per_period: u64,
}
/// Intent does not establish admitted orders, installed equipment, or output.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InvestmentPolicy {
    pub process_id: ProcessId,
    pub supplier_site_id: SiteId,
    pub replacement_target_units: u64,
    /// Upper target for new purchase decisions, not an installation ban on owned stock.
    pub maximum_installed_units: u64,
    pub maximum_purchase_per_period: u64,
    pub expansion_earnings_fraction_bps: u16,
    pub cash_floor: Currency,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProductiveEquipment {
    pub definitions: Vec<EquipmentDefinition>,
    pub bindings: Vec<EquipmentBinding>,
    pub installation_inputs: Vec<InstallationInput>,
    pub cohorts: Vec<InstalledEquipmentCohort>,
    pub pending: Vec<PendingInstallation>,
    pub installation_policies: Vec<InstallationPolicy>,
    pub investment_policies: Vec<InvestmentPolicy>,
}

/// One explicit carrying row per physical asset, including an explicit zero cost.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum EquipmentAssetId {
    Installation(InstallationId),
    Installed(EquipmentCohortId),
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EquipmentCarryingValue {
    pub asset: EquipmentAssetId,
    pub owner: SiteId,
    pub amount: Currency,
}
