// Schema literals retain the language-neutral contract spelling.
mod canonical;
#[allow(
    clippy::unreadable_literal,
    reason = "the literal is an authored byte pattern"
)]
mod schema;
mod validate;

pub use canonical::{
    canonical_draft_bytes, parse_vector_corpus, projection_hash, seal_draft, RtdVectorCase,
};
pub use schema::*;
pub use validate::{append_bounded, parse_draft_json, validate_draft, RtdError};
