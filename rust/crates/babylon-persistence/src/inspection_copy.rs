//! One-way inspection copy of a material campaign from the exact pre-PER-293 schema.
mod rows;
mod source;
mod transport;

pub use transport::{copy_campaign, InspectionCopy, InspectionCopyError};
