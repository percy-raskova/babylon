//! Immutable current campaign admission shared by material readers and projections.
use crate::economic_catalog::EconomicProjectionView;
use crate::identity::CampaignId;
use crate::material_runtime::{
    MaterialComponentIdentity, MaterialRuntimeError, MaterialRuntimeFoundation,
};
use crate::material_storage::OpeningRegister;

use babylon_graph::stable_state::StableGraphState;
use babylon_kernel::clock::CampaignDuration;
use babylon_material_circuit::MaterialCatalog;

use babylon_tick::material_staffing::StaffingComposition;
use babylon_tick::material_world::MaterialWorldRegister;

use crate::michigan_material::MichiganDeliveryPreset;
use crate::simulation_experiment::ExperimentProfile;
use babylon_kernel::content_digest;
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;
use std::ops::Deref;
use std::sync::{Arc, Mutex, OnceLock, Weak};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EconomicContentError {
    UnknownPreset,
    Header,
    Foundation,
    Identity,
    OwnerPoisoned,
}
impl std::fmt::Display for EconomicContentError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
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
    opening: OnceLock<Result<OpeningRegister, EconomicContentError>>,
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
        let graph_digest = content_digest::sha256_of(graph.canonical_bytes());
        let source_digest = content_digest::sha256_of(graph.content_bundle().canonical_bytes());
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
            opening: OnceLock::new(),
        })
    }
    /// Move the admitted authority into the durable runtime without regeneration.
    #[must_use]
    pub(crate) fn into_foundation(self) -> MaterialRuntimeFoundation {
        self.foundation
    }
    pub(crate) const fn foundation(&self) -> &MaterialRuntimeFoundation {
        &self.foundation
    }
    /// Derive the immutable storage opening at most once. Runtime admission alone
    /// does not pay for a lookup used only by read-side consumers.
    pub(crate) fn opening(&self) -> Result<&OpeningRegister, EconomicContentError> {
        self.opening
            .get_or_init(|| {
                OpeningRegister::from_opening(self.initial_register())
                    .map_err(|_| EconomicContentError::Foundation)
            })
            .as_ref()
            .map_err(|error| *error)
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
    /// The one immutable definition set every period of this campaign borrows.
    #[must_use]
    pub fn material_catalog(&self) -> &MaterialCatalog {
        self.foundation.material_catalog()
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
    /// Return the complete canonical length without allocating an export.
    /// # Errors
    /// Refuses invalid canonical component bounds or duration.
    pub fn canonical_len(&self) -> Result<usize, MaterialRuntimeError> {
        self.foundation.canonical_len()
    }
    /// Allocate the current binary export only when explicitly requested.
    /// # Errors
    /// Refuses invalid canonical framing or an allocation failure.
    pub fn export_canonical_bytes(&self) -> Result<Vec<u8>, MaterialRuntimeError> {
        self.foundation.export_canonical_bytes()
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

/// Shared handle to one immutable admitted campaign foundation.
///
/// The admission is immutable and multi-megabyte; worker and reader threads
/// share one owner instead of cloning the foundation or serializing readers.
#[derive(Clone)]
pub struct EconomicContentHandle(
    // STYLE-EXCEPTION(EXC-04): one admitted foundation is shared across worker and reader threads.
    Arc<EconomicContentAdmission>,
);
impl EconomicContentHandle {
    /// The one immutable definition set this admission shares with every clone.
    #[must_use]
    pub fn material_catalog(&self) -> &MaterialCatalog {
        self.0.material_catalog()
    }
}

impl EconomicContentHandle {
    pub(crate) fn new(admission: EconomicContentAdmission) -> Self {
        // STYLE-EXCEPTION(EXC-04): first shared owner of the admitted foundation.
        Self(Arc::new(admission))
    }
    /// The number of strong owners of this admission.
    #[cfg(test)]
    #[must_use]
    pub(crate) fn strong_count(&self) -> usize {
        // STYLE-EXCEPTION(EXC-04): the cursor's weak-reference contract is asserted here.
        Arc::strong_count(&self.0)
    }
    pub(crate) fn downgrade(&self) -> EconomicContentRef {
        // STYLE-EXCEPTION(EXC-04): an observation cursor tracks the admission without owning it.
        EconomicContentRef(Arc::downgrade(&self.0))
    }
}
impl Deref for EconomicContentHandle {
    type Target = EconomicContentAdmission;
    fn deref(&self) -> &Self::Target {
        &self.0
    }
}

impl AsRef<EconomicContentAdmission> for EconomicContentHandle {
    fn as_ref(&self) -> &EconomicContentAdmission {
        &self.0
    }
}

/// Weak handle held by one observation cursor.
#[derive(Clone, Debug)]
pub(crate) struct EconomicContentRef(
    // STYLE-EXCEPTION(EXC-04): a weak reference never extends the admission lifetime.
    Weak<EconomicContentAdmission>,
);
impl EconomicContentRef {
    pub(crate) fn upgrade(&self) -> Option<EconomicContentHandle> {
        self.0.upgrade().map(EconomicContentHandle)
    }
}

/// One explicit owner retains at most one campaign's immutable admitted source.
/// No SQL rows, mutable material state, receipts or publication results live here.
#[derive(Clone, Default)]
pub(crate) struct EconomicAdmissionOwner {
    // STYLE-EXCEPTION(EXC-04): cloned session owners share the one admission slot.
    candidate: Arc<Mutex<Option<EconomicAdmissionCandidate>>>,
}
struct EconomicAdmissionCandidate {
    campaign: CampaignId,
    admitted: EconomicContentHandle,
}
impl EconomicAdmissionOwner {
    pub(crate) fn candidate(
        &self,
        campaign: CampaignId,
    ) -> Result<Option<EconomicContentHandle>, EconomicContentError> {
        let candidate = self
            .candidate
            .lock()
            .map_err(|_| EconomicContentError::OwnerPoisoned)?;
        Ok(candidate
            .as_ref()
            .filter(|candidate| candidate.campaign == campaign)
            .map(|candidate| candidate.admitted.clone()))
    }
    /// Call only after the complete consuming operation has succeeded.
    pub(crate) fn publish(
        &self,
        campaign: CampaignId,
        admitted: EconomicContentHandle,
    ) -> Result<(), EconomicContentError> {
        let previous = self
            .candidate
            .lock()
            .map_err(|_| EconomicContentError::OwnerPoisoned)?
            .replace(EconomicAdmissionCandidate { campaign, admitted });
        // Releasing a previous campaign can destroy large source owners. The
        // mutex protects only replacement, never that detached release work.
        drop(previous);
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
        && MichiganDeliveryPreset::from_id(preset).is_none()
        && ExperimentProfile::from_foundation_id(preset).is_none()
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::michigan_content::MichiganContentPreset;
    use crate::michigan_material::MichiganDeliveryPreset;

    fn admission() -> EconomicContentAdmission {
        EconomicContentAdmission::from_foundation(
            MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
                .create_foundation(&crate::test_support::catalog())
                .expect("the shipped numeric fixture founds a campaign"),
        )
        .expect("the admitted foundation carries the economic catalog")
    }

    #[test]
    fn economic_content_handle_shares_one_material_catalog_across_clones() {
        let handle = EconomicContentHandle::new(admission());
        let clone = handle.clone();
        assert!(std::ptr::eq(
            handle.material_catalog(),
            clone.material_catalog()
        ));
        assert_eq!(
            handle.material_catalog().catalog_digest,
            handle.initial_register().catalog_digest()
        );
        assert_eq!(
            handle.material_catalog(),
            handle.foundation().material_catalog()
        );
    }
}
