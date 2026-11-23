use super::{
    BodyRing, DeclaredSurface, Duration, FieldPlugin, Lasts, MeshPickingPlugin, Party, PathBuf,
    Pickable, Places, RunnerError, SceneBody, SceneCommand, SceneRunner, SceneStatus, Shock,
    ShowPeriod, SurfaceId, VisualAssetsPlugin,
};
use crate::small_world::controls::{
    BodyLabel, SceneButton, COPIES_LINE, EMPTY_LINE, NOT_WAYNE_LINE, UNFOGGED_LINE,
};
use crate::small_world::scene;
use bevy::asset::AssetPlugin;
use bevy::camera::NormalizedRenderTarget;
use bevy::image::ImagePlugin;
use bevy::picking::backend::HitData;
use bevy::picking::pointer::{Location, PointerButton, PointerId};
use bevy::prelude::*;
use bevy::render::texture::TexturePlugin;
use bevy::text::TextPlugin;
use bevy::time::TimeUpdateStrategy;
use hypergraph_rs_bevy::{FieldFrame, FlowReport, MarkBatch, ParticleId, SetId};
use std::error::Error;

type TestResult = Result<(), Box<dyn Error>>;

/// The headless base of the scene: no window, no graphics card, 10 ms to a frame.
fn scene_app(script: Option<PathBuf>) -> Result<App, Box<dyn Error>> {
    let mut app = App::new();
    app.add_plugins((
        MinimalPlugins,
        AssetPlugin::default(),
        ImagePlugin::default(),
        TextPlugin,
        TexturePlugin,
        // The mesh picking systems read the ray map this plugin makes.
        bevy::picking::PickingPlugin,
    ))
    .init_asset::<Mesh>()
    .init_asset::<StandardMaterial>()
    .insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_millis(
        10,
    )));
    scene::install_scene(&mut app, script)?;
    app.finish();
    app.cleanup();
    Ok(app)
}

fn updates(app: &mut App, n: usize) {
    for _ in 0..n {
        app.update();
    }
}

fn send(app: &mut App, command: SceneCommand) {
    app.world_mut().write_message(command);
}

fn history(app: &App) -> usize {
    app.world().resource::<SceneRunner>().runner.history().len()
}

fn texts(app: &mut App) -> Vec<String> {
    let world = app.world_mut();
    world
        .query::<&Text>()
        .iter(world)
        .map(|text| text.0.clone())
        .collect()
}

fn click(app: &mut App, entity: Entity) {
    app.world_mut().trigger(PointerClick {
        entity,
        pointer: Pointer::new(
            PointerId::Mouse,
            Location {
                target: NormalizedRenderTarget::None {
                    width: 0,
                    height: 0,
                },
                position: Vec2::ZERO,
            },
        ),
        button: PointerButton::Primary,
        hit: HitData::new(Entity::PLACEHOLDER, 0.0, None, None),
        duration: Duration::ZERO,
        count: 1,
    });
}

fn button(app: &mut App, kind: SceneButton) -> Result<Entity, Box<dyn Error>> {
    let world = app.world_mut();
    world
        .query::<(Entity, &SceneButton)>()
        .iter(world)
        .find_map(|(entity, candidate)| (*candidate == kind).then_some(entity))
        .ok_or_else(|| format!("no button {kind:?}").into())
}

#[test]
fn the_small_world_composition_has_no_campaign_session() -> TestResult {
    use crate::campaign_browser::CampaignBrowserPlugin;
    use crate::observer::ObserverSession;
    use crate::observer_audio::ObserverAudioPlugin;
    use crate::observer_focus::ObserverFocusPlugin;
    use crate::observer_history::ObserverHistoryPlugin;
    use crate::observer_io::{ObserverIoPlugin, RuntimePipe};
    use crate::observer_map3d::ObserverMap3dPlugin;
    use crate::observer_opening::OpeningPlugin;
    use crate::observer_performance::ObserverPerformancePlugin;
    use crate::observer_ui::ObserverShellPlugin;
    use crate::observer_warning::ObserverWarningPlugin;
    use crate::organizer::OrganizerPlugin;
    use crate::production::ProductionPlugin;
    use crate::session_log::SessionLogPlugin;
    use crate::ui::dossier_card::DossierCardPlugin;

    let mut app = scene_app(None)?;
    app.update();
    let world = app.world();
    assert!(!world.contains_resource::<ObserverSession>());
    assert!(!world.contains_resource::<RuntimePipe>());
    assert!(app.is_plugin_added::<FieldPlugin>());
    assert!(app.is_plugin_added::<VisualAssetsPlugin>());
    assert!(app.is_plugin_added::<MeshPickingPlugin>());
    assert!(!app.is_plugin_added::<ObserverIoPlugin>());
    assert!(!app.is_plugin_added::<CampaignBrowserPlugin>());
    assert!(!app.is_plugin_added::<OrganizerPlugin>());
    assert!(!app.is_plugin_added::<ProductionPlugin>());
    assert!(!app.is_plugin_added::<ObserverMap3dPlugin>());
    assert!(!app.is_plugin_added::<ObserverHistoryPlugin>());
    assert!(!app.is_plugin_added::<DossierCardPlugin>());
    assert!(!app.is_plugin_added::<ObserverShellPlugin>());
    assert!(!app.is_plugin_added::<OpeningPlugin>());
    assert!(!app.is_plugin_added::<ObserverWarningPlugin>());
    assert!(!app.is_plugin_added::<SessionLogPlugin>());
    assert!(!app.is_plugin_added::<ObserverAudioPlugin>());
    assert!(!app.is_plugin_added::<ObserverPerformancePlugin>());
    assert!(!app.is_plugin_added::<ObserverFocusPlugin>());
    let scene = world.resource::<SceneRunner>();
    assert_eq!(scene.runner.next_period(), 1);
    assert_eq!(scene.shown, None);
    Ok(())
}

#[test]
fn a_step_shows_the_next_period() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    assert_eq!(history(&app), 1);
    assert_eq!(app.world().resource::<FlowReport>().period, Some(1));
    assert_eq!(app.world().resource::<SceneRunner>().shown, Some(1));
    Ok(())
}

#[test]
fn again_replays_without_stepping() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Again);
    updates(&mut app, 3);
    assert_eq!(app.world().resource::<FlowReport>().period, None);
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    send(&mut app, SceneCommand::Again);
    updates(&mut app, 3);
    assert_eq!(history(&app), 1);
    assert_eq!(app.world().resource::<FlowReport>().period, Some(1));
    Ok(())
}

#[test]
fn start_over_rebuilds_the_opening() -> TestResult {
    let mut app = scene_app(None)?;
    for _ in 0..3 {
        send(&mut app, SceneCommand::Step);
        updates(&mut app, 3);
    }
    app.world_mut()
        .resource_mut::<SceneRunner>()
        .runner
        .strike(Shock::HarvestFails, Places::A, Lasts::UntilLifted)?;
    assert_eq!(history(&app), 3);
    assert_eq!(
        app.world()
            .resource::<SceneRunner>()
            .runner
            .shocks()
            .strikes()
            .len(),
        1
    );
    send(&mut app, SceneCommand::StartOver);
    updates(&mut app, 3);
    let scene = app.world().resource::<SceneRunner>();
    assert_eq!(scene.runner.history().len(), 0);
    assert_eq!(scene.runner.shocks().strikes(), []);
    assert_eq!(scene.runner.next_period(), 1);
    assert_eq!(scene.shown, None);
    Ok(())
}

#[test]
fn play_steps_on_its_timer() -> TestResult {
    let mut app = scene_app(None)?;
    app.update();
    let begun = app.world().resource::<Time>().elapsed();
    send(&mut app, SceneCommand::Play);
    let reach = |app: &mut App, seconds: f64| {
        while app
            .world()
            .resource::<Time>()
            .elapsed()
            .saturating_sub(begun)
            < Duration::from_secs_f64(seconds)
        {
            app.update();
        }
    };
    reach(&mut app, 3.49);
    assert_eq!(history(&app), 0);
    reach(&mut app, 3.5);
    assert_eq!(history(&app), 1);
    reach(&mut app, 7.0);
    assert_eq!(history(&app), 2);
    send(&mut app, SceneCommand::Pause);
    reach(&mut app, 14.0);
    assert_eq!(history(&app), 2);
    assert!(!app.world().resource::<SceneStatus>().playing);
    Ok(())
}

#[test]
fn a_refusal_is_shown_in_the_engine_s_words() -> TestResult {
    let refusal = scene::status_after(&Err(RunnerError::PastHorizon { period: 999 }));
    assert_eq!(
        refusal.refusal.as_deref(),
        Some("Period 999: this test economy is built for 998 periods")
    );
    assert!(!refusal.playing);

    let mut app = scene_app(None)?;
    app.update();
    {
        let mut status = app.world_mut().resource_mut::<SceneStatus>();
        status.playing = true;
        status.refusal = refusal.refusal;
    }
    app.update();
    assert!(texts(&mut app)
        .contains(&"Period 999: this test economy is built for 998 periods".to_owned()));
    assert!(texts(&mut app).contains(&"Stopped by the engine".to_owned()));
    // While it shows, Step does nothing.
    send(&mut app, SceneCommand::Step);
    app.update();
    assert_eq!(history(&app), 0);
    // Start over clears it.
    send(&mut app, SceneCommand::StartOver);
    updates(&mut app, 2);
    assert!(!texts(&mut app)
        .iter()
        .any(|line| line.starts_with("Period 999")));
    Ok(())
}

#[test]
fn a_frame_the_library_refuses_is_shown_as_the_refusal() -> TestResult {
    let mut app = scene_app(None)?;
    app.update();
    let twice = hypergraph_rs_bevy::ParticleFrame {
        id: "p".to_owned(),
        at: Vec3::ZERO,
        style: 0,
    };
    let frame = FieldFrame {
        period: 7,
        particles: vec![twice.clone(), twice],
        ..FieldFrame::default()
    };
    app.world_mut().write_message(ShowPeriod(Box::new(frame)));
    updates(&mut app, 2);
    let status = app.world().resource::<SceneStatus>();
    let words = status.refusal.as_deref().unwrap_or_default();
    assert!(
        words.starts_with("Period 7: the picture was refused"),
        "{words}"
    );
    assert!(!status.playing);
    Ok(())
}

#[test]
fn the_unfogged_words_are_on_screen() -> TestResult {
    let mut app = scene_app(None)?;
    app.update();
    let lines = texts(&mut app);
    assert!(lines.contains(&"ADMIN · MATERIAL TRUTH · UNFOGGED".to_owned()));
    assert!(lines.contains(&"A test economy. Not Wayne. Not saved.".to_owned()));
    assert_eq!(UNFOGGED_LINE, "ADMIN · MATERIAL TRUTH · UNFOGGED");
    assert_eq!(NOT_WAYNE_LINE, "A test economy. Not Wayne. Not saved.");
    assert!(lines.contains(&COPIES_LINE.to_owned()));
    assert_eq!(
        COPIES_LINE,
        "Place A and Place B are copies of one test economy, not real places."
    );
    Ok(())
}

#[test]
fn an_empty_scene_says_so() -> TestResult {
    let mut app = scene_app(None)?;
    app.update();
    let says = |app: &mut App| texts(app).contains(&EMPTY_LINE.to_owned());
    assert_eq!(EMPTY_LINE, "Nothing has run yet. Press Step.");
    assert!(says(&mut app));
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    assert!(!says(&mut app));
    send(&mut app, SceneCommand::StartOver);
    updates(&mut app, 3);
    assert!(says(&mut app));
    Ok(())
}

#[test]
fn the_buttons_write_the_scene_s_commands() -> TestResult {
    let mut app = scene_app(None)?;
    app.update();
    let step = button(&mut app, SceneButton::Step)?;
    click(&mut app, step);
    updates(&mut app, 3);
    assert_eq!(history(&app), 1);
    let play = button(&mut app, SceneButton::PlayPause)?;
    click(&mut app, play);
    app.update();
    assert!(app.world().resource::<SceneStatus>().playing);
    assert!(texts(&mut app).contains(&"Pause".to_owned()));
    click(&mut app, play);
    app.update();
    assert!(!app.world().resource::<SceneStatus>().playing);
    Ok(())
}

#[test]
fn every_body_has_a_pick_plate_and_a_label() -> TestResult {
    let mut app = scene_app(None)?;
    app.update();
    let world = app.world_mut();
    let plates: Vec<Party> = world
        .query::<&SceneBody>()
        .iter(world)
        .map(|body| body.0)
        .collect();
    assert_eq!(plates.len(), 10);
    let labels: Vec<Party> = world
        .query::<&BodyLabel>()
        .iter(world)
        .map(|label| label.0)
        .collect();
    assert_eq!(labels.len(), 10);
    assert!(plates.contains(&Party::Treasury) && plates.contains(&Party::Fund));
    Ok(())
}

#[test]
fn a_shown_period_draws_a_workplace_s_two_rings_and_a_start_over_takes_them_away() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    let rings = |app: &mut App| {
        let world = app.world_mut();
        world.query::<&BodyRing>().iter(world).count()
    };
    assert_eq!(
        rings(&mut app),
        16,
        "an hours ring and a money ring on each of eight"
    );
    send(&mut app, SceneCommand::StartOver);
    updates(&mut app, 2);
    assert_eq!(rings(&mut app), 0);
    Ok(())
}

#[test]
fn every_visual_entity_of_the_scene_declares_the_small_world() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    let world = app.world_mut();
    let mut visual = world.query_filtered::<(
        Entity,
        Option<&DeclaredSurface>,
    ), Or<(With<Text>, With<ImageNode>, With<Mesh2d>, With<Mesh3d>)>>();
    let mut count = 0;
    for (entity, declared) in visual.iter(world) {
        count += 1;
        assert_eq!(
            declared.map(|surface| surface.id),
            Some(SurfaceId::SmallWorld),
            "{entity:?} declares no surface"
        );
    }
    assert!(count > 0);
    let mut particles = world.query_filtered::<&DeclaredSurface, With<ParticleId>>();
    assert_eq!(particles.iter(world).count(), 12);
    let mut sets = world.query_filtered::<Entity, With<SetId>>();
    assert!(sets.iter(world).count() > 0);
    let mut marks = world.query_filtered::<(&DeclaredSurface, &Pickable), With<MarkBatch>>();
    let batches: Vec<_> = marks.iter(world).collect();
    assert!(
        !batches.is_empty(),
        "the period's marks are one mesh a stream"
    );
    for (_, pickable) in batches {
        assert_eq!(*pickable, Pickable::IGNORE);
    }
    Ok(())
}
