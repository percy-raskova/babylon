//! The typed structural verb algebra (`bsl-language.rst` §2.8): the seven
//! graph verbs plus `emit`, executed against any
//! [`babylon_graph::substrate::GraphSubstrate`] — generic over the store by
//! design, so this module needed no change when the production store
//! swapped from `MemoryGraph` to `HypergraphStore` at the Phase 1/2
//! boundary (ADR179 T3, executed by ADR193, 2026-08-11). This is the
//! crate-DAG edge Task 11 planned: `babylon-bsl` depends on `babylon-graph`.
//!
//! **No clique expansion exists in this module** and none may be added: a
//! member list is handed to `GraphSubstrate::add_hyperedge` whole — that is
//! Anti-Pattern VIII.9 enforced where the verbs live. There is deliberately
//! no `add-member`/`remove-member`: membership change is whole-hyperedge
//! replacement, `remove-hyperedge` then `add-hyperedge` in one effect list
//! (§2.8 draft ruling, D26 — whose member-list half **stands**).
//!
//! **`update-edge` and `update-hyperedge` (R9 chapters C2/C12, D35/D65) are
//! recognised here and refused loudly, with the reason named.** Both verbs
//! write a *declared field of an edge or a hyperedge*, and
//! `GraphSubstrate` has no storage for either: its edge state is one `f64`
//! strength keyed by `(type, from, to)` and its hyperedges carry no
//! attributes at all. Giving them storage widens the substrate's state and
//! therefore the canonical `state_hash` field set — a hash-relevant change
//! this chapter has no licence to improvise (Constitution III.7). The
//! grammar, the §3.7 cost rows, the §2.8 static checks and the error codes
//! land now; the storage is a **declared substrate gap**, escalated rather
//! than silently absorbed, exactly as `add-hyperedge`'s `<field-init>` was.
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

use crate::evaluator::{
    charge, check_node_referent_type, evaluate, require_graph, EvalCode, EvalEnv, EvalError, Value,
};
use crate::fuel::cost;
use crate::intrinsic_host::IntrinsicHost;
use crate::reader::{Atom, SExpr};
use crate::typecheck::TypeEnv;
use crate::types::{BslType, EnumRegistry, EnumTypeId};
use crate::write_log::{Write, WriteObserver, WriteRecord};
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

/// `update-node`'s four update-ops (§2.8), carried by a [`PendingWrite`]
/// rather than pre-combined: `add`/`sub`/`scale` need the target's CURRENT
/// value as of APPLY time, not collect time (Task 12, D-row Q2), so the
/// combine cannot happen until [`EffectExecutor::apply_pending_write`] runs.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UpdateOp {
    /// `(set <expr>)` — the operand IS the final value.
    Set,
    /// `(add <expr>)` — combine by addition at apply time.
    Add,
    /// `(sub <expr>)` — combine by subtraction at apply time.
    Sub,
    /// `(scale <expr>)` — combine by multiplication at apply time.
    Scale,
}

/// One collected, not-yet-applied `update-node` mutation (Task 12, P27
/// Phase 2 query-evaluation plan, §4.2 chapter C4 + §2.8 chapter C6). The
/// evaluator has ALREADY reduced the operand expression against the rule's
/// PRE-STATE during collection (`EffectExecutor::collect_effects`); the
/// accumulating ops read the target's CURRENT value at APPLY time (D-row
/// Q2) — §4.2's carrier-accumulation clause is only satisfiable that way:
/// reading the target at collect time would make three subjects each
/// adding to one carrier lose two of the three contributions.
///
/// **Scope.** Only `update-node` defers via this type. Every other effect
/// kind is unaffected by Task 12: `emit` never touched the graph and still
/// fires during collection (its payload evaluates against the SAME
/// pre-state, matching §2.8's own worked `for-each` example, whose `emit`
/// reads the PRE-scale `solidarity/strength`); the six graph-shape verbs
/// (`add-node`, `remove-node`, `add-edge`, `remove-edge`, `add-hyperedge`,
/// `remove-hyperedge`) remain served only through
/// [`EffectExecutor::execute_effects`], the immediate-apply path this
/// module keeps unchanged — see [`EffectExecutor::collect_effects`]'s own
/// doc for why deferring them is out of this task's scope.
#[derive(Debug, Clone, PartialEq)]
pub struct PendingWrite {
    /// The target node, already resolved (a computed `NodeRef`, per Task 11,
    /// resolves the same way whether the write applies immediately or is
    /// collected).
    pub id: NodeId,
    /// The declared field qname.
    pub field: String,
    /// Which of the four update-ops.
    pub op: UpdateOp,
    /// The reduced operand — `set`'s final value, or the amount
    /// `add`/`sub`/`scale` combine with the target's CURRENT value at apply
    /// time.
    pub operand: f64,
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
    /// **§2.13 addendum (D101).** The content-declared closed-enum
    /// registry — `numeric_write_value`'s enum branch resolves a written
    /// `<enum-ref>`'s ordinal through this, exactly as `bind_subject`
    /// (`tick.rs`) resolves the read-path inverse. An empty registry
    /// (`EnumRegistry::default()`) is the honest "no `defenum`s in scope"
    /// input for content with none — every enum-typed `store_range_check`/
    /// `numeric_write_value` site is unreachable without a
    /// `BslType::Enum`-declared field in `types` first, so an empty
    /// registry never silently under-serves real content.
    enums: &'a EnumRegistry,
    declared_nodes: HashMap<String, NodeId>,
    declared_hyperedges: HashMap<String, HyperedgeId>,
    /// The ADR182 R1 interception point. `None` is the unobserved path and
    /// does no observer work at all.
    observer: Option<&'a mut dyn WriteObserver>,
    /// The rule id every record from this executor is attributed to.
    attribution: String,
    /// Source-order position of the NEXT write. Counts writes performed,
    /// not effect items considered.
    ordinal: u32,
}

impl<'a> EffectExecutor<'a> {
    /// A fresh executor for one effect list. `types` supplies the declared
    /// field types the §3.3 store-boundary range check needs; `enums`
    /// supplies the §2.13 enum-ordinal registry a `BslType::Enum`-declared
    /// field's write path resolves against.
    #[must_use]
    pub fn new(types: &'a TypeEnv, enums: &'a EnumRegistry) -> Self {
        Self {
            types,
            enums,
            declared_nodes: HashMap::new(),
            declared_hyperedges: HashMap::new(),
            observer: None,
            attribution: String::new(),
            ordinal: 0,
        }
    }

    /// The same executor with the ADR182 R1 write log installed, attributing
    /// every record to `rule` (the `<system>/<rule-name>` qname). One
    /// executor runs one rule's effect list, so attribution is fixed at
    /// construction rather than carried per write.
    ///
    /// Observation MUST NOT change what the executor does: an observed and
    /// an unobserved run of the same effect list leave identical graph state
    /// and consume identical fuel. See `write_log`'s module doc.
    #[must_use]
    pub fn observed(
        types: &'a TypeEnv,
        enums: &'a EnumRegistry,
        rule: impl Into<String>,
        observer: &'a mut dyn WriteObserver,
    ) -> Self {
        Self {
            types,
            enums,
            declared_nodes: HashMap::new(),
            declared_hyperedges: HashMap::new(),
            observer: Some(observer),
            attribution: rule.into(),
            ordinal: 0,
        }
    }

    /// Hand one completed mutation to the observer, if any. Call sites are
    /// AFTER the substrate accepted the write, never before: a write that
    /// failed leaves no record.
    fn record(&mut self, write: Write) {
        if let Some(observer) = self.observer.as_mut() {
            observer.record(WriteRecord {
                rule: self.attribution.clone(),
                ordinal: self.ordinal,
                write,
            });
            self.ordinal += 1;
        }
    }

    /// The prior value of a field, for the log only — a failed probe means
    /// the field held nothing, which is exactly what `None` records. Never
    /// call this to make a decision (see `write_log`'s discipline 3).
    fn probe_previous(&self, graph: &dyn GraphSubstrate, id: NodeId, field: &str) -> Option<f64> {
        self.observer.as_ref()?;
        graph.node_attribute(id, field).ok()
    }

    /// Execute the items of an `(effects …)` form in source order (§2.8),
    /// applying each write IMMEDIATELY — the single-pass model.
    ///
    /// **NOT a production path (#519 fix round, fix 7).** No production
    /// driver has called this method since Task 12: `run_tick`
    /// (`tick.rs`) calls [`Self::collect_effects`] then
    /// [`Self::apply_pending_write`], the collect-then-apply split §4.2
    /// chapter C4's pre-state law requires. `execute_effects` survives
    /// because two things still legitimately need the immediate-apply
    /// model rather than the deferred one: this crate's OWN unit tests
    /// (verb-level correctness, write-log discipline, error messaging —
    /// none of which depend on collect-vs-apply staging) and
    /// `babylon-bsl/tests/conformance_corpus.rs`'s
    /// `bifurcation_routes_by_solidarity_density`, which needs no
    /// `env.graph` and applies one subject's effects once. A test meaning
    /// to prove something about `run_tick`'s ACTUAL pre-state/subject-order
    /// guarantees must not use this method or `Self::for_each` below —
    /// see `structural_verbs::tests::collect_then_apply`, or drive
    /// `run_tick` directly.
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
                let taken = crate::evaluator::as_bool(evaluate(cond, env, host, fuel)?)?;
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
                graph.remove_node(id).map_err(from_graph)?;
                self.record(Write::NodeRemoved { id });
                Ok(())
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
                graph.remove_hyperedge(id).map_err(from_graph)?;
                self.record(Write::HyperedgeRemoved { id });
                Ok(())
            }
            "emit" => Self::emit(items, env, host, sink, fuel),
            "for-each" => self.for_each(items, env, host, graph, sink, fuel),
            verb @ ("update-edge" | "update-hyperedge") => {
                // The verb EXISTS (D35/D65) — this is a storage gap, not an
                // unknown head, and the message must not confuse the two.
                Err(plain(format!(
                    "({verb} …) has no substrate storage: GraphSubstrate keys \
                     an edge to one f64 strength and gives a hyperedge no \
                     attributes at all. Widening that state widens the \
                     canonical state_hash field set, which is a declared \
                     Phase-2/substrate decision (Constitution III.7), never a \
                     silently-dropped write"
                )))
            }
            other => Err(plain(format!(
                "unknown effect head ({other} …) — the §2.8 verb set is closed"
            ))),
        }
    }

    /// `(for-each <query> <elem-name>? <effect-item>+)` (§2.8 chapter C6).
    /// This is the EXECUTE path's copy — production has not called it since
    /// Task 12 (`run_tick` calls `collect_item`'s own `"for-each"` arm
    /// instead); it survives as the single-pass immediate-apply harness
    /// `EffectExecutor::execute_effects`'s own callers use (this crate's
    /// unit tests, the conformance corpus — see that method's own doc).
    ///
    /// The query materializes through `env.graph` — the caller's pre-state
    /// reference — exactly once, before any of this `for-each`'s own
    /// per-element effects apply, mirroring `evaluator::eval_fold`/
    /// `eval_exists_forall`/`eval_selection`'s identical query-then-iterate
    /// shape in expression position.
    ///
    /// **Corrected (#519 fix round):** this doc used to claim `env.graph`
    /// is NEVER the same object a verb write path mutates, as though the
    /// TYPE SYSTEM enforced that. It does not: `env: &EvalEnv<'_>` and
    /// `graph: &mut dyn GraphSubstrate` are independent parameters, and
    /// nothing in this method's signature stops a caller from constructing
    /// both from the SAME underlying graph via sequential, non-overlapping
    /// reborrows — exactly the technique `tick.rs::run_tick` uses across
    /// its own Pass 1/Pass 2 split (NLL re-acquires a fresh reborrow per
    /// subject; the verifier compiled a Pass-1 mutation that built cleanly,
    /// proving the whole-pass guarantee is not type-level either). What the
    /// type system DOES guarantee, scoped to exactly this one call: nothing
    /// this method calls performs a write through `env.graph` (it is `&`,
    /// never `&mut`) — every write goes through the separate `graph`
    /// parameter below. That callers keep pre-state reads and live writes
    /// from OVERLAPPING in time is their own discipline (`run_tick`'s
    /// two-pass split, guarded by this crate's own pre-state tests), not a
    /// fact this method's signature forces on every caller.
    ///
    /// Application order is total: the body runs once per element in
    /// iteration order (outer), and its own items apply in source order
    /// (inner, via the ordinary `execute_item` recursion) — nested
    /// `for-each` composes the same way. An empty query applies nothing and
    /// is not an error: an iteration is a command, and "do it to none" is
    /// completely determined.
    #[allow(clippy::too_many_arguments)]
    fn for_each(
        &mut self,
        items: &[SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        graph: &mut dyn GraphSubstrate,
        sink: &mut dyn EventSink,
        fuel: &mut u64,
    ) -> Result<(), EvalError> {
        let (elem_name, effect_items, elements) = Self::for_each_prelude(items, env, host, fuel)?;
        for element in elements {
            let child = crate::evaluator::with_element(env, elem_name.clone(), element);
            for effect_item in effect_items {
                self.execute_item(effect_item, &child, host, graph, sink, fuel)?;
            }
        }
        Ok(())
    }

    /// Shared `for-each` prelude (§2.8 chapter C6): charge, destructure
    /// `(for-each <query> <elem-name>? <effect-item>+)`, strip an optional
    /// `:as` name, refuse an empty body, and materialize the query through
    /// `env.graph` exactly once — everything both [`Self::for_each`] (the
    /// execute path) and [`Self::collect_item`]'s `"for-each"` arm (the
    /// collect path) do IDENTICALLY before diverging on how they run the
    /// body over each element (mutate immediately vs. collect a
    /// [`PendingWrite`]).
    ///
    /// Extracted after the M4 mutation-verification gap this duplication
    /// caused (#519 fix round, fix 7): the two copies had already drifted
    /// — a mutation deleting the collect-path copy's iteration loop
    /// (materializing the query but never running the body) flipped ZERO
    /// tests, because every for-each test drove the execute path only.
    /// One prelude now means a shape bug here can only exist once, not
    /// twice with one copy silently stale.
    ///
    /// # Errors
    ///
    /// The missing-query and empty-body shape errors, or whatever
    /// [`crate::query::materialize`] raises.
    #[allow(clippy::type_complexity)]
    fn for_each_prelude<'e>(
        items: &'e [SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        fuel: &mut u64,
    ) -> Result<(Option<String>, &'e [SExpr], Vec<crate::query::Element>), EvalError> {
        charge(fuel, cost::FOR_EACH_BASE)?;
        let [_, query, rest @ ..] = items else {
            return Err(plain(
                "(for-each <query> <elem-name>? <effect-item>+) — missing query",
            ));
        };
        let (elem_name, effect_items) = crate::evaluator::strip_as_name(rest);
        if effect_items.is_empty() {
            return Err(plain(
                "(for-each …) requires at least one effect item (§2.8)",
            ));
        }
        let elements = crate::query::materialize(query, env, host, fuel)?;
        Ok((elem_name, effect_items, elements))
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
        // §2.10 discipline 1's runtime half (R9 chapter C2): `node`'s
        // static type is a reference (§3.1 gives it none), so the
        // field-owner-vs-referent disagreement `add-node` catches at LOAD
        // as `E-TYPE-014` can only be caught HERE, at evaluation, as
        // `E-EVAL-033` — before Task 11 this write succeeded silently.
        check_node_referent_type(&*graph, id, field, "update-node")?;
        let SExpr::List(op_items) = op_form else {
            return Err(plain(
                "update-op must be a form: (add|sub|set|scale <expr>)",
            ));
        };
        let [SExpr::Atom(Atom::Symbol(op)), operand] = op_items.as_slice() else {
            return Err(plain("update-op must be (add|sub|set|scale <expr>)"));
        };
        charge(fuel, cost::UPDATE_OP_BASE)?;
        let operand_value = self.numeric_write_value(operand, env, host, fuel, field)?;
        // `previous` is for the write log only. `set` does not otherwise read
        // the field, so it PROBES (a never-written field is `None`, not an
        // error — write_log discipline 3); the read-modify-write ops already
        // hold the value they need.
        let (new_value, previous) = match op.as_str() {
            "set" => (operand_value, self.probe_previous(&*graph, id, field)),
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
                (combined, Some(current))
            }
            other => {
                return Err(plain(format!(
                    "unknown update-op ({other} …) — the set is add|sub|set|scale (§2.8)"
                )))
            }
        };
        self.store_range_check(field, new_value)?;
        graph
            .update_node(id, field, new_value)
            .map_err(from_graph)?;
        self.record(Write::NodeAttribute {
            id,
            field: field.clone(),
            previous,
            value: new_value,
        });
        Ok(())
    }

    // ---- Task 12: the pre-state law — collect-then-apply ----

    /// COLLECT phase (§2.8 chapter C6 + §4.2 chapter C4): evaluate
    /// `effect_items` against `env`'s pre-state, returning the
    /// `update-node` writes they would perform WITHOUT applying any of
    /// them. This method takes no mutable graph at all — that is what
    /// makes "every firing observes the same pre-state" a property of the
    /// TYPE, not a convention a caller could violate by forgetting to
    /// re-read: nothing this method calls CAN mutate a graph.
    ///
    /// `emit` fires immediately even here (it never touched a graph, and
    /// its payload evaluates against the same frozen `env`, matching §2.8's
    /// own worked `for-each` example, whose `emit` reads the PRE-scale
    /// `solidarity/strength`). `guard` and `for-each` recurse the same way
    /// `Self::execute_item` does, over this collecting path instead.
    ///
    /// **Scope.** The six graph-shape verbs (`add-node`, `remove-node`,
    /// `add-edge`, `remove-edge`, `add-hyperedge`, `remove-hyperedge`)
    /// refuse loudly here, naming this gap: verified by grep over
    /// `rust/crates/babylon-tick/content/rules/*.bsl`, nothing landed uses
    /// them, and correctly deferring a MINTING verb needs a placeholder-id
    /// scheme neither this plan's `PendingWrite` sketch nor its two
    /// required tests specify — inventing one would be exactly the silent
    /// invention this crate's discipline forbids (Constitution, escalation
    /// clause). They stay fully served through [`Self::execute_effects`],
    /// unchanged, for callers that need them today.
    ///
    /// # Errors
    ///
    /// Any [`EvalError`] an operand or query raises, and a named refusal
    /// for a graph-shape verb this phase does not serve.
    pub fn collect_effects(
        &mut self,
        effect_items: &[SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        sink: &mut dyn EventSink,
        fuel: &mut u64,
    ) -> Result<Vec<PendingWrite>, EvalError> {
        let mut pending = Vec::new();
        self.collect_items(effect_items, env, host, sink, fuel, &mut pending)?;
        Ok(pending)
    }

    #[allow(clippy::too_many_arguments)]
    fn collect_items(
        &mut self,
        items: &[SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        sink: &mut dyn EventSink,
        fuel: &mut u64,
        pending: &mut Vec<PendingWrite>,
    ) -> Result<(), EvalError> {
        for item in items {
            self.collect_item(item, env, host, sink, fuel, pending)?;
        }
        Ok(())
    }

    #[allow(clippy::too_many_arguments)]
    fn collect_item(
        &mut self,
        item: &SExpr,
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        sink: &mut dyn EventSink,
        fuel: &mut u64,
        pending: &mut Vec<PendingWrite>,
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
                charge(fuel, cost::GUARD_BASE)?;
                let [_, cond, nested @ ..] = items.as_slice() else {
                    return Err(plain("(guard <cond> <effect-item>+) — missing condition"));
                };
                if nested.is_empty() {
                    return Err(plain("(guard …) requires at least one effect item"));
                }
                let taken = crate::evaluator::as_bool(evaluate(cond, env, host, fuel)?)?;
                if taken {
                    self.collect_items(nested, env, host, sink, fuel, pending)?;
                }
                Ok(())
            }
            "update-node" => {
                let write = self.collect_update_node(items, env, host, fuel)?;
                pending.push(write);
                Ok(())
            }
            "emit" => Self::emit(items, env, host, sink, fuel),
            "for-each" => {
                let (elem_name, effect_items, elements) =
                    Self::for_each_prelude(items.as_slice(), env, host, fuel)?;
                for element in elements {
                    let child = crate::evaluator::with_element(env, elem_name.clone(), element);
                    self.collect_items(effect_items, &child, host, sink, fuel, pending)?;
                }
                Ok(())
            }
            verb @ ("add-node" | "remove-node" | "add-edge" | "remove-edge" | "add-hyperedge"
            | "remove-hyperedge") => Err(plain(format!(
                "({verb} …) needs a mutable graph — Task 12's pre-state \
                 collection phase (§4.2 chapter C4) does not serve the \
                 graph-shape verbs, only update-node/emit/guard/for-each. \
                 Every rule `rule_pipeline::load_rule_form` accepts is \
                 already refused, BY NAME, before it ever reaches this arm \
                 (`check_no_deferred_shape_verbs`, the LOAD-time gate — \
                 §3's own law: every check in this chapter runs at content \
                 load, before any tick executes). Reaching this defense-in- \
                 depth arm at all means a caller invoked collect_effects \
                 directly, bypassing that gate. The follow-on that will \
                 serve {verb} is the placeholder-id design this module's \
                 own collect_effects doc escalates — never \
                 EffectExecutor::execute_effects, which is retired from \
                 production (Task 12) and stays only as a test/corpus \
                 harness (see its own doc)"
            ))),
            verb @ ("update-edge" | "update-hyperedge") => Err(plain(format!(
                "({verb} …) has no substrate storage: GraphSubstrate keys \
                 an edge to one f64 strength and gives a hyperedge no \
                 attributes at all. Widening that state widens the \
                 canonical state_hash field set, which is a declared \
                 Phase-2/substrate decision (Constitution III.7), never a \
                 silently-dropped write"
            ))),
            other => Err(plain(format!(
                "unknown effect head ({other} …) — the §2.8 verb set is closed"
            ))),
        }
    }

    /// The collect half of `update-node`: parse, resolve the referent, run
    /// §2.10 discipline 1's type check, and reduce the operand — everything
    /// [`Self::update_node`] does EXCEPT the read-modify-write itself, which
    /// [`Self::apply_pending_write`] performs later, at apply time. The
    /// referent-type check reads through `env.graph` (there is no mutable
    /// graph here to reborrow from, unlike [`Self::update_node`]'s), which
    /// is the SAME pre-state reference the operand's own query, if any,
    /// resolves against.
    fn collect_update_node(
        &mut self,
        items: &[SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        fuel: &mut u64,
    ) -> Result<PendingWrite, EvalError> {
        charge(fuel, cost::STRUCTURAL_VERB_BASE)?;
        let [_, node, SExpr::Atom(Atom::QName(field)), op_form] = items else {
            return Err(plain(
                "(update-node <expr> <qname> <update-op>) — unrecognized shape",
            ));
        };
        let id = self.resolve_node(node, env, host, fuel)?;
        let graph = require_graph(env, "update-node")?;
        check_node_referent_type(graph, id, field, "update-node")?;
        let SExpr::List(op_items) = op_form else {
            return Err(plain(
                "update-op must be a form: (add|sub|set|scale <expr>)",
            ));
        };
        let [SExpr::Atom(Atom::Symbol(op)), operand] = op_items.as_slice() else {
            return Err(plain("update-op must be (add|sub|set|scale <expr>)"));
        };
        charge(fuel, cost::UPDATE_OP_BASE)?;
        let operand_value = self.numeric_write_value(operand, env, host, fuel, field)?;
        let update_op = match op.as_str() {
            "set" => UpdateOp::Set,
            "add" => UpdateOp::Add,
            "sub" => UpdateOp::Sub,
            "scale" => UpdateOp::Scale,
            other => {
                return Err(plain(format!(
                    "unknown update-op ({other} …) — the set is add|sub|set|scale (§2.8)"
                )))
            }
        };
        Ok(PendingWrite {
            id,
            field: field.clone(),
            op: update_op,
            operand: operand_value,
        })
    }

    /// APPLY phase (Task 12): perform ONE collected write against the LIVE
    /// graph. `add`/`sub`/`scale` read the target's CURRENT value HERE, at
    /// apply time (D-row Q2) — this is what lets several subjects each
    /// contribute to one shared carrier without losing any contribution:
    /// each apply sees every PRIOR apply's result, in whatever order the
    /// caller applies the collected `Vec<PendingWrite>` (subject order
    /// outer, source order inner — this method performs exactly one write
    /// and does not itself impose an order over a batch).
    ///
    /// # Errors
    ///
    /// `E-EVAL-020` (store-boundary range violation), `E-EVAL-014`
    /// (non-finite combine), or the substrate's own existence error mapped
    /// to `E-EVAL-031`.
    pub fn apply_pending_write(
        &mut self,
        write: &PendingWrite,
        graph: &mut dyn GraphSubstrate,
    ) -> Result<(), EvalError> {
        let (new_value, previous) = match write.op {
            UpdateOp::Set => (
                write.operand,
                self.probe_previous(&*graph, write.id, &write.field),
            ),
            UpdateOp::Add | UpdateOp::Sub | UpdateOp::Scale => {
                let current = graph
                    .node_attribute(write.id, &write.field)
                    .map_err(from_graph)?;
                let combined = match write.op {
                    UpdateOp::Add => current + write.operand,
                    UpdateOp::Sub => current - write.operand,
                    UpdateOp::Scale => current * write.operand,
                    UpdateOp::Set => unreachable!("Set is handled in the arm above"),
                };
                if !combined.is_finite() {
                    return Err(EvalError::coded(
                        EvalCode::NonFinite,
                        format!("update-node on {} produced a non-finite value", write.field),
                    ));
                }
                (combined, Some(current))
            }
        };
        self.store_range_check(&write.field, new_value)?;
        graph
            .update_node(write.id, &write.field, new_value)
            .map_err(from_graph)?;
        self.record(Write::NodeAttribute {
            id: write.id,
            field: write.field.clone(),
            previous,
            value: new_value,
        });
        Ok(())
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
        self.record(Write::NodeAdded {
            id,
            node_type: node_type.to_owned(),
        });
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
            let value = self.numeric_write_value(value_expr, env, host, fuel, field)?;
            self.store_range_check(field, value)?;
            // A field-init on a freshly minted node normally has no prior
            // value; probing rather than assuming keeps a repeated init
            // honest.
            let previous = self.probe_previous(&*graph, id, field);
            graph.update_node(id, field, value).map_err(from_graph)?;
            self.record(Write::NodeAttribute {
                id,
                field: field.clone(),
                previous,
                value,
            });
        }
        Ok(())
    }

    /// `(add-edge <enum-ref> <expr> <expr> :strength <expr> <field-init>*)`
    /// — the `<field-init>*` tail is R9 chapter C2's addition (D37). Its
    /// static checks (`E-PARSE-041` on a `strength` init, `E-TYPE-014` on a
    /// foreign owner) are [`crate::grammar`]'s, at load; its *storage* is
    /// the declared substrate gap the module doc names.
    fn add_edge(
        &mut self,
        items: &[SExpr],
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        graph: &mut dyn GraphSubstrate,
        fuel: &mut u64,
    ) -> Result<(), EvalError> {
        charge(fuel, cost::STRUCTURAL_VERB_BASE)?;
        let [_, type_ref, from, to, SExpr::Atom(Atom::Keyword(kw)), strength_expr, field_inits @ ..] =
            items
        else {
            return Err(plain(
                "(add-edge <enum-ref> <expr> <expr> :strength <expr> <field-init>*) \
                 — unrecognized shape",
            ));
        };
        if kw != "strength" {
            return Err(plain(format!("add-edge requires :strength, found :{kw}")));
        }
        if !field_inits.is_empty() {
            return Err(plain(
                "an add-edge <field-init> has no substrate storage: an edge's \
                 state is one f64 strength keyed by (type, from, to). Widening \
                 it widens the canonical state_hash field set — a declared \
                 substrate gap (R9 chapter C2), never silently dropped",
            ));
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
            .map_err(from_graph)?;
        self.record(Write::EdgeAdded {
            edge_type: edge_type.to_owned(),
            from: from_id,
            to: to_id,
            strength,
        });
        Ok(())
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
            .map_err(from_graph)?;
        self.record(Write::EdgeRemoved {
            edge_type: edge_type.to_owned(),
            from: from_id,
            to: to_id,
        });
        Ok(())
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
        // Membership is a SET and declared member order is never observable
        // (§2.6 draft ruling D25; `members_of` returns ascending NodeId).
        // Canonicalize HERE so the write log cannot become the one surface
        // that leaks source order back. Duplicates stay the substrate's
        // error to raise — sorting does not mask them.
        members.sort_unstable();
        let id = graph
            .add_hyperedge(hyperedge_type, &members)
            .map_err(from_graph)?;
        self.declared_hyperedges.insert(name, id);
        // The member list is recorded WHOLE — the log expands it into pairs
        // no more than the executor does (VIII.9) — and in the canonical
        // ascending order established above, never as declared (D25).
        self.record(Write::HyperedgeAdded {
            id,
            hyperedge_type: hyperedge_type.to_owned(),
            members,
        });
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
    /// is a loud declared gap (i128 exactness does not survive an f64
    /// attribute), never a lossy cast — typed Currency storage is DEFERRED
    /// TO ITS FIRST CONSUMER (Director ruling, 2026-08-11 popup), not to a
    /// fixed phase boundary.
    ///
    /// **§2.13 addendum (D101).** When `field` is declared `BslType::Enum`
    /// (`self.types`), the write funnels through [`Self::enum_write_value`]
    /// instead: the ordinal is never a surface value, so a bare `Real`/`Int`
    /// here is exactly as illegal as it is at load
    /// (`scenario.rs::attribute_value_enum`, `E-LOAD-056`'s runtime
    /// re-check, `E-EVAL-042`). For every OTHER field this arm is a no-op —
    /// the existing catch-all below still refuses `Value::Enum` reaching a
    /// non-enum field with its ORIGINAL message, unchanged.
    fn numeric_write_value(
        &self,
        expr: &SExpr,
        env: &EvalEnv<'_>,
        host: &dyn IntrinsicHost,
        fuel: &mut u64,
        field: &str,
    ) -> Result<f64, EvalError> {
        let value = evaluate(expr, env, host, fuel)?;
        if let Some(BslType::Enum(ty)) = self.types.fields.get(field).map(|decl| &decl.ty) {
            return self.enum_write_value(value, field, *ty);
        }
        match value {
            // The evaluator guards its own arithmetic (E-EVAL-014), but a
            // value can reach the store boundary without passing through it
            // — an intrinsic host's return is the trait's named
            // defence-in-depth case. Guard HERE, the one funnel every write
            // value crosses, because §3.3's range check only rejects
            // non-finites on unit-interval fields: an Int or unbounded Real
            // field would otherwise take a NaN straight into the tick hash.
            Value::Real(r) if !r.is_finite() => Err(EvalError::coded(
                EvalCode::NonFinite,
                format!("refusing to store a non-finite value to {field}"),
            )),
            Value::Real(r) => Ok(r),
            // i64 -> f64 is deterministic; exactness beyond 2^53 belongs to
            // the typed-attribute-storage gap named in the module doc.
            #[allow(clippy::cast_precision_loss)]
            Value::Int(n) => Ok(n as f64),
            Value::Currency(_) => Err(plain(format!(
                "writing a Currency value to {field} needs typed attribute \
                 storage — the Director ruled (2026-08-11) that this lands \
                 with Currency's first real consumer — refusing the lossy \
                 f64 cast"
            ))),
            other => Err(plain(format!(
                "cannot store {other:?} as a numeric node attribute"
            ))),
        }
    }

    /// The `:enum-type`-declared half of [`Self::numeric_write_value`]
    /// (§2.13, D101): accepts ONLY a `Value::Enum` of the field's exact
    /// declared type, resolves its ordinal through `self.enums`, and
    /// returns `ordinal as f64` — the SAME binary64 lane every other
    /// declared type's write already uses. Everything else — a bare
    /// `Value::Real`/`Value::Int` (the eval-time form of the load-time
    /// bare-number mistake), a `Value::Enum` of a DIFFERENT declared type,
    /// or any other value — is `E-EVAL-042`.
    fn enum_write_value(
        &self,
        value: Value,
        field: &str,
        ty: EnumTypeId,
    ) -> Result<f64, EvalError> {
        let Value::Enum { enum_type, member } = value else {
            return Err(EvalError::coded(
                EvalCode::EnumWriteShapeViolation,
                format!(
                    "update-node {field}: an enum-typed field is written \
                     ONLY as <EnumType>/<MEMBER> — the ordinal is never a \
                     surface value; found {value:?} (§2.13)"
                ),
            ));
        };
        let declared_type = self.enums.name(ty);
        if enum_type != declared_type {
            return Err(EvalError::coded(
                EvalCode::EnumWriteShapeViolation,
                format!(
                    "update-node {field}: declared enum type is \
                     {declared_type}, found {enum_type}/{member} (§2.13)"
                ),
            ));
        }
        let Some(ordinal) = self.enums.ordinal(ty, &member) else {
            return Err(EvalError::coded(
                EvalCode::EnumWriteShapeViolation,
                format!(
                    "update-node {field}: {declared_type} has no member \
                     {member} — never a default (§2.13)"
                ),
            ));
        };
        Ok(f64::from(ordinal))
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

/// The six graph-shape verbs Task 12's collect-then-apply pre-state split
/// (§4.2 chapter C4) does not defer: deferring a MINTING verb needs a
/// placeholder-id scheme that repair does not specify (see
/// [`EffectExecutor::collect_effects`]'s own doc). The single source of
/// truth [`check_no_deferred_shape_verbs`] (the LOAD-time gate) walks
/// against.
pub(crate) const DEFERRED_SHAPE_VERBS: [&str; 6] = [
    "add-node",
    "remove-node",
    "add-edge",
    "remove-edge",
    "add-hyperedge",
    "remove-hyperedge",
];

/// Refuse, **at load**, a rule whose `<when>`/`<effects>` use any of the
/// `DEFERRED_SHAPE_VERBS` (#519 fix round, fix 4 — the regression this
/// repairs). Before this gate such a rule loaded clean and only failed at
/// RUNTIME, the first tick whose guard admitted a subject — the exact
/// load-passes/execute-dies shape `tick.rs::check_sources_servable`
/// exists to prevent for bindings, and a violation of this chapter's own
/// law: "every check in this chapter runs at content load, before any
/// tick executes" (§3). Walks guard/for-each nesting the same way
/// [`crate::rule_pipeline`]'s fold walk (`typecheck_rule_folds`) does —
/// the whole rule form, since these verbs are legal only in `<when>`
/// (never — they are effect-position-only) or `<effects>`, and walking
/// the header costs nothing extra.
///
/// `EffectExecutor::collect_items`'s own runtime refusal for these six
/// verbs stays live as defense in depth for any caller that reaches
/// `collect_effects` directly, bypassing this gate (as this module's own
/// `the_collect_path_refuses_a_shape_verb_naming_it` test does) — but
/// every rule `rule_pipeline::load_rule_form` accepts is now refused HERE
/// first, before that arm can ever fire in production.
///
/// # Errors
///
/// An uncoded message (no §2 grammar production is violated — every one
/// of these verbs IS legal content; this is Task 12's own composition
/// limit, the same no-invented-codes precedent `LoadError::Content` and
/// `evaluator.rs`'s `EFFECT_POSITION_ONLY`/`UNSERVED_EXPRESSION_HEADS`
/// tables use) naming the verb and the follow-on that will serve it.
pub fn check_no_deferred_shape_verbs(rule: &SExpr) -> Result<(), String> {
    if let Some(verb) = find_deferred_shape_verb(rule) {
        return Err(format!(
            "({verb} …) is one of the six graph-shape verbs Task 12's \
             collect-then-apply pre-state repair (§4.2 chapter C4) does \
             not yet serve — deferring a MINTING verb needs a \
             placeholder-id scheme this repair does not specify, so \
             run_tick's two-pass split cannot defer {verb} the way it \
             defers update-node. Refused HERE, at load (§3's own law: \
             every check in this chapter runs at content load, before any \
             tick executes), rather than letting the rule load clean and \
             abort the first tick whose guard admits a subject. The \
             follow-on that will serve {verb} is the placeholder-id \
             design EffectExecutor::collect_effects's own doc escalates."
        ));
    }
    Ok(())
}

/// Depth-first search for the first [`DEFERRED_SHAPE_VERBS`] head anywhere
/// in `expr`. `Option<&str>` borrows the symbol straight out of the AST —
/// no allocation for a check that runs on every rule at load.
fn find_deferred_shape_verb(expr: &SExpr) -> Option<&str> {
    let SExpr::List(items) = expr else {
        return None;
    };
    if let Some(SExpr::Atom(Atom::Symbol(head))) = items.first() {
        if DEFERRED_SHAPE_VERBS.contains(&head.as_str()) {
            return Some(head.as_str());
        }
    }
    for item in items {
        if let Some(verb) = find_deferred_shape_verb(item) {
            return Some(verb);
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::fuel::IntrinsicCosts;
    use crate::intrinsic_host::EmptyIntrinsicHost;
    use crate::reader::read;
    use crate::types::{FieldDecl, FieldKind};
    use crate::write_log::CollectingWriteLog;
    use babylon_graph::memory::MemoryGraph;

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

    /// The `types()` fixture above declares no enum-typed field — an empty
    /// registry is the honest "no `defenum`s in scope" input for every
    /// test in this module that does not build its own (the enum-write
    /// tests below build `organization_types()`/an `OrgKind` registry
    /// instead).
    fn enums() -> EnumRegistry {
        EnumRegistry::default()
    }

    struct Fixture {
        graph: MemoryGraph,
        self_id: NodeId,
        costs: IntrinsicCosts,
    }

    impl Fixture {
        fn new() -> Self {
            let mut graph = MemoryGraph::new();
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
                graph: None,
                elements: Vec::new(),
            };
            let types = types();
            let enums = enums();
            let mut executor = EffectExecutor::new(&types, &enums);
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

        /// The same run with the ADR182 R1 write log installed. Returns the
        /// log ALONGSIDE the result rather than through it: "a failed write
        /// leaves no record" is only assertable if the log survives the
        /// error.
        fn run_observed(
            &mut self,
            effects_source: &str,
            fuel: &mut u64,
        ) -> (Result<(), EvalError>, CollectingWriteLog) {
            let (form, _) = read(effects_source).expect("effects source must parse");
            let SExpr::List(items) = form else {
                unreachable!()
            };
            let env = EvalEnv {
                bindings: HashMap::from([("self".to_owned(), Value::NodeRef(self.self_id))]),
                intrinsic_costs: &self.costs,
                graph: None,
                elements: Vec::new(),
            };
            let types = types();
            let enums = enums();
            let mut log = CollectingWriteLog::new();
            let mut sink = CollectingSink::default();
            let result = {
                let mut executor =
                    EffectExecutor::observed(&types, &enums, "hunger/agitate", &mut log);
                executor.execute_effects(
                    &items[1..],
                    &env,
                    &EmptyIntrinsicHost,
                    &mut self.graph,
                    &mut sink,
                    fuel,
                )
            };
            (result, log)
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
        let grown = grown.unwrap();
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
        assert!(err.message.contains("typed attribute storage"), "{err}");
        assert!(err.message.contains("first real consumer"), "{err}");
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

    // ---- the ADR182 R1 write log ----

    /// Read the substrate back through the §2.6 query surface, whose
    /// iteration order is contractual — NOT through `Debug`, whose `HashMap`
    /// ordering is not.
    fn snapshot(graph: &MemoryGraph) -> Vec<String> {
        let mut out = Vec::new();
        for id in graph.nodes("SOCIAL_CLASS") {
            let agitation = graph.node_attribute(id, "social-class/agitation").ok();
            let head_count = graph.node_attribute(id, "social-class/head-count").ok();
            out.push(format!("node {id:?} {agitation:?} {head_count:?}"));
        }
        for (from, to) in graph.edges("SOLIDARITY") {
            out.push(format!("edge {from:?}->{to:?}"));
        }
        out
    }

    /// The script the equivalence contract runs: one of every recorded verb.
    const EVERY_VERB: &str = "(effects \
         (update-node self social-class/agitation (add 0.05i)) \
         (add-node NodeType/SOCIAL_CLASS recruit (social-class/agitation 0.2i)) \
         (add-edge EdgeType/SOLIDARITY recruit self :strength 0.5c) \
         (remove-edge EdgeType/SOLIDARITY recruit self) \
         (add-hyperedge HyperedgeType/CELL nucleus (members self recruit)) \
         (remove-hyperedge nucleus))";

    #[test]
    fn observation_changes_neither_state_nor_fuel() {
        // Discipline 1, the reason the log is safe to ship: observing is not
        // a semantic mode. If this ever fails, the write log has become a
        // participant and the engine's determinism hash is at risk.
        let mut unobserved = Fixture::new();
        let mut plain_fuel = 256;
        unobserved.run(EVERY_VERB, &mut plain_fuel).unwrap();

        let mut observed = Fixture::new();
        let mut observed_fuel = 256;
        let (result, _log) = observed.run_observed(EVERY_VERB, &mut observed_fuel);
        result.unwrap();

        assert_eq!(
            snapshot(&unobserved.graph),
            snapshot(&observed.graph),
            "an observed run must leave the substrate exactly as an unobserved one does"
        );
        assert_eq!(
            plain_fuel, observed_fuel,
            "the log must not charge the §4.5 meter — fuel is a conformance quantity"
        );
    }

    #[test]
    fn every_recorded_verb_lands_in_source_order() {
        let mut fixture = Fixture::new();
        let mut fuel = 256;
        let (result, log) = fixture.run_observed(EVERY_VERB, &mut fuel);
        result.unwrap();

        let self_id = fixture.self_id;
        let recruit = NodeId(self_id.0 + 1);
        assert_eq!(
            log.writes(),
            vec![
                Write::NodeAttribute {
                    id: self_id,
                    field: "social-class/agitation".to_owned(),
                    previous: Some(0.10),
                    value: 0.10 + 0.05,
                },
                Write::NodeAdded {
                    id: recruit,
                    node_type: "SOCIAL_CLASS".to_owned(),
                },
                Write::NodeAttribute {
                    id: recruit,
                    field: "social-class/agitation".to_owned(),
                    previous: None,
                    value: 0.2,
                },
                Write::EdgeAdded {
                    edge_type: "SOLIDARITY".to_owned(),
                    from: recruit,
                    to: self_id,
                    strength: 0.5,
                },
                Write::EdgeRemoved {
                    edge_type: "SOLIDARITY".to_owned(),
                    from: recruit,
                    to: self_id,
                },
                Write::HyperedgeAdded {
                    id: HyperedgeId(0),
                    hyperedge_type: "CELL".to_owned(),
                    members: vec![self_id, recruit],
                },
                Write::HyperedgeRemoved { id: HyperedgeId(0) },
            ],
        );
        assert_eq!(
            log.records.iter().map(|r| r.ordinal).collect::<Vec<_>>(),
            (0..7).collect::<Vec<_>>(),
            "ordinals count writes performed, densely, in source order"
        );
        assert!(
            log.records.iter().all(|r| r.rule == "hunger/agitate"),
            "every record carries the firing rule's id"
        );
    }

    /// A host whose intrinsic returns a non-finite `Real`. The trait doc
    /// names exactly this as the evaluator's defence-in-depth case: the
    /// evaluator guards its own arithmetic, so a non-finite can only reach
    /// the store boundary from across the intrinsic seam.
    struct RogueIntrinsicHost;

    impl IntrinsicHost for RogueIntrinsicHost {
        fn call(&self, _name: &str, _args: &[Value]) -> Result<Value, EvalError> {
            Ok(Value::Real(f64::NAN))
        }
    }

    #[test]
    fn a_non_finite_never_reaches_the_substrate_on_any_write_path() {
        // §3.3's range check only rejects non-finites on unit-interval
        // fields (`(0.0..=1.0).contains(NaN)` is false). head-count is Int,
        // so without the numeric_write_value guard a NaN would land in the
        // substrate — and in the tick hash. Both write paths are checked:
        // update-node's `set`, and add-node's field-init.
        for source in [
            "(effects (update-node self social-class/head-count (set (rogue))))",
            "(effects (add-node NodeType/SOCIAL_CLASS n (social-class/head-count (rogue))))",
        ] {
            let mut fixture = Fixture::new();
            let mut fuel = 256;
            let (form, _) = read(source).expect("effects source must parse");
            let SExpr::List(items) = form else {
                unreachable!()
            };
            // The intrinsic must be DECLARED or the call fails as a loader
            // bug (E-LOAD-021) before it can return anything at all.
            let costs = IntrinsicCosts::new(HashMap::from([("rogue".to_owned(), 1_u64)]));
            let env = EvalEnv {
                bindings: HashMap::from([("self".to_owned(), Value::NodeRef(fixture.self_id))]),
                intrinsic_costs: &costs,
                graph: None,
                elements: Vec::new(),
            };
            let types = types();
            let enums = enums();
            let mut executor = EffectExecutor::new(&types, &enums);
            let mut sink = CollectingSink::default();
            let err = executor
                .execute_effects(
                    &items[1..],
                    &env,
                    &RogueIntrinsicHost,
                    &mut fixture.graph,
                    &mut sink,
                    &mut fuel,
                )
                .unwrap_err();
            assert_eq!(err.code, Some(EvalCode::NonFinite), "{source}");
            assert!(
                fixture
                    .graph
                    .node_attribute(fixture.self_id, "social-class/head-count")
                    .is_err(),
                "the field must still hold nothing — refused, not stored: {source}"
            );
        }
    }

    #[test]
    fn hyperedge_members_are_canonicalized_never_logged_as_declared() {
        // D25: declared member order is never observable. The substrate
        // sorts on insert, so the write log is the one surface that could
        // leak source order back — it must not.
        let mut fixture = Fixture::new();
        let mut fuel = 256;
        let (result, log) = fixture.run_observed(
            "(effects \
               (add-node NodeType/SOCIAL_CLASS a) \
               (add-node NodeType/SOCIAL_CLASS b) \
               (add-hyperedge HyperedgeType/CELL c (members b a self)))",
            &mut fuel,
        );
        result.unwrap();
        let Some(Write::HyperedgeAdded { members, id, .. }) = log
            .writes()
            .into_iter()
            .find(|w| matches!(w, Write::HyperedgeAdded { .. }))
        else {
            panic!("expected a HyperedgeAdded record")
        };
        assert_eq!(
            members,
            vec![
                fixture.self_id,
                NodeId(fixture.self_id.0 + 1),
                NodeId(fixture.self_id.0 + 2)
            ],
            "declared order was b, a, self — the log must show ascending NodeId"
        );
        assert_eq!(
            members,
            fixture.graph.members_of(id).unwrap(),
            "the log must agree with what the substrate reports"
        );
    }

    #[test]
    fn a_hyperedge_member_list_is_logged_whole_never_expanded() {
        // VIII.9 held at the observation seam too: three members are one
        // record with three ids, never three pairwise records.
        let mut fixture = Fixture::new();
        let mut fuel = 256;
        let (result, log) = fixture.run_observed(
            "(effects \
               (add-node NodeType/SOCIAL_CLASS a) \
               (add-node NodeType/SOCIAL_CLASS b) \
               (add-hyperedge HyperedgeType/CELL c (members self a b)))",
            &mut fuel,
        );
        result.unwrap();
        let hyperedges: Vec<_> = log
            .writes()
            .into_iter()
            .filter(|w| matches!(w, Write::HyperedgeAdded { .. }))
            .collect();
        assert_eq!(hyperedges.len(), 1, "one hyperedge, one record");
        let Write::HyperedgeAdded { members, .. } = &hyperedges[0] else {
            unreachable!()
        };
        assert_eq!(members.len(), 3);
    }

    #[test]
    fn a_write_that_failed_leaves_no_record() {
        // The mirror of §2.8's "absence is never success": the log records
        // what crossed the boundary, not what was attempted. The first
        // effect succeeds, the second trips the §3.3 range check.
        let mut fixture = Fixture::new();
        let mut fuel = 256;
        let (result, log) = fixture.run_observed(
            "(effects \
               (update-node self social-class/head-count (set 100)) \
               (update-node self social-class/agitation (add 0.95i)))",
            &mut fuel,
        );
        assert_eq!(
            result.unwrap_err().code,
            Some(EvalCode::StoreRangeViolation)
        );
        assert_eq!(
            log.writes(),
            vec![Write::NodeAttribute {
                id: fixture.self_id,
                field: "social-class/head-count".to_owned(),
                previous: None,
                value: 100.0,
            }],
            "only the write that landed is recorded"
        );
    }

    #[test]
    fn an_untaken_guard_branch_records_nothing() {
        let mut fixture = Fixture::new();
        let mut fuel = 256;
        let (result, log) = fixture.run_observed(
            "(effects (guard (< 1 0) \
               (update-node self social-class/agitation (add 0.05i))))",
            &mut fuel,
        );
        result.unwrap();
        assert!(
            log.records.is_empty(),
            "the ordinal counts writes, not effect items considered"
        );
    }

    #[test]
    fn a_set_probes_its_previous_value_without_inventing_one() {
        // Discipline 3. `set` does not otherwise read the field, so the log
        // probes — and an unwritten field is None, never an error and never
        // a fabricated 0.0 (the §3.5 honest-null discipline).
        let mut fixture = Fixture::new();
        let mut fuel = 256;
        let (result, log) = fixture.run_observed(
            "(effects \
               (update-node self social-class/head-count (set 100)) \
               (update-node self social-class/head-count (set 250)))",
            &mut fuel,
        );
        result.unwrap();
        let previous: Vec<_> = log
            .records
            .iter()
            .map(|r| match &r.write {
                Write::NodeAttribute { previous, .. } => previous.to_owned(),
                other => panic!("expected attribute writes, got {other:?}"),
            })
            .collect();
        assert_eq!(
            previous,
            vec![None, Some(100.0)],
            "never written -> None; then the value the first set stored"
        );
    }

    // ---- Task 10: for-each in effect position (§2.8 chapter C6) ----

    /// Build the rule's PRE-STATE (what `for-each`'s query reads, through
    /// `env.graph`) and the LIVE graph (what effects actually mutate, the
    /// `&mut` parameter every verb writes through) from the SAME
    /// construction sequence, as TWO SEPARATE `MemoryGraph` objects.
    ///
    /// **Scope, narrowed by the PR #519 fix round.** This split exists only
    /// to satisfy the borrow checker for [`Self::execute_effects`], the
    /// single-pass path that holds `env.graph` and a live `&mut` graph
    /// SIMULTANEOUSLY — which can never alias the same object in safe Rust,
    /// so a caller needs two objects or none at all. Production never does
    /// this (Task 12's `collect_effects`/`apply_pending_write` split takes
    /// SEQUENTIAL borrows of ONE graph — see [`Self::collect_then_apply`]
    /// below), and neither should a test that means to exercise production
    /// semantics: because the two objects here can never be the SAME graph,
    /// no test built on this split can observe an aliasing bug — an
    /// implementation that silently read the WRONG one would still see
    /// equal content and pass. That is exactly what the fix round found: a
    /// mutation to `collect_update_node`'s referent-type check, or to the
    /// collect-path `for-each`, flipped none of this module's for-each/
    /// update-node tests, because every one of them drove
    /// `execute_effects` — production's ABANDONED path since Task 12 —
    /// through this fixture. The two callers left on it
    /// (`update_node_against_a_selection_result_writes_the_selected_node`,
    /// `for_each_query_does_not_see_an_earlier_verbs_effect_in_the_same_list`)
    /// are pinned to `execute_effects` ON PURPOSE — the latter needs
    /// `add-node`, which the collect path refuses by design (§4.2 chapter
    /// C4's scope note) — and stay here; every for-each/update-node test
    /// meaning to prove something about `run_tick`'s actual guarantees now
    /// uses `collect_then_apply` instead.
    fn pre_state_and_live(build: impl Fn(&mut MemoryGraph)) -> (MemoryGraph, MemoryGraph) {
        let mut pre_state = MemoryGraph::new();
        build(&mut pre_state);
        let mut live = MemoryGraph::new();
        build(&mut live);
        (pre_state, live)
    }

    /// Run one `(effects …)` list through the PRODUCTION path (Task 12):
    /// collect against an immutable borrow of `graph`, then — after that
    /// borrow ends — apply every collected write against a mutable one.
    /// This is EXACTLY the two passes `tick.rs::run_tick` runs, on ONE
    /// shared graph object, which is what lets a test built on it catch a
    /// bug in `collect_update_node` or the collect-path `for-each` that
    /// [`Self::pre_state_and_live`]'s two-object split structurally cannot
    /// (see that fixture's own doc for why).
    // Same precedent as `Fixture::run`'s own `#[allow]` above: the event
    // stream's shape is spelled out once in this doc rather than named
    // through a second type alias.
    #[allow(clippy::type_complexity)]
    fn collect_then_apply(
        graph: &mut MemoryGraph,
        types: &TypeEnv,
        enums: &EnumRegistry,
        bindings: HashMap<String, Value>,
        effects_source: &str,
        fuel: &mut u64,
    ) -> Result<Vec<(String, Vec<(String, Value)>)>, EvalError> {
        let (form, _) = read(effects_source).expect("effects source must parse");
        let SExpr::List(items) = form else {
            unreachable!()
        };
        let mut sink = CollectingSink::default();
        let pending = {
            let env = EvalEnv {
                bindings,
                intrinsic_costs: &IntrinsicCosts::default(),
                graph: Some(&*graph as &dyn GraphSubstrate),
                elements: Vec::new(),
            };
            let mut collector = EffectExecutor::new(types, enums);
            collector.collect_effects(&items[1..], &env, &EmptyIntrinsicHost, &mut sink, fuel)?
        };
        let mut applier = EffectExecutor::new(types, enums);
        for write in &pending {
            applier.apply_pending_write(write, &mut *graph)?;
        }
        Ok(sink.events)
    }

    #[test]
    fn for_each_over_an_empty_query_applies_nothing_and_does_not_error() {
        // No ORGANIZATION node exists, so (nodes NodeType/ORGANIZATION)
        // materializes empty. §2.8 chapter C6: an iteration is a COMMAND,
        // and "do it to none" is fully determined — this is the one place
        // an empty set is quiet (unlike mean/min/max/select-*, which must
        // PRODUCE a value and have none to produce, E-EVAL-021). Driven
        // through `collect_then_apply` (#519 fix round) — the PRODUCTION
        // path (`tick.rs::run_tick`'s two passes), not the abandoned
        // `execute_effects` single pass.
        let mut graph = MemoryGraph::new();
        let self_id = graph.add_node("SOCIAL_CLASS").unwrap();
        graph
            .update_node(self_id, "social-class/agitation", 0.10)
            .unwrap();
        let types = types();
        let mut fuel = 64;
        let events = collect_then_apply(
            &mut graph,
            &types,
            &enums(),
            HashMap::from([("self".to_owned(), Value::NodeRef(self_id))]),
            "(effects (for-each (nodes NodeType/ORGANIZATION) \
               (update-node self social-class/agitation (set 0.99i))))",
            &mut fuel,
        )
        .expect("an empty for-each is not an error");
        assert!(events.is_empty());
        let stored = graph
            .node_attribute(self_id, "social-class/agitation")
            .unwrap();
        assert!(
            (stored - 0.10).abs() < 1e-12,
            "an empty for-each applies NOTHING — the body never ran"
        );
    }

    #[test]
    fn for_each_applies_the_body_once_per_element_in_iteration_order() {
        // Driven through `collect_then_apply` (#519 fix round) — the
        // PRODUCTION path, on one shared graph.
        let mut graph = MemoryGraph::new();
        let a = graph.add_node("SOCIAL_CLASS").unwrap();
        let b = graph.add_node("SOCIAL_CLASS").unwrap();
        let c = graph.add_node("SOCIAL_CLASS").unwrap();
        let types = types();
        let mut fuel = 256;
        let events = collect_then_apply(
            &mut graph,
            &types,
            &enums(),
            HashMap::new(),
            "(effects (for-each (nodes NodeType/SOCIAL_CLASS) \
               (emit EventType/RUPTURE (who it))))",
            &mut fuel,
        )
        .unwrap();
        assert_eq!(
            events,
            vec![
                (
                    "RUPTURE".to_owned(),
                    vec![("who".to_owned(), Value::NodeRef(a))]
                ),
                (
                    "RUPTURE".to_owned(),
                    vec![("who".to_owned(), Value::NodeRef(b))]
                ),
                (
                    "RUPTURE".to_owned(),
                    vec![("who".to_owned(), Value::NodeRef(c))]
                ),
            ],
            "once per element, in §2.6 ascending-id iteration order"
        );
    }

    /// The §6.2 family-15 pre-state vector. §2.8 chapter C6, quoted in the
    /// module: "every expression anywhere in an effects list ... is
    /// evaluated against the pre-state". An EARLIER verb in the SAME
    /// effects list (`add-node`) mutates the LIVE graph only — never
    /// `env.graph`, which no verb write path touches — so `for-each`'s
    /// query, materialized through `env.graph`, must not see it. If it did,
    /// TWO `RUPTURE` events would fire instead of one.
    #[test]
    fn for_each_query_does_not_see_an_earlier_verbs_effect_in_the_same_list() {
        let (pre_state, mut live) = pre_state_and_live(|g| {
            g.add_node("SOCIAL_CLASS").unwrap();
        });
        let self_id = NodeId(0);
        let env = EvalEnv {
            bindings: HashMap::from([("self".to_owned(), Value::NodeRef(self_id))]),
            intrinsic_costs: &IntrinsicCosts::default(),
            graph: Some(&pre_state as &dyn GraphSubstrate),
            elements: Vec::new(),
        };
        let types = types();
        let enums = enums();
        let mut executor = EffectExecutor::new(&types, &enums);
        let mut sink = CollectingSink::default();
        let mut fuel = 256;
        let (form, _) = read(
            "(effects \
               (add-node NodeType/SOCIAL_CLASS extra) \
               (for-each (nodes NodeType/SOCIAL_CLASS) \
                 (emit EventType/RUPTURE (n 1))))",
        )
        .expect("must parse");
        let SExpr::List(items) = form else {
            unreachable!()
        };
        executor
            .execute_effects(
                &items[1..],
                &env,
                &EmptyIntrinsicHost,
                &mut live,
                &mut sink,
                &mut fuel,
            )
            .unwrap();
        assert_eq!(
            sink.events.len(),
            1,
            "for-each's query must read the rule's PRE-state (one \
             SOCIAL_CLASS node), never a live mutation an earlier verb in \
             this same effects list already applied (§2.8 chapter C6): {:?}",
            sink.events
        );
    }

    #[test]
    fn nested_for_each_composes_outer_iteration_then_inner_source_order() {
        // Driven through `collect_then_apply` (#519 fix round) — the
        // PRODUCTION path, on one shared graph.
        let mut graph = MemoryGraph::new();
        let sc1 = graph.add_node("SOCIAL_CLASS").unwrap();
        let sc2 = graph.add_node("SOCIAL_CLASS").unwrap();
        let org1 = graph.add_node("ORGANIZATION").unwrap();
        let org2 = graph.add_node("ORGANIZATION").unwrap();
        let types = types();
        let mut fuel = 8192;
        let events = collect_then_apply(
            &mut graph,
            &types,
            &enums(),
            HashMap::new(),
            "(effects \
               (for-each (nodes NodeType/SOCIAL_CLASS) :as outer-elem \
                 (emit EventType/OUTER_MARKER (who outer-elem)) \
                 (for-each (nodes NodeType/ORGANIZATION) \
                   (emit EventType/PAIR (outer outer-elem) (inner it)))))",
            &mut fuel,
        )
        .unwrap();
        assert_eq!(
            events,
            vec![
                (
                    "OUTER_MARKER".to_owned(),
                    vec![("who".to_owned(), Value::NodeRef(sc1))]
                ),
                (
                    "PAIR".to_owned(),
                    vec![
                        ("outer".to_owned(), Value::NodeRef(sc1)),
                        ("inner".to_owned(), Value::NodeRef(org1))
                    ]
                ),
                (
                    "PAIR".to_owned(),
                    vec![
                        ("outer".to_owned(), Value::NodeRef(sc1)),
                        ("inner".to_owned(), Value::NodeRef(org2))
                    ]
                ),
                (
                    "OUTER_MARKER".to_owned(),
                    vec![("who".to_owned(), Value::NodeRef(sc2))]
                ),
                (
                    "PAIR".to_owned(),
                    vec![
                        ("outer".to_owned(), Value::NodeRef(sc2)),
                        ("inner".to_owned(), Value::NodeRef(org1))
                    ]
                ),
                (
                    "PAIR".to_owned(),
                    vec![
                        ("outer".to_owned(), Value::NodeRef(sc2)),
                        ("inner".to_owned(), Value::NodeRef(org2))
                    ]
                ),
            ],
            "outer = iteration order, inner = source order — composed, not \
             an unordered reduction anywhere (§2.8 chapter C6)"
        );
    }

    /// Defense in depth (#519 fix round, fix 3): `collect_effects` is
    /// called directly here, bypassing `load_rule_form`'s LOAD-time gate
    /// entirely (the fix round's own fix 4) — the collect path must refuse
    /// a shape verb on its own, loudly, naming it, never silently doing
    /// nothing. Before this test existed `collect_effects` had exactly one
    /// caller in this whole crate (`collect_then_apply`, itself reachable
    /// only from this module's own tests), and nothing exercised this arm
    /// — proven by the verifier's mutation M5 (turn the six-verb refusal
    /// into a silent `Ok(())`), which flipped zero tests in the crate.
    #[test]
    fn the_collect_path_refuses_a_shape_verb_naming_it() {
        let mut graph = MemoryGraph::new();
        let self_id = graph.add_node("SOCIAL_CLASS").unwrap();
        let types = types();
        let mut fuel = 64;
        let err = collect_then_apply(
            &mut graph,
            &types,
            &enums(),
            HashMap::from([("self".to_owned(), Value::NodeRef(self_id))]),
            "(effects (add-node NodeType/SOCIAL_CLASS recruit))",
            &mut fuel,
        )
        .unwrap_err();
        assert!(err.message.contains("add-node"), "{err}");
    }

    /// A `guard` whose condition evaluates to a non-`Bool` refuses loudly
    /// on the COLLECT path — never a silent not-taken. Before the #519
    /// Copilot harvest both guard arms used
    /// `matches!(…, Value::Bool(true))`, which read `(guard 3 …)` as
    /// `false` and skipped the body without a word — masking exactly the
    /// type bugs §2.8's Bool contract exists to surface. Restoring that
    /// `matches!` form flips this test (mutation-checked).
    #[test]
    fn a_non_bool_guard_condition_is_a_loud_error_not_a_silent_skip() {
        let mut graph = MemoryGraph::new();
        let self_id = graph.add_node("SOCIAL_CLASS").unwrap();
        let types = types();
        let mut fuel = 64;
        let err = collect_then_apply(
            &mut graph,
            &types,
            &enums(),
            HashMap::from([("self".to_owned(), Value::NodeRef(self_id))]),
            "(effects (guard 3 (emit event/rupture)))",
            &mut fuel,
        )
        .unwrap_err();
        assert!(err.message.contains("expected Bool"), "{err}");
    }

    // ---- Task 11: update-node against a computed NodeRef ----

    /// The `TypeEnv` for Task 11's own tests: an `ORGANIZATION` field, so
    /// the §2.7 worked example's shape (`update-node` against a
    /// `select-max` result) is exercisable independent of `Fixture`'s
    /// `SOCIAL_CLASS`-only registry.
    fn organization_types() -> TypeEnv {
        TypeEnv {
            fields: HashMap::from([(
                "organization/claim-strength".to_owned(),
                FieldDecl {
                    ty: BslType::Intensity,
                    kind: FieldKind::Intensive,
                },
            )]),
            exemptions: &[],
        }
    }

    /// The §2.7 worked example's SHAPE: `(update-node (select-max …) …)`.
    /// The reference's own literal example writes `#t` to a `Bool` field
    /// (`organization/holds-office`) — `numeric_write_value` (this module)
    /// has no `Bool`-typed store path today (`GraphSubstrate::update_node`
    /// stores `f64` only; boolean field storage is a separate, pre-existing
    /// gap this task does not own), so this proves the SAME property —
    /// a computed `NodeRef` reaches `update-node`'s write path and writes
    /// the SELECTED element, never the wrong one — against a numeric field
    /// instead.
    #[test]
    fn update_node_against_a_selection_result_writes_the_selected_node() {
        let (pre_state, mut live) = pre_state_and_live(|g| {
            let low = g.add_node("ORGANIZATION").unwrap();
            let high = g.add_node("ORGANIZATION").unwrap();
            g.update_node(low, "organization/claim-strength", 0.2)
                .unwrap();
            g.update_node(high, "organization/claim-strength", 0.9)
                .unwrap();
        });
        let [low, high] = [NodeId(0), NodeId(1)];
        let env = EvalEnv {
            bindings: HashMap::new(),
            intrinsic_costs: &IntrinsicCosts::default(),
            graph: Some(&pre_state as &dyn GraphSubstrate),
            elements: Vec::new(),
        };
        let types = organization_types();
        let enums = enums();
        let mut executor = EffectExecutor::new(&types, &enums);
        let mut sink = CollectingSink::default();
        let mut fuel = 256;
        let (form, _) = read(
            "(effects (update-node \
               (select-max (nodes NodeType/ORGANIZATION) \
                            (field-of it organization/claim-strength)) \
               organization/claim-strength (set 0.5i)))",
        )
        .expect("must parse");
        let SExpr::List(items) = form else {
            unreachable!()
        };
        executor
            .execute_effects(
                &items[1..],
                &env,
                &EmptyIntrinsicHost,
                &mut live,
                &mut sink,
                &mut fuel,
            )
            .unwrap();
        let selected = live
            .node_attribute(high, "organization/claim-strength")
            .unwrap();
        assert!(
            (selected - 0.5).abs() < 1e-12,
            "the SELECTED (higher-scoring) node was written"
        );
        let untouched = live
            .node_attribute(low, "organization/claim-strength")
            .unwrap();
        assert!(
            (untouched - 0.2).abs() < 1e-12,
            "the non-selected node was left alone"
        );
    }

    /// §2.10 discipline 1's runtime half (R9 chapter C2): a reference has no
    /// static type (§3.1), so the field-owner-vs-referent disagreement that
    /// `add-node`/`add-edge`/`add-hyperedge` catch at LOAD as `E-TYPE-014`
    /// can only be caught HERE, at evaluation, as `E-EVAL-033`. Before this
    /// task `update_node` ran only `store_range_check` on the field — this
    /// write SUCCEEDED SILENTLY.
    #[test]
    fn update_node_whose_referent_is_of_another_type_is_e_eval_033() {
        // Driven through `collect_then_apply` (#519 fix round) — the
        // PRODUCTION path (`collect_update_node`, not `update_node`'s
        // execute-path copy).
        let mut graph = MemoryGraph::new();
        let subject = graph.add_node("SOCIAL_CLASS").unwrap();
        let types = TypeEnv {
            fields: HashMap::from([(
                "territory/population".to_owned(),
                FieldDecl {
                    ty: BslType::Int,
                    kind: FieldKind::Extensive,
                },
            )]),
            exemptions: &[],
        };
        let mut fuel = 64;
        let err = collect_then_apply(
            &mut graph,
            &types,
            &enums(),
            HashMap::from([("self".to_owned(), Value::NodeRef(subject))]),
            "(effects (update-node self territory/population (set 5)))",
            &mut fuel,
        )
        .unwrap_err();
        assert_eq!(err.code, Some(EvalCode::AccessorTypeOrValueMismatch));
        assert_eq!(err.code.unwrap().spec_code(), "E-EVAL-033");
        assert!(
            graph
                .node_attribute(subject, "territory/population")
                .is_err(),
            "the refused write must not have landed"
        );
    }

    #[test]
    fn a_set_on_a_never_written_field_still_succeeds_under_observation() {
        // The determinism trap this design exists to avoid: probing the
        // prior value must not propagate `node_attribute`'s honest-null
        // error, or an observed run would fail where an unobserved one
        // succeeds. Both paths are asserted green here.
        for observe in [false, true] {
            let mut fixture = Fixture::new();
            let mut fuel = 256;
            let source = "(effects (update-node self social-class/head-count (set 100)))";
            let result = if observe {
                fixture.run_observed(source, &mut fuel).0
            } else {
                fixture.run(source, &mut fuel).map(|_| ())
            };
            assert!(
                result.is_ok(),
                "observe={observe} must not change the verdict"
            );
        }
    }

    // ==================================================== §2.13 (D101):
    // the runtime enum write path — `update-node` on an `enum`-typed
    // field. Driven through `collect_then_apply` (the SAME two-call
    // sequence — `collect_effects` then `apply_pending_write` — that
    // `tick.rs::run_tick` runs in production; see that helper's own doc),
    // never `execute_effects` (test-harness-only since Task 12).

    /// `OrgKind` in declaration order: `STATE_APPARATUS`=0, `BUSINESS`=1,
    /// `POLITICAL_FACTION`=2, `CIVIL_SOCIETY`=3 — matching the spec's own
    /// worked example (Organization spec §1 Q1/Q15). One `organization/kind`
    /// field declared `BslType::Enum`, `FieldKind::NotApplicable`.
    fn org_kind_types_and_enums() -> (TypeEnv, EnumRegistry) {
        let mut enums = EnumRegistry::default();
        let ty = enums
            .declare(
                "OrgKind",
                &[
                    "STATE_APPARATUS".to_owned(),
                    "BUSINESS".to_owned(),
                    "POLITICAL_FACTION".to_owned(),
                    "CIVIL_SOCIETY".to_owned(),
                ],
            )
            .unwrap();
        let types = TypeEnv {
            fields: HashMap::from([(
                "organization/kind".to_owned(),
                FieldDecl {
                    ty: BslType::Enum(ty),
                    kind: FieldKind::NotApplicable,
                },
            )]),
            exemptions: &[],
        };
        (types, enums)
    }

    #[test]
    fn update_node_writes_an_enum_ref_and_stores_the_declared_ordinal() {
        let mut graph = MemoryGraph::new();
        let id = graph.add_node("ORGANIZATION").unwrap();
        let (types, enums) = org_kind_types_and_enums();
        let mut fuel = 64;
        collect_then_apply(
            &mut graph,
            &types,
            &enums,
            HashMap::from([("self".to_owned(), Value::NodeRef(id))]),
            "(effects (update-node self organization/kind (set OrgKind/POLITICAL_FACTION)))",
            &mut fuel,
        )
        .expect("a matching enum-ref write must succeed");
        let stored = graph.node_attribute(id, "organization/kind").unwrap();
        assert!(
            (stored - 2.0).abs() < 1e-12,
            "POLITICAL_FACTION is declaration-order ordinal 2, stored: {stored}"
        );
    }

    #[test]
    fn a_bare_real_write_into_an_enum_field_is_e_eval_042() {
        // The eval-time form of the load-time bare-number mistake
        // (`scenario.rs::attribute_value_enum`, E-LOAD-056) — the ordinal
        // is never a surface value, checked again HERE because content
        // cannot be checked once and for all at load (§3.7/§4.3's
        // two-site pattern).
        let mut graph = MemoryGraph::new();
        let id = graph.add_node("ORGANIZATION").unwrap();
        let (types, enums) = org_kind_types_and_enums();
        let mut fuel = 64;
        let err = collect_then_apply(
            &mut graph,
            &types,
            &enums,
            HashMap::from([("self".to_owned(), Value::NodeRef(id))]),
            "(effects (update-node self organization/kind (set 2)))",
            &mut fuel,
        )
        .unwrap_err();
        assert_eq!(err.code, Some(EvalCode::EnumWriteShapeViolation));
        assert_eq!(err.code.map(EvalCode::spec_code), Some("E-EVAL-042"));
    }

    #[test]
    fn a_cross_enum_type_write_is_e_eval_042() {
        // NodeType/BUSINESS is a perfectly legal <enum-ref> — of the WRONG
        // declared type for this field, but with a MEMBER NAME that
        // collides with a real OrgKind member (BUSINESS, ordinal 1) —
        // deliberately, so a mutant that skipped the type comparison and
        // fell through to the member lookup would find "BUSINESS" and
        // WRONGLY succeed with ordinal 1, rather than failing for a
        // different, equally-plausible-looking reason (an earlier version
        // of this test used SOCIAL_CLASS, whose absence from OrgKind's
        // member list made the member-lookup branch ALSO refuse — masking
        // whether the type check itself ran; caught by mutation testing).
        // No load-time gate catches this either way (update-node's write
        // operand is not one of `grammar.rs`'s typed ENUM_REF_POSITIONS),
        // so this proves the runtime check is load-bearing on its own.
        let mut graph = MemoryGraph::new();
        let id = graph.add_node("ORGANIZATION").unwrap();
        let (types, enums) = org_kind_types_and_enums();
        let mut fuel = 64;
        let err = collect_then_apply(
            &mut graph,
            &types,
            &enums,
            HashMap::from([("self".to_owned(), Value::NodeRef(id))]),
            "(effects (update-node self organization/kind (set NodeType/BUSINESS)))",
            &mut fuel,
        )
        .unwrap_err();
        assert_eq!(err.code, Some(EvalCode::EnumWriteShapeViolation));
        assert!(
            err.message.contains("declared enum type is OrgKind"),
            "{}",
            err.message
        );
        assert!(err.message.contains("NodeType/BUSINESS"), "{}", err.message);
    }

    #[test]
    fn an_undeclared_member_of_the_right_type_is_e_eval_042() {
        // OrgKind/NOWHERE lexes and type-checks fine (the reader never
        // validates enum-ref MEMBERSHIP, only shape) — the registry lookup
        // at write time is what catches it.
        let mut graph = MemoryGraph::new();
        let id = graph.add_node("ORGANIZATION").unwrap();
        let (types, enums) = org_kind_types_and_enums();
        let mut fuel = 64;
        let err = collect_then_apply(
            &mut graph,
            &types,
            &enums,
            HashMap::from([("self".to_owned(), Value::NodeRef(id))]),
            "(effects (update-node self organization/kind (set OrgKind/NOWHERE)))",
            &mut fuel,
        )
        .unwrap_err();
        assert_eq!(err.code, Some(EvalCode::EnumWriteShapeViolation));
        assert!(err.message.contains("NOWHERE"), "{}", err.message);
    }

    #[test]
    fn an_enum_ref_write_into_a_non_enum_field_refuses_via_the_original_catchall() {
        // The EXISTING catch-all in `numeric_write_value` — unchanged
        // message — still fires for a non-enum field, proving the new
        // branch is scoped to enum-declared fields only (`store field`
        // has no enum in `types` here at all).
        let mut graph = MemoryGraph::new();
        let id = graph.add_node("SOCIAL_CLASS").unwrap();
        let types = types();
        let enums = enums();
        let mut fuel = 64;
        let err = collect_then_apply(
            &mut graph,
            &types,
            &enums,
            HashMap::from([("self".to_owned(), Value::NodeRef(id))]),
            "(effects (update-node self social-class/head-count (set OrgKind/BUSINESS)))",
            &mut fuel,
        )
        .unwrap_err();
        assert!(
            err.message.contains("cannot store"),
            "the ORIGINAL non-enum catch-all message must be unchanged: {}",
            err.message
        );
    }
}
