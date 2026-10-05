//! Explicit V3 durable material campaign, marker-last and checkpoint-complete.

mod component_identity;
mod decode;
mod envelope;
mod observer_actions;
pub(crate) use component_identity::MaterialComponentIdentity;
pub use envelope::MAX_MATERIAL_FOUNDATION_BYTES;

use crate::stored_tick::{StoredEvent, StoredTickReadSource, StoredTickRelation};

use crate::CommittedTickReceipt;
use crate::{
    checkpoint::{CommittedFullCheckpoint, CommittedResolveTick},
    committed_tick_envelope::CommittedTickRowFamilies,
    foundation::{CampaignFoundation, FoundationContentBundle},
    identity::CampaignId,
    material_envelope::{CommittedMaterialTickAttestation, CommittedMaterialTickEnvelope},
    runtime::{
        insert_campaign_foundation_rows, insert_typed_tick_pre_marker_rows, prepare_committed_tick,
        reconstruct_graph_foundation_session, verify_runtime_schema_client,
        RustPersistenceRuntimeError,
    },
    semantic_batches::{
        compose_graph_rows_with_encoder, compose_material_state_rows, StableGraphRowRef,
    },
    stored_tick,
};
use crate::{material_storage, state_storage::TypedLookup};
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::stable_state::StableGraphState;
use babylon_kernel::content_digest::sha256_of;
use babylon_material_circuit::MaterialCircuitState;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::choice_receipt::ChoiceReceipt;
use babylon_tick::{
    material_replay::{
        IdentifiedMaterialTick, MaterialCommitError, MaterialReplayError, MaterialReplaySession,
    },
    material_world::{MaterialWorldError, MaterialWorldRegister},
    replay_session::{ReplayCommitDisposition, ReplayTickSession},
};
use postgres::{fallible_iterator::FallibleIterator as _, Config, GenericClient, NoTls};
use std::time::{Duration, Instant};

/// Actual operational stage starts; these observations never enter canonical output.
#[derive(
    Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, serde::Serialize, serde::Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub enum MaterialAdvanceStage {
    PreparingCommitments,
    ResolvingEconomy,
    PreparingStorage,
    SavingPeriod,
}

const FOUNDATION_DOMAIN: &[u8] = b"babylon.material-campaign-foundation.v3\0";

const WRITER_CONNECT_TIMEOUT: Duration = Duration::from_secs(5);
const WRITER_TCP_USER_TIMEOUT: Duration = Duration::from_secs(30);
// Tick computation is detached before these transactions begin. Individual
// writer statements get a larger budget than the observer's read queries.
// Match the catalog reader's JIT setting: every fresh writer connection checks
// the same census, whose compilation cost is not amortized across ticks.
const WRITER_STARTUP_OPTIONS: &str = "-c search_path=pg_catalog -c quote_all_identifiers=off \
    -c statement_timeout=120000ms -c lock_timeout=5000ms \
    -c idle_in_transaction_session_timeout=120000ms -c jit=off";

pub(crate) fn bounded_material_writer_config(
    config: &Config,
) -> Result<Config, MaterialRuntimeError> {
    // Validate the caller before introducing trusted startup settings. Never
    // accept caller options merely because they resemble our timeout values.
    crate::postgres_catalog::validate_connection_target(config).map_err(|error| {
        RustPersistenceRuntimeError::CurrentSchema(crate::CurrentSchemaError::ConnectionTarget(
            error,
        ))
    })?;
    let mut bounded = config.clone();
    bounded
        .connect_timeout(WRITER_CONNECT_TIMEOUT)
        .tcp_user_timeout(WRITER_TCP_USER_TIMEOUT)
        .options(WRITER_STARTUP_OPTIONS);
    Ok(bounded)
}

/// Pinned authored identity; quantities remain in the complete material register.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MaterialFoundationSpec {
    pub preset_id: String,
    pub duration: babylon_kernel::clock::CampaignDuration,
    pub content_digest: [u8; 32],
}
/// Fresh tick-zero owners and their exact combined foundation.
pub struct MaterialRuntimeFoundation {
    graph: ReplayTickSession<HypergraphStore>,
    graph_foundation: CampaignFoundation,
    register: MaterialWorldRegister,
    spec: MaterialFoundationSpec,
    digest: [u8; 32],
    labor: babylon_tick::material_staffing::StaffingComposition,
}
/// Precise successor refusal classes. No fallback to a graph-only campaign.
#[derive(Debug)]
pub enum MaterialRuntimeError {
    Graph(RustPersistenceRuntimeError),
    Replay(MaterialReplayError),
    Register(MaterialWorldError),
    Storage(material_storage::Error),
    Database(postgres::Error),
    DatabaseLockRefused(postgres::Error),
    DatabaseStatementCanceled(postgres::Error),
    SchemaDrift,
    FoundationMismatch,
    #[cfg(test)]
    InjectedCommitLoss,
    LegacyCampaign,
    MissingCampaign,
    AlreadyExists,
    TailConflict,
    InvalidCheckpoint,
    Bounds,
    OrganizerStorage,
    OrganizerObserverProjectionRefused,
    MichiganEconomy(crate::michigan_economy::MichiganEconomyError),
    MichiganMaterial(crate::michigan_material::MichiganMaterialError),
}
impl std::fmt::Display for MaterialRuntimeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "material runtime refused: {self:?}")
    }
}
impl std::error::Error for MaterialRuntimeError {}
impl From<RustPersistenceRuntimeError> for MaterialRuntimeError {
    fn from(error: RustPersistenceRuntimeError) -> Self {
        Self::Graph(error)
    }
}
impl From<MaterialReplayError> for MaterialRuntimeError {
    fn from(error: MaterialReplayError) -> Self {
        Self::Replay(error)
    }
}
impl From<MaterialWorldError> for MaterialRuntimeError {
    fn from(error: MaterialWorldError) -> Self {
        Self::Register(error)
    }
}
impl From<crate::semantic_batches::SemanticBatchError> for MaterialRuntimeError {
    fn from(error: crate::semantic_batches::SemanticBatchError) -> Self {
        Self::Graph(error.into())
    }
}
impl From<material_storage::Error> for MaterialRuntimeError {
    fn from(value: material_storage::Error) -> Self {
        Self::Storage(value)
    }
}
impl From<postgres::Error> for MaterialRuntimeError {
    fn from(error: postgres::Error) -> Self {
        if error.code() == Some(&postgres::error::SqlState::LOCK_NOT_AVAILABLE) {
            Self::DatabaseLockRefused(error)
        } else if error.code() == Some(&postgres::error::SqlState::QUERY_CANCELED) {
            Self::DatabaseStatementCanceled(error)
        } else {
            Self::Database(error)
        }
    }
}

/// Exact SQL representation; null means continuous only with its explicit tag.
pub(crate) fn duration_columns(
    duration: babylon_kernel::clock::CampaignDuration,
) -> Result<(&'static str, Option<i64>), MaterialRuntimeError> {
    use babylon_kernel::clock::CampaignDuration;
    duration
        .validate()
        .map_err(|_| MaterialRuntimeError::Bounds)?;
    match duration {
        CampaignDuration::Continuous => Ok(("continuous", None)),
        CampaignDuration::Finite { final_period } => Ok((
            "finite",
            Some(i64::try_from(final_period).map_err(|_| MaterialRuntimeError::Bounds)?),
        )),
    }
}
pub(crate) fn read_duration(
    row: &postgres::Row,
) -> Result<babylon_kernel::clock::CampaignDuration, MaterialRuntimeError> {
    use babylon_kernel::clock::CampaignDuration;
    let kind: String = row.try_get("duration_kind")?;
    let final_period: Option<i64> = row.try_get("final_period")?;
    let value = match (kind.as_str(), final_period) {
        ("continuous", None) => CampaignDuration::Continuous,
        ("finite", Some(period)) => CampaignDuration::Finite {
            final_period: u64::try_from(period)
                .map_err(|_| MaterialRuntimeError::FoundationMismatch)?,
        },
        _ => return Err(MaterialRuntimeError::FoundationMismatch),
    };
    value
        .validate()
        .map_err(|_| MaterialRuntimeError::FoundationMismatch)?;
    Ok(value)
}

fn validate_foundation_spec(spec: &MaterialFoundationSpec) -> Result<(), MaterialRuntimeError> {
    if spec.preset_id.is_empty()
        || spec.preset_id.len() > 128
        || !spec
            .preset_id
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
        || spec.duration.validate().is_err()
    {
        return Err(MaterialRuntimeError::Bounds);
    }
    Ok(())
}

impl MaterialRuntimeFoundation {
    /// Capture a foundation whose content explicitly uses the current tagged source encoding.
    /// # Errors
    /// Refuses invalid graph, material register, spec or aggregate bounds.
    pub fn capture(
        graph: ReplayTickSession<HypergraphStore>,
        bundle: FoundationContentBundle,
        state: MaterialCircuitState,
        spec: MaterialFoundationSpec,
    ) -> Result<Self, MaterialRuntimeError> {
        validate_foundation_spec(&spec)?;
        let graph_foundation = CampaignFoundation::capture(&graph, bundle)?;
        let register = MaterialWorldRegister::try_new(0, state)?;
        Self::from_parts(graph, graph_foundation, register, spec)
    }

    /// Capture an explicitly composed current register, including organizer authority.
    /// # Errors
    /// Refuses a non-foundation register or any invalid captured source identity.
    pub(crate) fn capture_register(
        graph: ReplayTickSession<HypergraphStore>,
        bundle: FoundationContentBundle,
        register: MaterialWorldRegister,
        spec: MaterialFoundationSpec,
    ) -> Result<Self, MaterialRuntimeError> {
        validate_foundation_spec(&spec)?;
        let graph_foundation = CampaignFoundation::capture(&graph, bundle)?;
        Self::from_parts(graph, graph_foundation, register, spec)
    }

    // Both initial capture and stored reconstruction use this exact encoder.
    // Callers first prove that graph_foundation describes the prepared graph.
    fn from_parts(
        graph: ReplayTickSession<HypergraphStore>,
        graph_foundation: CampaignFoundation,
        register: MaterialWorldRegister,
        spec: MaterialFoundationSpec,
    ) -> Result<Self, MaterialRuntimeError> {
        validate_foundation_spec(&spec)?;
        if graph.completed_tick() != 0 || register.completed_tick() != 0 {
            return Err(MaterialRuntimeError::FoundationMismatch);
        }
        graph
            .validate_material_cycle()
            .map_err(|error| MaterialRuntimeError::Replay(MaterialReplayError::Graph(error)))?;
        let labor = if let Some(catalog) = graph_foundation.content_bundle().economic_catalog() {
            catalog
                .validate_foundation(&graph_foundation, &register, &spec)
                .map_err(|error| {
                    MaterialRuntimeError::Graph(RustPersistenceRuntimeError::EconomicCatalog(error))
                })?
        } else if spec.preset_id
            == crate::simulation_experiment::ExperimentProfile::HistoricalFreight.foundation_id()
        {
            crate::simulation_experiment::validate_freight_authority(
                &graph_foundation,
                &register,
                &spec,
            )
            .map_err(|_| MaterialRuntimeError::FoundationMismatch)?
        } else {
            return Err(MaterialRuntimeError::FoundationMismatch);
        };
        let digest = envelope::CanonicalMaterialFoundation::new(
            spec.preset_id.as_bytes(),
            spec.duration,
            &spec.content_digest,
            graph_foundation.canonical_bytes(),
            register.canonical_bytes(),
        )?
        .digest();
        Ok(Self {
            graph,
            graph_foundation,
            register,
            spec,
            digest,
            labor,
        })
    }
    /// Reconstruct from the exact captured components, through the same path as
    /// a durable open, without reading current authored experiment inputs.
    /// # Errors
    /// Refuses any component, source, register or aggregate identity mismatch.
    pub fn reconstruct_captured(&self) -> Result<Self, MaterialRuntimeError> {
        let original = &self.graph_foundation;
        let bundle = original.content_bundle();
        let text = |bytes: &[u8]| {
            std::str::from_utf8(bytes)
                .map(str::to_owned)
                .map_err(|_| MaterialRuntimeError::FoundationMismatch)
        };
        let session = text(original.replay_session_identity().as_bytes())?;
        let graph = CampaignFoundation::from_persisted(
            original.stable_graph_bytes().to_vec(),
            original.world_register_bytes().to_vec(),
            original.resolver_manifest_bytes().to_vec(),
            original.prepared_environment_bytes().to_vec(),
            &session,
            i64::from_be_bytes(original.rng_seed().to_be_bytes()),
            original.content_digest().defines_hash,
            original.content_digest().rules_hash,
            *original.reference_digest().as_bytes(),
            bundle.canonical_bytes(),
            sha256_of(original.canonical_bytes()),
        )?;
        reconstruct_material_foundation(
            StoredMaterialFoundation {
                spec: self.spec.clone(),
                initial_register_bytes: self.register.canonical_bytes().to_vec(),
                foundation_digest: self.digest,
                graph_foundation_digest: sha256_of(original.canonical_bytes()),
            },
            graph,
            self.digest,
        )
    }
    #[must_use]
    pub const fn digest(&self) -> [u8; 32] {
        self.digest
    }
    fn canonical_encoding(
        &self,
    ) -> Result<envelope::CanonicalMaterialFoundation<'_>, MaterialRuntimeError> {
        envelope::CanonicalMaterialFoundation::new(
            self.spec.preset_id.as_bytes(),
            self.spec.duration,
            &self.spec.content_digest,
            self.graph_foundation.canonical_bytes(),
            self.register.canonical_bytes(),
        )
    }
    /// Return the complete canonical length without allocating an export.
    /// # Errors
    /// Refuses invalid canonical component bounds or duration.
    pub fn canonical_len(&self) -> Result<usize, MaterialRuntimeError> {
        Ok(self.canonical_encoding()?.len())
    }
    /// Allocate the complete binary export only for its caller's lifetime.
    /// # Errors
    /// Refuses invalid canonical framing or an allocation failure.
    pub fn export_canonical_bytes(&self) -> Result<Vec<u8>, MaterialRuntimeError> {
        self.canonical_encoding()?.export()
    }
    #[must_use]
    pub const fn initial_register(&self) -> &MaterialWorldRegister {
        &self.register
    }
    #[must_use]
    pub const fn spec(&self) -> &MaterialFoundationSpec {
        &self.spec
    }
    #[must_use]
    pub const fn graph_foundation(&self) -> &CampaignFoundation {
        &self.graph_foundation
    }
    pub(crate) fn opening_graph_state(
        &self,
    ) -> Result<babylon_graph::stable_state::StableGraphState, MaterialRuntimeError> {
        self.graph
            .stable_graph_state()
            .map_err(|_| MaterialRuntimeError::FoundationMismatch)
    }
    /// Exact labor authority decoded from the admitted stored definitions.
    #[must_use]
    pub const fn labor(&self) -> &babylon_tick::material_staffing::StaffingComposition {
        &self.labor
    }
    /// Consume the exact foundation into its admitted graph and labor authority.
    /// # Errors
    /// Refuses invalid initial clocks or material replay bounds.
    pub fn into_session(
        self,
    ) -> Result<MaterialReplaySession<HypergraphStore>, MaterialRuntimeError> {
        Ok(MaterialReplaySession::new(
            self.graph,
            self.register,
            self.digest,
            self.spec.duration,
            self.labor,
        )?)
    }
}

/// Canonical writer for explicitly founded circuit campaigns.
pub struct DurableMaterialRuntime {
    config: Config,
    campaign: CampaignId,
    session: MaterialReplaySession<HypergraphStore>,
    lookup: material_storage::OpeningRegister,
    lookup_chain: [u8; 32],
    tail: Option<IdentifiedMaterialTick>,
    last_receipt: Option<crate::CommittedTickReceipt>,
    last_choice_receipts: Vec<babylon_tick::choice_receipt::ChoiceReceipt>,
}
impl DurableMaterialRuntime {
    /// Install both foundation components in one transaction, without an implicit tick.
    /// # Errors
    /// Refuses absent authority, existing graph-only campaigns, mismatched foundation or DB failure.
    pub fn create(
        config: &Config,
        campaign: CampaignId,
        foundation: MaterialRuntimeFoundation,
    ) -> Result<Self, MaterialRuntimeError> {
        Self::create_with_admission(config, campaign, foundation, false)
    }
    /// Lifecycle New requires absence under the same founding lock/transaction.
    pub(crate) fn create_new(
        config: &Config,
        campaign: CampaignId,
        foundation: MaterialRuntimeFoundation,
    ) -> Result<Self, MaterialRuntimeError> {
        Self::create_with_admission(config, campaign, foundation, true)
    }
    fn create_with_admission(
        config: &Config,
        campaign: CampaignId,
        foundation: MaterialRuntimeFoundation,
        require_absent: bool,
    ) -> Result<Self, MaterialRuntimeError> {
        if foundation
            .register
            .organizer_config()
            .is_some_and(|organizer| organizer.campaign_id != *campaign.canonical_bytes())
        {
            return Err(MaterialRuntimeError::FoundationMismatch);
        }
        let lookup = material_storage::OpeningRegister::from_opening(&foundation.register)
            .map_err(material_storage::Error::State)?;
        let initial_lookup_chain = material_storage::initial_lookup_chain(&lookup)?;
        let bounded = bounded_material_writer_config(config)?;
        let mut client = bounded.connect(NoTls)?;
        verify_runtime_schema_client(&mut client)?;
        let mut tx = client.transaction()?;
        tx.batch_execute(
            "SET LOCAL search_path TO pg_catalog; SET LOCAL synchronous_commit TO on",
        )?;
        tx.query_one(
            "SELECT pg_catalog.pg_advisory_xact_lock($1)",
            &[&crate::SCHEMA_ADVISORY_LOCK_KEY],
        )?;
        let existed=tx.query_opt("SELECT campaign_id FROM babylon_state.campaign WHERE campaign_id=$1::uuid FOR UPDATE",&[campaign.as_uuid()])?.is_some();
        if existed && require_absent {
            return Err(MaterialRuntimeError::AlreadyExists);
        }
        if existed {
            let stored = hydrate_material_foundation(&mut tx, campaign, foundation.digest())?;
            if !stored
                .canonical_encoding()?
                .matches_encoding(&foundation.canonical_encoding()?)
            {
                return Err(MaterialRuntimeError::FoundationMismatch);
            }
            if read_tail_tick(&mut tx, campaign)? != 0 {
                return Err(MaterialRuntimeError::TailConflict);
            }
        } else {
            insert_campaign_foundation_rows(&mut tx, campaign, &foundation.graph_foundation)?;
            let opening_graph = foundation.opening_graph_state()?;
            crate::graph_storage::seed(
                &mut tx,
                campaign,
                opening_graph.rows().nodes(),
                opening_graph.rows().node_f64(),
            )?;
            drop(opening_graph);
            let opening_rows = foundation
                .graph
                .current_material_state_rows()
                .map_err(|error| MaterialRuntimeError::Replay(MaterialReplayError::Graph(error)))?;
            crate::territory_storage::seed(&mut tx, campaign, opening_rows.territories().rows())?;
            drop(opening_rows);
            let (duration_kind, final_period) = duration_columns(foundation.spec.duration)?;
            tx.execute("INSERT INTO babylon_state.material_campaign_foundation_v3 (campaign_id,preset_id,duration_kind,final_period,content_sha256,initial_register_bytes,foundation_sha256) VALUES ($1::uuid,$2,$3,$4,$5,$6,$7)",&[campaign.as_uuid(),&foundation.spec.preset_id,&duration_kind,&final_period,&&foundation.spec.content_digest[..],&foundation.register.canonical_bytes(),&&foundation.digest[..]])?;
        }
        // Staffed rule ownership is fallible: refuse before any founding rows
        // become durable, so dropping this transaction also removes enrollment.
        crate::organizer_archive::insert_projection(&mut tx, campaign, &foundation.register)?;
        let session = foundation.into_session()?;
        tx.commit()?;
        Ok(Self {
            config: bounded,
            campaign,
            session,
            lookup,
            lookup_chain: initial_lookup_chain,
            tail: None,
            last_receipt: None,
            last_choice_receipts: Vec::new(),
        })
    }
    /// Reconstruct the stored foundation and hydrate the latest complete V3 checkpoint.
    /// The expected digest is supplied by the caller's content-admission policy;
    /// reopening never substitutes a newly constructed scenario or material state.
    /// # Errors
    /// Refuses old campaigns, gaps, altered component rows, identity mismatch or missing checkpoints.
    pub fn open(
        config: &Config,
        campaign: CampaignId,
        expected_foundation_digest: [u8; 32],
    ) -> Result<Self, MaterialRuntimeError> {
        Self::open_with_foundation_admission(config, campaign, |snapshot| {
            hydrate_material_foundation(snapshot, campaign, expected_foundation_digest)
        })
    }

    /// Admit one owned foundation and its checkpoint in the same Open snapshot.
    /// The admission policy must authenticate stored components in that snapshot;
    /// no cached foundation or independently read header enters this path.
    /// Supply raw caller configuration; this path adds its own trusted bounds.
    pub(crate) fn open_with_foundation_admission(
        config: &Config,
        campaign: CampaignId,
        admit: impl FnOnce(
            &mut postgres::Transaction<'_>,
        ) -> Result<MaterialRuntimeFoundation, MaterialRuntimeError>,
    ) -> Result<Self, MaterialRuntimeError> {
        let bounded = bounded_material_writer_config(config)?;
        let mut client = bounded.connect(NoTls)?;
        verify_runtime_schema_client(&mut client)?;
        let mut tx = client
            .build_transaction()
            .isolation_level(postgres::IsolationLevel::RepeatableRead)
            .read_only(true)
            .start()?;
        let foundation = admit(&mut tx)?;
        if foundation
            .register
            .organizer_config()
            .is_some_and(|organizer| organizer.campaign_id != *campaign.canonical_bytes())
        {
            return Err(MaterialRuntimeError::FoundationMismatch);
        }
        let tick = read_tail_tick(&mut tx, campaign)?;
        let lookup = material_storage::OpeningRegister::from_opening(&foundation.register)
            .map_err(material_storage::Error::State)?;
        let initial_lookup_chain = material_storage::initial_lookup_chain(&lookup)?;
        let stored = if tick == 0 {
            None
        } else {
            let scope = foundation
                .graph
                .stable_graph_state()
                .map_err(MaterialReplayError::Graph)?
                .scenario_scope()
                .to_owned();
            let components =
                MaterialComponentIdentity::from_foundation(&foundation.graph_foundation);
            Some(read_authenticated_material_tick(
                &mut tx,
                StoredTickReadSource::Runtime,
                campaign,
                tick,
                MaterialReadAuthority {
                    scope: &scope,
                    foundation_digest: foundation.digest(),
                    components: &components,
                    opening: &lookup,
                    lookup_chain: None,
                    witnesses: [None, None],
                },
            )?)
        };
        let mut session = foundation.into_session()?;
        let (tail, lookup_chain) = if let Some(stored) = stored {
            session.restore_full_checkpoint(
                &stored.graph,
                &stored.material,
                &stored.sections[1],
                stored.register.into_owned(),
            )?;
            if session.current_world_hash()? != stored.identity.result_world_hash() {
                return Err(MaterialRuntimeError::InvalidCheckpoint);
            }
            (Some(stored.identity), stored.lookup_chain)
        } else {
            (None, initial_lookup_chain)
        };
        tx.commit()?;
        Ok(Self {
            config: bounded,
            campaign,
            session,
            lookup,
            lookup_chain,
            tail,
            last_receipt: None,
            last_choice_receipts: Vec::new(),
        })
    }
    pub(crate) fn organizer_connection(&self) -> Result<postgres::Client, MaterialRuntimeError> {
        self.config
            .connect(NoTls)
            .map_err(MaterialRuntimeError::from)
    }
    #[must_use]
    pub const fn session(&self) -> &MaterialReplaySession<HypergraphStore> {
        &self.session
    }
    #[must_use]
    pub const fn campaign_id(&self) -> CampaignId {
        self.campaign
    }
    #[must_use]
    pub const fn tail(&self) -> Option<&IdentifiedMaterialTick> {
        self.tail.as_ref()
    }
    /// Process-local diagnostics for the last acknowledged tick.
    #[must_use]
    pub const fn diagnostic_receipt(&self) -> Option<&crate::CommittedTickReceipt> {
        self.last_receipt.as_ref()
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
    pub fn observe_committed_graph_state(
        &self,
        receipt: &CommittedTickReceipt,
    ) -> Result<StableGraphState, RustPersistenceRuntimeError> {
        if self.tail.as_ref().map(IdentifiedMaterialTick::resolve_tick)
            != Some(receipt.resolve_tick().get())
        {
            return Err(
                RustPersistenceRuntimeError::ObservationNotCurrentCommittedTail {
                    receipt_tick: receipt.resolve_tick().get(),
                    current_tail: self.tail.as_ref().map(IdentifiedMaterialTick::resolve_tick),
                },
            );
        }
        let observed = self.observe_current_stable_graph_state()?;
        if observed.digest().as_bytes() != &receipt.result_stable_graph_digest() {
            return Err(RustPersistenceRuntimeError::ObservationGraphDigestMismatch);
        }
        Ok(observed)
    }

    /// Borrow detailed choice evidence for the just-acknowledged process-local tick.
    ///
    /// This is an optional post-commit operational observation seam. It never
    /// participates in adjudication, hashing, persistence, retry, or restart.
    ///
    /// # Errors
    /// Refuses a receipt other than the current tail or detail not retained by
    /// this process (for example immediately after reopening a campaign).
    pub fn observe_committed_choice_receipts(
        &self,
        receipt: &CommittedTickReceipt,
    ) -> Result<&[ChoiceReceipt], RustPersistenceRuntimeError> {
        if self.tail.as_ref().map(IdentifiedMaterialTick::resolve_tick)
            != Some(receipt.resolve_tick().get())
        {
            return Err(
                RustPersistenceRuntimeError::ObservationNotCurrentCommittedTail {
                    receipt_tick: receipt.resolve_tick().get(),
                    current_tail: self.tail.as_ref().map(IdentifiedMaterialTick::resolve_tick),
                },
            );
        }
        if self.last_receipt.as_ref() != Some(receipt)
            || self.last_choice_receipts.len() != receipt.choice_receipt_count()
        {
            return Err(RustPersistenceRuntimeError::ObservationChoiceReceiptUnavailable);
        }
        Ok(&self.last_choice_receipts)
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
    pub fn observe_current_stable_graph_state(
        &self,
    ) -> Result<StableGraphState, RustPersistenceRuntimeError> {
        self.session
            .graph_session()
            .stable_graph_state()
            .map_err(|_| RustPersistenceRuntimeError::ReplayTick)
    }

    /// Prepare both owners, durably commit all eight families, then publish both.
    /// # Errors
    /// Refuses stale state, adjudication, row bounds or database failures without live publication.
    // Keep candidate preparation, marker-last ordering and ambiguous-commit
    // reconciliation visible together as one authoritative transaction.
    pub fn advance_and_commit(
        &mut self,
        sink: &mut CollectingSink,
        actions: &OrderedPracticeActionBatch,
    ) -> Result<IdentifiedMaterialTick, MaterialRuntimeError> {
        self.advance_and_commit_with_progress(sink, actions, &mut |_| {})
    }

    /// Observe genuine stage starts without changing detached preparation or durable publication.
    /// # Errors
    /// Returns the same admission, material and persistence refusals as `advance_and_commit`.
    #[allow(clippy::too_many_lines)]
    pub fn advance_and_commit_with_progress(
        &mut self,
        sink: &mut CollectingSink,
        actions: &OrderedPracticeActionBatch,
        progress: &mut dyn FnMut(MaterialAdvanceStage),
    ) -> Result<IdentifiedMaterialTick, MaterialRuntimeError> {
        let started = Instant::now();
        let next_period = self
            .session
            .completed_tick()
            .checked_add(1)
            .ok_or(MaterialRuntimeError::Bounds)?;
        progress(MaterialAdvanceStage::ResolvingEconomy);
        let pending = if self.has_organizer() {
            let mut client = self.organizer_connection()?;
            crate::organizer_runtime::pending(&mut client, self.campaign, next_period)?
        } else {
            None
        };
        let candidate = self
            .session
            .prepare_advance_with_organizer(actions, pending.as_ref())?;
        let adjudicated = Instant::now();
        progress(MaterialAdvanceStage::PreparingStorage);
        let identity = *candidate.identity();
        let mut diagnostic = crate::CommittedTickReceipt::from_material_candidate(&candidate)?;
        let choices = candidate.graph_report().report().choice_receipts.clone();
        let tick = CommittedResolveTick::try_from(identity.resolve_tick())
            .map_err(|_| MaterialRuntimeError::Bounds)?;
        let checkpoint =
            CommittedFullCheckpoint::capture(self.campaign, tick, candidate.graph_report())?;
        let families = prepare_committed_tick(candidate.graph_report())?
            .into_material_families(identity.tick_content_hash())?;
        let envelope = CommittedMaterialTickEnvelope::compose(
            self.campaign,
            &identity,
            families,
            candidate.material().register().canonical_bytes(),
            candidate.material().receipt_bytes(),
        )?;
        let encoded = material_storage::encode(
            candidate.material().register(),
            candidate.material().receipt_bytes(),
            &self.lookup,
            self.lookup_chain,
        )?;
        let prepared = Instant::now();
        progress(MaterialAdvanceStage::SavingPeriod);
        let mut client = self.config.connect(NoTls)?;
        let connected = Instant::now();
        let mut tx = client.transaction()?;
        tx.batch_execute(
            "SET LOCAL search_path TO pg_catalog; SET LOCAL synchronous_commit TO on",
        )?;
        let locked=tx.query_opt("SELECT campaign_id FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$1::uuid FOR UPDATE",&[self.campaign.as_uuid()])?;
        if locked.is_none() {
            return Err(MaterialRuntimeError::MissingCampaign);
        }
        let schema_started = Instant::now();
        verify_runtime_schema_client(&mut tx)?;
        let schema_verified = Instant::now();
        let timing = [
            started,
            adjudicated,
            prepared,
            connected,
            schema_started,
            schema_verified,
        ];
        let durable = read_tail_tick(&mut tx, self.campaign)?;
        if durable == identity.resolve_tick() {
            let stored = read_stored_material_tick(
                &mut tx,
                self.campaign,
                durable,
                &self.session,
                &self.lookup,
            )?;
            if stored.envelope.canonical_bytes()? != envelope.canonical_bytes()
                || stored.lookup_identity != material_storage::lookup_identity(&encoded.lookup)?
                || stored.lookup_chain != encoded.lookup_chain
            {
                return Err(MaterialRuntimeError::TailConflict);
            }
            tx.rollback()?;
            let (ack, _) = self
                .session
                .commit_prepared_and_publish(sink, candidate, |_| {
                    Ok::<_, MaterialRuntimeError>(
                        ReplayCommitDisposition::ReconciledAfterAmbiguousCommit,
                    )
                })
                .map_err(commit_error)?;
            self.lookup_chain = encoded.lookup_chain;
            self.tail = Some(ack);
            diagnostic.acknowledge(ReplayCommitDisposition::ReconciledAfterAmbiguousCommit);
            self.last_receipt = Some(diagnostic);
            self.last_choice_receipts = choices;
            record_advance_timing(ack.resolve_tick(), timing);
            return Ok(ack);
        }
        if durable != self.session.completed_tick() {
            return Err(MaterialRuntimeError::TailConflict);
        }
        if crate::organizer_runtime::pending(&mut tx, self.campaign, identity.resolve_tick())?
            != pending
        {
            return Err(MaterialRuntimeError::TailConflict);
        }
        let tick_sql =
            i64::try_from(identity.resolve_tick()).map_err(|_| MaterialRuntimeError::Bounds)?;
        insert_typed_tick_pre_marker_rows(
            &mut tx,
            self.campaign,
            tick_sql,
            candidate.graph_report(),
            &checkpoint,
            identity.tick_content_hash(),
        )?;
        tx.execute("INSERT INTO babylon_state.material_tick_v3 (campaign_id,resolve_tick,identity_bytes,register_storage_bytes,receipt_storage_bytes,lookup_delta_bytes) VALUES ($1::uuid,$2,$3,$4,$5,$6)",&[self.campaign.as_uuid(),&tick_sql,&identity.canonical_bytes(),&encoded.register_storage_bytes,&encoded.receipt_storage_bytes,&encoded.lookup_delta_bytes])?;
        crate::organizer_archive::insert_projection(
            &mut tx,
            self.campaign,
            candidate.material().register(),
        )?;
        if let Some(pending) = &pending {
            let affected = tx.execute("UPDATE babylon_state.organizer_command_v1 SET consumed_period=$3 WHERE campaign_id=$1 AND nonce=$2 AND consumed_period IS NULL", &[self.campaign.as_uuid(), &&pending.command.nonce[..], &tick_sql])?;
            if affected != 1 {
                return Err(MaterialRuntimeError::TailConflict);
            }
        }
        crate::metadata::advance_campaign_catalog_tick(
            &mut tx,
            self.campaign,
            tick_sql - 1,
            tick_sql,
        )?;
        let scope = candidate
            .graph_report()
            .result_stable_graph()
            .scenario_scope()
            .to_owned();
        let components = MaterialComponentIdentity::from_session(self.session.graph_session());
        let (ack, disposition) = self
            .session
            .commit_prepared_and_publish(sink, candidate, |_| {
                commit_material_envelope(
                    tx,
                    &self.config,
                    self.campaign,
                    &identity,
                    &envelope,
                    MaterialReadAuthority {
                        scope: &scope,
                        foundation_digest: identity.foundation_digest(),
                        components: &components,
                        opening: &self.lookup,
                        lookup_chain: None,
                        witnesses: [None, None],
                    },
                    (&encoded.lookup, encoded.lookup_chain),
                )
            })
            .map_err(commit_error)?;
        self.lookup_chain = encoded.lookup_chain;
        self.tail = Some(ack);
        diagnostic.acknowledge(disposition);
        self.last_receipt = Some(diagnostic);
        self.last_choice_receipts = choices;
        record_advance_timing(ack.resolve_tick(), timing);
        Ok(ack)
    }
}

// Commit the marker last, then reconcile an ambiguous acknowledgement against
// the complete authenticated candidate before permitting live publication.
fn commit_material_envelope(
    mut tx: postgres::Transaction<'_>,
    config: &Config,
    campaign: CampaignId,
    identity: &IdentifiedMaterialTick,
    envelope: &CommittedMaterialTickEnvelope,
    authority: MaterialReadAuthority<'_, '_>,
    expected_lookup: (&TypedLookup, [u8; 32]),
) -> Result<ReplayCommitDisposition, MaterialRuntimeError> {
    let (expected_lookup, expected_lookup_chain) = expected_lookup;
    let MaterialReadAuthority {
        scope,
        components,
        opening,
        ..
    } = authority;
    let tick = i64::try_from(identity.resolve_tick()).map_err(|_| MaterialRuntimeError::Bounds)?;
    #[cfg(test)]
    inject_marker_trigger_failure(&mut tx)?;
    tx.execute(
        "INSERT INTO babylon_state.tick_commit \
         (campaign_id,resolve_tick,envelope_layout_version,tick_content_hash,envelope_digest) \
         VALUES ($1::uuid,$2,3,$3,$4)",
        &[
            campaign.as_uuid(),
            &tick,
            &&identity.tick_content_hash().as_bytes()[..],
            &&envelope.digest()[..],
        ],
    )?;
    match commit_material_transaction(tx) {
        Ok(()) => Ok(ReplayCommitDisposition::Committed),
        Err(error) => {
            let mut retry_client = config.connect(NoTls)?;
            let mut retry = retry_client.transaction()?;
            verify_runtime_schema_client(&mut retry)?;
            if !marker_matches(
                &mut retry,
                StoredTickReadSource::Runtime,
                campaign,
                identity,
                envelope,
            )? {
                return Err(error);
            }
            let stored = read_authenticated_material_tick(
                &mut retry,
                StoredTickReadSource::Runtime,
                campaign,
                identity.resolve_tick(),
                MaterialReadAuthority {
                    scope,
                    foundation_digest: identity.foundation_digest(),
                    components,
                    opening,
                    lookup_chain: None,
                    witnesses: [None, None],
                },
            )?;
            if stored.identity != *identity
                || stored.envelope.canonical_bytes()? != envelope.canonical_bytes()
                || stored.lookup_identity != material_storage::lookup_identity(expected_lookup)?
                || stored.lookup_chain != expected_lookup_chain
            {
                return Err(MaterialRuntimeError::TailConflict);
            }
            Ok(ReplayCommitDisposition::ReconciledAfterAmbiguousCommit)
        }
    }
}

// Inject only after exact schema admission and all candidate rows are prepared.
// The replacement and its marker-trigger failure share the candidate transaction,
// so PostgreSQL rollback restores the original function without external repair.
#[cfg(test)]
fn inject_marker_trigger_failure(
    tx: &mut postgres::Transaction<'_>,
) -> Result<(), MaterialRuntimeError> {
    let armed = COMMIT_FAULT.with(|slot| {
        if slot.get() == Some(CommitFault::MarkerTrigger) {
            slot.set(None);
            true
        } else {
            false
        }
    });
    if armed {
        tx.batch_execute(
            "CREATE OR REPLACE FUNCTION babylon_meta.archive_wakeup_v1() RETURNS trigger \
             LANGUAGE plpgsql SET search_path = pg_catalog AS $fault$ BEGIN \
             RAISE EXCEPTION USING ERRCODE='P0001',MESSAGE='test-owned Archive wakeup failure'; END $fault$",
        )?;
    }
    Ok(())
}

// Keep commit acknowledgement loss inside the same reconciliation boundary as
// transport failure: only the persisted complete candidate can authorize publication.
fn commit_material_transaction(tx: postgres::Transaction<'_>) -> Result<(), MaterialRuntimeError> {
    #[cfg(test)]
    let fault = COMMIT_FAULT.with(|slot| slot.replace(None));
    #[cfg(test)]
    if fault == Some(CommitFault::BeforeCommit) {
        tx.rollback()?;
        return Err(MaterialRuntimeError::InjectedCommitLoss);
    }
    tx.commit()?;
    #[cfg(test)]
    if fault == Some(CommitFault::AfterCommit) {
        return Err(MaterialRuntimeError::InjectedCommitLoss);
    }
    Ok(())
}

#[cfg(test)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum CommitFault {
    BeforeCommit,
    AfterCommit,
    MarkerTrigger,
}
#[cfg(test)]
thread_local! {
    pub(crate) static COMMIT_FAULT: std::cell::Cell<Option<CommitFault>> = const { std::cell::Cell::new(None) };
}

// Operator diagnostics only: clocks never enter state, hashes, receipts or the
// protocol. Emit one bounded record after successful durable publication.
fn record_advance_timing(
    period: u64,
    [started, adjudicated, prepared, connected, schema_started, schema_verified]: [Instant; 6],
) {
    if std::env::var("BABYLON_TIMINGS").as_deref() == Ok("1") {
        eprintln!(
            "babylon-timing period={period} simulation_us={} preparation_us={} writer_connect_us={} writer_lock_us={} schema_verify_us={} write_publish_us={} durable_write_publish_us={} total_us={}",
            adjudicated.duration_since(started).as_micros(),
            prepared.duration_since(adjudicated).as_micros(),
            connected.duration_since(prepared).as_micros(),
            schema_started.duration_since(connected).as_micros(),
            schema_verified.duration_since(schema_started).as_micros(),
            schema_verified.elapsed().as_micros(),
            prepared.elapsed().as_micros(),
            started.elapsed().as_micros(),
        );
    }
}

fn commit_error(error: MaterialCommitError<MaterialRuntimeError>) -> MaterialRuntimeError {
    match error {
        MaterialCommitError::Preflight(error) => error.into(),
        MaterialCommitError::Commit(error) => error,
    }
}

struct StoredMaterialFoundation {
    spec: MaterialFoundationSpec,
    initial_register_bytes: Vec<u8>,
    foundation_digest: [u8; 32],
    graph_foundation_digest: [u8; 32],
}

impl StoredMaterialFoundation {
    fn from_row(row: &postgres::Row) -> Result<Self, MaterialRuntimeError> {
        let digest = |column: &str| -> Result<[u8; 32], MaterialRuntimeError> {
            row.try_get::<_, Vec<u8>>(column)?
                .try_into()
                .map_err(|_| MaterialRuntimeError::FoundationMismatch)
        };
        Ok(Self {
            spec: MaterialFoundationSpec {
                preset_id: row.try_get("preset_id")?,
                duration: read_duration(row)?,
                content_digest: digest("content_sha256")?,
            },
            initial_register_bytes: row.try_get("initial_register_bytes")?,
            foundation_digest: digest("foundation_sha256")?,
            graph_foundation_digest: digest("graph_foundation_sha256")?,
        })
    }
}

#[derive(Clone, Copy)]
pub(crate) enum FoundationReadSource {
    Runtime,
    FullObserver,
}

fn hydrate_material_foundation(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    expected_foundation_digest: [u8; 32],
) -> Result<MaterialRuntimeFoundation, MaterialRuntimeError> {
    load_material_foundation_components(
        client,
        campaign,
        expected_foundation_digest,
        FoundationReadSource::Runtime,
    )
}

enum CapturedGraphFoundation {
    Runtime(crate::runtime::CapturedCampaignFoundation),
    FullObserver,
}

pub(crate) struct CapturedMaterialFoundation {
    components: postgres::Row,
    graph: CapturedGraphFoundation,
    expected_foundation_digest: [u8; 32],
}

/// Admit the single stored component representation through the same reconstruction.
/// Observer reads use only their restricted view; runtime retains geography checks.
pub(crate) fn load_material_foundation_components(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    expected_foundation_digest: [u8; 32],
    source: FoundationReadSource,
) -> Result<MaterialRuntimeFoundation, MaterialRuntimeError> {
    capture_material_foundation_components(client, campaign, expected_foundation_digest, source)?
        .admit()
}

pub(crate) fn capture_material_foundation_components(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    expected_foundation_digest: [u8; 32],
    source: FoundationReadSource,
) -> Result<CapturedMaterialFoundation, MaterialRuntimeError> {
    use crate::production_projection::diagnostics::{Stage, Timing};
    let query = match source {
        FoundationReadSource::Runtime => {
            "SELECT f.preset_id,f.duration_kind,f.final_period,f.content_sha256,f.initial_register_bytes,f.foundation_sha256,g.foundation_sha256 AS graph_foundation_sha256 FROM babylon_state.material_campaign_foundation_v3 f JOIN babylon_state.campaign_foundation g USING(campaign_id) WHERE campaign_id=$1::uuid"
        }
        FoundationReadSource::FullObserver => {
            "SELECT * FROM public.v_observer_material_foundation_v1 WHERE campaign_id=$1::uuid"
        }
    };
    let query_timing = Timing::start(Stage::FoundationQuery, 0);
    let row = client.query_opt(query, &[campaign.as_uuid()])?;
    drop(query_timing);
    let Some(row) = row else {
        return Err(match source {
            FoundationReadSource::FullObserver => MaterialRuntimeError::MissingCampaign,
            FoundationReadSource::Runtime => {
                if client
                    .query_opt(
                        "SELECT campaign_id FROM babylon_state.campaign WHERE campaign_id=$1::uuid",
                        &[campaign.as_uuid()],
                    )?
                    .is_some()
                {
                    MaterialRuntimeError::LegacyCampaign
                } else {
                    MaterialRuntimeError::MissingCampaign
                }
            }
        });
    };
    if row.try_get::<_, &[u8]>("foundation_sha256")? != expected_foundation_digest {
        return Err(MaterialRuntimeError::FoundationMismatch);
    }
    let graph = match source {
        FoundationReadSource::Runtime => CapturedGraphFoundation::Runtime(
            crate::runtime::capture_campaign_foundation(client, campaign)?,
        ),
        FoundationReadSource::FullObserver => CapturedGraphFoundation::FullObserver,
    };
    Ok(CapturedMaterialFoundation {
        components: row,
        graph,
        expected_foundation_digest,
    })
}

impl CapturedMaterialFoundation {
    /// Every hit checks actual current snapshot components against an admitted
    /// canonical source. Captured SQL buffers are released after this witness.
    pub(crate) fn validate_against(
        &self,
        admitted: &crate::economic_content::EconomicContentAdmission,
    ) -> Result<(), MaterialRuntimeError> {
        let row = &self.components;
        let foundation = admitted.foundation();
        let spec = foundation.spec();
        if row.try_get::<_, &str>("preset_id")? != spec.preset_id
            || read_duration(row)? != spec.duration
            || row.try_get::<_, &[u8]>("content_sha256")? != spec.content_digest
            || row.try_get::<_, &[u8]>("initial_register_bytes")?
                != foundation.initial_register().canonical_bytes()
            || row.try_get::<_, &[u8]>("foundation_sha256")? != admitted.digest()
            || self.expected_foundation_digest != admitted.digest()
            || row.try_get::<_, &[u8]>("graph_foundation_sha256")? != admitted.graph_digest
        {
            return Err(MaterialRuntimeError::FoundationMismatch);
        }
        let graph = foundation.graph_foundation();
        match &self.graph {
            CapturedGraphFoundation::Runtime(captured) => {
                captured.validate_against(graph, &admitted.graph_digest)?;
            }
            CapturedGraphFoundation::FullObserver => {
                crate::runtime::verify_captured_foundation_components(
                    row,
                    graph,
                    &admitted.graph_digest,
                    "graph_foundation_sha256",
                )?;
            }
        }
        Ok(())
    }

    pub(crate) fn admit(self) -> Result<MaterialRuntimeFoundation, MaterialRuntimeError> {
        use crate::production_projection::diagnostics::{Stage, Timing};
        let Self {
            components: row,
            graph,
            expected_foundation_digest,
        } = self;
        let stored = StoredMaterialFoundation::from_row(&row)?;
        let graph = match graph {
            CapturedGraphFoundation::Runtime(captured) => {
                drop(row);
                captured.admit()?
            }
            CapturedGraphFoundation::FullObserver => {
                let _graph_admission_timing = Timing::start(Stage::FoundationGraphAdmission, 0);
                let digest = |name: &str| -> Result<[u8; 32], MaterialRuntimeError> {
                    row.try_get::<_, Vec<u8>>(name)?
                        .try_into()
                        .map_err(|_| MaterialRuntimeError::FoundationMismatch)
                };
                let stable_graph = row.try_get("stable_graph")?;
                let world_registers = row.try_get("world_registers")?;
                let resolver_manifest = row.try_get("resolver_manifest")?;
                let prepared_environment = row.try_get("prepared_environment")?;
                let replay_session_id: String = row.try_get("replay_session_id")?;
                let rng_seed = row.try_get("rng_seed")?;
                let defines_hash = digest("defines_hash")?;
                let rules_hash = digest("rules_hash")?;
                let ref_digest = digest("ref_digest")?;
                let bundle: Vec<u8> = row.try_get("content_bundle_bytes")?;
                drop(row);
                CampaignFoundation::from_persisted(
                    stable_graph,
                    world_registers,
                    resolver_manifest,
                    prepared_environment,
                    &replay_session_id,
                    rng_seed,
                    defines_hash,
                    rules_hash,
                    ref_digest,
                    &bundle,
                    stored.graph_foundation_digest,
                )?
            }
        };
        reconstruct_material_foundation(stored, graph, expected_foundation_digest)
    }
}

fn reconstruct_material_foundation(
    stored: StoredMaterialFoundation,
    graph_foundation: CampaignFoundation,
    expected_foundation_digest: [u8; 32],
) -> Result<MaterialRuntimeFoundation, MaterialRuntimeError> {
    use crate::production_projection::diagnostics::{Stage, Timing};
    let component_timing = Timing::start(Stage::FoundationComponentHash, 0);
    if stored.foundation_digest != expected_foundation_digest
        || sha256_of(graph_foundation.canonical_bytes()) != stored.graph_foundation_digest
    {
        return Err(MaterialRuntimeError::FoundationMismatch);
    }
    // Authenticate canonical component framing before catalog regeneration.
    // This hashes borrowed components without allocating a second full export.
    let component_digest = envelope::CanonicalMaterialFoundation::new(
        stored.spec.preset_id.as_bytes(),
        stored.spec.duration,
        &stored.spec.content_digest,
        graph_foundation.canonical_bytes(),
        &stored.initial_register_bytes,
    )?
    .digest();
    if component_digest != expected_foundation_digest {
        return Err(MaterialRuntimeError::FoundationMismatch);
    }
    drop(component_timing);
    let register_timing = Timing::start(Stage::FoundationRegisterDecode, 0);
    let register = MaterialWorldRegister::decode(&stored.initial_register_bytes)?;
    if register.completed_tick() != 0 {
        return Err(MaterialRuntimeError::FoundationMismatch);
    }
    drop(register_timing);
    // The decoded register owns its canonical bytes; release the database copy.
    drop(stored.initial_register_bytes);
    let graph_timing = Timing::start(Stage::FoundationGraphSession, 0);
    let graph = reconstruct_graph_foundation_session(&graph_foundation)?;
    drop(graph_timing);
    let _admission_timing = Timing::start(Stage::FoundationAdmission, 0);
    let reconstructed =
        MaterialRuntimeFoundation::from_parts(graph, graph_foundation, register, stored.spec)?;
    if reconstructed.digest() != expected_foundation_digest {
        return Err(MaterialRuntimeError::FoundationMismatch);
    }
    Ok(reconstructed)
}
fn read_tail_tick(
    client: &mut impl GenericClient,
    campaign: CampaignId,
) -> Result<u64, MaterialRuntimeError> {
    let row=client.query_one("SELECT count(*),coalesce(max(resolve_tick),0),coalesce(bool_and(envelope_layout_version=3),true) FROM babylon_state.tick_commit WHERE campaign_id=$1::uuid",&[campaign.as_uuid()])?;
    let count: i64 = row.try_get(0)?;
    let tick: i64 = row.try_get(1)?;
    let version: bool = row.try_get(2)?;
    if count != tick || !version {
        return Err(MaterialRuntimeError::TailConflict);
    }
    u64::try_from(tick).map_err(|_| MaterialRuntimeError::TailConflict)
}
fn marker_matches(
    client: &mut impl GenericClient,
    source: StoredTickReadSource,
    campaign: CampaignId,
    identity: &IdentifiedMaterialTick,
    envelope: &CommittedMaterialTickEnvelope,
) -> Result<bool, MaterialRuntimeError> {
    let tick = i64::try_from(identity.resolve_tick()).map_err(|_| MaterialRuntimeError::Bounds)?;
    let row = capture_marker(client, source, campaign, tick)?;
    admitted_marker_matches(row.as_ref(), identity, envelope.digest())
}

fn capture_marker(
    client: &mut impl GenericClient,
    source: StoredTickReadSource,
    campaign: CampaignId,
    tick: i64,
) -> Result<Option<postgres::Row>, MaterialRuntimeError> {
    Ok(client.query_opt(&format!("SELECT envelope_layout_version,tick_content_hash,envelope_digest FROM {} WHERE campaign_id=$1::uuid AND resolve_tick=$2", source.relation(StoredTickRelation::TickCommit)), &[campaign.as_uuid(), &tick])?)
}

fn admitted_marker_matches(
    row: Option<&postgres::Row>,
    identity: &IdentifiedMaterialTick,
    envelope_digest: [u8; 32],
) -> Result<bool, MaterialRuntimeError> {
    let Some(row) = row else {
        return Ok(false);
    };
    if row.try_get::<_, i16>(0)? != 3
        || row.try_get::<_, Vec<u8>>(1)? != identity.tick_content_hash().as_bytes()
        || row.try_get::<_, Vec<u8>>(2)? != envelope_digest
    {
        return Err(MaterialRuntimeError::TailConflict);
    }
    Ok(true)
}

// Authenticated observation needs complete admission and the exact envelope
// digest. Durable reconciliation additionally needs retained canonical bytes.
enum StoredMaterialEnvelope {
    Complete(CommittedMaterialTickEnvelope),
    Attested(CommittedMaterialTickAttestation),
}
#[derive(Clone, Copy)]
enum MaterialEnvelopeRead {
    CanonicalBytes,
    AuthenticatedRead,
}
impl StoredMaterialEnvelope {
    fn digest(&self) -> [u8; 32] {
        match self {
            Self::Complete(envelope) => envelope.digest(),
            Self::Attested(envelope) => envelope.digest(),
        }
    }
    fn canonical_bytes(&self) -> Result<&[u8], MaterialRuntimeError> {
        match self {
            Self::Complete(envelope) => Ok(envelope.canonical_bytes()),
            Self::Attested(_) => Err(MaterialRuntimeError::TailConflict),
        }
    }
}

/// A fully authenticated committed material tick, never a partial checkpoint read.
pub(crate) struct StoredMaterialTick<'w> {
    pub(crate) identity: IdentifiedMaterialTick,
    envelope: StoredMaterialEnvelope,
    pub(crate) graph: babylon_graph::stable_state::StableGraphState,
    material: babylon_tick::material_state::MaterialStateRows,
    sections: Vec<Vec<u8>>,
    pub(crate) register: std::borrow::Cow<'w, MaterialWorldRegister>,
    pub(crate) events: Vec<StoredEvent>,
    lookup_identity: (usize, [u8; 32]),
    lookup_chain: [u8; 32],
}

pub(crate) type RegisterWitnesses<'w> = [Option<&'w MaterialWorldRegister>; 2];

/// Uses the same complete decoder and envelope proof as durable reconciliation.
/// The caller retains its role confinement and repeatable-read transaction.
pub(crate) fn read_observer_material_tick<'w>(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    scope: &str,
    foundation_digest: [u8; 32],
    components: &MaterialComponentIdentity,
    lookup_authority: (
        &material_storage::OpeningRegister,
        [u8; 32],
        RegisterWitnesses<'w>,
    ),
) -> Result<StoredMaterialTick<'w>, MaterialRuntimeError> {
    let (opening, chain, witnesses) = lookup_authority;
    read_authenticated_material_tick(
        client,
        StoredTickReadSource::FullObserver,
        campaign,
        tick,
        MaterialReadAuthority {
            scope,
            foundation_digest,
            components,
            opening,
            lookup_chain: Some(chain),
            witnesses,
        },
    )
}

fn read_stored_material_tick(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    session: &MaterialReplaySession<HypergraphStore>,
    opening: &material_storage::OpeningRegister,
) -> Result<StoredMaterialTick<'static>, MaterialRuntimeError> {
    let scope = session
        .graph_session()
        .stable_graph_state()
        .map_err(MaterialReplayError::Graph)?
        .scenario_scope()
        .to_owned();
    let components = MaterialComponentIdentity::from_session(session.graph_session());
    read_authenticated_material_tick(
        client,
        StoredTickReadSource::Runtime,
        campaign,
        tick,
        MaterialReadAuthority {
            scope: &scope,
            foundation_digest: session.foundation_digest(),
            components: &components,
            opening,
            lookup_chain: None,
            witnesses: [None, None],
        },
    )
}

/// Authenticate one requested Archive period against the existing committed
/// envelope and captured foundation, without replaying or restoring history.
pub(crate) struct CapturedArchiveOrganizerRegister {
    campaign: CampaignId,
    tick: u64,
    content_hash: [u8; 32],
    foundation: CapturedMaterialFoundation,
    current: CapturedMaterialTick,
    prior: Option<CapturedMaterialTick>,
    lookup: Vec<postgres::Row>,
    actions: postgres::Row,
    command: crate::organizer_runtime::CapturedOrganizerCommand,
    projection: crate::organizer_archive::CapturedOrganizerProjection,
}

pub(crate) fn capture_archive_organizer_register(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    receipt: &crate::PendingArchiveReceipt,
) -> Result<Option<CapturedArchiveOrganizerRegister>, MaterialRuntimeError> {
    let Some(row) = client.query_opt("SELECT foundation_sha256 FROM babylon_state.material_campaign_foundation_v3 WHERE campaign_id=$1", &[campaign.as_uuid()])? else { return Ok(None); };
    let digest = row
        .try_get::<_, Vec<u8>>(0)?
        .try_into()
        .map_err(|_| MaterialRuntimeError::FoundationMismatch)?;
    let tick = receipt.resolve_tick();
    let tick_sql = i64::try_from(tick).map_err(|_| MaterialRuntimeError::Bounds)?;
    let foundation = capture_material_foundation_components(
        client,
        campaign,
        digest,
        FoundationReadSource::Runtime,
    )?;
    let current =
        CapturedMaterialTick::capture(client, StoredTickReadSource::Runtime, campaign, tick)?;
    let prior = if tick > 1 {
        Some(CapturedMaterialTick::capture(
            client,
            StoredTickReadSource::Runtime,
            campaign,
            tick - 1,
        )?)
    } else {
        None
    };
    let lookup = capture_material_lookup(client, StoredTickReadSource::Runtime, campaign, tick)?;
    let actions = client.query_opt("SELECT layout_version,action_batch_digest,exact_action_batch_bytes FROM babylon_state.tick_action_batch_v1 WHERE campaign_id=$1::uuid AND resolve_tick=$2", &[campaign.as_uuid(), &tick_sql])?.ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
    let command = crate::organizer_runtime::capture_pending(client, campaign, tick)?;
    let projection = crate::organizer_archive::capture_projection(client, campaign, tick)?;
    Ok(Some(CapturedArchiveOrganizerRegister {
        campaign,
        tick,
        content_hash: *receipt.tick_content_hash(),
        foundation,
        current,
        prior,
        lookup,
        actions,
        command,
        projection,
    }))
}

impl CapturedArchiveOrganizerRegister {
    pub(crate) fn admit(
        self,
        cached: Option<std::sync::Arc<crate::economic_content::EconomicContentAdmission>>,
    ) -> Result<
        (
            MaterialWorldRegister,
            std::sync::Arc<crate::economic_content::EconomicContentAdmission>,
        ),
        MaterialRuntimeError,
    > {
        let admitted = admit_archive_foundation(self.foundation, cached)?;
        let digest = admitted.digest();
        let scope = admitted.foundation_graph().scenario_scope();
        let components = &admitted.component_identity;
        let opening = admitted
            .opening()
            .map_err(|_| MaterialRuntimeError::FoundationMismatch)?;
        let (lookup, prior_lookup) = admit_archive_lookup(self.lookup, self.tick, opening)?;
        let authority = MaterialReadAuthority {
            scope,
            foundation_digest: digest,
            components,
            opening,
            lookup_chain: None,
            witnesses: [None, None],
        };
        // Admit the complete historical proof first, retaining only the small
        // organizer inputs. Its decoded register and proof owners must leave
        // scope before reconstructing the current national register.
        let prior_organizer = if let Some(prior) = self.prior {
            let prior = prior.admit(
                self.campaign,
                self.tick - 1,
                authority,
                prior_lookup.ok_or(MaterialRuntimeError::InvalidCheckpoint)?,
                MaterialEnvelopeRead::AuthenticatedRead,
            )?;
            components.validate_sections(&prior.sections)?;
            if prior.identity.foundation_digest() != digest {
                return Err(MaterialRuntimeError::InvalidCheckpoint);
            }
            Some((
                prior.register.organizer_config().cloned(),
                prior.register.organizer_state().cloned(),
            ))
        } else {
            None
        };
        // Complete envelope/marker/section admission before releasing its proof owners.
        let register = {
            let stored = self.current.admit(
                self.campaign,
                self.tick,
                authority,
                lookup,
                MaterialEnvelopeRead::AuthenticatedRead,
            )?;
            if stored.identity.foundation_digest() != digest
                || stored.identity.tick_content_hash().as_bytes() != &self.content_hash
            {
                return Err(MaterialRuntimeError::InvalidCheckpoint);
            }
            components.validate_sections(&stored.sections)?;
            stored.register
        };
        let accepted = if let Some(config) = register.organizer_config() {
            let prior_state = if let Some((prior_config, prior_state)) = prior_organizer {
                if prior_config.as_ref() != Some(config) {
                    return Err(MaterialRuntimeError::InvalidCheckpoint);
                }
                prior_state.ok_or(MaterialRuntimeError::InvalidCheckpoint)?
            } else {
                babylon_practice_contract::initial_organizer_state(config)
                    .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?
            };
            let command = self.command.admit()?;
            if command.as_ref().is_some_and(|(_, consumed)| {
                consumed.and_then(|period| u64::try_from(period).ok()) != Some(self.tick)
            }) {
                return Err(MaterialRuntimeError::InvalidCheckpoint);
            }
            let commitment = command.as_ref().map(|(commitment, _)| commitment);
            let receipt = register
                .organizer_state()
                .and_then(|state| {
                    state.receipts.iter().find(|row| {
                        row.actor_id == config.controlled_actor_id && row.period == self.tick
                    })
                })
                .ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
            if receipt.commitment_id != commitment.map(|input| input.commitment_id) {
                return Err(MaterialRuntimeError::InvalidCheckpoint);
            }
            Some(
                babylon_practice_contract::organizer_action_batch(
                    config,
                    &prior_state,
                    commitment,
                    components.session_id().clone(),
                )
                .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?,
            )
        } else {
            None
        };
        components.validate_actions(
            self.tick,
            self.actions.try_get(0)?,
            &self.actions.try_get::<_, Vec<u8>>(1)?,
            &self.actions.try_get::<_, Vec<u8>>(2)?,
            accepted.as_ref(),
        )?;
        self.projection.validate(&register)?;
        Ok((register.into_owned(), admitted))
    }
}

fn admit_archive_foundation(
    foundation: CapturedMaterialFoundation,
    cached: Option<std::sync::Arc<crate::economic_content::EconomicContentAdmission>>,
) -> Result<std::sync::Arc<crate::economic_content::EconomicContentAdmission>, MaterialRuntimeError>
{
    if let Some(admitted) = cached {
        foundation.validate_against(&admitted)?;
        drop(foundation);
        Ok(admitted)
    } else {
        Ok(std::sync::Arc::new(
            crate::economic_content::EconomicContentAdmission::from_foundation(foundation.admit()?)
                .map_err(|_| MaterialRuntimeError::FoundationMismatch)?,
        ))
    }
}

#[derive(Clone, Copy)]
struct MaterialReadAuthority<'a, 'w> {
    scope: &'a str,
    foundation_digest: [u8; 32],
    components: &'a MaterialComponentIdentity,
    opening: &'a material_storage::OpeningRegister,
    lookup_chain: Option<[u8; 32]>,
    witnesses: RegisterWitnesses<'w>,
}

fn read_authenticated_material_tick<'w>(
    client: &mut impl GenericClient,
    source: StoredTickReadSource,
    campaign: CampaignId,
    tick: u64,
    authority: MaterialReadAuthority<'_, 'w>,
) -> Result<StoredMaterialTick<'w>, MaterialRuntimeError> {
    let MaterialReadAuthority {
        foundation_digest,
        components,
        opening,
        witnesses,
        ..
    } = authority;
    let stored = read_stored_material_tick_rows(client, source, campaign, tick, authority)?;
    if stored.identity.foundation_digest() != foundation_digest {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    validate_component_identity(
        client,
        source,
        campaign,
        tick,
        components,
        &stored,
        (opening, witnesses),
    )?;
    if source == StoredTickReadSource::Runtime {
        crate::organizer_archive::validate_projection(client, campaign, &stored.register)?;
    }
    Ok(stored)
}

// Preserve original cold contract: consecutive lookup metadata through the
// requested marker, then only that period's full canonical envelope. No older
// state/receipt/envelope is decoded here. One local table is live at a time.
fn read_material_lookup(
    client: &mut impl GenericClient,
    source: StoredTickReadSource,
    campaign: CampaignId,
    tick: u64,
    opening: &material_storage::OpeningRegister,
) -> Result<material_storage::DecodedPeriodLookup, MaterialRuntimeError> {
    if tick == 0 {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    let tick_sql = i64::try_from(tick).map_err(|_| MaterialRuntimeError::Bounds)?;
    let query = format!("SELECT m.resolve_tick,m.lookup_delta_bytes FROM {} m JOIN {} c ON c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick WHERE m.campaign_id=$1::uuid AND m.resolve_tick>=1 AND m.resolve_tick<=$2 ORDER BY m.resolve_tick", source.relation(StoredTickRelation::MaterialTick), source.relation(StoredTickRelation::TickCommit));
    let parameters: &[&(dyn postgres::types::ToSql + Sync)] = &[campaign.as_uuid(), &tick_sql];
    let mut rows = client.query_raw(&query, parameters.iter().copied())?;
    admit_lookup_chain(
        || rows.next().map_err(MaterialRuntimeError::from),
        tick,
        opening,
        false,
    )
    .map(|(current, _)| current)
}

fn capture_material_lookup(
    client: &mut impl GenericClient,
    source: StoredTickReadSource,
    campaign: CampaignId,
    tick: u64,
) -> Result<Vec<postgres::Row>, MaterialRuntimeError> {
    if tick == 0 {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    let tick_sql = i64::try_from(tick).map_err(|_| MaterialRuntimeError::Bounds)?;
    let query = format!(
        "SELECT m.resolve_tick,m.lookup_delta_bytes FROM {} m JOIN {} c ON c.campaign_id=m.campaign_id AND c.resolve_tick=m.resolve_tick WHERE m.campaign_id=$1::uuid AND m.resolve_tick>=1 AND m.resolve_tick<=$2 ORDER BY m.resolve_tick",
        source.relation(StoredTickRelation::MaterialTick),
        source.relation(StoredTickRelation::TickCommit),
    );
    Ok(client.query(&query, &[campaign.as_uuid(), &tick_sql])?)
}

fn admit_archive_lookup(
    rows: Vec<postgres::Row>,
    tick: u64,
    opening: &material_storage::OpeningRegister,
) -> Result<
    (
        material_storage::DecodedPeriodLookup,
        Option<material_storage::DecodedPeriodLookup>,
    ),
    MaterialRuntimeError,
> {
    let mut rows = rows.into_iter();
    admit_lookup_chain(|| Ok(rows.next()), tick, opening, true)
}

fn admit_lookup_chain(
    mut next: impl FnMut() -> Result<Option<postgres::Row>, MaterialRuntimeError>,
    tick: u64,
    opening: &material_storage::OpeningRegister,
    retain_prior: bool,
) -> Result<
    (
        material_storage::DecodedPeriodLookup,
        Option<material_storage::DecodedPeriodLookup>,
    ),
    MaterialRuntimeError,
> {
    let mut expected = 1_u64;
    let mut chain = material_storage::initial_lookup_chain(opening)?;
    let mut tail = None;
    let mut prior = None;
    while let Some(row) = next()? {
        if u64::try_from(row.try_get::<_, i64>(0)?).ok() != Some(expected) {
            return Err(MaterialRuntimeError::InvalidCheckpoint);
        }
        let decoded = material_storage::read_period_lookup(
            opening,
            expected,
            row.try_get(1)?,
            material_storage::LookupAnchor::Previous(chain),
        )?;
        chain = decoded.chain;
        if expected == tick {
            tail = Some(decoded);
        } else if retain_prior && expected.checked_add(1) == Some(tick) {
            prior = Some(decoded);
        }
        expected = expected
            .checked_add(1)
            .ok_or(MaterialRuntimeError::Bounds)?;
    }
    if expected != tick.checked_add(1).ok_or(MaterialRuntimeError::Bounds)? {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    Ok((tail.ok_or(MaterialRuntimeError::InvalidCheckpoint)?, prior))
}

fn read_stored_material_tick_rows<'w>(
    client: &mut impl GenericClient,
    source: StoredTickReadSource,
    campaign: CampaignId,
    tick: u64,
    authority: MaterialReadAuthority<'_, 'w>,
) -> Result<StoredMaterialTick<'w>, MaterialRuntimeError> {
    let captured = CapturedMaterialTick::capture(client, source, campaign, tick)?;
    let decoded = if let Some(chain) = authority.lookup_chain {
        material_storage::read_period_lookup(
            authority.opening,
            tick,
            captured.row.try_get(3)?,
            material_storage::LookupAnchor::Current(chain),
        )?
    } else {
        read_material_lookup(client, source, campaign, tick, authority.opening)?
    };
    let envelope_read = match source {
        StoredTickReadSource::Runtime => MaterialEnvelopeRead::CanonicalBytes,
        StoredTickReadSource::FullObserver => MaterialEnvelopeRead::AuthenticatedRead,
    };
    captured.admit(campaign, tick, authority, decoded, envelope_read)
}

struct CapturedMaterialTick {
    row: postgres::Row,
    graph: stored_tick::CapturedGraphState,
    material: stored_tick::CapturedMaterialRows,
    checkpoint: stored_tick::CapturedCheckpointRows,
    events: stored_tick::CapturedEventRows,
    choices: stored_tick::CapturedChoiceReceiptRows,
    archive: stored_tick::CapturedArchiveReceiptRows,
    marker: Option<postgres::Row>,
}
impl CapturedMaterialTick {
    fn capture(
        client: &mut impl GenericClient,
        source: StoredTickReadSource,
        campaign: CampaignId,
        tick: u64,
    ) -> Result<Self, MaterialRuntimeError> {
        let tick_sql = i64::try_from(tick).map_err(|_| MaterialRuntimeError::Bounds)?;
        let row = client.query_opt(&format!("SELECT identity_bytes,register_storage_bytes,receipt_storage_bytes,lookup_delta_bytes FROM {} WHERE campaign_id=$1::uuid AND resolve_tick=$2",source.relation(StoredTickRelation::MaterialTick)), &[campaign.as_uuid(),&tick_sql])?.ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
        Ok(Self {
            row,
            graph: stored_tick::CapturedGraphState::capture(client, source, campaign, tick_sql)?,
            material: stored_tick::CapturedMaterialRows::capture(
                client, source, campaign, tick_sql,
            )?,
            checkpoint: stored_tick::CapturedCheckpointRows::capture(
                client, source, campaign, tick_sql,
            )?,
            events: stored_tick::CapturedEventRows::capture(client, source, campaign, tick_sql)?,
            choices: stored_tick::CapturedChoiceReceiptRows::capture(
                client, source, campaign, tick_sql,
            )?,
            archive: stored_tick::CapturedArchiveReceiptRows::capture(
                client, source, campaign, tick_sql,
            )?,
            marker: capture_marker(client, source, campaign, tick_sql)?,
        })
    }
    fn admit<'w>(
        self,
        campaign: CampaignId,
        tick: u64,
        authority: MaterialReadAuthority<'_, 'w>,
        decoded: material_storage::DecodedPeriodLookup,
        envelope_read: MaterialEnvelopeRead,
    ) -> Result<StoredMaterialTick<'w>, MaterialRuntimeError> {
        let MaterialReadAuthority {
            scope,
            opening,
            components,
            witnesses,
            ..
        } = authority;
        let row = self.row;
        let identity = IdentifiedMaterialTick::decode(&row.try_get::<_, Vec<u8>>(0)?)?;
        let register_storage: Vec<u8> = row.try_get(1)?;
        let receipt_storage: Vec<u8> = row.try_get(2)?;
        // try_get owns the package copies; release the raw PostgreSQL backing row.
        drop(row);
        let lookup_chain = decoded.chain;
        let admitted = material_storage::decode_typed_with_witness(
            opening,
            tick,
            &register_storage,
            &receipt_storage,
            &decoded.lookup,
            lookup_chain,
            witnesses
                .into_iter()
                .flatten()
                .find(|register| register.completed_tick() == tick),
        )?;
        drop(register_storage);
        drop(receipt_storage);
        let lookup_identity = material_storage::lookup_identity(&decoded.lookup)?;
        drop(decoded);
        let decoded_register = admitted.register;
        // Storage admission proved exact equality with the immutable register,
        // whether owned or borrowed. Frame that owner and release the raw copy.
        drop(admitted.register_bytes);
        drop(admitted.receipts);
        if identity.resolve_tick() != tick || decoded_register.completed_tick() != tick {
            return Err(MaterialRuntimeError::InvalidCheckpoint);
        }
        let graph = self.graph.admit(scope)?;
        let material = self.material.admit()?;
        let (checkpoint, sections) = self.checkpoint.admit(
            tick,
            stored_tick::CheckpointSectionSources {
                graph: &graph,
                material: &material,
                foundation_sections: components.checkpoint_sources(),
            },
        )?;
        let (graph_rows, _) =
            compose_graph_rows_with_encoder(graph.rows(), &mut |row: StableGraphRowRef<'_>| {
                row.encode()
            })?;
        let events = self.events.admit()?;
        let families = CommittedTickRowFamilies {
            graph: graph_rows,
            state: compose_material_state_rows(&material)?,
            event: events.encoded,
            choice_receipt: self.choices.admit()?,
            checkpoint,
            archive_dirty_receipt: self.archive.admit()?,
        };
        let envelope = match envelope_read {
            MaterialEnvelopeRead::CanonicalBytes => {
                StoredMaterialEnvelope::Complete(CommittedMaterialTickEnvelope::compose(
                    campaign,
                    &identity,
                    families,
                    decoded_register.canonical_bytes(),
                    &admitted.receipt_bytes,
                )?)
            }
            MaterialEnvelopeRead::AuthenticatedRead => {
                let attested = CommittedMaterialTickEnvelope::attest(
                    campaign,
                    &identity,
                    families,
                    decoded_register.canonical_bytes(),
                    &admitted.receipt_bytes,
                )?;
                if std::env::var("BABYLON_TIMINGS").as_deref() == Ok("1") {
                    eprintln!(
                        "material_envelope_attestation tick={tick} canonical_bytes={} scratch_limit_bytes=65536",
                        attested.encoded_bytes(),
                    );
                }
                StoredMaterialEnvelope::Attested(attested)
            }
        };
        drop(admitted.receipt_bytes);
        if !admitted_marker_matches(self.marker.as_ref(), &identity, envelope.digest())? {
            return Err(MaterialRuntimeError::InvalidCheckpoint);
        }
        Ok(StoredMaterialTick {
            identity,
            envelope,
            graph,
            material,
            sections,
            register: decoded_register,
            lookup_identity,
            lookup_chain,
            events: events.decoded,
        })
    }
}
// Only runtime authority can authenticate organizer inputs. The player uses
// the restricted projection; no observer SQL view acquires private input access.
fn authenticated_organizer_actions(
    client: &mut impl GenericClient,
    source: StoredTickReadSource,
    campaign: CampaignId,
    tick: u64,
    components: &MaterialComponentIdentity,
    stored: &StoredMaterialTick<'_>,
    foundation_opening: &material_storage::OpeningRegister,
) -> Result<Option<OrderedPracticeActionBatch>, MaterialRuntimeError> {
    let register = &stored.register;
    let Some(config) = register.organizer_config() else {
        return Ok(None);
    };
    if source != StoredTickReadSource::Runtime {
        return Err(MaterialRuntimeError::OrganizerObserverProjectionRefused);
    }
    let previous_tick = tick
        .checked_sub(1)
        .ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
    let opening = if previous_tick == 0 {
        babylon_practice_contract::initial_organizer_state(config)
            .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?
    } else {
        let previous = read_stored_material_tick_rows(
            client,
            source,
            campaign,
            previous_tick,
            MaterialReadAuthority {
                scope: stored.graph.scenario_scope(),
                foundation_digest: stored.identity.foundation_digest(),
                components,
                opening: foundation_opening,
                lookup_chain: None,
                witnesses: [None, None],
            },
        )?;
        components.validate_sections(&previous.sections)?;
        if previous.identity.foundation_digest() != stored.identity.foundation_digest()
            || previous.register.organizer_config() != Some(config)
        {
            return Err(MaterialRuntimeError::InvalidCheckpoint);
        }
        previous
            .register
            .organizer_state()
            .cloned()
            .ok_or(MaterialRuntimeError::InvalidCheckpoint)?
    };
    let command = crate::organizer_runtime::capture_pending(client, campaign, tick)?.admit()?;
    if command.as_ref().is_some_and(|(_, consumed)| {
        consumed.and_then(|period| u64::try_from(period).ok()) != Some(tick)
    }) {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    let commitment = command.map(|(commitment, _)| commitment);
    let receipt = register
        .organizer_state()
        .and_then(|state| {
            state.receipts.iter().find(|receipt| {
                receipt.actor_id == config.controlled_actor_id && receipt.period == tick
            })
        })
        .ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
    if receipt.commitment_id != commitment.as_ref().map(|input| input.commitment_id) {
        return Err(MaterialRuntimeError::InvalidCheckpoint);
    }
    babylon_practice_contract::organizer_action_batch(
        config,
        &opening,
        commitment.as_ref(),
        components.session_id().clone(),
    )
    .map(Some)
    .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)
}

fn observer_organizer_actions(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: u64,
    components: &MaterialComponentIdentity,
    stored: &StoredMaterialTick<'_>,
    register_authority: (&material_storage::OpeningRegister, RegisterWitnesses<'_>),
    bytes: &[u8],
) -> Result<Option<OrderedPracticeActionBatch>, MaterialRuntimeError> {
    let (opening, witnesses) = register_authority;
    let Some(config) = stored.register.organizer_config() else {
        return Ok(None);
    };
    let previous_tick = tick
        .checked_sub(1)
        .ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
    let prior = if previous_tick == 0 {
        babylon_practice_contract::initial_organizer_state(config)
            .map_err(|_| MaterialRuntimeError::InvalidCheckpoint)?
    } else {
        let previous = read_stored_material_tick_rows(
            client,
            StoredTickReadSource::FullObserver,
            campaign,
            previous_tick,
            MaterialReadAuthority {
                scope: stored.graph.scenario_scope(),
                foundation_digest: stored.identity.foundation_digest(),
                components,
                opening,
                lookup_chain: None,
                witnesses,
            },
        )?;
        components.validate_sections(&previous.sections)?;
        if previous.identity.foundation_digest() != stored.identity.foundation_digest()
            || previous.register.organizer_config() != Some(config)
        {
            return Err(MaterialRuntimeError::InvalidCheckpoint);
        }
        previous
            .register
            .organizer_state()
            .cloned()
            .ok_or(MaterialRuntimeError::InvalidCheckpoint)?
    };
    let current = stored
        .register
        .organizer_state()
        .ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
    observer_actions::reconstruct(
        config,
        &prior,
        current,
        components.session_id(),
        tick,
        bytes,
    )
    .map(Some)
}

fn validate_component_identity(
    client: &mut impl GenericClient,
    source: StoredTickReadSource,
    campaign: CampaignId,
    tick: u64,
    components: &MaterialComponentIdentity,
    stored: &StoredMaterialTick<'_>,
    register_authority: (&material_storage::OpeningRegister, RegisterWitnesses<'_>),
) -> Result<(), MaterialRuntimeError> {
    let (opening, witnesses) = register_authority;
    components.validate_sections(&stored.sections)?;
    let tick_sql = i64::try_from(tick).map_err(|_| MaterialRuntimeError::Bounds)?;
    let row = client
        .query_opt(
            &format!(
                "SELECT layout_version,action_batch_digest,exact_action_batch_bytes FROM {} \
            WHERE campaign_id=$1::uuid AND resolve_tick=$2",
                source.relation(StoredTickRelation::TickActionBatch)
            ),
            &[campaign.as_uuid(), &tick_sql],
        )?
        .ok_or(MaterialRuntimeError::InvalidCheckpoint)?;
    let bytes = row.try_get::<_, Vec<u8>>(2)?;
    let accepted = match source {
        StoredTickReadSource::Runtime => authenticated_organizer_actions(
            client, source, campaign, tick, components, stored, opening,
        )?,
        StoredTickReadSource::FullObserver => observer_organizer_actions(
            client,
            campaign,
            tick,
            components,
            stored,
            (opening, witnesses),
            &bytes,
        )?,
    };
    components.validate_actions(
        tick,
        row.try_get(0)?,
        &row.try_get::<_, Vec<u8>>(1)?,
        &bytes,
        accepted.as_ref(),
    )
}

#[cfg(test)]
mod reconstruction_tests;

#[cfg(test)]
mod writer_bounds_tests {
    use super::*;

    #[test]
    fn validated_caller_gets_bounded_writer_settings_without_mutating_the_input() {
        let mut caller = Config::new();
        caller
            .host("127.0.0.1")
            .user("writer")
            .dbname("campaigns")
            .connect_timeout(Duration::from_secs(3600))
            .tcp_user_timeout(Duration::from_secs(3600));
        let bounded = bounded_material_writer_config(&caller).unwrap();
        assert_eq!(bounded.get_user(), caller.get_user());
        assert_eq!(bounded.get_dbname(), caller.get_dbname());
        assert_eq!(
            bounded.get_connect_timeout().copied(),
            Some(WRITER_CONNECT_TIMEOUT)
        );
        assert_eq!(
            bounded.get_tcp_user_timeout().copied(),
            Some(WRITER_TCP_USER_TIMEOUT)
        );
        assert_eq!(bounded.get_options(), Some(WRITER_STARTUP_OPTIONS));
        assert_eq!(caller.get_options(), None);
        crate::postgres_catalog::validate_connection_target(&caller).unwrap();
        assert!(!WRITER_STARTUP_OPTIONS.contains("default_transaction_read_only=on"));
        assert!(WRITER_STARTUP_OPTIONS.contains("-c jit=off"));
    }

    #[test]
    fn caller_startup_options_are_refused_even_when_equal_to_trusted_settings() {
        for options in [
            "-c lock_timeout=0 -c statement_timeout=0",
            WRITER_STARTUP_OPTIONS,
            "",
        ] {
            let mut caller = Config::new();
            caller.host("127.0.0.1").options(options);
            assert!(matches!(
                bounded_material_writer_config(&caller),
                Err(MaterialRuntimeError::Graph(
                    RustPersistenceRuntimeError::CurrentSchema(
                        crate::CurrentSchemaError::ConnectionTarget(_)
                    )
                ))
            ));
            assert_eq!(caller.get_options(), Some(options));
        }
    }

    #[test]
    fn writer_settings_do_not_bypass_the_loopback_target_boundary() {
        let mut caller = Config::new();
        caller.host("192.0.2.1");
        assert!(matches!(
            bounded_material_writer_config(&caller),
            Err(MaterialRuntimeError::Graph(
                RustPersistenceRuntimeError::CurrentSchema(
                    crate::CurrentSchemaError::ConnectionTarget(_)
                )
            ))
        ));
    }

    #[test]
    #[ignore = "requires a bootstrapped local BABYLON_RUNTIME_DSN; reads authority and settings only"]
    fn live_bounded_writer_verifies_authority_and_timeouts_in_read_only_transaction() {
        let raw: Config = std::env::var("BABYLON_RUNTIME_DSN")
            .expect("explicit bootstrapped local runtime target")
            .parse()
            .expect("runtime connection configuration");
        let bounded = bounded_material_writer_config(&raw).unwrap();
        let mut client = bounded.connect(NoTls).expect("bounded writer connection");
        let mut transaction = client
            .build_transaction()
            .read_only(true)
            .start()
            .expect("read-only authority probe");
        verify_runtime_schema_client(&mut transaction)
            .expect("trusted timeout options preserve the active authority check");
        let settings = transaction
            .query_one(
                "SELECT current_setting('statement_timeout')::interval = interval '120 seconds', \
                 current_setting('lock_timeout')::interval = interval '5 seconds', \
                 current_setting('idle_in_transaction_session_timeout')::interval = interval '120 seconds', \
                 current_setting('transaction_read_only') = 'on', \
                 current_setting('jit') = 'off'",
                &[],
            )
            .expect("read bounded connection settings");
        for index in 0..5 {
            assert!(settings.get::<_, bool>(index), "connection setting {index}");
        }
        transaction.rollback().expect("end read-only probe");
        assert_eq!(raw.get_options(), None);
    }
}

#[cfg(test)]
mod diagnostics_tests;

#[cfg(test)]
mod maintenance_tests;

#[cfg(test)]
#[test]
fn foundation_session_shares_the_exact_opening_canonical_allocation() {
    let foundation = crate::michigan_content::MichiganContentPreset::FourWeekStandard
        .create_foundation(&crate::test_support::catalog())
        .unwrap();
    let opening = foundation.initial_register().shared_canonical_bytes();
    let session = foundation.into_session().unwrap();
    let shared = session.material().shared_canonical_bytes();
    assert!(std::sync::Arc::ptr_eq(&opening, &shared));
    assert_eq!(opening.as_slice(), session.material().canonical_bytes());
    assert_eq!(sha256_of(opening.as_slice()), session.material().digest());
}
