//! `babylon-tick`'s `run_once` seam — the Phase 2 Slice 1 flow (scenario load
//! -> rule load -> one tick -> state hash) as a library function, so both
//! the CLI driver (`main.rs`) and `babylon-client`'s engine link (B0) call
//! exactly one implementation. See `main.rs` for the CLI-facing docs; this
//! module is the seam itself.

use babylon_bsl::declarations::{parse_intrinsic_decls, FieldRegistry};
use babylon_bsl::evaluator::Value;
use babylon_bsl::fuel::{CardinalityCeilings, IntrinsicCosts};
use babylon_bsl::intrinsic_host::KernelIntrinsicHost;
use babylon_bsl::rule_pipeline::{load_rule_form, split_content, LoadContext, LoadedRule};
use babylon_bsl::scenario::{load_scenario, load_scenario_with_prelude};
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_bsl::tick::run_tick;
use babylon_bsl::typecheck::TypeEnv;
use babylon_bsl::types::EnumRegistry;
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

/// `run_once`, with the scenario load routed through a **declaration
/// prelude** first (Train B item 4, issue #591, D157) — the
/// scenario-declaration sharing seam. `prelude_src` MAY declare `defenum` /
/// `defvocabulary` / `defconst` / `deffield` forms the scenario's own
/// `deffield`s and node/edge seeds resolve against, exactly as if the
/// scenario had declared them itself; the scenario MAY re-declare a
/// `defenum` the prelude declared, verbatim (`EnumRegistry::declare`'s
/// identical-recognition arm, this train — `defenum`-only: `deffield`,
/// `defconst`, and `defvocabulary` still refuse ANY re-declaration,
/// identical or not), and a disagreeing `defenum` re-declaration still
/// refuses loudly.
///
/// Argument order is `(scenario, prelude, rule)` — `scenario_src` leads,
/// matching `run_once`'s own lead argument; `prelude_src` slots second,
/// between the two sources it sits between in the load pipeline.
///
/// # Errors
///
/// A description of the first failing stage — the prelude, an intrinsic
/// declaration, a scenario load, a rule load, a state hash, or the tick
/// itself.
pub fn run_once_with_prelude(
    scenario_src: &str,
    prelude_src: &str,
    rule_src: &str,
) -> Result<TickReport, String> {
    let mut graph = HypergraphStore::new();
    let mut sink = CollectingSink::default();
    run_once_into_with_prelude(scenario_src, prelude_src, rule_src, &mut graph, &mut sink)
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
///
/// `Debug` (T2, issue #559): needed so `Result<PreparedRules, String>` can be
/// formatted with `{:?}` in a test assertion message (every field already
/// derives `Debug`, so this is additive only).
#[derive(Debug)]
pub(crate) struct PreparedRules {
    pub rules: Vec<(String, LoadedRule)>,
    pub types: TypeEnv,
    pub intrinsics: IntrinsicCosts,
    pub consts: HashMap<String, Value>,
    /// **§2.13 addendum (D101).** The scenario's `defenum` registry —
    /// `run_tick`'s write path (`update-node` on an enum-typed field) and
    /// read path (`bind_subject` rendering a stored ordinal back to its
    /// member) both resolve against this.
    pub enums: EnumRegistry,
}

pub(crate) fn prepare_rules<G: GraphSubstrate + CanonicalState>(
    scenario_src: &str,
    // Train B item 4 (#591, D157): `None` for every pre-existing caller
    // (`run_once_into`, `TickSession::new`) — behavior unchanged, byte for
    // byte. `Some(prelude)` routes the scenario load through
    // `load_scenario_with_prelude` instead of `load_scenario`.
    prelude_src: Option<&str>,
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

    let scenario = match prelude_src {
        Some(prelude) => {
            load_scenario_with_prelude(prelude, scenario_src, graph).map_err(|e| e.to_string())?
        }
        None => load_scenario(scenario_src, graph).map_err(|e| e.to_string())?,
    };

    // The scenario's `deffield` forms ARE the registries for slice 1. When
    // Phase 2's content registries land they replace this wholesale; until
    // then a field's type and intensivity come from a declaration rather
    // than from a guess about its stored value.
    //
    // D32 (bsl-language.rst §2.9): every EdgeType carries one implicit
    // <edge-type>/strength field, needing no deffield. FieldRegistry::
    // with_implicit_edge_strength already builds this seed set, fully tested
    // (declarations.rs, r9_chapters.rs's own type_env() fixture) but had no
    // production caller until T2 (issue #559) — this is that caller. Seeded
    // from the scenario's declared defvocabulary EdgeType members
    // (scenario.vocabulary; `None` for a scenario declaring no defvocabulary
    // at all — the loop below is then a no-op, matching every pre-T2
    // scenario's behavior exactly). An explicit deffield re-declaring an
    // implicit field is D32's own named violation (E-LOAD-001,
    // FieldRegistry::declare's own duplicate guard) — checked here rather
    // than through that guard, because scenario.rs's simpler load_deffield
    // builds `scenario.fields` with no notion of "implicit" to check
    // against; this is that check's only home until Phase 2's content-pack
    // field registries replace scenario.fields wholesale (declarations.rs's
    // own module doc).
    let mut fields = scenario.fields.clone();
    if let Some(vocabulary) = scenario.vocabulary.as_ref() {
        let mut implicit: Vec<_> = FieldRegistry::with_implicit_edge_strength(vocabulary)
            .type_env_fields()
            .into_iter()
            .collect();
        // Byte order, the same convention `rules.sort_by` uses below: the
        // Err/Ok verdict never depended on `type_env_fields()`'s HashMap
        // iteration order, but the refusal TEXT did — with two or more
        // colliding qnames it nondeterministically named a different field
        // per process. Sorting makes the message always name the byte-least
        // colliding qname (declarations.rs's own reporting sorts the same
        // way before its first-failure checks).
        implicit.sort_by(|(a, _), (b, _)| a.as_bytes().cmp(b.as_bytes()));
        for (qname, decl) in implicit {
            if fields.contains_key(&qname) {
                return Err(format!(
                    "E-LOAD-001: {qname} is the implicit <edge-type>/strength field (D32) — \
                     re-declaring it with an explicit deffield is a duplicate declaration, never \
                     a silent override (bsl-language.rst §2.9)"
                ));
            }
            fields.insert(qname, decl);
        }
    }
    let types = TypeEnv {
        fields,
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
        // The territory/* rule pack (Material Base @2.0, four sequential
        // phase rules — heat dynamics, eviction pipeline, spillover,
        // necropolitics; Territory port train, P27 PR B). This entry was
        // ADDED EARLIER by the query-evaluation train solely so
        // `query_lane_e2e.rs`'s four synthetic, Territory-SHAPED vectors
        // had a legal namespace to anchor under, explicitly marked at the
        // time as "not a Territory-port system... this train ships none" —
        // the port train now ships the real content this namespace was
        // reserved for; the string literal itself is unchanged.
        "territory".to_owned(),
        // The organization/* rule pack (Task 8, Organization foundation
        // plan) — same class of minimal driver-scaffolding addition as the
        // five above; Task 10 ships the first content using this
        // namespace.
        "organization".to_owned(),
        // The production/* rule pack (Material Base @3.0, four rules —
        // direct production, employed routing, employed fallback,
        // extraction-intensity broadcast; Production port train, issue
        // #565). Genuinely NEW registration (unlike territory's own
        // pre-existing placeholder above) — the scout dossier
        // (reports/production-bsl-surface-facts-2026-08-12.md §3) confirmed
        // "production" had zero prior hits in this HashSet on either tree.
        "production".to_owned(),
        // The social-class/* namespace (T2 slice-2 edge reads, issue #559).
        // Added solely so `edge_lane_e2e.rs`'s three synthetic, Solidarity-
        // SHAPED vectors have a legal namespace to anchor under (E-LOAD-002)
        // — the SAME class of driver-scaffolding entry "territory" itself
        // was when the query-evaluation train added it for
        // `query_lane_e2e.rs`'s vectors (see that entry's own comment
        // above). NOT a system port: T2 ships no Solidarity content
        // (Solidarity's PORT is a separate Wave C train), and no engine
        // system is named "social-class" — this is the e2e fixture's own
        // subject-type namespace, nothing more.
        "social-class".to_owned(),
        // The solidarity/* rule pack (Material Base @8.0, consciousness
        // transmission over SOLIDARITY edges — Wave C: Solidarity port
        // train, issue #557 umbrella, Task 1). Same class of minimal
        // driver-scaffolding addition as "vitality"/"lifecycle"/
        // "dispossession"/"metabolism"/"production" above: registers the
        // namespace so `solidarity/p0-transmit`'s rule id resolves under
        // E-LOAD-002 before the pack itself lands (Task 2).
        "solidarity".to_owned(),
        // The decomposition/* rule pack (Material Base @11.0, LA class
        // breakdown into CARCERAL_ENFORCER/INTERNAL_PROLETARIAT during
        // terminal crisis; Decomposition+ControlRatio port train, Task 1 of
        // `docs/superpowers/plans/2026-08-17-decomposition-controlratio-
        // port.md`). Genuinely NEW registration — the Task 0 surface-facts
        // dossier confirmed zero prior hits in this HashSet.
        "decomposition".to_owned(),
        // The control-ratio/* rule pack (Material Base @12.0, the
        // guard:prisoner ratio crisis + the ADR070-reserved revolution-vs-
        // genocide terminal decision; same port train, Task 1). Hyphenated
        // spelling is the RULED spelling (Task 0 dossier §7, three
        // independent proofs: `reader.rs::validate_symbol` accepts hyphens,
        // the landed `"social-class"` precedent immediately above, and
        // `edge_lane_e2e.rs`'s landed hyphenated rule-id first segments) —
        // genuinely NEW registration, same class as "decomposition" above.
        "control-ratio".to_owned(),
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
        // scoping) AND Task 8's closed-vocabulary membership enforcement
        // (E-LOAD-030/031) need a `ClosedVocabulary`. Task 7 landed the
        // scenario-side declaration form (`defvocabulary`); Task 8 wires
        // enforcement live — whatever the scenario declared (`Some`, or
        // `None` for a scenario declaring none at all, exactly today's
        // unchecked behavior) is what every rule loads against.
        vocabulary_registry: scenario.vocabulary.as_ref(),
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
        enums: scenario.enums,
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
    let prepared = prepare_rules(scenario_src, None, rule_src, graph)?;
    run_prepared_tick(prepared, graph, sink)
}

/// `run_once_into`, with the scenario load routed through a **declaration
/// prelude** first — the caller-supplied-graph/sink sibling of
/// [`run_once_with_prelude`], exactly as `run_once_into` is `run_once`'s
/// (Train B item 4, issue #591, D157). Added alongside
/// [`run_once_with_prelude`] because `consciousness_ternary_conformance.rs`
/// needs it directly: once `consciousness-ternary-conformance.bscn` stopped
/// re-declaring `WorldView` itself (this train), every one of its callers —
/// not only `tick_goldens.rs`'s golden — needs the prelude, and this
/// module's other entry points (`run_once`, `TickSession`) are all it has
/// to route through.
///
/// # Errors
///
/// A description of the first failing stage — the prelude, an intrinsic
/// declaration, a scenario load, a rule load, a state hash, or the tick
/// itself.
pub fn run_once_into_with_prelude<G: GraphSubstrate + CanonicalState>(
    scenario_src: &str,
    prelude_src: &str,
    rule_src: &str,
    graph: &mut G,
    sink: &mut CollectingSink,
) -> Result<TickReport, String> {
    let prepared = prepare_rules(scenario_src, Some(prelude_src), rule_src, graph)?;
    run_prepared_tick(prepared, graph, sink)
}

/// `run_once_with_prelude` (this train) and `run_once_into` (above) share
/// this from the point `prepare_rules` has already returned: run every
/// prepared rule to completion, in order, against the SAME `graph`, and
/// assemble the [`TickReport`]. Extracted so a prelude-bearing caller does
/// not duplicate this loop — `prepare_rules`'s own `prelude_src` parameter
/// is the only thing that differs between the two callers, and it is fully
/// resolved before this function ever runs.
///
/// # Errors
///
/// The tick itself (named to its own rule id), or a pre/post state-hash
/// failure.
fn run_prepared_tick<G: GraphSubstrate + CanonicalState>(
    prepared: PreparedRules,
    graph: &mut G,
    sink: &mut CollectingSink,
) -> Result<TickReport, String> {
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
            &prepared.enums,
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
    use super::{prepare_rules, run_once};
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

    // F3 (#534 fix round item 3, panel-proven): `prepare_rules`'s ONE
    // production wiring line — `vocabulary_registry:
    // scenario.vocabulary.as_ref()` — was unpinned; mutating it to `None`
    // flipped zero tests. This drives `run_once`, the ACTUAL production
    // seam (the CLI driver and `babylon-client`'s engine link both call
    // exactly this function), with a scenario declaring a vocabulary and a
    // rule whose enum-ref typos a member of a DECLARED kind — proving the
    // registry really is threaded end to end through `prepare_rules`, not
    // merely unit-tested in isolation at each of the three producers.
    const VOCAB_WIRING_SCENARIO: &str = r"
(scenario ft/vocab-wiring-probe
  (defvocabulary NodeType (SOCIAL_CLASS))
  (deffield social-class/wages int extensive)
  (node core NodeType/SOCIAL_CLASS (social-class/wages 100)))
";
    const VOCAB_WIRING_RULE: &str = r#"(rule vitality/vocab-wiring-probe
  :material-basis "F3 (#534 fix round item 3): proves the production seam threads a declared vocabulary end to end"
  :fuel 64
  (domain NodeType/SOCIAL_CLA)
  (bindings (binding wages :field social-class/wages))
  (when (> wages 0))
  (effects (emit EventType/PROBE)))"#;

    #[test]
    fn a_declared_vocabulary_typo_refuses_through_the_production_seam() {
        let err = run_once(VOCAB_WIRING_SCENARIO, VOCAB_WIRING_RULE).unwrap_err();
        assert!(err.contains("E-LOAD-031"), "{err}");
    }

    // T2 (issue #559) PLAN-MUST-VERIFY probe: proves the D32 implicit-strength seed reaches
    // typecheck_aggregation through prepare_rules's REAL production wiring, using only
    // already-served slice-1 infrastructure (neighbors) — provable BEFORE edges/field-of-over-
    // EdgeRef land in PR B (Tasks 3-5). The rule LOADS today only if the wiring works; it would
    // still refuse E-EVAL-033 if actually RUN (its fold body reads a NodeRef's field-of an
    // edge-owned qname, a referent-type mismatch) — this probe tests LOADING only, deliberately.
    const D32_WIRING_PROBE_SCENARIO: &str = r"
(scenario ft/d32-wiring-probe
  (defvocabulary NodeType (SOCIAL_CLASS))
  (defvocabulary EdgeType (SOLIDARITY))
  (deffield social-class/shape int extensive)
  (node core NodeType/SOCIAL_CLASS (social-class/shape 1))
  (node other NodeType/SOCIAL_CLASS (social-class/shape 1))
  (edge EdgeType/SOLIDARITY core other 1))
";
    const D32_WIRING_PROBE_RULE: &str = r#"(rule vitality/d32-wiring-probe
  :material-basis "PLAN-MUST-VERIFY probe (T2, issue #559): the D32 implicit-strength field must resolve through prepare_rules's real TypeEnv construction, not merely in isolation (r9_chapters.rs::type_env already proves the isolated chain)"
  :fuel 128
  (bindings (binding shape :field social-class/shape))
  (when (= shape 1))
  (effects (emit EventType/PROBE
    (s (fold sum (neighbors self EdgeType/SOLIDARITY :any NodeType/SOCIAL_CLASS)
             (field-of it solidarity/strength))))))"#;

    #[test]
    fn the_d32_implicit_strength_field_resolves_through_the_real_wiring_seam() {
        let mut graph = babylon_graph::hypergraph_store::HypergraphStore::new();
        let result = prepare_rules(
            D32_WIRING_PROBE_SCENARIO,
            None,
            D32_WIRING_PROBE_RULE,
            &mut graph,
        );
        assert!(
            result.is_ok(),
            "the D32 implicit-strength field must resolve through prepare_rules's real \
             TypeEnv construction: {result:?}"
        );
    }

    // Task 2 Step 4: proves the E-LOAD-001 half, not just the happy path — a rule-irrelevant
    // EXPLICIT `deffield` re-declaring the implicit `<edge-type>/strength` field must refuse,
    // never silently override. Zero-regression check (verified, not assumed):
    // `rg -n "strength" rust/crates/babylon-tick/content/scenarios/*.bscn` returns no hits today
    // — no committed scenario explicitly declares an edge-owned `strength` field, so this new
    // refusal cannot regress any existing content.
    const D32_WIRING_PROBE_SCENARIO_WITH_EXPLICIT_REDECLARATION: &str = r"
(scenario ft/d32-wiring-probe
  (defvocabulary NodeType (SOCIAL_CLASS))
  (defvocabulary EdgeType (SOLIDARITY))
  (deffield social-class/shape int extensive)
  (deffield solidarity/strength int extensive)
  (node core NodeType/SOCIAL_CLASS (social-class/shape 1))
  (node other NodeType/SOCIAL_CLASS (social-class/shape 1))
  (edge EdgeType/SOLIDARITY core other 1))
";

    #[test]
    fn an_explicit_deffield_redeclaring_the_implicit_strength_field_is_e_load_001() {
        let mut graph = babylon_graph::hypergraph_store::HypergraphStore::new();
        let err = prepare_rules(
            D32_WIRING_PROBE_SCENARIO_WITH_EXPLICIT_REDECLARATION,
            None,
            D32_WIRING_PROBE_RULE,
            &mut graph,
        )
        .unwrap_err();
        assert!(err.contains("E-LOAD-001"), "{err}");
    }

    // Adversarial-verifier fix round, Fix 2: with TWO explicit re-declarations colliding against
    // the implicit seed set, the pre-fix loop iterated `type_env_fields()`'s HashMap directly and
    // returned on the first hit — so the refusal nondeterministically named either
    // `solidarity/strength` or `tenancy/strength` across runs (proven empirically over 64 runs).
    // Post-fix the seed pairs are byte-sorted before the collision check, so the refusal always
    // names the byte-least colliding qname. Pinned as an EXACT full-string assertion, looped over
    // fresh `prepare_rules` calls (each loop builds fresh HashMaps with fresh RandomState keys, so
    // a regression to unsorted iteration gets many chances to surface in one test run).
    const D32_TWO_COLLISION_SCENARIO: &str = r"
(scenario ft/d32-two-collision-probe
  (defvocabulary NodeType (SOCIAL_CLASS))
  (defvocabulary EdgeType (SOLIDARITY TENANCY))
  (deffield social-class/shape int extensive)
  (deffield solidarity/strength int extensive)
  (deffield tenancy/strength int extensive)
  (node core NodeType/SOCIAL_CLASS (social-class/shape 1))
  (node other NodeType/SOCIAL_CLASS (social-class/shape 1))
  (edge EdgeType/SOLIDARITY core other 1))
";

    #[test]
    fn a_two_collision_e_load_001_refusal_always_names_the_byte_least_field() {
        for _ in 0..20 {
            let mut graph = babylon_graph::hypergraph_store::HypergraphStore::new();
            let err = prepare_rules(
                D32_TWO_COLLISION_SCENARIO,
                None,
                D32_WIRING_PROBE_RULE,
                &mut graph,
            )
            .unwrap_err();
            assert_eq!(
                err,
                "E-LOAD-001: solidarity/strength is the implicit <edge-type>/strength field \
                 (D32) — re-declaring it with an explicit deffield is a duplicate declaration, \
                 never a silent override (bsl-language.rst §2.9)"
            );
        }
    }

    // G3(b) (#534 fix round 2): the "Task-10 detonation pin". The
    // organization foundation plan's own scenario shape
    // (docs/superpowers/plans/2026-08-11-organization-foundation-plan.md
    // Task 10, ~lines 443-480) declares NodeType/EdgeType vocabularies but
    // NEVER EventType, then its probe rule emits
    // `EventType/ORGANIZATION_SEEDED` from inside an emit form carrying a
    // payload item (`(probe 1)`) — the exact shape G1's tightened
    // `check_enum_ref_membership`/`find_deferred_shape_verb` now recurse
    // one level deeper into (each payload item's VALUE, not just its
    // LABEL). This proves the plan's own real-world content still loads
    // clean and fires through `run_once`, the actual production seam
    // (scenario hydration's F1 inertness for an opted-out EventType kind,
    // AND emit's own operand plus its payload value, all through one
    // pipeline) — not merely each walker's own isolated unit tests.
    const TASK_10_SCENARIO: &str = r"
(scenario organization/foundation-detonation-pin
  (defvocabulary NodeType (SOCIAL_CLASS ORGANIZATION))
  (defvocabulary EdgeType (MEMBERSHIP))
  (deffield organization/active int extensive)
  (node worker NodeType/SOCIAL_CLASS)
  (node cell NodeType/ORGANIZATION (organization/active 1))
  (edge EdgeType/MEMBERSHIP cell worker 1))
";
    const TASK_10_RULE: &str = r#"(rule organization/kind-probe
  :material-basis "Task 10's own probe rule shape (organization foundation plan) — EventType stays undeclared while NodeType/EdgeType are declared, proving hydration and the emit payload both leave an opted-out kind inert through the full production seam"
  :fuel 32
  (bindings (binding active :field organization/active))
  (when (= active 1))
  (effects (emit EventType/ORGANIZATION_SEEDED (probe 1))))"#;

    #[test]
    fn the_task_10_scenario_shape_loads_clean_and_fires_through_run_once() {
        let report = run_once(TASK_10_SCENARIO, TASK_10_RULE).expect(
            "EventType was never declared — its checking must stay inert, at both \
             hydration and the emit payload G1 now recurses into",
        );
        assert_eq!(
            report.fired, 1,
            "the probe rule must fire for exactly the one active organization"
        );
    }
}
