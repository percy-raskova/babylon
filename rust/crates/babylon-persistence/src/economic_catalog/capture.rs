//! Source-only durable capture and deterministic importer selection.
use super::{
    codec, national::NationalSources, CatalogGeography, EconomicCatalogError, EconomicCatalogInput,
    EconomicOpening, EconomicProjectionView, SourceArtifact, SourceArtifactKind,
};
use babylon_kernel::{clock::CampaignDuration, content_digest::sha256_of};
use std::collections::BTreeSet;

type Result<T> = std::result::Result<T, EconomicCatalogError>;

pub(super) enum CapturedSources {
    National(Box<NationalSources>),
    Michigan(Box<super::control::MichiganSources>),
}
/// One durable source table and current compiler pin. The opening is regenerated
/// in memory; no derived per-site or global state is encoded inside the catalog.
pub struct CapturedEconomicCatalog {
    pub(super) input: EconomicCatalogInput,
    pub(super) sources: CapturedSources,
    pub(super) opening: EconomicOpening,
    pub(super) bytes: Vec<u8>,
    pub(super) digest: [u8; 32],
    pub(super) local_detail: Option<babylon_tick::h3_runtime::MichiganDynamicHexFoundation>,
    spatial_detail: Option<crate::spatial_reference_products::SpatialReferenceProducts>,
}
impl std::fmt::Debug for CapturedEconomicCatalog {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("CapturedEconomicCatalog")
            .field("scenario", &self.input.scenario_id)
            .field("preset", &self.input.preset_id)
            .field("compiler", &self.compiler_version())
            .field("digest", &self.digest)
            .finish_non_exhaustive()
    }
}
impl PartialEq for CapturedEconomicCatalog {
    fn eq(&self, other: &Self) -> bool {
        self.bytes == other.bytes
    }
}
impl Eq for CapturedEconomicCatalog {}
impl CapturedEconomicCatalog {
    /// Admit all sources, regenerate once, and optionally compare supplied inputs
    /// against the complete deterministic result before accepting authority.
    /// # Errors
    /// Refuses incomplete/malformed evidence, incompatible compiler scope or a
    /// supplied opening differing from the source-derived initialization.
    pub fn capture(
        mut input: EconomicCatalogInput,
        expected: Option<&EconomicOpening>,
    ) -> Result<Self> {
        input.sources.sort_by_key(SourceArtifact::kind);
        for pair in input.sources.windows(2) {
            if pair[0].kind() == pair[1].kind() {
                return Err(EconomicCatalogError::DuplicateSource(pair[0].kind()));
            }
        }
        validate_text_sources(&input)?;
        let compiler = compiler_for(&input)?;
        // Check framing and byte bounds before source expansion or generation.
        let bytes = codec::encode(&input, compiler)?;
        let digest = sha256_of(&bytes);
        let local_detail = local_detail(&input)?;
        let spatial_detail = spatial_detail(&input, local_detail.as_ref())?;
        let (sources, opening) = match input.geography {
            CatalogGeography::NationalCounties
            | CatalogGeography::NationalCountiesWithMichiganDetail => {
                let (sources, opening) = NationalSources::admit(&input)?;
                (CapturedSources::National(Box::new(sources)), opening)
            }
            CatalogGeography::MichiganControl => {
                let (sources, opening) = super::control::MichiganSources::admit(&mut input)?;
                (CapturedSources::Michigan(Box::new(sources)), opening)
            }
        };
        if expected.is_some_and(|expected| *expected != opening) {
            return Err(EconomicCatalogError::Opening("supplied opening mismatch"));
        }
        Ok(Self {
            input,
            sources,
            opening,
            bytes,
            digest,
            local_detail,
            spatial_detail,
        })
    }
    /// Reopening uses only these captured bytes and the supported compiler version.
    /// # Errors
    /// Refuses changed digest, unsupported versions or noncanonical source framing.
    pub fn decode(bytes: &[u8], expected_digest: [u8; 32]) -> Result<Self> {
        if bytes.len() > codec::MAX_CATALOG_BYTES {
            return Err(EconomicCatalogError::Bound);
        }
        if sha256_of(bytes) != expected_digest {
            return Err(EconomicCatalogError::Digest);
        }
        let (input, compiler) = codec::decode(bytes)?;
        if compiler_for(&input)? != compiler {
            return Err(EconomicCatalogError::CompilerVersion);
        }
        let catalog = Self::capture(input, None)?;
        if catalog.bytes != bytes {
            return Err(EconomicCatalogError::WireNoncanonical);
        }
        Ok(catalog)
    }
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8] {
        &self.bytes
    }
    #[must_use]
    pub const fn digest(&self) -> [u8; 32] {
        self.digest
    }
    #[must_use]
    pub fn compiler_version(&self) -> &'static str {
        match self.input.geography {
            CatalogGeography::MichiganControl => "michigan-control-v1",
            _ => "national-world-v1",
        }
    }
    #[must_use]
    pub const fn opening(&self) -> &EconomicOpening {
        &self.opening
    }
    #[must_use]
    pub fn view(&self) -> EconomicProjectionView<'_> {
        EconomicProjectionView {
            scenario_id: &self.input.scenario_id,
            preset_id: &self.input.preset_id,
            duration: self.input.duration,
            source_digest: self.digest,
            opening: &self.opening,
            sources: match &self.sources {
                CapturedSources::National(s) => s.view(),
                CapturedSources::Michigan(s) => s.view(),
            },
        }
    }
    pub(crate) fn spatial_detail(
        &self,
    ) -> Option<&crate::spatial_reference_products::SpatialReferenceProducts> {
        self.spatial_detail.as_ref()
    }
    pub(crate) fn has_organizer(&self) -> bool {
        self.input.organizer.is_some()
    }
    #[must_use]
    pub fn source(&self, kind: SourceArtifactKind) -> Option<&[u8]> {
        self.input
            .sources
            .binary_search_by_key(&kind, SourceArtifact::kind)
            .ok()
            .map(|i| self.input.sources[i].bytes())
    }
}
fn compiler_for(input: &EconomicCatalogInput) -> Result<&'static str> {
    input
        .duration
        .validate()
        .map_err(|_| EconomicCatalogError::Identity)?;
    match input.geography {
        CatalogGeography::NationalCounties
        | CatalogGeography::NationalCountiesWithMichiganDetail
            if input.scenario_id == crate::national_economy::NATIONAL_SCENARIO_ID
                && input.preset_id == "national-world"
                && input.duration == CampaignDuration::Continuous
                && input.organizer.is_none() =>
        {
            Ok("national-world-v1")
        }
        CatalogGeography::MichiganControl
            if input.scenario_id == crate::michigan_cohorts::MICHIGAN_COHORT_SCENARIO =>
        {
            Ok("michigan-control-v1")
        }
        _ => Err(EconomicCatalogError::Identity),
    }
}
pub(super) fn source(input: &EconomicCatalogInput, kind: SourceArtifactKind) -> Result<&[u8]> {
    input
        .sources
        .iter()
        .find(|row| row.kind() == kind)
        .map(SourceArtifact::bytes)
        .ok_or(EconomicCatalogError::Source(kind))
}
pub(super) fn source_coverage(
    input: &EconomicCatalogInput,
    required: &[SourceArtifactKind],
    optional: &[SourceArtifactKind],
) -> Result<()> {
    let found: BTreeSet<_> = input.sources.iter().map(SourceArtifact::kind).collect();
    for kind in required {
        if !found.contains(kind) {
            return Err(EconomicCatalogError::Source(*kind));
        }
    }
    for kind in found {
        if !required.contains(&kind) && !optional.contains(&kind) {
            return Err(EconomicCatalogError::UnexpectedSource(kind));
        }
    }
    Ok(())
}
fn local_detail(
    input: &EconomicCatalogInput,
) -> Result<Option<babylon_tick::h3_runtime::MichiganDynamicHexFoundation>> {
    let bytes = input
        .sources
        .iter()
        .find(|s| s.kind() == SourceArtifactKind::MichiganDynamicHexes);
    match (input.geography, bytes) {
        (CatalogGeography::NationalCounties, None) => Ok(None),
        (
            CatalogGeography::MichiganControl
            | CatalogGeography::NationalCountiesWithMichiganDetail,
            Some(bytes),
        ) => crate::decode_michigan_dynamic_hex_foundation(bytes.bytes())
            .map(Some)
            .map_err(|_| EconomicCatalogError::Source(SourceArtifactKind::MichiganDynamicHexes)),
        _ => Err(EconomicCatalogError::Source(
            SourceArtifactKind::MichiganDynamicHexes,
        )),
    }
}

fn spatial_detail(
    input: &EconomicCatalogInput,
    local: Option<&babylon_tick::h3_runtime::MichiganDynamicHexFoundation>,
) -> Result<Option<crate::spatial_reference_products::SpatialReferenceProducts>> {
    let kind = SourceArtifactKind::MichiganSpatialProducts;
    let bytes = input.sources.iter().find(|row| row.kind() == kind);
    match (local, bytes) {
        (None, None) => Ok(None),
        (Some(local), Some(bytes)) => {
            crate::spatial_reference_products::SpatialReferenceProducts::decode_captured(
                bytes.bytes(),
                local,
            )
            .map(Some)
            .map_err(|_| EconomicCatalogError::Source(kind))
        }
        _ => Err(EconomicCatalogError::Source(kind)),
    }
}

fn validate_text_sources(input: &EconomicCatalogInput) -> Result<()> {
    for kind in [
        SourceArtifactKind::GraphDeclarations,
        SourceArtifactKind::Rules,
        SourceArtifactKind::PreludeDeclarations,
    ] {
        if let Some(row) = input.sources.iter().find(|row| row.kind() == kind) {
            if row.bytes().len() > 1_048_576
                || row.bytes().contains(&0)
                || std::str::from_utf8(row.bytes()).is_err()
            {
                return Err(EconomicCatalogError::Source(kind));
            }
        }
    }
    Ok(())
}

impl CapturedEconomicCatalog {
    /// Capture a freshly authored Michigan control and its explicit local detail.
    /// Reuse local detail already captured by a decoded control. Subsequent
    /// decoding uses these bytes, never the current fixture accessor.
    /// # Errors
    /// Refuses missing original source inputs or any change during regeneration.
    pub fn from_michigan(
        catalog: &crate::michigan_material::MichiganMaterialCatalog,
    ) -> Result<Self> {
        let mut sources = catalog.captured_sources().to_vec();
        if !sources
            .iter()
            .any(|source| source.kind() == SourceArtifactKind::MichiganDynamicHexes)
        {
            sources.push(SourceArtifact::capture(
                SourceArtifactKind::MichiganDynamicHexes,
                crate::michigan_dynamic_hex_foundation_fixture_parts().concat(),
            ));
        }
        if !sources
            .iter()
            .any(|source| source.kind() == SourceArtifactKind::MichiganSpatialProducts)
        {
            sources.push(SourceArtifact::capture(
                SourceArtifactKind::MichiganSpatialProducts,
                crate::spatial_reference_products::fixture_bytes().to_vec(),
            ));
        }
        let input = EconomicCatalogInput {
            scenario_id: crate::michigan_cohorts::MICHIGAN_COHORT_SCENARIO.to_owned(),
            preset_id: catalog
                .experiment()
                .map_or(catalog.preset().id(), |spec| spec.profile.foundation_id())
                .to_owned(),
            duration: catalog.duration(),
            sources,
            geography: CatalogGeography::MichiganControl,
            organizer: catalog.organizer_config().cloned(),
        };
        Self::capture(
            input,
            Some(&super::michigan::import_michigan_opening(catalog)?),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn missing_or_changed_captured_detail_cannot_reload_the_embedded_fixture() {
        let control = crate::michigan_material::MichiganMaterialCatalog::from_defines_toml(
            include_str!("../../../../../content/scenarios/michigan/defines.toml"),
        )
        .unwrap();
        let captured = CapturedEconomicCatalog::from_michigan(&control).unwrap();
        let mut missing = captured.input.clone();
        missing
            .sources
            .retain(|row| row.kind() != SourceArtifactKind::MichiganSpatialProducts);
        assert!(matches!(
            CapturedEconomicCatalog::capture(missing, None),
            Err(EconomicCatalogError::Source(
                SourceArtifactKind::MichiganSpatialProducts
            ))
        ));
        let mut changed = captured.input;
        let source = changed
            .sources
            .iter_mut()
            .find(|row| row.kind() == SourceArtifactKind::MichiganSpatialProducts)
            .unwrap();
        let mut bytes = source.bytes().to_vec();
        bytes[52] ^= 1;
        *source = SourceArtifact::capture(SourceArtifactKind::MichiganSpatialProducts, bytes);
        assert!(matches!(
            CapturedEconomicCatalog::capture(changed, None),
            Err(EconomicCatalogError::Source(
                SourceArtifactKind::MichiganSpatialProducts
            ))
        ));
    }
}
