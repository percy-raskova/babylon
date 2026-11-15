//! Store positive positions at both period boundaries under their single scoped node key.
use super::labor_facts::LaborPositionFact;
use super::JournalError;
use serde::{Serialize, Serializer};
use std::collections::BTreeMap;

/// PostgreSQL consumes decimal strings exactly, including the full unsigned microhour range.
#[derive(Clone, Copy)]
struct MicroHours(u128);

impl Serialize for MicroHours {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.collect_str(&self.0)
    }
}

#[derive(Default, Serialize)]
pub(super) struct PositionPair {
    node_ordinal: i64,
    opening_quantity: Option<u64>,
    opening_recorded_micro_hours: Option<MicroHours>,
    opening_unknown_opening: Option<bool>,
    closing_quantity: Option<u64>,
    closing_recorded_micro_hours: Option<MicroHours>,
    closing_unknown_opening: Option<bool>,
}

/// Keep the receipt-derived logical order and fingerprint independent of the physical layout.
pub(super) fn pairs(positions: &[LaborPositionFact]) -> Result<Vec<PositionPair>, JournalError> {
    let mut pairs = BTreeMap::new();
    for position in positions {
        let row = pairs
            .entry(position.node_ordinal)
            .or_insert_with(|| PositionPair {
                node_ordinal: position.node_ordinal,
                ..PositionPair::default()
            });
        let (quantity, hours, unknown) = match position.side {
            "opening" => (
                &mut row.opening_quantity,
                &mut row.opening_recorded_micro_hours,
                &mut row.opening_unknown_opening,
            ),
            "closing" => (
                &mut row.closing_quantity,
                &mut row.closing_recorded_micro_hours,
                &mut row.closing_unknown_opening,
            ),
            _ => return Err(JournalError::Projection),
        };
        if quantity.replace(position.quantity).is_some() {
            return Err(JournalError::Projection);
        }
        *hours = Some(MicroHours(position.recorded_micro_hours));
        *unknown = Some(position.unknown_opening);
    }
    Ok(pairs.into_values().collect())
}
