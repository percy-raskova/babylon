//! Allocator state that is real world state but not graph content.
//!
//! [`crate::state_hash::CanonicalState`] deliberately hashes live graph
//! facts only. Monotonic identity cursors are different: removing an object
//! does not rewind them, and the next minted identity affects every later
//! reference. Tick-level world hashing therefore consumes this sibling
//! contract without changing the established graph-state byte layout.

/// The next identities each monotonic graph allocator will mint.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct AllocatorCursors {
    /// The next [`crate::substrate::NodeId`] value.
    pub next_node: u64,
    /// The next [`crate::substrate::HyperedgeId`] value.
    pub next_hyperedge: u64,
}

/// Read-only access to identity allocator state for transaction and hash
/// boundaries.
pub trait AllocatorState {
    /// Return both next-id cursors without advancing either allocator.
    fn allocator_cursors(&self) -> AllocatorCursors;
}
