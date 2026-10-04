//! Immutable current campaign admission shared by material readers and projections.
use crate::{
    economic_catalog::EconomicProjectionView,
    material_runtime::{MaterialComponentIdentity, MaterialRuntimeFoundation},
};
use babylon_graph::stable_state::StableGraphState;
use babylon_kernel::{clock::CampaignDuration, content_digest::sha256_of};
use babylon_tick::{material_staffing::StaffingComposition, material_world::MaterialWorldRegister};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EconomicContentError {
    UnknownPreset,
    Header,
    Foundation,
    Identity,
}
impl std::fmt::Display for EconomicContentError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "economic content admission refused: {self:?}")
    }
}
impl std::error::Error for EconomicContentError {}

/// One admitted immutable foundation. Its catalog is never cloned into a second
/// metadata owner, and projection reads never call the opening generator.
pub struct EconomicContentAdmission {
    foundation: MaterialRuntimeFoundation,
    foundation_graph: StableGraphState,
    pub(crate) graph_digest: [u8; 32],
    pub(crate) source_digest: [u8; 32],
    pub(crate) component_identity: MaterialComponentIdentity,
}
impl EconomicContentAdmission {
    /// Reuse an already checked current economic foundation.
    /// # Errors
    /// Refuses a graph-only source or a failed canonical graph projection.
    pub fn from_foundation(
        foundation: MaterialRuntimeFoundation,
    ) -> Result<Self, EconomicContentError> {
        let graph = foundation.graph_foundation();
        if graph.content_bundle().economic_catalog().is_none() {
            return Err(EconomicContentError::Foundation);
        }
        let graph_digest = sha256_of(graph.canonical_bytes());
        let source_digest = sha256_of(graph.content_bundle().canonical_bytes());
        let component_identity = MaterialComponentIdentity::from_foundation(graph);
        let foundation_graph = foundation
            .opening_graph_state()
            .map_err(|_| EconomicContentError::Foundation)?;
        Ok(Self {
            foundation,
            foundation_graph,
            graph_digest,
            source_digest,
            component_identity,
        })
    }
    /// Move the admitted authority into the durable runtime without regeneration.
    #[must_use]
    pub(crate) fn into_foundation(self) -> MaterialRuntimeFoundation {
        self.foundation
    }
    /// Borrow immutable metadata from the admitted economic source.
    /// # Panics
    /// Panics only if the private constructor invariant is violated.
    #[must_use]
    pub fn view(&self) -> EconomicProjectionView<'_> {
        self.foundation
            .graph_foundation()
            .content_bundle()
            .economic_catalog()
            .expect("economic source admitted at construction")
            .view()
    }
    #[must_use]
    pub fn initial_register(&self) -> &MaterialWorldRegister {
        self.foundation.initial_register()
    }
    #[must_use]
    pub fn staffing(&self) -> &StaffingComposition {
        self.foundation.labor()
    }
    #[must_use]
    pub const fn foundation_graph(&self) -> &StableGraphState {
        &self.foundation_graph
    }
    #[must_use]
    pub fn duration(&self) -> CampaignDuration {
        self.foundation.spec().duration
    }
    #[must_use]
    pub fn preset_id(&self) -> &str {
        &self.foundation.spec().preset_id
    }
    #[must_use]
    pub fn digest(&self) -> [u8; 32] {
        self.foundation.digest()
    }
    #[must_use]
    pub fn content_digest(&self) -> [u8; 32] {
        self.foundation.spec().content_digest
    }
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8] {
        self.foundation.canonical_bytes()
    }
    /// # Errors
    /// Refuses clocks or source/foundation identities from any other campaign.
    pub fn validate_header(
        &self,
        duration: CampaignDuration,
        content: &[u8],
        foundation: &[u8],
        tick: u64,
    ) -> Result<(), EconomicContentError> {
        if duration != self.duration()
            || !duration.contains(tick)
            || content != self.content_digest()
            || foundation != self.digest()
        {
            return Err(EconomicContentError::Identity);
        }
        Ok(())
    }
    /// # Errors
    /// Refuses a graph foundation or content envelope from another capture.
    pub fn validate_graph(
        &self,
        foundation: &[u8],
        source: &[u8],
    ) -> Result<(), EconomicContentError> {
        if foundation != self.graph_digest || source != self.source_digest {
            return Err(EconomicContentError::Identity);
        }
        Ok(())
    }
}
/// Header checking alone never admits opaque material authority.
/// # Errors
/// Refuses unsupported presets, invalid clocks, absent or malformed identities.
pub fn validate_economic_header(
    preset: &str,
    duration: CampaignDuration,
    content: &[u8],
    foundation: &[u8],
    tick: u64,
) -> Result<(), EconomicContentError> {
    if preset != "national-world"
        && crate::michigan_material::MichiganDeliveryPreset::from_id(preset).is_none()
        && crate::simulation_experiment::ExperimentProfile::from_foundation_id(preset).is_none()
    {
        return Err(EconomicContentError::UnknownPreset);
    }
    if duration.validate().is_err()
        || !duration.contains(tick)
        || content.len() != 32
        || foundation.len() != 32
        || content.iter().all(|byte| *byte == 0)
        || foundation.iter().all(|byte| *byte == 0)
    {
        return Err(EconomicContentError::Header);
    }
    Ok(())
}
/// Decode captured sources once and verify the complete reconstructed foundation.
/// # Errors
/// Refuses unsupported, changed, noncanonical or mismatched current authority.
pub fn admit_economic_content(
    preset: &str,
    duration: CampaignDuration,
    content: &[u8],
    foundation: &[u8],
    tick: u64,
    bytes: &[u8],
) -> Result<EconomicContentAdmission, EconomicContentError> {
    validate_economic_header(preset, duration, content, foundation, tick)?;
    let digest = foundation
        .try_into()
        .map_err(|_| EconomicContentError::Header)?;
    let admitted = EconomicContentAdmission::from_foundation(
        MaterialRuntimeFoundation::decode(bytes, digest)
            .map_err(|_| EconomicContentError::Foundation)?,
    )?;
    if admitted.preset_id() != preset {
        return Err(EconomicContentError::Identity);
    }
    admitted.validate_header(duration, content, foundation, tick)?;
    Ok(admitted)
}
