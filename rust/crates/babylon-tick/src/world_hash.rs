//! Nominal whole-world hashing above the established graph-state hash.
//!
//! The graph hash remains its own stable contract. This layer adds only
//! auxiliary state that exists today: completed weekly time, both monotonic
//! graph allocator cursors, and the versioned static phase-schedule digest.
//! It does not invent future economic registers or persistence-envelope
//! fields.
//!
//! # Canonical byte layout — version 1
//!
//! Every integer is big-endian. The encoding is the fixed domain string
//! `babylon.world-state\0`, then `u32` layout version 1, followed by:
//!
//! ```text
//! 0x01 | 32-byte graph hash
//! 0x02 | i64 completed tick
//! 0x03 | u64 next-node cursor | u64 next-hyperedge cursor
//! 0x04 | 32-byte governed phase-schedule digest
//! ```

use babylon_graph::allocator_state::AllocatorCursors;
use babylon_kernel::sha256_of;

const WORLD_HASH_LAYOUT_VERSION: u32 = 1;
const WORLD_HASH_DOMAIN: &[u8] = b"babylon.world-state\0";

/// Hash one graph hash plus the real auxiliary state that names its world.
pub(crate) fn nominal_world_hash(
    graph_hash: [u8; 32],
    completed_tick: i64,
    cursors: AllocatorCursors,
    schedule_digest: [u8; 32],
) -> Result<[u8; 32], String> {
    if completed_tick < 0 {
        return Err(format!(
            "completed tick must be non-negative, got {completed_tick}"
        ));
    }
    let mut bytes = Vec::with_capacity(116);
    bytes.extend_from_slice(WORLD_HASH_DOMAIN);
    bytes.extend_from_slice(&WORLD_HASH_LAYOUT_VERSION.to_be_bytes());
    bytes.push(0x01);
    bytes.extend_from_slice(&graph_hash);
    bytes.push(0x02);
    bytes.extend_from_slice(&completed_tick.to_be_bytes());
    bytes.push(0x03);
    bytes.extend_from_slice(&cursors.next_node.to_be_bytes());
    bytes.extend_from_slice(&cursors.next_hyperedge.to_be_bytes());
    bytes.push(0x04);
    bytes.extend_from_slice(&schedule_digest);
    Ok(sha256_of(&bytes))
}

#[cfg(test)]
mod tests {
    use super::nominal_world_hash;
    use crate::phase_order::schedule_digest;
    use babylon_graph::allocator_state::{AllocatorCursors, AllocatorState};
    use babylon_graph::hypergraph_store::HypergraphStore;
    use babylon_graph::state_hash::CanonicalState;
    use babylon_graph::substrate::GraphSubstrate;

    #[test]
    fn empty_tick_zero_world_hash_pins_the_version_one_layout() {
        let graph = HypergraphStore::new();
        let hash = nominal_world_hash(
            graph.state_hash().unwrap(),
            0,
            graph.allocator_cursors(),
            schedule_digest().unwrap(),
        )
        .unwrap();
        assert_eq!(
            crate::hex(&hash),
            "bb1fd62f9053807b13fe00a45fc7f2c032dc9d23a4d778e8c5c016bbb59c2932"
        );
    }

    #[test]
    fn allocator_history_moves_world_hash_when_live_graph_facts_match() {
        let untouched = HypergraphStore::new();
        let mut allocated = HypergraphStore::new();
        let transient = allocated.add_node("SOCIAL_CLASS").unwrap();
        allocated.remove_node(transient).unwrap();
        assert_eq!(
            untouched.state_hash().unwrap(),
            allocated.state_hash().unwrap()
        );

        let schedule = schedule_digest().unwrap();
        let a = nominal_world_hash(
            untouched.state_hash().unwrap(),
            0,
            untouched.allocator_cursors(),
            schedule,
        )
        .unwrap();
        let b = nominal_world_hash(
            allocated.state_hash().unwrap(),
            0,
            allocated.allocator_cursors(),
            schedule,
        )
        .unwrap();
        assert_ne!(a, b);
    }

    #[test]
    fn negative_completed_time_refuses_loudly() {
        let error = nominal_world_hash(
            [0; 32],
            -1,
            AllocatorCursors {
                next_node: 0,
                next_hyperedge: 0,
            },
            [0; 32],
        )
        .unwrap_err();
        assert_eq!(error, "completed tick must be non-negative, got -1");
    }
}
