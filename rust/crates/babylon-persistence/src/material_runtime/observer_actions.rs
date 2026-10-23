//! Full-observer semantic proof from public, authenticated accepted intents.
//! Runtime additionally proves consumption against its private command ledger.

#[cfg(test)]
mod tests;

#[path = "observer_actions/cursor.rs"]
mod cursor;

#[allow(unused_imports)]
pub(super) use cursor::reconstruct;
#[allow(unused_imports)]
use cursor::{parse, Cursor, Result};

#[allow(unused_imports)]
use super::MaterialRuntimeError;
#[allow(unused_imports)]
use babylon_kernel::{content_digest::sha256_of, replay::ReplaySessionId};
#[allow(unused_imports)]
use babylon_practice_contract::{
    admit_organizer, decode_practice_intent, encode_practice_action_id_preimage,
    encode_practice_intent, organizer_action_batch, validate_organizer_pair,
    OrderedPracticeActionBatch, OrganizerChoice, OrganizerCommand, OrganizerConfig, OrganizerState,
    PracticeIntent, MAX_PRACTICE_INTENT_CANONICAL_BYTES, MAX_RESOLVED_PRACTICE_BATCH_ITEMS,
    ORDERED_PRACTICE_ACTION_BATCH_DOMAIN_BYTES,
};
