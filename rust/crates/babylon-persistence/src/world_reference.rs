//! Pinned, disjoint world reporting scopes and explicitly qualified source measures.
//!
//! Population projections and annual goods-trade dollars create no labor supply,
//! inventories, productive capacity, purchasing power or automatic demand.

mod model;

mod parse;

#[cfg(test)]
mod tests;

pub use model::*;

#[path = "world_reference/artifact.rs"]
mod artifact;

use artifact::MEMBER_COUNT;
pub use artifact::{world_reference, WorldReference, WorldReferenceError, WorldSourceDigests};
