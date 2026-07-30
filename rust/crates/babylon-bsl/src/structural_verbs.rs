//! The typed structural verb algebra (`bsl-language.rst` §2.8): the seven
//! graph verbs plus `emit`, executed against any
//! [`babylon_graph::substrate::GraphSubstrate`] — in Phase 1 that means
//! `PlaceholderGraph`; the production store swaps in at the Phase 1/2
//! boundary. This is the crate-DAG edge Task 11 planned: `babylon-bsl` now
//! depends on `babylon-graph`.
//!
//! **No clique expansion exists in this module** and none may be added: a
//! member list is handed to `GraphSubstrate::add_hyperedge` whole — that is
//! Anti-Pattern VIII.9 enforced where the verbs live. There is deliberately
//! no `add-member`/`remove-member`/`update-hyperedge`: membership change is
//! whole-hyperedge replacement, `remove-hyperedge` then `add-hyperedge` in
//! one effect list (§2.8 draft ruling).
//!
//! **Id operands are effect-list-scoped names** (draft ruling recorded in
//! §2.8, implementation-discovered): `add-node`/`add-hyperedge`'s id
//! operand is read as a symbol naming the minted object for the rest of the
//! effect list — the substrate mints the actual identity; roster
//! replacement referencing the new hyperedge needs exactly this.
//!
//! Discipline held here, not invented here:
//! - Effects apply in **source order** (§2.8); `guard` evaluates only the
//!   taken branch (§4.1) and charges accordingly.
//! - Substrate failures surface as `E-EVAL-031` — removing what does not
//!   exist, adding what exists, unknown/duplicate members: absence is never
//!   success, and nothing is silently deduplicated.
//! - The **store boundary** runs §3.3's one range check: a written value
//!   outside the target field's declared `[0,1]` domain is `E-EVAL-020`, a
//!   loud failure, never a clamp.
//! - Fuel: verbs charge their §3.7 base cost (3), update-ops theirs (1),
//!   operand expressions charge through the Task 14 evaluator — one §4.5
//!   meter end to end.
//! - I.15's edge-mode transition law and typed attribute storage (Currency
//!   i128 exactness — the trait's `f64` attributes cannot hold it, so a
//!   Currency-typed write is a LOUD error, not a lossy cast) are declared
//!   Phase-2 gaps, named here rather than silently absorbed.

use crate::evaluator::{charge, evaluate, EvalCode, EvalEnv, EvalError, Value};
use crate::fuel::cost;
use crate::intrinsic_host::IntrinsicHost;
use crate::reader::{Atom, SExpr};
use crate::typecheck::TypeEnv;
use crate::types::BslType;
use babylon_graph::substrate::{GraphError, GraphSubstrate, HyperedgeId, NodeId};
use std::collections::HashMap;

/// Where `emit` lands (§2.8): an event sink the engine wires to the kernel
/// event bus (Phase 3). Payload values are already evaluated.
pub trait EventSink {
    /// Record one emitted event.
    fn emit(&mut self, event_type: &str, payload: Vec<(String, Value)>);
}

/// A sink that simply collects, for tests and the conformance corpus.
#[derive(Debug, Default)]
pub struct CollectingSink {
    /// Every event emitted, in source order.
    pub events: Vec<(String, Vec<(String, Value)>)>,
}

impl EventSink for CollectingSink {
    fn emit(&mut self, event_type: &str, payload: Vec<(String, Value)>) {
        self.events.push((event_type.to_owned(), payload));
    }
}

fn plain(message: impl Into<String>) -> EvalError {
    EvalError::plain(message)
}

fn from_graph(e: GraphError) -> EvalError {
    // Every GraphSubstrate failure is the §2.8 existence discipline:
    // absence is never success, presence is never overwritten, a member
    // list is a set (E-EVAL-031).
    EvalError::coded(EvalCode::ExistenceDiscipline, e.message)
}

/// Executes one rule's effect list against a substrate, carrying the
/// effect-list-scoped names `add-node`/`add-hyperedge` introduce.
pub struct EffectExecutor<'a> {
    types: &'a TypeEnv,
    declared_nodes: HashMap<String, NodeId>,
    declared_hyperedges: HashMap<String, HyperedgeId>,
}

impl<'a> EffectExecutor<'a> {
    /// A fresh executor for one effect list. `types` supplies the declared
    /// field types the §3.3 store-boundary range check needs.
    #[must_use]
    pub fn new(types: &'a TypeEnv) -> Self {
        Self {
            types,
            declared_nodes: HashMap::new(),
            declared_hyperedges: HashMap::new(),
        }
    }

    /// Execute the items of an `(effects …)` form in source order (§2.8).
    ///
    /// # Errors
    ///
    /// Any [`EvalError`] an operand expression raises, `E-EVAL-031` from
    /// the substrate's existence discipline, `E-EVAL-020` from the store
    /// boundary, `E-EVAL-040` from the shared fuel meter, and loud uncoded
    /// errors for shapes off the §2.8 grammar.
    #[allow(clippy::too_many_arguments)]
    pub fn execute_effects(
        &mut self,
        effect_items: &[SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        graph: &mut dyn GraphSubstrate,
        sink: &mut dyn EventSink,
        fuel: &mut u64,
    ) -> Result<(), EvalError> {
        for item in effect_items {
            self.execute_item(item, env, host, graph, sink, fuel)?;
        }
        Ok(())
    }

    #[allow(clippy::too_many_arguments)]
    fn execute_item(
        &mut self,
        item: &SExpr,
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        graph: &mut dyn GraphSubstrate,
        sink: &mut dyn EventSink,
        fuel: &mut u64,
    ) -> Result<(), EvalError> {
        let SExpr::List(items) = item else {
            return Err(plain(format!(
                "an effect item must be a form, found {item:?}"
            )));
        };
        let Some(SExpr::Atom(Atom::Symbol(head))) = items.first() else {
            return Err(plain(format!(
                "an effect item must be a verb or guard form, found {:?}",
                items.first()
            )));
        };
        match head.as_str() {
            "guard" => {
                // cost(guard) base, then only the taken branch (§4.1).
                charge(fuel, cost::GUARD_BASE)?;
                let [_, cond, nested @ ..] = items.as_slice() else {
                    return Err(plain("(guard <cond> <effect-item>+) — missing condition"));
                };
                if nested.is_empty() {
                    return Err(plain("(guard …) requires at least one effect item"));
                }
                let taken = matches!(evaluate(cond, env, host, fuel)?, Value::Bool(true));
                if taken {
                    for nested_item in nested {
                        self.execute_item(nested_item, env, host, graph, sink, fuel)?;
                    }
                }
                Ok(())
            }
            "update-node" => self.update_node(items, env, host, graph, fuel),
            "add-node" => self.add_node(items, env, host, graph, fuel),
            "remove-node" => {
                charge(fuel, cost::STRUCTURAL_VERB_BASE)?;
                let [_, node] = items.as_slice() else {
                    return Err(plain("(remove-node <expr>) takes exactly one operand"));
                };
                let id = self.resolve_node(node, env, host, fuel)?;
                graph.remove_node(id).map_err(from_graph)
            }
            "add-edge" => self.add_edge(items, env, host, graph, fuel),
            "remove-edge" => self.remove_edge(items, env, host, graph, fuel),
            "add-hyperedge" => self.add_hyperedge(items, env, host, graph, fuel),
            "remove-hyperedge" => {
                charge(fuel, cost::STRUCTURAL_VERB_BASE)?;
                let [_, h] = items.as_slice() else {
                    return Err(plain("(remove-hyperedge <expr>) takes exactly one operand"));
                };
                let id = self.resolve_hyperedge(h, env, host, fuel)?;
                graph.remove_hyperedge(id).map_err(from_graph)
            }
            "emit" => Self::emit(items, env, host, sink, fuel),
            other => Err(plain(format!(
                "unknown effect head ({other} …) — the §2.8 verb set is closed"
            ))),
        }
    }

    /// `(update-node <expr> <qname> <update-op>)` — read-modify-write under
    /// the §3.3 store-boundary range check.
    fn update_node(
        &mut self,
        items: &[SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        graph: &mut dyn GraphSubstrate,
        fuel: &mut u64,
    ) -> Result<(), EvalError> {
        charge(fuel, cost::STRUCTURAL_VERB_BASE)?;
        let [_, node, SExpr::Atom(Atom::QName(field)), op_form] = items else {
            return Err(plain(
                "(update-node <expr> <qname> <update-op>) — unrecognized shape",
            ));
        };
        let id = self.resolve_node(node, env, host, fuel)?;
        let SExpr::List(op_items) = op_form else {
            return Err(plain(
                "update-op must be a form: (add|sub|set|scale <expr>)",
            ));
        };
        let [SExpr::Atom(Atom::Symbol(op)), operand] = op_items.as_slice() else {
            return Err(plain("update-op must be (add|sub|set|scale <expr>)"));
        };
        charge(fuel, cost::UPDATE_OP_BASE)?;
        let operand_value = Self::numeric_write_value(operand, env, host, fuel, field)?;
        let new_value = match op.as_str() {
            "set" => operand_value,
            "add" | "sub" | "scale" => {
                let current = graph.node_attribute(id, field).map_err(from_graph)?;
                let combined = match op.as_str() {
                    "add" => current + operand_value,
                    "sub" => current - operand_value,
                    _ => current * operand_value,
                };
                if !combined.is_finite() {
                    return Err(EvalError::coded(
                        EvalCode::NonFinite,
                        format!("({op} …) on {field} produced a non-finite value"),
                    ));
                }
                combined
            }
            other => {
                return Err(plain(format!(
                    "unknown update-op ({other} …) — the set is add|sub|set|scale (§2.8)"
                )))
            }
        };
        self.store_range_check(field, new_value)?;
        graph.update_node(id, field, new_value).map_err(from_graph)
    }

    /// `(add-node <enum-ref> <expr> <field-init>*)`.
    fn add_node(
        &mut self,
        items: &[SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        graph: &mut dyn GraphSubstrate,
        fuel: &mut u64,
    ) -> Result<(), EvalError> {
        charge(fuel, cost::STRUCTURAL_VERB_BASE)?;
        let [_, type_ref, id_expr, field_inits @ ..] = items else {
            return Err(plain(
                "(add-node <enum-ref> <expr> <field-init>*) — too few operands",
            ));
        };
        let node_type = Self::enum_member(type_ref)?;
        let name = self.fresh_declared_name(id_expr, env)?;
        let id = graph.add_node(node_type).map_err(from_graph)?;
        self.declared_nodes.insert(name, id);
        for init in field_inits {
            let SExpr::List(pair) = init else {
                return Err(plain(format!(
                    "a field-init must be (<qname> <expr>), found {init:?}"
                )));
            };
            let [SExpr::Atom(Atom::QName(field)), value_expr] = pair.as_slice() else {
                return Err(plain(format!(
                    "a field-init must be (<qname> <expr>), found {pair:?}"
                )));
            };
            let value = Self::numeric_write_value(value_expr, env, host, fuel, field)?;
            self.store_range_check(field, value)?;
            graph.update_node(id, field, value).map_err(from_graph)?;
        }
        Ok(())
    }

    /// `(add-edge <enum-ref> <expr> <expr> :strength <expr>)`.
    fn add_edge(
        &mut self,
        items: &[SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        graph: &mut dyn GraphSubstrate,
        fuel: &mut u64,
    ) -> Result<(), EvalError> {
        charge(fuel, cost::STRUCTURAL_VERB_BASE)?;
        let [_, type_ref, from, to, SExpr::Atom(Atom::Keyword(kw)), strength_expr] = items else {
            return Err(plain(
                "(add-edge <enum-ref> <expr> <expr> :strength <expr>) — unrecognized shape",
            ));
        };
        if kw != "strength" {
            return Err(plain(format!("add-edge requires :strength, found :{kw}")));
        }
        let edge_type = Self::enum_member(type_ref)?;
        let from_id = self.resolve_node(from, env, host, fuel)?;
        let to_id = self.resolve_node(to, env, host, fuel)?;
        let strength = match evaluate(strength_expr, env, host, fuel)? {
            Value::Real(r) => r,
            other => {
                return Err(plain(format!(
                    ":strength must evaluate in the binary64 lane, got {other:?}"
                )))
            }
        };
        graph
            .add_edge(edge_type, from_id, to_id, strength)
            .map_err(from_graph)
    }

    /// `(remove-edge <enum-ref> <expr> <expr>)`.
    fn remove_edge(
        &mut self,
        items: &[SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        graph: &mut dyn GraphSubstrate,
        fuel: &mut u64,
    ) -> Result<(), EvalError> {
        charge(fuel, cost::STRUCTURAL_VERB_BASE)?;
        let [_, type_ref, from, to] = items else {
            return Err(plain(
                "(remove-edge <enum-ref> <expr> <expr>) — unrecognized shape",
            ));
        };
        let edge_type = Self::enum_member(type_ref)?;
        let from_id = self.resolve_node(from, env, host, fuel)?;
        let to_id = self.resolve_node(to, env, host, fuel)?;
        graph
            .remove_edge(edge_type, from_id, to_id)
            .map_err(from_graph)
    }

    /// `(add-hyperedge <enum-ref> <expr> <members> <field-init>*)` — the
    /// member list crosses WHOLE; no path here expands it (VIII.9).
    fn add_hyperedge(
        &mut self,
        items: &[SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        graph: &mut dyn GraphSubstrate,
        fuel: &mut u64,
    ) -> Result<(), EvalError> {
        charge(fuel, cost::STRUCTURAL_VERB_BASE)?;
        let [_, type_ref, id_expr, members_form, field_inits @ ..] = items else {
            return Err(plain(
                "(add-hyperedge <enum-ref> <expr> <members> <field-init>*) — too few operands",
            ));
        };
        if !field_inits.is_empty() {
            // §2.8's ruling already names the adjacent gap (per-membership
            // payload, hyperedge field mutation); initial hyperedge fields
            // have no trait storage either — loud, not dropped.
            return Err(plain(
                "hyperedge <field-init> has no substrate storage in Phase 1 — \
                 a declared Phase-2 gap (§2.8 draft ruling), never silently dropped",
            ));
        }
        let hyperedge_type = Self::enum_member(type_ref)?;
        let name = self.fresh_declared_name(id_expr, env)?;
        let SExpr::List(member_items) = members_form else {
            return Err(plain("expected a (members <expr>+) form"));
        };
        let [SExpr::Atom(Atom::Symbol(head)), member_exprs @ ..] = member_items.as_slice() else {
            return Err(plain("expected a (members <expr>+) form"));
        };
        if head != "members" || member_exprs.is_empty() {
            // The grammar's <expr>+ makes a zero-member hyperedge
            // unexpressible; meeting one here is a shape error.
            return Err(plain("(members <expr>+) requires at least one member"));
        }
        let mut members = Vec::with_capacity(member_exprs.len());
        for member in member_exprs {
            members.push(self.resolve_node(member, env, host, fuel)?);
        }
        let id = graph
            .add_hyperedge(hyperedge_type, &members)
            .map_err(from_graph)?;
        self.declared_hyperedges.insert(name, id);
        Ok(())
    }

    /// `(emit <enum-ref> <payload-item>*)` — payload names are labels;
    /// there is no string interpolation in a payload (§2.8).
    fn emit(
        items: &[SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        sink: &mut dyn EventSink,
        fuel: &mut u64,
    ) -> Result<(), EvalError> {
        charge(fuel, cost::STRUCTURAL_VERB_BASE)?;
        let [_, type_ref, payload_items @ ..] = items else {
            return Err(plain(
                "(emit <enum-ref> <payload-item>*) — missing event type",
            ));
        };
        let event_type = Self::enum_member(type_ref)?;
        let mut payload = Vec::with_capacity(payload_items.len());
        for item in payload_items {
            let SExpr::List(pair) = item else {
                return Err(plain(format!(
                    "a payload item must be (<symbol> <expr>), found {item:?}"
                )));
            };
            let [SExpr::Atom(Atom::Symbol(name)), value_expr] = pair.as_slice() else {
                return Err(plain(format!(
                    "a payload item must be (<symbol> <expr>), found {pair:?}"
                )));
            };
            payload.push((name.clone(), evaluate(value_expr, env, host, fuel)?));
        }
        sink.emit(event_type, payload);
        Ok(())
    }

    /// An enum-ref operand's member name — the substrate's type string.
    fn enum_member(expr: &SExpr) -> Result<&str, EvalError> {
        match expr {
            SExpr::Atom(Atom::EnumRef { member, .. }) => Ok(member),
            other => Err(plain(format!(
                "expected an enum-ref where the grammar requires one, found {other:?}"
            ))),
        }
    }

    /// The id operand of `add-node`/`add-hyperedge`: a symbol introducing a
    /// fresh effect-list-scoped name (the §2.8 draft ruling this task
    /// records). Shadowing a binding, a reserved symbol, or an earlier
    /// declared id is loud.
    fn fresh_declared_name(&self, id_expr: &SExpr, env: &EvalEnv<'_>) -> Result<String, EvalError> {
        let SExpr::Atom(Atom::Symbol(name)) = id_expr else {
            return Err(plain(format!(
                "an add-node/add-hyperedge id operand must be a symbol naming \
                 the minted object for this effect list (§2.8 draft ruling), \
                 found {id_expr:?}"
            )));
        };
        let taken = crate::bindings::RESERVED_NAMES.contains(&name.as_str())
            || env.bindings.contains_key(name)
            || self.declared_nodes.contains_key(name)
            || self.declared_hyperedges.contains_key(name);
        if taken {
            return Err(plain(format!(
                "declared id {name} shadows an existing name — E-PARSE-022's \
                 no-shadowing discipline applies to effect-scoped ids too"
            )));
        }
        Ok(name.clone())
    }

    /// Resolve a node-ref operand: an effect-scoped declared id, or any
    /// expression evaluating to a `NodeRef` (`self`, a bound ref).
    fn resolve_node(
        &self,
        expr: &SExpr,
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        fuel: &mut u64,
    ) -> Result<NodeId, EvalError> {
        if let SExpr::Atom(Atom::Symbol(name)) = expr {
            if let Some(id) = self.declared_nodes.get(name) {
                charge(fuel, cost::VARIABLE_REF)?;
                return Ok(*id);
            }
        }
        match evaluate(expr, env, host, fuel)? {
            Value::NodeRef(id) => Ok(id),
            other => Err(plain(format!(
                "expected a NodeRef operand, got {other:?} (§3.1)"
            ))),
        }
    }

    /// Resolve a hyperedge-ref operand, symmetrically.
    fn resolve_hyperedge(
        &self,
        expr: &SExpr,
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        fuel: &mut u64,
    ) -> Result<HyperedgeId, EvalError> {
        if let SExpr::Atom(Atom::Symbol(name)) = expr {
            if let Some(id) = self.declared_hyperedges.get(name) {
                charge(fuel, cost::VARIABLE_REF)?;
                return Ok(*id);
            }
        }
        match evaluate(expr, env, host, fuel)? {
            Value::HyperedgeRef(id) => Ok(id),
            other => Err(plain(format!(
                "expected a HyperedgeRef operand, got {other:?} (§3.1)"
            ))),
        }
    }

    /// Evaluate a value that will be WRITTEN to `field`, in the binary64
    /// lane the trait's attribute storage carries. A Currency-typed value
    /// is a loud declared Phase-2 gap (i128 exactness does not survive an
    /// f64 attribute), never a lossy cast.
    fn numeric_write_value(
        expr: &SExpr,
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        fuel: &mut u64,
        field: &str,
    ) -> Result<f64, EvalError> {
        match evaluate(expr, env, host, fuel)? {
            Value::Real(r) => Ok(r),
            // i64 -> f64 is deterministic; exactness beyond 2^53 belongs to
            // the typed-attribute-storage gap named in the module doc.
            #[allow(clippy::cast_precision_loss)]
            Value::Int(n) => Ok(n as f64),
            Value::Currency(_) => Err(plain(format!(
                "writing a Currency value to {field} needs typed attribute \
                 storage (Phase 2 gap, module doc) — refusing the lossy f64 cast"
            ))),
            other => Err(plain(format!(
                "cannot store {other:?} as a numeric node attribute"
            ))),
        }
    }

    /// §3.3's one range check, at the store boundary: a value outside the
    /// target field's declared domain is `E-EVAL-020` — never a clamp. A
    /// field absent from the registry is loud (closed vocabulary, §3.6).
    fn store_range_check(&self, field: &str, value: f64) -> Result<(), EvalError> {
        let Some(decl) = self.types.fields.get(field) else {
            return Err(plain(format!(
                "unknown field {field} — the vocabulary is closed (§3.6); the \
                 loader should have rejected this content"
            )));
        };
        let unit_interval = matches!(
            decl.ty,
            BslType::Probability | BslType::Intensity | BslType::Coefficient
        );
        if unit_interval && !(0.0..=1.0).contains(&value) {
            return Err(EvalError::coded(
                EvalCode::StoreRangeViolation,
                format!(
                    "storing {value} to {field} ({:?}) leaves its declared \
                     [0,1] domain — a loud failure, never a clamp (§3.3)",
                    decl.ty
                ),
            ));
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::fuel::IntrinsicCosts;
    use crate::intrinsic_host::EmptyIntrinsicHost;
    use crate::reader::read;
    use crate::types::{FieldDecl, FieldKind};
    use babylon_graph::placeholder::PlaceholderGraph;

    fn types() -> TypeEnv {
        TypeEnv {
            fields: HashMap::from([
                (
                    "social-class/agitation".to_owned(),
                    FieldDecl {
                        ty: BslType::Intensity,
                        kind: FieldKind::Intensive,
                    },
                ),
                (
                    "social-class/head-count".to_owned(),
                    FieldDecl {
                        ty: BslType::Int,
                        kind: FieldKind::Extensive,
                    },
                ),
            ]),
            exemptions: &[],
        }
    }

    struct Fixture {
        graph: PlaceholderGraph,
        self_id: NodeId,
        costs: IntrinsicCosts,
    }

    impl Fixture {
        fn new() -> Self {
            let mut graph = PlaceholderGraph::new();
            let self_id = graph.add_node("SOCIAL_CLASS").unwrap();
            graph
                .update_node(self_id, "social-class/agitation", 0.10)
                .unwrap();
            Self {
                graph,
                self_id,
                costs: IntrinsicCosts::default(),
            }
        }

        /// Execute an `(effects …)` source against the fixture, returning
        /// the collected event stream.
        #[allow(clippy::type_complexity)]
        fn run(
            &mut self,
            effects_source: &str,
            fuel: &mut u64,
        ) -> Result<Vec<(String, Vec<(String, Value)>)>, EvalError> {
            let (form, _) = read(effects_source).expect("effects source must parse");
            let SExpr::List(items) = form else {
                unreachable!()
            };
            let env = EvalEnv {
                bindings: HashMap::from([("self".to_owned(), Value::NodeRef(self.self_id))]),
                intrinsic_costs: &self.costs,
            };
            let types = types();
            let mut executor = EffectExecutor::new(&types);
            let mut sink = CollectingSink::default();
            executor.execute_effects(
                &items[1..],
                &env,
                &EmptyIntrinsicHost,
                &mut self.graph,
                &mut sink,
                fuel,
            )?;
            Ok(sink.events)
        }
    }

    #[test]
    fn the_demo_rule_effect_executes_with_pinned_fuel() {
        // The §5.6 effect against agitation = 0.10: update-node charges its
        // static per-node sum exactly — verb(3) + self(1) + qname(0) +
        // update-op(1) + literal(0) = 5.
        let mut fixture = Fixture::new();
        let mut fuel = 64;
        fixture
            .run(
                "(effects (update-node self social-class/agitation (add 0.05i)))",
                &mut fuel,
            )
            .unwrap();
        let stored = fixture
            .graph
            .node_attribute(fixture.self_id, "social-class/agitation")
            .unwrap();
        assert!((stored - 0.15).abs() < 1e-12);
        assert_eq!(fuel, 59, "5 consumed — a conformance-vector quantity");
    }

    #[test]
    fn the_store_boundary_rejects_out_of_range_never_clamps() {
        let mut fixture = Fixture::new();
        let mut fuel = 64;
        let err = fixture
            .run(
                "(effects (update-node self social-class/agitation (add 0.95i)))",
                &mut fuel,
            )
            .unwrap_err();
        assert_eq!(err.code, Some(EvalCode::StoreRangeViolation));
        assert_eq!(err.code.unwrap().spec_code(), "E-EVAL-020");
        // The failed write left the attribute untouched.
        let stored = fixture
            .graph
            .node_attribute(fixture.self_id, "social-class/agitation")
            .unwrap();
        assert!((stored - 0.10).abs() < 1e-12);
    }

    #[test]
    fn add_node_introduces_a_name_later_effects_can_use() {
        let mut fixture = Fixture::new();
        let mut fuel = 128;
        fixture
            .run(
                "(effects \
                   (add-node NodeType/SOCIAL_CLASS recruit (social-class/agitation 0.2i)) \
                   (add-edge EdgeType/SOLIDARITY recruit self :strength 0.5c))",
                &mut fuel,
            )
            .unwrap();
        assert_eq!(fixture.graph.edge_count(), 1);
    }

    #[test]
    fn roster_replacement_is_remove_then_add_in_one_list() {
        // §2.8 draft ruling: no add-member verb exists; changing a roster
        // is remove-hyperedge + add-hyperedge in one effect list.
        let mut fixture = Fixture::new();
        let mut fuel = 256;
        fixture
            .run(
                "(effects \
                   (add-node NodeType/SOCIAL_CLASS comrade) \
                   (add-hyperedge HyperedgeType/CELL nucleus (members self)) \
                   (remove-hyperedge nucleus) \
                   (add-hyperedge HyperedgeType/CELL grown (members self comrade)))",
                &mut fuel,
            )
            .unwrap();
        let grown = fixture.graph.hyperedges_of(fixture.self_id, "CELL");
        assert_eq!(grown.len(), 1);
        assert_eq!(
            fixture.graph.members_of(grown[0]).unwrap().len(),
            2,
            "the replacement roster, whole — never pairwise edges"
        );
    }

    #[test]
    fn substrate_discipline_surfaces_as_e_eval_031() {
        let mut fixture = Fixture::new();
        let mut fuel = 128;
        // Duplicate member: the substrate refuses, nothing deduplicates.
        let err = fixture
            .run(
                "(effects (add-hyperedge HyperedgeType/CELL c (members self self)))",
                &mut fuel,
            )
            .unwrap_err();
        assert_eq!(err.code, Some(EvalCode::ExistenceDiscipline));
        assert_eq!(err.code.unwrap().spec_code(), "E-EVAL-031");
        // Removing an edge that does not exist: absence is never success.
        let mut fuel2 = 128;
        let err2 = fixture
            .run(
                "(effects (remove-edge EdgeType/SOLIDARITY self self))",
                &mut fuel2,
            )
            .unwrap_err();
        assert_eq!(err2.code, Some(EvalCode::ExistenceDiscipline));
    }

    #[test]
    fn a_false_guard_skips_and_does_not_charge_its_effects() {
        let mut fixture = Fixture::new();
        let mut fuel = 64;
        fixture
            .run(
                "(effects (guard (< 1 0) \
                   (update-node self social-class/agitation (add 0.05i))))",
                &mut fuel,
            )
            .unwrap();
        // guard(1) + cmp(1) + two literals(0) = 2; the verb never charged.
        assert_eq!(fuel, 62);
        let stored = fixture
            .graph
            .node_attribute(fixture.self_id, "social-class/agitation")
            .unwrap();
        assert!((stored - 0.10).abs() < 1e-12, "untaken effects never apply");
    }

    #[test]
    fn emit_collects_the_evaluated_payload() {
        let mut fixture = Fixture::new();
        let mut fuel = 64;
        let events = fixture
            .run(
                "(effects (emit EventType/RUPTURE (severity 0.9c) (tick 52)))",
                &mut fuel,
            )
            .unwrap();
        assert_eq!(
            events,
            vec![(
                "RUPTURE".to_owned(),
                vec![
                    ("severity".to_owned(), Value::Real(0.9)),
                    ("tick".to_owned(), Value::Int(52)),
                ]
            )]
        );
    }

    #[test]
    fn currency_writes_are_a_loud_declared_gap_never_a_lossy_cast() {
        let mut fixture = Fixture::new();
        let mut fuel = 64;
        let err = fixture
            .run(
                "(effects (update-node self social-class/head-count (set 100$)))",
                &mut fuel,
            )
            .unwrap_err();
        assert!(err.message.contains("Phase 2 gap"), "{err}");
    }

    #[test]
    fn a_declared_id_may_not_shadow_bindings_or_reserved_names() {
        let mut fixture = Fixture::new();
        for id in ["self", "it"] {
            let mut fuel = 64;
            let err = fixture
                .run(
                    &format!("(effects (add-node NodeType/SOCIAL_CLASS {id}))"),
                    &mut fuel,
                )
                .unwrap_err();
            assert!(err.message.contains("shadows"), "{id}: {err}");
        }
    }

    #[test]
    fn hyperedge_field_inits_are_a_loud_phase_2_gap() {
        let mut fixture = Fixture::new();
        let mut fuel = 128;
        let err = fixture
            .run(
                "(effects (add-hyperedge HyperedgeType/CELL c (members self) \
                   (social-class/agitation 0.5i)))",
                &mut fuel,
            )
            .unwrap_err();
        assert!(err.message.contains("Phase-2 gap"), "{err}");
    }
}
