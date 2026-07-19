//! The two node kinds and membership edge type for the bipartite representation.

use serde::{Deserialize, Serialize};

/// The two roles in the bipartite structure.
///
/// `Agent` nodes are the hypergraph's nodes (entities). `Hyperedge` nodes
/// are the hypergraph's edges — their members are exactly their `Agent`
/// neighbors in the bipartite graph.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum NodeKind<N, E> {
    /// An entity node (XGI "node"). Carries its own attributes.
    Agent(N),
    /// A hyperedge node (XGI "edge"). The members of the hyperedge are
    /// exactly the Agent neighbors.
    Hyperedge(E),
}

/// A membership edge in the bipartite graph: Agent <-> Hyperedge.
///
/// Carries per-membership attributes (XGI's edge-member attrs).
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MembershipEdge<M> {
    /// The per-membership data (e.g., role, strength, visibility).
    pub member_data: M,
}

/// A direction for directed membership in a [`super::dihypergraph::DiHypergraph`].
///
/// XGI parity: XGI's direction strings `"in"`/`"out"` — `"in"` puts the
/// node in the edge's TAIL (`_edge[e]["in"]`, the arc agent→edge), `"out"`
/// in the HEAD (`_edge[e]["out"]`, the arc edge→agent). The enum makes an
/// invalid direction compile-time-impossible where XGI raises
/// `XGIError("Invalid direction!")` at runtime (divergence D14); the serde
/// spelling is the lowercase XGI string so the Phase 7 binding maps
/// strings onto variants directly.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Direction {
    /// Tail membership — the arc agent→edge (XGI `"in"`).
    In,
    /// Head membership — the arc edge→agent (XGI `"out"`).
    Out,
}
