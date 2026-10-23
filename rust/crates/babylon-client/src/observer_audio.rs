//! Music and restrained feedback from viewer interactions and acknowledged commits.
//! Audio never participates in campaign identity or mechanics.

mod catalog;

#[path = "observer_audio/settings.rs"]
mod settings;

#[allow(unused_imports)]
use settings::{
    desired_deck, effect, feedback, gameplay_audio, mix, opening_fanfare, register_audio, setup,
    start_music, AudioBank, EffectLifetime, MusicDeck, ProductionFanfare, TITLE_GAIN,
};
pub use settings::{ObserverAudioPlugin, ObserverAudioSettings};

#[allow(unused_imports)]
use crate::map::SelectedCounty;
#[allow(unused_imports)]
use crate::observer::{ObserverSession, SessionPhase};
#[allow(unused_imports)]
use crate::observer_io::ObserverSet;
#[allow(unused_imports)]
use crate::observer_opening::{OpeningPresentation, OpeningStage};
#[allow(unused_imports)]
use crate::observer_ui::ObserverCommand;
#[allow(unused_imports)]
use bevy::asset::io::embedded::EmbeddedAssetRegistry;
#[allow(unused_imports)]
use bevy::audio::{AudioSinkPlayback, Volume};
#[allow(unused_imports)]
use catalog::{DEFAULT_TRACK_INDEX, MUSIC_TRACKS, TITLE_TRACK_INDEX};
#[allow(unused_imports)]
use std::path::{Path, PathBuf};

#[allow(unused_imports)]
use bevy::prelude::*;
