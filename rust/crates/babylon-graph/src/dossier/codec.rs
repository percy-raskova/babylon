//! Bounded canonical bytes for one actor's private, possibly stale beliefs.
//!
//! Version 1 is `babylon.dossier`, a zero byte, and a big-endian u32 version,
//! followed by the owner as u64, a u32 node count and sorted u64 node IDs,
//! then a u32 edge count and sorted `(edge type, from, to)` rows. Each edge
//! type is a u32 byte length and UTF-8 bytes; endpoints are u64. All integers
//! are big-endian. Identities reserve `u64::MAX`; edge types contain 1–128
//! bytes. At most 262,144 nodes, 65,536 edges, and 16,777,216 bytes are admitted.
//! There is no older format or compatibility decoder.

use super::Dossier;
use crate::stable_element::MAX_STABLE_RESOLVER_MANIFEST_BYTES;
use crate::stable_state::{MAX_STABLE_GRAPH_ELEMENTS, MAX_STABLE_GRAPH_NODES};
use crate::substrate::{GraphError, NodeId};
use std::collections::{BTreeMap, BTreeSet};

const HEADER: &[u8] = b"babylon.dossier\0\0\0\0\x01";
const MAX_NODES: usize = MAX_STABLE_GRAPH_NODES;
const MAX_EDGES: usize = MAX_STABLE_GRAPH_ELEMENTS;
const MAX_EDGE_TYPE_BYTES: usize = 128;
const MAX_BYTES: usize = MAX_STABLE_RESOLVER_MANIFEST_BYTES;

fn refusal(message: &str) -> GraphError {
    GraphError {
        message: format!("dossier codec: {message}"),
    }
}

fn valid_node(node: NodeId) -> Result<(), GraphError> {
    if node.0 == u64::MAX {
        return Err(refusal("reserved node identity"));
    }
    Ok(())
}

fn valid_edge_type(value: &str) -> Result<(), GraphError> {
    if value.is_empty() || value.len() > MAX_EDGE_TYPE_BYTES {
        return Err(refusal("edge type length is outside 1..=128 bytes"));
    }
    Ok(())
}

impl Dossier {
    /// Encode the owner's resolved nodes and directed ties in canonical order.
    ///
    /// # Errors
    /// Returns an error for reserved identities, invalid lengths, excessive
    /// counts or byte size, dangling endpoints, or allocation failure.
    pub fn encode_canonical(&self) -> Result<Vec<u8>, GraphError> {
        valid_node(self.owner)?;
        if self.resolved_nodes.len() > MAX_NODES {
            return Err(refusal("too many nodes"));
        }
        let mut edge_count = 0_usize;
        let mut size = HEADER.len() + 8 + 4 + 4;
        size = size
            .checked_add(
                self.resolved_nodes
                    .len()
                    .checked_mul(8)
                    .ok_or_else(|| refusal("size overflow"))?,
            )
            .ok_or_else(|| refusal("size overflow"))?;
        for &node in &self.resolved_nodes {
            valid_node(node)?;
        }
        for (kind, edges) in &self.resolved_edges {
            valid_edge_type(kind)?;
            edge_count = edge_count
                .checked_add(edges.len())
                .ok_or_else(|| refusal("edge count overflow"))?;
            if edge_count > MAX_EDGES {
                return Err(refusal("too many edges"));
            }
            let row_size = 4 + kind.len() + 16;
            size = size
                .checked_add(
                    edges
                        .len()
                        .checked_mul(row_size)
                        .ok_or_else(|| refusal("size overflow"))?,
                )
                .ok_or_else(|| refusal("size overflow"))?;
            for &(from, to) in edges {
                if !self.resolved_nodes.contains(&from) || !self.resolved_nodes.contains(&to) {
                    return Err(refusal("edge endpoint is not a resolved node"));
                }
            }
        }
        if size > MAX_BYTES {
            return Err(refusal("encoded bytes exceed limit"));
        }
        let mut output = Vec::new();
        output
            .try_reserve_exact(size)
            .map_err(|_| refusal("allocation failed"))?;
        output.extend_from_slice(HEADER);
        output.extend_from_slice(&self.owner.0.to_be_bytes());
        output.extend_from_slice(
            &u32::try_from(self.resolved_nodes.len())
                .map_err(|_| refusal("node count overflow"))?
                .to_be_bytes(),
        );
        for node in &self.resolved_nodes {
            output.extend_from_slice(&node.0.to_be_bytes());
        }
        output.extend_from_slice(
            &u32::try_from(edge_count)
                .map_err(|_| refusal("edge count overflow"))?
                .to_be_bytes(),
        );
        for (kind, edges) in &self.resolved_edges {
            for (from, to) in edges {
                output.extend_from_slice(
                    &u32::try_from(kind.len())
                        .map_err(|_| refusal("edge type length overflow"))?
                        .to_be_bytes(),
                );
                output.extend_from_slice(kind.as_bytes());
                output.extend_from_slice(&from.0.to_be_bytes());
                output.extend_from_slice(&to.0.to_be_bytes());
            }
        }
        Ok(output)
    }

    /// Decode exactly one canonical dossier without consulting the substrate.
    ///
    /// # Errors
    /// Returns an error for malformed, out-of-bounds, unordered, duplicate,
    /// dangling, trailing, or noncanonical input.
    pub fn decode_canonical(bytes: &[u8]) -> Result<Self, GraphError> {
        if bytes.len() > MAX_BYTES {
            return Err(refusal("encoded bytes exceed limit"));
        }
        let mut cursor = Cursor { bytes, pos: 0 };
        if cursor.take(HEADER.len())? != HEADER {
            return Err(refusal("invalid header"));
        }
        let owner = NodeId(cursor.u64()?);
        valid_node(owner)?;
        let node_count = cursor.count(MAX_NODES, "too many nodes")?;
        let mut resolved_nodes = BTreeSet::new();
        let mut previous_node = None;
        for _ in 0..node_count {
            let node = NodeId(cursor.u64()?);
            valid_node(node)?;
            if previous_node.is_some_and(|prev| prev >= node) {
                return Err(refusal("nodes are not sorted and unique"));
            }
            resolved_nodes.insert(node);
            previous_node = Some(node);
        }
        let edge_count = cursor.count(MAX_EDGES, "too many edges")?;
        let mut resolved_edges: BTreeMap<String, BTreeSet<(NodeId, NodeId)>> = BTreeMap::new();
        let mut previous_edge: Option<(&str, NodeId, NodeId)> = None;
        for _ in 0..edge_count {
            let length = cursor.count(MAX_EDGE_TYPE_BYTES, "edge type exceeds length limit")?;
            let kind = std::str::from_utf8(cursor.take(length)?)
                .map_err(|_| refusal("edge type is not UTF-8"))?;
            valid_edge_type(kind)?;
            let from = NodeId(cursor.u64()?);
            let to = NodeId(cursor.u64()?);
            if !resolved_nodes.contains(&from) || !resolved_nodes.contains(&to) {
                return Err(refusal("edge endpoint is not a resolved node"));
            }
            let row = (kind, from, to);
            if previous_edge.is_some_and(|prev| prev >= row) {
                return Err(refusal("edges are not sorted and unique"));
            }
            if let Some(ties) = resolved_edges.get_mut(kind) {
                ties.insert((from, to));
            } else {
                let mut edge_type = String::new();
                edge_type
                    .try_reserve_exact(kind.len())
                    .map_err(|_| refusal("allocation failed"))?;
                edge_type.push_str(kind);
                resolved_edges.insert(edge_type, BTreeSet::from([(from, to)]));
            }
            previous_edge = Some(row);
        }
        if cursor.pos != bytes.len() {
            return Err(refusal("trailing bytes"));
        }
        let dossier = Self {
            owner,
            resolved_nodes,
            resolved_edges,
        };
        if dossier.encode_canonical()?.as_slice() != bytes {
            return Err(refusal("noncanonical bytes"));
        }
        Ok(dossier)
    }
}

struct Cursor<'a> {
    bytes: &'a [u8],
    pos: usize,
}
impl<'a> Cursor<'a> {
    fn take(&mut self, len: usize) -> Result<&'a [u8], GraphError> {
        let end = self
            .pos
            .checked_add(len)
            .ok_or_else(|| refusal("offset overflow"))?;
        let part = self
            .bytes
            .get(self.pos..end)
            .ok_or_else(|| refusal("truncated input"))?;
        self.pos = end;
        Ok(part)
    }
    fn u32(&mut self) -> Result<u32, GraphError> {
        let mut data = [0; 4];
        data.copy_from_slice(self.take(4)?);
        Ok(u32::from_be_bytes(data))
    }
    fn u64(&mut self) -> Result<u64, GraphError> {
        let mut data = [0; 8];
        data.copy_from_slice(self.take(8)?);
        Ok(u64::from_be_bytes(data))
    }
    fn count(&mut self, max: usize, message: &str) -> Result<usize, GraphError> {
        let count = usize::try_from(self.u32()?).map_err(|_| refusal(message))?;
        if count > max {
            return Err(refusal(message));
        }
        Ok(count)
    }
}
