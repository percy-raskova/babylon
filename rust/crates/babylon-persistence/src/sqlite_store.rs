//! Embedded `SQLite` campaign store: physical schema, codecs, chunks and lock.
//!
//! This module publishes the Task 5 (`P3a`) foundation for the single-owner
//! campaign database: the exact nine-table `STRICT` schema, the closed versioned
//! integer registries, the canonical binary codecs, the bounded chunk table and
//! the task-scoped campaign file lock. The lifecycle owner that drives these
//! primitives arrives in Task 6 (`P3b`).

pub mod chunks;
pub mod codec;
pub mod lock;
pub mod schema;

#[cfg(test)]
mod tests;

pub use chunks::read_state_chunk;
pub use chunks::write_content_entry;
pub use chunks::write_journal_record;
pub use chunks::write_recent_detail;
pub use chunks::write_service_state;
pub use chunks::write_state_chunk;
pub use chunks::ChunkSection;
pub use chunks::ContentEntryKind;
pub use chunks::DetailFamily;
pub use chunks::JournalKind;
pub use chunks::JournalRecordInput;
pub use chunks::JournalSubject;
pub use chunks::SubjectKind;
pub use codec::decode_choice_endpoint_u128;
pub use codec::decode_money_i128;
pub use codec::decode_payload;
pub use codec::encode_choice_endpoint_u128;
pub use codec::encode_money_i128;
pub use codec::encode_payload;
pub use codec::EncodedPayload;
pub use codec::PayloadBudget;
pub use codec::PayloadCodec;
pub use codec::StoredPayload;
pub use codec::CHOICE_ENDPOINT_BYTES;
pub use codec::MAX_CHOICE_ENDPOINT;
pub use codec::MAX_CONTENT_CHUNK_BYTES;
pub use codec::MAX_PERMANENT_JOURNAL_BYTES;
pub use codec::MAX_RECENT_DETAIL_BYTES;
pub use codec::MAX_SERVICE_STATE_BYTES;
pub use codec::MAX_STATE_CHUNK_BYTES;
pub use codec::MONEY_BYTES;
pub use lock::lock_path;
pub use lock::CampaignLock;
pub use lock::SaveError;
pub use schema::configure_connection;
pub use schema::install_schema;
pub use schema::verify_installed_schema;
pub use schema::SnapshotRole;
pub use schema::BUSY_TIMEOUT;
pub use schema::SCHEMA_VERSION;
