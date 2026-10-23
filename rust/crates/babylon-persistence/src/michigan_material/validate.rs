//! Admission checks consume captured authority only, including on restart.
mod physical;

#[path = "validate/rules.rs"]
mod rules;

pub(super) use rules::{apply, canonicalize, content, interventions};
use rules::{county, digest};
