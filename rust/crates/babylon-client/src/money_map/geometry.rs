//! Directed, fixed county-to-county ribbons. Width encodes relative payment value on this page.
use super::super::relationships;
use super::super::relationships::CountyAnchors;
use super::super::MAP_LAYER;
use super::state::{self, Action, Direction, MoneyView, Target};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer_theme as theme;
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
            let n = row.micros.parse::<f64>().ok()?;
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
