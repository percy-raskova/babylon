//! Full-observer semantic proof from public, authenticated accepted intents.
//! Runtime additionally proves consumption against its private command ledger.

#[cfg(test)]
mod tests;

#[path = "observer_actions/cursor.rs"]
mod cursor;

pub(super) use cursor::reconstruct;
