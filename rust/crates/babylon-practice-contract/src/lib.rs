#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

#[allow(clippy::unreadable_literal)]
mod generated;

pub use generated::*;

pub mod admission;
pub mod budget;
pub mod codec;
pub mod topology;

pub use admission::{validate_authority_pair, validate_quote_context, validate_resolve_batch};
pub use budget::{compute_budget_delta, read_action_budget, write_action_budget};
pub use codec::{
    budget_delta_digest, decode_budget_delta, decode_input_authority, decode_intent,
    decode_rejection, encode_budget_delta, encode_input_authority, encode_intent,
    encode_intent_parameters, encode_rejection, input_authority_digest, intent_digest,
    parameter_bytes_digest, rejection_for, submission_rejection_alias,
    target_selection_policy_digest,
};
pub use topology::{validate_topology, PracticeTopologyLoadCounter};
