//! Stable anchored callout layout; no animation or game action is attached.

use bevy::input_focus::tab_navigation::TabGroup;
use bevy::prelude::*;
use bevy::ui::FocusPolicy;

use super::runtime::{InterfaceTour, TourControl, TourRoot};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer::ObserverSession;
use crate::observer_focus::ObserverFocusTarget;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverUiState;
use crate::organizer::{ui, OrganizerClient};
use crate::ui::Interaction;

pub(super) const STEP_COUNT: usize = 7;

#[derive(Component)]
pub(super) struct Callout;
#[derive(Component)]
pub(super) struct Heading;
#[derive(Component)]
pub(super) struct Explanation;
#[derive(Component)]
pub(super) struct Highlight;

struct Step {
    heading: &'static str,
    anchor: &'static str,
    explanation: &'static str,
}

fn step(index: usize, client: &OrganizerClient) -> Step {
    match index {
        0 => Step {
            heading: "Your organization and workspace",
            anchor: "wayne.workspace",
            explanation: "This workspace shows your organization’s disclosed situation in the current period. This tour only explains the interface. It leaves your choices and the world unchanged.",
        },
        1 => Step {
            heading: "Map and selected subject",
            anchor: "wayne.subject",
            explanation: "The map locates the work. Select a disclosed subject to read its situation in the field dossier. World, Evidence and Archive offer context; undisclosed information remains unavailable.",
        },
        2 => Step {
            heading: "Three dated resource readings",
            anchor: "wayne.resources",
            explanation: "Cash and organizer-hours are controlled resources. Household time reports remaining hours in a closed period; next-period capacity is unknown. Unavailable means undisclosed, not zero. A draft reserves nothing.",
        },
        3 => Step {
            heading: "Choices and amount controls",
            anchor: "wayne.choices",
            explanation: if client.collection_preview().is_some() || !client.aid.is_empty() {
                "Choice cards show costs, partners and timing. Details expands the explanation. Contribution or aid amounts appear when the selected practice supports them. Editing a draft submits nothing; partner participation and outcomes remain independent."
            } else {
                "Choice cards show costs, partners and timing. Details expands the explanation. This campaign has no contribution or aid amount controls. Selecting a draft submits nothing; partner participation and outcomes remain independent."
            },
        },
        4 => Step {
            heading: "Review before Confirm",
            anchor: "wayne.review",
            explanation: "Review checks the selected draft and shows its actual terms, warnings and timing. Confirm is a separate action that submits the reviewed choice. This tour performs neither action and promises no outcome.",
        },
        5 => Step {
            heading: "Advance and processing",
            anchor: "wayne.advance",
            explanation: "Advance one period sits at the far right. While working, the header shows the actual operation stage and elapsed time, including the committed organizer refresh. It is not a percentage or a predicted result.",
        },
        _ => Step {
            heading: "Back, Organizing Home and results",
            anchor: "wayne.navigation",
            explanation: "Back closes a detail or returns to the previous view. Organizing Home returns to the current decision screen. Neither undoes gameplay. Read completed results in the disclosed reports and receipts. Next finishes this tour; replay it in Settings.",
        },
    }
}

pub(super) fn control(parent: &mut ChildSpawnerCommands, label: &str, control: TourControl) {
    parent
        .spawn((
            crate::ui::pressable(),
            control,
            ObserverFocusTarget::action(None),
            Node {
                padding: UiRect::axes(px(12), px(7)),
                border: UiRect::all(px(2)),
                flex_shrink: 0.0,
                flex_direction: if control == TourControl::Replay {
                    FlexDirection::Column
                } else {
                    FlexDirection::Row
                },
                ..default()
            },
            BackgroundColor(theme::PANEL),
            BorderColor::all(theme::BLUE),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_children(|button| {
            button.spawn(ui::text(label, 16.0, theme::PAPER));
            if control == TourControl::Replay {
                button.spawn(ui::text(
                    "Available in an open organizing campaign after any operation or refresh finishes.",
                    12.0,
                    theme::GRAY,
                ));
            }
        });
}

pub(super) fn spawn(mut commands: Commands) {
    commands
        .spawn((
            TourRoot,
            Name::new("wayne.interface-tour"),
            Node {
                display: Display::None,
                position_type: PositionType::Absolute,
                left: px(0),
                top: px(0),
                width: percent(100),
                height: percent(100),
                ..default()
            },
            BackgroundColor(Color::BLACK.with_alpha(0.30)),
            FocusPolicy::Block,
            TabGroup::modal(),
            ZIndex(30),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_children(|root| {
            root.spawn((
                Highlight,
                Node {
                    position_type: PositionType::Absolute,
                    border: UiRect::all(px(3)),
                    ..default()
                },
                BorderColor::all(theme::YELLOW),
                Pickable::IGNORE,
            ));
            root.spawn((
                Callout,
                Node {
                    position_type: PositionType::Absolute,
                    left: px(24),
                    bottom: px(24),
                    width: px(600),
                    max_width: percent(90),
                    padding: UiRect::all(px(18)),
                    border: UiRect::all(px(2)),
                    row_gap: px(10),
                    ..ui::column()
                },
                BackgroundColor(theme::INK),
                BorderColor::all(theme::YELLOW),
                ZIndex(1),
            ))
            .with_children(|panel| {
                panel.spawn((ui::text("", 21.0, theme::YELLOW), Heading));
                panel.spawn((ui::text("", 16.0, theme::PAPER), Explanation));
                panel.spawn(ui::row()).with_children(|row| {
                    control(row, "Previous", TourControl::Previous);
                    control(row, "Next", TourControl::Next);
                    control(row, "Skip [Esc]", TourControl::Skip);
                });
                panel.spawn(ui::text(
                    "Play is paused. Closing the tour leaves it paused.",
                    12.0,
                    theme::GRAY,
                ));
            });
        });
}

pub(super) fn paint(
    tour: Res<InterfaceTour>,
    client: Res<OrganizerClient>,
    session: Res<ObserverSession>,
    mut headings: Query<&mut Text, (With<Heading>, Without<Explanation>)>,
    mut explanations: Query<&mut Text, (With<Explanation>, Without<Heading>)>,
    mut buttons: Query<(
        &TourControl,
        &ObserverFocusTarget,
        &Interaction,
        &mut BackgroundColor,
        &mut Node,
    )>,
) {
    if let Some(index) = tour.step {
        let current = step(index, &client);
        for mut text in &mut headings {
            text.set_if_neq(Text::new(format!(
                "INTERFACE TOUR  ·  {} / {STEP_COUNT}\n{}",
                index + 1,
                current.heading
            )));
        }
        for mut text in &mut explanations {
            text.set_if_neq(Text::new(current.explanation));
        }
    }
    for (control, target, interaction, mut background, mut node) in &mut buttons {
        if *control == TourControl::Replay {
            let display = if session.organizer_enabled {
                Display::Flex
            } else {
                Display::None
            };
            if node.display != display {
                node.display = display;
            }
        }
        let color = if !target.available {
            theme::PANEL.with_alpha(0.5)
        } else if matches!(interaction, Interaction::Hovered | Interaction::Pressed) {
            theme::BLUE.with_alpha(0.35)
        } else {
            theme::PANEL
        };
        background.set_if_neq(BackgroundColor(color));
    }
}

type AnchorGeometry<'w, 's> = Query<
    'w,
    's,
    (
        &'static Name,
        &'static ComputedNode,
        &'static UiGlobalTransform,
    ),
    (Without<TourRoot>, Without<Callout>, Without<Highlight>),
>;

type CalloutGeometry<'w, 's> =
    Query<'w, 's, (&'static mut Node, &'static ComputedNode), (With<Callout>, Without<Highlight>)>;

/// Geometry is measured after layout and converted from physical UI coordinates.
pub(super) fn position(
    tour: Res<InterfaceTour>,
    client: Res<OrganizerClient>,
    ui_state: Res<ObserverUiState>,
    roots: Query<&ComputedNode, With<TourRoot>>,
    anchors: AnchorGeometry,
    mut highlights: Query<&mut Node, (With<Highlight>, Without<Callout>)>,
    mut callouts: CalloutGeometry,
) {
    let (Some(index), Ok(root)) = (tour.step, roots.single()) else {
        return;
    };
    if !ui_state.interface_tour_open {
        return;
    }
    let viewport = root.size() * root.inverse_scale_factor();
    if !viewport.is_finite() || viewport.min_element() <= 0.0 {
        return;
    }
    let anchor = step(index, &client).anchor;
    let target = anchors.iter().find_map(|(name, node, transform)| {
        if name.as_str() != anchor || node.size().min_element() <= 0.0 {
            return None;
        }
        let scale = root.inverse_scale_factor();
        let rect = Rect::from_center_size(transform.translation * scale, node.size() * scale);
        (rect.min.is_finite() && rect.max.is_finite())
            .then(|| rect.intersect(Rect::from_corners(Vec2::ZERO, viewport)))
    });
    for mut node in &mut highlights {
        if let Some(rect) = target {
            node.display = Display::Flex;
            node.left = px((rect.min.x - 4.0).max(0.0));
            node.top = px((rect.min.y - 4.0).max(0.0));
            node.width = px((rect.width() + 8.0).min(viewport.x));
            node.height = px((rect.height() + 8.0).min(viewport.y));
        } else {
            node.display = Display::None;
        }
    }
    for (mut node, computed) in &mut callouts {
        let size = computed.size() * computed.inverse_scale_factor();
        let x = ((viewport.x - size.x) * 0.5).max(12.0);
        let y = if target.is_some_and(|rect| rect.center().y > viewport.y * 0.5) {
            16.0
        } else {
            (viewport.y - size.y - 16.0).max(16.0)
        };
        node.left = px(x);
        node.top = px(y);
        node.bottom = Val::Auto;
    }
}
