//! Refusals at the captured source and deterministic initialization boundary.
use super::SourceArtifactKind;
use crate::national_economy::NationalOpeningError;
use babylon_bsl::scenario::ScenarioError;
use babylon_material_circuit::MaterialCircuitError;
use babylon_tick::material_staffing::MaterialStaffingError;
use babylon_tick::material_state::MaterialStateError;
use babylon_tick::replay_session::ReplayTickError;
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;

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
    Scenario(Box<ScenarioError>),
    Replay(Box<ReplayTickError>),
    Geography(Box<MaterialStateError>),
    NationalOpening(NationalOpeningError),
    Foundation,
    Arithmetic,
    Circuit(MaterialCircuitError),
    Staffing(MaterialStaffingError),
}
impl std::fmt::Display for EconomicCatalogError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "economic catalog refused: {self:?}")
    }
}
impl std::error::Error for EconomicCatalogError {}
impl From<MaterialCircuitError> for EconomicCatalogError {
    fn from(error: MaterialCircuitError) -> Self {
        Self::Circuit(error)
    }
}

impl From<ScenarioError> for EconomicCatalogError {
    fn from(error: ScenarioError) -> Self {
        Self::Scenario(Box::new(error))
    }
}
impl From<ReplayTickError> for EconomicCatalogError {
    fn from(error: ReplayTickError) -> Self {
        Self::Replay(Box::new(error))
    }
}

impl From<MaterialStateError> for EconomicCatalogError {
    fn from(error: MaterialStateError) -> Self {
        Self::Geography(Box::new(error))
    }
}
