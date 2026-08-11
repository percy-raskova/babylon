//! Builds the county map's two `Mesh2d` entities from the embedded atlas
//! (B1 Task 6): a merged choropleth **fill** mesh (one triangle list, one
//! `ColorMaterial`, per-vertex colors so a later lens recolor is a buffer
//! write) and a **border** mesh (one line list over every ring's edges, a
//! single `DIM` `ColorMaterial`).

use super::bands::PANEL;
use crate::atlas::CountyAtlas;
use crate::palette;
use crate::tessellate::{self, Tessellation};
use bevy::asset::RenderAssetUsages;
use bevy::mesh::{Indices, PrimitiveTopology};
use bevy::prelude::*;

const ATLAS_BYTES: &[u8] = include_bytes!("../../assets/map/county_atlas.bin");

/// The exact fill-mesh vertex count the committed atlas tessellates to —
/// `atlas.vertices().len()`, since `tessellate::tessellate` appends every
/// ring's vertices exactly once. Pinned here so Task 6's headless test can
/// assert the real mesh without re-tessellating inside the test.
pub const EXPECTED_VERTEX_COUNT: usize = 360_064;

/// Marks the choropleth fill mesh entity.
#[derive(Component)]
pub struct MapFill;

/// Marks the county-border line mesh entity.
#[derive(Component)]
pub struct MapBorders;

/// The tessellation plus the two spawned mesh handles, stashed as a
/// resource so later systems (the lens recolor system) can reach the same
/// `vertex_county`/`county_vertex_range` data without re-tessellating.
#[derive(Resource)]
pub struct MapSurface {
    pub tessellation: Tessellation,
    pub fill_mesh: Handle<Mesh>,
    pub border_mesh: Handle<Mesh>,
}

/// `Startup` system: parse the embedded atlas, tessellate it, and spawn
/// the fill and border entities. Panicking on an atlas failure is the
/// right posture here — a client that opens without its map is the
/// loud-failure case, the same one B0 took with the engine link.
///
/// `pub`, not `pub(super)` (B2 Task 12): `loop_ui.rs` (Task 14) orders its
/// own Startup system `.after(map::spawn_map_surface)`, which needs this
/// visible outside `map`'s own module tree — a sibling module, not a
/// descendant of `map`.
pub fn spawn_map_surface(
    mut commands: Commands,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<ColorMaterial>>,
) {
    let atlas = CountyAtlas::parse(ATLAS_BYTES)
        .unwrap_or_else(|e| panic!("county atlas failed to parse at startup: {e}"));
    let tessellation = tessellate::tessellate(&atlas);

    let fill_mesh = meshes.add(build_fill_mesh(&tessellation));
    let border_mesh = meshes.add(build_border_mesh(&atlas));

    commands.spawn((
        Mesh2d(fill_mesh.clone()),
        MeshMaterial2d(materials.add(ColorMaterial::default())),
        Transform::from_xyz(0.0, 0.0, 0.0),
        MapFill,
    ));
    commands.spawn((
        Mesh2d(border_mesh.clone()),
        MeshMaterial2d(materials.add(ColorMaterial::from(palette::DIM))),
        Transform::from_xyz(0.0, 0.0, 1.0),
        MapBorders,
    ));

    commands.insert_resource(MapSurface {
        tessellation,
        fill_mesh,
        border_mesh,
    });
}

/// The merged choropleth mesh: one `TriangleList` over every county's
/// triangles, every vertex starting at `PANEL`.
fn build_fill_mesh(tessellation: &Tessellation) -> Mesh {
    let panel = PANEL.to_linear().to_f32_array();
    let colors: Vec<[f32; 4]> = vec![panel; tessellation.positions.len()];

    let mut mesh = Mesh::new(
        PrimitiveTopology::TriangleList,
        RenderAssetUsages::default(),
    );
    mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, tessellation.positions.clone());
    mesh.insert_attribute(Mesh::ATTRIBUTE_COLOR, colors);
    mesh.insert_indices(Indices::U32(tessellation.indices.clone()));
    mesh
}

/// The border mesh: a `LineList` over every ring's edges (exterior and
/// hole rings alike — a hole's boundary is a real edge the player should
/// see). Two adjacent counties each carry their own copy of a shared
/// boundary, so a shared border draws twice; that is the atlas's own
/// per-county ring storage, not a bug this mesh introduces.
fn build_border_mesh(atlas: &CountyAtlas) -> Mesh {
    let vertices = atlas.vertices();
    let mut positions: Vec<[f32; 3]> = Vec::new();

    for county_index in 0..atlas.len() {
        let county = atlas
            .county(county_index)
            .expect("county_index is within 0..atlas.len()");
        for ring in county.rings {
            let start = ring.vertex_start as usize;
            let end = start + ring.vertex_count as usize;
            let ring_vertices = &vertices[start..end];
            let n = ring_vertices.len();
            for i in 0..n {
                let a = ring_vertices[i];
                let b = ring_vertices[(i + 1) % n];
                // z = 0.0 in the mesh itself; the border entity's own
                // Transform carries the z = 1.0 offset above the fill.
                positions.push([a.x, a.y, 0.0]);
                positions.push([b.x, b.y, 0.0]);
            }
        }
    }

    let mut mesh = Mesh::new(PrimitiveTopology::LineList, RenderAssetUsages::default());
    mesh.insert_attribute(Mesh::ATTRIBUTE_POSITION, positions);
    mesh
}
