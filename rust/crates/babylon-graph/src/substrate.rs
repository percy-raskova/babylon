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
//!
//! **Task 16 revisions (recorded, not silent):** type/attribute names are
//! `&str` (the drafted `&'static str` forced every runtime-string caller
//! through `Box::leak` — the exact smell the Phase-1 plan's own TODO said
//! not to ship); `add_edge` carries the `:strength` operand §2.8's grammar
//! makes mandatory; and `node_attribute` exists because §2.8's four
//! update-ops (`add`/`sub`/`scale` read-modify-write) are unimplementable
//! without a read point. Attribute values are `f64` — the binary64 lane
//! only; typed attribute storage (Currency's i128 exactness) is a declared
//! Phase-2 gap, not a silent coercion (`babylon-bsl`'s executor rejects
//! Currency-typed writes loudly).

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

/// §2.6 `<direction>` for the `neighbors` query: `:out` follows
/// source→target, `:in` the reverse, `:any` their union.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Direction {
    /// `:out` — nodes this node points at across the edge type.
    Out,
    /// `:in` — nodes pointing at this node across the edge type.
    In,
    /// `:any` — the set union of both directions.
    Any,
}

/// The typed structural-verb surface a `GraphSubstrate` implementation
/// provides. `node_type`/`edge_type`/`hyperedge_type` are plain `&str` (the
/// closed `NodeType`/`EdgeType`/`HyperedgeType` enums are a `babylon-domain`
/// concern, Phase 2/3; this trait is domain-agnostic on purpose so it
/// compiles before those enums port).
///
/// **Absence is never success** (§2.8): removing what does not exist and
/// adding what already exists are errors on every method below — a
/// substrate that silently no-ops either is non-conforming.
pub trait GraphSubstrate {
    // ---- dyadic half (II.9 morphism layer) ----

    /// Mint one typed node.
    ///
    /// # Errors
    /// Returns [`GraphError`] if the implementation cannot allocate the node
    /// (for example, an exhausted identity space).
    fn add_node(&mut self, node_type: &str) -> Result<NodeId, GraphError>;

    /// Remove a node, **cascading** to its incident structure (ADR185 R2).
    ///
    /// Removal is whole: every incident dyadic edge goes, and the node is
    /// dropped from every hyperedge's member list. A member list is therefore
    /// always a set of LIVE nodes — that is what makes [`Self::members_of`]
    /// mean the same thing to every reader.
    ///
    /// A hyperedge whose last member is removed is itself removed: an empty
    /// hyperedge is unrepresentable here ([`Self::add_hyperedge`] rejects an
    /// empty member list), so leaving one behind would create by deletion a
    /// state that cannot be created directly.
    ///
    /// **The cascade must be OBSERVABLE.** The substrate performs it; the
    /// caller is responsible for recording it. `remove-node` is a BSL
    /// structural verb, so the effect executor emits one write-log record per
    /// cascaded edge and membership — otherwise a class dissolving would
    /// quietly shrink its industry's membership with no event anybody wrote.
    /// Cascade is the semantics; silence is not (ADR185 R2, ADR182 R1).
    ///
    /// # Errors
    /// Returns [`GraphError`] if `id` names no node in this substrate.
    fn remove_node(&mut self, id: NodeId) -> Result<(), GraphError>;

    /// Mint one typed dyadic edge with its mandatory `:strength` (§2.8).
    ///
    /// # Errors
    /// Returns [`GraphError`] if either endpoint does not exist, or if the
    /// `(edge_type, from, to)` edge already exists (`E-EVAL-031` — never a
    /// silent overwrite).
    fn add_edge(
        &mut self,
        edge_type: &str,
        from: NodeId,
        to: NodeId,
        strength: f64,
    ) -> Result<(), GraphError>;

    /// Remove one typed dyadic edge.
    ///
    /// # Errors
    /// Returns [`GraphError`] if the edge does not exist — absence is never
    /// treated as success (`E-EVAL-031`).
    fn remove_edge(&mut self, edge_type: &str, from: NodeId, to: NodeId) -> Result<(), GraphError>;

    /// Update a single attribute on a node under the I.15 edge-mode state
    /// machine's constraints — this trait method does NOT itself enforce
    /// I.15 (that is a `babylon-domain` law over the concrete shape); it is
    /// the mechanical write point I.15's checker wraps.
    ///
    /// # Errors
    /// Returns [`GraphError`] if `id` names no node in this substrate.
    fn update_node(&mut self, id: NodeId, attribute: &str, value: f64) -> Result<(), GraphError>;

    /// Read a single attribute — the read half §2.8's `add`/`sub`/`scale`
    /// update-ops need for their read-modify-write.
    ///
    /// # Errors
    /// Returns [`GraphError`] if `id` names no node, or the attribute has
    /// never been written — never a default `0.0` (the honest-null
    /// discipline, §3.5).
    fn node_attribute(&self, id: NodeId, attribute: &str) -> Result<f64, GraphError>;

    /// Whether `id` names a live node.
    fn node_exists(&self, id: NodeId) -> bool;

    // Removal semantics are RULED (ADR185 R2), not left to the implementor:
    // see [`Self::remove_node`]. A second implementor that orphans, or that
    // rejects instead of cascading, is wrong — not merely different.

    // ---- §2.6 query surface (dyadic half) ----
    //
    // Iteration order is part of the CONTRACT (§2.6 iteration-order ruling):
    // ascending id order / ascending (source-id, target-id) order — never
    // graph-internal storage order. Predicates (`<node-pred>` etc.) are the
    // evaluator's concern; the substrate provides the unfiltered range.

    /// `(nodes <enum-ref>)` — every node of the given type, ascending
    /// [`NodeId`] order. An unknown type is an empty range, not an error:
    /// type validity is BSL's static check (`E-TYPE-011`), not the
    /// substrate's.
    fn nodes(&self, node_type: &str) -> Vec<NodeId>;

    /// `(edges <enum-ref>)` — every dyadic edge of the given type as
    /// `(source, target)`, ascending `(source-id, target-id)` order.
    fn edges(&self, edge_type: &str) -> Vec<(NodeId, NodeId)>;

    /// `(neighbors <expr> <enum-ref> <direction>)` — the `NodeSet` reachable
    /// from `node` across `edge_type` in `direction`, ascending [`NodeId`]
    /// order, deduplicated (a set, so `:any` never yields a node twice).
    ///
    /// # Errors
    /// Returns [`GraphError`] if `node` does not exist — a dangling
    /// `NodeRef` must never read as an empty neighborhood (the honest-null
    /// discipline).
    fn neighbors(
        &self,
        node: NodeId,
        edge_type: &str,
        direction: Direction,
    ) -> Result<Vec<NodeId>, GraphError>;

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
        hyperedge_type: &str,
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
    ///
    /// An unknown *type* is an empty range, matching [`Self::nodes`]: type
    /// validity is BSL's static check (`E-TYPE-011`), not the substrate's.
    /// An unknown *node* is an error, matching [`Self::neighbors`].
    ///
    /// The two halves are not symmetric on purpose. "This node belongs to no
    /// community" and "there is no such node" are different facts, and the
    /// first is load-bearing here: a county with no census rows must not
    /// read as a node that belongs to nothing, because a target belonging to
    /// no protective structure is the CHEAPEST one an adversary can reach
    /// ([`crate::backfire`]). Pine Ridge (FIPS 46102) is empty at every
    /// census vintage, so this is a live data shape, not a hypothetical.
    ///
    /// # Errors
    /// Returns [`GraphError`] if `node` does not exist.
    fn hyperedges_of(
        &self,
        node: NodeId,
        hyperedge_type: &str,
    ) -> Result<Vec<HyperedgeId>, GraphError>;

    /// The declared type of a live node — `(neighbors … <NodeType>)`'s
    /// filter (§2.6, D24: this operand FILTERS) and §2.10 discipline 1's
    /// `E-EVAL-033` referent check both need it, and neither is expressible
    /// without it.
    ///
    /// READ-ONLY: it reports a fact the substrate already stores to satisfy
    /// [`Self::nodes`]. It adds no state, and `CanonicalState`'s four
    /// sections are untouched.
    ///
    /// # Errors
    /// Returns [`GraphError`] if `id` names no live node — a dangling
    /// `NodeRef` never reads as an untyped node (III.11).
    fn node_type_of(&self, id: NodeId) -> Result<&str, GraphError>;

    /// Read one dyadic edge's attribute (§2.10's `edge-between`/`field-of` share this) — the read
    /// half `edge-between`'s existence check and `field-of` over an `EdgeRef` both derive from.
    /// `attribute` is the FULL QNAME (e.g. `"solidarity/strength"`), mirroring
    /// [`Self::node_attribute`]'s own convention exactly — never a bare segment.
    ///
    /// **T2 scope (issue #559): the only PATTERN resolvable against real storage today is a qname
    /// ENDING IN `/strength`** — every `EdgeType` carries one implicit, always-written `Coefficient`
    /// field (D32, `bsl-language.rst` §2.9), and `add_edge`'s mandatory `:strength` operand is the
    /// only thing this trait's edge storage holds. **This method does NOT verify that `attribute`'s
    /// OWNER segment names `edge_type`** — exactly as [`Self::node_attribute`] performs no
    /// ownership check of its own, that half of §2.10 discipline 1 is the CALLER's obligation
    /// (`field_of_edge`'s `check_edge_referent_type`, upstream of every call this trait receives).
    /// A qname whose ATTRIBUTE segment is anything but `strength` is legal grammar (a `deffield`
    /// may own off an `EdgeType`, dossier-confirmed) but has no storage behind it until T3
    /// (ADR198 R1) — it reads exactly like a never-written node field: `GraphError`, never a
    /// default `0.0`. **READ-ONLY**: reports a fact `CanonicalState` section `0x03` already hashes
    /// (III.7, the `node_type_of` precedent — `ai/decisions/ADR197_bsl_query_evaluation_slice1_handoff.yaml`).
    ///
    /// # Errors
    /// Returns [`GraphError`] if no `(edge_type, from, to)` edge exists, or if `attribute` does not
    /// END IN `/strength` — absence is never a default `0.0`.
    fn edge_attribute(
        &self,
        edge_type: &str,
        from: NodeId,
        to: NodeId,
        attribute: &str,
    ) -> Result<f64, GraphError>;
}
