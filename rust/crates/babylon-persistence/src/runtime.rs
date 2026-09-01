//! Sole Rust persistence activation and durable replay composition root.

use babylon_bsl::identity_codec::StableBslValueV1;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_state::StableGraphStateV1;
use babylon_kernel::sha256_of;
use babylon_kernel::tick_content_hash::TickContentHashV1;
use babylon_practice_contract::ordered_action_v1::OrderedPracticeActionBatchV1;
use babylon_tick::material_state::MaterialStateV1;
use babylon_tick::replay_session::{
    IdentifiedTickReportV1, ReplayCommitAcknowledgementV1, ReplayCommitDispositionV1,
    ReplayTickSession,
};
use postgres::binary_copy::BinaryCopyInWriter;
use postgres::types::{ToSql, Type};
use postgres::{Config, GenericClient, NoTls};

use crate::bootstrap::{bootstrap_h3_reader_epoch_v1, H3ReaderBootstrapErrorV1};
use crate::checkpoint::{
    compose_archive_dirty_receipt_v1, compose_checkpoint_rows_v1, ArchiveDirtyReceiptV1,
    CheckpointRowsV1, CommittedFullCheckpointV1, CommittedResolveTickErrorV1,
    CommittedResolveTickV1,
};
use crate::committed_tick_envelope::{
    CommittedTickEnvelopeErrorV1, CommittedTickEnvelopeV1, CommittedTickRowFamiliesV1,
    CommittedTickRowV1,
};
use crate::foundation::{CampaignFoundationV1, FoundationContentBundleV1};
use crate::identity::CampaignId;
use crate::legacy_adopter::{
    acquire_lock, release_lock, validate_legacy_connection_target, LegacyAdopterError,
};
use crate::metadata::{
    advance_campaign_catalog_tick_v1, ensure_campaign_catalog_row_v1, read_campaign_catalog_row_v1,
};
use crate::michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation_v1;
use crate::postgres_diagnostic::PostgresDiagnosticV1;
use crate::semantic_batches::{
    compose_graph_event_semantic_batches_v1, compose_material_state_rows_v1,
    GraphEventSemanticBatchesV1, SemanticBatchErrorV1,
};
use crate::semantic_codec::SemanticCodecErrorV1;
use crate::stored_tick::read_stored_typed_tick_v1;
use crate::tick_commit_claim::TickCommitClaimV1;

const MIGRATION_0008_SQL: &str =
    include_str!("../migrations/0008_rust_persistence_preparation.sql");
const MIGRATION_0009_SQL: &str = include_str!("../migrations/0009_rust_persistence_activation.sql");
const CUTOVER_CONTRACT: &[u8] =
    include_bytes!("../../../../contracts/rust_persistence_cutover_v1.yaml");
const READER_CONTRACT: &[u8] = include_bytes!("../../../../contracts/h3_reader_cutover_v1.yaml");
const AUTHORITY_LEDGER_DOMAIN: &[u8] = b"babylon.persistence-authority-ledger-row.v1\0";
const AUTHORITY_LEDGER_LAYOUT_V1: u32 = 1;
const REFERENCE_BUNDLE_DOMAIN_V1: &[u8] = b"babylon.h3.reference-bundle-composite.v1\0";

/// Closed one-way persistence authority state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PersistenceAuthorityStateV1 {
    /// The additive typed schema exists, but Python authority has not been destroyed.
    Prepared,
    /// Epoch 9 committed with the Rust-active row as its final DML statement.
    RustActive,
}

impl PersistenceAuthorityStateV1 {
    const fn tag(self) -> u8 {
        match self {
            Self::Prepared => 1,
            Self::RustActive => 2,
        }
    }
}

/// One exact digest-chained row from the persistence authority ledger.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PersistenceAuthorityLedgerRowV1 {
    ordinal: u16,
    state: PersistenceAuthorityStateV1,
    schema_epoch: u16,
    contract_sha256: [u8; 32],
    reader_contract_sha256: [u8; 32],
    predecessor_sha256: Option<[u8; 32]>,
    canonical_bytes: Vec<u8>,
    row_sha256: [u8; 32],
}

impl PersistenceAuthorityLedgerRowV1 {
    fn prepared() -> Result<Self, RustPersistenceActivationErrorV1> {
        Self::compose(
            1,
            PersistenceAuthorityStateV1::Prepared,
            8,
            sha256_of(CUTOVER_CONTRACT),
            sha256_of(READER_CONTRACT),
            None,
        )
    }

    fn rust_active(prepared: &Self) -> Result<Self, RustPersistenceActivationErrorV1> {
        Self::compose(
            2,
            PersistenceAuthorityStateV1::RustActive,
            9,
            prepared.contract_sha256,
            prepared.reader_contract_sha256,
            Some(prepared.row_sha256),
        )
    }

    fn compose(
        ordinal: u16,
        state: PersistenceAuthorityStateV1,
        schema_epoch: u16,
        contract_sha256: [u8; 32],
        reader_contract_sha256: [u8; 32],
        predecessor_sha256: Option<[u8; 32]>,
    ) -> Result<Self, RustPersistenceActivationErrorV1> {
        let capacity = AUTHORITY_LEDGER_DOMAIN
            .len()
            .checked_add(4 + 2 + 1 + 2 + 32 + 32 + 1)
            .and_then(|value| value.checked_add(predecessor_sha256.as_ref().map_or(0, |_| 32)))
            .ok_or(RustPersistenceActivationErrorV1::LedgerEncoding)?;
        let mut canonical_bytes = Vec::new();
        canonical_bytes
            .try_reserve_exact(capacity)
            .map_err(|_| RustPersistenceActivationErrorV1::LedgerEncoding)?;
        canonical_bytes.extend_from_slice(AUTHORITY_LEDGER_DOMAIN);
        canonical_bytes.extend_from_slice(&AUTHORITY_LEDGER_LAYOUT_V1.to_be_bytes());
        canonical_bytes.extend_from_slice(&ordinal.to_be_bytes());
        canonical_bytes.push(state.tag());
        canonical_bytes.extend_from_slice(&schema_epoch.to_be_bytes());
        canonical_bytes.extend_from_slice(&contract_sha256);
        canonical_bytes.extend_from_slice(&reader_contract_sha256);
        match predecessor_sha256 {
            None => canonical_bytes.push(0),
            Some(predecessor) => {
                canonical_bytes.push(1);
                canonical_bytes.extend_from_slice(&predecessor);
            }
        }
        if canonical_bytes.len() != capacity {
            return Err(RustPersistenceActivationErrorV1::LedgerEncoding);
        }
        let row_sha256 = sha256_of(&canonical_bytes);
        Ok(Self {
            ordinal,
            state,
            schema_epoch,
            contract_sha256,
            reader_contract_sha256,
            predecessor_sha256,
            canonical_bytes,
            row_sha256,
        })
    }

    /// Return the fixed one-based ledger ordinal.
    #[must_use]
    pub const fn ordinal(&self) -> u16 {
        self.ordinal
    }

    /// Return the closed authority state.
    #[must_use]
    pub const fn state(&self) -> PersistenceAuthorityStateV1 {
        self.state
    }

    /// Return the state-owned schema epoch.
    #[must_use]
    pub const fn schema_epoch(&self) -> u16 {
        self.schema_epoch
    }

    /// Return the exact cutover-contract digest.
    #[must_use]
    pub const fn contract_sha256(&self) -> [u8; 32] {
        self.contract_sha256
    }

    /// Return the exact joined reader-contract digest.
    #[must_use]
    pub const fn reader_contract_sha256(&self) -> [u8; 32] {
        self.reader_contract_sha256
    }

    /// Return the exact predecessor-row digest when this is the active row.
    #[must_use]
    pub const fn predecessor_sha256(&self) -> Option<[u8; 32]> {
        self.predecessor_sha256
    }
}

/// Successful exact two-state activation receipt.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ActivationReportV1 {
    prepared_row: PersistenceAuthorityLedgerRowV1,
    rust_active_row: PersistenceAuthorityLedgerRowV1,
}

impl ActivationReportV1 {
    /// Borrow the exact durable preparation row.
    #[must_use]
    pub const fn prepared_row(&self) -> &PersistenceAuthorityLedgerRowV1 {
        &self.prepared_row
    }

    /// Borrow the exact terminal Rust-authority row.
    #[must_use]
    pub const fn rust_active_row(&self) -> &PersistenceAuthorityLedgerRowV1 {
        &self.rust_active_row
    }
}

/// Closed activation refusal surface without driver or credential leakage.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RustPersistenceActivationErrorV1 {
    /// The joined H3 reader epoch could not be established first.
    ReaderBootstrap(H3ReaderBootstrapErrorV1),
    /// The target violated the local maintenance connection contract.
    ConnectionTarget,
    /// A bounded database operation failed.
    Database {
        operation: &'static str,
        diagnostic: Option<PostgresDiagnosticV1>,
    },
    /// Advisory-lock acquisition failed with its typed database cause.
    Lock(LegacyAdopterError),
    /// The durable ledger did not equal the exact two-row state machine.
    AuthorityLedgerMismatch,
    /// Exact ledger bytes could not be allocated or composed.
    LedgerEncoding,
    /// The advisory-lock cleanup failed after the primary operation.
    Cleanup(LegacyAdopterError),
}

impl std::fmt::Display for RustPersistenceActivationErrorV1 {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "Rust persistence activation refused: {self:?}")
    }
}

impl std::error::Error for RustPersistenceActivationErrorV1 {}

impl RustPersistenceActivationErrorV1 {
    fn postgres(operation: &'static str, error: &postgres::Error) -> Self {
        Self::Database {
            operation,
            diagnostic: Some(PostgresDiagnosticV1::capture(error)),
        }
    }
}

/// Reach the reader epoch, commit additive preparation, then commit one-way Rust authority.
///
/// The epoch-9 SQL refuses non-empty opaque predecessor rows. The active ledger row is inserted
/// after every destructive statement and is therefore the final DML before COMMIT.
///
/// # Errors
/// Returns a closed bootstrap, target, database, ledger, or cleanup refusal.
pub fn activate_rust_persistence_v1(
    config: &Config,
) -> Result<ActivationReportV1, RustPersistenceActivationErrorV1> {
    validate_legacy_connection_target(config)
        .map_err(|_| RustPersistenceActivationErrorV1::ConnectionTarget)?;
    if let Some(report) = read_terminal_activation_report_v1(config)? {
        return Ok(report);
    }
    if let Err(error) = bootstrap_h3_reader_epoch_v1(config) {
        if let Some(report) = read_terminal_activation_report_v1(config)? {
            return Ok(report);
        }
        return Err(RustPersistenceActivationErrorV1::ReaderBootstrap(error));
    }
    let mut client = config
        .connect(NoTls)
        .map_err(|error| RustPersistenceActivationErrorV1::postgres("connect", &error))?;
    acquire_lock(&mut client).map_err(RustPersistenceActivationErrorV1::Lock)?;
    let result = activate_under_lock(&mut client);
    let cleanup = release_lock(&mut client).map_err(RustPersistenceActivationErrorV1::Cleanup);
    match cleanup {
        Ok(()) => result,
        Err(error) => Err(error),
    }
}

fn read_terminal_activation_report_v1(
    config: &Config,
) -> Result<Option<ActivationReportV1>, RustPersistenceActivationErrorV1> {
    let expected_prepared = PersistenceAuthorityLedgerRowV1::prepared()?;
    let expected_active = PersistenceAuthorityLedgerRowV1::rust_active(&expected_prepared)?;
    let mut client = config.connect(NoTls).map_err(|error| {
        RustPersistenceActivationErrorV1::postgres("connect for terminal authority check", &error)
    })?;
    let observed = read_authority_ledger(&mut client)?;
    if observed.is_empty() || observed.as_slice() == [expected_prepared.clone()] {
        return Ok(None);
    }
    if observed.as_slice() != [expected_prepared.clone(), expected_active.clone()] {
        return Err(RustPersistenceActivationErrorV1::AuthorityLedgerMismatch);
    }
    Ok(Some(ActivationReportV1 {
        prepared_row: expected_prepared,
        rust_active_row: expected_active,
    }))
}

fn activate_under_lock(
    client: &mut postgres::Client,
) -> Result<ActivationReportV1, RustPersistenceActivationErrorV1> {
    let expected_prepared = PersistenceAuthorityLedgerRowV1::prepared()?;
    let expected_active = PersistenceAuthorityLedgerRowV1::rust_active(&expected_prepared)?;
    let mut observed = read_authority_ledger(client)?;
    if observed.is_empty() {
        let mut transaction = client.transaction().map_err(|error| {
            RustPersistenceActivationErrorV1::postgres("begin preparation", &error)
        })?;
        transaction
            .batch_execute(
                "SET LOCAL search_path TO pg_catalog; SET LOCAL synchronous_commit TO on",
            )
            .map_err(|error| {
                RustPersistenceActivationErrorV1::postgres("prepare settings", &error)
            })?;
        transaction
            .batch_execute(MIGRATION_0008_SQL)
            .map_err(|error| RustPersistenceActivationErrorV1::postgres("migration 8", &error))?;
        insert_authority_row(&mut transaction, &expected_prepared)?;
        let commit_result = transaction.commit();
        observed = read_authority_ledger(client)?;
        if observed.as_slice() != [expected_prepared.clone()] {
            if let Err(error) = commit_result {
                return Err(RustPersistenceActivationErrorV1::postgres(
                    "unresolved preparation commit",
                    &error,
                ));
            }
        }
    }
    if observed.as_slice() == [expected_prepared.clone()] {
        let mut transaction = client.transaction().map_err(|error| {
            RustPersistenceActivationErrorV1::postgres("begin activation", &error)
        })?;
        transaction
            .batch_execute(
                "SET LOCAL search_path TO pg_catalog; SET LOCAL synchronous_commit TO on",
            )
            .map_err(|error| {
                RustPersistenceActivationErrorV1::postgres("activation settings", &error)
            })?;
        transaction
            .batch_execute(MIGRATION_0009_SQL)
            .map_err(|error| RustPersistenceActivationErrorV1::postgres("migration 9", &error))?;
        insert_authority_row(&mut transaction, &expected_active)?;
        let commit_result = transaction.commit();
        observed = read_authority_ledger(client)?;
        if observed.as_slice() != [expected_prepared.clone(), expected_active.clone()] {
            if let Err(error) = commit_result {
                return Err(RustPersistenceActivationErrorV1::postgres(
                    "unresolved activation commit",
                    &error,
                ));
            }
        }
    }
    if observed != [expected_prepared.clone(), expected_active.clone()] {
        return Err(RustPersistenceActivationErrorV1::AuthorityLedgerMismatch);
    }
    Ok(ActivationReportV1 {
        prepared_row: expected_prepared,
        rust_active_row: expected_active,
    })
}

fn insert_authority_row(
    client: &mut impl GenericClient,
    row: &PersistenceAuthorityLedgerRowV1,
) -> Result<(), RustPersistenceActivationErrorV1> {
    let affected = client
        .execute(
            "INSERT INTO babylon_meta.persistence_authority_ledger \
             (ordinal, state_tag, schema_epoch, contract_sha256, reader_contract_sha256, \
              predecessor_sha256, row_sha256) VALUES ($1, $2, $3, $4, $5, $6, $7)",
            &[
                &i16::try_from(row.ordinal)
                    .map_err(|_| RustPersistenceActivationErrorV1::LedgerEncoding)?,
                &i16::from(row.state.tag()),
                &i16::try_from(row.schema_epoch)
                    .map_err(|_| RustPersistenceActivationErrorV1::LedgerEncoding)?,
                &&row.contract_sha256[..],
                &&row.reader_contract_sha256[..],
                &row.predecessor_sha256.as_ref().map(<[u8; 32]>::as_slice),
                &&row.row_sha256[..],
            ],
        )
        .map_err(|error| {
            RustPersistenceActivationErrorV1::postgres("insert authority ledger row", &error)
        })?;
    if affected != 1 {
        return Err(RustPersistenceActivationErrorV1::AuthorityLedgerMismatch);
    }
    Ok(())
}

fn read_authority_ledger(
    client: &mut impl GenericClient,
) -> Result<Vec<PersistenceAuthorityLedgerRowV1>, RustPersistenceActivationErrorV1> {
    let exists: bool = client
        .query_one(
            "SELECT pg_catalog.to_regclass('babylon_meta.persistence_authority_ledger') IS NOT NULL",
            &[],
        )
        .and_then(|row| row.try_get(0))
        .map_err(|error| {
            RustPersistenceActivationErrorV1::postgres("locate authority ledger", &error)
        })?;
    if !exists {
        return Ok(Vec::new());
    }
    let rows = client
        .query(
            "SELECT ordinal, state_tag, schema_epoch, contract_sha256, reader_contract_sha256, \
                    predecessor_sha256, row_sha256 \
             FROM babylon_meta.persistence_authority_ledger ORDER BY ordinal LIMIT 3",
            &[],
        )
        .map_err(|error| {
            RustPersistenceActivationErrorV1::postgres("read authority ledger", &error)
        })?;
    let mut decoded = Vec::new();
    decoded
        .try_reserve_exact(rows.len())
        .map_err(|_| RustPersistenceActivationErrorV1::LedgerEncoding)?;
    for row in rows {
        let ordinal: i16 = row
            .try_get(0)
            .map_err(|_| RustPersistenceActivationErrorV1::AuthorityLedgerMismatch)?;
        let state_tag: i16 = row
            .try_get(1)
            .map_err(|_| RustPersistenceActivationErrorV1::AuthorityLedgerMismatch)?;
        let schema_epoch: i16 = row
            .try_get(2)
            .map_err(|_| RustPersistenceActivationErrorV1::AuthorityLedgerMismatch)?;
        let contract: Vec<u8> = row
            .try_get(3)
            .map_err(|_| RustPersistenceActivationErrorV1::AuthorityLedgerMismatch)?;
        let reader: Vec<u8> = row
            .try_get(4)
            .map_err(|_| RustPersistenceActivationErrorV1::AuthorityLedgerMismatch)?;
        let predecessor: Option<Vec<u8>> = row
            .try_get(5)
            .map_err(|_| RustPersistenceActivationErrorV1::AuthorityLedgerMismatch)?;
        let stored_sha: Vec<u8> = row
            .try_get(6)
            .map_err(|_| RustPersistenceActivationErrorV1::AuthorityLedgerMismatch)?;
        let state = match state_tag {
            1 => PersistenceAuthorityStateV1::Prepared,
            2 => PersistenceAuthorityStateV1::RustActive,
            _ => return Err(RustPersistenceActivationErrorV1::AuthorityLedgerMismatch),
        };
        let contract: [u8; 32] = contract
            .try_into()
            .map_err(|_| RustPersistenceActivationErrorV1::AuthorityLedgerMismatch)?;
        let reader: [u8; 32] = reader
            .try_into()
            .map_err(|_| RustPersistenceActivationErrorV1::AuthorityLedgerMismatch)?;
        let predecessor = predecessor
            .map(|value| {
                value
                    .try_into()
                    .map_err(|_| RustPersistenceActivationErrorV1::AuthorityLedgerMismatch)
            })
            .transpose()?;
        let decoded_row = PersistenceAuthorityLedgerRowV1::compose(
            u16::try_from(ordinal)
                .map_err(|_| RustPersistenceActivationErrorV1::AuthorityLedgerMismatch)?,
            state,
            u16::try_from(schema_epoch)
                .map_err(|_| RustPersistenceActivationErrorV1::AuthorityLedgerMismatch)?,
            contract,
            reader,
            predecessor,
        )?;
        if stored_sha.as_slice() != decoded_row.row_sha256 {
            return Err(RustPersistenceActivationErrorV1::AuthorityLedgerMismatch);
        }
        decoded.push(decoded_row);
    }
    Ok(decoded)
}

/// A checked refusal while deriving durable inputs from one identified tick.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RustPersistenceRuntimeErrorV1 {
    /// The terminal Rust-active ledger row is absent or does not match this binary.
    ActivationRequired,
    /// A local-only runtime connection or transaction operation failed.
    Database {
        /// Stable operation name without caller-supplied text.
        operation: &'static str,
        /// Bounded secret-safe driver diagnostic, when the failure came from `PostgreSQL`.
        diagnostic: Option<PostgresDiagnosticV1>,
    },
    /// A requested campaign foundation is absent.
    FoundationAbsent,
    /// Durable campaign bytes differ from the requested exact foundation.
    CampaignConflict,
    /// This binary cannot yet reconstruct the named nonzero durable tick.
    RestartUnavailable {
        /// Exact acknowledged tick which requires reconstruction.
        last_committed_tick: u64,
    },
    /// The replay session refused preparation or acknowledgement.
    ReplayTick,
    /// A post-ack observation receipt does not name this runtime's committed tail.
    ObservationNotCurrentCommittedTail {
        /// Exact tick named by the refused receipt.
        receipt_tick: u64,
        /// Current runtime tail, or `None` before the first acknowledgement.
        current_tail: Option<u64>,
    },
    /// Recomposition did not reproduce the receipt-bound post-tick graph digest.
    ObservationGraphDigestMismatch,
    /// The report's completed tick cannot be a durable `PostgreSQL` tick.
    ResolveTickOutOfRange {
        /// Exact refused completed tick.
        actual: i64,
    },
    /// Campaign foundation capture was attempted after a real tick executed.
    FoundationAfterTickZero {
        /// Exact completed tick owned by the refused session.
        actual: i64,
    },
    /// A tick-owned exact source could not be recomposed or copied.
    ReplaySource,
    /// A delta checkpoint cannot be selected as a restart root.
    DeltaCheckpointNotRestartRoot,
    /// A governed semantic row codec refused its report-owned input.
    SemanticCodec,
    /// The aggregate committed-tick bounds refused the composed rows.
    SemanticEnvelope(CommittedTickEnvelopeErrorV1),
    /// Checked semantic-batch arithmetic overflowed.
    CapacityOverflow {
        /// Stable refused buffer or count name.
        field: &'static str,
    },
    /// A semantic producer count cannot fit its governed integer width.
    IntegerConversion {
        /// Stable refused count name.
        field: &'static str,
        /// Exact refused source value.
        value: usize,
    },
    /// A report-derived semantic buffer could not reserve exact capacity.
    Allocation {
        /// Stable refused buffer name.
        field: &'static str,
        /// Exact requested capacity.
        requested: usize,
    },
}

impl From<SemanticBatchErrorV1> for RustPersistenceRuntimeErrorV1 {
    fn from(value: SemanticBatchErrorV1) -> Self {
        match value {
            SemanticBatchErrorV1::Codec(_) => Self::SemanticCodec,
            SemanticBatchErrorV1::Envelope(error) => Self::SemanticEnvelope(error),
            SemanticBatchErrorV1::CapacityOverflow { field } => Self::CapacityOverflow { field },
            SemanticBatchErrorV1::IntegerConversion { field, value } => {
                Self::IntegerConversion { field, value }
            }
            SemanticBatchErrorV1::Allocation { field, requested } => {
                Self::Allocation { field, requested }
            }
        }
    }
}

impl From<SemanticCodecErrorV1> for RustPersistenceRuntimeErrorV1 {
    fn from(value: SemanticCodecErrorV1) -> Self {
        match value {
            SemanticCodecErrorV1::CapacityOverflow { field } => Self::CapacityOverflow { field },
            SemanticCodecErrorV1::IntegerConversion { field, value } => {
                Self::IntegerConversion { field, value }
            }
            SemanticCodecErrorV1::Allocation { field, requested } => {
                Self::Allocation { field, requested }
            }
            SemanticCodecErrorV1::ByteLimit { .. }
            | SemanticCodecErrorV1::Refusal(_)
            | SemanticCodecErrorV1::Invalid(_) => Self::SemanticCodec,
        }
    }
}

impl std::fmt::Display for RustPersistenceRuntimeErrorV1 {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "Rust persistence runtime refused: {self:?}")
    }
}

impl std::error::Error for RustPersistenceRuntimeErrorV1 {}

impl RustPersistenceRuntimeErrorV1 {
    pub(crate) fn database(operation: &'static str) -> Self {
        Self::Database {
            operation,
            diagnostic: None,
        }
    }

    pub(crate) fn postgres(operation: &'static str, error: &postgres::Error) -> Self {
        Self::Database {
            operation,
            diagnostic: Some(PostgresDiagnosticV1::capture(error)),
        }
    }
}

/// Bounded durable observation returned only after marker-last acknowledgement.
///
/// This intentionally excludes write identities, values, database coordinates,
/// and other detailed persistence evidence.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommittedTickReceiptV1 {
    resolve_tick: CommittedResolveTickV1,
    commit_disposition: ReplayCommitDispositionV1,
    graph_before: [u8; 32],
    graph_after: [u8; 32],
    prior_stable_graph_digest: [u8; 32],
    result_stable_graph_digest: [u8; 32],
    world_before: [u8; 32],
    world_after: [u8; 32],
    considered: usize,
    fired: usize,
    per_rule_considered: Vec<(String, usize)>,
    per_rule_fired: Vec<(String, usize)>,
    event_count: usize,
    event_digest: [u8; 32],
    audit_receipt_count: usize,
    material_row_count: usize,
    material_row_digest: [u8; 32],
    tick_content_hash: TickContentHashV1,
}

impl CommittedTickReceiptV1 {
    fn from_acknowledged(
        resolve_tick: CommittedResolveTickV1,
        commit_disposition: ReplayCommitDispositionV1,
        acknowledged: IdentifiedTickReportV1,
    ) -> Self {
        let prior_stable_graph_digest = acknowledged.prior_stable_graph_digest().into_bytes();
        let result_stable_graph_digest = acknowledged.result_stable_graph_digest().into_bytes();
        let event_count = acknowledged.successful_event_batch().events().len();
        let event_digest = acknowledged.successful_event_batch().source_digest();
        let material_row_count = acknowledged.material_state_rows().source_count();
        let material_row_digest = acknowledged.material_state_rows().source_digest();
        let tick_content_hash = acknowledged.tick_content_hash();
        let babylon_tick::TickReport {
            before: graph_before,
            after: graph_after,
            world_before,
            world_after,
            considered,
            fired,
            per_rule_considered,
            per_rule_fired,
            audit_receipts,
        } = acknowledged.into_report();
        Self {
            resolve_tick,
            commit_disposition,
            graph_before,
            graph_after,
            prior_stable_graph_digest,
            result_stable_graph_digest,
            world_before,
            world_after,
            considered,
            fired,
            per_rule_considered,
            per_rule_fired,
            event_count,
            event_digest,
            audit_receipt_count: audit_receipts.len(),
            material_row_count,
            material_row_digest,
            tick_content_hash,
        }
    }

    /// Return the one-based durable tick.
    #[must_use]
    pub const fn resolve_tick(&self) -> CommittedResolveTickV1 {
        self.resolve_tick
    }

    /// Return how `PostgreSQL` acknowledgement was established.
    #[must_use]
    pub const fn commit_disposition(&self) -> ReplayCommitDispositionV1 {
        self.commit_disposition
    }

    /// Return the administrative `GraphStateHash` before adjudication.
    #[must_use]
    pub const fn graph_before(&self) -> [u8; 32] {
        self.graph_before
    }

    /// Return the administrative `GraphStateHash` after adjudication.
    #[must_use]
    pub const fn graph_after(&self) -> [u8; 32] {
        self.graph_after
    }

    /// Return the stable graph-state digest bound to the acknowledged prior.
    #[must_use]
    pub const fn prior_stable_graph_digest(&self) -> [u8; 32] {
        self.prior_stable_graph_digest
    }

    /// Return the stable graph-state digest bound to the acknowledged result.
    #[must_use]
    pub const fn result_stable_graph_digest(&self) -> [u8; 32] {
        self.result_stable_graph_digest
    }

    /// Return the nominal-world hash before adjudication.
    #[must_use]
    pub const fn world_before(&self) -> [u8; 32] {
        self.world_before
    }

    /// Return the nominal-world hash after adjudication.
    #[must_use]
    pub const fn world_after(&self) -> [u8; 32] {
        self.world_after
    }

    /// Return the total number of guard evaluations.
    #[must_use]
    pub const fn considered(&self) -> usize {
        self.considered
    }

    /// Return the total number of subjects that fired.
    #[must_use]
    pub const fn fired(&self) -> usize {
        self.fired
    }

    /// Borrow per-rule guard counts in governed causal order.
    #[must_use]
    pub fn per_rule_considered(&self) -> &[(String, usize)] {
        &self.per_rule_considered
    }

    /// Borrow per-rule firing counts in governed causal order.
    #[must_use]
    pub fn per_rule_fired(&self) -> &[(String, usize)] {
        &self.per_rule_fired
    }

    /// Return the number of retained successful events.
    #[must_use]
    pub const fn event_count(&self) -> usize {
        self.event_count
    }

    /// Return the digest of the exact tick event section.
    #[must_use]
    pub const fn event_digest(&self) -> [u8; 32] {
        self.event_digest
    }

    /// Return the number of identity-free causal audit receipts.
    #[must_use]
    pub const fn audit_receipt_count(&self) -> usize {
        self.audit_receipt_count
    }

    /// Return the number of canonical material rows.
    #[must_use]
    pub const fn material_row_count(&self) -> usize {
        self.material_row_count
    }

    /// Return the digest of the canonical material-row aggregate.
    #[must_use]
    pub const fn material_row_digest(&self) -> [u8; 32] {
        self.material_row_digest
    }

    /// Return the constitutional content identity acknowledged by `PostgreSQL`.
    #[must_use]
    pub const fn tick_content_hash(&self) -> TickContentHashV1 {
        self.tick_content_hash
    }
}

/// Sole production owner of a replay session and its Rust persistence authority.
pub struct DurableReplayRuntimeV1<G> {
    config: Config,
    campaign_id: CampaignId,
    session: ReplayTickSession<G>,
    foundation: CampaignFoundationV1,
    activation_row: PersistenceAuthorityLedgerRowV1,
    last_committed_tick: Option<CommittedResolveTickV1>,
}

impl DurableReplayRuntimeV1<HypergraphStore> {
    /// Capture and durably install a new tick-zero campaign under active Rust authority.
    ///
    /// # Errors
    /// Refuses absent authority, a nonzero session, an exact campaign conflict, or a database
    /// failure before exposing a runtime.
    pub fn create(
        config: &Config,
        campaign_id: CampaignId,
        session: ReplayTickSession<HypergraphStore>,
        content_bundle: FoundationContentBundleV1,
    ) -> Result<Self, RustPersistenceRuntimeErrorV1> {
        let activation_row = require_active_authority(config)?;
        let foundation = CampaignFoundationV1::capture(&session, content_bundle)?;
        persist_campaign_foundation_v1(config, campaign_id, &foundation)?;
        if let Some(last) = read_last_committed_tick_v1(config, campaign_id)? {
            return Err(RustPersistenceRuntimeErrorV1::RestartUnavailable {
                last_committed_tick: last.get(),
            });
        }
        Ok(Self {
            config: config.clone(),
            campaign_id,
            session,
            foundation,
            activation_row,
            last_committed_tick: None,
        })
    }

    /// Reconstruct a durable campaign from its latest exact full checkpoint.
    ///
    /// # Errors
    /// Refuses absent authority or foundation, any exact replay-source mismatch, a database
    /// failure, or a full-checkpoint section that cannot reproduce typed state.
    pub fn open(
        config: &Config,
        campaign_id: CampaignId,
    ) -> Result<Self, RustPersistenceRuntimeErrorV1> {
        let activation_row = require_active_authority(config)?;
        let foundation = hydrate_campaign_foundation_v1(config, campaign_id)?;
        let bundle = foundation.content_bundle();
        let scenario = std::str::from_utf8(bundle.scenario_source_bytes())
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
        let prelude = bundle
            .prelude_source_bytes()
            .map(std::str::from_utf8)
            .transpose()
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
        let rules = std::str::from_utf8(bundle.rule_source_bytes())
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
        let material = MaterialStateV1::try_new(
            michigan_dynamic_hex_foundation_v1()
                .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?,
        )
        .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
        let session = ReplayTickSession::new(
            scenario,
            prelude,
            rules,
            HypergraphStore::new(),
            foundation.replay_session_identity().clone(),
            foundation.rng_seed(),
            foundation.content_digest().clone(),
            foundation.reference_digest(),
            material,
        )
        .map_err(|_| RustPersistenceRuntimeErrorV1::ReplayTick)?;
        let verification_bundle = FoundationContentBundleV1::try_new(
            scenario,
            prelude,
            rules,
            bundle.defines_bytes(),
            bundle.reference_bundle_manifest_bytes(),
        )?;
        let verification = CampaignFoundationV1::capture(&session, verification_bundle)?;
        if verification.canonical_bytes() != foundation.canonical_bytes() {
            return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
        }
        let (session, last_committed_tick) = replay_durable_tail_v1(config, campaign_id, session)?;
        validate_campaign_catalog_tail_v1(config, campaign_id, last_committed_tick)?;
        Ok(Self {
            config: config.clone(),
            campaign_id,
            session,
            foundation,
            activation_row,
            last_committed_tick,
        })
    }

    /// Adjudicate one detached candidate, commit typed rows marker-last, then publish it.
    ///
    /// # Errors
    /// Every replay, semantic, database, retry, or acknowledgement refusal leaves the caller
    /// sink and live session tick unchanged.
    pub fn advance_and_commit(
        &mut self,
        sink: &mut CollectingSink,
        actions: &OrderedPracticeActionBatchV1,
    ) -> Result<CommittedTickReceiptV1, RustPersistenceRuntimeErrorV1> {
        let candidate = self
            .session
            .prepare_advance(actions)
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplayTick)?;
        let prepared = prepare_committed_tick_v1(candidate.report())?;
        let checkpoint = CommittedFullCheckpointV1::capture(
            self.campaign_id,
            prepared.resolve_tick(),
            candidate.report(),
        )?;
        let resolve_tick = prepared.resolve_tick();
        let tick_content_hash = prepared.tick_content_hash();
        let envelope = prepared.into_envelope(self.campaign_id)?;
        let disposition = commit_typed_tick_v1(
            &self.config,
            self.campaign_id,
            candidate.report(),
            &checkpoint,
            &envelope,
        )?;
        let acknowledgement =
            ReplayCommitAcknowledgementV1::new(disposition, resolve_tick.get(), tick_content_hash);
        let acknowledged = self
            .session
            .acknowledge_prepared(sink, candidate, acknowledgement)
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplayTick)?;
        self.last_committed_tick = Some(resolve_tick);
        Ok(CommittedTickReceiptV1::from_acknowledged(
            resolve_tick,
            disposition,
            acknowledged,
        ))
    }

    /// Recompose the exact graph state bound to the current acknowledged receipt.
    ///
    /// This observation stays separate from the bounded receipt so persistence
    /// acknowledgements remain identity- and value-free. The caller must present
    /// the current runtime tail, and recomposition must reproduce its sealed
    /// post-tick graph digest before any state is returned.
    ///
    /// # Errors
    /// Refuses a receipt for any other tick, graph-state recomposition failure,
    /// or a recomposed digest that differs from the acknowledged graph digest.
    pub fn observe_committed_graph_state_v1(
        &self,
        receipt: &CommittedTickReceiptV1,
    ) -> Result<StableGraphStateV1, RustPersistenceRuntimeErrorV1> {
        if self.last_committed_tick != Some(receipt.resolve_tick()) {
            return Err(
                RustPersistenceRuntimeErrorV1::ObservationNotCurrentCommittedTail {
                    receipt_tick: receipt.resolve_tick().get(),
                    current_tail: self.last_committed_tick.map(CommittedResolveTickV1::get),
                },
            );
        }
        let observed = self.observe_current_stable_graph_state_v1()?;
        if observed.digest().as_bytes() != &receipt.result_stable_graph_digest() {
            return Err(RustPersistenceRuntimeErrorV1::ObservationGraphDigestMismatch);
        }
        Ok(observed)
    }

    /// Recompose the runtime's current stable graph without mutating it.
    ///
    /// This unbound observation supports capturing a pre-tick state. A caller
    /// must bind its digest to the next acknowledged receipt before exposing
    /// any derived values.
    ///
    /// # Errors
    /// Refuses any stable-identity, topology, numeric, bound, or allocation
    /// failure while recomposing the current graph.
    pub fn observe_current_stable_graph_state_v1(
        &self,
    ) -> Result<StableGraphStateV1, RustPersistenceRuntimeErrorV1> {
        self.session
            .stable_graph_state()
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplayTick)
    }

    /// Borrow the exact durable campaign foundation.
    #[must_use]
    pub const fn foundation(&self) -> &CampaignFoundationV1 {
        &self.foundation
    }

    /// Borrow the terminal authority row used to construct this runtime.
    #[must_use]
    pub const fn activation_row(&self) -> &PersistenceAuthorityLedgerRowV1 {
        &self.activation_row
    }

    /// Return the last marker acknowledged by this runtime.
    #[must_use]
    pub const fn last_committed_tick(&self) -> Option<CommittedResolveTickV1> {
        self.last_committed_tick
    }
}

/// Hydrate one exact durable foundation under terminal Rust authority.
///
/// # Errors
/// Returns an authority, target, database, absence, digest, or replay-source refusal.
pub fn hydrate_campaign_foundation_v1(
    config: &Config,
    campaign_id: CampaignId,
) -> Result<CampaignFoundationV1, RustPersistenceRuntimeErrorV1> {
    let _active = require_active_authority(config)?;
    validate_legacy_connection_target(config)
        .map_err(|_| RustPersistenceRuntimeErrorV1::database("validate foundation target"))?;
    let mut client = config.connect(NoTls).map_err(|error| {
        RustPersistenceRuntimeErrorV1::postgres("connect foundation reader", &error)
    })?;
    let row = client
        .query_opt(
            "SELECT stable_graph, world_registers, resolver_manifest, prepared_environment, \
                    replay_session_id, rng_seed, defines_hash, rules_hash, ref_digest, \
                    scenario_source, prelude_source, rule_source, defines_bytes, \
                    reference_manifest_bytes, foundation_sha256 \
             FROM babylon_state.campaign_foundation WHERE campaign_id = $1::uuid",
            &[campaign_id.as_uuid()],
        )
        .map_err(|error| {
            RustPersistenceRuntimeErrorV1::postgres("read campaign foundation", &error)
        })?
        .ok_or(RustPersistenceRuntimeErrorV1::FoundationAbsent)?;
    let stable_graph: Vec<u8> = decode_runtime_column(&row, 0)?;
    let world_registers: Vec<u8> = decode_runtime_column(&row, 1)?;
    let resolver_manifest: Vec<u8> = decode_runtime_column(&row, 2)?;
    let prepared_environment: Vec<u8> = decode_runtime_column(&row, 3)?;
    let replay_session_id: String = decode_runtime_column(&row, 4)?;
    let rng_seed: i64 = decode_runtime_column(&row, 5)?;
    let defines_hash = decode_digest_column(&row, 6)?;
    let rules_hash = decode_digest_column(&row, 7)?;
    let reference_digest = decode_digest_column(&row, 8)?;
    let scenario_source: String = decode_runtime_column(&row, 9)?;
    let prelude_source: Option<String> = decode_runtime_column(&row, 10)?;
    let rule_source: String = decode_runtime_column(&row, 11)?;
    let defines_bytes: Vec<u8> = decode_runtime_column(&row, 12)?;
    let reference_manifest: Vec<u8> = decode_runtime_column(&row, 13)?;
    let foundation_sha256 = decode_digest_column(&row, 14)?;
    CampaignFoundationV1::from_persisted(
        stable_graph,
        world_registers,
        resolver_manifest,
        prepared_environment,
        &replay_session_id,
        rng_seed,
        defines_hash,
        rules_hash,
        reference_digest,
        &scenario_source,
        prelude_source.as_deref(),
        &rule_source,
        &defines_bytes,
        &reference_manifest,
        foundation_sha256,
    )
}

fn require_active_authority(
    config: &Config,
) -> Result<PersistenceAuthorityLedgerRowV1, RustPersistenceRuntimeErrorV1> {
    validate_legacy_connection_target(config)
        .map_err(|_| RustPersistenceRuntimeErrorV1::ActivationRequired)?;
    let mut client = config.connect(NoTls).map_err(|error| {
        RustPersistenceRuntimeErrorV1::postgres("connect authority reader", &error)
    })?;
    require_active_authority_client(&mut client)
}

fn require_active_authority_client(
    client: &mut impl GenericClient,
) -> Result<PersistenceAuthorityLedgerRowV1, RustPersistenceRuntimeErrorV1> {
    let expected_prepared = PersistenceAuthorityLedgerRowV1::prepared()
        .map_err(|_| RustPersistenceRuntimeErrorV1::ActivationRequired)?;
    let expected_active = PersistenceAuthorityLedgerRowV1::rust_active(&expected_prepared)
        .map_err(|_| RustPersistenceRuntimeErrorV1::ActivationRequired)?;
    let observed = read_authority_ledger(client).map_err(|error| match error {
        RustPersistenceActivationErrorV1::Database {
            operation,
            diagnostic,
        } => RustPersistenceRuntimeErrorV1::Database {
            operation,
            diagnostic,
        },
        _ => RustPersistenceRuntimeErrorV1::ActivationRequired,
    })?;
    if observed != [expected_prepared, expected_active.clone()] {
        return Err(RustPersistenceRuntimeErrorV1::ActivationRequired);
    }
    Ok(expected_active)
}

fn persist_campaign_foundation_v1(
    config: &Config,
    campaign_id: CampaignId,
    foundation: &CampaignFoundationV1,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    validate_legacy_connection_target(config).map_err(|_| {
        RustPersistenceRuntimeErrorV1::database("validate foundation writer target")
    })?;
    let mut client = config.connect(NoTls).map_err(|error| {
        RustPersistenceRuntimeErrorV1::postgres("connect foundation writer", &error)
    })?;
    let mut transaction = client.transaction().map_err(|error| {
        RustPersistenceRuntimeErrorV1::postgres("begin foundation writer", &error)
    })?;
    transaction
        .batch_execute("SET LOCAL search_path TO pg_catalog; SET LOCAL synchronous_commit TO on")
        .map_err(|error| {
            RustPersistenceRuntimeErrorV1::postgres("foundation writer settings", &error)
        })?;
    insert_campaign_foundation_rows_v1(&mut transaction, campaign_id, foundation)?;
    transaction.commit().map_err(|error| {
        RustPersistenceRuntimeErrorV1::postgres("commit campaign foundation", &error)
    })?;
    let hydrated = hydrate_campaign_foundation_v1(config, campaign_id)?;
    if hydrated.canonical_bytes() != foundation.canonical_bytes() {
        return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
    }
    Ok(())
}

fn insert_campaign_foundation_rows_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    foundation: &CampaignFoundationV1,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    let _active = require_active_authority_client(client)?;
    let replay_session = std::str::from_utf8(foundation.replay_session_identity().as_bytes())
        .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
    let bundle = foundation.content_bundle();
    let base_reference_digest = base_reference_digest_v1(
        bundle.reference_bundle_manifest_bytes(),
        foundation.reference_digest(),
    )?;
    client
        .execute(
            "INSERT INTO babylon_state.campaign \
             (campaign_id, replay_layout_version, rng_layout_version, replay_session_id, rng_seed, \
              defines_hash, rules_hash, ref_digest) \
             VALUES ($1, 1, 2, $2, $3, $4, $5, $6) ON CONFLICT (campaign_id) DO NOTHING",
            &[
                campaign_id.as_uuid(),
                &replay_session,
                &i64::from_be_bytes(foundation.rng_seed().to_be_bytes()),
                &&foundation.content_digest().defines_hash[..],
                &&foundation.content_digest().rules_hash[..],
                &&base_reference_digest[..],
            ],
        )
        .map_err(|error| {
            RustPersistenceRuntimeErrorV1::postgres("insert campaign identity", &error)
        })?;
    let scenario = std::str::from_utf8(bundle.scenario_source_bytes())
        .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
    let prelude = bundle
        .prelude_source_bytes()
        .map(std::str::from_utf8)
        .transpose()
        .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
    let rules = std::str::from_utf8(bundle.rule_source_bytes())
        .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
    let foundation_sha256 = sha256_of(foundation.canonical_bytes());
    client
        .execute(
            "INSERT INTO babylon_state.campaign_foundation \
             (campaign_id, stable_graph, world_registers, resolver_manifest, prepared_environment, \
              replay_session_id, rng_seed, defines_hash, rules_hash, ref_digest, scenario_source, \
              prelude_source, rule_source, defines_bytes, reference_manifest_bytes, foundation_sha256) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16) \
             ON CONFLICT (campaign_id) DO NOTHING",
            &[
                campaign_id.as_uuid(),
                &foundation.stable_graph_bytes(),
                &foundation.world_register_bytes(),
                &foundation.resolver_manifest_bytes(),
                &foundation.prepared_environment_bytes(),
                &replay_session,
                &i64::from_be_bytes(foundation.rng_seed().to_be_bytes()),
                &&foundation.content_digest().defines_hash[..],
                &&foundation.content_digest().rules_hash[..],
                &foundation.reference_digest().as_bytes().as_slice(),
                &scenario,
                &prelude,
                &rules,
                &bundle.defines_bytes(),
                &bundle.reference_bundle_manifest_bytes(),
                &&foundation_sha256[..],
            ],
        )
        .map_err(|error| {
            RustPersistenceRuntimeErrorV1::postgres("insert campaign foundation", &error)
        })?;
    let stored_sha: Vec<u8> = client
        .query_one(
            "SELECT foundation_sha256 FROM babylon_state.campaign_foundation \
             WHERE campaign_id = $1::uuid",
            &[campaign_id.as_uuid()],
        )
        .and_then(|row| row.try_get(0))
        .map_err(|error| {
            RustPersistenceRuntimeErrorV1::postgres("verify campaign foundation", &error)
        })?;
    if stored_sha.as_slice() != foundation_sha256 {
        return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
    }
    ensure_campaign_catalog_row_v1(client, campaign_id, foundation)?;
    Ok(())
}

fn base_reference_digest_v1(
    reference_manifest: &[u8],
    expected_bundle_digest: babylon_kernel::tick_content_hash::RefDigestV1,
) -> Result<[u8; 32], RustPersistenceRuntimeErrorV1> {
    let expected_len = REFERENCE_BUNDLE_DOMAIN_V1
        .len()
        .checked_add(64)
        .ok_or(RustPersistenceRuntimeErrorV1::ReplaySource)?;
    if reference_manifest.len() != expected_len
        || !reference_manifest.starts_with(REFERENCE_BUNDLE_DOMAIN_V1)
        || sha256_of(reference_manifest) != *expected_bundle_digest.as_bytes()
    {
        return Err(RustPersistenceRuntimeErrorV1::ReplaySource);
    }
    reference_manifest[REFERENCE_BUNDLE_DOMAIN_V1.len()..REFERENCE_BUNDLE_DOMAIN_V1.len() + 32]
        .try_into()
        .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)
}

fn read_last_committed_tick_v1(
    config: &Config,
    campaign_id: CampaignId,
) -> Result<Option<CommittedResolveTickV1>, RustPersistenceRuntimeErrorV1> {
    let mut client = config.connect(NoTls).map_err(|error| {
        RustPersistenceRuntimeErrorV1::postgres("connect marker reader", &error)
    })?;
    let row = client
        .query_opt(
            "SELECT resolve_tick FROM babylon_state.tick_commit \
             WHERE campaign_id = $1::uuid ORDER BY resolve_tick DESC LIMIT 1",
            &[campaign_id.as_uuid()],
        )
        .map_err(|error| RustPersistenceRuntimeErrorV1::postgres("read last marker", &error))?;
    row.map(|row| {
        let raw: i64 = decode_runtime_column(&row, 0)?;
        let raw =
            u64::try_from(raw).map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)?;
        CommittedResolveTickV1::try_from(raw)
            .map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)
    })
    .transpose()
}

fn validate_campaign_catalog_tail_v1(
    config: &Config,
    campaign_id: CampaignId,
    last_committed_tick: Option<CommittedResolveTickV1>,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    let mut client = config.connect(NoTls).map_err(|error| {
        RustPersistenceRuntimeErrorV1::postgres("connect retained campaign catalog reader", &error)
    })?;
    let catalog = read_campaign_catalog_row_v1(&mut client, campaign_id)?
        .ok_or(RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    let expected = last_committed_tick.map_or(0, CommittedResolveTickV1::get);
    if catalog.last_tick() == expected {
        Ok(())
    } else {
        Err(RustPersistenceRuntimeErrorV1::CampaignConflict)
    }
}

fn commit_typed_tick_v1(
    config: &Config,
    campaign_id: CampaignId,
    report: &IdentifiedTickReportV1,
    checkpoint: &CommittedFullCheckpointV1,
    envelope: &CommittedTickEnvelopeV1,
) -> Result<ReplayCommitDispositionV1, RustPersistenceRuntimeErrorV1> {
    let claim = envelope.claim();
    if claim.campaign_id() != campaign_id
        || claim.resolve_tick()
            != u64::try_from(report.result_registers().completed_tick())
                .map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)?
        || claim.tick_content_hash() != report.tick_content_hash()
        || checkpoint.sections().len() != 9
    {
        return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
    }
    let resolve_tick = i64::try_from(claim.resolve_tick())
        .map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    validate_legacy_connection_target(config)
        .map_err(|_| RustPersistenceRuntimeErrorV1::database("validate typed tick target"))?;
    let mut client = config.connect(NoTls).map_err(|error| {
        RustPersistenceRuntimeErrorV1::postgres("connect typed tick writer", &error)
    })?;
    if marker_matches_envelope_v1(&mut client, report, envelope)? {
        return Ok(ReplayCommitDispositionV1::ReconciledAfterAmbiguousCommit);
    }
    let mut transaction = client
        .transaction()
        .map_err(|error| RustPersistenceRuntimeErrorV1::postgres("begin typed tick", &error))?;
    transaction
        .batch_execute("SET LOCAL search_path TO pg_catalog; SET LOCAL synchronous_commit TO on")
        .map_err(|error| RustPersistenceRuntimeErrorV1::postgres("typed tick settings", &error))?;
    let _active = require_active_authority_client(&mut transaction)?;
    let locked = transaction
        .query_opt(
            "SELECT campaign_id FROM babylon_state.campaign WHERE campaign_id = $1::uuid FOR UPDATE",
            &[campaign_id.as_uuid()],
        )
        .map_err(|error| RustPersistenceRuntimeErrorV1::postgres("lock campaign", &error))?;
    if locked.is_none() {
        return Err(RustPersistenceRuntimeErrorV1::FoundationAbsent);
    }
    let last_tick: Option<i64> = transaction
        .query_one(
            "SELECT pg_catalog.max(resolve_tick) FROM babylon_state.tick_commit WHERE campaign_id = $1::uuid",
            &[campaign_id.as_uuid()],
        )
        .and_then(|row| row.try_get(0))
        .map_err(|error| {
            RustPersistenceRuntimeErrorV1::postgres("read campaign marker tail", &error)
        })?;
    let expected_predecessor = resolve_tick
        .checked_sub(1)
        .ok_or(RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    if last_tick.unwrap_or(0) != expected_predecessor {
        return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
    }

    insert_typed_tick_pre_marker_rows_v1(
        &mut transaction,
        campaign_id,
        resolve_tick,
        report,
        checkpoint,
        envelope,
    )?;
    commit_marker_last_v1(
        config,
        transaction,
        campaign_id,
        resolve_tick,
        report,
        envelope,
    )
}

fn commit_marker_last_v1(
    config: &Config,
    mut transaction: postgres::Transaction<'_>,
    campaign_id: CampaignId,
    resolve_tick: i64,
    report: &IdentifiedTickReportV1,
    envelope: &CommittedTickEnvelopeV1,
) -> Result<ReplayCommitDispositionV1, RustPersistenceRuntimeErrorV1> {
    #[cfg(test)]
    if LIVE_FAIL_BEFORE_MARKER.swap(false, std::sync::atomic::Ordering::SeqCst) {
        transaction.batch_execute("SELECT 1 / 0").map_err(|error| {
            RustPersistenceRuntimeErrorV1::postgres("injected pre-marker refusal", &error)
        })?;
    }

    let predecessor = resolve_tick
        .checked_sub(1)
        .ok_or(RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    advance_campaign_catalog_tick_v1(&mut transaction, campaign_id, predecessor, resolve_tick)?;

    // Constitutional visibility point: no durable row may be inserted after this marker.
    require_single_insert_v1(
        transaction.execute(
            "INSERT INTO babylon_state.tick_commit \
             (campaign_id, resolve_tick, envelope_layout_version, tick_content_hash, envelope_digest) \
             VALUES ($1::uuid, $2, 1, $3, $4)",
            &[
                campaign_id.as_uuid(),
                &resolve_tick,
                &&envelope.claim().tick_content_hash().as_bytes()[..],
                &&envelope.digest().as_bytes()[..],
            ],
        ),
        "insert marker last",
    )?;
    match commit_transaction_v1(transaction) {
        TickCommitAttemptV1::Acknowledged => Ok(ReplayCommitDispositionV1::Committed),
        TickCommitAttemptV1::Ambiguous { diagnostic } => {
            let mut reconciliation = config.connect(NoTls).map_err(|error| {
                RustPersistenceRuntimeErrorV1::postgres("reconnect ambiguous commit", &error)
            })?;
            if marker_matches_envelope_v1(&mut reconciliation, report, envelope)? {
                #[cfg(test)]
                LIVE_RECONCILIATIONS.fetch_add(1, std::sync::atomic::Ordering::SeqCst);
                Ok(ReplayCommitDispositionV1::ReconciledAfterAmbiguousCommit)
            } else {
                Err(RustPersistenceRuntimeErrorV1::Database {
                    operation: "unresolved ambiguous commit",
                    diagnostic,
                })
            }
        }
    }
}

fn insert_typed_tick_pre_marker_rows_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    resolve_tick: i64,
    report: &IdentifiedTickReportV1,
    checkpoint: &CommittedFullCheckpointV1,
    envelope: &CommittedTickEnvelopeV1,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    let action_layout = i16::try_from(report.action_batch_layout_version())
        .map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    require_single_insert_v1(
        client.execute(
            "INSERT INTO babylon_state.tick_action_batch_v1 \
             (campaign_id, resolve_tick, layout_version, action_batch_digest, exact_action_batch_bytes) \
             VALUES ($1::uuid, $2, $3, $4, $5)",
            &[
                campaign_id.as_uuid(),
                &resolve_tick,
                &action_layout,
                &&report.action_batch_digest().as_bytes()[..],
                &report.action_batch_bytes(),
            ],
        ),
        "insert action batch",
    )?;
    insert_typed_graph_rows_v1(client, campaign_id, resolve_tick, report)?;
    insert_typed_material_rows_v1(client, campaign_id, resolve_tick, report)?;
    insert_typed_event_rows_v1(client, campaign_id, resolve_tick, report)?;
    insert_full_checkpoint_v1(client, campaign_id, resolve_tick, checkpoint)?;
    require_single_insert_v1(
        client.execute(
            "INSERT INTO babylon_state.archive_dirty_receipt_v1 \
             (campaign_id, resolve_tick, tick_content_hash) VALUES ($1::uuid, $2, $3)",
            &[
                campaign_id.as_uuid(),
                &resolve_tick,
                &&envelope.claim().tick_content_hash().as_bytes()[..],
            ],
        ),
        "insert archive dirty receipt",
    )
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum TickCommitAttemptV1 {
    Acknowledged,
    Ambiguous {
        diagnostic: Option<PostgresDiagnosticV1>,
    },
}

fn commit_transaction_v1(transaction: postgres::Transaction<'_>) -> TickCommitAttemptV1 {
    if let Err(error) = transaction.commit() {
        return TickCommitAttemptV1::Ambiguous {
            diagnostic: Some(PostgresDiagnosticV1::capture(&error)),
        };
    }
    #[cfg(test)]
    if LIVE_COMMIT_AS_AMBIGUOUS.swap(false, std::sync::atomic::Ordering::SeqCst) {
        return TickCommitAttemptV1::Ambiguous { diagnostic: None };
    }
    TickCommitAttemptV1::Acknowledged
}

#[cfg(test)]
static LIVE_FAIL_BEFORE_MARKER: std::sync::atomic::AtomicBool =
    std::sync::atomic::AtomicBool::new(false);
#[cfg(test)]
static LIVE_COMMIT_AS_AMBIGUOUS: std::sync::atomic::AtomicBool =
    std::sync::atomic::AtomicBool::new(false);
#[cfg(test)]
static LIVE_RECONCILIATIONS: std::sync::atomic::AtomicUsize =
    std::sync::atomic::AtomicUsize::new(0);

fn marker_matches_envelope_v1(
    client: &mut impl GenericClient,
    report: &IdentifiedTickReportV1,
    envelope: &CommittedTickEnvelopeV1,
) -> Result<bool, RustPersistenceRuntimeErrorV1> {
    let claim = envelope.claim();
    let Some(stored) = read_stored_typed_tick_v1(
        client,
        claim.campaign_id(),
        claim.resolve_tick(),
        report.result_stable_graph().scenario_scope(),
    )?
    else {
        return Ok(false);
    };
    let catalog = read_campaign_catalog_row_v1(client, claim.campaign_id())?
        .ok_or(RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    if catalog.last_tick() != claim.resolve_tick() {
        return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
    }
    let action_layout = i16::try_from(report.action_batch_layout_version())
        .map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    if stored.action_layout() != action_layout
        || stored.action_digest().as_slice() != report.action_batch_digest().as_bytes()
        || stored.action_bytes() != report.action_batch_bytes()
    {
        return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
    }
    envelope
        .classify_retry_against(stored.envelope())
        .map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    Ok(true)
}

fn replay_durable_tail_v1(
    config: &Config,
    campaign_id: CampaignId,
    mut session: ReplayTickSession<HypergraphStore>,
) -> Result<
    (
        ReplayTickSession<HypergraphStore>,
        Option<CommittedResolveTickV1>,
    ),
    RustPersistenceRuntimeErrorV1,
> {
    let mut client = config.connect(NoTls).map_err(|error| {
        RustPersistenceRuntimeErrorV1::postgres("connect restart reader", &error)
    })?;
    let Some(root) = select_durable_restart_root_v1(&mut client, campaign_id)? else {
        return Ok((session, None));
    };
    let scenario_scope =
        restore_durable_restart_root_v1(&mut client, campaign_id, &mut session, &root)?;
    let last = replay_ticks_after_restart_root_v1(
        &mut client,
        campaign_id,
        &mut session,
        &scenario_scope,
        &root,
    )?;
    Ok((session, Some(last)))
}

struct DurableRestartRootV1 {
    resolve_tick_sql: i64,
    resolve_tick: u64,
    marker_count: i64,
}

fn select_durable_restart_root_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
) -> Result<Option<DurableRestartRootV1>, RustPersistenceRuntimeErrorV1> {
    let root_tick: Option<i64> = client
        .query_one(
            "SELECT pg_catalog.max(marker.resolve_tick) \
             FROM babylon_state.tick_commit AS marker \
             JOIN babylon_state.checkpoint_manifest AS checkpoint \
               ON checkpoint.campaign_id = marker.campaign_id \
              AND checkpoint.resolve_tick = marker.resolve_tick \
              AND checkpoint.completeness_tag = 1 \
             WHERE marker.campaign_id = $1::uuid",
            &[campaign_id.as_uuid()],
        )
        .and_then(|row| row.try_get(0))
        .map_err(|error| {
            RustPersistenceRuntimeErrorV1::postgres("select latest full checkpoint", &error)
        })?;
    let marker_count: i64 = client
        .query_one(
            "SELECT pg_catalog.count(*) FROM babylon_state.tick_commit \
             WHERE campaign_id = $1::uuid",
            &[campaign_id.as_uuid()],
        )
        .and_then(|row| row.try_get(0))
        .map_err(|error| {
            RustPersistenceRuntimeErrorV1::postgres("count restart markers", &error)
        })?;
    let Some(root_tick_sql) = root_tick else {
        if marker_count == 0 {
            return Ok(None);
        }
        return Err(RustPersistenceRuntimeErrorV1::DeltaCheckpointNotRestartRoot);
    };
    let root_tick = u64::try_from(root_tick_sql)
        .map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    let prefix_count: i64 = client
        .query_one(
            "SELECT pg_catalog.count(*) FROM babylon_state.tick_commit \
             WHERE campaign_id = $1::uuid AND resolve_tick <= $2",
            &[campaign_id.as_uuid(), &root_tick_sql],
        )
        .and_then(|row| row.try_get(0))
        .map_err(|error| {
            RustPersistenceRuntimeErrorV1::postgres("count checkpoint prefix markers", &error)
        })?;
    if u64::try_from(prefix_count).ok() != Some(root_tick) {
        return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
    }
    Ok(Some(DurableRestartRootV1 {
        resolve_tick_sql: root_tick_sql,
        resolve_tick: root_tick,
        marker_count,
    }))
}

fn restore_durable_restart_root_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    session: &mut ReplayTickSession<HypergraphStore>,
    root: &DurableRestartRootV1,
) -> Result<String, RustPersistenceRuntimeErrorV1> {
    let scenario_scope = session
        .stable_graph_state()
        .map_err(|_| RustPersistenceRuntimeErrorV1::ReplayTick)?
        .scenario_scope()
        .to_owned();
    let stored =
        read_stored_typed_tick_v1(client, campaign_id, root.resolve_tick, &scenario_scope)?
            .ok_or(RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    validate_stored_empty_actions_v1(&stored, session, root.resolve_tick)?;
    validate_checkpoint_identity_sections_v1(&stored, session)?;
    session
        .restore_full_checkpoint(
            root.resolve_tick_sql,
            stored.graph_state(),
            stored.material_rows(),
            stored
                .checkpoint_section(2)
                .ok_or(RustPersistenceRuntimeErrorV1::CampaignConflict)?,
        )
        .map_err(|_| RustPersistenceRuntimeErrorV1::ReplayTick)?;
    Ok(scenario_scope)
}

fn replay_ticks_after_restart_root_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    session: &mut ReplayTickSession<HypergraphStore>,
    scenario_scope: &str,
    root: &DurableRestartRootV1,
) -> Result<CommittedResolveTickV1, RustPersistenceRuntimeErrorV1> {
    let tail_ticks = client
        .query(
            "SELECT resolve_tick FROM babylon_state.tick_commit \
             WHERE campaign_id = $1::uuid AND resolve_tick > $2 ORDER BY resolve_tick",
            &[campaign_id.as_uuid(), &root.resolve_tick_sql],
        )
        .map_err(|error| RustPersistenceRuntimeErrorV1::postgres("read restart tail", &error))?;
    let mut expected_tick = root
        .resolve_tick
        .checked_add(1)
        .ok_or(RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    let mut sink = CollectingSink::default();
    let mut last = CommittedResolveTickV1::try_from(root.resolve_tick)
        .map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    for row in tail_ticks {
        let stored_tick: i64 = decode_runtime_column(&row, 0)?;
        let stored_tick = u64::try_from(stored_tick)
            .map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)?;
        if stored_tick != expected_tick {
            return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
        }
        let stored = read_stored_typed_tick_v1(client, campaign_id, expected_tick, scenario_scope)?
            .ok_or(RustPersistenceRuntimeErrorV1::CampaignConflict)?;
        validate_stored_empty_actions_v1(&stored, session, expected_tick)?;
        let actions =
            OrderedPracticeActionBatchV1::empty(session.session_identity().clone(), expected_tick)
                .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
        let candidate = session
            .prepare_advance(&actions)
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplayTick)?;
        let prepared = prepare_committed_tick_v1(candidate.report())?;
        let resolve_tick = prepared.resolve_tick();
        if resolve_tick.get() != expected_tick {
            return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
        }
        let checkpoint =
            CommittedFullCheckpointV1::capture(campaign_id, resolve_tick, candidate.report())?;
        let tick_content_hash = prepared.tick_content_hash();
        let envelope = prepared.into_envelope(campaign_id)?;
        envelope
            .classify_retry_against(stored.envelope())
            .map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)?;
        validate_stored_checkpoint_sections_v1(&stored, &checkpoint)?;
        let acknowledgement = ReplayCommitAcknowledgementV1::new(
            ReplayCommitDispositionV1::ReconciledAfterAmbiguousCommit,
            expected_tick,
            tick_content_hash,
        );
        session
            .acknowledge_prepared(&mut sink, candidate, acknowledgement)
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplayTick)?;
        last = resolve_tick;
        expected_tick = expected_tick
            .checked_add(1)
            .ok_or(RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    }
    if u64::try_from(root.marker_count).ok() != Some(last.get()) {
        return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
    }
    Ok(last)
}

fn validate_stored_empty_actions_v1(
    stored: &crate::stored_tick::StoredTypedTickV1,
    session: &ReplayTickSession<HypergraphStore>,
    resolve_tick: u64,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    let actions =
        OrderedPracticeActionBatchV1::empty(session.session_identity().clone(), resolve_tick)
            .map_err(|_| RustPersistenceRuntimeErrorV1::ReplaySource)?;
    if stored.action_layout() != 1
        || stored.action_digest().as_slice() != actions.digest().as_bytes()
        || stored.action_bytes() != actions.canonical_bytes()
    {
        return Err(RustPersistenceRuntimeErrorV1::ReplaySource);
    }
    Ok(())
}

fn validate_checkpoint_identity_sections_v1(
    stored: &crate::stored_tick::StoredTypedTickV1,
    session: &ReplayTickSession<HypergraphStore>,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    let mut content_digest = Vec::new();
    content_digest.try_reserve_exact(64).map_err(|_| {
        RustPersistenceRuntimeErrorV1::Allocation {
            field: "restart content digest",
            requested: 64,
        }
    })?;
    content_digest.extend_from_slice(&session.content_digest().defines_hash);
    content_digest.extend_from_slice(&session.content_digest().rules_hash);
    let seed = session.rng_seed().to_be_bytes();
    let reference = session.reference_digest();
    let expected = [
        (3_u8, session.resolver_manifest_bytes()),
        (4, session.prepared_environment_bytes()),
        (5, session.session_identity().as_bytes()),
        (6, seed.as_slice()),
        (7, content_digest.as_slice()),
        (8, reference.as_bytes().as_slice()),
    ];
    if expected.into_iter().any(|(tag, bytes)| {
        stored
            .checkpoint_section(tag)
            .is_none_or(|stored| stored != bytes)
    }) {
        return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
    }
    Ok(())
}

fn validate_stored_checkpoint_sections_v1(
    stored: &crate::stored_tick::StoredTypedTickV1,
    checkpoint: &CommittedFullCheckpointV1,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    if checkpoint.exact_section_bytes().len() != 9
        || checkpoint
            .exact_section_bytes()
            .iter()
            .enumerate()
            .any(|(index, expected)| {
                let tag = u8::try_from(index + 1).ok();
                tag.and_then(|tag| stored.checkpoint_section(tag)) != Some(expected.as_slice())
            })
    {
        return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
    }
    Ok(())
}

fn insert_typed_graph_rows_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    resolve_tick: i64,
    report: &IdentifiedTickReportV1,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    let rows = report.result_stable_graph().rows();
    for (local_name, node_type) in rows.nodes() {
        require_single_insert_v1(
            client.execute(
                "INSERT INTO babylon_state.graph_node_v1 \
                 (campaign_id, resolve_tick, local_name, node_type) VALUES ($1::uuid, $2, $3, $4)",
                &[campaign_id.as_uuid(), &resolve_tick, local_name, node_type],
            ),
            "insert graph node",
        )?;
    }
    for (local_name, qname, bits) in rows.node_f64() {
        let value_bits = bit_pattern_i64_v1(*bits);
        require_single_insert_v1(
            client.execute(
                "INSERT INTO babylon_state.graph_node_f64_v1 \
                 (campaign_id, resolve_tick, local_name, qname, value_bits) \
                 VALUES ($1::uuid, $2, $3, $4, $5)",
                &[
                    campaign_id.as_uuid(),
                    &resolve_tick,
                    local_name,
                    qname,
                    &value_bits,
                ],
            ),
            "insert graph node f64",
        )?;
    }
    for (edge_type, source, target, strength_bits) in rows.edges() {
        let strength_bits = bit_pattern_i64_v1(*strength_bits);
        require_single_insert_v1(
            client.execute(
                "INSERT INTO babylon_state.graph_edge_v1 \
                 (campaign_id, resolve_tick, edge_type, source_local_name, target_local_name, strength_bits) \
                 VALUES ($1::uuid, $2, $3, $4, $5, $6)",
                &[
                    campaign_id.as_uuid(),
                    &resolve_tick,
                    edge_type,
                    source,
                    target,
                    &strength_bits,
                ],
            ),
            "insert graph edge",
        )?;
    }
    for (local_name, hyperedge_type, members) in rows.hyperedges() {
        require_single_insert_v1(
            client.execute(
                "INSERT INTO babylon_state.graph_hyperedge_v1 \
                 (campaign_id, resolve_tick, local_name, hyperedge_type) VALUES ($1::uuid, $2, $3, $4)",
                &[campaign_id.as_uuid(), &resolve_tick, local_name, hyperedge_type],
            ),
            "insert graph hyperedge",
        )?;
        for (position, member) in members.iter().enumerate() {
            let position = checked_position_v1(position)?;
            require_single_insert_v1(
                client.execute(
                    "INSERT INTO babylon_state.graph_hyperedge_member_v1 \
                     (campaign_id, resolve_tick, local_name, position, member) \
                     VALUES ($1::uuid, $2, $3, $4, $5)",
                    &[
                        campaign_id.as_uuid(),
                        &resolve_tick,
                        local_name,
                        &position,
                        member,
                    ],
                ),
                "insert graph hyperedge member",
            )?;
        }
    }
    insert_graph_value_rows_v1(client, campaign_id, resolve_tick, report)
}

fn insert_graph_value_rows_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    resolve_tick: i64,
    report: &IdentifiedTickReportV1,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    let rows = report.result_stable_graph().rows();
    for (edge_type, source, target, qname, bits) in rows.edge_f64() {
        let value_bits = bit_pattern_i64_v1(*bits);
        require_single_insert_v1(
            client.execute(
                "INSERT INTO babylon_state.graph_edge_f64_v1 \
                 (campaign_id, resolve_tick, edge_type, source_local_name, target_local_name, qname, value_bits) \
                 VALUES ($1::uuid, $2, $3, $4, $5, $6, $7)",
                &[
                    campaign_id.as_uuid(),
                    &resolve_tick,
                    edge_type,
                    source,
                    target,
                    qname,
                    &value_bits,
                ],
            ),
            "insert graph edge f64",
        )?;
    }
    for (local_name, qname, micro_units) in rows.node_currency() {
        let decimal = micro_units.to_string();
        require_single_insert_v1(
            client.execute(
                "INSERT INTO babylon_state.graph_node_currency_v1 \
                 (campaign_id, resolve_tick, local_name, qname, micro_units) \
                 VALUES ($1::uuid, $2, $3, $4, $5::text::numeric)",
                &[
                    campaign_id.as_uuid(),
                    &resolve_tick,
                    local_name,
                    qname,
                    &decimal,
                ],
            ),
            "insert graph node currency",
        )?;
    }
    for (local_name, qname, bits) in rows.hyperedge_f64() {
        let value_bits = bit_pattern_i64_v1(*bits);
        require_single_insert_v1(
            client.execute(
                "INSERT INTO babylon_state.graph_hyperedge_f64_v1 \
                 (campaign_id, resolve_tick, local_name, qname, value_bits) \
                 VALUES ($1::uuid, $2, $3, $4, $5)",
                &[
                    campaign_id.as_uuid(),
                    &resolve_tick,
                    local_name,
                    qname,
                    &value_bits,
                ],
            ),
            "insert graph hyperedge f64",
        )?;
    }
    Ok(())
}

fn insert_typed_material_rows_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    resolve_tick: i64,
    report: &IdentifiedTickReportV1,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    let rows = report.material_state_rows();
    for row in rows.world_registers().rows() {
        let prefix: [&(dyn ToSql + Sync); 3] = [campaign_id.as_uuid(), &resolve_tick, &row.qname()];
        insert_bsl_value_row_v1(
            client,
            "INSERT INTO babylon_state.world_register_v1 \
             (campaign_id, resolve_tick, register_name, value_tag, int_value, currency_value, \
              real_bits, ratio_bits, ratio_min_bits, ratio_max_bits, bool_value, enum_type, enum_member, stable_key) \
             VALUES ($1::uuid, $2, $3, $4, $5, $6::text::numeric, $7, $8, $9, $10, $11, $12, $13, $14)",
            &prefix,
            row.value(),
            "insert world register",
        )?;
    }
    for row in rows.territories().rows() {
        let territory_id = stable_key_bytes_v1(row.territory_id())?;
        require_single_insert_v1(
            client.execute(
                "INSERT INTO babylon_state.territory_state_v1 \
                 (campaign_id, resolve_tick, territory_id) VALUES ($1::uuid, $2, $3)",
                &[campaign_id.as_uuid(), &resolve_tick, &territory_id],
            ),
            "insert territory state",
        )?;
        for (position, (field_name, value)) in row.ordered_fields().iter().enumerate() {
            let position = checked_position_v1(position)?;
            let prefix: [&(dyn ToSql + Sync); 5] = [
                campaign_id.as_uuid(),
                &resolve_tick,
                &territory_id,
                &position,
                field_name,
            ];
            insert_bsl_value_row_v1(
                client,
                "INSERT INTO babylon_state.territory_state_field_v1 \
                 (campaign_id, resolve_tick, territory_id, position, field_name, value_tag, int_value, \
                  currency_value, real_bits, ratio_bits, ratio_min_bits, ratio_max_bits, bool_value, \
                  enum_type, enum_member, stable_key) \
                 VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8::text::numeric, $9, $10, $11, $12, $13, $14, $15, $16)",
                &prefix,
                value,
                "insert territory field",
            )?;
        }
    }
    insert_dynamic_hex_rows_v1(client, campaign_id, resolve_tick, report)?;
    insert_organization_state_rows_v1(client, campaign_id, resolve_tick, report)
}

fn insert_dynamic_hex_rows_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    resolve_tick: i64,
    report: &IdentifiedTickReportV1,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    let rows = report.material_state_rows().dynamic_hexes().rows();
    let expected =
        u64::try_from(rows.len()).map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)?;
    let sink = client
        .copy_in(
            "COPY babylon_state.hex_state_delta_v1 \
             (campaign_id, resolve_tick, cell_id, c_bits, v_bits, s_bits, k_bits, \
              biocapacity_stock_bits, energy_stock_bits, raw_material_stock_bits, \
              internet_access_pct_bits, surveillance_coupling_bits) FROM STDIN BINARY",
        )
        .map_err(|error| {
            RustPersistenceRuntimeErrorV1::postgres("begin dynamic hex state copy", &error)
        })?;
    let mut writer = BinaryCopyInWriter::new(
        sink,
        &[
            Type::UUID,
            Type::INT8,
            Type::INT8,
            Type::INT8,
            Type::INT8,
            Type::INT8,
            Type::INT8,
            Type::INT8,
            Type::INT8,
            Type::INT8,
            Type::INT8,
            Type::INT8,
        ],
    );
    for row in rows {
        let cell_id = i64::try_from(row.cell_id().as_u64())
            .map_err(|_| RustPersistenceRuntimeErrorV1::SemanticCodec)?;
        let values = row.value_bits().map(bit_pattern_i64_v1);
        writer
            .write(&[
                campaign_id.as_uuid(),
                &resolve_tick,
                &cell_id,
                &values[0],
                &values[1],
                &values[2],
                &values[3],
                &values[4],
                &values[5],
                &values[6],
                &values[7],
                &values[8],
            ])
            .map_err(|error| {
                RustPersistenceRuntimeErrorV1::postgres("write dynamic hex state copy", &error)
            })?;
    }
    let inserted = writer.finish().map_err(|error| {
        RustPersistenceRuntimeErrorV1::postgres("finish dynamic hex state copy", &error)
    })?;
    if inserted != expected {
        return Err(RustPersistenceRuntimeErrorV1::database(
            "count dynamic hex state copy",
        ));
    }
    Ok(())
}

fn insert_organization_state_rows_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    resolve_tick: i64,
    report: &IdentifiedTickReportV1,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    for row in report.material_state_rows().organizations().rows() {
        let organization_id = stable_key_bytes_v1(row.organization_id())?;
        let prefix: [&(dyn ToSql + Sync); 3] =
            [campaign_id.as_uuid(), &resolve_tick, &organization_id];
        insert_bsl_value_row_v1(
            client,
            "INSERT INTO babylon_state.organization_state_v1 \
             (campaign_id, resolve_tick, organization_id, organization_kind_tag, \
              organization_kind_int, organization_kind_currency, organization_kind_real_bits, \
              organization_kind_ratio_bits, organization_kind_ratio_min_bits, \
              organization_kind_ratio_max_bits, organization_kind_bool, \
              organization_kind_enum_type, organization_kind_enum_member, organization_kind_stable_key) \
             VALUES ($1::uuid, $2, $3, $4, $5, $6::text::numeric, $7, $8, $9, $10, $11, $12, $13, $14)",
            &prefix,
            row.organization_kind(),
            "insert organization state",
        )?;
        for (position, territory_id) in row.ordered_territory_ids().iter().enumerate() {
            let position = checked_position_v1(position)?;
            let territory_id = stable_key_bytes_v1(territory_id)?;
            require_single_insert_v1(
                client.execute(
                    "INSERT INTO babylon_state.organization_territory_v1 \
                     (campaign_id, resolve_tick, organization_id, position, territory_id) \
                     VALUES ($1::uuid, $2, $3, $4, $5)",
                    &[
                        campaign_id.as_uuid(),
                        &resolve_tick,
                        &organization_id,
                        &position,
                        &territory_id,
                    ],
                ),
                "insert organization territory",
            )?;
        }
        for (position, (field_name, value)) in row.ordered_fields().iter().enumerate() {
            let position = checked_position_v1(position)?;
            let prefix: [&(dyn ToSql + Sync); 5] = [
                campaign_id.as_uuid(),
                &resolve_tick,
                &organization_id,
                &position,
                field_name,
            ];
            insert_bsl_value_row_v1(
                client,
                "INSERT INTO babylon_state.organization_state_field_v1 \
                 (campaign_id, resolve_tick, organization_id, position, field_name, value_tag, int_value, \
                  currency_value, real_bits, ratio_bits, ratio_min_bits, ratio_max_bits, bool_value, \
                  enum_type, enum_member, stable_key) \
                 VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8::text::numeric, $9, $10, $11, $12, $13, $14, $15, $16)",
                &prefix,
                value,
                "insert organization field",
            )?;
        }
    }
    Ok(())
}

fn insert_typed_event_rows_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    resolve_tick: i64,
    report: &IdentifiedTickReportV1,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    for (ordinal, event) in report.successful_event_batch().events().iter().enumerate() {
        let ordinal = i64::try_from(ordinal).map_err(|_| {
            RustPersistenceRuntimeErrorV1::IntegerConversion {
                field: "successful event ordinal",
                value: ordinal,
            }
        })?;
        require_single_insert_v1(
            client.execute(
                "INSERT INTO babylon_state.tick_event_v1 \
                 (campaign_id, resolve_tick, ordinal, event_type) VALUES ($1::uuid, $2, $3, $4)",
                &[
                    campaign_id.as_uuid(),
                    &resolve_tick,
                    &ordinal,
                    &event.event_type(),
                ],
            ),
            "insert tick event",
        )?;
        for (position, (field_name, value)) in event.fields().iter().enumerate() {
            let position = checked_position_v1(position)?;
            let prefix: [&(dyn ToSql + Sync); 5] = [
                campaign_id.as_uuid(),
                &resolve_tick,
                &ordinal,
                &position,
                field_name,
            ];
            insert_bsl_value_row_v1(
                client,
                "INSERT INTO babylon_state.tick_event_field_v1 \
                 (campaign_id, resolve_tick, ordinal, position, field_name, value_tag, int_value, \
                  currency_value, real_bits, ratio_bits, ratio_min_bits, ratio_max_bits, bool_value, \
                  enum_type, enum_member, stable_key) \
                 VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8::text::numeric, $9, $10, $11, $12, $13, $14, $15, $16)",
                &prefix,
                value,
                "insert tick event field",
            )?;
        }
    }
    Ok(())
}

fn insert_full_checkpoint_v1(
    client: &mut impl GenericClient,
    campaign_id: CampaignId,
    resolve_tick: i64,
    checkpoint: &CommittedFullCheckpointV1,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    let completeness_tag = 1_i16;
    require_single_insert_v1(
        client.execute(
            "INSERT INTO babylon_state.checkpoint_manifest \
             (campaign_id, resolve_tick, completeness_tag, manifest_bytes, manifest_sha256) \
             VALUES ($1::uuid, $2, $3, $4, $5)",
            &[
                campaign_id.as_uuid(),
                &resolve_tick,
                &completeness_tag,
                &checkpoint.manifest_bytes(),
                &&checkpoint.manifest_sha256()[..],
            ],
        ),
        "insert checkpoint manifest",
    )?;
    if checkpoint.sections().len() != checkpoint.exact_section_bytes().len() {
        return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
    }
    for (section, exact_bytes) in checkpoint
        .sections()
        .iter()
        .zip(checkpoint.exact_section_bytes())
    {
        if sha256_of(exact_bytes) != section.sha256() {
            return Err(RustPersistenceRuntimeErrorV1::CampaignConflict);
        }
        let section_tag = i16::from(section.tag().tag());
        let ordinal = 0_i64;
        require_single_insert_v1(
            client.execute(
                "INSERT INTO babylon_state.checkpoint_section_v1 \
                 (campaign_id, resolve_tick, section_tag, ordinal, exact_section_bytes) \
                 VALUES ($1::uuid, $2, $3, $4, $5)",
                &[
                    campaign_id.as_uuid(),
                    &resolve_tick,
                    &section_tag,
                    &ordinal,
                    exact_bytes,
                ],
            ),
            "insert checkpoint section",
        )?;
    }
    Ok(())
}

struct BslSqlValueV1 {
    tag: i16,
    int_value: Option<i64>,
    currency_value: Option<String>,
    real_bits: Option<i64>,
    ratio_bits: Option<i64>,
    ratio_min_bits: Option<i64>,
    ratio_max_bits: Option<i64>,
    bool_value: Option<bool>,
    enum_type: Option<String>,
    enum_member: Option<String>,
    stable_key: Option<Vec<u8>>,
}

impl BslSqlValueV1 {
    fn from_stable(value: &StableBslValueV1) -> Result<Self, RustPersistenceRuntimeErrorV1> {
        let mut row = Self {
            tag: 0,
            int_value: None,
            currency_value: None,
            real_bits: None,
            ratio_bits: None,
            ratio_min_bits: None,
            ratio_max_bits: None,
            bool_value: None,
            enum_type: None,
            enum_member: None,
            stable_key: None,
        };
        match value {
            StableBslValueV1::Int(value) => {
                row.tag = 1;
                row.int_value = Some(*value);
            }
            StableBslValueV1::CurrencyMicroUnits(value) => {
                row.tag = 2;
                row.currency_value = Some(value.to_string());
            }
            StableBslValueV1::RealBits(bits) => {
                row.tag = 3;
                row.real_bits = Some(bit_pattern_i64_v1(*bits));
            }
            StableBslValueV1::RatioBits { value, floor, cap } => {
                row.tag = 4;
                row.ratio_bits = Some(bit_pattern_i64_v1(*value));
                row.ratio_min_bits = floor.map(bit_pattern_i64_v1);
                row.ratio_max_bits = cap.map(bit_pattern_i64_v1);
            }
            StableBslValueV1::Bool(value) => {
                row.tag = 5;
                row.bool_value = Some(*value);
            }
            StableBslValueV1::Enum { enum_type, member } => {
                row.tag = 6;
                row.enum_type = Some(enum_type.clone());
                row.enum_member = Some(member.clone());
            }
            StableBslValueV1::Node(key) => {
                row.tag = 7;
                row.stable_key = Some(stable_key_bytes_v1(key)?);
            }
            StableBslValueV1::Hyperedge(key) => {
                row.tag = 8;
                row.stable_key = Some(stable_key_bytes_v1(key)?);
            }
            StableBslValueV1::Edge(key) => {
                row.tag = 9;
                row.stable_key = Some(stable_key_bytes_v1(key)?);
            }
        }
        Ok(row)
    }
}

fn insert_bsl_value_row_v1(
    client: &mut impl GenericClient,
    sql: &str,
    prefix: &[&(dyn ToSql + Sync)],
    value: &StableBslValueV1,
    operation: &'static str,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    let value = BslSqlValueV1::from_stable(value)?;
    let mut params: Vec<&(dyn ToSql + Sync)> = Vec::new();
    params.try_reserve_exact(prefix.len() + 11).map_err(|_| {
        RustPersistenceRuntimeErrorV1::Allocation {
            field: "typed BSL SQL parameters",
            requested: prefix.len() + 11,
        }
    })?;
    params.extend_from_slice(prefix);
    params.extend_from_slice(&[
        &value.tag,
        &value.int_value,
        &value.currency_value,
        &value.real_bits,
        &value.ratio_bits,
        &value.ratio_min_bits,
        &value.ratio_max_bits,
        &value.bool_value,
        &value.enum_type,
        &value.enum_member,
        &value.stable_key,
    ]);
    require_single_insert_v1(client.execute(sql, &params), operation)
}

fn stable_key_bytes_v1(
    key: &babylon_graph::stable_element::StableElementKeyV1,
) -> Result<Vec<u8>, RustPersistenceRuntimeErrorV1> {
    key.canonical_bytes()
        .map_err(|_| RustPersistenceRuntimeErrorV1::SemanticCodec)
}

fn bit_pattern_i64_v1(bits: u64) -> i64 {
    i64::from_be_bytes(bits.to_be_bytes())
}

fn checked_position_v1(position: usize) -> Result<i32, RustPersistenceRuntimeErrorV1> {
    i32::try_from(position).map_err(|_| RustPersistenceRuntimeErrorV1::IntegerConversion {
        field: "typed child position",
        value: position,
    })
}

fn require_single_insert_v1(
    result: Result<u64, postgres::Error>,
    operation: &'static str,
) -> Result<(), RustPersistenceRuntimeErrorV1> {
    let affected =
        result.map_err(|error| RustPersistenceRuntimeErrorV1::postgres(operation, &error))?;
    if affected == 1 {
        Ok(())
    } else {
        Err(RustPersistenceRuntimeErrorV1::database(operation))
    }
}

fn decode_runtime_column<T: postgres::types::FromSqlOwned>(
    row: &postgres::Row,
    index: usize,
) -> Result<T, RustPersistenceRuntimeErrorV1> {
    row.try_get(index)
        .map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)
}

fn decode_digest_column(
    row: &postgres::Row,
    index: usize,
) -> Result<[u8; 32], RustPersistenceRuntimeErrorV1> {
    let bytes: Vec<u8> = decode_runtime_column(row, index)?;
    bytes
        .try_into()
        .map_err(|_| RustPersistenceRuntimeErrorV1::CampaignConflict)
}

/// Exact report-derived inputs held before a durable commit attempt.
///
/// This type owns no replay engine and cannot adjudicate or recompute a tick.
/// It is deliberately not yet convertible to a committed envelope: material
/// and full-checkpoint composition remain successor cutover work.
#[derive(Debug, PartialEq, Eq)]
pub struct PreparedCommittedTickV1 {
    resolve_tick: CommittedResolveTickV1,
    tick_content_hash: TickContentHashV1,
    graph_event_batches: GraphEventSemanticBatchesV1,
    material_state_rows: Vec<CommittedTickRowV1>,
    checkpoint_rows: CheckpointRowsV1,
    archive_dirty_receipt: ArchiveDirtyReceiptV1,
}

impl PreparedCommittedTickV1 {
    /// Return the exact positive resolve tick carried by the source report.
    #[must_use]
    pub const fn resolve_tick(&self) -> CommittedResolveTickV1 {
        self.resolve_tick
    }

    /// Return the constitutional content identity carried by the source report.
    #[must_use]
    pub const fn tick_content_hash(&self) -> TickContentHashV1 {
        self.tick_content_hash
    }

    /// Borrow the exact report-derived checkpoint producer.
    #[must_use]
    pub const fn checkpoint_rows(&self) -> &CheckpointRowsV1 {
        &self.checkpoint_rows
    }

    /// Borrow the exact singular Archive work receipt.
    #[must_use]
    pub const fn archive_dirty_receipt(&self) -> &ArchiveDirtyReceiptV1 {
        &self.archive_dirty_receipt
    }

    fn into_envelope(
        self,
        campaign_id: CampaignId,
    ) -> Result<CommittedTickEnvelopeV1, RustPersistenceRuntimeErrorV1> {
        let claim = TickCommitClaimV1::compose(
            campaign_id,
            self.resolve_tick.get(),
            self.tick_content_hash,
        );
        let (graph, event) = self.graph_event_batches.into_rows();
        CommittedTickEnvelopeV1::compose(
            claim,
            CommittedTickRowFamiliesV1 {
                graph,
                state: self.material_state_rows,
                event,
                checkpoint: self.checkpoint_rows.into_rows(),
                archive_dirty_receipt: self.archive_dirty_receipt.into_row(),
            },
        )
        .map_err(RustPersistenceRuntimeErrorV1::SemanticEnvelope)
    }

    #[cfg(test)]
    pub(crate) fn graph_row_count(&self) -> usize {
        self.graph_event_batches.graph_row_count()
    }

    #[cfg(test)]
    pub(crate) fn event_row_count(&self) -> usize {
        self.graph_event_batches.event_row_count()
    }
}

/// Derive one stopped, database-free durable candidate from one identified report.
///
/// # Errors
/// Returns the first resolve-tick, codec, allocation, or aggregate-bound
/// refusal. This function never parses rules, executes a tick, or judges game
/// mechanics; every semantic source comes from `report`.
pub fn prepare_committed_tick_v1(
    report: &IdentifiedTickReportV1,
) -> Result<PreparedCommittedTickV1, RustPersistenceRuntimeErrorV1> {
    let completed_tick = report.result_registers().completed_tick();
    let raw_resolve_tick = u64::try_from(completed_tick).map_err(|_| {
        RustPersistenceRuntimeErrorV1::ResolveTickOutOfRange {
            actual: completed_tick,
        }
    })?;
    let resolve_tick = CommittedResolveTickV1::try_from(raw_resolve_tick).map_err(
        |_: CommittedResolveTickErrorV1| RustPersistenceRuntimeErrorV1::ResolveTickOutOfRange {
            actual: completed_tick,
        },
    )?;
    let graph_event_batches = compose_graph_event_semantic_batches_v1(report)?;
    let material_state_rows = compose_material_state_rows_v1(report.material_state_rows())?;
    let checkpoint_rows = compose_checkpoint_rows_v1(report, resolve_tick)?;
    let archive_dirty_receipt = compose_archive_dirty_receipt_v1(report)?;
    Ok(PreparedCommittedTickV1 {
        resolve_tick,
        tick_content_hash: report.tick_content_hash(),
        graph_event_batches,
        material_state_rows,
        checkpoint_rows,
        archive_dirty_receipt,
    })
}

#[cfg(test)]
mod live_tests {
    use std::str::FromStr;
    use std::sync::atomic::Ordering;

    use babylon_bsl::rule_pipeline::split_content;
    use babylon_bsl::rules_hash_of;
    use babylon_kernel::replay::{ReplaySeed, ReplaySessionIdV1};
    use babylon_kernel::sha256_of;
    use babylon_kernel::tick_content_hash::RefDigestV1;
    use babylon_kernel::ContentDigest;
    use postgres::{Config, NoTls};
    use uuid::Uuid;

    use super::*;

    const DSN_ENV: &str = "BABYLON_LEGACY_ADOPTER_TEST_DSN";
    const ACK_ENV: &str = "BABYLON_LEGACY_ADOPTER_DISPOSABLE_ACK";
    const ACK: &str = "I_UNDERSTAND_PER20_DROPS_SCRATCH_DATABASES_ROLES_AND_CREATED_BABYLON_INTEL";
    const CANARY_ENV: &str = "BABYLON_LEGACY_ADOPTER_DISPOSABLE_CANARY";
    const TEMPLATE_DB_ENV: &str = "BABYLON_RUNTIME_TEMPLATE_DB";
    const DEFINES: &[u8] = br#"{"alpha":1}"#;
    const REFERENCE_BUNDLE_DOMAIN: &[u8] = b"babylon.h3.reference-bundle-composite.v1\0";
    const SCENARIO: &str = r"
(scenario test/runtime-live
  (defvocabulary NodeType (SOCIAL_CLASS))
  (deffield social-class/draw coefficient extensive)
  (node class-a NodeType/SOCIAL_CLASS (social-class/draw 0.0c)))
";
    const RULE: &str = r#"
(rule production/runtime-live
  :role mechanic
  :evidence derived
  :material-basis "live marker-last persistence contract"
  :fuel 32
  (bindings (binding draw :field social-class/draw))
  (when #t)
  (effects
    (update-node self social-class/draw (set 0.25c))
    (emit EventType/CHECKPOINTED (subject self))))
"#;

    #[test]
    #[ignore = "requires the task-owned disposable PER-20 PostgreSQL runtime"]
    fn live_marker_last_commit_and_restart_are_atomic() {
        let base = validated_base_config();
        verify_frozen_python_estate_activation(&base);
        let template = validated_template_name();
        let database = TestDatabase::create_from_template(&base, &template, "runtimeatomic");
        let config = database.config(&base);
        let campaign_id =
            CampaignId::from_uuid(Uuid::from_u128(0x2810_0000_0000_0000_0000_0000_0000_00a1));
        let (session, bundle) = runtime_fixture();
        let mut runtime = DurableReplayRuntimeV1::create(&config, campaign_id, session, bundle)
            .expect("runtime constructs after activation");
        let metadata = crate::metadata::RetainedMetadataStoreV1::new(&config);
        seed_and_verify_navigation_metadata(&metadata, campaign_id);
        let actions = OrderedPracticeActionBatchV1::empty(
            runtime.foundation().replay_session_identity().clone(),
            1,
        )
        .expect("first action batch");
        let mut sink = CollectingSink::default();

        LIVE_FAIL_BEFORE_MARKER.store(true, Ordering::SeqCst);
        let Err(RustPersistenceRuntimeErrorV1::Database {
            operation: "injected pre-marker refusal",
            diagnostic: Some(diagnostic),
        }) = runtime.advance_and_commit(&mut sink, &actions)
        else {
            panic!("injected refusal must retain its server diagnostic");
        };
        assert_eq!(diagnostic.sqlstate(), Some("22012"));
        assert!(sink.events.is_empty());
        assert_eq!(runtime.last_committed_tick(), None);
        assert_eq!(committed_payload_row_count(&config, campaign_id), 0);

        let receipt = runtime
            .advance_and_commit(&mut sink, &actions)
            .expect("identical retry commits");
        assert_eq!(receipt.resolve_tick().get(), 1);
        assert_eq!(
            receipt.commit_disposition(),
            ReplayCommitDispositionV1::Committed
        );
        assert_eq!(receipt.considered(), 1);
        assert_eq!(receipt.fired(), 1);
        assert_eq!(receipt.event_count(), 1);
        assert_eq!(receipt.audit_receipt_count(), 2);
        assert!(receipt.material_row_count() > 0);
        assert_eq!(runtime.last_committed_tick(), Some(receipt.resolve_tick()));
        assert_eq!(sink.events.len(), 1);
        assert_eq!(marker_row_count(&config, campaign_id), 1);
        assert_eq!(
            metadata
                .campaign(campaign_id)
                .expect("advanced catalog reads")
                .expect("campaign remains retained")
                .last_tick(),
            1
        );

        let reopened = DurableReplayRuntimeV1::open(&config, campaign_id)
            .expect("marker-owned checkpoint restarts");
        assert_eq!(reopened.last_committed_tick(), Some(receipt.resolve_tick()));
        database.cleanup();
    }

    fn seed_and_verify_navigation_metadata(
        metadata: &crate::metadata::RetainedMetadataStoreV1,
        campaign_id: CampaignId,
    ) {
        let initial_catalog = metadata
            .campaign(campaign_id)
            .expect("catalog reads")
            .expect("runtime creates the retained catalog row");
        assert_eq!(initial_catalog.last_tick(), 0);
        metadata
            .replace_watchlist(
                campaign_id,
                &["social-class/C001".to_owned(), "territory/wayne".to_owned()],
            )
            .expect("watchlist replaces atomically");
        metadata
            .replace_jumplist(
                campaign_id,
                &["territory/wayne".to_owned(), "territory/wayne".to_owned()],
            )
            .expect("jumplist preserves legal duplicates");
        metadata
            .replace_breadcrumbs(
                campaign_id,
                &["world/michigan".to_owned(), "territory/wayne".to_owned()],
            )
            .expect("breadcrumbs replace atomically");
        assert_eq!(
            metadata
                .watchlist(campaign_id)
                .expect("watchlist reads")
                .iter()
                .map(crate::metadata::WatchlistRowV1::entity_id)
                .collect::<Vec<_>>(),
            ["social-class/C001", "territory/wayne"]
        );
        assert_eq!(
            metadata
                .jumplist(campaign_id)
                .expect("jumplist reads")
                .iter()
                .map(crate::metadata::JumplistRowV1::entity_id)
                .collect::<Vec<_>>(),
            ["territory/wayne", "territory/wayne"]
        );
        assert_eq!(
            metadata
                .breadcrumbs(campaign_id)
                .expect("breadcrumbs read")
                .iter()
                .map(crate::metadata::BreadcrumbRowV1::entity_id)
                .collect::<Vec<_>>(),
            ["world/michigan", "territory/wayne"]
        );
    }

    fn verify_frozen_python_estate_activation(base: &Config) {
        let database = TestDatabase::create(base, "runtimelegacy");
        let config = database.config(base);
        crate::schema_epoch::legacy_epoch_fixture::build_frozen_python_estate(&config);
        let first = activate_rust_persistence_v1(&config)
            .expect("the exact empty frozen Python estate activates");
        let second =
            activate_rust_persistence_v1(&config).expect("terminal Rust activation is idempotent");
        assert_eq!(first, second);
        let row = config
            .connect(NoTls)
            .expect("disposition connection")
            .query_one(
                "SELECT pg_catalog.count(*), \
                        pg_catalog.bool_and(observed_row_count = 0 \
                          AND ordered_semantic_sha256 = pg_catalog.sha256(''::pg_catalog.bytea) \
                          AND disposition_tag = 1), \
                        pg_catalog.to_regclass('public.game_session') IS NULL, \
                        pg_catalog.to_regclass('public._babylon_schema_stamp') IS NULL, \
                        pg_catalog.to_regclass('public.document_chunk') IS NOT NULL \
                 FROM babylon_meta.python_relation_disposition_v1",
                &[],
            )
            .expect("disposition proof");
        assert_eq!(row.try_get::<_, i64>(0).expect("disposition count"), 61);
        assert!(row.try_get::<_, bool>(1).expect("zero-row proof"));
        assert!(row.try_get::<_, bool>(2).expect("game authority retired"));
        assert!(row
            .try_get::<_, bool>(3)
            .expect("Python schema stamp retired"));
        assert!(row.try_get::<_, bool>(4).expect("AI periphery retained"));
        database.cleanup();
    }

    #[test]
    #[ignore = "requires the task-owned disposable PER-20 PostgreSQL runtime"]
    fn live_commit_ambiguity_reconciliation_is_exact() {
        let base = validated_base_config();
        let template = validated_template_name();
        let database = TestDatabase::create_from_template(&base, &template, "runtimeambiguous");
        let config = database.config(&base);
        let campaign_id =
            CampaignId::from_uuid(Uuid::from_u128(0x2810_0000_0000_0000_0000_0000_0000_00a2));
        let (session, bundle) = runtime_fixture();
        let mut runtime = DurableReplayRuntimeV1::create(&config, campaign_id, session, bundle)
            .expect("runtime constructs after activation");
        let actions = OrderedPracticeActionBatchV1::empty(
            runtime.foundation().replay_session_identity().clone(),
            1,
        )
        .expect("first action batch");
        let mut sink = CollectingSink::default();

        LIVE_RECONCILIATIONS.store(0, Ordering::SeqCst);
        LIVE_COMMIT_AS_AMBIGUOUS.store(true, Ordering::SeqCst);
        let receipt = runtime
            .advance_and_commit(&mut sink, &actions)
            .expect("committed ambiguity reconciles through the exact marker");
        assert_eq!(receipt.resolve_tick().get(), 1);
        assert_eq!(
            receipt.commit_disposition(),
            ReplayCommitDispositionV1::ReconciledAfterAmbiguousCommit
        );
        assert_eq!(LIVE_RECONCILIATIONS.load(Ordering::SeqCst), 1);
        assert_eq!(sink.events.len(), 1);
        assert_eq!(marker_row_count(&config, campaign_id), 1);

        let reopened = DurableReplayRuntimeV1::open(&config, campaign_id)
            .expect("reconciled marker is the restart root");
        assert_eq!(reopened.last_committed_tick(), Some(receipt.resolve_tick()));
        database.cleanup();
    }

    #[test]
    #[ignore = "requires the task-owned disposable PER-20 PostgreSQL runtime"]
    fn live_retry_and_restart_refuse_a_mutated_typed_payload() {
        let base = validated_base_config();
        let template = validated_template_name();
        let database = TestDatabase::create_from_template(&base, &template, "runtimemutated");
        let config = database.config(&base);
        let campaign_id =
            CampaignId::from_uuid(Uuid::from_u128(0x2810_0000_0000_0000_0000_0000_0000_00a3));
        let (session, bundle) = runtime_fixture();
        let mut runtime = DurableReplayRuntimeV1::create(&config, campaign_id, session, bundle)
            .expect("runtime constructs after activation");
        let actions = OrderedPracticeActionBatchV1::empty(
            runtime.foundation().replay_session_identity().clone(),
            1,
        )
        .expect("first action batch");
        runtime
            .advance_and_commit(&mut CollectingSink::default(), &actions)
            .expect("first tick commits");
        config
            .connect(NoTls)
            .expect("mutation connection")
            .execute(
                "UPDATE babylon_state.graph_node_f64_v1 SET value_bits = 0 \
                 WHERE campaign_id = $1::uuid AND resolve_tick = 1",
                &[campaign_id.as_uuid()],
            )
            .expect("typed test row mutates");

        assert_eq!(
            DurableReplayRuntimeV1::open(&config, campaign_id).map(|_| ()),
            Err(RustPersistenceRuntimeErrorV1::CampaignConflict)
        );

        let (retry_session, _) = runtime_fixture();
        let candidate = retry_session
            .prepare_advance(&actions)
            .expect("retry candidate");
        let prepared = prepare_committed_tick_v1(candidate.report()).expect("retry envelope input");
        let envelope = prepared.into_envelope(campaign_id).expect("retry envelope");
        assert_eq!(
            marker_matches_envelope_v1(
                &mut config.connect(NoTls).expect("retry connection"),
                candidate.report(),
                &envelope,
            ),
            Err(RustPersistenceRuntimeErrorV1::CampaignConflict)
        );
        database.cleanup();
    }

    #[test]
    #[ignore = "requires the task-owned disposable PER-20 PostgreSQL runtime"]
    fn live_restart_uses_the_latest_full_checkpoint_not_the_foundation_history() {
        let base = validated_base_config();
        let template = validated_template_name();
        let database = TestDatabase::create_from_template(&base, &template, "runtimelatest");
        let config = database.config(&base);
        let campaign_id =
            CampaignId::from_uuid(Uuid::from_u128(0x2810_0000_0000_0000_0000_0000_0000_00a4));
        let (session, bundle) = runtime_fixture();
        let mut runtime = DurableReplayRuntimeV1::create(&config, campaign_id, session, bundle)
            .expect("runtime constructs after activation");
        for resolve_tick in 1..=3 {
            let actions = OrderedPracticeActionBatchV1::empty(
                runtime.foundation().replay_session_identity().clone(),
                resolve_tick,
            )
            .expect("action batch");
            runtime
                .advance_and_commit(&mut CollectingSink::default(), &actions)
                .expect("tick commits");
        }
        let next_actions = OrderedPracticeActionBatchV1::empty(
            runtime.foundation().replay_session_identity().clone(),
            4,
        )
        .expect("next action batch");
        let uninterrupted_hash = runtime
            .session
            .prepare_advance(&next_actions)
            .expect("uninterrupted candidate")
            .report()
            .tick_content_hash();
        config
            .connect(NoTls)
            .expect("historical mutation connection")
            .execute(
                "DELETE FROM babylon_state.tick_action_batch_v1 \
                 WHERE campaign_id = $1::uuid AND resolve_tick = 1",
                &[campaign_id.as_uuid()],
            )
            .expect("old action row deletes");

        let reopened = DurableReplayRuntimeV1::open(&config, campaign_id)
            .expect("latest full checkpoint is a sufficient restart root");
        assert_eq!(
            reopened
                .last_committed_tick()
                .map(CommittedResolveTickV1::get),
            Some(3)
        );
        let restored_hash = reopened
            .session
            .prepare_advance(&next_actions)
            .expect("restored candidate")
            .report()
            .tick_content_hash();
        assert_eq!(restored_hash, uninterrupted_hash);
        database.cleanup();
    }

    fn runtime_fixture() -> (
        ReplayTickSession<HypergraphStore>,
        FoundationContentBundleV1,
    ) {
        let (_, rules) = split_content(RULE).expect("live rule parses");
        let forms = rules.into_iter().map(|(_, form)| form).collect::<Vec<_>>();
        let content = ContentDigest {
            defines_hash: sha256_of(DEFINES),
            rules_hash: rules_hash_of(&forms).expect("live rule hashes"),
        };
        let foundation = michigan_dynamic_hex_foundation_v1().expect("foundation decodes");
        let mut reference_manifest = REFERENCE_BUNDLE_DOMAIN.to_vec();
        reference_manifest.extend_from_slice(&foundation.base_reference_cohort_digest());
        reference_manifest.extend_from_slice(&foundation.r8_section_digest());
        assert_eq!(
            sha256_of(&reference_manifest),
            foundation.reference_bundle_digest()
        );
        let reference = RefDigestV1::from_bytes(foundation.reference_bundle_digest());
        let session = ReplayTickSession::new(
            SCENARIO,
            None,
            RULE,
            HypergraphStore::new(),
            ReplaySessionIdV1::try_from("per281/runtime-live").expect("session id"),
            ReplaySeed::new(281),
            content,
            reference,
            MaterialStateV1::try_new(foundation).expect("material state"),
        )
        .expect("tick-zero session prepares");
        let bundle =
            FoundationContentBundleV1::try_new(SCENARIO, None, RULE, DEFINES, &reference_manifest)
                .expect("content bundle");
        (session, bundle)
    }

    fn validated_base_config() -> Config {
        assert_eq!(std::env::var(ACK_ENV).as_deref(), Ok(ACK));
        let canary = std::env::var(CANARY_ENV).expect("runner supplies the disposable canary");
        assert_eq!(canary.len(), 32);
        let dsn = std::env::var(DSN_ENV).expect("runner supplies the disposable DSN");
        let config = Config::from_str(&dsn).expect("runner DSN parses");
        validate_legacy_connection_target(&config).expect("loopback target");
        assert_eq!(config.get_user(), Some("test"));
        assert_eq!(config.get_dbname(), Some("postgres"));
        let actual: Option<String> = config
            .connect(NoTls)
            .expect("canary connection")
            .query_one(
                "SELECT pg_catalog.current_setting('babylon.per20_disposable', true)",
                &[],
            )
            .expect("canary query")
            .try_get(0)
            .expect("canary decode");
        assert_eq!(actual.as_deref(), Some(canary.as_str()));
        config
    }

    fn validated_template_name() -> String {
        let template = std::env::var(TEMPLATE_DB_ENV)
            .expect("runner supplies the validated Rust-active template database");
        let suffix = template
            .strip_prefix("per281_runtime_template_")
            .expect("runtime template uses the task-owned prefix");
        assert_eq!(suffix.len(), 12);
        assert!(suffix
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte)));
        assert!(template
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'_'));
        template
    }

    fn marker_row_count(config: &Config, campaign_id: CampaignId) -> i64 {
        config
            .connect(NoTls)
            .expect("marker connection")
            .query_one(
                "SELECT pg_catalog.count(*) FROM babylon_state.tick_commit \
                 WHERE campaign_id = $1::uuid",
                &[campaign_id.as_uuid()],
            )
            .expect("marker count")
            .try_get(0)
            .expect("marker count decodes")
    }

    fn committed_payload_row_count(config: &Config, campaign_id: CampaignId) -> i64 {
        config
            .connect(NoTls)
            .expect("payload connection")
            .query_one(
                "SELECT \
                   (SELECT pg_catalog.count(*) FROM babylon_state.tick_action_batch_v1 WHERE campaign_id = $1::uuid) + \
                   (SELECT pg_catalog.count(*) FROM babylon_state.graph_node_v1 WHERE campaign_id = $1::uuid) + \
                   (SELECT pg_catalog.count(*) FROM babylon_state.graph_node_f64_v1 WHERE campaign_id = $1::uuid) + \
                   (SELECT pg_catalog.count(*) FROM babylon_state.graph_edge_v1 WHERE campaign_id = $1::uuid) + \
                   (SELECT pg_catalog.count(*) FROM babylon_state.graph_hyperedge_v1 WHERE campaign_id = $1::uuid) + \
                   (SELECT pg_catalog.count(*) FROM babylon_state.world_register_v1 WHERE campaign_id = $1::uuid) + \
                   (SELECT pg_catalog.count(*) FROM babylon_state.territory_state_v1 WHERE campaign_id = $1::uuid) + \
                   (SELECT pg_catalog.count(*) FROM babylon_state.hex_state_delta_v1 WHERE campaign_id = $1::uuid) + \
                   (SELECT pg_catalog.count(*) FROM babylon_state.organization_state_v1 WHERE campaign_id = $1::uuid) + \
                   (SELECT pg_catalog.count(*) FROM babylon_state.tick_event_v1 WHERE campaign_id = $1::uuid) + \
                   (SELECT pg_catalog.count(*) FROM babylon_state.checkpoint_manifest WHERE campaign_id = $1::uuid) + \
                   (SELECT pg_catalog.count(*) FROM babylon_state.checkpoint_section_v1 WHERE campaign_id = $1::uuid) + \
                   (SELECT pg_catalog.count(*) FROM babylon_state.archive_dirty_receipt_v1 WHERE campaign_id = $1::uuid)",
                &[campaign_id.as_uuid()],
            )
            .expect("payload count")
            .try_get(0)
            .expect("payload count decodes")
    }

    struct TestDatabase {
        name: String,
        admin: Config,
        active: bool,
    }

    impl TestDatabase {
        fn create(base: &Config, label: &str) -> Self {
            assert!(label.bytes().all(|byte| byte.is_ascii_lowercase()));
            let name = format!("per281_runtime_{label}_{}", std::process::id());
            let mut admin = base.clone();
            admin.dbname("postgres");
            let sql = format!("CREATE DATABASE \"{name}\" OWNER test TEMPLATE template1");
            admin
                .connect(NoTls)
                .expect("admin connection")
                .batch_execute(&sql)
                .expect("scratch database creation");
            Self {
                name,
                admin,
                active: true,
            }
        }

        fn config(&self, base: &Config) -> Config {
            let mut config = base.clone();
            config.dbname(&self.name);
            config
        }

        fn create_from_template(base: &Config, template: &str, label: &str) -> Self {
            assert!(label.bytes().all(|byte| byte.is_ascii_lowercase()));
            assert!(template
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_'));
            let name = format!("per281_runtime_{label}_{}", std::process::id());
            let mut admin = base.clone();
            admin.dbname("postgres");
            let sql = format!("CREATE DATABASE \"{name}\" OWNER test TEMPLATE \"{template}\"");
            admin
                .connect(NoTls)
                .expect("admin connection")
                .batch_execute(&sql)
                .expect("runtime clone creation");
            let database = Self {
                name,
                admin,
                active: true,
            };
            let observation = database
                .config(base)
                .connect(NoTls)
                .expect("runtime clone connection")
                .query_one(
                    "SELECT \
                       (SELECT pg_catalog.string_agg(ordinal::pg_catalog.text || ':' || \
                                state_tag::pg_catalog.text || ':' || schema_epoch::pg_catalog.text, \
                                ',' ORDER BY ordinal) \
                        FROM babylon_meta.persistence_authority_ledger), \
                       (SELECT pg_catalog.count(*) FROM babylon_meta.campaign)",
                    &[],
                )
                .expect("runtime clone observation");
            assert_eq!(
                observation
                    .try_get::<_, String>(0)
                    .expect("authority ledger decodes"),
                "1:1:8,2:2:9"
            );
            assert_eq!(
                observation
                    .try_get::<_, i64>(1)
                    .expect("campaign count decodes"),
                0
            );
            database
        }

        fn cleanup(mut self) {
            self.try_drop_database()
                .expect("runtime test database cleanup");
            self.active = false;
        }

        fn try_drop_database(&self) -> Result<(), ()> {
            let sql = format!("DROP DATABASE IF EXISTS \"{}\" WITH (FORCE)", self.name);
            self.admin
                .connect(NoTls)
                .map_err(|_| ())?
                .batch_execute(&sql)
                .map_err(|_| ())
        }
    }

    impl Drop for TestDatabase {
        fn drop(&mut self) {
            if !self.active {
                return;
            }
            if std::thread::panicking() {
                let _cleanup = self.try_drop_database();
                return;
            }
            self.try_drop_database()
                .expect("runtime test database cleanup");
            self.active = false;
        }
    }
}

#[cfg(test)]
mod tests {
    use babylon_bsl::rule_pipeline::split_content;
    use babylon_bsl::rules_hash_of;
    use babylon_bsl::structural_verbs::CollectingSink;
    use babylon_graph::hypergraph_store::HypergraphStore;
    use babylon_kernel::replay::{ReplaySeed, ReplaySessionIdV1};
    use babylon_kernel::tick_content_hash::RefDigestV1;
    use babylon_kernel::{sha256_of, ContentDigest};
    use babylon_practice_contract::ordered_action_v1::OrderedPracticeActionBatchV1;
    use babylon_tick::material_state::MaterialStateV1;
    use babylon_tick::replay_session::{ReplayCommitDispositionV1, ReplayTickSession};

    use crate::michigan_dynamic_hex_foundation_v1;

    use super::{
        prepare_committed_tick_v1, CampaignFoundationV1, CampaignId, CommittedResolveTickV1,
        CommittedTickReceiptV1, DurableReplayRuntimeV1, FoundationContentBundleV1,
        PersistenceAuthorityLedgerRowV1, RustPersistenceRuntimeErrorV1,
    };

    const SCENARIO: &str = r"
(scenario demo/runtime-prepare
  (defvocabulary NodeType (SOCIAL_CLASS))
  (deffield social-class/draw coefficient extensive)
  (node class-a NodeType/SOCIAL_CLASS (social-class/draw 0.0c)))
";
    const RULE: &str = r#"
(rule production/runtime-prepare
  :role mechanic
  :evidence derived
  :material-basis "prepared persistence input law"
  :fuel 32
  (bindings (binding draw :field social-class/draw))
  (when #t)
  (effects
    (update-node self social-class/draw (set 0.25c))
    (emit EventType/RUNTIME_PREPARED (subject self))))
"#;

    fn committed_observation_fixture() -> (
        DurableReplayRuntimeV1<HypergraphStore>,
        CommittedTickReceiptV1,
    ) {
        const DEFINES: &[u8] = &[0x53];
        const REFERENCE_BUNDLE_DOMAIN: &[u8] = b"babylon.h3.reference-bundle-composite.v1\0";
        let (_, rules) = split_content(RULE).expect("rule parses");
        let forms = rules.into_iter().map(|(_, form)| form).collect::<Vec<_>>();
        let content = ContentDigest {
            defines_hash: sha256_of(DEFINES),
            rules_hash: rules_hash_of(&forms).expect("rule hashes"),
        };
        let session_id =
            ReplaySessionIdV1::try_from("per304/runtime-observation-api").expect("session id");
        let material_foundation = michigan_dynamic_hex_foundation_v1().expect("foundation decodes");
        let mut reference_manifest = REFERENCE_BUNDLE_DOMAIN.to_vec();
        reference_manifest.extend_from_slice(&material_foundation.base_reference_cohort_digest());
        reference_manifest.extend_from_slice(&material_foundation.r8_section_digest());
        assert_eq!(
            sha256_of(&reference_manifest),
            material_foundation.reference_bundle_digest()
        );
        let reference = RefDigestV1::from_bytes(material_foundation.reference_bundle_digest());
        let mut session = ReplayTickSession::new(
            SCENARIO,
            None,
            RULE,
            HypergraphStore::new(),
            session_id.clone(),
            ReplaySeed::new(304),
            content,
            reference,
            MaterialStateV1::try_new(material_foundation).expect("material state"),
        )
        .expect("session prepares");
        let bundle =
            FoundationContentBundleV1::try_new(SCENARIO, None, RULE, DEFINES, &reference_manifest)
                .expect("content bundle");
        let foundation = CampaignFoundationV1::capture(&session, bundle).expect("foundation");
        let actions = OrderedPracticeActionBatchV1::empty(session_id, 1).expect("actions");
        let report = session
            .advance(&mut CollectingSink::default(), &actions)
            .expect("tick succeeds");
        let receipt = CommittedTickReceiptV1::from_acknowledged(
            CommittedResolveTickV1::try_from(1).expect("positive tick"),
            ReplayCommitDispositionV1::Committed,
            report,
        );
        let prepared = PersistenceAuthorityLedgerRowV1::prepared().expect("prepared row");
        let activation_row =
            PersistenceAuthorityLedgerRowV1::rust_active(&prepared).expect("active row");
        let runtime = DurableReplayRuntimeV1 {
            config: postgres::Config::new(),
            campaign_id: CampaignId::from_uuid(uuid::Uuid::from_u128(0x304)),
            session,
            foundation,
            activation_row,
            last_committed_tick: Some(receipt.resolve_tick()),
        };
        (runtime, receipt)
    }

    #[test]
    fn prepared_tick_uses_one_identified_report_without_engine_authority() {
        let (_, rules) = split_content(RULE).expect("rule parses");
        let forms = rules.into_iter().map(|(_, form)| form).collect::<Vec<_>>();
        let content = ContentDigest {
            defines_hash: [0x51; 32],
            rules_hash: rules_hash_of(&forms).expect("rule hashes"),
        };
        let session_id = ReplaySessionIdV1::try_from("per281/runtime-prepare").expect("session id");
        let foundation = michigan_dynamic_hex_foundation_v1().expect("foundation decodes");
        let mut session = ReplayTickSession::new(
            SCENARIO,
            None,
            RULE,
            HypergraphStore::new(),
            session_id.clone(),
            ReplaySeed::new(53),
            content,
            RefDigestV1::from_bytes(foundation.reference_bundle_digest()),
            MaterialStateV1::try_new(foundation).expect("material state"),
        )
        .expect("session prepares");
        let actions = OrderedPracticeActionBatchV1::empty(session_id, 1).expect("actions");
        let report = session
            .advance(&mut CollectingSink::default(), &actions)
            .expect("tick succeeds");

        let prepared = prepare_committed_tick_v1(&report).expect("report composes once");
        assert_eq!(prepared.resolve_tick().get(), 1);
        assert_eq!(prepared.tick_content_hash(), report.tick_content_hash());
        assert_eq!(prepared.graph_row_count(), 2);
        assert_eq!(prepared.event_row_count(), 1);

        let source = include_str!("runtime.rs");
        let production = source
            .split_once("#[cfg(test)]\nmod live_tests")
            .expect("live tests follow the complete production runtime")
            .0;
        assert_eq!(
            production
                .matches("compose_graph_event_semantic_batches_v1(report)")
                .count(),
            1
        );
        let prohibited_prepare = ["prepare", "_rules("].concat();
        let prohibited_run = ["run_prepared", "_replay_tick("].concat();
        assert!(!production.contains(&prohibited_prepare));
        assert!(!production.contains(&prohibited_run));
    }

    #[test]
    fn bounded_receipt_preserves_only_report_aggregates_and_hashes() {
        let (_, rules) = split_content(RULE).expect("rule parses");
        let forms = rules.into_iter().map(|(_, form)| form).collect::<Vec<_>>();
        let content = ContentDigest {
            defines_hash: [0x52; 32],
            rules_hash: rules_hash_of(&forms).expect("rule hashes"),
        };
        let session_id =
            ReplaySessionIdV1::try_from("per304/runtime-observation").expect("session id");
        let foundation = michigan_dynamic_hex_foundation_v1().expect("foundation decodes");
        let mut session = ReplayTickSession::new(
            SCENARIO,
            None,
            RULE,
            HypergraphStore::new(),
            session_id.clone(),
            ReplaySeed::new(304),
            content,
            RefDigestV1::from_bytes(foundation.reference_bundle_digest()),
            MaterialStateV1::try_new(foundation).expect("material state"),
        )
        .expect("session prepares");
        let actions = OrderedPracticeActionBatchV1::empty(session_id, 1).expect("actions");
        let report = session
            .advance(&mut CollectingSink::default(), &actions)
            .expect("tick succeeds");
        let expected_graph_before = report.report().before;
        let expected_graph_after = report.report().after;
        let expected_prior_stable_graph_digest = report.prior_stable_graph_digest().into_bytes();
        let expected_stable_graph_digest = report.result_stable_graph_digest().into_bytes();
        let expected_world_before = report.report().world_before;
        let expected_world_after = report.report().world_after;
        let expected_event_digest = report.successful_event_batch().source_digest();
        let expected_material_digest = report.material_state_rows().source_digest();
        let expected_tick_content_hash = report.tick_content_hash();

        let receipt = CommittedTickReceiptV1::from_acknowledged(
            CommittedResolveTickV1::try_from(1).expect("positive tick"),
            ReplayCommitDispositionV1::ReconciledAfterAmbiguousCommit,
            report,
        );

        assert_eq!(receipt.resolve_tick().get(), 1);
        assert_eq!(
            receipt.commit_disposition(),
            ReplayCommitDispositionV1::ReconciledAfterAmbiguousCommit
        );
        assert_eq!(receipt.graph_before(), expected_graph_before);
        assert_eq!(receipt.graph_after(), expected_graph_after);
        assert_eq!(
            receipt.prior_stable_graph_digest(),
            expected_prior_stable_graph_digest
        );
        assert_eq!(
            receipt.result_stable_graph_digest(),
            expected_stable_graph_digest
        );
        assert_eq!(receipt.world_before(), expected_world_before);
        assert_eq!(receipt.world_after(), expected_world_after);
        assert_eq!(receipt.considered(), 1);
        assert_eq!(receipt.fired(), 1);
        assert_eq!(
            receipt.per_rule_considered(),
            &[("production/runtime-prepare".to_owned(), 1)]
        );
        assert_eq!(
            receipt.per_rule_fired(),
            &[("production/runtime-prepare".to_owned(), 1)]
        );
        assert_eq!(receipt.event_count(), 1);
        assert_eq!(receipt.event_digest(), expected_event_digest);
        assert_eq!(receipt.audit_receipt_count(), 2);
        assert!(receipt.material_row_count() > 0);
        assert_eq!(receipt.material_row_digest(), expected_material_digest);
        assert_eq!(receipt.tick_content_hash(), expected_tick_content_hash);
    }

    #[test]
    fn committed_observation_is_bound_to_the_current_receipt_tick_and_digest() {
        let (mut runtime, mut receipt) = committed_observation_fixture();

        let current = runtime
            .observe_current_stable_graph_state_v1()
            .expect("current stable graph is observable without mutation");
        let observed = runtime
            .observe_committed_graph_state_v1(&receipt)
            .expect("current acknowledged graph is observable");
        assert_eq!(current, observed);
        assert_eq!(
            observed.digest().into_bytes(),
            receipt.result_stable_graph_digest()
        );

        runtime.last_committed_tick =
            Some(CommittedResolveTickV1::try_from(2).expect("positive committed tail"));
        assert_eq!(
            runtime.observe_committed_graph_state_v1(&receipt),
            Err(
                RustPersistenceRuntimeErrorV1::ObservationNotCurrentCommittedTail {
                    receipt_tick: 1,
                    current_tail: Some(2),
                }
            )
        );

        runtime.last_committed_tick = Some(receipt.resolve_tick());
        receipt.result_stable_graph_digest = [0xff; 32];
        assert_eq!(
            runtime.observe_committed_graph_state_v1(&receipt),
            Err(RustPersistenceRuntimeErrorV1::ObservationGraphDigestMismatch)
        );
    }
}
