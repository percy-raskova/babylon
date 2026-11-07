//! One focused inspector with answers first and stable return navigation.
use super::{
    board, presentation, theme, DeclaredSurface, DetailControls, ObserverFocusTarget, ObserverSet,
    OrganizerAction, OrganizerChoice, OrganizerInspector, OrganizerInspectorRoot, Overlay, Scope,
    SurfaceId, TextPart,
};
use crate::observer::ObservationContext;
use crate::organizer::ui;
use bevy::input_focus::tab_navigation::TabGroup;
use bevy::input_focus::{FocusCause, InputFocus};
use bevy::prelude::*;

pub(super) fn install(app: &mut App) {
    app.add_systems(
        Update,
        (reset_reading, paint_neighbors).in_set(ObserverSet::Paint),
    );
}

pub(super) fn spawn(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                left: percent(14),
                right: percent(14),
                top: px(98),
                bottom: px(48),
                padding: UiRect::all(px(20)),
                border: UiRect::all(px(2)),
                display: Display::None,
                ..ui::column()
            },
            BackgroundColor(theme::INK),
            BorderColor::all(theme::YELLOW),
            ZIndex(25),
            OrganizerInspectorRoot,
            Overlay,
            TabGroup::modal(),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_children(|panel| {
            panel.spawn(ui::row()).with_children(|bar| {
                ui::button(
                    bar,
                    "Return to decision [Esc]",
                    OrganizerAction::CloseInspector,
                );
                bar.spawn((
                    ui::text("Evidence", 22.0, theme::YELLOW),
                    TextPart::InspectorTitle,
                ));
            });
            panel
                .spawn((ui::row(), DetailControls(OrganizerInspector::Review)))
                .with_children(|controls| {
                    ui::button(controls, "Confirm ruling", OrganizerAction::Confirm);
                });
            ui::spawn_scrolling_reading(panel, |body| {
                board::all_practices(body);
                body.spawn((ui::column(), DetailControls(OrganizerInspector::Review)))
                    .with_children(|review| {
                        review.spawn((
                            ui::text("", 19.0, theme::PAPER),
                            TextPart::Review,
                            ObserverFocusTarget::reading(None),
                        ));
                    });
                direction(body);
                body.spawn((ui::column(), DetailControls(OrganizerInspector::Receipts)))
                    .with_children(board::history_links);
                ui::spawn_notes(body);
                body.spawn((
                    ui::text("", 17.0, theme::PAPER),
                    TextPart::InspectorBody,
                    ObserverFocusTarget::reading(None),
                ));
                body.spawn((ui::column(), DetailControls(OrganizerInspector::Evidence)))
                    .with_children(|controls| {
                        ui::button(controls, "Report Archive", OrganizerAction::ArchiveReport);
                        neighbor(controls, ReportDirection::Previous);
                        neighbor(controls, ReportDirection::Next);
                        controls.spawn(ui::row()).with_children(|buttons| {
                            ui::button(
                                buttons,
                                "Keep report in draft",
                                OrganizerAction::KeepEvidence,
                            );
                            ui::button(
                                buttons,
                                "Remove saved reference",
                                OrganizerAction::RemoveReference,
                            );
                        });
                    });
                body.spawn(ui::row()).with_children(|controls| {
                    ui::button(
                        controls,
                        "Cited workplace Archive",
                        OrganizerAction::ArchiveWorkplace,
                    );
                    ui::button(
                        controls,
                        "Our practice Archive",
                        OrganizerAction::ArchiveOrganization,
                    );
                });
                body.spawn((ui::text("", 12.0, theme::GRAY), TextPart::DraftStatus));
                body.spawn((ui::text("", 13.0, theme::YELLOW), TextPart::Message));
            });
        });
}

fn direction(body: &mut ChildSpawnerCommands) {
    body.spawn((ui::column(), DetailControls(OrganizerInspector::Direction)))
        .with_children(|detail| {
            detail.spawn((ui::text("", 16.0, theme::PAPER), TextPart::Context));
            detail.spawn(ui::row()).with_children(|controls| {
                ui::button(
                    controls,
                    "Pause routine",
                    OrganizerAction::Choose(OrganizerChoice::PauseStanding),
                );
                ui::button(
                    controls,
                    "Authorize / resume routine",
                    OrganizerAction::Choose(OrganizerChoice::ResumeStanding),
                );
                ui::button(
                    controls,
                    "Refresh committed situation",
                    OrganizerAction::Refresh,
                );
            });
        });
}

#[derive(Default, PartialEq, Eq)]
pub(super) struct ReadingIdentity {
    context: Option<ObservationContext>,
    inspector: Option<OrganizerInspector>,
    report: Option<[u8; 32]>,
}

pub(super) fn reset_reading(
    scope: Scope,
    mut prior: Local<ReadingIdentity>,
    texts: Query<(Entity, &TextPart, &ChildOf)>,
    mut positions: Query<&mut ScrollPosition>,
    mut focus: ResMut<InputFocus>,
) {
    let next = ReadingIdentity {
        context: Some(scope.session.context()),
        inspector: Some(scope.client.inspector),
        report: (scope.client.inspector == OrganizerInspector::Evidence)
            .then(|| scope.client.selected_evidence_id(scope.session.viewed_tick))
            .flatten(),
    };
    if *prior == next {
        return;
    }
    *prior = next;
    if scope.client.inspector != OrganizerInspector::Evidence {
        return;
    }
    for (entity, part, parent) in &texts {
        if matches!(part, TextPart::InspectorBody) {
            if let Ok(mut position) = positions.get_mut(parent.parent()) {
                position.0 = Vec2::ZERO;
            }
            focus.set(entity, FocusCause::Navigated);
        }
    }
}

#[derive(Component)]
pub(super) struct NeighborCaption(ReportDirection);

#[derive(Clone, Copy, PartialEq, Eq)]
enum ReportDirection {
    Previous,
    Next,
}

fn neighbor(parent: &mut ChildSpawnerCommands, direction: ReportDirection) {
    let next = direction == ReportDirection::Next;
    parent
        .spawn(Node {
            width: percent(100),
            flex_shrink: 0.0,
            row_gap: px(3),
            ..ui::column()
        })
        .with_children(|line| {
            ui::button(
                line,
                if next {
                    "Next report"
                } else {
                    "Previous report"
                },
                if next {
                    OrganizerAction::NextEvidence
                } else {
                    OrganizerAction::PreviousEvidence
                },
            );
            line.spawn((ui::text("", 13.0, theme::GRAY), NeighborCaption(direction)));
        });
}

pub(super) fn paint_neighbors(scope: Scope, mut captions: Query<(&NeighborCaption, &mut Text)>) {
    for (caption, mut text) in &mut captions {
        let report = scope
            .client
            .evidence_neighbor(
                caption.0 == ReportDirection::Next,
                scope.session.viewed_tick,
            )
            .and_then(|id| scope.client.lawful_evidence(id, scope.session.viewed_tick));
        text.set_if_neq(Text::new(report.map_or_else(
            || "No further report in this view".into(),
            presentation::report_caption,
        )));
    }
}
