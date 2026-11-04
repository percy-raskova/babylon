//! Test-only helpers shared across the crate's unit tests.

use bevy::camera::visibility::InheritedVisibility;
use bevy::ecs::schedule::IntoScheduleConfigs as _;
use bevy::input_focus::InputFocusSystems;
use bevy::math::Vec2;
use bevy::prelude::{App, Bundle, Font, Handle, Plugin, PreUpdate, Query};
use std::ffi::OsString;
use std::sync::PoisonError;
use std::sync::{Mutex, MutexGuard};

/// Serializes tests that mutate process-global environment state.
static ENV_LOCK: Mutex<()> = Mutex::new(());

/// Locks [`ENV_LOCK`] and restores the guarded variable's prior value on
/// drop. Rust test threads run in one process, so a test that sets or
/// removes a variable must both serialize against its peers and put the
/// ambient value back; otherwise a dev box with `BABYLON_CAMPAIGN_ID` or
/// `BABYLON_READER_DSN` exported changes what unrelated tests see.
pub(crate) struct EnvVarGuard {
    _lock: MutexGuard<'static, ()>,
    key: &'static str,
    prior: Option<OsString>,
}

impl EnvVarGuard {
    /// Locks the environment and remembers `key`'s prior value.
    pub(crate) fn lock(key: &'static str) -> Self {
        let lock = ENV_LOCK.lock().unwrap_or_else(PoisonError::into_inner);
        let prior = std::env::var_os(key);
        Self {
            _lock: lock,
            key,
            prior,
        }
    }

    /// Sets the guarded variable for the lifetime of this guard.
    pub(crate) fn set(&self, value: &str) {
        std::env::set_var(self.key, value);
    }

    /// Removes the guarded variable for the lifetime of this guard.
    pub(crate) fn remove(&self) {
        std::env::remove_var(self.key);
    }
}

impl Drop for EnvVarGuard {
    fn drop(&mut self) {
        match self.prior.take() {
            Some(value) => std::env::set_var(self.key, value),
            None => std::env::remove_var(self.key),
        }
    }
}

/// Marks every UI node visible, standing in for the render pipeline.
///
/// Bevy 0.20's tab navigation skips descendants whose `InheritedVisibility` is
/// false, and only the visibility plugin (installed by the render stack)
/// computes that component from the `Visibility` hierarchy. A headless fixture
/// runs no renderer and never spawns a camera, so every node would stay
/// invisible and no control could ever be tabbed to. The observer's own focus
/// tree still decides tabbability from `Display`, `Visibility`, and policy, so
/// modelling "rendered and visible" here preserves the fixture's intent.
pub(crate) struct HeadlessVisibilityPlugin;

impl Plugin for HeadlessVisibilityPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(
            PreUpdate,
            reveal_ui_nodes.before(InputFocusSystems::Dispatch),
        );
    }
}

fn reveal_ui_nodes(mut nodes: Query<&mut InheritedVisibility>) {
    for mut visibility in &mut nodes {
        if !visibility.get() {
            *visibility = InheritedVisibility::VISIBLE;
        }
    }
}

/// Creates the real-font UI layout environment shared by text measurement tests.
pub(crate) fn ui_text_app() -> (App, Handle<Font>) {
    use bevy::app::{HierarchyPropagatePlugin, PostUpdate, PropagateSet};
    use bevy::asset::{AssetPlugin, Assets};
    use bevy::camera::{ComputedCameraValues, RenderTargetInfo, Viewport};
    use bevy::prelude::*;
    use bevy::text::{self, TextPlugin};
    use bevy::ui::ui_surface::UiSurface;
    use bevy::ui::{self, update, widget, ComputedUiRenderTargetInfo, ComputedUiTargetCamera};

    let mut app = App::new();
    app.add_plugins((
        MinimalPlugins,
        AssetPlugin::default(),
        TextPlugin,
        HierarchyPropagatePlugin::<ComputedUiTargetCamera>::new(PostUpdate),
        HierarchyPropagatePlugin::<ComputedUiRenderTargetInfo>::new(PostUpdate),
    ))
    .init_resource::<UiScale>()
    .init_resource::<UiSurface>()
    .add_systems(
        PostUpdate,
        (
            update::propagate_ui_target_cameras,
            widget::measure_text_system
                .after(text::load_font_assets_into_font_collection)
                .after(text::detect_text_needs_rerender),
            ui::ui_layout_system,
        )
            .chain(),
    )
    .configure_sets(
        PostUpdate,
        (
            PropagateSet::<ComputedUiTargetCamera>::default(),
            PropagateSet::<ComputedUiRenderTargetInfo>::default(),
        )
            .after(update::propagate_ui_target_cameras)
            .before(widget::measure_text_system),
    );
    let viewport = UVec2::new(1366, 768);
    app.world_mut().spawn((
        Camera2d,
        Camera {
            computed: ComputedCameraValues {
                target_info: Some(RenderTargetInfo {
                    physical_size: viewport,
                    scale_factor: 1.0,
                }),
                ..default()
            },
            viewport: Some(Viewport {
                physical_size: viewport,
                ..default()
            }),
            ..default()
        },
    ));
    let font = Font::from_bytes(
        include_bytes!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../assets/fonts/SourceSans3[wght].ttf"
        ))
        .to_vec(),
    );
    let font = app.world_mut().resource_mut::<Assets<Font>>().add(font);
    (app, font)
}

/// Measures a production text bundle through Bevy's real font and UI layout systems.
pub(crate) fn measure_ui_text(bundle: impl Bundle) -> Vec2 {
    use bevy::prelude::*;

    let (mut app, font) = ui_text_app();
    let leaf = app.world_mut().spawn(bundle).id();
    app.world_mut()
        .get_mut::<TextFont>(leaf)
        .expect("production text supplies a font")
        .font = font.into();
    let root = app
        .world_mut()
        .spawn(Node {
            width: px(640),
            height: px(300),
            align_items: AlignItems::Start,
            ..default()
        })
        .id();
    app.world_mut().entity_mut(root).add_child(leaf);
    app.finish();
    app.cleanup();
    for _ in 0..4 {
        app.update();
    }
    app.world()
        .get::<ComputedNode>(leaf)
        .expect("production text has computed layout")
        .size()
}
