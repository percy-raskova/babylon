//! The `GraphSubstrate` trait: the typed-verb surface BSL's structural
//! effects compile against (`docs/reference/bsl-language.rst` §2.6 queries,
//! §2.8 verbs), independent of the underlying storage.
//!
//! **Two typed halves, one substrate (Amendment D, sub-ruling D-2).** The
//! dyadic half (`add_edge`/`remove_edge`) is II.9's strictly dyadic morphism
//! layer. The hyperedge half (`add_hyperedge`/`remove_hyperedge`/
//! `members_of`/`hyperedges_of`) is Amendment D's first-class membership
//! layer. A dyadic caller cannot be handed a hyperedge and vice versa —
//! II.7's "MUST remain separate" is enforced by the type system rather than
//! by two libraries.
//!
//! **Silent on representation, loud on shape.** No adjacency iteration order
//! and no storage type is exposed; a Levi/incidence bipartite store is
//! permitted and unobservable. What IS exposed, because the ruling fixes it:
//! a hyperedge has an identity and a member list, and there is no method
//! anywhere that expands a member list into pairwise edges (VIII.9).

/// Opaque node identity — a newtype so no caller depends on it being an
/// integer index vs. a UUID vs. anything else the concrete shape picks.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct NodeId(pub u64);

/// Opaque hyperedge identity. **Distinct from [`NodeId`] on purpose**: a
/// hyperedge is a first-class object, not a node with a member set stashed in
/// its attributes (the shape D-4 explicitly declines to ratify for
/// `ECONOMIC_SECTOR`). Two id types is what makes the dyadic/hyperedge
/// separation type-level rather than conventional.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct HyperedgeId(pub u64);

/// A structural-verb failure. Loud by construction (III.11): every fallible
/// method on [`GraphSubstrate`] returns one rather than silently coercing.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GraphError {
    /// Human-readable cause, suitable for surfacing to a BSL diagnostic.
    pub message: String,
}

/// The typed structural-verb surface a `GraphSubstrate` implementation
/// provides. `node_type`/`edge_type`/`hyperedge_type` are `&'static str` here
/// (the closed `NodeType`/`EdgeType`/`HyperedgeType` enums are a
/// `babylon-domain` concern, Phase 2/3; this trait is domain-agnostic on
/// purpose so it compiles before those enums port).
pub trait GraphSubstrate {
    // ---- dyadic half (II.9 morphism layer) ----

    /// Mint one typed node.
    ///
    /// # Errors
    /// Returns [`GraphError`] if the implementation cannot allocate the node
    /// (for example, an exhausted identity space).
    fn add_node(&mut self, node_type: &'static str) -> Result<NodeId, GraphError>;

    /// Remove a node.
    ///
    /// # Errors
    /// Returns [`GraphError`] if `id` names no node in this substrate.
    fn remove_node(&mut self, id: NodeId) -> Result<(), GraphError>;

    /// Mint one typed dyadic edge.
    ///
    /// # Errors
    /// Returns [`GraphError`] if either endpoint does not exist.
    fn add_edge(
        &mut self,
        edge_type: &'static str,
        from: NodeId,
        to: NodeId,
    ) -> Result<(), GraphError>;

    /// Remove one typed dyadic edge.
    ///
    /// # Errors
    /// Returns [`GraphError`] if the implementation cannot service the
    /// removal (for example, an unknown endpoint under a stricter store).
    fn remove_edge(
        &mut self,
        edge_type: &'static str,
        from: NodeId,
        to: NodeId,
    ) -> Result<(), GraphError>;

    /// Update a single attribute on a node under the I.15 edge-mode state
    /// machine's constraints — this trait method does NOT itself enforce
    /// I.15 (that is a `babylon-domain` law over the concrete shape); it is
    /// the mechanical write point I.15's checker wraps.
    ///
    /// # Errors
    /// Returns [`GraphError`] if `id` names no node in this substrate.
    fn update_node(
        &mut self,
        id: NodeId,
        attribute: &'static str,
        value: f64,
    ) -> Result<(), GraphError>;

    /// Whether `id` names a live node.
    fn node_exists(&self, id: NodeId) -> bool;

    // ---- hyperedge half (Amendment D: first-class membership) ----

    /// Mint one typed hyperedge over `members`. The member list is a SET:
    /// a repeated [`NodeId`], an unknown [`NodeId`], or an empty list is a
    /// loud error (BSL `E-EVAL-031`), never deduplicated or ignored. Cost is
    /// `members.len()` incidences — never `C(n,2)` edges.
    ///
    /// # Errors
    /// Returns [`GraphError`] if `members` is empty, contains a duplicate, or
    /// names a node that does not exist.
    fn add_hyperedge(
        &mut self,
        hyperedge_type: &'static str,
        members: &[NodeId],
    ) -> Result<HyperedgeId, GraphError>;

    /// Remove one hyperedge whole. There is deliberately no `remove_member`:
    /// membership change is whole-hyperedge replacement (BSL invariant S-10).
    ///
    /// # Errors
    /// Returns [`GraphError`] if `id` names no hyperedge in this substrate.
    fn remove_hyperedge(&mut self, id: HyperedgeId) -> Result<(), GraphError>;

    /// Members of one hyperedge, in **ascending [`NodeId`] order** — declared
    /// member order is never observable (BSL §2.6 draft ruling D25).
    ///
    /// # Errors
    /// Returns [`GraphError`] if `id` names no hyperedge in this substrate.
    fn members_of(&self, id: HyperedgeId) -> Result<Vec<NodeId>, GraphError>;

    /// The hyperedges of the given type a node belongs to, in ascending
    /// [`HyperedgeId`] order.
    fn hyperedges_of(&self, node: NodeId, hyperedge_type: &'static str) -> Vec<HyperedgeId>;

    /// Whether `id` names a live hyperedge.
    fn hyperedge_exists(&self, id: HyperedgeId) -> bool;
}
