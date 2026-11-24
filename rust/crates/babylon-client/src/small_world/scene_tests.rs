use super::{
    BodyRing, DeclaredSurface, Duration, FieldPlugin, Lasts, MeshPickingPlugin, Party, PathBuf,
    Pickable, Places, RunnerError, SceneBody, SceneCommand, SceneRunner, SceneStatus, Shock,
    ShowPeriod, SurfaceId, VisualAssetsPlugin,
};
use crate::small_world::controls::{
    BodyLabel, ControlRow, EmptyLine, PeopleLine, SceneButton, StandingColumn, COPIES_LINE,
    EMPTY_LINE, NOT_WAYNE_LINE, PICK_LINE, UNFOGGED_LINE,
};
use crate::small_world::frame::ParticleMode;
use crate::small_world::inspect::ScenePick;
use crate::small_world::panel;
use crate::small_world::panel::{
    InspectorBody, InspectorPanel, Lower, LowerBody, NoticeLine, PagerLabel, PanelButton,
    PanelView, ShockButton, ShockNotice, TableBody, STORED_WORK_LINE, TO_THE_CENT_LINE,
};
use crate::small_world::rules::{
    RuleButton, RulesBody, SceneRule, FROM_LINE, RULES_LINE, RULES_SHOWN, SHOWN_RULES,
};
use crate::small_world::scene::SceneShown;
use crate::small_world::table::Grouping;
use crate::small_world::{controls, scene};
use babylon_circuit_worlds::{Kind, Place, Workplace, World as BabylonWorld};
use bevy::asset::AssetPlugin;
use bevy::camera::NormalizedRenderTarget;
use bevy::image::ImagePlugin;
use bevy::picking::backend::HitData;
use bevy::picking::pointer::{Location, PointerButton, PointerId};
use bevy::prelude::*;
use bevy::render::texture::TexturePlugin;
use bevy::text::TextPlugin;
use bevy::time::TimeUpdateStrategy;
use hypergraph_rs_bevy::Motion;
use hypergraph_rs_bevy::{FieldFrame, FlowReport, MarkBatch, ParticleId, SetId};
use serde_json::Value;
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
fn play_steps_at_once_and_then_on_its_timer() -> TestResult {
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
    reach(&mut app, 0.01);
    assert_eq!(history(&app), 1);
    reach(&mut app, 3.49);
    assert_eq!(history(&app), 1);
    reach(&mut app, 3.5);
    assert_eq!(history(&app), 2);
    reach(&mut app, 7.0);
    assert_eq!(history(&app), 3);
    send(&mut app, SceneCommand::Pause);
    reach(&mut app, 14.0);
    assert_eq!(history(&app), 3);
    assert!(!app.world().resource::<SceneStatus>().playing);
    Ok(())
}

#[test]
fn the_window_can_open_on_its_first_period() -> TestResult {
    let mut app = App::new();
    app.add_plugins((
        MinimalPlugins,
        AssetPlugin::default(),
        ImagePlugin::default(),
        TextPlugin,
        TexturePlugin,
        bevy::picking::PickingPlugin,
    ))
    .init_asset::<Mesh>()
    .init_asset::<StandardMaterial>()
    .insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_millis(
        10,
    )));
    scene::install_scene(&mut app, None)?;
    scene::open_on_first_period(&mut app);
    app.finish();
    app.cleanup();
    let lines = |app: &mut App| {
        app.world_mut()
            .query_filtered::<Entity, With<EmptyLine>>()
            .iter(app.world())
            .count()
    };
    // Half a second in: nothing has run, and the scene does not say "press Step".
    updates(&mut app, 50);
    assert_eq!(history(&app), 0);
    assert_eq!(lines(&mut app), 0);
    // After `OPENING_DELAY` the first period is shown, once, and the scene is not playing.
    updates(&mut app, 110);
    assert_eq!(history(&app), 1);
    assert_eq!(app.world().resource::<FlowReport>().period, Some(1));
    assert!(!app.world().resource::<SceneStatus>().playing);
    updates(&mut app, 400);
    assert_eq!(history(&app), 1);
    // A run started over waits for the player's first step, and says so.
    send(&mut app, SceneCommand::StartOver);
    updates(&mut app, 200);
    assert_eq!(history(&app), 0);
    assert_eq!(lines(&mut app), 1);
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

fn shock_button(app: &mut App, kind: ShockButton) -> Result<Entity, Box<dyn Error>> {
    let world = app.world_mut();
    world
        .query::<(Entity, &ShockButton)>()
        .iter(world)
        .find_map(|(entity, candidate)| (*candidate == kind).then_some(entity))
        .ok_or_else(|| format!("no shock button {kind:?}").into())
}

fn panel_button(app: &mut App, kind: PanelButton) -> Result<Entity, Box<dyn Error>> {
    let world = app.world_mut();
    world
        .query::<(Entity, &PanelButton)>()
        .iter(world)
        .find_map(|(entity, candidate)| (*candidate == kind).then_some(entity))
        .ok_or_else(|| format!("no panel button {kind:?}").into())
}

/// The inspector's rows: each row holds its label and its figure, in that order.
fn inspector_rows(app: &mut App) -> Vec<(String, String)> {
    let world = app.world_mut();
    let Some(body) = world
        .query_filtered::<Entity, With<InspectorBody>>()
        .iter(world)
        .next()
    else {
        return Vec::new();
    };
    let rows: Vec<Entity> = world
        .get::<Children>(body)
        .map(|c| c.iter().collect())
        .unwrap_or_default();
    rows.into_iter()
        .filter_map(|row| {
            let words: Vec<String> = world
                .get::<Children>(row)?
                .iter()
                .filter_map(|e| world.get::<Text>(e).map(|t| t.0.clone()))
                .collect();
            Some((
                words.first()?.clone(),
                words.get(1).cloned().unwrap_or_default(),
            ))
        })
        .collect()
}

/// The table's rows as their words: the label, then each cell's figure.
fn table_rows(app: &mut App) -> Vec<Vec<String>> {
    let world = app.world_mut();
    let Some(body) = world
        .query_filtered::<Entity, With<TableBody>>()
        .iter(world)
        .next()
    else {
        return Vec::new();
    };
    let rows: Vec<Entity> = world
        .get::<Children>(body)
        .map(|c| c.iter().collect())
        .unwrap_or_default();
    rows.into_iter()
        .map(|row| {
            let cells: Vec<Entity> = world
                .get::<Children>(row)
                .map(|c| c.iter().collect())
                .unwrap_or_default();
            cells
                .into_iter()
                .filter_map(|cell| {
                    world
                        .get::<Children>(cell)?
                        .iter()
                        .find_map(|e| world.get::<Text>(e).map(|t| t.0.clone()))
                })
                .collect()
        })
        .collect()
}

fn table_row(app: &mut App, label: &str) -> Result<Vec<String>, String> {
    table_rows(app)
        .into_iter()
        .find(|row| row.first().map(String::as_str) == Some(label))
        .map(|row| row[1..].to_vec())
        .ok_or_else(|| format!("no table row {label}"))
}

fn row_value(rows: &[(String, String)], label: &str) -> Option<String> {
    rows.iter()
        .find(|(l, _)| l == label)
        .map(|(_, value)| value.clone())
}

#[test]
fn a_strike_from_the_controls_holds_from_the_next_period() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    for kind in [
        ShockButton::Place(Shock::HarvestFails, Places::A),
        ShockButton::Lasts(Shock::HarvestFails, Lasts::UntilLifted),
        ShockButton::Strike(Shock::HarvestFails),
    ] {
        let entity = shock_button(&mut app, kind)?;
        click(&mut app, entity);
        updates(&mut app, 2);
    }
    {
        let scene = app.world().resource::<SceneRunner>();
        let strikes = scene.runner.shocks().strikes();
        assert_eq!(strikes.len(), 1);
        assert_eq!(strikes[0].from, 2);
        assert_eq!(strikes[0].shock, Shock::HarvestFails);
    }
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    let scene = app.world().resource::<SceneRunner>();
    assert_eq!(scene.runner.history()[1].figures.farm_yield, [9, 10]);
    let words = texts(&mut app);
    assert!(words.iter().any(|w| w.starts_with(
        "SHOCK · The harvest fails in Place A · a farm makes 9 food a batch, not 10 · from period 2 · holds"
    )));
    // Striking it again is refused in the scene's words, and they stay for four seconds.
    let strike = shock_button(&mut app, ShockButton::Strike(Shock::HarvestFails))?;
    click(&mut app, strike);
    updates(&mut app, 2);
    assert!(texts(&mut app).contains(&"Already holds in Place A".to_owned()));
    updates(&mut app, 450);
    assert_eq!(app.world().resource::<ShockNotice>().text, None);
    assert!(!texts(&mut app).contains(&"Already holds in Place A".to_owned()));
    Ok(())
}

#[test]
fn the_particle_switch_shows_people() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    let particles = |app: &App| {
        app.world()
            .resource::<SceneShown>()
            .0
            .as_ref()
            .map(|picture| picture.frame.particles.len())
    };
    let people_line = |app: &mut App| {
        let world = app.world_mut();
        world.query::<&PeopleLine>().iter(world).count()
    };
    assert_eq!(particles(&app), Some(12));
    assert_eq!(people_line(&mut app), 0);
    send(&mut app, SceneCommand::Particles(ParticleMode::People));
    updates(&mut app, 3);
    assert_eq!(particles(&app), Some(80));
    assert_eq!(people_line(&mut app), 1);
    assert!(texts(&mut app).contains(&controls::PEOPLE_LINE.to_owned()));
    assert_eq!(history(&app), 1, "switching shows the same period again");
    send(&mut app, SceneCommand::Particles(ParticleMode::Groups));
    updates(&mut app, 3);
    assert_eq!(particles(&app), Some(12));
    assert_eq!(people_line(&mut app), 0);
    Ok(())
}

#[test]
fn the_marks_switch_sets_the_motion() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    send(&mut app, SceneCommand::Marks(Motion::Reduced));
    updates(&mut app, 3);
    assert_eq!(
        app.world()
            .resource::<hypergraph_rs_bevy::FieldConfig>()
            .motion,
        Motion::Reduced
    );
    send(&mut app, SceneCommand::Marks(Motion::Full));
    updates(&mut app, 3);
    assert_eq!(
        app.world()
            .resource::<hypergraph_rs_bevy::FieldConfig>()
            .motion,
        Motion::Full
    );
    Ok(())
}

#[test]
fn the_table_switches_its_grouping_and_period() -> TestResult {
    let mut app = scene_app(None)?;
    for _ in 0..2 {
        send(&mut app, SceneCommand::Step);
        updates(&mut app, 3);
    }
    assert!(texts(&mut app).contains(&"Period 2".to_owned()));
    let class = panel_button(&mut app, PanelButton::Tab(Grouping::Class))?;
    click(&mut app, class);
    updates(&mut app, 2);
    let earners = "Earners who do not own".to_owned();
    assert!(texts(&mut app).contains(&earners));
    let back = panel_button(&mut app, PanelButton::Previous)?;
    click(&mut app, back);
    updates(&mut app, 2);
    let view = app.world().resource::<PanelView>().clone();
    assert_eq!(view.grouping, Grouping::Class);
    assert_eq!(view.period, Some(1));
    let label = {
        let world = app.world_mut();
        world
            .query_filtered::<&Text, With<PagerLabel>>()
            .iter(world)
            .map(|t| t.0.clone())
            .next()
    };
    assert_eq!(label.as_deref(), Some("Period 1"));
    assert!(texts(&mut app).contains(&earners));
    let cells = |figures: [&str; 4]| figures.map(str::to_owned).to_vec();
    assert_eq!(
        table_row(&mut app, "Earners who do not own")?,
        cells(["480", "0", "$4,800.00", "$4,800.00"])
    );
    for label in ["Owners who do not earn", "Neither owner nor earner"] {
        let row = table_row(&mut app, label)?;
        assert_eq!(row[2], "$1,280.00", "{label} in");
        assert_eq!(row[3], "$1,280.00", "{label} out");
    }
    let owners = table_row(&mut app, "Owners who earn")?;
    assert_eq!(owners[0], "0");
    assert_eq!(owners[2], "$0.00");
    assert_eq!(owners[3], "$0.00");
    let all = texts(&mut app);
    assert!(all.contains(&"Stored work got back: not measured yet.".to_owned()));
    assert!(all.contains(
        &"Money in the table is rounded to the cent. Click a body for exact figures.".to_owned()
    ));
    assert_eq!(STORED_WORK_LINE, "Stored work got back: not measured yet.");
    assert_eq!(
        TO_THE_CENT_LINE,
        "Money in the table is rounded to the cent. Click a body for exact figures."
    );
    // The scene still shows the latest period.
    assert_eq!(app.world().resource::<SceneRunner>().shown, Some(2));
    let latest = panel_button(&mut app, PanelButton::Latest)?;
    click(&mut app, latest);
    updates(&mut app, 2);
    assert_eq!(app.world().resource::<PanelView>().period, None);
    Ok(())
}

#[test]
fn a_pick_shows_its_own_figures() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    let farm_a = {
        let world = app.world_mut();
        world
            .query::<(Entity, &SceneBody)>()
            .iter(world)
            .find_map(|(entity, body)| {
                (body.0
                    == Party::Workplace(Workplace {
                        place: Place::A,
                        kind: Kind::Farm,
                    }))
                .then_some(entity)
            })
            .ok_or("no plate of farm A")?
    };
    click(&mut app, farm_a);
    updates(&mut app, 2);
    let rows = inspector_rows(&mut app);
    assert_eq!(row_value(&rows, "Hours given").as_deref(), Some("40"));
    assert_eq!(row_value(&rows, "Made").as_deref(), Some("40"));
    assert!(texts(&mut app).contains(&"Place A farm".to_owned()));

    let group = {
        let world = app.world_mut();
        world
            .query::<(Entity, &ParticleId)>()
            .iter(world)
            .find_map(|(entity, id)| (id.0 == "household:13").then_some(entity))
            .ok_or("no particle household:13")?
    };
    click(&mut app, group);
    updates(&mut app, 2);
    let rows = inspector_rows(&mut app);
    assert_eq!(row_value(&rows, "Persons").as_deref(), Some("4"));

    let set = {
        let world = app.world_mut();
        let set = world
            .query::<(Entity, &SetId)>()
            .iter(world)
            .find_map(|(entity, id)| (id.0 == "workforce:a:farm").then_some(entity))
            .ok_or("no set workforce:a:farm")?;
        world
            .get::<Children>(set)
            .and_then(|children| {
                children
                    .iter()
                    .find(|child| world.get::<Mesh3d>(*child).is_some())
            })
            .ok_or("set workforce:a:farm has no child mesh")?
    };
    click(&mut app, set);
    updates(&mut app, 2);
    let rows = inspector_rows(&mut app);
    assert_eq!(
        row_value(&rows, "Place A farm workers").as_deref(),
        Some("40 hours")
    );
    assert_eq!(row_value(&rows, "Outline holds").as_deref(), Some("100 %"));
    assert_eq!(
        rows.iter().filter(|(l, _)| l.ends_with("workers")).count(),
        1
    );
    Ok(())
}

#[test]
fn a_click_on_empty_space_clears_the_pick() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    let plate = {
        let world = app.world_mut();
        world
            .query::<(Entity, &SceneBody)>()
            .iter(world)
            .map(|(entity, _)| entity)
            .next()
            .ok_or("no plate")?
    };
    click(&mut app, plate);
    updates(&mut app, 2);
    assert!(app.world().resource::<ScenePick>().0.is_some());
    let nothing = app.world_mut().spawn_empty().id();
    click(&mut app, nothing);
    updates(&mut app, 2);
    assert_eq!(app.world().resource::<ScenePick>().0, None);
    Ok(())
}

#[test]
fn a_click_on_the_inspector_keeps_the_pick() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    let plate = {
        let world = app.world_mut();
        world
            .query::<(Entity, &SceneBody)>()
            .iter(world)
            .map(|(entity, _)| entity)
            .next()
            .ok_or("no plate")?
    };
    click(&mut app, plate);
    updates(&mut app, 2);
    let picked = app.world().resource::<ScenePick>().0.clone();
    assert!(picked.is_some());
    let panel = {
        let world = app.world_mut();
        let panel = world
            .query_filtered::<(Entity, &Node), With<InspectorPanel>>()
            .iter(world)
            .map(|(entity, node)| (entity, node.display))
            .next()
            .ok_or("no inspector panel")?;
        assert_ne!(panel.1, Display::None, "shown while something is picked");
        panel.0
    };
    click(&mut app, panel);
    updates(&mut app, 2);
    assert_eq!(app.world().resource::<ScenePick>().0, picked);
    Ok(())
}

#[test]
fn the_inspector_is_hidden_without_a_pick() -> TestResult {
    let mut app = scene_app(None)?;
    updates(&mut app, 3);
    let world = app.world_mut();
    let display = world
        .query_filtered::<&Node, With<InspectorPanel>>()
        .iter(world)
        .map(|node| node.display)
        .next()
        .ok_or("no inspector panel")?;
    assert_eq!(display, Display::None);
    Ok(())
}

#[test]
fn the_bar_has_one_row() -> TestResult {
    let mut app = scene_app(None)?;
    app.update();
    let world = app.world_mut();
    let rows: Vec<(Entity, u8)> = world
        .query::<(Entity, &ControlRow)>()
        .iter(world)
        .map(|(entity, row)| (entity, row.0))
        .collect();
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0].1, 1);
    let buttons = world
        .get::<Children>(rows[0].0)
        .map_or(0, |c| c.iter().count());
    assert_eq!(buttons, 8);
    Ok(())
}

#[test]
fn the_key_stands_at_the_top_left() -> TestResult {
    let mut app = scene_app(None)?;
    app.update();
    let world = app.world_mut();
    let (column, node) = world
        .query_filtered::<(Entity, &Node), With<StandingColumn>>()
        .iter(world)
        .next()
        .ok_or("no standing column")?;
    assert_eq!(node.top, px(scene::HEADER_HEIGHT + 12.0));
    assert_eq!(node.left, px(16));
    assert_eq!(node.width, px(340));
    assert_eq!(node.right, Val::Auto);
    assert_eq!(node.bottom, Val::Auto);
    let last = world
        .get::<Children>(column)
        .and_then(|c| c.last().copied())
        .ok_or("no lines")?;
    assert_eq!(
        world.get::<Text>(last).map(|t| t.0.as_str()),
        Some(PICK_LINE)
    );
    assert_eq!(PICK_LINE, "Click a body, a dot or an outline.");
    Ok(())
}

#[test]
fn not_drawn_line_prints_the_report() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    let line = panel::not_drawn_line(app.world().resource::<FlowReport>());
    assert_eq!(
        line,
        "Not drawn: 0 hours; food 8, power 12, care 4 units; wages $0.00, purchases $1,680.00, taxes $960.00, benefits $0.00, profit $160.00"
    );
    assert!(texts(&mut app).contains(&line));
    Ok(())
}

#[test]
fn the_units_line_is_built_from_the_marks_constants() {
    assert_eq!(
        controls::units_line(),
        "One dot: 2 hours of work. One square: 4 units of a good. One streak: $80. Hours and money are two scales."
    );
}

/// A folder of this test's own, removed when it goes out of scope.
struct TestFolder(std::path::PathBuf);

impl TestFolder {
    fn new() -> Result<Self, Box<dyn Error>> {
        let folder = std::env::temp_dir().join(format!("babylon-script-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&folder)?;
        Ok(Self(folder))
    }
}

impl Drop for TestFolder {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

#[test]
fn a_script_presses_the_same_controls() -> TestResult {
    let folder = TestFolder::new()?;
    let script = folder.0.join("run.jsonl");
    std::fs::write(
        &script,
        "{\"step\":1}\n{\"strike\":{\"shock\":\"harvest_fails\",\"places\":\"a\",\"lasts\":\"until_lifted\"}}\n",
    )?;
    let mut app = scene_app(Some(script))?;
    updates(&mut app, 500);
    let scene = app.world().resource::<SceneRunner>();
    assert_eq!(scene.runner.history().len(), 1);
    assert_eq!(scene.runner.shocks().strikes().len(), 1);
    let replies = std::fs::read_to_string(folder.0.join("replies.jsonl"))?;
    let lines: Vec<&str> = replies.lines().collect();
    assert_eq!(
        lines,
        vec![
            r#"{"event":"done","line":1}"#,
            r#"{"event":"done","line":2}"#
        ]
    );
    Ok(())
}

#[test]
fn a_refused_strike_ends_the_script_and_keeps_the_refusal() -> TestResult {
    let folder = TestFolder::new()?;
    let script = folder.0.join("run.jsonl");
    std::fs::write(
        &script,
        "{\"strike\":{\"shock\":\"power_cut\",\"places\":\"a\",\"lasts\":\"ten_periods\"}}\n{\"step\":1}\n",
    )?;
    let mut app = scene_app(Some(script))?;
    updates(&mut app, 50);
    assert_eq!(history(&app), 0);
    let replies = std::fs::read_to_string(folder.0.join("replies.jsonl"))?;
    assert!(replies.contains(r#""event":"refused""#), "{replies}");
    assert!(folder.0.join("refusal.json").exists());
    Ok(())
}

#[test]
fn a_capture_is_saved_as_a_png() -> TestResult {
    use bevy::asset::RenderAssetUsages;
    use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};
    use bevy::render::view::screenshot::{Screenshot, ScreenshotCaptured};

    let folder = TestFolder::new()?;
    let script = folder.0.join("run.jsonl");
    std::fs::write(&script, "{\"capture\":\"shot\"}\n")?;
    let mut app = scene_app(Some(script))?;
    updates(&mut app, 3);
    let entity = {
        let world = app.world_mut();
        world
            .query_filtered::<Entity, With<Screenshot>>()
            .single(world)?
    };
    let image = Image::new_fill(
        Extent3d {
            width: 2,
            height: 2,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        &[200, 30, 40, 255],
        TextureFormat::Rgba8UnormSrgb,
        RenderAssetUsages::default(),
    );
    app.world_mut()
        .trigger(ScreenshotCaptured { entity, image });
    updates(&mut app, 3);
    let saved = image::open(folder.0.join("shot.png"))?;
    assert_eq!((saved.width(), saved.height()), (2, 2));
    let replies = std::fs::read_to_string(folder.0.join("replies.jsonl"))?;
    assert_eq!(replies.lines().count(), 1);
    assert!(replies.contains(r#""event":"done""#));
    Ok(())
}

fn rule_button(app: &mut App, rule: SceneRule) -> Result<Entity, Box<dyn Error>> {
    let world = app.world_mut();
    world
        .query::<(Entity, &RuleButton)>()
        .iter(world)
        .find_map(|(entity, candidate)| (candidate.0 == rule).then_some(entity))
        .ok_or_else(|| format!("no rule button {rule:?}").into())
}

fn rules_on(app: &App) -> usize {
    app.world().resource::<SceneRunner>().runner.rules().len()
}

fn count_of<C: Component>(app: &mut App) -> usize {
    let world = app.world_mut();
    world
        .query_filtered::<Entity, With<C>>()
        .iter(world)
        .count()
}

/// The texts under an entity, in the order of the tree.
fn texts_under(world: &World, entity: Entity, into: &mut Vec<String>) {
    if let Some(text) = world.get::<Text>(entity) {
        into.push(text.0.clone());
    }
    if let Some(children) = world.get::<Children>(entity) {
        for child in children.iter() {
            texts_under(world, child, into);
        }
    }
}

/// The rule buttons under an entity, in the order of the tree.
fn rule_buttons_under(world: &World, entity: Entity, into: &mut Vec<SceneRule>) {
    if let Some(button) = world.get::<RuleButton>(entity) {
        into.push(button.0);
    }
    if let Some(children) = world.get::<Children>(entity) {
        for child in children.iter() {
            rule_buttons_under(world, child, into);
        }
    }
}

fn caption_of(app: &mut App, tab: Lower) -> Result<String, Box<dyn Error>> {
    let world = app.world_mut();
    let entity = world
        .query::<(Entity, &PanelButton)>()
        .iter(world)
        .find_map(|(entity, kind)| (*kind == PanelButton::Lower(tab)).then_some(entity))
        .ok_or("no lower tab")?;
    let mut words = Vec::new();
    texts_under(world, entity, &mut words);
    Ok(words.concat())
}

#[test]
fn the_rail_has_the_rules_tab_only_for_rules_shown() -> TestResult {
    let mut app = scene_app(None)?;
    updates(&mut app, 2);
    let display = |app: &mut App, tab: Lower| {
        let world = app.world_mut();
        world
            .query::<(&LowerBody, &Node)>()
            .iter(world)
            .find_map(|(body, node)| (body.0 == tab).then_some(node.display))
    };
    if !RULES_SHOWN {
        assert!(count_of::<PanelButton>(&mut app) > 0);
        let world = app.world_mut();
        assert_eq!(
            world
                .query::<&PanelButton>()
                .iter(world)
                .filter(|kind| matches!(kind, PanelButton::Lower(_)))
                .count(),
            0
        );
        assert_eq!(count_of::<RulesBody>(&mut app), 0);
        assert_eq!(texts(&mut app).iter().filter(|w| *w == "Shocks").count(), 1);
        assert_eq!(count_of::<LowerBody>(&mut app), 1);
        assert_eq!(display(&mut app, Lower::Shocks), Some(Display::Flex));
        return Ok(());
    }
    assert_eq!(caption_of(&mut app, Lower::Shocks)?, "Shocks");
    assert_eq!(caption_of(&mut app, Lower::Rules)?, "Rules");
    assert_eq!(display(&mut app, Lower::Shocks), Some(Display::Flex));
    assert_eq!(display(&mut app, Lower::Rules), Some(Display::None));
    let tab = panel_button(&mut app, PanelButton::Lower(Lower::Rules))?;
    click(&mut app, tab);
    updates(&mut app, 2);
    assert_eq!(app.world().resource::<PanelView>().lower, Lower::Rules);
    assert_eq!(display(&mut app, Lower::Shocks), Some(Display::None));
    assert_eq!(display(&mut app, Lower::Rules), Some(Display::Flex));
    let world = app.world_mut();
    let node = world.get::<Node>(tab).ok_or("tab has no node")?;
    assert_eq!(node.border.left, px(3));
    let lower = world
        .query::<(Entity, &LowerBody)>()
        .iter(world)
        .find_map(|(entity, body)| (body.0 == Lower::Rules).then_some(entity))
        .ok_or("no rules body")?;
    let kids: Vec<Entity> = world
        .get::<Children>(lower)
        .ok_or("rules body has no children")?
        .iter()
        .collect();
    assert_eq!(kids.len(), 3);
    assert!(world.get::<RulesBody>(kids[0]).is_some());
    let mut standing = Vec::new();
    texts_under(world, kids[1], &mut standing);
    assert_eq!(standing, vec![RULES_LINE.to_owned()]);
    assert!(world.get::<NoticeLine>(kids[2]).is_some());
    let mut inside = Vec::new();
    texts_under(world, kids[0], &mut inside);
    assert_eq!(inside.first().map(String::as_str), Some(FROM_LINE));
    let mut listed = Vec::new();
    rule_buttons_under(world, kids[0], &mut listed);
    assert_eq!(listed, SHOWN_RULES.to_vec());
    assert_eq!(
        world.query::<&RuleButton>().iter(world).count(),
        SHOWN_RULES.len()
    );
    assert_eq!(count_of::<LowerBody>(&mut app), 2);
    assert_eq!(count_of::<NoticeLine>(&mut app), 2);
    Ok(())
}

#[test]
fn a_rule_that_waits_is_refused_in_the_scene_s_words() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::TurnOn(SceneRule::StopWithoutPay));
    updates(&mut app, 2);
    assert!(texts(&mut app)
        .contains(&"No money, no work waits for people look for work in their place".to_owned()));
    assert_eq!(rules_on(&app), 0);
    assert_eq!(history(&app), 0);
    assert_eq!(app.world().resource::<PanelView>().lower, Lower::Rules);
    Ok(())
}

#[test]
fn a_rule_not_yet_built_is_refused_in_the_scene() -> TestResult {
    let mut app = scene_app(None)?;
    send(&mut app, SceneCommand::Step);
    updates(&mut app, 3);
    send(&mut app, SceneCommand::TurnOn(SceneRule::GoodsStepDown));
    updates(&mut app, 2);
    let notice = app.world().resource::<ShockNotice>().text.clone();
    assert!(
        notice
            .as_deref()
            .is_some_and(|w| w.starts_with("The engine refused a goods price steps down: ")),
        "{notice:?}"
    );
    assert_eq!(rules_on(&app), 0);
    Ok(())
}

#[test]
fn every_shown_rule_turns_on_from_the_next_period_and_holds() -> TestResult {
    if !RULES_SHOWN {
        return Ok(());
    }
    let mut app = scene_app(None)?;
    for _ in 0..2 {
        send(&mut app, SceneCommand::Step);
        updates(&mut app, 3);
    }
    for (k, rule) in SHOWN_RULES.iter().enumerate() {
        let wanted = rule.rule(&BabylonWorld::scene());
        let entity = rule_button(&mut app, *rule)?;
        click(&mut app, entity);
        updates(&mut app, 2);
        let scene = app.world().resource::<SceneRunner>();
        assert_eq!(
            scene.runner.switch(wanted),
            babylon_circuit_worlds::Switch::On { from: 3 }
        );
        let entity = rule_button(&mut app, *rule)?;
        let world = app.world_mut();
        let node = world.get::<Node>(entity).ok_or("no node")?;
        assert_eq!(node.border.left, px(3));
        let border = world.get::<BorderColor>(entity).ok_or("no border")?;
        assert_eq!(border.left, crate::observer_theme::YELLOW);
        let row = world.get::<ChildOf>(entity).ok_or("no row")?.parent();
        let mut inside = Vec::new();
        texts_under(world, row, &mut inside);
        assert!(inside.contains(&"3".to_owned()), "{inside:?}");
        assert_eq!(
            caption_of(&mut app, Lower::Rules)?,
            format!("Rules · {} on", k + 1)
        );
        let entity = rule_button(&mut app, *rule)?;
        click(&mut app, entity);
        updates(&mut app, 2);
        let name = babylon_circuit_worlds::rule_name(wanted);
        assert_eq!(
            app.world().resource::<ShockNotice>().text,
            Some(format!(
                "{name} is on from period 3 and holds until you start over"
            ))
        );
        assert_eq!(rules_on(&app), k + 1);
    }
    assert_eq!(rules_on(&app), SHOWN_RULES.len());
    assert!(texts(&mut app).contains(&RULES_LINE.to_owned()));
    send(&mut app, SceneCommand::StartOver);
    updates(&mut app, 3);
    assert_eq!(rules_on(&app), 0);
    assert_eq!(caption_of(&mut app, Lower::Rules)?, "Rules");
    for rule in SHOWN_RULES {
        let entity = rule_button(&mut app, *rule)?;
        let world = app.world_mut();
        let row = world.get::<ChildOf>(entity).ok_or("no row")?.parent();
        let mut inside = Vec::new();
        texts_under(world, row, &mut inside);
        assert!(
            !inside.iter().any(|w| w.parse::<u32>().is_ok()),
            "{inside:?}"
        );
    }
    Ok(())
}

#[test]
fn a_refused_rule_ends_the_script_and_keeps_the_refusal() -> TestResult {
    let folder = TestFolder::new()?;
    let script = folder.0.join("run.jsonl");
    std::fs::write(&script, "{\"step\":1}\n{\"rule\":\"stop_without_pay\"}\n")?;
    let mut app = scene_app(Some(script))?;
    updates(&mut app, 500);
    let replies = std::fs::read_to_string(folder.0.join("replies.jsonl"))?;
    let lines: Vec<&str> = replies.lines().collect();
    assert_eq!(lines.len(), 2, "{replies}");
    assert_eq!(lines[0], r#"{"event":"done","line":1}"#);
    assert_eq!(
        lines[1],
        r#"{"event":"refused","line":2,"reason":"No money, no work waits for people look for work in their place"}"#
    );
    let kept = std::fs::read_to_string(folder.0.join("refusal.json"))?;
    let value: Value = serde_json::from_str(&kept)?;
    assert_eq!(value["rules"], serde_json::json!([]));
    Ok(())
}
