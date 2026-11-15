//! One-way inspection copy of a material campaign from an admitted predecessor schema.
mod rows;
mod source;
mod transport;

pub use transport::{copy_campaign, InspectionCopy, InspectionCopyError};
