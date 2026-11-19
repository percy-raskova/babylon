//! Fixed-size symbols anchored to the geographic map, with bounded displacement for close peers.
use super::ObserverMapCamera;
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer_theme as theme;
use crate::observer_ui::{ObserverUiState, ObserverViewport};
use crate::production::PrimaryView;
use crate::visual_assets::{MapSymbol, VisualAssets};
use bevy::a11y::AccessibilityNode;
use bevy::ecs::system::{EntityCommands, SystemParam};
use bevy::prelude::*;
use bevy::window::PrimaryWindow;

#[derive(Component)]
pub(crate) struct MapObstruction;

/// Window coordinates occupied by the controls and symbols above the map.
#[derive(Resource, Default)]
pub(super) struct MapLabelExclusions(pub(super) Vec<Rect>);

#[derive(Component)]
pub(super) struct Leader;

#[derive(Component)]
pub(crate) struct GeographicSymbol {
    pub(crate) anchor: Vec3,
    /// Lower values reserve space first. The selected and local groups precede other endpoints.
    pub(crate) priority: u8,
    pub(crate) symbol: MapSymbol,
    pub(crate) label: String,
    pub(crate) view: PrimaryView,
    pub(crate) surface: SurfaceId,
}

impl GeographicSymbol {
    pub(crate) fn spawn<'a>(
        self,
        commands: &'a mut Commands,
        assets: &VisualAssets,
        selected: bool,
    ) -> EntityCommands<'a> {
        let size = self.symbol.size();
        let width = size.max(36.0);
        let label = self.label.clone();
        let mut button = commands.spawn((
            crate::ui::pressable(),
            Name::new(label.clone()),
            Node {
                position_type: PositionType::Absolute,
                width: px(width),
                height: px(width),
                align_items: AlignItems::Center,
                justify_content: JustifyContent::Center,
                border: UiRect::all(px(2)),
                ..default()
            },
            BackgroundColor(theme::INK.with_alpha(0.91)),
            BorderColor::all(if selected { theme::YELLOW } else { theme::LAND }),
            ZIndex(if selected { 5 } else { 3 }),
            Visibility::Hidden,
            DeclaredSurface::new(self.surface),
        ));
        button
            .entry::<AccessibilityNode>()
            .and_modify(move |mut node| node.set_label(label));
        button.with_child((
            self.symbol.image(assets),
            Node {
                width: px(size - 4.0),
                height: px(size - 4.0),
                ..default()
            },
            Pickable::IGNORE,
        ));
        button.with_child((
            Leader,
            Node {
                position_type: PositionType::Absolute,
                height: px(1.5),
                display: Display::None,
                ..default()
            },
            BackgroundColor(theme::PAPER),
            Pickable::IGNORE,
        ));
        button.insert(self);
        button
    }
}

fn seat(point: Vec2, size: Vec2, bounds: Rect, taken: &[Rect]) -> Option<Rect> {
    if !bounds.contains(point) {
        return None;
    }
    let half = size * 0.5;
    let (short, long) = if size.x > size.y {
        (Vec2::Y, Vec2::X)
    } else {
        (Vec2::X, Vec2::Y)
    };
    let directions = [
        short,
        -short,
        long,
        -long,
        short + long,
        short - long,
        long - short,
        -short - long,
    ];
    for shift in std::iter::once(Vec2::ZERO).chain(
        [1.0, 2.0]
            .into_iter()
            .flat_map(|ring| directions.map(|direction| direction * ring)),
    ) {
        let center = point + shift * (size + Vec2::splat(6.0));
        let rect = Rect::from_corners(center - half, center + half);
        if bounds.contains(rect.min)
            && bounds.contains(rect.max)
            && taken
                .iter()
                .all(|other| rect.intersect(other.inflate(2.0)).is_empty())
        {
            return Some(rect);
        }
    }
    None
}

type ObstructionNodes<'w, 's> = Query<
    'w,
    's,
    (
        &'static ComputedNode,
        &'static UiGlobalTransform,
        &'static Visibility,
    ),
    (With<MapObstruction>, Without<GeographicSymbol>),
>;
type LeaderNodes<'w, 's> = Query<
    'w,
    's,
    (&'static mut Node, &'static mut UiTransform),
    (With<Leader>, Without<GeographicSymbol>),
>;

#[derive(SystemParam)]
pub(super) struct SymbolViewport<'w, 's> {
    ui: Res<'w, ObserverUiState>,
    view: Res<'w, PrimaryView>,
    viewport: Res<'w, ObserverViewport>,
    scale: Res<'w, UiScale>,
    camera: Query<'w, 's, (&'static Camera, &'static Transform), With<ObserverMapCamera>>,
    windows: Query<'w, 's, &'static Window, With<PrimaryWindow>>,
    obstructions: ObstructionNodes<'w, 's>,
}

pub(super) fn place(
    scene: SymbolViewport,
    mut markers: Query<(
        Entity,
        &GeographicSymbol,
        &Children,
        &mut Node,
        &mut Visibility,
    )>,
    mut leaders: LeaderNodes,
    mut exclusions: ResMut<MapLabelExclusions>,
) {
    let active = matches!(*scene.view, PrimaryView::Map | PrimaryView::Organizer)
        && !scene.ui.menu_open
        && !scene.ui.splash_visible
        && !scene.ui.archive_open
        && !scene.ui.history_open
        && !scene.ui.comparison_open
        && scene.ui.disclosure.is_none();
    let camera = scene
        .camera
        .single()
        .ok()
        .filter(|(camera, _)| active && camera.is_active)
        .map(|(camera, tf)| (camera, GlobalTransform::from(*tf)));
    let mut order: Vec<_> = markers
        .iter()
        .map(|(entity, m, ..)| (m.priority, m.symbol, m.label.as_str(), entity))
        .collect();
    order.sort_unstable();
    let entities: Vec<_> = order.into_iter().map(|(_, _, _, entity)| entity).collect();
    let mut occupied: Vec<Rect> = scene
        .windows
        .single()
        .ok()
        .into_iter()
        .flat_map(|window| {
            scene
                .obstructions
                .iter()
                .filter(|(node, _, visibility)| {
                    **visibility != Visibility::Hidden && node.size().min_element() > 0.0
                })
                .map(move |(node, transform, _)| {
                    Rect::from_center_size(
                        transform.affine().translation / window.scale_factor(),
                        node.size() / window.scale_factor(),
                    )
                })
        })
        .collect();
    for entity in entities {
        let Ok((_, marker, children, mut node, mut vis)) = markers.get_mut(entity) else {
            continue;
        };
        let rect = camera
            .as_ref()
            .filter(|_| marker.view == *scene.view && node.display != Display::None)
            .zip(scene.viewport.0)
            .and_then(|((camera, transform), bounds)| {
                let anchor = camera.world_to_viewport(transform, marker.anchor).ok()?;
                let (Val::Px(width), Val::Px(height)) = (node.width, node.height) else {
                    return None;
                };
                seat(
                    anchor,
                    Vec2::new(width, height) * scene.scale.0,
                    bounds,
                    &occupied,
                )
                .map(|rect| (rect, anchor))
            });
        vis.set_if_neq(if rect.is_some() {
            Visibility::Visible
        } else {
            Visibility::Hidden
        });
        if let Some((rect, anchor)) = rect {
            for child in children {
                if let Ok((line, rotation)) = leaders.get_mut(*child) {
                    locate_leader(rect, anchor, scene.scale.0, line, rotation);
                }
            }
            let left = px(rect.min.x / scene.scale.0);
            let top = px(rect.min.y / scene.scale.0);
            if node.left != left || node.top != top {
                node.left = left;
                node.top = top;
            }
            occupied.push(rect);
        }
    }
    exclusions.0 = occupied;
}

/// The callout ends at the tile border and points back to the exact projected location.
fn locate_leader(
    rect: Rect,
    anchor: Vec2,
    scale: f32,
    mut line: Mut<Node>,
    mut rotation: Mut<UiTransform>,
) {
    let offset = (anchor - rect.center()) / scale;
    let mut next = line.clone();
    next.display = Display::None;
    let half = rect.size() * 0.5 / scale;
    let edge_ratio = (offset.abs() / half).max_element();
    if edge_ratio > 1.0 {
        let start = offset / edge_ratio;
        let length = offset.distance(start);
        // Child absolute positioning begins inside the parent's two-pixel border.
        let middle = half - Vec2::splat(2.0) + start.midpoint(offset);
        next.display = Display::Flex;
        next.left = px(middle.x - length * 0.5);
        next.top = px(middle.y - 0.75);
        next.width = px(length);
        rotation.set_if_neq(UiTransform::from_rotation(Rot2::radians(
            offset.y.atan2(offset.x),
        )));
    }
    line.set_if_neq(next);
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn crowded_county_symbols_have_distinct_screen_targets() {
        let bounds = Rect::from_corners(Vec2::ZERO, Vec2::splat(600.0));
        let center = bounds.center();
        let mut taken = vec![];
        for symbol in [
            MapSymbol::Origin,
            MapSymbol::Producer,
            MapSymbol::Shop,
            MapSymbol::Utility,
        ] {
            let rect = seat(center, Vec2::splat(symbol.size().max(36.0)), bounds, &taken)
                .expect("space near centroid");
            assert!(taken.iter().all(|other| rect.intersect(*other).is_empty()));
            taken.push(rect);
        }
        let food = Vec2::new(164.0, 62.0);
        let first = seat(center, food, bounds, &[]).expect("food tag fits");
        let second = seat(center, food, bounds, &[first]).expect("neighbor fits");
        assert_eq!(second.size(), food);
        assert!(second.intersect(first).is_empty());
        assert!(seat(Vec2::splat(-1.0), Vec2::splat(36.0), bounds, &taken).is_none());
    }

    #[test]
    fn cook_and_wayne_cards_clear_the_atlas_dock_at_compact_fit() {
        let bounds = Rect::new(16.0, 84.0, 984.0, 498.0);
        let dock = Rect::new(16.0, 128.0, 271.0, 486.0);
        let size = Vec2::new(164.0, 62.0);
        let wayne = seat(Vec2::new(565.0, 264.0), size, bounds, &[dock]).expect("Wayne card");
        let cook_anchor = Vec2::new(435.0, 310.0);
        let cook = seat(cook_anchor, size, bounds, &[dock, wayne]).expect("Cook card");
        assert!(cook.intersect(dock).is_empty() && cook.intersect(wayne).is_empty());
        assert_eq!(
            cook.center().x.to_bits(),
            cook_anchor.x.to_bits(),
            "the short vertical move keeps Cook near its county"
        );
        let behind_dock = seat(Vec2::new(40.0, 310.0), size, bounds, &[dock, wayne])
            .expect("a county behind the dock can point to a visible card");
        assert!(behind_dock.min.x > dock.max.x);
    }
}
