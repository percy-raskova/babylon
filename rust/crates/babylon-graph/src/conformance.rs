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
use crate::substrate::{Direction, GraphSubstrate, NodeId};

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
    state_hash_is_stable_and_order_invariant_and_sensitive(&make);
    a_decade_boundary_orders_numerically_not_lexicographically(&make);
    declared_order_never_leaks_through_any_ranged_accessor(&make);
    node_type_of_reports_the_declared_type(&make);
    node_type_of_a_dangling_id_is_loud_not_untyped(&make);
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

/// Build the same world twice, in opposite WRITE order (both instances mint
/// the same ids in the same order — only the order of subsequent
/// updates/edges/hyperedges differs). Constitution III.7: the state hash
/// must not depend on write order.
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
    forward.add_hyperedge("economic_sector", &[a, b]).unwrap();

    let mut reverse = make();
    let a2 = reverse.add_node("social_class").unwrap();
    let b2 = reverse.add_node("social_class").unwrap();
    reverse.add_hyperedge("economic_sector", &[b2, a2]).unwrap();
    reverse.add_edge("solidarity", a2, b2, 0.5).unwrap();
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

    graph.remove_edge("solidarity", a, b).unwrap();
    let after_edge = graph.state_hash().unwrap();
    assert_ne!(
        after_attribute, after_edge,
        "an edge removal moves the hash"
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
/// FIGHTS id order, at every ranged accessor — `edges`, `hyperedges_of`, and
/// `members_of` all sort on the ruled key regardless of the order members
/// or edges were declared in.
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

#[cfg(test)]
mod tests {
    use super::run_substrate_conformance;
    use crate::memory::MemoryGraph;

    #[test]
    fn memory_graph_passes_the_conformance_suite() {
        run_substrate_conformance(MemoryGraph::new);
    }
}
