//! Eight-family committed-material successor. Component row codecs remain exact.

use crate::{
    committed_tick_envelope::{
        compose_row_families, validate_committed_tick_envelope_bounds, CommittedTickRowBatch,
        CommittedTickRowFamilies,
    },
    identity::CampaignId,
    runtime::RustPersistenceRuntimeError,
};
use babylon_kernel::content_digest::sha256_of;
use babylon_tick::material_replay::IdentifiedMaterialTick;

const DOMAIN: &[u8] = b"babylon.committed-material-tick.v3\0";
/// Derived from six row-family bounds, register, receipt and exact framing.
pub const MAX_COMMITTED_MATERIAL_TICK_BYTES: usize =
    babylon_tick::material_world::MAX_MATERIAL_WORLD_REGISTER_BYTES
        + babylon_tick::material_world::MAX_MATERIAL_TICK_RECEIPT_BYTES
        + crate::committed_tick_envelope::MAX_COMMITTED_COMPONENT_BODY_BYTES
        + FIXED_FRAMING_BYTES;
const FIXED_FRAMING_BYTES: usize = DOMAIN.len() + 4 + 16 + 8 + 32 + 8 * 9 + 16;

fn material_component_lengths(
    register: usize,
    receipts: usize,
) -> Result<(), RustPersistenceRuntimeError> {
    if register > babylon_tick::material_world::MAX_MATERIAL_WORLD_REGISTER_BYTES
        || receipts > babylon_tick::material_world::MAX_MATERIAL_TICK_RECEIPT_BYTES
    {
        return Err(RustPersistenceRuntimeError::CampaignConflict);
    }
    Ok(())
}

/// Exact closed envelope, with material register and receipts inseparable from its claim.
#[derive(Debug, PartialEq, Eq)]
pub struct CommittedMaterialTickEnvelope {
    bytes: Vec<u8>,
    digest: [u8; 32],
}
impl CommittedMaterialTickEnvelope {
    /// Frame six typed component families followed by register and material receipt families.
    /// # Errors
    /// Refuses component ordering/shape, aggregate bounds, hash mismatch and allocation failure.
    pub fn compose(
        campaign: CampaignId,
        identity: &IdentifiedMaterialTick,
        families: CommittedTickRowFamilies,
        register: &[u8],
        receipts: &[u8],
    ) -> Result<Self, RustPersistenceRuntimeError> {
        let (components, capacity) = prepare_components(identity, families, register, receipts)?;
        let mut bytes = Vec::new();
        bytes
            .try_reserve_exact(capacity)
            .map_err(|_| RustPersistenceRuntimeError::Allocation {
                field: "material envelope",
                requested: capacity,
            })?;
        let bytes = encode_into(
            BoundedSink::new(bytes, capacity),
            campaign,
            identity,
            &components,
            register,
            receipts,
        )?;
        let digest = sha256_of(&bytes);
        Ok(Self { bytes, digest })
    }

    /// Verify the same complete V3 framing without retaining a second copy.
    /// This proof is for authenticated reads; durable reconciliation retains
    /// canonical bytes and compares them exactly through `compose`.
    pub(crate) fn attest(
        campaign: CampaignId,
        identity: &IdentifiedMaterialTick,
        families: CommittedTickRowFamilies,
        register: &[u8],
        receipts: &[u8],
    ) -> Result<CommittedMaterialTickAttestation, RustPersistenceRuntimeError> {
        let (components, capacity) = prepare_components(identity, families, register, receipts)?;
        let digest = encode_into(
            BoundedSink::new(BufferedDigest::new()?, capacity),
            campaign,
            identity,
            &components,
            register,
            receipts,
        )?;
        Ok(CommittedMaterialTickAttestation {
            digest,
            encoded_bytes: capacity,
        })
    }
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8] {
        &self.bytes
    }
    #[must_use]
    pub const fn digest(&self) -> [u8; 32] {
        self.digest
    }
}
/// Constructed only after complete component admission and exact framing.
#[derive(Debug, PartialEq, Eq)]
pub(crate) struct CommittedMaterialTickAttestation {
    digest: [u8; 32],
    encoded_bytes: usize,
}
impl CommittedMaterialTickAttestation {
    #[must_use]
    pub(crate) const fn digest(&self) -> [u8; 32] {
        self.digest
    }
    #[must_use]
    pub(crate) const fn encoded_bytes(&self) -> usize {
        self.encoded_bytes
    }
}

fn prepare_components(
    identity: &IdentifiedMaterialTick,
    families: CommittedTickRowFamilies,
    register: &[u8],
    receipts: &[u8],
) -> Result<([CommittedTickRowBatch; 6], usize), RustPersistenceRuntimeError> {
    material_component_lengths(register.len(), receipts.len())?;
    if sha256_of(receipts) != identity.receipt_digest() {
        return Err(RustPersistenceRuntimeError::CampaignConflict);
    }
    let components =
        compose_row_families(families).map_err(RustPersistenceRuntimeError::SemanticEnvelope)?;
    let body_bytes = validate_committed_tick_envelope_bounds(
        components.each_ref().map(|batch| batch.rows().len()),
        components.each_ref().map(CommittedTickRowBatch::body_bytes),
    )
    .map_err(RustPersistenceRuntimeError::SemanticEnvelope)?;
    let capacity = FIXED_FRAMING_BYTES
        .checked_add(body_bytes)
        .and_then(|bytes| bytes.checked_add(register.len()))
        .and_then(|bytes| bytes.checked_add(receipts.len()))
        .ok_or(RustPersistenceRuntimeError::CampaignConflict)?;
    if capacity > MAX_COMMITTED_MATERIAL_TICK_BYTES {
        return Err(RustPersistenceRuntimeError::CampaignConflict);
    }
    Ok((components, capacity))
}

/// Both consumers receive exactly the same ordered chunks. The digest consumer
/// updates one SHA state over their concatenation; it does not combine hashes.
fn encode_into<S: ByteSink>(
    mut sink: BoundedSink<S>,
    campaign: CampaignId,
    identity: &IdentifiedMaterialTick,
    components: &[CommittedTickRowBatch; 6],
    register: &[u8],
    receipts: &[u8],
) -> Result<S::Output, RustPersistenceRuntimeError> {
    sink.append(DOMAIN)?;
    sink.append(&3_u32.to_be_bytes())?;
    sink.append(campaign.canonical_bytes())?;
    sink.append(&identity.resolve_tick().to_be_bytes())?;
    sink.append(identity.tick_content_hash().as_bytes())?;
    for (index, batch) in components.iter().enumerate() {
        let tag =
            u8::try_from(index + 1).map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?;
        sink.append(&[tag])?;
        append_u64(&mut sink, batch.rows().len())?;
        for row in batch.rows() {
            append_row(&mut sink, row.key(), row.payload())?;
        }
    }
    for (tag, payload) in [(7, register), (8, receipts)] {
        sink.append(&[tag])?;
        sink.append(&1_u64.to_be_bytes())?;
        append_row(&mut sink, &[], payload)?;
    }
    sink.finish()
}

fn append_u64<S: ByteSink>(
    sink: &mut BoundedSink<S>,
    value: usize,
) -> Result<(), RustPersistenceRuntimeError> {
    sink.append(
        &u64::try_from(value)
            .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?
            .to_be_bytes(),
    )
}

fn append_row<S: ByteSink>(
    sink: &mut BoundedSink<S>,
    key: &[u8],
    payload: &[u8],
) -> Result<(), RustPersistenceRuntimeError> {
    for value in [key, payload] {
        sink.append(
            &u32::try_from(value.len())
                .map_err(|_| RustPersistenceRuntimeError::CampaignConflict)?
                .to_be_bytes(),
        )?;
        sink.append(value)?;
    }
    Ok(())
}

trait ByteSink {
    type Output;
    fn append(&mut self, bytes: &[u8]);
    fn finish(self) -> Self::Output;
}

impl ByteSink for Vec<u8> {
    type Output = Self;
    fn append(&mut self, bytes: &[u8]) {
        self.extend_from_slice(bytes);
    }
    fn finish(self) -> Self::Output {
        self
    }
}

/// Admission's exact length is checked before each write and before exposing
/// either output. A failed frame cannot return a partial envelope or digest.
struct BoundedSink<S> {
    inner: S,
    expected: usize,
    written: usize,
    failed: bool,
}

impl<S: ByteSink> BoundedSink<S> {
    const fn new(inner: S, expected: usize) -> Self {
        Self {
            inner,
            expected,
            written: 0,
            failed: false,
        }
    }
    fn append(&mut self, bytes: &[u8]) -> Result<(), RustPersistenceRuntimeError> {
        if self.failed {
            return Err(RustPersistenceRuntimeError::CampaignConflict);
        }
        let Some(total) = self
            .written
            .checked_add(bytes.len())
            .filter(|&total| total <= self.expected)
        else {
            self.failed = true;
            return Err(RustPersistenceRuntimeError::CampaignConflict);
        };
        self.inner.append(bytes);
        self.written = total;
        Ok(())
    }
    fn finish(self) -> Result<S::Output, RustPersistenceRuntimeError> {
        if self.failed || self.written != self.expected {
            return Err(RustPersistenceRuntimeError::CampaignConflict);
        }
        Ok(self.inner.finish())
    }
}

const HASH_BUFFER_BYTES: usize = 65_536;

struct BufferedDigest {
    hash: sha2::Sha256,
    buffer: Vec<u8>,
}

impl BufferedDigest {
    fn new() -> Result<Self, RustPersistenceRuntimeError> {
        use sha2::Digest as _;
        let mut buffer = Vec::new();
        buffer.try_reserve_exact(HASH_BUFFER_BYTES).map_err(|_| {
            RustPersistenceRuntimeError::Allocation {
                field: "material envelope hash buffer",
                requested: HASH_BUFFER_BYTES,
            }
        })?;
        Ok(Self {
            hash: sha2::Sha256::new(),
            buffer,
        })
    }
    fn flush(&mut self) {
        use sha2::Digest as _;
        self.hash.update(&self.buffer);
        self.buffer.clear();
    }
}

impl ByteSink for BufferedDigest {
    type Output = [u8; 32];
    fn append(&mut self, bytes: &[u8]) {
        use sha2::Digest as _;
        if bytes.len() >= HASH_BUFFER_BYTES {
            self.flush();
            self.hash.update(bytes);
        } else {
            if bytes.len() > HASH_BUFFER_BYTES - self.buffer.len() {
                self.flush();
            }
            self.buffer.extend_from_slice(bytes);
        }
    }
    fn finish(mut self) -> Self::Output {
        use sha2::Digest as _;
        self.flush();
        self.hash.finalize().into()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn independent_components_and_exact_derived_framing() {
        assert_eq!(FIXED_FRAMING_BYTES, 183);
        // Current receipts add 32 income bytes per bounded row and a complete
        // 327,680-row gift family (387 bytes each plus nine framing bytes),
        // and one 317-byte collection row plus nine family framing bytes.
        assert_eq!(
            741_605_729 + 32 * 131_072 + 387 * 327_680 + 9 + 317 + 9,
            872_612_528
        );
        assert_eq!(
            MAX_COMMITTED_MATERIAL_TICK_BYTES,
            1_000_000_000 + 134_217_728 + 5 * 67_108_864 + 872_612_528 + FIXED_FRAMING_BYTES
        );
        assert!(material_component_lengths(1_000_000_000, 872_612_528).is_ok());
        assert!(material_component_lengths(1_000_000_001, 0).is_err());
        assert!(material_component_lengths(0, 872_612_529).is_err());
        for index in 0..6 {
            let mut counts = [0; 6];
            let mut bodies = [0; 6];
            counts[5] = 1;
            bodies[5] = 9;
            counts[index] = 1;
            bodies[index] = crate::committed_tick_envelope::ALL_COMMITTED_TICK_ROW_FAMILIES[index]
                .maximum_body_bytes()
                + 1;
            assert!(validate_committed_tick_envelope_bounds(counts, bodies).is_err());
        }
    }
}

#[cfg(test)]
#[path = "material_envelope/tests.rs"]
mod streaming_controls;
