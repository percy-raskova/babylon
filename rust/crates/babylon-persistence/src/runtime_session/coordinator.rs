//! One pipe owner serializes lifecycle changes, durable ACKs and Archive reports.

mod active;

#[cfg(test)]
mod tests;

#[path = "coordinator/session.rs"]
mod session;

#[allow(unused_imports)]
pub(super) use session::{serve, ArchiveControl, SessionEvent};
#[allow(unused_imports)]
use session::{
    ArchiveEventSink, Coordinator, Factories, COMPLETION_CHECK, EVENT_CAPACITY, SHUTDOWN_GRACE,
};

#[allow(unused_imports)]
use super::input::{InputEvent, SessionInput};
#[allow(unused_imports)]
use super::{
    emit, RuntimeSessionErrorCode, RuntimeSessionRequest, RuntimeSessionResponse,
    RuntimeSessionScope, RuntimeSessionTarget, SessionBackend, RUNTIME_SESSION_PROTOCOL_VERSION,
};
#[allow(unused_imports)]
use crate::archive_driver::{ArchiveDriver, ArchiveDriverEvent, ArchiveDriverRequestError};
#[allow(unused_imports)]
use crate::identity::CampaignId;
#[allow(unused_imports)]
use active::Active;
#[allow(unused_imports)]
use std::io::{BufRead, Write};
#[allow(unused_imports)]
use std::sync::mpsc::{self, Receiver, SyncSender};
#[allow(unused_imports)]
use std::time::Duration;
