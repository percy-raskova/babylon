//! Generic 3D scene builders for the TOPOLOGY pane's 3D lane (Task 33/34,
//! `docs/superpowers/specs/2026-07-27-m4-topology-contracts.md` §5/§6).
//!
//! Two pure builders, both plain functions of their inputs (no clock, no
//! rand): [`hypergraph_scene`] lifts a bipartite member/community layout
//! (the §1 `paoh` envelope; positions computed Python-side) into a
//! `SceneGraph3D`, and [`field_surface`] IDW-interpolates scattered
//! `(x, y, scalar)` samples (the §2 field-state dossier, joined to
//! coordinates client-side) into a quad-grid heightfield. [`CameraState`]
//! holds the client-side camera as discrete per-keypress steps — §6's
//! determinism law (no clock, no rand, no easing).
//!
//! **Banned imports (§5 RULED):** this module never reaches into
//! `hypergraph_rs::raster::instruments::*`, `::deck::*`, or `::ingest::*` —
//! those are the Deck-fixture-coupled instrument builders (`cylinder.rs`,
//! `terrain.rs`). Only their PATTERN is followed below, transcribed
//! generically against this crate's own inputs and re-cited inline.

use std::collections::{HashMap, HashSet};

use hypergraph_rs::layout::convex_hull;
use hypergraph_rs::raster::{Camera, Face, Node3, Rgb, SceneGraph3D, Strut, Vertex3};
use hypergraph_rs::viz::NodeStyle;

// ---------------------------------------------------------------------
// hypergraph_scene (Task 33)
// ---------------------------------------------------------------------

/// Member-plane z (§5: "members z=0, communities z=0.6").
pub const MEMBER_Z: f64 = 0.0;
/// Community-plane z (§5).
pub const COMMUNITY_Z: f64 = 0.6;

/// Fixed hull-face opacity: this generic builder has no org-degree scalar
/// to drive `cylinder.rs`'s `0.12 + 0.3*o` ramp (`instruments/cylinder.rs`
/// `build_cylinder`), so hull translucency is a flat constant instead.
const HULL_OPACITY: f64 = 0.22;

/// Ghost-strut ink: §9b GOLD (`theme.rs`), the accent role used here for
/// the bipartite ghost edges connecting a member's plane position to its
/// community's plane position — the `cylinder.rs` `GHOST_STRUT_COLOR`
/// pattern (`instruments/cylinder.rs:34`), recolored to this crate's own
/// palette rather than the deck's `rgba(217,164,65,.65)` gold.
const STRUT_COLOR: Rgb = Rgb(255, 215, 0);

/// Build a scene from a bipartite member/community layout: `nodes` is
/// `(id, [x, y], radius, color)` for every node the caller wants rendered
/// — the §1 `paoh` envelope's `layout` map carries positions for BOTH
/// member ids and community ids, and both belong in this one slice;
/// `hulls` is `(member_ids, fill)` per community, used to fan-triangulate
/// that community's hull; `struts` is `(id, id)` pairs to connect with a
/// straight line (the PAOH bipartite ghost edges, member ↔ its community).
///
/// **Plane split (§5 RULED):** a node id that appears in ANY hull's
/// member list sits on the MEMBER plane (`z = MEMBER_Z`); every other id
/// in `nodes` (never listed as a hull's member — a community id, under
/// the §1 bipartite-shell convention where a community is never its own
/// hull's member) sits on the COMMUNITY plane (`z = COMMUNITY_Z`). The
/// builder never inspects an id's string shape, only hull membership, so
/// it stays generic over whatever the caller's ids look like.
///
/// Hull faces are fan-triangulated from the convex hull of a community's
/// own member (x, y) positions, lifted to the community plane — the
/// `cylinder.rs::hull_faces` pattern (`instruments/cylinder.rs:117-147`),
/// adapted from its y-up height axis to this builder's z-up plane split.
/// A member id missing from `nodes` is skipped (degrades gracefully
/// rather than panicking); fewer than 3 resolved points make no hull.
///
/// Struts connect the fully resolved (already plane-split) positions of
/// both ids; either id absent from `nodes` drops that strut silently.
///
/// Bounded throughout: one pass over `nodes`, over `hulls` (each bounded
/// by its own member count), and over `struts` — all fixed-size caller
/// inputs, no unbounded iteration.
pub fn hypergraph_scene(
    nodes: &[(String, [f64; 2], f64, Rgb)],
    hulls: &[(Vec<String>, Rgb)],
    struts: &[(String, String)],
) -> SceneGraph3D {
    let mut hull_member_ids: HashSet<&str> = HashSet::new();
    for (members, _) in hulls {
        for m in members {
            hull_member_ids.insert(m.as_str());
        }
    }

    let mut positions: HashMap<&str, Vertex3> = HashMap::with_capacity(nodes.len());
    let mut out_nodes = Vec::with_capacity(nodes.len());
    for (id, xy, radius, color) in nodes {
        let z = if hull_member_ids.contains(id.as_str()) {
            MEMBER_Z
        } else {
            COMMUNITY_Z
        };
        let pos = Vertex3 {
            x: xy[0],
            y: xy[1],
            z,
        };
        positions.insert(id.as_str(), pos);
        out_nodes.push(Node3 {
            id: id.clone(),
            pos,
            radius: *radius,
            color: *color,
            style: NodeStyle::default(),
            attrs: serde_json::Value::Null,
        });
    }

    let mut faces = Vec::new();
    for (members, fill) in hulls {
        let pts_xy: Vec<(f64, f64)> = members
            .iter()
            .filter_map(|m| positions.get(m.as_str()))
            .map(|p| (p.x, p.y))
            .collect();
        faces.extend(hull_faces(&pts_xy, COMMUNITY_Z, *fill, HULL_OPACITY));
    }

    let mut out_struts = Vec::with_capacity(struts.len());
    for (a, b) in struts {
        if let (Some(&pa), Some(&pb)) = (positions.get(a.as_str()), positions.get(b.as_str())) {
            out_struts.push(Strut {
                a: pa,
                b: pb,
                color: STRUT_COLOR,
            });
        }
    }

    let bounding_box = compute_bounding_box(
        out_nodes
            .iter()
            .map(|n| n.pos)
            .chain(faces.iter().flat_map(|f| f.verts))
            .chain(out_struts.iter().flat_map(|s| [s.a, s.b])),
    );

    // §5's banner reuse: the scene's own scalars, so `labeled_scalars()`
    // stamps a real line for the hypergraph (verify-panel finding —
    // field_surface already honored it). Counted before the moves below.
    let mut metadata = serde_json::Map::new();
    metadata.insert("nodes".into(), out_nodes.len().into());
    metadata.insert("hulls".into(), hulls.len().into());
    metadata.insert("struts".into(), out_struts.len().into());

    SceneGraph3D {
        nodes: out_nodes,
        faces,
        struts: out_struts,
        bounding_box,
        metadata,
    }
}

/// Fan-triangulate the convex hull of `pts_xy` into `Face`s at fixed
/// height `z` — the `cylinder.rs::hull_faces` pattern
/// (`instruments/cylinder.rs:117-147`), generalized to take a caller-fixed
/// `z` instead of the cylinder's `o(C)`-derived height. Fewer than 3 hull
/// points make no hull. Bounded: `pts_xy.len()`.
fn hull_faces(pts_xy: &[(f64, f64)], z: f64, fill: Rgb, opacity: f64) -> Vec<Face> {
    let hull = convex_hull(pts_xy);
    if hull.len() < 3 {
        return Vec::new();
    }
    let v0 = Vertex3 {
        x: hull[0].0,
        y: hull[0].1,
        z,
    };
    let mut faces = Vec::with_capacity(hull.len() - 2);
    for i in 1..hull.len() - 1 {
        let v1 = Vertex3 {
            x: hull[i].0,
            y: hull[i].1,
            z,
        };
        let v2 = Vertex3 {
            x: hull[i + 1].0,
            y: hull[i + 1].1,
            z,
        };
        faces.push(Face {
            verts: [v0, v1, v2],
            fill,
            opacity,
        });
    }
    faces
}

// ---------------------------------------------------------------------
// field_surface (Task 34)
// ---------------------------------------------------------------------

/// IDW smoothing epsilon, folded into `d²` before the reciprocal — ported
/// verbatim from `instruments/terrain.rs::EPS` (`:26`), scout-verified to
/// materially smooth the field rather than being a cosmetic render knob
/// (§5). This module never imports `instruments::terrain` directly (the
/// §5 ban); the formula is reimplemented in [`idw_height`] below.
const IDW_EPS: f64 = 0.02;

/// World extent for the quad grid: `x, z ∈ [-FIELD_EXTENT, FIELD_EXTENT]`.
/// §2's surface builder joins samples against the same unit-circle frame
/// §1's bipartite-shell layout uses for member nodes (radius 1.0), so this
/// builder shares that fixed frame rather than deriving one from the
/// sample distribution — the two 3D lanes stay in one common camera-space.
pub const FIELD_EXTENT: f64 = 1.0;

/// Per-sample marker radius — matches `instruments/terrain.rs`'s own
/// per-agent marker radius (`:163`).
const FIELD_NODE_RADIUS: f64 = 0.024;

/// `instruments/terrain.rs::idw_height` (`:49-58`) reimplemented locally
/// (the §5 ban forbids importing it): IDW-weighted mean of `samples`'
/// scalars at `(x, y)`, normalized by `tmax`. `IDW_EPS` folded into `d²`
/// before the reciprocal keeps the field finite even evaluated exactly at
/// a sample's own position. Bounded: `samples.len()`.
fn idw_height(x: f64, y: f64, samples: &[(f64, f64, f64)], tmax: f64) -> f64 {
    let mut num = 0.0;
    let mut den = 0.0;
    for &(sx, sy, t) in samples {
        let d2 = (x - sx).powi(2) + (y - sy).powi(2) + IDW_EPS;
        num += t / d2;
        den += 1.0 / d2;
    }
    (num / den) / tmax
}

/// Build a scalar-surface scene (Task 34) from scattered `(x, y, scalar)`
/// samples via an IDW-interpolated quad grid — the generic lift of
/// `instruments/terrain.rs::build_terrain`, stripped of its `DeckWorld`
/// per-agent-bloc coupling (§5). `grid` is `(n, m)`: `n` quad columns by
/// `m` quad rows, `(n+1)*(m+1)` vertices, `n*m*2` triangle faces — bounded
/// by the caller-chosen fixed resolution (each dimension floored at 1).
///
/// Empty `samples` returns [`SceneGraph3D::empty`]: an IDW interpolant
/// needs at least one source, and there is nothing to surface otherwise
/// (the alternative — dividing by a zero `den` — would be `NaN`, and this
/// crate never returns a non-finite scene).
pub fn field_surface(samples: &[(f64, f64, f64)], grid: (u16, u16)) -> SceneGraph3D {
    if samples.is_empty() {
        return SceneGraph3D::empty();
    }
    let n = usize::from(grid.0).max(1);
    let m = usize::from(grid.1).max(1);
    // `.max(0.001)`: `instruments/terrain.rs`'s own tmax floor (`:90`),
    // guarding the final `/tmax` divide against an all-zero sample set.
    let tmax = samples
        .iter()
        .map(|&(_, _, t)| t)
        .fold(0.0_f64, f64::max)
        .max(0.001);

    let height_at = |x: f64, y: f64| idw_height(x, y, samples, tmax);
    let vertex = |i: usize, j: usize| -> (Vertex3, f64) {
        let x = (i as f64 / n as f64 * 2.0 - 1.0) * FIELD_EXTENT;
        let z = (j as f64 / m as f64 * 2.0 - 1.0) * FIELD_EXTENT;
        let t = height_at(x, z);
        (Vertex3 { x, y: t, z }, t)
    };

    // Bounded: n*m quads, 2 triangle faces each (fixed caller resolution).
    let mut faces = Vec::with_capacity(n * m * 2);
    for i in 0..n {
        for j in 0..m {
            let (v00, t00) = vertex(i, j);
            let (v10, _) = vertex(i + 1, j);
            let (v11, t11) = vertex(i + 1, j + 1);
            let (v01, _) = vertex(i, j + 1);
            // Per-quad t = mean of the two diagonal corners
            // (`instruments/terrain.rs:129`).
            let t = (t00 + t11) / 2.0;
            let fill = heat_ramp(t);
            let opacity = 0.2 + t.clamp(0.0, 1.0) * 0.5;
            faces.push(Face {
                verts: [v00, v10, v11],
                fill,
                opacity,
            });
            faces.push(Face {
                verts: [v00, v11, v01],
                fill,
                opacity,
            });
        }
    }

    // Bounded: one marker per sample.
    let mut nodes = Vec::with_capacity(samples.len());
    for (idx, &(x, y, _)) in samples.iter().enumerate() {
        let t = height_at(x, y);
        nodes.push(Node3 {
            id: format!("sample-{idx}"),
            pos: Vertex3 { x, y: t, z: y },
            radius: FIELD_NODE_RADIUS,
            color: heat_ramp(t),
            style: NodeStyle::default(),
            attrs: serde_json::Value::Null,
        });
    }

    let bounding_box = compute_bounding_box(
        nodes
            .iter()
            .map(|n| n.pos)
            .chain(faces.iter().flat_map(|f| f.verts)),
    );

    let mut metadata = serde_json::Map::new();
    metadata.insert(
        "grid_vertices".to_string(),
        serde_json::json!((n + 1) * (m + 1)),
    );
    metadata.insert("tmax".to_string(), serde_json::json!(tmax));

    SceneGraph3D {
        nodes,
        faces,
        struts: Vec::new(),
        bounding_box,
        metadata,
    }
}

/// §9b role ramp: DIM → GREEN_DARK → GOLD → CRIMSON by normalized height
/// (§5 RULED) — a local 4-stop analogue of `raster::color::heat`'s 3-stop
/// gold/bone/crimson ramp (`color.rs:26-40`), using this crate's own
/// palette (`theme.rs`'s `Color::Rgb` literals, transcribed as
/// `hypergraph_rs::raster::Rgb`) instead of the deck's. `t` clamped to
/// `[0, 1]`; three equal linear-mix segments.
fn heat_ramp(t: f64) -> Rgb {
    let t = t.clamp(0.0, 1.0);
    const DIM: (u8, u8, u8) = (64, 64, 64);
    const GREEN_DARK: (u8, u8, u8) = (34, 139, 34);
    const GOLD: (u8, u8, u8) = (255, 215, 0);
    const CRIMSON: (u8, u8, u8) = (220, 20, 60);

    let (from, to, k) = if t < 1.0 / 3.0 {
        (DIM, GREEN_DARK, t * 3.0)
    } else if t < 2.0 / 3.0 {
        (GREEN_DARK, GOLD, (t - 1.0 / 3.0) * 3.0)
    } else {
        (GOLD, CRIMSON, (t - 2.0 / 3.0) * 3.0)
    };

    Rgb(
        mix_channel(from.0, to.0, k),
        mix_channel(from.1, to.1, k),
        mix_channel(from.2, to.2, k),
    )
}

/// Linear channel mix — `raster::color::mix`'s formula (`color.rs:16-21`)
/// reimplemented locally (that fn is private to `hypergraph_rs`).
fn mix_channel(a: u8, b: u8, t: f64) -> u8 {
    let v = a as f64 + (b as f64 - a as f64) * t;
    v.floor() as u8
}

// ---------------------------------------------------------------------
// Shared geometry helper
// ---------------------------------------------------------------------

/// The axis-aligned bounding box of `points`, or the zero box if `points`
/// is empty. Bounded by the caller's own (already-bounded) point count.
fn compute_bounding_box(points: impl Iterator<Item = Vertex3>) -> (f64, f64, f64, f64, f64, f64) {
    let mut min = (f64::INFINITY, f64::INFINITY, f64::INFINITY);
    let mut max = (f64::NEG_INFINITY, f64::NEG_INFINITY, f64::NEG_INFINITY);
    let mut any = false;
    for p in points {
        any = true;
        min.0 = min.0.min(p.x);
        min.1 = min.1.min(p.y);
        min.2 = min.2.min(p.z);
        max.0 = max.0.max(p.x);
        max.1 = max.1.max(p.y);
        max.2 = max.2.max(p.z);
    }
    if !any {
        return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0);
    }
    (min.0, min.1, min.2, max.0, max.1, max.2)
}

// ---------------------------------------------------------------------
// CameraState (Task 32)
// ---------------------------------------------------------------------

/// Rotation step around Y per `←`/`→`, degrees (§6).
pub const RY_STEP_DEG: f64 = 15.0;
/// Rotation step around X per `↑`/`↓`, degrees (§6).
pub const RX_STEP_DEG: f64 = 10.0;
/// Distance step per `+`/`-` (§6).
pub const DIST_STEP: f64 = 0.5;
/// Distance clamp floor (§6).
pub const DIST_MIN: f64 = 1.5;
/// Distance clamp ceiling (§6).
pub const DIST_MAX: f64 = 12.0;
/// The `0`-key "front" reset distance — the same front camera the M0
/// walking skeleton's own golden uses (`tests/raster_skeleton.rs`).
pub const FRONT_DIST: f64 = 4.0;
/// Fixed vertical FOV, degrees — §6 lists no FOV key, so this never
/// changes at runtime.
pub const FOV_DEG: f64 = 70.0;

/// Client-side camera state for the TOPOLOGY pane's 3D lane (Task 32,
/// §6): discrete per-keypress steps only — no clock, no rand, no easing.
/// `(scene, camera, cols, rows) -> frame` (`hypergraph_rs::raster::rasterize`)
/// stays a pure function of a [`Camera`] built fresh each frame from this
/// state via [`CameraState::camera`].
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct CameraState {
    ry_deg: f64,
    rx_deg: f64,
    dist: f64,
}

impl Default for CameraState {
    /// The front camera: `ry = rx = 0`, `dist = FRONT_DIST` — the `0`-key
    /// reset target.
    fn default() -> Self {
        Self {
            ry_deg: 0.0,
            rx_deg: 0.0,
            dist: FRONT_DIST,
        }
    }
}

impl CameraState {
    /// `←`/`→`: step `ry` by `steps * RY_STEP_DEG`, wrapped into
    /// `[0, 360)` (angles are periodic; wrapping keeps the state from
    /// growing without bound over a long session).
    pub fn step_ry(&mut self, steps: f64) {
        self.ry_deg = (self.ry_deg + steps * RY_STEP_DEG).rem_euclid(360.0);
    }

    /// `↑`/`↓`: step `rx` by `steps * RX_STEP_DEG`, wrapped into
    /// `[0, 360)`.
    pub fn step_rx(&mut self, steps: f64) {
        self.rx_deg = (self.rx_deg + steps * RX_STEP_DEG).rem_euclid(360.0);
    }

    /// `+`/`-`: step `dist` by `steps * DIST_STEP`, clamped to
    /// `[DIST_MIN, DIST_MAX]` (§6).
    pub fn step_dist(&mut self, steps: f64) {
        self.dist = (self.dist + steps * DIST_STEP).clamp(DIST_MIN, DIST_MAX);
    }

    /// `0`: reset to the front camera.
    pub fn reset(&mut self) {
        *self = Self::default();
    }

    /// Build the `hypergraph_rs` camera this state describes, fresh —
    /// degrees converted to the radians `Camera::ry`/`Camera::rx` expect
    /// (`raster::camera::Camera`, `camera.rs:28-33`).
    pub fn camera(&self) -> Camera {
        Camera {
            ry: self.ry_deg.to_radians(),
            rx: self.rx_deg.to_radians(),
            dist: self.dist,
            fov: FOV_DEG,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// `(nodes, hulls, struts)` — `hypergraph_scene`'s three input slices,
    /// named to sidestep clippy's `type_complexity` on the raw tuple.
    type HypergraphFixture = (
        Vec<(String, [f64; 2], f64, Rgb)>,
        Vec<(Vec<String>, Rgb)>,
        Vec<(String, String)>,
    );

    fn triangle_fixture() -> HypergraphFixture {
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
        (nodes, hulls, struts)
    }

    #[test]
    fn hypergraph_scene_splits_planes_by_hull_membership() {
        let (nodes, hulls, struts) = triangle_fixture();
        let scene = hypergraph_scene(&nodes, &hulls, &struts);

        let by_id = |id: &str| scene.nodes.iter().find(|n| n.id == id).unwrap();
        assert_eq!(by_id("m1").pos.z, MEMBER_Z);
        assert_eq!(by_id("m2").pos.z, MEMBER_Z);
        assert_eq!(by_id("m3").pos.z, MEMBER_Z);
        assert_eq!(by_id("union_local").pos.z, COMMUNITY_Z);
    }

    #[test]
    fn hypergraph_scene_fan_triangulates_the_triangle_hull() {
        let (nodes, hulls, struts) = triangle_fixture();
        let scene = hypergraph_scene(&nodes, &hulls, &struts);
        // A 3-point hull is already a single triangle: exactly one face.
        assert_eq!(scene.faces.len(), 1);
        for v in scene.faces[0].verts {
            assert_eq!(v.z, COMMUNITY_Z);
        }
    }

    #[test]
    fn hypergraph_scene_resolves_struts_across_planes() {
        let (nodes, hulls, struts) = triangle_fixture();
        let scene = hypergraph_scene(&nodes, &hulls, &struts);
        assert_eq!(scene.struts.len(), 3);
        for s in &scene.struts {
            assert_eq!(s.a.z, MEMBER_Z);
            assert_eq!(s.b.z, COMMUNITY_Z);
        }
    }

    #[test]
    fn hypergraph_scene_drops_struts_and_hull_members_missing_from_nodes() {
        let nodes = vec![("m1".to_string(), [0.0, 0.0], 0.05, Rgb(1, 2, 3))];
        let hulls = vec![(vec!["m1".to_string(), "ghost".to_string()], Rgb(1, 2, 3))];
        let struts = vec![("m1".to_string(), "ghost".to_string())];
        let scene = hypergraph_scene(&nodes, &hulls, &struts);
        // Only 2 resolved hull points -> no hull (< 3), no faces.
        assert!(scene.faces.is_empty());
        // The strut's far end is unresolvable -> dropped.
        assert!(scene.struts.is_empty());
        assert_eq!(scene.nodes.len(), 1);
    }

    #[test]
    fn field_surface_of_empty_samples_is_the_empty_scene() {
        let scene = field_surface(&[], (4, 4));
        assert_eq!(scene, SceneGraph3D::empty());
    }

    #[test]
    fn field_surface_builds_the_requested_grid() {
        let samples = vec![
            (-0.5, -0.5, 0.2),
            (0.5, -0.5, 0.6),
            (-0.5, 0.5, 0.9),
            (0.5, 0.5, 0.1),
        ];
        let scene = field_surface(&samples, (6, 4));
        assert_eq!(scene.faces.len(), 6 * 4 * 2);
        assert_eq!(scene.nodes.len(), samples.len());
        assert_eq!(
            scene.metadata.get("grid_vertices").and_then(|v| v.as_u64()),
            Some((7 * 5) as u64)
        );
    }

    #[test]
    fn heat_ramp_pins_its_four_stops() {
        assert_eq!(heat_ramp(0.0), Rgb(64, 64, 64));
        assert_eq!(heat_ramp(1.0 / 3.0), Rgb(34, 139, 34));
        assert_eq!(heat_ramp(2.0 / 3.0), Rgb(255, 215, 0));
        assert_eq!(heat_ramp(1.0), Rgb(220, 20, 60));
    }

    #[test]
    fn camera_state_steps_and_clamps_and_resets() {
        let mut cam = CameraState::default();
        assert_eq!(cam.camera().dist, FRONT_DIST);

        cam.step_ry(1.0);
        cam.step_rx(1.0);
        let c = cam.camera();
        assert!((c.ry - RY_STEP_DEG.to_radians()).abs() < 1e-12);
        assert!((c.rx - RX_STEP_DEG.to_radians()).abs() < 1e-12);

        // Distance clamps at the floor/ceiling rather than overshooting.
        for _ in 0..100 {
            cam.step_dist(-1.0);
        }
        assert_eq!(cam.camera().dist, DIST_MIN);
        for _ in 0..100 {
            cam.step_dist(1.0);
        }
        assert_eq!(cam.camera().dist, DIST_MAX);

        cam.reset();
        assert_eq!(cam, CameraState::default());
    }
}
