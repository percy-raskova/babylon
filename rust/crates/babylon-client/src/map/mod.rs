//! The county map render lane (B1 Tasks 6-7, B2 Phase C Tasks 8-12):
//! `MapPlugin` ties the embedded atlas, `earcutr` tessellation,
//! mesh-building, the bounded pan/zoom camera, county hover/selection and
//! the 3-way lens picker together.
//!
//! **Sequencing note (B2 Task 12).** The plan's own text has Task 12
//! register `bands::recolor_on_lens_changed` inside `MapPlugin`. That
//! system reads `Res<crate::lens::CurrentLensData>`, which nothing in
//! `MapPlugin` ever inserts — `EngineSession`/`CurrentLensData` are Task
//! 13/14's own `TickLoopPlugin` responsibility. Registering it here would
//! panic on the very first `Update` pass for every test (including this
//! task's OWN Step 1 test, which adds `MapPlugin` alone) and for every
//! ALREADY-PASSING pre-existing test (`tests/map_mesh.rs`,
//! `tests/map_camera.rs`) that builds an app from `MapPlugin` without ever
//! providing `CurrentLensData`. `recolor_on_lens_changed` (and
//! `hud::refresh_hud`, which needs the same resource) move to
//! `TickLoopPlugin` (Task 14) instead, which is the plugin that actually
//! owns `CurrentLensData`'s lifecycle — the real app (`main.rs`) always
//! adds both plugins together, so this is a registration-site move with no
//! behavior change for the shipped game.

mod bands;
mod camera;
mod hud;
mod mesh;
mod pick;

pub use bands::{ActiveLens, LensChanged, PANEL};
pub use camera::{clamp_camera, closest_in_zoom, whole_map_zoom, MapBounds};
pub use hud::{AbsenceBanner, CountyHudText, HudTick};
pub use mesh::{spawn_map_surface, MapBorders, MapFill, MapSurface, EXPECTED_VERTEX_COUNT};
pub use pick::{CountyIndex, CursorWorldPosition, HoveredCounty, SelectedCounty};

pub(crate) use bands::recolor_on_lens_changed;
pub(crate) use hud::refresh_hud;

use bevy::camera_controller::pan_camera::PanCameraPlugin;
use bevy::input::keyboard::KeyCode;
use bevy::input::{ButtonInput, InputPlugin};
use bevy::prelude::*;

/// `Update` system: `Tab` cycles the active lens
/// `Tension -> Legitimation -> PopulationTrend -> Tension`, a `match`
/// naming all three arms explicitly so no wraparound bug can hide, and
/// fires `LensChanged`.
///
/// `pub(crate)`, not private (FB7, adversarial-panel MINOR):
/// `TickLoopPlugin`'s `recolor_on_lens_changed`/`refresh_hud` registration
/// orders `.after(advance_on_space)` (the FB1 ordering fix) but was silent
/// on ordering against THIS system — a Tab press and a same-frame recolor
/// pass are cross-plugin, so nothing implied an order between them.
/// `loop_ui.rs` names this function directly in its own `.after(...)`.
pub(crate) fn cycle_lens_on_tab(
    keys: Res<ButtonInput<KeyCode>>,
    mut active: ResMut<ActiveLens>,
    mut lens_changed: MessageWriter<LensChanged>,
) {
    if !keys.just_pressed(KeyCode::Tab) {
        return;
    }
    *active = match *active {
        ActiveLens::Tension => ActiveLens::Legitimation,
        ActiveLens::Legitimation => ActiveLens::PopulationTrend,
        ActiveLens::PopulationTrend => ActiveLens::Tension,
    };
    lens_changed.write(LensChanged);
}

/// Wires the county map's render lane into a Bevy `App`.
///
/// Depends only on `Assets<Mesh>`, `Assets<ColorMaterial>` and the input
/// resources `PanCameraPlugin`'s system reads existing — it registers
/// `bevy::mesh::MeshPlugin`, `bevy::sprite_render::ColorMaterialPlugin` and
/// `bevy::input::InputPlugin` itself when they are not already present.
/// The CI-shaped headless test (Task 6 Step 1) adds only `MinimalPlugins` +
/// `AssetPlugin`, none of which registers those types on their own; the
/// real client adds all three transitively via `DefaultPlugins` already,
/// so the `is_plugin_added` guard here avoids Bevy's duplicate-unique-
/// plugin panic there. All three plugins are pure ECS resource/asset
/// registration with no display or GPU dependency (`ColorMaterialPlugin`'s
/// render-sub-app-only setup is itself guarded internally with `if let
/// Some(render_app) = app.get_sub_app_mut(RenderApp)`), so adding them
/// under `MinimalPlugins` needs no display server, no GPU and no window —
/// the CI reality this whole plan holds to. `PanCameraPlugin` itself is
/// never part of `DefaultPlugins` (it is not a core rendering plugin), so
/// it is added unconditionally.
pub struct MapPlugin;

impl Plugin for MapPlugin {
    fn build(&self, app: &mut App) {
        if !app.is_plugin_added::<bevy::mesh::MeshPlugin>() {
            app.add_plugins(bevy::mesh::MeshPlugin);
        }
        if !app.is_plugin_added::<bevy::sprite_render::ColorMaterialPlugin>() {
            app.add_plugins(bevy::sprite_render::ColorMaterialPlugin);
        }
        if !app.is_plugin_added::<InputPlugin>() {
            app.add_plugins(InputPlugin);
        }
        app.add_plugins(PanCameraPlugin);
        app.add_message::<LensChanged>();
        app.insert_resource(ActiveLens::PopulationTrend);
        app.init_resource::<pick::CursorWorldPosition>();
        app.init_resource::<pick::HoveredCounty>();
        app.init_resource::<pick::SelectedCounty>();
        app.init_resource::<hud::HudTick>();
        app.add_systems(
            Startup,
            (
                mesh::spawn_map_surface,
                camera::spawn_camera,
                pick::build_county_index,
                hud::spawn_hud,
            ),
        );
        app.add_systems(
            Update,
            (
                camera::resize_camera_bounds_system,
                camera::clamp_camera_system,
                pick::track_cursor_world_position,
                pick::update_hovered_county,
                pick::promote_selection_on_click,
                pick::update_selection_outline,
                cycle_lens_on_tab,
            )
                .chain(),
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::asset::AssetPlugin;
    use bevy::input::keyboard::KeyboardInput;
    use bevy::input::ButtonState;

    /// Presses `key` through the REAL `KeyboardInput` message pipeline
    /// rather than mutating `ButtonInput` directly. Necessary (not
    /// stylistic) whenever `InputPlugin` is genuinely present (as it is
    /// here — `MapPlugin` conditionally self-adds it): `InputPlugin`'s own
    /// `PreUpdate` `keyboard_input_system` unconditionally clears
    /// `just_pressed`/`just_released` every frame to make room for real
    /// events, before re-populating them from whatever `KeyboardInput`
    /// messages arrived — a direct `ButtonInput::press()` call made from
    /// outside any schedule (i.e. from test code, before `app.update()`)
    /// gets wiped by that same clear before an `Update`-scheduled system
    /// like `cycle_lens_on_tab` ever observes it. Writing a real message
    /// instead lets `keyboard_input_system`'s own event-driven logic set
    /// `just_pressed` correctly, exactly as a genuine winit key event
    /// would. `window: Entity::PLACEHOLDER` is safe — `keyboard_input_system`
    /// never reads the `window` field when updating `ButtonInput`.
    fn press_key_via_real_event(app: &mut App, key: bevy::input::keyboard::KeyCode) {
        app.world_mut()
            .resource_mut::<Messages<KeyboardInput>>()
            .write(KeyboardInput {
                key_code: key,
                logical_key: bevy::input::keyboard::Key::Unidentified(
                    bevy::input::keyboard::NativeKey::Unidentified,
                ),
                state: ButtonState::Pressed,
                text: None,
                repeat: false,
                window: Entity::PLACEHOLDER,
            });
    }

    #[derive(Resource, Default)]
    struct LensChangedCount(usize);

    fn count_lens_changed(
        mut messages: MessageReader<LensChanged>,
        mut count: ResMut<LensChangedCount>,
    ) {
        count.0 += messages.read().count();
    }

    #[test]
    fn tab_cycles_the_active_lens_and_fires_lens_changed_each_press() {
        let mut app = App::new();
        app.add_plugins((MinimalPlugins, AssetPlugin::default()));
        app.add_plugins(MapPlugin);
        app.init_resource::<LensChangedCount>();
        // `.after(cycle_lens_on_tab)`: unordered relative to MapPlugin's
        // own `.chain()`'d systems otherwise, which can run this BEFORE
        // cycle_lens_on_tab writes the frame's message — undercounting by
        // exactly one (verified: without this, 3 presses counted 2).
        app.add_systems(Update, count_lens_changed.after(cycle_lens_on_tab));
        app.update(); // Startup.

        assert_eq!(
            *app.world().resource::<ActiveLens>(),
            ActiveLens::PopulationTrend,
            "the startup default must be PopulationTrend (Tension is unconditionally absent \
             on this demo content — Task 8's own finding)"
        );

        let mut seen = vec![*app.world().resource::<ActiveLens>()];
        for _ in 0..3 {
            press_key_via_real_event(&mut app, KeyCode::Tab);
            app.update();
            seen.push(*app.world().resource::<ActiveLens>());
            // `ButtonInput::press` only sets `just_pressed` on a genuine
            // NOT-pressed -> pressed transition — without releasing
            // between taps, `keyboard_input_system`'s own Pressed-event
            // handling sees the key already held and never re-arms
            // `just_pressed`, so every press after the first would be
            // silently swallowed. Release directly (not through another
            // event + update cycle): this only needs to flip the `pressed`
            // set, which `clear()` never touches, so it survives into the
            // next iteration's fresh Pressed event correctly.
            app.world_mut()
                .resource_mut::<ButtonInput<KeyCode>>()
                .release(KeyCode::Tab);
        }

        assert_eq!(
            seen,
            vec![
                ActiveLens::PopulationTrend,
                ActiveLens::Tension,
                ActiveLens::Legitimation,
                ActiveLens::PopulationTrend,
            ],
            "three presses from the default must visit every lens once and return to start"
        );
        assert_eq!(
            app.world().resource::<LensChangedCount>().0,
            3,
            "every press must fire LensChanged"
        );
    }
}
