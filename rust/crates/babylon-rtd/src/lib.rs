#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

// Generated literals retain the contract source spelling. The generator owns
// their formatting, so this narrow exemption avoids hand-editing its output.
mod canonical;
#[allow(clippy::unreadable_literal)]
mod generated;
mod validate;

pub use canonical::{
    canonical_draft_bytes, parse_vector_corpus, projection_hash, seal_draft, RtdVectorCaseV1,
};
pub use generated::*;
pub use validate::{append_bounded, parse_draft_json, validate_draft, RtdError};
