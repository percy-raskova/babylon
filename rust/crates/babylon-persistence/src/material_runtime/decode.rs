//! Exact current aggregate framing before expensive source regeneration.
use super::{
    reconstruct_material_foundation, MaterialFoundationSpec, MaterialRuntimeError,
    MaterialRuntimeFoundation, StoredMaterialFoundation, FOUNDATION_DOMAIN,
    MAX_MATERIAL_FOUNDATION_BYTES,
};
use crate::CampaignFoundation;
use babylon_kernel::{clock::CampaignDuration, content_digest::sha256_of};

impl MaterialRuntimeFoundation {
    /// Admit one complete current foundation, with no legacy source decoder.
    /// # Errors
    /// Refuses framing, digest, source compilation, replay or material differences.
    pub fn decode(bytes: &[u8], expected: [u8; 32]) -> Result<Self, MaterialRuntimeError> {
        if bytes.len() > MAX_MATERIAL_FOUNDATION_BYTES || sha256_of(bytes) != expected {
            return Err(MaterialRuntimeError::FoundationMismatch);
        }
        let mut cursor = Cursor { bytes };
        if cursor.take(FOUNDATION_DOMAIN.len())? != FOUNDATION_DOMAIN || cursor.word()? != 3 {
            return Err(MaterialRuntimeError::FoundationMismatch);
        }
        let duration = CampaignDuration::decode(cursor.array()?)
            .map_err(|_| MaterialRuntimeError::FoundationMismatch)?;
        let content_digest = cursor.array()?;
        let preset = cursor.blob64()?;
        let graph = cursor.blob64()?;
        let initial_register = cursor.blob64()?;
        super::envelope::material_foundation_length(
            preset.len(),
            graph.len(),
            initial_register.len(),
        )?;
        let preset_id = std::str::from_utf8(preset)
            .map_err(|_| MaterialRuntimeError::FoundationMismatch)?
            .to_owned();
        if !cursor.bytes.is_empty() {
            return Err(MaterialRuntimeError::FoundationMismatch);
        }
        let graph_foundation_digest = sha256_of(graph);
        let graph = decode_graph(graph)?;
        let reconstructed = reconstruct_material_foundation(
            StoredMaterialFoundation {
                spec: MaterialFoundationSpec {
                    preset_id,
                    duration,
                    content_digest,
                },
                initial_register_bytes: initial_register.to_vec(),
                foundation_digest: expected,
                graph_foundation_digest,
            },
            graph,
            expected,
        )?;
        if reconstructed.canonical_bytes() != bytes {
            return Err(MaterialRuntimeError::FoundationMismatch);
        }
        Ok(reconstructed)
    }
}
fn decode_graph(bytes: &[u8]) -> Result<CampaignFoundation, MaterialRuntimeError> {
    let mut cursor = Cursor { bytes };
    let graph = cursor.blob32()?;
    let world = cursor.blob32()?;
    let resolver = cursor.blob32()?;
    let environment = cursor.blob32()?;
    let session = std::str::from_utf8(cursor.blob32()?)
        .map_err(|_| MaterialRuntimeError::FoundationMismatch)?;
    let seed = i64::from_be_bytes(cursor.array()?);
    let defines = cursor.array()?;
    let rules = cursor.array()?;
    let reference = cursor.array()?;
    Ok(CampaignFoundation::from_persisted(
        graph.to_vec(),
        world.to_vec(),
        resolver.to_vec(),
        environment.to_vec(),
        session,
        seed,
        defines,
        rules,
        reference,
        cursor.bytes,
        sha256_of(bytes),
    )?)
}
struct Cursor<'a> {
    bytes: &'a [u8],
}
impl<'a> Cursor<'a> {
    fn take(&mut self, count: usize) -> Result<&'a [u8], MaterialRuntimeError> {
        let value = self
            .bytes
            .get(..count)
            .ok_or(MaterialRuntimeError::FoundationMismatch)?;
        self.bytes = &self.bytes[count..];
        Ok(value)
    }
    fn array<const N: usize>(&mut self) -> Result<[u8; N], MaterialRuntimeError> {
        self.take(N)?
            .try_into()
            .map_err(|_| MaterialRuntimeError::FoundationMismatch)
    }
    fn word(&mut self) -> Result<u32, MaterialRuntimeError> {
        Ok(u32::from_be_bytes(self.array()?))
    }
    fn blob32(&mut self) -> Result<&'a [u8], MaterialRuntimeError> {
        let count = usize::try_from(self.word()?).map_err(|_| MaterialRuntimeError::Bounds)?;
        self.take(count)
    }
    fn blob64(&mut self) -> Result<&'a [u8], MaterialRuntimeError> {
        let count = usize::try_from(u64::from_be_bytes(self.array()?))
            .map_err(|_| MaterialRuntimeError::Bounds)?;
        self.take(count)
    }
}
