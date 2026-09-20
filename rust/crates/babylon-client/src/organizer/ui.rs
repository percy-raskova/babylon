//! Native Bevy controls and evidence inspectors for the lawful organizer projection.

use babylon_persistence::runtime_session::{OrganizerChoice, OrganizerInquiry};
use bevy::ecs::system::SystemParam;
use bevy::input::{
    keyboard::{Key, KeyboardInput},
    ButtonState,
};
use bevy::input_focus::tab_navigation::TabGroup;
use bevy::input_focus::{FocusedInput, InputFocus};
use bevy::prelude::*;

use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer::ObserverSession;
use crate::observer_focus::{
    ObserverFocusSystems, ObserverFocusTarget, ObserverKeyboardActivate, ObserverKeyboardClaim,
};
use crate::observer_io::ObserverSet;
use crate::observer_theme as theme;
use crate::observer_ui::{ObserverCommand, ObserverFontRole, ObserverUiState};
use crate::production::PrimaryView;

use super::{presentation, OrganizerClient, OrganizerInspector, RequestKind};

#[derive(Message, Clone, Copy, Debug)]
pub(crate) enum OrganizerAction {
    Open,
    Choose(OrganizerChoice),
    Review,
    Confirm,
    Advance,
    Refresh,
    Inspect(OrganizerInspector),
    OpenReferences,
    PreviousEvidence,
    NextEvidence,
    KeepEvidence,
    RemoveReference,
    CloseInspector,
    ArchiveWorkplace,
    ArchiveOrganization,
}

/// Route shell shortcuts through the same availability checks as organizer controls.
#[derive(Event)]
pub(crate) struct OrganizerActionRequested(pub OrganizerAction);

#[derive(Event)]
pub(crate) struct OrganizerEvidenceRequested;

#[derive(Event)]
pub(crate) struct OrganizerArchiveRequested {
    pub organization: bool,
}

#[derive(Component)]
pub(crate) struct OrganizerInspectorRoot;
#[derive(Component)]
struct OrganizerRoot;
#[derive(Component)]
struct InspectorShield;
#[derive(Component, Clone, Copy)]
struct ActionButton(OrganizerAction);
#[derive(Component)]
struct NotesField;
#[derive(Component)]
struct DetailControls(OrganizerInspector);
#[derive(Component)]
struct ScrollHint(Entity);

#[derive(Component, Clone, Copy)]
enum TextPart {
    Title,
    Situation,
    Means,
    Context,
    Aftermath,
    ChoiceHeading,
    Approach(OrganizerChoice),
    ChoiceMarker(OrganizerChoice),
    Review,
    Message,
    Notes,
    DraftStatus,
    ReferenceSummary,
    InspectorTitle,
    InspectorBody,
}

fn text(value: impl Into<String>, size: f32, color: Color) -> impl Bundle {
    (
        Text::new(value),
        TextFont {
            font_size: size,
            ..default()
        },
        TextColor(color),
        TextLayout::new_with_linebreak(bevy::text::LineBreak::WordOrCharacter),
        Node {
            min_width: px(0),
            max_width: percent(100),
            flex_shrink: 0.0,
            ..default()
        },
        ObserverFontRole::Body,
        DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
    )
}

fn column() -> Node {
    Node {
        flex_direction: FlexDirection::Column,
        row_gap: px(14),
        min_width: px(0),
        ..default()
    }
}

fn row() -> Node {
    Node {
        flex_wrap: FlexWrap::Wrap,
        column_gap: px(8),
        row_gap: px(8),
        flex_shrink: 0.0,
        min_width: px(0),
        ..default()
    }
}

pub(crate) fn button(parent: &mut ChildSpawnerCommands, label: &str, action: OrganizerAction) {
    parent
        .spawn((
            Button,
            ActionButton(action),
            ObserverFocusTarget::action(None),
            Node {
                padding: UiRect::axes(px(12), px(10)),
                border: UiRect::bottom(px(2)),
                min_width: px(0),
                flex_shrink: 0.0,
                ..default()
            },
            BackgroundColor(theme::PANEL),
            BorderColor::all(theme::GRAY),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_child(text(label, 15.0, theme::PAPER));
}

fn spawn(mut commands: Commands) {
    commands.spawn((
        Node {
            position_type: PositionType::Absolute,
            width: percent(100),
            height: percent(100),
            display: Display::None,
            ..default()
        },
        BackgroundColor(theme::INK.with_alpha(0.8)),
        ZIndex(24),
        InspectorShield,
        DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
    ));

    spawn_workspace(&mut commands);
    spawn_inspector(&mut commands);
}

fn spawn_workspace(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                left: px(24),
                right: px(24),
                top: px(88),
                bottom: px(60),
                row_gap: px(14),
                display: Display::None,
                ..column()
            },
            BackgroundColor(theme::INK),
            ZIndex(7),
            OrganizerRoot,
            TabGroup::new(8),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_children(|root| {
            spawn_identity(root);
            root.spawn(Node {
                flex_grow: 1.0,
                min_height: px(0),
                column_gap: px(18),
                ..default()
            })
            .with_children(|body| {
                spawn_briefing(body);
                spawn_approaches(body);
            });
            spawn_decision_footer(root);
        });
}

fn spawn_identity(root: &mut ChildSpawnerCommands) {
    root.spawn(Node {
        justify_content: JustifyContent::SpaceBetween,
        align_items: AlignItems::Center,
        column_gap: px(24),
        flex_shrink: 0.0,
        ..default()
    })
    .with_children(|header| {
        header
            .spawn(Node {
                row_gap: px(2),
                ..column()
            })
            .with_children(|identity| {
                identity.spawn(text("YOU DIRECT", 11.0, theme::GRAY));
                identity
                    .spawn((
                        text("Wayne Organizing Collective", 27.0, theme::PAPER),
                        TextPart::Title,
                    ))
                    .insert(ObserverFontRole::Display);
            });
        header.spawn((
            text("Opening the organization…", 16.0, theme::YELLOW),
            TextPart::Means,
            ObserverFocusTarget::reading(None),
        ));
    });
}

fn spawn_briefing(body: &mut ChildSpawnerCommands) {
    body.spawn((
        Node {
            flex_grow: 1.0,
            flex_basis: px(0),
            min_height: px(0),
            padding: UiRect::all(px(16)),
            row_gap: px(4),
            ..column()
        },
        BackgroundColor(theme::PANEL),
    ))
    .with_children(|briefing| spawn_scrolling_reading(briefing, spawn_briefing_content));
}

fn spawn_briefing_content(briefing: &mut ChildSpawnerCommands) {
    briefing.spawn(text("OUR SITUATION", 13.0, theme::YELLOW));
    briefing.spawn((
        text("", 15.0, theme::PAPER),
        TextPart::Context,
        ObserverFocusTarget::reading(None),
    ));
    briefing.spawn(text("WORKPLACE REPORT", 12.0, theme::YELLOW));
    briefing.spawn((
        text("Opening the latest report…", 15.0, theme::PAPER),
        TextPart::Situation,
        ObserverFocusTarget::reading(None),
    ));
    briefing.spawn(text("LAST PERIOD", 12.0, theme::YELLOW));
    briefing.spawn((
        text("", 14.0, theme::PAPER),
        TextPart::Aftermath,
        ObserverFocusTarget::reading(None),
    ));
    briefing.spawn(row()).with_children(|links| {
        button(
            links,
            "Workplace evidence",
            OrganizerAction::Inspect(OrganizerInspector::Evidence),
        );
        button(
            links,
            "Relationships",
            OrganizerAction::Inspect(OrganizerInspector::Relationships),
        );
        button(
            links,
            "Direction / routine",
            OrganizerAction::Inspect(OrganizerInspector::Direction),
        );
        button(
            links,
            "Practice history",
            OrganizerAction::Inspect(OrganizerInspector::Receipts),
        );
        button(
            links,
            "Personal notes",
            OrganizerAction::Inspect(OrganizerInspector::Notes),
        );
    });
}

fn spawn_approaches(body: &mut ChildSpawnerCommands) {
    body.spawn(Node {
        flex_grow: 2.0,
        flex_basis: px(0),
        min_height: px(0),
        row_gap: px(4),
        ..column()
    })
    .with_children(|choices| spawn_scrolling_reading(choices, spawn_approach_grid));
}

fn spawn_approach_grid(choices: &mut ChildSpawnerCommands) {
    choices.spawn((text("", 13.0, theme::YELLOW), TextPart::ChoiceHeading));
    for pair in [
        [
            OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
            OrganizerChoice::Inquiry(OrganizerInquiry::MaintenanceReceived),
        ],
        [OrganizerChoice::Reinforce, OrganizerChoice::Hold],
    ] {
        choices
            .spawn(Node {
                column_gap: px(10),
                min_width: px(0),
                ..default()
            })
            .with_children(|cards| {
                for choice in pair {
                    spawn_approach(cards, choice);
                }
            });
    }
}

fn spawn_scrolling_reading(
    parent: &mut ChildSpawnerCommands,
    contents: impl FnOnce(&mut ChildSpawnerCommands),
) {
    let reading = parent
        .spawn(Node {
            flex_grow: 1.0,
            min_height: px(0),
            row_gap: px(10),
            overflow: Overflow::scroll_y(),
            ..column()
        })
        .with_children(contents)
        .id();
    parent
        .spawn((text("", 12.0, theme::GRAY), ScrollHint(reading)))
        .insert(Node {
            height: px(16),
            min_height: px(16),
            flex_shrink: 0.0,
            ..default()
        });
}

fn scroll_hint(computed: &ComputedNode) -> &'static str {
    let Some(maximum) = crate::observer_focus::scroll_max(computed) else {
        return "";
    };
    if maximum.y <= 1.0 {
        return "";
    }
    let position = computed.scroll_position.y * computed.inverse_scale_factor;
    match (position > 1.0, maximum.y - position > 1.0) {
        (true, true) => "More above and below · scroll this panel",
        (true, false) => "More above · scroll this panel",
        (false, true) => "More below · scroll this panel",
        (false, false) => "",
    }
}

fn paint_scroll_hints(regions: Query<&ComputedNode>, mut hints: Query<(&ScrollHint, &mut Text)>) {
    for (hint, mut text) in &mut hints {
        let label = regions.get(hint.0).map_or("", scroll_hint);
        if text.0 != label {
            text.0 = label.into();
        }
    }
}

fn spawn_approach(cards: &mut ChildSpawnerCommands, choice: OrganizerChoice) {
    cards
        .spawn((
            Button,
            ActionButton(OrganizerAction::Choose(choice)),
            ObserverFocusTarget::action(None),
            Node {
                flex_grow: 1.0,
                flex_basis: px(0),
                padding: UiRect::all(px(14)),
                border: UiRect::left(px(3)),
                row_gap: px(6),
                ..column()
            },
            BackgroundColor(theme::PANEL),
            BorderColor::all(theme::GRAY),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_children(|card| {
            card.spawn((
                text("SELECT", 11.0, theme::YELLOW),
                TextPart::ChoiceMarker(choice),
            ));
            card.spawn(text(presentation::choice(choice), 18.0, theme::PAPER));
            card.spawn((text("", 14.0, theme::GRAY), TextPart::Approach(choice)));
        });
}

fn spawn_decision_footer(root: &mut ChildSpawnerCommands) {
    root.spawn((
        Node {
            padding: UiRect::all(px(14)),
            column_gap: px(20),
            flex_shrink: 0.0,
            border: UiRect::top(px(2)),
            ..default()
        },
        BackgroundColor(theme::PANEL),
        BorderColor::all(theme::YELLOW),
    ))
    .with_children(|footer| {
        footer
            .spawn(Node {
                flex_grow: 1.0,
                flex_basis: px(0),
                row_gap: px(6),
                ..column()
            })
            .with_children(|summary| {
                summary.spawn((
                    text("", 15.0, theme::PAPER),
                    TextPart::Review,
                    ObserverFocusTarget::reading(None),
                ));
                summary.spawn((text("", 13.0, theme::YELLOW), TextPart::Message));
                summary.spawn((text("", 11.0, theme::GRAY), TextPart::DraftStatus));
            });
        footer
            .spawn(Node {
                width: px(338),
                flex_shrink: 0.0,
                row_gap: px(8),
                ..column()
            })
            .with_children(|controls| {
                controls.spawn(row()).with_children(|buttons| {
                    button(buttons, "Review choice", OrganizerAction::Review);
                    button(buttons, "Confirm ruling", OrganizerAction::Confirm);
                });
                button(controls, "Advance one period", OrganizerAction::Advance);
            });
    });
}

fn spawn_inspector(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                left: percent(9),
                right: percent(9),
                top: px(98),
                bottom: px(48),
                padding: UiRect::all(px(22)),
                border: UiRect::all(px(2)),
                display: Display::None,
                ..column()
            },
            BackgroundColor(theme::INK),
            BorderColor::all(theme::YELLOW),
            ZIndex(25),
            OrganizerInspectorRoot,
            TabGroup::modal(),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_children(|panel| {
            panel.spawn(row()).with_children(|bar| {
                bar.spawn((
                    text("Evidence", 24.0, theme::YELLOW),
                    TextPart::InspectorTitle,
                ));
                button(
                    bar,
                    "Return to decision [Esc]",
                    OrganizerAction::CloseInspector,
                );
                button(
                    bar,
                    "Cited workplace Archive",
                    OrganizerAction::ArchiveWorkplace,
                );
                button(
                    bar,
                    "Our practice Archive",
                    OrganizerAction::ArchiveOrganization,
                );
            });
            panel.spawn((text("", 12.0, theme::GRAY), TextPart::DraftStatus));
            panel.spawn((text("", 13.0, theme::YELLOW), TextPart::Message));
            panel
                .spawn((column(), DetailControls(OrganizerInspector::Evidence)))
                .with_children(|controls| {
                    controls.spawn(row()).with_children(|buttons| {
                        button(
                            buttons,
                            "Previous report",
                            OrganizerAction::PreviousEvidence,
                        );
                        button(buttons, "Next report", OrganizerAction::NextEvidence);
                        button(
                            buttons,
                            "Keep report in draft",
                            OrganizerAction::KeepEvidence,
                        );
                        button(
                            buttons,
                            "Remove saved reference",
                            OrganizerAction::RemoveReference,
                        );
                    });
                });
            panel
                .spawn((row(), DetailControls(OrganizerInspector::Direction)))
                .with_children(|controls| {
                    button(
                        controls,
                        "Pause routine",
                        OrganizerAction::Choose(OrganizerChoice::PauseStanding),
                    );
                    button(
                        controls,
                        "Authorize / resume routine",
                        OrganizerAction::Choose(OrganizerChoice::ResumeStanding),
                    );
                    button(
                        controls,
                        "Refresh committed situation",
                        OrganizerAction::Refresh,
                    );
                });
            spawn_scrolling_reading(panel, |body| {
                spawn_notes(body);
                body.spawn((
                    text("", 17.0, theme::PAPER),
                    TextPart::InspectorBody,
                    ObserverFocusTarget::reading(None),
                ));
            });
        });
}

fn spawn_notes(body: &mut ChildSpawnerCommands) {
    body.spawn((column(), DetailControls(OrganizerInspector::Notes)))
        .with_children(|notes| {
            notes.spawn(text("Your notes and references stay with this draft. Editing them spends no time and submits no ruling.", 15.0, theme::GRAY));
            notes.spawn((
                Button, NotesField, ObserverFocusTarget::text_input(None),
                Node { min_height: px(160), padding: UiRect::all(px(12)),
                    border: UiRect::all(px(1)), width: percent(100), flex_shrink: 0.0, ..default() },
                BackgroundColor(theme::PANEL), BorderColor::all(theme::GRAY),
                DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
            )).with_child((text("Click or Tab here to write notes.", 16.0, theme::PAPER), TextPart::Notes));
            notes.spawn(text("Ctrl+A selects all · arrows edit · Tab leaves the field", 12.0, theme::GRAY));
            notes.spawn((text("", 13.0, theme::GRAY), TextPart::ReferenceSummary));
            button(notes, "Open saved references", OrganizerAction::OpenReferences);
        });
}

fn visible(
    action: OrganizerAction,
    client: &OrganizerClient,
    session: &ObserverSession,
    ui: &ObserverUiState,
    view: PrimaryView,
) -> bool {
    if !session.organizer_enabled || ui.splash_visible || ui.menu_open || ui.comparison_open {
        return false;
    }
    if matches!(action, OrganizerAction::Open) {
        return client.inspector == OrganizerInspector::Closed;
    }
    if matches!(action, OrganizerAction::OpenReferences) {
        return view == PrimaryView::Organizer && client.inspector == OrganizerInspector::Notes;
    }
    if matches!(
        action,
        OrganizerAction::Refresh
            | OrganizerAction::Choose(
                OrganizerChoice::PauseStanding | OrganizerChoice::ResumeStanding
            )
    ) {
        return view == PrimaryView::Organizer && client.inspector == OrganizerInspector::Direction;
    }
    if matches!(action, OrganizerAction::ArchiveWorkplace) {
        return view == PrimaryView::Organizer || client.inspector != OrganizerInspector::Closed;
    }
    if matches!(
        action,
        OrganizerAction::PreviousEvidence
            | OrganizerAction::NextEvidence
            | OrganizerAction::KeepEvidence
            | OrganizerAction::RemoveReference
    ) {
        return view == PrimaryView::Organizer && client.inspector == OrganizerInspector::Evidence;
    }
    if matches!(
        action,
        OrganizerAction::CloseInspector | OrganizerAction::ArchiveOrganization
    ) {
        return client.inspector != OrganizerInspector::Closed;
    }
    view == PrimaryView::Organizer && client.inspector == OrganizerInspector::Closed
}

fn enabled(action: OrganizerAction, client: &OrganizerClient, session: &ObserverSession) -> bool {
    match action {
        OrganizerAction::Choose(_) | OrganizerAction::Review => client.available(session),
        OrganizerAction::Advance => {
            crate::observer_controls::availability(ObserverCommand::Step, session)
                == crate::observer_controls::ControlAvailability::Enabled
        }
        OrganizerAction::Confirm => {
            client.available(session)
                && client.review_context.as_ref() == Some(&session.context())
                && client.preview.as_ref().is_some_and(|preview| {
                    preview.refusal.is_none() && preview.current_period == session.durable_tick
                })
                && client.reviewed_command.is_some()
        }
        OrganizerAction::Inspect(_) | OrganizerAction::OpenReferences => client.view.is_some(),
        OrganizerAction::PreviousEvidence => client
            .evidence_neighbor(false, session.viewed_tick)
            .is_some(),
        OrganizerAction::NextEvidence => client
            .evidence_neighbor(true, session.viewed_tick)
            .is_some(),
        OrganizerAction::KeepEvidence => client.can_keep_evidence(session).is_ok(),
        OrganizerAction::RemoveReference => client.can_remove_reference(session).is_ok(),
        OrganizerAction::Refresh => {
            client.pending.is_none() && !session.advance_pending() && !session.lifecycle_pending()
        }
        OrganizerAction::ArchiveWorkplace | OrganizerAction::ArchiveOrganization => {
            client.view.is_some()
                && matches!(
                    session.phase,
                    crate::observer::SessionPhase::Ready | crate::observer::SessionPhase::Complete
                )
        }
        OrganizerAction::Open | OrganizerAction::CloseInspector => true,
    }
}

#[derive(SystemParam)]
struct Scope<'w> {
    client: Res<'w, OrganizerClient>,
    session: Res<'w, ObserverSession>,
    ui: Res<'w, ObserverUiState>,
    view: Res<'w, PrimaryView>,
}

fn pointer_buttons(
    scope: Scope,
    buttons: Query<(&ActionButton, &Interaction), Changed<Interaction>>,
    mut actions: MessageWriter<OrganizerAction>,
) {
    for (button, interaction) in &buttons {
        if *interaction == Interaction::Pressed
            && visible(
                button.0,
                &scope.client,
                &scope.session,
                &scope.ui,
                *scope.view,
            )
        {
            actions.write(button.0);
        }
    }
}

fn requested(event: On<OrganizerActionRequested>, mut actions: MessageWriter<OrganizerAction>) {
    actions.write(event.0);
}

fn keyboard_button(
    event: On<ObserverKeyboardActivate>,
    scope: Scope,
    buttons: Query<(&ActionButton, &ObserverFocusTarget)>,
    mut actions: MessageWriter<OrganizerAction>,
) {
    if let Ok((button, target)) = buttons.get(event.entity) {
        if event.context == target.context
            && visible(
                button.0,
                &scope.client,
                &scope.session,
                &scope.ui,
                *scope.view,
            )
        {
            actions.write(button.0);
        }
    }
}

type FocusTargets<'w, 's> = Query<
    'w,
    's,
    (
        &'static mut ObserverFocusTarget,
        Option<&'static ActionButton>,
        Option<&'static TextPart>,
        Option<&'static NotesField>,
    ),
>;

fn sync_targets(scope: Scope, mut targets: FocusTargets) {
    for (mut target, button, text, notes) in &mut targets {
        if button.is_none() && text.is_none() && notes.is_none() {
            continue;
        }
        let mut next = target.clone();
        next.context = Some(scope.session.context());
        next.available = if let Some(button) = button {
            visible(
                button.0,
                &scope.client,
                &scope.session,
                &scope.ui,
                *scope.view,
            ) && enabled(button.0, &scope.client, &scope.session)
        } else {
            let inspector = matches!(text, Some(TextPart::InspectorBody));
            scope.session.organizer_enabled
                && !scope.ui.menu_open
                && !scope.ui.splash_visible
                && !scope.ui.comparison_open
                && if notes.is_some() {
                    *scope.view == PrimaryView::Organizer
                        && scope.client.inspector == OrganizerInspector::Notes
                } else if inspector {
                    !matches!(
                        scope.client.inspector,
                        OrganizerInspector::Closed | OrganizerInspector::Notes
                    )
                } else {
                    *scope.view == PrimaryView::Organizer
                        && scope.client.inspector == OrganizerInspector::Closed
                }
        };
        target.set_if_neq(next);
    }
}

#[derive(SystemParam)]
struct ActionState<'w> {
    client: ResMut<'w, OrganizerClient>,
    session: ResMut<'w, ObserverSession>,
    ui: ResMut<'w, ObserverUiState>,
    view: ResMut<'w, PrimaryView>,
    focus: ResMut<'w, InputFocus>,
    atlas: Res<'w, crate::atlas::CountyAtlas>,
    selected: ResMut<'w, crate::map::SelectedCounty>,
    time: Res<'w, Time>,
}

fn actions(
    mut events: MessageReader<OrganizerAction>,
    mut state: ActionState,
    mut commands: Commands,
    mut observer_commands: MessageWriter<ObserverCommand>,
) {
    for action in events.read().copied() {
        if !visible(
            action,
            &state.client,
            &state.session,
            &state.ui,
            *state.view,
        ) {
            continue;
        }
        if !enabled(action, &state.client, &state.session) {
            state.client.message =
                unavailable_message(action, &state.client, &state.session).into();
            continue;
        }
        let ActionState {
            client,
            session,
            ui,
            view,
            focus,
            atlas,
            selected,
            time,
        } = &mut state;
        match action {
            OrganizerAction::Open => {
                **view = PrimaryView::Organizer;
                ui.archive_open = false;
                ui.history_open = false;
                if let Some(entity) = client.return_focus.take() {
                    focus.set(entity);
                }
            }
            OrganizerAction::Choose(choice) => {
                choose_approach(client, focus, time.elapsed_secs_f64(), choice);
            }
            OrganizerAction::Review => review_approach(client, session),
            OrganizerAction::Confirm => confirm_approach(client, session),
            OrganizerAction::Advance => {
                observer_commands.write(ObserverCommand::Step);
            }
            OrganizerAction::Refresh => {
                client.status_due = true;
            }
            OrganizerAction::Inspect(inspector) => {
                client.return_focus = focus.get();
                client.inspector = inspector;
                if inspector == OrganizerInspector::Evidence {
                    client.open_evidence_reports(session.viewed_tick);
                }
            }
            OrganizerAction::OpenReferences => {
                if client.inspector == OrganizerInspector::Closed {
                    client.return_focus = focus.get();
                }
                client.inspector = OrganizerInspector::Evidence;
                client.open_saved_references();
            }
            OrganizerAction::PreviousEvidence
            | OrganizerAction::NextEvidence
            | OrganizerAction::KeepEvidence
            | OrganizerAction::RemoveReference => {
                change_evidence(action, client, session, time.elapsed_secs_f64());
            }
            OrganizerAction::ArchiveWorkplace | OrganizerAction::ArchiveOrganization => {
                if client.inspector == OrganizerInspector::Closed {
                    client.return_focus = focus.get();
                }
                selected.0 = atlas.index_of_fips("26163");
                commands.trigger(OrganizerArchiveRequested {
                    organization: matches!(action, OrganizerAction::ArchiveOrganization),
                });
                client.inspector = OrganizerInspector::Closed;
                **view = PrimaryView::Map;
                ui.archive_open = true;
                ui.history_open = false;
            }
            OrganizerAction::CloseInspector => {
                client.inspector = OrganizerInspector::Closed;
                if let Some(entity) = client.return_focus.take() {
                    focus.set(entity);
                }
            }
        }
    }
}

fn choose_approach(
    client: &mut OrganizerClient,
    focus: &mut InputFocus,
    now: f64,
    choice: OrganizerChoice,
) {
    if let Some(draft) = &mut client.draft {
        draft.choice = choice;
    }
    client.clear_review();
    client.dirty(now);
    client.message.clear();
    if client.inspector == OrganizerInspector::Direction {
        client.inspector = OrganizerInspector::Closed;
        if let Some(entity) = client.return_focus.take() {
            focus.set(entity);
        }
    }
}

fn review_approach(client: &mut OrganizerClient, session: &mut ObserverSession) {
    if let Some(command) = client.make_command(session, client.choice()) {
        client.queue(session, RequestKind::Preview, Some(command));
        client.message =
            "Checking the next-period commitment against current authority and time…".into();
    }
}

fn confirm_approach(client: &mut OrganizerClient, session: &mut ObserverSession) {
    if let Some(command) = client.reviewed_command.clone() {
        client.save_draft();
        client.queue(session, RequestKind::Submit, Some(command));
        client.message = "Submitting the reviewed ruling. Awaiting durable acceptance…".into();
    }
}

fn change_evidence(
    action: OrganizerAction,
    client: &mut OrganizerClient,
    session: &ObserverSession,
    now: f64,
) {
    match action {
        OrganizerAction::PreviousEvidence | OrganizerAction::NextEvidence => {
            client.move_evidence(
                matches!(action, OrganizerAction::NextEvidence),
                session.viewed_tick,
                now,
            );
        }
        OrganizerAction::KeepEvidence => {
            client.message = client.keep_evidence(session, now).map_or_else(str::to_owned, |()| "Report reference added to the personal draft. This does not submit or change a ruling.".into());
        }
        OrganizerAction::RemoveReference => {
            client.message = client.remove_reference(session, now).map_or_else(str::to_owned, |()| "Reference removed from the personal draft. The earned report remains available.".into());
        }
        _ => {}
    }
}

fn unavailable_message(
    action: OrganizerAction,
    client: &OrganizerClient,
    session: &ObserverSession,
) -> &'static str {
    match action {
        OrganizerAction::Advance => {
            if let crate::observer_controls::ControlAvailability::Disabled(reason) =
                crate::observer_controls::availability(ObserverCommand::Step, session)
            {
                return reason;
            }
        }
        OrganizerAction::KeepEvidence => {
            return client
                .can_keep_evidence(session)
                .err()
                .unwrap_or("This report cannot be retained.")
        }
        OrganizerAction::RemoveReference => {
            return client
                .can_remove_reference(session)
                .err()
                .unwrap_or("No saved reference is selected.")
        }
        OrganizerAction::PreviousEvidence | OrganizerAction::NextEvidence => {
            return "No other report is available in that direction."
        }
        _ => {}
    }
    if session.viewed_tick != session.durable_tick {
        "Return Live before changing the organization's commitments."
    } else if session.phase == crate::observer::SessionPhase::Complete {
        "This campaign is complete. Its reports and practice receipts remain available."
    } else if client
        .pending
        .as_ref()
        .is_some_and(|pending| pending.kind == RequestKind::Submit)
    {
        "Waiting for durable acceptance of this ruling. Refresh its status after the response."
    } else if client.commitment.is_some() {
        "A ruling is already accepted for this period. Advance or inspect its status."
    } else {
        "Wait for the committed situation or review the selected approach."
    }
}

fn open_evidence(
    _event: On<OrganizerEvidenceRequested>,
    mut client: ResMut<OrganizerClient>,
    mut view: ResMut<PrimaryView>,
    focus: Res<InputFocus>,
    session: Res<ObserverSession>,
    mut ui: ResMut<ObserverUiState>,
) {
    if session.organizer_enabled {
        ui.archive_open = false;
        ui.history_open = false;
        ui.disclosure = None;
        client.return_focus = focus.get();
        client.inspector = OrganizerInspector::Evidence;
        client.open_evidence_reports(session.viewed_tick);
        *view = PrimaryView::Organizer;
    }
}

fn escape(
    keys: Res<ButtonInput<KeyCode>>,
    client: Res<OrganizerClient>,
    ui: Res<ObserverUiState>,
    view: Res<PrimaryView>,
    mut claimed: ResMut<ObserverKeyboardClaim>,
    mut actions: MessageWriter<OrganizerAction>,
) {
    if !ui.menu_open
        && !ui.splash_visible
        && !ui.comparison_open
        && *view == PrimaryView::Organizer
        && client.inspector != OrganizerInspector::Closed
        && keys.just_pressed(KeyCode::Escape)
    {
        claimed.claim(KeyCode::Escape);
        actions.write(OrganizerAction::CloseInspector);
    }
}

fn notes_input(
    mut event: On<FocusedInput<KeyboardInput>>,
    fields: Query<&ObserverFocusTarget, With<NotesField>>,
    focus: Res<InputFocus>,
    keys: Res<ButtonInput<KeyCode>>,
    mut client: ResMut<OrganizerClient>,
    session: Res<ObserverSession>,
    time: Res<Time>,
) {
    let Some(entity) = focus.get() else {
        return;
    };
    let Ok(target) = fields.get(entity) else {
        return;
    };
    if !target.available
        || target.context != Some(session.context())
        || event.original_event_target() != entity
        || event.input.state != ButtonState::Pressed
        || event.input.key_code == KeyCode::Tab
    {
        return;
    }
    event.propagate(false);
    let Some(draft) = &mut client.draft else {
        return;
    };
    let before = draft.notes.text.clone();
    let control = keys.pressed(KeyCode::ControlLeft)
        || keys.pressed(KeyCode::ControlRight)
        || keys.pressed(KeyCode::SuperLeft)
        || keys.pressed(KeyCode::SuperRight);
    match event.input.key_code {
        KeyCode::KeyA if control => draft.notes.selected_all = true,
        KeyCode::ArrowLeft => draft.notes.left(),
        KeyCode::ArrowRight => draft.notes.right(),
        KeyCode::Home => draft.notes.home(),
        KeyCode::End => draft.notes.end(),
        KeyCode::Backspace => draft.notes.backspace(),
        KeyCode::Delete => draft.notes.delete(),
        KeyCode::Enter => draft.notes.insert("\n"),
        _ if !control => {
            if let Some(text) = &event.input.text {
                draft.notes.insert(text);
            } else if let Key::Character(text) = &event.input.logical_key {
                draft.notes.insert(text);
            }
        }
        _ => {}
    }
    if draft.notes.text != before {
        client.dirty(time.elapsed_secs_f64());
    }
}

type OrganizerRoots<'w, 's> = Query<
    'w,
    's,
    &'static mut Node,
    (
        With<OrganizerRoot>,
        Without<OrganizerInspectorRoot>,
        Without<ActionButton>,
        Without<InspectorShield>,
    ),
>;
type InspectorPanels<'w, 's> = Query<
    'w,
    's,
    &'static mut Node,
    (
        With<OrganizerInspectorRoot>,
        Without<OrganizerRoot>,
        Without<ActionButton>,
        Without<InspectorShield>,
    ),
>;
type PaintedButtons<'w, 's> = Query<
    'w,
    's,
    (
        &'static ActionButton,
        &'static Interaction,
        &'static mut Node,
        &'static mut BackgroundColor,
        &'static mut BorderColor,
    ),
    (
        Without<OrganizerRoot>,
        Without<OrganizerInspectorRoot>,
        Without<InspectorShield>,
    ),
>;
type InspectorShields<'w, 's> = Query<
    'w,
    's,
    &'static mut Node,
    (
        With<InspectorShield>,
        Without<OrganizerRoot>,
        Without<OrganizerInspectorRoot>,
        Without<ActionButton>,
    ),
>;
type DetailPanels<'w, 's> = Query<
    'w,
    's,
    (&'static DetailControls, &'static mut Node),
    (
        Without<OrganizerRoot>,
        Without<OrganizerInspectorRoot>,
        Without<ActionButton>,
        Without<InspectorShield>,
    ),
>;

#[derive(SystemParam)]
struct Paint<'w, 's> {
    texts: Query<'w, 's, (&'static TextPart, &'static mut Text)>,
    roots: OrganizerRoots<'w, 's>,
    inspectors: InspectorPanels<'w, 's>,
    buttons: PaintedButtons<'w, 's>,
    shields: InspectorShields<'w, 's>,
    notes: Query<'w, 's, Entity, With<NotesField>>,
    detail_controls: DetailPanels<'w, 's>,
}

fn paint(scope: Scope, focus: Res<InputFocus>, mut paint: Paint) {
    let primary = *scope.view == PrimaryView::Organizer
        && scope.session.organizer_enabled
        && !scope.ui.menu_open
        && !scope.ui.splash_visible
        && !scope.ui.comparison_open;
    paint_layout(&scope, primary, &mut paint);
    if scope.client.is_changed()
        || scope.session.is_changed()
        || scope.view.is_changed()
        || focus.is_changed()
    {
        paint_text(&scope, &focus, &mut paint);
    }
    paint_buttons(&scope, &mut paint.buttons);
}

fn paint_layout(scope: &Scope, primary: bool, paint: &mut Paint) {
    for (details, mut node) in &mut paint.detail_controls {
        let display = if primary && scope.client.inspector == details.0 {
            Display::Flex
        } else {
            Display::None
        };
        if node.display != display {
            node.display = display;
        }
    }
    for mut node in &mut paint.roots {
        let bottom = if scope.ui.history_open {
            px(260)
        } else {
            px(60)
        };
        if node.bottom != bottom {
            node.bottom = bottom;
        }
        let next = if primary {
            Display::Flex
        } else {
            Display::None
        };
        if node.display != next {
            node.display = next;
        }
    }
    for mut node in &mut paint.inspectors {
        let next = if primary && scope.client.inspector != OrganizerInspector::Closed {
            Display::Flex
        } else {
            Display::None
        };
        if node.display != next {
            node.display = next;
        }
    }
    for mut node in &mut paint.shields {
        let next = if primary && scope.client.inspector != OrganizerInspector::Closed {
            Display::Flex
        } else {
            Display::None
        };
        if node.display != next {
            node.display = next;
        }
    }
}

fn paint_text(scope: &Scope, focus: &InputFocus, paint: &mut Paint) {
    let historical = scope.session.viewed_tick != scope.session.durable_tick;
    let complete = scope.session.phase == crate::observer::SessionPhase::Complete;
    let (inspector_title, inspector_body) =
        presentation::inspector(&scope.client, scope.session.viewed_tick);
    let note_focused = focus
        .get()
        .is_some_and(|entity| paint.notes.contains(entity));
    for (part, mut text) in &mut paint.texts {
        let value = match part {
            TextPart::Title => scope.client.view.as_ref().map_or_else(|| "Wayne Organizing Collective".into(), |view| view.organization_label.clone()),
            TextPart::Situation => scope.client.view.as_ref().map_or_else(|| "Awaiting the committed organizer situation…".into(), |view| presentation::situation(view, scope.session.viewed_tick)),
            TextPart::Means => scope.client.view.as_ref().map_or_else(String::new, |view| {
                let horizon = scope.session.horizon_tick.map_or_else(|| "—".into(), |value| value.to_string());
                if historical { format!("HISTORY · period {} / {horizon}\nCurrent period {} · {} organizer-hours", scope.session.viewed_tick, view.period, view.available_hours) }
                else { format!("PERIOD {} / {horizon} · 4 weeks\n{} organizer-hours available", view.period, view.available_hours) }
            }),
            TextPart::Context => scope.client.view.as_ref().map_or_else(String::new, presentation::context),
            TextPart::Aftermath => scope.client.view.as_ref().map_or_else(String::new, |view| presentation::aftermath(view, scope.session.viewed_tick)),
            TextPart::ChoiceHeading => if complete { "CAMPAIGN COMPLETE".into() } else if historical { "CURRENT CHOICES · RETURN LIVE TO DECIDE".into() } else { "CHOOSE OUR WORK FOR THE NEXT PERIOD".into() },
            TextPart::Approach(choice) => if complete { "No further period remains. Inspect our practice history and retained reports.".into() } else { scope.client.view.as_ref().map_or_else(String::new, |view| presentation::approach(view, *choice)) },
            TextPart::ChoiceMarker(choice) => {
                if complete { "CLOSED".into() }
                else if scope.client.commitment.as_ref().is_some_and(|value| value.command.choice == *choice) { "ACCEPTED".into() }
                else if scope.client.choice() == *choice { "SELECTED DRAFT".into() }
                else { "SELECT".into() }
            },
            TextPart::Review => presentation::review(&scope.client, historical, complete, scope.session.phase == crate::observer::SessionPhase::Advancing),
            TextPart::ReferenceSummary => format!("{} report reference(s) in this personal draft. References help you review evidence; they never execute a practice.", scope.client.draft.as_ref().map_or(0, |draft| draft.references.len())),
            TextPart::DraftStatus => if !scope.client.draft_writable { "Draft saving unavailable · original file retained".into() } else if scope.client.draft_dirty { "Draft changes awaiting save".into() } else { "Personal draft saved".into() },
            TextPart::Message => scope.client.message.clone(),
            TextPart::Notes => scope.client.draft.as_ref().map_or_else(String::new, |draft| {
                if draft.notes.text.is_empty() && !note_focused { "Click or Tab here to write personal notes.".into() }
                else { draft.notes.display(note_focused) }
            }),
            TextPart::InspectorTitle => inspector_title.clone(), TextPart::InspectorBody => inspector_body.clone(),
        };
        if text.0 != value {
            text.0 = value;
        }
    }
}

fn paint_buttons(scope: &Scope, buttons: &mut PaintedButtons) {
    for (button, interaction, mut node, mut background, mut border) in &mut *buttons {
        if matches!(button.0, OrganizerAction::Open) {
            let next = if scope.session.organizer_enabled {
                Display::Flex
            } else {
                Display::None
            };
            if node.display != next {
                node.display = next;
            }
        }
        let available = visible(
            button.0,
            &scope.client,
            &scope.session,
            &scope.ui,
            *scope.view,
        ) && enabled(button.0, &scope.client, &scope.session);
        let selected =
            matches!(button.0, OrganizerAction::Choose(choice) if choice == scope.client.choice());
        let next_action = available
            && match button.0 {
                OrganizerAction::Review => scope.client.preview.is_none(),
                OrganizerAction::Confirm => scope.client.preview.is_some(),
                OrganizerAction::Advance => scope.client.commitment.is_some(),
                _ => false,
            };
        let color = if !available {
            theme::INK
        } else if *interaction == Interaction::Pressed {
            theme::RED.with_alpha(0.4)
        } else if *interaction == Interaction::Hovered || selected || next_action {
            theme::YELLOW.with_alpha(0.2)
        } else {
            theme::PANEL
        };
        background.set_if_neq(BackgroundColor(color));
        border.set_if_neq(BorderColor::all(if selected || next_action {
            theme::YELLOW
        } else if available {
            theme::GRAY
        } else {
            theme::GRAY.with_alpha(0.3)
        }));
    }
}

pub(super) fn install(app: &mut App) {
    app.add_message::<OrganizerAction>()
        .add_systems(Startup, spawn)
        .add_systems(
            PreUpdate,
            sync_targets.in_set(ObserverFocusSystems::Eligibility),
        )
        .add_systems(
            Update,
            (pointer_buttons, escape, actions)
                .chain()
                .in_set(ObserverSet::Input),
        )
        .add_systems(Update, paint.in_set(ObserverSet::Paint))
        .add_systems(
            PostUpdate,
            paint_scroll_hints.after(bevy::ui::UiSystems::Layout),
        )
        .add_observer(requested)
        .add_observer(keyboard_button)
        .add_observer(notes_input)
        .add_observer(open_evidence);
}

#[cfg(test)]
mod tests {
    use super::super::{draft::OrganizerDraft, editor::NoteEditor};
    use super::*;
    use crate::atlas::CountyAtlas;
    use crate::map::SelectedCounty;
    use crate::observer_focus::ObserverKeyboardClaim;
    use crate::observer_ui::ObserverCommand;
    use babylon_persistence::identity::CampaignId;
    use babylon_persistence::runtime_session::{OrganizerStandingWork, OrganizerView};

    #[derive(Resource, Default)]
    struct ArchiveRequests(Vec<bool>);

    #[test]
    fn scroll_cues_follow_resolved_geometry_without_layout_change_notifications() {
        for scale in [1.0, 1.25] {
            let mut app = App::new();
            app.add_systems(Update, paint_scroll_hints);
            let reading = app
                .world_mut()
                .spawn(ComputedNode {
                    size: Vec2::new(400.0, 100.0) * scale,
                    content_size: Vec2::new(400.0, 300.0) * scale,
                    inverse_scale_factor: scale.recip(),
                    ..default()
                })
                .id();
            let hint = app
                .world_mut()
                .spawn((ScrollHint(reading), Text::default()))
                .id();
            app.update();
            assert_eq!(
                app.world().get::<Text>(hint).unwrap().0,
                "More below · scroll this panel"
            );
            // Bevy resolves physical scroll offsets without marking this
            // component changed. The hint must still update at larger UI scales.
            app.world_mut()
                .get_mut::<ComputedNode>(reading)
                .unwrap()
                .bypass_change_detection()
                .scroll_position
                .y = 190.0 * scale;
            app.update();
            assert_eq!(
                app.world().get::<Text>(hint).unwrap().0,
                "More above and below · scroll this panel"
            );
            app.world_mut()
                .get_mut::<ComputedNode>(reading)
                .unwrap()
                .bypass_change_detection()
                .scroll_position
                .y = 200.0 * scale;
            app.update();
            assert_eq!(
                app.world().get::<Text>(hint).unwrap().0,
                "More above · scroll this panel"
            );
            app.world_mut()
                .get_mut::<ComputedNode>(reading)
                .unwrap()
                .bypass_change_detection()
                .content_size = Vec2::new(400.0, 100.0) * scale;
            app.update();
            assert!(app.world().get::<Text>(hint).unwrap().0.is_empty());
        }
    }

    fn organizer_navigation() -> (App, Entity, OrganizerDraft) {
        let mut session = ObserverSession::new(CampaignId::from_uuid(uuid::Uuid::from_u128(927)));
        session.phase = crate::observer::SessionPhase::Ready;
        session.organizer_enabled = true;
        let draft = OrganizerDraft {
            workplace_id: 91,
            choice: OrganizerChoice::Reinforce,
            notes: NoteEditor::from_text("Keep this draft while reading evidence.".into()).unwrap(),
            references: Vec::new(),
            selected_reference: None,
        };
        let client = OrganizerClient {
            draft: Some(draft.clone()),
            view: Some(OrganizerView {
                period: 0,
                actor_id: 90,
                authority_id: [1; 16],
                organization_label: "Fixture collective".into(),
                workplace_id: 91,
                workplace_label: "Fixture workplace".into(),
                workplace_partner_id: 92,
                workplace_partner_label: "Fixture workplace contacts".into(),
                neighborhood_partner_id: 93,
                neighborhood_partner_label: "Fixture neighborhood contacts".into(),
                available_hours: 16,
                inquiry_hours: 12,
                contact_hours: 8,
                content_digest: [2; 32],
                resource_digest: [3; 32],
                standing: OrganizerStandingWork {
                    partner_actor_id: 93,
                    authorized: true,
                    paused_reason: None,
                },
                agreements: Vec::new(),
                observations: Vec::new(),
                receipts: Vec::new(),
                positions: Vec::new(),
            }),
            ..default()
        };
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .configure_sets(
                Update,
                (
                    ObserverSet::Input,
                    ObserverSet::Receive,
                    ObserverSet::Install,
                    ObserverSet::Paint,
                )
                    .chain(),
            )
            .insert_resource(session)
            .insert_resource(client)
            .insert_resource(PrimaryView::Organizer)
            .insert_resource(ObserverUiState {
                menu_open: false,
                splash_visible: false,
                ..default()
            })
            .insert_resource(
                CountyAtlas::parse(include_bytes!(concat!(
                    env!("CARGO_MANIFEST_DIR"),
                    "/../../../assets/map/county_atlas.bin"
                )))
                .unwrap(),
            )
            .insert_resource(SelectedCounty(Some(0)))
            .init_resource::<InputFocus>()
            .init_resource::<ButtonInput<KeyCode>>()
            .init_resource::<ObserverKeyboardClaim>()
            .init_resource::<ArchiveRequests>()
            .add_message::<ObserverCommand>()
            .add_systems(
                Update,
                crate::observer_ui::keyboard.before(ObserverSet::Input),
            )
            .add_observer(
                |event: On<OrganizerArchiveRequested>, mut requests: ResMut<ArchiveRequests>| {
                    requests.0.push(event.organization);
                },
            );
        install(&mut app);
        let focus = app.world_mut().spawn_empty().id();
        app.world_mut().resource_mut::<InputFocus>().set(focus);
        app.update();
        (app, focus, draft)
    }

    fn return_to_organizer(app: &mut App, focus: Entity, draft: &OrganizerDraft) {
        let archive_focus = app.world_mut().spawn_empty().id();
        app.world_mut()
            .resource_mut::<InputFocus>()
            .set(archive_focus);
        app.world_mut()
            .resource_mut::<ButtonInput<KeyCode>>()
            .reset_all();
        app.world_mut().write_message(OrganizerAction::Open);
        app.update();
        assert_eq!(
            *app.world().resource::<PrimaryView>(),
            PrimaryView::Organizer
        );
        assert!(!app.world().resource::<ObserverUiState>().archive_open);
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(focus));
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.draft.as_ref(), Some(draft));
        assert!(
            client.outbox.is_none(),
            "inspecting evidence cannot submit the draft"
        );
    }

    fn reviewed_period_three() -> (App, OrganizerDraft) {
        let (mut app, _, draft) = organizer_navigation();
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.connected_fixture();
            session.ready(3, None);
            let context = session.context();
            assert!(session.installed(&context));
        }
        app.world_mut()
            .resource_mut::<OrganizerClient>()
            .view
            .as_mut()
            .unwrap()
            .period = 3;
        app.add_systems(Update, super::super::transport.before(ObserverSet::Paint));
        review_selected(&mut app);
        assert!(confirmation_enabled(&app));
        (app, draft)
    }

    fn review_selected(app: &mut App) {
        app.world_mut()
            .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                let mut session = world.resource_mut::<ObserverSession>();
                let command = client.make_command(&session, client.choice()).unwrap();
                client.queue(&mut session, RequestKind::Preview, Some(command.clone()));
                let request = client.pending.as_ref().unwrap().id;
                let _ = client.outbox.take();
                client
                    .previewed(request, preview_for(&command), &mut session)
                    .unwrap();
            });
    }

    fn preview_for(command: &super::super::OrganizerCommand) -> super::super::OrganizerPreview {
        super::super::OrganizerPreview {
            choice: command.choice,
            current_period: command.expected_period,
            resolves_period: command.expected_period + 1,
            available_hours: 16,
            required_hours: 8,
            replaces_standing_work: true,
            refusal: None,
            observations: Vec::new(),
        }
    }

    fn confirmation_enabled(app: &App) -> bool {
        enabled(
            OrganizerAction::Confirm,
            app.world().resource::<OrganizerClient>(),
            app.world().resource::<ObserverSession>(),
        )
    }

    fn inspect_period(app: &mut App, period: u64) {
        let mut session = app.world_mut().resource_mut::<ObserverSession>();
        session.inspect_tick(period);
        let context = session.context();
        assert!(session.installed(&context));
    }

    fn press_named(app: &mut App, label: &str) {
        let world = app.world_mut();
        let action = world
            .query::<(&ActionButton, &Children)>()
            .iter(world)
            .find_map(|(action, children)| {
                children[..]
                    .iter()
                    .any(|child| {
                        world
                            .get::<Text>(*child)
                            .is_some_and(|text| text.0 == label)
                    })
                    .then_some(action.0)
            })
            .unwrap_or_else(|| panic!("native button missing: {label}"));
        let _ = world.write_message(action);
        app.update();
    }

    fn painted_text(app: &mut App, inspector: bool) -> String {
        let world = app.world_mut();
        world
            .query::<(&TextPart, &Text)>()
            .iter(world)
            .find_map(|(part, text)| {
                ((inspector && matches!(part, TextPart::InspectorBody))
                    || (!inspector && matches!(part, TextPart::Review)))
                .then(|| text.0.clone())
            })
            .unwrap()
    }

    fn reference_fixture() -> (App, OrganizerDraft) {
        use babylon_persistence::runtime_session::{OrganizerObservation, OrganizerReport};
        let (mut app, _, draft) = organizer_navigation();
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.connected_fixture();
            session.ready(3, None);
            let context = session.context();
            assert!(session.installed(&context));
        }
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.campaign = Some(uuid::Uuid::from_u128(927));
            client.draft_writable = true;
            let view = client.view.as_mut().unwrap();
            view.period = 3;
            for period in [2, 3] {
                view.observations.push(OrganizerObservation {
                    observation_id: [u8::try_from(period).unwrap(); 32],
                    actor_id: view.actor_id,
                    subject_id: view.workplace_id,
                    source_actor_id: view.workplace_partner_id,
                    observed_period: period - 1,
                    acquired_period: period,
                    receipt_id: Some([7; 32]),
                    report: OrganizerReport::Work {
                        performed_labor_hours: 12,
                        output_kg: 777,
                        previous_labor_hours: None,
                        previous_output_kg: None,
                    },
                });
            }
        }
        press_named(&mut app, "Workplace evidence");
        (app, draft)
    }

    fn panel_has_visible_text(app: &mut App, inspector: bool, expected: &str) -> bool {
        let world = app.world_mut();
        world
            .query::<(Entity, &Text)>()
            .iter(world)
            .any(|(entity, text)| {
                if !text.0.contains(expected) {
                    return false;
                }
                let mut ancestor = Some(entity);
                while let Some(entity) = ancestor {
                    if world
                        .get::<Node>(entity)
                        .is_some_and(|node| node.display == Display::None)
                    {
                        return false;
                    }
                    if (inspector && world.get::<OrganizerInspectorRoot>(entity).is_some())
                        || (!inspector && world.get::<OrganizerRoot>(entity).is_some())
                    {
                        return true;
                    }
                    ancestor = world.get::<ChildOf>(entity).map(ChildOf::parent);
                }
                false
            })
    }

    #[test]
    fn unwritable_draft_status_survives_selection_and_inspection() {
        let (mut app, _) = reference_fixture();
        app.world_mut()
            .resource_mut::<OrganizerClient>()
            .draft_writable = false;
        press_named(&mut app, "Return to decision [Esc]");
        press_named(&mut app, "Reinforce workplace contact");
        assert!(panel_has_visible_text(
            &mut app,
            false,
            "saving unavailable"
        ));
        press_named(&mut app, "Direction / routine");
        assert!(panel_has_visible_text(&mut app, true, "saving unavailable"));
        assert!(!app.world().resource::<OrganizerClient>().draft_writable);
    }

    #[test]
    fn personal_notes_show_save_recovery_without_erasing_command_errors() {
        let (mut app, _, draft) = organizer_navigation();
        press_named(&mut app, "Personal notes");
        let failure = "Cannot save the personal draft; notes remain in this window.";
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.draft_dirty = true;
            client.draft_writable = true;
            client.draft_saved(Err(failure.into()));
        }
        app.update();
        assert!(panel_has_visible_text(&mut app, true, failure),
            "the Notes view must expose save failures, not a hidden sibling or covered decision footer");
        let client = app.world().resource::<OrganizerClient>();
        assert!(client.draft_dirty);
        assert_eq!(client.draft.as_ref(), Some(&draft));
        assert!(client.outbox.is_none());

        app.world_mut()
            .resource_mut::<OrganizerClient>()
            .draft_saved(Ok(()));
        app.update();
        assert!(
            !panel_has_visible_text(&mut app, true, failure),
            "a successful retry must remove the old save failure"
        );
        assert!(panel_has_visible_text(
            &mut app,
            true,
            "Personal draft saved"
        ));

        let command_error = "The campaign changed. Refresh and review this ruling again.";
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.draft_dirty = true;
            client.draft_saved(Err(failure.into()));
            client.message = command_error.into();
            client.draft_saved(Ok(()));
        }
        app.update();
        assert!(
            panel_has_visible_text(&mut app, true, command_error),
            "saving notes cannot dismiss an unrelated command error"
        );
        let client = app.world().resource::<OrganizerClient>();
        assert!(!client.draft_dirty);
        assert_eq!(client.draft.as_ref(), Some(&draft));
        assert!(client.outbox.is_none());
    }

    #[test]
    fn personal_notes_open_separately_without_replacing_the_decision_or_submitting_it() {
        let (mut app, focus, draft) = organizer_navigation();
        let notes = app
            .world_mut()
            .query_filtered::<Entity, With<NotesField>>()
            .single(app.world())
            .unwrap();
        app.update();
        assert!(
            !app.world()
                .get::<ObserverFocusTarget>(notes)
                .unwrap()
                .available,
            "notes must not capture decision-screen typing before they are opened"
        );
        press_named(&mut app, "Personal notes");
        app.update();
        assert!(
            app.world()
                .get::<ObserverFocusTarget>(notes)
                .unwrap()
                .available
        );
        assert_eq!(
            app.world().resource::<OrganizerClient>().draft.as_ref(),
            Some(&draft)
        );
        assert!(app.world().resource::<OrganizerClient>().outbox.is_none());
        press_named(&mut app, "Return to decision [Esc]");
        app.update();
        assert!(
            !app.world()
                .get::<ObserverFocusTarget>(notes)
                .unwrap()
                .available
        );
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(focus));
        assert_eq!(
            app.world().resource::<OrganizerClient>().draft.as_ref(),
            Some(&draft)
        );
    }

    #[test]
    fn escape_closes_only_inspector_before_shell_shortcuts() {
        use bevy::ecs::system::RunSystemOnce;

        let (mut app, focus, draft) = organizer_navigation();
        press_named(&mut app, "Personal notes");
        app.world_mut()
            .resource_mut::<ButtonInput<KeyCode>>()
            .press(KeyCode::Escape);
        app.update();
        // Exercise a shell consumer that runs after the inspector closes in this frame.
        app.world_mut()
            .run_system_once(crate::observer_ui::keyboard)
            .unwrap();
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.inspector, OrganizerInspector::Closed);
        assert_eq!(client.draft.as_ref(), Some(&draft));
        assert!(client.outbox.is_none());
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(focus));
        assert!(
            app.world()
                .resource::<Messages<ObserverCommand>>()
                .is_empty(),
            "the Escape that closes Notes cannot also open the campaign menu"
        );
    }

    #[test]
    fn decision_footer_advances_through_the_existing_transport_and_refuses_held_history() {
        let (mut app, _) = reviewed_period_three();
        press_named(&mut app, "Advance one period");
        let commands: Vec<_> = app
            .world_mut()
            .resource_mut::<Messages<ObserverCommand>>()
            .drain()
            .collect();
        assert_eq!(commands, [ObserverCommand::Step]);
        assert!(
            app.world().resource::<OrganizerClient>().outbox.is_none(),
            "Advance cannot submit the selected draft as a ruling"
        );
        inspect_period(&mut app, 2);
        press_named(&mut app, "Advance one period");
        assert!(app
            .world()
            .resource::<Messages<ObserverCommand>>()
            .is_empty());
        assert!(app
            .world()
            .resource::<OrganizerClient>()
            .message
            .contains("Return Live"));
    }

    #[test]
    fn draft_reference_controls_preserve_selection_history_and_nonexecuting_notes() {
        let (mut app, before) = reference_fixture();
        press_named(&mut app, "Keep report in draft");
        let saved = app
            .world()
            .resource::<OrganizerClient>()
            .draft
            .clone()
            .unwrap();
        assert_ne!(saved, before);
        assert_eq!(saved.choice, before.choice);
        assert_eq!(saved.notes, before.notes);
        assert!(painted_text(&mut app, true).contains("\nIN PERSONAL DRAFT\n\n"));
        assert!(app
            .world()
            .resource::<OrganizerClient>()
            .message
            .contains("reference added"));
        let world = app.world_mut();
        assert!(world
            .query::<&Text>()
            .iter(world)
            .any(|text| text.0.contains("changes awaiting save")));
        press_named(&mut app, "Return to decision [Esc]");
        inspect_period(&mut app, 2);
        press_named(&mut app, "Personal notes");
        press_named(&mut app, "Open saved references");
        let held = painted_text(&mut app, true);
        assert!(held.contains("unavailable in this inspected view"));
        assert!(!held.contains("777 kg"));
        assert_eq!(
            app.world().resource::<OrganizerClient>().draft.as_ref(),
            Some(&saved)
        );
        inspect_period(&mut app, 3);
        app.update();
        assert!(painted_text(&mut app, true).contains("777 kg"));
        press_named(&mut app, "Remove saved reference");
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.draft.as_ref(), Some(&before));
        assert!(client.pending.is_none());
        assert!(client.outbox.is_none());
        assert!(client.commitment.is_none());
    }

    #[test]
    fn draft_references_cannot_reopen_hidden_foreign_or_missing_observations() {
        for fault in 0..4 {
            let (mut app, _) = reference_fixture();
            press_named(&mut app, "Keep report in draft");
            press_named(&mut app, "Return to decision [Esc]");
            {
                let mut client = app.world_mut().resource_mut::<OrganizerClient>();
                let observations = &mut client.view.as_mut().unwrap().observations;
                let selected = observations.last_mut().unwrap();
                match fault {
                    0 => selected.acquired_period = 4,
                    1 => selected.actor_id = 999,
                    2 => selected.subject_id = 999,
                    _ => {
                        observations.pop();
                    }
                }
            }
            press_named(&mut app, "Personal notes");
            press_named(&mut app, "Open saved references");
            let text = painted_text(&mut app, true);
            assert!(text.contains("unavailable in this inspected view"));
            assert!(!text.contains("777 kg"));
            let retained = app.world().resource::<OrganizerClient>().draft.clone();
            press_named(&mut app, "Keep report in draft");
            assert_eq!(app.world().resource::<OrganizerClient>().draft, retained);
            assert!(app.world().resource::<OrganizerClient>().outbox.is_none());
            press_named(&mut app, "Remove saved reference");
        }
    }

    #[test]
    fn resolving_ruling_has_distinct_native_wording_without_credited_outcome() {
        let (mut app, _) = reviewed_period_three();
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.commitment = Some(super::super::OrganizerCommitment {
                command: client.reviewed_command.clone().unwrap(),
                resolves_period: 4,
                commitment_id: [4; 32],
            });
        }
        app.update();
        assert!(painted_text(&mut app, false).contains("ACCEPTED"));
        app.world_mut().resource_mut::<ObserverSession>().phase =
            crate::observer::SessionPhase::Advancing;
        app.update();
        let text = painted_text(&mut app, false);
        assert!(text.contains("RESOLVING · period 4"));
        assert!(!text.contains("Advance to receive"));
        assert!(text.contains("No outcome is credited"));
        assert!(app
            .world()
            .resource::<OrganizerClient>()
            .view
            .as_ref()
            .unwrap()
            .receipts
            .is_empty());
    }

    #[test]
    fn resolving_ruling_without_commitment_respects_paused_routine() {
        let (mut app, _) = reviewed_period_three();
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.commitment = None;
            let standing = &mut client.view.as_mut().unwrap().standing;
            standing.authorized = false;
            standing.paused_reason =
                Some(babylon_persistence::runtime_session::OrganizerPauseReason::Explicit);
        }
        app.world_mut().resource_mut::<ObserverSession>().phase =
            crate::observer::SessionPhase::Advancing;
        app.update();
        let text = painted_text(&mut app, false);
        assert!(text.contains("RESOLVING · period 4"));
        assert!(text.contains("No standing routine is authorized for this period."));
        assert!(!text.contains("The authorized standing practice is being resolved."));
        assert!(app
            .world()
            .resource::<OrganizerClient>()
            .commitment
            .is_none());
        assert!(app
            .world()
            .resource::<OrganizerClient>()
            .view
            .as_ref()
            .unwrap()
            .receipts
            .is_empty());
    }

    #[test]
    fn history_roundtrip_requires_new_review_and_preserves_draft_and_accepted_status() {
        let (mut app, draft) = reviewed_period_three();
        inspect_period(&mut app, 2);
        assert!(!confirmation_enabled(&app));
        inspect_period(&mut app, 3);
        assert!(app
            .world()
            .resource::<OrganizerClient>()
            .available(app.world().resource::<ObserverSession>()));
        assert!(
            !confirmation_enabled(&app),
            "returning live requires a fresh review"
        );
        app.update();
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.draft.as_ref(), Some(&draft));
        assert!(client.preview.is_none());
        assert!(client.reviewed_command.is_none());

        review_selected(&mut app);
        assert!(confirmation_enabled(&app));
        let accepted = app
            .world_mut()
            .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                let mut session = world.resource_mut::<ObserverSession>();
                let command = client.reviewed_command.clone().unwrap();
                client.queue(&mut session, RequestKind::Submit, Some(command.clone()));
                let request = client.pending.as_ref().unwrap().id;
                let _ = client.outbox.take();
                let accepted = super::super::OrganizerCommitment {
                    command,
                    resolves_period: 4,
                    commitment_id: [4; 32],
                };
                client
                    .accepted(request, accepted.clone(), &mut session)
                    .unwrap();
                accepted
            });
        inspect_period(&mut app, 2);
        app.update();
        inspect_period(&mut app, 3);
        app.update();
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.draft.as_ref(), Some(&draft));
        assert_eq!(client.commitment, Some(accepted));
        assert!(presentation::review(client, false, false, false)
            .contains("ACCEPTED · resolves period 4"));
        assert!(client.pending.is_none());
        assert!(client.outbox.is_none());
        assert!(!confirmation_enabled(&app));
    }

    #[test]
    fn preview_reply_from_before_history_cannot_restore_confirmation() {
        let (mut app, draft) = reviewed_period_three();
        app.world_mut()
            .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                let mut session = world.resource_mut::<ObserverSession>();
                let command = client.make_command(&session, client.choice()).unwrap();
                client.queue(&mut session, RequestKind::Preview, Some(command.clone()));
                let request = client.pending.as_ref().unwrap().id;
                let _ = client.outbox.take();
                session.inspect_tick(2);
                let context = session.context();
                assert!(session.installed(&context));
                session.return_live();
                let context = session.context();
                assert!(session.installed(&context));
                client
                    .previewed(request, preview_for(&command), &mut session)
                    .unwrap();
            });
        assert!(!confirmation_enabled(&app));
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.draft.as_ref(), Some(&draft));
        assert!(client.preview.is_none());
        assert!(client.pending.is_none());
        assert!(!app
            .world()
            .resource::<ObserverSession>()
            .organizer_control_pending());
    }

    #[test]
    fn organizer_archive_shortcut_opens_workplace_and_returns_to_unchanged_draft() {
        let (mut app, focus, draft) = organizer_navigation();
        app.world_mut()
            .resource_mut::<ButtonInput<KeyCode>>()
            .press(KeyCode::KeyI);
        app.update();
        assert_eq!(
            *app.world().resource::<PrimaryView>(),
            PrimaryView::Map,
            "the Archive must become the visible primary surface"
        );
        assert!(app.world().resource::<ObserverUiState>().archive_open);
        assert_eq!(
            app.world().resource::<ArchiveRequests>().0,
            [false],
            "the shortcut must request the lawful workplace dossier"
        );
        assert_eq!(
            app.world().resource::<SelectedCounty>().0,
            app.world().resource::<CountyAtlas>().index_of_fips("26163")
        );
        assert!(
            app.world()
                .resource::<Messages<ObserverCommand>>()
                .is_empty(),
            "the organizer shortcut cannot also toggle the generic Archive"
        );
        assert_eq!(
            app.world().resource::<OrganizerClient>().return_focus,
            Some(focus)
        );
        return_to_organizer(&mut app, focus, &draft);
    }

    fn focused_organizer(notes: bool) -> (App, Entity, Entity, OrganizerDraft) {
        use crate::observer_focus::ObserverFocusPlugin;
        use bevy::input::InputPlugin;
        use bevy::window::PrimaryWindow;

        let (mut app, _, draft) = organizer_navigation();
        app.add_plugins((InputPlugin, ObserverFocusPlugin));
        // Use the shell's actual campaign and modal admission, including Notes.
        crate::observer_ui::install_shell_focus_policy(&mut app);
        let window = app
            .world_mut()
            .spawn((Window::default(), PrimaryWindow))
            .id();
        if notes {
            app.world_mut()
                .write_message(OrganizerAction::Inspect(OrganizerInspector::Notes));
            app.update();
            // The next PreUpdate admits the new modal and chooses its initial
            // focus before a later pointer/Tab gesture enters the notes field.
            app.update();
        }
        let focus = if notes {
            app.world_mut()
                .query_filtered::<Entity, With<NotesField>>()
                .single(app.world())
                .unwrap()
        } else {
            app.world_mut()
                .query::<(Entity, &ActionButton)>()
                .iter(app.world())
                .find_map(|(entity, button)| {
                    matches!(
                        button.0,
                        OrganizerAction::Choose(OrganizerChoice::Reinforce)
                    )
                    .then_some(entity)
                })
                .unwrap()
        };
        app.world_mut().resource_mut::<InputFocus>().set(focus);
        app.update();
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(focus));
        assert!(app
            .world()
            .resource::<ObserverKeyboardClaim>()
            .blocks_world_shortcuts());
        (app, window, focus, draft)
    }

    fn typing_key(app: &mut App, window: Entity, key_code: KeyCode, text: &str) {
        app.world_mut().write_message(KeyboardInput {
            key_code,
            logical_key: Key::Character(text.into()),
            state: ButtonState::Pressed,
            text: Some(text.into()),
            repeat: false,
            window,
        });
        app.update();
    }

    #[test]
    fn focused_organizer_circuit_shortcut_opens_earned_evidence_and_restores_draft_focus() {
        let (mut app, window, focus, draft) = focused_organizer(false);
        typing_key(&mut app, window, KeyCode::KeyP, "p");
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.inspector, OrganizerInspector::Evidence);
        assert_eq!(client.return_focus, Some(focus));
        assert_eq!(client.draft.as_ref(), Some(&draft));
        assert!(
            client.view.as_ref().unwrap().observations.is_empty(),
            "opening the inspector cannot fabricate earned evidence"
        );
        assert!(
            client.outbox.is_none(),
            "navigation cannot request hidden material state"
        );
        app.world_mut()
            .write_message(OrganizerAction::CloseInspector);
        app.update();
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.inspector, OrganizerInspector::Closed);
        assert_eq!(client.draft.as_ref(), Some(&draft));
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(focus));
    }

    #[test]
    fn focused_organizer_archive_shortcut_keeps_selection_and_return_focus() {
        let (mut app, window, focus, draft) = focused_organizer(false);
        typing_key(&mut app, window, KeyCode::KeyI, "i");
        assert_eq!(*app.world().resource::<PrimaryView>(), PrimaryView::Map);
        assert!(app.world().resource::<ObserverUiState>().archive_open);
        assert_eq!(app.world().resource::<ArchiveRequests>().0, [false]);
        assert_eq!(
            app.world().resource::<OrganizerClient>().return_focus,
            Some(focus)
        );
        assert!(app
            .world()
            .resource::<Messages<ObserverCommand>>()
            .is_empty());
        return_to_organizer(&mut app, focus, &draft);
    }

    #[test]
    fn organizer_notes_keep_circuit_and_archive_letters_as_text() {
        let (mut app, window, _, draft) = focused_organizer(true);
        typing_key(&mut app, window, KeyCode::KeyP, "p");
        typing_key(&mut app, window, KeyCode::KeyI, "i");
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.inspector, OrganizerInspector::Notes);
        assert_eq!(
            *app.world().resource::<PrimaryView>(),
            PrimaryView::Organizer
        );
        assert!(app.world().resource::<ArchiveRequests>().0.is_empty());
        assert!(!app.world().resource::<ObserverUiState>().archive_open);
        let edited = client.draft.as_ref().unwrap();
        assert_eq!(edited.notes.text, format!("{}pi", draft.notes.text));
        assert_eq!(edited.workplace_id, draft.workplace_id);
        assert_eq!(edited.choice, draft.choice);
        assert!(client.outbox.is_none());
    }

    #[test]
    fn inspector_archive_retains_the_focus_saved_before_inspection() {
        let (mut app, focus, draft) = organizer_navigation();
        app.world_mut()
            .write_message(OrganizerAction::Inspect(OrganizerInspector::Evidence));
        app.update();
        let inspector_focus = app.world_mut().spawn_empty().id();
        app.world_mut()
            .resource_mut::<InputFocus>()
            .set(inspector_focus);
        app.world_mut()
            .write_message(OrganizerAction::ArchiveWorkplace);
        app.update();
        assert_eq!(app.world().resource::<ArchiveRequests>().0, [false]);
        assert_eq!(
            app.world().resource::<OrganizerClient>().return_focus,
            Some(focus)
        );
        return_to_organizer(&mut app, focus, &draft);
    }
}
