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

use super::error::{EdgeError, MembershipError, NodeError};
use super::kinds::{Direction, MembershipEdge, NodeKind};

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

impl<N, E, M> std::fmt::Debug for DiHypergraph<N, E, M> {
    /// XGI parity: `__repr__` is `f"{cls}({self.edges.dimembers()})"` —
    /// the class name wrapping the edge-dimembers list, one
    /// `(tail, head)` tuple per edge, e.g.
    /// `DiHypergraph([({a, b, c}, {b, d}), ({a}, {})])`. Edges list in
    /// insertion order; both sides format insertion-ordered (divergence
    /// D5: XGI's member sets are unordered — their repr order is
    /// hash-randomized across runs — we are strictly more defined).
    /// Member id strings are unquoted, an empty side formats as `{}`
    /// (Python's `set()` artifact is not reproduced), and lonely nodes
    /// never appear (the repr lists only edges' members).
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "DiHypergraph([")?;
        for (i, eid) in self.hyperedge_ids.keys().enumerate() {
            if i > 0 {
                write!(f, ", ")?;
            }
            let tail = self.tail(eid).unwrap_or_default();
            let head = self.head(eid).unwrap_or_default();
            write!(f, "({{{}}}, {{{}}})", tail.join(", "), head.join(", "))?;
        }
        write!(f, "])")
    }
}

impl<N: PartialEq, E: PartialEq, M: PartialEq> PartialEq for DiHypergraph<N, E, M> {
    /// Two dihypergraphs are equal if they have the same nodes, edges,
    /// directed memberships, and attributes. XGI parity: `DH1 == DH2`
    /// (XGI delegates to `xgi.algorithms.equal` with the defaults
    /// compare_edge_ids=True, compare_attrs=True): the edge-id ->
    /// `{"in": tail, "out": head}` mapping, node attrs, edge attrs, and
    /// net attrs are all significant; insertion/member order is not.
    /// DIRECTION IS SIGNIFICANT (probed v0.10.2: the same nodes with
    /// tail/head swapped are NOT equal; a both-directions member differs
    /// from a tail-only one). Membership (M) attrs are not compared —
    /// matching the undirected core.
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
            let (mut t1, mut h1) = self.dimembers(eid).unwrap_or_default();
            let (mut t2, mut h2) = other.dimembers(eid).unwrap_or_default();
            t1.sort();
            t2.sort();
            h1.sort();
            h2.sort();
            if t1 != t2 || h1 != h2 {
                return false;
            }
        }
        self.graph_attrs == other.graph_attrs
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

    /// Add a node to an edge in the given direction — auto-creates both
    /// if missing; idempotent on re-add (set semantics per direction).
    /// INFALLIBLE — XGI returns `None` in every branch (probed v0.10.2)
    /// and its only error path is the invalid-direction string, which the
    /// [`Direction`] enum makes compile-time-impossible (divergence D14).
    ///
    /// XGI parity: `DH.add_node_to_edge(edge, node, direction)` —
    /// `"in"` ([`Direction::In`]) puts the node in the TAIL, `"out"`
    /// ([`Direction::Out`]) in the HEAD. Adding a node that is already a
    /// member in the OTHER direction puts it in BOTH sets.
    ///
    /// XGI never touches its uid counter here either — like the
    /// undirected class, auto-creating a numeric edge id does not bump
    /// `_edge_uid` (probed: the next auto id is 0, and XGI's auto-id
    /// add_edge does not existence-check, so the sequence silently
    /// overwrites that edge's members in XGI). The Rust core bumps iff
    /// `edge_id.parse::<u64>()` succeeds — the D3/D11 rule extended to
    /// `DiHypergraph` — foreclosing the collision class.
    pub fn add_node_to_edge(&mut self, edge_id: &str, node_id: &str, direction: Direction)
    where
        N: Default,
        E: Default,
        M: Default + Clone,
    {
        self.assert_not_frozen();
        // Auto-create edge if missing
        if !self.hyperedge_ids.contains_key(edge_id) {
            let he_idx = self.inner.add_node(NodeKind::Hyperedge(E::default()));
            self.hyperedge_ids.insert(edge_id.to_string(), he_idx);
            // D11-extension: bump the uid counter if edge_id is numeric
            // (XGI does not — probed for DiHypergraph too).
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
        let agent_idx = self.agent_ids[node_id];
        let he_idx = self.hyperedge_ids[edge_id];
        // Insert the arc for the direction (set semantics: re-adding an
        // existing membership is a no-op). In = tail = agent -> edge;
        // Out = head = edge -> agent.
        let (from, to) = match direction {
            Direction::In => (agent_idx, he_idx),
            Direction::Out => (he_idx, agent_idx),
        };
        if self.inner.find_edge(from, to).is_none() {
            self.inner.add_edge(
                from,
                to,
                MembershipEdge {
                    member_data: M::default(),
                },
            );
        }
    }

    /// Remove a node from an edge IN THE GIVEN DIRECTION only; the node
    /// itself (and any membership in the other direction) survives.
    /// `remove_empty` drops the edge if it is left empty, where directed
    /// "empty" means BOTH tail AND head are empty (probed v0.10.2: an
    /// edge with one side still populated survives even with
    /// `remove_empty=True`).
    ///
    /// XGI parity: `DH.remove_node_from_edge(edge, node, direction,
    /// remove_empty=True)`. XGI raises XGIError for a missing edge, a
    /// missing node, or a node not a member IN THAT DIRECTION (probed:
    /// "in-edge e1 does not contain node 2" for a head-only member) —
    /// the Rust core returns the matching [`MembershipError`] variant and
    /// the PyO3 binding translates Err -> raise, reproducing XGI's exact
    /// per-direction messages (D2 error channel). XGI's fourth error,
    /// the invalid-direction string, is validated FIRST in XGI and is
    /// compile-time-impossible here (D14).
    pub fn remove_node_from_edge(
        &mut self,
        edge_id: &str,
        node_id: &str,
        direction: Direction,
        remove_empty: bool,
    ) -> Result<(), MembershipError> {
        self.assert_not_frozen();
        let he_idx = *self
            .hyperedge_ids
            .get(edge_id)
            .ok_or(MembershipError::EdgeNotFound {
                edge_id: edge_id.to_string(),
            })?;
        let agent_idx = *self
            .agent_ids
            .get(node_id)
            .ok_or(MembershipError::NodeNotFound {
                node_id: node_id.to_string(),
            })?;

        // Membership is PER-DIRECTION: the arc for `direction` must exist.
        let (from, to) = match direction {
            Direction::In => (agent_idx, he_idx),
            Direction::Out => (he_idx, agent_idx),
        };
        let arc = self
            .inner
            .find_edge(from, to)
            .ok_or(MembershipError::NotAMember {
                node_id: node_id.to_string(),
                edge_id: edge_id.to_string(),
            })?;
        self.inner.remove_edge(arc);

        // Directed "emptied" = BOTH tail AND head empty (probed).
        if remove_empty {
            let has_tail = self
                .agent_ids
                .values()
                .any(|a| self.inner.contains_edge(*a, he_idx));
            let has_head = self
                .agent_ids
                .values()
                .any(|a| self.inner.contains_edge(he_idx, *a));
            if !has_tail && !has_head {
                self.inner.remove_node(he_idx);
                self.hyperedge_ids.shift_remove(edge_id);
            }
        }
        Ok(())
    }

    /// Remove a hyperedge from the dihypergraph.
    /// XGI parity: `DH.remove_edge(e)`.
    pub fn remove_edge(&mut self, edge_id: &str) -> Result<(), EdgeError> {
        self.assert_not_frozen();
        let he_idx = *self.hyperedge_ids.get(edge_id).ok_or(EdgeError::NotFound {
            edge_id: edge_id.to_string(),
        })?;
        self.inner.remove_node(he_idx);
        self.hyperedge_ids.shift_remove(edge_id);
        Ok(())
    }

    /// Remove multiple edges, returning a result per ATTEMPTED edge.
    ///
    /// XGI parity: `DH.remove_edges_from(ebunch)` — XGI iterates in
    /// order and RAISES `IDNotFound` on the first missing id: ids BEFORE
    /// it are already removed (partial effects), ids AFTER it are never
    /// attempted (probed v0.10.2: `["e1", "ghost", "e3"]` removes e1 and
    /// leaves e2 AND e3 in place). The core records per-item results and
    /// STOPS after the first `Err` — the D2-class channel translation;
    /// the binding truncates at the first `Err` and raises, reproducing
    /// XGI exactly (the state already matches).
    pub fn remove_edges_from(
        &mut self,
        edges: impl IntoIterator<Item = String>,
    ) -> Vec<Result<(), EdgeError>> {
        self.assert_not_frozen();
        let mut results = Vec::new();
        for edge_id in edges {
            let result = self.remove_edge(&edge_id);
            let stop = result.is_err();
            results.push(result);
            if stop {
                break;
            }
        }
        results
    }

    /// Remove a node from the dihypergraph — three-mode (register D9).
    ///
    /// XGI parity: `DH.remove_node(n, strong=False, remove_empty=True)`.
    /// Weak mode drops the node from BOTH directions of every containing
    /// edge; an edge left empty — BOTH tail AND head empty, the probed
    /// directed definition — is removed iff `remove_empty`. Strong mode
    /// removes every incident edge (in either direction) ENTIRELY,
    /// regardless of `remove_empty` (probed: the flag is irrelevant in
    /// strong mode).
    pub fn remove_node(
        &mut self,
        node_id: &str,
        strong: bool,
        remove_empty: bool,
    ) -> Result<(), NodeError> {
        self.assert_not_frozen();
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
                // Remove the node's arcs in BOTH directions.
                if let Some(e) = self.inner.find_edge(agent_idx, he_idx) {
                    self.inner.remove_edge(e);
                }
                if let Some(e) = self.inner.find_edge(he_idx, agent_idx) {
                    self.inner.remove_edge(e);
                }
                if remove_empty {
                    // Directed "emptied" = BOTH tail AND head empty.
                    let has_tail = self
                        .agent_ids
                        .values()
                        .any(|a| self.inner.contains_edge(*a, he_idx));
                    let has_head = self
                        .agent_ids
                        .values()
                        .any(|a| self.inner.contains_edge(he_idx, *a));
                    if !has_tail && !has_head {
                        self.inner.remove_node(he_idx);
                        self.hyperedge_ids.shift_remove(eid);
                    }
                }
            }
        }

        self.inner.remove_node(agent_idx);
        self.agent_ids.shift_remove(node_id);
        Ok(())
    }

    /// Remove multiple nodes, returning a result per node.
    ///
    /// XGI parity: `DH.remove_nodes_from(nodes, strong, remove_empty)` —
    /// XGI WARNS on a missing id ("Node {n} not in dihypergraph" — note:
    /// "dihypergraph", unlike the undirected class's "hypergraph"
    /// message), SKIPS it, and CONTINUES with the rest (probed v0.10.2).
    /// The core records a per-item `Err(NodeError::NotFound)` and
    /// continues — the D2-class channel translation; the binding warns
    /// per `Err` item to reproduce XGI's behavior.
    pub fn remove_nodes_from(
        &mut self,
        nodes: impl IntoIterator<Item = String>,
        strong: bool,
        remove_empty: bool,
    ) -> Vec<Result<(), NodeError>> {
        self.assert_not_frozen();
        nodes
            .into_iter()
            .map(|n| self.remove_node(&n, strong, remove_empty))
            .collect()
    }

    /// Add multiple directed edges, returning a result per edge.
    ///
    /// XGI parity: `DH.add_edges_from(ebunch, **attr)` — XGI accepts
    /// members-only / (members, idx) / (members, attrdict) /
    /// (members, idx, attrdict) / dict bunches plus a `**attr`
    /// broadcast; the core takes uniform `(tail, head, idx, attrs)`
    /// quadruples, so format detection and broadcast merging are binding
    /// concerns (D7 class). A duplicate idx warns + skips + CONTINUES in
    /// XGI; the core records `Err(EdgeError::AlreadyExists)` per item and
    /// continues — the D2-class channel translation. An empty
    /// `(tail, head)` pair creates an empty edge (probed: XGI's Notes
    /// claim empty edges are skipped — the runtime creates them; the
    /// D1-class docstring lie).
    pub fn add_edges_from(
        &mut self,
        edges: impl IntoIterator<Item = (Vec<String>, Vec<String>, Option<String>, E)>,
    ) -> Vec<Result<String, EdgeError>>
    where
        N: Default,
        M: Default + Clone,
    {
        self.assert_not_frozen();
        edges
            .into_iter()
            .map(|(tail, head, idx, attrs)| self.add_edge((tail, head), idx, attrs))
            .collect()
    }

    /// Mutably access a node's attributes.
    ///
    /// XGI parity: `DH.nodes[node_id][key] = value` (in-place attr-dict
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
    /// XGI parity: `DH.edges[edge_id][key] = value` (in-place attr-dict
    /// mutation).
    pub fn edge_attrs_mut(&mut self, edge_id: &str) -> Option<&mut E> {
        let idx = *self.hyperedge_ids.get(edge_id)?;
        match self.inner.node_weight_mut(idx) {
            Some(NodeKind::Hyperedge(attrs)) => Some(attrs),
            _ => None,
        }
    }

    /// Remove all nodes, edges, and attributes — node attrs, edge attrs,
    /// and graph-level attrs.
    ///
    /// Resets the auto-id counter: a cleared dihypergraph behaves
    /// identically to a fresh one (`clear() ≡ new()`; III.7
    /// replay-from-empty determinism). XGI's DiHypergraph.clear()
    /// continues its counter (probed v0.10.2: the next auto id is 1) —
    /// divergence D10, extended to DiHypergraph.
    ///
    /// XGI parity: `DH.clear()`. Guarded by freeze; the `frozen = false`
    /// reset runs only when the guard passes, documenting that a cleared
    /// dihypergraph is unfrozen.
    pub fn clear(&mut self) {
        self.assert_not_frozen();
        self.inner = StableDiGraph::new();
        self.agent_ids.clear();
        self.hyperedge_ids.clear();
        self.edge_uid_counter = 0;
        self.graph_attrs.clear();
        self.frozen = false;
    }

    /// Remove all edges, keeping every node, all node attrs, and all
    /// graph-level attrs.
    ///
    /// Divergence D16: XGI's DiHypergraph HAS NO `clear_edges` (probed
    /// v0.10.2: `AttributeError` via XGI's `__getattr__` stat fallback).
    /// The core provides it for API uniformity with
    /// [`super::hypergraph::Hypergraph::clear_edges`], with the same
    /// semantics: nodes, node attrs, and net attrs survive, and the uid
    /// counter is NOT reset (no "cleared ≡ fresh" reading — the node
    /// state survives, so counter continuity matches state continuity).
    /// Guarded by freeze — the D12 uniform-guard rationale.
    pub fn clear_edges(&mut self) {
        self.assert_not_frozen();
        let he_indices: Vec<NodeIndex> = self.hyperedge_ids.values().copied().collect();
        for he_idx in he_indices {
            self.inner.remove_node(he_idx);
        }
        self.hyperedge_ids.clear();
    }

    /// Freeze the dihypergraph, preventing structural modification.
    /// Idempotent (re-freezing is a no-op). XGI parity: `DH.freeze()`.
    ///
    /// The guard covers ALL structural mutators uniformly — divergence
    /// D12, extended: XGI's DiHypergraph freeze list omits
    /// `add_node_to_edge` AND `remove_node_from_edge` (unlike the
    /// undirected class, which guards both — probed v0.10.2: both mutate
    /// a FROZEN DiHypergraph unimpeded); `clear_edges` does not exist in
    /// XGI at all (D16). A freeze that permits membership surgery or
    /// wholesale edge deletion is not a freeze. The attr-dict channel
    /// (set_*_attributes, attrs_mut) stays open — XGI parity.
    pub fn freeze(&mut self) {
        self.frozen = true;
    }

    /// Check if the dihypergraph is frozen. XGI parity: `DH.is_frozen`.
    pub fn is_frozen(&self) -> bool {
        self.frozen
    }

    /// Return an independent deep copy. XGI parity: `DH.copy()`.
    /// Divergence D13 (DiHypergraph parity): the `frozen` flag carries —
    /// XGI's freeze is per-instance method-swizzling, so `copy()` of a
    /// frozen XGI network is NOT frozen (probed); here `frozen` is data,
    /// and a deep clone of data carries it.
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
            frozen: self.frozen,
        }
    }
}

/// Bulk attribute setters, available when the node/edge attribute
/// channels are `serde_json::Value` (the default). Mirrors the
/// undirected core's bounded block: XGI's attr slots are always dicts; a
/// generic `N`/`E` cannot merge maps.
impl<M> DiHypergraph<serde_json::Value, serde_json::Value, M> {
    /// Set node attributes from (id, attr_map) pairs.
    ///
    /// XGI parity: `DH.set_node_attributes(values, name=None)` — XGI
    /// takes a dict-of-dicts (pairs raise XGIError at its Python
    /// boundary; the core takes pairs and the binding converts — D7
    /// class; the scalar / dict-of-scalars `name=` forms are binding
    /// sugar). Attrs are MERGED into each existing node's dict; a
    /// non-object attr slot is REPLACED by the incoming map. Missing
    /// node ids are silently skipped — XGI warns ("Node X does not
    /// exist!"); the warn channel is a binding concern (D2 class).
    pub fn set_node_attributes(
        &mut self,
        values: impl IntoIterator<Item = (String, serde_json::Map<String, serde_json::Value>)>,
    ) {
        for (node_id, attrs) in values {
            if let Some(node_attrs) = self.node_attrs_mut(&node_id) {
                match node_attrs.as_object_mut() {
                    Some(obj) => {
                        for (k, v) in attrs {
                            obj.insert(k, v);
                        }
                    }
                    None => *node_attrs = serde_json::Value::Object(attrs.into_iter().collect()),
                }
            }
        }
    }

    /// Set edge attributes from (id, attr_map) pairs.
    ///
    /// XGI parity: `DH.set_edge_attributes(values, name=None)`. Same
    /// semantics as [`Self::set_node_attributes`]: merge into object
    /// slots, replace non-object slots, silently skip missing edge ids
    /// (XGI warns — binding concern).
    pub fn set_edge_attributes(
        &mut self,
        values: impl IntoIterator<Item = (String, serde_json::Map<String, serde_json::Value>)>,
    ) {
        for (edge_id, attrs) in values {
            if let Some(edge_attrs) = self.edge_attrs_mut(&edge_id) {
                match edge_attrs.as_object_mut() {
                    Some(obj) => {
                        for (k, v) in attrs {
                            obj.insert(k, v);
                        }
                    }
                    None => *edge_attrs = serde_json::Value::Object(attrs.into_iter().collect()),
                }
            }
        }
    }
}
