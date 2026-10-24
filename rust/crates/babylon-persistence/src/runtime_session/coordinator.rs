//! One pipe owner serializes lifecycle changes, durable ACKs and Archive reports.

mod active;

#[cfg(test)]
mod tests;

#[path = "coordinator/session.rs"]
mod session;

use session::COMPLETION_CHECK;
pub(super) use session::{serve, ArchiveControl, SessionEvent};
#[cfg(test)]
use session::{ArchiveEventSink, Coordinator, Factories};

#[cfg(test)]
use super::input::{InputEvent, SessionInput};
#[cfg(test)]
use super::{
    RuntimeSessionErrorCode, RuntimeSessionRequest, RuntimeSessionResponse, RuntimeSessionScope,
    RuntimeSessionTarget, SessionBackend, RUNTIME_SESSION_PROTOCOL_VERSION,
};
#[cfg(test)]
use crate::archive_driver::ArchiveDriverEvent;
#[cfg(test)]
use active::Active;
#[cfg(test)]
use std::io::{BufRead, Write};
#[cfg(test)]
use std::sync::mpsc::{self, Receiver};
#[cfg(test)]
use std::time::Duration;
