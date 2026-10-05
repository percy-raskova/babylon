//! Aggregate framing keeps each component's own independently checked bound.

use super::{MaterialRuntimeError, FOUNDATION_DOMAIN};
use crate::semantic_codec::MAX_CAMPAIGN_FOUNDATION_BYTES;
use babylon_tick::material_world::MAX_MATERIAL_WORLD_REGISTER_BYTES;

const FIXED_FRAMING_BYTES: usize = FOUNDATION_DOMAIN.len() + 4 + 9 + 32 + 3 * 8;
const MAX_PRESET_BYTES: usize = 128;

/// Explicit Derived complete framing ceiling for the approved component bounds.
/// The source catalog occurs once, inside the graph foundation.
pub const MAX_MATERIAL_FOUNDATION_BYTES: usize = 1_067_109_101;

pub(super) fn material_foundation_length(
    preset: usize,
    graph: usize,
    register: usize,
) -> Result<usize, MaterialRuntimeError> {
    if !(1..=MAX_PRESET_BYTES).contains(&preset)
        || !(1..=MAX_CAMPAIGN_FOUNDATION_BYTES).contains(&graph)
        || !(1..=MAX_MATERIAL_WORLD_REGISTER_BYTES).contains(&register)
    {
        return Err(MaterialRuntimeError::Bounds);
    }
    FIXED_FRAMING_BYTES
        .checked_add(preset)
        .and_then(|length| length.checked_add(graph))
        .and_then(|length| length.checked_add(register))
        .filter(|length| *length <= MAX_MATERIAL_FOUNDATION_BYTES)
        .ok_or(MaterialRuntimeError::Bounds)
}

/// Borrow current canonical components; only the fixed framing is owned.
pub(super) struct CanonicalMaterialFoundation<'a> {
    duration: [u8; 9],
    content_digest: &'a [u8; 32],
    sections: [&'a [u8]; 3],
    lengths: [[u8; 8]; 3],
    length: usize,
}
impl<'a> CanonicalMaterialFoundation<'a> {
    pub(super) fn new(
        preset: &'a [u8],
        duration: babylon_kernel::clock::CampaignDuration,
        content_digest: &'a [u8; 32],
        graph: &'a [u8],
        register: &'a [u8],
    ) -> Result<Self, MaterialRuntimeError> {
        let length = material_foundation_length(preset.len(), graph.len(), register.len())?;
        let sections = [preset, graph, register];
        let mut lengths = [[0; 8]; 3];
        for (prefix, section) in lengths.iter_mut().zip(sections) {
            *prefix = u64::try_from(section.len())
                .map_err(|_| MaterialRuntimeError::Bounds)?
                .to_be_bytes();
        }
        Ok(Self {
            duration: duration
                .canonical_bytes()
                .map_err(|_| MaterialRuntimeError::Bounds)?,
            content_digest,
            sections,
            lengths,
            length,
        })
    }
    fn parts(&self) -> [&[u8]; 10] {
        const VERSION: [u8; 4] = 3_u32.to_be_bytes();
        [
            FOUNDATION_DOMAIN,
            &VERSION,
            &self.duration,
            self.content_digest,
            &self.lengths[0],
            self.sections[0],
            &self.lengths[1],
            self.sections[1],
            &self.lengths[2],
            self.sections[2],
        ]
    }
    pub(super) const fn len(&self) -> usize {
        self.length
    }
    pub(super) fn digest(&self) -> [u8; 32] {
        use sha2::{Digest, Sha256};
        let mut hasher = Sha256::new();
        for part in self.parts() {
            hasher.update(part);
        }
        hasher.finalize().into()
    }
    pub(super) fn matches_bytes(&self, bytes: &[u8]) -> bool {
        let mut remaining = bytes;
        for part in self.parts() {
            let Some(tail) = remaining.strip_prefix(part) else {
                return false;
            };
            remaining = tail;
        }
        remaining.is_empty()
    }
    pub(super) fn matches_encoding(&self, other: &CanonicalMaterialFoundation<'_>) -> bool {
        self.length == other.length
            && self
                .parts()
                .into_iter()
                .zip(other.parts())
                .all(|(left, right)| left == right)
    }
    pub(super) fn export(&self) -> Result<Vec<u8>, MaterialRuntimeError> {
        let mut bytes = Vec::new();
        bytes.try_reserve_exact(self.length).map_err(|_| {
            MaterialRuntimeError::Graph(crate::runtime::RustPersistenceRuntimeError::Allocation {
                field: "material foundation export",
                requested: self.length,
            })
        })?;
        for part in self.parts() {
            bytes.extend_from_slice(part);
        }
        if bytes.len() != self.length {
            return Err(MaterialRuntimeError::Bounds);
        }
        Ok(bytes)
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn measured_national_register_fits_the_current_foundation_envelope() {
        // Actual native register measurement; this is a byte-bound witness,
        // not a fabricated valid graph foundation or register.
        let register_bytes = 240_132_229;
        let length = super::material_foundation_length(14, 4096, register_bytes).unwrap();
        assert_eq!(
            length,
            super::super::FOUNDATION_DOMAIN.len() + 4 + 9 + 32 + 3 * 8 + 14 + 4096 + register_bytes
        );
    }

    #[test]
    fn aggregate_room_never_admits_an_oversized_or_absent_component() {
        use babylon_tick::material_world::MAX_MATERIAL_WORLD_REGISTER_BYTES;
        assert!(super::material_foundation_length(0, 1, 1).is_err());
        assert!(super::material_foundation_length(129, 1, 1).is_err());
        assert!(super::material_foundation_length(1, 67_108_865, 1).is_err());
        assert!(
            super::material_foundation_length(1, 1, MAX_MATERIAL_WORLD_REGISTER_BYTES + 1).is_err()
        );
        assert!(super::material_foundation_length(1, 0, 1).is_err());
        assert!(super::material_foundation_length(1, 1, 0).is_err());
        assert!(super::material_foundation_length(1, usize::MAX, 1).is_err());
    }
    #[test]
    fn measured_household_foundation_and_maximum_components_fit_exactly() {
        assert_eq!(
            super::material_foundation_length(14, 57_018_148, 284_889_820).unwrap(),
            341_908_091
        );
        assert_eq!(
            super::material_foundation_length(128, 67_108_864, 1_000_000_000).unwrap(),
            super::MAX_MATERIAL_FOUNDATION_BYTES
        );
        assert_eq!(super::MAX_MATERIAL_FOUNDATION_BYTES, 1_067_109_101);
        assert!(super::material_foundation_length(129, 67_108_864, 1_000_000_000).is_err());
        assert!(super::material_foundation_length(128, 67_108_865, 1_000_000_000).is_err());
        assert!(super::material_foundation_length(128, 67_108_864, 1_000_000_001).is_err());
    }

    #[test]
    fn streamed_framing_matches_exact_current_export_and_digest() {
        use babylon_kernel::{clock::CampaignDuration, content_digest::sha256_of};
        for duration in [
            CampaignDuration::Continuous,
            CampaignDuration::Finite { final_period: 16 },
        ] {
            // These are framing witnesses, not admitted graph/register fixtures.
            let content = [19; 32];
            let preset = b"framing-control";
            let graph = b"graph-section";
            let register = b"register-section";
            let encoding = super::CanonicalMaterialFoundation::new(
                preset, duration, &content, graph, register,
            )
            .unwrap();
            let mut expected = Vec::new();
            expected.extend_from_slice(super::super::FOUNDATION_DOMAIN);
            expected.extend_from_slice(&3_u32.to_be_bytes());
            expected.extend_from_slice(&duration.canonical_bytes().unwrap());
            expected.extend_from_slice(&content);
            for part in [preset.as_slice(), graph.as_slice(), register.as_slice()] {
                expected.extend_from_slice(&u64::try_from(part.len()).unwrap().to_be_bytes());
                expected.extend_from_slice(part);
            }
            assert_eq!(encoding.len(), expected.len());
            assert_eq!(encoding.digest(), sha256_of(&expected));
            assert_eq!(encoding.export().unwrap(), expected);
            assert!(encoding.matches_bytes(&expected));
            let same = super::CanonicalMaterialFoundation::new(
                preset, duration, &content, graph, register,
            )
            .unwrap();
            assert!(encoding.matches_encoding(&same));
            let changed = super::CanonicalMaterialFoundation::new(
                preset,
                duration,
                &content,
                graph,
                b"different-register-section",
            )
            .unwrap();
            assert!(!encoding.matches_encoding(&changed));
        }
    }

    #[test]
    fn streamed_equality_refuses_any_damage_truncation_or_trailing_bytes() {
        use babylon_kernel::clock::CampaignDuration;
        let content = [47; 32];
        let encoding = super::CanonicalMaterialFoundation::new(
            b"equality-control",
            CampaignDuration::Continuous,
            &content,
            b"graph-framing",
            b"register-framing",
        )
        .unwrap();
        let bytes = encoding.export().unwrap();
        for index in 0..bytes.len() {
            let mut damaged = bytes.clone();
            damaged[index] ^= 1;
            assert!(!encoding.matches_bytes(&damaged), "damage at byte {index}");
            assert!(
                !encoding.matches_bytes(&bytes[..index]),
                "truncated at byte {index}"
            );
        }
        let mut trailing = bytes;
        trailing.push(0);
        assert!(!encoding.matches_bytes(&trailing));
        for final_period in [0, u64::MAX] {
            assert!(super::CanonicalMaterialFoundation::new(
                b"equality-control",
                CampaignDuration::Finite { final_period },
                &content,
                b"graph-framing",
                b"register-framing",
            )
            .is_err());
        }
    }
}
