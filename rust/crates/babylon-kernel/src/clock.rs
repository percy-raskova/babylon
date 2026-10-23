//! Fixed simulation interval and the evidence record session identifier.

mod duration;

pub use duration::{CampaignDuration, InvalidCampaignDuration};

#[path = "clock/tick_clock.rs"]
mod tick_clock;

pub use tick_clock::{EmptySessionId, SessionId, DAYS_PER_TICK, TICKS_PER_YEAR, WEEKS_PER_TICK};
