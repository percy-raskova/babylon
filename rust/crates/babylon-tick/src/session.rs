//! `TickSession` — the persistent load-once, advance-many seam B2 needs,
//! now multi-rule (Phase A, Tasks 2-4). `run_once`/`run_once_into`
//! (`lib.rs`) model one tick end to end and hardcode `run_tick`'s tick
//! argument to `1` for every rule the content set holds; a player-driven
//! loop needs the split this type provides instead: parse and load cost
//! paid ONCE in `new`, the SAME `PreparedRules` and the SAME graph reused
//! by every `advance()` call, every rule in the content set run once per
//! call, in ascending rule-id byte order (§4.2, register row D16/D100 —
//! `prepare_rules` sorts once at load time), with `tick` incremented by
//! this type.

use crate::{prepare_rules, PreparedRules, TickReport};
use babylon_bsl::intrinsic_host::KernelIntrinsicHost;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_bsl::tick::run_tick;
use babylon_graph::state_hash::CanonicalState;
use babylon_graph::substrate::GraphSubstrate;

/// One content set, loaded once, advanced tick by tick against ONE held
/// graph. `G` is caller-supplied (same shape as `run_once_into`) so the
/// caller picks the substrate — production callers pass `HypergraphStore`
/// (ADR193).
pub struct TickSession<G> {
    graph: G,
    prepared: PreparedRules,
    tick: i64,
}

impl<G: GraphSubstrate + CanonicalState> TickSession<G> {
    /// Parse `rule_src` (one or more `(rule …)` forms) and load
    /// `scenario_src` into `graph` once. `prepare_rules` sorts the forms
    /// into ascending rule-id byte order (§4.2, D16/D100) before this
    /// returns — the caller's own concatenation order is never observable.
    ///
    /// # Errors
    /// The same failure modes `run_once_into`'s load half has: an
    /// intrinsic declaration, a scenario load, or a rule load — named to
    /// its own rule id when more than one rule is present.
    pub fn new(scenario_src: &str, rule_src: &str, mut graph: G) -> Result<Self, String> {
        let prepared = prepare_rules(scenario_src, rule_src, &mut graph)?;
        Ok(Self {
            graph,
            prepared,
            tick: 0,
        })
    }

    /// Run one more tick against the held graph: every rule in the
    /// content set, in ASCENDING RULE-ID BYTE ORDER (§4.2, D16/D100 —
    /// sorted once, at load time, by `prepare_rules`), each to completion
    /// before the next starts, against the SAME graph — so a later rule
    /// sees an earlier rule's writes from this same tick, matching the
    /// frozen engine's own in-place strict-order semantics (inherited
    /// from calling `run_tick` sequentially against one `&mut G`).
    ///
    /// **This is a RECORDED GAP, not a design feature.** §4.2 says "rules
    /// within one system position observe the same pre-state"
    /// (bsl-language.rst §4.2), which covers rule-to-rule pre-state
    /// sharing, not only subject-to-subject within one rule. Task 12
    /// (D-row Q1) repaired the within-rule half (`run_tick`'s
    /// collect-then-apply split); this cross-rule half is a separate,
    /// still-open divergence — D-row Q14 (the query-evaluation plan's
    /// draft-ruling register) — latent today because every landed rule
    /// pack keeps its system position to exactly one rule. The first call
    /// runs tick 1 (matching `run_once`'s own numbering), the second tick
    /// 2, and so on.
    ///
    /// # Errors
    /// The tick itself (named to its own rule id), or a pre/post
    /// state-hash failure. On any error the session's tick counter does
    /// NOT advance — `tick()` counts COMPLETED ticks only (a failed tick
    /// must not look consumed to retry/error-handling callers).
    pub fn advance(&mut self, sink: &mut CollectingSink) -> Result<TickReport, String> {
        let next_tick = self.tick + 1;
        let before = self
            .graph
            .state_hash()
            .map_err(|e| format!("pre-tick state: {}", e.message))?;
        let mut per_rule_fired = Vec::with_capacity(self.prepared.rules.len());
        for (id, loaded) in &self.prepared.rules {
            let outcome = run_tick(
                loaded,
                &self.prepared.types,
                &KernelIntrinsicHost,
                &mut self.graph,
                sink,
                &self.prepared.intrinsics,
                &self.prepared.consts,
                next_tick,
            )
            .map_err(|e| format!("tick failed in rule {id}: {e}"))?;
            per_rule_fired.push((id.clone(), outcome.fired));
        }
        let fired = per_rule_fired.iter().map(|(_, n)| n).sum();
        let after = self
            .graph
            .state_hash()
            .map_err(|e| format!("post-tick state: {}", e.message))?;
        self.tick = next_tick;
        Ok(TickReport {
            before,
            after,
            fired,
            per_rule_fired,
        })
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
    use babylon_bsl::structural_verbs::CollectingSink;
    use babylon_graph::hypergraph_store::HypergraphStore;

    const SCENARIO: &str =
        include_str!("../content/scenarios/vitality-lifecycle-combined-conformance.bscn");
    const VITALITY: &str = include_str!("../content/rules/vitality.bsl");
    const LIFECYCLE: &str = include_str!("../content/rules/lifecycle.bsl");

    fn rule_src() -> String {
        format!("{VITALITY}\n{LIFECYCLE}")
    }

    #[test]
    fn advance_numbers_ticks_starting_at_one_over_a_two_rule_session() {
        let mut session =
            TickSession::new(SCENARIO, &rule_src(), HypergraphStore::new()).expect("load");
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
        let mut session =
            TickSession::new(SCENARIO, &rule_src(), HypergraphStore::new()).expect("load");
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
        // own seam end to end.
        let mut a =
            TickSession::new(SCENARIO, &rule_src(), HypergraphStore::new()).expect("load a");
        let mut b =
            TickSession::new(SCENARIO, &rule_src(), HypergraphStore::new()).expect("load b");
        let mut sink_a = CollectingSink::default();
        let mut sink_b = CollectingSink::default();
        for _ in 0..5 {
            let ra = a.advance(&mut sink_a).expect("a advances");
            let rb = b.advance(&mut sink_b).expect("b advances");
            assert_eq!(
                ra.after, rb.after,
                "same content + same tick count must hash identically"
            );
        }
    }
}
