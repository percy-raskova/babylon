//! The county map render lane (B1 Tasks 6-7): `MapPlugin` ties the
//! embedded atlas, `earcutr` tessellation, mesh-building and the bounded
//! pan/zoom camera together into three spawned entities — the choropleth
//! fill, the county-border overlay, and the map's own `Camera2d`.

mod bands;
mod camera;
mod hud;
mod mesh;
mod pick;

pub use bands::PANEL;
pub use camera::{clamp_camera, closest_in_zoom, whole_map_zoom, MapBounds};
pub use mesh::{MapBorders, MapFill, MapSurface, EXPECTED_VERTEX_COUNT};

use bevy::camera_controller::pan_camera::PanCameraPlugin;
use bevy::input::InputPlugin;
use bevy::prelude::*;

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
        app.add_systems(Startup, (mesh::spawn_map_surface, camera::spawn_camera));
        app.add_systems(
            Update,
            (
                camera::resize_camera_bounds_system,
                camera::clamp_camera_system,
            ),
        );
    }
}
