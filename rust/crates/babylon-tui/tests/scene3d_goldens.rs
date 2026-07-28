//! Task 33/34 goldens: `hypergraph_scene` + `field_surface` fixtures,
//! rasterized at front + three-quarter cameras (§4's golden-strategy
//! ruling: raw 3D frames get `insta::assert_snapshot!("{buf:?}")`, named
//! `<scene>_{front,3q}` — here via the test function's own name, matching
//! the `raster_skeleton.rs` M0 convention).
#![cfg(feature = "raster")]

use babylon_tui::raster_bridge::blit_rect;
use babylon_tui::scene3d::{field_surface, hypergraph_scene, CameraState};
use hypergraph_rs::raster::{rasterize, Camera, Rgb, SceneGraph3D};
use ratatui::buffer::Buffer;
use ratatui::layout::Rect;

const COLS: u16 = 80;
const ROWS: u16 = 24;

/// A 3-member, 1-community fixture: a triangle hull with 3 ghost struts,
/// one from each member to the community node.
fn hypergraph_fixture() -> SceneGraph3D {
    let nodes = vec![
        ("m1".to_string(), [-0.6, -0.5], 0.05, Rgb(233, 223, 201)),
        ("m2".to_string(), [0.6, -0.5], 0.05, Rgb(233, 223, 201)),
        ("m3".to_string(), [0.0, 0.6], 0.05, Rgb(233, 223, 201)),
        (
            "union_local".to_string(),
            [0.0, 0.0],
            0.08,
            Rgb(217, 164, 65),
        ),
    ];
    let hulls = vec![(
        vec!["m1".to_string(), "m2".to_string(), "m3".to_string()],
        Rgb(217, 164, 65),
    )];
    let struts = vec![
        ("m1".to_string(), "union_local".to_string()),
        ("m2".to_string(), "union_local".to_string()),
        ("m3".to_string(), "union_local".to_string()),
    ];
    hypergraph_scene(&nodes, &hulls, &struts)
}

/// A 4-sample scalar field over a small quad grid.
fn field_fixture() -> SceneGraph3D {
    let samples = vec![
        (-0.5, -0.5, 0.2),
        (0.5, -0.5, 0.6),
        (-0.5, 0.5, 0.9),
        (0.5, 0.5, 0.1),
    ];
    field_surface(&samples, (6, 4))
}

/// The `0`-key front camera.
fn front_camera() -> Camera {
    CameraState::default().camera()
}

/// A three-quarter camera: 3 `ry` steps (45°) + 2 `rx` steps (20°).
fn three_quarter_camera() -> Camera {
    let mut cam = CameraState::default();
    cam.step_ry(3.0);
    cam.step_rx(2.0);
    cam.camera()
}

fn render(scene: &SceneGraph3D, camera: &Camera) -> Buffer {
    let grid = rasterize(scene, camera, COLS, ROWS);
    let mut buf = Buffer::empty(Rect::new(0, 0, COLS, ROWS));
    let area = buf.area;
    blit_rect(&grid, &mut buf, area);
    buf
}

#[test]
fn hypergraph_scene_front() {
    let buf = render(&hypergraph_fixture(), &front_camera());
    insta::assert_snapshot!(format!("{buf:?}"));
}

#[test]
fn hypergraph_scene_3q() {
    let buf = render(&hypergraph_fixture(), &three_quarter_camera());
    insta::assert_snapshot!(format!("{buf:?}"));
}

#[test]
fn field_surface_front() {
    let buf = render(&field_fixture(), &front_camera());
    insta::assert_snapshot!(format!("{buf:?}"));
}

#[test]
fn field_surface_3q() {
    let buf = render(&field_fixture(), &three_quarter_camera());
    insta::assert_snapshot!(format!("{buf:?}"));
}
