//! Rebuild geographic geometry only when the admitted campaign scope changes.
use super::{
    county_prism, hover_county, leave_county, relationships, scene_point, select_county,
    CountySlab, MapGeometry, MapLegend, MapOrbit, ObserverMapCamera, BASE_HEIGHT, DATA_HEIGHT,
    MAP_LAYER, METRES_TO_SCENE,
};
use crate::atlas::CountyAtlas;
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::map::CountyMapScope;
use crate::observer_theme as theme;
use crate::observer_ui::{ObserverUiState, ObserverViewport};
use crate::production::PrimaryView;
use bevy::camera::visibility::RenderLayers;
use bevy::ecs::system::SystemParam;
use bevy::light::CascadeShadowConfigBuilder;
use bevy::prelude::*;
use bevy::window::PrimaryWindow;

#[derive(Component)]
pub(super) struct MapScene;

#[derive(Component)]
struct InsetLabel(Vec3);

#[derive(SystemParam)]
pub(super) struct SceneAssets<'w> {
    meshes: ResMut<'w, Assets<Mesh>>,
    materials: ResMut<'w, Assets<StandardMaterial>>,
}

pub(super) fn setup_map(
    mut commands: Commands,
    atlas: Res<CountyAtlas>,
    scope: Res<CountyMapScope>,
    mut assets: SceneAssets,
    old: Query<Entity, With<MapScene>>,
    mut rendered: Local<Option<CountyMapScope>>,
    mut triangles: Local<Option<crate::tessellate::Tessellation>>,
) {
    if rendered.as_ref() == Some(&scope) {
        return;
    }
    *rendered = Some(scope.clone());
    for entity in &old {
        commands.entity(entity).despawn();
    }
    commands.insert_resource(relationships::CountyAnchors::default());
    commands.insert_resource(MapGeometry::default());
    let counties = scope.counties();
    let Some(bounds) = scope_bounds(&atlas, counties) else {
        return;
    };
    let origin = bounds.center();
    let extent = bounds.size() * METRES_TO_SCENE;
    let triangles = triangles.get_or_insert_with(|| crate::tessellate::tessellate(&atlas));
    commands.insert_resource(relationships::CountyAnchors::from_atlas(
        &atlas, counties, origin,
    ));
    for &index in counties {
        spawn_county(&mut commands, &mut assets, &atlas, triangles, index, origin);
    }
    spawn_map_scene(
        &mut commands,
        extent,
        &mut assets.meshes,
        &mut assets.materials,
    );
    spawn_insets(&mut commands, &atlas, counties, origin);
}

fn scope_bounds(atlas: &CountyAtlas, counties: &[usize]) -> Option<Rect> {
    counties
        .iter()
        .filter_map(|&i| atlas.county(i))
        .map(|c| Rect::from_corners(c.bbox.min, c.bbox.max))
        .reduce(|a, b| Rect::from_corners(a.min.min(b.min), a.max.max(b.max)))
}

fn spawn_county(
    commands: &mut Commands,
    assets: &mut SceneAssets,
    atlas: &CountyAtlas,
    triangles: &crate::tessellate::Tessellation,
    index: usize,
    origin: Vec2,
) {
    let county = atlas
        .county(index)
        .expect("scope admits each atlas identity");
    let (body, edge) = county_prism(atlas, triangles, index, origin);
    let outline = assets.materials.add(StandardMaterial {
        base_color: theme::INK,
        unlit: true,
        ..default()
    });
    commands
        .spawn((
            Mesh3d(assets.meshes.add(body)),
            MeshMaterial3d(assets.materials.add(StandardMaterial {
                base_color: theme::LAND,
                perceptual_roughness: 0.78,
                metallic: 0.08,
                ..default()
            })),
            Transform::from_scale(Vec3::new(1.0, BASE_HEIGHT, 1.0)),
            RenderLayers::layer(MAP_LAYER),
            MapScene,
            CountySlab {
                atlas_index: index,
                fips: county.fips.to_owned(),
                outline: outline.clone(),
            },
            DeclaredSurface::new(SurfaceId::ObserverShell),
        ))
        .with_child((
            Mesh3d(assets.meshes.add(edge)),
            MeshMaterial3d(outline),
            RenderLayers::layer(MAP_LAYER),
            Pickable::IGNORE,
            DeclaredSurface::new(SurfaceId::ObserverShell),
        ))
        .observe(hover_county)
        .observe(leave_county)
        .observe(select_county);
}

fn spawn_map_scene(
    commands: &mut Commands,
    extent: Vec2,
    meshes: &mut Assets<Mesh>,
    materials: &mut Assets<StandardMaterial>,
) {
    let plinth = materials.add(StandardMaterial {
        base_color: theme::INK,
        perceptual_roughness: 0.94,
        ..default()
    });
    commands.spawn((
        Mesh3d(meshes.add(Cuboid::new(extent.x + 60.0, 10.0, extent.y + 60.0))),
        MeshMaterial3d(plinth),
        Transform::from_xyz(0.0, -5.1, 0.0),
        RenderLayers::layer(MAP_LAYER),
        Pickable::IGNORE,
        MapScene,
        DeclaredSurface::new(SurfaceId::ObserverShell),
    ));
    commands.spawn((
        DirectionalLight {
            color: theme::PAPER,
            illuminance: 9000.0,
            shadows_enabled: true,
            ..default()
        },
        Transform::from_xyz(-400.0, 800.0, 300.0).looking_at(Vec3::ZERO, Vec3::Y),
        CascadeShadowConfigBuilder {
            first_cascade_far_bound: extent.max_element() * 0.5,
            maximum_distance: extent.max_element() * 6.0,
            ..default()
        }
        .build(),
        RenderLayers::layer(MAP_LAYER),
        MapScene,
    ));
    commands.spawn((
        DirectionalLight {
            color: theme::BLUE,
            illuminance: 1800.0,
            ..default()
        },
        Transform::from_xyz(500.0, 300.0, -300.0).looking_at(Vec3::ZERO, Vec3::Y),
        RenderLayers::layer(MAP_LAYER),
        MapScene,
    ));
    let orbit = MapOrbit::new(extent.max_element());
    commands.spawn((
        Camera3d::default(),
        Camera {
            clear_color: ClearColorConfig::Custom(theme::INK),
            ..default()
        },
        Projection::Perspective(PerspectiveProjection {
            fov: 45.0_f32.to_radians(),
            near: 0.5,
            far: camera_far(extent, &orbit),
            ..default()
        }),
        orbit.transform(),
        RenderLayers::layer(MAP_LAYER),
        ObserverMapCamera,
        Msaa::Sample4,
        MapScene,
    ));
    commands.insert_resource(orbit);
    commands.insert_resource(MapGeometry { extent });
    commands.spawn((
        Text::new("Campaign county geography"),
        TextFont {
            font_size: 14.0,
            ..default()
        },
        TextColor(theme::PAPER),
        crate::observer_ui::ObserverFontRole::Body,
        Node {
            position_type: PositionType::Absolute,
            max_width: px(700),
            padding: UiRect::axes(px(10), px(6)),
            ..default()
        },
        BackgroundColor(theme::INK),
        ZIndex(4),
        Pickable::IGNORE,
        Visibility::Hidden,
        MapLegend,
        MapScene,
        DeclaredSurface::new(SurfaceId::ObserverShell),
    ));
}

pub(super) fn camera_far(extent: Vec2, orbit: &MapOrbit) -> f32 {
    // The far corner remains inside the frustum at maximum allowed pan and zoom.
    orbit.distance.max(orbit.fitted_distance * 3.0) + extent.length() * 1.5 + DATA_HEIGHT + 100.0
}

fn spawn_insets(commands: &mut Commands, atlas: &CountyAtlas, counties: &[usize], origin: Vec2) {
    for (prefix, caption) in [
        ("02", "Alaska · relocated inset · 35% scale"),
        ("15", "Hawaii · relocated inset · original scale"),
    ] {
        let indices: Vec<_> = counties
            .iter()
            .copied()
            .filter(|&i| atlas.county(i).is_some_and(|c| c.fips.starts_with(prefix)))
            .collect();
        let Some(bounds) = scope_bounds(atlas, &indices) else {
            continue;
        };
        let anchor = scene_point(
            Vec2::new(bounds.center().x, bounds.max.y),
            origin,
            BASE_HEIGHT,
        );
        commands.spawn((
            Text::new(caption),
            TextFont {
                font_size: 14.0,
                ..default()
            },
            TextColor(theme::PAPER),
            crate::observer_ui::ObserverFontRole::Body,
            Node {
                position_type: PositionType::Absolute,
                padding: UiRect::axes(px(6), px(4)),
                ..default()
            },
            BackgroundColor(theme::INK),
            ZIndex(4),
            Pickable::IGNORE,
            Visibility::Hidden,
            InsetLabel(anchor),
            MapScene,
            DeclaredSurface::new(SurfaceId::ObserverShell),
        ));
    }
}

#[derive(SystemParam)]
pub(super) struct InsetPlacement<'w, 's> {
    view: Res<'w, PrimaryView>,
    ui: Res<'w, ObserverUiState>,
    viewport: Res<'w, ObserverViewport>,
    scale: Res<'w, UiScale>,
    windows: Query<'w, 's, &'static Window, With<PrimaryWindow>>,
    camera: Query<'w, 's, (&'static Camera, &'static Transform), With<ObserverMapCamera>>,
    labels: Query<
        'w,
        's,
        (
            &'static InsetLabel,
            &'static ComputedNode,
            &'static mut Node,
            &'static mut Visibility,
        ),
    >,
}

pub(super) fn place_insets(mut placement: InsetPlacement) {
    let active = *placement.view == PrimaryView::Map
        && !placement.ui.menu_open
        && !placement.ui.splash_visible
        && !placement.ui.comparison_open
        && placement.ui.disclosure.is_none();
    for (label, computed, mut node, mut visibility) in &mut placement.labels {
        let rect = if active {
            match (
                placement.viewport.0,
                placement.camera.single(),
                placement.windows.single(),
            ) {
                (Some(bounds), Ok((camera, transform)), Ok(window)) => {
                    let size = computed.size() / window.scale_factor();
                    (size.is_finite() && size.min_element() > 0.0)
                        .then(|| {
                            camera
                                .world_to_viewport(&GlobalTransform::from(*transform), label.0)
                                .ok()
                                .and_then(|anchor| {
                                    crate::production_layout::place_label(anchor, bounds, size, &[])
                                })
                        })
                        .flatten()
                }
                _ => None,
            }
        } else {
            None
        };
        visibility.set_if_neq(if rect.is_some() {
            Visibility::Visible
        } else {
            Visibility::Hidden
        });
        if let Some(rect) = rect {
            let left = px(rect.min.x / placement.scale.0);
            let top = px(rect.min.y / placement.scale.0);
            if node.left != left {
                node.left = left;
            }
            if node.top != top {
                node.top = top;
            }
        }
    }
}

pub(super) fn fit_orbit(orbit: &mut MapOrbit, extent: Vec2, aspect: f32) {
    if !aspect.is_finite() || aspect <= 0.0 || extent.min_element() <= 0.0 {
        return;
    }
    let vertical = 45.0_f32.to_radians() * 0.5;
    let half_angle = (vertical.tan() * aspect.min(1.0)).atan();
    let radius = extent.length() * 0.5 + BASE_HEIGHT + DATA_HEIGHT;
    let fitted = radius / half_angle.sin();
    let relative_zoom = orbit.distance / orbit.fitted_distance;
    if fitted.is_finite() && fitted > 0.0 && fitted.to_bits() != orbit.fitted_distance.to_bits() {
        orbit.fitted_distance = fitted;
        orbit.distance = fitted * relative_zoom.clamp(0.08, 3.0);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn national_camera_fits_corners_and_keeps_maximum_pan_zoom_finite() {
        let extent = Vec2::new(4625.4, 4310.3);
        for aspect in [0.5, 1.0, 2.0] {
            let mut orbit = MapOrbit::new(extent.max_element());
            fit_orbit(&mut orbit, extent, aspect);
            let far = camera_far(extent, &orbit);
            let view = orbit.transform().to_matrix().inverse();
            let projection = Mat4::perspective_rh(45.0_f32.to_radians(), aspect, 0.5, far);
            for x in [-extent.x * 0.5, extent.x * 0.5] {
                for z in [-extent.y * 0.5, extent.y * 0.5] {
                    for y in [0.0, BASE_HEIGHT + DATA_HEIGHT] {
                        let clip = projection * view * Vec4::new(x, y, z, 1.0);
                        assert!(clip.is_finite());
                        assert!(clip.w > 0.0);
                        assert!((clip.x / clip.w).abs() <= 1.0);
                        assert!((clip.y / clip.w).abs() <= 1.0);
                        assert!((0.0..=1.0).contains(&(clip.z / clip.w)));
                    }
                }
            }
            orbit.distance = orbit.fitted_distance * 3.0;
            orbit.target.x = extent.x;
            orbit.target.z = extent.y;
            let camera = orbit.transform().translation;
            for corner in [
                Vec3::new(-extent.x * 0.5, 0.0, -extent.y * 0.5),
                Vec3::new(extent.x * 0.5, BASE_HEIGHT + DATA_HEIGHT, extent.y * 0.5),
            ] {
                assert!(camera.distance(corner) < camera_far(extent, &orbit));
            }
        }
    }
}
