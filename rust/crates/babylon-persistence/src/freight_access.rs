//! Regional truck-routing reference and separately captured economic corridors.
mod access;
mod reference;
#[cfg(test)]
mod tests;

pub use access::{distance_band, Access, AccessDirection, AccessError, AccessRow, Corridor};
pub use reference::{AirportPoint, Reference};
