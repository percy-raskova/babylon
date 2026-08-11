//! `HypergraphStore`: the [`GraphSubstrate`] adapter over
//! `hypergraph-rs` (ADR179 T3) — the storage-swap plan's Phase C.
//!
//! **Two data structures, not one** (delta document §8 covenant 7,
//! `docs/reference/graph-storage-capability-delta.md`). The dyadic half
//! (`nodes`, `attributes`, `edges`) is native Rust maps, identical in shape
//! to [`crate::memory::MemoryGraph`]'s. The hyperedge half delegates to one
//! `hypergraph_rs::Hypergraph<(), String, MembershipPayload>` — the
//! Levi/incidence encoding Amendment D permits as an INTERNAL storage
//! strategy and forbids exposing (D-1). Splitting the halves into separate
//! structures makes Anti-Pattern VIII.9 (no method may expand a hyperedge
//! into pairwise edges) a structural fact rather than a covenant to police:
//! `neighbors()` reads only `edges`, so there is no code path through which
//! a many-member hyperedge could read as a pairwise expansion.
//!
//! **The identity map.** `NodeId`/`HyperedgeId` mint exactly as
//! `MemoryGraph` mints them — monotonic `u64` counters, never a function of
//! declared order (open question 2, ADR191 R2: identity stays a mint
//! counter). The library's own ids are `String`; this adapter's key is the
//! 16-character lowercase zero-padded hex of the id's big-endian `u64`
//! (`node_key`/`hyperedge_key` below), which makes byte-lexicographic and
//! numeric order the same order (delta §4 CD7's recommended resolution,
//! adopted here as a mechanical property rather than a spec claim). Reverse
//! maps (`node_keys`, `hyperedge_keys`) resolve library results back to
//! typed ids without re-parsing hex.
//!
//! **Node universes coincide by construction** (delta §8 covenant 4):
//! [`GraphSubstrate::add_node`] mints into the library's `add_node` in the
//! same call that mints into this adapter's own `nodes` map, so the
//! existence check `add_hyperedge`'s preamble runs against `self.nodes`
//! actually proves something about the library's universe too — the
//! library's silent auto-create of an unknown member never becomes
//! reachable, because no member this adapter would validate can be unknown
//! to the library.

use crate::state_hash::CanonicalState;
use crate::substrate::{Direction, GraphError, GraphSubstrate, HyperedgeId, NodeId};
use hypergraph_rs::Hypergraph;
use std::collections::HashMap;

/// The 16-character lowercase zero-padded hex of `id`'s big-endian `u64` —
/// the library key a [`NodeId`] mints under.
fn node_key(id: NodeId) -> String {
    format!("{:016x}", id.0)
}

/// The same encoding for a [`HyperedgeId`].
fn hyperedge_key(id: HyperedgeId) -> String {
    format!("{:016x}", id.0)
}

/// The membership payload slot `hypergraph-rs`'s `MembershipEdge<M>` carries
/// on every (member, hyperedge) incidence edge — the `petgraph` edge
/// weight, structurally the right home for Amendment AG (i) / ADR189's
/// attributed membership, because the (member, hyperedge) pair it names is
/// exactly the key this slot hangs on.
///
/// **Carried, empty, unhashed — nothing in this train writes it.** The
/// library exposes the slot with zero accessors (six construction sites
/// hard-code `M::default()`, zero reads —
/// `percy-raskova/hypergraph-rs#2`, filed Phase B Task 4 Step 4). This type
/// exists so the slot already sits in the adapter's type when the accessor
/// lands upstream; the moment an AG task adds a write through it, this
/// comment is the first thing it must revisit.
#[derive(Debug, Default, Clone, PartialEq, Eq)]
struct MembershipPayload;

/// The `hypergraph-rs`-backed [`GraphSubstrate`]/[`CanonicalState`] adapter.
/// See the module documentation. Nothing but [`Self::new`] is public — a
/// caller depends on the traits; the store's internal shape is its own
/// business.
#[derive(Debug, Default)]
pub struct HypergraphStore {
    /// Dyadic half — identical in shape to `MemoryGraph`'s.
    nodes: HashMap<NodeId, String>,
    node_keys: HashMap<String, NodeId>,
    attributes: HashMap<(NodeId, String), f64>,
    edges: HashMap<(String, NodeId, NodeId), f64>,
    /// Hyperedge half — the library key -> `HyperedgeId` reverse map, and the
    /// `(hyperedge_type -> ids)` index the library carries no type
    /// dimension for (delta §4: "the library has no type-keyed query, so
    /// the adapter must build the index itself regardless").
    hyperedge_keys: HashMap<String, HyperedgeId>,
    hyperedge_type_index: HashMap<String, Vec<HyperedgeId>>,
    /// The Levi/incidence store — internal only (D-1). `E = String` carries
    /// the hyperedge type (delta §4 CD1: no type-keyed query on the
    /// library side, so the type rides in `attrs` AND the side index).
    inner: Hypergraph<(), String, MembershipPayload>,
    next_id: u64,
    next_hyperedge_id: u64,
}

impl HypergraphStore {
    /// An empty substrate.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// The frozen pre-check (delta §8 covenant 6, CD4) at the head of every
    /// one of the 7 mutating [`GraphSubstrate`] methods — `add_node`,
    /// `remove_node`, `add_edge`, `remove_edge`, `update_node`,
    /// `add_hyperedge`, `remove_hyperedge` — via the library's public
    /// `is_frozen()`. Nothing in this crate ever freezes `self.inner` (no
    /// `GraphSubstrate` method exposes a freeze verb — that would be
    /// amendment territory, delta §4 CD4), so this is defense against a
    /// FUTURE reachable path (`hypergraph_rs::subhypergraph` freezes its
    /// return and there is no unfreeze anywhere in the library) rather than
    /// a condition this train can trigger.
    fn check_not_frozen(&self) -> Result<(), GraphError> {
        if self.inner.is_frozen() {
            return Err(GraphError {
                message: "substrate is frozen — no mutation is possible".to_owned(),
            });
        }
        Ok(())
    }

    /// Drop `id` from the `hyperedge_type` bucket of the type index. A
    /// no-op if `id` was never in it — callers pass the type an id was
    /// minted or found under, so this never needs to be loud.
    fn drop_from_type_index(&mut self, hyperedge_type: &str, id: HyperedgeId) {
        if let Some(ids) = self.hyperedge_type_index.get_mut(hyperedge_type) {
            ids.retain(|existing| *existing != id);
        }
    }
}

impl GraphSubstrate for HypergraphStore {
    fn add_node(&mut self, node_type: &str) -> Result<NodeId, GraphError> {
        self.check_not_frozen()?;
        let id = NodeId(self.next_id);
        self.next_id += 1;
        let key = node_key(id);
        self.nodes.insert(id, node_type.to_owned());
        self.node_keys.insert(key.clone(), id);
        // Covenant 4: mint through the library too, or the existence check
        // below proves nothing about the library's universe.
        self.inner.add_node(&key, ());
        Ok(id)
    }

    fn remove_node(&mut self, id: NodeId) -> Result<(), GraphError> {
        self.check_not_frozen()?;
        if self.nodes.remove(&id).is_none() {
            return Err(GraphError {
                message: format!("no such node: {id:?}"),
            });
        }
        let key = node_key(id);
        self.node_keys.remove(&key);
        self.attributes.retain(|(node, _), _| *node != id);
        self.edges
            .retain(|(_, from, to), _| *from != id && *to != id);

        // ADR185 R2 cascade, hyperedge half. Capture (edge key, type) for
        // every hyperedge this node belongs to BEFORE the library call —
        // once the library has run its own weak-removal-with-cleanup, a
        // hyperedge that lost its LAST member is gone from `inner` and its
        // attrs are unreachable, so the type must be read first.
        let prior_memberships: Vec<(String, String)> = self
            .inner
            .memberships(&key)
            .unwrap_or_default()
            .into_iter()
            .filter_map(|edge_key| {
                self.inner
                    .edge_attrs(&edge_key)
                    .cloned()
                    .map(|ty| (edge_key, ty))
            })
            .collect();

        // strong=false, remove_empty=true: detach this node from every
        // membership, then drop any hyperedge left with none — exactly
        // ADR185 R2 (H2 SHRINK), verified by the conformance suite rather
        // than assumed from the signature (Task 7 Step 5).
        self.inner
            .remove_node(&key, false, true)
            .map_err(|e| GraphError {
                message: format!("hyperedge-half removal of {id:?}: {e}"),
            })?;

        for (edge_key, hyperedge_type) in prior_memberships {
            if !self.inner.has_edge(&edge_key) {
                if let Some(hid) = self.hyperedge_keys.remove(&edge_key) {
                    self.drop_from_type_index(&hyperedge_type, hid);
                }
            }
        }
        Ok(())
    }

    fn add_edge(
        &mut self,
        edge_type: &str,
        from: NodeId,
        to: NodeId,
        strength: f64,
    ) -> Result<(), GraphError> {
        self.check_not_frozen()?;
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
        self.check_not_frozen()?;
        let key = (edge_type.to_owned(), from, to);
        self.edges
            .remove(&key)
            .map(|_| ())
            .ok_or_else(|| GraphError {
                message: format!("no such edge: {key:?} — absence is never success"),
            })
    }

    fn update_node(&mut self, id: NodeId, attribute: &str, value: f64) -> Result<(), GraphError> {
        self.check_not_frozen()?;
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
        self.check_not_frozen()?;
        // The loud preamble (delta §8 covenant 3), CD2/CD3 in one place:
        // empty, duplicate, and unknown members are all loud errors here,
        // before delegation — the sort happens anyway (members come back
        // ascending), so the duplicate check is free. The floor is exactly
        // ONE member; "hardening" to two would smuggle in an unruled
        // cardinality constant.
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
        let key = hyperedge_key(id);
        let member_keys: Vec<String> = sorted.iter().map(|n| node_key(*n)).collect();
        self.inner
            .add_edge(member_keys, Some(key.clone()), hyperedge_type.to_owned())
            .map_err(|e| GraphError {
                message: format!("hyperedge-half mint: {e}"),
            })?;
        self.hyperedge_keys.insert(key, id);
        self.hyperedge_type_index
            .entry(hyperedge_type.to_owned())
            .or_default()
            .push(id);
        Ok(id)
    }

    fn remove_hyperedge(&mut self, id: HyperedgeId) -> Result<(), GraphError> {
        self.check_not_frozen()?;
        let key = hyperedge_key(id);
        let hyperedge_type = self.inner.edge_attrs(&key).cloned();
        self.inner.remove_edge(&key).map_err(|_| GraphError {
            message: format!("no such hyperedge: {id:?}"),
        })?;
        self.hyperedge_keys.remove(&key);
        if let Some(ty) = hyperedge_type {
            self.drop_from_type_index(&ty, id);
        }
        Ok(())
    }

    fn members_of(&self, id: HyperedgeId) -> Result<Vec<NodeId>, GraphError> {
        let key = hyperedge_key(id);
        let members = self.inner.members(&key).ok_or_else(|| GraphError {
            message: format!("no such hyperedge: {id:?}"),
        })?;
        let mut result: Vec<NodeId> = members
            .into_iter()
            .map(|member_key| {
                *self.node_keys.get(&member_key).unwrap_or_else(|| {
                    panic!(
                        "internal invariant violated: library member {member_key} \
                         has no NodeId mapping — node/library universe desync"
                    )
                })
            })
            .collect();
        result.sort_unstable(); // BSL D25: declared member order is never observable
        Ok(result)
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
        let Some(type_ids) = self.hyperedge_type_index.get(hyperedge_type) else {
            return Ok(Vec::new());
        };
        let key = node_key(node);
        let membership_keys = self.inner.memberships(&key).unwrap_or_default();
        let mut found: Vec<HyperedgeId> = membership_keys
            .into_iter()
            .filter_map(|member_key| self.hyperedge_keys.get(&member_key).copied())
            .filter(|hid| type_ids.contains(hid))
            .collect();
        found.sort_unstable();
        Ok(found)
    }
}

impl CanonicalState for HypergraphStore {
    fn all_nodes(&self) -> Vec<(NodeId, String)> {
        self.nodes
            .iter()
            .map(|(id, ty)| (*id, ty.clone()))
            .collect()
    }

    fn all_attributes(&self) -> Vec<(NodeId, String, f64)> {
        self.attributes
            .iter()
            .map(|((id, name), value)| (*id, name.clone(), *value))
            .collect()
    }

    fn all_edges(&self) -> Vec<(String, NodeId, NodeId, f64)> {
        self.edges
            .iter()
            .map(|((ty, from, to), strength)| (ty.clone(), *from, *to, *strength))
            .collect()
    }

    /// Walks the library's `edge_ids()`, maps each through the identity
    /// map, reads members, maps those back, and reads the type off `attrs`
    /// — no sorting here (the provided `encode_state` sorts; a store that
    /// needed to sort to come out right here would have a bug this method
    /// should not paper over).
    fn all_hyperedges(&self) -> Vec<(HyperedgeId, String, Vec<NodeId>)> {
        self.inner
            .edge_ids()
            .into_iter()
            .map(|key| {
                let id = *self.hyperedge_keys.get(&key).unwrap_or_else(|| {
                    panic!(
                        "internal invariant violated: library edge {key} \
                         has no HyperedgeId mapping"
                    )
                });
                let hyperedge_type = self.inner.edge_attrs(&key).cloned().unwrap_or_else(|| {
                    panic!("internal invariant violated: library edge {key} has no type attrs")
                });
                let members = self
                    .inner
                    .members(&key)
                    .unwrap_or_default()
                    .into_iter()
                    .map(|member_key| {
                        *self.node_keys.get(&member_key).unwrap_or_else(|| {
                            panic!(
                                "internal invariant violated: library member {member_key} \
                                 has no NodeId mapping"
                            )
                        })
                    })
                    .collect();
                (id, hyperedge_type, members)
            })
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::HypergraphStore;
    use crate::conformance::run_substrate_conformance;

    #[test]
    fn hypergraph_store_passes_the_conformance_suite() {
        run_substrate_conformance(HypergraphStore::new);
    }
}
