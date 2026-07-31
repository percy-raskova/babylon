//! `MemoryGraph`: the in-memory [`GraphSubstrate`] **production logic runs
//! against** (Director ruling 2026-07-31, P27 Phase 2 Slice 1).
//!
//! It shipped in Phase 1 as `PlaceholderGraph`, a compile-target whose own
//! documentation said not to build on it. The promotion is not a change of
//! ambition but a recognition of what it already was: every invariant the
//! trait rules is already held here, and held on purpose.
//!
//! - **Amendment D shape.** Hyperedges are their own objects with their own
//!   id space; members are a sorted set; nothing expands to `C(n,2)` edges.
//! - **§2.8 existence discipline.** Duplicate add and absent remove are loud
//!   errors, never silent no-ops.
//! - **Honest nulls.** An unwritten attribute errors; it never reads 0.0.
//! - **ADR185 R2 cascade.** Removal is whole — edges, memberships and
//!   attributes go with the node, so a member list is always a set of live
//!   nodes and no internal map holds a key naming a corpse.
//! - **Contractual iteration order.** Every ranged accessor sorts before
//!   returning; storage order is never observable.
//!
//! **What it is not.** It is in-memory and unpersisted: there is no
//! snapshot, no journal, and no recovery. A campaign lives in a process.
//! Persistence is a separate estate and does not belong behind this trait.
//!
//! **On the swap.** The ADR179 T3 capability delta rules that hypergraph-rs
//! can back `GraphSubstrate` behind an adapter, *and not yet* — five of its
//! seven deltas are the library being silently permissive where III.11
//! requires loud failure, which is faithful XGI parity rather than a library
//! defect. That swap is deferred, not cancelled. Depend on the TRAIT, and
//! this type stays replaceable.
use crate::state_hash::StateEncoder;
use crate::substrate::{Direction, GraphError, GraphSubstrate, HyperedgeId, NodeId};
use std::collections::HashMap;

/// The in-memory substrate. See the module documentation.
#[derive(Debug, Default)]
pub struct MemoryGraph {
    nodes: HashMap<NodeId, String>,
    attributes: HashMap<(NodeId, String), f64>,
    /// `(edge_type, from, to)` -> strength. Real storage, so the §2.8
    /// duplicate-add / absent-remove discipline is checkable.
    edges: HashMap<(String, NodeId, NodeId), f64>,
    /// Hyperedge id -> (type, sorted member list). Stored as ONE record per
    /// hyperedge — the toy analogue of a first-class object. A production
    /// store may instead keep incidence edges (Levi); callers cannot tell.
    hyperedges: HashMap<HyperedgeId, (String, Vec<NodeId>)>,
    next_id: u64,
    next_hyperedge_id: u64,
}

impl MemoryGraph {
    /// An empty substrate.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Test-visible edge count (the dyadic half only).
    #[must_use]
    pub fn edge_count(&self) -> usize {
        self.edges.len()
    }

    /// Test-visible count of stored attribute keys, so the ADR185 R2 cascade
    /// can be checked for orphan rows from outside.
    #[must_use]
    pub fn attribute_key_count(&self) -> usize {
        self.attributes.len()
    }

    /// Serialize the whole store into the canonical state encoding
    /// ([`crate::state_hash`]), sorting every section.
    ///
    /// The sorting is where determinism is bought: this store is
    /// `HashMap`-backed and its iteration order varies per process, so an
    /// unsorted encoding would produce a different tick hash on every run of
    /// identical content.
    ///
    /// # Errors
    /// Returns [`GraphError`] if a non-finite value is stored (it must never
    /// enter the tick hash) or a count overflows its length prefix.
    pub fn encode_state(&self) -> Result<StateEncoder, GraphError> {
        let mut encoder = StateEncoder::new();

        let mut nodes: Vec<(NodeId, String)> = self
            .nodes
            .iter()
            .map(|(id, ty)| (*id, ty.clone()))
            .collect();
        nodes.sort_unstable_by_key(|(id, _)| *id);
        encoder.write_nodes(&nodes)?;

        let mut attributes: Vec<(NodeId, String, f64)> = self
            .attributes
            .iter()
            .map(|((id, name), value)| (*id, name.clone(), *value))
            .collect();
        attributes.sort_unstable_by(|a, b| a.0.cmp(&b.0).then_with(|| a.1.cmp(&b.1)));
        encoder.write_attributes(&attributes)?;

        let mut edges: Vec<(String, NodeId, NodeId, f64)> = self
            .edges
            .iter()
            .map(|((ty, from, to), strength)| (ty.clone(), *from, *to, *strength))
            .collect();
        edges.sort_unstable_by(|a, b| {
            a.0.cmp(&b.0)
                .then_with(|| a.1.cmp(&b.1))
                .then_with(|| a.2.cmp(&b.2))
        });
        encoder.write_edges(&edges)?;

        let mut hyperedges: Vec<(HyperedgeId, String, Vec<NodeId>)> = self
            .hyperedges
            .iter()
            .map(|(id, (ty, members))| (*id, ty.clone(), members.clone()))
            .collect();
        hyperedges.sort_unstable_by_key(|(id, _, _)| *id);
        encoder.write_hyperedges(&hyperedges)?;

        Ok(encoder)
    }

    /// The tick-hash contribution of this store's state (Constitution III.7).
    ///
    /// # Errors
    /// Returns [`GraphError`] for the reasons [`Self::encode_state`] does.
    pub fn state_hash(&self) -> Result<[u8; 32], GraphError> {
        Ok(self.encode_state()?.finish())
    }
}

impl GraphSubstrate for MemoryGraph {
    fn add_node(&mut self, node_type: &str) -> Result<NodeId, GraphError> {
        let id = NodeId(self.next_id);
        self.next_id += 1;
        self.nodes.insert(id, node_type.to_owned());
        Ok(id)
    }

    fn remove_node(&mut self, id: NodeId) -> Result<(), GraphError> {
        if self.nodes.remove(&id).is_none() {
            return Err(GraphError {
                message: format!("no such node: {id:?}"),
            });
        }
        // ADR185 R2: removal is WHOLE. Incident edges go, the node is dropped
        // from every member list, and its attributes go with it — so a member
        // list stays a set of live nodes, `members_of` means one thing to
        // every reader, and no internal map holds a key naming a dead node.
        //
        // The attribute sweep is not merely hygiene. `next_id` is monotonic
        // here so ids are never reused, but a production store that recycles
        // an id would resurrect a corpse's attributes onto a fresh node —
        // silently, and reading as real data. The invariant is what makes
        // that class of bug unavailable to the next implementor.
        self.attributes.retain(|(node, _), _| *node != id);
        self.edges
            .retain(|(_, from, to), _| *from != id && *to != id);
        for (_, members) in self.hyperedges.values_mut() {
            members.retain(|member| *member != id);
        }
        // An empty hyperedge is unrepresentable (`add_hyperedge` rejects an
        // empty member list), so leaving one behind would create by deletion
        // a state that cannot be created directly.
        self.hyperedges
            .retain(|_, (_, members)| !members.is_empty());
        Ok(())
    }

    fn add_edge(
        &mut self,
        edge_type: &str,
        from: NodeId,
        to: NodeId,
        strength: f64,
    ) -> Result<(), GraphError> {
        if !self.node_exists(from) || !self.node_exists(to) {
            return Err(GraphError {
                message: "edge endpoint does not exist".into(),
            });
        }
        let key = (edge_type.to_owned(), from, to);
        if self.edges.contains_key(&key) {
            return Err(GraphError {
                message: format!("edge already exists: {key:?}"),
            });
        }
        self.edges.insert(key, strength);
        Ok(())
    }

    fn remove_edge(&mut self, edge_type: &str, from: NodeId, to: NodeId) -> Result<(), GraphError> {
        let key = (edge_type.to_owned(), from, to);
        self.edges
            .remove(&key)
            .map(|_| ())
            .ok_or_else(|| GraphError {
                message: format!("no such edge: {key:?} — absence is never success"),
            })
    }

    fn update_node(&mut self, id: NodeId, attribute: &str, value: f64) -> Result<(), GraphError> {
        if !self.node_exists(id) {
            return Err(GraphError {
                message: format!("no such node: {id:?}"),
            });
        }
        self.attributes.insert((id, attribute.to_owned()), value);
        Ok(())
    }

    fn node_attribute(&self, id: NodeId, attribute: &str) -> Result<f64, GraphError> {
        if !self.node_exists(id) {
            return Err(GraphError {
                message: format!("no such node: {id:?}"),
            });
        }
        self.attributes
            .get(&(id, attribute.to_owned()))
            .copied()
            .ok_or_else(|| GraphError {
                message: format!(
                    "attribute {attribute} was never written on {id:?} — never a default 0.0"
                ),
            })
    }

    fn node_exists(&self, id: NodeId) -> bool {
        self.nodes.contains_key(&id)
    }

    fn nodes(&self, node_type: &str) -> Vec<NodeId> {
        let mut found: Vec<NodeId> = self
            .nodes
            .iter()
            .filter(|(_, ty)| *ty == node_type)
            .map(|(id, _)| *id)
            .collect();
        found.sort_unstable();
        found
    }

    fn edge_strength(&self, edge_type: &str, from: NodeId, to: NodeId) -> Result<f64, GraphError> {
        // Endpoint check FIRST: "no such node" and "these two real nodes are
        // not joined" are different facts, and collapsing them would make a
        // dangling NodeRef read as a merely-absent edge — the honest-null
        // discipline `node_attribute` and `neighbors` already hold.
        for (id, role) in [(from, "source"), (to, "target")] {
            if !self.node_exists(id) {
                return Err(GraphError {
                    message: format!("edge {role} {id:?} does not exist"),
                });
            }
        }
        self.edges
            .get(&(edge_type.to_owned(), from, to))
            .copied()
            .ok_or_else(|| GraphError {
                message: format!(
                    "no {edge_type} edge from {from:?} to {to:?} — a missing edge \
                     has no strength, and 0.0 is a real strength a present edge \
                     can carry (III.11: absence is not a value)"
                ),
            })
    }

    fn edges(&self, edge_type: &str) -> Vec<(NodeId, NodeId)> {
        let mut found: Vec<(NodeId, NodeId)> = self
            .edges
            .keys()
            .filter(|(ty, _, _)| ty == edge_type)
            .map(|(_, from, to)| (*from, *to))
            .collect();
        found.sort_unstable();
        found
    }

    fn neighbors(
        &self,
        node: NodeId,
        edge_type: &str,
        direction: Direction,
    ) -> Result<Vec<NodeId>, GraphError> {
        if !self.node_exists(node) {
            return Err(GraphError {
                message: format!("no such node: {node:?} — a dangling ref never reads empty"),
            });
        }
        let mut found: Vec<NodeId> = self
            .edges
            .keys()
            .filter(|(ty, _, _)| ty == edge_type)
            .filter_map(|(_, from, to)| match direction {
                Direction::Out => (*from == node).then_some(*to),
                Direction::In => (*to == node).then_some(*from),
                Direction::Any if *from == node => Some(*to),
                Direction::Any if *to == node => Some(*from),
                Direction::Any => None,
            })
            .collect();
        found.sort_unstable();
        found.dedup();
        Ok(found)
    }

    fn add_hyperedge(
        &mut self,
        hyperedge_type: &str,
        members: &[NodeId],
    ) -> Result<HyperedgeId, GraphError> {
        if members.is_empty() {
            return Err(GraphError {
                message: "hyperedge must have at least one member".into(),
            });
        }
        let mut sorted: Vec<NodeId> = members.to_vec();
        sorted.sort_unstable();
        if sorted.windows(2).any(|w| w[0] == w[1]) {
            return Err(GraphError {
                message: "duplicate member in hyperedge".into(),
            });
        }
        if let Some(missing) = sorted.iter().find(|n| !self.node_exists(**n)) {
            return Err(GraphError {
                message: format!("no such member node: {missing:?}"),
            });
        }
        let id = HyperedgeId(self.next_hyperedge_id);
        self.next_hyperedge_id += 1;
        self.hyperedges
            .insert(id, (hyperedge_type.to_owned(), sorted));
        Ok(id)
    }

    fn remove_hyperedge(&mut self, id: HyperedgeId) -> Result<(), GraphError> {
        self.hyperedges
            .remove(&id)
            .map(|_| ())
            .ok_or_else(|| GraphError {
                message: format!("no such hyperedge: {id:?}"),
            })
    }

    fn members_of(&self, id: HyperedgeId, hyperedge_type: &str) -> Result<Vec<NodeId>, GraphError> {
        let (stored_type, members) = self.hyperedges.get(&id).ok_or_else(|| GraphError {
            message: format!("no such hyperedge: {id:?}"),
        })?;
        if stored_type != hyperedge_type {
            return Err(GraphError {
                message: format!(
                    "hyperedge {id:?} is a {stored_type}, not a {hyperedge_type} — \
                     BSL E-EVAL-032. A mismatched referent is an ERROR, never an \
                     empty member list: reading zero members from the wrong type \
                     would look exactly like a real hyperedge that happens to be \
                     empty, and the two are different facts"
                ),
            });
        }
        Ok(members.clone()) // already sorted at insert
    }

    fn hyperedges_of(
        &self,
        node: NodeId,
        hyperedge_type: &str,
    ) -> Result<Vec<HyperedgeId>, GraphError> {
        if !self.nodes.contains_key(&node) {
            return Err(GraphError {
                message: format!(
                    "no such node: {node:?} — belonging to nothing and not existing \
                     are different facts"
                ),
            });
        }
        let mut found: Vec<HyperedgeId> = self
            .hyperedges
            .iter()
            .filter(|(_, (ty, members))| ty == hyperedge_type && members.contains(&node))
            .map(|(id, _)| *id)
            .collect();
        found.sort_unstable();
        Ok(found)
    }
}

#[cfg(test)]
mod tests {
    use super::{GraphSubstrate, MemoryGraph, NodeId};
    use crate::substrate::Direction;

    #[test]
    fn removing_a_node_cascades_to_its_edges_and_memberships() {
        // ADR185 R2. Before this ruling remove_node dropped the node and
        // nothing else, leaving `edges` holding dead endpoints and member
        // lists holding dead ids — so `edges()` returned endpoints that
        // failed `node_exists`, and `members_of` stopped being a set of live
        // nodes. Removal is whole.
        let mut graph = MemoryGraph::new();
        let doomed = graph.add_node("social_class").unwrap();
        let survivor = graph.add_node("social_class").unwrap();
        let bystander = graph.add_node("social_class").unwrap();
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
            graph.members_of(sector, "economic_sector").unwrap(),
            vec![survivor, bystander],
            "a member list is a set of LIVE nodes"
        );
        assert!(graph
            .neighbors(doomed, "solidarity", Direction::Any)
            .is_err());
    }

    /// Build the same world twice, inserting in opposite orders.
    fn same_world_two_orders() -> (MemoryGraph, MemoryGraph) {
        let mut forward = MemoryGraph::new();
        let a = forward.add_node("social_class").unwrap();
        let b = forward.add_node("social_class").unwrap();
        forward.update_node(a, "wages", 120.0).unwrap();
        forward.update_node(a, "value_produced", 80.0).unwrap();
        forward.update_node(b, "wages", 40.0).unwrap();
        forward.add_edge("solidarity", a, b, 0.5).unwrap();
        forward.add_hyperedge("economic_sector", &[a, b]).unwrap();

        let mut reverse = MemoryGraph::new();
        let a2 = reverse.add_node("social_class").unwrap();
        let b2 = reverse.add_node("social_class").unwrap();
        // Same facts, opposite write order.
        reverse.add_hyperedge("economic_sector", &[b2, a2]).unwrap();
        reverse.add_edge("solidarity", a2, b2, 0.5).unwrap();
        reverse.update_node(b2, "wages", 40.0).unwrap();
        reverse.update_node(a2, "value_produced", 80.0).unwrap();
        reverse.update_node(a2, "wages", 120.0).unwrap();

        (forward, reverse)
    }

    #[test]
    fn the_state_hash_does_not_depend_on_insertion_order() {
        // THE determinism contract for this store (Constitution III.7). It is
        // `HashMap`-backed, so its iteration order varies per process; if the
        // encoding did not sort, the same world would hash differently on
        // every run and replay would be impossible.
        let (forward, reverse) = same_world_two_orders();
        assert_eq!(
            forward.state_hash().unwrap(),
            reverse.state_hash().unwrap(),
            "the same world must hash identically however it was built"
        );
    }

    #[test]
    fn the_state_hash_is_stable_across_repeated_encodings() {
        // Guards against a hash that varies within one process too — the
        // failure a single equality check between two graphs would miss.
        let (graph, _) = same_world_two_orders();
        let first = graph.state_hash().unwrap();
        for _ in 0..8 {
            assert_eq!(graph.state_hash().unwrap(), first);
        }
    }

    #[test]
    fn any_real_change_moves_the_state_hash() {
        // The dual of determinism: a hash nothing changes is worthless.
        let (mut graph, _) = same_world_two_orders();
        let before = graph.state_hash().unwrap();

        graph.update_node(NodeId(0), "wages", 121.0).unwrap();
        let after_attribute = graph.state_hash().unwrap();
        assert_ne!(before, after_attribute, "an attribute write moves it");

        graph
            .remove_edge("solidarity", NodeId(0), NodeId(1))
            .unwrap();
        let after_edge = graph.state_hash().unwrap();
        assert_ne!(after_attribute, after_edge, "an edge removal moves it");

        graph.add_node("organization").unwrap();
        assert_ne!(
            after_edge,
            graph.state_hash().unwrap(),
            "a new node moves it"
        );
    }

    #[test]
    fn removal_takes_the_nodes_attributes_with_it() {
        // No internal map may hold a key naming a dead node. `next_id` is
        // monotonic here so ids are never reused — but a production store
        // that recycles one would resurrect a corpse's attributes onto a
        // fresh node, silently, reading as real data.
        let mut graph = MemoryGraph::new();
        let doomed = graph.add_node("social_class").unwrap();
        let survivor = graph.add_node("social_class").unwrap();
        graph.update_node(doomed, "wealth", 42.0).unwrap();
        graph.update_node(survivor, "wealth", 7.0).unwrap();

        graph.remove_node(doomed).unwrap();

        assert_eq!(
            graph.attribute_key_count(),
            1,
            "the removed node's attribute rows are gone, not orphaned"
        );
        assert!(
            (graph.node_attribute(survivor, "wealth").unwrap() - 7.0).abs() < 1e-12,
            "and the survivor's are untouched"
        );
    }

    #[test]
    fn a_hyperedge_losing_its_last_member_is_removed_not_emptied() {
        // An empty hyperedge is unrepresentable — add_hyperedge rejects an
        // empty member list — so leaving one behind would create BY DELETION
        // a state that cannot be created directly.
        let mut graph = MemoryGraph::new();
        let only = graph.add_node("social_class").unwrap();
        let sector = graph.add_hyperedge("economic_sector", &[only]).unwrap();

        graph.remove_node(only).unwrap();

        let err = graph.members_of(sector, "economic_sector").unwrap_err();
        assert!(err.message.contains("no such hyperedge"), "{}", err.message);
    }

    #[test]
    fn belonging_to_nothing_and_not_existing_are_different_facts() {
        // The honest-null discipline at the hyperedge half. An unknown TYPE
        // is an empty range (type validity is BSL's E-TYPE-011, not the
        // substrate's); an unknown NODE is loud.
        //
        // Why the asymmetry is load-bearing rather than pedantic: a target
        // that belongs to no protective structure is the CHEAPEST one an
        // adversary can reach. If a missing node read as "belongs to
        // nothing", every data hole would present as a defenceless target.
        // Pine Ridge (FIPS 46102) has zero census rows at every vintage, so
        // that is a real shape in the data, not a hypothetical.
        let mut graph = MemoryGraph::new();
        let lone = graph.add_node("social_class").unwrap();

        assert_eq!(
            graph.hyperedges_of(lone, "community").unwrap(),
            vec![],
            "a real node in no community of that type is an empty range"
        );
        assert_eq!(
            graph.hyperedges_of(lone, "no_such_type").unwrap(),
            vec![],
            "an unknown TYPE is empty, not an error — E-TYPE-011 is BSL's job"
        );

        let err = graph.hyperedges_of(NodeId(999), "community").unwrap_err();
        assert!(
            err.message.contains("different facts"),
            "an absent NODE must be loud: {}",
            err.message
        );
    }

    #[test]
    fn add_then_update_then_read_back() {
        let mut graph = MemoryGraph::new();
        let node = graph.add_node("social_class").unwrap();
        graph.update_node(node, "wealth", 42.0).unwrap();
        assert_eq!(graph.node_attribute(node, "wealth"), Ok(42.0));
    }

    #[test]
    fn an_unwritten_attribute_reads_loud_never_zero() {
        let mut graph = MemoryGraph::new();
        let node = graph.add_node("social_class").unwrap();
        assert!(graph.node_attribute(node, "wealth").is_err());
    }

    #[test]
    fn edge_strength_reads_back_what_add_edge_wrote() {
        let mut graph = MemoryGraph::new();
        let a = graph.add_node("social_class").unwrap();
        let b = graph.add_node("social_class").unwrap();
        graph.add_edge("solidarity", a, b, 0.25).unwrap();
        assert_eq!(graph.edge_strength("solidarity", a, b), Ok(0.25));
    }

    #[test]
    fn a_present_edge_may_carry_strength_zero_and_that_is_not_absence() {
        // The reason `edge_strength` returns a Result at all: 0.0 is a real
        // strength. If absence were spelled 0.0, these two states would be
        // indistinguishable to every caller.
        let mut graph = MemoryGraph::new();
        let a = graph.add_node("social_class").unwrap();
        let b = graph.add_node("social_class").unwrap();
        graph.add_edge("solidarity", a, b, 0.0).unwrap();
        assert_eq!(graph.edge_strength("solidarity", a, b), Ok(0.0));
        assert!(graph.edge_strength("wages", a, b).is_err());
    }

    #[test]
    fn edge_strength_separates_no_such_node_from_no_such_edge() {
        // Two different facts, two distinguishable errors. Collapsing them
        // would let a dangling NodeRef read as a merely-absent edge.
        let mut graph = MemoryGraph::new();
        let a = graph.add_node("social_class").unwrap();
        let b = graph.add_node("social_class").unwrap();

        let no_edge = graph.edge_strength("solidarity", a, b).unwrap_err();
        assert!(
            no_edge.message.contains("no solidarity edge"),
            "{no_edge:?}"
        );

        let dangling = graph
            .edge_strength("solidarity", a, NodeId(9999))
            .unwrap_err();
        assert!(dangling.message.contains("does not exist"), "{dangling:?}");
        assert_ne!(no_edge.message, dangling.message);
    }

    #[test]
    fn members_of_the_wrong_hyperedge_type_is_loud_never_empty() {
        // BSL E-EVAL-032. Reading zero members from the wrong type would look
        // exactly like a real hyperedge that happens to be empty — and the
        // type is a mandatory operand precisely so that cannot happen.
        let mut graph = MemoryGraph::new();
        let a = graph.add_node("social_class").unwrap();
        let sector = graph.add_hyperedge("economic_sector", &[a]).unwrap();

        assert_eq!(graph.members_of(sector, "economic_sector"), Ok(vec![a]));

        let err = graph.members_of(sector, "CELL").unwrap_err();
        assert!(err.message.contains("E-EVAL-032"), "{err:?}");
    }

    #[test]
    fn edge_to_nonexistent_node_is_a_loud_error() {
        let mut graph = MemoryGraph::new();
        let node = graph.add_node("territory").unwrap();
        assert!(graph
            .add_edge("adjacency", node, NodeId(9999), 1.0)
            .is_err());
    }

    #[test]
    fn duplicate_edge_add_and_absent_edge_remove_are_loud() {
        // §2.8: absence is never success, and adding what exists is an
        // error, not an overwrite.
        let mut graph = MemoryGraph::new();
        let a = graph.add_node("social_class").unwrap();
        let b = graph.add_node("social_class").unwrap();
        graph.add_edge("solidarity", a, b, 0.5).unwrap();
        assert!(graph.add_edge("solidarity", a, b, 0.9).is_err());
        graph.remove_edge("solidarity", a, b).unwrap();
        assert!(graph.remove_edge("solidarity", a, b).is_err());
    }

    #[test]
    fn hyperedge_members_come_back_sorted_not_in_declared_order() {
        // Amendment D / BSL D25: declared member order is unobservable.
        let mut graph = MemoryGraph::new();
        let first = graph.add_node("social_class").unwrap();
        let second = graph.add_node("social_class").unwrap();
        let third = graph.add_node("social_class").unwrap();
        let sector = graph
            .add_hyperedge("economic_sector", &[third, first, second])
            .unwrap();
        assert_eq!(
            graph.members_of(sector, "economic_sector").unwrap(),
            vec![first, second, third]
        );
    }

    #[test]
    fn duplicate_member_is_a_loud_error() {
        let mut graph = MemoryGraph::new();
        let member = graph.add_node("social_class").unwrap();
        assert!(graph
            .add_hyperedge("economic_sector", &[member, member])
            .is_err());
    }

    #[test]
    fn nodes_query_ranges_over_one_type_in_ascending_id_order() {
        // §2.6 `(nodes <enum-ref>)` + the iteration-order ruling: ascending
        // node-id order, never storage order.
        let mut graph = MemoryGraph::new();
        let class_a = graph.add_node("social_class").unwrap();
        let territory = graph.add_node("territory").unwrap();
        let class_b = graph.add_node("social_class").unwrap();
        assert_eq!(graph.nodes("social_class"), vec![class_a, class_b]);
        assert_eq!(graph.nodes("territory"), vec![territory]);
        assert_eq!(graph.nodes("organization"), Vec::<NodeId>::new());
    }

    #[test]
    fn edges_query_ranges_over_one_type_in_source_target_order() {
        // §2.6 `(edges <enum-ref>)`: ascending (source-id, target-id) order.
        let mut graph = MemoryGraph::new();
        let a = graph.add_node("social_class").unwrap();
        let b = graph.add_node("social_class").unwrap();
        let c = graph.add_node("social_class").unwrap();
        graph.add_edge("solidarity", b, a, 0.4).unwrap();
        graph.add_edge("solidarity", a, c, 0.6).unwrap();
        graph.add_edge("wages", c, a, 0.9).unwrap();
        assert_eq!(graph.edges("solidarity"), vec![(a, c), (b, a)]);
        assert_eq!(graph.edges("wages"), vec![(c, a)]);
        assert_eq!(graph.edges("tribute"), Vec::<(NodeId, NodeId)>::new());
    }

    #[test]
    fn neighbors_query_honors_direction_and_dedups_as_a_set() {
        // §2.6 `(neighbors <expr> <enum-ref> <direction>)`: :out follows
        // source->target, :in the reverse, :any their union — a NodeSet,
        // so a node reachable both ways appears once.
        let mut graph = MemoryGraph::new();
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
            vec![class_a, class_b]
        );
        // other edge types are invisible to this query
        assert_eq!(
            graph.neighbors(org, "solidarity", Direction::Any).unwrap(),
            Vec::<NodeId>::new()
        );
    }

    #[test]
    fn neighbors_of_a_nonexistent_node_is_a_loud_error() {
        // A dangling NodeRef must never read as an empty neighborhood.
        let graph = MemoryGraph::new();
        assert!(graph
            .neighbors(NodeId(9999), "membership", Direction::Any)
            .is_err());
    }

    #[test]
    fn co_projection_composes_from_neighbors_alone() {
        // The dossier §5.2 org<->org inducement (shared class base via
        // MEMBERSHIP) expressed as pure composition over the query surface —
        // the shape the heat system's targeting reads. Two orgs organizing
        // the same class are induced-adjacent; a third org organizing a
        // different class is not.
        let mut graph = MemoryGraph::new();
        let org_a = graph.add_node("organization").unwrap();
        let org_b = graph.add_node("organization").unwrap();
        let org_c = graph.add_node("organization").unwrap();
        let shared_class = graph.add_node("social_class").unwrap();
        let other_class = graph.add_node("social_class").unwrap();
        graph
            .add_edge("membership", org_a, shared_class, 1.0)
            .unwrap();
        graph
            .add_edge("membership", org_b, shared_class, 1.0)
            .unwrap();
        graph
            .add_edge("membership", org_c, other_class, 1.0)
            .unwrap();

        let induced: Vec<NodeId> = graph
            .neighbors(org_a, "membership", Direction::Out)
            .unwrap()
            .into_iter()
            .flat_map(|base| graph.neighbors(base, "membership", Direction::In).unwrap())
            .filter(|peer| *peer != org_a)
            .collect();
        assert_eq!(induced, vec![org_b]);
    }

    #[test]
    fn a_hyperedge_mints_no_pairwise_edges() {
        // VIII.9 by construction: n members cost one object, not C(n,2) edges.
        let mut graph = MemoryGraph::new();
        let first = graph.add_node("social_class").unwrap();
        let second = graph.add_node("social_class").unwrap();
        let sector = graph
            .add_hyperedge("economic_sector", &[first, second])
            .unwrap();
        assert_eq!(
            graph.hyperedges_of(first, "economic_sector").unwrap(),
            vec![sector]
        );
        // the dyadic half is untouched by minting a hyperedge
        assert_eq!(graph.edge_count(), 0);
        assert_eq!(graph.hyperedges.len(), 1);
    }
}
