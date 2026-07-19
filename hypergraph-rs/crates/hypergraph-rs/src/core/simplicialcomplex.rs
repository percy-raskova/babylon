//! The core `SimplicialComplex` data structure.
//!
//! A simplicial complex is a hypergraph closed under taking subfaces:
//! every non-empty subset of a simplex (of size >= 2) is itself an
//! edge. The complex WRAPS [`super::hypergraph::Hypergraph`] (spec
//! §3.4) — the closure is maintained by `add_simplex`, which adds the
//! top simplex plus every missing subface. Subfaces are computed
//! directly at add time; the OnceCell face-lattice cache is a deferred
//! optimization (YAGNI until profiling).
//!
//! XGI's "blocked" methods (`add_edge`, `add_edges_from`,
//! `add_weighted_edges_from`, `remove_edge(s)_from`,
//! `add_node_to_edge`) raise XGIError at runtime; here they are ABSENT
//! at the type level — divergence D15.

use super::error::EdgeError;
use super::hypergraph::Hypergraph;

/// A simplicial complex: a hypergraph closed under subfaces.
///
/// # Type Parameters
///
/// - `N` — node attribute type (defaults to `serde_json::Value`)
/// - `E` — simplex attribute type (defaults to `serde_json::Value`)
/// - `M` — per-membership attribute type (defaults to `serde_json::Value`)
pub struct SimplicialComplex<N = serde_json::Value, E = serde_json::Value, M = serde_json::Value> {
    /// The wrapped hypergraph. Simplices are its hyperedges; the
    /// subface closure is an invariant maintained by `add_simplex`.
    inner: Hypergraph<N, E, M>,
}

impl<N, E, M> Default for SimplicialComplex<N, E, M> {
    fn default() -> Self {
        Self::new()
    }
}

impl<N, E, M> SimplicialComplex<N, E, M> {
    /// Create an empty simplicial complex.
    pub fn new() -> Self {
        Self {
            inner: Hypergraph::new(),
        }
    }

    /// The number of nodes in the complex.
    pub fn num_nodes(&self) -> usize {
        self.inner.num_nodes()
    }

    /// The number of simplices (top-level and faces) in the complex.
    pub fn num_edges(&self) -> usize {
        self.inner.num_edges()
    }

    /// All node IDs in insertion order (III.7 determinism parity).
    /// XGI parity: `list(S.nodes)`.
    pub fn node_ids(&self) -> Vec<String> {
        self.inner.node_ids()
    }

    /// All simplex IDs in insertion order (III.7 determinism parity).
    /// XGI parity: `list(S.edges)`.
    pub fn edge_ids(&self) -> Vec<String> {
        self.inner.edge_ids()
    }

    /// The members of a simplex, in node-insertion order (D5: XGI
    /// returns an unordered frozenset — strictly more defined).
    ///
    /// XGI parity: `S.edges.members(e)`.
    pub fn members(&self, edge_id: &str) -> Option<Vec<String>> {
        self.inner.members(edge_id)
    }

    /// The simplices a node belongs to, in edge-insertion order (D5).
    ///
    /// XGI parity: `S.nodes.memberships(n)`.
    pub fn memberships(&self, node_id: &str) -> Option<Vec<String>> {
        self.inner.memberships(node_id)
    }

    /// Read a node's attributes.
    ///
    /// XGI parity: `S.nodes[node_id]`.
    pub fn node_attrs(&self, node_id: &str) -> Option<&N> {
        self.inner.node_attrs(node_id)
    }

    /// Read a simplex's attributes.
    ///
    /// XGI parity: `S.edges[edge_id]`.
    pub fn edge_attrs(&self, edge_id: &str) -> Option<&E> {
        self.inner.edge_attrs(edge_id)
    }

    /// Read a graph-level attribute.
    ///
    /// XGI parity: `S.graph[key]`.
    pub fn graph_attr(&self, key: &str) -> Option<&serde_json::Value> {
        self.inner.graph_attr(key)
    }

    /// Set a graph-level attribute.
    ///
    /// XGI parity: `S.graph[key] = value`.
    pub fn set_graph_attr(&mut self, key: &str, value: serde_json::Value) {
        self.inner.set_graph_attr(key, value);
    }

    /// Whether a simplex with EXACTLY this member set exists —
    /// member-SET comparison (order and duplicates in the query are
    /// insignificant).
    ///
    /// XGI parity: `S.has_simplex(simplex)` (`frozenset(simplex) in
    /// self._edge.values()`).
    pub fn has_simplex(&self, members: &[String]) -> bool {
        self.find_simplex(members).is_some()
    }

    /// The id of the simplex whose member set equals `members`
    /// (set comparison), if one exists. O(E) — fine at our scale.
    fn find_simplex(&self, members: &[String]) -> Option<String> {
        let mut target: Vec<&str> = members.iter().map(String::as_str).collect();
        target.sort_unstable();
        target.dedup();
        self.inner.edge_ids().into_iter().find(|eid| {
            let have = self.inner.members(eid).unwrap_or_default();
            // Members are set-unique by construction (add_edge dedups).
            let mut have: Vec<&str> = have.iter().map(String::as_str).collect();
            have.sort_unstable();
            have == target
        })
    }

    /// The proper non-empty subfaces of `members` of sizes 2..n-1 (NO
    /// singletons, NO empty set, NO the full set — probed v0.10.2:
    /// `_subfaces` iterates `combinations(simplex, n - 1)` for n from
    /// size down to 3). Enumerated in canonical order: sizes n-1 down
    /// to 2, lexicographic by member position within each size (XGI
    /// then shuffles via `set(faces)` — hash-ordered for str members;
    /// the D5-class "strictly more defined" ordering).
    fn subfaces(members: &[String]) -> Vec<Vec<String>> {
        let n = members.len();
        let mut out = Vec::new();
        for k in (2..n).rev() {
            out.extend(combinations(members, k));
        }
        out
    }

    /// Add a simplex and all its subfaces that do not exist yet.
    ///
    /// XGI parity: `S.add_simplex(members, idx=id, **attr)`. Members are
    /// deduped (XGI casts to a frozenset); the closure runs on the SET.
    /// The top simplex takes `idx` or the next auto id FIRST; subfaces
    /// then consume auto ids — subfaces are EXACTLY the proper
    /// non-empty subsets of sizes 2..n-1 (no singletons, probed). The
    /// uid-counter rule is the core's D3 rule (bump iff the id parses
    /// as u64 — probed parity: int idx 10 -> faces 11, 12, 13; str idx
    /// -> faces 0, 1, 2). Simplex attrs land ONLY on the top simplex;
    /// subfaces get `E::default()` (probed: XGI's {} — the core's Null
    /// placeholder, D7-class convention).
    ///
    /// The member-set check precedes the idx check (probed): re-adding
    /// an existing member SET is a silent no-op and returns the id of
    /// the EXISTING simplex — even a new explicit `idx` is discarded
    /// unconsumed. XGI returns `None` in every branch; the core returns
    /// `Ok(id)` for new AND already-present — the D8 return-channel
    /// class. A duplicate `idx` with a DIFFERENT member set is
    /// `Err(EdgeError::AlreadyExists)` (XGI warns + no-ops — the D2
    /// class; the binding translates).
    ///
    /// An empty `members` creates an empty simplex (probed: XGI's
    /// Notes claim empty simplices cannot be added; the runtime creates
    /// one — the D1-class docstring lie). Divergence D17: XGI treats a
    /// FALSY idx (`0`, `""`) as auto (`next(_edge_uid) if not idx else
    /// idx` — unique to SimplicialComplex); the core's `Option<String>`
    /// is exact — `Some("0")` is an explicit id.
    pub fn add_simplex(
        &mut self,
        members: Vec<String>,
        idx: Option<String>,
        attrs: E,
    ) -> Result<String, EdgeError>
    where
        N: Default,
        E: Default,
        M: Default + Clone,
    {
        // Set semantics: dedup, first-encounter order (XGI frozensets).
        let mut seen = std::collections::HashSet::new();
        let unique: Vec<String> = members
            .into_iter()
            .filter(|m| seen.insert(m.clone()))
            .collect();

        // Member-set dedup precedes the idx check (probed): a re-added
        // member set is a silent no-op returning the existing id.
        if let Some(existing) = self.find_simplex(&unique) {
            return Ok(existing);
        }

        let top_id = self.inner.add_edge(unique.clone(), idx, attrs)?;

        // Subface closure: add only faces whose member set is not
        // already present; each takes the next auto id (D3-bumped by
        // the top add). Auto ids never collide with explicit ids (the
        // D3/D11 foreclosure), so these adds cannot fail.
        for face in Self::subfaces(&unique) {
            if self.find_simplex(&face).is_none() {
                self.inner.add_edge(face, None, E::default())?;
            }
        }
        Ok(top_id)
    }
}

/// All `k`-subsets of `items`, in lexicographic index order (hand-rolled
/// — no new dependencies; the plan's Task 6 note). `items` is the
/// deduped member list in first-encounter order, so the enumeration is
/// fully deterministic (III.7).
fn combinations(items: &[String], k: usize) -> Vec<Vec<String>> {
    let n = items.len();
    let mut out = Vec::new();
    if k == 0 || k > n {
        return out;
    }
    let mut idx: Vec<usize> = (0..k).collect();
    loop {
        out.push(idx.iter().map(|&i| items[i].clone()).collect());
        // Advance the index vector to the next combination, or finish.
        let mut i = k;
        loop {
            if i == 0 {
                return out;
            }
            i -= 1;
            if idx[i] != i + n - k {
                idx[i] += 1;
                for j in (i + 1)..k {
                    idx[j] = idx[j - 1] + 1;
                }
                break;
            }
        }
    }
}
