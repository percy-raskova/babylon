//! Unanchored counterparts stay a readable list; they are never fake counties.
use super::{usable, EconomyEntity, NetworkProjection};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer::ObservationContext;
use crate::observer_theme as theme;
use crate::observer_ui::{ObserverUiState, ObserverViewport};
use crate::production::{PrimaryView, ProductionCommand};
use bevy::prelude::*;

#[derive(Component)]
pub(super) struct ExternalPeers;

pub(super) fn spawn_peers(
    commands: &mut Commands,
    projection: &NetworkProjection,
    context: &ObservationContext,
) {
    if projection.external.is_empty() {
        return;
    }
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                flex_direction: FlexDirection::Column,
                row_gap: px(6),
                padding: UiRect::all(px(8)),
                overflow: Overflow::scroll_y(),
                ..default()
            },
            BackgroundColor(theme::INK),
            ZIndex(6),
            Visibility::Hidden,
            EconomyEntity,
            ExternalPeers,
            bevy::input_focus::tab_navigation::TabGroup::new(25),
            DeclaredSurface::new(SurfaceId::ObserverProduction),
        ))
        .with_children(|panel| {
            panel.spawn((
                Text::new(format!(
                    "{} direct counterparts outside this county map",
                    projection.external.len()
                )),
                TextFont {
                    font_size: 14.0,
                    ..default()
                },
                TextColor(theme::YELLOW),
                crate::observer_ui::ObserverFontRole::Body,
            ));
            for peer in projection.external.values() {
                crate::production::button(
                    panel,
                    &peer.caption,
                    ProductionCommand::Select {
                        site_id: peer.site_id.clone(),
                        context: context.clone(),
                    },
                );
            }
        });
}

pub(super) fn place_peers(
    ui: Res<ObserverUiState>,
    view: Res<PrimaryView>,
    viewport: Res<ObserverViewport>,
    scale: Res<UiScale>,
    mut panels: Query<(&mut Node, &mut Visibility), With<ExternalPeers>>,
) {
    for (mut node, mut visibility) in &mut panels {
        let bounds = viewport.0.filter(|_| usable(&ui, *view));
        visibility.set_if_neq(if bounds.is_some() {
            Visibility::Visible
        } else {
            Visibility::Hidden
        });
        if let Some(bounds) = bounds {
            let width = (bounds.width() - 16.0).clamp(0.0, 320.0);
            let height = (bounds.height() * 0.4).max(0.0);
            let mut next = node.clone();
            next.left = px((bounds.max.x - width - 8.0) / scale.0);
            next.top = px((bounds.max.y - height - 8.0) / scale.0);
            next.width = px(width / scale.0);
            next.max_height = px(height / scale.0);
            node.set_if_neq(next);
        }
    }
}
