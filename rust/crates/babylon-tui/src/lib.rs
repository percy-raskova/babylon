//! Babylon Archive terminal client core (the raster cutover, ADR150).
//!
//! Rust owns the terminal event loop; Python remains the single writer and
//! serves frozen view-models as JSON strings across the [`host::Host`] seam.

pub mod app;
pub mod config;
pub mod host;
pub mod layout_registry;
pub mod md_style;
#[cfg(feature = "raster")]
pub mod raster_bridge;
pub mod router;
#[cfg(feature = "raster")]
pub mod scene3d;
pub mod theme;
pub mod views;
pub mod wiki_render;
