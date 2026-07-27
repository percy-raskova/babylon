//! Babylon Archive terminal client core (the raster cutover, ADR150).
//!
//! Rust owns the terminal event loop; Python remains the single writer and
//! serves frozen view-models as JSON strings across the [`host::Host`] seam.

pub mod app;
pub mod config;
pub mod host;
