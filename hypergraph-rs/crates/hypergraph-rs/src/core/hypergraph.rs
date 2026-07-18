//! The core `Hypergraph` data structure.

use indexmap::IndexMap;
use rustworkx_core::petgraph::stable_graph::{NodeIndex, StableDiGraph};

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

impl<N, E, M> std::fmt::Debug for Hypergraph<N, E, M> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Hypergraph")
            .field("nodes", &self.agent_ids.keys().collect::<Vec<_>>())
            .field("edges", &self.hyperedge_ids.keys().collect::<Vec<_>>())
            .finish()
    }
}

impl<N: PartialEq, E: PartialEq, M: PartialEq> PartialEq for Hypergraph<N, E, M> {
    /// Two hypergraphs are equal if they have the same nodes, edges,
    /// memberships, and attributes. XGI parity: `H1 == H2` (XGI delegates
    /// to `xgi.algorithms.equal` with the defaults compare_edge_ids=True,
    /// compare_attrs=True): the edge-id -> members mapping, node attrs,
    /// edge attrs, and net attrs are all significant; insertion/member
    /// order is not. Membership (M) attrs are not compared — XGI's
    /// undirected Hypergraph has no per-membership attr channel.
    fn eq(&self, other: &Self) -> bool {
        if self.agent_ids.len() != other.agent_ids.len() {
            return false;
        }
        for (nid, _) in &self.agent_ids {
            match (self.node_attrs(nid), other.node_attrs(nid)) {
                (Some(a), Some(b)) if a == b => {}
                _ => return false,
            }
        }
        if self.hyperedge_ids.len() != other.hyperedge_ids.len() {
            return false;
        }
        for (eid, _) in &self.hyperedge_ids {
            match (self.edge_attrs(eid), other.edge_attrs(eid)) {
                (Some(a), Some(b)) if a == b => {}
                _ => return false,
            }
            let mut m1 = self.members(eid).unwrap_or_default();
            let mut m2 = other.members(eid).unwrap_or_default();
            m1.sort();
            m2.sort();
            if m1 != m2 {
                return false;
            }
        }
        self.graph_attrs == other.graph_attrs
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
    /// `false` if it already existed. On an existing node the attributes are
    /// REPLACED (XGI: "If node is already in the hypergraph, its attributes
    /// are still updated"; a generic `N` cannot merge dicts — the PyO3
    /// binding merges before calling. Divergence D6).
    ///
    /// XGI parity: `H.add_node(node, **attr)`.
    pub fn add_node(&mut self, node_id: &str, attrs: N) -> bool {
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

    /// Read a node's attributes.
    ///
    /// XGI parity: `H.nodes[node_id]`.
    pub fn node_attrs(&self, node_id: &str) -> Option<&N> {
        let idx = *self.agent_ids.get(node_id)?;
        match self.inner.node_weight(idx) {
            Some(NodeKind::Agent(attrs)) => Some(attrs),
            _ => None,
        }
    }

    /// Read an edge's attributes.
    ///
    /// XGI parity: `H.edges[edge_id]`.
    pub fn edge_attrs(&self, edge_id: &str) -> Option<&E> {
        let idx = *self.hyperedge_ids.get(edge_id)?;
        match self.inner.node_weight(idx) {
            Some(NodeKind::Hyperedge(attrs)) => Some(attrs),
            _ => None,
        }
    }

    /// Mutably access a node's attributes.
    ///
    /// XGI parity: `H.nodes[node_id][key] = value` (in-place attr-dict
    /// mutation).
    pub fn node_attrs_mut(&mut self, node_id: &str) -> Option<&mut N> {
        let idx = *self.agent_ids.get(node_id)?;
        match self.inner.node_weight_mut(idx) {
            Some(NodeKind::Agent(attrs)) => Some(attrs),
            _ => None,
        }
    }

    /// Mutably access an edge's attributes.
    ///
    /// XGI parity: `H.edges[edge_id][key] = value` (in-place attr-dict
    /// mutation).
    pub fn edge_attrs_mut(&mut self, edge_id: &str) -> Option<&mut E> {
        let idx = *self.hyperedge_ids.get(edge_id)?;
        match self.inner.node_weight_mut(idx) {
            Some(NodeKind::Hyperedge(attrs)) => Some(attrs),
            _ => None,
        }
    }

    /// Read a graph-level attribute.
    ///
    /// XGI parity: `H.graph[key]`.
    pub fn graph_attr(&self, key: &str) -> Option<&serde_json::Value> {
        self.graph_attrs.get(key)
    }

    /// Set a graph-level attribute.
    ///
    /// XGI parity: `H.graph[key] = value`.
    pub fn set_graph_attr(&mut self, key: &str, value: serde_json::Value) {
        self.graph_attrs.insert(key.to_string(), value);
    }

    /// Check if a node exists in the hypergraph.
    ///
    /// XGI parity: `n in H` / `H.has_node(n)`.
    pub fn has_node(&self, node_id: &str) -> bool {
        self.agent_ids.contains_key(node_id)
    }

    /// Check if a hyperedge exists.
    ///
    /// XGI parity: `id in H.edges`.
    pub fn has_edge(&self, edge_id: &str) -> bool {
        self.hyperedge_ids.contains_key(edge_id)
    }

    /// Get the edge IDs of which a node is a member, in edge-insertion
    /// order (III.7 determinism parity; XGI returns an unordered set —
    /// divergence D5, we are strictly more defined).
    ///
    /// XGI parity: `H.nodes.memberships(n)`.
    pub fn memberships(&self, node_id: &str) -> Option<Vec<String>> {
        let agent_idx = *self.agent_ids.get(node_id)?;
        let result = self
            .hyperedge_ids
            .iter()
            .filter(|(_, he_idx)| self.inner.contains_edge(agent_idx, **he_idx))
            .map(|(eid, _)| eid.clone())
            .collect();
        Some(result)
    }

    /// Get the node IDs that are members of an edge, in node-insertion
    /// order (III.7 determinism parity; XGI returns an unordered set —
    /// divergence D5, we are strictly more defined).
    ///
    /// XGI parity: `H.edges.members(e)`.
    pub fn members(&self, edge_id: &str) -> Option<Vec<String>> {
        let he_idx = *self.hyperedge_ids.get(edge_id)?;
        let result = self
            .agent_ids
            .iter()
            .filter(|(_, agent_idx)| self.inner.contains_edge(**agent_idx, he_idx))
            .map(|(nid, _)| nid.clone())
            .collect();
        Some(result)
    }

    /// All node IDs in insertion order (III.7 determinism parity).
    /// XGI parity: `list(H.nodes)`.
    pub fn node_ids(&self) -> Vec<String> {
        self.agent_ids.keys().cloned().collect()
    }

    /// All edge IDs in insertion order (III.7 determinism parity).
    /// XGI parity: `list(H.edges)`.
    pub fn edge_ids(&self) -> Vec<String> {
        self.hyperedge_ids.keys().cloned().collect()
    }

    /// Add a hyperedge connecting the given members.
    ///
    /// XGI parity: `H.add_edge(members, idx=id, **attr)`. An empty `members`
    /// creates an empty hyperedge — XGI v0.10.2 behavior verified against
    /// the runtime (its docstring claims XGIError; the docstring is wrong,
    /// and XGI's own test_add_edge asserts empty edges). Divergence D1.
    pub fn add_edge(
        &mut self,
        members: Vec<String>,
        idx: Option<String>,
        attrs: E,
    ) -> Result<String, EdgeError>
    where
        N: Default,
        M: Default + Clone,
    {
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

        let mut seen = std::collections::HashSet::new();
        let unique_members: Vec<String> = members
            .into_iter()
            .filter(|m| seen.insert(m.clone()))
            .collect();

        for member in &unique_members {
            if !self.agent_ids.contains_key(member) {
                let nidx = self.inner.add_node(NodeKind::Agent(N::default()));
                self.agent_ids.insert(member.clone(), nidx);
            }
        }

        let he_idx = self.inner.add_node(NodeKind::Hyperedge(attrs));
        self.hyperedge_ids.insert(edge_id.clone(), he_idx);

        for member in &unique_members {
            let agent_idx = self.agent_ids[member];
            let membership = MembershipEdge {
                member_data: M::default(),
            };
            self.inner.add_edge(agent_idx, he_idx, membership.clone());
            self.inner.add_edge(he_idx, agent_idx, membership);
        }

        Ok(edge_id)
    }

    /// Remove a hyperedge from the hypergraph.
    /// XGI parity: `H.remove_edge(e)`.
    pub fn remove_edge(&mut self, edge_id: &str) -> Result<(), EdgeError> {
        let he_idx = *self.hyperedge_ids.get(edge_id).ok_or(EdgeError::NotFound {
            edge_id: edge_id.to_string(),
        })?;
        self.inner.remove_node(he_idx);
        self.hyperedge_ids.shift_remove(edge_id);
        Ok(())
    }

    /// Remove a node from the hypergraph.
    /// XGI parity: `H.remove_node(n, strong=False, remove_empty=True)`.
    pub fn remove_node(&mut self, node_id: &str, strong: bool) -> Result<(), NodeError> {
        let agent_idx = *self.agent_ids.get(node_id).ok_or(NodeError::NotFound {
            node_id: node_id.to_string(),
        })?;

        let edge_ids: Vec<String> = self.memberships(node_id).unwrap_or_default();

        if strong {
            for eid in edge_ids {
                self.remove_edge(&eid).map_err(|_| NodeError::NotFound {
                    node_id: node_id.to_string(),
                })?;
            }
        } else {
            for eid in &edge_ids {
                let he_idx = self.hyperedge_ids[eid];
                if let Some(e) = self.inner.find_edge(agent_idx, he_idx) {
                    self.inner.remove_edge(e);
                }
                if let Some(e) = self.inner.find_edge(he_idx, agent_idx) {
                    self.inner.remove_edge(e);
                }
                let has_members = self
                    .inner
                    .neighbors(he_idx)
                    .any(|n| matches!(self.inner.node_weight(n), Some(NodeKind::Agent(_))));
                if !has_members {
                    self.inner.remove_node(he_idx);
                    self.hyperedge_ids.shift_remove(eid);
                }
            }
        }

        self.inner.remove_node(agent_idx);
        self.agent_ids.shift_remove(node_id);
        Ok(())
    }

    /// Remove all nodes, edges, and attributes — node attrs, edge attrs,
    /// and graph-level attrs (XGI's `remove_net_attr=True` default).
    ///
    /// Resets the auto-id counter: a cleared hypergraph behaves identically
    /// to a fresh one (`clear() ≡ new()`; III.7 replay-from-empty
    /// determinism). XGI continues its counter — divergence D10.
    ///
    /// XGI parity: `H.clear()`.
    pub fn clear(&mut self) {
        self.inner = StableDiGraph::new();
        self.agent_ids.clear();
        self.hyperedge_ids.clear();
        self.edge_uid_counter = 0;
        self.graph_attrs.clear();
    }

    /// Return an independent deep copy. XGI parity: `H.copy()`.
    pub fn copy(&self) -> Self
    where
        N: Clone,
        E: Clone,
        M: Clone,
    {
        Self {
            inner: self.inner.clone(),
            agent_ids: self.agent_ids.clone(),
            hyperedge_ids: self.hyperedge_ids.clone(),
            edge_uid_counter: self.edge_uid_counter,
            graph_attrs: self.graph_attrs.clone(),
        }
    }

    /// Add a node to an existing edge. Auto-creates both if missing;
    /// idempotent on re-add (set semantics).
    ///
    /// XGI parity: `H.add_node_to_edge(edge, node)`. XGI never touches its
    /// uid counter here — auto-creating a numeric edge id does not bump
    /// `_edge_uid` (and XGI's auto-id add_edge does not existence-check, so
    /// the same sequence with id 0 silently overwrites that edge's members
    /// in XGI). The Rust core bumps iff `edge_id.parse::<u64>()` succeeds —
    /// the D3 rule extended to this method — foreclosing the collision
    /// class. Divergence D11.
    pub fn add_node_to_edge(&mut self, edge_id: &str, node_id: &str) -> Result<(), EdgeError>
    where
        N: Default,
        E: Default,
        M: Default + Clone,
    {
        // Auto-create edge if missing
        if !self.hyperedge_ids.contains_key(edge_id) {
            let he_idx = self.inner.add_node(NodeKind::Hyperedge(E::default()));
            self.hyperedge_ids.insert(edge_id.to_string(), he_idx);
            // D11: bump the uid counter if edge_id is numeric (XGI does not)
            if let Ok(n) = edge_id.parse::<u64>() {
                if n >= self.edge_uid_counter {
                    self.edge_uid_counter = n + 1;
                }
            }
        }
        // Auto-create node if missing
        if !self.agent_ids.contains_key(node_id) {
            let nidx = self.inner.add_node(NodeKind::Agent(N::default()));
            self.agent_ids.insert(node_id.to_string(), nidx);
        }
        // Add the membership edges (both directions for undirected)
        let agent_idx = self.agent_ids[node_id];
        let he_idx = self.hyperedge_ids[edge_id];
        // Set semantics: re-adding an existing membership is a no-op
        if self.inner.find_edge(agent_idx, he_idx).is_none() {
            let membership = MembershipEdge {
                member_data: M::default(),
            };
            self.inner.add_edge(agent_idx, he_idx, membership.clone());
            self.inner.add_edge(he_idx, agent_idx, membership);
        }
        Ok(())
    }

    /// Remove a node from an existing edge; the node itself survives.
    /// `remove_empty` drops the edge if it is left empty (XGI default
    /// `remove_empty=True`).
    ///
    /// XGI parity: `H.remove_node_from_edge(edge, node, remove_empty=True)`.
    /// XGI raises XGIError for a missing edge, a missing node, or a node
    /// not in the edge; the Rust core returns `Err(NodeError::NotFound)`
    /// and the PyO3 binding translates Err -> raise (D2 error channel).
    pub fn remove_node_from_edge(
        &mut self,
        edge_id: &str,
        node_id: &str,
        remove_empty: bool,
    ) -> Result<(), NodeError> {
        let he_idx = *self.hyperedge_ids.get(edge_id).ok_or(NodeError::NotFound {
            node_id: edge_id.to_string(),
        })?;
        let agent_idx = *self.agent_ids.get(node_id).ok_or(NodeError::NotFound {
            node_id: node_id.to_string(),
        })?;

        // Check if the node is actually in the edge
        let edge_to_he = self.inner.find_edge(agent_idx, he_idx);
        let edge_from_he = self.inner.find_edge(he_idx, agent_idx);
        if edge_to_he.is_none() {
            return Err(NodeError::NotFound {
                node_id: format!("node {node_id} not in edge {edge_id}"),
            });
        }

        // Remove the bipartite membership edges
        if let Some(e) = edge_to_he {
            self.inner.remove_edge(e);
        }
        if let Some(e) = edge_from_he {
            self.inner.remove_edge(e);
        }

        // Drop the edge if it was left empty and removal was requested
        if remove_empty {
            let has_members = self
                .inner
                .neighbors(he_idx)
                .any(|n| matches!(self.inner.node_weight(n), Some(NodeKind::Agent(_))));
            if !has_members {
                self.inner.remove_node(he_idx);
                self.hyperedge_ids.shift_remove(edge_id);
            }
        }
        Ok(())
    }

    /// Add multiple nodes. XGI parity: `H.add_nodes_from(nodes_for_adding)`.
    pub fn add_nodes_from(&mut self, nodes: impl IntoIterator<Item = (String, N)>) {
        for (node_id, attrs) in nodes {
            self.add_node(&node_id, attrs);
        }
    }

    /// Add multiple edges. Returns a result per edge.
    pub fn add_edges_from(
        &mut self,
        edges: impl IntoIterator<Item = (Vec<String>, Option<String>, E)>,
    ) -> Vec<Result<String, EdgeError>>
    where
        N: Default,
        M: Default + Clone,
    {
        edges
            .into_iter()
            .map(|(m, i, a)| self.add_edge(m, i, a))
            .collect()
    }
}
