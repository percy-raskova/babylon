//! PER-23 Slice 3 app construction (ADR249 R11): [`build_app`] assembles
//! the Bevy `App` for exactly two modes — the windowed administrative
//! viewer and the headless dossier CLI. Extracting this from `main` lets
//! both modes share one construction site, keeps `main` a pure dispatch
//! shim, and gives tests one function to exercise.

use bevy::app::MainScheduleOrder;
use bevy::camera::{NormalizedRenderTarget, RenderTarget};
use bevy::ecs::schedule::ScheduleLabel;
use bevy::log::LogPlugin;
use bevy::prelude::*;
use bevy::window::{MonitorSelection, PrimaryWindow, WindowCloseRequested, WindowPosition};

use crate::cli::CliCommand;
use crate::dossier::HeadlessInvocation;
use crate::observer::ObserverSession;
use crate::observer_focus::ObserverFocusPlugin;
use crate::observer_io::qualification::NativeAudit;
use crate::observer_io::ObserverIoPlugin;
use crate::observer_ui::ObserverShellPlugin;
use crate::organizer::qualification_input::Transport;
use crate::production::PrimaryView;
use crate::{logging, map, session_log, ui, visual_assets};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::runtime_session::RuntimeSessionTarget;
use std::path::PathBuf;

/// Which executable shape [`build_app`] assembles.
#[derive(Clone, Debug)]
pub enum AppMode {
    /// The persistent observer with one initial lifecycle destination.
    Windowed {
        /// Explicit New or existing-only Open, submitted after runtime Hello.
        initial_target: RuntimeSessionTarget,
        /// An explicitly requested private harness channel; ordinary play uses None.
        qualification_control: Option<PathBuf>,
    },
    /// One headless dossier command: JSONL on stdout, logs on stderr,
    /// process exit after the first update.
    Headless {
        /// The parsed dossier command.
        command: CliCommand,
        /// The canonical campaign identity.
        campaign_id: CampaignId,
    },
}

/// Assemble the Bevy `App` for one mode. Windowed keeps the pinned
/// `DefaultPlugins` estate (file + stderr logging, window title); headless
/// rides `MinimalPlugins` plus the pinned `LogPlugin` alone — no window,
/// no render, no visual plugins — and runs exactly one Startup system.
///
/// # Errors
/// Refuses an invalid initial lifecycle target before creating a window.
pub fn build_app(mode: AppMode) -> Result<App, String> {
    let mut app = App::new();
    match mode {
        AppMode::Windowed {
            initial_target,
            qualification_control,
        } => {
            let session = ObserverSession::with_initial_target(initial_target)?;
            let qualification = qualification_control
                .as_deref()
                .map(|path| Transport::connect(path, &session.campaign.as_uuid().to_string()))
                .transpose()?;
            let audit = if qualification.is_some() {
                NativeAudit::from_env(session.campaign)?
            } else {
                None
            };
            let campaign_id = session.campaign;
            app.add_plugins(
                DefaultPlugins
                    .set(LogPlugin {
                        filter: format!(
                            "{},babylon_client=debug,session=debug",
                            bevy::log::DEFAULT_FILTER
                        ),
                        custom_layer: logging::file_layer,
                        fmt_layer: logging::stderr_fmt_layer,
                        ..default()
                    })
                    .set(WindowPlugin {
                        close_when_requested: false,
                        primary_window: Some(Window {
                            title: "Babylon — The Fall of America".into(),
                            resolution: (1366, 768).into(),
                            position: WindowPosition::Centered(MonitorSelection::Primary),
                            ..default()
                        }),
                        ..default()
                    }),
            );
            install_window_camera_coherence(&mut app);
            // Nothing listens before LogPlugin::build installs the
            // subscriber, so the startup line stays after add_plugins. The
            // line stays static: no parse-channel value is logged.
            log::info!("babylon-client starting (durable observer)");
            app.add_plugins(visual_assets::VisualAssetsPlugin)
                .add_plugins(map::MapPlugin)
                .add_plugins(ObserverFocusPlugin)
                .add_plugins(ObserverShellPlugin)
                .add_plugins(crate::observer_opening::OpeningPlugin)
                .add_plugins(crate::observer_map3d::ObserverMap3dPlugin)
                .add_plugins(ObserverIoPlugin)
                .add_plugins(crate::production::ProductionPlugin)
                .add_plugins(crate::observer_audio::ObserverAudioPlugin)
                .add_plugins(crate::campaign_browser::CampaignBrowserPlugin)
                .add_plugins(crate::observer_history::ObserverHistoryPlugin)
                .add_plugins(crate::organizer::OrganizerPlugin)
                .add_plugins(crate::observer_performance::ObserverPerformancePlugin)
                // The card and telemetry consume the same scoped Archive resources.
                .add_plugins(ui::dossier_card::DossierCardPlugin)
                .add_plugins(session_log::SessionLogPlugin)
                .insert_resource(PrimaryView::Map)
                .insert_resource(session)
                .insert_resource(ui::dossier_card::DossierCampaignId(campaign_id))
                .insert_resource(ClearColor(crate::observer_theme::INK))
                .add_systems(PreUpdate, forward_native_close);
            if let Some(transport) = qualification {
                crate::organizer::qualification_input::install(&mut app, transport);
            }
            if let Some(audit) = audit {
                app.insert_resource(audit);
            }
        }
        AppMode::Headless {
            command,
            campaign_id,
        } => {
            app.add_plugins(MinimalPlugins)
                .add_plugins(LogPlugin {
                    filter: format!(
                        "{},babylon_client=debug,session=debug",
                        bevy::log::DEFAULT_FILTER
                    ),
                    custom_layer: logging::file_layer,
                    fmt_layer: logging::stderr_fmt_layer,
                    ..default()
                })
                .insert_resource(HeadlessInvocation::new(command, campaign_id))
                .add_systems(Startup, crate::dossier::run_headless_command);
        }
    }
    Ok(app)
}

#[derive(ScheduleLabel, Clone, Debug, PartialEq, Eq, Hash)]
struct WindowCameraCoherence;

fn camera_target_mismatch(
    camera: &Camera,
    target: &RenderTarget,
    window: Entity,
    extent: UVec2,
) -> bool {
    matches!(target.normalize(Some(window)), Some(NormalizedRenderTarget::Window(target)) if target.entity() == window)
        && camera.physical_target_size() != Some(extent)
}

fn window_camera_mismatch(
    windows: Query<(Entity, &Window), With<PrimaryWindow>>,
    cameras: Query<(&Camera, &RenderTarget)>,
) -> bool {
    let Ok((entity, window)) = windows.single() else {
        return false;
    };
    let extent = UVec2::new(window.physical_width(), window.physical_height());
    cameras
        .iter()
        .any(|(camera, target)| camera_target_mismatch(camera, target, entity, extent))
}

fn invalidate_window_cameras(
    windows: Query<(Entity, &Window), With<PrimaryWindow>>,
    mut cameras: Query<(&Camera, &RenderTarget, &mut Projection)>,
) {
    let Ok((entity, window)) = windows.single() else {
        return;
    };
    let extent = UVec2::new(window.physical_width(), window.physical_height());
    for (camera, target, mut projection) in &mut cameras {
        if camera_target_mismatch(camera, target, entity, extent) {
            projection.set_changed();
        }
    }
}

fn install_window_camera_coherence(app: &mut App) {
    // Winit can change the window again in Last, after Bevy's camera update.
    // Reuse Bevy's camera system before render extraction without fabricating
    // a WindowResized message, which is also an OS observation for controls.
    app.world_mut()
        .resource_mut::<MainScheduleOrder>()
        .insert_after(Last, WindowCameraCoherence);
    app.add_systems(
        WindowCameraCoherence,
        (
            invalidate_window_cameras,
            bevy::render::camera::camera_system,
        )
            .chain()
            .run_if(window_camera_mismatch),
    );
    app.add_systems(
        WindowCameraCoherence,
        crate::organizer::qualification_input::observe_window_after_last
            .after(bevy::render::camera::camera_system),
    );
}

// Closing the desktop window follows the same draft flush and acknowledged
// runtime shutdown as Quit. The window stays alive until that path emits AppExit.
fn forward_native_close(
    mut requests: MessageReader<WindowCloseRequested>,
    primary: Query<Entity, With<PrimaryWindow>>,
    mut commands: MessageWriter<crate::observer_ui::ObserverCommand>,
) {
    let mut close_primary = false;
    for request in requests.read() {
        close_primary |= primary.contains(request.window);
    }
    if close_primary {
        commands.write(crate::observer_ui::ObserverCommand::Quit);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cli::CliCommand;
    use crate::test_support::EnvVarGuard;
    use babylon_persistence::identity::CampaignId;
    use babylon_persistence::runtime_session::RuntimeSessionTarget;
    use uuid::Uuid;

    #[test]
    fn native_close_forwards_one_quit_and_keeps_the_window_until_shutdown() {
        use crate::observer_ui::ObserverCommand;
        let mut app = App::new();
        app.add_plugins((
            MinimalPlugins,
            crate::test_support::HeadlessVisibilityPlugin,
        ))
        .add_message::<WindowCloseRequested>()
        .add_message::<ObserverCommand>()
        .add_systems(PreUpdate, forward_native_close);
        let window = app.world_mut().spawn(PrimaryWindow).id();
        let other = app.world_mut().spawn_empty().id();
        for target in [other, window, window] {
            app.world_mut()
                .write_message(WindowCloseRequested { window: target });
        }
        app.update();
        assert_eq!(
            app.world_mut()
                .resource_mut::<Messages<ObserverCommand>>()
                .drain()
                .collect::<Vec<_>>(),
            [ObserverCommand::Quit]
        );
        assert!(app.world().get_entity(window).is_ok());
    }

    #[test]
    fn invalid_initial_target_refuses_before_window_construction() {
        let result = build_app(AppMode::Windowed {
            qualification_control: None,
            initial_target: RuntimeSessionTarget::Open {
                campaign_id: "not-a-campaign".into(),
            },
        });
        assert!(result.is_err());
    }

    #[test]
    fn headless_mode_builds_a_minimal_app_that_exits_after_startup() {
        // Isolate the test from any ambient reader DSN: a live DSN would
        // make the command succeed and defeat the exit-code assertion. The
        // guard serializes against other env-mutating tests and restores
        // the ambient value on drop.
        let env = EnvVarGuard::lock(babylon_persistence::READER_DSN_ENV);
        env.remove();
        let mut app = build_app(AppMode::Headless {
            command: CliCommand::TickStatus,
            campaign_id: CampaignId::from_uuid(Uuid::nil()),
        })
        .expect("headless mode needs no initial lifecycle target");
        assert!(!app.is_plugin_added::<ObserverFocusPlugin>());
        assert!(app
            .world()
            .get_resource::<crate::observer_focus::ObserverFocusPolicy>()
            .is_none());
        assert!(
            app.world().get_resource::<HeadlessInvocation>().is_some(),
            "the invocation resource is installed before Startup"
        );
        app.update();
        // Without a reader DSN the command refuses with exit code 2, and
        // the AppExit message must be queued: the app must not hang.
        let mut messages = app.world_mut().resource_mut::<Messages<AppExit>>();
        let exit = messages.drain().next().expect("the headless run exits");
        assert!(
            matches!(exit, AppExit::Error(code) if code.get() == 2),
            "a refused command exits non-zero, got {exit:?}"
        );
    }
    fn resize_camera_app() -> (App, Entity, [Entity; 2]) {
        use bevy::asset::{AssetEvent, Assets};
        use bevy::camera::Viewport;
        use bevy::render::camera;
        use bevy::render::texture::ManualTextureViews;
        use bevy::window::{WindowCreated, WindowResized, WindowScaleFactorChanged};

        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .init_resource::<Assets<Image>>()
            .init_resource::<ManualTextureViews>()
            .add_message::<AssetEvent<Image>>()
            .add_message::<WindowCreated>()
            .add_message::<WindowResized>()
            .add_message::<WindowScaleFactorChanged>()
            .add_systems(PostUpdate, camera::camera_system);
        install_window_camera_coherence(&mut app);
        let window = app
            .world_mut()
            .spawn((
                Window {
                    resolution: (1920, 1080).into(),
                    ..default()
                },
                PrimaryWindow,
            ))
            .id();
        let ui = app.world_mut().spawn(Camera2d).id();
        let map = app
            .world_mut()
            .spawn((
                Camera3d::default(),
                Camera {
                    viewport: Some(Viewport {
                        physical_position: UVec2::new(20, 20),
                        physical_size: UVec2::new(800, 500),
                        ..default()
                    }),
                    ..default()
                },
            ))
            .id();
        app.update();
        app.update();
        (app, window, [ui, map])
    }

    fn assert_camera_extents(app: &App, cameras: [Entity; 2], extent: UVec2) {
        for entity in cameras {
            let camera = app.world().get::<Camera>(entity).expect("camera exists");
            assert_eq!(camera.physical_target_size(), Some(extent));
            if let Some(viewport) = &camera.viewport {
                assert!((viewport.physical_position + viewport.physical_size)
                    .cmple(extent)
                    .all());
            }
        }
    }

    #[test]
    fn window_resize_keeps_camera_targets_coherent_before_extraction() {
        let (mut app, window, cameras) = resize_camera_app();
        assert_camera_extents(&app, cameras, UVec2::new(1920, 1080));
        app.world_mut()
            .get_mut::<Window>(window)
            .expect("window exists")
            .resolution
            .set_physical_resolution(1366, 768);
        app.update();
        assert_camera_extents(&app, cameras, UVec2::new(1366, 768));
    }

    #[derive(Resource, Default)]
    struct LateWindowExtent(Option<UVec2>);

    fn apply_late_window_extent(
        mut pending: ResMut<LateWindowExtent>,
        mut windows: Query<&mut Window, With<PrimaryWindow>>,
    ) {
        if let Some(extent) = pending.0.take() {
            windows
                .single_mut()
                .expect("one window")
                .resolution
                .set_physical_resolution(extent.x, extent.y);
        }
    }

    #[test]
    fn late_backend_resize_keeps_camera_targets_coherent() {
        let (mut app, _window, cameras) = resize_camera_app();
        app.insert_resource(LateWindowExtent(Some(UVec2::new(1280, 720))))
            .add_systems(Last, apply_late_window_extent);
        app.update();
        assert_camera_extents(&app, cameras, UVec2::new(1280, 720));
    }

    #[test]
    fn os_resize_event_updates_both_camera_targets() {
        use bevy::window::WindowResized;
        let (mut app, window, cameras) = resize_camera_app();
        app.world_mut()
            .get_mut::<Window>(window)
            .expect("window exists")
            .resolution
            .set_physical_resolution(1366, 768);
        app.world_mut().write_message(WindowResized {
            window,
            width: 1366.0,
            height: 768.0,
        });
        app.update();
        assert_camera_extents(&app, cameras, UVec2::new(1366, 768));
    }

    #[test]
    fn late_resize_does_not_repeat_scale_factor_viewport_adjustment() {
        use bevy::window::WindowScaleFactorChanged;
        let (mut app, window, cameras) = resize_camera_app();
        app.world_mut()
            .get_mut::<Camera>(cameras[1])
            .expect("map camera exists")
            .viewport
            .as_mut()
            .expect("map viewport exists")
            .physical_size = UVec2::splat(100);
        app.update();
        app.world_mut()
            .get_mut::<Window>(window)
            .expect("window exists")
            .resolution
            .set_scale_factor(2.0);
        app.world_mut().write_message(WindowScaleFactorChanged {
            window,
            scale_factor: 2.0,
        });
        app.insert_resource(LateWindowExtent(Some(UVec2::new(1366, 768))))
            .add_systems(Last, apply_late_window_extent);
        app.update();
        assert_camera_extents(&app, cameras, UVec2::new(1366, 768));
        let camera = app
            .world()
            .get::<Camera>(cameras[1])
            .expect("map camera exists");
        let viewport = camera.viewport.as_ref().expect("map viewport exists");
        assert_eq!(viewport.physical_position, UVec2::splat(40));
        assert_eq!(viewport.physical_size, UVec2::splat(200));
    }

    #[test]
    fn unchanged_window_does_not_mutate_camera_projection() {
        use bevy::ecs::change_detection::DetectChanges;
        let (mut app, _window, cameras) = resize_camera_app();
        let before: Vec<_> = cameras
            .iter()
            .map(|entity| {
                app.world()
                    .entity(*entity)
                    .get_ref::<Projection>()
                    .expect("projection exists")
                    .last_changed()
            })
            .collect();
        app.update();
        let after: Vec<_> = cameras
            .iter()
            .map(|entity| {
                app.world()
                    .entity(*entity)
                    .get_ref::<Projection>()
                    .expect("projection exists")
                    .last_changed()
            })
            .collect();
        assert_eq!(before, after);
    }
}
