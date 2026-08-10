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
//! not by storage. **Each subject reads through the same graph it mutates**,
//! in subject order — matching the frozen Python engine's documented
//! behaviour that systems mutate a shared graph in place and each sees prior
//! mutations. Snapshot semantics would be a different model and would need a
//! ruling; slice 1 does not quietly invent one.
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

/// `social-class` → `SOCIAL_CLASS`: the field namespace as a `NodeType`
/// member.
///
/// The verb layer stamps the enum member verbatim
/// (`(add-node NodeType/SOCIAL_CLASS …)` → `"SOCIAL_CLASS"`), and
/// [`crate::scenario`] mints the same, so this is the one conversion that
/// makes a rule's fields and the substrate's nodes name the same population.
fn namespace_to_node_type(namespace: &str) -> String {
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
    tick: i64,
) -> Result<HashMap<String, Value>, TickError> {
    let mut env = HashMap::from([("self".to_owned(), Value::NodeRef(subject))]);
    for binding in bindings {
        let qname = match &binding.source {
            BindSource::Field(qname) => qname,
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
            BindSource::Const(_) | BindSource::Metric(_) | BindSource::Year
            | BindSource::TickOfYear => {
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
///
/// What it cannot, and why each is a *seam* rather than a bug:
///
/// - `:const` — the defines environment is Phase-2 content
///   (`GameDefines`/`defines.yaml`); slice 1 has no coefficient registry.
/// - `:metric` — §2.11 metrics come from a registered kernel provider, and
///   slice 1 registers none.
/// - `:year` / `:tick-of-year` — §2.5 pins the epoch and the ticks-per-year
///   figure to the kernel's clock in the determinism contract, and slice 1
///   pins neither. Serving them would mean inventing a calendar, which is
///   exactly the guess III.11 forbids. `:tick`/`:tick-in-cycle` need no
///   epoch, which is why they are served and these are not.
fn check_sources_servable(bindings: &[BindingDecl]) -> Result<(), TickError> {
    for binding in bindings {
        let reason = match &binding.source {
            BindSource::Const(qname) => Some(format!(
                ":const {qname} — slice 1 has no defines environment; the \
                 coefficient registry is Phase-2 content (GameDefines/defines.yaml)"
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
            BindSource::Field(_)
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
/// # Errors
///
/// [`TickError`] if the subject type cannot be derived, a required field was
/// never written, the guard does not evaluate to a `Bool`, or evaluation or
/// an effect fails.
#[allow(clippy::too_many_arguments)]
pub fn run_tick(
    loaded: &LoadedRule,
    types: &TypeEnv,
    host: &dyn IntrinsicHost,
    graph: &mut dyn GraphSubstrate,
    sink: &mut dyn EventSink,
    costs: &crate::fuel::IntrinsicCosts,
    tick: i64,
) -> Result<TickOutcome, TickError> {
    check_sources_servable(&loaded.bindings)?;
    let subject_type = subject_type_of(&loaded.bindings)?;
    let (guard, effects) = guard_and_effects(&loaded.rule)?;
    let subjects = graph.nodes(&subject_type);
    let mut fired = 0_usize;

    for subject in &subjects {
        let mut values = bind_subject(*subject, &loaded.bindings, &*graph, tick)?;
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
        executor.execute_effects(effects, &env, host, graph, sink, &mut fuel)?;
        fired += 1;
    }

    Ok(TickOutcome {
        subject_type,
        considered: subjects.len(),
        fired,
    })
}

#[cfg(test)]
mod tests {
    use super::subject_type_of;
    use crate::bindings::{BindSource, BindingDecl};
    fn field(name: &str, qname: &str) -> BindingDecl {
        BindingDecl {
            name: name.to_owned(),
            source: BindSource::Field(qname.to_owned()),
            optional: false,
            default: None,
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
}
