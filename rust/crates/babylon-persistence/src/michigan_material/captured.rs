//! Explicit dependencies for source-only control reconstruction.
use super::{MichiganDefinesError, MichiganMaterialError, MichiganWorkforceSeed};
use crate::{
    michigan_cohorts::{build_cohorts_from_sources, MichiganCohorts},
    michigan_economy::MichiganEconomy,
    michigan_sectors::MichiganCountySectors,
};

pub(crate) struct MichiganObservedSources<'a> {
    pub(super) counties: &'a MichiganEconomy,
    pub(super) sectors: &'a MichiganCountySectors,
    pub(super) declarations: &'a str,
    pub(super) rules: &'a str,
    pub(super) artifacts: Vec<crate::economic_catalog::SourceArtifact>,
}
impl MichiganObservedSources<'_> {
    pub(super) fn cohorts(
        &self,
        workforce: &[MichiganWorkforceSeed],
    ) -> Result<MichiganCohorts, MichiganDefinesError> {
        build_cohorts_from_sources(self.counties, self.sectors, self.declarations, workforce)
            .map_err(|_| MichiganDefinesError::Material(MichiganMaterialError::ContentValue))
    }
}

impl MichiganObservedSources<'static> {
    pub(super) fn fresh() -> Result<Self, MichiganDefinesError> {
        Ok(Self {
            counties: crate::michigan_economy::michigan_economy()
                .map_err(|_| MichiganDefinesError::Material(MichiganMaterialError::SourceValue))?,
            sectors: crate::michigan_sectors::michigan_county_sectors()
                .map_err(|_| MichiganDefinesError::Material(MichiganMaterialError::SourceValue))?,
            declarations: include_str!(
                "../../../../../content/scenarios/michigan/cohort-declarations.bscn"
            ),
            rules: include_str!("../../../../../content/scenarios/michigan/material-cycle.bsl"),
            artifacts: common_sources(),
        })
    }
}

fn common_sources() -> Vec<crate::economic_catalog::SourceArtifact> {
    use crate::economic_catalog::{SourceArtifact, SourceArtifactKind as K};
    [
        (K::GraphDeclarations, include_bytes!("../../../../../content/scenarios/michigan/cohort-declarations.bscn").as_slice()),
        (K::Rules, include_bytes!("../../../../../content/scenarios/michigan/material-cycle.bsl").as_slice()),
        (K::MichiganCountyEvidence, include_bytes!("../../../../../src/babylon/data/reference/economy/qcew_county_economics_mi_2024.csv.gz").as_slice()),
        (K::MichiganSectorEvidence, include_bytes!("../../../../../src/babylon/data/reference/economy/qcew_county_sectors_mi_2024.csv.gz").as_slice()),
        (K::MichiganSectorSources, include_bytes!("../../../../../tools/qcew_county_economics_v1_source_manifest.json").as_slice()),
    ].into_iter().map(|(kind, bytes)| SourceArtifact::capture(kind, bytes.to_vec())).collect()
}
impl super::MichiganMaterialCatalog {
    pub(crate) fn captured_sources(&self) -> &[crate::economic_catalog::SourceArtifact] {
        &self.source_inputs
    }
    pub(super) fn replace_source(
        &mut self,
        kind: crate::economic_catalog::SourceArtifactKind,
        bytes: Vec<u8>,
    ) {
        self.source_inputs.retain(|source| source.kind() != kind);
        self.source_inputs
            .push(crate::economic_catalog::SourceArtifact::capture(
                kind, bytes,
            ));
        self.source_inputs
            .sort_by_key(crate::economic_catalog::SourceArtifact::kind);
    }
    pub(super) fn keep_sources(&self, mut result: Self) -> Self {
        result.source_inputs.clone_from(&self.source_inputs);
        result
    }
}

impl super::MichiganMaterialCatalog {
    /// Regenerate a control from the admitted source table, without filesystem or singleton access.
    pub(crate) fn from_captured_sources(
        input: &crate::economic_catalog::EconomicCatalogInput,
        counties: &MichiganEconomy,
        sectors: &MichiganCountySectors,
    ) -> Result<Self, MichiganDefinesError> {
        use crate::economic_catalog::SourceArtifactKind as K;
        let bytes = |kind| {
            input
                .sources
                .iter()
                .find(|row| row.kind() == kind)
                .map(crate::economic_catalog::SourceArtifact::bytes)
                .ok_or(MichiganDefinesError::Canonical)
        };
        let text =
            |kind| std::str::from_utf8(bytes(kind)?).map_err(|_| MichiganDefinesError::Canonical);
        let context = MichiganObservedSources {
            counties,
            sectors,
            declarations: text(K::GraphDeclarations)?,
            rules: text(K::Rules)?,
            artifacts: input.sources.clone(),
        };
        let experiment = input
            .sources
            .iter()
            .find(|row| row.kind() == K::MichiganExperiment);
        let preset = if experiment.is_some() {
            super::MichiganDeliveryPreset::Standard
        } else {
            super::MichiganDeliveryPreset::from_id(&input.preset_id)
                .ok_or(MichiganDefinesError::Canonical)?
        };
        let mut catalog = if preset.is_statewide() {
            captured_statewide(input, &context)?
        } else {
            let defines = if let Ok(raw) = bytes(K::MichiganDefines) {
                super::MichiganDefines::parse(
                    std::str::from_utf8(raw).map_err(|_| MichiganDefinesError::Canonical)?,
                )?
            } else {
                super::MichiganDefines::decode(bytes(K::DesignedPolicy)?)?
            };
            super::regional::compile_with_sources(
                defines,
                bytes(K::MichiganIndustryBaseline)?,
                bytes(K::MichiganRegionalTopology)?,
                &context,
            )?
        };
        if preset.is_maintenance() {
            catalog = super::maintenance::compile_with_sources(
                &catalog,
                bytes(K::MichiganMaintenanceIndustry)?,
                &context,
            )?;
        }
        if preset == super::MichiganDeliveryPreset::OrganizeInWayne {
            catalog = catalog.with_wayne_organizer_rules(context.rules)?;
            let id: [u8; 16] = bytes(K::OrganizerContext)?
                .try_into()
                .map_err(|_| MichiganDefinesError::Canonical)?;
            catalog = catalog.with_organizer_campaign(crate::identity::CampaignId::from_uuid(
                uuid::Uuid::from_bytes(id),
            ))?;
        } else {
            catalog = catalog.with_preset(preset)?;
        }
        if let Some(source) = experiment {
            let spec: crate::simulation_experiment::SimulationExperimentV1 =
                serde_json::from_slice(source.bytes())
                    .map_err(|_| MichiganDefinesError::Canonical)?;
            if spec
                .canonical_bytes()
                .map_err(|_| MichiganDefinesError::Canonical)?
                != source.bytes()
                || spec.profile.foundation_id() != input.preset_id
            {
                return Err(MichiganDefinesError::Canonical);
            }
            catalog = catalog.with_experiment(&spec)?;
        }
        if catalog.duration() != input.duration {
            return Err(MichiganDefinesError::Canonical);
        }
        Ok(catalog)
    }
}

fn captured_statewide(
    input: &crate::economic_catalog::EconomicCatalogInput,
    context: &MichiganObservedSources<'_>,
) -> Result<super::MichiganMaterialCatalog, MichiganDefinesError> {
    use crate::economic_catalog::SourceArtifactKind as K;
    let bytes = |kind| {
        input
            .sources
            .iter()
            .find(|row| row.kind() == kind)
            .map(crate::economic_catalog::SourceArtifact::bytes)
            .ok_or(MichiganDefinesError::Canonical)
    };
    let defines = std::str::from_utf8(bytes(K::MichiganDefines)?)
        .map_err(|_| MichiganDefinesError::Canonical)?;
    let (qualification, physical, overrides) = if input
        .sources
        .iter()
        .any(|row| row.kind() == K::MichiganStatewideManifest)
    {
        super::source::decode_statewide_sources(
            defines,
            bytes(K::MichiganStatewideManifest)?,
            bytes(K::MichiganQualification)?,
            bytes(K::MichiganPhysicalNetwork)?,
        )?
    } else {
        let physical = canonical_json(bytes(K::MichiganPhysicalNetworkJson)?)?;
        let overrides = canonical_json(bytes(K::MichiganControlOverrides)?)?;
        (
            bytes(K::MichiganQualificationJson)?.to_vec(),
            physical,
            overrides,
        )
    };
    super::statewide::compile_with_sources(
        defines,
        &qualification,
        physical,
        overrides,
        bytes(K::MichiganCommodityRoster)?,
        context,
    )
}
fn canonical_json<T: serde::de::DeserializeOwned + serde::Serialize>(
    bytes: &[u8],
) -> Result<T, MichiganDefinesError> {
    let value: T = serde_json::from_slice(bytes).map_err(|_| MichiganDefinesError::Canonical)?;
    if serde_json::to_vec(&value).map_err(|_| MichiganDefinesError::Canonical)? != bytes {
        return Err(MichiganDefinesError::Canonical);
    }
    Ok(value)
}
