//! `babylon-client`'s library surface — the atlas, tessellate, map,
//! palette and engine-link modules that both the binary (`main.rs`) and
//! the integration tests (`tests/engine_link.rs`, `tests/map_mesh.rs`)
//! consume. The Bevy `App` itself lives in `main.rs`; this crate is
//! otherwise a thin scaffold, not a reusable client-engine API.

pub mod atlas;
pub mod engine_link;
pub mod map;
pub mod palette;
pub mod tessellate;
