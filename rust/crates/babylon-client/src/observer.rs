//! Immutable observation context and transport for one durable campaign.
//! UI interactions schedule reads or one empty-action tick; they never own
//! a simulation session or mutate material state.

mod lifecycle;

#[path = "observer/session.rs"]
mod session;

pub use session::{ObservationContext, ObserverSession, Perspective, SessionPhase};
