//! Canonical typed-row reader shared by retry reconciliation and restart.

mod source;

pub(crate) use source::{StoredTickReadSource, StoredTickRelation};

#[path = "stored_tick/rows.rs"]
mod rows;

pub(crate) use rows::{
    decode_bsl_value, decode_stable_key, CapturedArchiveReceiptRows, CapturedCheckpointRows,
    CapturedChoiceReceiptRows, CapturedEventRows, CapturedGraphState, CapturedMaterialRows,
    CheckpointSectionSources, CheckpointSections, StoredEvent,
};
