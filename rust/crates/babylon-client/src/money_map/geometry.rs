//! Directed county ribbons. Width compares positive settlement amounts or recorded hours on this page.
use super::super::relationships;
use super::super::relationships::CountyAnchors;
use super::super::{MapOrbit, MAP_LAYER};
use super::state::{
    self, Action, Connection, Diagram, Direction, MoneyView, Observation, Scope, Target,
};
use super::{geographic_legs, grouping};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer_theme as theme;
use crate::observer_ui::ObserverViewport;
use babylon_persistence::money_journal::FlowGroup;
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
    mut palette: Local<Vec<(Color, Handle<StandardMaterial>)>>,
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
    // One unlit material per authored hue, retained across selections and layout switches.
    let mut material = |color: Color| {
        if let Some((_, handle)) = palette.iter().find(|(cached, _)| *cached == color) {
            return handle.clone();
        }
        let handle = materials.add(StandardMaterial {
            base_color: color,
            unlit: true,
            cull_mode: None,
            ..default()
        });
        palette.push((color, handle.clone()));
        handle
    };
    if view.freight.enabled {
        let colors = [theme::YELLOW, theme::BLUE, theme::GRAY, theme::PAPER].map(material);
        super::freight_plot::geography(&mut commands, &mut meshes, &view, scope, &anchors, &colors);
        return;
    }
    let Some(home) = anchors.county_position(&scope.county) else {
        return;
    };
    let values: Vec<_> = geographic_legs::rows(&view)
        .iter()
        .filter_map(|row| {
            let n = row.quantity.micros().parse::<f64>().ok()?;
            (n.is_finite() && n > 0.0).then_some((row, n))
        })
        .collect();
    let maximum = values.iter().map(|(_, n)| *n).fold(0.0_f64, f64::max);
    let aggregate = view
        .selected_row()
        .filter(|_| scope.group != FlowGroup::Location);
    let industry = aggregate
        .filter(|_| scope.group == FlowGroup::Industry)
        .map(|parent| grouping::industry_color(parent.key.peer.as_deref()));
    for (row, n) in values {
        let peer = row
            .key
            .peer
            .as_deref()
            .and_then(|id| id.strip_prefix("county:"))
            .and_then(|id| anchors.county_position(id));
        let (from, to, color) = match (row.key.direction, peer) {
            (Direction::PaidTo, Some(peer)) => (home, peer, theme::YELLOW),
            (Direction::ReceivedFrom, Some(peer)) => (peer, home, theme::BLUE),
            (Direction::Internal, _) => (home, home, theme::GRAY),
            _ => continue,
        };
        let Some(mesh) = relationships::payment_ribbon(from, to, width(n, maximum)) else {
            continue;
        };
        let selected = aggregate.is_some()
            || view
                .selected_row()
                .is_some_and(|active| active.key == row.key);
        let action = match aggregate {
            Some(parent) if row.key.direction != Direction::Internal && peer.is_some() => {
                Action::FollowLeg {
                    aggregate: parent.key.clone(),
                    leg: row.key.clone(),
                }
            }
            Some(parent) => Action::Select(parent.key.clone()),
            None => Action::Select(row.key.clone()),
        };
        commands
            .spawn((
                Mesh3d(meshes.add(mesh)),
                MeshMaterial3d(material(industry.unwrap_or(if selected {
                    theme::PAPER
                } else {
                    color
                }))),
                Transform::default(),
                RenderLayers::layer(MAP_LAYER),
                Ribbon,
                Target {
                    scope: scope.clone(),
                    offset: view.offset,
                    action,
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
        || obs
            .scope(event.scope.measure, event.scope.periods, event.scope.group)
            .as_ref()
            != Some(&event.scope)
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
        .filter(|_| event.scope.group == FlowGroup::Location)
        .and_then(|row| endpoint(row, home, &anchors));
    let bounds = if let Some(peer) = selected {
        Some((home.min(peer), home.max(peer)))
    } else {
        geographic_legs::rows(&view)
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
