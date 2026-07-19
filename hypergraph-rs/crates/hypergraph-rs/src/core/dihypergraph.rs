//! The core `DiHypergraph` data structure.
//!
//! Direction is encoded as **arc presence** on the same bipartite
//! `StableDiGraph<NodeKind<N, E>, MembershipEdge<M>>` substrate as the
//! undirected [`super::hypergraph::Hypergraph`]: tail membership = ONLY
//! the arc `agent → hyperedge`, head membership = ONLY the arc
//! `hyperedge → agent`, and a node in both directions has both arcs.
//! `MembershipEdge` is unchanged — direction is structural, not a flag.

use indexmap::IndexMap;
use rustworkx_core::petgraph::stable_graph::{NodeIndex, StableDiGraph};

use super::error::EdgeError;
use super::kinds::{MembershipEdge, NodeKind};

/// A directed hypergraph, represented as a bipartite graph.
///
/// The bipartite graph has two node kinds: `Agent` (the dihypergraph's
/// nodes) and `Hyperedge` (the dihypergraph's directed edges). Tail
/// membership is the arc `agent → hyperedge`; head membership is the arc
/// `hyperedge → agent`. This realizes spec §3.3's
/// "tail agents → hyperedge → head agents" literally.
///
/// # Type Parameters
///
/// - `N` — agent node attribute type (defaults to `serde_json::Value`)
/// - `E` — hyperedge attribute type (defaults to `serde_json::Value`)
/// - `M` — per-membership attribute type (defaults to `serde_json::Value`)
pub struct DiHypergraph<N = serde_json::Value, E = serde_json::Value, M = serde_json::Value> {
    /// The bipartite graph: Agent nodes + Hyperedge nodes + directed
    /// membership arcs. StableDiGraph preserves insertion order under
    /// removal (leaves holes, doesn't compact) — required for III.7
    /// determinism parity.
    inner: StableDiGraph<NodeKind<N, E>, MembershipEdge<M>>,

    /// Insertion-ordered bimap: agent_id -> NodeIndex in `inner`.
    agent_ids: IndexMap<String, NodeIndex>,

    /// Insertion-ordered bimap: edge_id -> NodeIndex in `inner`.
    hyperedge_ids: IndexMap<String, NodeIndex>,

    /// Auto-incrementing counter for edges added without an explicit `idx`.
    edge_uid_counter: u64,

    /// Graph-level attributes (XGI's `DH.graph` dict).
    graph_attrs: serde_json::Map<String, serde_json::Value>,

    /// Frozen flag: when set, every structural mutator panics (XGI's
    /// `freeze()` monkey-patches a fixed method list with a raiser; the
    /// flag is the data-oriented equivalent).
    frozen: bool,
}

impl<N, E, M> Default for DiHypergraph<N, E, M> {
    fn default() -> Self {
        Self::new()
    }
}

impl<N, E, M> DiHypergraph<N, E, M> {
    /// Create an empty directed hypergraph.
    pub fn new() -> Self {
        Self {
            inner: StableDiGraph::new(),
            agent_ids: IndexMap::new(),
            hyperedge_ids: IndexMap::new(),
            edge_uid_counter: 0,
            graph_attrs: serde_json::Map::new(),
            frozen: false,
        }
    }

    /// Panic if the dihypergraph is frozen. XGI parity: every method XGI's
    /// `freeze()` guards raises `XGIError("Frozen higher-order network
    /// can't be modified")`; the core panics and the PyO3 binding
    /// converts (panic ≡ raise — the D2 error-channel class).
    fn assert_not_frozen(&self) {
        if self.frozen {
            panic!("Frozen higher-order network can't be modified");
        }
    }

    /// The number of agent nodes in the dihypergraph.
    pub fn num_nodes(&self) -> usize {
        self.agent_ids.len()
    }

    /// The number of hyperedges in the dihypergraph.
    pub fn num_edges(&self) -> usize {
        self.hyperedge_ids.len()
    }

    /// Add a node with attributes. Returns `true` if a new node was
    /// created, `false` if it already existed. On an existing node the
    /// attributes are REPLACED (XGI merges dicts; a generic `N` cannot —
    /// the PyO3 binding merges before calling. Divergence D6).
    ///
    /// XGI parity: `DH.add_node(node, **attr)`.
    pub fn add_node(&mut self, node_id: &str, attrs: N) -> bool {
        self.assert_not_frozen();
        if let Some(&idx) = self.agent_ids.get(node_id) {
            if let Some(NodeKind::Agent(w)) = self.inner.node_weight_mut(idx) {
                *w = attrs;
            }
            return false;
        }
        let idx = self.inner.add_node(NodeKind::Agent(attrs));
        self.agent_ids.insert(node_id.to_string(), idx);
        true
    }

    /// Add multiple nodes. XGI parity: `DH.add_nodes_from(nodes_for_adding)`.
    pub fn add_nodes_from(&mut self, nodes: impl IntoIterator<Item = (String, N)>) {
        self.assert_not_frozen();
        for (node_id, attrs) in nodes {
            self.add_node(&node_id, attrs);
        }
    }

    /// Check if a node exists in the dihypergraph.
    ///
    /// XGI parity: `n in DH` / `DH.has_node(n)`.
    pub fn has_node(&self, node_id: &str) -> bool {
        self.agent_ids.contains_key(node_id)
    }

    /// Check if a hyperedge exists.
    ///
    /// XGI parity: `id in DH.edges`.
    pub fn has_edge(&self, edge_id: &str) -> bool {
        self.hyperedge_ids.contains_key(edge_id)
    }

    /// Read a node's attributes.
    ///
    /// XGI parity: `DH.nodes[node_id]`.
    pub fn node_attrs(&self, node_id: &str) -> Option<&N> {
        let idx = *self.agent_ids.get(node_id)?;
        match self.inner.node_weight(idx) {
            Some(NodeKind::Agent(attrs)) => Some(attrs),
            _ => None,
        }
    }

    /// Read an edge's attributes.
    ///
    /// XGI parity: `DH.edges[edge_id]`.
    pub fn edge_attrs(&self, edge_id: &str) -> Option<&E> {
        let idx = *self.hyperedge_ids.get(edge_id)?;
        match self.inner.node_weight(idx) {
            Some(NodeKind::Hyperedge(attrs)) => Some(attrs),
            _ => None,
        }
    }

    /// Read a graph-level attribute.
    ///
    /// XGI parity: `DH.graph[key]`.
    pub fn graph_attr(&self, key: &str) -> Option<&serde_json::Value> {
        self.graph_attrs.get(key)
    }

    /// Set a graph-level attribute.
    ///
    /// XGI parity: `DH.graph[key] = value`.
    pub fn set_graph_attr(&mut self, key: &str, value: serde_json::Value) {
        self.graph_attrs.insert(key.to_string(), value);
    }

    /// All node IDs in insertion order (III.7 determinism parity).
    /// XGI parity: `list(DH.nodes)`.
    pub fn node_ids(&self) -> Vec<String> {
        self.agent_ids.keys().cloned().collect()
    }

    /// All edge IDs in insertion order (III.7 determinism parity).
    /// XGI parity: `list(DH.edges)`.
    pub fn edge_ids(&self) -> Vec<String> {
        self.hyperedge_ids.keys().cloned().collect()
    }

    /// The tail members of an edge (nodes with an arc agent→edge), in
    /// node-insertion order (III.7 determinism parity; XGI returns an
    /// unordered set — divergence D5, we are strictly more defined).
    ///
    /// XGI parity: `DH.edges.tail(e)`.
    pub fn tail(&self, edge_id: &str) -> Option<Vec<String>> {
        let he_idx = *self.hyperedge_ids.get(edge_id)?;
        let result = self
            .agent_ids
            .iter()
            .filter(|(_, agent_idx)| self.inner.contains_edge(**agent_idx, he_idx))
            .map(|(nid, _)| nid.clone())
            .collect();
        Some(result)
    }

    /// The head members of an edge (nodes with an arc edge→agent), in
    /// node-insertion order (D5: strictly more defined than XGI's set).
    ///
    /// XGI parity: `DH.edges.head(e)`.
    pub fn head(&self, edge_id: &str) -> Option<Vec<String>> {
        let he_idx = *self.hyperedge_ids.get(edge_id)?;
        let result = self
            .agent_ids
            .iter()
            .filter(|(_, agent_idx)| self.inner.contains_edge(he_idx, **agent_idx))
            .map(|(nid, _)| nid.clone())
            .collect();
        Some(result)
    }

    /// The directed members of an edge: `(tail, head)` — TAIL FIRST
    /// (probed XGI order).
    ///
    /// XGI parity: `DH.edges.dimembers(e)`.
    pub fn dimembers(&self, edge_id: &str) -> Option<(Vec<String>, Vec<String>)> {
        let tail = self.tail(edge_id)?;
        let head = self.head(edge_id)?;
        Some((tail, head))
    }

    /// All members of an edge regardless of direction — tail ∪ head in
    /// node-insertion order, deduped (a node in both directions appears
    /// once; D5 ordering).
    ///
    /// XGI parity: `DH.edges.members(e)`.
    pub fn members(&self, edge_id: &str) -> Option<Vec<String>> {
        let he_idx = *self.hyperedge_ids.get(edge_id)?;
        let result = self
            .agent_ids
            .iter()
            .filter(|(_, agent_idx)| {
                self.inner.contains_edge(**agent_idx, he_idx)
                    || self.inner.contains_edge(he_idx, **agent_idx)
            })
            .map(|(nid, _)| nid.clone())
            .collect();
        Some(result)
    }

    /// The directed memberships of a node: `(in_edges, out_edges)` —
    /// "in" = edges where the node is in the HEAD (arc edge→agent),
    /// "out" = edges where the node is in the TAIL (arc agent→edge) —
    /// IN FIRST (probed XGI order: a tail-only node yields
    /// `(set(), {e})`, a head-only node `({e}, set())`). Each vec is in
    /// edge-insertion order (D5).
    ///
    /// XGI parity: `DH.nodes.dimemberships(n)`.
    pub fn dimemberships(&self, node_id: &str) -> Option<(Vec<String>, Vec<String>)> {
        let agent_idx = *self.agent_ids.get(node_id)?;
        let in_edges = self
            .hyperedge_ids
            .iter()
            .filter(|(_, he_idx)| self.inner.contains_edge(**he_idx, agent_idx))
            .map(|(eid, _)| eid.clone())
            .collect();
        let out_edges = self
            .hyperedge_ids
            .iter()
            .filter(|(_, he_idx)| self.inner.contains_edge(agent_idx, **he_idx))
            .map(|(eid, _)| eid.clone())
            .collect();
        Some((in_edges, out_edges))
    }

    /// All memberships of a node regardless of direction, in
    /// edge-insertion order (D5).
    ///
    /// XGI parity: `DH.nodes.memberships(n)`.
    pub fn memberships(&self, node_id: &str) -> Option<Vec<String>> {
        let agent_idx = *self.agent_ids.get(node_id)?;
        let result = self
            .hyperedge_ids
            .iter()
            .filter(|(_, he_idx)| {
                self.inner.contains_edge(agent_idx, **he_idx)
                    || self.inner.contains_edge(**he_idx, agent_idx)
            })
            .map(|(eid, _)| eid.clone())
            .collect();
        Some(result)
    }

    /// Add a directed hyperedge with the given `(tail, head)` members.
    ///
    /// XGI parity: `DH.add_edge((tail, head), idx=id, **attr)`. The
    /// `(Vec<String>, Vec<String>)` pair makes XGI's runtime errors
    /// `XGIError("Directed edge must be a list or tuple!")` (non-pair
    /// members) compile-time-impossible — divergence D14 (type-level
    /// prevention; the Phase 7 binding exposes shims raising XGIError).
    ///
    /// An empty tail AND head creates an empty directed edge — XGI
    /// v0.10.2 behavior verified against the runtime (D1-class parity
    /// with the undirected `add_edge([])`). Duplicates are deduped
    /// within each direction separately (XGI set semantics per
    /// direction); a node listed in BOTH the tail and the head lands in
    /// both (both arcs inserted). Missing member nodes are auto-created
    /// with default attrs. The uid-counter rule is IDENTICAL to the
    /// undirected core's (probed: DiHypergraph shares XGI's
    /// `update_uid_counter` — int idx bumps, D3/D4 apply).
    pub fn add_edge(
        &mut self,
        members: (Vec<String>, Vec<String>),
        idx: Option<String>,
        attrs: E,
    ) -> Result<String, EdgeError>
    where
        N: Default,
        M: Default + Clone,
    {
        self.assert_not_frozen();
        let edge_id = match &idx {
            Some(id) => {
                if self.hyperedge_ids.contains_key(id) {
                    return Err(EdgeError::AlreadyExists {
                        edge_id: id.clone(),
                    });
                }
                id.clone()
            }
            None => self.edge_uid_counter.to_string(),
        };

        if let Some(id) = &idx {
            if let Ok(n) = id.parse::<u64>() {
                if n >= self.edge_uid_counter {
                    self.edge_uid_counter = n + 1;
                }
            }
        } else {
            self.edge_uid_counter += 1;
        }

        let (tail, head) = members;
        let mut seen_tail = std::collections::HashSet::new();
        let unique_tail: Vec<String> = tail
            .into_iter()
            .filter(|m| seen_tail.insert(m.clone()))
            .collect();
        let mut seen_head = std::collections::HashSet::new();
        let unique_head: Vec<String> = head
            .into_iter()
            .filter(|m| seen_head.insert(m.clone()))
            .collect();

        // Auto-create missing nodes in tail-then-head encounter order
        // (XGI iterates tail first, then head).
        for member in unique_tail.iter().chain(unique_head.iter()) {
            if !self.agent_ids.contains_key(member) {
                let nidx = self.inner.add_node(NodeKind::Agent(N::default()));
                self.agent_ids.insert(member.clone(), nidx);
            }
        }

        let he_idx = self.inner.add_node(NodeKind::Hyperedge(attrs));
        self.hyperedge_ids.insert(edge_id.clone(), he_idx);

        // Tail membership = arc agent -> edge; head = arc edge -> agent.
        // A node in both directions gets both arcs.
        for member in &unique_tail {
            let agent_idx = self.agent_ids[member];
            self.inner.add_edge(
                agent_idx,
                he_idx,
                MembershipEdge {
                    member_data: M::default(),
                },
            );
        }
        for member in &unique_head {
            let agent_idx = self.agent_ids[member];
            self.inner.add_edge(
                he_idx,
                agent_idx,
                MembershipEdge {
                    member_data: M::default(),
                },
            );
        }

        Ok(edge_id)
    }
}
