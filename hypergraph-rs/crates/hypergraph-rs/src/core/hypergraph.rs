//! The core `Hypergraph` data structure.

use rustworkx_core::petgraph::stable_graph::{NodeIndex, StableDiGraph};
use indexmap::IndexMap;

use super::error::{EdgeError, NodeError};
use super::kinds::{MembershipEdge, NodeKind};

/// A hypergraph, represented as a bipartite graph.
///
/// The bipartite graph has two node kinds: `Agent` (the hypergraph's nodes)
/// and `Hyperedge` (the hypergraph's edges). Membership edges connect agents
/// to their hyperedges. This representation makes the hypergraph a genuine
/// rustworkx-core plugin — all petgraph/rustworkx-core algorithms work on
/// the bipartite graph directly.
///
/// # Type Parameters
///
/// - `N` — agent node attribute type (defaults to `serde_json::Value`)
/// - `E` — hyperedge attribute type (defaults to `serde_json::Value`)
/// - `M` — per-membership attribute type (defaults to `serde_json::Value`)
pub struct Hypergraph<N = serde_json::Value, E = serde_json::Value, M = serde_json::Value> {
    /// The bipartite graph: Agent nodes + Hyperedge nodes + membership edges.
    /// StableDiGraph preserves insertion order under removal (leaves holes,
    /// doesn't compact) — required for III.7 determinism parity.
    inner: StableDiGraph<NodeKind<N, E>, MembershipEdge<M>>,

    /// Insertion-ordered bimap: agent_id -> NodeIndex in `inner`.
    agent_ids: IndexMap<String, NodeIndex>,

    /// Insertion-ordered bimap: edge_id -> NodeIndex in `inner`.
    hyperedge_ids: IndexMap<String, NodeIndex>,

    /// Auto-incrementing counter for edges added without an explicit `idx`.
    edge_uid_counter: u64,

    /// Graph-level attributes (XGI's `H.graph` dict).
    graph_attrs: serde_json::Map<String, serde_json::Value>,
}

impl<N, E, M> Default for Hypergraph<N, E, M> {
    fn default() -> Self {
        Self::new()
    }
}

impl<N, E, M> Hypergraph<N, E, M> {
    /// Create an empty hypergraph.
    pub fn new() -> Self {
        Self {
            inner: StableDiGraph::new(),
            agent_ids: IndexMap::new(),
            hyperedge_ids: IndexMap::new(),
            edge_uid_counter: 0,
            graph_attrs: serde_json::Map::new(),
        }
    }

    /// The number of agent nodes in the hypergraph.
    pub fn num_nodes(&self) -> usize {
        self.agent_ids.len()
    }

    /// The number of hyperedges in the hypergraph.
    pub fn num_edges(&self) -> usize {
        self.hyperedge_ids.len()
    }

    /// Add a node with attributes. Returns `true` if a new node was created,
    /// `false` if it already existed.
    ///
    /// XGI parity: `H.add_node(node, **attr)`.
    pub fn add_node(&mut self, node_id: &str, attrs: N) -> bool {
        if self.agent_ids.contains_key(node_id) {
            return false;
        }
        let idx = self.inner.add_node(NodeKind::Agent(attrs));
        self.agent_ids.insert(node_id.to_string(), idx);
        true
    }

    /// Check if a node exists in the hypergraph.
    ///
    /// XGI parity: `n in H` / `H.has_node(n)`.
    pub fn has_node(&self, node_id: &str) -> bool {
        self.agent_ids.contains_key(node_id)
    }
}
