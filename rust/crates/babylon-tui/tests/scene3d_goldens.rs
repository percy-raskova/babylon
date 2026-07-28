//! Task 33/34 goldens (`hypergraph_scene` + `field_surface` fixtures) plus
//! the M5 Task 39-P `patches_scene` mascot, rasterized at front +
//! three-quarter cameras (§4's golden-strategy ruling: raw 3D frames get
//! `insta::assert_snapshot!("{buf:?}")`, named `<scene>_{front,3q}` — here
//! via the test function's own name, matching the `raster_skeleton.rs` M0
//! convention).
#![cfg(feature = "raster")]

use babylon_tui::raster_bridge::blit_rect;
use babylon_tui::scene3d::{
    field_surface, hypergraph_scene, patches_scene, trend_ridgeline, CameraState, RidgeSeries,
};
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

/// The mascot portrait framing: the front camera stepped all the way in
/// (`5 × DIST_STEP` hits the `DIST_MIN` clamp at 1.5) so the ~1.7-unit
/// monkey fills the frame — built ONLY from the public discrete-step API,
/// the same construction the tutorial placement will use (§6 determinism
/// law: no bespoke camera literals).
fn portrait_camera() -> Camera {
    let mut cam = CameraState::default();
    cam.step_dist(-5.0);
    cam.camera()
}

/// The portrait three-quarter: the same 45°/20° turn as
/// [`three_quarter_camera`], at portrait distance.
fn portrait_3q_camera() -> Camera {
    let mut cam = CameraState::default();
    cam.step_ry(3.0);
    cam.step_rx(2.0);
    cam.step_dist(-5.0);
    cam.camera()
}

#[test]
fn patches_scene_front() {
    let buf = render(&patches_scene(), &portrait_camera());
    insta::assert_snapshot!(format!("{buf:?}"));
}

#[test]
fn patches_scene_3q() {
    let buf = render(&patches_scene(), &portrait_3q_camera());
    insta::assert_snapshot!(format!("{buf:?}"));
}

/// Three ridges with distinct shapes: rising, falling, single-peak.
fn ridgeline_fixture() -> SceneGraph3D {
    let ridge = |name: &str, points: Vec<(f64, f64)>| RidgeSeries {
        name: name.to_string(),
        points,
    };
    trend_ridgeline(&[
        ridge(
            "rising",
            vec![(0.0, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 5.0)],
        ),
        ridge(
            "falling",
            vec![(0.0, 5.0), (1.0, 4.0), (2.0, 2.0), (3.0, 1.0)],
        ),
        ridge("peak", vec![(0.0, 0.0), (1.0, 4.0), (2.0, 4.5), (3.0, 0.5)]),
    ])
}

#[test]
fn trend_ridgeline_front() {
    let buf = render(&ridgeline_fixture(), &front_camera());
    insta::assert_snapshot!(format!("{buf:?}"));
}

#[test]
fn trend_ridgeline_3q() {
    let buf = render(&ridgeline_fixture(), &three_quarter_camera());
    insta::assert_snapshot!(format!("{buf:?}"));
}

#[test]
fn trend_ridgeline_structure_is_bounded_quads() {
    let scene = ridgeline_fixture();
    // 3 ridges × 3 segments × 2 triangles.
    assert_eq!(scene.faces.len(), 18);
    assert!(scene.nodes.is_empty() && scene.struts.is_empty());
    // Sub-2-point series contribute nothing; all-empty input is empty.
    let empty = trend_ridgeline(&[RidgeSeries {
        name: "lonely".to_string(),
        points: vec![(0.0, 1.0)],
    }]);
    assert!(empty.faces.is_empty());
}

#[test]
fn patches_scene_structure_is_the_ruled_mascot() {
    // The Director's palette contract (M5 §4): GOLD body, CRIMSON
    // accents, exactly two near-black eyes — pinned structurally so a
    // palette drift fails HERE with a named reason, not only as an
    // opaque golden diff.
    let scene = patches_scene();
    assert_eq!(scene.nodes.len(), 2, "Patches has exactly two eyes");
    assert!(scene.struts.is_empty(), "a monkey has no ghost struts");
    let gold = scene
        .faces
        .iter()
        .filter(|f| f.fill == Rgb(255, 215, 0))
        .count();
    let crimson = scene
        .faces
        .iter()
        .filter(|f| f.fill == Rgb(220, 20, 60))
        .count();
    assert!(
        gold > crimson && crimson >= 3,
        "gold body with crimson accents: gold={gold} crimson={crimson}"
    );
    let (min_x, _, _, max_x, _, _) = scene.bounding_box;
    assert!(
        min_x < 0.0 && max_x > 0.0 && min_x.abs() <= 1.0 && max_x <= 1.0,
        "the mascot stays inside the unit-ish stage: {:?}",
        scene.bounding_box
    );
}
