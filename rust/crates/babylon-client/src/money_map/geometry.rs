//! Directed county ribbons. Width compares positive settlement amounts or recorded hours on this page.
use super::super::relationships;
use super::super::relationships::CountyAnchors;
use super::super::{MapOrbit, MAP_LAYER};
use super::state::{
    self, Action, Connection, Diagram, Direction, MoneyView, Observation, Scope, Target,
};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer_theme as theme;
use crate::observer_ui::ObserverViewport;
use bevy::camera::visibility::RenderLayers;
use bevy::prelude::*;

#[derive(Component)]
pub(super) struct Ribbon;

#[allow(
    clippy::cast_possible_truncation,
    reason = "bounded ratio sets display width only"
)]
fn width(value: f64, max: f64) -> f32 {
    1.0 + 5.0 * (value / max).clamp(0.0, 1.0).sqrt() as f32
}

pub(super) fn render(
    mut commands: Commands,
    view: Res<MoneyView>,
    anchors: Res<CountyAnchors>,
    old: Query<(Entity, &Mesh3d), With<Ribbon>>,
    mut meshes: ResMut<Assets<Mesh>>,
    mut materials: ResMut<Assets<StandardMaterial>>,
    mut palette: Local<Option<[Handle<StandardMaterial>; 4]>>,
) {
    if !view.is_changed() && !anchors.is_changed() {
        return;
    }
    for (entity, mesh) in &old {
        commands.entity(entity).despawn();
        meshes.remove(mesh.0.id());
    }
    if view.shows_sankey() {
        return;
    }
    let Some(scope) = &view.scope else {
        return;
    };
    let Some(home) = anchors.county_position(&scope.county) else {
        return;
    };
    let colors = palette.get_or_insert_with(|| {
        [theme::YELLOW, theme::BLUE, theme::GRAY, theme::PAPER].map(|base_color| {
            materials.add(StandardMaterial {
                base_color,
                unlit: true,
                cull_mode: None,
                ..default()
            })
        })
    });
    let values: Vec<_> = view
        .rows
        .iter()
        .filter_map(|row| {
            let n = row.quantity.micros().parse::<f64>().ok()?;
            (n.is_finite() && n > 0.0).then_some((row, n))
        })
        .collect();
    let maximum = values.iter().map(|(_, n)| *n).fold(0.0_f64, f64::max);
    for (row, n) in values {
        let peer = row
            .key
            .peer
            .as_deref()
            .and_then(|id| id.strip_prefix("county:"))
            .and_then(|id| anchors.county_position(id));
        let (from, to, color) = match (row.key.direction, peer) {
            (Direction::PaidTo, Some(peer)) => (home, peer, 0),
            (Direction::ReceivedFrom, Some(peer)) => (peer, home, 1),
            (Direction::Internal, _) => (home, home, 2),
            _ => continue,
        };
        let Some(mesh) = relationships::payment_ribbon(from, to, width(n, maximum)) else {
            continue;
        };
        let selected = view
            .selected_row()
            .is_some_and(|active| active.key == row.key);
        commands
            .spawn((
                Mesh3d(meshes.add(mesh)),
                MeshMaterial3d(colors[if selected { 3 } else { color }].clone()),
                Transform::default(),
                RenderLayers::layer(MAP_LAYER),
                Ribbon,
                Target {
                    scope: scope.clone(),
                    offset: view.offset,
                    action: Action::Select(row.key.clone()),
                },
                DeclaredSurface::new(SurfaceId::ObserverProduction),
            ))
            .observe(state::pointer);
    }
}

#[derive(Event)]
pub(super) struct FrameConnections {
    pub(super) scope: Scope,
    pub(super) offset: u64,
}

fn endpoint(row: &Connection, home: Vec3, anchors: &CountyAnchors) -> Option<Vec3> {
    if row.quantity.micros() == "0" {
        return None;
    }
    if row.key.direction == Direction::Internal {
        return Some(home);
    }
    row.key
        .peer
        .as_deref()?
        .strip_prefix("county:")
        .and_then(|county| anchors.county_position(county))
}

pub(super) fn frame_bounds(orbit: &mut MapOrbit, min: Vec3, max: Vec3, aspect: f32) {
    // The map camera uses a 45-degree vertical field of view. Include the arrow bend and
    // loop outside the endpoint chord, and keep the current pitch, yaw and national reset.
    let half_angle = ((std::f32::consts::FRAC_PI_8).tan() * aspect.min(1.0)).atan();
    let radius = (max - min).length() * 0.5 + 30.0;
    orbit.target = min.midpoint(max);
    orbit.distance = (1.12 * radius / half_angle.sin())
        .clamp(orbit.fitted_distance * 0.08, orbit.fitted_distance * 3.0);
}

pub(super) fn frame_connections(
    event: On<FrameConnections>,
    obs: Observation,
    mut view: ResMut<MoneyView>,
    viewport: Res<ObserverViewport>,
    anchors: Res<CountyAnchors>,
    mut orbit: ResMut<MapOrbit>,
) {
    if !obs.interactive()
        || obs.scope(event.scope.measure, event.scope.periods).as_ref() != Some(&event.scope)
        || view.scope.as_ref() != Some(&event.scope)
        || view.offset != event.offset
    {
        return;
    }
    let Some(home) = anchors.county_position(&event.scope.county) else {
        return;
    };
    let Some(rect) = viewport.0.filter(|r| r.width() > 0.0 && r.height() > 0.0) else {
        return;
    };
    let selected = view
        .selected_row()
        .and_then(|row| endpoint(row, home, &anchors));
    let bounds = if let Some(peer) = selected {
        Some((home.min(peer), home.max(peer)))
    } else {
        view.rows
            .iter()
            .filter_map(|row| endpoint(row, home, &anchors))
            .map(|point| (home.min(point), home.max(point)))
            .reduce(|(lo, hi), (next_lo, next_hi)| (lo.min(next_lo), hi.max(next_hi)))
    };
    if let Some((min, max)) = bounds {
        frame_bounds(&mut orbit, min, max, rect.width() / rect.height());
        view.diagram = Diagram::Map;
    }
}
