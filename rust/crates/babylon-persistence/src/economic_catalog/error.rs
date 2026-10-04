//! Refusals at the captured source and deterministic initialization boundary.
use super::SourceArtifactKind;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EconomicCatalogError {
    Bound,
    Identity,
    Source(SourceArtifactKind),
    DuplicateSource(SourceArtifactKind),
    UnexpectedSource(SourceArtifactKind),
    Opening(&'static str),
    CompilerVersion,
    Digest,
    WireDomain,
    WireVersion,
    WireTruncated,
    WireTag,
    WireNoncanonical,
    WireTrailing,
    Graph,
    Scenario(Box<babylon_bsl::scenario::ScenarioError>),
    Replay(Box<babylon_tick::replay_session::ReplayTickError>),
    Geography(Box<babylon_tick::material_state::MaterialStateError>),
    NationalOpening(crate::national_economy::NationalOpeningError),
    Foundation,
    Arithmetic,
    Circuit(babylon_material_circuit::MaterialCircuitError),
    Staffing(babylon_tick::material_staffing::MaterialStaffingError),
}
impl std::fmt::Display for EconomicCatalogError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "economic catalog refused: {self:?}")
    }
}
impl std::error::Error for EconomicCatalogError {}
impl From<babylon_material_circuit::MaterialCircuitError> for EconomicCatalogError {
    fn from(error: babylon_material_circuit::MaterialCircuitError) -> Self {
        Self::Circuit(error)
    }
}

impl From<babylon_bsl::scenario::ScenarioError> for EconomicCatalogError {
    fn from(error: babylon_bsl::scenario::ScenarioError) -> Self {
        Self::Scenario(Box::new(error))
    }
}
impl From<babylon_tick::replay_session::ReplayTickError> for EconomicCatalogError {
    fn from(error: babylon_tick::replay_session::ReplayTickError) -> Self {
        Self::Replay(Box::new(error))
    }
}

impl From<babylon_tick::material_state::MaterialStateError> for EconomicCatalogError {
    fn from(error: babylon_tick::material_state::MaterialStateError) -> Self {
        Self::Geography(Box::new(error))
    }
}
