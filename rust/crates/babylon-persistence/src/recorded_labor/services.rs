//! Actual staged service deliveries, use and expiry.
mod close;
#[cfg(test)]
mod tests;

pub(super) use close::{finish, handoff};
