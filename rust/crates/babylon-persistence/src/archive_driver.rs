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

#[allow(unused_imports)]
use driver::COMMAND_CAPACITY;
pub use driver::{
    ArchiveDriver, ArchiveDriverEvent, ArchiveDriverFailure, ArchiveDriverRequestError,
    ArchiveDriverStartError,
};

#[allow(unused_imports)]
use crate::{identity::CampaignId, ArchiveWorkerCancellation, SemanticArchiveError};
#[allow(unused_imports)]
use postgres::Config;
#[allow(unused_imports)]
use std::sync::mpsc::{self, SyncSender, TrySendError};
#[allow(unused_imports)]
use std::thread::{self, JoinHandle};
