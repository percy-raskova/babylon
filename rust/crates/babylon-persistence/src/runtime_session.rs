//! Bounded campaign lifecycle and durable next-period rulings over parent-owned pipes.

mod backend;

mod coordinator;

mod input;

mod protocol;

pub use protocol::*;

#[path = "runtime_session/session.rs"]
mod session;

use session::{emit, SessionBackend};
pub use session::{run_runtime_session, run_runtime_session_stdio, RuntimeSessionErrorCode};
