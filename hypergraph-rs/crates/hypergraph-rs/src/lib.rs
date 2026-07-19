//! # hypergraph-rs
//!
//! A Rust port of XGI (the Python hypergraph library), built as a genuine
//! rustworkx-core plugin. The hypergraph IS a
//! [`rustworkx_core::petgraph::stable_graph::StableDiGraph`] with two node
//! kinds (`Agent` and `Hyperedge`) connected by `MembershipEdge` edges.

pub mod core;

pub use core::dihypergraph::DiHypergraph;
pub use core::error::{EdgeError, MembershipError, NodeError};
pub use core::hypergraph::Hypergraph;
pub use core::kinds::{Direction, MembershipEdge, NodeKind};
