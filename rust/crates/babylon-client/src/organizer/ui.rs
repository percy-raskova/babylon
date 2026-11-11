//! Native Bevy controls and evidence inspectors for the lawful organizer projection.

use super::amount_editor::{self, AmountField};
use super::evidence::EvidenceMode;
use super::{board, workspace, workspace_copy as copy};

#[path = "report_view.rs"]
mod report_view;

use super::scene::{
    BodyShape, OrganizerScene, OrganizerSceneMode, OrganizerSubject, RelationKind, SceneNode,
};
use super::workspace::DispatchDestination;
#[cfg(test)]
use crate::observer_focus::ObserverFocusPolicy;
use babylon_persistence::runtime_session::OrganizerChoice;
#[cfg(test)]
use babylon_persistence::ArchiveEvidenceClass;
use bevy::ecs::system::SystemParam;
use bevy::input::keyboard::{Key, KeyboardInput};
use bevy::input::ButtonState;
use board::{ComparisonCard, Overlay, PaperAction};
use copy::{DatedLink, Destination};

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

use super::editor::FocusState;
use super::qualification_input::HandlerReceipt;
use super::{presentation, OrganizerClient, OrganizerInspector, RequestKind};
use crate::observer::SessionPhase;
use crate::observer_controls::ControlAvailability;
use crate::ui;
use crate::ui::Interaction;
use babylon_persistence::runtime_session::OrganizerGiftConsent;
use bevy::input_focus::FocusCause;
use bevy::text::LineBreak;
use bevy::ui::UiSystems;

#[derive(Message, Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum OrganizerAction {
    Open,
    SetSceneMode(OrganizerSceneMode),
    SelectSubject(OrganizerSubject),
    Choose(OrganizerChoice),
    FocusAmount(AmountField),
    DraftFromReport,
    Review,
    Confirm,
    Advance,
    Refresh,
    Inspect(OrganizerInspector),
    OpenReferences,
    InspectSubjectEvidence,
    Follow(DatedLink),
    PreviousEvidence,
    NextEvidence,
    KeepEvidence,
    RemoveReference,
    CloseInspector,
    ArchiveWorkplace,
    ArchiveReport,
    ArchiveSelection,
    ArchiveOrganization,
}

/// Feedback for an accepted local navigation or draft selection.
#[derive(Event, Clone, Copy)]
pub(crate) enum OrganizerFeedback {
    Select,
    Open,
    Back,
}

/// Route shell shortcuts through the same availability checks as organizer controls.
#[derive(Event)]
pub(crate) struct OrganizerActionRequested(pub OrganizerAction);

#[derive(Event)]
pub(crate) struct OrganizerEvidenceRequested;

#[derive(Event)]
pub(crate) struct OrganizerArchiveRequested {
    pub target: OrganizerArchiveTarget,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum OrganizerArchiveTarget {
    Browse,
    Workplace,
    Collective,
    PartnerOrganization(u64),
}

#[derive(Component)]
pub(crate) struct OrganizerInspectorRoot;
#[derive(Component)]
pub(super) struct OrganizerRoot;
#[derive(Component)]
pub(crate) struct SceneRoot;
#[derive(Component)]
struct SceneContent;
#[derive(Component)]
pub(super) struct SceneDetail;

#[derive(Component)]
pub(super) struct SceneEvidence;
#[derive(Component)]
struct RelationStage;
#[derive(Component)]
struct RelationBody;
#[derive(Component)]
struct RelationSubject(OrganizerSubject);
#[derive(Component, Clone, Copy)]
struct RelationEdge {
    from: OrganizerSubject,
    to: OrganizerSubject,
    kind: RelationKind,
}

#[derive(Resource, Default)]
struct RenderedScene {
    scene: Option<OrganizerScene>,
    mode: Option<OrganizerSceneMode>,
    historical: Option<bool>,
    availability: Option<SceneAvailability>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum SceneAvailability {
    Ready,
    Loading,
    HistoricalUnavailable,
    Refused(String),
    Unavailable,
}
#[derive(Component)]
struct InspectorShield;
#[derive(Component, Clone, Copy, PartialEq, Eq)]
pub(super) struct ActionButton(pub(super) OrganizerAction);
#[derive(Component)]
struct ButtonStateMarker;
#[derive(Component)]
struct NotesField;
#[derive(Component)]
pub(super) struct DetailControls(pub(super) OrganizerInspector);
#[derive(Component)]
struct ScrollHint(Entity);

#[derive(Component, Clone, Copy)]
pub(super) enum TextPart {
    Title,
    Situation,
    Means,
    InspectorMeans,
    Context,
    Aftermath,
    ChoiceHeading,
    ReviewAvailability,
    Approach(OrganizerChoice),
    ChoiceMarker(OrganizerChoice),
    SceneModeMarker(OrganizerSceneMode),
    Review,
    Message,
    Notes,
    DraftStatus,
    ReferenceSummary,
    InspectorTitle,
    InspectorBody,
}

pub(super) fn text(value: impl Into<String>, size: f32, color: Color) -> impl Bundle {
    (
        Text::new(value),
        TextFont {
            font_size: FontSize::Px(size),
            ..default()
        },
        TextColor(color),
        TextLayout::linebreak(LineBreak::WordOrCharacter),
        Node {
            max_width: percent(100),
            flex_shrink: 0.0,
            ..default()
        },
        ObserverFontRole::Body,
        DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
    )
}

pub(super) fn column() -> Node {
    Node {
        flex_direction: FlexDirection::Column,
        row_gap: px(14),
        min_width: px(0),
        ..default()
    }
}

pub(super) fn row() -> Node {
    Node {
        flex_wrap: FlexWrap::Wrap,
        column_gap: px(8),
        row_gap: px(8),
        flex_shrink: 0.0,
        min_width: px(0),
        ..default()
    }
}

pub(crate) fn button(
    parent: &mut ChildSpawnerCommands,
    label: &str,
    action: OrganizerAction,
) -> Entity {
    parent
        .spawn((
            ui::pressable(),
            ActionButton(action),
            ObserverFocusTarget::action(None),
            Node {
                padding: UiRect::axes(px(8), px(5)),
                border: UiRect::bottom(px(2)),
                min_width: px(0),
                flex_shrink: 0.0,
                ..default()
            },
            BackgroundColor(theme::PANEL),
            BorderColor::all(theme::GRAY),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_children(|children| {
            children
                .spawn(text(label, 14.0, theme::PAPER))
                .insert(Node {
                    flex_shrink: 0.0,
                    ..default()
                });
            children.spawn((text("", 15.0, theme::PAPER), ButtonStateMarker));
            if let OrganizerAction::SetSceneMode(mode) = action {
                children.spawn((
                    text("", 15.0, theme::PAPER),
                    TextPart::SceneModeMarker(mode),
                ));
            }
        })
        .id()
}

fn relation_subject(parent: &mut ChildSpawnerCommands, node: &SceneNode) {
    parent
        .spawn((
            ui::pressable(),
            ActionButton(OrganizerAction::SelectSubject(node.subject)),
            RelationSubject(node.subject),
            ObserverFocusTarget::action(None),
            Node {
                padding: UiRect::axes(px(10), px(8)),
                border: UiRect::bottom(px(2)),
                min_width: px(0),
                flex_shrink: 0.0,
                ..default()
            },
            BackgroundColor(theme::PANEL),
            BorderColor::all(theme::GRAY),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_children(|children| {
            board::thumbnail(children, node.subject);
            children
                .spawn(text(node.caption(), 15.0, theme::PAPER))
                .insert(Node {
                    flex_grow: 1.0,
                    flex_basis: px(0),
                    min_width: px(0),
                    flex_shrink: 1.0,
                    ..default()
                });
            children.spawn((text("", 15.0, theme::PAPER), ButtonStateMarker));
        });
}

fn spawn(mut commands: Commands) {
    commands
        .spawn((
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
            Overlay,
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_children(|shield| {
            shield
                .spawn((text("", 14.0, theme::PAPER), TextPart::InspectorMeans))
                .insert((
                    Node {
                        position_type: PositionType::Absolute,
                        left: px(18),
                        right: px(18),
                        top: px(16),
                        height: px(50),
                        ..default()
                    },
                    Pickable::IGNORE,
                ));
        });

    spawn_scene(&mut commands);
    board::spawn_workspace(&mut commands);
    report_view::spawn(&mut commands);
}

fn spawn_scene(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                left: px(16),
                right: percent(28),
                top: px(87),
                bottom: px(266),
                display: Display::None,
                ..column()
            },
            ZIndex(8),
            SceneRoot,
            Pickable::IGNORE,
            TabGroup::new(9),
            DeclaredSurface::new(SurfaceId::OrganizerWorkspace),
        ))
        .with_children(|root| {
            root.spawn((
                Overlay,
                Node {
                    align_self: AlignSelf::Start,
                    ..row()
                },
            ))
            .with_children(|modes| {
                button(
                    modes,
                    "Places · Wayne County",
                    OrganizerAction::SetSceneMode(OrganizerSceneMode::Places),
                );
                button(
                    modes,
                    "Relationships · Wayne County",
                    OrganizerAction::SetSceneMode(OrganizerSceneMode::Relationships),
                );
            });
            root.spawn((
                Node {
                    flex_grow: 1.0,
                    min_height: px(0),
                    ..column()
                },
                SceneContent,
                Pickable::IGNORE,
            ));
        });
}

fn history_inspector_allowed(inspector: OrganizerInspector) -> bool {
    matches!(
        inspector,
        OrganizerInspector::Evidence | OrganizerInspector::Receipts | OrganizerInspector::Notes
    )
}

fn scene_refresh_pending(scope: &Scope) -> bool {
    scope.client.status_due
        || scope
            .client
            .pending
            .as_ref()
            .is_some_and(|pending| pending.kind == RequestKind::Status)
        || scope.session.advance_pending()
        || scope.session.lifecycle_pending()
        || matches!(
            scope.session.phase,
            SessionPhase::Connecting | SessionPhase::Loading | SessionPhase::Advancing
        )
}

fn scene_availability(scope: &Scope, scene: Option<&OrganizerScene>) -> SceneAvailability {
    if scene.is_some() {
        SceneAvailability::Ready
    } else if scope.session.phase == SessionPhase::Failed || scope.session.runtime_disconnected() {
        SceneAvailability::Refused(
            scope
                .session
                .error
                .clone()
                .unwrap_or_else(|| "Organizer connection lost.".into()),
        )
    } else if scene_refresh_pending(scope) {
        SceneAvailability::Loading
    } else if let Some(message) = scope.client.status_refusal(&scope.session) {
        SceneAvailability::Refused(message.into())
    } else if scope.session.viewed_tick != scope.session.durable_tick {
        SceneAvailability::HistoricalUnavailable
    } else {
        SceneAvailability::Unavailable
    }
}

fn scene_placeholder(availability: &SceneAvailability) -> &str {
    match availability {
        SceneAvailability::Ready => "",
        SceneAvailability::Loading => "Loading organizer scene…",
        SceneAvailability::HistoricalUnavailable => {
            "Historical organizer scene is unavailable for this period."
        }
        SceneAvailability::Refused(message) => message,
        SceneAvailability::Unavailable => "Organizer scene is unavailable.",
    }
}

fn render_scene(
    mut commands: Commands,
    scope: Scope,
    mut rendered: ResMut<RenderedScene>,
    mut roots: Query<&mut Node, (With<SceneRoot>, Without<SceneContent>)>,
    contents: Query<Entity, With<SceneContent>>,
    mut details: Query<&mut Text, With<SceneDetail>>,
    mut evidence: Query<&mut Node, (With<SceneEvidence>, Without<SceneRoot>)>,
) {
    let primary = *scope.view == PrimaryView::Organizer
        && scope.session.organizer_enabled
        && !scope.ui.menu_open
        && !scope.ui.splash_visible
        && !scope.ui.comparison_open
        && (scope.client.inspector == OrganizerInspector::Closed
            || (scope.session.viewed_tick != scope.session.durable_tick
                && !history_inspector_allowed(scope.client.inspector)));
    for mut root in &mut roots {
        let mut next = root.clone();
        next.display = if primary {
            Display::Flex
        } else {
            Display::None
        };
        root.set_if_neq(next);
    }
    let next = scope.client.scene_for(&scope.session);
    let historical = scope.session.viewed_tick != scope.session.durable_tick;
    let availability = scene_availability(&scope, next.as_ref());
    let placeholder = scene_placeholder(&availability);
    let report_subject_selected = next.as_ref().is_some_and(|scene| {
        scene.nodes.iter().any(|node| {
            Some(node.subject) == scope.client.selected_subject
                && scope
                    .client
                    .view
                    .as_ref()
                    .and_then(|view| node.subject.report_subject(view))
                    .is_some()
        })
    });
    for mut node in &mut evidence {
        node.display = if report_subject_selected {
            Display::Flex
        } else {
            Display::None
        };
    }
    for mut detail in &mut details {
        let value = next.as_ref().map_or_else(
            || placeholder.into(),
            |scene| retained_scene_detail(&scope, scene),
        );
        detail.set_if_neq(Text::new(value));
    }
    if rendered.scene == next
        && rendered.mode == Some(scope.client.scene_mode)
        && rendered.historical == Some(historical)
        && rendered.availability.as_ref() == Some(&availability)
    {
        return;
    }
    rendered.scene.clone_from(&next);
    rendered.mode = Some(scope.client.scene_mode);
    rendered.historical = Some(historical);
    rendered.availability = Some(availability.clone());
    for content in &contents {
        commands.entity(content).despawn_children();
        commands.entity(content).with_children(|parent| {
            let Some(scene) = &next else {
                parent.spawn((
                    text(placeholder, 17.0, theme::PAPER),
                    BackgroundColor(theme::INK),
                ));
                if scope.session.viewed_tick != scope.session.durable_tick {
                    parent.spawn(row()).with_children(|links| {
                        button(
                            links,
                            "Historical evidence",
                            OrganizerAction::Inspect(OrganizerInspector::Evidence),
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
                return;
            };
            if scope.client.scene_mode == OrganizerSceneMode::Places {
                spawn_places(parent, scene);
            } else {
                spawn_relationships(parent, scene);
            }
        });
    }
}

fn retained_scene_detail(scope: &Scope, scene: &OrganizerScene) -> String {
    let selected = scope
        .client
        .selected_subject
        .or_else(|| scene.nodes.first().map(|node| node.subject));
    let detail = scene_detail(Some(scene), selected);
    if scope.session.phase == SessionPhase::Failed || scope.session.runtime_disconnected() {
        let error = scope
            .session
            .error
            .as_deref()
            .unwrap_or("Organizer connection lost.");
        format!("Organizer scene error: {error}\n{detail}")
    } else if scene_refresh_pending(scope) {
        format!("Refreshing organizer scene · showing the last committed view.\n{detail}")
    } else if let Some(message) = scope.client.status_refusal(&scope.session) {
        format!("Organizer scene refresh refused: {message}\n{detail}")
    } else {
        detail
    }
}

fn scene_detail(scene: Option<&OrganizerScene>, selected: Option<OrganizerSubject>) -> String {
    let Some(scene) = scene else {
        return "Organizer scene unavailable for this period".into();
    };
    let Some(node) =
        selected.and_then(|subject| scene.nodes.iter().find(|node| node.subject == subject))
    else {
        return "Select a subject to inspect its disclosed relations".into();
    };
    let relationships = [
        RelationKind::Agreement,
        RelationKind::RoutineContact,
        RelationKind::EarnedContact,
        RelationKind::BodyIncidence,
    ]
    .into_iter()
    .filter_map(|kind| {
        let labels = scene
            .relations
            .iter()
            .filter(|relation| {
                (relation.from == node.subject || relation.to == node.subject)
                    && relation.kind == kind
            })
            .map(|relation| {
                if kind == RelationKind::Agreement {
                    let partner = if relation.from == node.subject {
                        relation.to
                    } else {
                        relation.from
                    };
                    scene
                        .nodes
                        .iter()
                        .find(|other| other.subject == partner)
                        .map_or_else(
                            || relation.label.clone(),
                            |other| format!("{} · {}", other.label, relation.label),
                        )
                } else {
                    relation.label.clone()
                }
            })
            .collect::<Vec<_>>();
        (!labels.is_empty()).then(|| {
            if kind == RelationKind::Agreement {
                labels.join("\n")
            } else {
                relation_summary(kind, &labels.iter().map(String::as_str).collect::<Vec<_>>())
            }
        })
    })
    .collect::<Vec<_>>()
    .join("\n");
    if relationships.is_empty() {
        node.caption()
    } else {
        format!("{}\n{}", node.caption(), relationships)
    }
}

fn spawn_places(parent: &mut ChildSpawnerCommands, scene: &OrganizerScene) {
    parent
        .spawn((
            Node {
                align_self: AlignSelf::Start,
                width: px(255),
                max_height: percent(100),
                overflow: Overflow::scroll_y(),
                padding: UiRect::all(px(12)),
                row_gap: px(6),
                ..column()
            },
            Overlay,
            BackgroundColor(theme::INK.with_alpha(0.9)),
        ))
        .with_children(|dock| {
            dock.spawn(text("Wayne County", 28.0, theme::PAPER))
                .insert(ObserverFontRole::Display);
            dock.spawn(text("Known groups and places", 14.0, theme::YELLOW));
            dock.spawn(Node {
                row_gap: px(3),
                ..column()
            })
            .with_children(|buttons| {
                for node in &scene.nodes {
                    let subject = button(
                        buttons,
                        &node.caption(),
                        OrganizerAction::SelectSubject(node.subject),
                    );
                    buttons.commands().entity(subject).insert(Node {
                        width: percent(100),
                        max_width: percent(100),
                        padding: UiRect::axes(px(8), px(5)),
                        border: UiRect::bottom(px(2)),
                        flex_shrink: 0.0,
                        row_gap: px(0),
                        ..column()
                    });
                }
            });
        });
    parent.spawn(Node {
        flex_grow: 1.0,
        ..default()
    });
}

fn spawn_relationships(parent: &mut ChildSpawnerCommands, scene: &OrganizerScene) {
    parent
        .spawn((
            Node {
                flex_grow: 1.0,
                min_height: px(0),
                row_gap: px(8),
                ..column()
            },
            Overlay,
            BackgroundColor(theme::INK.with_alpha(0.86)),
        ))
        .with_children(|stage| {
            stage.spawn(text(&scene.body_status, 14.0, theme::YELLOW));
            let region = stage
                .spawn((
                    Node {
                        position_type: PositionType::Relative,
                        flex_grow: 1.0,
                        min_height: px(0),
                        overflow: Overflow::scroll_y(),
                        justify_content: JustifyContent::SpaceBetween,
                        padding: UiRect::axes(percent(2), px(8)),
                        ..default()
                    },
                    RelationStage,
                ))
                .with_children(|space| {
                    spawn_relation_edges(space, scene);
                    spawn_relation_subjects(space, scene);
                })
                .id();
            stage
                .spawn((text("", 12.0, theme::GRAY), ScrollHint(region)))
                .insert(Node {
                    height: px(16),
                    min_height: px(16),
                    flex_shrink: 0.0,
                    ..default()
                });
        });
}

fn spawn_relation_edges(space: &mut ChildSpawnerCommands, scene: &OrganizerScene) {
    let mut pairs = scene
        .relations
        .iter()
        .filter(|relation| relation.kind != RelationKind::BodyIncidence)
        .map(|relation| (relation.from, relation.to, relation.kind))
        .collect::<Vec<_>>();
    pairs.sort_unstable();
    pairs.dedup();
    for (from, to, kind) in pairs {
        space.spawn((
            Node {
                position_type: PositionType::Absolute,
                height: px(2),
                ..default()
            },
            BackgroundColor(relation_color(kind)),
            UiTransform::IDENTITY,
            Pickable::IGNORE,
            RelationEdge { from, to, kind },
        ));
    }
}

fn relation_color(kind: RelationKind) -> Color {
    match kind {
        RelationKind::Agreement => theme::YELLOW,
        RelationKind::RoutineContact => theme::BLUE,
        RelationKind::EarnedContact => theme::COPPER,
        RelationKind::BodyIncidence => theme::GRAY,
    }
}

fn relation_summary(kind: RelationKind, labels: &[&str]) -> String {
    if kind == RelationKind::EarnedContact {
        let count = labels.len();
        format!(
            "{count} earned contact{} in recent receipts",
            if count == 1 { "" } else { "s" }
        )
    } else {
        labels.join(" · ")
    }
}

fn relation_labels(
    parent: &mut ChildSpawnerCommands,
    scene: &OrganizerScene,
    subject: OrganizerSubject,
) {
    let mut kinds = scene
        .relations
        .iter()
        .filter(|relation| relation.to == subject)
        .map(|relation| relation.kind)
        .collect::<Vec<_>>();
    kinds.sort_unstable();
    kinds.dedup();
    if kinds.is_empty() {
        return;
    }
    parent
        .spawn(Node {
            row_gap: px(3),
            ..column()
        })
        .with_children(|group| {
            for kind in kinds {
                let labels = scene
                    .relations
                    .iter()
                    .filter(|relation| relation.to == subject && relation.kind == kind)
                    .map(|relation| relation.label.as_str())
                    .collect::<Vec<_>>();
                group
                    .spawn(Node {
                        column_gap: px(6),
                        ..row()
                    })
                    .with_children(|line| {
                        line.spawn((
                            text(kind.marker(), 12.0, theme::INK),
                            BackgroundColor(relation_color(kind)),
                            Pickable::IGNORE,
                        ))
                        .insert(Node {
                            min_width: px(20),
                            height: px(20),
                            justify_content: JustifyContent::Center,
                            align_items: AlignItems::Center,
                            ..default()
                        });
                        line.spawn((
                            text(relation_summary(kind, &labels), 12.0, theme::PAPER),
                            Pickable::IGNORE,
                        ))
                        .insert(Node {
                            flex_grow: 1.0,
                            flex_shrink: 1.0,
                            min_width: px(0),
                            ..default()
                        });
                    });
            }
        });
}

fn spawn_relation_subjects(space: &mut ChildSpawnerCommands, scene: &OrganizerScene) {
    let mut members = scene.body_members.clone();
    if members.is_empty() {
        if let Some(node) = scene
            .nodes
            .iter()
            .find(|node| matches!(node.subject, OrganizerSubject::Collective(_)))
        {
            members.push(node.subject);
        }
    }
    let radius = match scene.body_shape {
        Some(BodyShape::Halo) => percent(50),
        Some(BodyShape::Capsule) => px(45),
        Some(BodyShape::Membrane) => px(20),
        None => px(0),
    };
    space
        .spawn((
            Node {
                width: percent(38),
                flex_shrink: 0.0,
                align_self: AlignSelf::FlexStart,
                padding: UiRect::all(px(12)),
                row_gap: px(8),
                border: UiRect::all(px(if scene.body_shape.is_some() { 2 } else { 0 })),
                border_radius: BorderRadius::all(radius),
                ..column()
            },
            BorderColor::all(theme::YELLOW),
            RelationBody,
        ))
        .with_children(|body| {
            for member in &members {
                if let Some(node) = scene.nodes.iter().find(|node| node.subject == *member) {
                    relation_subject(body, node);
                    relation_labels(body, scene, node.subject);
                }
            }
        });
    space
        .spawn(Node {
            width: percent(42),
            flex_shrink: 0.0,
            align_self: AlignSelf::FlexStart,
            row_gap: px(12),
            ..column()
        })
        .with_children(|others| {
            for node in &scene.nodes {
                if !members.contains(&node.subject) {
                    relation_subject(others, node);
                    relation_labels(others, scene, node.subject);
                }
            }
        });
}

fn position_relations(
    stage: Query<(&ComputedNode, &UiGlobalTransform), With<RelationStage>>,
    subjects: Query<(&RelationSubject, &ComputedNode, &UiGlobalTransform)>,
    mut edges: Query<(&RelationEdge, &mut Node, &mut UiTransform)>,
) {
    let Ok((computed, stage_transform)) = stage.single() else {
        return;
    };
    let matrix = stage_transform.affine();
    if !matrix.is_finite() || matrix.matrix2.determinant().abs() <= f32::EPSILON {
        return;
    }
    let inverse = matrix.inverse();
    let point = |subject| {
        subjects
            .iter()
            .find(|(node, _, _)| node.0 == subject)
            .map(|(_, size, transform)| {
                let scale = computed.inverse_scale_factor();
                (
                    (inverse.transform_point2(transform.affine().translation)
                        + computed.size() * 0.5
                        + computed.scroll_position)
                        * scale,
                    size.size() * scale * 0.5,
                )
            })
    };
    for (edge, mut node, mut transform) in &mut edges {
        let (Some((from, from_half)), Some((to, to_half))) = (point(edge.from), point(edge.to))
        else {
            continue;
        };
        let delta = to - from;
        let distance = delta.length();
        if !distance.is_finite() || distance <= f32::EPSILON {
            continue;
        }
        let direction = delta / distance;
        let boundary = |half: Vec2| (half.x / direction.x.abs()).min(half.y / direction.y.abs());
        let start = from + direction * boundary(from_half);
        let end = to - direction * boundary(to_half);
        let length = (end - start).dot(direction).max(0.0);
        let parallel = match edge.kind {
            RelationKind::Agreement | RelationKind::BodyIncidence => 0.0,
            RelationKind::RoutineContact => -3.0,
            RelationKind::EarnedContact => 3.0,
        };
        let center = start + direction * (length * 0.5) + direction.perp() * parallel;
        if !center.is_finite() || !length.is_finite() {
            continue;
        }
        let mut next = node.clone();
        next.left = px(center.x - length * 0.5);
        next.top = px(center.y - 1.0);
        next.width = px(length);
        transform.set_if_neq(UiTransform::from_rotation(Rot2::radians(
            delta.y.atan2(delta.x),
        )));
        node.set_if_neq(next);
    }
}

pub(super) fn spawn_scrolling_reading(
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

pub(super) fn spawn_approach(cards: &mut ChildSpawnerCommands, choice: OrganizerChoice) {
    cards
        .spawn((
            ui::pressable(),
            ActionButton(OrganizerAction::Choose(choice)),
            ObserverFocusTarget::action(None),
            Node {
                flex_shrink: 0.0,
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
            card.spawn((text("", 11.0, theme::PAPER), ButtonStateMarker));
            card.spawn((
                text("SELECT", 11.0, theme::YELLOW),
                TextPart::ChoiceMarker(choice),
            ));
            card.spawn(text(presentation::choice(choice), 18.0, theme::PAPER));
            card.spawn((text("", 14.0, theme::GRAY), TextPart::Approach(choice)));
        });
}

fn spawn_notes(body: &mut ChildSpawnerCommands) {
    body.spawn((column(), DetailControls(OrganizerInspector::Notes)))
        .with_children(|notes| {
            notes.spawn(text("Your notes and references stay with this draft. Editing them spends no time and submits no ruling.", 15.0, theme::GRAY));
            notes.spawn((
                ui::pressable(), NotesField, ObserverFocusTarget::text_input(None),
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

pub(super) fn visible(
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
    if session.viewed_tick != session.durable_tick
        && matches!(
            action,
            OrganizerAction::Inspect(
                OrganizerInspector::Relationships
                    | OrganizerInspector::Direction
                    | OrganizerInspector::Review
                    | OrganizerInspector::Practices
            )
        )
    {
        return false;
    }
    if let OrganizerAction::Follow(link) = action {
        return view == PrimaryView::Organizer
            && matches!(
                client.inspector,
                OrganizerInspector::Closed | OrganizerInspector::Receipts
            )
            && link.current(session);
    }
    if let OrganizerAction::FocusAmount(field) = action {
        return view == PrimaryView::Organizer
            && client.inspector == OrganizerInspector::Closed
            && field.applies(client.choice())
            && session.viewed_tick == session.durable_tick;
    }
    if action == OrganizerAction::DraftFromReport {
        return view == PrimaryView::Organizer
            && client.inspector == OrganizerInspector::Evidence
            && client.report_aid_choice(session).is_some();
    }
    if matches!(action, OrganizerAction::Confirm) {
        return view == PrimaryView::Organizer && client.inspector == OrganizerInspector::Review;
    }
    if let OrganizerAction::Choose(choice) = action {
        return view == PrimaryView::Organizer
            && match client.inspector {
                OrganizerInspector::Practices => true,
                OrganizerInspector::Direction => matches!(
                    choice,
                    OrganizerChoice::PauseStanding | OrganizerChoice::ResumeStanding
                ),
                OrganizerInspector::Closed => {
                    workspace::comparison(client, session).is_some_and(|comparison| {
                        comparison
                            .alternatives
                            .iter()
                            .any(|term| term.choice == choice)
                    })
                }
                _ => false,
            };
    }
    if matches!(action, OrganizerAction::OpenReferences) {
        return view == PrimaryView::Organizer && client.inspector == OrganizerInspector::Notes;
    }
    if matches!(action, OrganizerAction::Refresh) {
        return view == PrimaryView::Organizer && client.inspector == OrganizerInspector::Direction;
    }
    if matches!(action, OrganizerAction::ArchiveReport) {
        return client.inspector == OrganizerInspector::Evidence;
    }
    if matches!(
        action,
        OrganizerAction::ArchiveWorkplace | OrganizerAction::ArchiveSelection
    ) {
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

pub(super) fn enabled(
    action: OrganizerAction,
    client: &OrganizerClient,
    session: &ObserverSession,
) -> bool {
    match action {
        OrganizerAction::Choose(choice) => workspace::reviewable(client, session, choice),
        OrganizerAction::DraftFromReport => {
            client.report_aid_choice(session).is_some_and(|choice| {
                client.available(session)
                    && workspace::reviewable(client, session, choice)
                    && client.draft_writable
                    && (client
                        .selected_evidence_id(session.viewed_tick)
                        .is_some_and(|id| client.evidence_is_saved(id))
                        || client.can_keep_evidence(session).is_ok())
            })
        }
        OrganizerAction::FocusAmount(_) => amount_editor::editing_allowed(client, session),
        OrganizerAction::Review => {
            amount_editor::allocation(client).is_ok()
                && enabled(OrganizerAction::Choose(client.choice()), client, session)
        }
        OrganizerAction::Advance => {
            crate::observer_controls::availability(ObserverCommand::Step, session)
                == ControlAvailability::Enabled
        }
        OrganizerAction::Confirm => {
            client.available(session)
                && client.choice_available(client.choice())
                && client.review_context.as_ref() == Some(&session.context())
                && client.preview.as_ref().is_some_and(|preview| {
                    preview.refusal.is_none() && preview.current_period == session.durable_tick
                })
                && client.reviewed_command.is_some()
                && match client.choice() {
                    choice @ (OrganizerChoice::LocalAid | OrganizerChoice::RemoteAid) => {
                        presentation::aid_terms_attributed(client, choice)
                    }
                    _ => true,
                }
        }
        OrganizerAction::InspectSubjectEvidence => client.selected_report_subject().is_some(),
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
        OrganizerAction::ArchiveReport => {
            report_archive_target(client, session.viewed_tick).is_some()
                && enabled(OrganizerAction::ArchiveWorkplace, client, session)
        }
        OrganizerAction::ArchiveWorkplace
        | OrganizerAction::ArchiveSelection
        | OrganizerAction::ArchiveOrganization => {
            client.view.is_some()
                && (matches!(session.phase, SessionPhase::Ready | SessionPhase::Complete)
                    || (session.phase == SessionPhase::Advancing
                        && session.advance_pending()
                        && client
                            .view
                            .as_ref()
                            .is_some_and(|view| view.period == session.viewed_tick)))
        }
        OrganizerAction::SetSceneMode(_) => client.scene_for(session).is_some(),
        OrganizerAction::SelectSubject(subject) => client
            .scene_for(session)
            .is_some_and(|scene| scene.nodes.iter().any(|node| node.subject == subject)),
        OrganizerAction::Follow(link) => {
            client.campaign == Some(*session.campaign.as_uuid())
                && link.current(session)
                && match link.destination {
                    Destination::Subject(subject) => {
                        enabled(OrganizerAction::SelectSubject(subject), client, session)
                    }
                    Destination::Detail(DispatchDestination::Report(id)) => {
                        client.lawful_evidence(id, session.viewed_tick).is_some()
                    }
                    Destination::Detail(DispatchDestination::Inspector(inspector)) => {
                        enabled(OrganizerAction::Inspect(inspector), client, session)
                    }
                    Destination::Detail(DispatchDestination::ArchiveOrganization) => {
                        enabled(OrganizerAction::ArchiveOrganization, client, session)
                    }
                    Destination::Detail(DispatchDestination::ArchiveWorkplace) => {
                        enabled(OrganizerAction::ArchiveWorkplace, client, session)
                    }
                }
        }
        OrganizerAction::Open | OrganizerAction::CloseInspector => true,
    }
}

#[derive(SystemParam)]
pub(super) struct Scope<'w> {
    pub(super) client: Res<'w, OrganizerClient>,
    pub(super) session: Res<'w, ObserverSession>,
    pub(super) ui: Res<'w, ObserverUiState>,
    pub(super) view: Res<'w, PrimaryView>,
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
            let inspector = matches!(text, Some(TextPart::InspectorBody | TextPart::Review));
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

fn route_link(
    action: OrganizerAction,
    client: &mut OrganizerClient,
    period: u64,
) -> Option<OrganizerAction> {
    let OrganizerAction::Follow(link) = action else {
        return Some(action);
    };
    Some(match link.destination {
        Destination::Subject(subject) => OrganizerAction::SelectSubject(subject),
        Destination::Detail(DispatchDestination::Report(id)) => client
            .open_evidence_report(id, period)
            .then_some(OrganizerAction::Inspect(OrganizerInspector::Evidence))?,
        Destination::Detail(DispatchDestination::Inspector(inspector)) => {
            OrganizerAction::Inspect(inspector)
        }
        Destination::Detail(DispatchDestination::ArchiveWorkplace) => {
            OrganizerAction::ArchiveWorkplace
        }
        Destination::Detail(DispatchDestination::ArchiveOrganization) => {
            OrganizerAction::ArchiveOrganization
        }
    })
}

fn feedback(action: OrganizerAction) -> Option<OrganizerFeedback> {
    match action {
        OrganizerAction::SetSceneMode(_)
        | OrganizerAction::SelectSubject(_)
        | OrganizerAction::Choose(_) => Some(OrganizerFeedback::Select),
        OrganizerAction::Inspect(_)
        | OrganizerAction::InspectSubjectEvidence
        | OrganizerAction::OpenReferences
        | OrganizerAction::Review => Some(OrganizerFeedback::Open),
        OrganizerAction::CloseInspector => Some(OrganizerFeedback::Back),
        _ => None,
    }
}

fn action_available(action: OrganizerAction, state: &mut ActionState) -> bool {
    if !visible(
        action,
        &state.client,
        &state.session,
        &state.ui,
        *state.view,
    ) {
        return false;
    }
    if enabled(action, &state.client, &state.session) {
        return true;
    }
    let allocation_error = (action == OrganizerAction::Review
        && state.client.available(&state.session))
    .then(|| amount_editor::allocation(&state.client).err())
    .flatten();
    state.client.message = allocation_error
        .unwrap_or_else(|| unavailable_message(action, &state.client, &state.session).into());
    false
}

fn pauses_playback(action: OrganizerAction) -> bool {
    matches!(action, OrganizerAction::Inspect(inspector) if inspector != OrganizerInspector::Closed)
        || matches!(
            action,
            OrganizerAction::Review
                | OrganizerAction::FocusAmount(_)
                | OrganizerAction::DraftFromReport
                | OrganizerAction::OpenReferences
                | OrganizerAction::InspectSubjectEvidence
                | OrganizerAction::ArchiveSelection
                | OrganizerAction::ArchiveReport
                | OrganizerAction::ArchiveWorkplace
                | OrganizerAction::ArchiveOrganization
                | OrganizerAction::Refresh
        )
}

fn report_archive_target(client: &OrganizerClient, period: u64) -> Option<OrganizerArchiveTarget> {
    use babylon_persistence::runtime_session::OrganizerReport;

    let id = client.selected_evidence_id(period)?;
    if let Some(observation) = client.lawful_evidence(id, period) {
        return Some(match observation.report {
            OrganizerReport::Partner { .. } => {
                OrganizerArchiveTarget::PartnerOrganization(observation.subject_id)
            }
            _ => OrganizerArchiveTarget::Workplace,
        });
    }
    (client.evidence.mode == EvidenceMode::Saved && client.draft.as_ref()?.references.contains(&id))
        .then_some(OrganizerArchiveTarget::Browse)
}

fn open_archive(action: OrganizerAction, state: &mut ActionState, commands: &mut Commands) -> bool {
    let ActionState {
        client,
        session,
        ui,
        view,
        focus,
        atlas,
        selected,
        ..
    } = state;
    let target = match action {
        OrganizerAction::ArchiveOrganization => OrganizerArchiveTarget::Collective,
        OrganizerAction::ArchiveSelection => match client.selected_subject {
            Some(
                OrganizerSubject::AidPartner(id)
                | OrganizerSubject::WorkplaceCommittee(id)
                | OrganizerSubject::NeighborhoodGroup(id),
            ) => OrganizerArchiveTarget::PartnerOrganization(id),
            Some(OrganizerSubject::Collective(_)) => OrganizerArchiveTarget::Collective,
            _ => OrganizerArchiveTarget::Workplace,
        },
        OrganizerAction::ArchiveReport => {
            let Some(target) = report_archive_target(client, session.viewed_tick) else {
                return false;
            };
            target
        }
        _ => OrganizerArchiveTarget::Workplace,
    };
    if client.inspector == OrganizerInspector::Closed {
        client.return_focus = focus.get();
    }
    selected.0 = atlas.index_of_fips("26163");
    commands.trigger(OrganizerArchiveRequested { target });
    client.inspector = OrganizerInspector::Closed;
    **view = PrimaryView::Map;
    ui.archive_open = true;
    ui.history_open = false;
    true
}

fn actions(
    mut events: MessageReader<OrganizerAction>,
    mut state: ActionState,
    fields: Query<(Entity, &AmountField)>,
    mut commands: Commands,
    mut observer_commands: MessageWriter<ObserverCommand>,
    mut qualification: Option<ResMut<HandlerReceipt>>,
) {
    for (&action, message_id) in events.read_with_id() {
        if !action_available(action, &mut state) {
            if let Some(receipt) = qualification.as_deref_mut() {
                receipt.organizer_finished(message_id, false, &state.client);
            }
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
        let Some(action) = route_link(action, client, session.viewed_tick) else {
            continue;
        };
        if pauses_playback(action) {
            session.pause_playback();
        }
        if let Some(cue) = feedback(action) {
            commands.trigger(cue);
        }
        match action {
            OrganizerAction::Follow(_) => unreachable!("dated links were routed above"),
            OrganizerAction::Open => open_organizer(view, ui, client, focus, atlas, selected),
            OrganizerAction::SetSceneMode(mode) => client.scene_mode = mode,
            OrganizerAction::SelectSubject(subject) => {
                select_subject(subject, client, atlas, selected);
            }
            OrganizerAction::Choose(choice) => {
                choose_approach(client, focus, time.elapsed_secs_f64(), choice);
            }
            OrganizerAction::FocusAmount(field) => {
                if let Some((entity, _)) = fields.iter().find(|(_, value)| **value == field) {
                    focus.set(entity, FocusCause::Navigated);
                }
            }
            OrganizerAction::DraftFromReport => {
                if !draft_from_report(client, session, focus, time.elapsed_secs_f64()) {
                    continue;
                }
            }
            OrganizerAction::Review => {
                if !review_approach(client, session, focus) {
                    continue;
                }
            }
            OrganizerAction::Confirm => {
                confirm_approach(client, session);
                close_inspector(client, focus);
            }
            OrganizerAction::Advance => {
                observer_commands.write(ObserverCommand::Step);
            }
            OrganizerAction::Refresh => {
                client.status_due = true;
            }
            OrganizerAction::Inspect(inspector) => {
                inspect(client, focus, inspector, session.viewed_tick);
            }
            OrganizerAction::InspectSubjectEvidence => {
                if !client.open_selected_subject_reports(session.viewed_tick) {
                    continue;
                }
                client.return_focus = focus.get();
                client.inspector = OrganizerInspector::Evidence;
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
            OrganizerAction::ArchiveWorkplace
            | OrganizerAction::ArchiveOrganization
            | OrganizerAction::ArchiveReport
            | OrganizerAction::ArchiveSelection => {
                if !open_archive(action, &mut state, &mut commands) {
                    continue;
                }
            }
            OrganizerAction::CloseInspector => {
                close_inspector(client, focus);
            }
        }
        if let Some(receipt) = qualification.as_deref_mut() {
            receipt.organizer_finished(message_id, true, &state.client);
        }
    }
}

fn inspect(
    client: &mut OrganizerClient,
    focus: &InputFocus,
    inspector: OrganizerInspector,
    period: u64,
) {
    if client.inspector == OrganizerInspector::Closed {
        client.return_focus = focus.get();
    }
    client.inspector = inspector;
    if inspector == OrganizerInspector::Evidence {
        client.open_evidence_reports(period);
    }
}

fn draft_from_report(
    client: &mut OrganizerClient,
    session: &ObserverSession,
    focus: &mut InputFocus,
    now: f64,
) -> bool {
    let Some(choice) = client.report_aid_choice(session) else {
        return false;
    };
    let Some(id) = client.selected_evidence_id(session.viewed_tick) else {
        return false;
    };
    if !client.evidence_is_saved(id) {
        if let Err(reason) = client.keep_evidence(session, now) {
            client.message = reason.into();
            return false;
        }
    }
    if let Some(draft) = client.draft.as_mut() {
        draft.selected_reference = Some(id);
    }
    close_inspector(client, focus);
    choose_approach(client, focus, now, choice);
    if client.message.is_empty() {
        client.message = "Report cited in your draft. Adjust the amounts before review.".into();
    } else {
        client.message.insert_str(0, "Report cited in your draft. ");
    }
    true
}

fn close_inspector(client: &mut OrganizerClient, focus: &mut InputFocus) {
    client.inspector = OrganizerInspector::Closed;
    if let Some(entity) = client.return_focus.take() {
        focus.set(entity, FocusCause::Navigated);
    }
}

fn open_organizer(
    view: &mut PrimaryView,
    ui: &mut ObserverUiState,
    client: &mut OrganizerClient,
    focus: &mut InputFocus,
    atlas: &crate::atlas::CountyAtlas,
    selected: &mut crate::map::SelectedCounty,
) {
    *view = PrimaryView::Organizer;
    selected.0 = atlas.index_of_fips("26163");
    ui.archive_open = false;
    ui.history_open = false;
    ui.disclosure = None;
    if let Some(entity) = client.return_focus.take() {
        focus.set(entity, FocusCause::Navigated);
    }
}

fn select_subject(
    subject: OrganizerSubject,
    client: &mut OrganizerClient,
    atlas: &crate::atlas::CountyAtlas,
    selected: &mut crate::map::SelectedCounty,
) {
    client.selected_subject = Some(subject);
    selected.0 = atlas.index_of_fips("26163");
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
    client.message = amount_editor::reconcile(client).err().unwrap_or_default();
    if matches!(
        client.inspector,
        OrganizerInspector::Direction | OrganizerInspector::Practices
    ) {
        client.inspector = OrganizerInspector::Closed;
        if let Some(entity) = client.return_focus.take() {
            focus.set(entity, FocusCause::Navigated);
        }
    }
}

fn review_approach(
    client: &mut OrganizerClient,
    session: &mut ObserverSession,
    focus: &InputFocus,
) -> bool {
    if let Err(reason) = amount_editor::reconcile(client) {
        client.message = reason;
        return false;
    }
    let Some(command) = client.make_command(session, client.choice()) else {
        client.message = "Current terms do not support the selected request.".into();
        return false;
    };
    client.queue(session, RequestKind::Preview, Some(command));
    client.return_focus = focus.get();
    client.inspector = OrganizerInspector::Review;
    client.message =
        "Checking the next-period commitment against current authority and time…".into();
    true
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
            if let ControlAvailability::Disabled(reason) =
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
    } else if session.phase == SessionPhase::Complete {
        "This campaign is complete. Its reports and practice receipts remain available."
    } else if client
        .pending
        .as_ref()
        .is_some_and(|pending| pending.kind == RequestKind::Submit)
    {
        "Waiting for durable acceptance of this ruling. Refresh its status after the response."
    } else if client.commitment.is_some() {
        "A ruling is already accepted for this period. Advance or inspect its status."
    } else if matches!(action, OrganizerAction::Choose(OrganizerChoice::Collect))
        || client.choice() == OrganizerChoice::Collect
    {
        if client
            .collection_preview()
            .is_some_and(|terms| terms.cash_consent == OrganizerGiftConsent::Refuse)
        {
            "The household independently refused cash consent. Other work does not grant that permission."
        } else {
            "Refresh the current attributed collection terms before reviewing this ruling."
        }
    } else {
        "Wait for the committed situation or review the selected approach."
    }
}

fn open_evidence(
    _event: On<OrganizerEvidenceRequested>,
    mut client: ResMut<OrganizerClient>,
    mut view: ResMut<PrimaryView>,
    focus: Res<InputFocus>,
    mut session: ResMut<ObserverSession>,
    mut ui: ResMut<ObserverUiState>,
) {
    if session.organizer_enabled {
        session.pause_playback();
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
        Option<&'static PaperAction>,
        &'static Interaction,
        &'static mut Node,
        &'static mut BackgroundColor,
        &'static mut BorderColor,
    ),
    (
        Without<ComparisonCard>,
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
        let next = if primary && scope.client.inspector == OrganizerInspector::Closed {
            Display::Flex
        } else {
            Display::None
        };
        if node.display != next {
            node.display = next;
        }
    }
    for mut node in &mut paint.inspectors {
        let next = if primary
            && (scope.session.viewed_tick == scope.session.durable_tick
                || history_inspector_allowed(scope.client.inspector))
            && scope.client.inspector != OrganizerInspector::Closed
        {
            Display::Flex
        } else {
            Display::None
        };
        if node.display != next {
            node.display = next;
        }
    }
    for mut node in &mut paint.shields {
        let next = if primary
            && (scope.session.viewed_tick == scope.session.durable_tick
                || history_inspector_allowed(scope.client.inspector))
            && scope.client.inspector != OrganizerInspector::Closed
        {
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
    let complete = scope.session.phase == SessionPhase::Complete;
    let (inspector_title, mut inspector_body) =
        presentation::inspector(&scope.client, scope.session.viewed_tick);
    if scope.client.inspector == OrganizerInspector::Relationships {
        if let Some((
            babylon_persistence::runtime_session::OrganizerBodyDisclosure::Partial(part),
            body_scope,
        )) = scope.client.body_for(&scope.session)
        {
            if body_scope.period == scope.session.viewed_tick {
                use std::fmt::Write as _;
                let _ = write!(inspector_body, "\nDISCLOSED PART OF CONTROLLED BODY\nBody ID: {} · key: {} / {}\nOnly disclosed collective and contributor incidence is shown; other incidence is unknown.", part.runtime_hyperedge_id, part.scenario, part.local_name);
            }
        }
    }
    let note_focused = focus
        .get()
        .is_some_and(|entity| paint.notes.contains(entity));
    let note_focus = if note_focused {
        FocusState::Focused
    } else {
        FocusState::Unfocused
    };
    let comparison = workspace::comparison(&scope.client, &scope.session);
    for (part, mut text) in &mut paint.texts {
        let value = match part {
            TextPart::Title => scope.client.view.as_ref().map_or_else(|| "Wayne Organizing Collective".into(), |view| view.organization_label.clone()),
            TextPart::Situation => board::subject_reading(scope),
            TextPart::Means | TextPart::InspectorMeans => copy::resource_masthead(&scope.client, &scope.session),
            TextPart::Context => scope.client.view.as_ref().filter(|view| view.period == scope.session.viewed_tick).map_or_else(String::new, presentation::context),
            TextPart::Aftermath => continue,
            TextPart::ReviewAvailability => copy::review_reason(&scope.client, comparison.as_ref()),
            TextPart::ChoiceHeading => if complete { "Campaign complete".into() } else if historical { "Past commitments".into() } else { format!("Work for period {}", scope.session.viewed_tick.saturating_add(1)) },
            TextPart::Approach(_) if historical => String::new(),
            TextPart::Approach(choice) => if complete { "No further period remains. Inspect our practice history and retained reports.".into() } else { scope.client.view.as_ref().map_or_else(String::new, |view| presentation::client_approach(&scope.client, view, *choice)) },
            TextPart::ChoiceMarker(choice) => {
                if complete { "CLOSED".into() }
                else if scope.client.commitment.as_ref().is_some_and(|value| value.command.choice == *choice) { "ACCEPTED".into() }
                else if scope.client.choice() == *choice { "SELECTED DRAFT".into() }
                else { comparison.as_ref().and_then(|v| v.all_practices.iter().find(|p| p.choice == *choice)).map_or_else(|| "Unavailable".into(), |p| copy::availability(p.availability)) }
            },
            TextPart::SceneModeMarker(mode) => if *mode == scope.client.scene_mode { " · SELECTED".into() } else { String::new() },
            TextPart::Review => presentation::review(&scope.client, historical, complete, scope.session.phase == SessionPhase::Advancing),
            TextPart::ReferenceSummary => format!("{} report reference(s) in this personal draft. References help you review evidence; they never execute a practice.", scope.client.draft.as_ref().map_or(0, |draft| draft.references.len())),
            TextPart::DraftStatus => if !scope.client.draft_writable { "Draft saving unavailable · original file retained".into() } else if scope.client.draft_dirty { "Draft changes awaiting save".into() } else { "Personal draft saved".into() },
            TextPart::Message => if scope.session.advance_pending() {
                format!("Advance requested from P{} · awaiting commit", scope.session.durable_tick)
            } else if scope.client.message.is_empty() {
                scope.client.commitment.as_ref().map_or_else(|| amount_editor::allocation(&scope.client).err().unwrap_or_default(), |ruling| format!("Ruling accepted · advance to resolve P{}", ruling.resolves_period))
            } else { scope.client.message.clone() },
            TextPart::Notes => scope.client.draft.as_ref().map_or_else(String::new, |draft| {
                if draft.notes.text.is_empty() && note_focus == FocusState::Unfocused { "Click or Tab here to write personal notes.".into() }
                else { draft.notes.display(note_focus) }
            }),
            TextPart::InspectorTitle => inspector_title.clone(), TextPart::InspectorBody => inspector_body.clone(),
        };
        if text.0 != value {
            text.0 = value;
        }
    }
}

fn paint_buttons(scope: &Scope, buttons: &mut PaintedButtons) {
    for (button, paper, interaction, mut node, mut background, mut border) in &mut *buttons {
        if matches!(
            button.0,
            OrganizerAction::FocusAmount(_) | OrganizerAction::DraftFromReport
        ) {
            node.display = if visible(
                button.0,
                &scope.client,
                &scope.session,
                &scope.ui,
                *scope.view,
            ) {
                Display::Flex
            } else {
                Display::None
            };
        }
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
        let selected = matches!(button.0, OrganizerAction::Choose(choice) if choice == scope.client.choice())
            || matches!(button.0, OrganizerAction::SetSceneMode(mode) if mode == scope.client.scene_mode)
            || matches!(button.0, OrganizerAction::SelectSubject(subject) if Some(subject) == scope.client.selected_subject);
        let next_action = available
            && match button.0 {
                OrganizerAction::Review => scope.client.preview.is_none(),
                OrganizerAction::Confirm => scope.client.preview.is_some(),
                OrganizerAction::Advance => scope.client.commitment.is_some(),
                _ => false,
            };
        let color = if paper.is_some() {
            if !available || *interaction == Interaction::Pressed {
                theme::INK
            } else {
                theme::PANEL
            }
        } else if !available {
            theme::INK
        } else if *interaction == Interaction::Pressed {
            theme::RED.with_alpha(0.4)
        } else if *interaction == Interaction::Hovered || selected || next_action {
            theme::YELLOW.with_alpha(0.2)
        } else {
            theme::PANEL
        };
        background.set_if_neq(BackgroundColor(color));
        border.set_if_neq(BorderColor::all(
            if selected
                || next_action
                || (paper.is_some() && available && *interaction == Interaction::Hovered)
            {
                theme::YELLOW
            } else if available {
                theme::GRAY
            } else {
                theme::GRAY.with_alpha(0.3)
            },
        ));
    }
}

fn paint_button_markers(
    scope: Scope,
    buttons: Query<(&ActionButton, &Interaction, &Children)>,
    mut markers: Query<&mut Text, With<ButtonStateMarker>>,
) {
    for (button, interaction, children) in &buttons {
        let available = visible(
            button.0,
            &scope.client,
            &scope.session,
            &scope.ui,
            *scope.view,
        ) && enabled(button.0, &scope.client, &scope.session);
        let marker = match (available, *interaction == Interaction::Hovered) {
            (true, true) => " · HOVER",
            (false, true) => " · HOVER · UNAVAILABLE",
            (false, false) => " · UNAVAILABLE",
            (true, false) => "",
        };
        for child in children.iter() {
            if let Ok(mut text) = markers.get_mut(child) {
                text.set_if_neq(Text::new(marker));
            }
        }
    }
}

fn normalize_history_inspector(
    session: Res<ObserverSession>,
    mut client: ResMut<OrganizerClient>,
    mut focus: ResMut<InputFocus>,
) {
    if session.viewed_tick != session.durable_tick
        && matches!(
            client.inspector,
            OrganizerInspector::Relationships
                | OrganizerInspector::Direction
                | OrganizerInspector::Review
                | OrganizerInspector::Practices
        )
    {
        client.inspector = OrganizerInspector::Closed;
        if let Some(entity) = client.return_focus.take() {
            focus.set(entity, FocusCause::Navigated);
        }
    }
}

pub(super) fn install(app: &mut App) {
    board::install(app);
    amount_editor::install(app);
    report_view::install(app);
    app.init_resource::<RenderedScene>()
        .add_message::<OrganizerAction>()
        .add_systems(Startup, spawn)
        .add_systems(
            PreUpdate,
            normalize_history_inspector.before(ObserverFocusSystems::Eligibility),
        )
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
        .add_systems(
            Update,
            (paint, render_scene, paint_button_markers).in_set(ObserverSet::Paint),
        )
        .add_systems(
            PostUpdate,
            (paint_scroll_hints, position_relations).after(UiSystems::Layout),
        )
        .add_observer(requested)
        .add_observer(keyboard_button)
        .add_observer(notes_input)
        .add_observer(open_evidence);
}

#[cfg(test)]
pub(crate) fn install_evidence_observer_for_test(app: &mut App) {
    app.add_observer(open_evidence);
}

#[cfg(test)]
#[path = "report_reading_tests.rs"]
mod report_reading_tests;

#[cfg(test)]
#[path = "render_geometry_tests.rs"]
mod render_geometry_tests;
#[cfg(test)]
#[path = "resource_header_tests.rs"]
mod resource_header_tests;

#[cfg(test)]
pub(crate) mod tests {
    use super::super::draft::OrganizerDraft;
    use super::super::editor::NoteEditor;
    use babylon_persistence::runtime_session::OrganizerAllocation;

    use super::super::OrganizerCommand;
    use super::super::OrganizerPreview;
    use super::*;
    use crate::atlas::CountyAtlas;
    use crate::map::SelectedCounty;
    use crate::observer::ObservationContext;
    use crate::observer::SessionPhase;
    use crate::observer_focus::ObserverFocusKind;
    use crate::observer_focus::ObserverKeyboardClaim;
    use crate::observer_ui::ObserverCommand;
    use crate::observer_ui::ObserverFrame;
    use babylon_persistence::identity::CampaignId;
    use babylon_persistence::observer_reader::ObserverEconomySnapshot;
    use babylon_persistence::runtime_session::OrganizerGiftConsent;
    use babylon_persistence::runtime_session::OrganizerInquiry;
    use babylon_persistence::runtime_session::OrganizerPauseReason;
    use babylon_persistence::runtime_session::OrganizerSnapshot;
    use babylon_persistence::runtime_session::{
        OrganizerAidKind, OrganizerStandingWork, OrganizerView,
    };
    use babylon_persistence::runtime_session::{RuntimeSessionRequest, RuntimeSessionResponse};
    use bevy::text::TextLayoutInfo;
    use bevy::time::TimeUpdateStrategy;
    use std::sync::mpsc::Sender;
    use uuid::Uuid;

    #[derive(Resource, Default)]
    struct ObservedCommands(Vec<ObserverCommand>);

    fn observe_commands(
        mut events: MessageReader<ObserverCommand>,
        mut seen: ResMut<ObservedCommands>,
    ) {
        seen.0.extend(events.read().copied());
    }

    pub(super) fn admitted_scene_fixture() -> (App, Option<OrganizerDraft>) {
        use babylon_persistence::runtime_session::{
            OrganizerBodySource, OrganizerObservation, OrganizerReport,
        };
        let (_, _, _, mut snapshot) = super::super::tests::status_fixture();
        let (mut client, mut session) = super::super::tests::ready();
        session.content_hash = Some(crate::dossier::hex_bytes([4; 32]));
        session.world_hash = Some(crate::dossier::hex_bytes([5; 32]));
        snapshot.body_scope.source = Some(OrganizerBodySource::Committed {
            tick_content_hash: [4; 32],
            world_hash: [5; 32],
        });
        for period in [2, 3] {
            snapshot.view.observations.push(OrganizerObservation {
                observation_id: [u8::try_from(period).expect("fixture period fits"); 32],
                actor_id: 90,
                subject_id: 91,
                source_actor_id: 92,
                observed_period: period - 1,
                acquired_period: period,
                receipt_id: Some([7; 32]),
                report: OrganizerReport::Work {
                    performed_labor_hours: 2,
                    output_kg: 777,
                    previous_labor_hours: None,
                    previous_output_kg: None,
                },
            });
        }
        client.queue(&mut session, RequestKind::Status, None);
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } =
            client.outbox.take().expect("status request")
        else {
            panic!("status request")
        };
        client
            .status(request_id, snapshot, &mut session)
            .expect("admitted status");
        let draft = client.draft.clone();
        let (mut app, _, _) = organizer_navigation();
        app.insert_resource(client).insert_resource(session);
        app.init_resource::<ObservedCommands>()
            .add_systems(Update, observe_commands.after(ObserverSet::Input));
        app.update();
        app.update();
        (app, draft)
    }

    #[test]
    fn captured_workplace_targets_are_named_after_selecting_neighborhood() {
        let (mut app, _) = admitted_scene_fixture();
        let neighborhood = OrganizerSubject::NeighborhoodGroup(93);
        app.world_mut()
            .write_message(OrganizerAction::SelectSubject(neighborhood));
        app.update();

        for (choice, label) in [
            (
                OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost),
                "Ask about work and output",
            ),
            (
                OrganizerChoice::Inquiry(OrganizerInquiry::MaintenanceReceived),
                "Ask about maintenance",
            ),
            (OrganizerChoice::Reinforce, "Reinforce workplace contact"),
        ] {
            let card = {
                let world = app.world_mut();
                world
                    .query::<(&TextPart, &Text)>()
                    .iter(world)
                    .find_map(|(part, text)| {
                        matches!(part, TextPart::Approach(value) if *value == choice)
                            .then(|| text.0.clone())
                    })
                    .expect("approach card")
            };
            assert!(
                card.contains("Target: Fixture workplace · Partner: Fixture workplace contacts"),
                "{card}"
            );
            press_named(&mut app, label);
            review_selected(&mut app);
            app.update();
            let review = painted_text(&mut app, false);
            let target = review
                .find("Target: Fixture workplace · Partner: Fixture workplace contacts")
                .expect("captured target visible");
            let cost = review.find("Cost:").expect("finite cost visible");
            let displaced = review
                .find("Replaces neighborhood work once")
                .expect("displaced work visible");
            let partner = review
                .find("Partner participation is independent")
                .expect("independent response visible");
            let resolves = review
                .find("Resolves period 4")
                .expect("resolution period visible");
            assert!(
                target < cost && cost < displaced && displaced < partner && partner < resolves,
                "{review}"
            );
            assert_eq!(
                app.world().resource::<OrganizerClient>().selected_subject,
                Some(neighborhood)
            );
        }
    }

    #[test]
    fn reinforce_review_distinguishes_contact_purpose_from_contributor_concern() {
        use babylon_persistence::runtime_session::OrganizerPosition;
        let (mut app, _) = admitted_scene_fixture();
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            let view = client.view.as_mut().expect("view");
            view.public_workplace_contact = true;
            view.positions.push(OrganizerPosition {
                contributor_id: 90,
                label: "Fixture contributor".into(),
                promised_hours: 2,
                concern: "Households need food".into(),
                objection: String::new(),
                review_condition: String::new(),
            });
        }
        app.update();
        let context = {
            let world = app.world_mut();
            world
                .query::<(&TextPart, &Text)>()
                .iter(world)
                .find_map(|(part, text)| matches!(part, TextPart::Context).then(|| text.0.clone()))
                .expect("context")
        };
        assert!(
            context.contains("Contributor concerns (background)"),
            "{context}"
        );
        assert!(context.contains("Households need food"), "{context}");
        press_named(&mut app, "Reinforce workplace contact");
        review_selected(&mut app);
        app.update();
        let review = painted_text(&mut app, false);
        let reviewed_draft = app.world().resource::<OrganizerClient>().draft.clone();
        assert!(
            review.contains("Target: Fixture workplace · Partner: Fixture workplace contacts"),
            "{review}"
        );
        assert!(
            review.contains("contact the workplace partner") && review.contains("report sharing"),
            "{review}"
        );
        assert!(review.contains("not household aid"), "{review}");
        assert!(
            review.contains("If contact is completed")
                && review.contains("can renew")
                && review.contains("does not itself provide a report"),
            "{review}"
        );
        assert!(
            review.contains("Cost: 8 of 16 organizer-hours")
                && review.contains("Replaces neighborhood work once"),
            "{review}"
        );
        assert!(
            review.contains("Partner participation is independent")
                && review.contains("Confirm alone"),
            "{review}"
        );
        app.world_mut()
            .write_message(OrganizerAction::SelectSubject(
                OrganizerSubject::NeighborhoodGroup(93),
            ));
        app.update();
        assert_eq!(
            app.world().resource::<OrganizerClient>().selected_subject,
            Some(OrganizerSubject::NeighborhoodGroup(93))
        );
        assert_eq!(painted_text(&mut app, false), review);
        assert_eq!(
            app.world().resource::<OrganizerClient>().draft,
            reviewed_draft
        );
        assert!(app.world().resource::<OrganizerClient>().outbox.is_none());
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.commitment = Some(super::super::OrganizerCommitment {
                command: client.reviewed_command.clone().expect("reviewed command"),
                resolves_period: 4,
                commitment_id: [4; 32],
            });
        }
        app.update();
        let accepted = painted_text(&mut app, false);
        assert!(
            accepted.contains("ACCEPTED") && accepted.contains("Fixture workplace contacts"),
            "{accepted}"
        );
        assert!(
            accepted.contains("contact the workplace partner")
                && accepted.contains("not household aid"),
            "{accepted}"
        );
        assert!(
            accepted.contains("If contact is completed") && accepted.contains("can renew"),
            "{accepted}"
        );
        assert!(accepted.contains("Advance to resolve"), "{accepted}");
    }

    #[test]
    fn accepted_workplace_ruling_keeps_its_target_after_selection_changes() {
        let (mut app, _) = admitted_scene_fixture();
        press_named(&mut app, "Reinforce workplace contact");
        review_selected(&mut app);
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.commitment = Some(super::super::OrganizerCommitment {
                command: client.reviewed_command.clone().expect("reviewed command"),
                resolves_period: 4,
                commitment_id: [4; 32],
            });
        }
        app.world_mut()
            .write_message(OrganizerAction::SelectSubject(
                OrganizerSubject::NeighborhoodGroup(93),
            ));
        app.update();
        let accepted = painted_text(&mut app, false);
        assert!(
            accepted.contains("Target: Fixture workplace · Partner: Fixture workplace contacts"),
            "{accepted}"
        );
        assert!(accepted.contains("Advance to resolve"), "{accepted}");
    }

    #[test]
    fn scene_navigation_preserves_draft_and_action_target() {
        let (mut app, draft) = admitted_scene_fixture();
        let committee = OrganizerSubject::WorkplaceCommittee(92);
        let entity = {
            let world = app.world_mut();
            let mut query = world.query::<(Entity, &ActionButton)>();
            query.iter(world).find_map(|(entity, action)|
                matches!(action.0, OrganizerAction::SelectSubject(subject) if subject == committee).then_some(entity)
            ).expect("committee target")
        };
        *app.world_mut()
            .get_mut::<Interaction>(entity)
            .expect("interaction") = Interaction::Hovered;
        app.update();
        assert_eq!(
            app.world().resource::<OrganizerClient>().selected_subject,
            None
        );
        app.world_mut()
            .write_message(OrganizerAction::SelectSubject(committee));
        app.world_mut().write_message(OrganizerAction::SetSceneMode(
            OrganizerSceneMode::Relationships,
        ));
        app.update();
        press_named(&mut app, "Inspect selected evidence");
        assert_eq!(
            app.world().resource::<OrganizerClient>().inspector,
            OrganizerInspector::Evidence
        );
        assert_eq!(
            app.world()
                .resource::<OrganizerClient>()
                .selected_evidence_id(3),
            Some([3; 32])
        );
        press_named(&mut app, "Next report");
        assert_eq!(
            app.world()
                .resource::<OrganizerClient>()
                .selected_evidence_id(3),
            Some([2; 32])
        );
        press_named(&mut app, "Cited workplace Archive");
        assert_eq!(
            app.world().resource::<ArchiveRequests>().0,
            [OrganizerArchiveTarget::Workplace]
        );
        assert_eq!(*app.world().resource::<PrimaryView>(), PrimaryView::Map);
        app.world_mut().write_message(OrganizerAction::Open);
        app.update();
        assert_eq!(
            app.world().resource::<OrganizerClient>().selected_subject,
            Some(committee)
        );
        press_named(&mut app, "Inspect selected evidence");
        press_named(&mut app, "Return to decision [Esc]");
        app.world_mut()
            .write_message(OrganizerAction::SelectSubject(
                OrganizerSubject::NeighborhoodGroup(93),
            ));
        app.update();
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(
            client.selected_subject,
            Some(OrganizerSubject::NeighborhoodGroup(93))
        );
        assert_eq!(client.draft, draft);
        let view = client.view.as_ref().expect("view");
        assert_eq!(
            (view.actor_id, view.workplace_id, view.workplace_partner_id),
            (90, 91, 92)
        );
        assert!(client.outbox.is_none());
        assert!(!app.world().resource::<ObserverSession>().advance_pending());
        press_named(&mut app, "Review choice");
        assert!(matches!(
            app.world().resource::<OrganizerClient>().outbox,
            Some(RuntimeSessionRequest::PreviewOrganizer { .. })
        ));
        assert!(!app.world().resource::<ObserverSession>().advance_pending());
        assert!(!app
            .world()
            .resource::<ObservedCommands>()
            .0
            .contains(&ObserverCommand::Step));
        inspect_period(&mut app, 0);
        app.update();
        let client = app.world().resource::<OrganizerClient>();
        let session = app.world().resource::<ObserverSession>();
        assert!(!enabled(OrganizerAction::Confirm, client, session));
        assert!(client.lawful_evidence([2; 32], 0).is_none());
        assert_eq!(client.draft, draft);
    }

    fn partial_scene_fixture() -> App {
        use babylon_persistence::runtime_session::{
            OrganizerBodyDisclosure, OrganizerBodyPart, OrganizerBodySource, OrganizerPosition,
        };
        let (_, _, _, mut snapshot) = super::super::tests::status_fixture();
        let (mut client, mut session) = super::super::tests::ready();
        session.content_hash = Some(crate::dossier::hex_bytes([4; 32]));
        session.world_hash = Some(crate::dossier::hex_bytes([5; 32]));
        snapshot.body_scope.source = Some(OrganizerBodySource::Committed {
            tick_content_hash: [4; 32],
            world_hash: [5; 32],
        });
        snapshot.view.positions.push(OrganizerPosition {
            contributor_id: 90,
            label: "Disclosed contributor".into(),
            promised_hours: 2,
            concern: String::new(),
            objection: String::new(),
            review_condition: String::new(),
        });
        snapshot.body = OrganizerBodyDisclosure::Partial(OrganizerBodyPart {
            runtime_hyperedge_id: 7,
            scenario: "economy/national-world".into(),
            local_name: "organizer-participant-body-90".into(),
            contributors: vec![90],
            evidence_class: ArchiveEvidenceClass::Designed,
        });
        client.queue(&mut session, RequestKind::Status, None);
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } =
            client.outbox.take().expect("status fixture")
        else {
            panic!("status fixture")
        };
        assert!(client.status(request_id, snapshot, &mut session).is_ok());
        let (mut app, _, _) = organizer_navigation();
        app.insert_resource(client).insert_resource(session);
        app.update();
        app.update();
        app
    }

    #[test]
    fn scene_selection_and_privacy() {
        use babylon_persistence::runtime_session::OrganizerBodyDisclosure;
        let mut app = partial_scene_fixture();
        let subject = OrganizerSubject::WorkplaceCommittee(92);
        let entity = {
            let world = app.world_mut();
            let mut query = world.query::<(Entity, &ActionButton)>();
            query
                .iter(world)
                .find_map(|(entity, action)| {
                    matches!(action.0, OrganizerAction::SelectSubject(value) if value == subject)
                        .then_some(entity)
                })
                .expect("admitted subject button")
        };
        *app.world_mut()
            .get_mut::<Interaction>(entity)
            .expect("pressable") = Interaction::Hovered;
        app.update();
        assert_eq!(
            app.world().resource::<OrganizerClient>().selected_subject,
            None
        );
        let context = app.world().resource::<ObserverSession>().context();
        app.world_mut().trigger(ObserverKeyboardActivate {
            entity,
            context: Some(context),
        });
        app.update();
        assert_eq!(
            app.world().resource::<OrganizerClient>().selected_subject,
            Some(subject)
        );
        assert_eq!(
            app.world().resource::<SelectedCounty>().0,
            app.world().resource::<CountyAtlas>().index_of_fips("26163")
        );
        app.world_mut().write_message(OrganizerAction::SetSceneMode(
            OrganizerSceneMode::Relationships,
        ));
        app.update();
        app.update();
        assert_relationship_geometry(&mut app);
        let before = relationship_targets(&mut app);
        // Synthetic bypass of producer admission: the actual projector removes hidden
        // incidence. This tests that even a perturbed disclosure cannot move targets.
        if let Some(OrganizerBodyDisclosure::Partial(part)) =
            &mut app.world_mut().resource_mut::<OrganizerClient>().body
        {
            part.runtime_hyperedge_id = 999;
            part.contributors.push(999);
        } else {
            panic!("partial body fixture");
        }
        app.update();
        assert_eq!(relationship_targets(&mut app), before);
        inspect_period(&mut app, 2);
        app.update();
        app.update();
        assert_eq!(
            app.world().resource::<OrganizerClient>().selected_subject,
            Some(subject)
        );
        let world = app.world_mut();
        let mut details = world.query_filtered::<&Text, With<SceneDetail>>();
        assert!(details
            .iter(world)
            .all(|text| text.0.contains("unavailable")));
        let mut actions = world.query::<&ActionButton>();
        assert!(!actions
            .iter(world)
            .any(|action| matches!(action.0, OrganizerAction::SelectSubject(_))));
        // Returning live invalidates this admitted context until a fresh status.
        // A subsequent held period must still get its own history controls.
        app.world_mut()
            .resource_mut::<ObserverSession>()
            .inspect_tick(3);
        app.update();
        app.world_mut()
            .resource_mut::<ObserverSession>()
            .inspect_tick(2);
        app.update();
        let world = app.world_mut();
        let mut text = world.query::<&Text>();
        assert!(text
            .iter(world)
            .any(|value| value.0 == "Historical evidence"));
    }

    fn assert_relationship_geometry(app: &mut App) {
        {
            let world = app.world_mut();
            let mut bodies = world.query_filtered::<(Entity, &Node), With<RelationBody>>();
            let (body, outline) = bodies.single(world).expect("partial body boundary");
            assert_eq!(outline.border_radius, BorderRadius::all(px(45)));
            let mut nodes = world.query::<(&RelationSubject, &ChildOf)>();
            let inside = nodes
                .iter(world)
                .filter(|(_, parent)| parent.parent() == body)
                .map(|(subject, _)| subject.0)
                .collect::<Vec<_>>();
            assert_eq!(
                inside,
                vec![
                    OrganizerSubject::Collective(90),
                    OrganizerSubject::Contributor(90)
                ]
            );
        }
        let (stage, endpoints, edge) = {
            let world = app.world_mut();
            let mut stages = world.query_filtered::<Entity, With<RelationStage>>();
            let stage = stages.single(world).expect("relationship stage");
            let mut nodes = world.query::<(Entity, &RelationSubject)>();
            let endpoints = nodes
                .iter(world)
                .map(|(entity, subject)| (entity, subject.0))
                .collect::<Vec<_>>();
            let mut edges = world.query::<(Entity, &RelationEdge)>();
            let (edge, relation) = edges
                .iter(world)
                .next()
                .expect("disclosed relationship line");
            (stage, (endpoints, relation.from, relation.to), edge)
        };
        app.world_mut().entity_mut(stage).insert((
            ComputedNode {
                size: Vec2::new(600.0, 400.0),
                inverse_scale_factor: 1.0,
                ..default()
            },
            UiGlobalTransform::default(),
        ));
        for (entity, subject) in endpoints.0 {
            let position = if subject == endpoints.1 {
                Vec2::new(-150.0, 0.0)
            } else if subject == endpoints.2 {
                Vec2::new(150.0, 0.0)
            } else {
                Vec2::ZERO
            };
            app.world_mut().entity_mut(entity).insert((
                UiGlobalTransform::from_translation(position),
                ComputedNode {
                    size: Vec2::new(100.0, 50.0),
                    inverse_scale_factor: 1.0,
                    ..default()
                },
            ));
        }
        app.update();
        assert_eq!(
            app.world().get::<Node>(edge).expect("line geometry").width,
            px(200),
            "the connector must stop at each subject boundary"
        );
        let initial_top = app.world().get::<Node>(edge).expect("line geometry").top;
        let Val::Px(initial_top) = initial_top else {
            panic!("projected endpoint top")
        };
        app.world_mut()
            .get_mut::<ComputedNode>(stage)
            .expect("stage geometry")
            .scroll_position = Vec2::new(0.0, 40.0);
        app.update();
        assert_eq!(
            app.world().get::<Node>(edge).expect("line geometry").top,
            px(initial_top + 40.0),
            "the connector stays attached when its stage scrolls"
        );
    }

    fn relationship_targets(app: &mut App) -> Vec<(OrganizerSubject, Node, [f32; 6])> {
        let world = app.world_mut();
        let mut targets = world.query::<(&RelationSubject, &Node, &UiGlobalTransform)>();
        let mut result = targets
            .iter(world)
            .map(|(subject, node, transform)| {
                (subject.0, node.clone(), transform.affine().to_cols_array())
            })
            .collect::<Vec<_>>();
        result.sort_by_key(|(subject, _, _)| *subject);
        result
    }

    fn in_scene_content(world: &World, entity: Entity) -> bool {
        let mut current = entity;
        while let Some(parent) = world.get::<ChildOf>(current) {
            current = parent.parent();
            if world.get::<SceneContent>(current).is_some() {
                return true;
            }
        }
        false
    }

    #[test]
    fn scene_review_history_fallback_activates_by_pointer_and_keyboard() {
        for initial in [
            OrganizerInspector::Relationships,
            OrganizerInspector::Direction,
        ] {
            for (label, target) in [
                ("Historical evidence", OrganizerInspector::Evidence),
                ("Practice history", OrganizerInspector::Receipts),
                ("Personal notes", OrganizerInspector::Notes),
            ] {
                for keyboard in [false, true] {
                    let (mut app, original_focus, draft) = organizer_navigation();
                    {
                        let mut session = app.world_mut().resource_mut::<ObserverSession>();
                        session.connected_fixture();
                        session.ready(3, None);
                        let context = session.context();
                        assert!(session.installed(&context));
                    }
                    {
                        let mut client = app.world_mut().resource_mut::<OrganizerClient>();
                        client.view.as_mut().expect("view").period = 3;
                        client.inspector = initial;
                        client.return_focus = Some(original_focus);
                        client.selected_subject = Some(OrganizerSubject::Collective(90));
                        client.scene_mode = OrganizerSceneMode::Relationships;
                    }
                    app.init_resource::<ObserverFocusPolicy>();
                    crate::observer_ui::install_shell_focus_policy(&mut app);
                    app.update();
                    assert!(app
                        .world()
                        .resource::<ObserverFocusPolicy>()
                        .modal
                        .is_some());
                    inspect_period(&mut app, 2);
                    app.update();
                    app.update();
                    assert_eq!(
                        app.world().resource::<OrganizerClient>().inspector,
                        OrganizerInspector::Closed
                    );
                    assert!(app
                        .world()
                        .resource::<ObserverFocusPolicy>()
                        .modal
                        .is_none());
                    assert_eq!(
                        app.world().resource::<InputFocus>().get(),
                        Some(original_focus)
                    );
                    let entity = {
                        let world = app.world_mut();
                        let mut buttons = world.query::<(Entity, &ActionButton, &Children)>();
                        buttons
                            .iter(world)
                            .find_map(|(entity, _, children)| {
                                (in_scene_content(world, entity)
                                    && children.iter().any(|child| {
                                        world.get::<Text>(child).is_some_and(|text| text.0 == label)
                                    }))
                                .then_some(entity)
                            })
                            .expect("visible historical control")
                    };
                    assert!(
                        app.world()
                            .get::<ObserverFocusTarget>(entity)
                            .expect("focus target")
                            .available,
                        "{initial:?}, {target:?}, keyboard={keyboard}"
                    );
                    app.world_mut()
                        .resource_mut::<InputFocus>()
                        .set(entity, FocusCause::Navigated);
                    if keyboard {
                        let context = app.world().resource::<ObserverSession>().context();
                        app.world_mut().trigger(ObserverKeyboardActivate {
                            entity,
                            context: Some(context),
                        });
                    } else {
                        *app.world_mut()
                            .get_mut::<Interaction>(entity)
                            .expect("pointer target") = Interaction::Pressed;
                    }
                    app.update();
                    let client = app.world().resource::<OrganizerClient>();
                    assert_eq!(client.inspector, target);
                    assert_eq!(client.draft.as_ref(), Some(&draft));
                    assert_eq!(
                        client.selected_subject,
                        Some(OrganizerSubject::Collective(90))
                    );
                    assert_eq!(client.scene_mode, OrganizerSceneMode::Relationships);
                    assert_eq!(client.return_focus, Some(entity));
                    assert!(client.outbox.is_none());
                    assert!(!confirmation_enabled(&app));
                }
            }
        }
    }

    fn scene_text(app: &mut App) -> String {
        let world = app.world_mut();
        let mut texts = world.query::<(Entity, &Text)>();
        texts
            .iter(world)
            .filter(|(entity, _)| in_scene_content(world, *entity))
            .map(|(_, text)| text.0.as_str())
            .collect::<Vec<_>>()
            .join("\n")
    }

    #[test]
    fn scene_repaints_pending_refusal_history_and_authenticated_bodies() {
        let (mut client, mut session, request, _snapshot) = super::super::tests::status_fixture();
        client.scene_mode = OrganizerSceneMode::Relationships;
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
            panic!("status fixture")
        };
        let (mut app, _, _) = organizer_navigation();
        app.insert_resource(client).insert_resource(session);
        app.update();
        assert!(scene_text(&mut app).contains("Loading organizer scene"));
        app.world_mut()
            .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                let mut session = world.resource_mut::<ObserverSession>();
                assert!(client.refused(Some(request_id), "Status refused".into(), &mut session));
            });
        app.update();
        assert!(scene_text(&mut app).contains("Status refused"));
        let (new_client, new_session, request, snapshot) = super::super::tests::status_fixture();
        client = new_client;
        client.scene_mode = OrganizerSceneMode::Relationships;
        session = new_session;
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
            panic!("status fixture")
        };
        assert!(client.status(request_id, snapshot, &mut session).is_ok());
        app.insert_resource(client).insert_resource(session);
        app.update();
        assert!(scene_text(&mut app).contains("Collective structure unknown"));
        inspect_period(&mut app, 2);
        app.update();
        assert!(scene_text(&mut app).contains("Historical organizer scene is unavailable"));
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.durable_tick = 4;
            session.viewed_tick = 4;
        }
        app.world_mut().resource_mut::<OrganizerClient>().status_due = true;
        app.update();
        assert!(scene_text(&mut app).contains("Loading organizer scene"));
        let mut partial = partial_scene_fixture();
        partial
            .world_mut()
            .write_message(OrganizerAction::SetSceneMode(
                OrganizerSceneMode::Relationships,
            ));
        partial.update();
        let client = partial
            .world_mut()
            .remove_resource::<OrganizerClient>()
            .expect("partial client");
        let session = partial
            .world_mut()
            .remove_resource::<ObserverSession>()
            .expect("partial session");
        app.insert_resource(client).insert_resource(session);
        app.update();
        let visible = scene_text(&mut app);
        assert!(visible.contains("Partial view of our collective"));
        assert!(!visible.contains("Body key"), "{visible}");
        assert!(
            !visible.contains("organizer-participant-body-90"),
            "{visible}"
        );
        app.world_mut()
            .write_message(OrganizerAction::Inspect(OrganizerInspector::Relationships));
        app.update();
        let details = painted_text(&mut app, true);
        assert!(
            details.contains("organizer-participant-body-90"),
            "{details}"
        );
    }

    #[test]
    fn relationship_map_summarizes_recent_contacts_without_losing_receipts() {
        use babylon_persistence::runtime_session::{
            OrganizerOutcome, OrganizerPartnerResponse, OrganizerReceipt,
        };
        let mut app = partial_scene_fixture();
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            let view = client.view.as_mut().expect("view");
            view.period = 3;
            for period in 1..=3 {
                view.receipts.push(OrganizerReceipt {
                    receipt_id: [u8::try_from(period).expect("fixture period fits"); 32],
                    commitment_id: Some([4; 32]),
                    actor_id: 90,
                    period,
                    choice: OrganizerChoice::Reinforce,
                    standing_work: false,
                    outcome: OrganizerOutcome::ContactCompleted,
                    hours_spent: 2,
                    partner_actor_id: Some(92),
                    partner_response: OrganizerPartnerResponse::Participated,
                    observation_ids: vec![],
                    contact_product_id: Some([5; 32]),
                    time_use: vec![],
                });
            }
            view.total_receipt_count = 3;
        }
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.durable_tick = 3;
            session.viewed_tick = 3;
        }
        app.world_mut().write_message(OrganizerAction::SetSceneMode(
            OrganizerSceneMode::Relationships,
        ));
        app.update();
        let visible = scene_text(&mut app);
        assert!(
            visible.contains("3 earned contacts in recent receipts"),
            "{visible}"
        );
        assert!(!visible.contains("Earned contact · period 1"), "{visible}");
        app.world_mut()
            .write_message(OrganizerAction::Inspect(OrganizerInspector::Receipts));
        app.update();
        let history = painted_text(&mut app, true);
        for period in 1..=3 {
            assert!(history.contains(&format!("PERIOD {period}")), "{history}");
        }
    }

    #[test]
    fn historical_status_refusal_is_scoped_and_cleared_on_recovery() {
        let (mut client, mut session, request, snapshot) = super::super::tests::status_fixture();
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
            panic!("status fixture")
        };
        client
            .status(request_id, snapshot.clone(), &mut session)
            .expect("live status");
        let (mut app, _, _) = organizer_navigation();
        app.insert_resource(client).insert_resource(session);
        inspect_period(&mut app, 2);
        app.world_mut().resource_mut::<OrganizerClient>().message = "Draft saved".into();
        app.update();
        assert!(scene_text(&mut app).contains("Historical organizer scene is unavailable"));
        assert!(!scene_text(&mut app).contains("Draft saved"));
        let queue_status = |app: &mut App| {
            app.world_mut()
                .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                    let mut session = world.resource_mut::<ObserverSession>();
                    client.queue(&mut session, RequestKind::Status, None);
                    client.pending.as_ref().expect("status pending").id
                })
        };
        let pending = queue_status(&mut app);
        app.update();
        assert!(scene_text(&mut app).contains("Loading organizer scene"));
        app.world_mut()
            .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                let mut session = world.resource_mut::<ObserverSession>();
                assert!(client.refused(
                    Some(pending),
                    "Historical status refused".into(),
                    &mut session
                ));
            });
        app.update();
        assert!(scene_text(&mut app).contains("Historical status refused"));
        assert!(!scene_text(&mut app).contains("Historical organizer scene is unavailable"));
        assert!(!app.world().resource::<OrganizerClient>().status_due);
        assert!(app.world().resource::<OrganizerClient>().pending.is_none());
        inspect_period(&mut app, 1);
        app.update();
        assert!(scene_text(&mut app).contains("Historical organizer scene is unavailable"));
        assert!(!scene_text(&mut app).contains("Historical status refused"));
        inspect_period(&mut app, 2);
        let pending = queue_status(&mut app);
        app.update();
        assert!(scene_text(&mut app).contains("Loading organizer scene"));
        app.world_mut()
            .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                let mut session = world.resource_mut::<ObserverSession>();
                client
                    .status(pending, snapshot, &mut session)
                    .expect("recovered status");
            });
        app.update();
        assert!(scene_text(&mut app).contains("Historical organizer scene is unavailable"));
        assert!(!scene_text(&mut app).contains("Historical status refused"));
        inspect_period(&mut app, 3);
        app.world_mut().resource_mut::<OrganizerClient>().message = "Draft saved".into();
        app.update();
        assert!(scene_text(&mut app).contains("Organizer scene is unavailable"));
        assert!(!scene_text(&mut app).contains("Draft saved"));
    }

    #[test]
    fn refresh_marks_the_retained_scene_without_replacing_focused_subject() {
        let mut app = partial_scene_fixture();
        let subject = {
            let world = app.world_mut();
            let mut buttons = world.query::<(Entity, &ActionButton)>();
            buttons
                .iter(world)
                .find_map(|(entity, action)| {
                    matches!(action.0, OrganizerAction::SelectSubject(_)).then_some(entity)
                })
                .expect("scene subject")
        };
        app.world_mut()
            .resource_mut::<InputFocus>()
            .set(subject, FocusCause::Navigated);
        app.world_mut().resource_mut::<OrganizerClient>().status_due = true;
        app.update();
        let detail = |app: &mut App| {
            let world = app.world_mut();
            let mut details = world.query_filtered::<&Text, With<SceneDetail>>();
            details.single(world).expect("scene detail").0.clone()
        };
        assert!(detail(&mut app).contains("Refreshing organizer scene"));
        assert!(app.world().get_entity(subject).is_ok());
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(subject));
        app.world_mut().resource_mut::<OrganizerClient>().status_due = false;
        app.update();
        assert!(!detail(&mut app).contains("Refreshing organizer scene"));
        assert!(app.world().get_entity(subject).is_ok());
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(subject));
    }

    #[test]
    fn retained_scene_shows_refused_refresh_and_recovers_without_losing_focus() {
        let mut app = partial_scene_fixture();
        let (subject, snapshot) = {
            let world = app.world_mut();
            let mut buttons = world.query::<(Entity, &ActionButton)>();
            let subject = buttons
                .iter(world)
                .find_map(|(entity, action)| {
                    matches!(action.0, OrganizerAction::SelectSubject(_)).then_some(entity)
                })
                .expect("scene subject");
            let client = world.resource::<OrganizerClient>();
            let (_, _, _, mut snapshot) = super::super::tests::status_fixture();
            snapshot.view = client.view.clone().expect("admitted view");
            snapshot.body = client.body.clone().expect("admitted body");
            snapshot.body_scope = client.body_scope.clone().expect("admitted scope");
            (subject, snapshot)
        };
        app.world_mut()
            .resource_mut::<InputFocus>()
            .set(subject, FocusCause::Navigated);
        let queue_status = |app: &mut App| {
            app.world_mut()
                .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                    let mut session = world.resource_mut::<ObserverSession>();
                    client.queue(&mut session, RequestKind::Status, None);
                    client.pending.as_ref().expect("status pending").id
                })
        };
        let detail = |app: &mut App| {
            let world = app.world_mut();
            let mut details = world.query_filtered::<&Text, With<SceneDetail>>();
            details.single(world).expect("scene detail").0.clone()
        };
        let pending = queue_status(&mut app);
        app.update();
        assert!(detail(&mut app).contains("Refreshing organizer scene"));
        app.world_mut()
            .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                let mut session = world.resource_mut::<ObserverSession>();
                assert!(client.refused(Some(pending), "Refresh refused".into(), &mut session));
            });
        app.update();
        assert!(detail(&mut app).contains("Refresh refused"));
        assert!(app.world().get_entity(subject).is_ok());
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(subject));
        let pending = queue_status(&mut app);
        app.update();
        assert!(detail(&mut app).contains("Refreshing organizer scene"));
        app.world_mut()
            .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                let mut session = world.resource_mut::<ObserverSession>();
                client
                    .status(pending, snapshot, &mut session)
                    .expect("recovered status");
            });
        app.update();
        assert!(!detail(&mut app).contains("Refresh refused"));
        assert!(!detail(&mut app).contains("Refreshing organizer scene"));
        assert!(app.world().get_entity(subject).is_ok());
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(subject));
    }

    #[test]
    fn historical_inspectors_hide_current_totals_pending_and_later_reports() {
        use babylon_persistence::runtime_session::{
            OrganizerAidKind, OrganizerAidPending, OrganizerOutcome, OrganizerPartnerResponse,
            OrganizerReceipt,
        };
        let (mut app, _) = reference_fixture();
        press_named(&mut app, "Keep report in draft");
        press_named(&mut app, "Return to decision [Esc]");
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.pending_aid.push(OrganizerAidPending {
                allocation: babylon_persistence::runtime_session::OrganizerAllocation::Aid {
                    food_quantity: 4,
                    cash_micros: 18,
                },
                dispatch_support: crate::organizer::tests::aid_dispatch_fixture(),
                response: None,
                lost_quantity: 0,

                kind: OrganizerAidKind::Remote,
                original_commitment_id: [11; 32],
                material_commitment_id: [12; 32],
                mandate_id: [13; 32],
                admitted_period: 1,
                dispatch_period: 3,
                good_id: [14; 32],
                unit_id: [15; 32],
            });
            let view = client.view.as_mut().expect("view");
            view.total_observation_count = 901;
            view.total_receipt_count = 902;
            view.receipts.push(OrganizerReceipt {
                receipt_id: [1; 32],
                commitment_id: None,
                actor_id: view.actor_id,
                period: 3,
                choice: OrganizerChoice::Hold,
                standing_work: true,
                outcome: OrganizerOutcome::EvidenceWithheld,
                hours_spent: 99,
                partner_actor_id: None,
                partner_response: OrganizerPartnerResponse::NotRequested,
                observation_ids: vec![],
                contact_product_id: None,
                time_use: vec![],
            });
        }
        inspect_period(&mut app, 1);
        app.update();
        press_named(&mut app, "Historical evidence");
        let reports = painted_text(&mut app, true);
        assert!(!reports.contains("901"));
        assert!(!reports.contains("777 kg"));
        assert!(reports.contains("as-of total is unavailable"));
        press_named(&mut app, "Return to decision [Esc]");
        press_named(&mut app, "Personal notes");
        press_named(&mut app, "Open saved references");
        let saved = painted_text(&mut app, true);
        assert!(saved.contains("CURRENT PERSONAL DRAFT"));
        assert!(!saved.contains("777 kg"));
        press_named(&mut app, "Return to decision [Esc]");
        press_named(&mut app, "Practice history");
        let receipts = painted_text(&mut app, true);
        assert!(!receipts.contains("902"));
        assert!(!receipts.contains("99 organizer-hours"));
        assert!(!receipts.contains("Pending remote solidarity"));
        assert!(!receipts.contains("No practice has completed"));
        assert!(receipts.contains("as-of total is unavailable"));
        assert!(receipts.contains("Our practice Archive"));
        press_named(&mut app, "Return to decision [Esc]");
        inspect_period(&mut app, 2);
        app.update();
        press_named(&mut app, "Historical evidence");
        let earlier_report = painted_text(&mut app, true);
        assert!(earlier_report.contains("777 kg"));
        assert!(earlier_report.contains("NOT IN CURRENT PERSONAL DRAFT"));
    }

    #[test]
    fn ordinary_and_relationship_controls_show_non_color_state_without_activation() {
        let mut app = partial_scene_fixture();
        app.world_mut().write_message(OrganizerAction::SetSceneMode(
            OrganizerSceneMode::Relationships,
        ));
        app.update();
        app.update();
        let (relation, disabled, choice) = {
            let world = app.world_mut();
            let mut query = world.query::<(Entity, &ActionButton, Option<&RelationSubject>)>();
            let relation = query
                .iter(world)
                .find_map(|(entity, _, relation)| relation.map(|_| entity))
                .expect("relation");
            let disabled = query
                .iter(world)
                .find_map(|(entity, button, _)| {
                    matches!(button.0, OrganizerAction::Confirm).then_some(entity)
                })
                .expect("confirm");
            let choice = query
                .iter(world)
                .find_map(|(entity, button, _)| {
                    matches!(
                        button.0,
                        OrganizerAction::Choose(OrganizerChoice::Reinforce)
                    )
                    .then_some(entity)
                })
                .expect("choice");
            (relation, disabled, choice)
        };
        let caption = |app: &App, entity| {
            app.world()
                .get::<Children>(entity)
                .expect("caption")
                .iter()
                .filter_map(|child| app.world().get::<Text>(child).map(|text| text.0.as_str()))
                .collect::<Vec<_>>()
                .join(" ")
        };
        assert!(caption(&app, disabled).contains("UNAVAILABLE"));
        let before = app.world().resource::<OrganizerClient>().selected_subject;
        *app.world_mut()
            .get_mut::<Interaction>(relation)
            .expect("interaction") = Interaction::Hovered;
        app.update();
        assert!(caption(&app, relation).contains("HOVER"));
        assert_eq!(
            app.world().resource::<OrganizerClient>().selected_subject,
            before
        );
        let chosen = app.world().resource::<OrganizerClient>().choice();
        *app.world_mut()
            .get_mut::<Interaction>(choice)
            .expect("choice interaction") = Interaction::Hovered;
        app.update();
        assert!(caption(&app, choice).contains("HOVER"));
        assert_eq!(app.world().resource::<OrganizerClient>().choice(), chosen);
        app.world_mut()
            .resource_mut::<InputFocus>()
            .set(relation, FocusCause::Navigated);
        app.update();
        assert_eq!(
            app.world().resource::<OrganizerClient>().selected_subject,
            before
        );
        *app.world_mut()
            .get_mut::<Interaction>(disabled)
            .expect("interaction") = Interaction::Pressed;
        app.update();
        let context = app.world().resource::<ObserverSession>().context();
        app.world_mut().trigger(ObserverKeyboardActivate {
            entity: disabled,
            context: Some(context),
        });
        app.update();
        assert!(app.world().resource::<OrganizerClient>().outbox.is_none());
        assert!(app
            .world()
            .resource::<OrganizerClient>()
            .commitment
            .is_none());
    }

    #[test]
    fn scene_review_mode_selection_has_persistent_text_cue() {
        let (mut client, mut session, request, snapshot) = super::super::tests::status_fixture();
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
            panic!("status fixture")
        };
        assert!(client.status(request_id, snapshot, &mut session).is_ok());
        let (mut app, _, _) = organizer_navigation();
        app.insert_resource(client).insert_resource(session);
        app.update();
        app.update();
        let (places, relationships) = {
            let world = app.world_mut();
            let mut buttons = world.query::<(Entity, &ActionButton)>();
            let ids = buttons
                .iter(world)
                .filter_map(|(entity, button)| match button.0 {
                    OrganizerAction::SetSceneMode(mode) => Some((mode, entity)),
                    _ => None,
                })
                .collect::<Vec<_>>();
            (
                ids.iter()
                    .find(|(mode, _)| *mode == OrganizerSceneMode::Places)
                    .expect("places")
                    .1,
                ids.iter()
                    .find(|(mode, _)| *mode == OrganizerSceneMode::Relationships)
                    .expect("relationships")
                    .1,
            )
        };
        let caption = |app: &App, entity| {
            let world = app.world();
            world
                .get::<Children>(entity)
                .expect("mode caption")
                .iter()
                .filter_map(|child| world.get::<Text>(child).map(|text| text.0.as_str()))
                .collect::<Vec<_>>()
                .join(" ")
        };
        assert!(caption(&app, places).contains("SELECTED"));
        assert!(!caption(&app, relationships).contains("SELECTED"));
        *app.world_mut()
            .get_mut::<Interaction>(relationships)
            .expect("hover") = Interaction::Hovered;
        app.update();
        assert!(caption(&app, places).contains("SELECTED"));
        assert!(!caption(&app, relationships).contains("SELECTED"));
        let context = app.world().resource::<ObserverSession>().context();
        app.world_mut().trigger(ObserverKeyboardActivate {
            entity: relationships,
            context: Some(context),
        });
        app.update();
        assert_eq!(
            app.world().resource::<OrganizerClient>().scene_mode,
            OrganizerSceneMode::Relationships
        );
        assert!(!caption(&app, places).contains("SELECTED"));
        assert!(caption(&app, relationships).contains("SELECTED"));
    }

    #[test]
    fn organizer_text_is_measured_at_readable_width_with_the_real_font() {
        let size = crate::test_support::measure_ui_text(text(
            "The organization has time to investigate workplace conditions.",
            16.0,
            Color::WHITE,
        ));
        assert!(
            size.x > 100.0 && size.y < 100.0,
            "actual text layout: {size:?}"
        );
    }

    #[derive(Resource, Default)]
    struct ArchiveRequests(Vec<OrganizerArchiveTarget>);

    pub(super) fn measured_board(viewport: UVec2, scale: f32, larger: bool, long: bool) -> App {
        let (mut app, body_font) = crate::test_support::ui_text_app();
        let display = Font::from_bytes(
            include_bytes!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../../assets/fonts/BarlowCondensed-SemiBold.ttf"
            ))
            .to_vec(),
        );
        let display_font = app.world_mut().resource_mut::<Assets<Font>>().add(display);
        let (mut client, mut session, request, snapshot) = super::super::tests::status_fixture();
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
            panic!("status fixture");
        };
        client
            .status(request_id, snapshot, &mut session)
            .expect("admitted scene");
        if let Some(view) = client.view.as_mut() {
            let national: OrganizerSnapshot = serde_json::from_str(include_str!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../babylon-persistence/tests/fixtures/national_organizer_opening_v19.json"
            )))
            .expect("captured national opening");
            if viewport.x > 1400 {
                view.contact_hours = national.view.contact_hours;
                view.available_hours = national.view.available_hours;
            }
            view.agreements = national.view.agreements.clone();
            for agreement in &mut view.agreements {
                agreement.actor_id = view.actor_id;
                agreement.partner_actor_id =
                    if agreement.partner_actor_id == national.view.workplace_partner_id {
                        view.workplace_partner_id
                    } else {
                        view.neighborhood_partner_id
                    };
            }
            view.organization_label = national.view.organization_label;
            view.neighborhood_partner_label = national.view.neighborhood_partner_label;
            view.workplace_label = national.view.workplace_label;
            view.workplace_partner_label = national.view.workplace_partner_label;
            view.positions = national.view.positions;
            if long {
                view.workplace_label = "Wayne County repair and maintenance workplace committee serving the eastern industrial district".into();
            }
        }
        {
            let world = app.world_mut();
            let mut cameras = world.query::<&mut Camera>();
            let mut camera = cameras.single_mut(world).expect("UI camera");
            camera
                .computed
                .target_info
                .as_mut()
                .expect("target")
                .physical_size = viewport;
            camera.viewport.as_mut().expect("viewport").physical_size = viewport;
        }
        app.insert_resource(UiScale(scale))
            .insert_resource(client)
            .insert_resource(session)
            .insert_resource(ObserverUiState {
                menu_open: false,
                splash_visible: false,
                larger_interface: larger,
                ..default()
            })
            .insert_resource(PrimaryView::Organizer)
            .init_resource::<InputFocus>()
            .add_systems(Startup, spawn)
            .init_resource::<RenderedScene>()
            .add_systems(PreUpdate, sync_targets)
            .add_systems(
                Update,
                (paint, render_scene, paint_button_markers).in_set(ObserverSet::Paint),
            )
            .add_systems(PostUpdate, paint_scroll_hints.after(UiSystems::Layout));
        board::install(&mut app);
        amount_editor::install(&mut app);
        report_view::install(&mut app);
        app.finish();
        app.cleanup();
        app.update();
        {
            let world = app.world_mut();
            let mut fonts = world.query::<(&ObserverFontRole, &mut TextFont)>();
            for (role, mut font) in fonts.iter_mut(world) {
                font.font = if matches!(role, ObserverFontRole::Display) {
                    display_font.clone()
                } else {
                    body_font.clone()
                }
                .into();
            }
        }
        for _ in 0..4 {
            app.update();
        }
        app
    }

    pub(super) fn workspace_rect(app: &App, entity: Entity) -> Rect {
        let world = app.world();
        Rect::from_center_size(
            world
                .get::<UiGlobalTransform>(entity)
                .expect("transform")
                .translation,
            world.get::<ComputedNode>(entity).expect("layout").size(),
        )
    }

    fn install_relationship_art(app: &mut App) {
        use bevy::asset::{AssetApp, RenderAssetUsages};
        use bevy::image::{CompressedImageFormats, ImageSampler, ImageType};
        use bevy::ui::widget;
        app.init_asset::<Image>()
            .init_asset::<TextureAtlasLayout>()
            .add_systems(
                PostUpdate,
                (
                    widget::update_image_content_size_system.before(bevy::ui::ui_layout_system),
                    widget::text_system.after(bevy::ui::ui_layout_system),
                ),
            );
        let illustrations: [&[u8]; 3] = [
            include_bytes!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../../assets/visual/group-wayne-collective.webp"
            )),
            include_bytes!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../../assets/visual/group-workplace-committee.webp"
            )),
            include_bytes!(concat!(
                env!("CARGO_MANIFEST_DIR"),
                "/../../../assets/visual/group-neighborhood-contact.webp"
            )),
        ];
        let images = illustrations.map(|bytes| {
            let image = Image::from_buffer(
                bytes,
                ImageType::Extension("webp"),
                CompressedImageFormats::NONE,
                true,
                ImageSampler::linear(),
                RenderAssetUsages::default(),
            )
            .expect("the shipped group illustration decodes");
            app.world_mut().resource_mut::<Assets<Image>>().add(image)
        });
        let portraits = {
            let world = app.world_mut();
            world
                .query::<(Entity, &ChildOf)>()
                .iter(world)
                .filter_map(|(entity, parent)| {
                    world.get::<ImageNode>(entity)?;
                    let subject = world.get::<RelationSubject>(parent.parent())?;
                    let index = match subject.0 {
                        OrganizerSubject::Collective(_) => 0,
                        OrganizerSubject::WorkplaceCommittee(_) => 1,
                        OrganizerSubject::NeighborhoodGroup(_) => 2,
                        OrganizerSubject::AidPartner(_)
                        | OrganizerSubject::Contributor(_)
                        | OrganizerSubject::Workplace(_) => return None,
                    };
                    Some((entity, images[index].clone()))
                })
                .collect::<Vec<_>>()
        };
        assert_eq!(
            portraits.len(),
            3,
            "all admitted group illustrations participate in layout"
        );
        for (entity, image) in portraits {
            app.world_mut()
                .entity_mut(entity)
                .insert(ImageNode::new(image));
        }
    }

    fn measured_relationship_board(viewport: UVec2, scale: f32) -> App {
        let mut app = measured_board(viewport, scale, false, false);
        let body_font = {
            let world = app.world_mut();
            world
                .query::<(&TextPart, &TextFont)>()
                .iter(world)
                .find_map(|(part, font)| {
                    matches!(part, TextPart::Situation).then_some(font.font.clone())
                })
                .expect("the workspace has an embedded reading face")
        };
        app.world_mut().resource_mut::<OrganizerClient>().scene_mode =
            OrganizerSceneMode::Relationships;
        app.update();
        app.update();
        install_relationship_art(&mut app);
        {
            let world = app.world_mut();
            for (role, mut font) in world
                .query::<(&ObserverFontRole, &mut TextFont)>()
                .iter_mut(world)
            {
                if matches!(role, ObserverFontRole::Body) {
                    font.font = body_font.clone();
                }
            }
        }
        for _ in 0..6 {
            app.update();
        }
        app
    }

    pub(super) fn glyph_rects(app: &App, entity: Entity) -> Vec<Rect> {
        let world = app.world();
        let node = world
            .get::<ComputedNode>(entity)
            .expect("measured text node");
        let transform = world
            .get::<UiGlobalTransform>(entity)
            .expect("text transform")
            .affine();
        let text = world
            .get::<TextLayoutInfo>(entity)
            .expect("resolved native glyphs");
        text.glyphs
            .iter()
            .filter(|glyph| glyph.atlas_info.rect.size().min_element() > 0.0)
            .map(|glyph| {
                let local = node.content_box().min + glyph.position;
                let half = glyph.atlas_info.rect.size() * 0.5;
                Rect::from_corners(
                    transform.transform_point2(local - half),
                    transform.transform_point2(local + half),
                )
            })
            .collect()
    }

    pub(super) fn assert_glyphs_in(app: &App, entity: Entity, bounds: Rect) {
        let glyphs = glyph_rects(app, entity);
        assert!(
            !glyphs.is_empty(),
            "projected text has no rendered glyphs: {:?}",
            app.world().get::<Text>(entity)
        );
        let outside = glyphs.iter().find(|glyph| {
            (glyph.intersect(bounds).size() - glyph.size())
                .abs()
                .max_element()
                > 1.1
        });
        assert!(outside.is_none(), "actual glyph must fit its clipping boundary: {:?}; node {:?}; bounds {bounds:?}; outside {outside:?}",
            app.world().get::<Text>(entity), workspace_rect(app, entity));
    }

    fn relationship_readings(app: &mut App) -> (Entity, Vec<Entity>) {
        let scene = app
            .world()
            .resource::<OrganizerClient>()
            .scene_for(app.world().resource::<ObserverSession>())
            .expect("actual admitted scene projection");
        let (stage, texts, captions) = {
            let world = app.world_mut();
            let stage = world
                .query_filtered::<Entity, With<RelationStage>>()
                .single(world)
                .expect("one relationship reading region");
            let captions = world
                .query::<(Entity, &RelationSubject, &Children)>()
                .iter(world)
                .map(|(entity, subject, children)| {
                    (entity, subject.0, children.iter().collect::<Vec<_>>())
                })
                .collect::<Vec<_>>();
            let texts = world
                .query::<(Entity, &Text)>()
                .iter(world)
                .filter_map(|(entity, text)| {
                    let mut ancestor = entity;
                    while let Some(parent) = world.get::<ChildOf>(ancestor) {
                        ancestor = parent.parent();
                        if ancestor == stage {
                            return (!text.0.is_empty()).then_some(entity);
                        }
                    }
                    None
                })
                .collect::<Vec<_>>();
            (stage, texts, captions)
        };
        assert!(
            !texts.is_empty(),
            "admitted relationship captions and typed facts exist"
        );
        assert_eq!(
            captions.len(),
            scene.nodes.len(),
            "every admitted subject stays represented"
        );
        for (card, subject, children) in captions {
            let expected = scene
                .nodes
                .iter()
                .find(|node| node.subject == subject)
                .expect("typed disclosed subject")
                .caption();
            let caption = children
                .into_iter()
                .find(|child| {
                    app.world()
                        .get::<Text>(*child)
                        .is_some_and(|text| text.0 == expected)
                })
                .expect("later painting must preserve the actual admitted caption");
            assert_glyphs_in(app, caption, workspace_rect(app, caption));
            assert_glyphs_in(app, caption, workspace_rect(app, card));
        }
        (stage, texts)
    }

    fn assert_relationship_reading_scrolls(app: &mut App, stage: Entity, texts: Vec<Entity>) {
        for entity in texts {
            let rect = workspace_rect(app, entity);
            let bounds = workspace_rect(app, stage);
            let computed = app
                .world()
                .get::<ComputedNode>(stage)
                .expect("reading layout");
            let maximum =
                crate::observer_focus::scroll_max(computed).expect("scrollable relationships");
            let position = computed.scroll_position.y * computed.inverse_scale_factor;
            let next = (position + (rect.min.y - bounds.min.y) * computed.inverse_scale_factor)
                .clamp(0.0, maximum.y);
            app.world_mut()
                .get_mut::<ScrollPosition>(stage)
                .expect("existing reading position")
                .y = next;
            app.update();
            app.update();
            assert_glyphs_in(app, entity, workspace_rect(app, stage));
        }
    }

    #[test]
    fn native_relationship_captions_and_disclosed_facts_have_visible_glyphs() {
        for (viewport, scale) in [
            (UVec2::new(1366, 768), 1.0),
            (UVec2::new(1920, 1080), 1.0),
            (UVec2::new(1920, 1080), 1.25),
        ] {
            let mut app = measured_relationship_board(viewport, scale);
            let (stage, texts) = relationship_readings(&mut app);
            assert_relationship_reading_scrolls(&mut app, stage, texts);
        }
    }

    fn assert_in_view(app: &App, entity: Entity, limit: Rect) {
        let rect = workspace_rect(app, entity);
        assert!(
            rect.size().min_element() > 0.0,
            "{entity:?}: empty {rect:?}, text {:?}, node {:?}",
            app.world().get::<Text>(entity),
            app.world().get::<Node>(entity)
        );
        let clipped = limit.intersect(rect);
        assert!(
            (clipped.size() - rect.size()).abs().max_element() <= 1.1,
            "{entity:?}: {rect:?} clipped to {clipped:?} by {limit:?}"
        );
    }

    #[test]
    fn native_workspace_roster_labels_stay_inside_their_panel() {
        for (viewport, scale) in [
            (UVec2::new(1366, 768), 1.0),
            (UVec2::new(1920, 1080), 1.0),
            (UVec2::new(1920, 1080), 1.25),
        ] {
            let mut app = measured_board(viewport, scale, false, false);
            let subjects = {
                let world = app.world_mut();
                world
                    .query::<(Entity, &ActionButton, &Children, &ChildOf)>()
                    .iter(world)
                    .filter(|(_, action, _, _)| {
                        matches!(action.0, OrganizerAction::SelectSubject(_))
                    })
                    .map(|(entity, _, children, parent)| {
                        (entity, children.iter().collect::<Vec<_>>(), parent.parent())
                    })
                    .collect::<Vec<_>>()
            };
            assert_eq!(subjects.len(), 5, "all disclosed subjects remain reachable");
            for (button, children, list) in subjects {
                let panel = app
                    .world()
                    .get::<ChildOf>(list)
                    .expect("roster panel")
                    .parent();
                let panel_bounds = workspace_rect(&app, panel);
                assert_in_view(&app, button, panel_bounds);
                for child in children {
                    if app
                        .world()
                        .get::<Text>(child)
                        .is_some_and(|text| !text.0.is_empty())
                    {
                        assert_in_view(&app, child, workspace_rect(&app, button));
                    }
                }
            }
        }
    }

    #[test]
    fn native_workspace_dossier_attributes_each_agreement_to_its_partner() {
        let mut app = measured_board(UVec2::new(1366, 768), 1.0, false, false);
        let world = app.world_mut();
        let detail = world
            .query_filtered::<&Text, With<SceneDetail>>()
            .single(world)
            .expect("selected collective dossier");
        for partner in [
            "Wayne Workplace Committee",
            "Wayne Neighborhood Contact Group",
        ] {
            assert!(
                detail
                    .0
                    .lines()
                    .any(|line| line.contains(partner) && line.contains("Agreement · periods 0–1")),
                "each agreement must retain its disclosed partner: {}",
                detail.0
            );
        }
        assert_eq!(
            detail
                .0
                .lines()
                .filter(|line| line.contains("Agreement"))
                .count(),
            2,
            "independent agreements must remain distinguishable: {}",
            detail.0
        );
    }

    #[test]
    fn native_workspace_dossier_exposes_scrolling_and_reaches_its_last_links() {
        let mut app = measured_board(UVec2::new(1366, 768), 1.0, false, false);
        let (reading, hint) = {
            let world = app.world_mut();
            let mut hints = world.query::<(Entity, &ScrollHint, &Text)>();
            hints
                .iter(world)
                .find_map(|(entity, hint, text)| {
                    text.0.contains("More below").then_some((hint.0, entity))
                })
                .expect("the clipped dossier must show a persistent scroll cue")
        };
        let reading_bounds = workspace_rect(&app, reading);
        assert_in_view(
            &app,
            hint,
            Rect::from_corners(Vec2::ZERO, Vec2::new(1366.0, 768.0)),
        );
        assert!(
            workspace_rect(&app, hint).min.y >= reading_bounds.max.y,
            "the scroll cue must remain outside the scrolling content"
        );
        let focused_readings = {
            let world = app.world_mut();
            world
                .query::<(Entity, &ObserverFocusTarget, &TextPart)>()
                .iter(world)
                .filter(|(_, target, part)| {
                    target.available
                        && target.kind == ObserverFocusKind::Reading
                        && matches!(part, TextPart::Situation)
                })
                .map(|(entity, _, _)| entity)
                .collect::<Vec<_>>()
        };
        assert_eq!(
            focused_readings.len(),
            1,
            "the dossier has one reading target"
        );
        let maximum = crate::observer_focus::scroll_max(
            app.world()
                .get::<ComputedNode>(reading)
                .expect("reading layout"),
        )
        .expect("dossier scroll extent");
        app.world_mut()
            .get_mut::<ScrollPosition>(reading)
            .expect("dossier scroll position")
            .y = maximum.y;
        app.update();
        app.update();
        let links = {
            let world = app.world_mut();
            world
                .query::<(Entity, &Children)>()
                .iter(world)
                .filter_map(|(entity, children)| {
                    children
                        .iter()
                        .any(|child| {
                            world.get::<Text>(child).is_some_and(|text| {
                                matches!(text.0.as_str(), "Personal notes" | "Trends")
                            })
                        })
                        .then_some(entity)
                })
                .collect::<Vec<_>>()
        };
        assert_eq!(
            links.len(),
            2,
            "both final navigation controls remain present"
        );
        for link in links {
            assert_in_view(&app, link, workspace_rect(&app, reading));
        }
        assert!(
            app.world()
                .get::<Text>(hint)
                .expect("scroll cue")
                .0
                .contains("More above"),
            "cue after scrolling: {:?}; computed {:?}; requested {:?}",
            app.world().get::<Text>(hint),
            app.world().get::<ComputedNode>(reading),
            app.world().get::<ScrollPosition>(reading)
        );
    }

    fn paper_contrast(foreground: Color, background: Color) -> f32 {
        fn luminance(color: [f32; 3]) -> f32 {
            let linear = color.map(|channel| {
                if channel <= 0.04045 {
                    channel / 12.92
                } else {
                    ((channel + 0.055) / 1.055).powf(2.4)
                }
            });
            0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
        }
        let background = background.to_srgba();
        let paper = Color::srgb_u8(229, 217, 191).to_srgba();
        let background = [
            background.red * background.alpha + paper.red * (1.0 - background.alpha),
            background.green * background.alpha + paper.green * (1.0 - background.alpha),
            background.blue * background.alpha + paper.blue * (1.0 - background.alpha),
        ];
        let foreground = foreground.to_srgba();
        let text = luminance([foreground.red, foreground.green, foreground.blue]);
        let surface = luminance(background);
        (text.max(surface) + 0.05) / (text.min(surface) + 0.05)
    }

    #[test]
    fn native_workspace_paper_actions_preserve_admission_and_readable_labels() {
        let mut app = measured_board(UVec2::new(1366, 768), 1.0, false, false);
        let review = {
            let world = app.world_mut();
            world
                .query::<(Entity, &ActionButton)>()
                .iter(world)
                .find_map(|(entity, button)| {
                    (button.0 == OrganizerAction::Review).then_some(entity)
                })
                .expect("paper Review action")
        };
        for (available, interaction) in [
            (true, Interaction::None),
            (true, Interaction::Hovered),
            (true, Interaction::Pressed),
            (false, Interaction::None),
        ] {
            if !available {
                app.world_mut().resource_mut::<ObserverSession>().phase = SessionPhase::Advancing;
            }
            *app.world_mut()
                .get_mut::<Interaction>(review)
                .expect("paper action interaction") = interaction;
            app.update();
            let client = app.world().resource::<OrganizerClient>();
            let session = app.world().resource::<ObserverSession>();
            assert_eq!(enabled(OrganizerAction::Review, client, session), available);
            let unavailable = app
                .world()
                .get::<Children>(review)
                .expect("review labels")
                .iter()
                .any(|child| {
                    app.world()
                        .get::<Text>(child)
                        .is_some_and(|text| text.0.contains("UNAVAILABLE"))
                });
            assert_eq!(unavailable, !available);
            let background = app
                .world()
                .get::<BackgroundColor>(review)
                .expect("paper action surface")
                .0;
            for child in app
                .world()
                .get::<Children>(review)
                .expect("paper action labels")
                .iter()
            {
                if app
                    .world()
                    .get::<Text>(child)
                    .is_some_and(|text| !text.0.is_empty())
                {
                    let foreground = app
                        .world()
                        .get::<TextColor>(child)
                        .expect("paper action ink")
                        .0;
                    assert!(paper_contrast(foreground, background) >= 4.5,
                        "Review label contrast must remain readable; available={available}, contrast={}", paper_contrast(foreground, background));
                }
            }
        }
    }

    #[test]
    fn native_workspace_opening_dispatch_uses_its_content_height() {
        let mut app = measured_board(UVec2::new(1366, 768), 1.0, false, false);
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.viewed_tick = 0;
            session.durable_tick = 0;
        }
        app.world_mut()
            .resource_mut::<OrganizerClient>()
            .view
            .as_mut()
            .expect("admitted opening")
            .period = 0;
        app.update();
        app.update();
        let (copy, reading) = {
            let world = app.world_mut();
            world
                .query::<(Entity, &TextPart, &Text, &ChildOf)>()
                .iter(world)
                .find_map(|(entity, part, text, parent)| {
                    matches!(part, TextPart::Aftermath).then_some((
                        entity,
                        parent.parent(),
                        text.0.clone(),
                    ))
                })
                .map(|(entity, parent, text)| {
                    assert!(
                        text.contains("Opening period"),
                        "actual opening copy: {text}"
                    );
                    (entity, parent)
                })
                .expect("opening dispatch")
        };
        let panel = app
            .world()
            .get::<ChildOf>(reading)
            .expect("dispatch panel")
            .parent();
        assert!(
            workspace_rect(&app, panel).height() < 120.0,
            "opening copy should not reserve a full decision-sized panel: {:?}",
            workspace_rect(&app, panel)
        );
        assert_in_view(&app, copy, workspace_rect(&app, panel));
        let overlay = app.world().get::<Overlay>(panel);
        assert!(
            overlay.is_some(),
            "compact dispatch keeps its actual overlay input boundary"
        );
    }

    enum ReceiptOrder {
        Original,
        Reversed,
    }

    fn measured_pending_support_dispatch(
        viewport: UVec2,
        scale: f32,
        receipt_order: ReceiptOrder,
    ) -> (App, Entity) {
        use babylon_persistence::runtime_session::{
            OrganizerOutcome, OrganizerPartnerResponse, OrganizerReceipt,
        };
        let mut app = measured_board(viewport, scale, false, false);
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.viewed_tick = 1;
            session.durable_tick = 1;
        }
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            let view = client.view.as_mut().expect("admitted P1 organizer view");
            view.period = 1;
            // The native P1 dispatch has two stages of one original command,
            // zero organizer hours, and no requested partner practice.
            view.receipts = [
                OrganizerOutcome::AidAwaitingSupport,
                OrganizerOutcome::AidScheduled,
            ]
            .into_iter()
            .enumerate()
            .map(|(index, outcome)| OrganizerReceipt {
                receipt_id: [if index == 0 { 1 } else { 3 }; 32],
                commitment_id: Some([2; 32]),
                actor_id: view.actor_id,
                period: 1,
                choice: OrganizerChoice::RemoteAid,
                standing_work: false,
                outcome,
                hours_spent: 0,
                partner_actor_id: None,
                partner_response: OrganizerPartnerResponse::NotRequested,
                observation_ids: Vec::new(),
                contact_product_id: None,
                time_use: Vec::new(),
            })
            .collect();
            let mut actual = view.receipts[0].clone();
            actual.receipt_id = [4; 32];
            actual.outcome = OrganizerOutcome::AidPracticeCompleted;
            actual.hours_spent = 2;
            actual.partner_actor_id = Some(view.neighborhood_partner_id);
            actual.partner_response = OrganizerPartnerResponse::Participated;
            view.receipts.push(actual.clone());
            actual.receipt_id = [5; 32];
            actual.commitment_id = Some([6; 32]);
            view.receipts.push(actual);
            if matches!(receipt_order, ReceiptOrder::Reversed) {
                view.receipts.reverse();
            }
            view.total_receipt_count = 4;
        }
        app.update();
        app.update();
        let aftermath = {
            let world = app.world_mut();
            world
                .query::<(Entity, &TextPart)>()
                .iter(world)
                .find_map(|(entity, part)| matches!(part, TextPart::Aftermath).then_some(entity))
                .expect("the dispatch retains its admitted reading target")
        };
        let font = app
            .world()
            .get::<TextFont>(aftermath)
            .expect("embedded body font")
            .font
            .clone();
        {
            let world = app.world_mut();
            for (role, mut text) in world
                .query::<(&ObserverFontRole, &mut TextFont)>()
                .iter_mut(world)
            {
                if matches!(role, ObserverFontRole::Body) {
                    text.font = font.clone();
                }
            }
        }
        for _ in 0..4 {
            app.update();
        }
        (app, aftermath)
    }

    fn assert_current_aid_stages(app: &App, aftermath: Entity, viewport: UVec2, scale: f32) {
        let (reversed, reverse_aftermath) =
            measured_pending_support_dispatch(viewport, scale, ReceiptOrder::Reversed);
        assert_eq!(
            app.world().get::<Text>(aftermath),
            reversed.world().get::<Text>(reverse_aftermath),
            "commitment stages must not depend on input order"
        );
        let world = app.world();
        let body = world.get::<Text>(aftermath).expect("typed P1 dispatch");
        assert!(
            body.0
                .contains("Support committed; awaiting material resolution")
                && body.0.contains("Support remains in transit"),
            "both actual stages remain distinct: {}",
            body.0
        );
        assert_eq!(body.0.matches("Period 1 · accepted ruling").count(), 2,
                "one heading per actual commitment; independent same-choice commitment stays distinct: {}", body.0);
        assert_eq!(
            body.0.matches("Organize remote solidarity").count(),
            2,
            "one action heading per commitment: {}",
            body.0
        );
        assert!(
            body.0.contains("Independent response") && body.0.contains("2 organizer-hours spent"),
            "actual response and hours lead the stages: {}",
            body.0
        );
        assert!(
            body.0.find("Independent response") < body.0.find("awaiting material resolution"),
            "current result precedes original provisional stage: {}",
            body.0
        );
    }

    #[test]
    fn native_workspace_dispatch_exposes_its_two_stage_receipt_continuation() {
        for (viewport, scale) in [
            (UVec2::new(1366, 768), 1.0),
            (UVec2::new(1920, 1080), 1.0),
            (UVec2::new(1920, 1080), 1.25),
        ] {
            let (mut app, aftermath) =
                measured_pending_support_dispatch(viewport, scale, ReceiptOrder::Original);
            assert_current_aid_stages(&app, aftermath, viewport, scale);
            let world = app.world();
            let target = world
                .get::<ObserverFocusTarget>(aftermath)
                .expect("existing reading target");
            assert!(
                target.available && target.kind == ObserverFocusKind::Reading,
                "the existing contextual reading remains eligible"
            );
            let reading = world
                .get::<ChildOf>(aftermath)
                .expect("dispatch reading")
                .parent();
            let panel = world
                .get::<ChildOf>(reading)
                .expect("dispatch overlay")
                .parent();
            assert!(
                world.get::<Overlay>(panel).is_some(),
                "actual overlay bounds still own map input"
            );
            let maximum = crate::observer_focus::scroll_max(
                world
                    .get::<ComputedNode>(reading)
                    .expect("real-font reading layout"),
            )
            .expect("scrolling dispatch");
            assert!(
                maximum.y > 1.0,
                "actual typed P1 content overflows: {maximum:?}"
            );
            let hint = {
                let world = app.world_mut();
                world
                    .query::<(Entity, &ScrollHint, &Text)>()
                    .iter(world)
                    .find_map(|(entity, hint, text)| {
                        (hint.0 == reading && text.0.contains("More below")).then_some(entity)
                    })
                    .expect("clipped receipt continuation must have a visible scroll cue")
            };
            assert_in_view(&app, hint, workspace_rect(&app, panel));
            assert!(
                workspace_rect(&app, hint).min.y >= workspace_rect(&app, reading).max.y,
                "the cue stays visible outside the scrolling content"
            );
            let continuation = {
                let world = app.world_mut();
                world.query::<(Entity, &ActionButton)>().iter(world).find_map(|(entity, action)| {
                    matches!(action.0, OrganizerAction::Follow(link)
                        if matches!(link.destination, Destination::Detail(DispatchDestination::Inspector(OrganizerInspector::Receipts))))
                        .then_some(entity)
                }).expect("dated practice receipt continuation")
            };
            app.world_mut()
                .get_mut::<ScrollPosition>(reading)
                .expect("existing dispatch scroll position")
                .y = maximum.y;
            app.update();
            app.update();
            assert_in_view(&app, continuation, workspace_rect(&app, reading));
            for child in app
                .world()
                .get::<Children>(continuation)
                .expect("receipt continuation labels")
                .iter()
            {
                if app
                    .world()
                    .get::<Text>(child)
                    .is_some_and(|text| !text.0.is_empty())
                {
                    assert_in_view(&app, child, workspace_rect(&app, reading));
                }
            }
            assert!(
                app.world()
                    .get::<Text>(hint)
                    .expect("persistent cue")
                    .0
                    .contains("More above"),
                "scrolling to the continuation exposes the return reading direction"
            );
        }
    }

    #[test]
    fn native_comparison_measures_projected_costs_and_terms_inside_the_visible_cards() {
        for (viewport, scale) in [
            (UVec2::new(1366, 768), 1.0),
            (UVec2::new(1920, 1080), 1.0),
            (UVec2::new(1920, 1080), 1.25),
        ] {
            let mut app = measured_board(viewport, scale, false, false);
            let bounds = Rect::from_corners(Vec2::ZERO, viewport.as_vec2());
            let cards = {
                let world = app.world_mut();
                world
                    .query_filtered::<(Entity, &Children, &ChildOf), With<ComparisonCard>>()
                    .iter(world)
                    .map(|(entity, kids, pair)| {
                        (entity, kids.iter().collect::<Vec<_>>(), pair.parent())
                    })
                    .collect::<Vec<_>>()
            };
            assert_eq!(cards.len(), 2);
            assert!(
                workspace_rect(&app, cards[0].0)
                    .intersect(workspace_rect(&app, cards[1].0))
                    .width()
                    <= 1.0
            );
            for (entity, children, pair) in cards {
                assert_in_view(&app, entity, bounds);
                let area = workspace_rect(&app, entity).intersect(workspace_rect(&app, pair));
                let mut copy = String::new();
                for child in children {
                    assert_in_view(&app, child, area);
                    copy.push_str(&app.world().get::<Text>(child).expect("printed card line").0);
                }
                let cost = if viewport.x > 1400 {
                    "2 of 2"
                } else {
                    "8 of 16"
                };
                assert!(
                    copy.contains(cost) && copy.contains("Resolves P4"),
                    "{copy}"
                );
                assert!(copy.contains("work") && copy.contains("contact"), "{copy}");
            }
            let fixed = {
                let world = app.world_mut();
                world
                    .query::<(Entity, &ActionButton)>()
                    .iter(world)
                    .filter_map(|(entity, action)| {
                        matches!(
                            action.0,
                            OrganizerAction::Review
                                | OrganizerAction::Advance
                                | OrganizerAction::Inspect(OrganizerInspector::Practices)
                        )
                        .then_some(entity)
                    })
                    .collect::<Vec<_>>()
            };
            assert_eq!(fixed.len(), 3);
            for entity in fixed {
                assert_in_view(&app, entity, bounds);
            }
            app.world_mut().resource_mut::<OrganizerClient>().scene_mode =
                OrganizerSceneMode::Relationships;
            app.update();
            app.update();
            let world = app.world_mut();
            assert!(
                world
                    .query_filtered::<Entity, With<RelationStage>>()
                    .single(world)
                    .is_ok(),
                "measured Relationships stage"
            );
            app.world_mut().resource_mut::<OrganizerClient>().inspector =
                OrganizerInspector::Review;
            app.update();
            let confirm = {
                let world = app.world_mut();
                world
                    .query::<(Entity, &ActionButton)>()
                    .iter(world)
                    .find_map(|(entity, button)| {
                        (button.0 == OrganizerAction::Confirm).then_some(entity)
                    })
                    .expect("confirmation")
            };
            assert_in_view(&app, confirm, bounds);
        }
    }

    #[test]
    fn pending_historical_and_unknown_terms_keep_the_native_deck_readable() {
        for (viewport, scale) in [(UVec2::new(1366, 768), 1.0), (UVec2::new(1920, 1080), 1.25)] {
            for state in ["pending", "historical", "unknown"] {
                let mut app = measured_board(viewport, scale, false, false);
                match state {
                    "pending" => {
                        app.world_mut()
                            .resource_mut::<ObserverSession>()
                            .begin_advance()
                            .expect("admitted live session can advance");
                    }
                    "historical" => {
                        let mut session = app.world_mut().resource_mut::<ObserverSession>();
                        session.inspect_tick(2);
                        let context = session.context();
                        assert!(session.installed(&context));
                    }
                    "unknown" => app.world_mut().resource_mut::<OrganizerClient>().view = None,
                    _ => unreachable!("authored frame states"),
                }
                app.update();
                app.update();
                let bounds = Rect::from_corners(Vec2::ZERO, viewport.as_vec2());
                let cards = {
                    let world = app.world_mut();
                    world
                        .query_filtered::<(Entity, &Children, &ChildOf), With<ComparisonCard>>()
                        .iter(world)
                        .map(|(entity, children, pair)| {
                            (entity, children.iter().collect::<Vec<_>>(), pair.parent())
                        })
                        .collect::<Vec<_>>()
                };
                assert_eq!(cards.len(), 2, "{state} comparison");
                for (entity, children, pair) in cards {
                    assert_in_view(&app, entity, bounds);
                    let area = workspace_rect(&app, entity).intersect(workspace_rect(&app, pair));
                    for child in children {
                        if !app
                            .world()
                            .get::<Text>(child)
                            .expect("card line")
                            .0
                            .is_empty()
                        {
                            assert_in_view(&app, child, area);
                        }
                    }
                }
                if state == "pending" {
                    let world = app.world_mut();
                    let message = world
                        .query::<(Entity, &TextPart, &Text, &ComputedNode)>()
                        .iter(world)
                        .find_map(|(entity, part, text, computed)| {
                            (matches!(part, TextPart::Message)
                                && text.0.contains("Advance requested from P3")
                                && computed.size().min_element() > 0.0)
                                .then_some(entity)
                        })
                        .expect("visible pending advance message");
                    assert_in_view(&app, message, bounds);
                }
            }
        }
    }

    #[derive(Clone, Copy, Debug)]
    enum InterfaceSize {
        Standard,
        Larger,
    }

    fn measured_pending_aid(viewport: UVec2, interface: InterfaceSize) -> App {
        use bevy::asset::AssetApp as _;
        let larger = matches!(interface, InterfaceSize::Larger);
        let fitted = if viewport.x > 1400 { 1.25 } else { 1.0 };
        let scale = fitted * if larger { 1.15 } else { 1.0 };
        let mut app = measured_board(viewport, scale, larger, false);
        app.init_asset::<Image>()
            .init_asset::<TextureAtlasLayout>()
            .add_systems(
                PostUpdate,
                bevy::ui::widget::text_system.after(bevy::ui::ui_layout_system),
            );
        let font = {
            let world = app.world_mut();
            world
                .query::<(&TextPart, &TextFont)>()
                .iter(world)
                .find_map(|(part, font)| {
                    matches!(part, TextPart::Situation).then_some(font.font.clone())
                })
                .expect("embedded reading face")
        };
        let snapshot: OrganizerSnapshot = serde_json::from_str(include_str!(
            "../../../babylon-persistence/tests/fixtures/national_organizer_pending_v19.json"
        ))
        .expect("actual national pending remote aid");
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.ready(1, None);
            let context = session.context();
            assert!(session.installed(&context));
        }
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.draft_writable = true;
            client.draft_dirty = false;
            client.view = Some(snapshot.view);
            client.aid = snapshot.aid;
            client.pending_aid = snapshot.pending_aid;
            let draft = client.draft.as_mut().expect("saved personal draft");
            draft.choice = OrganizerChoice::RemoteAid;
            draft.aid_allocation = babylon_persistence::runtime_session::OrganizerAllocation::Aid {
                food_quantity: 2,
                cash_micros: 280_000_000,
            };
        }
        for _ in 0..6 {
            app.update();
        }
        {
            let world = app.world_mut();
            for (role, mut text) in world
                .query::<(&ObserverFontRole, &mut TextFont)>()
                .iter_mut(world)
            {
                if matches!(role, ObserverFontRole::Body) {
                    text.font = font.clone();
                }
            }
        }
        for _ in 0..4 {
            app.update();
        }
        app
    }

    #[test]
    fn pending_aid_keeps_reason_and_routine_navigation_in_the_initial_native_view() {
        for (viewport, interface) in [
            (UVec2::new(1366, 768), InterfaceSize::Standard),
            (UVec2::new(1366, 768), InterfaceSize::Larger),
            (UVec2::new(1920, 1080), InterfaceSize::Standard),
            (UVec2::new(1920, 1080), InterfaceSize::Larger),
        ] {
            let mut app = measured_pending_aid(viewport, interface);
            let bounds = Rect::from_corners(Vec2::ZERO, viewport.as_vec2());
            let (direction, reason) = {
                let world = app.world_mut();
                let direction = world
                    .query::<(Entity, &ActionButton)>()
                    .iter(world)
                    .find_map(|(entity, action)| {
                        (action.0 == OrganizerAction::Inspect(OrganizerInspector::Direction))
                            .then_some(entity)
                    })
                    .expect("existing Direction action");
                let reason = world
                    .query::<(Entity, &Text)>()
                    .iter(world)
                    .find_map(|(entity, text)| {
                        (text.0.contains("Review blocked") && text.0.contains("saved, unsubmitted"))
                            .then_some(entity)
                    })
                    .expect("specific route reason beside disabled Review");
                (direction, reason)
            };
            assert_in_view(&app, direction, bounds);
            assert_in_view(&app, reason, bounds);
            assert_glyphs_in(&app, reason, bounds);
            assert!(
                app.world()
                    .get::<ObserverFocusTarget>(direction)
                    .is_some_and(|target| target.available),
                "fixed Direction remains focusable at {viewport:?}, {interface:?}"
            );
            let client = app.world().resource::<OrganizerClient>();
            let session = app.world().resource::<ObserverSession>();
            assert!(!enabled(OrganizerAction::Review, client, session));
            assert!(workspace::reviewable(
                client,
                session,
                OrganizerChoice::LocalAid
            ));
            assert_eq!(client.choice(), OrganizerChoice::RemoteAid);
            assert_eq!(
                client.draft.as_ref().expect("saved draft").aid_allocation,
                babylon_persistence::runtime_session::OrganizerAllocation::Aid {
                    food_quantity: 2,
                    cash_micros: 280_000_000
                }
            );
            app.world_mut()
                .resource_mut::<OrganizerClient>()
                .draft_dirty = true;
            app.update();
            let pending_save = &app.world().get::<Text>(reason).expect("same reason").0;
            assert!(
                pending_save.contains("awaiting save")
                    && !pending_save.contains("saved, unsubmitted"),
                "editing a blocked draft must not invent disk persistence: {pending_save}"
            );
            app.world_mut()
                .resource_mut::<OrganizerClient>()
                .draft_writable = false;
            app.update();
            let refused_save = &app.world().get::<Text>(reason).expect("same reason").0;
            assert!(
                refused_save.contains("saving unavailable"),
                "saving failure remains visible near the blocked action: {refused_save}"
            );
        }
    }

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
                app.world()
                    .get::<Text>(hint)
                    .expect("the fixture world holds the addressed component")
                    .0,
                "More below · scroll this panel"
            );
            // Bevy resolves physical scroll offsets without marking this
            // component changed. The hint must still update at larger UI scales.
            app.world_mut()
                .get_mut::<ComputedNode>(reading)
                .expect("the fixture world holds the addressed component")
                .bypass_change_detection()
                .scroll_position
                .y = 190.0 * scale;
            app.update();
            assert_eq!(
                app.world()
                    .get::<Text>(hint)
                    .expect("the fixture world holds the addressed component")
                    .0,
                "More above and below · scroll this panel"
            );
            app.world_mut()
                .get_mut::<ComputedNode>(reading)
                .expect("the fixture world holds the addressed component")
                .bypass_change_detection()
                .scroll_position
                .y = 200.0 * scale;
            app.update();
            assert_eq!(
                app.world()
                    .get::<Text>(hint)
                    .expect("the fixture world holds the addressed component")
                    .0,
                "More above · scroll this panel"
            );
            app.world_mut()
                .get_mut::<ComputedNode>(reading)
                .expect("the fixture world holds the addressed component")
                .bypass_change_detection()
                .content_size = Vec2::new(400.0, 100.0) * scale;
            app.update();
            assert_eq!(
                app.world()
                    .get::<Text>(hint)
                    .expect("the fixture world holds the addressed component")
                    .0
                    .len(),
                0
            );
        }
    }

    pub(crate) fn dossier_navigation_fixture() -> (App, Entity, String) {
        let (app, focus, draft) = organizer_navigation();
        (app, focus, format!("{draft:?}"))
    }

    pub(crate) fn draft_debug(app: &App) -> String {
        format!(
            "{:?}",
            app.world()
                .resource::<OrganizerClient>()
                .draft
                .as_ref()
                .expect("fixture draft")
        )
    }

    fn record_archive_request(
        event: On<OrganizerArchiveRequested>,
        mut requests: ResMut<ArchiveRequests>,
    ) {
        requests.0.push(event.target);
    }

    fn organizer_navigation() -> (App, Entity, OrganizerDraft) {
        let mut session = ObserverSession::new(CampaignId::from_uuid(Uuid::from_u128(927)));
        session.phase = SessionPhase::Ready;
        session.organizer_enabled = true;
        let draft = OrganizerDraft {
            aid_allocation: OrganizerAllocation::None,
            collection_allocation: OrganizerAllocation::None,
            workplace_id: 91,
            choice: OrganizerChoice::Reinforce,
            notes: NoteEditor::from_text("Keep this draft while reading evidence.".into())
                .expect("the authored input admits the derived value"),
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
                public_workplace_contact: false,
                content_digest: [2; 32],
                resource_digest: [3; 32],
                standing: OrganizerStandingWork {
                    partner_actor_id: 93,
                    authorized: true,
                    paused_reason: None,
                },
                agreements: Vec::new(),
                total_observation_count: 0,
                observations: Vec::new(),
                total_receipt_count: 0,
                receipts: Vec::new(),
                positions: Vec::new(),
                aid_partners: vec![],
                aid_options: Vec::new(),
            }),
            ..default()
        };
        let mut app = App::new();
        app.add_plugins((
            MinimalPlugins,
            crate::test_support::HeadlessVisibilityPlugin,
        ))
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
            .expect("the authored literal parses as the declared type"),
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
        .add_observer(record_archive_request);
        install(&mut app);
        let focus = app.world_mut().spawn_empty().id();
        app.world_mut()
            .resource_mut::<InputFocus>()
            .set(focus, FocusCause::Navigated);
        app.update();
        (app, focus, draft)
    }

    fn return_to_organizer(app: &mut App, focus: Entity, draft: &OrganizerDraft) {
        let archive_focus = app.world_mut().spawn_empty().id();
        app.world_mut()
            .resource_mut::<InputFocus>()
            .set(archive_focus, FocusCause::Navigated);
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
            .expect("the fixture set the optional field before this borrow")
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
                let command = client
                    .make_command(&session, client.choice())
                    .expect("the fixture command builds");
                client.queue(&mut session, RequestKind::Preview, Some(command.clone()));
                let request = client
                    .pending
                    .as_ref()
                    .expect("the fixture set the optional field before this read")
                    .id;
                let _ = client.outbox.take();
                client
                    .previewed(request, preview_for(&command), &mut session)
                    .expect("the fixture call `previewed` succeeds for the authored inputs");
            });
    }

    fn preview_for(command: &OrganizerCommand) -> OrganizerPreview {
        OrganizerPreview {
            allocation: command.allocation,
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
        if matches!(action, OrganizerAction::Choose(_))
            && !visible(
                action,
                world.resource::<OrganizerClient>(),
                world.resource::<ObserverSession>(),
                world.resource::<ObserverUiState>(),
                *world.resource::<PrimaryView>(),
            )
            && world.resource::<OrganizerClient>().inspector == OrganizerInspector::Closed
            && world.resource::<ObserverSession>().viewed_tick
                == world.resource::<ObserverSession>().durable_tick
        {
            world.write_message(OrganizerAction::Inspect(OrganizerInspector::Practices));
            app.update();
        }
        let _ = app.world_mut().write_message(action);
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
            .expect("the fixture yields the searched value")
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
            client.campaign = Some(Uuid::from_u128(927));
            client.draft_writable = true;
            let view = client
                .view
                .as_mut()
                .expect("the fixture set the optional field before this borrow");
            view.period = 3;
            for period in [2, 3] {
                view.observations.push(OrganizerObservation {
                    observation_id: [u8::try_from(period)
                        .expect("the fixture value fits the target range");
                        32],
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
        press_named(&mut app, "Acquired reports");
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
            .expect("the fixture holds exactly one matching row");
        app.update();
        assert!(
            !app.world()
                .get::<ObserverFocusTarget>(notes)
                .expect("the fixture world holds the addressed component")
                .available,
            "notes must not capture decision-screen typing before they are opened"
        );
        press_named(&mut app, "Personal notes");
        app.update();
        assert!(
            app.world()
                .get::<ObserverFocusTarget>(notes)
                .expect("the fixture world holds the addressed component")
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
                .expect("the fixture world holds the addressed component")
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
            .expect("the Bevy system completes one run");
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
            .expect("the fixture value clones");
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
    fn evicted_draft_reference_stays_saved_and_routes_to_earned_archive() {
        let (mut app, _) = reference_fixture();
        press_named(&mut app, "Keep report in draft");
        press_named(&mut app, "Return to decision [Esc]");
        let retained = app.world().resource::<OrganizerClient>().draft.clone();
        let period = app.world().resource::<ObserverSession>().viewed_tick;
        let subject = Some(OrganizerSubject::NeighborhoodGroup(93));
        app.world_mut()
            .resource_mut::<OrganizerClient>()
            .selected_subject = subject;
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            let view = client
                .view
                .as_mut()
                .expect("the fixture set the optional field before this borrow");
            view.total_observation_count = 325;
            view.observations.pop();
        }
        press_named(&mut app, "Personal notes");
        press_named(&mut app, "Open saved references");
        assert!(painted_text(&mut app, true).contains("Open Report Archive"));
        assert!(!painted_text(&mut app, true).contains("777 kg"));
        assert_eq!(app.world().resource::<OrganizerClient>().draft, retained);
        assert!(app.world().resource::<OrganizerClient>().outbox.is_none());
        press_named(&mut app, "Report Archive");
        assert_eq!(
            app.world().resource::<ArchiveRequests>().0,
            [OrganizerArchiveTarget::Browse]
        );
        assert!(app.world().resource::<ObserverUiState>().archive_open);
        assert_eq!(app.world().resource::<OrganizerClient>().draft, retained);
        assert!(app.world().resource::<OrganizerClient>().outbox.is_none());
        app.world_mut().write_message(OrganizerAction::Open);
        app.update();
        assert_eq!(
            app.world().resource::<ObserverSession>().viewed_tick,
            period
        );
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.selected_subject, subject);
        assert_eq!(client.draft, retained);
    }

    #[test]
    fn draft_references_cannot_reopen_hidden_foreign_or_missing_observations() {
        for fault in 0..4 {
            let (mut app, _) = reference_fixture();
            press_named(&mut app, "Keep report in draft");
            press_named(&mut app, "Return to decision [Esc]");
            {
                let mut client = app.world_mut().resource_mut::<OrganizerClient>();
                let observations = &mut client
                    .view
                    .as_mut()
                    .expect("the fixture set the optional field before this borrow")
                    .observations;
                let selected = observations
                    .last_mut()
                    .expect("the fixture sequence is non-empty");
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
                command: client
                    .reviewed_command
                    .clone()
                    .expect("the fixture value clones"),
                resolves_period: 4,
                commitment_id: [4; 32],
            });
        }
        app.update();
        assert!(painted_text(&mut app, false).contains("ACCEPTED"));
        app.world_mut().resource_mut::<ObserverSession>().phase = SessionPhase::Advancing;
        app.update();
        let text = painted_text(&mut app, false);
        assert!(text.contains("RESOLVING · period 4"));
        assert!(!text.contains("Advance to receive"));
        assert!(text.contains("No outcome is credited"));
        assert_eq!(
            app.world()
                .resource::<OrganizerClient>()
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .receipts
                .len(),
            0
        );
    }

    #[test]
    fn resolving_ruling_without_commitment_respects_paused_routine() {
        let (mut app, _) = reviewed_period_three();
        {
            let mut client = app.world_mut().resource_mut::<OrganizerClient>();
            client.commitment = None;
            let standing = &mut client
                .view
                .as_mut()
                .expect("the fixture set the optional field before this borrow")
                .standing;
            standing.authorized = false;
            standing.paused_reason = Some(OrganizerPauseReason::Explicit);
        }
        app.world_mut().resource_mut::<ObserverSession>().phase = SessionPhase::Advancing;
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
        assert_eq!(
            app.world()
                .resource::<OrganizerClient>()
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .receipts
                .len(),
            0
        );
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
                let command = client
                    .reviewed_command
                    .clone()
                    .expect("the fixture value clones");
                client.queue(&mut session, RequestKind::Submit, Some(command.clone()));
                let request = client
                    .pending
                    .as_ref()
                    .expect("the fixture set the optional field before this read")
                    .id;
                let _ = client.outbox.take();
                let accepted = super::super::OrganizerCommitment {
                    command,
                    resolves_period: 4,
                    commitment_id: [4; 32],
                };
                client
                    .accepted(request, accepted.clone(), &mut session)
                    .expect("the fixture call `accepted` succeeds for the authored inputs");
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
                let command = client
                    .make_command(&session, client.choice())
                    .expect("the fixture command builds");
                client.queue(&mut session, RequestKind::Preview, Some(command.clone()));
                let request = client
                    .pending
                    .as_ref()
                    .expect("the fixture set the optional field before this read")
                    .id;
                let _ = client.outbox.take();
                session.inspect_tick(2);
                let context = session.context();
                assert!(session.installed(&context));
                session.return_live();
                let context = session.context();
                assert!(session.installed(&context));
                client
                    .previewed(request, preview_for(&command), &mut session)
                    .expect("the fixture call `previewed` succeeds for the authored inputs");
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
            [OrganizerArchiveTarget::Workplace],
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

    #[test]
    fn pending_advance_paints_request_and_keeps_committed_navigation_and_notes_live() {
        use babylon_persistence::runtime_session::RuntimeSessionRequest;
        use std::time::Duration;

        let (mut app, window, notes, draft) = focused_organizer(true);
        app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::ZERO));
        let (requests, replies) =
            crate::observer_io::tests::install_pending_command_fixture(&mut app);
        let (status, reading, measures) =
            crate::observer_ui::tests::install_pending_paint_fixture(&mut app);
        let county = app
            .world()
            .resource::<CountyAtlas>()
            .index_of_fips("26163")
            .expect("the fixture call `index_of_fips` succeeds for the authored inputs");
        app.world_mut().resource_mut::<SelectedCounty>().0 = Some(county);
        app.world_mut()
            .resource_mut::<ObserverSession>()
            .foundation_digest = Some("foundation".into());
        {
            let mut state = app.world_mut().resource_mut::<ObserverSession>();
            state.ready(3, Some("3".repeat(64)));
            let installed_context = state.context();
            assert!(state.installed(&installed_context));
        }
        app.world_mut()
            .resource_mut::<OrganizerClient>()
            .view
            .as_mut()
            .expect("the fixture set the optional field before this borrow")
            .period = 3;
        let mut committed = crate::observer_io::tests::snapshot_with_event(
            app.world().resource::<ObserverSession>(),
            "freight arrival",
            3,
        );
        committed.production = Some(crate::production_freight::tests::fixture());
        app.world_mut().resource_mut::<ObserverFrame>().0 = Some(committed.clone());
        app.update();
        let context = app.world().resource::<ObserverSession>().context();
        app.world_mut().write_message(ObserverCommand::Step);
        app.update();
        let request = requests
            .try_recv()
            .expect("the producer sends before this receive");
        assert!(matches!(
            request,
            RuntimeSessionRequest::Advance { request_id: 1, .. }
        ));
        assert_eq!(
            app.world()
                .get::<Text>(status)
                .expect("the fixture world holds the addressed component")
                .0,
            "Period 4 requested; awaiting commit · 0s elapsed"
        );
        assert_eq!(app.world().resource::<ObserverSession>().durable_tick, 3);
        assert_pending_frame(&app, &context, &committed);

        app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_secs(7)));
        app.update();
        assert_eq!(
            app.world()
                .get::<Text>(status)
                .expect("the fixture world holds the addressed component")
                .0,
            "Period 4 requested; awaiting commit · 7s elapsed"
        );
        app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::ZERO));
        exercise_actual_advance_progress(&mut app, &replies, status, &context, &committed);
        typing_key(&mut app, window, KeyCode::KeyX, "x");
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(notes));
        assert_ne!(
            app.world()
                .resource::<OrganizerClient>()
                .draft
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .notes
                .text,
            draft.notes.text
        );
        assert!(panel_has_visible_text(&mut app, true, "Personal notes"));
        exercise_pending_committed_panels(&mut app, reading, measures);
        assert_pending_frame(&app, &context, &committed);
        assert!(app.world().resource::<ObserverSession>().advance_pending());
        assert!(app.world().resource::<OrganizerClient>().outbox.is_none());
        assert!(
            requests.try_recv().is_err(),
            "local reads and note edits cannot submit another period or organizer action"
        );
    }

    fn exercise_actual_advance_progress(
        app: &mut App,
        replies: &Sender<Result<RuntimeSessionResponse, String>>,
        status: Entity,
        context: &ObservationContext,
        committed: &ObserverEconomySnapshot,
    ) {
        let scope = app
            .world()
            .resource::<ObserverSession>()
            .runtime_scope()
            .expect("the fixture runtime scope exists")
            .clone();
        for (index, (stage, caption)) in [
            ("preparing_commitments", "Preparing commitments"),
            ("resolving_economy", "Resolving economy"),
            ("preparing_storage", "Preparing storage"),
            ("saving_period", "Saving period"),
        ]
        .into_iter()
        .enumerate()
        {
            // Literal wire evidence is independent of the future enum/API.
            let response = serde_json::from_value(serde_json::json!({
                "type": "advance_progress", "request_id": 1, "scope": scope,
                "resolve_tick": 4, "stage": stage
            }))
            .expect("current protocol must admit real advance phase messages");
            replies
                .send(Ok(response))
                .expect("the receiver stays alive for the send");
            app.insert_resource(TimeUpdateStrategy::ManualDuration(
                std::time::Duration::from_secs(1),
            ));
            app.update();
            assert_eq!(
                app.world()
                    .get::<Text>(status)
                    .expect("the fixture world holds the addressed component")
                    .0,
                format!("Period 4 · {caption} · {}s elapsed", index + 8)
            );
            assert_pending_frame(app, context, committed);
        }
        app.insert_resource(TimeUpdateStrategy::ManualDuration(
            std::time::Duration::ZERO,
        ));
    }

    fn assert_pending_frame(
        app: &App,
        context: &ObservationContext,
        committed: &ObserverEconomySnapshot,
    ) {
        let state = app.world().resource::<ObserverSession>();
        assert_eq!(&state.context(), context);
        assert_eq!(state.durable_tick, 3);
        assert_eq!(
            state.content_hash.as_deref(),
            Some("3".repeat(64)).as_deref()
        );
        assert_eq!(
            app.world().resource::<ObserverFrame>().for_session(state),
            Some(committed)
        );
    }

    fn exercise_pending_committed_panels(app: &mut App, reading: Entity, measures: Entity) {
        use crate::observer_ui::{NetworkSector, RoadLayer};
        for inspector in [
            OrganizerInspector::Relationships,
            OrganizerInspector::Receipts,
        ] {
            // Inspector navigation starts from the actual modal close control.
            // Notes and the preceding inspector intentionally hide menu actions.
            app.world_mut()
                .write_message(OrganizerAction::CloseInspector);
            app.update();
            assert_eq!(
                app.world().resource::<OrganizerClient>().inspector,
                OrganizerInspector::Closed
            );
            app.world_mut()
                .write_message(OrganizerAction::Inspect(inspector));
            app.update();
            assert_eq!(
                app.world().resource::<OrganizerClient>().inspector,
                inspector
            );
            let expected = if inspector == OrganizerInspector::Relationships {
                "CURRENT COMMUNICATION AGREEMENTS"
            } else {
                "COMMITTED PRACTICE HISTORY"
            };
            assert!(panel_has_visible_text(app, true, expected));
        }
        app.world_mut()
            .write_message(OrganizerAction::ArchiveWorkplace);
        app.update();
        assert_eq!(*app.world().resource::<PrimaryView>(), PrimaryView::Map);
        assert_eq!(
            app.world().resource::<ArchiveRequests>().0,
            [OrganizerArchiveTarget::Workplace]
        );
        assert_eq!(
            app.world()
                .get::<Text>(reading)
                .expect("the fixture world holds the addressed component")
                .0,
            "Choose a cohort to follow its commodities, freight and workers in Circuit."
        );
        for command in [
            ObserverCommand::EconomicDetails,
            ObserverCommand::Relationships,
            ObserverCommand::RoadLayer(RoadLayer::EconomyNetwork),
            ObserverCommand::NetworkSector(NetworkSector::Manufacturing),
        ] {
            app.world_mut().write_message(command);
            app.update();
            assert!(app
                .world()
                .resource::<crate::observer_ui::ObserverFeedback>()
                .message
                .is_none());
        }
        assert_eq!(
            app.world()
                .get::<Text>(measures)
                .expect("the fixture world holds the addressed component")
                .0,
            "Choose an economic lens to inspect exact county readings."
        );
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
                .expect("the fixture holds exactly one matching row")
        } else {
            app.world_mut()
                .query_filtered::<(Entity, &ActionButton), With<ComparisonCard>>()
                .iter(app.world())
                .find_map(|(entity, button)| {
                    matches!(
                        button.0,
                        OrganizerAction::Choose(OrganizerChoice::Reinforce)
                    )
                    .then_some(entity)
                })
                .expect("the fixture yields the searched value")
        };
        app.world_mut()
            .resource_mut::<InputFocus>()
            .set(focus, FocusCause::Navigated);
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
        app.world_mut().resource_mut::<ObserverSession>().playing = true;
        typing_key(&mut app, window, KeyCode::KeyP, "p");
        assert!(!app.world().resource::<ObserverSession>().playing);
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.inspector, OrganizerInspector::Evidence);
        assert_eq!(client.return_focus, Some(focus));
        assert_eq!(client.draft.as_ref(), Some(&draft));
        assert!(
            client
                .view
                .as_ref()
                .expect("the fixture set the optional field before this read")
                .observations
                .is_empty(),
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
        assert_eq!(
            app.world().resource::<ArchiveRequests>().0,
            [OrganizerArchiveTarget::Workplace]
        );
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
    fn dated_report_navigation_keeps_its_observed_and_acquired_period_and_rejects_old_generation() {
        let (mut app, draft) = admitted_scene_fixture();
        let subject = OrganizerSubject::NeighborhoodGroup(93);
        app.world_mut()
            .write_message(OrganizerAction::SelectSubject(subject));
        app.update();
        app.world_mut().resource_mut::<ObserverSession>().playing = true;
        let (button, original) = {
            let world = app.world_mut();
            world
                .query::<(Entity, &ActionButton)>()
                .iter(world)
                .find_map(|(entity, button)| match button.0 {
                    OrganizerAction::Follow(link)
                        if link.destination
                            == Destination::Detail(DispatchDestination::Report([3; 32])) =>
                    {
                        Some((entity, link))
                    }
                    _ => None,
                })
                .expect("dated report in the actual period dispatch")
        };
        let dispatch = {
            let world = app.world_mut();
            world
                .query::<(&TextPart, &Text)>()
                .iter(world)
                .find_map(|(part, text)| {
                    matches!(part, TextPart::Aftermath).then(|| text.0.clone())
                })
                .expect("period dispatch")
        };
        assert!(dispatch.contains("observed P2, acquired P3"), "{dispatch}");
        assert!(!dispatch.contains("observed P1, acquired P2"), "{dispatch}");
        *app.world_mut()
            .get_mut::<Interaction>(button)
            .expect("dispatch target") = Interaction::Pressed;
        app.update();
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.inspector, OrganizerInspector::Evidence);
        assert!(!app.world().resource::<ObserverSession>().playing);
        assert_eq!(client.selected_evidence_id(3), Some([3; 32]));
        assert_eq!(client.draft, draft);
        press_named(&mut app, "Return to decision [Esc]");
        assert_eq!(
            app.world().resource::<OrganizerClient>().selected_subject,
            Some(subject)
        );
        inspect_period(&mut app, 2);
        app.update();
        inspect_period(&mut app, 3);
        app.update();
        app.world_mut()
            .write_message(OrganizerAction::Follow(original));
        app.world_mut().resource_mut::<ObserverSession>().playing = true;
        app.update();
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.inspector, OrganizerInspector::Closed);
        assert_eq!(client.draft, draft);
        assert!(client.outbox.is_none());
        assert!(
            app.world().resource::<ObserverSession>().playing,
            "stale links cannot pause"
        );
    }

    #[test]
    fn native_review_opens_the_authenticated_terms_before_confirm_can_submit() {
        let (mut app, _) = admitted_scene_fixture();
        let control = |app: &mut App, action: OrganizerAction| {
            let world = app.world_mut();
            world
                .query::<(Entity, &ActionButton)>()
                .iter(world)
                .find_map(|(entity, button)| (button.0 == action).then_some(entity))
                .expect("native action")
        };
        app.world_mut().resource_mut::<ObserverSession>().playing = true;
        let review = control(&mut app, OrganizerAction::Review);
        let confirm = control(&mut app, OrganizerAction::Confirm);
        *app.world_mut()
            .get_mut::<Interaction>(review)
            .expect("Review button") = Interaction::Pressed;
        app.update();
        let command = app
            .world_mut()
            .resource_scope(|world, mut client: Mut<OrganizerClient>| {
                assert_eq!(client.inspector, OrganizerInspector::Review);
                let Some(RuntimeSessionRequest::PreviewOrganizer {
                    request_id,
                    command,
                    ..
                }) = client.outbox.take()
                else {
                    panic!("review produced preview request");
                };
                let mut session = world.resource_mut::<ObserverSession>();
                assert!(!enabled(OrganizerAction::Confirm, &client, &session));
                client
                    .previewed(request_id, preview_for(&command), &mut session)
                    .expect("matching authenticated preview");
                assert!(
                    !session.playing,
                    "Review keeps the authenticated terms readable"
                );
                command
            });
        app.update();
        assert!(panel_has_visible_text(
            &mut app,
            true,
            "Cost: 8 of 16 organizer-hours"
        ));
        *app.world_mut()
            .get_mut::<Interaction>(confirm)
            .expect("Confirm button") = Interaction::Pressed;
        app.update();
        let client = app.world().resource::<OrganizerClient>();
        assert!(
            matches!(&client.outbox, Some(RuntimeSessionRequest::SubmitOrganizer { command: submitted, .. }) if *submitted == command)
        );
        assert_eq!(client.inspector, OrganizerInspector::Closed);
        assert!(!app.world().resource::<ObserverSession>().advance_pending());
    }

    #[test]
    fn all_practices_exposes_nine_choices_without_selecting_or_reviewing_one() {
        let (mut app, draft) = admitted_scene_fixture();
        let inquiry = OrganizerChoice::Inquiry(OrganizerInquiry::WorkLost);
        app.world_mut()
            .write_message(OrganizerAction::Choose(inquiry));
        app.update();
        assert_eq!(app.world().resource::<OrganizerClient>().draft, draft);
        press_named(&mut app, "All practices");
        let world = app.world_mut();
        assert_eq!(
            world.resource::<OrganizerClient>().inspector,
            OrganizerInspector::Practices
        );
        let mut shown = Vec::new();
        for (button, parent) in world.query::<(&ActionButton, &ChildOf)>().iter(world) {
            if let OrganizerAction::Choose(choice) = button.0 {
                if world
                    .get::<DetailControls>(parent.parent())
                    .is_some_and(|section| section.0 == OrganizerInspector::Practices)
                {
                    shown.push(choice);
                }
            }
        }
        assert_eq!(shown, workspace::ALL_PRACTICES);
        assert!(world.resource::<OrganizerClient>().outbox.is_none());
        for label in ["Organize local aid", "Organize remote solidarity"] {
            press_named(&mut app, label);
            let client = app.world().resource::<OrganizerClient>();
            assert_eq!(
                client.inspector,
                OrganizerInspector::Practices,
                "missing material terms keep {label} unavailable"
            );
            assert_eq!(
                client.draft, draft,
                "{label} cannot select an unauthenticated draft"
            );
            assert!(
                client.outbox.is_none(),
                "{label} cannot queue an engine request"
            );
        }
        press_named(&mut app, "Ask about work and output");
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.choice(), inquiry);
        assert_eq!(client.inspector, OrganizerInspector::Closed);
        assert!(client.outbox.is_none());
    }

    #[test]
    fn disclosed_visit_is_period_filtered_and_uses_existing_archive_navigation() {
        let (mut app, focus, draft) = organizer_navigation();
        {
            let client = app.world().resource::<OrganizerClient>();
            assert_eq!(
                presentation::encounter_history(
                    client,
                    client.view.as_ref().expect("fixture view"),
                    3
                ),
                ""
            );
        }
        let (mut client, session, request, snapshot) = crate::organizer::tests::status_fixture();
        client.draft = Some(draft.clone());
        app.insert_resource(client).insert_resource(session);
        let replies = crate::observer_io::tests::install_status_receiver(&mut app);
        let RuntimeSessionRequest::OrganizerStatus {
            scope, request_id, ..
        } = request
        else {
            panic!("expected status request");
        };
        replies
            .send(Ok(RuntimeSessionResponse::OrganizerStatus {
                scope,
                request_id,
                snapshot: Box::new(snapshot),
            }))
            .expect("response receiver remains open");
        app.update();
        assert_eq!(
            app.world()
                .resource::<OrganizerClient>()
                .city_pd_encounters
                .len(),
            1
        );
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.inspect_tick(1);
            let context = session.context();
            assert!(session.installed(&context));
        }
        app.update();
        let aftermath = |app: &mut App| {
            let world = app.world_mut();
            world
                .query::<(&TextPart, &Text)>()
                .iter(world)
                .find_map(|(part, text)| {
                    matches!(part, TextPart::Aftermath).then(|| text.0.clone())
                })
                .expect("aftermath exists")
        };
        assert!(!aftermath(&mut app).contains("CITY PD VISIT"));
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.return_live();
            let context = session.context();
            assert!(session.installed(&context));
        }
        app.update();
        let text = aftermath(&mut app);
        assert!(
            !text.contains("CITY PD VISIT · PERIOD 2"),
            "old encounter in the current dispatch: {text}"
        );
        press_named(&mut app, "Practice history");
        let history = painted_text(&mut app, true);
        assert!(history.contains("CITY PD VISIT · PERIOD 2"), "{history}");
        assert!(history.contains("Cited workplace Archive"), "{history}");
        press_named(&mut app, "Cited workplace Archive");
        assert_eq!(
            app.world().resource::<ArchiveRequests>().0,
            [OrganizerArchiveTarget::Workplace]
        );
        return_to_organizer(&mut app, focus, &draft);
    }

    #[test]
    fn historical_navigation_reconciles_stale_status_without_disconnecting() {
        let (mut app, focus, draft) = organizer_navigation();
        let (mut client, session, request, snapshot) = crate::organizer::tests::status_fixture();
        client.draft = Some(draft.clone());
        let command = client
            .make_command(&session, OrganizerChoice::Hold)
            .expect("fixture command");
        client.preview = Some(preview_for(&command));
        client.reviewed_command = Some(command);
        client.review_context = Some(session.context());
        app.insert_resource(client).insert_resource(session);
        let (requests, replies) = crate::observer_io::tests::install_status_pipe(&mut app);
        app.add_systems(
            Update,
            super::super::transport
                .after(ObserverSet::Receive)
                .before(ObserverSet::Paint),
        );
        let RuntimeSessionRequest::OrganizerStatus {
            scope, request_id, ..
        } = request
        else {
            panic!("expected status request");
        };
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.inspect_tick(1);
            let context = session.context();
            assert!(session.installed(&context));
        }
        replies
            .send(Ok(RuntimeSessionResponse::OrganizerStatus {
                scope: scope.clone(),
                request_id,
                snapshot: Box::new(snapshot.clone()),
            }))
            .expect("response receiver remains open");
        app.update();
        let session = app.world().resource::<ObserverSession>();
        assert!(
            !session.runtime_disconnected(),
            "local navigation must not disconnect the runtime"
        );
        assert_ne!(session.phase, SessionPhase::Failed);
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(
            client
                .view
                .as_ref()
                .expect("original view")
                .organization_label,
            "Fixture collective"
        );
        assert_eq!(client.city_pd_encounters.len(), 0);
        assert_eq!(client.draft.as_ref(), Some(&draft));
        assert!(client.reviewed_command.is_none());
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(focus));
        let RuntimeSessionRequest::OrganizerStatus {
            request_id: retry_id,
            scope: retry_scope,
            ..
        } = requests.try_recv().expect("fresh status requested")
        else {
            panic!("expected fresh status");
        };
        assert_ne!(retry_id, request_id);
        assert_eq!(retry_scope, scope);
        replies
            .send(Ok(RuntimeSessionResponse::OrganizerStatus {
                scope: retry_scope,
                request_id: retry_id,
                snapshot: Box::new(snapshot),
            }))
            .expect("response receiver remains open");
        app.update();
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(
            client
                .view
                .as_ref()
                .expect("updated view")
                .organization_label,
            "Updated collective"
        );
        assert_eq!(client.city_pd_encounters.len(), 1);
        assert_eq!(client.draft.as_ref(), Some(&draft));
        assert!(client.reviewed_command.is_none());
        assert_eq!(app.world().resource::<InputFocus>().get(), Some(focus));
        assert!(!app
            .world()
            .resource::<ObserverSession>()
            .runtime_disconnected());
    }

    #[test]
    fn settled_scene_refreshes_after_history_and_return_live() {
        use babylon_persistence::runtime_session::RuntimeSessionErrorCode;
        let (mut client, mut session, request, snapshot) = super::super::tests::status_fixture();
        let RuntimeSessionRequest::OrganizerStatus { request_id, .. } = request else {
            panic!("initial status request");
        };
        client
            .status(request_id, snapshot.clone(), &mut session)
            .expect("settled live status");
        client.scene_mode = OrganizerSceneMode::Relationships;
        let (mut app, _, draft) = organizer_navigation();
        client.draft = Some(draft.clone());
        app.insert_resource(client).insert_resource(session);
        let (requests, replies) = crate::observer_io::tests::install_status_pipe(&mut app);
        app.add_systems(
            Update,
            super::super::transport
                .after(ObserverSet::Receive)
                .before(ObserverSet::Paint),
        );
        app.update();
        let neighborhood = OrganizerSubject::NeighborhoodGroup(93);
        app.world_mut()
            .write_message(OrganizerAction::SelectSubject(neighborhood));
        app.update();
        assert!(scene_text(&mut app).contains("Collective structure unknown"));
        assert!(requests.try_recv().is_err());
        inspect_period(&mut app, 2);
        app.update();
        let RuntimeSessionRequest::OrganizerStatus {
            scope, request_id, ..
        } = requests.try_recv().expect("history status requested")
        else {
            panic!("history status request");
        };
        assert!(scene_text(&mut app).contains("Loading organizer scene"));
        assert!(!scene_text(&mut app).contains("Fixture workplace"));
        replies
            .send(Ok(RuntimeSessionResponse::Error {
                scope,
                request_id: Some(request_id),
                code: RuntimeSessionErrorCode::StorageRefused,
                tail: None,
            }))
            .expect("history refusal");
        app.update();
        assert!(scene_text(&mut app).contains("StorageRefused"));
        app.update();
        assert!(
            requests.try_recv().is_err(),
            "a matching refusal must not retry"
        );
        {
            let mut session = app.world_mut().resource_mut::<ObserverSession>();
            session.return_live();
            let context = session.context();
            assert!(session.installed(&context));
        }
        app.update();
        let RuntimeSessionRequest::OrganizerStatus {
            scope, request_id, ..
        } = requests.try_recv().expect("returned live status requested")
        else {
            panic!("returned live status request");
        };
        assert!(scene_text(&mut app).contains("Loading organizer scene"));
        replies
            .send(Ok(RuntimeSessionResponse::OrganizerStatus {
                scope,
                request_id,
                snapshot: Box::new(snapshot),
            }))
            .expect("validated live status");
        app.update();
        assert!(scene_text(&mut app).contains("Collective structure unknown"));
        let client = app.world().resource::<OrganizerClient>();
        assert_eq!(client.selected_subject, Some(neighborhood));
        assert_eq!(client.draft.as_ref(), Some(&draft));
        assert!(client
            .scene_for(app.world().resource::<ObserverSession>())
            .is_some());
        app.update();
        assert!(
            requests.try_recv().is_err(),
            "settled context must not retry"
        );
    }

    #[test]
    fn stale_status_refusal_requeues_the_returned_live_context() {
        use babylon_persistence::runtime_session::RuntimeSessionErrorCode;
        let (client, session, request, snapshot) = super::super::tests::status_fixture();
        let RuntimeSessionRequest::OrganizerStatus {
            scope, request_id, ..
        } = request
        else {
            panic!("status request")
        };
        let (mut app, _, _) = organizer_navigation();
        app.insert_resource(client).insert_resource(session);
        let (requests, replies) = crate::observer_io::tests::install_status_pipe(&mut app);
        app.add_systems(
            Update,
            super::super::transport
                .after(ObserverSet::Receive)
                .before(ObserverSet::Paint),
        );
        inspect_period(&mut app, 2);
        inspect_period(&mut app, 3);
        replies
            .send(Ok(RuntimeSessionResponse::Error {
                scope: scope.clone(),
                request_id: Some(request_id),
                code: RuntimeSessionErrorCode::StorageRefused,
                tail: None,
            }))
            .expect("refusal delivered");
        app.update();
        let RuntimeSessionRequest::OrganizerStatus {
            request_id: retry_id,
            scope: retry_scope,
            ..
        } = requests.try_recv().expect("fresh status requested")
        else {
            panic!("replacement status")
        };
        assert_ne!(retry_id, request_id);
        assert_eq!(retry_scope, scope);
        assert!(scene_text(&mut app).contains("Loading organizer scene"));
        assert!(!scene_text(&mut app).contains("StorageRefused"));
        replies
            .send(Ok(RuntimeSessionResponse::OrganizerStatus {
                scope: retry_scope,
                request_id: retry_id,
                snapshot: Box::new(snapshot),
            }))
            .expect("replacement delivered");
        app.update();
        let client = app.world().resource::<OrganizerClient>();
        let session = app.world().resource::<ObserverSession>();
        assert!(!client.status_due);
        assert!(client.pending.is_none());
        assert!(client.scene_for(session).is_some());
        assert!(!session.runtime_disconnected());
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
        assert_eq!(app.world().resource::<ArchiveRequests>().0.len(), 0);
        assert!(!app.world().resource::<ObserverUiState>().archive_open);
        let edited = client
            .draft
            .as_ref()
            .expect("the fixture set the optional field before this read");
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
            .set(inspector_focus, FocusCause::Navigated);
        app.world_mut()
            .write_message(OrganizerAction::ArchiveWorkplace);
        app.update();
        assert_eq!(
            app.world().resource::<ArchiveRequests>().0,
            [OrganizerArchiveTarget::Workplace]
        );
        assert_eq!(
            app.world().resource::<OrganizerClient>().return_focus,
            Some(focus)
        );
        return_to_organizer(&mut app, focus, &draft);
    }
    include!("aid_review_tests.rs");
    include!("allocation_input_tests.rs");
}

#[cfg(test)]
#[path = "reading_pause_tests.rs"]
mod reading_pause_tests;
