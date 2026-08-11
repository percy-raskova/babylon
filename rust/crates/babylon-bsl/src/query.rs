//! Query element materialization (`bsl-language.rst` §2.6).
//!
//! **Slice boundary, recorded honestly.** Task 2 of the BSL
//! query-evaluation plan
//! (`docs/superpowers/plans/2026-08-11-bsl-query-evaluation-plan.md`) added
//! this module a task early, so [`crate::evaluator::EvalEnv`]'s §2.6
//! chapter C8 element stack had a type to hold before any query head
//! actually produced one. Task 4 is the one that fills in [`materialize`]:
//! `nodes` and typed `neighbors` — the two heads slice 1 serves. The other
//! four §2.6 heads (`edges`, `hyperedges`, `members-of`, `hyperedges-of`)
//! are recognized here (so a fold/exists/forall/select-* over one of them
//! refuses with the RIGHT slice number, never `eval_intrinsic`'s
//! `E-LOAD-021` misdiagnosis) but are not materialized — that is slice 2/3's
//! work.
//!
//! Only [`Element::Node`] exists yet. `Edge(EdgeKey)` (slice 2 — `EdgeKey`
//! is not a type this codebase has minted) and `Hyperedge(HyperedgeId)`
//! (slice 3) are deliberately not added here: minting `EdgeKey` is slice 2's
//! own scope, not Task 4's, and a variant nothing can construct would be
//! dead weight, not forward-compatibility.
//!
//! **Determinism (Constraint 2).** `nodes`/`neighbors` on `GraphSubstrate`
//! already return a canonically sorted, deduplicated `Vec` (§2.6's total
//! order is the substrate's own contract, not something this module must
//! re-establish). `neighbors`' `NodeType` filter therefore runs as a `Vec`
//! filter **after** that sort — never by re-collecting into a `HashMap`/
//! `HashSet`, which would launder the order through an unspecified one.

use crate::evaluator::{charge, evaluate, require_graph, EvalEnv, EvalError, Value};
use crate::fuel::cost;
use crate::intrinsic_host::IntrinsicHost;
use crate::reader::{Atom, SExpr};
use babylon_graph::substrate::{Direction, NodeId};

/// One materialized graph element (§2.6). See the module doc for why only
/// `Node` exists yet.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum Element {
    /// A materialized node — the only element kind slice 1's node-set query
    /// lane produces.
    Node(NodeId),
}

impl Element {
    /// This element's runtime value. An element reached through `it` or a
    /// `:as` name is a reference of the appropriate kind (§2.6) — for
    /// `Node`, exactly what `self`/`add-node` already produce.
    #[must_use]
    pub fn to_value(self) -> Value {
        match self {
            Self::Node(id) => Value::NodeRef(id),
        }
    }
}

/// The six §2.6 query heads, mapped to the slice that serves them — shared
/// by [`materialize`]'s refusal for the four heads slice 1 does not serve.
/// Kept in sync with `evaluator::UNSERVED_EXPRESSION_HEADS`'s own rows for
/// the same four heads; the two tables answer different questions (that
/// module classifies every expression-position head, this one is the
/// query-position dispatch), so one small duplication here is cheaper than
/// a cross-module lookup for four stable rows.
const UNSERVED_QUERY_HEADS: [(&str, &str); 4] = [
    ("edges", "slice 2"),
    ("hyperedges", "slice 3"),
    ("members-of", "slice 3"),
    ("hyperedges-of", "slice 3"),
];

/// Materialize a `<query>` form in §2.6's total order, charging §3.7's
/// `cost(query)` base (the querying form's own base — `fold`/`exists`/…
/// charge their own separately) plus this query's operand expression(s).
///
/// # Errors
///
/// A query head slice 1 does not serve (named, with its slice); a dangling
/// element operand (the substrate's own loud error, or — for `neighbors`'
/// source operand — an UNCODED loud error per D-row Q3, since the reference
/// names no `E-EVAL` code for a dangling query operand); a missing graph
/// (`require_graph`'s driver error); a malformed shape.
pub fn materialize(
    query: &SExpr,
    env: &EvalEnv<'_>,
    host: &dyn IntrinsicHost,
    fuel: &mut u64,
) -> Result<Vec<Element>, EvalError> {
    let SExpr::List(items) = query else {
        return Err(EvalError::plain(format!(
            "expected a §2.6 query form, found {query:?}"
        )));
    };
    let Some(SExpr::Atom(Atom::Symbol(head))) = items.first() else {
        return Err(EvalError::plain(
            "a query form must be headed by a symbol (§2.6)",
        ));
    };
    match head.as_str() {
        "nodes" => materialize_nodes(items, env, fuel),
        "neighbors" => materialize_neighbors(items, env, host, fuel),
        h => {
            if let Some((_, slice)) = UNSERVED_QUERY_HEADS.iter().find(|(n, _)| *n == h) {
                return Err(EvalError::plain(format!(
                    "({h} …) is a §2.6 query head the query evaluator does not \
                     yet serve — it lands with {slice}, never as a default here"
                )));
            }
            Err(EvalError::plain(format!(
                "{h} is not one of §2.6's six query heads"
            )))
        }
    }
}

/// `(nodes <enum-ref> <node-pred>?)`. The `<node-pred>` operand is a real
/// §2.6 grammar production, but zero conformance vectors and zero content
/// rules exercise it (verified 2026-08-11 the same way D51's `neighbors`
/// finding was) — slice 1's task list names no predicate test, so it stays a
/// loud, named gap rather than a silent one (Constraint 4): a predicated
/// `nodes` refuses by name instead of silently ignoring the predicate or
/// applying an unreviewed reading of it.
fn materialize_nodes(
    items: &[SExpr],
    env: &EvalEnv<'_>,
    fuel: &mut u64,
) -> Result<Vec<Element>, EvalError> {
    charge(fuel, cost::QUERY_BASE)?;
    let [_, type_ref, extra @ ..] = items else {
        return Err(EvalError::plain(
            "(nodes <enum-ref> <node-pred>?) — missing the NodeType operand",
        ));
    };
    if !extra.is_empty() {
        return Err(EvalError::plain(
            "(nodes <enum-ref> <node-pred>) — the element-predicate operand \
             is a real §2.6 production this evaluator does not yet serve \
             (no exercised vector or content rule needs it); slice 1 serves \
             the unpredicated (nodes <enum-ref>) form only",
        ));
    }
    let node_type = enum_member(type_ref)?;
    let graph = require_graph(env, "nodes")?;
    Ok(graph
        .nodes(node_type)
        .into_iter()
        .map(Element::Node)
        .collect())
}

/// `(neighbors <expr> <EdgeType> <direction> <NodeType>)` — D51's mandatory
/// four-operand form. The `NodeType` operand **filters** (D24): a neighbour
/// reached across the named edge type that is not of the annotated type is
/// simply not in the result (§2.6). `GraphSubstrate::neighbors` already
/// returns a sorted, deduplicated `Vec` (D72's set semantics), so filtering
/// it preserves both properties — no re-collection into a hash container.
fn materialize_neighbors(
    items: &[SExpr],
    env: &EvalEnv<'_>,
    host: &dyn IntrinsicHost,
    fuel: &mut u64,
) -> Result<Vec<Element>, EvalError> {
    charge(fuel, cost::QUERY_BASE)?;
    let [_, source_expr, edge_ref, direction_kw, node_ref] = items else {
        return Err(EvalError::plain(
            "(neighbors <expr> <EdgeType> <direction> <NodeType>) — the \
             NodeType fourth operand is MANDATORY (D51; a three-operand form \
             is E-PARSE-042 at load, not a silent bound)",
        ));
    };
    let source = match evaluate(source_expr, env, host, fuel)? {
        Value::NodeRef(id) => id,
        other => {
            return Err(EvalError::plain(format!(
                "(neighbors …)'s first operand must evaluate to a NodeRef, \
                 got {other:?}"
            )))
        }
    };
    let edge_type = enum_member(edge_ref)?;
    let direction = direction_of(direction_kw)?;
    let result_type = enum_member(node_ref)?;
    let graph = require_graph(env, "neighbors")?;
    let neighbor_ids = graph.neighbors(source, edge_type, direction).map_err(|e| {
        // D-row Q3: a query OPERAND naming no live element has no E-EVAL
        // code — §2.6 codes the annotation mismatch (E-EVAL-032) and §2.10
        // codes accessor referents (E-EVAL-033), but the reference codes no
        // query-operand case. Uncoded loud, per the crate's standing
        // "no invented codes" precedent, until the D-row lands.
        EvalError::plain(format!(
            "(neighbors …): {} — a dangling NodeRef never reads as an empty \
             neighborhood (§2.6 honest-null discipline); D-row Q3 (query-\
             evaluation plan) — no E-EVAL code is minted for this case yet",
            e.message
        ))
    })?;
    let mut out = Vec::with_capacity(neighbor_ids.len());
    for id in neighbor_ids {
        // Defense in depth: `neighbor_ids` came from the substrate's own
        // `neighbors()`, whose contract only ever returns live node ids, so
        // `node_type_of` should never fail here. Reaching the error arm
        // would mean the substrate's own contract broke, not a content bug.
        let node_type = graph.node_type_of(id).map_err(|e| {
            EvalError::plain(format!(
                "(neighbors …): a neighbour returned by the substrate is not \
                 itself readable as a live node ({}) — a substrate contract \
                 violation, not a content error",
                e.message
            ))
        })?;
        if node_type == result_type {
            out.push(Element::Node(id));
        }
    }
    Ok(out)
}

/// An enum-ref operand's member name — read directly, exactly as
/// `structural_verbs::EffectExecutor::enum_member` reads one, and NOT
/// through `evaluate()`: an enum-ref atom is a static type annotation here,
/// not a value the query computes with (`bound_checker`'s `atom_cost` charges
/// it 0 for the same reason).
fn enum_member(expr: &SExpr) -> Result<&str, EvalError> {
    match expr {
        SExpr::Atom(Atom::EnumRef { member, .. }) => Ok(member),
        other => Err(EvalError::plain(format!(
            "expected an enum-ref where the grammar requires one, found {other:?}"
        ))),
    }
}

/// `<direction> ::= ":out" | ":in" | ":any"` (§2.6).
fn direction_of(expr: &SExpr) -> Result<Direction, EvalError> {
    match expr {
        SExpr::Atom(Atom::Keyword(kw)) if kw == "out" => Ok(Direction::Out),
        SExpr::Atom(Atom::Keyword(kw)) if kw == "in" => Ok(Direction::In),
        SExpr::Atom(Atom::Keyword(kw)) if kw == "any" => Ok(Direction::Any),
        other => Err(EvalError::plain(format!(
            "expected a direction (:out | :in | :any), found {other:?}"
        ))),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::fuel::IntrinsicCosts;
    use crate::intrinsic_host::EmptyIntrinsicHost;
    use crate::reader::read;
    use babylon_graph::memory::MemoryGraph;
    use babylon_graph::substrate::GraphSubstrate;
    use std::collections::HashMap;

    fn costs() -> IntrinsicCosts {
        IntrinsicCosts::default()
    }

    fn env<'a>(graph: &'a dyn GraphSubstrate, costs: &'a IntrinsicCosts) -> EvalEnv<'a> {
        EvalEnv {
            bindings: HashMap::new(),
            intrinsic_costs: costs,
            graph: Some(graph),
            elements: Vec::new(),
        }
    }

    fn materialize_src(
        source: &str,
        graph: &dyn GraphSubstrate,
        costs: &IntrinsicCosts,
        fuel: &mut u64,
    ) -> Result<Vec<Element>, EvalError> {
        let (expr, _) = read(source).expect("test source must parse");
        materialize(&expr, &env(graph, costs), &EmptyIntrinsicHost, fuel)
    }

    /// M2 (PR #514 fix-round finding): the ORIGINAL 3-node version of this
    /// test declared its nodes as `c, b, a` and claimed that exercised
    /// "descending declared order" — but `MemoryGraph::add_node` assigns
    /// `NodeId`s monotonically in CALL order (`next_id` only ever
    /// increments, and `remove_node`'s own doc records that ids are never
    /// reused), so `c` (added first) always gets the LOWEST id and `a`
    /// (added last) always gets the HIGHEST — insertion call order and
    /// ascending-id order can NEVER diverge for this store, no matter what
    /// symbolic name order the test author chooses. The old comment's claim
    /// ("the LAST-declared node gets the LOWEST id") was the opposite of
    /// what the fixture actually does, and a materializer that merely
    /// echoed insertion order would have passed the old test.
    ///
    /// What genuinely varies — and is worth guarding — is the underlying
    /// `HashMap`'s iteration order (`MemoryGraph::nodes` sorts it before
    /// returning, but nothing upstream of that sort is contractually
    /// ordered). Fifty nodes makes an accidental sorted match astronomically
    /// unlikely, so a `sort_unstable()` regression will show up here with
    /// overwhelming probability where a 3-element fixture would not — see
    /// this fix's commit body for the mutation evidence.
    #[test]
    fn nodes_materializes_in_ascending_id_order() {
        const N: usize = 50;
        let mut graph = MemoryGraph::new();
        for _ in 0..N {
            graph.add_node("SOCIAL_CLASS").unwrap();
        }
        let costs = costs();
        let mut fuel = 10_000;
        let result =
            materialize_src("(nodes NodeType/SOCIAL_CLASS)", &graph, &costs, &mut fuel).unwrap();
        let ids: Vec<NodeId> = result
            .iter()
            .map(|element| match element {
                Element::Node(id) => *id,
            })
            .collect();
        assert_eq!(ids.len(), N);
        assert!(
            ids.windows(2).all(|w| w[0] < w[1]),
            "materialized nodes must be strictly ascending by id: {ids:?}"
        );
    }

    #[test]
    fn nodes_filters_by_the_annotated_type() {
        let mut graph = MemoryGraph::new();
        let sc = graph.add_node("SOCIAL_CLASS").unwrap();
        graph.add_node("ORGANIZATION").unwrap();
        let costs = costs();
        let mut fuel = 1_000;
        let result =
            materialize_src("(nodes NodeType/SOCIAL_CLASS)", &graph, &costs, &mut fuel).unwrap();
        assert_eq!(result, vec![Element::Node(sc)]);
    }

    /// D24: the `neighbors` result `NodeType` FILTERS. A node reachable via
    /// `TENANCY` that is `ORGANIZATION`-typed must not appear when the
    /// annotation reads `NodeType/SOCIAL_CLASS`.
    #[test]
    fn neighbors_filters_by_the_annotated_node_type() {
        let mut graph = MemoryGraph::new();
        let subject = graph.add_node("SOCIAL_CLASS").unwrap();
        let tenant = graph.add_node("SOCIAL_CLASS").unwrap();
        let org = graph.add_node("ORGANIZATION").unwrap();
        graph.add_edge("TENANCY", tenant, subject, 1.0).unwrap();
        graph.add_edge("TENANCY", org, subject, 1.0).unwrap();
        let costs = costs();
        let mut fuel = 1_000;
        let bindings = HashMap::from([("self".to_owned(), Value::NodeRef(subject))]);
        let env = EvalEnv {
            bindings,
            intrinsic_costs: &costs,
            graph: Some(&graph as &dyn GraphSubstrate),
            elements: Vec::new(),
        };
        let (expr, _) =
            read("(neighbors self EdgeType/TENANCY :in NodeType/SOCIAL_CLASS)").unwrap();
        let result = materialize(&expr, &env, &EmptyIntrinsicHost, &mut fuel).unwrap();
        assert_eq!(result, vec![Element::Node(tenant)]);
    }

    /// §6.2 family-17's multiplicity vector (D72): two qualifying edges (one
    /// `:out`, one `:in`) reaching one node under `:any` yield it ONCE —
    /// `neighbors` is a set, not a multiset.
    #[test]
    fn neighbors_is_a_set_not_a_multiset() {
        let mut graph = MemoryGraph::new();
        let subject = graph.add_node("SOCIAL_CLASS").unwrap();
        let other = graph.add_node("SOCIAL_CLASS").unwrap();
        graph.add_edge("SOLIDARITY", subject, other, 1.0).unwrap();
        graph.add_edge("SOLIDARITY", other, subject, 1.0).unwrap();
        let costs = costs();
        let mut fuel = 1_000;
        let bindings = HashMap::from([("self".to_owned(), Value::NodeRef(subject))]);
        let env = EvalEnv {
            bindings,
            intrinsic_costs: &costs,
            graph: Some(&graph as &dyn GraphSubstrate),
            elements: Vec::new(),
        };
        let (expr, _) =
            read("(neighbors self EdgeType/SOLIDARITY :any NodeType/SOCIAL_CLASS)").unwrap();
        let result = materialize(&expr, &env, &EmptyIntrinsicHost, &mut fuel).unwrap();
        assert_eq!(
            result,
            vec![Element::Node(other)],
            "one node, once, not twice"
        );
    }

    #[test]
    fn neighbors_of_a_dangling_node_is_loud_not_empty() {
        let graph = MemoryGraph::new();
        let costs = costs();
        let mut fuel = 1_000;
        let bindings = HashMap::from([("self".to_owned(), Value::NodeRef(NodeId(999)))]);
        let env = EvalEnv {
            bindings,
            intrinsic_costs: &costs,
            graph: Some(&graph as &dyn GraphSubstrate),
            elements: Vec::new(),
        };
        let (expr, _) =
            read("(neighbors self EdgeType/SOLIDARITY :any NodeType/SOCIAL_CLASS)").unwrap();
        let err = materialize(&expr, &env, &EmptyIntrinsicHost, &mut fuel).unwrap_err();
        assert_eq!(err.code, None, "D-row Q3: uncoded loud, not E-EVAL-031");
        assert!(err.message.contains("D-row Q3"), "{err}");
        assert!(err.message.contains("never reads as an empty"), "{err}");
    }

    #[test]
    fn query_materialization_charges_the_3_7_query_base() {
        let mut graph = MemoryGraph::new();
        graph.add_node("SOCIAL_CLASS").unwrap();
        let costs = costs();
        // (nodes <enum-ref>): QUERY_BASE(1) + enum-ref(0) = 1.
        let mut fuel = 10;
        materialize_src("(nodes NodeType/SOCIAL_CLASS)", &graph, &costs, &mut fuel).unwrap();
        assert_eq!(fuel, 9);

        // (neighbors self <EdgeType> <dir> <NodeType>):
        // QUERY_BASE(1) + self variable-ref(1) = 2.
        let subject = NodeId(0);
        let bindings = HashMap::from([("self".to_owned(), Value::NodeRef(subject))]);
        let env = EvalEnv {
            bindings,
            intrinsic_costs: &costs,
            graph: Some(&graph as &dyn GraphSubstrate),
            elements: Vec::new(),
        };
        let (expr, _) =
            read("(neighbors self EdgeType/SOLIDARITY :any NodeType/SOCIAL_CLASS)").unwrap();
        let mut fuel2 = 10;
        materialize(&expr, &env, &EmptyIntrinsicHost, &mut fuel2).unwrap();
        assert_eq!(fuel2, 8);
    }

    #[test]
    fn a_predicated_nodes_query_is_a_loud_named_gap() {
        let graph = MemoryGraph::new();
        let costs = costs();
        let mut fuel = 1_000;
        let err = materialize_src(
            "(nodes NodeType/SOCIAL_CLASS #t)",
            &graph,
            &costs,
            &mut fuel,
        )
        .unwrap_err();
        assert!(err.message.contains("element-predicate"), "{err}");
    }

    #[test]
    fn edges_hyperedges_and_members_of_name_their_slice() {
        let graph = MemoryGraph::new();
        let costs = costs();
        for (source, slice) in [
            ("(edges EdgeType/SOLIDARITY)", "slice 2"),
            ("(hyperedges HyperedgeType/CELL)", "slice 3"),
            ("(members-of self HyperedgeType/CELL)", "slice 3"),
            ("(hyperedges-of self HyperedgeType/CELL)", "slice 3"),
        ] {
            let mut fuel = 1_000;
            let err = materialize_src(source, &graph, &costs, &mut fuel).unwrap_err();
            assert!(err.message.contains(slice), "{source}: {err}");
        }
    }
}
