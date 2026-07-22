//! Error types for hypergraph operations.

use thiserror::Error;

/// Error raised when a node operation fails.
#[derive(Debug, Clone, Error, PartialEq)]
pub enum NodeError {
    /// The node ID was not found in the hypergraph.
    #[error("node {node_id} does not exist")]
    NotFound { node_id: String },
}

/// Error raised when a membership operation fails
/// (`Hypergraph::remove_node_from_edge`).
///
/// XGI raises `XGIError` for all three branches, each with a distinct
/// message (probed v0.10.2); the core returns a dedicated variant per
/// branch so callers discriminate without string-matching. The PyO3
/// binding translates `Err` -> raise, reproducing XGI's exact messages
/// (D2 error-channel class).
#[derive(Debug, Clone, Error, PartialEq)]
pub enum MembershipError {
    /// The edge ID was not found in the hypergraph.
    #[error("edge {edge_id} does not exist")]
    EdgeNotFound { edge_id: String },
    /// The node ID was not found in the hypergraph.
    #[error("node {node_id} does not exist")]
    NodeNotFound { node_id: String },
    /// Both exist, but the node is not a member of the edge.
    #[error("node {node_id} is not a member of edge {edge_id}")]
    NotAMember { node_id: String, edge_id: String },
}

/// Error raised when an edge operation fails.
#[derive(Debug, Clone, Error, PartialEq)]
pub enum EdgeError {
    /// The edge ID was not found in the hypergraph.
    #[error("edge {edge_id} does not exist")]
    NotFound { edge_id: String },
    /// The edge ID already exists (duplicate on add_edge).
    ///
    /// XGI warns and no-ops here (`warn(f"uid {idx} already exists, ...")`);
    /// the Rust core returns an error instead. The PyO3 binding MUST
    /// translate this back into a `UserWarning` + `None` return for XGI
    /// conformance. Divergence D2.
    #[error("edge {edge_id} already exists")]
    AlreadyExists { edge_id: String },
}
