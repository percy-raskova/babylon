//! Canonical handle-independent bytes for private, possibly stale beliefs.
//!
//! Version 2 frames every owner and endpoint as a complete stable node key.
//! Counts and lengths are big-endian u32. Nodes and edge rows are sorted by
//! their canonical key bytes; no version 1 or raw-handle decoder exists.

use std::collections::{BTreeMap, BTreeSet};

use super::Dossier;
use crate::stable_element::{
    StableElementKey, StableElementResolver, MAX_STABLE_RESOLVER_MANIFEST_BYTES,
};
use crate::stable_state::{MAX_STABLE_GRAPH_ELEMENTS, MAX_STABLE_GRAPH_NODES};
use crate::substrate::{GraphError, NodeId};

const HEADER: &[u8] = b"babylon.dossier\0\0\0\0\x02";
const MAX_NODES: usize = MAX_STABLE_GRAPH_NODES;
const MAX_EDGES: usize = MAX_STABLE_GRAPH_ELEMENTS;
const MAX_EDGE_TYPE_BYTES: usize = 128;
const MAX_KEY_BYTES: usize = 512;
const MAX_BYTES: usize = MAX_STABLE_RESOLVER_MANIFEST_BYTES;

type EdgeRow = (String, Vec<u8>, Vec<u8>);

fn refusal(message: &str) -> GraphError {
    GraphError {
        message: format!("dossier codec: {message}"),
    }
}
fn valid_edge_type(value: &str) -> Result<(), GraphError> {
    if value.is_empty() || value.len() > MAX_EDGE_TYPE_BYTES {
        return Err(refusal("edge type length is outside 1..=128 bytes"));
    }
    Ok(())
}
fn node_bytes(resolver: &StableElementResolver, node: NodeId) -> Result<Vec<u8>, GraphError> {
    let key = resolver
        .node_key(node)
        .map_err(|_| refusal("unsealed node handle"))?;
    if !matches!(key, StableElementKey::Node { .. }) {
        return Err(refusal("identity is not a node"));
    }
    resolver
        .validate_sealed_key(key)
        .map_err(|_| refusal("unsealed node identity"))?;
    let bytes = key
        .canonical_bytes()
        .map_err(|_| refusal("invalid stable node identity"))?;
    if bytes.len() > MAX_KEY_BYTES {
        return Err(refusal("node key exceeds length limit"));
    }
    Ok(bytes)
}
fn resolve_node(resolver: &StableElementResolver, bytes: &[u8]) -> Result<NodeId, GraphError> {
    let key = StableElementKey::from_canonical_bytes(bytes)
        .map_err(|_| refusal("invalid stable node identity"))?;
    resolver
        .validate_sealed_key(&key)
        .map_err(|_| refusal("foreign or unsealed node identity"))?;
    let StableElementKey::Node { local_name, .. } = key else {
        return Err(refusal("identity is not a node"));
    };
    resolver
        .node_handle_by_local_name(&local_name)
        .map_err(|_| refusal("unresolvable node identity"))
}
fn append(out: &mut Vec<u8>, bytes: &[u8]) -> Result<(), GraphError> {
    let end = out
        .len()
        .checked_add(bytes.len())
        .ok_or_else(|| refusal("size overflow"))?;
    if end > MAX_BYTES {
        return Err(refusal("encoded bytes exceed limit"));
    }
    out.try_reserve(bytes.len())
        .map_err(|_| refusal("allocation failed"))?;
    out.extend_from_slice(bytes);
    Ok(())
}
fn count(out: &mut Vec<u8>, n: usize) -> Result<(), GraphError> {
    append(
        out,
        &u32::try_from(n)
            .map_err(|_| refusal("count overflow"))?
            .to_be_bytes(),
    )
}
fn framed(out: &mut Vec<u8>, bytes: &[u8]) -> Result<(), GraphError> {
    count(out, bytes.len())?;
    append(out, bytes)
}
impl Dossier {
    /// Encode beliefs using the captured sealed identity resolver.
    ///
    /// # Errors
    /// Refuses unsealed identities, invalid lengths, bounds, or dangling ties.
    pub fn encode_canonical(
        &self,
        resolver: &StableElementResolver,
    ) -> Result<Vec<u8>, GraphError> {
        if self.resolved_nodes.len() > MAX_NODES {
            return Err(refusal("too many nodes"));
        }
        let owner = node_bytes(resolver, self.owner)?;
        let mut nodes = BTreeSet::new();
        for &node in &self.resolved_nodes {
            nodes.insert(node_bytes(resolver, node)?);
        }
        let mut edges = BTreeSet::<EdgeRow>::new();
        for (kind, ties) in &self.resolved_edges {
            valid_edge_type(kind)?;
            for &(from, to) in ties {
                if !self.resolved_nodes.contains(&from) || !self.resolved_nodes.contains(&to) {
                    return Err(refusal("edge endpoint is not a resolved node"));
                }
                if edges.len() >= MAX_EDGES {
                    return Err(refusal("too many edges"));
                }
                edges.insert((
                    kind.clone(),
                    node_bytes(resolver, from)?,
                    node_bytes(resolver, to)?,
                ));
            }
        }
        let mut output = Vec::new();
        append(&mut output, HEADER)?;
        framed(&mut output, &owner)?;
        count(&mut output, nodes.len())?;
        for node in nodes {
            framed(&mut output, &node)?;
        }
        count(&mut output, edges.len())?;
        for (kind, from, to) in edges {
            framed(&mut output, kind.as_bytes())?;
            framed(&mut output, &from)?;
            framed(&mut output, &to)?;
        }
        Ok(output)
    }

    /// Decode a canonical dossier into handles in the captured resolver.
    ///
    /// # Errors
    /// Refuses malformed, foreign, unsealed, duplicate, dangling, or noncanonical input.
    pub fn decode_canonical(
        bytes: &[u8],
        resolver: &StableElementResolver,
    ) -> Result<Self, GraphError> {
        if bytes.len() > MAX_BYTES {
            return Err(refusal("encoded bytes exceed limit"));
        }
        let mut cursor = Cursor { bytes, pos: 0 };
        if cursor.take(HEADER.len())? != HEADER {
            return Err(refusal("invalid header"));
        }
        let owner = resolve_node(resolver, cursor.framed(MAX_KEY_BYTES)?)?;
        let node_count = cursor.count(MAX_NODES)?;
        let mut nodes = BTreeSet::new();
        let mut previous_node: Option<&[u8]> = None;
        for _ in 0..node_count {
            let raw = cursor.framed(MAX_KEY_BYTES)?;
            if previous_node.is_some_and(|previous| previous >= raw) {
                return Err(refusal("nodes are not sorted and unique"));
            }
            if !nodes.insert(resolve_node(resolver, raw)?) {
                return Err(refusal("duplicate node identity"));
            }
            previous_node = Some(raw);
        }
        let edge_count = cursor.count(MAX_EDGES)?;
        let mut edges: BTreeMap<String, BTreeSet<(NodeId, NodeId)>> = BTreeMap::new();
        let mut previous_edge: Option<(&str, &[u8], &[u8])> = None;
        for _ in 0..edge_count {
            let kind = std::str::from_utf8(cursor.framed(MAX_EDGE_TYPE_BYTES)?)
                .map_err(|_| refusal("edge type is not UTF-8"))?;
            valid_edge_type(kind)?;
            let from_bytes = cursor.framed(MAX_KEY_BYTES)?;
            let to_bytes = cursor.framed(MAX_KEY_BYTES)?;
            let row = (kind, from_bytes, to_bytes);
            if previous_edge.is_some_and(|previous| previous >= row) {
                return Err(refusal("edges are not sorted and unique"));
            }
            let from = resolve_node(resolver, from_bytes)?;
            let to = resolve_node(resolver, to_bytes)?;
            if !nodes.contains(&from) || !nodes.contains(&to) {
                return Err(refusal("edge endpoint is not a resolved node"));
            }
            edges.entry(kind.to_owned()).or_default().insert((from, to));
            previous_edge = Some(row);
        }
        if cursor.pos != bytes.len() {
            return Err(refusal("trailing bytes"));
        }
        let dossier = Self {
            owner,
            resolved_nodes: nodes,
            resolved_edges: edges,
        };
        if dossier.encode_canonical(resolver)?.as_slice() != bytes {
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
        let result = self
            .bytes
            .get(self.pos..end)
            .ok_or_else(|| refusal("truncated input"))?;
        self.pos = end;
        Ok(result)
    }
    fn count(&mut self, max: usize) -> Result<usize, GraphError> {
        let mut raw = [0; 4];
        raw.copy_from_slice(self.take(4)?);
        let count =
            usize::try_from(u32::from_be_bytes(raw)).map_err(|_| refusal("length overflow"))?;
        if count > max {
            return Err(refusal("count or length exceeds limit"));
        }
        Ok(count)
    }
    fn framed(&mut self, max: usize) -> Result<&'a [u8], GraphError> {
        let len = self.count(max)?;
        self.take(len)
    }
}
