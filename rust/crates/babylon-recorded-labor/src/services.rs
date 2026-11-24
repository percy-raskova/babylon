//! Actual staged service deliveries, use and expiry.
mod close;

pub use close::{finish, handoff};

#[cfg(test)]
mod tests;
