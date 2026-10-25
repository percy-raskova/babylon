//! Embedded `SQLite` campaign store: schema, codecs, chunks, lock, owner and
//! online backup export.
//!
//! This module publishes the single-owner campaign database: the exact
//! nine-table `STRICT` schema, the closed versioned integer registries, the
//! canonical binary codecs, the bounded chunk table, the task-scoped campaign
//! file lock, the create/open/accept/commit lifecycle owner and the verified
//! online backup export.

pub mod chunks;
pub mod codec;
pub mod export;
pub mod lock;
pub mod owner;
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
pub use codec::decode_chunk_payload;
pub use codec::decode_money_i128;
pub use codec::encode_choice_endpoint_u128;
pub use codec::encode_chunk_payload;
pub use codec::encode_money_i128;
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
pub use export::VerifiedExport;
pub use lock::lock_path;
pub use lock::CampaignLock;
pub use lock::SaveError;
pub use owner::AcceptanceKind;
pub use owner::AcceptanceReceipt;
pub use owner::AdmittedContent;
pub use owner::AdmittedContentEntry;
pub use owner::AdmittedOpening;
pub use owner::BuildIdentity;
pub use owner::CommandError;
pub use owner::CommitKind;
pub use owner::CommittedPeriod;
pub use owner::CurrentChunk;
pub use owner::CurrentRoot;
#[cfg(test)]
pub use owner::FaultPoint;
pub use owner::PlayerCommand;
pub use owner::PreparedJournalRecord;
pub use owner::PreparedKnowledgeGrant;
pub use owner::PreparedPeriod;
pub use owner::PreparedSubject;
pub use owner::SqliteCampaignStore;
pub use owner::StateChunk;
pub use owner::MAX_CONTENT_KEY_BYTES;
pub use owner::MAX_KNOWLEDGE_PAYLOAD_BYTES;
pub use owner::MAX_SNAPSHOT_CHUNKS;
pub use owner::MAX_SUBJECT_ID_BYTES;
pub use schema::configure_connection;
pub use schema::install_schema;
pub use schema::verify_installed_schema;
pub use schema::SnapshotRole;
pub use schema::BUSY_TIMEOUT;
pub use schema::SCHEMA_VERSION;
