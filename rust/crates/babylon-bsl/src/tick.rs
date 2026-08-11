//! The tick: subject iteration over one loaded rule (P27 Phase 2 Slice 1).
//!
//! This is the loop the engine was missing. Every other piece existed —
//! [`crate::rule_pipeline::load_rule`] gates a rule, [`crate::evaluator`]
//! evaluates an expression, [`crate::structural_verbs::EffectExecutor`]
//! mutates a substrate — but nothing drove them over a world.
//!
//! **A rule does not loop; the engine does.** BSL rules are written against
//! `self` (`(update-node self social-class/agitation (add 0.05i))`), so the
//! rule states what happens to *one* subject and the engine applies it to
//! each in turn. That is why there is no `for-each` in the grammar.
//!
//! # The subject type, and how it is derived
//!
//! [`crate::bindings::BindSource::Field`]'s own contract is "a declared field
//! of **`self`'s node type**", so a rule's field bindings name their subject:
//! `social-class/wages` can only be read off a `social-class` node. Slice 1
//! therefore derives the subject type from the shared namespace of the
//! rule's `:field` bindings, and rejects a rule whose fields disagree —
//! because two namespaces mean two subject types, and picking one silently
//! would run the rule over the wrong population.
//!
//! **This is a slice-1 derivation, not a spec ruling.** The durable source
//! should be the `deffield` registry (Phase-2 content), which knows each
//! field's owning type without inference. Recorded here so the assumption is
//! visible rather than load-bearing-and-forgotten.
//!
//! # Determinism
//!
//! Subjects come from [`GraphSubstrate::nodes`], which is contractually
//! ascending by id, so the order rules fire in is fixed by the substrate and
//! not by storage.
//!
//! **Superseded (Task 12, P27 Phase 2 query-evaluation plan, 2026-08-11):**
//! this section used to say each subject reads through the same graph it
//! mutates and sees prior subjects' mutations, matching the frozen Python
//! engine's in-place behaviour. That was an admitted implementation/spec
//! divergence (D-row Q1), not a ruling — §4.2 chapter C4 says *"all firings
//! of one rule observe the same pre-state … and the effects they collect
//! are applied in that subject order."* [`run_tick`] now follows the spec:
//! it runs in two passes, collecting every subject's writes (via
//! [`crate::structural_verbs::EffectExecutor::collect_effects`]) against
//! the SAME pre-tick graph before applying any of them (via
//! [`crate::structural_verbs::EffectExecutor::apply_pending_write`]), in
//! subject order. Verified byte-neutral for every rule pack landed at the
//! time of the repair (`rust/crates/babylon-tick/tests/tick_goldens.rs`) —
//! none reads another node's field, so the divergence was unobservable
//! until a rule does.
//!
//! # Fuel
//!
//! Each subject gets its own budget, taken from the rule's DECLARED
//! `:fuel` — never from `static_bound`, which is `check_rule`'s computed
//! proof that the rule fits, not the allowance it runs under.
//!
//! The budget is per-SUBJECT because the §3.7 bound is per-subject:
//! `check_rule` accepted the rule against one subject's worth of work, so
//! sharing one meter across a population would make a rule's admissibility
//! depend on how many nodes happened to exist, which is not a property of
//! the rule.

use crate::bindings::{BindSource, BindingDecl};
use crate::evaluator::{evaluate, EvalEnv, EvalError, Value};
use crate::intrinsic_host::IntrinsicHost;
use crate::reader::{Atom, SExpr};
use crate::rule_pipeline::LoadedRule;
use crate::structural_verbs::{EffectExecutor, EventSink};
use crate::typecheck::TypeEnv;
use babylon_graph::substrate::{GraphSubstrate, NodeId};
use std::collections::HashMap;

/// Why a tick would not run.
#[derive(Debug, Clone, PartialEq)]
pub struct TickError {
    /// Human-readable detail.
    pub message: String,
}

impl std::fmt::Display for TickError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.message)
    }
}

impl std::error::Error for TickError {}

impl From<EvalError> for TickError {
    fn from(err: EvalError) -> Self {
        Self {
            message: format!("{err}"),
        }
    }
}

fn err(message: impl Into<String>) -> TickError {
    TickError {
        message: message.into(),
    }
}

/// What one tick did.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TickOutcome {
    /// The node type the rule ran over.
    pub subject_type: String,
    /// How many subjects the guard was evaluated against.
    pub considered: usize,
    /// How many passed the guard and had their effects executed.
    pub fired: usize,
}

/// The defines environment §4.2 names — coefficients by qualified name, the
/// values a `:const` binding reads (§2.5).
///
/// Its *contents* are content: `GameDefines`/`defines.yaml` in Phase 2, the
/// scenario's `(defconst …)` rows until then. Its *shape* belongs here
/// because the tick is where a coefficient meets a rule.
pub type DefinesEnv = HashMap<String, Value>;

/// `social-class` → `SOCIAL_CLASS`: the field namespace as a `NodeType`
/// member.
///
/// The verb layer stamps the enum member verbatim
/// (`(add-node NodeType/SOCIAL_CLASS …)` → `"SOCIAL_CLASS"`), and
/// [`crate::scenario`] mints the same, so this is the one conversion that
/// makes a rule's fields and the substrate's nodes name the same population.
///
/// `pub(crate)` (Task 8, P27 Phase 2 Slice 1): `evaluator::field_of_node`
/// needs the SAME rendering to compare a `field-of` qname's owning segment
/// against `GraphSubstrate::node_type_of`'s result (§2.10 discipline 1) —
/// reused rather than re-derived, so the two readings cannot drift apart.
pub(crate) fn namespace_to_node_type(namespace: &str) -> String {
    namespace.to_uppercase().replace('-', "_")
}

/// The subject type a rule's `:field` bindings agree on.
fn subject_type_of(bindings: &[BindingDecl]) -> Result<String, TickError> {
    let mut namespaces: Vec<&str> = Vec::new();
    for binding in bindings {
        if let BindSource::Field(qname) = &binding.source {
            let namespace = qname.split('/').next().unwrap_or_default();
            if !namespaces.contains(&namespace) {
                namespaces.push(namespace);
            }
        }
    }
    match namespaces.as_slice() {
        [] => Err(err(
            "the rule declares no :field binding, so it names no subject type — \
             slice 1 runs rules over a population, not over the graph as a whole",
        )),
        [one] => Ok(namespace_to_node_type(one)),
        many => Err(err(format!(
            "the rule's :field bindings span {} namespaces ({}), so its subject type \
             is ambiguous; a field is a field OF self's node type",
            many.len(),
            many.join(", ")
        ))),
    }
}

/// Pull `(when …)` and `(effects …)` out of a loaded rule form.
fn guard_and_effects(rule: &SExpr) -> Result<(Option<&SExpr>, &[SExpr]), TickError> {
    let SExpr::List(items) = rule else {
        return Err(err("a rule is a list form"));
    };
    let mut guard = None;
    let mut effects: &[SExpr] = &[];
    for item in items {
        let SExpr::List(parts) = item else { continue };
        let Some(SExpr::Atom(Atom::Symbol(tag))) = parts.first() else {
            continue;
        };
        match tag.as_str() {
            "when" => guard = parts.get(1),
            "effects" => effects = &parts[1..],
            _ => {}
        }
    }
    Ok((guard, effects))
}

/// Read one subject's **external** bindings out of the world.
///
/// An `:optional` binding with no stored value falls back to its declared
/// `:default`; a required one that was never written propagates the
/// substrate's loud error, because III.11 says absence is not zero.
///
/// The match over `<bind-src>` is **exhaustive on purpose**. It used to
/// read `let BindSource::Field(qname) = … else { continue };`, which
/// silently skipped every other source: a rule declaring a `:expr`, a
/// `:const`, a `:metric` or a calendar binding loaded clean and then died
/// at guard evaluation with a generic unbound-variable error — the
/// load-passes/execute-dies shape. Every arm now either produces a value or
/// is refused by [`check_sources_servable`] before any subject runs.
fn bind_subject(
    subject: NodeId,
    bindings: &[BindingDecl],
    graph: &dyn GraphSubstrate,
    defines: &DefinesEnv,
    tick: i64,
) -> Result<HashMap<String, Value>, TickError> {
    let mut env = HashMap::from([("self".to_owned(), Value::NodeRef(subject))]);
    for binding in bindings {
        let qname = match &binding.source {
            BindSource::Field(qname) => qname,
            // §2.5/§4.2: a coefficient out of the defines environment. The
            // value is the same for every subject, so this is a lookup
            // rather than a read — but it happens HERE, per subject, so that
            // one code path owns "what a binding resolves to".
            BindSource::Const(qname) => {
                let Some(value) = defines.get(qname) else {
                    // Unreachable when the vocabulary and the environment
                    // come from one scenario, which is what the message
                    // says: `resolve_bindings` already rejected an unknown
                    // qname with E-LOAD-010, and `check_sources_servable`
                    // already refused an unsupplied one at entry. Arriving
                    // here is a driver wiring bug, never content's fault.
                    return Err(err(format!(
                        "binding `{}`: :const {qname} resolved at load but the \
                         defines environment holds no value for it — the \
                         binding vocabulary and the defines environment have \
                         drifted apart",
                        binding.name
                    )));
                };
                env.insert(binding.name.clone(), value.clone());
                continue;
            }
            // §2.5: the current tick, as `Int`. The driver knows its own
            // tick number, so this is served rather than refused.
            BindSource::Tick => {
                env.insert(binding.name.clone(), Value::Int(tick));
                continue;
            }
            // `tick mod k` for a LITERAL k (D68), which needs only the tick.
            // `k > 0` is guaranteed by `E-PARSE-014` at load.
            BindSource::TickInCycle(length) => {
                env.insert(binding.name.clone(), Value::Int(tick.rem_euclid(*length)));
                continue;
            }
            // Resolved AFTER this pass, in declaration order, against the
            // external bindings above (§2.5/§4.2) — see `resolve_expr_bindings`.
            BindSource::Expr(_) => continue,
            // Refused at entry by `check_sources_servable`; reaching here
            // would mean that check and this match had drifted apart.
            BindSource::Metric(_) | BindSource::Year | BindSource::TickOfYear => {
                return Err(err(format!(
                    "binding `{}`: unservable source reached the subject loop —                      check_sources_servable and bind_subject have drifted",
                    binding.name
                )))
            }
        };
        let value = match graph.node_attribute(subject, qname) {
            Ok(value) => Value::Real(value),
            Err(graph_err) => {
                let Some(default) = binding.default.as_ref().filter(|_| binding.optional) else {
                    return Err(err(format!("subject {subject:?}: {}", graph_err.message)));
                };
                atom_to_value(default).ok_or_else(|| {
                    err(format!(
                        "binding `{}` has a :default that is not a numeric literal",
                        binding.name
                    ))
                })?
            }
        };
        env.insert(binding.name.clone(), value);
    }
    Ok(env)
}

fn atom_to_value(atom: &Atom) -> Option<Value> {
    match atom {
        Atom::Int(value) => Some(Value::Int(*value)),
        Atom::Scaled(scaled) => {
            // `unscaled / 10^scale`, the canonical minimal-scale form. Both
            // operands are exact in f64 at these magnitudes (scale <= 9).
            #[allow(clippy::cast_precision_loss)]
            let numerator = scaled.unscaled as f64;
            Some(Value::Real(
                numerator / 10_f64.powi(i32::from(scaled.scale)),
            ))
        }
        Atom::Bool(value) => Some(Value::Bool(*value)),
        _ => None,
    }
}

/// Refuse, **at entry and by name**, every `<bind-src>` slice 1 cannot
/// honestly serve (§2.5). The alternative — letting the subject loop skip
/// them — is the inert-no-caller shape: the rule loads, then dies mid-guard
/// with a generic unbound-variable error that names neither the source nor
/// the reason.
///
/// What slice 1 CAN serve, and why:
///
/// - `:field` — the substrate holds it.
/// - `:tick` and `:tick-in-cycle` — the driver knows its own tick number,
///   and D68's cycle length is a literal, so both are exact.
/// - `:expr` — self-contained: it needs only the bound environment, the
///   evaluator and the fuel meter, all of which the per-subject path has.
/// - `:const` — **when, and only when, the driver supplied the coefficient.**
///   §4.2 puts the defines environment in a rule's environment alongside the
///   graph and the tick, and the driver now passes one in. Until the Phase-2
///   `GameDefines`/`defines.yaml` registry exists, its contents are the
///   scenario's `(defconst …)` rows. A rule reading a coefficient the
///   environment does not hold is refused BY NAME below, never defaulted.
///
/// What it cannot, and why each is a *seam* rather than a bug:
///
/// - `:metric` — §2.11 metrics come from a registered kernel provider, and
///   slice 1 registers none.
/// - `:year` / `:tick-of-year` — §2.5 pins the epoch and the ticks-per-year
///   figure to the kernel's clock in the determinism contract, and slice 1
///   pins neither. Serving them would mean inventing a calendar, which is
///   exactly the guess III.11 forbids. `:tick`/`:tick-in-cycle` need no
///   epoch, which is why they are served and these are not.
fn check_sources_servable(bindings: &[BindingDecl], defines: &DefinesEnv) -> Result<(), TickError> {
    for binding in bindings {
        let reason = match &binding.source {
            // Servable exactly when the driver supplied the coefficient.
            // Checked AT ENTRY, by name, for the same reason as every other
            // row: a rule that dies mid-guard on an unbound variable names
            // neither the source nor the reason.
            BindSource::Const(qname) if !defines.contains_key(qname) => Some(format!(
                ":const {qname} — the driver supplied no such coefficient. The \
                 defines environment is the scenario's (defconst …) rows until \
                 the Phase-2 GameDefines/defines.yaml registry lands"
            )),
            BindSource::Metric(name) => Some(format!(
                ":metric {name} — slice 1 registers no metric provider; §2.11 \
                 providers are Phase-2 kernel services"
            )),
            BindSource::Year => Some(
                ":year — slice 1 pins no epoch; §2.5 puts the epoch and the \
                 ticks-per-year figure in the kernel's clock (determinism \
                 contract), and inventing one here would be a guess"
                    .to_owned(),
            ),
            BindSource::TickOfYear => Some(
                ":tick-of-year — slice 1 pins no ticks-per-year figure (§2.5, \
                 as for :year)"
                    .to_owned(),
            ),
            // Every servable source, including a `:const` the driver DID
            // supply — the guard arm above owns the unsupplied case.
            BindSource::Const(_)
            | BindSource::Field(_)
            | BindSource::Tick
            | BindSource::TickInCycle(_)
            | BindSource::Expr(_) => None,
        };
        if let Some(reason) = reason {
            return Err(err(format!(
                "binding `{}` is not servable in slice 1: {reason}",
                binding.name
            )));
        }
    }
    Ok(())
}

/// Run one rule over every subject of its type.
///
/// **The §4.2 chapter C4 pre-state law (Task 12, P27 Phase 2 query-
/// evaluation plan):** *"All firings of one rule observe the same
/// pre-state … and the effects they collect are applied in that subject
/// order."* This function runs in two passes over `subjects` rather than
/// one, and that split IS the repair, not an optimisation:
///
/// - **Pass 1 — collect.** `graph` is borrowed IMMUTABLY only, for this
///   WHOLE pass (`env.graph = Some(&*graph)`, held per subject but never
///   invalidated by a write, because nothing in this pass performs one).
///   Every subject's guard and effects (via
///   [`crate::structural_verbs::EffectExecutor::collect_effects`]) evaluate
///   against the SAME, unchanged graph — which is what makes "every firing
///   observes the same pre-state" a property of the borrow, not a
///   convention a caller could violate by forgetting to re-read. `update-
///   node`'s writes come out as [`crate::structural_verbs::PendingWrite`]s,
///   appended to one flat, RULE-wide list in subject order.
/// - **Pass 2 — apply.** The immutable borrow above has ended (Pass 1
///   returned), so `graph` is now borrowed mutably. Each collected write
///   applies in the order it was collected — subject order outer, source
///   order inner, by construction of the flat list — and `add`/`sub`/
///   `scale` read the target's CURRENT value HERE, at apply time (D-row
///   Q2), which is what lets several subjects each contribute to one
///   shared carrier without losing any contribution.
///
/// **Scope.** Only `update-node` participates in this two-pass split.
/// `emit`, `guard` and `for-each` are served inside Pass 1 (`emit` never
/// touches the graph; its payload evaluates against the same pre-state).
/// The six graph-shape verbs (`add-node`, `remove-node`, `add-edge`,
/// `remove-edge`, `add-hyperedge`, `remove-hyperedge`) are NOT served by
/// this function — nothing in the landed rule-pack estate uses them
/// (verified by grep over `rust/crates/babylon-tick/content/rules/*.bsl`),
/// and correctly deferring a MINTING verb needs a placeholder-id scheme
/// this plan does not specify. A rule that needs one is a declared,
/// escalated gap — see `EffectExecutor::collect_effects`'s own doc.
///
/// # Errors
///
/// [`TickError`] if the subject type cannot be derived, a rule reads a
/// coefficient `defines` does not hold, a required field was never written,
/// the guard does not evaluate to a `Bool`, evaluation or collection fails,
/// or a collected write fails to apply.
#[allow(clippy::too_many_arguments)]
pub fn run_tick(
    loaded: &LoadedRule,
    types: &TypeEnv,
    host: &dyn IntrinsicHost,
    graph: &mut dyn GraphSubstrate,
    sink: &mut dyn EventSink,
    costs: &crate::fuel::IntrinsicCosts,
    defines: &DefinesEnv,
    tick: i64,
) -> Result<TickOutcome, TickError> {
    check_sources_servable(&loaded.bindings, defines)?;
    let subject_type = subject_type_of(&loaded.bindings)?;
    let (guard, effects) = guard_and_effects(&loaded.rule)?;
    let subjects = graph.nodes(&subject_type);
    let mut fired = 0_usize;
    let mut all_pending: Vec<crate::structural_verbs::PendingWrite> = Vec::new();

    // ---- Pass 1: collect, against the SAME pre-tick state for every
    // subject (`graph` is never mutated in this loop). ----
    for subject in &subjects {
        let mut values = bind_subject(*subject, &loaded.bindings, &*graph, defines, tick)?;
        // Per-subject budget, from the rule's DECLARED `:fuel` — not from
        // `static_bound`, which is the load-time proof that the rule fits
        // rather than the allowance it runs under. Metering on the computed
        // bound would couple runtime to whatever the checker returns and
        // would under-fund a rule whose author allotted more.
        //
        // Per SUBJECT, because the §3.7 bound is per-subject: one shared
        // meter would make a rule's admissibility depend on how many nodes
        // happened to exist, which is not a property of the rule.
        let mut fuel = loaded.declared_fuel;

        // §2.5/§4.2: `:expr` bindings resolve in DECLARATION order against
        // the bindings already resolved, and §4.5 charges each expression
        // ONCE, through this subject's meter. Doing it here — after the
        // external sources, before the guard — is what makes a computed
        // binding an abbreviation rather than a sequencing construct: it
        // cannot observe an effect, because no effect has run.
        crate::rule_pipeline::resolve_expr_bindings(
            &loaded.bindings,
            &mut values,
            costs,
            host,
            &mut fuel,
        )?;
        let env = EvalEnv {
            bindings: values,
            intrinsic_costs: costs,
            // Task 12 lands this: `env.graph` is now a real, live reference
            // — safe to hold alongside `graph`'s later mutable use (Pass 2)
            // precisely because Pass 1 never performs one. The old aliasing
            // conflict this comment used to describe (`Some(&*graph)` here
            // colliding with `execute_effects`'s `&mut` below) is gone
            // because Pass 1 calls `collect_effects`, which takes no
            // mutable graph at all.
            graph: Some(&*graph),
            elements: Vec::new(),
        };

        if let Some(guard) = guard {
            match evaluate(guard, &env, host, &mut fuel)? {
                Value::Bool(true) => {}
                Value::Bool(false) => continue,
                other => {
                    return Err(err(format!(
                        "a (when …) guard must evaluate to Bool, got {other:?}"
                    )))
                }
            }
        }

        let mut executor = EffectExecutor::new(types);
        let pending = executor.collect_effects(effects, &env, host, sink, &mut fuel)?;
        all_pending.extend(pending);
        fired += 1;
    }

    // ---- Pass 2: apply, in the order collected (subject order outer,
    // source order inner) — `graph` is mutable again, the Pass-1 immutable
    // borrow having already ended. ----
    let mut applier = EffectExecutor::new(types);
    for write in &all_pending {
        applier.apply_pending_write(write, graph)?;
    }

    Ok(TickOutcome {
        subject_type,
        considered: subjects.len(),
        fired,
    })
}

#[cfg(test)]
mod tests {
    use super::{check_sources_servable, run_tick, subject_type_of, DefinesEnv};
    use crate::bindings::{BindSource, BindingDecl};
    use crate::evaluator::Value;
    use std::collections::HashMap;
    fn field(name: &str, qname: &str) -> BindingDecl {
        BindingDecl {
            name: name.to_owned(),
            source: BindSource::Field(qname.to_owned()),
            optional: false,
            default: None,
        }
    }

    fn constant(name: &str, qname: &str) -> BindingDecl {
        BindingDecl {
            name: name.to_owned(),
            source: BindSource::Const(qname.to_owned()),
            optional: false,
            default: None,
        }
    }

    #[test]
    fn a_const_the_driver_supplied_is_servable() {
        let env = DefinesEnv::from([("economy/base-subsistence".to_owned(), Value::Real(0.0005))]);
        assert!(check_sources_servable(
            &[constant("base-subsistence", "economy/base-subsistence")],
            &env
        )
        .is_ok());
    }

    #[test]
    fn a_const_the_driver_did_not_supply_is_refused_by_name_at_entry() {
        // Refused AT ENTRY rather than at the read: a rule that dies
        // mid-guard on an unbound variable names neither the source nor the
        // reason, and a defaulted coefficient would be silent degradation.
        let err = check_sources_servable(
            &[constant("floor-wage", "economy/floor-wage")],
            &DefinesEnv::new(),
        )
        .unwrap_err();
        assert!(
            err.message.contains("economy/floor-wage"),
            "{}",
            err.message
        );
        assert!(
            err.message.contains("supplied no such coefficient"),
            "{}",
            err.message
        );
    }

    #[test]
    fn the_calendar_sources_needing_an_epoch_stay_refused() {
        // A defines environment does not buy `:year` — §2.5 puts the epoch
        // and the ticks-per-year figure in the kernel's clock, and this
        // driver pins neither. Guards the const change against widening the
        // refusal set by accident.
        for source in [BindSource::Year, BindSource::TickOfYear] {
            let decl = BindingDecl {
                name: "when".to_owned(),
                source,
                optional: false,
                default: None,
            };
            assert!(check_sources_servable(&[decl], &DefinesEnv::new()).is_err());
        }
    }

    #[test]
    fn the_subject_type_comes_from_the_field_namespace() {
        let bindings = vec![
            field("wages", "social-class/wages"),
            field("value-produced", "social-class/value-produced"),
        ];
        assert_eq!(subject_type_of(&bindings).unwrap(), "SOCIAL_CLASS");
    }

    #[test]
    fn fields_spanning_two_namespaces_are_ambiguous_not_guessed() {
        // Two namespaces mean two subject types; picking one silently would
        // run the rule over the wrong population.
        let bindings = vec![
            field("wages", "social-class/wages"),
            field("budget", "organization/budget"),
        ];
        let err = subject_type_of(&bindings).unwrap_err();
        assert!(err.message.contains("ambiguous"), "{}", err.message);
    }

    #[test]
    fn a_rule_with_no_field_binding_names_no_population() {
        let err = subject_type_of(&[]).unwrap_err();
        assert!(
            err.message.contains("names no subject type"),
            "{}",
            err.message
        );
    }

    // ============================================= Task 12 — the pre-state
    // law: collect-then-apply, within and across firings (§4.2 chapter C4).

    /// A minimal, hand-built `LoadContext` — no scenario text, no `deffield`
    /// forms; the world is built directly against `MemoryGraph` and the
    /// field registry is a plain `TypeEnv`, exactly as
    /// `fundamental_theorem_tick.rs` (the crate's own end-to-end template)
    /// does. `vocabulary_registry: None` skips the closed-vocabulary checks
    /// that need a registry this test has no reason to build.
    struct Fixture {
        types: crate::typecheck::TypeEnv,
        vocabulary: crate::bindings::BindingVocabulary,
        ceilings: crate::fuel::CardinalityCeilings,
        intrinsics: crate::fuel::IntrinsicCosts,
        systems: std::collections::HashSet<String>,
    }

    impl Fixture {
        fn new(
            fields: std::collections::HashMap<String, crate::types::FieldDecl>,
            edge_ceilings: std::collections::HashMap<String, u64>,
        ) -> Self {
            let types = crate::typecheck::TypeEnv {
                fields,
                exemptions: &[],
            };
            let vocabulary = crate::bindings::BindingVocabulary {
                fields: types.fields.keys().cloned().collect(),
                consts: std::collections::HashSet::new(),
                metrics: std::collections::HashSet::new(),
            };
            Self {
                types,
                vocabulary,
                ceilings: crate::fuel::CardinalityCeilings::new(edge_ceilings, HashMap::new()),
                intrinsics: crate::fuel::IntrinsicCosts::default(),
                systems: std::collections::HashSet::from(["geography".to_owned()]),
            }
        }

        fn load(&self, rule_source: &str, rule_file: &str) -> crate::rule_pipeline::LoadedRule {
            let ctx = crate::rule_pipeline::LoadContext {
                vocabulary: &self.vocabulary,
                types: &self.types,
                ceilings: &self.ceilings,
                intrinsics: &self.intrinsics,
                systems: &self.systems,
                vocabulary_registry: None,
                rule_file,
            };
            crate::rule_pipeline::load_rule(rule_source, &ctx)
                .expect("the rule must pass every load gate")
        }
    }

    fn territory_field(kind: crate::types::FieldKind) -> crate::types::FieldDecl {
        crate::types::FieldDecl {
            ty: crate::types::BslType::Int,
            kind,
        }
    }

    /// §4.2 chapter C4, quoted in the plan: "All firings of one rule
    /// observe the same pre-state … and the effects they collect are
    /// applied in that subject order." Two TERRITORY nodes, `a` (lower id)
    /// and `b` (higher id), joined by ONE `ADJACENCY` edge `a -> b` (so
    /// each is in the other's `:any` neighbourhood) — the Territory
    /// Phase-3 spillover shape (`fold sum` over `neighbors`' `heat`).
    ///
    /// Under IN-PLACE semantics (the pre-Task-12 defect, admitted in this
    /// module's own doc before this task): `a` fires first (ascending
    /// subject id), applies immediately, then `b` fires and reads `a`'s
    /// ALREADY-UPDATED heat — 100 + 110 = 210. Under §4.2 C4, `b` reads
    /// `a`'s PRE-TICK heat — 100 + 10 = 110, matching `a`'s own 10 + 100 =
    /// 110 exactly (both firings observed the SAME pre-state).
    #[test]
    fn all_firings_of_one_rule_observe_the_same_pre_state() {
        use babylon_graph::memory::MemoryGraph;
        use babylon_graph::substrate::GraphSubstrate;

        let mut graph = MemoryGraph::new();
        let a = graph.add_node("TERRITORY").unwrap();
        let b = graph.add_node("TERRITORY").unwrap();
        graph.update_node(a, "territory/heat", 10.0).unwrap();
        graph.update_node(b, "territory/heat", 100.0).unwrap();
        graph.add_edge("ADJACENCY", a, b, 1.0).unwrap();

        let fixture = Fixture::new(
            HashMap::from([(
                "territory/heat".to_owned(),
                territory_field(crate::types::FieldKind::Extensive),
            )]),
            HashMap::from([
                ("NodeType/TERRITORY".to_owned(), 100),
                ("EdgeType/ADJACENCY".to_owned(), 100),
            ]),
        );
        let loaded = fixture.load(
            r#"
(rule geography/spillover
  :material-basis "adjacent territories exchange heat; every firing of one rule observes the same pre-state (§4.2 chapter C4)"
  :fuel 256
  (bindings
    (binding heat :field territory/heat))
  (effects
    (update-node self territory/heat
      (add (fold sum (neighbors self EdgeType/ADJACENCY :any NodeType/TERRITORY)
                 (field-of it territory/heat))))))
"#,
            "geography/spillover.bsl",
        );

        let mut sink = crate::structural_verbs::CollectingSink::default();
        run_tick(
            &loaded,
            &fixture.types,
            &crate::intrinsic_host::EmptyIntrinsicHost,
            &mut graph,
            &mut sink,
            &fixture.intrinsics,
            &DefinesEnv::new(),
            1,
        )
        .expect("the tick must run");

        let a_heat = graph.node_attribute(a, "territory/heat").unwrap();
        let b_heat = graph.node_attribute(b, "territory/heat").unwrap();
        assert!(
            (a_heat - 110.0).abs() < 1e-9,
            "a's own 10 + b's PRE-TICK 100 = 110, got {a_heat}"
        );
        assert!(
            (b_heat - 110.0).abs() < 1e-9,
            "b's own 100 + a's PRE-TICK 10 = 110 — NOT 210, which is what \
             in-place semantics would compute by reading a's \
             ALREADY-UPDATED heat; got {b_heat}"
        );
    }

    /// The §6.2 family-12 accumulation vector: three TERRITORY subjects
    /// (`s1`, `s2`, `s3`, ascending id) each `(add …)` to ONE shared
    /// carrier — an `ORGANIZATION` node reached via each subject's own
    /// outgoing `ADJACENCY` edge (an `ORGANIZATION` carrier is never itself
    /// a `TERRITORY` subject, so no guard is needed to exclude it from the
    /// population). Values `1e16, 1.0, -1e16` are the SAME non-associative
    /// triple `fold_reduces_in_iteration_order_and_the_order_is_observable`
    /// (`evaluator.rs`) already pins: applied in ascending SUBJECT order,
    /// `(1e16 + 1.0) + -1e16 == 0.0`, not `1.0` — proving both that `add`
    /// reads the target's CURRENT value at APPLY time (D-row Q2: a
    /// collect-time read would have every subject read the carrier's
    /// UNCHANGED initial 0.0 and the last applied write would win, losing
    /// two of the three contributions) and that the binary64 reduction
    /// order follows subject order.
    #[test]
    fn accumulation_into_a_shared_target_reduces_in_subject_order_and_keeps_every_contribution() {
        use babylon_graph::memory::MemoryGraph;
        use babylon_graph::substrate::GraphSubstrate;

        let mut graph = MemoryGraph::new();
        let carrier = graph.add_node("ORGANIZATION").unwrap();
        graph
            .update_node(carrier, "organization/pool", 0.0)
            .unwrap();
        for contribution in [1.0e16, 1.0, -1.0e16] {
            let subject = graph.add_node("TERRITORY").unwrap();
            graph
                .update_node(subject, "territory/contribution", contribution)
                .unwrap();
            graph.add_edge("ADJACENCY", subject, carrier, 1.0).unwrap();
        }

        let fixture = Fixture::new(
            HashMap::from([
                (
                    "territory/contribution".to_owned(),
                    territory_field(crate::types::FieldKind::Extensive),
                ),
                (
                    "organization/pool".to_owned(),
                    territory_field(crate::types::FieldKind::Extensive),
                ),
            ]),
            HashMap::from([
                ("NodeType/TERRITORY".to_owned(), 100),
                ("NodeType/ORGANIZATION".to_owned(), 100),
                ("EdgeType/ADJACENCY".to_owned(), 100),
            ]),
        );
        let loaded = fixture.load(
            r#"
(rule geography/pool-contribution
  :material-basis "each territory contributes its share to a shared regional pool; the pool must count every contribution, computed at apply time (D-row Q2)"
  :fuel 256
  (bindings
    (binding contribution :field territory/contribution))
  (effects
    (update-node
      (select-max (neighbors self EdgeType/ADJACENCY :out NodeType/ORGANIZATION) 1)
      organization/pool
      (add contribution))))
"#,
            "geography/pool-contribution.bsl",
        );

        let mut sink = crate::structural_verbs::CollectingSink::default();
        let outcome = run_tick(
            &loaded,
            &fixture.types,
            &crate::intrinsic_host::EmptyIntrinsicHost,
            &mut graph,
            &mut sink,
            &fixture.intrinsics,
            &DefinesEnv::new(),
            1,
        )
        .expect("the tick must run");
        assert_eq!(outcome.fired, 3, "all three territories fired");

        let pool = graph.node_attribute(carrier, "organization/pool").unwrap();
        // Exact IEEE-754 equality, deliberately (§4.3): the basic ops are
        // correctly rounded and reproduce bit-exactly, so an epsilon margin
        // here would obscure precisely the reduction-order property this
        // test exists to pin — the same reasoning `apply_equality`'s own
        // exact-comparison arm documents (evaluator.rs).
        #[allow(clippy::float_cmp)]
        let exact = pool == 0.0;
        assert!(
            exact,
            "(1e16 + 1.0) + -1e16 == 0.0 in ascending subject order — every \
             contribution counted, none lost, and the SAME bits the fold \
             reduction-order test already pins, got {pool}"
        );
    }
}
