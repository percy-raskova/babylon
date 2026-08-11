//! `babylon-tick`'s `run_once` seam — the Phase 2 Slice 1 flow (scenario load
//! -> rule load -> one tick -> state hash) as a library function, so both
//! the CLI driver (`main.rs`) and `babylon-client`'s engine link (B0) call
//! exactly one implementation. See `main.rs` for the CLI-facing docs; this
//! module is the seam itself.

use babylon_bsl::declarations::parse_intrinsic_decls;
use babylon_bsl::evaluator::Value;
use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
use babylon_bsl::intrinsic_host::KernelIntrinsicHost;
use babylon_bsl::rule_pipeline::{load_rule_form, split_content, LoadContext, LoadedRule};
use babylon_bsl::scenario::load_scenario;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_bsl::tick::run_tick;
use babylon_bsl::typecheck::TypeEnv;
use babylon_bsl::BindingVocabulary;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_graph::state_hash::CanonicalState;
use babylon_graph::substrate::GraphSubstrate;
use std::collections::{HashMap, HashSet};

pub mod session;
pub use session::TickSession;

/// The result of running one or more rules over one scenario for one tick:
/// the pre-tick and post-tick state hashes, and how many subjects fired.
#[derive(Debug)]
pub struct TickReport {
    pub before: [u8; 32],
    pub after: [u8; 32],
    /// The TOTAL fired-subject count across every rule this tick ran —
    /// unchanged in meaning and type for a single-rule content set (today
    /// every existing caller: `run_once`, the CLI, B0's engine-link probe,
    /// every `*_conformance.rs` test). For a multi-rule tick this is the
    /// SUM across rules — kept a plain `usize` rather than widened to
    /// `Vec<usize>` specifically so `report.fired == N` assertions across
    /// this crate's `tests/*_conformance.rs` and `tests/floor_intrinsic_e2e.rs`
    /// keep compiling and keep passing unmodified.
    pub fired: usize,
    /// Per-rule detail, in ASCENDING RULE-ID BYTE ORDER (§4.2, register row
    /// D16) — `(rule_id, fired)`. NEVER declaration order or file order;
    /// §4.2 says those "are never observable", and this field's own order
    /// is the driver's proof that it honors that. Length 1 for every
    /// existing single-rule content set (`fired == per_rule_fired[0].1`
    /// always holds); length N for an N-rule content set.
    pub per_rule_fired: Vec<(String, usize)>,
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
///
/// `rule_src` may carry zero or more `(intrinsic …)` top-forms (§2.2's
/// `<intrinsic-decl>`) alongside its one `(rule …)` form, in EITHER order —
/// `(intrinsic …)` is ordinary content, not a side channel a caller must
/// route through a separate parameter (§2.2: "file boundaries and file
/// names carry no semantics"). A rule calling an undeclared intrinsic
/// refuses loudly (`E-LOAD-021`); a declared name outside
/// `declarations::DECLARABLE_INTRINSICS` refuses the WHOLE load
/// (`E-LOAD-020`/`E-LOAD-024`/`E-LOAD-001`), never a partial admission.
pub fn run_once(scenario_src: &str, rule_src: &str) -> Result<TickReport, String> {
    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    run_once_into(scenario_src, rule_src, &mut graph, &mut sink)
}

/// Everything `run_once_into` does before running a tick: parse the
/// intrinsic declarations, load the scenario into `graph`, and load every
/// `(rule …)` form `split_content` returns against the vocabulary/types/
/// ceilings that scenario declared — sorted into ascending rule-id BYTE
/// order (§4.2, register row D16) before this returns, so every later
/// stage (`TickSession::advance`, `run_once_into`) just iterates the
/// already-correct order. Shared by `run_once_into` (which still runs
/// exactly tick 1) and, from `session.rs` on, `TickSession::new` (Program
/// 28 B2, `docs/superpowers/plans/2026-08-11-b2-tick-loop-plan.md` Phase A
/// Task 4).
pub(crate) struct PreparedRules {
    pub rules: Vec<(String, LoadedRule)>,
    pub types: TypeEnv,
    pub intrinsics: IntrinsicCosts,
    pub consts: HashMap<String, Value>,
}

pub(crate) fn prepare_rules<G: GraphSubstrate + CanonicalState>(
    scenario_src: &str,
    rule_src: &str,
    graph: &mut G,
) -> Result<PreparedRules, String> {
    // §2.2's `<intrinsic-decl>` top-forms, split from the `(rule …)` forms
    // they may share a source with (`split_content`), then parsed into the
    // `IntrinsicCosts` the loader's static bound check AND the evaluator
    // both need — refusing loudly and wholesale on the first bad
    // declaration, including a duplicate name (`E-LOAD-001`) or a
    // signature disagreeing with the kernel's registration (`E-LOAD-020`),
    // never a partial admission of the ones that do qualify.
    let (intrinsic_forms, rule_forms) = split_content(rule_src).map_err(|e| e.to_string())?;
    let declared = parse_intrinsic_decls(&intrinsic_forms).map_err(|e| e.to_string())?;
    let intrinsics = IntrinsicCosts::new(
        declared
            .into_iter()
            .map(|(name, decl)| (name, decl.cost))
            .collect(),
    );

    let scenario = load_scenario(scenario_src, graph).map_err(|e| e.to_string())?;

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
        // The scenario's `(defconst …)` rows ARE the defines environment for
        // slice 1, exactly as its `deffield` rows are the field registry.
        // Taking the vocabulary and the values from ONE declaration is what
        // keeps `E-LOAD-010` (unknown coefficient, at load) and the tick's
        // lookup from ever disagreeing.
        consts: scenario.consts.keys().cloned().collect(),
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
    //
    // Same for `EdgeType/MEMBER` (query-evaluation plan, Task 15, P27 Phase
    // 2 PR 5): `bound_checker::neighbors_ceiling` bounds a `(neighbors …)`
    // fold against the LESSER of the queried edge type's ceiling and the
    // annotated result NodeType's, so a rule using `neighbors` needs an
    // edge-type entry too, or the load fails `MissingCeiling` on the edge
    // axis specifically. `scenario.node_types` and `scenario.edge_types`
    // key disjoint namespaces (`NodeType/…` vs `EdgeType/…`), so merging
    // them into one flat map — which is what `CardinalityCeilings` already
    // is — cannot collide.
    let ceilings = CardinalityCeilings::new(
        scenario
            .node_types
            .iter()
            .map(|(member, count)| (format!("NodeType/{member}"), *count))
            .chain(
                scenario
                    .edge_types
                    .iter()
                    .map(|(member, count)| (format!("EdgeType/{member}"), *count)),
            )
            .collect(),
        HashMap::new(),
    );
    let systems: HashSet<String> = HashSet::from([
        "economics".to_owned(),
        "vitality".to_owned(),
        "consciousness".to_owned(),
        // The lifecycle/* rule pack (Material Base @7.0, the D-P-D' circuit)
        // — same class of minimal driver-scaffolding addition as "vitality"
        // above.
        "lifecycle".to_owned(),
        // The dispossession/* rule pack (Material Base @10.0, primitive
        // accumulation as value transfer) — same class of minimal
        // driver-scaffolding addition as "vitality"/"lifecycle" above.
        "dispossession".to_owned(),
        // The metabolism/* rule pack (Material Base @13.0, the per-territory
        // half of the metabolic rift) — same class of minimal
        // driver-scaffolding addition as the three above.
        "metabolism".to_owned(),
        // NOT a Territory-port system (§2.3's anchor default names a real
        // content pack; this train ships none — see the query-evaluation
        // plan's Task 15, "this task ships no Territory content"). Added
        // solely so `query_lane_e2e.rs`'s four synthetic, Territory-SHAPED
        // vectors have a legal, honestly-named rule-id namespace to anchor
        // under; same class of minimal driver-scaffolding addition as the
        // four above.
        "territory".to_owned(),
    ]);

    // ONE shared LoadContext for every rule in the content set — the
    // vocabulary/types/ceilings come from the SCENARIO, not from any one
    // rule, and each rule's own load only reads the subset its bindings
    // reference (verified: no cross-rule interference for vitality +
    // lifecycle, whose bindings are wholly disjoint — see the plan's
    // Multi-Rule Decision section's domain-disjointness note).
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

    // rule_forms is `Vec<(String, SExpr)>` — each rule's id already paired
    // with its form by split_content (Task 2), so no second extraction
    // here. Loaded in WHATEVER order split_content returned them (reader-
    // encounter order, unspecified) — then SORTED by id, ascending byte
    // order, before returning. This is the one place execution order gets
    // decided (§4.2, register row D16): sorting here, once, at load time,
    // means every later stage (TickSession::advance, run_once_into) just
    // iterates the already-correct order and never re-derives it.
    let mut rules = Vec::with_capacity(rule_forms.len());
    for (id, form) in rule_forms {
        let loaded = load_rule_form(form, &ctx).map_err(|e| format!("rule {id} rejected: {e}"))?;
        rules.push((id, loaded));
    }
    rules.sort_by(|(a, _), (b, _)| a.as_bytes().cmp(b.as_bytes()));

    Ok(PreparedRules {
        rules,
        types,
        intrinsics,
        consts: scenario.consts,
    })
}

/// `run_once`, with the world and the event sink supplied by the caller so
/// they survive the call.
///
/// `run_once` returns hashes, which prove that state MOVED and that it moves
/// the same way twice — but a conformance vector has to name the values a
/// named class ended the tick holding, and an emitted event has to be
/// inspectable at all. Threading the two outputs through a parameter keeps
/// **one** implementation of the flow: `run_once`'s signature and
/// [`TickReport`] are the seam `babylon-client` consumes and neither moves.
///
/// Generic over the substrate — the storage-swap plan's entire
/// production-side change was this one signature (Phase A Task 3) plus one
/// construction-site swap (Phase D Task 10): `run_once` now constructs
/// `HypergraphStore` (ADR179 T3) rather than `MemoryGraph`; this function
/// itself never moved.
///
/// # Errors
///
/// A description of the first failing stage — an intrinsic declaration, a
/// scenario load, a rule load, a state hash, or the tick itself.
pub fn run_once_into<G: GraphSubstrate + CanonicalState>(
    scenario_src: &str,
    rule_src: &str,
    graph: &mut G,
    sink: &mut CollectingSink,
) -> Result<TickReport, String> {
    let prepared = prepare_rules(scenario_src, rule_src, graph)?;

    let before = graph
        .state_hash()
        .map_err(|e| format!("pre-tick state: {}", e.message))?;

    // Every rule in `prepared.rules` runs to COMPLETION (every matching
    // subject) before the next rule starts — never interleaved — against
    // the SAME `graph`, so a later rule sees an EARLIER rule's writes from
    // the SAME tick. This falls out of calling `run_tick` sequentially
    // against one `&mut G`, and it matches the frozen Python engine's own
    // in-place, strict-order mutation semantics — but it is NOT what §4.2
    // demands: "rules within one system position observe the same
    // pre-state" (bsl-language.rst §4.2) covers RULE-to-rule pre-state
    // sharing, not just subject-to-subject within one rule. Task 12
    // (D-row Q1) repaired the within-rule half via `run_tick`'s
    // collect-then-apply split; this cross-rule half is a SEPARATE,
    // RECORDED gap — D-row Q14 (the query-evaluation plan's draft-ruling
    // register) — latent today because every landed rule pack keeps its
    // system position to exactly one rule (see `vitality.bsl`'s own
    // header). This is a divergence to fix in its own train, not a
    // design feature "inherited for free". The ORDER `prepared.rules`
    // iterates in is rule-id byte order (`prepare_rules`'s sort), not the
    // frozen engine's tick-position order.
    let mut per_rule_fired = Vec::with_capacity(prepared.rules.len());
    for (id, loaded) in &prepared.rules {
        let outcome = run_tick(
            loaded,
            &prepared.types,
            &KernelIntrinsicHost,
            graph,
            sink,
            &prepared.intrinsics,
            &prepared.consts,
            // `run_once` is one tick, and it is tick 1 — the same number the
            // CLI has always printed. §2.5's `:tick`/`:tick-in-cycle`
            // bindings read it; `:year`/`:tick-of-year` need an epoch
            // slice 1 does not pin and are refused by name at `run_tick`
            // entry.
            1,
        )
        .map_err(|e| format!("tick failed in rule {id}: {e}"))?;
        per_rule_fired.push((id.clone(), outcome.fired));
    }
    let fired = per_rule_fired.iter().map(|(_, n)| n).sum();

    let after = graph
        .state_hash()
        .map_err(|e| format!("post-tick state: {}", e.message))?;

    Ok(TickReport {
        before,
        after,
        fired,
        per_rule_fired,
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

    #[test]
    fn single_rule_content_still_reports_fired_and_a_one_entry_per_rule_fired() {
        let report = run_once(SCENARIO, RULE).expect("single-rule run");
        assert_eq!(report.per_rule_fired.len(), 1);
        assert_eq!(report.per_rule_fired[0].1, report.fired);
    }
}
