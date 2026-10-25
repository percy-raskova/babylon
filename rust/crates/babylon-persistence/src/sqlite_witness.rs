//! Temporary P1 two-period persistence witness for the embedded campaign store.
//!
//! This module is throwaway scaffolding for the PER-354 architecture reset. It
//! proves that canonical period frames survive a bounded `SQLite` commit, cold
//! reopen, scoped read and online export without changing their identities.
//! Task 6 moves these contracts onto the production campaign store and deletes
//! this module. It is not a backend interface.

mod store;
#[cfg(test)]
mod tests;

pub use store::SqliteWitnessStore;
pub use store::WitnessAcceptance;
pub use store::WitnessAcceptanceKind;
pub use store::WitnessCommitKind;
pub use store::WitnessCommitReceipt;
pub use store::WitnessError;
pub use store::WitnessExportReport;
pub use store::WitnessJournalEntry;
pub use store::WitnessJournalKind;
pub use store::WitnessKnowledgeGrant;
pub use store::WitnessPeriodCommit;
pub use store::WitnessStorageFootprint;
pub use store::MAX_WITNESS_JOURNAL_PAYLOAD_BYTES;
pub use store::MAX_WITNESS_OPENING_BYTES;
pub use store::MAX_WITNESS_RECEIPT_BYTES;
pub use store::MAX_WITNESS_REGISTER_BYTES;
pub use store::MAX_WITNESS_SCOPED_PAYLOAD_BYTES;
pub use store::WITNESS_NONCE_BYTES;
pub use store::WITNESS_SCHEMA_VERSION;
