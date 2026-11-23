//! The small world's scene: the plugin that runs the doubled world in this process, its
//! commands, the camera that looks straight down at the plane, and the bodies and rings drawn
//! over the hypergraph library's particles, sets and marks.
//!
//! No campaign, runtime, pipe or database is behind it: `install_scene` adds none of the
//! observer's plugins, and nothing here is saved.

use super::controls;
use super::frame;
use super::frame::{BodyPicture, ParticleMode, Picture};
use super::layout::{FUND_AT, HOURS_RING_Y, MONEY_RING_Y, PLANE, TREASURY_AT, WORKPLACE_X};
use super::reading::Party;
use super::table::Grouping;
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer_ui;
use crate::palette::{BONE, FIELD, GOLD};
use crate::visual_assets::VisualAssetsPlugin;
use babylon_circuit_worlds::{
    Lasts, PeriodResult, Place, Places, Runner, RunnerError, Shock, Workplace,
};
use bevy::camera::visibility::RenderLayers;
use bevy::camera::{ScalingMode, Viewport};
use bevy::core_pipeline::tonemapping::Tonemapping;
use bevy::ecs::system::SystemParam;
use bevy::prelude::*;
use bevy::ui::UiSystems;
use bevy::window::PrimaryWindow;
use hypergraph_rs::geometry::{Outline, Point};
use hypergraph_rs_bevy::{
    FieldError, FieldPlugin, FieldSystems, FrameRefused, Glyph, MarkBatch, MarkOf, Motion,
    PathLines, ReplayPeriod, ShowPeriod,
};
use std::f32::consts::FRAC_PI_2;
use std::path::PathBuf;
use std::time::Duration;

/// Three beats of one second and half a second at rest, between one played step and the next.
pub const PLAY_INTERVAL: Duration = Duration::from_millis(3_500);
/// The header's height in logical pixels.
pub const HEADER_HEIGHT: f32 = 48.0;
/// The control bar's height in logical pixels.
pub const BAR_HEIGHT: f32 = 72.0;
/// The right rail's width, where the table and the inspector stand.
pub const RAIL_WIDTH: f32 = 400.0;

/// How high the camera stands above the middle of the plane.
const CAMERA_HEIGHT: f32 = 40.0;
/// The render layer of the user-interface camera, as the observer's.
const UI_LAYER: usize = 31;
/// What a click on a body hits: a disc of the field's colour under it.
const PLATE_RADIUS: f32 = 0.95;
/// The plate's height; everything else of a body is a child of it.
const PLATE_Y: f32 = 0.01;
/// The body's centre disc and its frame: height and size.
const BODY_Y: f32 = 0.05;
const CORE_RADIUS: f32 = 0.2;
const FRAME_SCALE: f32 = 0.6;
/// A ring is 48 segments, 0.055 wide; the hours ring is dashed.
const RING_SEGMENTS: u32 = 48;
const RING_WIDTH: f32 = 0.055;
const HOURS_DASH: (f64, f64) = (0.18, 0.12);

/// The scene's state: the runner that closes periods, how particles are drawn, and the period
/// whose picture is shown (none until the first step, and again after a start over).
#[derive(Resource)]
pub struct SceneRunner {
    pub runner: Runner,
    pub mode: ParticleMode,
    pub shown: Option<u64>,
}

/// The picture of the period shown: bodies, positions, sets and the reading it was built from.
#[derive(Resource, Default)]
pub struct SceneShown(pub Option<Picture>);

/// Whether the run is playing, and the engine's words when it refused.
#[derive(Resource, Default, Clone, Debug, PartialEq, Eq)]
pub struct SceneStatus {
    pub playing: bool,
    pub refusal: Option<String>,
}

/// The script file the scene was given, for the script's own system.
#[derive(Resource, Default, Clone, Debug, PartialEq, Eq)]
pub struct SceneScript(pub Option<PathBuf>);

/// Time since the last played step.
#[derive(Resource, Default)]
struct PlayClock(Duration);

/// What a button, the script or the table asks of the scene.
#[derive(Message, Clone, Debug, PartialEq, Eq)]
pub enum SceneCommand {
    Step,
    Play,
    Pause,
    Again,
    StartOver,
    Particles(ParticleMode),
    Marks(Motion),
    Strike(Shock, Places, Lasts),
    Lift(Shock, Place),
    Grouping(Grouping),
    TablePeriod(Option<u64>),
}

/// The order of the scene's systems in `Update`.
#[derive(SystemSet, Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SceneSet {
    /// Buttons' own messages, the viewport, the script.
    Input,
    /// One command at a time on the runner; a step writes the period's frame.
    Run,
    /// Words, rings and labels, after the library has drawn.
    Paint,
}

/// The scene's one 3D camera.
#[derive(Component)]
pub struct SceneCamera;

/// A body's pick plate; the body's disc, frame and rings are its children.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub struct SceneBody(pub Party);

#[derive(Component)]
struct BodyRing;

#[derive(Resource)]
struct SceneMaterials {
    bone: Handle<StandardMaterial>,
    gold: Handle<StandardMaterial>,
}

/// The ten bodies of the plane: eight workplaces, the treasury and the fund.
#[must_use]
pub fn body_points() -> [(Party, Point); 10] {
    let workplace = |k: usize| {
        let w = Workplace::ALL[k];
        (Party::Workplace(w), (WORKPLACE_X[w.index()], 0.0))
    };
    [
        workplace(0),
        workplace(1),
        workplace(2),
        workplace(3),
        workplace(4),
        workplace(5),
        workplace(6),
        workplace(7),
        (Party::Treasury, TREASURY_AT),
        (Party::Fund, FUND_AT),
    ]
}

/// What a step did to the status: nothing for a closed period, the engine's own words for a
/// refusal, which also stops play.
#[must_use]
pub fn status_after(step: &Result<&PeriodResult, RunnerError>) -> SceneStatus {
    match step {
        Ok(_) => SceneStatus::default(),
        Err(error) => SceneStatus {
            playing: false,
            refusal: Some(error.to_string()),
        },
    }
}

/// Adds the scene to an app that already has Bevy's own plugins: the fonts, the picking of
/// meshes, the hypergraph library's field, and the scene's resources and systems. It adds none
/// of the observer's plugins and no session, pipe or reader.
///
/// # Errors
/// The runner's or the field's refusal, in words.
pub fn install_scene(app: &mut App, script: Option<PathBuf>) -> Result<(), String> {
    let runner = Runner::open().map_err(|error| error.to_string())?;
    let field = FieldPlugin::new(
        frame::field_config(),
        frame::field_styles(),
        frame::field_palette(),
    )
    .map_err(|error: FieldError| format!("the scene's field refused its styles: {error:?}"))?;
    app.add_plugins(VisualAssetsPlugin).add_systems(
        PostUpdate,
        observer_ui::apply_fonts.before(UiSystems::Content),
    );
    if !app.is_plugin_added::<MeshPickingPlugin>() {
        app.add_plugins(MeshPickingPlugin);
    }
    app.add_plugins(field)
        .insert_resource(ClearColor(FIELD))
        .insert_resource(SceneRunner {
            runner,
            mode: ParticleMode::default(),
            shown: None,
        })
        .add_plugins(SmallWorldPlugin { script });
    Ok(())
}

/// The scene's own resources, messages and systems. `install_scene` adds it last, after it
/// has opened the runner, so it is not added by itself.
pub struct SmallWorldPlugin {
    pub script: Option<PathBuf>,
}

impl Plugin for SmallWorldPlugin {
    fn build(&self, app: &mut App) {
        app.add_message::<SceneCommand>()
            .init_resource::<SceneStatus>()
            .init_resource::<SceneShown>()
            .init_resource::<PlayClock>()
            .insert_resource(SceneScript(self.script.clone()))
            .configure_sets(
                Update,
                (SceneSet::Input, SceneSet::Run)
                    .chain()
                    .before(FieldSystems::Install),
            )
            .configure_sets(Update, SceneSet::Paint.after(FieldSystems::Animate))
            .add_observer(ignore_picking)
            .add_observer(declare_surface)
            .add_systems(Startup, setup_scene)
            .add_systems(Update, fit_viewport.in_set(SceneSet::Input))
            .add_systems(Update, run_commands.in_set(SceneSet::Run))
            .add_systems(
                Update,
                (
                    show_refusals,
                    redraw_rings,
                    controls::paint_header,
                    controls::paint_buttons,
                    controls::paint_banner,
                    controls::paint_empty_line,
                    controls::place_labels,
                )
                    .chain()
                    .in_set(SceneSet::Paint),
            );
    }
}

/// The library's marks and path lines are never picked.
fn ignore_picking(event: On<Add<(MarkOf, MarkBatch, PathLines)>>, mut commands: Commands) {
    commands.entity(event.entity).insert(Pickable::IGNORE);
}

/// The library knows nothing of the client's surfaces: every mesh it spawns is the scene's.
fn declare_surface(
    event: On<Add<Mesh3d>>,
    declared: Query<(), With<DeclaredSurface>>,
    mut commands: Commands,
) {
    if !declared.contains(event.entity) {
        commands
            .entity(event.entity)
            .insert(DeclaredSurface::new(SurfaceId::SmallWorld));
    }
}

/// A flat mesh in the plane of the scene (x across, z deep), face up.
fn flat(mesh: impl Into<Mesh>) -> Mesh {
    mesh.into().rotated_by(Quat::from_rotation_x(-FRAC_PI_2))
}

fn unlit(color: Color) -> StandardMaterial {
    StandardMaterial {
        base_color: color,
        unlit: true,
        cull_mode: None,
        double_sided: true,
        ..default()
    }
}

fn setup_scene(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
) {
    spawn_cameras(&mut commands);
    let (field, bone, gold) = (
        materials.add(unlit(FIELD)),
        materials.add(unlit(BONE)),
        materials.add(unlit(GOLD)),
    );
    let plate = meshes.add(flat(Circle::new(PLATE_RADIUS)));
    let core = meshes.add(flat(Circle::new(CORE_RADIUS)));
    let frame = meshes.add(hypergraph_rs_bevy::glyph_mesh(Glyph::SquareFrame, 16));
    for (party, at) in body_points() {
        let lift = Transform::from_xyz(0.0, BODY_Y - PLATE_Y, 0.0);
        commands
            .spawn((
                Mesh3d(plate.clone()),
                MeshMaterial3d(field.clone()),
                Transform::from_translation(hypergraph_rs_bevy::plan_to_scene(at, PLATE_Y)),
                SceneBody(party),
                DeclaredSurface::new(SurfaceId::SmallWorld),
            ))
            .with_children(|body| {
                body.spawn((
                    Mesh3d(core.clone()),
                    MeshMaterial3d(gold.clone()),
                    lift,
                    DeclaredSurface::new(SurfaceId::SmallWorld),
                ));
                if matches!(party, Party::Treasury | Party::Fund) {
                    body.spawn((
                        Mesh3d(frame.clone()),
                        MeshMaterial3d(gold.clone()),
                        lift.with_scale(Vec3::splat(FRAME_SCALE)),
                        DeclaredSurface::new(SurfaceId::SmallWorld),
                    ));
                }
            });
    }
    commands.insert_resource(SceneMaterials { bone, gold });
    controls::spawn_chrome(&mut commands);
}

fn spawn_cameras(commands: &mut Commands) {
    let middle = hypergraph_rs_bevy::plan_to_scene(
        (
            f64::midpoint(PLANE.0, PLANE.2),
            f64::midpoint(PLANE.1, PLANE.3),
        ),
        0.0,
    );
    #[expect(
        clippy::cast_possible_truncation,
        reason = "the plane's extent is a few tens of units"
    )]
    let (width, depth) = ((PLANE.2 - PLANE.0) as f32, (PLANE.3 - PLANE.1) as f32);
    commands.spawn((
        Camera3d::default(),
        // The palette's colours reach the screen as they are, and the client ships no LUT.
        Tonemapping::None,
        Projection::Orthographic(OrthographicProjection {
            scaling_mode: ScalingMode::AutoMin {
                min_width: width,
                min_height: depth,
            },
            ..OrthographicProjection::default_3d()
        }),
        Msaa::Sample4,
        Transform::from_translation(middle + Vec3::Y * CAMERA_HEIGHT)
            .looking_at(middle, Vec3::NEG_Z),
        SceneCamera,
    ));
    commands.spawn((
        Camera2d,
        Camera {
            order: 10,
            clear_color: ClearColorConfig::None,
            ..default()
        },
        RenderLayers::layer(UI_LAYER),
        IsDefaultUiCamera,
    ));
}

/// The viewport is the window without the header, the control bar and the right rail. With no
/// primary window (the headless tests) it stays unset.
fn fit_viewport(
    windows: Query<&Window, With<PrimaryWindow>>,
    mut cameras: Query<&mut Camera, With<SceneCamera>>,
) {
    let (Ok(window), Ok(mut camera)) = (windows.single(), cameras.single_mut()) else {
        return;
    };
    let (width, height) = (window.width(), window.height());
    if width <= RAIL_WIDTH || height <= HEADER_HEIGHT + BAR_HEIGHT {
        return;
    }
    let scale = window.scale_factor();
    let value = Viewport {
        physical_position: (Vec2::new(0.0, HEADER_HEIGHT) * scale).as_uvec2(),
        physical_size: (Vec2::new(width - RAIL_WIDTH, height - HEADER_HEIGHT - BAR_HEIGHT) * scale)
            .as_uvec2(),
        ..default()
    };
    if camera.viewport.as_ref().is_none_or(|old| {
        old.physical_position != value.physical_position || old.physical_size != value.physical_size
    }) {
        camera.viewport = Some(value);
    }
}

/// The parts of the scene a command changes.
#[derive(SystemParam)]
struct Stage<'w> {
    scene: ResMut<'w, SceneRunner>,
    status: ResMut<'w, SceneStatus>,
    shown: ResMut<'w, SceneShown>,
    clock: ResMut<'w, PlayClock>,
    shows: MessageWriter<'w, ShowPeriod>,
    replays: MessageWriter<'w, ReplayPeriod>,
}

impl Stage<'_> {
    fn refuse(&mut self, words: String) {
        self.status.refusal = Some(words);
        self.status.playing = false;
    }

    /// Close one period and show it; a refusal stops the run and play.
    fn step(&mut self) {
        if self.status.refusal.is_some() {
            return;
        }
        let mode = self.scene.mode;
        let built = match self.scene.runner.step() {
            Ok(result) => Ok((result.period, frame::build_picture(result, mode))),
            Err(error) => Err(error),
        };
        match built {
            Ok((period, Ok(picture))) => {
                self.shows
                    .write(ShowPeriod(Box::new(picture.frame.clone())));
                self.scene.shown = Some(period);
                self.shown.0 = Some(picture);
            }
            Ok((period, Err(error))) => self.refuse(format!("Period {period}: {error}")),
            Err(error) => *self.status = status_after(&Err(error)),
        }
    }

    fn start_over(&mut self) {
        match Runner::open() {
            Ok(runner) => {
                self.scene.runner = runner;
                self.scene.shown = None;
                self.shown.0 = None;
                *self.status = SceneStatus::default();
                self.clock.0 = Duration::ZERO;
            }
            Err(error) => self.refuse(error.to_string()),
        }
    }

    fn handle(&mut self, command: SceneCommand) {
        match command {
            SceneCommand::Step => self.step(),
            SceneCommand::Play => {
                if self.status.refusal.is_none() {
                    self.status.playing = true;
                    self.clock.0 = Duration::ZERO;
                }
            }
            SceneCommand::Pause => self.status.playing = false,
            SceneCommand::Again => {
                if self.scene.shown.is_some() {
                    self.replays.write(ReplayPeriod);
                }
            }
            SceneCommand::StartOver => self.start_over(),
            // The particle switch, the marks' motion, the shocks and the table are the next
            // task's: no control of this scene writes them yet.
            SceneCommand::Particles(_)
            | SceneCommand::Marks(_)
            | SceneCommand::Strike(..)
            | SceneCommand::Lift(..)
            | SceneCommand::Grouping(_)
            | SceneCommand::TablePeriod(_) => {}
        }
    }
}

fn run_commands(mut commands: MessageReader<SceneCommand>, time: Res<Time>, mut stage: Stage) {
    for command in commands.read() {
        stage.handle(command.clone());
    }
    if stage.status.playing {
        stage.clock.0 += time.delta();
        if stage.clock.0 >= PLAY_INTERVAL {
            stage.clock.0 -= PLAY_INTERVAL;
            stage.step();
        }
    }
}

/// A frame the library refuses is shown as the refusal, in its own words, and stops play.
fn show_refusals(mut refused: MessageReader<FrameRefused>, mut status: ResMut<SceneStatus>) {
    for refusal in refused.read() {
        status.refusal = Some(format!(
            "Period {}: the picture was refused: {}",
            refusal.period, refusal.error
        ));
        status.playing = false;
    }
}

/// One ring of a body: a ribbon round the plate's centre at a height above the plate.
fn ring_mesh(radius: f32, dash: Option<(f64, f64)>, height: f32) -> Result<Mesh, FieldError> {
    let outline = Outline::Ring {
        center: (0.0, 0.0),
        radius: f64::from(radius),
    };
    let segments: Vec<(Point, Point)> = hypergraph_rs_bevy::outline_paths(&outline, RING_SEGMENTS)?
        .iter()
        .flat_map(|path| hypergraph_rs_bevy::dashed(path, dash))
        .collect();
    Ok(hypergraph_rs_bevy::ribbon_mesh(
        &segments, RING_WIDTH, height,
    ))
}

/// Redraw every ring when a picture is shown; none while no period is shown.
fn redraw_rings(
    mut commands: Commands,
    shown: Res<SceneShown>,
    materials: Option<Res<SceneMaterials>>,
    rings: Query<Entity, With<BodyRing>>,
    plates: Query<(Entity, &SceneBody)>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut status: ResMut<SceneStatus>,
) {
    if !shown.is_changed() {
        return;
    }
    for ring in &rings {
        commands.entity(ring).despawn();
    }
    let (Some(picture), Some(materials)) = (shown.0.as_ref(), materials) else {
        return;
    };
    for body in &picture.bodies {
        let Some((plate, _)) = plates.iter().find(|(_, scene)| scene.0 == body.party) else {
            continue;
        };
        for (radius, dash, height, material) in ring_specs(body, &materials) {
            match ring_mesh(radius, dash, height) {
                Ok(mesh) => {
                    commands.entity(plate).with_child((
                        Mesh3d(meshes.add(mesh)),
                        MeshMaterial3d(material),
                        BodyRing,
                        Pickable::IGNORE,
                        DeclaredSurface::new(SurfaceId::SmallWorld),
                    ));
                }
                Err(error) => {
                    status.refusal = Some(format!("A ring could not be drawn: {error}"));
                    status.playing = false;
                }
            }
        }
    }
}

/// One ring: radius, dash, height above its plate and colour.
type RingSpec = (f32, Option<(f64, f64)>, f32, Handle<StandardMaterial>);

/// The rings a body shows.
fn ring_specs(body: &BodyPicture, materials: &SceneMaterials) -> Vec<RingSpec> {
    let mut specs = Vec::new();
    if let Some(radius) = body.hours_ring {
        specs.push((
            radius,
            Some(HOURS_DASH),
            HOURS_RING_Y - PLATE_Y,
            materials.bone.clone(),
        ));
    }
    if let Some(radius) = body.money_ring {
        specs.push((radius, None, MONEY_RING_Y - PLATE_Y, materials.gold.clone()));
    }
    specs
}

#[cfg(test)]
#[path = "scene_tests.rs"]
mod tests;
