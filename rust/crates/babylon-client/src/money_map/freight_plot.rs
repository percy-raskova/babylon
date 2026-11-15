//! Directed freight diagrams share peer identities with the geographic map and accessible list.
use super::super::relationships::{self, CountyAnchors};
use super::super::MAP_LAYER;
use super::freight::PageKey;
use super::freight_rail;
use super::geometry::Ribbon;
use super::rail;
use super::state::{self, Action, MoneyView, Observation, Scope, Target};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer_layout::ObserverRegion;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use babylon_kernel::economic_location::EconomicLocation;
use babylon_persistence::freight_access::{Access, AccessDirection, AccessRow};
use bevy::camera::visibility::RenderLayers;
use bevy::prelude::*;

/// All identified county endpoints remain selectable, including those without a certified route.
pub(super) fn geography(
    commands: &mut Commands,
    meshes: &mut Assets<Mesh>,
    view: &MoneyView,
    scope: &Scope,
    anchors: &CountyAnchors,
    colors: &[Handle<StandardMaterial>; 4],
) {
    let freight = &view.freight;
    let Some(home) = freight
        .origin
        .and_then(|c| anchors.county_position(c.as_str()))
    else {
        return;
    };
    for row in freight.all_rows() {
        let EconomicLocation::County(county) = row.peer else {
            continue;
        };
        let Some(peer) = anchors.county_position(county.geoid().as_str()) else {
            continue;
        };
        let outbound = freight.direction == AccessDirection::Outbound;
        let (from, to) = if outbound { (home, peer) } else { (peer, home) };
        let color = if freight.selected == Some(row.peer) {
            3
        } else if !row.corridors.is_empty() {
            0
        } else if matches!(row.access, Access::Reachable { .. }) {
            1
        } else {
            2
        };
        let (mesh, transform) =
            if matches!(row.access, Access::Reachable { .. }) || !row.corridors.is_empty() {
                let Some(arrow) = relationships::payment_ribbon(from, to, 1.5) else {
                    continue;
                };
                (arrow, Transform::default())
            } else {
                (
                    Mesh::from(Sphere::new(1.8)),
                    Transform::from_translation(peer + Vec3::Y * 2.0),
                )
            };
        commands
            .spawn((
                Mesh3d(meshes.add(mesh)),
                MeshMaterial3d(colors[color].clone()),
                transform,
                RenderLayers::layer(MAP_LAYER),
                Ribbon,
                Target {
                    scope: scope.clone(),
                    offset: view.offset,
                    action: Action::Freight(freight.selection(row.peer)),
                },
                DeclaredSurface::new(SurfaceId::ObserverProduction),
            ))
            .observe(state::pointer);
    }
}
type CanvasKey = (Scope, PageKey);

fn network_row(
    panel: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
    row: &AccessRow,
    left: &str,
    right: &str,
) {
    let linked = matches!(row.access, Access::Reachable { .. }) || !row.corridors.is_empty();
    let color = if linked { theme::BLUE } else { theme::GRAY };
    panel
        .spawn(Node {
            width: percent(100),
            align_items: AlignItems::Center,
            ..default()
        })
        .with_children(|line| {
            line.spawn(Node {
                width: percent(33),
                min_width: px(0),
                ..default()
            })
            .with_child(rail::label(
                left,
                15.0,
                theme::PAPER,
                ObserverFontRole::Body,
            ));
            line.spawn(Node {
                width: percent(12),
                height: px(2),
                ..default()
            })
            .insert(BackgroundColor(if linked { color } else { theme::INK }));
            line.spawn(rail::label(
                if linked { "▶" } else { "·" },
                16.0,
                color,
                ObserverFontRole::Body,
            ));
            line.spawn(Node {
                width: percent(49),
                min_width: px(0),
                flex_direction: FlexDirection::Column,
                ..default()
            })
            .with_children(|end| {
                rail::control(
                    end,
                    view,
                    scope,
                    Action::Freight(view.freight.selection(row.peer)),
                    format!("{left} → {right}\n{}", freight_rail::reading(row)),
                );
            });
        });
}

pub(super) fn paint(
    mut commands: Commands,
    view: Res<MoneyView>,
    obs: Observation,
    mut current: Local<Option<(CanvasKey, Entity)>>,
) {
    if !view.is_changed()
        && !obs.session.is_changed()
        && !obs.ui.is_changed()
        && !obs.primary.is_changed()
    {
        return;
    }
    let key = view
        .scope
        .as_ref()
        .filter(|_| obs.interactive() && view.shows_sankey())
        .and_then(|s| view.freight.page_key().map(|p| (s.clone(), p)));
    if current.as_ref().map(|(k, _)| k) == key.as_ref() {
        return;
    }
    if let Some((_, old)) = current.take() {
        commands.entity(old).despawn();
    }
    let Some(key) = key else {
        return;
    };
    let scope = &key.0;
    let freight = &view.freight;
    let outbound = freight.direction == AccessDirection::Outbound;
    let name = freight.origin.map_or_else(String::new, |c| {
        rail::location(Some(&format!("county:{c}")), &obs.atlas)
    });
    let mut root = commands.spawn((
        ObserverRegion::World,
        Node {
            position_type: PositionType::Absolute,
            flex_direction: FlexDirection::Column,
            padding: UiRect::all(px(14)),
            row_gap: px(8),
            overflow: Overflow::scroll_y(),
            ..default()
        },
        BackgroundColor(theme::INK),
        ZIndex(5),
        DeclaredSurface::new(SurfaceId::ObserverProduction),
    ));
    root.with_children(|panel| {
        panel.spawn(rail::label(
            format!("Terminal network · {name}"),
            20.0,
            theme::PAPER,
            ObserverFontRole::Display,
        ));
        panel.spawn(rail::label(
            if outbound {
                "Origin → destinations"
            } else {
                "Origins → destination"
            },
            16.0,
            theme::GRAY,
            ObserverFontRole::Body,
        ));
        for row in freight.visible() {
            let peer = freight_rail::peer_name(row, &obs.atlas);
            let (left, right) = if outbound {
                (name.as_str(), peer.as_str())
            } else {
                (peer.as_str(), name.as_str())
            };
            network_row(panel, &view, scope, row, left, right);
        }
    });
    *current = Some((key, root.id()));
}
