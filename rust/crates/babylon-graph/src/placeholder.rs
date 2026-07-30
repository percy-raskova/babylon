//! `PlaceholderGraph`: an in-memory `HashMap`-backed toy [`GraphSubstrate`]
//! implementation. **This is NOT the production graph storage** — it exists
//! solely so Tasks 16/17 of the Phase-1 plan (BSL's typed structural verbs,
//! the conformance corpus) have something real to typecheck and run against
//! before the concrete Phase-2 storage lands. It DOES honor the Amendment D
//! shape the trait fixes (hyperedges are their own objects with their own id
//! space, members are a sorted set, no pairwise expansion anywhere), because
//! that shape is ruled, not provisional — and it honors the §2.8 existence
//! discipline (duplicate add and absent remove are loud errors), because the
//! verb layer's tests pin exactly that. Deleting this module and swapping in
//! the production storage is expected, low-risk churn — nothing outside this
//! crate and its direct test dependents should assume its internals.
use crate::substrate::{Direction, GraphError, GraphSubstrate, HyperedgeId, NodeId};
use std::collections::HashMap;

/// A toy substrate. See the module documentation: compile-target, not a
/// foundation.
#[derive(Debug, Default)]
pub struct PlaceholderGraph {
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

impl PlaceholderGraph {
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
}

impl GraphSubstrate for PlaceholderGraph {
    fn add_node(&mut self, node_type: &str) -> Result<NodeId, GraphError> {
        let id = NodeId(self.next_id);
        self.next_id += 1;
        self.nodes.insert(id, node_type.to_owned());
        Ok(id)
    }

    fn remove_node(&mut self, id: NodeId) -> Result<(), GraphError> {
        self.nodes
            .remove(&id)
            .map(|_| ())
            .ok_or_else(|| GraphError {
                message: format!("no such node: {id:?}"),
            })
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

    fn members_of(&self, id: HyperedgeId) -> Result<Vec<NodeId>, GraphError> {
        self.hyperedges
            .get(&id)
            .map(|(_, members)| members.clone()) // already sorted at insert
            .ok_or_else(|| GraphError {
                message: format!("no such hyperedge: {id:?}"),
            })
    }

    fn hyperedges_of(&self, node: NodeId, hyperedge_type: &str) -> Vec<HyperedgeId> {
        let mut found: Vec<HyperedgeId> = self
            .hyperedges
            .iter()
            .filter(|(_, (ty, members))| ty == hyperedge_type && members.contains(&node))
            .map(|(id, _)| *id)
            .collect();
        found.sort_unstable();
        found
    }

    fn hyperedge_exists(&self, id: HyperedgeId) -> bool {
        self.hyperedges.contains_key(&id)
    }
}

#[cfg(test)]
mod tests {
    use super::{GraphSubstrate, NodeId, PlaceholderGraph};
    use crate::substrate::Direction;

    #[test]
    fn add_then_update_then_read_back() {
        let mut graph = PlaceholderGraph::new();
        let node = graph.add_node("social_class").unwrap();
        graph.update_node(node, "wealth", 42.0).unwrap();
        assert_eq!(graph.node_attribute(node, "wealth"), Ok(42.0));
    }

    #[test]
    fn an_unwritten_attribute_reads_loud_never_zero() {
        let mut graph = PlaceholderGraph::new();
        let node = graph.add_node("social_class").unwrap();
        assert!(graph.node_attribute(node, "wealth").is_err());
    }

    #[test]
    fn edge_to_nonexistent_node_is_a_loud_error() {
        let mut graph = PlaceholderGraph::new();
        let node = graph.add_node("territory").unwrap();
        assert!(graph
            .add_edge("adjacency", node, NodeId(9999), 1.0)
            .is_err());
    }

    #[test]
    fn duplicate_edge_add_and_absent_edge_remove_are_loud() {
        // §2.8: absence is never success, and adding what exists is an
        // error, not an overwrite.
        let mut graph = PlaceholderGraph::new();
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
        let mut graph = PlaceholderGraph::new();
        let first = graph.add_node("social_class").unwrap();
        let second = graph.add_node("social_class").unwrap();
        let third = graph.add_node("social_class").unwrap();
        let sector = graph
            .add_hyperedge("economic_sector", &[third, first, second])
            .unwrap();
        assert_eq!(
            graph.members_of(sector).unwrap(),
            vec![first, second, third]
        );
    }

    #[test]
    fn duplicate_member_is_a_loud_error() {
        let mut graph = PlaceholderGraph::new();
        let member = graph.add_node("social_class").unwrap();
        assert!(graph
            .add_hyperedge("economic_sector", &[member, member])
            .is_err());
    }

    #[test]
    fn nodes_query_ranges_over_one_type_in_ascending_id_order() {
        // §2.6 `(nodes <enum-ref>)` + the iteration-order ruling: ascending
        // node-id order, never storage order.
        let mut graph = PlaceholderGraph::new();
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
        let mut graph = PlaceholderGraph::new();
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
        let mut graph = PlaceholderGraph::new();
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
        let graph = PlaceholderGraph::new();
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
        let mut graph = PlaceholderGraph::new();
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
        let mut graph = PlaceholderGraph::new();
        let first = graph.add_node("social_class").unwrap();
        let second = graph.add_node("social_class").unwrap();
        let sector = graph
            .add_hyperedge("economic_sector", &[first, second])
            .unwrap();
        assert_eq!(graph.hyperedges_of(first, "economic_sector"), vec![sector]);
        // the dyadic half is untouched by minting a hyperedge
        assert_eq!(graph.edge_count(), 0);
        assert_eq!(graph.hyperedges.len(), 1);
    }
}
