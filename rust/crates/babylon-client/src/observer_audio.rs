//! Music and restrained feedback from viewer interactions and acknowledged commits.
//! Audio never participates in campaign identity or mechanics.

use bevy::asset::io::embedded::EmbeddedAssetRegistry;
use bevy::audio::{AudioSinkPlayback, Volume};
use bevy::prelude::*;
use std::path::{Path, PathBuf};

mod catalog;

use catalog::{DEFAULT_TRACK_INDEX, MUSIC_TRACKS};

use crate::map::SelectedCounty;
use crate::observer::{ObserverSession, SessionPhase};
use crate::observer_io::ObserverSet;
use crate::observer_ui::ObserverCommand;

#[derive(Resource)]
pub struct ObserverAudioSettings {
    pub music_volume: f32,
    pub effects_volume: f32,
    pub track: usize,
}
impl Default for ObserverAudioSettings {
    fn default() -> Self {
        Self {
            music_volume: 0.25,
            effects_volume: 0.4,
            track: DEFAULT_TRACK_INDEX,
        }
    }
}

impl ObserverAudioSettings {
    /// Advance through the authored soundtrack independently of campaign state.
    pub fn next_track(&mut self) {
        self.track = (self.track + 1) % MUSIC_TRACKS.len();
    }

    #[must_use]
    pub fn track_title(&self) -> &'static str {
        MUSIC_TRACKS
            .get(self.track)
            .map_or("Unavailable", |track| track.title)
    }

    #[must_use]
    pub const fn track_count() -> usize {
        MUSIC_TRACKS.len()
    }
}

#[derive(Resource)]
struct AudioBank {
    select: Handle<AudioSource>,
    tab: Handle<AudioSource>,
    open: Handle<AudioSource>,
    back: Handle<AudioSource>,
    tick: Handle<AudioSource>,
    fault: Handle<AudioSource>,
}
#[derive(Component)]
struct MusicDeck(usize);
#[derive(Component)]
struct EffectLifetime(Timer);

fn start_music(commands: &mut Commands, server: &AssetServer, settings: &ObserverAudioSettings) {
    let Some(track) = MUSIC_TRACKS.get(settings.track) else {
        error!(
            track = settings.track,
            "Music selection is outside the embedded soundtrack"
        );
        return;
    };
    commands.spawn((
        AudioPlayer::new(server.load(format!("embedded://{}", track.path))),
        PlaybackSettings {
            volume: Volume::SILENT,
            ..PlaybackSettings::ONCE
        },
        MusicDeck(settings.track),
    ));
}

fn setup(mut commands: Commands, server: Res<AssetServer>, settings: Res<ObserverAudioSettings>) {
    start_music(&mut commands, &server, &settings);
    commands.insert_resource(AudioBank {
        select: server.load("embedded://sfx/ui/ui_select.ogg"),
        tab: server.load("embedded://sfx/ui/ui_tab.ogg"),
        open: server.load("embedded://sfx/ui/ui_open.ogg"),
        back: server.load("embedded://sfx/ui/ui_back.ogg"),
        tick: server.load("embedded://sfx/state/tick_advance.ogg"),
        fault: server.load("embedded://sfx/state/state_fault.ogg"),
    });
}

fn effect(commands: &mut Commands, source: Handle<AudioSource>, volume: f32) {
    if volume <= 0.0 {
        return;
    }
    commands.spawn((
        AudioPlayer::new(source),
        PlaybackSettings {
            volume: Volume::Linear(volume),
            ..PlaybackSettings::DESPAWN
        },
        EffectLifetime(Timer::from_seconds(8.0, TimerMode::Once)),
    ));
}

fn feedback(
    mut commands: Commands,
    mut input: MessageReader<ObserverCommand>,
    bank: Res<AudioBank>,
    settings: Res<ObserverAudioSettings>,
    state: Res<ObserverSession>,
    selection: Res<SelectedCounty>,
    mut last: Local<Option<(u64, SessionPhase, Option<usize>)>>,
) {
    let mut cue = None;
    for input in input.read() {
        cue = Some(match input {
            ObserverCommand::Lens(_)
            | ObserverCommand::MaterialLens(_)
            | ObserverCommand::CycleGood(_)
            | ObserverCommand::Perspective => bank.tab.clone(),
            ObserverCommand::Archive | ObserverCommand::Menu => bank.open.clone(),
            ObserverCommand::PreviousPeriod | ObserverCommand::Live => bank.back.clone(),
            _ => bank.select.clone(),
        });
    }
    if let Some((tick, phase, selected)) = *last {
        if selection.0 != selected {
            cue = Some(bank.select.clone());
        }
        if state.durable_tick > tick {
            cue = Some(bank.tick.clone());
        }
        if state.phase == SessionPhase::Failed && phase != SessionPhase::Failed {
            cue = Some(bank.fault.clone());
        }
    }
    *last = Some((state.durable_tick, state.phase, selection.0));
    if let Some(cue) = cue {
        effect(&mut commands, cue, settings.effects_volume);
    }
}

fn mix(
    time: Res<Time>,
    mut settings: ResMut<ObserverAudioSettings>,
    deck: Single<(Entity, &MusicDeck, Option<&mut AudioSink>)>,
    mut effects: Query<(Entity, &mut EffectLifetime)>,
    server: Res<AssetServer>,
    mut commands: Commands,
) {
    let (entity, playing, sink) = deck.into_inner();
    let finished = sink.as_ref().is_some_and(|sink| sink.empty());
    if playing.0 != settings.track || finished {
        // A manual Next wins if the old recording finishes in the same frame.
        if playing.0 == settings.track {
            settings.next_track();
        }
        if let Some(sink) = sink {
            sink.stop();
        }
        commands.entity(entity).despawn();
        start_music(&mut commands, &server, &settings);
    } else if let Some(mut sink) = sink {
        let target = settings.music_volume;
        let current = sink.volume().to_linear();
        let step = time.delta_secs() * 0.35;
        let volume = if current < target {
            (current + step).min(target)
        } else {
            (current - step).max(target)
        };
        sink.set_volume(Volume::Linear(volume));
    }
    for (entity, mut ttl) in &mut effects {
        ttl.0.tick(time.delta());
        if ttl.0.is_finished() {
            commands.entity(entity).despawn();
        }
    }
}

fn register_audio(registry: &EmbeddedAssetRegistry, name: &str, bytes: &'static [u8]) {
    registry.insert_asset(
        PathBuf::from(concat!(env!("CARGO_MANIFEST_DIR"), "/../../../assets")).join(name),
        Path::new(name),
        bytes,
    );
}

pub struct ObserverAudioPlugin;
impl Plugin for ObserverAudioPlugin {
    fn build(&self, app: &mut App) {
        let registry = app.world().resource::<EmbeddedAssetRegistry>();
        for track in MUSIC_TRACKS {
            register_audio(registry, track.path, track.bytes);
        }
        for (name, bytes) in [
            (
                "sfx/ui/ui_select.ogg",
                include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/../../../assets/sfx/ui/ui_select.ogg"
                )) as &[u8],
            ),
            (
                "sfx/ui/ui_tab.ogg",
                include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/../../../assets/sfx/ui/ui_tab.ogg"
                )) as &[u8],
            ),
            (
                "sfx/ui/ui_open.ogg",
                include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/../../../assets/sfx/ui/ui_open.ogg"
                )) as &[u8],
            ),
            (
                "sfx/ui/ui_back.ogg",
                include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/../../../assets/sfx/ui/ui_back.ogg"
                )) as &[u8],
            ),
            (
                "sfx/state/tick_advance.ogg",
                include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/../../../assets/sfx/state/tick_advance.ogg"
                )) as &[u8],
            ),
            (
                "sfx/state/state_fault.ogg",
                include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/../../../assets/sfx/state/state_fault.ogg"
                )) as &[u8],
            ),
        ] {
            register_audio(registry, name, bytes);
        }
        app.init_resource::<ObserverAudioSettings>()
            .add_systems(Startup, setup)
            .add_systems(Update, (feedback, mix).chain().after(ObserverSet::Install));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::asset::{AssetApp, AssetPlugin};
    use bevy::audio::PlaybackMode;
    use bevy::ecs::system::RunSystemOnce;
    use rodio::Source;
    use std::time::Duration;

    fn music_app() -> App {
        let mut app = App::new();
        app.add_plugins((MinimalPlugins, AssetPlugin::default()))
            .init_asset::<AudioSource>()
            .init_resource::<ObserverAudioSettings>()
            .add_systems(Startup, setup)
            .add_systems(Update, mix);
        app.finish();
        app.cleanup();
        app.update();
        app
    }

    #[test]
    fn music_starts_only_one_finite_track() {
        let mut app = music_app();
        let mut decks = app
            .world_mut()
            .query::<(&MusicDeck, &PlaybackSettings, &AudioPlayer)>();
        let (deck, settings, player) = decks.single(app.world()).expect("one music decoder");
        assert_eq!(deck.0, 0);
        assert!(matches!(settings.mode, PlaybackMode::Once));
        assert_eq!(
            player.0.path().unwrap().path(),
            Path::new("music/ambient/01_history_breathing.ogg")
        );
    }

    #[test]
    fn music_completion_advances_once_and_replaces_the_finished_deck() {
        let mut app = music_app();
        let mut decks = app.world_mut().query::<(Entity, &MusicDeck)>();
        let finished = decks
            .iter(app.world())
            .find_map(|(entity, deck)| (deck.0 == 0).then_some(entity))
            .unwrap();
        let (sink, _samples) = rodio::Sink::new_idle();
        app.world_mut()
            .entity_mut(finished)
            .insert(AudioSink::new(sink));
        app.update();
        assert_eq!(app.world().resource::<ObserverAudioSettings>().track, 1);
        let (next, deck) = decks.single(app.world()).expect("one replacement decoder");
        assert_eq!(deck.0, 1);
        assert_ne!(next, finished);
        assert!(!app.world().entities().contains(finished));
        app.update();
        assert_eq!(app.world().resource::<ObserverAudioSettings>().track, 1);
        assert_eq!(decks.single(app.world()).unwrap().0, next);
        // Next while muted wins over completion observed in the same frame.
        {
            let mut settings = app.world_mut().resource_mut::<ObserverAudioSettings>();
            settings.track = 2;
            settings.music_volume = 0.0;
        }
        let (sink, _next_samples) = rodio::Sink::new_idle();
        app.world_mut()
            .entity_mut(next)
            .insert(AudioSink::new(sink));
        app.update();
        assert_eq!(app.world().resource::<ObserverAudioSettings>().track, 2);
        assert_eq!(decks.single(app.world()).unwrap().1 .0, 2);
        assert!(!app.world().entities().contains(next));
    }

    #[test]
    fn music_mute_and_restore_keep_the_current_recording() {
        let mut app = music_app();
        let mut decks = app.world_mut().query_filtered::<Entity, With<MusicDeck>>();
        let playing = decks.single(app.world()).expect("one current recording");
        let (sink, _samples) = rodio::Sink::new_idle();
        sink.append(rodio::source::SineWave::new(440.0).take_duration(Duration::from_secs(60)));
        app.world_mut()
            .entity_mut(playing)
            .insert(AudioSink::new(sink));
        for volume in [0.0_f32, 0.5] {
            app.world_mut()
                .resource_mut::<ObserverAudioSettings>()
                .music_volume = volume;
            app.world_mut()
                .resource_mut::<Time>()
                .advance_by(Duration::from_secs(4));
            app.world_mut().run_system_once(mix).unwrap();
            assert_eq!(
                app.world()
                    .get::<AudioSink>(playing)
                    .unwrap()
                    .volume()
                    .to_linear()
                    .to_bits(),
                volume.to_bits()
            );
            assert_eq!(decks.single(app.world()).unwrap(), playing);
            assert_eq!(app.world().resource::<ObserverAudioSettings>().track, 0);
        }
    }
}
