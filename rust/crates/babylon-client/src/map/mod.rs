//! The county map render lane (B1 Task 6): `MapPlugin` ties the embedded
//! atlas, `earcutr` tessellation and mesh-building together into two
//! spawned entities — the choropleth fill and the county-border overlay.

mod mesh;

pub use mesh::{MapBorders, MapFill, MapSurface, EXPECTED_VERTEX_COUNT};

use bevy::prelude::*;

/// Wires the county map's render lane into a Bevy `App`.
///
/// Depends only on `Assets<Mesh>` and `Assets<ColorMaterial>` existing —
/// it registers `bevy::mesh::MeshPlugin` / `bevy::sprite_render::
/// ColorMaterialPlugin` itself when they are not already present. The
/// CI-shaped headless test (Task 6 Step 1) adds only `MinimalPlugins` +
/// `AssetPlugin`, neither of which registers those asset types on its
/// own; the real client adds them transitively via `DefaultPlugins`
/// already, so the `is_plugin_added` guard here avoids Bevy's
/// duplicate-unique-plugin panic there. Both plugins gracefully skip their
/// render-sub-app-only setup when no render sub-app exists (they guard
/// internally with `app.get_sub_app_mut(RenderApp)`), so adding them under
/// `MinimalPlugins` needs no display server, no GPU and no window — the
/// CI reality this whole plan holds to.
pub struct MapPlugin;

impl Plugin for MapPlugin {
    fn build(&self, app: &mut App) {
        if !app.is_plugin_added::<bevy::mesh::MeshPlugin>() {
            app.add_plugins(bevy::mesh::MeshPlugin);
        }
        if !app.is_plugin_added::<bevy::sprite_render::ColorMaterialPlugin>() {
            app.add_plugins(bevy::sprite_render::ColorMaterialPlugin);
        }
        app.add_systems(Startup, mesh::spawn_map_surface);
    }
}
