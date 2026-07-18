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
