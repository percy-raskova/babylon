//! The Python↔Rust seam: every read crosses as a JSON string (design §4).

/// Host surface the Python side implements (M0: lobby only; grows per milestone).
pub trait Host {
    /// The lobby campaign catalog as a JSON array string.
    fn lobby_catalog_json(&self) -> String;
}
