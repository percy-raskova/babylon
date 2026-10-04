//! Explicit Michigan control choices imported into the common captured catalog.

use crate::{
    economic_content::EconomicContentAdmission,
    material_runtime::MaterialRuntimeFoundation,
    michigan_cohorts::MICHIGAN_COHORT_SCENARIO,
    michigan_material::{MichiganDeliveryPreset, MichiganMaterialCatalog},
};

/// Graph content revisions are separate from the logical delivery choice.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MichiganContentPreset {
    OrganizeInWayne,
    FourWeekStandard,
    FourWeekDelayed,
    SharedFreightAmple,
    SharedFreightConstrained,
    StatewideBaseline,
    StatewideFreightConstraint,
    StatewidePackagingShortage,
    StatewideBoth,
    StatewideMaintenanceBaseline,
    StatewideMaintenanceLaborShortage,
    StatewideMaintenancePartsShortage,
    StatewideMaintenanceBoth,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum MichiganContentError {
    MaterialSource,
    Foundation,
}
impl std::fmt::Display for MichiganContentError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "Michigan content admission refused: {self:?}")
    }
}
impl std::error::Error for MichiganContentError {}

pub const MICHIGAN_CONTENT_PRESETS: [MichiganContentPreset; 13] = [
    MichiganContentPreset::OrganizeInWayne,
    MichiganContentPreset::FourWeekStandard,
    MichiganContentPreset::FourWeekDelayed,
    MichiganContentPreset::SharedFreightAmple,
    MichiganContentPreset::SharedFreightConstrained,
    MichiganContentPreset::StatewideBaseline,
    MichiganContentPreset::StatewideFreightConstraint,
    MichiganContentPreset::StatewidePackagingShortage,
    MichiganContentPreset::StatewideBoth,
    MichiganContentPreset::StatewideMaintenanceBaseline,
    MichiganContentPreset::StatewideMaintenanceLaborShortage,
    MichiganContentPreset::StatewideMaintenancePartsShortage,
    MichiganContentPreset::StatewideMaintenanceBoth,
];

impl MichiganContentPreset {
    #[must_use]
    pub const fn new_campaign(delivery: MichiganDeliveryPreset) -> Self {
        match delivery {
            MichiganDeliveryPreset::OrganizeInWayne => Self::OrganizeInWayne,
            MichiganDeliveryPreset::Standard => Self::FourWeekStandard,
            MichiganDeliveryPreset::Delayed => Self::FourWeekDelayed,
            MichiganDeliveryPreset::SharedFreightAmple => Self::SharedFreightAmple,
            MichiganDeliveryPreset::SharedFreightConstrained => Self::SharedFreightConstrained,
            MichiganDeliveryPreset::StatewideBaseline => Self::StatewideBaseline,
            MichiganDeliveryPreset::StatewideFreightConstraint => Self::StatewideFreightConstraint,
            MichiganDeliveryPreset::StatewidePackagingShortage => Self::StatewidePackagingShortage,
            MichiganDeliveryPreset::StatewideBoth => Self::StatewideBoth,
            MichiganDeliveryPreset::StatewideMaintenanceBaseline => {
                Self::StatewideMaintenanceBaseline
            }
            MichiganDeliveryPreset::StatewideMaintenanceLaborShortage => {
                Self::StatewideMaintenanceLaborShortage
            }
            MichiganDeliveryPreset::StatewideMaintenancePartsShortage => {
                Self::StatewideMaintenancePartsShortage
            }
            MichiganDeliveryPreset::StatewideMaintenanceBoth => Self::StatewideMaintenanceBoth,
        }
    }
    #[must_use]
    pub const fn id(self) -> &'static str {
        self.delivery().id()
    }
    #[must_use]
    pub fn from_id(id: &str) -> Option<Self> {
        MICHIGAN_CONTENT_PRESETS
            .into_iter()
            .find(|preset| preset.id() == id)
    }
    #[must_use]
    pub const fn delivery(self) -> MichiganDeliveryPreset {
        match self {
            Self::OrganizeInWayne => MichiganDeliveryPreset::OrganizeInWayne,
            Self::FourWeekStandard => MichiganDeliveryPreset::Standard,
            Self::FourWeekDelayed => MichiganDeliveryPreset::Delayed,
            Self::SharedFreightAmple => MichiganDeliveryPreset::SharedFreightAmple,
            Self::SharedFreightConstrained => MichiganDeliveryPreset::SharedFreightConstrained,
            Self::StatewideBaseline => MichiganDeliveryPreset::StatewideBaseline,
            Self::StatewideFreightConstraint => MichiganDeliveryPreset::StatewideFreightConstraint,
            Self::StatewidePackagingShortage => MichiganDeliveryPreset::StatewidePackagingShortage,
            Self::StatewideBoth => MichiganDeliveryPreset::StatewideBoth,
            Self::StatewideMaintenanceBaseline => {
                MichiganDeliveryPreset::StatewideMaintenanceBaseline
            }
            Self::StatewideMaintenanceLaborShortage => {
                MichiganDeliveryPreset::StatewideMaintenanceLaborShortage
            }
            Self::StatewideMaintenancePartsShortage => {
                MichiganDeliveryPreset::StatewideMaintenancePartsShortage
            }
            Self::StatewideMaintenanceBoth => MichiganDeliveryPreset::StatewideMaintenanceBoth,
        }
    }
    #[must_use]
    pub const fn scenario(self) -> &'static str {
        MICHIGAN_COHORT_SCENARIO
    }
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::OrganizeInWayne => "Organize in Wayne",
            Self::FourWeekStandard => "Michigan: standard delivery (four active cohorts)",
            Self::FourWeekDelayed => "Michigan: delayed delivery (four active cohorts)",
            Self::SharedFreightAmple => "Shared freight — ample",
            Self::SharedFreightConstrained => "Shared freight — constrained",
            Self::StatewideBaseline => "Statewide Michigan — baseline",
            Self::StatewideFreightConstraint => "Statewide Michigan — freight constraint",
            Self::StatewidePackagingShortage => "Statewide Michigan — packaging shortage",
            Self::StatewideBoth => "Statewide Michigan — both constraints",
            Self::StatewideMaintenanceBaseline => "Wayne maintenance — baseline",
            Self::StatewideMaintenanceLaborShortage => "Wayne maintenance — labor shortage",
            Self::StatewideMaintenancePartsShortage => "Wayne maintenance — parts shortage",
            Self::StatewideMaintenanceBoth => "Wayne maintenance — both constraints",
        }
    }
    /// # Errors
    /// Refuses any changed source or foundation construction failure.
    pub fn admitted(
        self,
        catalog: &MichiganMaterialCatalog,
    ) -> Result<EconomicContentAdmission, MichiganContentError> {
        EconomicContentAdmission::from_foundation(self.build_foundation(catalog)?)
            .map_err(|_| MichiganContentError::Foundation)
    }
    /// Create a campaign from explicit, already validated numeric parameters.
    /// # Errors
    /// Refuses invalid material composition or observed source drift.
    pub fn create_foundation(
        self,
        catalog: &MichiganMaterialCatalog,
    ) -> Result<MaterialRuntimeFoundation, MichiganContentError> {
        self.build_foundation(catalog)
    }
    /// Create a new campaign with explicitly captured player authority.
    /// # Errors
    /// Refuses invalid authored organizer content or material foundation.
    pub fn create_foundation_for_campaign(
        &self,
        catalog: &MichiganMaterialCatalog,
        campaign: crate::identity::CampaignId,
    ) -> Result<MaterialRuntimeFoundation, MichiganContentError> {
        let catalog = catalog
            .with_organizer_campaign(campaign)
            .map_err(|_| MichiganContentError::Foundation)?;
        self.build_foundation(&catalog)
    }
    fn build_foundation(
        self,
        catalog: &MichiganMaterialCatalog,
    ) -> Result<MaterialRuntimeFoundation, MichiganContentError> {
        if catalog.experiment().is_some() {
            return Err(MichiganContentError::Foundation);
        }
        let selected = catalog
            .with_preset(self.delivery())
            .map_err(|_| MichiganContentError::MaterialSource)?;
        let captured = crate::economic_catalog::CapturedEconomicCatalog::from_michigan(&selected)
            .map_err(|_| MichiganContentError::MaterialSource)?;
        captured
            .create_foundation(
                babylon_kernel::replay::ReplaySessionId::try_from(
                    crate::michigan_cohorts::MICHIGAN_COHORT_SESSION,
                )
                .map_err(|_| MichiganContentError::Foundation)?,
                babylon_kernel::replay::ReplaySeed::new(319),
            )
            .map_err(|_| MichiganContentError::Foundation)
    }
}

#[cfg(test)]
mod tests;
