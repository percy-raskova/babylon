//! `TickSession` — the persistent load-once, advance-many seam B2 needs,
//! now multi-rule (Phase A, Tasks 2-4). `run_once`/`run_once_into`
//! (`lib.rs`) model one tick end to end and hardcode `run_tick`'s tick
//! argument to `1` for every rule the content set holds; a player-driven
//! loop needs the split this type provides instead: parse and load cost
//! paid ONCE in `new`, the SAME `PreparedRules` and the SAME graph reused
//! by every `advance()` call, every rule in the content set run once per
//! call in the governed 34-slot causal order, with `tick` incremented by
//! this type. D16's ascending rule-ID byte order breaks ties at one resolved
//! position.

use crate::{prepare_rules, run_prepared_tick, PreparedRules, TickReport};
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::allocator_state::AllocatorState;
use babylon_graph::state_hash::CanonicalState;
use babylon_graph::substrate::GraphSubstrate;
use babylon_graph::working_copy::DetachedCopy;
use babylon_kernel::SessionId;

/// One content set, loaded once, advanced tick by tick against ONE held
/// graph. `G` is caller-supplied (same shape as `run_once_into`) so the
/// caller picks the substrate — production callers pass `HypergraphStore`
/// (ADR193).
pub struct TickSession<G> {
    graph: G,
    prepared: PreparedRules,
    tick: i64,
    /// The `rng-draw` seam's session id (Task 4, #576 intrinsic-host train,
    /// plan §3.5) — constant for this session's whole lifetime, unlike
    /// `tick`, which `advance()` increments. `advance()` passes `&session`
    /// into every rule's `run_tick` call, unchanged, every call.
    session: SessionId,
}

impl<G: GraphSubstrate + CanonicalState + AllocatorState + DetachedCopy> TickSession<G> {
    /// Parse `rule_src` (one or more `(rule …)` forms) and load
    /// `scenario_src` into `graph` once. `prepare_rules` compiles the forms
    /// into governed phase order before this returns — the caller's own
    /// concatenation order is never observable.
    ///
    /// `session` is this session's `rng-draw` identity (plan §3.5) — a
    /// caller-supplied, deterministic id (III.7: never a UUID, never a
    /// wall-clock read). Picking the campaign's REAL session id (a
    /// `ContentDigest` hex, or the scenario id) is a separate, small
    /// recorded decision (plan §3.5, Task 6.5); this parameter is the seam
    /// that decision lands through, not a policy of its own.
    ///
    /// # Errors
    /// The same failure modes `run_once_into`'s load half has: an
    /// intrinsic declaration, a scenario load, or a rule load — named to
    /// its own rule id when more than one rule is present.
    pub fn new(
        scenario_src: &str,
        rule_src: &str,
        mut graph: G,
        session: SessionId,
    ) -> Result<Self, String> {
        // Train B item 4 (#591, D157): no prelude — `Self::new_with_prelude`
        // (below) is the prelude-threaded sibling.
        let prepared =
            prepare_rules(scenario_src, None, rule_src, &mut graph).map_err(|e| e.to_string())?;
        Ok(Self {
            graph,
            prepared,
            tick: 0,
            session,
        })
    }

    /// `Self::new`, with the scenario load routed through a **declaration
    /// prelude** first (Train B item 4, issue #591, D157) — see
    /// `babylon_bsl::scenario::load_scenario_with_prelude`'s own doc for the
    /// mechanism. Added alongside `Self::new` because
    /// `consciousness_ternary_conformance.rs`'s `tick_two_accumulation_witness`
    /// is a REAL consumer, not speculative surface: once
    /// `consciousness-ternary-conformance.bscn` stopped re-declaring
    /// `WorldView` itself (this train), that test's `TickSession::new` call
    /// needed a prelude too.
    ///
    /// # Errors
    /// The same failure modes `Self::new` has, plus the prelude's own (a
    /// non-declaration top-form, or an unreadable prelude source).
    pub fn new_with_prelude(
        scenario_src: &str,
        prelude_src: &str,
        rule_src: &str,
        mut graph: G,
        session: SessionId,
    ) -> Result<Self, String> {
        let prepared = prepare_rules(scenario_src, Some(prelude_src), rule_src, &mut graph)
            .map_err(|e| e.to_string())?;
        Ok(Self {
            graph,
            prepared,
            tick: 0,
            session,
        })
    }

    /// Run one more tick against the held graph: every rule in the
    /// content set in the governed phase order compiled once at load time
    /// by `prepare_rules`. D16 orders same-position ties by rule-ID bytes.
    /// Each rule runs to completion before the next starts against the same
    /// disposable working graph, so a later rule sees an earlier rule's
    /// writes from this tick. The working graph and its buffered events are
    /// published together only after every rule and hash succeeds.
    ///
    /// **This is a RECORDED GAP, not a design feature.** §4.2 says "rules
    /// within one system position observe the same pre-state"
    /// (bsl-language.rst §4.2), which covers rule-to-rule pre-state
    /// sharing, not only subject-to-subject within one rule. Task 12
    /// (D-row Q1) repaired the within-rule half (`run_tick`'s
    /// collect-then-apply split); this cross-rule half is a separate,
    /// still-open divergence — D-row Q14 (the query-evaluation plan's
    /// draft-ruling register). It is live and observable in multi-rule packs
    /// that exchange same-position writes. PER-17 preserves that behavior;
    /// repairing it needs explicit content dispositions and behavioral
    /// contracts. The first call runs tick 1 (matching `run_once`'s own
    /// numbering), the second tick 2, and so on.
    ///
    /// # Errors
    /// The tick itself (named to its own rule id), or a pre/post
    /// schedule/world/graph hash failure, event reservation failure, or a
    /// checked tick-counter overflow. On any error the graph, caller's
    /// existing events, and session counter stay unchanged — `tick()` counts
    /// completed ticks only.
    pub fn advance(&mut self, sink: &mut CollectingSink) -> Result<TickReport, String> {
        let next_tick = self
            .tick
            .checked_add(1)
            .ok_or_else(|| "tick counter overflow before adjudication".to_owned())?;
        let report = run_prepared_tick(
            &self.prepared,
            &mut self.graph,
            sink,
            &self.session,
            next_tick,
        )?;
        self.tick = next_tick;
        Ok(report)
    }

    /// The current tick number — 0 before the first `advance()` call.
    #[must_use]
    pub fn tick(&self) -> i64 {
        self.tick
    }

    /// Read-only access to the held graph — the client's map lens and
    /// state panel project live state through this.
    #[must_use]
    pub fn graph(&self) -> &G {
        &self.graph
    }
}

#[cfg(test)]
mod tests {
    use crate::session::TickSession;
    use crate::{run_prepared_tick_with, EventRecord, HashBoundary, PreparedEventBatchSink};
    use babylon_bsl::structural_verbs::CollectingSink;
    use babylon_graph::allocator_state::AllocatorState;
    use babylon_graph::hypergraph_store::HypergraphStore;
    use babylon_graph::memory::MemoryGraph;
    use babylon_graph::state_hash::{CanonicalState, StateEncoder};
    use babylon_graph::substrate::{GraphError, GraphSubstrate, NodeId};
    use babylon_graph::working_copy::DetachedCopy;
    use babylon_kernel::SessionId;
    use std::process::Command;

    const SCENARIO: &str =
        include_str!("../content/scenarios/vitality-lifecycle-combined-conformance.bscn");
    const VITALITY: &str = include_str!("../content/rules/vitality.bsl");
    const LIFECYCLE: &str = include_str!("../content/rules/lifecycle.bsl");

    const ATOMICITY_SCENARIO: &str = r"
(scenario tick/atomicity-probe
  (defvocabulary NodeType (SOCIAL_CLASS))
  (deffield social-class/probability probability intensive)
  (node first NodeType/SOCIAL_CLASS (social-class/probability 0.1p))
  (node second NodeType/SOCIAL_CLASS (social-class/probability 0.9p)))
";
    const ATOMICITY_RULE: &str = r#"(rule vitality/atomicity-probe
  :material-basis "PER-18 E-EVAL-020 rollback probe: one legal write precedes one illegal write"
  :fuel 64
  (bindings (binding probability :field social-class/probability))
  (when (> probability 0.0p))
  (effects
    (emit EventType/PROBE)
    (update-node self social-class/probability (add 0.4i))))"#;

    const CLOCK_SCENARIO: &str = r"
(scenario tick/world-clock-probe
  (defvocabulary NodeType (SOCIAL_CLASS))
  (deffield social-class/active int intensive)
  (node only NodeType/SOCIAL_CLASS (social-class/active 1)))
";
    const CLOCK_RULE: &str = r#"(rule vitality/world-clock-probe
  :material-basis "PER-18 nominal world hash probe: elapsed committed time is world state"
  :fuel 32
  (bindings (binding active :field social-class/active))
  (when (= active 1))
  (effects (emit EventType/PROBE)))"#;

    const PHASE_FAULT_SCENARIO: &str = r"
(scenario tick/phase-fault-matrix
  (defvocabulary NodeType (SOCIAL_CLASS))
  (deffield social-class/probability probability intensive)
  (deffield social-class/base int extensive)
  (deffield social-class/action int extensive)
  (node first NodeType/SOCIAL_CLASS
    (social-class/probability 0.1p)
    (social-class/base 0)
    (social-class/action 0))
  (node second NodeType/SOCIAL_CLASS
    (social-class/probability 0.9p)
    (social-class/base 0)
    (social-class/action 0)))
";
    const MATERIAL_SUCCESS_RULE: &str = r#"(rule vitality/phase-success
  :material-basis "PER-18 rollback matrix: representative Material Base work"
  :fuel 64
  (bindings (binding value :field social-class/base))
  (when (>= value 0))
  (effects
    (emit EventType/MATERIAL_WORK)
    (update-node self social-class/base (add 1))))"#;
    const ACTION_SUCCESS_RULE: &str = r#"(rule ooda/phase-success
  :material-basis "PER-18 rollback matrix: representative Action work"
  :fuel 64
  (bindings (binding value :field social-class/action))
  (when (>= value 0))
  (effects
    (emit EventType/ACTION_WORK)
    (update-node self social-class/action (add 1))))"#;
    const MATERIAL_FAILURE_RULE: &str = r#"(rule metabolism/phase-failure
  :material-basis "PER-18 rollback matrix: fail at the end of Material Base"
  :fuel 64
  (bindings (binding probability :field social-class/probability))
  (when (> probability 0.0p))
  (effects
    (emit EventType/MATERIAL_FAILURE)
    (update-node self social-class/probability (add 0.4i))))"#;
    const ACTION_FAILURE_RULE: &str = r#"(rule ooda/phase-failure
  :material-basis "PER-18 rollback matrix: fail after Material Base"
  :fuel 64
  (bindings (binding probability :field social-class/probability))
  (when (> probability 0.0p))
  (effects
    (emit EventType/ACTION_FAILURE)
    (update-node self social-class/probability (add 0.4i))))"#;
    const CONSEQUENCE_FAILURE_RULE: &str = r#"(rule epistemic-horizon/phase-failure
  :material-basis "PER-18 rollback matrix: fail after Material Base and Action"
  :fuel 64
  (bindings (binding probability :field social-class/probability))
  (when (> probability 0.0p))
  (effects
    (emit EventType/CONSEQUENCE_FAILURE)
    (update-node self social-class/probability (add 0.4i))))"#;

    const HASH_FAILURE_SCENARIO: &str = r"
(scenario tick/hash-failure
  (defvocabulary NodeType (SOCIAL_CLASS))
  (deffield social-class/count int extensive)
  (node only NodeType/SOCIAL_CLASS (social-class/count 1)))
";
    const HASH_FAILURE_RULE: &str = r#"(rule vitality/hash-failure
  :material-basis "PER-18 hash-boundary rollback mutates before the post hash"
  :fuel 32
  (bindings (binding count :field social-class/count))
  (when (= count 1))
  (effects
    (emit EventType/HASH_WORK)
    (update-node self social-class/count (add 1))))"#;

    const ENVELOPE_SCENARIO: &str = r"
(scenario tick/process-envelope
  (defvocabulary NodeType (SOCIAL_CLASS))
  (deffield social-class/material int extensive)
  (deffield social-class/action int extensive)
  (node subject NodeType/SOCIAL_CLASS
    (social-class/material 1)
    (social-class/action 10)))
";
    const ENVELOPE_RULES: &str = r#"(rule ooda/envelope-action
  :material-basis "PER-18 real envelope proof: Action rule"
  :fuel 32
  (bindings (binding action :field social-class/action))
  (when (= action 10))
  (effects
    (emit EventType/ACTION_ENVELOPE)
    (update-node self social-class/action (add 2))))

(rule vitality/envelope-material
  :material-basis "PER-18 real envelope proof: Material Base rule"
  :fuel 32
  (bindings (binding material :field social-class/material))
  (when (= material 1))
  (effects
    (emit EventType/MATERIAL_ENVELOPE)
    (update-node self social-class/material (add 1))))"#;

    const ENVELOPE_CHILD_ENV: &str = "BABYLON_PER18_TICK_ENVELOPE_CHILD";
    const ENVELOPE_MARKER: &str = "PER18_TICK_ENVELOPE=";

    fn rule_src() -> String {
        format!("{VITALITY}\n{LIFECYCLE}")
    }

    /// The `rng-draw` seam's session id (Task 4, #576 intrinsic-host train)
    /// for this module's own tests — a fixed literal, since none of them
    /// exercise `rng-draw` (Task 5 lands it) and III.7 forbids a UUID/
    /// wall-clock one anyway.
    fn test_session() -> SessionId {
        SessionId::new("tick-session-test").expect("literal is non-empty")
    }

    #[derive(Default)]
    struct RejectingBatchSink {
        prepare_attempts: usize,
        commit_attempts: usize,
    }

    impl PreparedEventBatchSink for RejectingBatchSink {
        fn try_prepare(&mut self, _additional: usize) -> Result<(), String> {
            self.prepare_attempts += 1;
            Err("injected event publication refusal".to_owned())
        }

        fn commit_prepared(&mut self, _events: Vec<EventRecord>) {
            self.commit_attempts += 1;
        }
    }

    #[test]
    fn rejecting_event_publication_happens_before_graph_publication() {
        let mut session = TickSession::new(
            CLOCK_SCENARIO,
            CLOCK_RULE,
            HypergraphStore::new(),
            test_session(),
        )
        .expect("the event publication probe loads");
        let before = session.graph.encode_state().unwrap().as_bytes().to_vec();
        let cursors = session.graph.allocator_cursors();
        let mut publisher = RejectingBatchSink::default();

        let error = run_prepared_tick_with(
            &session.prepared,
            &mut session.graph,
            &mut publisher,
            &session.session,
            1,
            |_boundary: HashBoundary, graph: &HypergraphStore| graph.state_hash(),
        )
        .expect_err("publication is injected to fail");

        assert_eq!(error, "injected event publication refusal");
        assert_eq!(publisher.prepare_attempts, 1);
        assert_eq!(publisher.commit_attempts, 0);
        assert_eq!(session.tick, 0);
        assert_eq!(session.graph.encode_state().unwrap().as_bytes(), before);
        assert_eq!(session.graph.allocator_cursors(), cursors);
    }

    fn assert_phase_fault_rolls_back<G>(rules: &str)
    where
        G: GraphSubstrate + CanonicalState + AllocatorState + DetachedCopy + Default,
    {
        let mut session =
            TickSession::new(PHASE_FAULT_SCENARIO, rules, G::default(), test_session())
                .expect("the phase fault fixture loads");
        let before = session.graph().encode_state().unwrap().as_bytes().to_vec();
        let cursors = session.graph().allocator_cursors();
        let completed_tick = session.tick();
        let mut sink = CollectingSink {
            events: vec![("EventType/PRIOR".to_owned(), Vec::new())],
        };
        let prior_events = sink.events.clone();

        let error = session
            .advance(&mut sink)
            .expect_err("the second probability write exceeds one");

        assert!(error.contains("E-EVAL-020"), "{error}");
        assert_eq!(session.graph().encode_state().unwrap().as_bytes(), before);
        assert_eq!(session.graph().allocator_cursors(), cursors);
        assert_eq!(session.tick(), completed_tick);
        assert_eq!(sink.events, prior_events);
    }

    #[test]
    fn rollback_covers_material_action_and_consequence_faults_on_both_backends() {
        let material = format!("{MATERIAL_SUCCESS_RULE}\n{MATERIAL_FAILURE_RULE}");
        let action = format!("{MATERIAL_SUCCESS_RULE}\n{ACTION_FAILURE_RULE}");
        let consequence =
            format!("{MATERIAL_SUCCESS_RULE}\n{ACTION_SUCCESS_RULE}\n{CONSEQUENCE_FAILURE_RULE}");

        assert_phase_fault_rolls_back::<MemoryGraph>(&material);
        assert_phase_fault_rolls_back::<HypergraphStore>(&material);
        assert_phase_fault_rolls_back::<MemoryGraph>(&action);
        assert_phase_fault_rolls_back::<HypergraphStore>(&action);
        assert_phase_fault_rolls_back::<MemoryGraph>(&consequence);
        assert_phase_fault_rolls_back::<HypergraphStore>(&consequence);
    }

    fn assert_hash_fault_rolls_back<H>(mut state_hash: H, expected: &str)
    where
        H: FnMut(HashBoundary, &HypergraphStore) -> Result<[u8; 32], GraphError>,
    {
        let mut session = TickSession::new(
            HASH_FAILURE_SCENARIO,
            HASH_FAILURE_RULE,
            HypergraphStore::new(),
            test_session(),
        )
        .expect("the hash fault fixture loads");
        let before = session.graph.encode_state().unwrap().as_bytes().to_vec();
        let cursors = session.graph.allocator_cursors();
        let mut sink = CollectingSink {
            events: vec![("EventType/PRIOR".to_owned(), Vec::new())],
        };
        let events = sink.events.clone();

        let error = run_prepared_tick_with(
            &session.prepared,
            &mut session.graph,
            &mut sink,
            &session.session,
            1,
            &mut state_hash,
        )
        .expect_err("the selected hash boundary refuses");

        assert!(error.contains(expected), "{error}");
        assert_eq!(session.graph.encode_state().unwrap().as_bytes(), before);
        assert_eq!(session.graph.allocator_cursors(), cursors);
        assert_eq!(session.tick, 0);
        assert_eq!(sink.events, events);
    }

    #[test]
    fn pre_hash_failure_leaves_the_whole_tick_unpublished() {
        assert_hash_fault_rolls_back(
            |boundary, graph| match boundary {
                HashBoundary::Pre => Err(GraphError {
                    message: "injected pre-hash refusal".to_owned(),
                }),
                HashBoundary::Post => graph.state_hash(),
            },
            "pre-tick state: injected pre-hash refusal",
        );
    }

    #[test]
    fn post_hash_nan_failure_leaves_the_whole_tick_unpublished() {
        assert_hash_fault_rolls_back(
            |boundary, graph| match boundary {
                HashBoundary::Pre => graph.state_hash(),
                HashBoundary::Post => {
                    let mut encoder = StateEncoder::new();
                    encoder.write_attributes(&[(
                        NodeId(99),
                        "fault/non-finite".to_owned(),
                        f64::NAN,
                    )])?;
                    Ok(encoder.finish())
                }
            },
            "post-tick state: attribute fault/non-finite on NodeId(99) is NaN",
        );
    }

    #[derive(Debug, PartialEq)]
    struct TickEnvelopeProof {
        before: [u8; 32],
        after: [u8; 32],
        world_before: [u8; 32],
        world_after: [u8; 32],
        per_rule_fired: Vec<(String, usize)>,
        events: Vec<EventRecord>,
    }

    impl TickEnvelopeProof {
        fn canonical_text(&self) -> String {
            let rules = self
                .per_rule_fired
                .iter()
                .map(|(id, fired)| format!("{id}={fired}"))
                .collect::<Vec<_>>()
                .join(",");
            let events = self
                .events
                .iter()
                .map(|(kind, payload)| format!("{kind}#{}", payload.len()))
                .collect::<Vec<_>>()
                .join(",");
            format!(
                "graph-before={};graph-after={};world-before={};world-after={};rules={rules};events={events}",
                crate::hex(&self.before),
                crate::hex(&self.after),
                crate::hex(&self.world_before),
                crate::hex(&self.world_after),
            )
        }
    }

    fn envelope_prestate<G>(reverse_writes: bool) -> G
    where
        G: GraphSubstrate + Default,
    {
        let mut graph = G::default();
        let territory = graph.add_node("TERRITORY").unwrap();
        let organization = graph.add_node("ORGANIZATION").unwrap();
        if reverse_writes {
            graph
                .update_node(organization, "organization/power", 0.625)
                .unwrap();
            graph
                .update_node(territory, "territory/pressure", 0.125)
                .unwrap();
            graph
                .add_hyperedge("PRESENCE_GROUP", &[organization, territory])
                .unwrap();
            graph
                .add_edge("PRESENCE", organization, territory, 0.75)
                .unwrap();
        } else {
            graph
                .add_edge("PRESENCE", organization, territory, 0.75)
                .unwrap();
            graph
                .add_hyperedge("PRESENCE_GROUP", &[territory, organization])
                .unwrap();
            graph
                .update_node(territory, "territory/pressure", 0.125)
                .unwrap();
            graph
                .update_node(organization, "organization/power", 0.625)
                .unwrap();
        }
        graph
    }

    fn run_tick_envelope<G>(reverse_writes: bool) -> TickEnvelopeProof
    where
        G: GraphSubstrate + CanonicalState + AllocatorState + DetachedCopy + Default,
    {
        let graph = envelope_prestate::<G>(reverse_writes);
        let mut session = TickSession::new(
            ENVELOPE_SCENARIO,
            ENVELOPE_RULES,
            graph,
            SessionId::new("per18-envelope").unwrap(),
        )
        .expect("the real multi-rule envelope fixture loads");
        let mut sink = CollectingSink::default();
        let report = session.advance(&mut sink).expect("the real tick commits");
        let expected_events = vec![
            ("MATERIAL_ENVELOPE".to_owned(), Vec::new()),
            ("ACTION_ENVELOPE".to_owned(), Vec::new()),
        ];
        assert_eq!(
            report.per_rule_fired,
            vec![
                ("vitality/envelope-material".to_owned(), 1),
                ("ooda/envelope-action".to_owned(), 1),
            ]
        );
        assert_eq!(sink.events, expected_events);
        TickEnvelopeProof {
            before: report.before,
            after: report.after,
            world_before: report.world_before,
            world_after: report.world_after,
            per_rule_fired: report.per_rule_fired,
            events: sink.events,
        }
    }

    fn child_tick_envelope(mode: &str) -> String {
        let executable = std::env::current_exe().expect("the test executable has a path");
        let output = Command::new(executable)
            .env(ENVELOPE_CHILD_ENV, mode)
            .args([
                "--exact",
                "session::tests::real_tick_envelope_child_probe",
                "--nocapture",
            ])
            .output()
            .expect("the child test process starts");
        let stdout = String::from_utf8(output.stdout).expect("child stdout is UTF-8");
        let stderr = String::from_utf8(output.stderr).expect("child stderr is UTF-8");
        assert!(
            output.status.success(),
            "child process failed\nstdout: {stdout}\nstderr: {stderr}"
        );
        stdout
            .lines()
            .find_map(|line| line.strip_prefix(ENVELOPE_MARKER))
            .expect("child stdout carries the real tick envelope marker")
            .to_owned()
    }

    #[test]
    fn real_tick_envelope_child_probe() {
        let Some(mode) = std::env::var_os(ENVELOPE_CHILD_ENV) else {
            return;
        };
        let mode = mode.to_string_lossy();
        let envelope = match mode.as_ref() {
            "memory-reverse" => run_tick_envelope::<MemoryGraph>(true),
            "hypergraph-forward" => run_tick_envelope::<HypergraphStore>(false),
            other => panic!("unknown PER-18 child envelope mode: {other}"),
        };
        println!("{ENVELOPE_MARKER}{}", envelope.canonical_text());
    }

    #[test]
    fn real_tick_envelope_is_identical_across_process_order_and_backend() {
        let memory_parent = run_tick_envelope::<MemoryGraph>(false);
        let hypergraph_parent = run_tick_envelope::<HypergraphStore>(true);
        assert_eq!(memory_parent, hypergraph_parent);
        let expected = memory_parent.canonical_text();

        assert_eq!(child_tick_envelope("memory-reverse"), expected);
        assert_eq!(child_tick_envelope("hypergraph-forward"), expected);
    }

    #[test]
    fn a_failed_tick_leaves_graph_counter_and_prior_events_unchanged() {
        let mut session = TickSession::new(
            ATOMICITY_SCENARIO,
            ATOMICITY_RULE,
            HypergraphStore::new(),
            test_session(),
        )
        .expect("the rollback probe loads");
        let before_hash = session.graph().state_hash().expect("pre-state hashes");
        let mut sink = CollectingSink {
            events: vec![("EventType/PRIOR".to_owned(), Vec::new())],
        };
        let before_events = sink.events.clone();

        let before_cursors = session.graph().allocator_cursors();

        for _ in 0..2 {
            let error = session
                .advance(&mut sink)
                .expect_err("the second write exceeds one");

            assert!(error.contains("E-EVAL-020"), "{error}");
            assert_eq!(session.tick(), 0, "a failed tick is not completed");
            assert_eq!(
                session
                    .graph()
                    .state_hash()
                    .expect("post-failure state hashes"),
                before_hash,
                "the first subject's valid write must roll back with the failed tick"
            );
            assert_eq!(session.graph().allocator_cursors(), before_cursors);
            assert_eq!(
                sink.events, before_events,
                "events emitted before the failing write must not escape the tick"
            );
        }

        let mut future = session.graph().clone();
        assert_eq!(future.add_node("SOCIAL_CLASS").unwrap(), NodeId(2));
    }

    #[test]
    fn nominal_world_hash_moves_with_completed_time_when_graph_hash_does_not() {
        let mut session = TickSession::new(
            CLOCK_SCENARIO,
            CLOCK_RULE,
            HypergraphStore::new(),
            test_session(),
        )
        .expect("the world-clock probe loads");
        let mut sink = CollectingSink::default();

        let first = session.advance(&mut sink).expect("tick one commits");
        let second = session.advance(&mut sink).expect("tick two commits");

        assert_eq!(
            first.before, first.after,
            "an emit-only rule does not move graph state"
        );
        assert_eq!(first.after, second.before);
        assert_ne!(first.world_before, first.world_after);
        assert_eq!(first.world_after, second.world_before);
        assert_ne!(second.world_before, second.world_after);
    }

    #[test]
    fn completed_tick_overflow_refuses_before_any_world_or_event_mutation() {
        let mut session = TickSession::new(
            CLOCK_SCENARIO,
            CLOCK_RULE,
            HypergraphStore::new(),
            test_session(),
        )
        .expect("the world-clock probe loads");
        session.tick = i64::MAX;
        let before_hash = session.graph().state_hash().unwrap();
        let before_cursors = session.graph().allocator_cursors();
        let mut sink = CollectingSink {
            events: vec![("EventType/PRIOR".to_owned(), Vec::new())],
        };

        let error = session.advance(&mut sink).unwrap_err();

        assert_eq!(error, "tick counter overflow before adjudication");
        assert_eq!(session.tick(), i64::MAX);
        assert_eq!(session.graph().state_hash().unwrap(), before_hash);
        assert_eq!(session.graph().allocator_cursors(), before_cursors);
        assert_eq!(sink.events.len(), 1);
        assert_eq!(sink.events[0].0, "EventType/PRIOR");
    }

    #[test]
    fn advance_numbers_ticks_starting_at_one_over_a_two_rule_session() {
        let mut session = TickSession::new(
            SCENARIO,
            &rule_src(),
            HypergraphStore::new(),
            test_session(),
        )
        .expect("load");
        assert_eq!(session.tick(), 0);
        let mut sink = CollectingSink::default();
        let r1 = session.advance(&mut sink).expect("tick 1");
        assert_eq!(session.tick(), 1);
        assert_eq!(r1.per_rule_fired.len(), 2);
        session.advance(&mut sink).expect("tick 2");
        assert_eq!(session.tick(), 2);
    }

    #[test]
    fn advance_moves_state_and_each_tick_hashes_differently() {
        let mut session = TickSession::new(
            SCENARIO,
            &rule_src(),
            HypergraphStore::new(),
            test_session(),
        )
        .expect("load");
        let mut sink = CollectingSink::default();
        let t1 = session.advance(&mut sink).expect("tick 1");
        let t2 = session.advance(&mut sink).expect("tick 2");
        assert_ne!(t1.before, t1.after, "tick 1 must move state");
        assert_eq!(t1.after, t2.before, "tick 2 starts where tick 1 left off");
        assert_ne!(
            t2.before, t2.after,
            "tick 2 must move state too — not a one-shot"
        );
    }

    #[test]
    fn two_independent_sessions_over_the_same_content_hash_identically() {
        // The determinism guard this plan's own instructions require, at
        // the babylon-tick level — Phase E's test (tests/determinism.rs in
        // babylon-client) repeats this same property through the client's
        // own seam end to end. Both sessions share the SAME session id —
        // the replay contract the `rng-draw` seam is built for (D69).
        let mut a = TickSession::new(
            SCENARIO,
            &rule_src(),
            HypergraphStore::new(),
            test_session(),
        )
        .expect("load a");
        let mut b = TickSession::new(
            SCENARIO,
            &rule_src(),
            HypergraphStore::new(),
            test_session(),
        )
        .expect("load b");
        let mut sink_a = CollectingSink::default();
        let mut sink_b = CollectingSink::default();
        for _ in 0..5 {
            let ra = a.advance(&mut sink_a).expect("a advances");
            let rb = b.advance(&mut sink_b).expect("b advances");
            assert_eq!(
                ra.after, rb.after,
                "same content + same tick count must hash identically"
            );
            assert_eq!(
                ra.world_after, rb.world_after,
                "nominal world hashes must be byte-identical too"
            );
        }
    }
}
