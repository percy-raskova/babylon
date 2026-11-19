//! Store positive positions at both period boundaries under their single scoped node key.
use super::labor_facts::{LaborNodeFact, LaborPositionFact};
use super::JournalError;
use serde::{Serialize, Serializer};

/// PostgreSQL consumes decimal strings exactly, including the full unsigned microhour range.
#[derive(Clone, Copy)]
struct MicroHours(u128);

impl Serialize for MicroHours {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.collect_str(&self.0)
    }
}

#[derive(Default, Serialize)]
struct PositionPair {
    opening_quantity: Option<u64>,
    opening_recorded_micro_hours: Option<MicroHours>,
    opening_unknown_opening: Option<bool>,
    closing_quantity: Option<u64>,
    closing_recorded_micro_hours: Option<MicroHours>,
    closing_unknown_opening: Option<bool>,
}

#[derive(Serialize)]
pub(super) struct NodeWithPositions<'a> {
    #[serde(flatten)]
    node: &'a LaborNodeFact,
    #[serde(flatten)]
    positions: PositionPair,
}

/// Attach each positive boundary to its actual node without changing canonical fact order.
pub(super) fn attach<'a>(
    nodes: &'a [LaborNodeFact],
    positions: &[LaborPositionFact],
) -> Result<Vec<NodeWithPositions<'a>>, JournalError> {
    let mut rows: Vec<_> = nodes
        .iter()
        .map(|node| NodeWithPositions {
            node,
            positions: PositionPair::default(),
        })
        .collect();
    for position in positions {
        if position.quantity == 0 {
            return Err(JournalError::Projection);
        }
        let idx = usize::try_from(position.node_ordinal).map_err(|_| JournalError::Projection)?;
        let row = rows
            .get_mut(idx)
            .filter(|row| row.node.node_ordinal == position.node_ordinal)
            .ok_or(JournalError::Projection)?;
        let row = &mut row.positions;
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
    Ok(rows)
}
