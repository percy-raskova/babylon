//! Music and restrained feedback from viewer interactions and acknowledged commits.
//! Audio never participates in campaign identity or mechanics.

use bevy::asset::io::embedded::EmbeddedAssetRegistry;
use bevy::audio::{AudioSinkPlayback, Volume};
use bevy::prelude::*;
use std::path::{Path, PathBuf};

mod catalog;

use catalog::{DEFAULT_TRACK_INDEX, MUSIC_TRACKS, TITLE_TRACK_INDEX};

use crate::map::SelectedCounty;
use crate::observer::{ObserverSession, SessionPhase};
use crate::observer_io::ObserverSet;
use crate::observer_opening::{OpeningPresentation, OpeningStage};
use crate::observer_ui::ObserverCommand;

// +3 dB. The Purge's decoded -6.19 dBTP peak leaves headroom at full volume.
const TITLE_GAIN: f32 = 1.412_537_6;

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
    production: Handle<AudioSource>,
}
#[derive(Component, Clone, Copy, Debug, Eq, PartialEq)]
enum MusicDeck {
    Title,
    Gameplay(usize),
}
#[derive(Component)]
struct ProductionFanfare;
#[derive(Component)]
struct EffectLifetime(Timer);

fn desired_deck(
    opening: Option<&OpeningPresentation>,
    settings: &ObserverAudioSettings,
) -> Option<MusicDeck> {
    match opening.map(|opening| opening.stage) {
        Some(OpeningStage::Warning | OpeningStage::Production) => None,
        Some(OpeningStage::Title) => Some(MusicDeck::Title),
        Some(OpeningStage::Game) | None => Some(MusicDeck::Gameplay(settings.track)),
    }
}

fn start_music(commands: &mut Commands, server: &AssetServer, deck: MusicDeck) {
    let index = match deck {
        MusicDeck::Title => TITLE_TRACK_INDEX,
        MusicDeck::Gameplay(index) => index,
    };
    let Some(track) = MUSIC_TRACKS.get(index) else {
        error!(
            track = index,
            "Music selection is outside the embedded soundtrack"
        );
        return;
    };
    commands.spawn((
        AudioPlayer::new(server.load(format!("embedded://{}", track.path))),
        PlaybackSettings {
            volume: Volume::SILENT,
            ..match deck {
                MusicDeck::Title => PlaybackSettings::LOOP,
                MusicDeck::Gameplay(_) => PlaybackSettings::ONCE,
            }
        },
        deck,
    ));
}

fn setup(
    mut commands: Commands,
    server: Res<AssetServer>,
    settings: Res<ObserverAudioSettings>,
    opening: Option<Res<OpeningPresentation>>,
) {
    if let Some(deck) = desired_deck(opening.as_deref(), &settings) {
        start_music(&mut commands, &server, deck);
    }
    commands.insert_resource(AudioBank {
        select: server.load("embedded://sfx/ui/ui_select.ogg"),
        tab: server.load("embedded://sfx/ui/ui_tab.ogg"),
        open: server.load("embedded://sfx/ui/ui_open.ogg"),
        back: server.load("embedded://sfx/ui/ui_back.ogg"),
        tick: server.load("embedded://sfx/state/tick_advance.ogg"),
        fault: server.load("embedded://sfx/state/state_fault.ogg"),
        production: server.load("embedded://sfx/stinger/production_fanfare.ogg"),
    });
}

fn effect(commands: &mut Commands, source: Handle<AudioSource>, volume: f32) -> Option<Entity> {
    if volume <= 0.0 {
        return None;
    }
    Some(
        commands
            .spawn((
                AudioPlayer::new(source),
                PlaybackSettings {
                    volume: Volume::Linear(volume),
                    ..PlaybackSettings::DESPAWN
                },
                EffectLifetime(Timer::from_seconds(8.0, TimerMode::Once)),
            ))
            .id(),
    )
}

fn opening_fanfare(
    mut commands: Commands,
    opening: Option<Res<OpeningPresentation>>,
    bank: Res<AudioBank>,
    settings: Res<ObserverAudioSettings>,
    playing: Query<(Entity, Option<&AudioSink>), With<ProductionFanfare>>,
    mut previous: Local<Option<OpeningStage>>,
) {
    let stage = opening.as_ref().map(|opening| opening.stage);
    if *previous == stage {
        return;
    }
    *previous = stage;
    for (entity, sink) in &playing {
        if let Some(sink) = sink {
            sink.stop();
        }
        commands.entity(entity).despawn();
    }
    if stage == Some(OpeningStage::Production) {
        if let Some(entity) = effect(
            &mut commands,
            bank.production.clone(),
            settings.effects_volume,
        ) {
            commands.entity(entity).insert((
                ProductionFanfare,
                EffectLifetime(Timer::from_seconds(9.0, TimerMode::Once)),
            ));
        }
    }
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
        let _ = effect(&mut commands, cue, settings.effects_volume);
    }
}

fn gameplay_audio(opening: Option<Res<OpeningPresentation>>) -> bool {
    opening.is_none_or(|opening| opening.stage == OpeningStage::Game)
}

fn mix(
    time: Res<Time>,
    mut settings: ResMut<ObserverAudioSettings>,
    opening: Option<Res<OpeningPresentation>>,
    mut decks: Query<(Entity, &MusicDeck, Option<&mut AudioSink>)>,
    mut effects: Query<(Entity, &mut EffectLifetime)>,
    server: Res<AssetServer>,
    mut commands: Commands,
) {
    let mut desired = desired_deck(opening.as_deref(), &settings);
    let mut active = false;
    for (entity, playing, sink) in &mut decks {
        let finished = matches!(playing, MusicDeck::Gameplay(_))
            && sink.as_ref().is_some_and(|sink| sink.empty());
        if Some(*playing) != desired || finished || active {
            // A manual Next wins if the old recording finishes in the same frame.
            if finished && Some(*playing) == desired {
                settings.next_track();
                desired = desired_deck(opening.as_deref(), &settings);
            }
            if let Some(sink) = sink {
                sink.stop();
            }
            commands.entity(entity).despawn();
        } else {
            active = true;
            if let Some(mut sink) = sink {
                let target = settings.music_volume
                    * if *playing == MusicDeck::Title {
                        TITLE_GAIN
                    } else {
                        1.0
                    };
                let current = sink.volume().to_linear();
                let step = time.delta_secs() * 0.35;
                let volume = if current < target {
                    (current + step).min(target)
                } else {
                    (current - step).max(target)
                };
                sink.set_volume(Volume::Linear(volume));
            }
        }
    }
    if !active {
        if let Some(deck) = desired {
            start_music(&mut commands, &server, deck);
        }
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
            (
                "sfx/stinger/production_fanfare.ogg",
                include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/../../../assets/sfx/stinger/production_fanfare.ogg"
                )) as &[u8],
            ),
        ] {
            register_audio(registry, name, bytes);
        }
        app.init_resource::<ObserverAudioSettings>()
            .add_systems(Startup, setup)
            .add_systems(
                Update,
                (opening_fanfare, feedback.run_if(gameplay_audio), mix)
                    .chain()
                    .after(ObserverSet::Install),
            );
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
        music_app_with_opening(None)
    }

    fn music_app_with_opening(stage: Option<OpeningStage>) -> App {
        let mut app = App::new();
        if let Some(stage) = stage {
            app.init_resource::<OpeningPresentation>();
            app.world_mut().resource_mut::<OpeningPresentation>().stage = stage;
        }
        app.add_plugins((MinimalPlugins, AssetPlugin::default()))
            .init_asset::<AudioSource>()
            .init_resource::<ObserverAudioSettings>()
            .add_systems(Startup, setup)
            .add_systems(Update, (opening_fanfare, mix).chain());
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
        assert_eq!(*deck, MusicDeck::Gameplay(0));
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
            .find_map(|(entity, deck)| (*deck == MusicDeck::Gameplay(0)).then_some(entity))
            .unwrap();
        let (sink, _samples) = rodio::Sink::new_idle();
        app.world_mut()
            .entity_mut(finished)
            .insert(AudioSink::new(sink));
        app.update();
        assert_eq!(app.world().resource::<ObserverAudioSettings>().track, 1);
        let (next, deck) = decks.single(app.world()).expect("one replacement decoder");
        assert_eq!(*deck, MusicDeck::Gameplay(1));
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
        assert_eq!(
            *decks.single(app.world()).unwrap().1,
            MusicDeck::Gameplay(2)
        );
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

    #[test]
    fn title_theme_boost_reaches_the_sink_and_mute_remains_silent() {
        let mut app = music_app_with_opening(Some(OpeningStage::Title));
        let playing = app
            .world_mut()
            .query_filtered::<Entity, With<MusicDeck>>()
            .single(app.world())
            .unwrap();
        let (sink, _samples) = rodio::Sink::new_idle();
        app.world_mut()
            .entity_mut(playing)
            .insert(AudioSink::new(sink));
        app.world_mut()
            .resource_mut::<ObserverAudioSettings>()
            .music_volume = 1.0;
        app.world_mut()
            .resource_mut::<Time>()
            .advance_by(Duration::from_secs(8));
        app.world_mut().run_system_once(mix).unwrap();
        let volume = app
            .world()
            .get::<AudioSink>(playing)
            .unwrap()
            .volume()
            .to_linear();
        assert!((20.0 * volume.log10() - 3.0).abs() < 0.001);
        app.world_mut()
            .resource_mut::<ObserverAudioSettings>()
            .music_volume = 0.0;
        app.world_mut().run_system_once(mix).unwrap();
        assert_eq!(
            app.world()
                .get::<AudioSink>(playing)
                .unwrap()
                .volume()
                .to_linear()
                .to_bits(),
            0.0_f32.to_bits()
        );
    }

    #[test]
    fn title_loops_the_purge_then_game_starts_the_unchanged_playlist() {
        let mut app = music_app_with_opening(Some(OpeningStage::Warning));
        let mut decks = app
            .world_mut()
            .query::<(Entity, &MusicDeck, &PlaybackSettings, &AudioPlayer)>();
        assert_eq!(decks.iter(app.world()).count(), 0);
        app.world_mut().resource_mut::<OpeningPresentation>().stage = OpeningStage::Title;
        app.update();
        let (title, deck, settings, player) = decks.single(app.world()).expect("title music");
        assert_eq!(*deck, MusicDeck::Title);
        assert!(matches!(settings.mode, PlaybackMode::Loop));
        assert_eq!(
            player.0.path().unwrap().path(),
            Path::new("music/fascist/05_the_purge.ogg")
        );
        let (sink, _samples) = rodio::Sink::new_idle();
        app.world_mut()
            .entity_mut(title)
            .insert(AudioSink::new(sink));
        app.update();
        assert_eq!(decks.single(app.world()).unwrap().0, title);
        assert_eq!(
            app.world().resource::<ObserverAudioSettings>().track,
            DEFAULT_TRACK_INDEX
        );
        app.world_mut().resource_mut::<OpeningPresentation>().stage = OpeningStage::Game;
        app.update();
        let (game, deck, settings, player) = decks.single(app.world()).expect("game music");
        assert_ne!(game, title);
        assert_eq!(*deck, MusicDeck::Gameplay(DEFAULT_TRACK_INDEX));
        assert!(matches!(settings.mode, PlaybackMode::Once));
        assert_eq!(
            player.0.path().unwrap().path(),
            Path::new("music/ambient/01_history_breathing.ogg")
        );
        assert!(!app.world().entities().contains(title));
    }

    #[test]
    fn production_plays_one_fanfare_and_skip_stops_it_without_music_overlap() {
        let mut app = music_app_with_opening(Some(OpeningStage::Warning));
        app.world_mut().resource_mut::<OpeningPresentation>().stage = OpeningStage::Production;
        app.update();
        let mut fanfares = app
            .world_mut()
            .query_filtered::<(Entity, &PlaybackSettings), With<ProductionFanfare>>();
        let (fanfare, settings) = fanfares.single(app.world()).expect("one production cue");
        assert_eq!(
            settings.volume.to_linear().to_bits(),
            ObserverAudioSettings::default().effects_volume.to_bits()
        );
        let mut decks = app.world_mut().query_filtered::<Entity, With<MusicDeck>>();
        assert_eq!(decks.iter(app.world()).count(), 0);
        app.update();
        assert_eq!(fanfares.single(app.world()).unwrap().0, fanfare);
        app.world_mut().resource_mut::<OpeningPresentation>().stage = OpeningStage::Title;
        app.update();
        assert_eq!(fanfares.iter(app.world()).count(), 0);
        assert!(!app.world().entities().contains(fanfare));
        assert_eq!(decks.iter(app.world()).count(), 1);
    }

    #[test]
    fn production_respects_effects_mute_and_does_not_retrigger_on_unmute() {
        let mut app = music_app_with_opening(Some(OpeningStage::Warning));
        app.world_mut()
            .resource_mut::<ObserverAudioSettings>()
            .effects_volume = 0.0;
        app.world_mut().resource_mut::<OpeningPresentation>().stage = OpeningStage::Production;
        app.update();
        let mut fanfares = app
            .world_mut()
            .query_filtered::<Entity, With<ProductionFanfare>>();
        assert_eq!(fanfares.iter(app.world()).count(), 0);
        app.world_mut()
            .resource_mut::<ObserverAudioSettings>()
            .effects_volume = 0.5;
        app.update();
        assert_eq!(fanfares.iter(app.world()).count(), 0);
    }
}
