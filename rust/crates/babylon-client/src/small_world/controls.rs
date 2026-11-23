//! The scene's words and buttons: the header, the control bar, the refusal banner, the labels
//! under the bodies and the standing lines. Everything here is `unfogged material truth`: the
//! scene belongs to the `SmallWorld` surface and nothing else.

use super::frame::BodyPicture;
use super::reading::Party;
use super::scene;
use super::scene::{
    SceneCamera, SceneCommand, SceneRunner, SceneShown, SceneStatus, BAR_HEIGHT, HEADER_HEIGHT,
    RAIL_WIDTH,
};
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use crate::palette::FIELD;
use crate::ui;
use bevy::picking::pointer::PointerButton;
use bevy::prelude::*;

/// The header's first line.
pub const UNFOGGED_LINE: &str = "ADMIN · MATERIAL TRUTH · UNFOGGED";
/// The header's second line.
pub const NOT_WAYNE_LINE: &str = "A test economy. Not Wayne. Not saved.";
/// The standing line at the viewport's bottom left.
pub const COPIES_LINE: &str =
    "Place A and Place B are copies of one test economy, not real places.";
/// The line in the middle of the viewport until a period has been shown.
pub const EMPTY_LINE: &str = "Nothing has run yet. Press Step.";

/// How far under a body's lowest outer point its label stands, in logical pixels.
const LABEL_GAP: f32 = 10.0;
/// What the label's plate is drawn at: the field's colour, a little see-through.
const LABEL_PLATE_ALPHA: f32 = 0.82;
/// The centre disc of a body, the least a label hangs under.
const CORE_EXTENT: f32 = 0.2;
/// The outer reach of a treasury's or a fund's frame.
const FRAME_EXTENT: f32 = 0.6;
/// Half the width of a ring's line.
const RING_HALF_LINE: f32 = 0.0275;

/// A button of the control bar.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub enum SceneButton {
    Step,
    PlayPause,
    Again,
    StartOver,
}

/// The row of the control bar a button sits in: row 1 is Task 7's, row 2 and the rail are Task 8's.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub struct ControlRow(pub u8);

/// The label that hangs under a body.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub struct BodyLabel(pub Party);

#[derive(Component)]
pub struct ButtonCaption;
#[derive(Component)]
pub struct HeaderPeriod;
#[derive(Component)]
pub struct HeaderState;
#[derive(Component)]
pub struct RefusalBanner;
#[derive(Component)]
pub struct EmptyLine;

fn text(value: impl Into<String>, size: f32, color: Color, role: ObserverFontRole) -> impl Bundle {
    (
        Text::new(value),
        TextFont {
            font_size: FontSize::Px(size),
            ..default()
        },
        TextColor(color),
        role,
        DeclaredSurface::new(SurfaceId::SmallWorld),
        Pickable::IGNORE,
    )
}

/// Spawn the header, the control bar, the standing line and a label for each body.
pub fn spawn_chrome(commands: &mut Commands) {
    spawn_header(commands);
    spawn_bar(commands);
    commands.spawn((
        text(COPIES_LINE, 13.0, theme::PAPER, ObserverFontRole::Body),
        Node {
            position_type: PositionType::Absolute,
            left: px(16),
            bottom: px(BAR_HEIGHT + 8.0),
            ..default()
        },
    ));
    for party in scene::body_points().map(|(party, _)| party) {
        commands.spawn((
            text(party.label(), 12.0, theme::PAPER, ObserverFontRole::Body),
            BodyLabel(party),
            Node {
                position_type: PositionType::Absolute,
                padding: UiRect::axes(px(4), px(1)),
                ..default()
            },
            UiTransform::from_translation(Val2::percent(-50.0, 0.0)),
            BackgroundColor(FIELD.with_alpha(LABEL_PLATE_ALPHA)),
            Visibility::Hidden,
        ));
    }
}

fn spawn_header(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                top: px(0),
                left: px(0),
                right: px(0),
                height: px(HEADER_HEIGHT),
                padding: UiRect::axes(px(16), px(2)),
                justify_content: JustifyContent::SpaceBetween,
                align_items: AlignItems::Center,
                ..default()
            },
            BackgroundColor(theme::PANEL),
            ZIndex(10),
        ))
        .with_children(|header| {
            header
                .spawn(Node {
                    flex_direction: FlexDirection::Column,
                    ..default()
                })
                .with_children(|left| {
                    left.spawn(text(
                        UNFOGGED_LINE,
                        20.0,
                        theme::RED,
                        ObserverFontRole::Display,
                    ));
                    left.spawn(text(
                        NOT_WAYNE_LINE,
                        14.0,
                        theme::PAPER,
                        ObserverFontRole::Body,
                    ));
                });
            header
                .spawn(Node {
                    flex_direction: FlexDirection::Column,
                    align_items: AlignItems::FlexEnd,
                    ..default()
                })
                .with_children(|right| {
                    right.spawn((
                        text("", 20.0, theme::PAPER, ObserverFontRole::Display),
                        HeaderPeriod,
                    ));
                    right.spawn((
                        text("", 14.0, theme::PAPER, ObserverFontRole::Body),
                        HeaderState,
                    ));
                });
        });
}

fn spawn_bar(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                bottom: px(0),
                left: px(0),
                right: px(0),
                height: px(BAR_HEIGHT),
                padding: UiRect::all(px(8)),
                flex_direction: FlexDirection::Column,
                row_gap: px(8),
                ..default()
            },
            BackgroundColor(theme::PANEL),
            ZIndex(10),
        ))
        .with_children(|bar| {
            for number in [1_u8, 2] {
                bar.spawn((
                    ControlRow(number),
                    Node {
                        height: px(32),
                        column_gap: px(8),
                        align_items: AlignItems::Center,
                        ..default()
                    },
                ))
                .with_children(|row| {
                    if number == 1 {
                        for (kind, caption) in [
                            (SceneButton::Step, "Step"),
                            (SceneButton::PlayPause, "Play"),
                            (SceneButton::Again, "Again"),
                            (SceneButton::StartOver, "Start over"),
                        ] {
                            spawn_button(row, kind, caption);
                        }
                    }
                });
            }
        });
}

fn spawn_button(row: &mut ChildSpawnerCommands, kind: SceneButton, caption: &str) {
    row.spawn((
        ui::pressable(),
        kind,
        Node {
            height: px(28),
            min_width: px(96),
            border: UiRect::all(px(1)),
            padding: UiRect::horizontal(px(12)),
            justify_content: JustifyContent::Center,
            align_items: AlignItems::Center,
            ..default()
        },
        BorderColor::all(theme::PAPER),
        BackgroundColor(Color::NONE),
    ))
    .observe(pressed)
    .with_child((
        text(caption, 14.0, theme::PAPER, ObserverFontRole::Body),
        ButtonCaption,
    ));
}

fn pressed(
    event: On<PointerClick>,
    buttons: Query<&SceneButton>,
    status: Res<SceneStatus>,
    mut commands: MessageWriter<SceneCommand>,
) {
    if event.button != PointerButton::Primary {
        return;
    }
    let Ok(button) = buttons.get(event.entity) else {
        return;
    };
    let refused = status.refusal.is_some();
    let command = match button {
        SceneButton::Step if !refused => SceneCommand::Step,
        SceneButton::PlayPause if status.playing => SceneCommand::Pause,
        SceneButton::PlayPause if !refused => SceneCommand::Play,
        SceneButton::Again => SceneCommand::Again,
        SceneButton::StartOver => SceneCommand::StartOver,
        SceneButton::Step | SceneButton::PlayPause => return,
    };
    commands.write(command);
}

/// The header's right side: the period shown and whether the run is playing or stopped.
pub fn paint_header(
    runner: Res<SceneRunner>,
    status: Res<SceneStatus>,
    mut period: Query<&mut Text, (With<HeaderPeriod>, Without<HeaderState>)>,
    mut state: Query<&mut Text, (With<HeaderState>, Without<HeaderPeriod>)>,
) {
    let line = runner
        .shown
        .map_or_else(|| "No period yet".to_owned(), |n| format!("Period {n}"));
    for mut text in &mut period {
        text.set_if_neq(Text::new(line.clone()));
    }
    let words = if status.refusal.is_some() {
        "Stopped by the engine"
    } else if status.playing {
        "Playing"
    } else {
        ""
    };
    for mut text in &mut state {
        text.set_if_neq(Text::new(words));
    }
}

/// Step and Play go dim while a refusal shows; the Play button reads Pause while it plays.
pub fn paint_buttons(
    status: Res<SceneStatus>,
    mut buttons: Query<(&SceneButton, &Children, &mut BorderColor)>,
    mut captions: Query<(&mut Text, &mut TextColor), With<ButtonCaption>>,
) {
    for (button, children, mut border) in &mut buttons {
        let dim = status.refusal.is_some()
            && (*button == SceneButton::Step
                || (*button == SceneButton::PlayPause && !status.playing));
        let color = if dim {
            theme::PAPER.with_alpha(0.35)
        } else {
            theme::PAPER
        };
        border.set_if_neq(BorderColor::all(color));
        for child in children {
            if let Ok((mut text, mut text_color)) = captions.get_mut(*child) {
                text_color.set_if_neq(TextColor(color));
                if *button == SceneButton::PlayPause {
                    text.set_if_neq(Text::new(if status.playing { "Pause" } else { "Play" }));
                }
            }
        }
    }
}

/// The engine's own words at the top of the viewport while a refusal holds.
pub fn paint_banner(
    mut commands: Commands,
    status: Res<SceneStatus>,
    banner: Query<(Entity, &Children), With<RefusalBanner>>,
    mut words: Query<&mut Text, Without<RefusalBanner>>,
) {
    let existing = banner.iter().next();
    match (&status.refusal, existing) {
        (Some(refusal), None) => {
            commands
                .spawn((
                    RefusalBanner,
                    Node {
                        position_type: PositionType::Absolute,
                        left: px(16),
                        right: px(RAIL_WIDTH + 16.0),
                        top: px(HEADER_HEIGHT + 8.0),
                        padding: UiRect::all(px(8)),
                        border: UiRect::all(px(2)),
                        ..default()
                    },
                    BackgroundColor(theme::PANEL),
                    BorderColor::all(theme::RED),
                    ZIndex(20),
                ))
                .with_child(text(
                    refusal.clone(),
                    14.0,
                    theme::PAPER,
                    ObserverFontRole::Body,
                ));
        }
        (Some(refusal), Some((_, children))) => {
            for child in children {
                if let Ok(mut text) = words.get_mut(*child) {
                    text.set_if_neq(Text::new(refusal.clone()));
                }
            }
        }
        (None, Some((entity, _))) => commands.entity(entity).despawn(),
        (None, None) => {}
    }
}

/// "Nothing has run yet" stands in the middle of the viewport until a period is shown.
pub fn paint_empty_line(
    mut commands: Commands,
    runner: Res<SceneRunner>,
    line: Query<Entity, With<EmptyLine>>,
) {
    let existing = line.iter().next();
    match (runner.shown.is_none(), existing) {
        (true, None) => {
            commands.spawn((
                EmptyLine,
                text(EMPTY_LINE, 14.0, theme::PAPER, ObserverFontRole::Body),
                TextLayout::justify(Justify::Center),
                Node {
                    position_type: PositionType::Absolute,
                    left: px(0),
                    right: px(RAIL_WIDTH),
                    top: percent(50),
                    // The viewport's middle, not the window's: it runs from the header to the bar.
                    margin: UiRect::top(px((HEADER_HEIGHT - BAR_HEIGHT) / 2.0)),
                    ..default()
                },
            ));
        }
        (false, Some(entity)) => commands.entity(entity).despawn(),
        _ => {}
    }
}

/// How far under its centre a body reaches on the plane: its outer ring or its frame.
fn body_extent(party: Party, bodies: &[BodyPicture]) -> f32 {
    match party {
        Party::Treasury | Party::Fund => FRAME_EXTENT,
        Party::Workplace(_) | Party::Household(_) => bodies
            .iter()
            .find(|body| body.party == party)
            .map_or(CORE_EXTENT, |body| {
                [body.hours_ring, body.money_ring]
                    .into_iter()
                    .flatten()
                    .fold(CORE_EXTENT, f32::max)
                    + RING_HALF_LINE
            }),
    }
}

/// Stand each body's label 10 px under the projected lowest point of its outer ring or frame.
/// The label's top edge in window pixels. `world_to_viewport` already adds the
/// viewport origin (which sits under the header), so the header is not added again.
fn label_top(viewport_y: f32) -> f32 {
    viewport_y + LABEL_GAP
}

pub fn place_labels(
    cameras: Query<(&Camera, &GlobalTransform), With<SceneCamera>>,
    shown: Res<SceneShown>,
    mut labels: Query<(&BodyLabel, &mut Node, &mut Visibility)>,
) {
    let Ok((camera, transform)) = cameras.single() else {
        return;
    };
    let bodies = shown.0.as_ref().map_or(&[][..], |picture| &picture.bodies);
    for (label, mut node, mut visibility) in &mut labels {
        let Some((_, at)) = scene::body_points()
            .into_iter()
            .find(|(p, _)| *p == label.0)
        else {
            continue;
        };
        let lowest =
            hypergraph_rs_bevy::plan_to_scene(at, 0.0) + Vec3::Z * body_extent(label.0, bodies);
        match camera.world_to_viewport(transform, lowest) {
            Ok(point) => {
                node.left = px(point.x);
                node.top = px(label_top(point.y));
                visibility.set_if_neq(Visibility::Inherited);
            }
            Err(_) => {
                visibility.set_if_neq(Visibility::Hidden);
            }
        }
    }
}

#[cfg(test)]
mod label_tests {
    use super::*;

    #[test]
    fn label_sits_ten_pixels_under_the_projected_point_without_the_header_added_twice() {
        assert_eq!(label_top(100.0), 110.0);
    }
}
