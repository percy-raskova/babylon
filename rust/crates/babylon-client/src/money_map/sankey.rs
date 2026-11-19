//! A static, scrollable two-stage flow diagram occupies the same region as the county map.
use super::grouping;
use super::sankey_layout::{Band, DiagramLayout, Place};
use super::state::{Action, Measure, MoneyView, Observation, Page, Scope, Status, Target};
use super::{rail, sankey_image, sankey_layout, state};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer_layout::ObserverRegion;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use babylon_persistence::money_journal::LaborCarryAmount;
use bevy::picking::pointer::PointerButton;
use bevy::prelude::*;
use bevy::window::PrimaryWindow;

#[derive(Component)]
pub(super) struct Plot {
    scope: Scope,
    offset: u64,
    layout: DiagramLayout,
}

#[derive(PartialEq, Eq)]
struct PageKey {
    scope: Scope,
    offset: u64,
    status: Status,
}

pub(super) struct Canvas {
    key: PageKey,
    entity: Entity,
    image: Option<Handle<Image>>,
}

pub(super) fn paint(
    mut commands: Commands,
    view: Res<MoneyView>,
    obs: Observation,
    mut images: ResMut<Assets<Image>>,
    plots: Query<(&Plot, &ImageNode)>,
    mut drawn: Local<Option<Canvas>>,
) {
    if !view.is_changed()
        && !obs.ui.is_changed()
        && !obs.primary.is_changed()
        && !obs.session.is_changed()
    {
        return;
    }
    let active = obs.interactive() && view.shows_sankey() && !view.freight.enabled;
    let key = view.scope.as_ref().filter(|_| active).map(|scope| PageKey {
        scope: scope.clone(),
        offset: view.offset,
        status: view.status,
    });
    if let Some(current) = drawn.as_ref().filter(|p| Some(&p.key) == key.as_ref()) {
        if view.is_changed() {
            if let Some((plot, image)) = plots
                .iter()
                .find(|(p, _)| p.scope == current.key.scope && p.offset == current.key.offset)
            {
                if let Some(mut target) = images.get_mut(&image.image) {
                    *target = sankey_image::paint(&plot.layout, &view);
                }
            }
        }
        return;
    }
    if let Some(old) = drawn.take() {
        commands.entity(old.entity).despawn();
        if let Some(h) = old.image {
            images.remove(h.id());
        }
    }
    let Some(key) = key else { return };
    *drawn = Some(spawn_diagram(&mut commands, key, &view, &obs, &mut images));
}

fn heading(scope: &Scope, obs: &Observation) -> String {
    let home = rail::location(Some(&format!("county:{}", scope.county)), &obs.atlas);
    let tick = scope.context.tick;
    match scope.periods.window(tick) {
        Some(prior) => format!("{home} · Period {tick} · comparing period {}", prior.first),
        None => format!("{home} · Period {tick}"),
    }
}

fn boundary(panel: &mut ChildSpawnerCommands, title: &str, amount: &LaborCarryAmount, width: f32) {
    let hours = rail::labor_hours(&amount.recorded_micro_hours.to_string());
    let plural = |count| if count == 1 { "position" } else { "positions" };
    let mut text = format!(
        "{title} · {hours} across {} located {}",
        amount.positions,
        plural(amount.positions)
    );
    if amount.unknown_positions > 0 {
        use std::fmt::Write;
        write!(
            text,
            " · unknown prior labor in {} {}",
            amount.unknown_positions,
            plural(amount.unknown_positions)
        )
        .expect("writing to a String cannot fail");
    }
    panel
        .spawn((
            Node {
                width: percent(100),
                flex_direction: FlexDirection::Column,
                flex_shrink: 0.0,
                padding: UiRect::axes(px(10), px(5)),
                row_gap: px(3),
                ..default()
            },
            BackgroundColor(theme::PANEL),
            Pickable::IGNORE,
        ))
        .with_children(|stock| {
            stock.spawn(rail::label(
                text,
                16.0,
                theme::PAPER,
                ObserverFontRole::Body,
            ));
            stock.spawn((
                Node {
                    width: percent(width),
                    height: px(5),
                    ..default()
                },
                BackgroundColor(theme::BLUE),
                Pickable::IGNORE,
            ));
        });
}

fn spawn_diagram(
    commands: &mut Commands,
    key: PageKey,
    view: &MoneyView,
    obs: &Observation,
    images: &mut Assets<Image>,
) -> Canvas {
    let mut canvas = commands.spawn((
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
        Pickable::default(),
        DeclaredSurface::new(SurfaceId::ObserverProduction),
    ));
    let layout = sankey_layout::layout(&key.scope.county, &view.rows);
    let handle = (!layout.bands.is_empty()).then(|| images.add(sankey_image::paint(&layout, view)));
    canvas.with_children(|panel| {
        panel.spawn(rail::label(
            heading(&key.scope, obs),
            20.0,
            theme::PAPER,
            ObserverFontRole::Display,
        ));
        let balances = match &view.page {
            Some(Page::Labor(page)) => page.county_carry.as_ref(),
            _ => None,
        };
        let boundaries = balances.map(|carry| {
            let widths = sankey_layout::stock_widths(
                carry.opening.recorded_micro_hours,
                carry.closing.recorded_micro_hours,
            );
            (carry, widths)
        });
        if let Some((carry, widths)) = boundaries {
            boundary(panel, "Opening carry", &carry.opening, widths[0]);
            panel.spawn(rail::label(
                format!("Transfers during period {}", key.scope.context.tick),
                17.0,
                theme::PAPER,
                ObserverFontRole::Display,
            ));
        }
        movements(panel, &key, view, obs, layout, handle.as_ref());
        if let Some((carry, widths)) = boundaries {
            boundary(panel, "Closing carry", &carry.closing, widths[1]);
        }
    });
    Canvas {
        key,
        entity: canvas.id(),
        image: handle,
    }
}

fn movements(
    panel: &mut ChildSpawnerCommands,
    key: &PageKey,
    view: &MoneyView,
    obs: &Observation,
    layout: DiagramLayout,
    handle: Option<&Handle<Image>>,
) {
    let Some(image) = handle else {
        panel.spawn(rail::label(
            match (key.status, key.scope.measure, view.rows.is_empty()) {
                (Status::Ready, Measure::Labor, false) => {
                    "Movements are listed with no current recorded hours to draw."
                }
                (Status::Ready, Measure::Labor, true) => {
                    "No recorded labor movements on this page."
                }
                (Status::Ready, Measure::Money, _) => "No settled connections on this page.",
                _ => "Waiting for the period’s flow report.",
            },
            15.0,
            theme::GRAY,
            ObserverFontRole::Body,
        ));
        return;
    };
    panel
        .spawn(Node {
            width: percent(100),
            flex_shrink: 0.0,
            justify_content: JustifyContent::SpaceBetween,
            ..default()
        })
        .with_children(|header| {
            let from = match key.scope.measure {
                Measure::Money => "Payer",
                Measure::Labor => "Origin",
            };
            for text in [from, "Recipient"] {
                header.spawn(rail::label(
                    text,
                    17.0,
                    theme::PAPER,
                    ObserverFontRole::Display,
                ));
            }
        });
    panel
        .spawn(Node {
            width: percent(100),
            height: px(logical(f64::from(layout.height))),
            flex_shrink: 0.0,
            ..default()
        })
        .with_children(|graph| {
            column(graph, &layout.payers, obs, view, 0.0);
            column(graph, &layout.recipients, obs, view, 75.0);
            graph
                .spawn((
                    ImageNode::new(image.clone()).with_mode(NodeImageMode::Stretch),
                    Node {
                        position_type: PositionType::Absolute,
                        left: percent(25),
                        width: percent(50),
                        height: percent(100),
                        ..default()
                    },
                    Plot {
                        scope: key.scope.clone(),
                        offset: key.offset,
                        layout,
                    },
                ))
                .observe(select);
        });
}

#[allow(
    clippy::cast_possible_truncation,
    reason = "page geometry is limited to 21 group labels and 184 logical pixels of ribbon capacity"
)]
fn logical(p: f64) -> f32 {
    p as f32
}

fn column(
    parent: &mut ChildSpawnerCommands,
    nodes: &[Place],
    obs: &Observation,
    view: &MoneyView,
    left: f32,
) {
    for place in nodes {
        let Some(scope) = &view.scope else {
            return;
        };
        let captured = view
            .rows
            .iter()
            .find(|r| r.key.peer == place.key)
            .and_then(|r| r.label.as_deref());
        let text = grouping::peer_label(scope, place.key.as_deref(), captured, &obs.atlas);
        parent
            .spawn((
                Node {
                    position_type: PositionType::Absolute,
                    left: percent(left),
                    width: percent(25),
                    top: px(logical(place.top + 0.5 * place.thickness) - 20.0),
                    height: px(40),
                    padding: UiRect::horizontal(px(6)),
                    align_items: AlignItems::Center,
                    overflow: Overflow::clip(),
                    ..default()
                },
                Pickable::IGNORE,
            ))
            .with_child(rail::label(
                text,
                14.0,
                theme::PAPER,
                ObserverFontRole::Body,
            ));
    }
}

fn select(
    click: On<PointerClick>,
    plots: Query<(&Plot, &ComputedNode, &UiGlobalTransform)>,
    windows: Query<&Window, With<PrimaryWindow>>,
    observed: Observation,
    mut view: ResMut<MoneyView>,
    mut commands: Commands,
) {
    if click.button != PointerButton::Primary || !view.shows_sankey() {
        return;
    }
    let (Ok((plot, node, transform)), Ok(window)) = (plots.get(click.entity), windows.single())
    else {
        return;
    };
    let Some(point) =
        node.normalize_point(*transform, click.pointer.position * window.scale_factor())
    else {
        return;
    };
    let x = f64::from(point.x) + 0.5;
    let y = (f64::from(point.y) + 0.5) * f64::from(plot.layout.height);
    let hit = |b: &&Band| {
        let top = b.upper_at(x);
        y >= top && y < top + b.thickness
    };
    let selected = view.selected_row().map(|r| &r.key);
    let Some(band) = plot
        .layout
        .bands
        .iter()
        .filter(hit)
        .find(|b| selected == view.rows.get(b.row).map(|r| &r.key))
        .or_else(|| plot.layout.bands.iter().rev().find(hit))
    else {
        return;
    };
    if let Some(row) = view.rows.get(band.row) {
        let target = Target {
            scope: plot.scope.clone(),
            offset: plot.offset,
            action: Action::Select(row.key.clone()),
        };
        state::activate(&target, &observed, &mut view, &mut commands);
    }
}
