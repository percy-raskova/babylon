//! Eight-family committed-material successor. Component row codecs remain exact.

#[cfg(test)]
#[path = "material_envelope/tests.rs"]
mod streaming_controls;

#[path = "material_envelope/envelope.rs"]
mod envelope;

#[allow(unused_imports)]
pub(crate) use envelope::CommittedMaterialTickAttestation;
#[allow(unused_imports)]
use envelope::{
    append_row, append_u64, encode_into, material_component_lengths, prepare_components,
    BoundedSink, BufferedDigest, ByteSink, DOMAIN, FIXED_FRAMING_BYTES, HASH_BUFFER_BYTES,
};
pub use envelope::{CommittedMaterialTickEnvelope, MAX_COMMITTED_MATERIAL_TICK_BYTES};

#[allow(unused_imports)]
use crate::{
    committed_tick_envelope::{
        compose_row_families, validate_committed_tick_envelope_bounds, CommittedTickRowBatch,
        CommittedTickRowFamilies,
    },
    identity::CampaignId,
    runtime::RustPersistenceRuntimeError,
};
#[allow(unused_imports)]
use babylon_kernel::content_digest::sha256_of;
#[allow(unused_imports)]
use babylon_tick::material_replay::IdentifiedMaterialTick;
