//! Bounded, immutable chunk and journal-table writes.
//!
//! Every writer preflights the decoded payload against its table contract before
//! the statement executes, so an oversized record leaves no partial row. Chunk
//! identity is the integer `chunk_id`; `(section, ordinal)` names the manifest
//! position that later periods may share.

use rusqlite::params;
use rusqlite::Connection;

use crate::sqlite_store::codec;
use crate::sqlite_store::codec::PayloadBudget;
use crate::sqlite_store::codec::PayloadCodec;
use crate::sqlite_store::codec::StoredPayload;
use crate::sqlite_store::SaveError;

/// Closed state-chunk section registry, matching the nine restart-root sections.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum ChunkSection {
    /// Stable graph nodes and edges.
    StableGraph = 1,
    /// World registers (material, household, organizer and monetary state).
    WorldRegisters = 2,
    /// Resolver manifest and compiled definitions identity.
    ResolverManifest = 3,
    /// Prepared environment facts.
    PreparedEnvironment = 4,
    /// Replay session identity.
    ReplaySessionIdentity = 5,
    /// Deterministic random seed.
    RngSeed = 6,
    /// Captured content digest.
    ContentDigest = 7,
    /// Reference artifact digest.
    ReferenceDigest = 8,
    /// Semantic state not owned by another section.
    SemanticState = 9,
}

impl ChunkSection {
    /// Return the exact versioned integer stored in `state_chunk.section`.
    #[must_use]
    pub const fn code(self) -> i64 {
        self as i64
    }

    /// Recover a closed section from its stored integer.
    #[must_use]
    pub const fn from_code(code: i64) -> Option<Self> {
        match code {
            1 => Some(Self::StableGraph),
            2 => Some(Self::WorldRegisters),
            3 => Some(Self::ResolverManifest),
            4 => Some(Self::PreparedEnvironment),
            5 => Some(Self::ReplaySessionIdentity),
            6 => Some(Self::RngSeed),
            7 => Some(Self::ContentDigest),
            8 => Some(Self::ReferenceDigest),
            9 => Some(Self::SemanticState),
            _ => None,
        }
    }
}

/// Closed content-entry kind registry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum ContentEntryKind {
    /// Captured source rules and data.
    CapturedSource = 1,
    /// Compiled definitions derived from the captured source.
    CompiledDefinitions = 2,
    /// Package provenance and dependency identity.
    Provenance = 3,
    /// Opening metadata captured with the campaign.
    OpeningMetadata = 4,
}

impl ContentEntryKind {
    /// Return the exact versioned integer stored in `content_entry.kind`.
    #[must_use]
    pub const fn code(self) -> i64 {
        self as i64
    }
}

/// Closed recent-detail family registry: 36 receipt families plus one event stream.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum DetailFamily {
    /// Material production close.
    Production = 1,
    /// In-flight freight and capacity dispatches.
    Dispatches = 2,
    /// Freight and stock losses.
    Losses = 3,
    /// Arrived freight settlement.
    Arrivals = 4,
    /// Delivered shipments.
    Deliveries = 5,
    /// Realized production and settlement.
    Realizations = 6,
    /// Handling charges.
    Handling = 7,
    /// Local fulfillment.
    LocalFulfillments = 8,
    /// Local transfers.
    LocalTransfers = 9,
    /// Maintenance service.
    Maintenance = 10,
    /// Money transfers.
    MoneyTransfers = 11,
    /// Accrued wages.
    WageAccruals = 12,
    /// Labor use.
    LaborUse = 13,
    /// Household demand.
    HouseholdDemand = 14,
    /// Household consumption.
    HouseholdConsumption = 15,
    /// Procurement.
    Procurement = 16,
    /// Production plans.
    ProductionPlans = 17,
    /// Prices.
    Prices = 18,
    /// Income.
    Income = 19,
    /// Service performance.
    ServicePerformance = 20,
    /// Household services.
    HouseholdServices = 21,
    /// Service markets.
    ServiceMarkets = 22,
    /// Service outputs.
    ServiceOutputs = 23,
    /// Public budgets.
    PublicBudgets = 24,
    /// Taxes.
    Taxes = 25,
    /// Distributions.
    Distributions = 26,
    /// Contributions.
    Contributions = 27,
    /// Staffing members.
    StaffingMembers = 28,
    /// Member labor use.
    MemberLaborUse = 29,
    /// Installation.
    Installation = 30,
    /// Equipment wear.
    EquipmentWear = 31,
    /// Investment.
    Investment = 32,
    /// Installation decisions.
    InstallationDecisions = 33,
    /// Household time.
    HouseholdTime = 34,
    /// Aid.
    Aid = 35,
    /// Collections.
    Collections = 36,
    /// Exhaustive technical events, ordered by ordinal.
    EventChunk = 37,
}

impl DetailFamily {
    /// Every closed family in versioned order.
    pub const ALL: [Self; 37] = [
        Self::Production,
        Self::Dispatches,
        Self::Losses,
        Self::Arrivals,
        Self::Deliveries,
        Self::Realizations,
        Self::Handling,
        Self::LocalFulfillments,
        Self::LocalTransfers,
        Self::Maintenance,
        Self::MoneyTransfers,
        Self::WageAccruals,
        Self::LaborUse,
        Self::HouseholdDemand,
        Self::HouseholdConsumption,
        Self::Procurement,
        Self::ProductionPlans,
        Self::Prices,
        Self::Income,
        Self::ServicePerformance,
        Self::HouseholdServices,
        Self::ServiceMarkets,
        Self::ServiceOutputs,
        Self::PublicBudgets,
        Self::Taxes,
        Self::Distributions,
        Self::Contributions,
        Self::StaffingMembers,
        Self::MemberLaborUse,
        Self::Installation,
        Self::EquipmentWear,
        Self::Investment,
        Self::InstallationDecisions,
        Self::HouseholdTime,
        Self::Aid,
        Self::Collections,
        Self::EventChunk,
    ];

    /// Return the exact versioned integer stored in `recent_detail.family`.
    #[must_use]
    pub const fn code(self) -> i64 {
        self as i64
    }
}

/// Closed permanent-journal kind registry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum JournalKind {
    /// The exact accepted command and commitment.
    AcceptedCommand = 1,
    /// The ordered action batch consumed by a period commit.
    ResolvedBatch = 2,
    /// One governed choice receipt with selected and unselected alternatives.
    GovernedChoice = 3,
    /// One player-relevant outcome receipt.
    PlayerReceipt = 4,
    /// One compact world period summary.
    PeriodSummary = 5,
    /// One delivered or explicitly earned dossier.
    Dossier = 6,
}

impl JournalKind {
    /// Return the exact versioned integer stored in `permanent_journal.kind`.
    #[must_use]
    pub const fn code(self) -> i64 {
        self as i64
    }

    /// Recover a closed journal kind from its stored integer.
    #[must_use]
    pub const fn from_code(code: i64) -> Option<Self> {
        match code {
            1 => Some(Self::AcceptedCommand),
            2 => Some(Self::ResolvedBatch),
            3 => Some(Self::GovernedChoice),
            4 => Some(Self::PlayerReceipt),
            5 => Some(Self::PeriodSummary),
            6 => Some(Self::Dossier),
            _ => None,
        }
    }
}

/// Closed subject registry shared by journal and knowledge indexes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum SubjectKind {
    /// The controlled player.
    Player = 1,
    /// A county.
    County = 2,
    /// A place.
    Place = 3,
    /// A workplace.
    Workplace = 4,
    /// An organization.
    Organization = 5,
    /// A material or service product.
    Product = 6,
    /// A standing agreement.
    Agreement = 7,
    /// A shipment or freight obligation.
    Shipment = 8,
    /// A production or purchase commitment.
    Commitment = 9,
    /// An earned observation.
    Observation = 10,
}

impl SubjectKind {
    /// Return the exact versioned integer stored in a `subject_kind` column.
    #[must_use]
    pub const fn code(self) -> i64 {
        self as i64
    }

    /// Recover a closed subject kind from its stored integer.
    #[must_use]
    pub const fn from_code(code: i64) -> Option<Self> {
        match code {
            1 => Some(Self::Player),
            2 => Some(Self::County),
            3 => Some(Self::Place),
            4 => Some(Self::Workplace),
            5 => Some(Self::Organization),
            6 => Some(Self::Product),
            7 => Some(Self::Agreement),
            8 => Some(Self::Shipment),
            9 => Some(Self::Commitment),
            10 => Some(Self::Observation),
            _ => None,
        }
    }
}

/// One typed journal subject, always paired with its identity bytes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct JournalSubject<'a> {
    /// Closed subject kind.
    pub kind: SubjectKind,
    /// Exact typed identity bytes.
    pub id: &'a [u8],
}

/// One immutable permanent-journal record offered for insertion.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct JournalRecordInput<'a> {
    /// Positive journal sequence assigned by the extraction policy.
    pub journal_seq: u64,
    /// Closed record kind.
    pub kind: JournalKind,
    /// Period the record belongs to.
    pub period: u64,
    /// Optional durable actor identity.
    pub actor_id: Option<[u8; 8]>,
    /// Optional typed subject.
    pub subject: Option<JournalSubject<'a>>,
    /// Optional accepted-command nonce.
    pub nonce: Option<[u8; 16]>,
    /// Optional canonical idempotency key for projections such as dossiers.
    pub record_key: Option<&'a [u8]>,
    /// Opaque canonical payload bytes.
    pub payload: &'a [u8],
    /// Previous journal entry hash from the immutable chain.
    pub previous_hash: [u8; 32],
    /// This entry's canonical hash.
    pub entry_hash: [u8; 32],
}

/// Insert one bounded immutable state chunk and return its integer identity.
///
/// # Errors
///
/// Refuses decoded bytes above four MiB before any statement executes, an
/// ordinal outside the checked integer range, or a `SQLite` failure.
pub fn write_state_chunk(
    connection: &Connection,
    section: ChunkSection,
    ordinal: u32,
    raw: &[u8],
) -> Result<i64, SaveError> {
    let encoded = codec::encode_chunk_payload(PayloadBudget::StateChunk, raw)?;
    connection.execute(
        "INSERT INTO state_chunk (section, ordinal, codec, raw_len, raw_hash, payload)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
        params![
            section.code(),
            i64::from(ordinal),
            encoded.codec.code(),
            i64::from(encoded.raw_len),
            &encoded.raw_hash[..],
            encoded.payload,
        ],
    )?;
    Ok(connection.last_insert_rowid())
}

/// Read and authenticate one state chunk by its integer identity.
///
/// # Errors
///
/// Refuses a missing chunk, a payload outside the state-chunk budget, a codec or
/// length or digest mismatch, or a `SQLite` failure.
pub fn read_state_chunk(connection: &Connection, chunk_id: i64) -> Result<Vec<u8>, SaveError> {
    let (codec_code, raw_len, raw_hash, payload): (i64, i64, Vec<u8>, Vec<u8>) = connection
        .query_row(
            "SELECT codec, raw_len, raw_hash, payload FROM state_chunk WHERE chunk_id = ?1",
            params![chunk_id],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
        )?;
    let stored = StoredPayload {
        codec: PayloadCodec::from_code(codec_code)?,
        raw_len: u32::try_from(raw_len).map_err(|_| SaveError::Arithmetic {
            field: "state chunk raw length",
        })?,
        raw_hash: hash_from_row("state_chunk", &raw_hash)?,
        payload: &payload,
    };
    codec::decode_chunk_payload(PayloadBudget::StateChunk, &stored)
}

/// Read and authenticate every fragment of one content entry in ordinal order.
///
/// # Errors
///
/// Refuses an absent entry, a payload outside the content budget, a codec or
/// length or digest mismatch, or a `SQLite` failure.
pub fn read_content_entry(
    connection: &Connection,
    kind: ContentEntryKind,
    entry_key: &[u8],
) -> Result<Vec<Vec<u8>>, SaveError> {
    let mut statement = connection.prepare(
        "SELECT codec, raw_len, raw_hash, payload FROM content_entry
         WHERE kind = ?1 AND entry_key = ?2 ORDER BY ordinal",
    )?;
    let rows = statement
        .query_map(params![kind.code(), entry_key], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, i64>(1)?,
                row.get::<_, Vec<u8>>(2)?,
                row.get::<_, Vec<u8>>(3)?,
            ))
        })?
        .collect::<Result<Vec<_>, _>>()?;
    if rows.is_empty() {
        return Err(SaveError::InvalidField {
            table: "content_entry",
            field: "entry_key",
            reason: "the requested content entry is absent",
        });
    }
    let mut decoded = Vec::with_capacity(rows.len());
    for (codec_code, raw_len, raw_hash, payload) in rows {
        let stored = StoredPayload {
            codec: PayloadCodec::from_code(codec_code)?,
            raw_len: u32::try_from(raw_len).map_err(|_| SaveError::Arithmetic {
                field: "content entry raw length",
            })?,
            raw_hash: hash_from_row("content_entry", &raw_hash)?,
            payload: &payload,
        };
        decoded.push(codec::decode_chunk_payload(
            PayloadBudget::ContentEntry,
            &stored,
        )?);
    }
    Ok(decoded)
}

/// Entry key of the authored-graph opening metadata that declares a campaign
/// with no player-command surface.
pub const AUTHORED_GRAPH_ADMISSION_KEY: &[u8] = b"authored-graph-admission";

/// Insert one bounded immutable content or compiled-definition chunk.
///
/// # Errors
///
/// Refuses an empty entry key, decoded bytes above four MiB before any statement
/// executes, or a `SQLite` failure.
pub fn write_content_entry(
    connection: &Connection,
    kind: ContentEntryKind,
    entry_key: &[u8],
    ordinal: u32,
    raw: &[u8],
) -> Result<(), SaveError> {
    if entry_key.is_empty() {
        return Err(SaveError::InvalidField {
            table: "content_entry",
            field: "entry_key",
            reason: "the entry key is empty",
        });
    }
    let encoded = codec::encode_chunk_payload(PayloadBudget::ContentEntry, raw)?;
    connection.execute(
        "INSERT INTO content_entry (kind, entry_key, ordinal, codec, raw_len, raw_hash, payload)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        params![
            kind.code(),
            entry_key,
            i64::from(ordinal),
            encoded.codec.code(),
            i64::from(encoded.raw_len),
            &encoded.raw_hash[..],
            encoded.payload,
        ],
    )?;
    Ok(())
}

/// Return whether one content entry holds at least one fragment.
///
/// # Errors
///
/// Refuses a `SQLite` failure. An absent entry is not an error.
pub fn has_content_entry(
    connection: &Connection,
    kind: ContentEntryKind,
    entry_key: &[u8],
) -> Result<bool, SaveError> {
    let count: i64 = connection.query_row(
        "SELECT COUNT(*) FROM content_entry WHERE kind = ?1 AND entry_key = ?2",
        params![kind.code(), entry_key],
        |row| row.get(0),
    )?;
    Ok(count != 0)
}

/// Insert one bounded recent-detail row for a completed period.
///
/// # Errors
///
/// Refuses decoded bytes above four MiB before any statement executes, a period
/// outside the checked integer range, or a `SQLite` failure.
pub fn write_recent_detail(
    connection: &Connection,
    period: u64,
    family: DetailFamily,
    ordinal: u32,
    raw: &[u8],
) -> Result<(), SaveError> {
    let encoded = codec::encode_chunk_payload(PayloadBudget::RecentDetail, raw)?;
    connection.execute(
        "INSERT INTO recent_detail (period, family, ordinal, codec, raw_len, raw_hash, payload)
         VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
        params![
            checked_i64(period, "recent detail period")?,
            family.code(),
            i64::from(ordinal),
            encoded.codec.code(),
            i64::from(encoded.raw_len),
            &encoded.raw_hash[..],
            encoded.payload,
        ],
    )?;
    Ok(())
}

/// Insert one bounded immutable permanent-journal record.
///
/// Command-resolution metadata stays `NULL`; a later serialized owner
/// transaction records the resolved period and sequence.
///
/// # Errors
///
/// Refuses a non-positive sequence, an unpaired or empty subject, an empty
/// record key, decoded bytes above sixteen MiB before any statement executes, an
/// out-of-range period, or a `SQLite` failure.
pub fn write_journal_record(
    connection: &Connection,
    record: &JournalRecordInput<'_>,
) -> Result<(), SaveError> {
    if record.journal_seq == 0 {
        return Err(SaveError::InvalidField {
            table: "permanent_journal",
            field: "journal_seq",
            reason: "the journal sequence must be positive",
        });
    }
    let (subject_kind, subject_id) = match record.subject {
        Some(subject) => {
            if subject.id.is_empty() {
                return Err(SaveError::InvalidField {
                    table: "permanent_journal",
                    field: "subject_id",
                    reason: "the subject identity is empty",
                });
            }
            (Some(subject.kind.code()), Some(subject.id))
        }
        None => (None, None),
    };
    if record.record_key.is_some_and(<[u8]>::is_empty) {
        return Err(SaveError::InvalidField {
            table: "permanent_journal",
            field: "record_key",
            reason: "the record key is empty",
        });
    }
    let encoded = codec::encode_chunk_payload(PayloadBudget::PermanentJournal, record.payload)?;
    connection.execute(
        "INSERT INTO permanent_journal (
            journal_seq, kind, period, actor_id, subject_kind, subject_id, nonce, record_key,
            codec, raw_len, raw_hash, payload, previous_hash, entry_hash
        ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)",
        params![
            checked_i64(record.journal_seq, "journal sequence")?,
            record.kind.code(),
            checked_i64(record.period, "journal period")?,
            record.actor_id.as_ref().map(|actor| &actor[..]),
            subject_kind,
            subject_id,
            record.nonce.as_ref().map(|nonce| &nonce[..]),
            record.record_key,
            encoded.codec.code(),
            i64::from(encoded.raw_len),
            &encoded.raw_hash[..],
            encoded.payload,
            &record.previous_hash[..],
            &record.entry_hash[..],
        ],
    )?;
    Ok(())
}

/// Replace the single bounded Archive service record unconditionally.
///
/// The statement overwrites the sequence and payload rather than comparing an
/// expected sequence; callers own the ordering check.
///
/// # Errors
///
/// Refuses decoded bytes above one MiB before any statement executes, a service
/// sequence outside the checked integer range, or a `SQLite` failure.
pub fn write_service_state(
    connection: &Connection,
    service_seq: u64,
    raw: &[u8],
) -> Result<(), SaveError> {
    let encoded = codec::encode_chunk_payload(PayloadBudget::ServiceState, raw)?;
    connection.execute(
        "INSERT INTO service_state (id, service_seq, codec, raw_len, raw_hash, payload)
         VALUES (1, ?1, ?2, ?3, ?4, ?5)
         ON CONFLICT(id) DO UPDATE SET
            service_seq = excluded.service_seq,
            codec = excluded.codec,
            raw_len = excluded.raw_len,
            raw_hash = excluded.raw_hash,
            payload = excluded.payload",
        params![
            checked_i64(service_seq, "service sequence")?,
            encoded.codec.code(),
            i64::from(encoded.raw_len),
            &encoded.raw_hash[..],
            encoded.payload,
        ],
    )?;
    Ok(())
}

fn checked_i64(value: u64, field: &'static str) -> Result<i64, SaveError> {
    i64::try_from(value).map_err(|_| SaveError::Arithmetic { field })
}

fn hash_from_row(table: &'static str, bytes: &[u8]) -> Result<[u8; 32], SaveError> {
    <[u8; 32]>::try_from(bytes).map_err(|_| SaveError::CorruptPayload {
        table,
        reason: "the stored hash is not 32 bytes",
    })
}
