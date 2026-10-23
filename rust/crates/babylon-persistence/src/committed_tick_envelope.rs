//! Canonical graph, state, event, choice, checkpoint and Archive component rows.

#[cfg(test)]
mod tests;

#[path = "committed_tick_envelope/envelope.rs"]
mod envelope;

pub(crate) use envelope::compose_row_families;
pub use envelope::{
    validate_committed_tick_envelope_bounds, CommittedTickEnvelopeError, CommittedTickRow,
    CommittedTickRowBatch, CommittedTickRowFamilies, CommittedTickRowFamily,
    ALL_COMMITTED_TICK_ROW_FAMILIES, COMMITTED_TICK_ROW_FAMILY_COUNT,
    MAX_COMMITTED_COMPONENT_BODY_BYTES, MAX_COMMITTED_GRAPH_ROW_BATCH_BYTES,
    MAX_COMMITTED_TICK_ROWS, MAX_COMMITTED_TICK_ROW_BATCH_BYTES,
};
