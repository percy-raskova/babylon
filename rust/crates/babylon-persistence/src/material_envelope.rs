//! Eight-family committed-material successor. Component row codecs remain exact.

#[cfg(test)]
#[path = "material_envelope/tests.rs"]
mod streaming_controls;

#[path = "material_envelope/envelope.rs"]
mod envelope;

pub(crate) use envelope::CommittedMaterialTickAttestation;
#[cfg(test)]
use envelope::{BoundedSink, BufferedDigest, HASH_BUFFER_BYTES};
pub use envelope::{CommittedMaterialTickEnvelope, MAX_COMMITTED_MATERIAL_TICK_BYTES};

#[cfg(test)]
use crate::committed_tick_envelope::CommittedTickRowFamilies;
#[cfg(test)]
use crate::identity::CampaignId;
#[cfg(test)]
use crate::runtime::RustPersistenceRuntimeError;
#[cfg(test)]
use babylon_kernel::content_digest::sha256_of;
#[cfg(test)]
use babylon_tick::material_replay::IdentifiedMaterialTick;
