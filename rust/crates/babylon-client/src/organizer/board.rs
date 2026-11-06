//! Composition of the native organizer workspace.
use super::scene::OrganizerSubject;
use super::ui::{
    self, ActionButton, DetailControls, OrganizerAction, OrganizerRoot, SceneDetail, SceneEvidence,
    SceneRoot, Scope, TextPart,
};
use super::workspace;
use super::workspace::ALL_PRACTICES;
use super::workspace_copy::{self as copy, Bulletin, DatedLink, Destination};
use super::{presentation, OrganizerInspector};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer_focus::ObserverFocusTarget;
use crate::observer_io::ObserverSet;
use crate::observer_theme as theme;
use crate::observer_ui::{ObserverCommand, ObserverDisclosure, ObserverFontRole};
use crate::production::PrimaryView;
use crate::production::ProductionCommand;
use crate::ui::{self as widgets, Interaction};
use crate::visual_assets::{SurfaceKind, VisualAssetId, VisualAssets};
use babylon_persistence::runtime_session::OrganizerChoice;
use bevy::input_focus::tab_navigation::TabGroup;
use bevy::prelude::*;

const PAPER: Color = Color::srgb_u8(229, 217, 191);
const PAPER_LIGHT: Color = Color::srgb_u8(246, 235, 212);
const RUST: Color = Color::srgb_u8(145, 64, 40);
const PRINT: Color = Color::srgb_u8(38, 38, 34);
const RAIL: Color = Color::srgb_u8(31, 36, 34);

#[derive(Component)]
pub(crate) struct Overlay;
#[derive(Component)]
struct Portrait(Option<VisualAssetId>);
#[derive(Component)]
pub(super) struct ChoicePair;
#[derive(Component)]
pub(crate) struct DecisionDeck;
#[derive(Component)]
pub(super) struct ComparisonCard(usize);
#[derive(Component)]
struct BulletinLinks;
#[derive(Component)]
struct StockPaper;
#[derive(Component)]
pub(super) struct PaperAction;
#[derive(Component)]
struct DispatchPanel;
#[derive(Component)]
struct PeriodTitle;
#[derive(Component)]
struct CardLine {
    slot: usize,
    field: CardField,
}
#[derive(Clone, Copy)]
enum CardField {
    Title,
    Terms,
    Status,
}

fn kicker(parent: &mut ChildSpawnerCommands, label: &str, color: Color) {
    parent
        .spawn(ui::text(label, 12.0, color))
        .insert(ObserverFontRole::Exact);
}

fn portrait(subject: OrganizerSubject) -> Option<VisualAssetId> {
    match subject {
        OrganizerSubject::Collective(_) => Some(VisualAssetId::GroupWayneCollective),
        OrganizerSubject::NeighborhoodGroup(_) => Some(VisualAssetId::GroupNeighborhoodContact),
        OrganizerSubject::WorkplaceCommittee(_) => Some(VisualAssetId::GroupWorkplaceCommittee),
        OrganizerSubject::Contributor(_) | OrganizerSubject::Workplace(_) => None,
    }
}

pub(super) fn thumbnail(parent: &mut ChildSpawnerCommands, subject: OrganizerSubject) {
    if let Some(id) = portrait(subject) {
        parent.spawn((
            Node {
                width: px(42),
                height: px(42),
                margin: UiRect::right(px(8)),
                flex_shrink: 0.0,
                ..default()
            },
            ImageNode::default(),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
            Portrait(Some(id)),
            Pickable::IGNORE,
        ));
    }
}

pub(super) fn spawn_workspace(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                width: percent(100),
                height: percent(100),
                display: Display::None,
                ..default()
            },
            OrganizerRoot,
            Pickable::IGNORE,
            ZIndex(7),
            TabGroup::new(8),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_children(|root| {
            masthead(root);
            dossier(root);
            deck(root);
            dispatch_panel(root);
        });
}

fn masthead(root: &mut ChildSpawnerCommands) {
    root.spawn((
        Overlay,
        Node {
            position_type: PositionType::Absolute,
            top: px(0),
            left: px(0),
            right: px(0),
            height: px(82),
            padding: UiRect::axes(px(18), px(2)),
            border: UiRect::bottom(px(2)),
            row_gap: px(2),
            ..ui::column()
        },
        BackgroundColor(theme::INK),
        BorderColor::all(theme::YELLOW),
    ))
    .with_children(|bar| {
        bar.spawn(Node {
            width: percent(100),
            height: px(40),
            flex_shrink: 0.0,
            column_gap: px(12),
            align_items: AlignItems::Center,
            ..default()
        })
        .with_children(|row| {
            row.spawn((ui::text("", 22.0, theme::PAPER), TextPart::Title))
                .insert((
                    ObserverFontRole::Display,
                    Node {
                        flex_grow: 1.0,
                        min_width: px(0),
                        ..default()
                    },
                ));
            ui::button(row, "Advance one period", OrganizerAction::Advance);
            crate::production::button(row, "World", ProductionCommand::Map);
            crate::production::button(row, "Evidence", ProductionCommand::Open);
            ui::button(row, "Archive", OrganizerAction::ArchiveWorkplace);
            crate::observer_ui::button(
                row,
                "Time",
                ObserverCommand::Disclosure(ObserverDisclosure::Time),
            );
            crate::observer_ui::button(row, "Menu", ObserverCommand::Menu);
        });
        bar.spawn((ui::text("", 14.0, theme::PAPER), TextPart::Means))
            .insert(Node {
                width: percent(100),
                height: px(34),
                flex_shrink: 0.0,
                min_width: px(0),
                ..default()
            });
    });
}

fn dossier(root: &mut ChildSpawnerCommands) {
    root.spawn((
        Overlay,
        Node {
            position_type: PositionType::Absolute,
            right: px(16),
            width: percent(26),
            top: px(87),
            bottom: px(266),
            padding: UiRect::all(px(12)),
            border: UiRect::top(px(3)),
            row_gap: px(6),
            ..ui::column()
        },
        BackgroundColor(RAIL),
        BorderColor::all(theme::COPPER),
    ))
    .with_children(|panel| {
        kicker(panel, "FIELD DOSSIER   /   WAYNE", theme::COPPER);
        ui::spawn_scrolling_reading(panel, |panel| {
            panel.spawn((
                ImageNode::default(),
                DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
                Portrait(None),
                Node {
                    width: percent(100),
                    aspect_ratio: Some(2.8),
                    flex_shrink: 0.0,
                    ..default()
                },
                Pickable::IGNORE,
            ));
            panel
                .spawn((ui::text("", 18.0, theme::PAPER), SceneDetail))
                .insert(ObserverFontRole::Display);
            panel.spawn((
                ui::text("", 14.0, theme::PAPER),
                TextPart::Situation,
                ObserverFocusTarget::reading(None),
            ));
            panel
                .spawn((ui::row(), SceneEvidence))
                .with_children(|links| {
                    ui::button(
                        links,
                        "Inspect selected evidence",
                        OrganizerAction::Inspect(OrganizerInspector::Evidence),
                    );
                });
            panel.spawn(ui::row()).with_children(|links| {
                for (label, dest) in [
                    ("Workplace evidence", OrganizerInspector::Evidence),
                    ("Relationships", OrganizerInspector::Relationships),
                    ("Direction / routine", OrganizerInspector::Direction),
                    ("Practice history", OrganizerInspector::Receipts),
                    ("Personal notes", OrganizerInspector::Notes),
                ] {
                    ui::button(links, label, OrganizerAction::Inspect(dest));
                }
                crate::observer_ui::button(links, "Trends", ObserverCommand::History);
            });
        });
    });
}

pub(super) fn subject_reading(scope: &Scope) -> String {
    let Some(view) = scope
        .client
        .view
        .as_ref()
        .filter(|view| view.period == scope.session.viewed_tick)
    else {
        return String::new();
    };
    let subject = scope
        .client
        .selected_subject
        .unwrap_or(OrganizerSubject::Collective(view.actor_id));
    match subject {
        OrganizerSubject::Workplace(_) | OrganizerSubject::WorkplaceCommittee(_) => {
            presentation::situation(view, scope.session.viewed_tick)
        }
        OrganizerSubject::Contributor(id) => view
            .positions
            .iter()
            .find(|position| position.contributor_id == id)
            .map_or_else(String::new, |position| {
                format!(
                    "{} hours committed · {}",
                    position.promised_hours, position.concern
                )
            }),
        OrganizerSubject::NeighborhoodGroup(id)
            if view.standing.partner_actor_id == id && view.standing.authorized =>
        {
            format!("{} organizer-hours for the saved contact practice when eligible. Participation is independent.", view.contact_hours)
        }
        OrganizerSubject::NeighborhoodGroup(_) => "Neighborhood work is paused.".into(),
        OrganizerSubject::Collective(_) => view.positions.first().map_or_else(
            || "No contributor statement available in this period.".into(),
            |position| {
                format!(
                    "{} · {}\n{}",
                    position.label, position.concern, position.objection
                )
            },
        ),
    }
}

fn deck(root: &mut ChildSpawnerCommands) {
    root.spawn((
        Overlay,
        DecisionDeck,
        Node {
            position_type: PositionType::Absolute,
            left: px(16),
            right: percent(28),
            bottom: px(12),
            padding: UiRect::all(px(12)),
            row_gap: px(6),
            border: UiRect::top(px(4)),
            ..ui::column()
        },
        BackgroundColor(PAPER),
        BorderColor::all(RUST),
    ))
    .with_children(|deck| {
        deck.spawn((
            StockPaper,
            ImageNode::default(),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
            Node {
                position_type: PositionType::Absolute,
                left: px(0),
                right: px(0),
                top: px(0),
                bottom: px(0),
                ..default()
            },
            Pickable::IGNORE,
        ));
        deck.spawn(Node {
            align_items: AlignItems::Center,
            column_gap: px(8),
            flex_shrink: 0.0,
            ..default()
        })
        .with_children(|bar| {
            bar.spawn((ui::text("", 24.0, PRINT), TextPart::ChoiceHeading))
                .insert((
                    ObserverFontRole::Display,
                    Node {
                        flex_grow: 1.0,
                        flex_basis: px(0),
                        min_width: px(0),
                        ..default()
                    },
                ));
            let practices = ui::button(
                bar,
                "All practices",
                OrganizerAction::Inspect(OrganizerInspector::Practices),
            );
            bar.commands().entity(practices).insert(PaperAction);
            let review = ui::button(bar, "Review choice", OrganizerAction::Review);
            bar.commands().entity(review).insert(PaperAction);
        });
        deck.spawn((
            ChoicePair,
            Node {
                flex_shrink: 0.0,
                min_height: px(0),
                column_gap: px(8),
                row_gap: px(8),
                overflow: Overflow::scroll_y(),
                ..default()
            },
        ))
        .with_children(comparison_cards);
        deck.spawn(Node {
            align_items: AlignItems::Center,
            column_gap: px(10),
            flex_shrink: 0.0,
            ..default()
        })
        .with_children(|foot| {
            foot.spawn((ui::text("", 12.0, PRINT), TextPart::DraftStatus));
            foot.spawn((ui::text("", 13.0, RUST), TextPart::Message))
                .insert(Node {
                    flex_grow: 1.0,
                    flex_basis: px(0),
                    flex_shrink: 1.0,
                    min_width: px(0),
                    ..default()
                });
        });
    });
}

fn comparison_cards(pair: &mut ChildSpawnerCommands) {
    for (i, choice) in [OrganizerChoice::Reinforce, OrganizerChoice::Hold]
        .into_iter()
        .enumerate()
    {
        pair.spawn((
            widgets::pressable(),
            ComparisonCard(i),
            ActionButton(OrganizerAction::Choose(choice)),
            ObserverFocusTarget::action(None),
            Node {
                flex_basis: px(0),
                flex_grow: 1.0,
                flex_shrink: 0.0,
                min_width: px(0),
                padding: UiRect::axes(px(12), px(7)),
                border: UiRect::left(px(4)),
                row_gap: px(3),
                ..ui::column()
            },
            BackgroundColor(PAPER_LIGHT),
            BorderColor::all(RUST),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_children(|card| {
            card.spawn((
                ui::text("", 12.0, RUST),
                CardLine {
                    slot: i,
                    field: CardField::Status,
                },
            ))
            .insert(ObserverFontRole::Exact);
            card.spawn((
                ui::text("", 20.0, PRINT),
                CardLine {
                    slot: i,
                    field: CardField::Title,
                },
            ))
            .insert(ObserverFontRole::Display);
            card.spawn((
                ui::text("", 15.0, PRINT),
                CardLine {
                    slot: i,
                    field: CardField::Terms,
                },
            ));
        });
    }
}

fn dispatch_panel(root: &mut ChildSpawnerCommands) {
    root.spawn((
        Overlay,
        DispatchPanel,
        Node {
            position_type: PositionType::Absolute,
            right: px(16),
            bottom: px(12),
            width: percent(26),
            height: px(240),
            max_height: px(240),
            padding: UiRect::all(px(13)),
            border: UiRect::top(px(4)),
            row_gap: px(6),
            ..ui::column()
        },
        BackgroundColor(RAIL),
        BorderColor::all(theme::YELLOW),
    ))
    .with_children(|panel| {
        panel
            .spawn((ui::text("", 23.0, theme::PAPER), PeriodTitle))
            .insert(ObserverFontRole::Display);
        ui::spawn_scrolling_reading(panel, |reading| {
            reading.spawn((
                ui::text("", 15.0, theme::PAPER),
                TextPart::Aftermath,
                ObserverFocusTarget::reading(None),
            ));
            reading.spawn((ui::row(), BulletinLinks));
        });
    });
}

pub(super) fn all_practices(body: &mut ChildSpawnerCommands) {
    body.spawn((ui::column(), DetailControls(OrganizerInspector::Practices)))
        .with_children(|list| {
            for choice in ALL_PRACTICES {
                ui::spawn_approach(list, choice);
            }
        });
}

fn paint_cards(
    scope: Scope,
    mut cards: Query<(
        &ComparisonCard,
        &mut ActionButton,
        Ref<Interaction>,
        &mut BackgroundColor,
        &mut BorderColor,
    )>,
    mut texts: Query<(&CardLine, &mut Text)>,
) {
    if *scope.view != PrimaryView::Organizer {
        return;
    }
    if !(scope.client.is_changed()
        || scope.session.is_changed()
        || scope.view.is_changed()
        || cards
            .iter()
            .any(|(_, _, interaction, _, _)| interaction.is_changed()))
    {
        return;
    }
    let choices = workspace::comparison(&scope.client, &scope.session);
    let mut pointer_cues = ["", ""];
    for (slot, mut button, interaction, mut bg, mut border) in &mut cards {
        if let Some(choices) = &choices {
            let choice = &choices.alternatives[slot.0];
            button.set_if_neq(ActionButton(OrganizerAction::Choose(choice.choice)));
            let selected = choice.choice == choices.draft_choice;
            let hovered = *interaction != Interaction::None;
            pointer_cues[slot.0] = match *interaction {
                Interaction::Hovered => "HOVER   /   ",
                Interaction::Pressed => "PRESSED   /   ",
                Interaction::None => "",
            };
            bg.set_if_neq(BackgroundColor(if hovered || selected {
                PAPER_LIGHT
            } else {
                PAPER
            }));
            border.set_if_neq(BorderColor::all(if selected {
                RUST
            } else {
                Color::srgb_u8(142, 129, 103)
            }));
        }
    }
    for (field, mut value) in &mut texts {
        let next = choices.as_ref().map_or_else(
            || match field.field {
                CardField::Status => "UNAVAILABLE".into(),
                CardField::Title => {
                    if scope.session.viewed_tick == scope.session.durable_tick {
                        "Awaiting current terms".into()
                    } else {
                        "Historical terms unavailable".into()
                    }
                }
                CardField::Terms => String::new(),
            },
            |choices| {
                let term = &choices.alternatives[field.slot];
                match field.field {
                    CardField::Title => term.title.into(),
                    CardField::Terms => copy::terms(term),
                    CardField::Status => {
                        let status = if term.choice == choices.draft_choice {
                            "DRAFT"
                        } else {
                            "ALTERNATIVE"
                        };
                        format!(
                            "{}{status}   /   P{}   /   {}",
                            pointer_cues[field.slot],
                            term.captured_period,
                            copy::availability(term.availability)
                        )
                    }
                }
            },
        );
        value.set_if_neq(Text::new(next));
    }
}

#[derive(Component)]
struct HistoryLinks;

pub(super) fn history_links(parent: &mut ChildSpawnerCommands) {
    parent.spawn((ui::row(), HistoryLinks));
}

fn paint_history_links(
    scope: Scope,
    mut commands: Commands,
    regions: Query<Entity, With<HistoryLinks>>,
    mut cache: Local<Vec<(String, DatedLink)>>,
) {
    if scope.client.inspector != OrganizerInspector::Receipts
        || !(scope.client.is_changed() || scope.session.is_changed())
    {
        return;
    }
    let mut links = Vec::new();
    if let Some(dispatch) = workspace::dispatch(&scope.client, scope.session.viewed_tick) {
        for report in dispatch
            .history
            .reports
            .iter()
            .chain(&dispatch.current.reports)
        {
            let observation = report.observation;
            links.push((
                format!(
                    "{} · observed P{} / acquired P{}",
                    report.source.label, observation.observed_period, observation.acquired_period
                ),
                DatedLink::new(
                    &scope.session,
                    dispatch.period,
                    Destination::Detail(report.destination),
                ),
            ));
        }
    }
    if *cache == links {
        return;
    }
    for entity in &regions {
        commands
            .entity(entity)
            .despawn_children()
            .with_children(|row| {
                for (caption, link) in &links {
                    ui::button(row, caption, OrganizerAction::Follow(*link));
                }
            });
    }
    *cache = links;
}

fn paint_bulletin(
    scope: Scope,
    mut commands: Commands,
    mut cached: Local<Option<Bulletin>>,
    links: Query<Entity, With<BulletinLinks>>,
    mut panels: Query<&mut Node, With<DispatchPanel>>,
    mut text: Query<(&mut Text, Option<&PeriodTitle>, Option<&TextPart>)>,
) {
    if *scope.view != PrimaryView::Organizer
        || !(scope.client.is_changed() || scope.session.is_changed() || scope.view.is_changed())
    {
        return;
    }
    let next = copy::bulletin(&scope);
    if cached.as_ref() == Some(&next) {
        return;
    }
    for mut panel in &mut panels {
        let height = if next.compact { Val::Auto } else { px(240) };
        if panel.height != height {
            panel.height = height;
        }
    }
    for (mut text, heading, part) in &mut text {
        if heading.is_some() {
            text.set_if_neq(Text::new(&next.heading));
        } else if matches!(part, Some(TextPart::Aftermath)) {
            text.set_if_neq(Text::new(&next.copy));
        }
    }
    if cached.as_ref().is_none_or(|old| old.links != next.links) {
        for entity in &links {
            commands
                .entity(entity)
                .despawn_children()
                .with_children(|links| {
                    for (caption, link) in &next.links {
                        ui::button(links, caption, OrganizerAction::Follow(*link));
                    }
                });
        }
    }
    *cached = Some(next);
}

fn paint_portraits(
    scope: Scope,
    assets: Option<Res<VisualAssets>>,
    mut images: Query<(Ref<Portrait>, &mut ImageNode, &mut Node)>,
) {
    let Some(assets) = assets else {
        return;
    };
    if *scope.view != PrimaryView::Organizer {
        return;
    }
    for (portrait_node, mut image, mut node) in &mut images {
        if !(portrait_node.is_added()
            || scope.client.is_changed()
            || scope.session.is_changed()
            || scope.view.is_changed()
            || assets.is_changed())
        {
            continue;
        }
        let id = portrait_node.0.or_else(|| {
            let scene = scope.client.scene_for(&scope.session)?;
            let node = scope
                .client
                .selected_subject
                .and_then(|subject| scene.nodes.iter().find(|node| node.subject == subject))
                .or_else(|| scene.nodes.first())?;
            portrait(node.subject)
        });
        let display = if id.is_some() {
            Display::Flex
        } else {
            Display::None
        };
        if node.display != display {
            node.display = display;
        }
        if let Some(id) = id {
            let mut next = ImageNode::new(assets.image(id));
            if portrait_node.0.is_none() {
                // Dossier art uses the central landscape band of each 512px square.
                next.rect = Some(Rect::new(0.0, 112.0, 512.0, 112.0 + 512.0 / 2.8));
            }
            if image.image != next.image || image.rect != next.rect {
                *image = next;
            }
        }
    }
}

fn print_paper(
    assets: Option<Res<VisualAssets>>,
    mut paper: Query<&mut ImageNode, With<StockPaper>>,
) {
    let Some(assets) = assets else {
        return;
    };
    if !assets.is_changed() {
        return;
    }
    for mut image in &mut paper {
        *image = ImageNode::from_atlas_image(
            assets.surface_atlas.clone(),
            TextureAtlas {
                layout: assets.surface_layout.clone(),
                index: SurfaceKind::Paper.index(),
            },
        )
        .with_mode(NodeImageMode::Tiled {
            tile_x: true,
            tile_y: true,
            stretch_value: 1.0,
        })
        .with_color(Color::WHITE.with_alpha(0.16));
    }
}

fn fit_scene(
    decks: Query<&ComputedNode, With<DecisionDeck>>,
    mut scenes: Query<&mut Node, With<SceneRoot>>,
) {
    let Ok(deck) = decks.single() else {
        return;
    };
    // Keep the map and its relation reading above the actual comparison text.
    let bottom = px(deck.size().y * deck.inverse_scale_factor + 26.0);
    for mut scene in &mut scenes {
        if scene.bottom != bottom {
            scene.bottom = bottom;
        }
    }
}

pub(super) fn install(app: &mut App) {
    app.add_systems(
        Update,
        (
            fit_scene,
            paint_cards,
            paint_bulletin,
            paint_history_links,
            print_paper,
            paint_portraits,
        )
            .in_set(ObserverSet::Paint),
    );
}
