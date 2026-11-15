//! Versioned PostgreSQL money movement facts from authenticated committed receipts.
//! The database owner publishes; the full observer can only read. This journal never
//! participates in adjudication. All micros and SQL sums are exact decimal strings.
mod model;
mod storage;
#[cfg(test)]
mod tests;

pub use model::{
    derive_movements, JournalError, MoneyEndpoint, MoneyLocationKind, MoneyMovement, MoneyPurpose,
    MoneyReference, MoneyReferenceKind, MoneyTotal, PublishReport,
};
pub(crate) use storage::VIEWS;
pub use storage::{MoneyJournalWriter, MONEY_DETAIL_RETENTION_SQL};
