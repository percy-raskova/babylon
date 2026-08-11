//! Query element materialization (`bsl-language.rst` §2.6).
//!
//! **Slice boundary, recorded honestly.** Task 2 of the BSL
//! query-evaluation plan
//! (`docs/superpowers/plans/2026-08-11-bsl-query-evaluation-plan.md`) adds
//! this module a task early, so [`crate::evaluator::EvalEnv`]'s §2.6
//! chapter C8 element stack has a type to hold before any query head
//! actually produces one — the environment cannot express "the element the
//! innermost enclosing iterating form bound" without it. Task 4 is the one
//! that fills in `ElementSet` and `materialize()` (the six heads' dispatch,
//! the §2.6 total order, the `neighbors` type filter); that work is **not**
//! done here.
//!
//! Only [`Element::Node`] exists yet. `Edge(EdgeKey)` (slice 2 — `EdgeKey`
//! is not a type this codebase has minted) and `Hyperedge(HyperedgeId)`
//! (slice 3) are deliberately not added here: minting `EdgeKey` is slice 2's
//! own scope, not Task 2's, and a variant nothing can construct would be
//! dead weight, not forward-compatibility.

use crate::evaluator::Value;
use babylon_graph::substrate::NodeId;

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
