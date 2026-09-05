//! Native observer shell. All economic readings come from one installed frame.

use std::fmt::Write as _;

use babylon_persistence::ObserverEconomySnapshotV1;
use bevy::ecs::system::SystemParam;
use bevy::prelude::*;
use bevy::window::PrimaryWindow;

use crate::atlas::CountyAtlas;
use crate::decision_surface::{DeclaredSurface, SurfaceId};
use crate::map::{HoveredCounty, SelectedCounty};
use crate::map_economy_lens::{
    project_map_lens, CountyLensReading, EconomyMetric, MapLens, MaterialLensKind,
};
use crate::observer::ObserverSession;
use crate::observer_controls::{availability, turn_presentation, ControlAvailability};
use crate::observer_layout::{ObserverLayout, ObserverRegion};
use crate::observer_theme as theme;

pub(crate) const OBSERVER_PANEL_BOTTOM: f32 = 96.0;

#[derive(Resource, Default)]
pub struct ObserverFrame(pub Option<ObserverEconomySnapshotV1>);

impl ObserverFrame {
    /// Returns only the exact installed week and capability for this session.
    /// Async generation is checked before installation by the IO task.
    #[must_use]
    pub fn for_session(&self, session: &ObserverSession) -> Option<&ObserverEconomySnapshotV1> {
        self.0.as_ref().filter(|frame| {
            frame.campaign_id == session.campaign.as_uuid().to_string()
                && frame.resolve_tick == session.viewed_tick
                && matches!(
                    (session.perspective, frame.visibility),
                    (
                        crate::observer::Perspective::FullObserver,
                        babylon_persistence::ObserverVisibilityV1::FullObserver
                    ) | (
                        crate::observer::Perspective::PlayerKnowledge,
                        babylon_persistence::ObserverVisibilityV1::KnownPreview
                    )
                )
                && session
                    .foundation_digest
                    .as_ref()
                    .is_none_or(|digest| *digest == frame.foundation_digest)
                && (session.viewed_tick != session.durable_tick
                    || frame.tick_content_hash == session.content_hash)
        })
    }
}

// These are independent presentation preferences and disclosures, not transport phases.
#[allow(clippy::struct_excessive_bools)]
#[derive(Resource)]
pub struct ObserverUiState {
    pub lens: MapLens,
    pub archive_open: bool,
    pub reduced_motion: bool,
    pub menu_open: bool,
    pub splash_visible: bool,
    pub history_open: bool,
    pub stop_on_delivery: bool,
    pub comparison_open: bool,
    pub disclosure: Option<ObserverDisclosure>,
    pub evidence_open: bool,
}
impl Default for ObserverUiState {
    fn default() -> Self {
        Self {
            lens: MapLens::default(),
            archive_open: false,
            reduced_motion: false,
            menu_open: true,
            splash_visible: true,
            history_open: false,
            stop_on_delivery: false,
            comparison_open: false,
            disclosure: None,
            evidence_open: false,
        }
    }
}

#[derive(Resource, Default)]
pub struct ObserverViewport(pub Option<Rect>);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ObserverDisclosure {
    Time,
    Lens,
}

/// Short, non-sensitive explanations for declined controls.
#[derive(Resource, Default)]
pub(crate) struct ObserverFeedback {
    pub message: Option<&'static str>,
    pub revision: u64,
    pub expires_at: f64,
}
impl ObserverFeedback {
    pub(crate) fn reject(&mut self, reason: &'static str, now: f64) {
        self.message = Some(reason);
        self.revision = self.revision.wrapping_add(1);
        self.expires_at = now + 4.0;
    }
}

#[derive(Message, Clone, Copy, Debug, PartialEq, Eq)]
pub enum ObserverCommand {
    TogglePlay,
    Step,
    Speed,
    Perspective,
    PreviousWeek,
    NextWeek,
    Live,
    Lens(EconomyMetric),
    MaterialLens(MaterialLensKind),
    CycleGood(bool),
    Archive,
    Menu,
    NewCampaign,
    NewDelayedCampaign,
    ReopenCampaign,
    Quit,
    UiScale,
    ReducedMotion,
    MusicVolume,
    EffectsVolume,
    MusicTrack,
    History,
    StopOnDelivery,
    Disclosure(ObserverDisclosure),
    Evidence,
}

#[derive(Component, Clone, Copy)]
struct ObserverButton {
    command: ObserverCommand,
    in_menu: bool,
}

#[derive(Component)]
struct ObserverButtonCaption(ObserverCommand);
#[derive(Component)]
struct ControlDrawer(ObserverDisclosure);
#[derive(Component)]
struct HistoryControls;
#[derive(Component)]
struct VerificationDetails;
#[derive(Component)]
struct ControlHint;

#[derive(Component, Clone, Copy)]
enum ObserverText {
    Clock,
    Identity,
    Status,
    Legend,
    County,
    Measures,
    Hover,
    Audio,
    Evidence,
    EvidenceDetails,
    Production,
    Source,
}

#[derive(Component)]
struct ObserverInspector;
#[derive(Component)]
struct MapLensControls;
#[derive(Component)]
struct CircuitGuide;

#[derive(Component)]
pub struct ObserverMenu;
/// The saved-campaign browser occupies its own bounded menu column.
#[derive(Component)]
pub struct ObserverCampaignCatalog;
#[derive(Component)]
struct ObserverSplash;
#[derive(Component)]
struct SplashText;

/// Full-window UI camera; the geography camera owns only the map viewport.
#[derive(Component)]
pub struct ObserverUiCamera;

fn label(text: impl Into<String>, size: f32, color: Color) -> impl Bundle {
    (
        Text::new(text),
        TextFont {
            font_size: size,
            ..default()
        },
        TextColor(color),
        DeclaredSurface::new(SurfaceId::ObserverShell),
    )
}

fn block_label(text: impl Into<String>, size: f32, color: Color) -> impl Bundle {
    (
        label(text, size, color),
        Node {
            min_width: px(0),
            max_width: percent(100),
            flex_shrink: 0.0,
            ..default()
        },
    )
}

/// Preserve every identity character while bounding the inspector's line width.
fn wrapped_identity(value: &str) -> String {
    let mut wrapped = String::with_capacity(value.len() + value.len() / 24);
    for (index, character) in value.chars().enumerate() {
        if index > 0 && index % 24 == 0 {
            wrapped.push('\n');
        }
        wrapped.push(character);
    }
    wrapped
}

fn button(parent: &mut ChildSpawnerCommands, text: &str, command: ObserverCommand) {
    scoped_button(parent, text, command, false);
}

fn scoped_button(
    parent: &mut ChildSpawnerCommands,
    text: &str,
    command: ObserverCommand,
    in_menu: bool,
) {
    parent
        .spawn((
            Button,
            Node {
                width: match command {
                    ObserverCommand::TogglePlay => px(200),
                    ObserverCommand::Step => px(174),
                    _ => Val::Auto,
                },
                justify_content: JustifyContent::Center,
                padding: UiRect::axes(px(12), px(8)),
                border: match command {
                    ObserverCommand::TogglePlay | ObserverCommand::Step => UiRect {
                        left: px(1),
                        right: px(1),
                        top: px(1),
                        bottom: px(3),
                    },
                    _ => UiRect::bottom(px(2)),
                },
                border_radius: BorderRadius::ZERO,
                flex_shrink: 0.0,
                min_width: px(0),
                ..default()
            },
            BackgroundColor(theme::PANEL),
            BorderColor::all(theme::GRAY),
            ObserverButton { command, in_menu },
            DeclaredSurface::new(SurfaceId::ObserverShell),
        ))
        .with_child((
            label(text, 13.0, theme::PAPER),
            ObserverButtonCaption(command),
        ));
}

fn row() -> Node {
    Node {
        column_gap: px(8),
        align_items: AlignItems::Center,
        min_width: px(0),
        ..default()
    }
}

fn spawn_hud(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                left: px(16),
                right: px(16),
                top: px(12),
                height: px(76),
                padding: UiRect::axes(px(16), px(10)),
                flex_direction: FlexDirection::Column,
                row_gap: px(8),
                ..default()
            },
            BackgroundColor(theme::INK),
            ZIndex(8),
            DeclaredSurface::new(SurfaceId::ObserverShell),
        ))
        .with_children(|hud| {
            hud.spawn(row()).with_children(|bar| {
                bar.spawn(label("BABYLON", 23.0, theme::YELLOW));
                bar.spawn((
                    label("Opening campaign", 16.0, theme::PAPER),
                    Node {
                        width: px(160),
                        flex_shrink: 0.0,
                        ..default()
                    },
                    ObserverText::Clock,
                ));
                bar.spawn(Node {
                    flex_grow: 1.0,
                    ..default()
                });
                button(bar, "Run month", ObserverCommand::TogglePlay);
                button(
                    bar,
                    "Time +",
                    ObserverCommand::Disclosure(ObserverDisclosure::Time),
                );
                bar.spawn(Node {
                    width: px(12),
                    ..default()
                });
                crate::production::button(
                    bar,
                    "WORK [P]",
                    crate::production::ProductionCommand::Open,
                );
                crate::production::button(
                    bar,
                    "WORLD [M]",
                    crate::production::ProductionCommand::Map,
                );
                button(bar, "Menu [Esc]", ObserverCommand::Menu);
            });
            hud.spawn(row()).with_children(|bar| {
                bar.spawn((label("", 13.0, theme::YELLOW), ObserverText::Status));
                bar.spawn(Node {
                    flex_grow: 1.0,
                    ..default()
                });
                bar.spawn((label("", 11.0, theme::GRAY), ObserverText::Identity));
            });
        });
}

fn spawn_inspector(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                padding: UiRect::all(px(12)),
                column_gap: px(24),
                border: UiRect::top(px(2)),
                overflow: Overflow::scroll_y(),
                ..default()
            },
            ObserverRegion::Context,
            BackgroundColor(theme::INK.with_alpha(0.97)),
            BorderColor::all(theme::PAPER.with_alpha(0.8)),
            ZIndex(6),
            ObserverInspector,
            DeclaredSurface::new(SurfaceId::ObserverShell),
        ))
        .with_children(|panel| {
            panel.spawn(context_column()).with_children(|local| {
                local.spawn(row()).with_children(|heading| {
                    heading.spawn((
                        label("Select a county", 20.0, theme::PAPER),
                        Node {
                            min_width: px(0),
                            flex_basis: px(0),
                            flex_grow: 1.0,
                            ..default()
                        },
                        ObserverText::County,
                    ));
                    crate::production::button(
                        heading,
                        "Follow [P]",
                        crate::production::ProductionCommand::Open,
                    );
                });
                local.spawn((
                    block_label("", 13.0, theme::PAPER),
                    ObserverText::Production,
                ));
            });
            panel.spawn(context_column()).with_children(|detail| {
                detail.spawn((block_label("", 16.0, theme::YELLOW), ObserverText::Measures));
                detail.spawn((block_label("", 11.0, theme::GRAY), ObserverText::Source));
                button(detail, "Cited Archive [I]", ObserverCommand::Archive);
                detail.spawn((block_label("", 11.0, theme::GRAY), ObserverText::Evidence));
            });
        });
}

pub(crate) fn context_column() -> Node {
    Node {
        flex_basis: px(0),
        flex_grow: 1.0,
        min_width: px(0),
        flex_direction: FlexDirection::Column,
        row_gap: px(8),
        ..default()
    }
}

fn spawn_footer(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                padding: UiRect::all(px(8)),
                column_gap: px(12),
                align_items: AlignItems::Center,
                overflow: Overflow::scroll_x(),
                ..default()
            },
            BackgroundColor(theme::INK),
            ObserverRegion::Footer,
            ZIndex(8),
            DeclaredSurface::new(SurfaceId::ObserverShell),
        ))
        .with_children(|bar| {
            button(bar, "Trends [H]", ObserverCommand::History);
            bar.spawn((row(), HistoryControls))
                .with_children(|controls| {
                    button(controls, "< Week", ObserverCommand::PreviousWeek);
                    button(controls, "Week >", ObserverCommand::NextWeek);
                    button(controls, "Return Live", ObserverCommand::Live);
                });
            bar.spawn((row(), MapLensControls))
                .with_children(|controls| {
                    button(
                        controls,
                        "Map lens +",
                        ObserverCommand::Disclosure(ObserverDisclosure::Lens),
                    );
                    button(controls, "< Good", ObserverCommand::CycleGood(true));
                    button(controls, "Good >", ObserverCommand::CycleGood(false));
                    controls.spawn((label("", 12.0, theme::PAPER), ObserverText::Legend));
                });
            bar.spawn((
                label(
                    "Trace suppliers and buyers. Inspect the log for consequences.",
                    13.0,
                    theme::GRAY,
                ),
                CircuitGuide,
            ));
        });
}

fn spawn_drawers(commands: &mut Commands) {
    for disclosure in [ObserverDisclosure::Time, ObserverDisclosure::Lens] {
        let node = Node {
            position_type: PositionType::Absolute,
            left: px(16),
            width: px(720),
            top: if disclosure == ObserverDisclosure::Time {
                px(112)
            } else {
                Val::Auto
            },
            bottom: if disclosure == ObserverDisclosure::Lens {
                px(OBSERVER_PANEL_BOTTOM)
            } else {
                Val::Auto
            },
            padding: UiRect::all(px(16)),
            row_gap: px(12),
            flex_direction: FlexDirection::Column,
            border: UiRect::top(px(3)),
            display: Display::None,
            ..default()
        };
        commands.spawn((node, BackgroundColor(theme::INK), BorderColor::all(theme::YELLOW),
            ZIndex(12), ControlDrawer(disclosure), DeclaredSurface::new(SurfaceId::ObserverShell),
        )).with_children(|panel| {
            panel.spawn(row()).with_children(|bar| {
                bar.spawn(label(if disclosure == ObserverDisclosure::Time { "CAMPAIGN TIME" } else { "MAP LENS" }, 17.0, theme::YELLOW));
                bar.spawn(Node { flex_grow: 1.0, ..default() });
                button(bar, "Close", ObserverCommand::Disclosure(disclosure));
            });
            if disclosure == ObserverDisclosure::Time {
                panel.spawn(block_label(crate::observer_controls::MONTH_ADVANCE_HELP, 14.0, theme::PAPER));
                panel.spawn(row()).with_children(|bar| {
                    button(bar, "Advance one week", ObserverCommand::Step);
                    button(bar, "Speed", ObserverCommand::Speed);
                    button(bar, "Stop on delivery", ObserverCommand::StopOnDelivery);
                });
                panel.spawn(block_label("Space: run / pause month     Enter: advance one week     H: inspect trends", 12.0, theme::GRAY));
            } else {
                panel.spawn(row()).with_children(|bar| {
                    for (kind, title) in [(MaterialLensKind::ProducedThisWeek,"Production [5]"), (MaterialLensKind::OnHand,"Inventory [6]"), (MaterialLensKind::InboundInTransit,"Inbound [7]")] {
                        button(bar, title, ObserverCommand::MaterialLens(kind));
                    }
                });
                panel.spawn(block_label("Observed county context / BLS QCEW 2024", 12.0, theme::GRAY));
                panel.spawn(row()).with_children(|bar| {
                    for (metric, title) in EconomyMetric::ALL.into_iter().zip(["Jobs [1]","Payroll [2]","Weekly wage [3]","Establishments [4]"]) {
                        button(bar, title, ObserverCommand::Lens(metric));
                    }
                });
                panel.spawn(block_label(crate::observer_map3d::MAP_VIEW_HELP, 12.0, theme::GRAY));
            }
        });
    }
}

fn spawn_menu(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                left: percent(12),
                right: percent(12),
                top: px(112),
                bottom: px(40),
                padding: UiRect::all(px(20)),
                row_gap: px(14),
                flex_direction: FlexDirection::Column,
                overflow: Overflow::clip(),
                border: UiRect::all(px(2)),
                ..default()
            },
            BackgroundColor(theme::INK),
            BorderColor::all(theme::YELLOW),
            ZIndex(20),
            Visibility::Hidden,
            ObserverMenu,
            DeclaredSurface::new(SurfaceId::ObserverShell),
        ))
        .with_children(|panel| {
            panel.spawn(block_label("C A M P A I G N", 23.0, theme::YELLOW));
            panel
                .spawn(Node {
                    flex_grow: 1.0,
                    min_height: px(0),
                    min_width: px(0),
                    column_gap: px(24),
                    ..default()
                })
                .with_children(|columns| {
                    columns.spawn(menu_column()).with_children(menu_campaign);
                    columns.spawn(menu_column()).with_children(menu_settings);
                });
            panel.spawn(row()).with_children(|bar| {
                bar.spawn(label(
                    "Committed weeks are saved automatically.",
                    12.0,
                    theme::GRAY,
                ));
                bar.spawn(Node {
                    flex_grow: 1.0,
                    ..default()
                });
                scoped_button(bar, "Quit game [Q]", ObserverCommand::Quit, true);
            });
        });
}

fn menu_column() -> Node {
    Node {
        flex_grow: 1.0,
        flex_basis: px(0),
        min_width: px(0),
        min_height: px(0),
        flex_direction: FlexDirection::Column,
        row_gap: px(8),
        overflow: Overflow::scroll_y(),
        ..default()
    }
}

fn menu_campaign(panel: &mut ChildSpawnerCommands) {
    for (title, command) in [
        ("Continue [C]", ObserverCommand::Menu),
        (
            "Reopen committed campaign [R]",
            ObserverCommand::ReopenCampaign,
        ),
        ("New Michigan campaign [N]", ObserverCommand::NewCampaign),
        (
            "New delivery-delay scenario [D]",
            ObserverCommand::NewDelayedCampaign,
        ),
    ] {
        scoped_button(panel, title, command, true);
    }
    panel.spawn(block_label(
        "A new campaign preserves your existing world.",
        12.0,
        theme::GRAY,
    ));
    panel.spawn((
        Node {
            min_width: px(0),
            flex_shrink: 0.0,
            flex_direction: FlexDirection::Column,
            row_gap: px(8),
            margin: UiRect::top(px(10)),
            ..default()
        },
        ObserverCampaignCatalog,
    ));
}

fn menu_settings(panel: &mut ChildSpawnerCommands) {
    panel.spawn(block_label("PRESENTATION / SOUND", 17.0, theme::YELLOW));
    for (title, command) in [
        ("Observer perspective [K]", ObserverCommand::Perspective),
        ("Interface size [U]", ObserverCommand::UiScale),
        ("Reduced motion [M]", ObserverCommand::ReducedMotion),
        ("Music volume / mute [B]", ObserverCommand::MusicVolume),
        ("Sound effects / mute [F]", ObserverCommand::EffectsVolume),
        ("Change theme [J]", ObserverCommand::MusicTrack),
    ] {
        scoped_button(panel, title, command, true);
    }
    panel.spawn((block_label("", 13.0, theme::YELLOW), ObserverText::Audio));
    scoped_button(
        panel,
        "Verification details +",
        ObserverCommand::Evidence,
        true,
    );
    panel.spawn((
        block_label("", 11.0, theme::GRAY),
        ObserverText::EvidenceDetails,
        VerificationDetails,
    ));
    panel.spawn(block_label(
        "OBSERVE / TRACE / COMPARE\nPlayer interventions are unavailable in observer mode.",
        12.0,
        theme::GRAY,
    ));
}

fn spawn_splash(commands: &mut Commands) {
    commands
        .spawn((
            Button,
            Node {
                position_type: PositionType::Absolute,
                left: px(0),
                right: px(0),
                top: px(0),
                bottom: px(0),
                align_items: AlignItems::Center,
                justify_content: JustifyContent::Center,
                flex_direction: FlexDirection::Column,
                row_gap: px(32),
                ..default()
            },
            BackgroundColor(theme::INK),
            ZIndex(100),
            ObserverSplash,
            DeclaredSurface::new(SurfaceId::TitleLockup),
        ))
        .with_children(|screen| {
            screen.spawn((label("PERSEPHONE RASKOVA", 44.0, theme::PAPER), SplashText));
            screen.spawn(label("A LIVING POLITICAL ECONOMY", 16.0, theme::YELLOW));
            screen.spawn(label(
                "Press any key or click to continue",
                12.0,
                theme::GRAY,
            ));
        });
}

fn spawn_shell(
    mut commands: Commands,
    atlas: Res<CountyAtlas>,
    mut selected: ResMut<SelectedCounty>,
) {
    if selected.0.is_none() {
        selected.0 = (0..atlas.len()).find(|index| {
            atlas
                .county(*index)
                .is_some_and(|county| county.fips == "26163")
        });
    }
    commands.spawn((
        Camera2d,
        Camera {
            order: 10,
            clear_color: ClearColorConfig::None,
            ..default()
        },
        bevy::camera::visibility::RenderLayers::layer(31),
        IsDefaultUiCamera,
        ObserverUiCamera,
    ));
    spawn_hud(&mut commands);
    spawn_inspector(&mut commands);
    spawn_footer(&mut commands);
    spawn_drawers(&mut commands);
    spawn_menu(&mut commands);
    spawn_splash(&mut commands);
    commands.spawn((
        label("", 14.0, theme::PAPER),
        Node {
            position_type: PositionType::Absolute,
            left: px(30),
            top: px(120),
            ..default()
        },
        ZIndex(5),
        ObserverText::Hover,
    ));
    commands.spawn((
        label("", 13.0, theme::YELLOW),
        Node {
            position_type: PositionType::Absolute,
            left: px(32),
            bottom: px(84),
            padding: UiRect::all(px(8)),
            ..default()
        },
        BackgroundColor(theme::INK),
        ZIndex(30),
        ControlHint,
    ));
}

fn splash(
    time: Res<Time>,
    keys: Res<ButtonInput<KeyCode>>,
    mouse: Res<ButtonInput<MouseButton>>,
    mut ui: ResMut<ObserverUiState>,
    mut elapsed: Local<f32>,
    mut roots: Query<&mut Visibility, With<ObserverSplash>>,
    mut titles: Query<&mut Text, With<SplashText>>,
) {
    if !ui.splash_visible {
        return;
    }
    *elapsed += time.delta_secs();
    if keys.get_just_pressed().next().is_some()
        || mouse.get_just_pressed().next().is_some()
        || *elapsed >= 2.4
    {
        ui.splash_visible = false;
        for mut visibility in &mut roots {
            *visibility = Visibility::Hidden;
        }
    } else if *elapsed >= 1.2 {
        for mut title in &mut titles {
            if title.0 != "GOLDEN MONKEY" {
                title.0 = "GOLDEN MONKEY".into();
            }
        }
    }
}

#[derive(EntityEvent)]
#[entity_event(propagate, auto_propagate)]
struct ScrollPanel {
    entity: Entity,
    delta: f32,
}

fn scroll_input(
    mut wheel: MessageReader<bevy::input::mouse::MouseWheel>,
    hover: Res<bevy::picking::hover::HoverMap>,
    mut commands: Commands,
) {
    for event in wheel.read() {
        let delta = -event.y
            * if event.unit == bevy::input::mouse::MouseScrollUnit::Line {
                28.0
            } else {
                1.0
            };
        for map in hover.values() {
            for entity in map.keys() {
                commands.trigger(ScrollPanel {
                    entity: *entity,
                    delta,
                });
            }
        }
    }
}

fn scroll_panel(
    mut event: On<ScrollPanel>,
    mut nodes: Query<(&Node, &ComputedNode, &mut ScrollPosition)>,
) {
    let Ok((node, computed, mut position)) = nodes.get_mut(event.entity) else {
        return;
    };
    if node.overflow.y != OverflowAxis::Scroll {
        return;
    }
    let maximum = ((computed.content_size().y - computed.size().y)
        * computed.inverse_scale_factor())
    .max(0.0);
    let next = (position.y + event.delta).clamp(0.0, maximum);
    if next.to_bits() != position.y.to_bits() {
        position.y = next;
        event.propagate(false);
    }
}

fn pointer_buttons(
    buttons: Query<(&Interaction, &ObserverButton), Changed<Interaction>>,
    ui: Res<ObserverUiState>,
    mut commands: MessageWriter<ObserverCommand>,
) {
    if ui.splash_visible || ui.comparison_open {
        return;
    }
    for (interaction, button) in &buttons {
        if *interaction == Interaction::Pressed && button.in_menu == ui.menu_open {
            commands.write(button.command);
        }
    }
}

type PaintedButtons<'w, 's> = Query<
    'w,
    's,
    (
        &'static Interaction,
        &'static ObserverButton,
        &'static mut BackgroundColor,
        &'static mut BorderColor,
        &'static mut Node,
    ),
    Without<ControlHint>,
>;
type HintText<'w, 's> = Query<
    'w,
    's,
    (&'static mut Text, &'static mut Node),
    (
        With<ControlHint>,
        Without<ObserverButtonCaption>,
        Without<ObserverButton>,
    ),
>;

#[derive(SystemParam)]
struct ButtonPaint<'w, 's> {
    buttons: PaintedButtons<'w, 's>,
    captions: Query<
        'w,
        's,
        (
            &'static ObserverButtonCaption,
            &'static mut Text,
            &'static mut TextColor,
        ),
        Without<ControlHint>,
    >,
    hints: HintText<'w, 's>,
}

fn caption(
    command: ObserverCommand,
    state: &ObserverSession,
    ui: &ObserverUiState,
) -> Option<String> {
    Some(match command {
        ObserverCommand::TogglePlay => format!("{} [Space]", turn_presentation(state).play_label),
        ObserverCommand::Step => turn_presentation(state).step_label,
        ObserverCommand::Quit => if state.quit_requested {
            "Closing game..."
        } else {
            "Quit game [Q]"
        }
        .to_owned(),
        ObserverCommand::Speed => format!("Speed: {} week(s) / sec", state.weeks_per_second),
        ObserverCommand::StopOnDelivery => format!(
            "Stop on delivery: {}",
            if ui.stop_on_delivery { "ON" } else { "OFF" }
        ),
        ObserverCommand::History => {
            format!("History {} [H]", if ui.history_open { "-" } else { "+" })
        }
        ObserverCommand::Perspective => state.perspective.label().to_owned(),
        ObserverCommand::Evidence => format!(
            "Verification details {}",
            if ui.evidence_open { "-" } else { "+" }
        ),
        _ => return None,
    })
}

fn paint_buttons(
    ui: Res<ObserverUiState>,
    state: Res<ObserverSession>,
    view: Res<crate::production::PrimaryView>,
    feedback: Res<ObserverFeedback>,
    mut paint: ButtonPaint,
) {
    let mut hint = feedback.message;
    for (interaction, button, mut background, mut border, mut node) in &mut paint.buttons {
        if matches!(button.command, ObserverCommand::CycleGood(_)) {
            let display = if *view == crate::production::PrimaryView::Map
                && matches!(&ui.lens, MapLens::Material { .. })
            {
                Display::Flex
            } else {
                Display::None
            };
            if node.display != display {
                node.display = display;
            }
        }
        let available = availability(button.command, &state);
        let active_scope =
            !ui.splash_visible && !ui.comparison_open && button.in_menu == ui.menu_open;
        if active_scope && *interaction != Interaction::None {
            if let ControlAvailability::Disabled(reason) = available {
                hint = Some(reason);
            }
        }
        let selected = match (button.command, &ui.lens) {
            (ObserverCommand::Lens(metric), MapLens::Qcew(current)) => metric == *current,
            (ObserverCommand::MaterialLens(kind), MapLens::Material { kind: current, .. }) => {
                kind == *current
            }
            (ObserverCommand::Disclosure(value), _) => ui.disclosure == Some(value),
            (ObserverCommand::History, _) => ui.history_open,
            (ObserverCommand::Archive, _) => ui.archive_open,
            _ => false,
        };
        let enabled = active_scope && available == ControlAvailability::Enabled;
        let next = match interaction {
            _ if !enabled => theme::INK,
            Interaction::Pressed => theme::RED.with_alpha(0.5),
            Interaction::Hovered => theme::YELLOW.with_alpha(0.25),
            Interaction::None if selected => theme::YELLOW.with_alpha(0.2),
            Interaction::None => theme::PANEL,
        };
        background.set_if_neq(BackgroundColor(next));
        border.set_if_neq(BorderColor::all(if !enabled {
            theme::GRAY.with_alpha(0.3)
        } else if selected {
            theme::YELLOW
        } else {
            theme::GRAY
        }));
    }
    for (marker, mut text, mut color) in &mut paint.captions {
        if state.is_changed() || ui.is_changed() || text.is_added() {
            if let Some(value) = caption(marker.0, &state, &ui) {
                text.set_if_neq(Text::new(value));
            }
        }
        color.set_if_neq(TextColor(
            if availability(marker.0, &state) == ControlAvailability::Enabled {
                theme::PAPER
            } else {
                theme::GRAY.with_alpha(0.65)
            },
        ));
    }
    for (mut text, mut node) in &mut paint.hints {
        text.set_if_neq(Text::new(hint.unwrap_or_default()));
        let display = if hint.is_some() && !ui.splash_visible {
            Display::Flex
        } else {
            Display::None
        };
        if node.display != display {
            node.display = display;
        }
    }
}

type DisclosureRows<'w, 's> = Query<
    'w,
    's,
    (
        &'static mut Node,
        Option<&'static MapLensControls>,
        Option<&'static CircuitGuide>,
        Option<&'static ControlDrawer>,
        Option<&'static HistoryControls>,
        Option<&'static VerificationDetails>,
    ),
    Or<(
        With<MapLensControls>,
        With<CircuitGuide>,
        With<ControlDrawer>,
        With<HistoryControls>,
        With<VerificationDetails>,
    )>,
>;

fn paint_view_controls(
    view: Res<crate::production::PrimaryView>,
    ui: Res<ObserverUiState>,
    state: Res<ObserverSession>,
    mut rows: DisclosureRows,
) {
    if !(view.is_changed() || ui.is_changed() || state.is_changed()) {
        return;
    }
    for (mut node, map, circuit, drawer, history, evidence) in &mut rows {
        let visible = if let Some(drawer) = drawer {
            ui.disclosure == Some(drawer.0)
                && !ui.menu_open
                && !ui.splash_visible
                && !ui.comparison_open
                && (drawer.0 != ObserverDisclosure::Lens
                    || *view == crate::production::PrimaryView::Map)
        } else if map.is_some() {
            *view == crate::production::PrimaryView::Map
                && !ui.history_open
                && state.viewed_tick == state.durable_tick
        } else if circuit.is_some() {
            *view == crate::production::PrimaryView::Production
                && !ui.history_open
                && state.viewed_tick == state.durable_tick
        } else if history.is_some() {
            ui.history_open || state.viewed_tick < state.durable_tick
        } else {
            evidence.is_some() && ui.evidence_open
        };
        node.display = if visible {
            Display::Flex
        } else {
            Display::None
        };
    }
}

fn expire_feedback(time: Res<Time>, mut feedback: ResMut<ObserverFeedback>) {
    if feedback.message.is_some() && time.elapsed_secs_f64() >= feedback.expires_at {
        feedback.message = None;
    }
}

fn keyboard(
    keys: Res<ButtonInput<KeyCode>>,
    ui: Res<ObserverUiState>,
    view: Res<crate::production::PrimaryView>,
    atlas: Res<CountyAtlas>,
    mut selected: ResMut<SelectedCounty>,
    mut commands: MessageWriter<ObserverCommand>,
) {
    if ui.splash_visible || ui.comparison_open {
        return;
    }
    if !ui.menu_open && keys.just_pressed(KeyCode::Escape) {
        commands.write(
            ui.disclosure
                .map_or(ObserverCommand::Menu, ObserverCommand::Disclosure),
        );
        return;
    }
    if ui.menu_open {
        for (key, command) in [
            (KeyCode::Escape, ObserverCommand::Menu),
            (KeyCode::KeyC, ObserverCommand::Menu),
            (KeyCode::KeyN, ObserverCommand::NewCampaign),
            (KeyCode::KeyR, ObserverCommand::ReopenCampaign),
            (KeyCode::KeyQ, ObserverCommand::Quit),
            (KeyCode::KeyD, ObserverCommand::NewDelayedCampaign),
            (KeyCode::KeyU, ObserverCommand::UiScale),
            (KeyCode::KeyM, ObserverCommand::ReducedMotion),
            (KeyCode::KeyB, ObserverCommand::MusicVolume),
            (KeyCode::KeyF, ObserverCommand::EffectsVolume),
            (KeyCode::KeyJ, ObserverCommand::MusicTrack),
            (KeyCode::KeyE, ObserverCommand::StopOnDelivery),
            (KeyCode::KeyK, ObserverCommand::Perspective),
        ] {
            if keys.just_pressed(key) {
                commands.write(command);
            }
        }
        return;
    }
    for (key, command) in [
        (KeyCode::Space, ObserverCommand::TogglePlay),
        (KeyCode::Enter, ObserverCommand::Step),
        (KeyCode::BracketLeft, ObserverCommand::PreviousWeek),
        (KeyCode::BracketRight, ObserverCommand::NextWeek),
        (KeyCode::KeyK, ObserverCommand::Perspective),
        (KeyCode::KeyI, ObserverCommand::Archive),
        (KeyCode::KeyT, ObserverCommand::Speed),
        (KeyCode::KeyH, ObserverCommand::History),
        (
            KeyCode::Digit5,
            ObserverCommand::MaterialLens(MaterialLensKind::ProducedThisWeek),
        ),
        (
            KeyCode::Digit6,
            ObserverCommand::MaterialLens(MaterialLensKind::OnHand),
        ),
        (
            KeyCode::Digit7,
            ObserverCommand::MaterialLens(MaterialLensKind::InboundInTransit),
        ),
        (KeyCode::Comma, ObserverCommand::CycleGood(true)),
        (KeyCode::Period, ObserverCommand::CycleGood(false)),
        (
            KeyCode::Digit1,
            ObserverCommand::Lens(EconomyMetric::Employment),
        ),
        (
            KeyCode::Digit2,
            ObserverCommand::Lens(EconomyMetric::Payroll),
        ),
        (
            KeyCode::Digit3,
            ObserverCommand::Lens(EconomyMetric::WeeklyWage),
        ),
        (
            KeyCode::Digit4,
            ObserverCommand::Lens(EconomyMetric::Establishments),
        ),
    ] {
        if keys.just_pressed(key) {
            commands.write(command);
        }
    }
    if *view == crate::production::PrimaryView::Map
        && (keys.just_pressed(KeyCode::ArrowLeft) || keys.just_pressed(KeyCode::ArrowRight))
    {
        let counties: Vec<usize> = (0..atlas.len())
            .filter(|index| {
                atlas
                    .county(*index)
                    .is_some_and(|county| county.fips.starts_with("26"))
            })
            .collect();
        if !counties.is_empty() {
            let current = counties.iter().position(|index| Some(*index) == selected.0);
            let next = current.map_or(0, |index| {
                if keys.just_pressed(KeyCode::ArrowRight) {
                    (index + 1) % counties.len()
                } else {
                    (index + counties.len() - 1) % counties.len()
                }
            });
            selected.0 = Some(counties[next]);
        }
    }
}

#[must_use]
pub fn grouped(value: u64) -> String {
    let raw = value.to_string();
    let mut text = String::with_capacity(raw.len() + raw.len() / 3);
    for (index, byte) in raw.bytes().enumerate() {
        if index > 0 && (raw.len() - index).is_multiple_of(3) {
            text.push(',');
        }
        text.push(char::from(byte));
    }
    text
}

#[must_use]
pub fn format_lens_reading(reading: CountyLensReading, unit: &str) -> String {
    match reading {
        CountyLensReading::Available(value) => format!("{} {unit}", grouped(value)),
        CountyLensReading::Unavailable(reason) => reason.label().to_owned(),
    }
}

fn local_relationships(
    snapshot: &babylon_persistence::ProductionSnapshotV1,
    county: Option<&str>,
) -> String {
    let Some(county) = county else {
        return "Select a county to follow its work and dependencies.".into();
    };
    let mut sites: Vec<_> = snapshot
        .sites
        .iter()
        .filter(|site| site.county_geoid == county)
        .collect();
    sites.sort_by(|a, b| a.id.cmp(&b.id));
    if sites.is_empty() {
        return "No production relationships are modeled here yet. The Archive contains the observed county context.".into();
    }
    let mut lines = Vec::new();
    for site in sites {
        let relations = crate::production_brief::dependency_sites(site, snapshot);
        if relations.is_empty() {
            lines.push(format!("{} / no disclosed supply relationships", site.name));
        }
        for (direction, other) in relations {
            lines.push(match direction {
                crate::production_brief::DependencyDirection::Upstream => {
                    format!("Industry {} relies on {}", site.industry_code, other.name)
                }
                crate::production_brief::DependencyDirection::Downstream => {
                    format!("Industry {} supplies {}", site.industry_code, other.name)
                }
            });
        }
    }
    format!("DESIGNED COUNTY COHORTS\n{}", lines.join("\n"))
}

#[derive(SystemParam)]
struct ShellState<'w> {
    state: Res<'w, ObserverSession>,
    frame: Res<'w, ObserverFrame>,
    ui: Res<'w, ObserverUiState>,
    view: Res<'w, crate::production::PrimaryView>,
    audio: Res<'w, crate::observer_audio::ObserverAudioSettings>,
    atlas: Res<'w, CountyAtlas>,
    selected: Res<'w, SelectedCounty>,
    hovered: Res<'w, HoveredCounty>,
}

fn repaint(
    shell: ShellState,
    mut texts: Query<(&ObserverText, &mut Text)>,
    mut menus: Query<&mut Visibility, With<ObserverMenu>>,
    mut inspectors: Query<&mut Visibility, (With<ObserverInspector>, Without<ObserverMenu>)>,
) {
    let ShellState {
        state,
        frame,
        ui,
        view,
        audio,
        atlas,
        selected,
        hovered,
    } = shell;
    if !(state.is_changed()
        || frame.is_changed()
        || ui.is_changed()
        || selected.is_changed()
        || hovered.is_changed()
        || view.is_changed()
        || audio.is_changed())
    {
        return;
    }
    let county = selected.0.and_then(|index| atlas.county(index));
    let installed = frame.for_session(&state);
    let lens = project_map_lens(installed, &ui.lens);
    let turn = turn_presentation(&state);
    for (kind, mut text) in &mut texts {
        if matches!(kind, ObserverText::EvidenceDetails) {
            if !ui.evidence_open {
                text.0.clear();
                continue;
            }
            if !(frame.is_changed() || state.is_changed() || ui.is_changed()) {
                continue;
            }
        }
        let value = match kind {
            ObserverText::Clock => turn.period.clone(),
            ObserverText::Identity => format!("{} | {}", state.perspective.label(), if state.archive_verified_tick < state.durable_tick { "Archive catching up" } else { "Archive verified" }),
            ObserverText::Status => turn.status.clone(),
            ObserverText::Legend => match &ui.lens {
                MapLens::Qcew(_) => format!("0..{} {}", lens.maximum().map_or_else(|| "-".into(), grouped), lens.unit),
                MapLens::Material {..} => lens.good_label.as_ref().map_or_else(|| "Material unavailable".into(), |good|format!("{good} ({})", lens.unit)),
            },
            ObserverText::County => county.as_ref().map_or_else(|| "Select a county".into(), |county| county.name.to_owned()),
            ObserverText::Measures => county.as_ref().map_or_else(|| "Select a county to inspect this lens.".into(), |county| format!("{}\n{}", lens.label, format_lens_reading(lens.county(county.fips), &lens.unit))),
            ObserverText::Hover if *view != crate::production::PrimaryView::Map => String::new(),
            ObserverText::Hover => hovered.0.and_then(|index| atlas.county(index)).filter(|county| county.fips.starts_with("26")).map_or_else(String::new, |county| format!("{}\n{}\n{}", county.name, lens.label, format_lens_reading(lens.county(county.fips), &lens.unit))),
            ObserverText::Audio => format!("{} | music {:.0}% | effects {:.0}%\nReduced motion: {} | Stop on delivery: {}", if audio.track==0 {"PHI"}else{"PANOPTICON"},audio.music_volume*100.0,audio.effects_volume*100.0,if ui.reduced_motion {"ON"}else{"OFF"},if ui.stop_on_delivery {"ON"}else{"OFF"}),
            ObserverText::Evidence => format!("Viewing week {} / Archive verified through {}", state.viewed_tick, state.archive_verified_tick),
            ObserverText::EvidenceDetails => installed.map_or_else(String::new, |snapshot| {
                let mut evidence = format!("CAMPAIGN\n{}\n\nCOMMITTED EVIDENCE / WEEK {}\n{}\n\nWORLD IDENTITY\n{}", wrapped_identity(&snapshot.campaign_id), snapshot.resolve_tick, wrapped_identity(snapshot.tick_content_hash.as_deref().unwrap_or(&snapshot.foundation_digest)), snapshot.nominal_world_hash.as_deref().map_or_else(|| "Unavailable in this observation".to_owned(), wrapped_identity));
                if let Some(digest) = snapshot.production_evidence_digest() {
                    let _ = write!(evidence, "\n\nPRODUCTION OBSERVATION\n{}", wrapped_identity(&digest.to_hex()));
                }
                evidence
            }),
            ObserverText::Source => match &ui.lens {
                MapLens::Qcew(_) => "OBSERVED | BLS QCEW | 2024 annual\nJobs are annual averages; weekly wages are means. Monetary values are dollars, not physical output.".into(),
                MapLens::Material {kind, ..} => format!("{}\n{}\nZero is a measured account; unavailable and unmodeled counties have no numeric reading.", lens.evidence, match kind {MaterialLensKind::ProducedThisWeek => "Output in the selected week; foundation has no production receipt.",MaterialLensKind::OnHand => "Stock held at the end of the selected week. Terminal goods remain unsold on hand.",MaterialLensKind::InboundInTransit => "Actual lots destined for this county, counted once. This is not traffic passing through the county."}),
            },
            ObserverText::Production => installed.and_then(|snapshot| snapshot.production.as_ref())
                .map_or_else(|| "Production relationships are unavailable in this observation.".into(), |production|
                    local_relationships(production, county.as_ref().map(|county| county.fips))),
        };
        text.set_if_neq(Text::new(value));
    }
    for mut visibility in &mut menus {
        visibility.set_if_neq(if ui.menu_open && !ui.comparison_open {
            Visibility::Visible
        } else {
            Visibility::Hidden
        });
    }
    for mut visibility in &mut inspectors {
        visibility.set_if_neq(
            if ui.archive_open
                || ui.history_open
                || ui.menu_open
                || ui.splash_visible
                || ui.comparison_open
                || *view == crate::production::PrimaryView::Production
            {
                Visibility::Hidden
            } else {
                Visibility::Visible
            },
        );
    }
}

fn fit_viewport(
    windows: Query<&Window, With<PrimaryWindow>>,
    scale: Res<UiScale>,
    ui: Res<ObserverUiState>,
    mut viewport: ResMut<ObserverViewport>,
    mut regions: Query<(&ObserverRegion, &mut Node)>,
) {
    let Ok(window) = windows.single() else {
        return;
    };
    let layout = ObserverLayout::new(
        Vec2::new(window.width(), window.height()),
        scale.0,
        ui.history_open,
    );
    for (region, mut node) in &mut regions {
        let rect = layout.region(*region);
        let (left, top, width, height) = (
            px(rect.min.x),
            px(rect.min.y),
            px(rect.width()),
            px(rect.height()),
        );
        if node.left != left || node.top != top || node.width != width || node.height != height {
            node.left = left;
            node.top = top;
            node.width = width;
            node.height = height;
        }
    }
    let rect = Rect::from_corners(layout.world.min * scale.0, layout.world.max * scale.0);
    if viewport.0 != Some(rect) {
        viewport.0 = Some(rect);
    }
}

fn reconcile_lens(
    frame: Res<ObserverFrame>,
    session: Res<ObserverSession>,
    mut ui: ResMut<ObserverUiState>,
    mut previous_scope: Local<
        Option<(
            babylon_persistence::CampaignId,
            crate::observer::Perspective,
        )>,
    >,
) {
    let scope = (session.campaign, session.perspective);
    let changed = previous_scope.as_ref() != Some(&scope);
    if !(changed || frame.is_changed() || session.is_changed() || ui.is_changed()) {
        return;
    }
    let mut lens = ui.lens.clone();
    lens.reconcile(frame.for_session(&session), changed);
    if ui.lens != lens {
        ui.lens = lens;
    }
    if changed {
        *previous_scope = Some(scope);
    }
}

pub struct ObserverShellPlugin;
impl Plugin for ObserverShellPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<ObserverFrame>()
            .init_resource::<ObserverUiState>()
            .init_resource::<ObserverViewport>()
            .init_resource::<ObserverFeedback>()
            .add_message::<ObserverCommand>()
            .add_systems(Startup, spawn_shell.after(crate::map::spawn_map_surface))
            .add_systems(
                Update,
                (
                    pointer_buttons,
                    keyboard,
                    scroll_input,
                    splash,
                    expire_feedback,
                )
                    .in_set(crate::observer_io::ObserverSet::Input),
            )
            .add_observer(scroll_panel)
            .add_systems(
                Update,
                reconcile_lens
                    .after(crate::observer_io::ObserverSet::Install)
                    .before(crate::observer_io::ObserverSet::Paint),
            )
            .add_systems(
                Update,
                (fit_viewport, repaint, paint_buttons, paint_view_controls)
                    .in_set(crate::observer_io::ObserverSet::Paint),
            );
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::input::keyboard::{Key, KeyboardInput, NativeKey};
    use bevy::input::{ButtonState, InputPlugin};

    #[test]
    fn shell_startup_waits_for_the_map_atlas_before_selecting_detroit() {
        let mut app = App::new();
        app.add_plugins((MinimalPlugins, bevy::asset::AssetPlugin::default()))
            .insert_resource(ObserverSession::new(
                babylon_persistence::CampaignId::from_uuid(uuid::Uuid::nil()),
            ))
            .add_plugins((crate::map::MapPlugin, ObserverShellPlugin));
        app.finish();
        app.cleanup();
        app.world_mut().run_schedule(Startup);
        let atlas = app.world().resource::<CountyAtlas>();
        let selected = app.world().resource::<SelectedCounty>().0;
        assert_eq!(
            selected
                .and_then(|index| atlas.county(index))
                .map(|county| county.fips),
            Some("26163")
        );
    }

    #[derive(Resource, Default)]
    struct ChangedButtonNodes(Vec<Entity>);

    fn button_paint_fixture() -> (App, [Entity; 3]) {
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .insert_resource(ObserverUiState {
                menu_open: false,
                splash_visible: false,
                ..default()
            })
            .insert_resource(ObserverSession::new(
                babylon_persistence::CampaignId::from_uuid(uuid::Uuid::from_u128(1)),
            ))
            .insert_resource(crate::production::PrimaryView::Map)
            .init_resource::<ObserverFeedback>()
            .init_resource::<ChangedButtonNodes>()
            .add_systems(
                Update,
                (
                    paint_buttons,
                    |nodes: Query<Entity, Changed<Node>>,
                     mut changed: ResMut<ChangedButtonNodes>| {
                        changed.0 = nodes.iter().collect();
                    },
                )
                    .chain(),
            );
        let buttons = [false, true].map(|previous| {
            app.world_mut()
                .spawn((
                    Interaction::None,
                    ObserverButton {
                        command: ObserverCommand::CycleGood(previous),
                        in_menu: false,
                    },
                    BackgroundColor::default(),
                    BorderColor::default(),
                    Node::default(),
                ))
                .id()
        });
        let hint = app
            .world_mut()
            .spawn((ControlHint, Text::default(), Node::default()))
            .id();
        (app, [buttons[0], buttons[1], hint])
    }

    #[test]
    fn unchanged_button_and_hint_visibility_does_not_invalidate_layout() {
        let (mut app, nodes) = button_paint_fixture();
        app.update();
        assert_eq!(app.world().resource::<ChangedButtonNodes>().0.len(), 3);
        app.update();
        assert!(app.world().resource::<ChangedButtonNodes>().0.is_empty());

        for (lens, message, display) in [
            (
                MapLens::Material {
                    kind: MaterialLensKind::OnHand,
                    good: None,
                },
                Some("Wait for the current week to finish."),
                Display::Flex,
            ),
            (MapLens::default(), None, Display::None),
        ] {
            app.world_mut().resource_mut::<ObserverUiState>().lens = lens;
            app.world_mut().resource_mut::<ObserverFeedback>().message = message;
            app.update();
            let changes = &app.world().resource::<ChangedButtonNodes>().0;
            assert_eq!(changes.len(), nodes.len());
            for node in nodes {
                assert!(changes.contains(&node));
                assert_eq!(app.world().get::<Node>(node).unwrap().display, display);
            }
            app.update();
            assert!(app.world().resource::<ChangedButtonNodes>().0.is_empty());
        }

        // Updating a visible explanation changes its text without dirtying its layout node.
        app.world_mut().resource_mut::<ObserverFeedback>().message = Some("Loading week.");
        app.update();
        assert_eq!(app.world().resource::<ChangedButtonNodes>().0, [nodes[2]]);
        app.world_mut().resource_mut::<ObserverFeedback>().message = Some("Finishing week.");
        app.update();
        assert!(app.world().resource::<ChangedButtonNodes>().0.is_empty());
        assert_eq!(
            app.world().get::<Text>(nodes[2]).unwrap().0,
            "Finishing week."
        );
    }

    #[test]
    fn menu_clicks_do_not_activate_world_controls_behind_it() {
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .insert_resource(ObserverUiState {
                splash_visible: false,
                ..default()
            })
            .add_message::<ObserverCommand>()
            .add_systems(Update, pointer_buttons);
        app.world_mut().spawn((
            Interaction::Pressed,
            ObserverButton {
                command: ObserverCommand::Step,
                in_menu: false,
            },
        ));
        let menu = app
            .world_mut()
            .spawn((
                Interaction::Pressed,
                ObserverButton {
                    command: ObserverCommand::Menu,
                    in_menu: true,
                },
            ))
            .id();
        app.update();
        let received: Vec<_> = app
            .world_mut()
            .resource_mut::<Messages<ObserverCommand>>()
            .drain()
            .collect();
        assert_eq!(received, [ObserverCommand::Menu]);
        app.world_mut().resource_mut::<ObserverUiState>().menu_open = false;
        app.world_mut()
            .entity_mut(menu)
            .insert(Interaction::Hovered);
        app.update();
        app.world_mut()
            .entity_mut(menu)
            .insert(Interaction::Pressed);
        app.update();
        assert_eq!(
            app.world_mut()
                .resource_mut::<Messages<ObserverCommand>>()
                .drain()
                .count(),
            0
        );
    }

    #[test]
    fn advanced_controls_start_collapsed_and_only_requested_drawer_is_visible() {
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .insert_resource(ObserverUiState {
                menu_open: false,
                splash_visible: false,
                ..default()
            })
            .insert_resource(crate::production::PrimaryView::Map)
            .insert_resource(ObserverSession::new(
                babylon_persistence::CampaignId::from_uuid(uuid::Uuid::from_u128(1)),
            ))
            .add_systems(Startup, |mut commands: Commands| {
                spawn_drawers(&mut commands);
                spawn_menu(&mut commands);
                spawn_footer(&mut commands);
            })
            .add_systems(Update, paint_view_controls);
        app.update();
        let world = app.world_mut();
        assert!(world
            .query_filtered::<&Node, With<ControlDrawer>>()
            .iter(world)
            .all(|node| node.display == Display::None));
        assert!(world
            .query_filtered::<&Node, With<VerificationDetails>>()
            .iter(world)
            .all(|node| node.display == Display::None));
        world.resource_mut::<ObserverUiState>().disclosure = Some(ObserverDisclosure::Lens);
        app.update();
        let world = app.world_mut();
        for (drawer, node) in world.query::<(&ControlDrawer, &Node)>().iter(world) {
            assert_eq!(
                node.display == Display::Flex,
                drawer.0 == ObserverDisclosure::Lens
            );
        }
        // A modal menu suppresses an open drawer and its buttons as one subtree.
        world.resource_mut::<ObserverUiState>().menu_open = true;
        app.update();
        let world = app.world_mut();
        assert!(world
            .query_filtered::<&Node, With<ControlDrawer>>()
            .iter(world)
            .all(|node| node.display == Display::None));
    }

    #[test]
    fn quit_shortcut_is_only_available_inside_the_campaign_menu() {
        let atlas = CountyAtlas::parse(include_bytes!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../assets/map/county_atlas.bin"
        )))
        .expect("atlas");
        let mut app = App::new();
        app.add_plugins(MinimalPlugins)
            .insert_resource(atlas)
            .init_resource::<SelectedCounty>()
            .init_resource::<crate::production::PrimaryView>()
            .init_resource::<ButtonInput<KeyCode>>()
            .insert_resource(ObserverUiState {
                splash_visible: false,
                menu_open: false,
                ..default()
            })
            .add_message::<ObserverCommand>()
            .add_systems(Update, keyboard);
        for menu_open in [false, true] {
            app.world_mut().resource_mut::<ObserverUiState>().menu_open = menu_open;
            app.world_mut()
                .resource_mut::<ButtonInput<KeyCode>>()
                .press(KeyCode::KeyQ);
            app.update();
            let commands: Vec<_> = app
                .world_mut()
                .resource_mut::<Messages<ObserverCommand>>()
                .drain()
                .collect();
            assert_eq!(
                commands,
                if menu_open {
                    vec![ObserverCommand::Quit]
                } else {
                    Vec::new()
                }
            );
            app.world_mut()
                .resource_mut::<ButtonInput<KeyCode>>()
                .reset_all();
        }
    }

    #[test]
    fn county_arrow_shortcuts_only_change_selection_on_geography() {
        let atlas = CountyAtlas::parse(include_bytes!(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../../assets/map/county_atlas.bin"
        )))
        .expect("atlas");
        let county = (0..atlas.len())
            .find(|index| atlas.county(*index).is_some_and(|row| row.fips == "26099"))
            .expect("Macomb");
        let mut app = App::new();
        app.add_plugins((MinimalPlugins, InputPlugin))
            .insert_resource(atlas)
            .insert_resource(SelectedCounty(Some(county)))
            .insert_resource(crate::production::PrimaryView::Production)
            .insert_resource(ObserverUiState {
                menu_open: false,
                splash_visible: false,
                ..default()
            })
            .add_message::<ObserverCommand>()
            .add_systems(Update, keyboard);
        for view in [
            crate::production::PrimaryView::Production,
            crate::production::PrimaryView::Map,
        ] {
            *app.world_mut()
                .resource_mut::<crate::production::PrimaryView>() = view;
            for key in [KeyCode::ArrowLeft, KeyCode::ArrowRight] {
                app.world_mut().resource_mut::<SelectedCounty>().0 = Some(county);
                app.world_mut()
                    .resource_mut::<Messages<KeyboardInput>>()
                    .write(KeyboardInput {
                        key_code: key,
                        logical_key: Key::Unidentified(NativeKey::Unidentified),
                        state: ButtonState::Pressed,
                        text: None,
                        repeat: false,
                        window: Entity::PLACEHOLDER,
                    });
                app.update();
                let after = app.world().resource::<SelectedCounty>().0;
                if view == crate::production::PrimaryView::Production {
                    assert_eq!(after, Some(county));
                } else {
                    assert_ne!(after, Some(county));
                }
                app.world_mut()
                    .resource_mut::<ButtonInput<KeyCode>>()
                    .release(key);
            }
        }
    }
}
