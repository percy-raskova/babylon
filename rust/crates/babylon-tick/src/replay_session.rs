//! Database-free execution of fully identified replay ticks.

use std::collections::TryReserveError;

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::allocator_state::AllocatorState;
use babylon_graph::stable_element::{StableElementResolverV1, StableIdentityError};
use babylon_graph::stable_state::{encode_stable_graph_state_v1, StableGraphStateHashV1};
use babylon_graph::state_hash::CanonicalState;
use babylon_graph::substrate::GraphSubstrate;
use babylon_graph::working_copy::DetachedCopy;
use babylon_kernel::{
    ContentDigest, OrderedPracticeActionBatchDigestV1, PreparedEnvironmentDigestV1, RefDigestV1,
    ReplaySeed, ReplaySessionIdV1, TickContentHashError, TickContentHashV1, TickContentPartsV1,
    TickContentPreimageV1,
};
use babylon_practice_contract::{
    OrderedPracticeActionBatchV1, ORDERED_PRACTICE_ACTION_BATCH_V1_LAYOUT_VERSION,
};

use crate::replay_identity::{
    encode_prepared_environment_v1, encode_stable_world_v1, encode_tick_payload_for_prepared_v1,
    encode_world_register_set_v1, world_register_manifest_v1, PreparedEnvironmentV1,
    ReplayTickIdentityError, StableWorldV1, TickPayloadV1, WorldRegisterManifestV1,
    WorldRegisterSetV1,
};
use crate::{prepare_rules, EventRecord, PreparedRules, TickReport};

/// A checked replay-session construction or tick refusal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReplayTickError {
    /// Scenario, declaration, rule, or schedule preparation failed.
    Preparation {
        /// Human-readable preparation refusal.
        message: String,
    },
    /// One detached adjudication or publication stage failed.
    Execution {
        /// Human-readable execution refusal.
        message: String,
    },
    /// The next completed tick could not be represented.
    TickCounterOverflow,
    /// A runtime action batch contained actions, which this gate forbids.
    NonEmptyActionBatch {
        /// Refused number of accepted actions.
        count: usize,
    },
    /// The action batch belonged to another replay session.
    ActionSessionMismatch,
    /// The action batch named a different resolve tick.
    ActionTickMismatch {
        /// Required next resolve tick.
        expected: u64,
        /// Tick carried by the supplied batch.
        actual: u64,
    },
    /// A tick-owned canonical identity refused its semantic input.
    Identity(ReplayTickIdentityError),
    /// Stable graph or resolver identity refused the graph.
    Stable(StableIdentityError),
    /// The fixed outer preimage could not be composed.
    Outer(TickContentHashError),
    /// A bounded report buffer could not reserve its exact capacity.
    Allocation {
        /// Stable buffer name.
        field: &'static str,
        /// Exact requested capacity.
        requested: usize,
    },
    /// A deterministic test composer refused before publication.
    Composer {
        /// Stable injected refusal detail.
        message: String,
    },
}

impl From<ReplayTickIdentityError> for ReplayTickError {
    fn from(value: ReplayTickIdentityError) -> Self {
        Self::Identity(value)
    }
}

impl From<StableIdentityError> for ReplayTickError {
    fn from(value: StableIdentityError) -> Self {
        Self::Stable(value)
    }
}

impl From<TickContentHashError> for ReplayTickError {
    fn from(value: TickContentHashError) -> Self {
        Self::Outer(value)
    }
}

impl std::fmt::Display for ReplayTickError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Preparation { message } => {
                write!(formatter, "replay preparation failed: {message}")
            }
            Self::Execution { message } => write!(formatter, "replay execution failed: {message}"),
            Self::TickCounterOverflow => formatter.write_str("replay tick counter overflowed"),
            Self::NonEmptyActionBatch { count } => {
                write!(
                    formatter,
                    "replay action batch must be empty, got {count} actions"
                )
            }
            Self::ActionSessionMismatch => {
                formatter.write_str("replay action batch session does not match")
            }
            Self::ActionTickMismatch { expected, actual } => write!(
                formatter,
                "replay action batch tick mismatch: expected {expected}, got {actual}"
            ),
            Self::Identity(error) => write!(formatter, "replay identity refused: {error:?}"),
            Self::Stable(error) => write!(formatter, "stable identity refused: {error:?}"),
            Self::Outer(error) => write!(formatter, "tick-content preimage refused: {error:?}"),
            Self::Allocation { field, requested } => {
                write!(formatter, "{field} allocation of {requested} bytes failed")
            }
            Self::Composer { message } => write!(formatter, "replay composer refused: {message}"),
        }
    }
}

impl std::error::Error for ReplayTickError {}

/// Non-durable evidence returned by one successful identified replay tick.
#[derive(Debug)]
pub struct IdentifiedTickReportV1 {
    report: TickReport,
    action_batch_bytes: Vec<u8>,
    action_batch_layout_version: u32,
    action_batch_digest: OrderedPracticeActionBatchDigestV1,
    prior_registers: WorldRegisterSetV1,
    prior_world: StableWorldV1,
    result_registers: WorldRegisterSetV1,
    result_world: StableWorldV1,
    payload: TickPayloadV1,
    outer_preimage: TickContentPreimageV1,
    resolver_manifest_digest: [u8; 32],
    prepared_environment_digest: PreparedEnvironmentDigestV1,
    prior_stable_graph_digest: StableGraphStateHashV1,
    result_stable_graph_digest: StableGraphStateHashV1,
    tick_content_hash: TickContentHashV1,
}

impl IdentifiedTickReportV1 {
    /// Borrow the existing administrative tick evidence.
    #[must_use]
    pub const fn report(&self) -> &TickReport {
        &self.report
    }

    /// Borrow the exact accepted-action batch bytes.
    #[must_use]
    pub fn action_batch_bytes(&self) -> &[u8] {
        &self.action_batch_bytes
    }

    /// Return the accepted-action batch layout version.
    #[must_use]
    pub const fn action_batch_layout_version(&self) -> u32 {
        self.action_batch_layout_version
    }

    /// Return the accepted-action batch digest.
    #[must_use]
    pub const fn action_batch_digest(&self) -> OrderedPracticeActionBatchDigestV1 {
        self.action_batch_digest
    }

    /// Borrow the exact prior register set.
    #[must_use]
    pub const fn prior_registers(&self) -> &WorldRegisterSetV1 {
        &self.prior_registers
    }

    /// Borrow the exact prior stable world.
    #[must_use]
    pub const fn prior_world(&self) -> &StableWorldV1 {
        &self.prior_world
    }

    /// Borrow the exact result register set.
    #[must_use]
    pub const fn result_registers(&self) -> &WorldRegisterSetV1 {
        &self.result_registers
    }

    /// Borrow the exact result stable world.
    #[must_use]
    pub const fn result_world(&self) -> &StableWorldV1 {
        &self.result_world
    }

    /// Borrow the exact governed tick payload.
    #[must_use]
    pub const fn payload(&self) -> &TickPayloadV1 {
        &self.payload
    }

    /// Borrow the exact fixed outer preimage.
    #[must_use]
    pub const fn outer_preimage(&self) -> &TickContentPreimageV1 {
        &self.outer_preimage
    }

    /// Return the sealed resolver-manifest digest.
    #[must_use]
    pub const fn resolver_manifest_digest(&self) -> [u8; 32] {
        self.resolver_manifest_digest
    }

    /// Return the prepared-environment digest.
    #[must_use]
    pub const fn prepared_environment_digest(&self) -> PreparedEnvironmentDigestV1 {
        self.prepared_environment_digest
    }

    /// Return the prior stable-graph digest.
    #[must_use]
    pub const fn prior_stable_graph_digest(&self) -> StableGraphStateHashV1 {
        self.prior_stable_graph_digest
    }

    /// Return the result stable-graph digest.
    #[must_use]
    pub const fn result_stable_graph_digest(&self) -> StableGraphStateHashV1 {
        self.result_stable_graph_digest
    }

    /// Return the authoritative tick-content identity.
    #[must_use]
    pub const fn tick_content_hash(&self) -> TickContentHashV1 {
        self.tick_content_hash
    }
}

/// One loaded replay environment advanced through RNG V2 only.
pub struct ReplayTickSession<G> {
    graph: G,
    prepared: PreparedRules,
    completed_tick: i64,
    session: ReplaySessionIdV1,
    seed: ReplaySeed,
    content: ContentDigest,
    reference: RefDigestV1,
    resolver: StableElementResolverV1,
    register_manifest: WorldRegisterManifestV1,
    prepared_environment: PreparedEnvironmentV1,
}

impl<G: GraphSubstrate + CanonicalState + AllocatorState + DetachedCopy> ReplayTickSession<G> {
    /// Load, verify, and seal one replay environment without executing a tick.
    ///
    /// # Errors
    /// Returns the first preparation, stable-identity, rules-hash, or bounded
    /// canonical-composition refusal.
    #[allow(
        clippy::too_many_arguments,
        reason = "the constructor makes every authoritative replay identity explicit"
    )]
    pub fn new(
        scenario_src: &str,
        prelude_src: Option<&str>,
        rule_src: &str,
        mut graph: G,
        session: ReplaySessionIdV1,
        seed: ReplaySeed,
        content: ContentDigest,
        reference: RefDigestV1,
    ) -> Result<Self, ReplayTickError> {
        let prepared =
            prepare_rules(scenario_src, prelude_src, rule_src, &mut graph).map_err(|error| {
                ReplayTickError::Preparation {
                    message: error.to_string(),
                }
            })?;
        let resolver = StableElementResolverV1::seal(
            &graph,
            &prepared.scenario_scope,
            &prepared.node_content_ids,
            &prepared.hyperedge_content_ids,
        )?;
        let register_manifest = world_register_manifest_v1()?;
        let prepared_environment =
            encode_prepared_environment_v1(&content, &prepared, &resolver, &register_manifest)?;
        Ok(Self {
            graph,
            prepared,
            completed_tick: 0,
            session,
            seed,
            content,
            reference,
            resolver,
            register_manifest,
            prepared_environment,
        })
    }

    /// Execute and atomically publish the next fully identified tick.
    ///
    /// # Errors
    /// Returns the first action, tick, execution, identity, stable-state,
    /// outer-hash, or event-reservation refusal without advancing the session.
    pub fn advance(
        &mut self,
        sink: &mut CollectingSink,
        actions: &OrderedPracticeActionBatchV1,
    ) -> Result<IdentifiedTickReportV1, ReplayTickError> {
        let next_tick = self
            .completed_tick
            .checked_add(1)
            .ok_or(ReplayTickError::TickCounterOverflow)?;
        let execution = ReplayExecutionInputs {
            session: &self.session,
            seed: self.seed,
            content: &self.content,
            reference: self.reference,
            resolver: &self.resolver,
            register_manifest: &self.register_manifest,
            prepared_environment: &self.prepared_environment,
            actions,
            composer: &ProductionReplayIdentityComposer,
        };
        let identified = crate::run_prepared_replay_tick(
            &self.prepared,
            &mut self.graph,
            sink,
            next_tick,
            execution,
        )?;
        self.completed_tick = next_tick;
        Ok(identified)
    }

    /// Return the number of fully published ticks.
    #[must_use]
    pub const fn completed_tick(&self) -> i64 {
        self.completed_tick
    }

    /// Borrow the held graph.
    #[must_use]
    pub const fn graph(&self) -> &G {
        &self.graph
    }

    /// Borrow the session-owned resolver-manifest bytes.
    #[must_use]
    pub fn resolver_manifest_bytes(&self) -> &[u8] {
        self.resolver.manifest().canonical_bytes()
    }

    /// Borrow the session-owned register-manifest bytes.
    #[must_use]
    pub fn register_manifest_bytes(&self) -> &[u8] {
        self.register_manifest.canonical_bytes()
    }

    /// Borrow the session-owned prepared-environment bytes.
    #[must_use]
    pub fn prepared_environment_bytes(&self) -> &[u8] {
        self.prepared_environment.canonical_bytes()
    }
}

pub(crate) struct ReplayPriorIdentityV1 {
    registers: WorldRegisterSetV1,
    world: StableWorldV1,
    stable_graph_digest: StableGraphStateHashV1,
}

pub(crate) struct ReplayExecutionInputs<'a, C> {
    pub(crate) session: &'a ReplaySessionIdV1,
    pub(crate) seed: ReplaySeed,
    pub(crate) content: &'a ContentDigest,
    pub(crate) reference: RefDigestV1,
    pub(crate) resolver: &'a StableElementResolverV1,
    pub(crate) register_manifest: &'a WorldRegisterManifestV1,
    pub(crate) prepared_environment: &'a PreparedEnvironmentV1,
    pub(crate) actions: &'a OrderedPracticeActionBatchV1,
    pub(crate) composer: &'a C,
}

pub(crate) struct ReplayIdentityInputs<'a, G, C> {
    pub(crate) execution: &'a ReplayExecutionInputs<'a, C>,
    pub(crate) prepared: &'a PreparedRules,
    pub(crate) prior: ReplayPriorIdentityV1,
    pub(crate) result_graph: &'a G,
    pub(crate) report: &'a TickReport,
    pub(crate) events: &'a [EventRecord],
    pub(crate) resolve_tick: i64,
}

pub(crate) trait ReplayIdentityComposer {
    fn compose<G: CanonicalState>(
        &self,
        inputs: ReplayIdentityInputs<'_, G, Self>,
    ) -> Result<ReplayIdentityArtifactsV1, ReplayTickError>
    where
        Self: Sized;
}

pub(crate) struct ProductionReplayIdentityComposer;

impl ReplayIdentityComposer for ProductionReplayIdentityComposer {
    fn compose<G: CanonicalState>(
        &self,
        inputs: ReplayIdentityInputs<'_, G, Self>,
    ) -> Result<ReplayIdentityArtifactsV1, ReplayTickError> {
        compose_replay_identity(inputs)
    }
}

pub(crate) struct ReplayIdentityArtifactsV1 {
    action_batch_bytes: Vec<u8>,
    action_batch_layout_version: u32,
    action_batch_digest: OrderedPracticeActionBatchDigestV1,
    prior_registers: WorldRegisterSetV1,
    prior_world: StableWorldV1,
    result_registers: WorldRegisterSetV1,
    result_world: StableWorldV1,
    payload: TickPayloadV1,
    outer_preimage: TickContentPreimageV1,
    resolver_manifest_digest: [u8; 32],
    prepared_environment_digest: PreparedEnvironmentDigestV1,
    prior_stable_graph_digest: StableGraphStateHashV1,
    result_stable_graph_digest: StableGraphStateHashV1,
    tick_content_hash: TickContentHashV1,
}

pub(crate) fn validate_replay_actions<C>(
    execution: &ReplayExecutionInputs<'_, C>,
    resolve_tick: i64,
) -> Result<u64, ReplayTickError> {
    let resolve_tick =
        u64::try_from(resolve_tick).map_err(|_| ReplayTickError::TickCounterOverflow)?;
    if !execution.actions.is_empty() {
        return Err(ReplayTickError::NonEmptyActionBatch {
            count: execution.actions.items().len(),
        });
    }
    if execution.actions.session() != execution.session {
        return Err(ReplayTickError::ActionSessionMismatch);
    }
    if execution.actions.resolve_tick() != resolve_tick {
        return Err(ReplayTickError::ActionTickMismatch {
            expected: resolve_tick,
            actual: execution.actions.resolve_tick(),
        });
    }
    Ok(resolve_tick)
}

pub(crate) fn compose_replay_prior<G: CanonicalState, C>(
    graph: &G,
    execution: &ReplayExecutionInputs<'_, C>,
    completed_tick: i64,
) -> Result<ReplayPriorIdentityV1, ReplayTickError> {
    let stable_graph = encode_stable_graph_state_v1(graph, execution.resolver)?;
    let stable_graph_digest = stable_graph.digest();
    let registers = encode_world_register_set_v1(execution.register_manifest, completed_tick)?;
    let world = encode_stable_world_v1(&stable_graph, &registers)?;
    drop(stable_graph);
    Ok(ReplayPriorIdentityV1 {
        registers,
        world,
        stable_graph_digest,
    })
}

fn compose_replay_identity<G: CanonicalState>(
    inputs: ReplayIdentityInputs<'_, G, ProductionReplayIdentityComposer>,
) -> Result<ReplayIdentityArtifactsV1, ReplayTickError> {
    let result_graph =
        encode_stable_graph_state_v1(inputs.result_graph, inputs.execution.resolver)?;
    let result_stable_graph_digest = result_graph.digest();
    let result_registers =
        encode_world_register_set_v1(inputs.execution.register_manifest, inputs.resolve_tick)?;
    let result_world = encode_stable_world_v1(&result_graph, &result_registers)?;
    drop(result_graph);
    let payload = encode_tick_payload_for_prepared_v1(
        inputs.prepared,
        &inputs.report.per_rule_fired,
        inputs.report.fired,
        inputs.events,
        &inputs.report.audit_receipts,
        inputs.execution.resolver,
    )?;
    let outer_preimage = compose_outer_preimage(&inputs, &result_world, &payload)?;
    let tick_content_hash = outer_preimage.digest();
    let action_batch_bytes = copy_action_bytes(inputs.execution.actions.canonical_bytes())?;
    Ok(ReplayIdentityArtifactsV1 {
        action_batch_bytes,
        action_batch_layout_version: ORDERED_PRACTICE_ACTION_BATCH_V1_LAYOUT_VERSION,
        action_batch_digest: inputs.execution.actions.digest(),
        prior_registers: inputs.prior.registers,
        prior_world: inputs.prior.world,
        result_registers,
        result_world,
        payload,
        outer_preimage,
        resolver_manifest_digest: inputs.execution.resolver.manifest().digest(),
        prepared_environment_digest: inputs.execution.prepared_environment.digest(),
        prior_stable_graph_digest: inputs.prior.stable_graph_digest,
        result_stable_graph_digest,
        tick_content_hash,
    })
}

fn compose_outer_preimage<G, C>(
    inputs: &ReplayIdentityInputs<'_, G, C>,
    result_world: &StableWorldV1,
    payload: &TickPayloadV1,
) -> Result<TickContentPreimageV1, ReplayTickError> {
    let resolve_tick =
        u64::try_from(inputs.resolve_tick).map_err(|_| ReplayTickError::TickCounterOverflow)?;
    Ok(TickContentPreimageV1::compose(&TickContentPartsV1 {
        session: inputs.execution.session,
        resolve_tick,
        seed: inputs.execution.seed,
        content: inputs.execution.content,
        reference: inputs.execution.reference,
        prepared: inputs.execution.prepared_environment.digest(),
        prior_world: inputs.prior.world.digest(),
        actions: inputs.execution.actions.digest(),
        result_world: result_world.digest(),
        payload: payload.digest(),
    })?)
}

fn copy_action_bytes(source: &[u8]) -> Result<Vec<u8>, ReplayTickError> {
    let mut bytes = Vec::new();
    bytes
        .try_reserve_exact(source.len())
        .map_err(|_: TryReserveError| ReplayTickError::Allocation {
            field: "identified action batch bytes",
            requested: source.len(),
        })?;
    bytes.extend_from_slice(source);
    Ok(bytes)
}

pub(crate) fn identified_report(
    report: TickReport,
    artifacts: ReplayIdentityArtifactsV1,
) -> IdentifiedTickReportV1 {
    IdentifiedTickReportV1 {
        report,
        action_batch_bytes: artifacts.action_batch_bytes,
        action_batch_layout_version: artifacts.action_batch_layout_version,
        action_batch_digest: artifacts.action_batch_digest,
        prior_registers: artifacts.prior_registers,
        prior_world: artifacts.prior_world,
        result_registers: artifacts.result_registers,
        result_world: artifacts.result_world,
        payload: artifacts.payload,
        outer_preimage: artifacts.outer_preimage,
        resolver_manifest_digest: artifacts.resolver_manifest_digest,
        prepared_environment_digest: artifacts.prepared_environment_digest,
        prior_stable_graph_digest: artifacts.prior_stable_graph_digest,
        result_stable_graph_digest: artifacts.result_stable_graph_digest,
        tick_content_hash: artifacts.tick_content_hash,
    }
}

#[cfg(test)]
mod tests {
    use babylon_bsl::rule_pipeline::split_content;
    use babylon_bsl::rules_hash_of;
    use babylon_graph::memory::MemoryGraph;
    use babylon_graph::state_hash::CanonicalState;
    use babylon_graph::substrate::GraphSubstrate;
    use babylon_kernel::{ContentDigest, RefDigestV1, ReplaySeed, ReplaySessionIdV1};
    use babylon_practice_contract::OrderedPracticeActionBatchV1;

    use super::{
        ReplayExecutionInputs, ReplayIdentityArtifactsV1, ReplayIdentityComposer,
        ReplayIdentityInputs, ReplayTickError, ReplayTickSession,
    };
    use crate::{EventRecord, PreparedEventBatchSink};

    const SCENARIO: &str = include_str!("../content/scenarios/two-classes.bscn");
    const RULE: &str = include_str!("../content/rules/fundamental-theorem.bsl");

    fn session() -> ReplayTickSession<MemoryGraph> {
        let replay = ReplaySessionIdV1::try_from("per60/atomic").unwrap();
        let (_, rules) = split_content(RULE).unwrap();
        let forms = rules.into_iter().map(|(_, form)| form).collect::<Vec<_>>();
        ReplayTickSession::new(
            SCENARIO,
            None,
            RULE,
            MemoryGraph::new(),
            replay,
            ReplaySeed::new(17),
            ContentDigest {
                defines_hash: [0x31; 32],
                rules_hash: rules_hash_of(&forms).unwrap(),
            },
            RefDigestV1::from_bytes([0x42; 32]),
        )
        .unwrap()
    }

    struct RefusingComposer;

    impl ReplayIdentityComposer for RefusingComposer {
        fn compose<G: CanonicalState>(
            &self,
            _inputs: ReplayIdentityInputs<'_, G, Self>,
        ) -> Result<ReplayIdentityArtifactsV1, ReplayTickError> {
            Err(ReplayTickError::Composer {
                message: "injected identity reservation refusal".to_owned(),
            })
        }
    }

    #[derive(Default)]
    struct RefusingSink {
        prepare_attempts: usize,
        commit_attempts: usize,
    }

    impl PreparedEventBatchSink for RefusingSink {
        fn try_prepare(&mut self, _additional: usize) -> Result<(), String> {
            self.prepare_attempts += 1;
            Err("injected replay event reservation refusal".to_owned())
        }

        fn commit_prepared(&mut self, _events: Vec<EventRecord>) {
            self.commit_attempts += 1;
        }
    }

    #[test]
    fn topology_change_refuses_without_advancing_or_reverting_the_external_change() {
        let mut session = session();
        session.graph.add_node("DYNAMIC").unwrap();
        let before = session.graph.encode_state().unwrap().as_bytes().to_vec();
        let actions = OrderedPracticeActionBatchV1::empty(session.session.clone(), 1).unwrap();
        let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();

        assert!(matches!(
            session.advance(&mut sink, &actions),
            Err(ReplayTickError::Stable(_))
        ));
        assert_eq!(session.completed_tick, 0);
        assert!(sink.events.is_empty());
        assert_eq!(session.graph.encode_state().unwrap().as_bytes(), before);
    }

    #[test]
    fn composer_refusal_leaves_graph_events_and_counter_unpublished() {
        let mut session = session();
        let before = session.graph.encode_state().unwrap().as_bytes().to_vec();
        let actions = OrderedPracticeActionBatchV1::empty(session.session.clone(), 1).unwrap();
        let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();
        let execution = ReplayExecutionInputs {
            session: &session.session,
            seed: session.seed,
            content: &session.content,
            reference: session.reference,
            resolver: &session.resolver,
            register_manifest: &session.register_manifest,
            prepared_environment: &session.prepared_environment,
            actions: &actions,
            composer: &RefusingComposer,
        };

        let error = crate::run_prepared_replay_tick(
            &session.prepared,
            &mut session.graph,
            &mut sink,
            1,
            execution,
        )
        .unwrap_err();
        assert!(matches!(error, ReplayTickError::Composer { .. }));
        assert_eq!(session.completed_tick, 0);
        assert!(sink.events.is_empty());
        assert_eq!(session.graph.encode_state().unwrap().as_bytes(), before);
    }

    #[test]
    fn event_reservation_refuses_after_identity_and_before_graph_publication() {
        let mut session = session();
        let before = session.graph.encode_state().unwrap().as_bytes().to_vec();
        let actions = OrderedPracticeActionBatchV1::empty(session.session.clone(), 1).unwrap();
        let composer = super::ProductionReplayIdentityComposer;
        let execution = ReplayExecutionInputs {
            session: &session.session,
            seed: session.seed,
            content: &session.content,
            reference: session.reference,
            resolver: &session.resolver,
            register_manifest: &session.register_manifest,
            prepared_environment: &session.prepared_environment,
            actions: &actions,
            composer: &composer,
        };
        let mut sink = RefusingSink::default();
        let result = crate::run_prepared_tick_transaction(
            &session.prepared,
            &mut session.graph,
            &mut sink,
            &crate::ExecutionIdentity::Replay(execution),
            1,
            |_boundary, graph: &MemoryGraph| graph.state_hash(),
        );

        assert!(result.is_err());
        assert_eq!(sink.prepare_attempts, 1);
        assert_eq!(sink.commit_attempts, 0);
        assert_eq!(session.completed_tick, 0);
        assert_eq!(session.graph.encode_state().unwrap().as_bytes(), before);
    }

    #[test]
    fn completed_tick_overflow_refuses_before_action_or_graph_work() {
        let mut session = session();
        session.completed_tick = i64::MAX;
        session
            .graph
            .update_node(
                babylon_graph::substrate::NodeId(0),
                "social-class/wages",
                f64::NAN,
            )
            .unwrap();
        let actions = OrderedPracticeActionBatchV1::empty(session.session.clone(), 1).unwrap();
        let mut sink = babylon_bsl::structural_verbs::CollectingSink::default();

        assert!(matches!(
            session.advance(&mut sink, &actions),
            Err(ReplayTickError::TickCounterOverflow)
        ));
        assert_eq!(session.completed_tick, i64::MAX);
        assert!(sink.events.is_empty());
    }
}
