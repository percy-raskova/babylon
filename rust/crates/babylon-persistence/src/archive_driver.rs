//! Archive-only notification listener and canonical ordered worker driver.
//!
//! Notifications are empty, lossy wake hints. Startup and reconnect first commit
//! LISTEN and then reconcile durable state. No SQL runs merely because an idle
//! notification wait timed out. The owner must never join an unfinished driver:
//! synchronous authentication and socket teardown are not a hard deadline API.

mod run;

#[cfg(test)]
mod tests;

mod driver;

pub use driver::{
    ArchiveDriver, ArchiveDriverEvent, ArchiveDriverFailure, ArchiveDriverRequestError,
    ArchiveDriverStartError,
};
