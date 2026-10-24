//! Captured source context with native geographic scope and explicit missingness.

#[cfg(test)]
mod tests;

#[path = "context/rows.rs"]
mod rows;

pub(crate) use rows::attach_observed_context;
