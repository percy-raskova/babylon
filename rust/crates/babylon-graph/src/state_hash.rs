//! The graph STATE hash — Constitution III.7's "every tick produces a
//! deterministic hash", for the substrate half.
//!
//! [`babylon_kernel::ContentDigest`] fingerprints what the engine was *told*
//! (defines + rules). This fingerprints what the engine *did*: the graph
//! after a tick. Two runs of the same content over the same starting state
//! must produce the same bytes here, and any real change to the world must
//! change them.
//!
//! # The canonical byte layout — normative
//!
//! This is a **cross-language contract**, so the layout is specified rather
//! than implied by one implementation (the rewrite test: another engine in
//! another language must be able to reproduce these bytes from this
//! description alone). Every integer is **big-endian**. Every string is
//! length-prefixed `u32` + raw UTF-8 bytes, never NUL-terminated.
//!
//! ```text
//! 0x01 ‖ u32 count ‖ per node,      ascending id:   u64 id ‖ str type
//! 0x02 ‖ u32 count ‖ per attribute, ascending (id, name):
//!                                    u64 id ‖ str name ‖ u64 value-bits
//! 0x03 ‖ u32 count ‖ per edge,      ascending (type, from, to):
//!                                    str type ‖ u64 from ‖ u64 to ‖ u64 strength-bits
//! 0x04 ‖ u32 count ‖ per hyperedge, ascending id:
//!                                    u64 id ‖ str type ‖ u32 member-count
//!                                           ‖ u64 member id, ascending
//! ```
//!
//! **Section tags are not decoration.** Without them a graph with one node
//! and no edges could serialize identically to one with no nodes and one
//! edge under some count arrangement; the tag makes each section's identity
//! explicit.
//!
//! **Sorting is the whole determinism argument.** `MemoryGraph` stores in
//! `HashMap`s, whose iteration order varies per process. Every section sorts
//! before writing, so storage order is unobservable here exactly as it is
//! unobservable through the trait's ranged accessors.
//!
//! # Floats
//!
//! Attribute values and edge strengths are `f64`, and two IEEE-754 facts
//! would otherwise break the contract:
//!
//! - **`-0.0` and `+0.0` compare equal but do not serialize equal.** A sign
//!   bit arriving from upstream arithmetic (`-1.0 * 0.0`) would change the
//!   hash without changing the world. They are canonicalized to `+0.0`.
//! - **NaN is not a value.** It is refused loudly rather than hashed, so a
//!   non-finite can never enter the tick hash and make a run irreproducible.
//!   The write path already refuses non-finites; this is the second gate,
//!   because a hash that silently accepted one would launder it.
//!
//! Finite values are hashed by `to_bits()`, which is exact — no formatting,
//! no rounding, no locale.

use crate::substrate::{GraphError, HyperedgeId, NodeId};
use babylon_kernel::sha256_of;

const TAG_NODES: u8 = 0x01;
const TAG_ATTRIBUTES: u8 = 0x02;
const TAG_EDGES: u8 = 0x03;
const TAG_HYPEREDGES: u8 = 0x04;

/// Accumulates the canonical encoding described in the module docs.
///
/// Sections must be written in tag order; the encoder does not reorder them,
/// because a caller that emitted them out of order has a bug the hash should
/// expose rather than paper over.
#[derive(Debug, Default)]
pub struct StateEncoder {
    bytes: Vec<u8>,
}

impl StateEncoder {
    /// A new, empty encoding.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    fn push_str(&mut self, value: &str) -> Result<(), GraphError> {
        let len = u32::try_from(value.len()).map_err(|_| GraphError {
            message: format!(
                "string of {} bytes exceeds the u32 length prefix",
                value.len()
            ),
        })?;
        self.bytes.extend_from_slice(&len.to_be_bytes());
        self.bytes.extend_from_slice(value.as_bytes());
        Ok(())
    }

    fn push_count(&mut self, tag: u8, count: usize) -> Result<(), GraphError> {
        let count = u32::try_from(count).map_err(|_| GraphError {
            message: format!("section {tag:#04x} holds {count} entries, past the u32 count"),
        })?;
        self.bytes.push(tag);
        self.bytes.extend_from_slice(&count.to_be_bytes());
        Ok(())
    }

    /// Canonicalize a stored float and append its bits.
    ///
    /// # Errors
    /// Returns [`GraphError`] on a non-finite value — it must never reach the
    /// tick hash.
    fn push_f64(&mut self, value: f64, what: &str) -> Result<(), GraphError> {
        if !value.is_finite() {
            return Err(GraphError {
                message: format!(
                    "{what} is {value} — a non-finite value cannot enter the state hash, \
                     because a run that hashed one could not be reproduced"
                ),
            });
        }
        // `-0.0 == 0.0` is true, so this normalizes the sign bit without a
        // branch on `is_sign_negative`.
        let canonical = if value == 0.0 { 0.0_f64 } else { value };
        self.bytes
            .extend_from_slice(&canonical.to_bits().to_be_bytes());
        Ok(())
    }

    /// Section `0x01`. `nodes` must already be sorted ascending by id.
    ///
    /// # Errors
    /// Returns [`GraphError`] if a count or string length overflows its prefix.
    pub fn write_nodes(&mut self, nodes: &[(NodeId, String)]) -> Result<(), GraphError> {
        self.push_count(TAG_NODES, nodes.len())?;
        for (id, node_type) in nodes {
            self.bytes.extend_from_slice(&id.0.to_be_bytes());
            self.push_str(node_type)?;
        }
        Ok(())
    }

    /// Section `0x02`. `attributes` must already be sorted ascending by
    /// `(id, name)`.
    ///
    /// # Errors
    /// Returns [`GraphError`] on overflow or a non-finite value.
    pub fn write_attributes(
        &mut self,
        attributes: &[(NodeId, String, f64)],
    ) -> Result<(), GraphError> {
        self.push_count(TAG_ATTRIBUTES, attributes.len())?;
        for (id, name, value) in attributes {
            self.bytes.extend_from_slice(&id.0.to_be_bytes());
            self.push_str(name)?;
            self.push_f64(*value, &format!("attribute {name} on {id:?}"))?;
        }
        Ok(())
    }

    /// Section `0x03`. `edges` must already be sorted ascending by
    /// `(type, from, to)`.
    ///
    /// # Errors
    /// Returns [`GraphError`] on overflow or a non-finite strength.
    pub fn write_edges(
        &mut self,
        edges: &[(String, NodeId, NodeId, f64)],
    ) -> Result<(), GraphError> {
        self.push_count(TAG_EDGES, edges.len())?;
        for (edge_type, from, to, strength) in edges {
            self.push_str(edge_type)?;
            self.bytes.extend_from_slice(&from.0.to_be_bytes());
            self.bytes.extend_from_slice(&to.0.to_be_bytes());
            self.push_f64(*strength, &format!("strength of {edge_type} edge"))?;
        }
        Ok(())
    }

    /// Section `0x04`. `hyperedges` must already be sorted ascending by id,
    /// each member list ascending.
    ///
    /// # Errors
    /// Returns [`GraphError`] if a count or string length overflows.
    pub fn write_hyperedges(
        &mut self,
        hyperedges: &[(HyperedgeId, String, Vec<NodeId>)],
    ) -> Result<(), GraphError> {
        self.push_count(TAG_HYPEREDGES, hyperedges.len())?;
        for (id, hyperedge_type, members) in hyperedges {
            self.bytes.extend_from_slice(&id.0.to_be_bytes());
            self.push_str(hyperedge_type)?;
            let count = u32::try_from(members.len()).map_err(|_| GraphError {
                message: format!("hyperedge {id:?} holds {} members", members.len()),
            })?;
            self.bytes.extend_from_slice(&count.to_be_bytes());
            for member in members {
                self.bytes.extend_from_slice(&member.0.to_be_bytes());
            }
        }
        Ok(())
    }

    /// The canonical bytes, for a differential when two hashes disagree.
    ///
    /// A bare hash says only *that* two states differ; the bytes say where.
    #[must_use]
    pub fn as_bytes(&self) -> &[u8] {
        &self.bytes
    }

    /// SHA-256 over the canonical encoding.
    #[must_use]
    pub fn finish(&self) -> [u8; 32] {
        sha256_of(&self.bytes)
    }
}

#[cfg(test)]
mod tests {
    use super::StateEncoder;
    use crate::substrate::{HyperedgeId, NodeId};

    fn encoder_with_one_attribute(value: f64) -> [u8; 32] {
        let mut enc = StateEncoder::new();
        enc.write_nodes(&[(NodeId(1), "social_class".to_owned())])
            .unwrap();
        enc.write_attributes(&[(NodeId(1), "wealth".to_owned(), value)])
            .unwrap();
        enc.write_edges(&[]).unwrap();
        enc.write_hyperedges(&[]).unwrap();
        enc.finish()
    }

    #[test]
    fn the_same_state_hashes_identically() {
        assert_eq!(
            encoder_with_one_attribute(42.0),
            encoder_with_one_attribute(42.0)
        );
    }

    #[test]
    fn a_changed_value_changes_the_hash() {
        assert_ne!(
            encoder_with_one_attribute(42.0),
            encoder_with_one_attribute(42.5)
        );
    }

    #[test]
    fn negative_zero_hashes_as_positive_zero() {
        // Otherwise a sign bit from upstream arithmetic (-1.0 * 0.0) would
        // change the tick hash without changing the world.
        assert!(
            (-0.0_f64).is_sign_negative(),
            "fixture must carry the sign bit"
        );
        assert_eq!(
            encoder_with_one_attribute(-0.0),
            encoder_with_one_attribute(0.0)
        );
    }

    #[test]
    fn a_non_finite_value_is_refused_never_hashed() {
        let mut enc = StateEncoder::new();
        enc.write_nodes(&[(NodeId(1), "social_class".to_owned())])
            .unwrap();
        let err = enc
            .write_attributes(&[(NodeId(1), "wealth".to_owned(), f64::NAN)])
            .unwrap_err();
        assert!(
            err.message.contains("could not be reproduced"),
            "{}",
            err.message
        );
    }

    #[test]
    fn section_tags_keep_shapes_distinct() {
        // One node and no edges must not collide with no nodes and one edge.
        let mut a = StateEncoder::new();
        a.write_nodes(&[(NodeId(1), "x".to_owned())]).unwrap();
        a.write_attributes(&[]).unwrap();
        a.write_edges(&[]).unwrap();
        a.write_hyperedges(&[]).unwrap();

        let mut b = StateEncoder::new();
        b.write_nodes(&[]).unwrap();
        b.write_attributes(&[]).unwrap();
        b.write_edges(&[("x".to_owned(), NodeId(1), NodeId(1), 1.0)])
            .unwrap();
        b.write_hyperedges(&[]).unwrap();

        assert_ne!(a.finish(), b.finish());
    }

    #[test]
    fn a_hyperedge_of_the_same_members_under_a_different_id_differs() {
        // Hyperedge identity is its own, not a function of its membership.
        let members = vec![NodeId(1), NodeId(2)];
        let mut a = StateEncoder::new();
        a.write_hyperedges(&[(HyperedgeId(0), "sector".to_owned(), members.clone())])
            .unwrap();
        let mut b = StateEncoder::new();
        b.write_hyperedges(&[(HyperedgeId(1), "sector".to_owned(), members)])
            .unwrap();
        assert_ne!(a.finish(), b.finish());
    }

    #[test]
    fn the_encoding_is_inspectable_for_a_differential() {
        // A bare hash says only THAT two states differ; the bytes say where.
        let mut enc = StateEncoder::new();
        enc.write_nodes(&[(NodeId(1), "social_class".to_owned())])
            .unwrap();
        let bytes = enc.as_bytes();
        assert_eq!(bytes[0], 0x01, "section tag leads");
        assert_eq!(
            &bytes[1..5],
            &1_u32.to_be_bytes(),
            "then a big-endian count"
        );
        assert_eq!(&bytes[5..13], &1_u64.to_be_bytes(), "then the node id");
    }
}
