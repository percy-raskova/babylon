//! The county map's bounded pan/zoom camera (B1 Task 7).
//!
//! `PanCamera` (`bevy::camera_controller::pan_camera`, the `pan_camera`
//! feature) drives panning (WASD) and zoom (mouse wheel / +/-) by writing
//! its `zoom_factor` straight into the camera entity's own `Transform`
//! scale (`run_pancamera_controller` in the crate: `transform.scale =
//! Vec3::splat(controller.zoom_factor)`). Under `ScalingMode::WindowSize`
//! with `OrthographicProjection::scale` left at its default `1.0` (this
//! module never touches it), that transform scale IS "world metres visible
//! per screen pixel" — so `zoom_factor` and this module's `clamp_camera`'s
//! `zoom` parameter are the same number.
//!
//! **A naming collision worth flagging explicitly** (the plan's Task 7
//! Step 1 prose vs. `PanCamera`'s own fields): the plan describes
//! "MAX_ZOOM" as the CLOSEST-IN bound ("one median county fills a third of
//! the viewport"). But `PanCamera.zoom_factor` runs the opposite way from
//! that prose: a SMALLER `zoom_factor` means fewer world metres map into
//! the same pixel count, i.e. MORE zoomed in; a LARGER `zoom_factor` means
//! more zoomed out. (Confirmed by reading `run_pancamera_controller`:
//! `zoom_factor -= zoom_amount`, and `zoom_amount` is positive for a
//! forward/up scroll — the intuitive "scroll up to zoom in" gesture
//! decreases `zoom_factor`.) So the plan's prose "MAX_ZOOM" (closest-in)
//! is `PanCamera.min_zoom` here, and its "MIN_ZOOM" (whole map visible,
//! "fully zoomed out") is `PanCamera.max_zoom`. This module names its own
//! constants and functions by their EFFECT rather than reusing the
//! ambiguous MIN/MAX prose, and every doc comment says which `PanCamera`
//! field it feeds.

use crate::atlas::CountyAtlas;
use bevy::camera::ScalingMode;
use bevy::camera_controller::pan_camera::PanCamera;
use bevy::math::{Rect, Vec2};
use bevy::prelude::*;
use bevy::window::PrimaryWindow;

const ATLAS_BYTES: &[u8] = include_bytes!("../../assets/map/county_atlas.bin");

/// Fallback viewport used only when no primary window exists — the
/// headless test path (`MinimalPlugins` carries no `WindowPlugin`).
/// Matches the size the `mesh2d_vertex_color_texture`-style examples and
/// this crate's own `WindowPlugin` default settle on in practice.
const FALLBACK_VIEWPORT: Vec2 = Vec2::new(1280.0, 720.0);

/// The fraction of the smaller viewport dimension a median county's
/// bounding-box diagonal should fill at the closest permitted zoom.
const MEDIAN_COUNTY_VIEWPORT_FRACTION: f32 = 1.0 / 3.0;

/// The atlas's `world_bounds()`, stashed at Startup so the per-frame clamp
/// system does not need to re-parse the embedded atlas every tick.
#[derive(Resource, Clone, Copy)]
pub struct MapBounds(pub Rect);

/// Feeds `PanCamera.min_zoom` (the SMALLEST `zoom_factor`, i.e. the
/// CLOSEST-in bound the camera may reach): the zoom at which a median
/// county's bounding-box diagonal fills `MEDIAN_COUNTY_VIEWPORT_FRACTION`
/// of the viewport's smaller dimension. Computed from the atlas rather
/// than a guessed magic number (Task 7 Step 1's own instruction).
#[must_use]
pub fn closest_in_zoom(atlas: &CountyAtlas, viewport: Vec2) -> f32 {
    let mut diagonals: Vec<f32> = (0..atlas.len())
        .map(|i| {
            let county = atlas.county(i).expect("index is within 0..atlas.len()");
            (county.bbox.max - county.bbox.min).length()
        })
        .collect();
    diagonals.sort_by(|a, b| a.partial_cmp(b).expect("bbox diagonals are finite"));
    let median = diagonals[diagonals.len() / 2];
    let target_pixels = viewport.x.min(viewport.y) * MEDIAN_COUNTY_VIEWPORT_FRACTION;
    median / target_pixels
}

/// Feeds `PanCamera.max_zoom` (the LARGEST `zoom_factor`, i.e. the
/// FARTHEST-out bound the camera may reach): the zoom at which `bounds`
/// exactly fits inside `viewport`.
#[must_use]
pub fn whole_map_zoom(bounds: Rect, viewport: Vec2) -> f32 {
    (bounds.width() / viewport.x).max(bounds.height() / viewport.y)
}

/// Clamps a camera's world-space translation so its visible rect never
/// leaves `bounds` grown by 10% on every side — except when the visible
/// rect is itself at least as large as the grown bounds (fully zoomed
/// out), in which case there is nothing left to clamp against and the
/// camera centres on `bounds.center()`. Pure and renderer-free so it can
/// be unit tested directly.
#[must_use]
pub fn clamp_camera(translation: Vec2, zoom: f32, viewport: Vec2, bounds: Rect) -> Vec2 {
    let half_extent = viewport * zoom * 0.5;
    let grown = grow(bounds, 0.10);

    let x = if half_extent.x * 2.0 >= grown.width() {
        bounds.center().x
    } else {
        translation
            .x
            .clamp(grown.min.x + half_extent.x, grown.max.x - half_extent.x)
    };
    let y = if half_extent.y * 2.0 >= grown.height() {
        bounds.center().y
    } else {
        translation
            .y
            .clamp(grown.min.y + half_extent.y, grown.max.y - half_extent.y)
    };
    Vec2::new(x, y)
}

/// `rect` grown by `fraction` of its own size, symmetric around its
/// center — a rect grown by 0.10 is 10% larger on each axis, 5% added to
/// each side.
fn grow(rect: Rect, fraction: f32) -> Rect {
    let margin = rect.size() * fraction * 0.5;
    Rect {
        min: rect.min - margin,
        max: rect.max + margin,
    }
}

fn primary_viewport(windows: &Query<&Window, With<PrimaryWindow>>) -> Vec2 {
    windows
        .single()
        .map(|w| Vec2::new(w.width(), w.height()))
        .unwrap_or(FALLBACK_VIEWPORT)
}

/// `Startup` system: spawns the map camera, sized and bounded from the
/// atlas. Re-parses the embedded atlas independently of
/// `map::mesh::spawn_map_surface`'s own parse rather than reaching into
/// its `MapSurface` resource — that keeps this system free of any
/// same-schedule command-flush-ordering assumption between two Startup
/// systems, at the cost of one extra (cheap, parse-only, no
/// tessellation) atlas decode at boot.
pub(super) fn spawn_camera(mut commands: Commands, windows: Query<&Window, With<PrimaryWindow>>) {
    let viewport = primary_viewport(&windows);
    let atlas = CountyAtlas::parse(ATLAS_BYTES)
        .unwrap_or_else(|e| panic!("county atlas failed to parse at startup: {e}"));

    let min_zoom = closest_in_zoom(&atlas, viewport);
    let max_zoom = whole_map_zoom(atlas.world_bounds(), viewport);
    let center = atlas.world_bounds().center();

    commands.spawn((
        Camera2d,
        Transform::from_xyz(center.x, center.y, 0.0),
        Projection::Orthographic(OrthographicProjection {
            scaling_mode: ScalingMode::WindowSize,
            ..OrthographicProjection::default_2d()
        }),
        PanCamera {
            // Start fully zoomed out (the whole map fits) rather than at
            // the crate's own `zoom_factor: 1.0` default, which would
            // start the player looking at an arbitrary few-pixel sliver
            // of one county.
            zoom_factor: max_zoom,
            min_zoom,
            max_zoom,
            // Rotation off: a rotated map disorients the player, and no
            // ruling asks for one.
            rotation_speed: 0.0,
            key_rotate_ccw: None,
            key_rotate_cw: None,
            ..default()
        },
    ));

    commands.insert_resource(MapBounds(atlas.world_bounds()));
}

/// `Update` system: applies `clamp_camera` after `PanCameraPlugin`'s own
/// `RunFixedMainLoop`-scheduled system has moved the camera this frame —
/// `RunFixedMainLoop` runs before `Update` in Bevy's default schedule
/// order, so a plain `Update` system already satisfies "after".
pub(super) fn clamp_camera_system(
    windows: Query<&Window, With<PrimaryWindow>>,
    bounds: Option<Res<MapBounds>>,
    mut cameras: Query<(&mut Transform, &PanCamera)>,
) {
    let Some(bounds) = bounds else {
        return;
    };
    let viewport = primary_viewport(&windows);
    for (mut transform, pan_camera) in &mut cameras {
        let clamped = clamp_camera(
            transform.translation.truncate(),
            pan_camera.zoom_factor,
            viewport,
            bounds.0,
        );
        transform.translation.x = clamped.x;
        transform.translation.y = clamped.y;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn atlas() -> CountyAtlas {
        CountyAtlas::parse(ATLAS_BYTES).expect("committed atlas parses")
    }

    #[test]
    fn fully_zoomed_out_centres_on_bounds_center() {
        let bounds = Rect::new(0.0, 0.0, 1000.0, 500.0);
        let viewport = Vec2::new(2000.0, 2000.0); // huge viewport
        let zoom = 1.0; // half_extent = 1000x1000, exceeds the grown bounds
        let far_away = Vec2::new(50_000.0, -50_000.0);
        let result = clamp_camera(far_away, zoom, viewport, bounds);
        assert_eq!(result, bounds.center());
    }

    #[test]
    fn panning_past_the_east_edge_clamps_inside_the_grown_bounds() {
        let bounds = Rect::new(0.0, 0.0, 1000.0, 500.0);
        let viewport = Vec2::new(100.0, 100.0);
        let zoom = 1.0; // half_extent = (50, 50), well inside the grown bounds
        let grown = grow(bounds, 0.10);

        let panned_past_east = Vec2::new(1_000_000.0, bounds.center().y);
        let result = clamp_camera(panned_past_east, zoom, viewport, bounds);

        let expected_x = grown.max.x - 50.0;
        assert!(
            (result.x - expected_x).abs() < 1e-4,
            "expected clamped x near {expected_x}, got {}",
            result.x
        );
        // y was not pushed out of range, so it should pass through
        // unchanged (still within the grown bounds' clamp interval).
        assert!((result.y - bounds.center().y).abs() < 1e-4);
    }

    #[test]
    fn a_visible_rect_within_bounds_is_left_alone() {
        let bounds = Rect::new(0.0, 0.0, 1000.0, 500.0);
        let viewport = Vec2::new(100.0, 100.0);
        let zoom = 1.0; // half_extent = (50, 50)
        let inside = Vec2::new(500.0, 250.0);
        let result = clamp_camera(inside, zoom, viewport, bounds);
        assert!((result - inside).length() < 1e-4);
    }

    #[test]
    fn closest_in_zoom_makes_the_median_county_fill_a_third_of_the_viewport() {
        let atlas = atlas();
        let viewport = Vec2::new(1280.0, 720.0);
        let zoom = closest_in_zoom(&atlas, viewport);

        let mut diagonals: Vec<f32> = (0..atlas.len())
            .map(|i| {
                let county = atlas.county(i).expect("index in range");
                (county.bbox.max - county.bbox.min).length()
            })
            .collect();
        diagonals.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let median = diagonals[diagonals.len() / 2];

        let median_screen_extent = median / zoom;
        let target = viewport.x.min(viewport.y) * MEDIAN_COUNTY_VIEWPORT_FRACTION;
        assert!(
            (median_screen_extent - target).abs() < 1e-2,
            "median county should occupy {target} px, got {median_screen_extent} px"
        );
    }

    #[test]
    fn whole_map_zoom_fits_the_bounds_exactly_on_the_binding_axis() {
        let atlas = atlas();
        let bounds = atlas.world_bounds();
        let viewport = Vec2::new(1280.0, 720.0);
        let zoom = whole_map_zoom(bounds, viewport);

        // At this zoom, the visible extent must be at least as large as
        // bounds on both axes...
        assert!(viewport.x * zoom >= bounds.width() - 1e-2);
        assert!(viewport.y * zoom >= bounds.height() - 1e-2);
        // ...and exactly equal to it on whichever axis is the binding
        // constraint.
        let x_binds = (viewport.x * zoom - bounds.width()).abs() < 1e-2;
        let y_binds = (viewport.y * zoom - bounds.height()).abs() < 1e-2;
        assert!(x_binds || y_binds, "neither axis is the binding constraint");
    }

    #[test]
    fn closest_in_zoom_is_smaller_than_whole_map_zoom() {
        let atlas = atlas();
        let viewport = Vec2::new(1280.0, 720.0);
        let min_zoom = closest_in_zoom(&atlas, viewport);
        let max_zoom = whole_map_zoom(atlas.world_bounds(), viewport);
        assert!(
            min_zoom < max_zoom,
            "the closest-in zoom {min_zoom} must be smaller than the whole-map zoom {max_zoom} \
             (PanCamera.min_zoom must be < PanCamera.max_zoom or the clamp is inverted)"
        );
    }
}
