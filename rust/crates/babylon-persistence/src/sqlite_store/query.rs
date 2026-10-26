//! Scoped, fog-safe player query and bounded history pagination.
//!
//! Every read is bound to one [`PlayerScope`]: a player identity, an as-of
//! period, a knowledge prefix and a journal prefix. A fact is disclosed only when
//! it was acquired by that player no later than the as-of period, its grant is
//! inside the knowledge prefix, and its source journal record is inside the
//! journal prefix. The intersection of those bounds means an inconsistent scope
//! can only over-restrict a read, never disclose a fact the scope has not earned.
//!
//! Reads select indexed rows only. [`ReadCost`] counts the stored rows one read
//! decoded, so a bounded-read assertion over it can fail when a read widens. A
//! scoped county or workplace selection has no chunk-table access path at all:
//! `sqlite_store::tests` proves that structurally over this module's source,
//! because a counter for an access that never happens cannot measure anything.

use rusqlite::params;
use rusqlite::Connection;
use rusqlite::Error as SqliteError;
use rusqlite::OptionalExtension;

use std::fmt::Formatter;
use std::fmt::Result as FmtResult;

use babylon_kernel::content_digest;

use crate::sqlite_store::chunks::JournalKind;
use crate::sqlite_store::chunks::SubjectKind;
use crate::sqlite_store::codec;
use crate::sqlite_store::codec::PayloadBudget;
use crate::sqlite_store::codec::PayloadCodec;
use crate::sqlite_store::codec::StoredPayload;
use crate::sqlite_store::lock::SaveError;
use crate::sqlite_store::owner;
use crate::sqlite_store::owner::KnowledgeInput;
use crate::sqlite_store::owner::Manifest;
use crate::sqlite_store::owner::MAX_KNOWLEDGE_PAYLOAD_BYTES;
use crate::sqlite_store::owner::MAX_SUBJECT_ID_BYTES;

/// Default number of journal records one history page returns.
pub const DEFAULT_HISTORY_LIMIT: u16 = 50;

/// Largest number of journal records one history page can return.
pub const MAX_HISTORY_LIMIT: u16 = 200;

/// Largest number of journal records one relationship projection returns.
pub const MAX_RELATIONSHIP_RECORDS: usize = 256;

/// Exact stored rows one scoped read decoded.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct ReadCost {
    rows_visited: u32,
}

impl ReadCost {
    /// Return how many stored rows the read decoded.
    #[must_use]
    pub const fn rows_visited(self) -> u32 {
        self.rows_visited
    }

    fn row(&mut self) {
        self.rows_visited = self.rows_visited.saturating_add(1);
    }
}

/// One player/period/knowledge/journal bound a read may not exceed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PlayerScope {
    player_id: [u8; 8],
    as_of_period: u64,
    knowledge_seq: u64,
    journal_seq: u64,
}

impl PlayerScope {
    /// Bind one read to a player and the exact durable prefixes it may see.
    ///
    /// The caller supplies the bounds it actually holds: a current view passes
    /// the durable tails, and a historical view passes the tails that period
    /// recorded. A bound beyond the durable tail refuses rather than widening.
    #[must_use]
    pub const fn new(
        player_id: [u8; 8],
        as_of_period: u64,
        knowledge_seq: u64,
        journal_seq: u64,
    ) -> Self {
        Self {
            player_id,
            as_of_period,
            knowledge_seq,
            journal_seq,
        }
    }

    /// Return the player identity the scope discloses to.
    #[must_use]
    pub const fn player_id(self) -> [u8; 8] {
        self.player_id
    }

    /// Return the latest period the scope may disclose.
    #[must_use]
    pub const fn as_of_period(self) -> u64 {
        self.as_of_period
    }

    /// Return the knowledge prefix the scope may read.
    #[must_use]
    pub const fn knowledge_seq(self) -> u64 {
        self.knowledge_seq
    }

    /// Return the journal prefix the scope may read.
    #[must_use]
    pub const fn journal_seq(self) -> u64 {
        self.journal_seq
    }
}

/// Why one scoped read was refused.
#[derive(Debug)]
pub enum ReadError {
    /// The scope or query named a period beyond the committed present.
    FuturePeriod {
        /// Highest committed period.
        current: u64,
        /// Requested period.
        requested: u64,
    },
    /// The scope named a knowledge prefix beyond the durable tail.
    UnknownKnowledgePrefix {
        /// Durable knowledge tail.
        tail: u64,
        /// Requested prefix.
        requested: u64,
    },
    /// The scope named a journal prefix beyond the durable tail.
    UnknownJournalPrefix {
        /// Durable journal tail.
        tail: u64,
        /// Requested prefix.
        requested: u64,
    },
    /// No earned grant discloses the requested subject inside the scope.
    UndisclosedSubject,
    /// A county identity is not five ASCII digits.
    InvalidCountyFips {
        /// Rejected identity bytes.
        fips: [u8; 5],
    },
    /// A typed subject identity is empty.
    EmptySubjectId {
        /// Which query field was empty.
        field: &'static str,
    },
    /// A typed subject identity exceeds its published allowance.
    SubjectIdTooLong {
        /// Allowance in bytes.
        limit: usize,
        /// Supplied length.
        actual: usize,
    },
    /// One stored payload exceeded its table allowance.
    PayloadTooLarge {
        /// Allowance in bytes.
        limit: usize,
        /// Recorded or supplied length.
        actual: usize,
    },
    /// The owner answered a different projection than the closed query names.
    UnexpectedProjection,
    /// One authored-graph viewer payload is outside its exact published layout.
    InvalidViewerFact {
        /// Why the payload was refused.
        reason: &'static str,
    },
    /// The underlying store refused the read.
    Store(SaveError),
}

impl std::fmt::Display for ReadError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::FuturePeriod { current, requested } => write!(
                formatter,
                "the campaign is committed through period {current}; period {requested} is in the future"
            ),
            Self::UnknownKnowledgePrefix { tail, requested } => write!(
                formatter,
                "the knowledge prefix {requested} exceeds the durable tail {tail}"
            ),
            Self::UnknownJournalPrefix { tail, requested } => write!(
                formatter,
                "the journal prefix {requested} exceeds the durable tail {tail}"
            ),
            Self::UndisclosedSubject => {
                write!(formatter, "no earned grant discloses the requested subject")
            }
            Self::InvalidCountyFips { fips } => write!(
                formatter,
                "the county identity {fips:?} is not five ASCII digits"
            ),
            Self::EmptySubjectId { field } => {
                write!(formatter, "the queried subject identity `{field}` is empty")
            }
            Self::SubjectIdTooLong { limit, actual } => write!(
                formatter,
                "the queried subject identity is {actual} bytes; the allowance is {limit}"
            ),
            Self::PayloadTooLarge { limit, actual } => write!(
                formatter,
                "the disclosed payload is {actual} bytes; the allowance is {limit}"
            ),
            Self::UnexpectedProjection => {
                write!(formatter, "the campaign answered a different projection")
            }
            Self::InvalidViewerFact { reason } => {
                write!(formatter, "the authored graph viewer fact was refused: {reason}")
            }
            Self::Store(error) => write!(formatter, "the scoped read was refused: {error}"),
        }
    }
}

impl std::error::Error for ReadError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Store(error) => Some(error),
            _ => None,
        }
    }
}

impl From<SaveError> for ReadError {
    fn from(error: SaveError) -> Self {
        Self::Store(error)
    }
}

impl From<SqliteError> for ReadError {
    fn from(error: SqliteError) -> Self {
        Self::Store(SaveError::from(error))
    }
}

/// One closed query the player surface can ask.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PlayerQuery {
    /// Count the subjects the scope has earned, by closed subject kind.
    MapSummary,
    /// Disclose the earned summary of one county.
    CountySummary {
        /// Five-digit county FIPS identity.
        county_fips: [u8; 5],
    },
    /// Disclose one earned subject fact.
    KnownSubject {
        /// Closed subject kind.
        subject_kind: SubjectKind,
        /// Exact typed identity bytes.
        subject_id: Vec<u8>,
    },
    /// List the journal records naming one earned subject.
    KnownRelationship {
        /// Closed subject kind.
        subject_kind: SubjectKind,
        /// Exact typed identity bytes.
        subject_id: Vec<u8>,
    },
    /// Disclose the player's one standing accepted commitment.
    CurrentCommitment,
    /// Disclose one published dossier the scope has earned.
    EarnedDossier {
        /// Closed subject kind.
        subject_kind: SubjectKind,
        /// Exact typed identity bytes.
        subject_id: Vec<u8>,
        /// Latest period whose earned facts the dossier may render.
        as_of_period: u64,
    },
}

/// One earned fact with the identity that authorizes it.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SubjectFact {
    /// Closed subject kind.
    pub subject_kind: SubjectKind,
    /// Exact typed identity bytes.
    pub subject_id: Vec<u8>,
    /// Caller-assigned grant key inside the subject.
    pub grant_key: i64,
    /// Period the fact was acquired, never the period it observes.
    pub acquired_period: u64,
    /// Position in the knowledge chain.
    pub knowledge_seq: u64,
    /// Journal record that earned the fact.
    pub source_journal_seq: u64,
    /// Exact canonical payload bytes.
    pub payload: Vec<u8>,
}

/// The one evidence label an authored-graph viewer fact publishes.
pub const AUTHORED_GRAPH_EVIDENCE_LABEL: &str = "Designed";

const AUTHORED_GRAPH_SUBJECT_DOMAIN: &[u8] = b"babylon.authored-graph.subject.v1\0";
const AUTHORED_GRAPH_FACT_DOMAIN: &[u8] = b"babylon.authored-graph.viewer-fact.v1\0";
const AUTHORED_GRAPH_FACT_LAYOUT: u8 = 1;
const AUTHORED_GRAPH_EVIDENCE_DESIGNED: u8 = 1;
const MAX_VIEWER_TEXT_BYTES: usize = 256;

/// One authored-graph node fact the bounded graph viewer may disclose.
///
/// The fact is a read-only fixture disclosure, never an earned world
/// observation: its payload carries the fixed [`AUTHORED_GRAPH_EVIDENCE_LABEL`]
/// evidence label and its probability is exposed as exact binary64 bits.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AuthoredGraphNodeFact {
    /// Stable authored identity (scenario scope plus local node name).
    pub subject_id: Vec<u8>,
    /// Authored scenario scope.
    pub scenario_scope: String,
    /// Authored node local name.
    pub local_name: String,
    /// Declared node type.
    pub node_type: String,
    /// Exact declared probability bits.
    pub probability_bits: u64,
    /// Fixed evidence label for this profile.
    pub evidence: &'static str,
}

impl AuthoredGraphNodeFact {
    /// Return the exact declared probability value.
    #[must_use]
    pub fn probability(&self) -> f64 {
        f64::from_bits(self.probability_bits)
    }
}

/// Encode the stable authored subject identity of one node.
///
/// # Errors
///
/// Refuses a scope or local name beyond its published text allowance.
pub fn authored_graph_subject_id(
    scenario_scope: &str,
    local_name: &str,
) -> Result<Vec<u8>, ReadError> {
    let mut output = Vec::new();
    output.extend_from_slice(AUTHORED_GRAPH_SUBJECT_DOMAIN);
    push_text(&mut output, scenario_scope)?;
    push_text(&mut output, local_name)?;
    Ok(output)
}

/// Encode one authored-graph node fact payload.
///
/// # Errors
///
/// Refuses a scope, local name or node type beyond its published allowance.
pub fn encode_authored_graph_node_fact(fact: &AuthoredGraphNodeFact) -> Result<Vec<u8>, ReadError> {
    let mut output = Vec::new();
    output.extend_from_slice(AUTHORED_GRAPH_FACT_DOMAIN);
    output.push(AUTHORED_GRAPH_FACT_LAYOUT);
    push_text(&mut output, &fact.scenario_scope)?;
    push_text(&mut output, &fact.local_name)?;
    push_text(&mut output, &fact.node_type)?;
    output.extend_from_slice(&fact.probability_bits.to_be_bytes());
    output.push(AUTHORED_GRAPH_EVIDENCE_DESIGNED);
    Ok(output)
}

/// Decode one authored-graph node fact and bind it to its granted identity.
///
/// # Errors
///
/// Refuses a payload outside this exact layout, non-UTF-8 or oversized text, a
/// non-finite probability, an unknown evidence label, trailing bytes, or a
/// subject identity that disagrees with the decoded scope and local name.
pub fn decode_authored_graph_node_fact(
    subject_id: &[u8],
    payload: &[u8],
) -> Result<AuthoredGraphNodeFact, ReadError> {
    let mut reader = ViewerReader::new(payload);
    reader.expect(AUTHORED_GRAPH_FACT_DOMAIN)?;
    if reader.u8()? != AUTHORED_GRAPH_FACT_LAYOUT {
        return Err(ReadError::InvalidViewerFact {
            reason: "the authored viewer fact declares an unsupported layout",
        });
    }
    let scenario_scope = reader.text()?;
    let local_name = reader.text()?;
    let node_type = reader.text()?;
    let probability_bits = reader.u64()?;
    if !f64::from_bits(probability_bits).is_finite() {
        return Err(ReadError::InvalidViewerFact {
            reason: "the authored viewer probability is not finite",
        });
    }
    if reader.u8()? != AUTHORED_GRAPH_EVIDENCE_DESIGNED {
        return Err(ReadError::InvalidViewerFact {
            reason: "the authored viewer fact carries an unknown evidence label",
        });
    }
    if !reader.is_empty() {
        return Err(ReadError::InvalidViewerFact {
            reason: "the authored viewer fact carries trailing bytes",
        });
    }
    if authored_graph_subject_id(&scenario_scope, &local_name)? != subject_id {
        return Err(ReadError::InvalidViewerFact {
            reason: "the authored viewer fact disagrees with its granted subject identity",
        });
    }
    Ok(AuthoredGraphNodeFact {
        subject_id: subject_id.to_vec(),
        scenario_scope,
        local_name,
        node_type,
        probability_bits,
        evidence: AUTHORED_GRAPH_EVIDENCE_LABEL,
    })
}

fn push_text(output: &mut Vec<u8>, value: &str) -> Result<(), ReadError> {
    if value.is_empty() || value.len() > MAX_VIEWER_TEXT_BYTES {
        return Err(ReadError::InvalidViewerFact {
            reason: "the authored viewer text is empty or beyond its allowance",
        });
    }
    let length = u32::try_from(value.len()).map_err(|_| ReadError::InvalidViewerFact {
        reason: "the authored viewer text is wider than its length prefix",
    })?;
    output.extend_from_slice(&length.to_be_bytes());
    output.extend_from_slice(value.as_bytes());
    Ok(())
}

struct ViewerReader<'a> {
    bytes: &'a [u8],
    cursor: usize,
}

impl<'a> ViewerReader<'a> {
    const fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, cursor: 0 }
    }

    fn take(&mut self, count: usize) -> Result<&'a [u8], ReadError> {
        let end = self
            .cursor
            .checked_add(count)
            .filter(|end| *end <= self.bytes.len())
            .ok_or(ReadError::InvalidViewerFact {
                reason: "the authored viewer fact is truncated",
            })?;
        let output = &self.bytes[self.cursor..end];
        self.cursor = end;
        Ok(output)
    }

    fn expect(&mut self, expected: &[u8]) -> Result<(), ReadError> {
        if self.take(expected.len())? != expected {
            return Err(ReadError::InvalidViewerFact {
                reason: "the authored viewer fact carries the wrong domain tag",
            });
        }
        Ok(())
    }

    fn u8(&mut self) -> Result<u8, ReadError> {
        let [value] = self.take(1)? else {
            return Err(ReadError::InvalidViewerFact {
                reason: "the authored viewer fact is truncated",
            });
        };
        Ok(*value)
    }

    fn u32(&mut self) -> Result<u32, ReadError> {
        let bytes = self.take(4)?;
        <[u8; 4]>::try_from(bytes)
            .map(u32::from_be_bytes)
            .map_err(|_| ReadError::InvalidViewerFact {
                reason: "the authored viewer fact is truncated",
            })
    }

    fn u64(&mut self) -> Result<u64, ReadError> {
        let bytes = self.take(8)?;
        <[u8; 8]>::try_from(bytes)
            .map(u64::from_be_bytes)
            .map_err(|_| ReadError::InvalidViewerFact {
                reason: "the authored viewer fact is truncated",
            })
    }

    fn text(&mut self) -> Result<String, ReadError> {
        let length = usize::try_from(self.u32()?).map_err(|_| ReadError::InvalidViewerFact {
            reason: "the authored viewer text length is out of range",
        })?;
        if length == 0 || length > MAX_VIEWER_TEXT_BYTES {
            return Err(ReadError::InvalidViewerFact {
                reason: "the authored viewer text is empty or beyond its allowance",
            });
        }
        let bytes = self.take(length)?;
        std::str::from_utf8(bytes)
            .map(str::to_owned)
            .map_err(|_| ReadError::InvalidViewerFact {
                reason: "the authored viewer text is not UTF-8",
            })
    }

    fn is_empty(&self) -> bool {
        self.cursor == self.bytes.len()
    }
}

/// One earned subject count inside a map summary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SubjectCount {
    /// Closed subject kind.
    pub kind: SubjectKind,
    /// Distinct earned subjects of that kind.
    pub count: u64,
}

/// Every subject count the scope has earned.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MapSummary {
    /// Ordered counts by closed subject kind.
    pub known_subjects: Vec<SubjectCount>,
}

/// One earned county summary.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CountySummary {
    /// Five-digit county FIPS identity.
    pub county_fips: [u8; 5],
    /// The earned fact that answers the query.
    pub fact: SubjectFact,
}

/// One journal record naming an earned subject.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct JournalEntryRef {
    /// Durable journal position.
    pub journal_seq: u64,
    /// Closed record kind.
    pub kind: JournalKind,
    /// Period the record belongs to.
    pub period: u64,
    /// Period that resolved the record, when the owner recorded it.
    pub resolved_period: Option<u64>,
    /// SHA-256 of the record's decoded bytes.
    pub payload_hash: [u8; 32],
}

/// The journal records one earned subject is named by.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SubjectRelationship {
    /// Closed subject kind.
    pub subject_kind: SubjectKind,
    /// Exact typed identity bytes.
    pub subject_id: Vec<u8>,
    /// Ordered records naming the subject, capped at [`MAX_RELATIONSHIP_RECORDS`].
    pub records: Vec<JournalEntryRef>,
    /// Whether further records exist beyond the named cap.
    pub truncated: bool,
}

/// One accepted command the player still stands behind.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AcceptedCommitment {
    /// Durable journal position of the acceptance.
    pub journal_seq: u64,
    /// Period the command applies to.
    pub period: u64,
    /// Command nonce.
    pub nonce: [u8; 16],
    /// Exact canonical command bytes.
    pub payload: Vec<u8>,
}

/// The player's standing accepted commitment, when one is unresolved.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CurrentCommitment {
    /// The single unresolved acceptance, when the player has one.
    pub accepted: Option<AcceptedCommitment>,
}

/// One published dossier the scope has earned.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EarnedDossier {
    /// Closed subject kind.
    pub subject_kind: SubjectKind,
    /// Exact typed identity bytes.
    pub subject_id: Vec<u8>,
    /// Period the dossier was published.
    pub period: u64,
    /// Durable journal position of the dossier record.
    pub journal_seq: u64,
    /// Exact canonical dossier bytes.
    pub payload: Vec<u8>,
}

/// The typed answer one scoped query produced.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PlayerBody {
    /// Earned subject counts.
    MapSummary(MapSummary),
    /// One earned county summary.
    CountySummary(CountySummary),
    /// One earned subject fact.
    Subject(SubjectFact),
    /// The records naming one earned subject.
    Relationship(SubjectRelationship),
    /// The player's standing accepted commitment.
    Commitment(CurrentCommitment),
    /// One earned published dossier.
    EarnedDossier(EarnedDossier),
}

/// One scoped answer with the identity and cost of the read that produced it.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlayerResult {
    /// Committed period the read ran against.
    pub committed_period: u64,
    /// Latest period the scope may disclose.
    pub as_of_period: u64,
    /// Knowledge prefix the scope may read.
    pub knowledge_seq: u64,
    /// Canonical world identity of the committed root.
    pub world_hash: [u8; 32],
    /// Rows the read decoded.
    pub cost: ReadCost,
    /// The typed answer.
    pub body: PlayerBody,
}

/// One exclusive `(period, journal_seq)` history position.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct HistoryCursor {
    period: u64,
    journal_seq: u64,
}

impl HistoryCursor {
    /// Continue a page strictly after one already-delivered record.
    #[must_use]
    pub const fn after(period: u64, journal_seq: u64) -> Self {
        Self {
            period,
            journal_seq,
        }
    }

    /// Return the period of the last delivered record.
    #[must_use]
    pub const fn period(self) -> u64 {
        self.period
    }

    /// Return the journal position of the last delivered record.
    #[must_use]
    pub const fn journal_seq(self) -> u64 {
        self.journal_seq
    }
}

/// One journal record inside a history page.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HistoryEntry {
    /// Durable journal position.
    pub journal_seq: u64,
    /// Closed record kind.
    pub kind: JournalKind,
    /// Period the record belongs to.
    pub period: u64,
    /// Optional earned subject the record names.
    pub subject_kind: Option<SubjectKind>,
    /// Exact typed subject identity, when the record names one.
    pub subject_id: Option<Vec<u8>>,
    /// Period that resolved the record, when the owner recorded it.
    pub resolved_period: Option<u64>,
    /// Exact canonical record bytes.
    pub payload: Vec<u8>,
}

/// One bounded page of the player's visible journal.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HistoryPage {
    /// Committed period the page was read at.
    pub committed_period: u64,
    /// Latest period the scope may disclose.
    pub as_of_period: u64,
    /// Ordered records after the supplied cursor.
    pub entries: Vec<HistoryEntry>,
    /// Cursor for the next page, absent on the last page.
    pub next: Option<HistoryCursor>,
    /// Rows the page visited.
    pub cost: ReadCost,
}

/// The committed boundary one read authenticates against.
pub(super) struct ReadBoundary<'a> {
    /// Committed period the campaign holds.
    pub(super) committed_period: u64,
    /// Canonical world identity of that root.
    pub(super) world_hash: [u8; 32],
    /// Durable manifest the read authenticates against.
    pub(super) manifest: &'a Manifest,
}

/// Answer one closed query inside one player scope.
pub(super) fn execute(
    connection: &Connection,
    boundary: &ReadBoundary<'_>,
    scope: PlayerScope,
    query: PlayerQuery,
) -> Result<PlayerResult, ReadError> {
    let mut cost = ReadCost::default();
    validate_scope(boundary, scope)?;
    let body = match query {
        PlayerQuery::MapSummary => {
            PlayerBody::MapSummary(map_summary(connection, scope, &mut cost)?)
        }
        PlayerQuery::CountySummary { county_fips } => {
            validate_fips(county_fips)?;
            let fact = visible_fact(
                connection,
                scope,
                SubjectKind::County,
                &county_fips,
                &mut cost,
            )?
            .ok_or(ReadError::UndisclosedSubject)?;
            PlayerBody::CountySummary(CountySummary { county_fips, fact })
        }
        PlayerQuery::KnownSubject {
            subject_kind,
            subject_id,
        } => {
            validate_subject_id(&subject_id, "subject_id")?;
            let fact = visible_fact(connection, scope, subject_kind, &subject_id, &mut cost)?
                .ok_or(ReadError::UndisclosedSubject)?;
            PlayerBody::Subject(fact)
        }
        PlayerQuery::KnownRelationship {
            subject_kind,
            subject_id,
        } => {
            validate_subject_id(&subject_id, "subject_id")?;
            PlayerBody::Relationship(relationship(
                connection,
                scope,
                subject_kind,
                &subject_id,
                &mut cost,
            )?)
        }
        PlayerQuery::CurrentCommitment => {
            PlayerBody::Commitment(current_commitment(connection, scope, &mut cost)?)
        }
        PlayerQuery::EarnedDossier {
            subject_kind,
            subject_id,
            as_of_period,
        } => {
            validate_subject_id(&subject_id, "subject_id")?;
            PlayerBody::EarnedDossier(earned_dossier(
                connection,
                scope,
                subject_kind,
                &subject_id,
                as_of_period,
                &mut cost,
            )?)
        }
    };
    Ok(PlayerResult {
        committed_period: boundary.committed_period,
        as_of_period: scope.as_of_period,
        knowledge_seq: scope.knowledge_seq,
        world_hash: boundary.world_hash,
        cost,
        body,
    })
}

/// Answer one bounded history page inside one player scope.
pub(super) fn history(
    connection: &Connection,
    boundary: &ReadBoundary<'_>,
    scope: PlayerScope,
    cursor: Option<HistoryCursor>,
    limit: u16,
) -> Result<HistoryPage, ReadError> {
    validate_scope(boundary, scope)?;
    let effective = effective_limit(limit);
    let after = cursor.unwrap_or_else(|| HistoryCursor::after(0, 0));
    let mut cost = ReadCost::default();
    let mut statement = connection.prepare(
        "SELECT j.journal_seq, j.kind, j.period, j.subject_kind, j.subject_id,
                j.resolved_period, j.codec, j.raw_len, j.raw_hash, j.payload
         FROM permanent_journal j
         WHERE j.journal_seq <= ?1 AND j.period <= ?2
           AND (j.period, j.journal_seq) > (?3, ?4)
           AND (
                (j.kind = ?5 AND j.actor_id = ?6)
                OR (
                    j.subject_kind IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM knowledge_grant g
                        WHERE g.player_id = ?6
                          AND g.subject_kind = j.subject_kind
                          AND g.subject_id = j.subject_id
                          AND g.acquired_period <= ?2
                          AND g.knowledge_seq <= ?7
                          AND g.source_journal_seq <= ?1
                    )
                )
           )
         ORDER BY j.period, j.journal_seq
         LIMIT ?8",
    )?;
    let mut rows = statement.query(params![
        integer(scope.journal_seq, "journal prefix")?,
        integer(scope.as_of_period, "as-of period")?,
        integer(after.period, "history cursor period")?,
        integer(after.journal_seq, "history cursor sequence")?,
        JournalKind::AcceptedCommand.code(),
        &scope.player_id[..],
        integer(scope.knowledge_seq, "knowledge prefix")?,
        i64::from(effective).saturating_add(1),
    ])?;
    let mut entries = Vec::new();
    while let Some(row) = rows.next()? {
        cost.row();
        let kind =
            JournalKind::from_code(row.get(1)?).ok_or_else(|| SaveError::CorruptPayload {
                table: "permanent_journal",
                reason: "the stored record kind is outside the closed registry",
            })?;
        let subject_kind = match row.get::<_, Option<i64>>(3)? {
            Some(code) => {
                Some(
                    SubjectKind::from_code(code).ok_or_else(|| SaveError::CorruptPayload {
                        table: "permanent_journal",
                        reason: "the stored subject kind is outside the closed registry",
                    })?,
                )
            }
            None => None,
        };
        let payload = decode_record(
            row.get(7)?,
            row.get(6)?,
            &row.get::<_, Vec<u8>>(8)?,
            &row.get::<_, Vec<u8>>(9)?,
        )?;
        entries.push(HistoryEntry {
            journal_seq: widen(row.get(0)?, "history journal sequence")?,
            kind,
            period: widen(row.get(2)?, "history period")?,
            subject_kind,
            subject_id: row.get(4)?,
            resolved_period: match row.get::<_, Option<i64>>(5)? {
                Some(period) => Some(widen(period, "history resolution period")?),
                None => None,
            },
            payload,
        });
    }
    let next = if entries.len() > usize::from(effective) {
        entries.truncate(usize::from(effective));
        entries
            .last()
            .map(|entry| HistoryCursor::after(entry.period, entry.journal_seq))
    } else {
        None
    };
    Ok(HistoryPage {
        committed_period: boundary.committed_period,
        as_of_period: scope.as_of_period,
        entries,
        next,
        cost,
    })
}

/// Return the page size a caller's limit selects.
fn effective_limit(limit: u16) -> u16 {
    if limit == 0 {
        DEFAULT_HISTORY_LIMIT
    } else {
        limit.min(MAX_HISTORY_LIMIT)
    }
}

/// Refuse a scope that reaches beyond the durable present.
fn validate_scope(boundary: &ReadBoundary<'_>, scope: PlayerScope) -> Result<(), ReadError> {
    if scope.as_of_period > boundary.committed_period {
        return Err(ReadError::FuturePeriod {
            current: boundary.committed_period,
            requested: scope.as_of_period,
        });
    }
    if scope.knowledge_seq > boundary.manifest.knowledge_tail_seq {
        return Err(ReadError::UnknownKnowledgePrefix {
            tail: boundary.manifest.knowledge_tail_seq,
            requested: scope.knowledge_seq,
        });
    }
    if scope.journal_seq > boundary.manifest.journal_tail_seq {
        return Err(ReadError::UnknownJournalPrefix {
            tail: boundary.manifest.journal_tail_seq,
            requested: scope.journal_seq,
        });
    }
    Ok(())
}

fn validate_fips(fips: [u8; 5]) -> Result<(), ReadError> {
    if fips.iter().all(u8::is_ascii_digit) {
        Ok(())
    } else {
        Err(ReadError::InvalidCountyFips { fips })
    }
}

fn validate_subject_id(subject_id: &[u8], field: &'static str) -> Result<(), ReadError> {
    if subject_id.is_empty() {
        return Err(ReadError::EmptySubjectId { field });
    }
    if subject_id.len() > MAX_SUBJECT_ID_BYTES {
        return Err(ReadError::SubjectIdTooLong {
            limit: MAX_SUBJECT_ID_BYTES,
            actual: subject_id.len(),
        });
    }
    Ok(())
}

/// Read the newest grant the scope discloses for one subject.
fn visible_fact(
    connection: &Connection,
    scope: PlayerScope,
    subject_kind: SubjectKind,
    subject_id: &[u8],
    cost: &mut ReadCost,
) -> Result<Option<SubjectFact>, ReadError> {
    let stored = connection
        .query_row(
            "SELECT knowledge_seq, grant_key, acquired_period, source_journal_seq,
                    payload, previous_hash, entry_hash
             FROM knowledge_grant
             WHERE player_id = ?1 AND subject_kind = ?2 AND subject_id = ?3
               AND acquired_period <= ?4
               AND knowledge_seq <= ?5
               AND source_journal_seq <= ?6
             ORDER BY knowledge_seq DESC LIMIT 1",
            params![
                &scope.player_id[..],
                subject_kind.code(),
                subject_id,
                integer(scope.as_of_period, "as-of period")?,
                integer(scope.knowledge_seq, "knowledge prefix")?,
                integer(scope.journal_seq, "journal prefix")?,
            ],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)?,
                    row.get::<_, i64>(2)?,
                    row.get::<_, i64>(3)?,
                    row.get::<_, Vec<u8>>(4)?,
                    row.get::<_, Vec<u8>>(5)?,
                    row.get::<_, Vec<u8>>(6)?,
                ))
            },
        )
        .optional()?;
    let Some((
        knowledge_seq,
        grant_key,
        acquired_period,
        source_journal_seq,
        payload,
        previous_hash,
        entry_hash,
    )) = stored
    else {
        return Ok(None);
    };
    cost.row();
    let knowledge_seq = widen(knowledge_seq, "knowledge sequence")?;
    let acquired_period = widen(acquired_period, "acquired period")?;
    let source_journal_seq = widen(source_journal_seq, "source journal sequence")?;
    let payload = authenticate_grant(
        subject_kind,
        subject_id,
        scope.player_id,
        knowledge_seq,
        grant_key,
        acquired_period,
        source_journal_seq,
        payload,
        &previous_hash,
        &entry_hash,
    )?;
    Ok(Some(SubjectFact {
        subject_kind,
        subject_id: subject_id.to_vec(),
        grant_key,
        acquired_period,
        knowledge_seq,
        source_journal_seq,
        payload,
    }))
}

/// Recompute one grant's entry hash before its payload is disclosed.
#[allow(
    clippy::too_many_arguments,
    reason = "the stored row is authenticated field by field against its canonical hash"
)]
fn authenticate_grant(
    subject_kind: SubjectKind,
    subject_id: &[u8],
    player_id: [u8; 8],
    knowledge_seq: u64,
    grant_key: i64,
    acquired_period: u64,
    source_journal_seq: u64,
    payload: Vec<u8>,
    previous_hash: &[u8],
    entry_hash: &[u8],
) -> Result<Vec<u8>, ReadError> {
    if payload.len() > MAX_KNOWLEDGE_PAYLOAD_BYTES {
        return Err(ReadError::PayloadTooLarge {
            limit: MAX_KNOWLEDGE_PAYLOAD_BYTES,
            actual: payload.len(),
        });
    }
    let recomputed = owner::knowledge_entry_hash(&KnowledgeInput {
        knowledge_seq,
        player_id,
        subject_kind,
        subject_id,
        grant_key,
        acquired_period,
        source_journal_seq,
        raw_len: u32::try_from(payload.len()).map_err(|_| SaveError::CorruptPayload {
            table: "knowledge_grant",
            reason: "the stored payload is wider than its length prefix",
        })?,
        raw_hash: content_digest::sha256_of(&payload),
        previous_hash: hash32(previous_hash, "knowledge_grant")?,
    })?;
    if recomputed != hash32(entry_hash, "knowledge_grant")? {
        return Err(ReadError::Store(SaveError::CorruptPayload {
            table: "knowledge_grant",
            reason: "the stored payload does not match its entry hash",
        }));
    }
    Ok(payload)
}

fn map_summary(
    connection: &Connection,
    scope: PlayerScope,
    cost: &mut ReadCost,
) -> Result<MapSummary, ReadError> {
    let mut statement = connection.prepare(
        "SELECT subject_kind, COUNT(DISTINCT subject_id)
         FROM knowledge_grant
         WHERE player_id = ?1 AND acquired_period <= ?2
           AND knowledge_seq <= ?3 AND source_journal_seq <= ?4
         GROUP BY subject_kind ORDER BY subject_kind",
    )?;
    let mut rows = statement.query(params![
        &scope.player_id[..],
        integer(scope.as_of_period, "as-of period")?,
        integer(scope.knowledge_seq, "knowledge prefix")?,
        integer(scope.journal_seq, "journal prefix")?,
    ])?;
    let mut known_subjects = Vec::new();
    while let Some(row) = rows.next()? {
        cost.row();
        let kind =
            SubjectKind::from_code(row.get(0)?).ok_or_else(|| SaveError::CorruptPayload {
                table: "knowledge_grant",
                reason: "the stored subject kind is outside the closed registry",
            })?;
        known_subjects.push(SubjectCount {
            kind,
            count: widen(row.get(1)?, "known subject count")?,
        });
    }
    Ok(MapSummary { known_subjects })
}

fn relationship(
    connection: &Connection,
    scope: PlayerScope,
    subject_kind: SubjectKind,
    subject_id: &[u8],
    cost: &mut ReadCost,
) -> Result<SubjectRelationship, ReadError> {
    if visible_fact(connection, scope, subject_kind, subject_id, cost)?.is_none() {
        return Err(ReadError::UndisclosedSubject);
    }
    let mut statement = connection.prepare(
        "SELECT journal_seq, kind, period, resolved_period, raw_hash
         FROM permanent_journal
         WHERE subject_kind = ?1 AND subject_id = ?2
           AND period <= ?3 AND journal_seq <= ?4
         ORDER BY period, journal_seq
         LIMIT ?5",
    )?;
    let mut rows = statement.query(params![
        subject_kind.code(),
        subject_id,
        integer(scope.as_of_period, "as-of period")?,
        integer(scope.journal_seq, "journal prefix")?,
        i64::try_from(MAX_RELATIONSHIP_RECORDS)
            .unwrap_or(i64::MAX)
            .saturating_add(1),
    ])?;
    let mut records = Vec::new();
    let mut truncated = false;
    while let Some(row) = rows.next()? {
        cost.row();
        if records.len() == MAX_RELATIONSHIP_RECORDS {
            truncated = true;
            break;
        }
        let kind =
            JournalKind::from_code(row.get(1)?).ok_or_else(|| SaveError::CorruptPayload {
                table: "permanent_journal",
                reason: "the stored record kind is outside the closed registry",
            })?;
        records.push(JournalEntryRef {
            journal_seq: widen(row.get(0)?, "relationship journal sequence")?,
            kind,
            period: widen(row.get(2)?, "relationship period")?,
            resolved_period: match row.get::<_, Option<i64>>(3)? {
                Some(period) => Some(widen(period, "relationship resolution period")?),
                None => None,
            },
            payload_hash: hash32(&row.get::<_, Vec<u8>>(4)?, "permanent_journal")?,
        });
    }
    Ok(SubjectRelationship {
        subject_kind,
        subject_id: subject_id.to_vec(),
        records,
        truncated,
    })
}

fn current_commitment(
    connection: &Connection,
    scope: PlayerScope,
    cost: &mut ReadCost,
) -> Result<CurrentCommitment, ReadError> {
    let stored = connection
        .query_row(
            "SELECT journal_seq, period, nonce, codec, raw_len, raw_hash, payload
             FROM permanent_journal
             WHERE kind = ?1 AND actor_id = ?2 AND resolved_period IS NULL
               AND journal_seq <= ?3
             ORDER BY period DESC LIMIT 1",
            params![
                JournalKind::AcceptedCommand.code(),
                &scope.player_id[..],
                integer(scope.journal_seq, "journal prefix")?
            ],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)?,
                    row.get::<_, Vec<u8>>(2)?,
                    row.get::<_, i64>(3)?,
                    row.get::<_, i64>(4)?,
                    row.get::<_, Vec<u8>>(5)?,
                    row.get::<_, Vec<u8>>(6)?,
                ))
            },
        )
        .optional()?;
    let Some((journal_seq, period, nonce, codec_code, raw_len, raw_hash, payload)) = stored else {
        return Ok(CurrentCommitment { accepted: None });
    };
    cost.row();
    let payload = decode_record(raw_len, codec_code, &raw_hash, &payload)?;
    Ok(CurrentCommitment {
        accepted: Some(AcceptedCommitment {
            journal_seq: widen(journal_seq, "commitment journal sequence")?,
            period: widen(period, "commitment period")?,
            nonce: hash16(&nonce)?,
            payload,
        }),
    })
}

fn earned_dossier(
    connection: &Connection,
    scope: PlayerScope,
    subject_kind: SubjectKind,
    subject_id: &[u8],
    as_of_period: u64,
    cost: &mut ReadCost,
) -> Result<EarnedDossier, ReadError> {
    if as_of_period > scope.as_of_period {
        return Err(ReadError::FuturePeriod {
            current: scope.as_of_period,
            requested: as_of_period,
        });
    }
    let bounded = PlayerScope::new(
        scope.player_id,
        as_of_period,
        scope.knowledge_seq,
        scope.journal_seq,
    );
    visible_fact(connection, bounded, subject_kind, subject_id, cost)?
        .ok_or(ReadError::UndisclosedSubject)?;
    let stored = connection
        .query_row(
            "SELECT journal_seq, period, codec, raw_len, raw_hash, payload
             FROM permanent_journal
             WHERE kind = ?1 AND subject_kind = ?2 AND subject_id = ?3
               AND journal_seq <= ?4
             ORDER BY journal_seq DESC LIMIT 1",
            params![
                JournalKind::Dossier.code(),
                subject_kind.code(),
                subject_id,
                integer(scope.journal_seq, "journal prefix")?,
            ],
            |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)?,
                    row.get::<_, i64>(2)?,
                    row.get::<_, i64>(3)?,
                    row.get::<_, Vec<u8>>(4)?,
                    row.get::<_, Vec<u8>>(5)?,
                ))
            },
        )
        .optional()?;
    let Some((journal_seq, period, codec_code, raw_len, raw_hash, payload)) = stored else {
        return Err(ReadError::UndisclosedSubject);
    };
    cost.row();
    let payload = decode_record(raw_len, codec_code, &raw_hash, &payload)?;
    Ok(EarnedDossier {
        subject_kind,
        subject_id: subject_id.to_vec(),
        period: widen(period, "dossier period")?,
        journal_seq: widen(journal_seq, "dossier journal sequence")?,
        payload,
    })
}

/// Decode one stored journal payload and authenticate its codec, width and hash.
fn decode_record(
    raw_len: i64,
    codec_code: i64,
    raw_hash: &[u8],
    payload: &[u8],
) -> Result<Vec<u8>, ReadError> {
    let stored = StoredPayload {
        codec: PayloadCodec::from_code(codec_code)?,
        raw_len: u32::try_from(raw_len).map_err(|_| SaveError::CorruptPayload {
            table: "permanent_journal",
            reason: "the stored decoded length is out of range",
        })?,
        raw_hash: hash32(raw_hash, "permanent_journal")?,
        payload,
    };
    Ok(codec::decode_chunk_payload(
        PayloadBudget::PermanentJournal,
        &stored,
    )?)
}

fn integer(value: u64, field: &'static str) -> Result<i64, ReadError> {
    i64::try_from(value).map_err(|_| SaveError::Arithmetic { field }.into())
}

fn widen(value: i64, field: &'static str) -> Result<u64, ReadError> {
    u64::try_from(value).map_err(|_| {
        SaveError::CorruptPayload {
            table: field,
            reason: "the stored integer is negative",
        }
        .into()
    })
}

fn hash32(bytes: &[u8], table: &'static str) -> Result<[u8; 32], ReadError> {
    <[u8; 32]>::try_from(bytes).map_err(|_| {
        SaveError::CorruptPayload {
            table,
            reason: "the stored hash is not 32 bytes",
        }
        .into()
    })
}

fn hash16(bytes: &[u8]) -> Result<[u8; 16], ReadError> {
    <[u8; 16]>::try_from(bytes).map_err(|_| {
        SaveError::CorruptPayload {
            table: "permanent_journal",
            reason: "the stored nonce is not 16 bytes",
        }
        .into()
    })
}
