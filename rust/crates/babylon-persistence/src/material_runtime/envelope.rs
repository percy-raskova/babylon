//! Aggregate framing keeps each component's own independently checked bound.

use super::{MaterialRuntimeError, FOUNDATION_DOMAIN};
use crate::semantic_codec::MAX_CAMPAIGN_FOUNDATION_BYTES;
use babylon_tick::material_world::MAX_MATERIAL_WORLD_REGISTER_BYTES;

const FIXED_FRAMING_BYTES: usize = FOUNDATION_DOMAIN.len() + 4 + 9 + 32 + 3 * 8;
const MAX_PRESET_BYTES: usize = 128;

/// Complete framing of independently bounded graph and material components.
/// The captured source catalog occurs once, inside the graph foundation.
pub const MAX_MATERIAL_FOUNDATION_BYTES: usize = FIXED_FRAMING_BYTES
    + MAX_PRESET_BYTES
    + MAX_CAMPAIGN_FOUNDATION_BYTES
    + MAX_MATERIAL_WORLD_REGISTER_BYTES;

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
}
