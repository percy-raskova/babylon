//! Eight-family committed-material successor. Component row codecs remain exact.

#[cfg(test)]
#[path = "material_envelope/tests.rs"]
mod streaming_controls;

#[path = "material_envelope/envelope.rs"]
mod envelope;

pub(crate) use envelope::CommittedMaterialTickAttestation;
pub use envelope::{CommittedMaterialTickEnvelope, MAX_COMMITTED_MATERIAL_TICK_BYTES};
