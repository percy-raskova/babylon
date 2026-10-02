//! Explicit Michigan importer authority. No current reference file is reopened.
use super::{
    capture::{source, source_coverage},
    EconomicCatalogError, EconomicCatalogInput, EconomicOpening, EconomicSourceView,
    SourceArtifactKind as K,
};
use crate::{
    michigan_economy::MichiganEconomy,
    michigan_material::{MichiganDeliveryPreset, MichiganMaterialCatalog},
    michigan_sectors::MichiganCountySectors,
};
type Result<T> = std::result::Result<T, EconomicCatalogError>;

pub(super) struct MichiganSources {
    pub(super) catalog: MichiganMaterialCatalog,
    pub(super) counties: MichiganEconomy,
    sectors: MichiganCountySectors,
}
impl MichiganSources {
    pub(super) fn admit(input: &mut EconomicCatalogInput) -> Result<(Self, EconomicOpening)> {
        coverage(input)?;
        let counties = MichiganEconomy::decode_captured(source(input, K::MichiganCountyEvidence)?)
            .map_err(|_| EconomicCatalogError::Source(K::MichiganCountyEvidence))?;
        let sectors = MichiganCountySectors::decode_captured(
            source(input, K::MichiganSectorEvidence)?,
            source(input, K::MichiganSectorSources)?,
        )
        .map_err(|_| EconomicCatalogError::Source(K::MichiganSectorEvidence))?;
        let catalog = MichiganMaterialCatalog::from_captured_sources(input, &counties, &sectors)
            .map_err(|_| EconomicCatalogError::Opening("Michigan source regeneration"))?;
        if input
            .organizer
            .as_ref()
            .is_some_and(|expected| Some(expected) != catalog.organizer_config())
        {
            return Err(EconomicCatalogError::Opening("organizer source mismatch"));
        }
        input.organizer = catalog.organizer_config().cloned();
        let opening = super::michigan::import_michigan_opening(&catalog)?;
        Ok((
            Self {
                catalog,
                counties,
                sectors,
            },
            opening,
        ))
    }
    pub(super) fn view(&self) -> EconomicSourceView<'_> {
        EconomicSourceView::MichiganControl {
            catalog: &self.catalog,
            counties: &self.counties,
            sectors: &self.sectors,
        }
    }
}
fn coverage(input: &EconomicCatalogInput) -> Result<()> {
    let has = |kind| input.sources.iter().any(|row| row.kind() == kind);
    let experiment = has(K::MichiganExperiment);
    let preset = if experiment {
        MichiganDeliveryPreset::Standard
    } else {
        MichiganDeliveryPreset::from_id(&input.preset_id).ok_or(EconomicCatalogError::Identity)?
    };
    let mut required = vec![
        K::GraphDeclarations,
        K::Rules,
        K::MichiganCountyEvidence,
        K::MichiganSectorEvidence,
        K::MichiganSectorSources,
        K::MichiganDynamicHexes,
        K::MichiganSpatialProducts,
    ];
    if preset.is_statewide() {
        required.extend([K::MichiganDefines, K::MichiganCommodityRoster]);
        if has(K::MichiganStatewideManifest) {
            required.extend([
                K::MichiganStatewideManifest,
                K::MichiganQualification,
                K::MichiganPhysicalNetwork,
            ]);
        } else {
            required.extend([
                K::MichiganQualificationJson,
                K::MichiganPhysicalNetworkJson,
                K::MichiganControlOverrides,
            ]);
        }
    } else {
        required.extend([K::MichiganIndustryBaseline, K::MichiganRegionalTopology]);
        required.push(if has(K::MichiganDefines) {
            K::MichiganDefines
        } else {
            K::DesignedPolicy
        });
    }
    if preset.is_maintenance() {
        required.push(K::MichiganMaintenanceIndustry);
    }
    if preset == MichiganDeliveryPreset::OrganizeInWayne {
        required.push(K::OrganizerContext);
    }
    if experiment {
        required.push(K::MichiganExperiment);
    }
    source_coverage(input, &required, &[])
}
