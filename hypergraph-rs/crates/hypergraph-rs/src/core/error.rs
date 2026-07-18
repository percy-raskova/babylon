//! Error types for hypergraph operations.

use thiserror::Error;

/// Error raised when a node operation fails.
#[derive(Debug, Clone, Error, PartialEq)]
pub enum NodeError {
    /// The node ID was not found in the hypergraph.
    #[error("node {node_id} does not exist")]
    NotFound { node_id: String },
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
