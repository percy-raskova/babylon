//! Checked immutable publication payload with its required emission witness.

#[cfg(test)]
mod tests;

#[path = "record/revision.rs"]
mod revision;

pub(super) use revision::{
    is_link, parse_page_key, CheckedRevision, GrantDependency, RevisionRecord,
};
