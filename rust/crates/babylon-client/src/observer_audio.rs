//! Music and restrained feedback from viewer interactions and acknowledged commits.
//! Audio never participates in campaign identity or mechanics.

mod catalog;

#[path = "observer_audio/settings.rs"]
mod settings;

pub use settings::{ObserverAudioPlugin, ObserverAudioSettings};
