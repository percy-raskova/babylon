//! The BD-3 walking skeleton: frozen scene fixture → `rasterize` → `blit`
//! → ratatui buffer golden. The entire M4 3D lane stands on this adapter.
#![cfg(feature = "raster")]

use babylon_tui::raster_bridge::blit;
use hypergraph_rs::raster::{rasterize, Camera, SceneGraph3D};
use ratatui::buffer::Buffer;
use ratatui::layout::Rect;

/// The cylinder scene golden, copied verbatim from hypergraph-rs's frozen
/// fixture set (tests/fixtures/scene3d/cylinder.json at the pinned rev).
const CYLINDER_SCENE: &str = include_str!("fixtures/scene3d/cylinder.json");

#[test]
fn cylinder_scene_blits_deterministically_at_80x24() {
    let scene: SceneGraph3D = serde_json::from_str(CYLINDER_SCENE).expect("frozen fixture parses");
    // The front camera hypergraph-rs's own frame tests use.
    let camera = Camera {
        ry: 0.0,
        rx: 0.0,
        dist: 4.0,
        fov: 70.0,
    };
    let grid = rasterize(&scene, &camera, 80, 24);
    assert_eq!((grid.cols, grid.rows), (80, 24));

    let mut buf = Buffer::empty(Rect::new(0, 0, 80, 24));
    blit(&grid, &mut buf);
    insta::assert_snapshot!(format!("{buf:?}"));
}
