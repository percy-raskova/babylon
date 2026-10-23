//! Full-observer semantic proof from public, authenticated accepted intents.
//! Runtime additionally proves consumption against its private command ledger.

#[cfg(test)]
mod tests;

#[path = "observer_actions/cursor.rs"]
mod cursor;

#[cfg(test)]
use cursor::parse;
pub(super) use cursor::reconstruct;

#[cfg(test)]
use babylon_kernel::content_digest::sha256_of;
#[cfg(test)]
use babylon_kernel::replay::ReplaySessionId;
#[cfg(test)]
use babylon_practice_contract::{
    admit_organizer, encode_practice_action_id_preimage, encode_practice_intent,
    organizer_action_batch, OrganizerConfig, OrganizerState, PracticeIntent,
    ORDERED_PRACTICE_ACTION_BATCH_DOMAIN_BYTES,
};
