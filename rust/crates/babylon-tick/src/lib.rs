//! `babylon-tick`'s `run_once` seam — the Phase 2 Slice 1 flow (scenario load
//! -> rule load -> one tick -> state hash) as a library function, so both
//! the CLI driver (`main.rs`) and `babylon-client`'s engine link (B0) call
//! exactly one implementation. See `main.rs` for the CLI-facing docs; this
//! module is the seam itself.

use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
use babylon_bsl::intrinsic_host::EmptyIntrinsicHost;
use babylon_bsl::rule_pipeline::{load_rule, LoadContext};
use babylon_bsl::scenario::load_scenario;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_bsl::tick::run_tick;
use babylon_bsl::typecheck::TypeEnv;
use babylon_bsl::BindingVocabulary;
use babylon_graph::memory::MemoryGraph;
use std::collections::{HashMap, HashSet};

/// The result of running one rule over one scenario for one tick: the
/// pre-tick and post-tick state hashes, and how many subjects fired.
pub struct TickReport {
    pub before: [u8; 32],
    pub after: [u8; 32],
    pub fired: usize,
}

/// Render a 32-byte hash as lowercase hex — the same format the CLI driver
/// prints and the engine-link probe logs.
pub fn hex(bytes: &[u8; 32]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// Load `scenario_src`, load `rule_src` through every gate, run one tick,
/// and return the pre/post state hashes plus the fired-subject count.
///
/// This is the Slice 1 contract: the CLI driver (`main.rs`) and
/// `babylon-client`'s engine link (Program 28 B0) both call exactly this
/// function, so "the client links the engine in-process" means literally
/// sharing this code path, not a lookalike reimplementation.
pub fn run_once(scenario_src: &str, rule_src: &str) -> Result<TickReport, String> {
    let mut graph = MemoryGraph::new();
    let scenario = load_scenario(scenario_src, &mut graph).map_err(|e| e.to_string())?;

    let before = graph
        .state_hash()
        .map_err(|e| format!("pre-tick state: {}", e.message))?;

    // The scenario's `deffield` forms ARE the registries for slice 1. When
    // Phase 2's content registries land they replace this wholesale; until
    // then a field's type and intensivity come from a declaration rather
    // than from a guess about its stored value.
    let types = TypeEnv {
        fields: scenario.fields.clone(),
        exemptions: &[],
    };
    let vocabulary = BindingVocabulary {
        fields: scenario.fields.keys().cloned().collect(),
        consts: HashSet::new(),
        metrics: HashSet::new(),
    };
    // One ceiling per node type the scenario ACTUALLY minted, keyed as the
    // bound checker expects (`NodeType/MEMBER`). Hard-coding a single type
    // would make this driver silently specific to `SOCIAL_CLASS`: any rule
    // querying another type would fail load with `MissingCeiling`, which is
    // a confusing way to say "this driver only ever supported one type".
    //
    // A type the scenario declared zero of still gets no ceiling — and that
    // is correct: a rule querying a population that does not exist should
    // fail loudly at load rather than quietly iterate nothing.
    let ceilings = CardinalityCeilings::new(
        scenario
            .node_types
            .iter()
            .map(|(member, count)| (format!("NodeType/{member}"), *count))
            .collect(),
        HashMap::new(),
    );
    let intrinsics = IntrinsicCosts::default();
    let systems: HashSet<String> = HashSet::from([
        "economics".to_owned(),
        "vitality".to_owned(),
        "consciousness".to_owned(),
    ]);

    let ctx = LoadContext {
        vocabulary: &vocabulary,
        types: &types,
        ceilings: &ceilings,
        intrinsics: &intrinsics,
        systems: &systems,
        // The R9 chapters' vocabulary-dependent gates (D37's field-init
        // owner rule, D43's domain inference, §2.5's foreign-`:field`
        // scoping) need a `ClosedVocabulary`. This driver declares none —
        // the scenario's `deffield` forms are its whole registry — so they
        // are skipped here rather than run against a guess. The registry is
        // Phase-2 content work.
        vocabulary_registry: None,
        rule_file: "rule",
    };
    let loaded = load_rule(rule_src, &ctx).map_err(|e| format!("rule rejected: {e}"))?;

    let mut sink = CollectingSink::default();
    let outcome = run_tick(
        &loaded,
        &types,
        &EmptyIntrinsicHost,
        &mut graph,
        &mut sink,
        &intrinsics,
    )
    .map_err(|e| format!("tick failed: {e}"))?;

    let after = graph
        .state_hash()
        .map_err(|e| format!("post-tick state: {}", e.message))?;

    Ok(TickReport {
        before,
        after,
        fired: outcome.fired,
    })
}

#[cfg(test)]
mod tests {
    use super::run_once;
    const SCENARIO: &str = include_str!("../content/scenarios/two-classes.bscn");
    const RULE: &str = include_str!("../content/rules/fundamental-theorem.bsl");

    #[test]
    fn run_once_is_deterministic() {
        let a = run_once(SCENARIO, RULE).expect("first run");
        let b = run_once(SCENARIO, RULE).expect("second run");
        assert_eq!(a.after, b.after);
        assert_ne!(a.before, a.after, "the rule must move state");
    }
}
