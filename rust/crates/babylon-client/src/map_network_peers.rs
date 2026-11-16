//! Unanchored counterparts have a compact disclosure with an independently scrollable list.
use super::{EconomyEntity, NetworkProjection, RelationshipObservation};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer::ObservationContext;
use crate::observer_focus::{ObserverFocusTarget, ObserverKeyboardActivate};
use crate::observer_theme as theme;
use crate::observer_ui::{ObserverFontRole, ObserverUiState, ObserverViewport};
use crate::production::{PrimaryView, ProductionCommand};
use bevy::a11y::AccessibilityNode;
use bevy::input_focus::tab_navigation::TabGroup;
use bevy::picking::pointer::PointerButton;
use bevy::prelude::*;

#[derive(Component)]
pub(super) struct ExternalPeers {
    expanded: bool,
    count: usize,
}
#[derive(Component)]
pub(super) struct Toggle {
    panel: Entity,
    context: ObservationContext,
}
#[derive(Component)]
pub(super) struct PeerList;
#[derive(Component)]
pub(super) struct ToggleCaption;

fn activate(
    entity: Entity,
    targets: &Query<&Toggle>,
    panels: &mut Query<&mut ExternalPeers>,
    obs: &RelationshipObservation,
) {
    let Ok(target) = targets.get(entity) else {
        return;
    };
    if super::usable(&obs.ui, *obs.view)
        && obs.session.accepts(&target.context)
        && super::super::disclosed_snapshot(&obs.frame, &obs.session).is_some()
    {
        if let Ok(mut panel) = panels.get_mut(target.panel) {
            panel.expanded = !panel.expanded;
        }
    }
}
fn click(
    event: On<PointerClick>,
    targets: Query<&Toggle>,
    mut panels: Query<&mut ExternalPeers>,
    obs: RelationshipObservation,
) {
    if event.button == PointerButton::Primary {
        activate(event.entity, &targets, &mut panels, &obs);
    }
}
fn key(
    event: On<ObserverKeyboardActivate>,
    targets: Query<&Toggle>,
    mut panels: Query<&mut ExternalPeers>,
    obs: RelationshipObservation,
) {
    if targets
        .get(event.entity)
        .is_ok_and(|t| Some(&t.context) == event.context.as_ref())
    {
        activate(event.entity, &targets, &mut panels, &obs);
    }
}

pub(super) fn spawn_peers(
    commands: &mut Commands,
    projection: &NetworkProjection,
    context: &ObservationContext,
) {
    if projection.external.is_empty() {
        return;
    }
    let mut panel = commands.spawn((
        Node {
            position_type: PositionType::Absolute,
            flex_direction: FlexDirection::Column,
            padding: UiRect::all(px(4)),
            ..default()
        },
        BackgroundColor(theme::INK),
        ZIndex(6),
        Visibility::Hidden,
        EconomyEntity,
        ExternalPeers {
            expanded: false,
            count: projection.external.len(),
        },
        crate::observer_map3d::symbols::MapObstruction,
        TabGroup::new(25),
        DeclaredSurface::new(SurfaceId::ObserverProduction),
    ));
    let panel_id = panel.id();
    panel.with_children(|panel| {
        let mut focus = ObserverFocusTarget::action(Some(context.clone()));
        focus.available = true;
        panel
            .spawn((
                crate::ui::pressable(),
                focus,
                Toggle {
                    panel: panel_id,
                    context: context.clone(),
                },
                Node {
                    height: px(32),
                    flex_shrink: 0.0,
                    align_items: AlignItems::Center,
                    padding: UiRect::horizontal(px(8)),
                    ..default()
                },
                BackgroundColor(theme::PANEL),
            ))
            .observe(click)
            .observe(key)
            .with_child((
                Text::default(),
                TextFont {
                    font_size: FontSize::Px(15.0),
                    ..default()
                },
                TextColor(theme::YELLOW),
                ObserverFontRole::Body,
                Pickable::IGNORE,
                ToggleCaption,
            ));
        panel
            .spawn((
                PeerList,
                Node {
                    display: Display::None,
                    flex_direction: FlexDirection::Column,
                    min_height: px(0),
                    row_gap: px(4),
                    overflow: Overflow::scroll_y(),
                    ..default()
                },
            ))
            .with_children(|list| {
                for peer in projection.external.values() {
                    crate::production::button(
                        list,
                        &peer.caption,
                        ProductionCommand::Select {
                            site_id: peer.site_id.clone(),
                            context: context.clone(),
                        },
                    );
                }
            });
    });
}

pub(super) fn sync_disclosure(
    panels: Query<(&ExternalPeers, &Children), Changed<ExternalPeers>>,
    mut toggles: Query<(&Children, &mut AccessibilityNode), With<Toggle>>,
    mut lists: Query<&mut Node, With<PeerList>>,
    mut captions: Query<&mut Text, With<ToggleCaption>>,
) {
    for (panel, children) in &panels {
        for child in children {
            if let Ok(mut list) = lists.get_mut(*child) {
                list.display = if panel.expanded {
                    Display::Flex
                } else {
                    Display::None
                };
            }
            if let Ok((children, mut accessibility)) = toggles.get_mut(*child) {
                let label = format!(
                    "{} outside-map counterparts  {}",
                    panel.count,
                    if panel.expanded { "−" } else { "+" }
                );
                accessibility.set_expanded(panel.expanded);
                accessibility.set_label(label.clone());
                for child in children {
                    if let Ok(mut text) = captions.get_mut(*child) {
                        text.0.clone_from(&label);
                    }
                }
            }
        }
    }
}

pub(super) fn place_peers(
    ui: Res<ObserverUiState>,
    view: Res<PrimaryView>,
    viewport: Res<ObserverViewport>,
    scale: Res<UiScale>,
    mut panels: Query<(&ExternalPeers, &mut Node, &mut Visibility)>,
) {
    for (panel, mut node, mut visibility) in &mut panels {
        let bounds = viewport.0.filter(|_| super::usable(&ui, *view));
        visibility.set_if_neq(if bounds.is_some() {
            Visibility::Visible
        } else {
            Visibility::Hidden
        });
        if let Some(bounds) = bounds {
            let width = (bounds.width() - 16.0).clamp(
                0.0,
                if panel.expanded {
                    320.0 * scale.0
                } else {
                    230.0 * scale.0
                },
            );
            let height = if panel.expanded {
                (bounds.height() * 0.4).max(0.0)
            } else {
                40.0 * scale.0
            };
            let mut next = node.clone();
            next.left = px((bounds.max.x - width - 8.0) / scale.0);
            next.top = px((bounds.max.y - height - 8.0) / scale.0);
            next.width = px(width / scale.0);
            next.height = px(height / scale.0);
            node.set_if_neq(next);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::map::SelectedCounty;
    use crate::observer::ObserverSession;
    use crate::observer_map3d::relationships::network::{ExternalPeer, NodeKey};
    use crate::observer_map3d::relationships::tests as relationships_fixture;
    use crate::production::ProductionNavigation;
    use bevy::picking::backend::HitData;
    use bevy::picking::pointer::{Location, PointerId};
    use std::time::Duration;

    #[test]
    fn outside_map_rows_stay_closed_until_activated_and_can_be_closed_again() {
        let (session, frame, anchors) = relationships_fixture::fixture();
        let context = session.context();
        let mut app = App::new();
        app.insert_resource(session)
            .insert_resource(frame)
            .insert_resource(anchors)
            .init_resource::<ProductionNavigation>()
            .insert_resource(SelectedCounty(Some(1)))
            .insert_resource(PrimaryView::Map)
            .insert_resource(ObserverUiState {
                menu_open: false,
                splash_visible: false,
                ..default()
            })
            .add_systems(
                Startup,
                |mut commands: Commands, session: Res<ObserverSession>| {
                    let mut projection = NetworkProjection::default();
                    projection.external.insert(
                        NodeKey::Site("foreign".into()),
                        ExternalPeer {
                            site_id: "foreign".into(),
                            caption: "Foreign supplier".into(),
                        },
                    );
                    spawn_peers(&mut commands, &projection, &session.context());
                },
            )
            .add_systems(Update, sync_disclosure);
        app.update();
        let world = app.world_mut();
        let toggle = world
            .query_filtered::<Entity, With<Toggle>>()
            .single(world)
            .expect("toggle");
        let list = world
            .query_filtered::<Entity, With<PeerList>>()
            .single(world)
            .expect("list");
        assert_eq!(
            world.get::<Node>(list).expect("peer list").display,
            Display::None
        );
        world.trigger(PointerClick {
            entity: toggle,
            pointer: Pointer::new(
                PointerId::Mouse,
                Location {
                    target: bevy::camera::NormalizedRenderTarget::None {
                        width: 0,
                        height: 0,
                    },
                    position: Vec2::ZERO,
                },
            ),
            button: PointerButton::Primary,
            hit: HitData::new(Entity::PLACEHOLDER, 1.0, None, None),
            duration: Duration::ZERO,
            count: 1,
        });
        app.update();
        assert_eq!(
            app.world().get::<Node>(list).expect("peer list").display,
            Display::Flex
        );
        assert_eq!(
            app.world()
                .get::<AccessibilityNode>(toggle)
                .expect("toggle")
                .is_expanded(),
            Some(true)
        );
        app.world_mut().trigger(ObserverKeyboardActivate {
            entity: toggle,
            context: Some(context),
        });
        app.update();
        assert_eq!(
            app.world().get::<Node>(list).expect("peer list").display,
            Display::None
        );
    }
}
