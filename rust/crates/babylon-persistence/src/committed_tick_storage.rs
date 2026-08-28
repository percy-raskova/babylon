//! Database-free typed mapping from `CommittedTickEnvelopeV1` to `PostgreSQL` rows.

use babylon_kernel::replay::{ReplaySeed, ReplaySessionIdV1};
use babylon_kernel::tick_content_hash::{RefDigestV1, TickContentHashV1};
use babylon_kernel::ContentDigest;

use crate::committed_tick_envelope::{
    CommittedTickEnvelopeDigestV1, CommittedTickEnvelopeV1, CommittedTickRowBatchV1,
    CommittedTickRowFamilyV1, CommittedTickRowV1, COMMITTED_TICK_ENVELOPE_LAYOUT_VERSION_V1,
};
use crate::identity::CampaignId;

const STATE_SCHEMA: &str = "babylon_state";
const TICK_COMMIT_ENVELOPE_LAYOUT_VERSION_V1: i16 = 1;
const _: () = assert!(COMMITTED_TICK_ENVELOPE_LAYOUT_VERSION_V1 == 1);
const FAMILY_COLUMNS: &[&str] = &["campaign_id", "resolve_tick", "row_key", "row_payload"];
const CAMPAIGN_COLUMNS: &[&str] = &[
    "campaign_id",
    "replay_layout_version",
    "rng_layout_version",
    "replay_session_id",
    "rng_seed",
    "defines_hash",
    "rules_hash",
    "ref_digest",
];
const TICK_COMMIT_COLUMNS: &[&str] = &[
    "campaign_id",
    "resolve_tick",
    "envelope_layout_version",
    "tick_content_hash",
    "envelope_digest",
];

/// Versioned schema-qualified `PostgreSQL` relation and its fixed column order.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PostgreSqlStorageTableV1 {
    schema: &'static str,
    relation: &'static str,
    qualified_name: &'static str,
    columns: &'static [&'static str],
}

impl PostgreSqlStorageTableV1 {
    /// Return the `PostgreSQL` schema name.
    #[must_use]
    pub const fn schema(self) -> &'static str {
        self.schema
    }

    /// Return the unqualified relation name.
    #[must_use]
    pub const fn relation(self) -> &'static str {
        self.relation
    }

    /// Return the exact schema-qualified relation name.
    #[must_use]
    pub const fn qualified_name(self) -> &'static str {
        self.qualified_name
    }

    /// Return the fixed database column order for typed parameter binding.
    #[must_use]
    pub const fn columns(self) -> &'static [&'static str] {
        self.columns
    }
}

const fn table(
    relation: &'static str,
    qualified_name: &'static str,
    columns: &'static [&'static str],
) -> PostgreSqlStorageTableV1 {
    PostgreSqlStorageTableV1 {
        schema: STATE_SCHEMA,
        relation,
        qualified_name,
        columns,
    }
}

/// Canonical campaign-run storage relation.
pub const CAMPAIGN_STORAGE_TABLE_V1: PostgreSqlStorageTableV1 =
    table("campaign", "babylon_state.campaign", CAMPAIGN_COLUMNS);
/// Future marker-last storage relation.
pub const TICK_COMMIT_STORAGE_TABLE_V1: PostgreSqlStorageTableV1 = table(
    "tick_commit",
    "babylon_state.tick_commit",
    TICK_COMMIT_COLUMNS,
);

/// One closed envelope-family to PostgreSQL-table mapping.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CommittedTickStorageTargetV1 {
    family: CommittedTickRowFamilyV1,
    table: PostgreSqlStorageTableV1,
}

impl CommittedTickStorageTargetV1 {
    /// Return the owning envelope family.
    #[must_use]
    pub const fn family(self) -> CommittedTickRowFamilyV1 {
        self.family
    }

    /// Return the exact schema-qualified storage table.
    #[must_use]
    pub const fn table(self) -> PostgreSqlStorageTableV1 {
        self.table
    }
}

const fn target(
    family: CommittedTickRowFamilyV1,
    relation: &'static str,
    qualified_name: &'static str,
) -> CommittedTickStorageTargetV1 {
    CommittedTickStorageTargetV1 {
        family,
        table: table(relation, qualified_name, FAMILY_COLUMNS),
    }
}

/// Exact family order and schema-qualified `PostgreSQL` storage mapping.
pub const ALL_COMMITTED_TICK_STORAGE_TARGETS_V1: [CommittedTickStorageTargetV1; 8] = [
    target(
        CommittedTickRowFamilyV1::Graph,
        "tick_graph_row",
        "babylon_state.tick_graph_row",
    ),
    target(
        CommittedTickRowFamilyV1::State,
        "tick_state_row",
        "babylon_state.tick_state_row",
    ),
    target(
        CommittedTickRowFamilyV1::Event,
        "tick_event_row",
        "babylon_state.tick_event_row",
    ),
    target(
        CommittedTickRowFamilyV1::Subsystem,
        "tick_subsystem_row",
        "babylon_state.tick_subsystem_row",
    ),
    target(
        CommittedTickRowFamilyV1::Conservation,
        "tick_conservation_row",
        "babylon_state.tick_conservation_row",
    ),
    target(
        CommittedTickRowFamilyV1::BoundaryFlow,
        "tick_boundary_flow_row",
        "babylon_state.tick_boundary_flow_row",
    ),
    target(
        CommittedTickRowFamilyV1::Checkpoint,
        "tick_checkpoint_row",
        "babylon_state.tick_checkpoint_row",
    ),
    target(
        CommittedTickRowFamilyV1::ArchiveDirtyReceipt,
        "tick_archive_dirty_receipt_row",
        "babylon_state.tick_archive_dirty_receipt_row",
    ),
];

/// Typed canonical campaign row, still without database I/O authority.
#[derive(Debug, Clone, Copy)]
pub struct CampaignStorageRowV1<'a> {
    campaign_id: CampaignId,
    replay_session_id: &'a ReplaySessionIdV1,
    rng_seed: ReplaySeed,
    content: &'a ContentDigest,
    reference: RefDigestV1,
}

impl<'a> CampaignStorageRowV1<'a> {
    /// Bind the separate durable and deterministic replay identities.
    #[must_use]
    pub const fn new(
        campaign_id: CampaignId,
        replay_session_id: &'a ReplaySessionIdV1,
        rng_seed: ReplaySeed,
        content: &'a ContentDigest,
        reference: RefDigestV1,
    ) -> Self {
        Self {
            campaign_id,
            replay_session_id,
            rng_seed,
            content,
            reference,
        }
    }

    /// Return the durable campaign key.
    #[must_use]
    pub const fn campaign_id(self) -> CampaignId {
        self.campaign_id
    }

    /// Return the exact checked replay-session bytes.
    #[must_use]
    pub fn replay_session_bytes(self) -> &'a [u8] {
        self.replay_session_id.as_bytes()
    }

    /// Return the signed PostgreSQL-compatible RNG seed.
    #[must_use]
    pub const fn rng_seed(self) -> i64 {
        i64::from_be_bytes(self.rng_seed.to_be_bytes())
    }

    /// Borrow the defines digest bytes.
    #[must_use]
    pub const fn defines_hash(self) -> &'a [u8; 32] {
        &self.content.defines_hash
    }

    /// Borrow the rules digest bytes.
    #[must_use]
    pub const fn rules_hash(self) -> &'a [u8; 32] {
        &self.content.rules_hash
    }

    /// Return the immutable reference-cohort digest.
    #[must_use]
    pub const fn reference(self) -> RefDigestV1 {
        self.reference
    }

    /// Return the stored replay layout version.
    #[must_use]
    pub const fn replay_layout_version(self) -> i16 {
        1
    }

    /// Return the stored RNG layout version.
    #[must_use]
    pub const fn rng_layout_version(self) -> i16 {
        2
    }
}

/// Future marker row derived from one checked committed envelope.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TickCommitStorageRowV1 {
    campaign_id: CampaignId,
    resolve_tick: i64,
    tick_content_hash: TickContentHashV1,
    envelope_digest: CommittedTickEnvelopeDigestV1,
}

impl TickCommitStorageRowV1 {
    /// Return the durable campaign key.
    #[must_use]
    pub const fn campaign_id(self) -> CampaignId {
        self.campaign_id
    }

    /// Return the checked `PostgreSQL` `BIGINT` tick.
    #[must_use]
    pub const fn resolve_tick(self) -> i64 {
        self.resolve_tick
    }

    /// Return the V1 envelope layout discriminator.
    #[must_use]
    pub const fn envelope_layout_version(self) -> i16 {
        TICK_COMMIT_ENVELOPE_LAYOUT_VERSION_V1
    }

    /// Return the kernel-owned constitutional tick-content identity.
    #[must_use]
    pub const fn tick_content_hash(self) -> TickContentHashV1 {
        self.tick_content_hash
    }

    /// Return the diagnostic exact-envelope digest.
    #[must_use]
    pub const fn envelope_digest(self) -> CommittedTickEnvelopeDigestV1 {
        self.envelope_digest
    }
}

/// One family batch bound to its exact table and marker key.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CommittedTickStorageBatchV1<'a> {
    target: CommittedTickStorageTargetV1,
    campaign_id: CampaignId,
    resolve_tick: i64,
    rows: &'a [CommittedTickRowV1],
}

impl<'a> CommittedTickStorageBatchV1<'a> {
    /// Return the closed family-to-table target.
    #[must_use]
    pub const fn target(&self) -> CommittedTickStorageTargetV1 {
        self.target
    }

    /// Return the durable campaign key repeated on every row.
    #[must_use]
    pub const fn campaign_id(&self) -> CampaignId {
        self.campaign_id
    }

    /// Return the checked `PostgreSQL` `BIGINT` tick repeated on every row.
    #[must_use]
    pub const fn resolve_tick(&self) -> i64 {
        self.resolve_tick
    }

    /// Borrow the strict key-ordered exact key and payload bytes.
    #[must_use]
    pub const fn rows(&self) -> &'a [CommittedTickRowV1] {
        self.rows
    }
}

/// Complete database-free row binding for all tables in one future transaction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommittedTickStorageEnvelopeV1<'a> {
    marker: TickCommitStorageRowV1,
    batches: [CommittedTickStorageBatchV1<'a>; 8],
}

impl<'a> CommittedTickStorageEnvelopeV1<'a> {
    /// Return the future marker-last row.
    #[must_use]
    pub const fn marker(&self) -> TickCommitStorageRowV1 {
        self.marker
    }

    /// Borrow every family batch in the same closed order as the envelope.
    #[must_use]
    pub const fn batches(&self) -> &[CommittedTickStorageBatchV1<'a>; 8] {
        &self.batches
    }
}

/// Checked refusal at the `PostgreSQL` type boundary.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CommittedTickStorageErrorV1 {
    /// An unsigned tick cannot be represented by `PostgreSQL` `BIGINT`.
    ResolveTickOutOfRange {
        /// Received unsigned tick.
        actual: u64,
        /// Largest accepted value.
        maximum: u64,
    },
    /// The envelope's closed family order did not match its storage target.
    FamilyOrderMismatch {
        /// Expected family from the storage mapping.
        expected: CommittedTickRowFamilyV1,
        /// Actual family supplied by the envelope.
        actual: CommittedTickRowFamilyV1,
    },
}

impl<'a> TryFrom<&'a CommittedTickEnvelopeV1> for CommittedTickStorageEnvelopeV1<'a> {
    type Error = CommittedTickStorageErrorV1;

    fn try_from(envelope: &'a CommittedTickEnvelopeV1) -> Result<Self, Self::Error> {
        let claim = envelope.claim();
        let resolve_tick = i64::try_from(claim.resolve_tick()).map_err(|_| {
            CommittedTickStorageErrorV1::ResolveTickOutOfRange {
                actual: claim.resolve_tick(),
                maximum: i64::MAX as u64,
            }
        })?;
        let marker = TickCommitStorageRowV1 {
            campaign_id: claim.campaign_id(),
            resolve_tick,
            tick_content_hash: claim.tick_content_hash(),
            envelope_digest: envelope.digest(),
        };
        let source = envelope.row_families();
        let batches = [
            map_batch(source, 0, marker, ALL_COMMITTED_TICK_STORAGE_TARGETS_V1[0])?,
            map_batch(source, 1, marker, ALL_COMMITTED_TICK_STORAGE_TARGETS_V1[1])?,
            map_batch(source, 2, marker, ALL_COMMITTED_TICK_STORAGE_TARGETS_V1[2])?,
            map_batch(source, 3, marker, ALL_COMMITTED_TICK_STORAGE_TARGETS_V1[3])?,
            map_batch(source, 4, marker, ALL_COMMITTED_TICK_STORAGE_TARGETS_V1[4])?,
            map_batch(source, 5, marker, ALL_COMMITTED_TICK_STORAGE_TARGETS_V1[5])?,
            map_batch(source, 6, marker, ALL_COMMITTED_TICK_STORAGE_TARGETS_V1[6])?,
            map_batch(source, 7, marker, ALL_COMMITTED_TICK_STORAGE_TARGETS_V1[7])?,
        ];
        Ok(Self { marker, batches })
    }
}

fn map_batch(
    source: &[CommittedTickRowBatchV1; 8],
    index: usize,
    marker: TickCommitStorageRowV1,
    target: CommittedTickStorageTargetV1,
) -> Result<CommittedTickStorageBatchV1<'_>, CommittedTickStorageErrorV1> {
    let batch = &source[index];
    if batch.family() != target.family() {
        return Err(CommittedTickStorageErrorV1::FamilyOrderMismatch {
            expected: target.family(),
            actual: batch.family(),
        });
    }
    Ok(CommittedTickStorageBatchV1 {
        target,
        campaign_id: marker.campaign_id(),
        resolve_tick: marker.resolve_tick(),
        rows: batch.rows(),
    })
}

impl std::fmt::Display for CommittedTickStorageErrorV1 {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            formatter,
            "committed tick storage mapping refused: {self:?}"
        )
    }
}

impl std::error::Error for CommittedTickStorageErrorV1 {}
