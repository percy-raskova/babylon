//! `babylon-client`'s library surface — the palette and engine-link modules
//! that both the binary (`main.rs`) and the integration tests
//! (`tests/engine_link.rs`) consume. The Bevy `App` itself lives in
//! `main.rs`; this crate is otherwise a thin scaffold, not a reusable
//! client-engine API.

pub mod engine_link;
pub mod palette;
