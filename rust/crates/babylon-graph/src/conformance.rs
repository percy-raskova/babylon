//! The substrate conformance suite — every invariant [`GraphSubstrate`] and
//! [`CanonicalState`] rule, executed against ANY store.
//!
//! `MemoryGraph`'s own unit tests already held every one of these facts, but
//! held them only for `MemoryGraph`. The storage-swap plan promotes them: a
//! second implementation (`HypergraphStore`, Phase C) has to hold the same
//! invariants, and this module is what proves it rather than asserts it —
//! `run_substrate_conformance` is `pub` rather than `#[cfg(test)]` because
//! the second store lives in this crate too, and a third might not.
//!
//! **Open question 2 (`bsl-language.rst` D96 / ADR191 R2 — RESOLVED NO):**
//! this suite deliberately does NOT assert that shuffling a scenario's node
//! *declaration* order leaves the state hash unchanged. `NodeId` is a
//! monotonic mint counter, so a declaration-order shuffle changes WHICH
//! facts exist under WHICH ids, not merely their write order — a case this
//! suite cannot pass and must not attempt. What it does assert instead:
//! `state_hash` is invariant to *write order* over the SAME set of minted
//! ids (see `state_hash_is_stable_and_order_invariant_and_sensitive` below).

use crate::state_hash::CanonicalState;
use crate::substrate::{Direction, GraphSubstrate, HyperedgeId, NodeId};

/// Run every invariant in this module against a fresh store from `make`.
///
/// `make` is called many times — once per invariant block, each starting
/// from an empty store — rather than once for the whole suite, so a failure
/// in one block never contaminates another block's starting state.
pub fn run_substrate_conformance<G, F>(make: F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    removal_cascades_edges_memberships_and_attributes(&make);
    duplicate_add_and_absent_remove_are_loud_on_both_halves(&make);
    honest_null_attribute_read(&make);
    members_of_is_always_ascending_never_declared_order(&make);
    hyperedge_membership_validation_is_loud(&make);
    nodes_edges_neighbors_hold_contractual_order_and_dedup(&make);
    hyperedges_of_type_vs_node_asymmetry(&make);
    a_hyperedge_mints_no_dyadic_edges(&make);
    hyperedges_by_type_is_ascending_and_typed(&make);
    hyperedges_of_an_undeclared_type_is_empty_not_loud(&make);
    state_hash_is_stable_and_order_invariant_and_sensitive(&make);
    a_decade_boundary_orders_numerically_not_lexicographically(&make);
    declared_order_never_leaks_through_any_ranged_accessor(&make);
    node_type_of_reports_the_declared_type(&make);
    node_type_of_a_dangling_id_is_loud_not_untyped(&make);
    edge_attribute_reads_back_the_seeded_strength(&make);
    edge_attribute_on_a_missing_edge_is_loud_not_zero(&make);
    edge_attribute_of_an_unstored_qname_is_loud(&make);
    edge_attribute_does_not_check_the_owner_segment(&make);
    update_edge_writes_and_reads_back_a_declared_attribute(&make);
    update_edge_on_a_missing_edge_is_loud_and_stores_nothing(&make);
    update_edge_against_strength_writes_the_existing_slot_never_a_fifth_section_row(&make);
    edge_removal_takes_the_edges_attributes_and_never_resurrects_them(&make);
}

/// ADR185 R2: removing a node takes its incident dyadic edges, its
/// attributes, and its hyperedge memberships with it — and a hyperedge
/// losing its last member is removed whole rather than left empty (an empty
/// hyperedge is unrepresentable; `add_hyperedge` rejects an empty list, so
/// leaving one behind would create by deletion a state that cannot be
/// created directly).
fn removal_cascades_edges_memberships_and_attributes<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let doomed = graph.add_node("social_class").unwrap();
    let survivor = graph.add_node("social_class").unwrap();
    let bystander = graph.add_node("social_class").unwrap();
    graph.update_node(doomed, "wealth", 42.0).unwrap();
    graph.update_node(survivor, "wealth", 7.0).unwrap();
    graph.add_edge("solidarity", doomed, survivor, 1.0).unwrap();
    graph
        .add_edge("solidarity", bystander, doomed, 1.0)
        .unwrap();
    graph
        .add_edge("solidarity", survivor, bystander, 1.0)
        .unwrap();
    let sector = graph
        .add_hyperedge("economic_sector", &[doomed, survivor, bystander])
        .unwrap();
    let solo = graph.add_node("social_class").unwrap();
    let lone_sector = graph.add_hyperedge("economic_sector", &[solo]).unwrap();

    graph.remove_node(doomed).unwrap();

    assert_eq!(
        graph.edges("solidarity"),
        vec![(survivor, bystander)],
        "both edges touching the removed node are gone; the third stands"
    );
    for (from, to) in graph.edges("solidarity") {
        assert!(graph.node_exists(from) && graph.node_exists(to));
    }
    assert_eq!(
        graph.members_of(sector).unwrap(),
        vec![survivor, bystander],
        "a member list is a set of LIVE nodes"
    );
    assert!(graph
        .neighbors(doomed, "solidarity", Direction::Any)
        .is_err());
    assert!(
        !graph
            .all_attributes()
            .iter()
            .any(|(id, _, _)| *id == doomed),
        "the removed node's attribute rows are gone, not orphaned"
    );
    assert!(
        (graph.node_attribute(survivor, "wealth").unwrap() - 7.0).abs() < 1e-12,
        "the survivor's attributes are untouched"
    );

    graph.remove_node(solo).unwrap();
    let err = graph.members_of(lone_sector).unwrap_err();
    assert!(
        err.message.contains("no such hyperedge"),
        "a hyperedge losing its last member is removed, not emptied: {}",
        err.message
    );
}

/// §2.8: absence is never success. Adding what already exists and removing
/// what does not are both loud errors, on the dyadic half AND the hyperedge
/// half — never a silent no-op or overwrite.
fn duplicate_add_and_absent_remove_are_loud_on_both_halves<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();

    graph.add_edge("solidarity", a, b, 0.5).unwrap();
    assert!(
        graph.add_edge("solidarity", a, b, 0.9).is_err(),
        "duplicate edge add is a loud error, never an overwrite"
    );
    graph.remove_edge("solidarity", a, b).unwrap();
    assert!(
        graph.remove_edge("solidarity", a, b).is_err(),
        "absent edge remove is a loud error, never a no-op"
    );
    assert!(
        graph
            .add_edge("solidarity", a, NodeId(999_999), 1.0)
            .is_err(),
        "an edge to a nonexistent endpoint is a loud error"
    );

    let sector = graph.add_hyperedge("economic_sector", &[a, b]).unwrap();
    graph.remove_hyperedge(sector).unwrap();
    assert!(
        graph.remove_hyperedge(sector).is_err(),
        "absent hyperedge remove is a loud error, never a no-op"
    );
    assert!(
        graph.remove_node(NodeId(999_999)).is_err(),
        "absent node remove is a loud error"
    );
}

/// An unwritten attribute errors on read; it never defaults to `0.0`.
fn honest_null_attribute_read<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let node = graph.add_node("social_class").unwrap();
    assert!(
        graph.node_attribute(node, "wealth").is_err(),
        "an unwritten attribute must error, never read as 0.0"
    );
    graph.update_node(node, "wealth", 42.0).unwrap();
    assert_eq!(graph.node_attribute(node, "wealth"), Ok(42.0));
}

/// Amendment D / BSL D25: declared member order is never observable —
/// `members_of` always returns ascending [`NodeId`] order.
fn members_of_is_always_ascending_never_declared_order<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let first = graph.add_node("social_class").unwrap();
    let second = graph.add_node("social_class").unwrap();
    let third = graph.add_node("social_class").unwrap();
    let sector = graph
        .add_hyperedge("economic_sector", &[third, first, second])
        .unwrap();
    assert_eq!(
        graph.members_of(sector).unwrap(),
        vec![first, second, third],
        "members_of must sort, regardless of declared order"
    );
}

/// A hyperedge's member list is a SET: empty, duplicate, or unknown members
/// are loud errors, never deduplicated or ignored (§2.8, `E-EVAL-031`). A
/// one-member hyperedge is legal — the ruled floor is one, never two.
fn hyperedge_membership_validation_is_loud<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let member = graph.add_node("social_class").unwrap();

    assert!(
        graph.add_hyperedge("economic_sector", &[]).is_err(),
        "an empty member list is a loud error"
    );
    assert!(
        graph
            .add_hyperedge("economic_sector", &[member, member])
            .is_err(),
        "a duplicate member is a loud error"
    );
    assert!(
        graph
            .add_hyperedge("economic_sector", &[NodeId(999_999)])
            .is_err(),
        "an unknown member is a loud error"
    );
    assert!(
        graph.add_hyperedge("economic_sector", &[member]).is_ok(),
        "a ONE-member hyperedge is legal — the floor is one, not two"
    );
}

/// §2.6: `nodes`/`edges`/`neighbors` range in ascending id order, and
/// `neighbors(:any)` is a set — a node reachable both ways appears once.
fn nodes_edges_neighbors_hold_contractual_order_and_dedup<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let class_a = graph.add_node("social_class").unwrap();
    let territory = graph.add_node("territory").unwrap();
    let class_b = graph.add_node("social_class").unwrap();
    assert_eq!(graph.nodes("social_class"), vec![class_a, class_b]);
    assert_eq!(graph.nodes("territory"), vec![territory]);
    assert_eq!(graph.nodes("organization"), Vec::<NodeId>::new());

    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();
    let c = graph.add_node("social_class").unwrap();
    graph.add_edge("solidarity", b, a, 0.4).unwrap();
    graph.add_edge("solidarity", a, c, 0.6).unwrap();
    graph.add_edge("wages", c, a, 0.9).unwrap();
    assert_eq!(graph.edges("solidarity"), vec![(a, c), (b, a)]);
    assert_eq!(graph.edges("wages"), vec![(c, a)]);
    assert_eq!(graph.edges("tribute"), Vec::<(NodeId, NodeId)>::new());

    let mut graph = make();
    let org = graph.add_node("organization").unwrap();
    let class_a = graph.add_node("social_class").unwrap();
    let class_b = graph.add_node("social_class").unwrap();
    graph.add_edge("membership", org, class_a, 1.0).unwrap();
    graph.add_edge("membership", org, class_b, 1.0).unwrap();
    graph.add_edge("membership", class_b, org, 0.2).unwrap();
    assert_eq!(
        graph.neighbors(org, "membership", Direction::Out).unwrap(),
        vec![class_a, class_b]
    );
    assert_eq!(
        graph.neighbors(org, "membership", Direction::In).unwrap(),
        vec![class_b]
    );
    assert_eq!(
        graph.neighbors(org, "membership", Direction::Any).unwrap(),
        vec![class_a, class_b],
        ":any is a SET — a node reachable both ways appears once"
    );
    assert!(
        graph
            .neighbors(NodeId(999_999), "membership", Direction::Any)
            .is_err(),
        "a dangling NodeRef never reads as an empty neighborhood"
    );
}

/// `hyperedges_of`: an unknown TYPE is an empty range (type validity is
/// BSL's `E-TYPE-011`, not the substrate's); an unknown NODE is a loud error
/// — belonging to nothing and not existing are different facts.
fn hyperedges_of_type_vs_node_asymmetry<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let lone = graph.add_node("social_class").unwrap();

    assert_eq!(
        graph.hyperedges_of(lone, "community").unwrap(),
        vec![],
        "a real node in no community of that type is an empty range"
    );
    assert_eq!(
        graph.hyperedges_of(lone, "no_such_type").unwrap(),
        vec![],
        "an unknown TYPE is empty, not an error"
    );
    let err = graph
        .hyperedges_of(NodeId(999_999), "community")
        .unwrap_err();
    assert!(
        !err.message.is_empty(),
        "an absent NODE must be a loud error"
    );
}

/// VIII.9 by construction: n members cost one hyperedge object, never
/// `C(n,2)` pairwise dyadic edges.
fn a_hyperedge_mints_no_dyadic_edges<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let first = graph.add_node("social_class").unwrap();
    let second = graph.add_node("social_class").unwrap();
    let sector = graph
        .add_hyperedge("economic_sector", &[first, second])
        .unwrap();
    assert_eq!(
        graph.hyperedges_of(first, "economic_sector").unwrap(),
        vec![sector]
    );
    assert!(
        graph.all_edges().is_empty(),
        "minting a hyperedge must not create any dyadic edge"
    );
}

/// E1b (`GraphSubstrate::hyperedges`): the type-scoped hyperedge enumerator
/// the community pack's head six rules iterate. Mint two TYPES interleaved
/// so a naive unfiltered read would leak the wrong type into the result,
/// and confirm the same-type subset comes back in ascending [`HyperedgeId`]
/// order regardless of storage order — the same guarantee [`Self::nodes`]/
/// [`Self::edges`] hold for their own ranges (symmetric with `:204`/`:208`).
fn hyperedges_by_type_is_ascending_and_typed<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();
    let c = graph.add_node("social_class").unwrap();

    // Interleave two hyperedge TYPES so a naive unfiltered read would leak
    // the wrong type into the result.
    let sector_one = graph.add_hyperedge("economic_sector", &[a]).unwrap();
    let community_one = graph.add_hyperedge("community", &[b]).unwrap();
    let sector_two = graph.add_hyperedge("economic_sector", &[b, c]).unwrap();
    let community_two = graph.add_hyperedge("community", &[a, c]).unwrap();

    assert_eq!(
        graph.hyperedges("economic_sector"),
        vec![sector_one, sector_two],
        "hyperedges() must filter by type and order ascending HyperedgeId"
    );
    assert_eq!(
        graph.hyperedges("community"),
        vec![community_one, community_two],
        "the other type's hyperedges are excluded, in their own ascending order"
    );
}

/// `hyperedges` of an undeclared type is an empty `Vec`, never a panic — the
/// method is infallible by signature, matching [`Self::nodes`]'s own
/// discipline for an unpopulated type (§2.6): type validity is BSL's static
/// check (`E-TYPE-011`), and the loudness for an invalid type lives at the
/// BOUND checker (`MissingCeiling`), never here.
fn hyperedges_of_an_undeclared_type_is_empty_not_loud<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    graph.add_hyperedge("economic_sector", &[a]).unwrap();

    assert_eq!(
        graph.hyperedges("no_such_type"),
        Vec::<HyperedgeId>::new(),
        "an unknown type is an empty range, not an error — the same \
         discipline nodes() holds for an unpopulated type"
    );
}

/// Build the same world twice, in opposite WRITE order (both instances mint
/// the same ids in the same order — only the order of subsequent
/// updates/edges/hyperedges differs). Constitution III.7: the state hash
/// must not depend on write order. The two `update_edge` writes (T3, ADR198
/// R1) put TWO fifth-section rows into the fixture, in opposite listing
/// order between the twins — so the order-invariance assertion below proves
/// the fifth section's sort, not just the first four's.
fn same_world_two_write_orders<G, F>(make: &F) -> (G, G)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut forward = make();
    let a = forward.add_node("social_class").unwrap();
    let b = forward.add_node("social_class").unwrap();
    forward.update_node(a, "wages", 120.0).unwrap();
    forward.update_node(a, "value_produced", 80.0).unwrap();
    forward.update_node(b, "wages", 40.0).unwrap();
    forward.add_edge("solidarity", a, b, 0.5).unwrap();
    forward
        .update_edge("solidarity", a, b, "solidarity/tension", 0.7)
        .unwrap();
    forward
        .update_edge("solidarity", a, b, "solidarity/trust", 0.2)
        .unwrap();
    forward.add_hyperedge("economic_sector", &[a, b]).unwrap();

    let mut reverse = make();
    let a2 = reverse.add_node("social_class").unwrap();
    let b2 = reverse.add_node("social_class").unwrap();
    reverse.add_hyperedge("economic_sector", &[b2, a2]).unwrap();
    reverse.add_edge("solidarity", a2, b2, 0.5).unwrap();
    // Same two edge attributes, opposite write order.
    reverse
        .update_edge("solidarity", a2, b2, "solidarity/trust", 0.2)
        .unwrap();
    reverse
        .update_edge("solidarity", a2, b2, "solidarity/tension", 0.7)
        .unwrap();
    reverse.update_node(b2, "wages", 40.0).unwrap();
    reverse.update_node(a2, "value_produced", 80.0).unwrap();
    reverse.update_node(a2, "wages", 120.0).unwrap();

    (forward, reverse)
}

/// The state hash: stable across repeated encodings within one process,
/// invariant to write order over the same minted ids, and moved by any real
/// change.
fn state_hash_is_stable_and_order_invariant_and_sensitive<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let (forward, reverse) = same_world_two_write_orders(make);
    assert_eq!(
        forward.state_hash().unwrap(),
        reverse.state_hash().unwrap(),
        "the same world must hash identically however it was WRITTEN"
    );

    let first = forward.state_hash().unwrap();
    for _ in 0..8 {
        assert_eq!(
            forward.state_hash().unwrap(),
            first,
            "the hash must be stable across repeated encodings"
        );
    }

    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();
    graph.update_node(a, "wages", 120.0).unwrap();
    graph.add_edge("solidarity", a, b, 0.5).unwrap();
    let before = graph.state_hash().unwrap();

    graph.update_node(a, "wages", 121.0).unwrap();
    let after_attribute = graph.state_hash().unwrap();
    assert_ne!(before, after_attribute, "an attribute write moves the hash");

    // T3 (ADR198 R1/R2): one edge-attribute write moves the hash — the
    // fifth section's existence is observable, never a silent store.
    graph
        .update_edge("solidarity", a, b, "solidarity/tension", 0.7)
        .unwrap();
    let after_edge_attribute = graph.state_hash().unwrap();
    assert_ne!(
        after_attribute, after_edge_attribute,
        "an edge-attribute write moves the hash"
    );

    graph.remove_edge("solidarity", a, b).unwrap();
    let after_edge = graph.state_hash().unwrap();
    assert_ne!(
        after_edge_attribute, after_edge,
        "an edge removal (taking its attribute rows with it) moves the hash"
    );

    graph.add_node("organization").unwrap();
    assert_ne!(
        after_edge,
        graph.state_hash().unwrap(),
        "a new node moves the hash"
    );
}

/// Delta document §4, CD5: build past a decade boundary — at least 12 nodes,
/// so `NodeId(10)` exists — and assert `nodes()` orders numerically. A store
/// keying nodes by a decimal STRING (`"10" < "2"` lexicographically) would
/// fail here; a store keying by zero-padded hex, or comparing the numeric id
/// directly, passes.
fn a_decade_boundary_orders_numerically_not_lexicographically<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let mut expected = Vec::with_capacity(12);
    for _ in 0..12 {
        expected.push(graph.add_node("social_class").unwrap());
    }
    expected.sort_unstable();
    assert_eq!(
        graph.nodes("social_class"),
        expected,
        "nodes() must order NUMERICALLY across a decade boundary"
    );
    assert!(
        graph.node_exists(NodeId(10)),
        "the fixture must actually cross id 10 for this test to mean anything"
    );
}

/// Delta document §4, CD5 (b): declare edges and hyperedges in an order that
/// FIGHTS id order, at every ranged accessor — `edges`, `hyperedges_of`,
/// `members_of`, and the type-scoped `hyperedges` (Task 2/E1b) all sort on
/// the ruled key regardless of the order members or edges were declared in.
fn declared_order_never_leaks_through_any_ranged_accessor<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();
    let c = graph.add_node("social_class").unwrap();

    // Edges declared with the highest source id first — the opposite of
    // ascending (source, target) order.
    graph.add_edge("wages", c, a, 1.0).unwrap();
    graph.add_edge("wages", b, a, 1.0).unwrap();
    graph.add_edge("wages", a, c, 1.0).unwrap();
    assert_eq!(
        graph.edges("wages"),
        vec![(a, c), (b, a), (c, a)],
        "edges() must sort ascending (source, target) regardless of add order"
    );

    // Both hyperedges declared with their members in DESCENDING order —
    // member declaration order and member id order disagree on purpose.
    let first_minted = graph.add_hyperedge("economic_sector", &[c, b, a]).unwrap();
    let second_minted = graph.add_hyperedge("economic_sector", &[a]).unwrap();
    assert_eq!(
        graph.members_of(first_minted).unwrap(),
        vec![a, b, c],
        "members_of sorts regardless of declared member order"
    );
    assert_eq!(
        graph.hyperedges_of(a, "economic_sector").unwrap(),
        vec![first_minted, second_minted],
        "hyperedges_of orders ascending HyperedgeId — mint order here, \
         since ids are assigned monotonically and cannot themselves be \
         declared out of order"
    );

    // E1b: hyperedges() gets the same fight. Mint a THIRD type's
    // hyperedges interleaved with the two above, and confirm the
    // type-filtered read comes back ascending — both for the newly
    // interleaved type and for the earlier one, unaffected by the
    // interleaving.
    let third_type_first = graph.add_hyperedge("community", &[c]).unwrap();
    let third_type_second = graph.add_hyperedge("community", &[a, b]).unwrap();
    assert_eq!(
        graph.hyperedges("community"),
        vec![third_type_first, third_type_second],
        "hyperedges() orders ascending HyperedgeId regardless of storage \
         order — mint order here, since ids are assigned monotonically and \
         cannot themselves be declared out of order"
    );
    assert_eq!(
        graph.hyperedges("economic_sector"),
        vec![first_minted, second_minted],
        "hyperedges() still returns the earlier type's own hyperedges in \
         ascending order, unaffected by the interleaved mints of a \
         different type"
    );
}

/// Task 3 (P27 Phase 2 Slice 1, `bsl-language.rst` §2.6 D24 / §2.10
/// discipline 1): `node_type_of` reports the declared type a live node was
/// minted under — the same fact `all_nodes`/`nodes(node_type)` already
/// report, read through a keyed lookup instead of a ranged listing.
fn node_type_of_reports_the_declared_type<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let class = graph.add_node("SOCIAL_CLASS").unwrap();
    let territory = graph.add_node("TERRITORY").unwrap();
    assert_eq!(graph.node_type_of(class).unwrap(), "SOCIAL_CLASS");
    assert_eq!(graph.node_type_of(territory).unwrap(), "TERRITORY");
}

/// A dangling [`NodeId`] must never read as an untyped node — the same
/// honest-null discipline `node_attribute`/`neighbors` already hold
/// (III.11): absence is a loud [`crate::substrate::GraphError`], never an
/// empty string or a default.
fn node_type_of_a_dangling_id_is_loud_not_untyped<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let graph = make();
    assert!(
        graph.node_type_of(NodeId(999_999)).is_err(),
        "a dangling NodeId must be a loud error, never an untyped read"
    );
}

/// T2 (issue #559, `bsl-language.rst` §2.10): `edge_attribute` reads back the strength seeded at
/// `add_edge` — the same fact `CanonicalState` section `0x03` already hashes, read through a keyed
/// lookup instead of `edges`' ranged listing.
fn edge_attribute_reads_back_the_seeded_strength<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();
    graph.add_edge("solidarity", a, b, 0.5).unwrap();
    // Epsilon-diff, not assert_eq! (clippy::float_cmp, crate-wide #![warn(clippy::pedantic)] —
    // matches this file's own precedent, e.g. removal_cascades_edges_memberships_and_attributes'
    // wealth check above): the value is an exact HashMap round-trip with no arithmetic, so the
    // comparison is deterministic regardless of the epsilon's width.
    assert!(
        (graph
            .edge_attribute("solidarity", a, b, "solidarity/strength")
            .unwrap()
            - 0.5)
            .abs()
            < f64::EPSILON
    );
}

/// A dangling `(edge_type, from, to)` triple must never read as an untyped edge's strength — the
/// same honest-null discipline `node_attribute`/`node_type_of` already hold (III.11).
fn edge_attribute_on_a_missing_edge_is_loud_not_zero<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();
    assert!(
        graph
            .edge_attribute("solidarity", a, b, "solidarity/strength")
            .is_err(),
        "no edge was ever added — never a default 0.0"
    );
}

/// A never-written non-strength qname is loud, never silently resolved to the strength value or a
/// default 0.0. **Superseded in place by T3 (ADR198 R1, issue #560)** — this row's own T2 doc
/// named the supersession in advance ("T2 stores exactly one edge attribute per edge (D32); T3
/// (ADR198 R1) widens this"): a deffield-declared edge qname now HAS storage, so "unstored" no
/// longer means "not strength". What stays law: a qname NEVER WRITTEN on an existing edge is
/// loud — the honest-null discipline `node_attribute` already holds (III.11). What changed: the
/// error now comes from the fifth-section store's own miss, and a write flips the qname to
/// readable (the positive half lives in
/// `update_edge_writes_and_reads_back_a_declared_attribute`).
fn edge_attribute_of_an_unstored_qname_is_loud<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();
    graph.add_edge("solidarity", a, b, 0.5).unwrap();
    assert!(
        graph
            .edge_attribute("solidarity", a, b, "solidarity/tension")
            .is_err(),
        "never written is loud — not the strength value, not a default 0.0"
    );
}

/// **Deliberate: the OWNER segment is NOT checked here (adversarial review, Major 6 residue).**
/// `edge_attribute` performs no ownership validation of its own — exactly `node_attribute`'s own
/// division of labor with `check_node_referent_type` (evaluator-side, upstream of every call this
/// trait receives). A qname whose owner segment names a DIFFERENT `EdgeType` than `edge_type`
/// still SUCCEEDS, because only the ATTRIBUTE segment (`strength`) is checked. Pinned here so a
/// future reader does not "fix" the suffix check into an owner check by surprise.
fn edge_attribute_does_not_check_the_owner_segment<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();
    graph.add_edge("solidarity", a, b, 0.5).unwrap();
    // Epsilon-diff, not assert_eq! — same clippy::float_cmp reason as the sibling test above.
    assert!(
        (graph
            .edge_attribute("solidarity", a, b, "tenancy/strength")
            .unwrap()
            - 0.5)
            .abs()
            < f64::EPSILON,
        "the owner segment ('tenancy' vs the edge's real type 'solidarity') is not verified here \
         — deliberately, by design; ownership is the CALLER's obligation"
    );
}

/// T3 (ADR198 R1/R3, issue #560): `update_edge` writes a deffield-declared edge attribute —
/// full symmetric with `update_node` — and the write reads back through BOTH the keyed lookup
/// (`edge_attribute`) and the fifth-section listing (`all_edge_attributes`), exactly. A second
/// write to the same `(edge, qname)` REPLACES (set semantics — `HashMap::insert`, the same
/// contract `update_node` holds), it never accumulates a duplicate row.
fn update_edge_writes_and_reads_back_a_declared_attribute<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();
    graph.add_edge("solidarity", a, b, 0.5).unwrap();

    graph
        .update_edge("solidarity", a, b, "solidarity/tension", 0.7)
        .unwrap();
    // Epsilon-diff, not assert_eq! — same clippy::float_cmp reason as the sibling rows above:
    // an exact HashMap round-trip with no arithmetic, deterministic regardless of the width.
    assert!(
        (graph
            .edge_attribute("solidarity", a, b, "solidarity/tension")
            .unwrap()
            - 0.7)
            .abs()
            < f64::EPSILON,
        "the keyed lookup reads the written value back"
    );
    let listed = graph
        .all_edge_attributes()
        .into_iter()
        .find(|(ty, from, to, name, _)| {
            ty == "solidarity" && *from == a && *to == b && name == "solidarity/tension"
        })
        .map(|(_, _, _, _, value)| value);
    assert_eq!(
        listed,
        Some(0.7),
        "the fifth-section listing reports the same fact, exactly (Option<f64> comparison — \
         no clippy::float_cmp on the contained float)"
    );

    graph
        .update_edge("solidarity", a, b, "solidarity/tension", 0.9)
        .unwrap();
    assert!(
        (graph
            .edge_attribute("solidarity", a, b, "solidarity/tension")
            .unwrap()
            - 0.9)
            .abs()
            < f64::EPSILON,
        "a second write REPLACES — set semantics, never an accumulated second row"
    );
    assert_eq!(
        graph
            .all_edge_attributes()
            .iter()
            .filter(|(ty, from, to, name, _)| {
                ty == "solidarity" && *from == a && *to == b && name == "solidarity/tension"
            })
            .count(),
        1,
        "one (edge, qname) pair holds exactly one row"
    );
}

/// The honest-null mirror of `add_edge`'s existence discipline: a write against a dangling
/// `(edge_type, from, to)` triple is a loud error under BOTH forks (strength and deffield
/// attribute), and — the load-bearing half — it STORES NOTHING: no orphan attribute row may
/// exist for an edge that was never minted (ADR185 R2's "no internal map holds a key naming a
/// corpse", extended to the fifth section).
fn update_edge_on_a_missing_edge_is_loud_and_stores_nothing<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();
    assert!(
        graph
            .update_edge("solidarity", a, b, "solidarity/strength", 0.8)
            .is_err(),
        "a strength write against an absent edge is loud, never a mint"
    );
    assert!(
        graph
            .update_edge("solidarity", a, b, "solidarity/tension", 0.7)
            .is_err(),
        "an attribute write against an absent edge is loud, never a mint"
    );
    assert!(
        graph.all_edge_attributes().is_empty(),
        "the refused writes stored nothing — no orphan rows"
    );
}

/// **The double-storage ruling (ADR198 R1's consequence no ruling text named, D143):** an
/// `update_edge` against `<edge-type>/strength` writes the edge's EXISTING strength slot — the
/// datum section `0x03` already hashes — and NEVER mints a fifth-section row. One datum, one
/// hashed home. The hash half of the proof: a store whose strength was written via
/// `update_edge` must encode byte-identically to one whose strength was set at `add_edge` time
/// — any fifth-section shadow row would move the bytes.
fn update_edge_against_strength_writes_the_existing_slot_never_a_fifth_section_row<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();
    graph.add_edge("solidarity", a, b, 0.5).unwrap();
    graph
        .update_edge("solidarity", a, b, "solidarity/strength", 0.8)
        .unwrap();

    let listed_strength = graph
        .all_edges()
        .into_iter()
        .find(|(ty, from, to, _)| ty == "solidarity" && *from == a && *to == b)
        .map(|(_, _, _, strength)| strength);
    assert_eq!(
        listed_strength,
        Some(0.8),
        "the write landed in the edge's strength slot (the 0x03 datum)"
    );
    assert!(
        graph.all_edge_attributes().is_empty(),
        "and minted NO fifth-section row — strength is not an edge attribute"
    );

    let mut twin = make();
    let ta = twin.add_node("social_class").unwrap();
    let tb = twin.add_node("social_class").unwrap();
    twin.add_edge("solidarity", ta, tb, 0.8).unwrap();
    assert_eq!(
        graph.encode_state().unwrap().as_bytes(),
        twin.encode_state().unwrap().as_bytes(),
        "strength written via update_edge encodes byte-identically to strength set at add_edge \
         time — no fifth-section shadow row exists"
    );
}

/// ADR185 R2's invariant, extended to the fifth section (T3): an edge's attribute rows go with
/// the edge — on `remove_edge` AND on the `remove_node` cascade — so no internal map ever holds
/// a key naming a corpse, and a re-minted edge never resurrects its predecessor's attributes.
/// The hash half: after removal the store must encode byte-identically to one that never held
/// the edge at all (removal is complete, not merely invisible).
fn edge_removal_takes_the_edges_attributes_and_never_resurrects_them<G, F>(make: &F)
where
    G: GraphSubstrate + CanonicalState,
    F: Fn() -> G,
{
    // Direct removal.
    let mut graph = make();
    let a = graph.add_node("social_class").unwrap();
    let b = graph.add_node("social_class").unwrap();
    graph.add_edge("solidarity", a, b, 0.5).unwrap();
    graph
        .update_edge("solidarity", a, b, "solidarity/tension", 0.7)
        .unwrap();

    graph.remove_edge("solidarity", a, b).unwrap();
    assert!(
        graph.all_edge_attributes().is_empty(),
        "remove_edge takes the edge's attribute rows with it"
    );
    assert!(
        graph
            .edge_attribute("solidarity", a, b, "solidarity/tension")
            .is_err(),
        "the removed edge's attributes are unreadable — never orphaned state"
    );

    // Removal completeness, proven through the hash: what remains is exactly "two nodes".
    let mut bare = make();
    let ba = bare.add_node("social_class").unwrap();
    let bb = bare.add_node("social_class").unwrap();
    assert_eq!(
        ba, a,
        "fixture mint order must line up for the hash comparison"
    );
    assert_eq!(
        bb, b,
        "fixture mint order must line up for the hash comparison"
    );
    assert_eq!(
        graph.state_hash().unwrap(),
        bare.state_hash().unwrap(),
        "after removal the store hashes as if the edge (and its attributes) never existed"
    );

    // Re-minting the same triple does not resurrect the old attribute rows.
    graph.add_edge("solidarity", a, b, 0.5).unwrap();
    assert!(
        graph
            .edge_attribute("solidarity", a, b, "solidarity/tension")
            .is_err(),
        "a re-minted edge carries no memory of its predecessor's attributes"
    );

    // The remove_node cascade half.
    let mut graph = make();
    let doomed = graph.add_node("social_class").unwrap();
    let survivor = graph.add_node("social_class").unwrap();
    graph.add_edge("solidarity", doomed, survivor, 1.0).unwrap();
    graph
        .update_edge("solidarity", doomed, survivor, "solidarity/tension", 0.3)
        .unwrap();
    graph.remove_node(doomed).unwrap();
    assert!(
        graph.all_edge_attributes().is_empty(),
        "the remove_node cascade takes incident edges' attribute rows too"
    );
}

#[cfg(test)]
mod tests {
    use super::run_substrate_conformance;
    use crate::memory::MemoryGraph;

    #[test]
    fn memory_graph_passes_the_conformance_suite() {
        run_substrate_conformance(MemoryGraph::new);
    }
}
