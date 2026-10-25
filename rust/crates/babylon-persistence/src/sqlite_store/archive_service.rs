//! Demand-driven Archive dossier service over the single `service_state` row.
//!
//! `service_state` is one bounded record (`<= 1 MiB` decoded, `<= 256` pending
//! requests) holding the monotonically increasing request floor and the queued
//! dossier identities. Enqueue and completion run as separate serialized owner
//! transactions that check the expected `service_seq`, so a stale caller refuses
//! instead of overwriting newer work.
//!
//! Completion appends the permanent dossier journal record and removes the
//! pending request in one transaction. The published record key is the canonical
//! concatenation of request id, source period, knowledge-prefix hash, subject
//! kind, subject-id length and exact subject bytes, and the unique
//! `(kind, record_key)` index makes a retry after a lost acknowledgement return
//! the durable record instead of publishing a second one. A request is refused
//! unless the recorded knowledge prefix discloses the subject, so the service can
//! only render facts the player has already earned.

use rusqlite::params;
use rusqlite::Connection;
use rusqlite::Error as SqliteError;
use rusqlite::OptionalExtension;
use rusqlite::TransactionBehavior;

use std::fmt::Formatter;
use std::fmt::Result as FmtResult;

use babylon_kernel::content_digest;

use crate::sqlite_store::chunks;
use crate::sqlite_store::chunks::JournalKind;
use crate::sqlite_store::chunks::JournalRecordInput;
use crate::sqlite_store::chunks::JournalSubject;
use crate::sqlite_store::chunks::SubjectKind;
use crate::sqlite_store::codec;
use crate::sqlite_store::codec::PayloadBudget;
use crate::sqlite_store::codec::PayloadCodec;
use crate::sqlite_store::codec::StoredPayload;
use crate::sqlite_store::codec::MAX_PERMANENT_JOURNAL_BYTES;
use crate::sqlite_store::lock::SaveError;
use crate::sqlite_store::owner;
use crate::sqlite_store::owner::JournalInput;
use crate::sqlite_store::owner::Manifest;
use crate::sqlite_store::owner::PreparedSubject;
use crate::sqlite_store::owner::MAX_SUBJECT_ID_BYTES;

/// Largest number of dossier requests one service record may hold.
pub const MAX_PENDING_DOSSIERS: usize = 256;

/// Version tag of the canonical `service_state` payload.
const SERVICE_VERSION: u8 = 1;

/// One queued dossier request.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DossierRequest {
    request_id: u64,
    player_id: [u8; 8],
    subject: PreparedSubject,
    source_period: u64,
    knowledge_prefix_hash: [u8; 32],
}

impl DossierRequest {
    /// Admit one request inside its published field bounds.
    ///
    /// # Errors
    ///
    /// Refuses an empty or oversized subject identity.
    pub fn new(
        request_id: u64,
        player_id: [u8; 8],
        subject: PreparedSubject,
        source_period: u64,
        knowledge_prefix_hash: [u8; 32],
    ) -> Result<Self, ServiceError> {
        validate_subject(&subject)?;
        Ok(Self {
            request_id,
            player_id,
            subject,
            source_period,
            knowledge_prefix_hash,
        })
    }

    /// Return the monotonic request identity.
    #[must_use]
    pub const fn request_id(&self) -> u64 {
        self.request_id
    }

    /// Return the period the requested fact belongs to.
    #[must_use]
    pub const fn source_period(&self) -> u64 {
        self.source_period
    }

    /// Return the canonical idempotency key this request publishes under.
    #[must_use]
    pub fn record_key(&self) -> Vec<u8> {
        canonical_record_key(
            self.request_id,
            self.source_period,
            self.knowledge_prefix_hash,
            self.subject.kind,
            &self.subject.id,
        )
    }
}

/// What enqueueing one request did.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ServiceDisposition {
    /// The request was appended to the queue.
    Queued,
    /// The identical request was already pending.
    AlreadyPending,
}

/// Durable acknowledgement of one queued dossier request.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ServiceReceipt {
    /// Monotonic request identity.
    pub request_id: u64,
    /// Service sequence the acknowledgement observed.
    pub service_seq: u64,
    /// Whether the request was appended or already pending.
    pub disposition: ServiceDisposition,
}

/// One completed dossier offered for publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DossierCompletion {
    request_id: u64,
    player_id: [u8; 8],
    subject: PreparedSubject,
    source_period: u64,
    knowledge_prefix_hash: [u8; 32],
    expected_service_seq: u64,
    payload: Vec<u8>,
}

impl DossierCompletion {
    /// Admit one completion inside its published field bounds.
    ///
    /// # Errors
    ///
    /// Refuses an empty or oversized subject identity, an empty payload, or a
    /// payload above the permanent-journal allowance.
    pub fn new(
        request_id: u64,
        player_id: [u8; 8],
        subject: PreparedSubject,
        source_period: u64,
        knowledge_prefix_hash: [u8; 32],
        expected_service_seq: u64,
        payload: Vec<u8>,
    ) -> Result<Self, ServiceError> {
        validate_subject(&subject)?;
        if payload.is_empty() {
            return Err(ServiceError::InvalidField {
                field: "payload",
                reason: "the dossier payload is empty",
            });
        }
        if payload.len() > MAX_PERMANENT_JOURNAL_BYTES {
            return Err(ServiceError::PayloadTooLarge {
                limit: MAX_PERMANENT_JOURNAL_BYTES,
                actual: payload.len(),
            });
        }
        Ok(Self {
            request_id,
            player_id,
            subject,
            source_period,
            knowledge_prefix_hash,
            expected_service_seq,
            payload,
        })
    }

    /// Return the canonical idempotency key this completion publishes under.
    #[must_use]
    pub fn record_key(&self) -> Vec<u8> {
        canonical_record_key(
            self.request_id,
            self.source_period,
            self.knowledge_prefix_hash,
            self.subject.kind,
            &self.subject.id,
        )
    }
}

/// What completing one dossier request did.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PublicationDisposition {
    /// The dossier record was appended now.
    Published,
    /// The identical dossier record was already durable.
    AlreadyPublished,
}

/// Durable acknowledgement of one published dossier.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PublishedDossierReceipt {
    /// Service sequence after the completion.
    pub service_seq: u64,
    /// Journal position of the dossier record.
    pub journal_seq: u64,
    /// Period the dossier was published.
    pub period: u64,
    /// Canonical idempotency key of the published record.
    pub record_key: Vec<u8>,
    /// Whether the record was appended or already durable.
    pub disposition: PublicationDisposition,
}

/// Why the Archive service refused one request.
#[derive(Debug)]
pub enum ServiceError {
    /// The queue already holds the maximum number of pending requests.
    QueueFull {
        /// Maximum pending requests.
        limit: usize,
    },
    /// The caller's expected service sequence is stale.
    ServiceSequence {
        /// Sequence the caller expected.
        expected: u64,
        /// Sequence the service record holds.
        actual: u64,
    },
    /// No pending request carries that request identity.
    UnknownRequest {
        /// Requested identity.
        request_id: u64,
    },
    /// A request identity repeats with different source or subject identity.
    ConflictingRequest {
        /// Requested identity.
        request_id: u64,
    },
    /// A request identity does not advance the monotonic floor.
    StaleRequestId {
        /// Floor the service record holds.
        next_request_id: u64,
    },
    /// The knowledge-prefix hash is not a position on the stored chain.
    UnknownKnowledgePrefix,
    /// No earned grant discloses the subject inside the recorded prefix.
    UndisclosedSubject,
    /// The request names a period beyond the committed present.
    FuturePeriod {
        /// Highest committed period.
        current: u64,
        /// Requested period.
        requested: u64,
    },
    /// A typed field is empty or outside its contract.
    InvalidField {
        /// Field that failed admission.
        field: &'static str,
        /// Why the field was refused.
        reason: &'static str,
    },
    /// A payload exceeded its published allowance.
    PayloadTooLarge {
        /// Allowance in bytes.
        limit: usize,
        /// Supplied length.
        actual: usize,
    },
    /// The underlying store refused the write.
    Store(SaveError),
}

impl std::fmt::Display for ServiceError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::QueueFull { limit } => write!(
                formatter,
                "the Archive queue already holds {limit} pending dossier requests"
            ),
            Self::ServiceSequence { expected, actual } => write!(
                formatter,
                "the Archive service expected sequence {expected} but holds {actual}"
            ),
            Self::UnknownRequest { request_id } => write!(
                formatter,
                "dossier request {request_id} is not pending"
            ),
            Self::ConflictingRequest { request_id } => write!(
                formatter,
                "dossier request {request_id} conflicts with the pending identity"
            ),
            Self::StaleRequestId { next_request_id } => write!(
                formatter,
                "the dossier request id must be at least {next_request_id}"
            ),
            Self::UnknownKnowledgePrefix => {
                write!(formatter, "the knowledge prefix is not on the stored chain")
            }
            Self::UndisclosedSubject => write!(
                formatter,
                "no earned grant discloses the dossier subject inside its prefix"
            ),
            Self::FuturePeriod { current, requested } => write!(
                formatter,
                "the campaign is committed through period {current}; period {requested} is in the future"
            ),
            Self::InvalidField { field, reason } => {
                write!(formatter, "the Archive service refused `{field}`: {reason}")
            }
            Self::PayloadTooLarge { limit, actual } => write!(
                formatter,
                "the dossier payload is {actual} bytes; the allowance is {limit}"
            ),
            Self::Store(error) => write!(formatter, "the Archive service was refused: {error}"),
        }
    }
}

impl std::error::Error for ServiceError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Store(error) => Some(error),
            _ => None,
        }
    }
}

impl From<SaveError> for ServiceError {
    fn from(error: SaveError) -> Self {
        Self::Store(error)
    }
}

impl From<SqliteError> for ServiceError {
    fn from(error: SqliteError) -> Self {
        Self::Store(SaveError::from(error))
    }
}

/// One pending dossier identity as it is stored.
#[derive(Clone, Debug, Eq, PartialEq)]
struct PendingRequest {
    request_id: u64,
    player_id: [u8; 8],
    subject_kind: SubjectKind,
    subject_id: Vec<u8>,
    source_period: u64,
    prefix_hash: [u8; 32],
    record_key: Vec<u8>,
}

impl PendingRequest {
    fn of_request(request: &DossierRequest) -> Self {
        Self {
            request_id: request.request_id,
            player_id: request.player_id,
            subject_kind: request.subject.kind,
            subject_id: request.subject.id.clone(),
            source_period: request.source_period,
            prefix_hash: request.knowledge_prefix_hash,
            record_key: request.record_key(),
        }
    }

    fn of_completion(completion: &DossierCompletion) -> Self {
        Self {
            request_id: completion.request_id,
            player_id: completion.player_id,
            subject_kind: completion.subject.kind,
            subject_id: completion.subject.id.clone(),
            source_period: completion.source_period,
            prefix_hash: completion.knowledge_prefix_hash,
            record_key: completion.record_key(),
        }
    }
}

/// The decoded Archive service record.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct ServiceState {
    next_request_id: u64,
    pending: Vec<PendingRequest>,
}

/// Queue one dossier request inside the bounded service record.
pub(super) fn enqueue(
    connection: &mut Connection,
    committed_period: u64,
    request: &DossierRequest,
) -> Result<ServiceReceipt, ServiceError> {
    if request.request_id == 0 {
        return Err(ServiceError::InvalidField {
            field: "request_id",
            reason: "the request identity must be positive",
        });
    }
    if request.source_period > committed_period {
        return Err(ServiceError::FuturePeriod {
            current: committed_period,
            requested: request.source_period,
        });
    }
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let (service_seq, mut state) = read_service_state(&transaction)?;
    if let Some(pending) = state
        .pending
        .iter()
        .find(|pending| pending.request_id == request.request_id)
    {
        if *pending == PendingRequest::of_request(request) {
            transaction.commit()?;
            return Ok(ServiceReceipt {
                request_id: request.request_id,
                service_seq,
                disposition: ServiceDisposition::AlreadyPending,
            });
        }
        return Err(ServiceError::ConflictingRequest {
            request_id: request.request_id,
        });
    }
    if state.pending.len() >= MAX_PENDING_DOSSIERS {
        return Err(ServiceError::QueueFull {
            limit: MAX_PENDING_DOSSIERS,
        });
    }
    if request.request_id <= state.next_request_id {
        return Err(ServiceError::StaleRequestId {
            next_request_id: state.next_request_id,
        });
    }
    let position = knowledge_prefix_position(&transaction, request.knowledge_prefix_hash)?
        .ok_or(ServiceError::UnknownKnowledgePrefix)?;
    if !discloses_subject(
        &transaction,
        request.player_id,
        request.subject.kind,
        &request.subject.id,
        request.source_period,
        position,
    )? {
        return Err(ServiceError::UndisclosedSubject);
    }
    state.pending.push(PendingRequest::of_request(request));
    state.next_request_id = request.request_id;
    let next_seq = service_seq.checked_add(1).ok_or(SaveError::Arithmetic {
        field: "service sequence",
    })?;
    store_service_state(&transaction, next_seq, &state)?;
    transaction.commit()?;
    Ok(ServiceReceipt {
        request_id: request.request_id,
        service_seq: next_seq,
        disposition: ServiceDisposition::Queued,
    })
}

/// Publish one completed dossier and retire its pending request.
pub(super) fn complete(
    connection: &mut Connection,
    committed_period: u64,
    completion: &DossierCompletion,
) -> Result<PublishedDossierReceipt, ServiceError> {
    let record_key = completion.record_key();
    let transaction = connection.transaction_with_behavior(TransactionBehavior::Immediate)?;
    let published = match existing_publication(&transaction, completion, &record_key)? {
        Some(receipt) => receipt,
        None => publish_dossier(&transaction, committed_period, completion, &record_key)?,
    };
    transaction.commit()?;
    Ok(published)
}

/// Return the durable dossier a retried completion already published.
fn existing_publication(
    connection: &Connection,
    completion: &DossierCompletion,
    record_key: &[u8],
) -> Result<Option<PublishedDossierReceipt>, ServiceError> {
    let existing = connection
        .query_row(
            "SELECT journal_seq, period, raw_len, raw_hash
             FROM permanent_journal WHERE kind = ?1 AND record_key = ?2",
            params![JournalKind::Dossier.code(), record_key],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)?,
                    row.get::<_, i64>(2)?,
                    row.get::<_, Vec<u8>>(3)?,
                ))
            },
        )
        .optional()?;
    let Some((journal_seq, period, raw_len, raw_hash)) = existing else {
        return Ok(None);
    };
    let payload_hash = content_digest::sha256_of(&completion.payload);
    let payload_len = i64::from(u32::try_from(completion.payload.len()).map_err(|_| {
        ServiceError::PayloadTooLarge {
            limit: MAX_PERMANENT_JOURNAL_BYTES,
            actual: completion.payload.len(),
        }
    })?);
    if raw_len != payload_len || raw_hash.as_slice() != payload_hash {
        return Err(ServiceError::ConflictingRequest {
            request_id: completion.request_id,
        });
    }
    let (service_seq, _state) = read_service_state(connection)?;
    Ok(Some(PublishedDossierReceipt {
        service_seq,
        journal_seq: widen(journal_seq, "dossier journal sequence")?,
        period: widen(period, "dossier period")?,
        record_key: record_key.to_vec(),
        disposition: PublicationDisposition::AlreadyPublished,
    }))
}

/// Admit the pending request and append its permanent dossier record.
fn publish_dossier(
    connection: &Connection,
    committed_period: u64,
    completion: &DossierCompletion,
    record_key: &[u8],
) -> Result<PublishedDossierReceipt, ServiceError> {
    let manifest = owner::read_manifest(connection)?;
    let (service_seq, mut state) = read_service_state(connection)?;
    if service_seq != completion.expected_service_seq {
        return Err(ServiceError::ServiceSequence {
            expected: completion.expected_service_seq,
            actual: service_seq,
        });
    }
    let position = knowledge_prefix_position(connection, completion.knowledge_prefix_hash)?
        .ok_or(ServiceError::UnknownKnowledgePrefix)?;
    let index = pending_index(&state, completion)?;
    if completion.source_period > committed_period {
        return Err(ServiceError::FuturePeriod {
            current: committed_period,
            requested: completion.source_period,
        });
    }
    if !discloses_subject(
        connection,
        completion.player_id,
        completion.subject.kind,
        &completion.subject.id,
        completion.source_period,
        position,
    )? {
        return Err(ServiceError::UndisclosedSubject);
    }
    let (journal_seq, period) = append_dossier(
        connection,
        &manifest,
        committed_period,
        completion,
        record_key,
    )?;
    state.pending.remove(index);
    let next_seq = service_seq.checked_add(1).ok_or(SaveError::Arithmetic {
        field: "service sequence",
    })?;
    store_service_state(connection, next_seq, &state)?;
    Ok(PublishedDossierReceipt {
        service_seq: next_seq,
        journal_seq,
        period,
        record_key: record_key.to_vec(),
        disposition: PublicationDisposition::Published,
    })
}

/// Locate the pending request and confirm the completion repeats its identity.
fn pending_index(
    state: &ServiceState,
    completion: &DossierCompletion,
) -> Result<usize, ServiceError> {
    let index = state
        .pending
        .iter()
        .position(|pending| pending.request_id == completion.request_id)
        .ok_or(ServiceError::UnknownRequest {
            request_id: completion.request_id,
        })?;
    if state.pending[index] != PendingRequest::of_completion(completion) {
        return Err(ServiceError::ConflictingRequest {
            request_id: completion.request_id,
        });
    }
    Ok(index)
}

/// Append the permanent dossier record and advance the journal tail.
fn append_dossier(
    connection: &Connection,
    manifest: &Manifest,
    committed_period: u64,
    completion: &DossierCompletion,
    record_key: &[u8],
) -> Result<(u64, u64), ServiceError> {
    let journal_seq = manifest
        .journal_tail_seq
        .checked_add(1)
        .ok_or(SaveError::Arithmetic {
            field: "journal sequence",
        })?;
    // A dossier is published between period summaries, so it belongs to the next
    // period boundary. Recording the committed period would place a later record
    // behind its own summary, which the replay chain refuses.
    let period = committed_period
        .checked_add(1)
        .ok_or(SaveError::Arithmetic {
            field: "dossier period",
        })?;
    let payload = &completion.payload;
    let raw_len = u32::try_from(payload.len()).map_err(|_| ServiceError::PayloadTooLarge {
        limit: MAX_PERMANENT_JOURNAL_BYTES,
        actual: payload.len(),
    })?;
    let raw_hash = content_digest::sha256_of(payload);
    let subject = (completion.subject.kind, completion.subject.id.as_slice());
    let entry_hash = owner::journal_entry_hash(&JournalInput {
        journal_seq,
        kind: JournalKind::Dossier,
        period,
        actor_id: None,
        subject: Some(subject),
        nonce: None,
        record_key: Some(record_key),
        raw_len,
        raw_hash,
        previous_hash: manifest.journal_tail_hash,
    })?;
    chunks::write_journal_record(
        connection,
        &JournalRecordInput {
            journal_seq,
            kind: JournalKind::Dossier,
            period,
            actor_id: None,
            subject: Some(JournalSubject {
                kind: subject.0,
                id: subject.1,
            }),
            nonce: None,
            record_key: Some(record_key),
            payload,
            previous_hash: manifest.journal_tail_hash,
            entry_hash,
        },
    )?;
    connection.execute(
        "UPDATE save_manifest SET journal_tail_seq = ?1, journal_tail_hash = ?2 WHERE id = 1",
        params![
            i64::try_from(journal_seq).map_err(|_| SaveError::Arithmetic {
                field: "journal sequence",
            })?,
            &entry_hash[..]
        ],
    )?;
    Ok((journal_seq, period))
}

/// Read every pending dossier request of one campaign.
pub(super) fn pending(connection: &Connection) -> Result<Vec<DossierRequest>, ServiceError> {
    let (_, state) = read_service_state(connection)?;
    state
        .pending
        .into_iter()
        .map(|pending| {
            DossierRequest::new(
                pending.request_id,
                pending.player_id,
                PreparedSubject {
                    kind: pending.subject_kind,
                    id: pending.subject_id,
                },
                pending.source_period,
                pending.prefix_hash,
            )
        })
        .collect()
}

/// Return the exact canonical idempotency key of one dossier.
fn canonical_record_key(
    request_id: u64,
    source_period: u64,
    knowledge_prefix_hash: [u8; 32],
    subject_kind: SubjectKind,
    subject_id: &[u8],
) -> Vec<u8> {
    let mut key = Vec::with_capacity(8 + 8 + 32 + 4 + 4 + subject_id.len());
    key.extend_from_slice(&request_id.to_be_bytes());
    key.extend_from_slice(&source_period.to_be_bytes());
    key.extend_from_slice(&knowledge_prefix_hash);
    key.extend_from_slice(
        &u32::try_from(subject_kind.code())
            .unwrap_or(u32::MAX)
            .to_be_bytes(),
    );
    key.extend_from_slice(
        &u32::try_from(subject_id.len())
            .unwrap_or(u32::MAX)
            .to_be_bytes(),
    );
    key.extend_from_slice(subject_id);
    key
}

fn validate_subject(subject: &PreparedSubject) -> Result<(), ServiceError> {
    if subject.id.is_empty() {
        return Err(ServiceError::InvalidField {
            field: "subject_id",
            reason: "the subject identity is empty",
        });
    }
    if subject.id.len() > MAX_SUBJECT_ID_BYTES {
        return Err(ServiceError::InvalidField {
            field: "subject_id",
            reason: "the subject identity exceeds one KiB",
        });
    }
    Ok(())
}

/// Resolve a knowledge-prefix hash to its chain position.
fn knowledge_prefix_position(
    connection: &Connection,
    prefix_hash: [u8; 32],
) -> Result<Option<u64>, ServiceError> {
    if prefix_hash == [0_u8; 32] {
        return Ok(Some(0));
    }
    let stored = connection
        .query_row(
            "SELECT knowledge_seq FROM knowledge_grant WHERE entry_hash = ?1",
            params![&prefix_hash[..]],
            |row| row.get::<_, i64>(0),
        )
        .optional()?;
    stored
        .map(|seq| widen(seq, "knowledge sequence"))
        .transpose()
}

/// Whether the recorded prefix discloses one subject by its source period.
fn discloses_subject(
    connection: &Connection,
    player_id: [u8; 8],
    subject_kind: SubjectKind,
    subject_id: &[u8],
    source_period: u64,
    prefix_position: u64,
) -> Result<bool, ServiceError> {
    let count: i64 = connection.query_row(
        "SELECT COUNT(*) FROM knowledge_grant
         WHERE player_id = ?1 AND subject_kind = ?2 AND subject_id = ?3
           AND acquired_period <= ?4 AND knowledge_seq <= ?5",
        params![
            &player_id[..],
            subject_kind.code(),
            subject_id,
            i64::try_from(source_period).map_err(|_| SaveError::Arithmetic {
                field: "source period",
            })?,
            i64::try_from(prefix_position).map_err(|_| SaveError::Arithmetic {
                field: "knowledge prefix",
            })?,
        ],
        |row| row.get(0),
    )?;
    Ok(count > 0)
}

fn read_service_state(connection: &Connection) -> Result<(u64, ServiceState), ServiceError> {
    let row = connection
        .query_row(
            "SELECT service_seq, codec, raw_len, raw_hash, payload
             FROM service_state WHERE id = 1",
            [],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)?,
                    row.get::<_, i64>(2)?,
                    row.get::<_, Vec<u8>>(3)?,
                    row.get::<_, Vec<u8>>(4)?,
                ))
            },
        )
        .optional()?;
    let Some((service_seq, codec_code, raw_len, raw_hash, payload)) = row else {
        return Ok((0, ServiceState::default()));
    };
    let raw = codec::decode_chunk_payload(
        PayloadBudget::ServiceState,
        &StoredPayload {
            codec: PayloadCodec::from_code(codec_code)?,
            raw_len: u32::try_from(raw_len).map_err(|_| SaveError::CorruptPayload {
                table: "service_state",
                reason: "the stored decoded length is out of range",
            })?,
            raw_hash: <[u8; 32]>::try_from(raw_hash.as_slice()).map_err(|_| {
                SaveError::CorruptPayload {
                    table: "service_state",
                    reason: "the stored hash is not 32 bytes",
                }
            })?,
            payload: &payload,
        },
    )?;
    Ok((widen(service_seq, "service sequence")?, decode_state(&raw)?))
}

fn store_service_state(
    connection: &Connection,
    service_seq: u64,
    state: &ServiceState,
) -> Result<(), ServiceError> {
    let encoded = encode_state(state);
    chunks::write_service_state(connection, service_seq, &encoded)?;
    Ok(())
}

fn encode_state(state: &ServiceState) -> Vec<u8> {
    let mut bytes = Vec::new();
    bytes.push(SERVICE_VERSION);
    bytes.extend_from_slice(&state.next_request_id.to_be_bytes());
    bytes.extend_from_slice(
        &u16::try_from(state.pending.len())
            .unwrap_or(u16::MAX)
            .to_be_bytes(),
    );
    for pending in &state.pending {
        bytes.extend_from_slice(&pending.request_id.to_be_bytes());
        bytes.extend_from_slice(&pending.player_id);
        bytes.push(subject_kind_integer(pending.subject_kind));
        push_blob(&mut bytes, &pending.subject_id);
        bytes.extend_from_slice(&pending.source_period.to_be_bytes());
        bytes.extend_from_slice(&pending.prefix_hash);
        push_blob(&mut bytes, &pending.record_key);
    }
    bytes
}

fn decode_state(bytes: &[u8]) -> Result<ServiceState, ServiceError> {
    let mut reader = ByteReader::new(bytes);
    let version = reader.u8()?;
    if version != SERVICE_VERSION {
        return Err(ServiceError::Store(SaveError::CorruptPayload {
            table: "service_state",
            reason: "the stored payload version is outside the closed registry",
        }));
    }
    let next_request_id = reader.u64()?;
    let count = usize::from(reader.u16()?);
    if count > MAX_PENDING_DOSSIERS {
        return Err(ServiceError::Store(SaveError::CorruptPayload {
            table: "service_state",
            reason: "the stored pending count exceeds its published bound",
        }));
    }
    let mut pending = Vec::with_capacity(count);
    let mut previous = 0_u64;
    for _ in 0..count {
        let request_id = reader.u64()?;
        if request_id <= previous || request_id > next_request_id {
            return Err(ServiceError::Store(SaveError::CorruptPayload {
                table: "service_state",
                reason: "the stored request identities are not ordered or inside the floor",
            }));
        }
        previous = request_id;
        let player_id = reader.array::<8>()?;
        let subject_kind = subject_kind_of(reader.u8()?)?;
        let subject_id = reader.blob()?;
        let source_period = reader.u64()?;
        let prefix_hash = reader.array::<32>()?;
        let record_key = reader.blob()?;
        pending.push(PendingRequest {
            request_id,
            player_id,
            subject_kind,
            subject_id,
            source_period,
            prefix_hash,
            record_key,
        });
    }
    if !reader.is_empty() {
        return Err(ServiceError::Store(SaveError::CorruptPayload {
            table: "service_state",
            reason: "the stored payload has trailing bytes",
        }));
    }
    Ok(ServiceState {
        next_request_id,
        pending,
    })
}

fn subject_kind_integer(kind: SubjectKind) -> u8 {
    u8::try_from(kind.code()).unwrap_or(u8::MAX)
}

fn subject_kind_of(code: u8) -> Result<SubjectKind, ServiceError> {
    SubjectKind::from_code(i64::from(code)).ok_or_else(|| {
        ServiceError::Store(SaveError::CorruptPayload {
            table: "service_state",
            reason: "the stored subject kind is outside the closed registry",
        })
    })
}

fn push_blob(bytes: &mut Vec<u8>, blob: &[u8]) {
    bytes.extend_from_slice(&u32::try_from(blob.len()).unwrap_or(u32::MAX).to_be_bytes());
    bytes.extend_from_slice(blob);
}

fn widen(value: i64, field: &'static str) -> Result<u64, ServiceError> {
    u64::try_from(value).map_err(|_| {
        SaveError::CorruptPayload {
            table: field,
            reason: "the stored integer is negative",
        }
        .into()
    })
}

/// Strict big-endian reader for the canonical service payload.
struct ByteReader<'a> {
    bytes: &'a [u8],
    offset: usize,
}

impl<'a> ByteReader<'a> {
    const fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn take(&mut self, width: usize) -> Result<&'a [u8], ServiceError> {
        let end = self.offset.checked_add(width).ok_or(ServiceError::Store(
            SaveError::CorruptPayload {
                table: "service_state",
                reason: "the stored payload offset overflows",
            },
        ))?;
        let slice = self.bytes.get(self.offset..end).ok_or(ServiceError::Store(
            SaveError::CorruptPayload {
                table: "service_state",
                reason: "the stored payload is truncated",
            },
        ))?;
        self.offset = end;
        Ok(slice)
    }

    fn u8(&mut self) -> Result<u8, ServiceError> {
        let slice = self.take(1)?;
        slice
            .first()
            .copied()
            .ok_or(ServiceError::Store(SaveError::CorruptPayload {
                table: "service_state",
                reason: "the stored payload is truncated",
            }))
    }

    fn u16(&mut self) -> Result<u16, ServiceError> {
        <[u8; 2]>::try_from(self.take(2)?)
            .map(u16::from_be_bytes)
            .map_err(|_| {
                ServiceError::Store(SaveError::CorruptPayload {
                    table: "service_state",
                    reason: "the stored payload is truncated",
                })
            })
    }

    fn u64(&mut self) -> Result<u64, ServiceError> {
        <[u8; 8]>::try_from(self.take(8)?)
            .map(u64::from_be_bytes)
            .map_err(|_| {
                ServiceError::Store(SaveError::CorruptPayload {
                    table: "service_state",
                    reason: "the stored payload is truncated",
                })
            })
    }

    fn array<const WIDTH: usize>(&mut self) -> Result<[u8; WIDTH], ServiceError> {
        <[u8; WIDTH]>::try_from(self.take(WIDTH)?).map_err(|_| {
            ServiceError::Store(SaveError::CorruptPayload {
                table: "service_state",
                reason: "the stored payload is truncated",
            })
        })
    }

    fn blob(&mut self) -> Result<Vec<u8>, ServiceError> {
        let width = usize::try_from(u32::from_be_bytes(self.array::<4>()?)).map_err(|_| {
            ServiceError::Store(SaveError::CorruptPayload {
                table: "service_state",
                reason: "the stored blob width is out of range",
            })
        })?;
        Ok(self.take(width)?.to_vec())
    }

    const fn is_empty(&self) -> bool {
        self.offset == self.bytes.len()
    }
}
