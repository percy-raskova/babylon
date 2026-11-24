//! The scene's right rail and shock controls: the table with its tabs and pager, the inspector,
//! the list of what was struck, and the buttons that strike and lift. Hours and money are kept
//! in their own columns and their own bar scales; a figure here is a figure of the period shown.

use super::controls::{self, SceneButton};
use super::frame::{self, Picture, STREAM_GOODS, STREAM_MONEY, STREAM_WORK};
use super::inspect::{self, Pick, ScenePick};
use super::marks;
use super::reading;
use super::rules::{self, RULES_SHOWN};
use super::scene::{SceneCommand, SceneRunner, SceneShown, BAR_HEIGHT, HEADER_HEIGHT, RAIL_WIDTH};
use super::table::{self, Grouping, HoursTable, Table};
use crate::human_numbers;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use crate::palette::{BONE, GOLD};
use crate::ui;
use babylon_circuit_worlds::{Lasts, PeriodResult, Place, Places, Shock, ShockBook, ShockError};
use bevy::ecs::system::SystemParam;
use bevy::picking::pointer::PointerButton;
use bevy::prelude::*;
use hypergraph_rs_bevy::{FieldConfig, FlowReport, Motion};
use std::time::Duration;

/// How long a refused strike's words stay on screen.
pub const NOTICE_SECONDS: Duration = Duration::from_secs(4);
/// The line under the power cut's controls.
pub const POWER_CUT_LINE: &str =
    "A power cut changes the size of a batch, so it holds until you start over.";

/// Under the table: why its money differs from the inspector's.
pub const TO_THE_CENT_LINE: &str =
    "Money in the table is rounded to the cent. Click a body for exact figures.";

/// Under the table while the second set shows.
pub const TO_THE_HOUR_LINE: &str =
    "Hours in the table are rounded to the hour. Click a body for exact figures.";
/// The switch's caption.
pub const COLUMNS_SWITCH: &str = "Hours back";
/// Where the second set has nothing to show.
const NO_HOURS_LINE: &str = "No hours were measured for this period.";

const HOURS_COLUMNS: [&str; 5] = ["Given", "Back", "For work", "By owning", "Support"];
/// The cells' widths of the second set, the lead's to tune.
const HOURS_CELL_WIDTHS: [f32; 5] = [40.0, 44.0, 48.0, 52.0, 48.0];
/// What a cell with no figure shows.
const DASH: &str = "—";

const TABLE_COLUMNS: [&str; 4] = ["Work given", "Paid, not used", "Money in", "Money out"];
const LABEL_WIDTH: f32 = 140.0;
/// The figure cells' widths, in the columns' order.
const CELL_WIDTHS: [f32; 4] = [40.0, 48.0, 74.0, 74.0];
/// The inspector panel's width, and the key's.
const SIDE_PANEL_WIDTH: f32 = 340.0;
const ROW_HEIGHT: f32 = 22.0;
const BAR_THICKNESS: f32 = 6.0;
const RAIL_PADDING: f32 = 12.0;
const BUTTON_HEIGHT: f32 = 28.0;
const SELECTED_EDGE: f32 = 3.0;

/// What the lower part of the rail shows.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Lower {
    #[default]
    Shocks,
    Rules,
}

/// Which set of columns the table shows.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Columns {
    /// Hours worked and money.
    #[default]
    Money,
    /// The hours stored in goods, split by the claim.
    Hours,
}

impl Columns {
    /// The other set.
    #[must_use]
    pub const fn other(self) -> Self {
        match self {
            Self::Money => Self::Hours,
            Self::Hours => Self::Money,
        }
    }
}

/// How the table is grouped and which period it and the inspector read; `None` is the latest.
#[derive(Resource, Clone, Debug, PartialEq, Eq)]
pub struct PanelView {
    pub grouping: Grouping,
    pub period: Option<u64>,
    /// The tab of the rail's lower part.
    pub lower: Lower,
    /// The set of columns the table shows.
    pub columns: Columns,
}

impl Default for PanelView {
    fn default() -> Self {
        Self {
            grouping: Grouping::Workplace,
            period: None,
            lower: Lower::Shocks,
            columns: Columns::Money,
        }
    }
}

/// A button of the rail: a tab, or one of the pager's.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub enum PanelButton {
    Tab(Grouping),
    Previous,
    Next,
    Latest,
    Lower(Lower),
    /// The switch between the table's two sets of columns.
    Columns,
}

/// A body of the rail's lower part, shown while the view's `lower` is its own.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub struct LowerBody(pub Lower);

/// A button of the shock controls.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub enum ShockButton {
    /// Where the shock is struck.
    Place(Shock, Places),
    /// How long the harvest fails.
    Lasts(Shock, Lasts),
    /// Strike it.
    Strike(Shock),
}

/// The "Lift" button of one row of the list of shocks.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub struct LiftButton(pub Shock, pub Place);

/// What the controls have chosen for one shock.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct ShockChoice {
    pub places: Places,
    pub lasts: Lasts,
}

/// The choices of every shock, in the order of `Shock::ALL`, held until "Strike" is pressed.
#[derive(Resource, Clone, Debug, PartialEq, Eq)]
pub struct ShockChoices(pub [ShockChoice; 2]);

impl Default for ShockChoices {
    fn default() -> Self {
        Self(
            [ShockChoice {
                places: Places::A,
                lasts: Lasts::UntilLifted,
            }; 2],
        )
    }
}

impl ShockChoices {
    fn index(shock: Shock) -> usize {
        Shock::ALL.iter().position(|s| *s == shock).unwrap_or(0)
    }

    /// The choice held for a shock.
    #[must_use]
    pub fn of(&self, shock: Shock) -> ShockChoice {
        self.0[Self::index(shock)]
    }
}

/// The words of the last refused strike or lift, and how long they stay.
#[derive(Resource, Default, Clone, Debug, PartialEq, Eq)]
pub struct ShockNotice {
    pub text: Option<String>,
    pub left: Duration,
}

impl ShockNotice {
    /// Show the words of a refusal for `NOTICE_SECONDS`.
    pub fn refuse(&mut self, error: ShockError) {
        self.say(refusal_words(error));
    }

    /// Show these words for `NOTICE_SECONDS`.
    pub fn say(&mut self, words: String) {
        self.text = Some(words);
        self.left = NOTICE_SECONDS;
    }
}

/// A refused strike or lift in the scene's own words.
#[must_use]
pub fn refusal_words(error: ShockError) -> String {
    match error {
        ShockError::AlreadyHolds { place, .. } => format!("Already holds in {}", place.label()),
        ShockError::NotHolding { place, .. } => format!("Nothing to lift in {}", place.label()),
        ShockError::TenPeriodsOnlyForTheHarvest => "Ten periods is only for the harvest".to_owned(),
        ShockError::HoldsUntilStartOver => "A power cut holds until you start over".to_owned(),
        ShockError::Stopped => "The run is stopped".to_owned(),
    }
}

/// One line of the list of what was struck.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ShockRow {
    pub text: String,
    /// Holds now or waits to hold.
    pub holding: bool,
    /// The shock and place a "Lift" button lifts, while it can be lifted.
    pub lift: Option<(Shock, Place)>,
}

/// What was struck, in the order struck, as the book stands before period `next_period`.
#[must_use]
pub fn shock_rows(book: &ShockBook, next_period: u64) -> Vec<ShockRow> {
    book.strikes()
        .iter()
        .map(|strike| {
            let holding = strike.until.is_none_or(|until| next_period < until);
            let end = match (strike.shock, strike.lasts, strike.until) {
                (Shock::PowerCut, _, _) => "holds until you start over".to_owned(),
                (_, Lasts::TenPeriods, Some(until))
                    if strike.from.checked_add(10) == Some(until) =>
                {
                    format!("until period {until}")
                }
                (_, _, Some(until)) => format!("lifted at period {until}"),
                (_, _, None) => "holds".to_owned(),
            };
            ShockRow {
                text: format!(
                    "SHOCK · {} in {} · {} · from period {} · {end}",
                    strike.shock.name(),
                    strike.place.label(),
                    strike.shock.figure(),
                    strike.from,
                ),
                holding,
                lift: (holding && strike.shock != Shock::PowerCut)
                    .then_some((strike.shock, strike.place)),
            }
        })
        .collect()
}

/// The words for a figure too large to add exactly.
fn too_large() -> String {
    "too large to add".to_owned()
}

/// What the period's picture left out, every figure from the library's own report.
#[must_use]
pub fn not_drawn_line(report: &FlowReport) -> String {
    if report.streams.is_empty() {
        return String::new();
    }
    let left_out = |stream: u16| -> Option<u128> {
        report
            .streams
            .iter()
            .filter(|s| s.stream == stream)
            .try_fold(0_u128, |sum, s| sum.checked_add(s.not_drawn))
    };
    let units = |stream: u16| left_out(stream).map_or_else(too_large, human_numbers::grouped);
    let dollars = |stream: u16| {
        left_out(stream)
            .and_then(|v| i128::try_from(v).ok())
            .map_or_else(too_large, human_numbers::currency_to_cent)
    };
    let capital_total = report
        .streams
        .iter()
        .filter(|s| s.stream == STREAM_MONEY[5])
        .try_fold(0_u128, |sum, s| sum.checked_add(s.total));
    let capital = match capital_total {
        Some(0) => String::new(),
        _ => format!(", capital {}", dollars(STREAM_MONEY[5])),
    };
    format!(
        "Not drawn: {} hours; food {}, power {}, care {} units; wages {}, purchases {}, taxes {}, benefits {}, profit {}{capital}",
        units(STREAM_WORK),
        units(STREAM_GOODS[0]),
        units(STREAM_GOODS[1]),
        units(STREAM_GOODS[2]),
        dollars(STREAM_MONEY[0]),
        dollars(STREAM_MONEY[1]),
        dollars(STREAM_MONEY[2]),
        dollars(STREAM_MONEY[3]),
        dollars(STREAM_MONEY[4]),
    )
}

#[derive(Component)]
pub struct TableBody;
#[derive(Component)]
pub struct PagerLabel;
/// The panel over the viewport's top right that holds the pick's figures; shown only while
/// something is picked.
#[derive(Component)]
pub struct InspectorPanel;
#[derive(Component)]
pub struct InspectorTitle;
#[derive(Component)]
pub struct InspectorBody;
#[derive(Component)]
pub struct ShocksBody;
#[derive(Component)]
pub struct NoticeLine;
#[derive(Component)]
pub struct NotDrawnLine;
/// The line under the table that says how its figures are rounded.
#[derive(Component)]
pub struct UnderTableLine;

/// A bordered button with a caption; the border is repainted by the paint systems.
pub(super) fn spawn_pressed<B: Bundle>(
    parent: &mut ChildSpawnerCommands,
    kind: B,
    caption: &str,
    size: f32,
) {
    parent
        .spawn((
            ui::pressable(),
            kind,
            Node {
                height: px(BUTTON_HEIGHT),
                flex_shrink: 0.0,
                border: UiRect::all(px(1)),
                padding: UiRect::horizontal(px(8)),
                justify_content: JustifyContent::Center,
                align_items: AlignItems::Center,
                ..default()
            },
            BorderColor::all(theme::PAPER),
            BackgroundColor(Color::NONE),
        ))
        .with_child(controls::text(
            caption,
            size,
            theme::PAPER,
            ObserverFontRole::Body,
        ));
}

/// The shock controls of the rail: for each shock, a line with its tag and name, its figure, and
/// a line that wraps with where to strike it, how long, and "Strike"; under the power cut's
/// controls the line that says why it cannot be lifted. The refused strike's notice follows.
pub fn spawn_shock_controls(parent: &mut ChildSpawnerCommands) {
    parent
        .spawn(Node {
            flex_direction: FlexDirection::Column,
            row_gap: px(10),
            ..default()
        })
        .with_children(|shocks| {
            for shock in Shock::ALL {
                spawn_shock(shocks, shock);
            }
        });
    parent.spawn((
        controls::text("", 12.0, theme::RED, ObserverFontRole::Body),
        NoticeLine,
        Node {
            margin: UiRect::top(px(4)),
            ..default()
        },
    ));
}

fn spawn_shock(shocks: &mut ChildSpawnerCommands, shock: Shock) {
    shocks
        .spawn(Node {
            flex_direction: FlexDirection::Column,
            row_gap: px(2),
            ..default()
        })
        .with_children(|group| {
            group
                .spawn(Node {
                    column_gap: px(6),
                    align_items: AlignItems::Center,
                    ..default()
                })
                .with_children(|line| {
                    line.spawn(controls::text(
                        "SHOCK",
                        13.0,
                        theme::RED,
                        ObserverFontRole::Display,
                    ));
                    line.spawn(controls::text(
                        shock.name(),
                        13.0,
                        theme::PAPER,
                        ObserverFontRole::Body,
                    ));
                });
            group.spawn(controls::text(
                shock.figure(),
                12.0,
                theme::GRAY,
                ObserverFontRole::Body,
            ));
            group
                .spawn(Node {
                    flex_wrap: FlexWrap::Wrap,
                    column_gap: px(4),
                    row_gap: px(4),
                    ..default()
                })
                .with_children(|buttons| {
                    for places in [Places::A, Places::B, Places::Both] {
                        let caption = match places {
                            Places::A => "Place A",
                            Places::B => "Place B",
                            Places::Both => "Both",
                        };
                        spawn_pressed(buttons, ShockButton::Place(shock, places), caption, 14.0);
                    }
                    if shock == Shock::HarvestFails {
                        for lasts in [Lasts::TenPeriods, Lasts::UntilLifted] {
                            spawn_pressed(
                                buttons,
                                ShockButton::Lasts(shock, lasts),
                                lasts.label(),
                                14.0,
                            );
                        }
                    }
                    spawn_pressed(buttons, ShockButton::Strike(shock), "Strike", 14.0);
                });
            if shock == Shock::PowerCut {
                group.spawn(controls::text(
                    POWER_CUT_LINE,
                    11.0,
                    theme::GRAY,
                    ObserverFontRole::Body,
                ));
            }
        });
}

/// The right rail: the table with its two lines at the top, the shocks below it.
pub fn spawn_rail(commands: &mut Commands) {
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                top: px(HEADER_HEIGHT),
                bottom: px(BAR_HEIGHT),
                right: px(0),
                width: px(RAIL_WIDTH),
                padding: UiRect::all(px(RAIL_PADDING)),
                flex_direction: FlexDirection::Column,
                overflow: Overflow::clip(),
                ..default()
            },
            BackgroundColor(theme::PANEL),
            ZIndex(10),
        ))
        .with_children(|rail| {
            rail.spawn(Node {
                flex_direction: FlexDirection::Column,
                row_gap: px(4),
                ..default()
            })
            .with_children(|section| {
                spawn_tabs_and_pager(section);
                section.spawn((
                    TableBody,
                    Node {
                        flex_direction: FlexDirection::Column,
                        ..default()
                    },
                ));
                section.spawn((
                    controls::text(TO_THE_CENT_LINE, 11.0, theme::GRAY, ObserverFontRole::Body),
                    UnderTableLine,
                ));
            });
            rail.spawn(Node {
                flex_direction: FlexDirection::Column,
                margin: UiRect::top(px(14)),
                ..default()
            })
            .with_children(spawn_lower);
        });
}

/// The rail's lower part: the shocks, and the rules behind a second tab while any rule is shown.
fn spawn_lower(section: &mut ChildSpawnerCommands) {
    if RULES_SHOWN {
        section
            .spawn(Node {
                column_gap: px(4),
                margin: UiRect::bottom(px(4)),
                ..default()
            })
            .with_children(|tabs| {
                spawn_pressed(tabs, PanelButton::Lower(Lower::Shocks), "Shocks", 13.0);
                spawn_pressed(tabs, PanelButton::Lower(Lower::Rules), "Rules", 13.0);
            });
    } else {
        section
            .spawn(Node {
                margin: UiRect::bottom(px(4)),
                ..default()
            })
            .with_child(controls::text(
                "Shocks",
                16.0,
                theme::YELLOW,
                ObserverFontRole::Display,
            ));
    }
    section
        .spawn((
            LowerBody(Lower::Shocks),
            Node {
                flex_direction: FlexDirection::Column,
                ..default()
            },
        ))
        .with_children(|body| {
            spawn_shock_controls(body);
            body.spawn((
                ShocksBody,
                Node {
                    flex_direction: FlexDirection::Column,
                    row_gap: px(2),
                    margin: UiRect::top(px(8)),
                    ..default()
                },
            ));
        });
    if RULES_SHOWN {
        section
            .spawn((
                LowerBody(Lower::Rules),
                Node {
                    flex_direction: FlexDirection::Column,
                    display: Display::None,
                    ..default()
                },
            ))
            .with_children(rules::spawn_rules_tab);
    }
}

/// The inspector: a panel over the viewport's top right, shown only while something is picked.
pub fn spawn_inspector(commands: &mut Commands) {
    commands
        .spawn((
            InspectorPanel,
            Node {
                position_type: PositionType::Absolute,
                top: px(HEADER_HEIGHT + 12.0),
                right: px(RAIL_WIDTH + 12.0),
                width: px(SIDE_PANEL_WIDTH),
                padding: UiRect::all(px(10)),
                border: UiRect::all(px(1)),
                flex_direction: FlexDirection::Column,
                row_gap: px(2),
                display: Display::None,
                ..default()
            },
            BackgroundColor(theme::PANEL),
            BorderColor::all(theme::GRAY),
            ZIndex(5),
        ))
        .with_children(|panel| {
            panel.spawn((
                controls::text("", 14.0, theme::YELLOW, ObserverFontRole::Display),
                InspectorTitle,
            ));
            panel.spawn((
                InspectorBody,
                Node {
                    flex_direction: FlexDirection::Column,
                    ..default()
                },
            ));
        });
}

fn spawn_tabs_and_pager(section: &mut ChildSpawnerCommands) {
    section
        .spawn(Node {
            column_gap: px(4),
            ..default()
        })
        .with_children(|tabs| {
            for (grouping, caption) in [
                (Grouping::Workplace, "By workplace"),
                (Grouping::Class, "By class"),
                (Grouping::Place, "By place"),
            ] {
                spawn_pressed(tabs, PanelButton::Tab(grouping), caption, 13.0);
            }
        });
    section
        .spawn(Node {
            column_gap: px(4),
            align_items: AlignItems::Center,
            ..default()
        })
        .with_children(|pager| {
            spawn_pressed(pager, PanelButton::Previous, "‹", 13.0);
            pager.spawn((
                controls::text("Period", 13.0, theme::PAPER, ObserverFontRole::Body),
                PagerLabel,
            ));
            spawn_pressed(pager, PanelButton::Next, "›", 13.0);
            spawn_pressed(pager, PanelButton::Latest, "Latest", 13.0);
            pager.spawn(Node {
                flex_grow: 1.0,
                ..default()
            });
            spawn_pressed(pager, PanelButton::Columns, COLUMNS_SWITCH, 13.0);
        });
}

/// The index of the history the view reads, or none while nothing has been closed.
fn view_index(view: &PanelView, closed: usize) -> Option<usize> {
    let last = closed.checked_sub(1)?;
    match view.period.and_then(|p| usize::try_from(p).ok()) {
        Some(p) if (1..=closed).contains(&p) => p.checked_sub(1),
        _ => Some(last),
    }
}

fn percent_of(value: u128, scale: u128) -> f32 {
    if scale == 0 {
        return 0.0;
    }
    let share = value.saturating_mul(100) / scale;
    f32::from(u8::try_from(share.min(100)).unwrap_or(100))
}

fn money_units(value: i128) -> u128 {
    u128::try_from(value.max(0)).unwrap_or(0)
}

fn spawn_cell(row: &mut ChildSpawnerCommands, width: f32, figure: &str, bar: Option<(f32, Color)>) {
    row.spawn(Node {
        width: px(width),
        flex_direction: FlexDirection::Column,
        overflow: Overflow::clip(),
        ..default()
    })
    .with_children(|cell| {
        cell.spawn(controls::text(
            figure,
            13.0,
            theme::PAPER,
            ObserverFontRole::Exact,
        ));
        if let Some((width, color)) = bar {
            cell.spawn((
                Node {
                    height: px(BAR_THICKNESS),
                    width: percent(width),
                    ..default()
                },
                BackgroundColor(color),
            ));
        }
    });
}

fn spawn_table(body: &mut ChildSpawnerCommands, table: &Table) {
    body.spawn(Node {
        align_items: AlignItems::FlexEnd,
        ..default()
    })
    .with_children(|header| {
        header.spawn(Node {
            width: px(LABEL_WIDTH),
            ..default()
        });
        for (name, width) in TABLE_COLUMNS.into_iter().zip(CELL_WIDTHS) {
            header
                .spawn(Node {
                    width: px(width),
                    ..default()
                })
                .with_child(controls::text(
                    name,
                    11.0,
                    theme::GRAY,
                    ObserverFontRole::Body,
                ));
        }
    });
    let (hours_scale, money_scale) = (
        u128::from(table.hours_scale),
        money_units(table.money_scale),
    );
    for line in &table.rows {
        body.spawn(Node {
            height: px(ROW_HEIGHT),
            ..default()
        })
        .with_children(|row| {
            row.spawn(Node {
                width: px(LABEL_WIDTH),
                overflow: Overflow::clip(),
                ..default()
            })
            .with_child(controls::text(
                &line.label,
                13.0,
                theme::PAPER,
                ObserverFontRole::Body,
            ));
            let hours = |value: u64| {
                (
                    human_numbers::grouped(u128::from(value)),
                    Some((percent_of(u128::from(value), hours_scale), BONE)),
                )
            };
            let money = |value: i128| {
                (
                    human_numbers::currency_to_cent(value),
                    Some((percent_of(money_units(value), money_scale), GOLD)),
                )
            };
            let cells = [
                hours(line.work_given),
                hours(line.paid_not_used),
                money(line.money_in),
                money(line.money_out),
            ];
            for ((figure, bar), width) in cells.into_iter().zip(CELL_WIDTHS) {
                spawn_cell(row, width, &figure, bar);
            }
        });
    }
}

fn spawn_hours_table(body: &mut ChildSpawnerCommands, table: &HoursTable) {
    body.spawn(Node {
        align_items: AlignItems::FlexEnd,
        ..default()
    })
    .with_children(|header| {
        header.spawn(Node {
            width: px(LABEL_WIDTH),
            ..default()
        });
        for (name, width) in HOURS_COLUMNS.into_iter().zip(HOURS_CELL_WIDTHS) {
            header
                .spawn(Node {
                    width: px(width),
                    ..default()
                })
                .with_child(controls::text(
                    name,
                    11.0,
                    theme::GRAY,
                    ObserverFontRole::Body,
                ));
        }
    });
    for line in &table.rows {
        body.spawn(Node {
            height: px(ROW_HEIGHT),
            ..default()
        })
        .with_children(|row| {
            row.spawn(Node {
                width: px(LABEL_WIDTH),
                overflow: Overflow::clip(),
                ..default()
            })
            .with_child(controls::text(
                &line.label,
                13.0,
                theme::PAPER,
                ObserverFontRole::Body,
            ));
            let micro = |value: Option<u128>| {
                value.map_or_else(
                    || (DASH.to_owned(), None),
                    |v| {
                        (
                            human_numbers::micro_hours_to_hour(v),
                            Some((percent_of(v, table.scale), BONE)),
                        )
                    },
                )
            };
            let given = line.given.map_or_else(
                || (DASH.to_owned(), None),
                |g| {
                    let figure = u128::from(g);
                    (
                        human_numbers::grouped(figure),
                        Some((
                            percent_of(figure.saturating_mul(1_000_000), table.scale),
                            BONE,
                        )),
                    )
                },
            );
            let cells = [
                given,
                micro(line.back),
                micro(line.for_work),
                micro(line.by_owning),
                micro(line.support),
            ];
            for ((figure, bar), width) in cells.into_iter().zip(HOURS_CELL_WIDTHS) {
                spawn_cell(row, width, &figure, bar);
            }
        });
    }
}

/// Write the line under the table: how the shown set of columns is rounded.
pub fn paint_under_table_line(
    view: Res<PanelView>,
    mut line: Query<&mut Text, With<UnderTableLine>>,
) {
    let words = match view.columns {
        Columns::Money => TO_THE_CENT_LINE,
        Columns::Hours => TO_THE_HOUR_LINE,
    };
    for mut text in &mut line {
        text.set_if_neq(Text::new(words));
    }
}

/// Repaint the table and the pager's label when the view, the history or the picture changes.
pub fn paint_table(
    mut commands: Commands,
    scene: Res<SceneRunner>,
    view: Res<PanelView>,
    shown: Res<SceneShown>,
    body: Query<Entity, With<TableBody>>,
    mut label: Query<&mut Text, With<PagerLabel>>,
) {
    if !(scene.is_changed() || view.is_changed() || shown.is_changed()) {
        return;
    }
    let history = scene.runner.history();
    let index = view_index(&view, history.len());
    let words = index.map_or_else(
        || "No period".to_owned(),
        |i| format!("Period {}", history[i].period),
    );
    for mut text in &mut label {
        text.set_if_neq(Text::new(words.clone()));
    }
    let Ok(body) = body.single() else {
        return;
    };
    commands.entity(body).despawn_related::<Children>();
    if view.columns == Columns::Hours {
        paint_hours_table(
            &mut commands,
            body,
            index.map(|i| &history[i]),
            view.grouping,
        );
        return;
    }
    let built = index
        .map(|i| reading::read_period(&history[i]).and_then(|r| table::table(&r, view.grouping)));
    match built {
        Some(Ok(built)) => {
            commands
                .entity(body)
                .with_children(|rows| spawn_table(rows, &built));
        }
        Some(Err(error)) => {
            commands.entity(body).with_child(controls::text(
                format!("The table cannot be built: {error}"),
                13.0,
                theme::RED,
                ObserverFontRole::Body,
            ));
        }
        None => {}
    }
}

/// The table's second set for the period, or the words that say why there is none.
fn paint_hours_table(
    commands: &mut Commands,
    body: Entity,
    result: Option<&PeriodResult>,
    grouping: Grouping,
) {
    let Some(result) = result else {
        return;
    };
    match table::hours_table(result, grouping) {
        Ok(Some(built)) => {
            commands
                .entity(body)
                .with_children(|rows| spawn_hours_table(rows, &built));
        }
        Ok(None) => {
            commands.entity(body).with_child(controls::text(
                NO_HOURS_LINE,
                13.0,
                theme::GRAY,
                ObserverFontRole::Body,
            ));
        }
        Err(error) => {
            commands.entity(body).with_child(controls::text(
                format!("The table cannot be built: {error}"),
                13.0,
                theme::RED,
                ObserverFontRole::Body,
            ));
        }
    }
}

fn spawn_rows(body: &mut ChildSpawnerCommands, rows: &[(String, String)]) {
    for (label, value) in rows {
        body.spawn(Node {
            height: px(18),
            justify_content: JustifyContent::SpaceBetween,
            column_gap: px(8),
            ..default()
        })
        .with_children(|line| {
            line.spawn(controls::text(
                label,
                12.0,
                theme::PAPER,
                ObserverFontRole::Body,
            ));
            line.spawn(controls::text(
                value,
                12.0,
                theme::PAPER,
                ObserverFontRole::Exact,
            ));
        });
    }
}

/// The inspector's panel stands while something is picked and not otherwise.
pub fn paint_inspector_panel(
    pick: Res<ScenePick>,
    mut panel: Query<&mut Node, With<InspectorPanel>>,
) {
    let display = if pick.0.is_some() {
        Display::Flex
    } else {
        Display::None
    };
    for mut node in &mut panel {
        if node.display != display {
            node.display = display;
        }
    }
}

/// Repaint the inspector: the pick's own figures for the period the view reads.
pub fn paint_inspector(
    mut commands: Commands,
    scene: Res<SceneRunner>,
    view: Res<PanelView>,
    shown: Res<SceneShown>,
    pick: Res<ScenePick>,
    body: Query<Entity, With<InspectorBody>>,
    mut title: Query<&mut Text, With<InspectorTitle>>,
) {
    if !(scene.is_changed() || view.is_changed() || shown.is_changed() || pick.is_changed()) {
        return;
    }
    let words = pick
        .0
        .as_ref()
        .map_or_else(String::new, inspect::pick_label);
    for mut text in &mut title {
        text.set_if_neq(Text::new(words.clone()));
    }
    let Ok(body) = body.single() else {
        return;
    };
    let history = scene.runner.history();
    let rows = match (&pick.0, view_index(&view, history.len())) {
        (None, _) => Ok(Vec::new()),
        (Some(_), None) => Err("Nothing has run yet.".to_owned()),
        (Some(pick), Some(index)) => rows_for(&scene, &shown, index, pick),
    };
    commands.entity(body).despawn_related::<Children>();
    commands.entity(body).with_children(|lines| match &rows {
        Ok(rows) => spawn_rows(lines, rows),
        Err(words) => {
            lines.spawn(controls::text(
                words,
                13.0,
                theme::GRAY,
                ObserverFontRole::Body,
            ));
        }
    });
}

/// The inspector's rows for a period of the history: the picture shown when it is the latest,
/// else one built again from that period's result in the mode shown.
fn rows_for(
    scene: &SceneRunner,
    shown: &SceneShown,
    index: usize,
    pick: &Pick,
) -> Result<Vec<(String, String)>, String> {
    let history = scene.runner.history();
    let result = &history[index];
    let built: Picture;
    let picture = match &shown.0 {
        Some(picture) if index + 1 == history.len() && picture.reading.period == result.period => {
            picture
        }
        _ => {
            built = frame::build_picture(result, scene.mode).map_err(|e| e.to_string())?;
            &built
        }
    };
    let mut rows = inspect::inspect(picture, result, pick).map_err(|e| e.to_string())?;
    rows.extend(marks::rule_rows(history, index, pick).map_err(|e| e.to_string())?);
    Ok(rows)
}

/// Repaint the list of what was struck.
pub fn paint_shocks(
    mut commands: Commands,
    scene: Res<SceneRunner>,
    body: Query<Entity, With<ShocksBody>>,
) {
    if !scene.is_changed() {
        return;
    }
    let Ok(body) = body.single() else {
        return;
    };
    let rows = shock_rows(scene.runner.shocks(), scene.runner.next_period());
    commands.entity(body).despawn_related::<Children>();
    commands.entity(body).with_children(|list| {
        for row in rows {
            list.spawn(Node {
                column_gap: px(8),
                align_items: AlignItems::Center,
                ..default()
            })
            .with_children(|line| {
                let color = if row.holding {
                    theme::PAPER
                } else {
                    theme::GRAY
                };
                line.spawn((
                    controls::text(&row.text, 12.0, color, ObserverFontRole::Body),
                    Node {
                        flex_shrink: 1.0,
                        ..default()
                    },
                ));
                if let Some((shock, place)) = row.lift {
                    spawn_pressed(line, LiftButton(shock, place), "Lift", 12.0);
                }
            });
        }
    });
}

/// A tab's caption: "Shocks" or "Shocks · {count} holding"; "Rules" or "Rules · {count} on". The count is left
/// out when it is 0.
#[must_use]
pub fn lower_caption(lower: Lower, count: usize) -> String {
    let (name, word) = match lower {
        Lower::Shocks => ("Shocks", "holding"),
        Lower::Rules => ("Rules", "on"),
    };
    if count == 0 {
        name.to_owned()
    } else {
        format!("{name} · {count} {word}")
    }
}

/// Show the body of the chosen tab and write the two tabs' captions.
pub fn paint_lower(
    view: Res<PanelView>,
    scene: Res<SceneRunner>,
    mut bodies: Query<(&LowerBody, &mut Node)>,
    tabs: Query<(&PanelButton, &Children)>,
    mut captions: Query<&mut Text>,
) {
    for (body, mut node) in &mut bodies {
        let display = if !RULES_SHOWN || body.0 == view.lower {
            Display::Flex
        } else {
            Display::None
        };
        if node.display != display {
            node.display = display;
        }
    }
    let holding = shock_rows(scene.runner.shocks(), scene.runner.next_period())
        .iter()
        .filter(|row| row.holding)
        .count();
    let on = scene.runner.rules().len();
    for (button, children) in &tabs {
        let PanelButton::Lower(lower) = button else {
            continue;
        };
        let words = lower_caption(
            *lower,
            match lower {
                Lower::Shocks => holding,
                Lower::Rules => on,
            },
        );
        for child in children {
            if let Ok(mut text) = captions.get_mut(*child) {
                text.set_if_neq(Text::new(words.clone()));
            }
        }
    }
}

/// The border of a chosen button is marked on its left side, 3 px of yellow.
pub(super) fn mark(node: &mut Node, border: &mut BorderColor, selected: bool) {
    let edge = px(if selected { SELECTED_EDGE } else { 1.0 });
    if node.border.left != edge {
        node.border.left = edge;
    }
    let color = if selected {
        theme::YELLOW
    } else {
        theme::PAPER
    };
    let wanted = BorderColor {
        left: color,
        ..BorderColor::all(theme::PAPER)
    };
    if *border != wanted {
        *border = wanted;
    }
}

/// Whether a button of the scene, the rail or the shock controls is the chosen one, or none of
/// the kinds that can be chosen.
fn chosen(
    buttons: (
        Option<&SceneButton>,
        Option<&PanelButton>,
        Option<&ShockButton>,
    ),
    scene: &SceneRunner,
    motion: Motion,
    view: &PanelView,
    choices: &ShockChoices,
) -> Option<bool> {
    match buttons {
        (Some(SceneButton::Particles(mode)), _, _) => Some(*mode == scene.mode),
        (Some(SceneButton::Marks(wanted)), _, _) => Some(*wanted == motion),
        (_, Some(PanelButton::Tab(grouping)), _) => Some(*grouping == view.grouping),
        (_, Some(PanelButton::Lower(lower)), _) => Some(*lower == view.lower),
        (_, Some(PanelButton::Columns), _) => Some(view.columns == Columns::Hours),
        (_, _, Some(ShockButton::Place(shock, places))) => {
            Some(choices.of(*shock).places == *places)
        }
        (_, _, Some(ShockButton::Lasts(shock, lasts))) => Some(choices.of(*shock).lasts == *lasts),
        _ => None,
    }
}

type ChoosableButton = (
    &'static mut Node,
    &'static mut BorderColor,
    Option<&'static SceneButton>,
    Option<&'static PanelButton>,
    Option<&'static ShockButton>,
);
type IsChoosable = Or<(With<SceneButton>, With<PanelButton>, With<ShockButton>)>;

/// Mark the chosen particle mode, motion, tab and shock choices.
pub fn paint_choices(
    scene: Res<SceneRunner>,
    config: Res<FieldConfig>,
    view: Res<PanelView>,
    choices: Res<ShockChoices>,
    mut buttons: Query<ChoosableButton, IsChoosable>,
) {
    for (mut node, mut border, scene_button, panel_button, shock_button) in &mut buttons {
        let kinds = (scene_button, panel_button, shock_button);
        if let Some(selected) = chosen(kinds, &scene, config.motion, &view, &choices) {
            mark(&mut node, &mut border, selected);
        }
    }
}

/// The words of a refused strike, until their four seconds are over.
pub fn paint_notice(
    time: Res<Time>,
    mut notice: ResMut<ShockNotice>,
    mut line: Query<&mut Text, With<NoticeLine>>,
) {
    if notice.text.is_some() {
        let left = notice.left.saturating_sub(time.delta());
        notice.left = left;
        if left.is_zero() {
            notice.text = None;
        }
    }
    let words = notice.text.clone().unwrap_or_default();
    for mut text in &mut line {
        text.set_if_neq(Text::new(words.clone()));
    }
}

/// The line of what the picture left out, from the library's report of the period.
pub fn paint_not_drawn(report: Res<FlowReport>, mut line: Query<&mut Text, With<NotDrawnLine>>) {
    let words = not_drawn_line(&report);
    for mut text in &mut line {
        text.set_if_neq(Text::new(words.clone()));
    }
}

/// The buttons the rail and the shock controls own.
#[derive(SystemParam)]
pub struct Buttons<'w, 's> {
    panel: Query<'w, 's, &'static PanelButton>,
    shocks: Query<'w, 's, &'static ShockButton>,
    lifts: Query<'w, 's, &'static LiftButton>,
}

fn press_panel(
    button: PanelButton,
    scene: &SceneRunner,
    view: &PanelView,
    commands: &mut MessageWriter<SceneCommand>,
) {
    let closed = u64::try_from(scene.runner.history().len()).unwrap_or(0);
    let current = view.period.unwrap_or(closed);
    match button {
        PanelButton::Tab(grouping) => {
            commands.write(SceneCommand::Grouping(grouping));
        }
        PanelButton::Previous if current > 1 => {
            commands.write(SceneCommand::TablePeriod(Some(current - 1)));
        }
        PanelButton::Next if current < closed => {
            commands.write(SceneCommand::TablePeriod(Some(current + 1)));
        }
        PanelButton::Latest => {
            commands.write(SceneCommand::TablePeriod(None));
        }
        PanelButton::Lower(lower) => {
            commands.write(SceneCommand::Lower(lower));
        }
        PanelButton::Columns => {
            commands.write(SceneCommand::Columns(view.columns.other()));
        }
        PanelButton::Previous | PanelButton::Next => {}
    }
}

fn press_shock(
    button: ShockButton,
    choices: &mut ShockChoices,
    commands: &mut MessageWriter<SceneCommand>,
) {
    match button {
        ShockButton::Place(shock, places) => {
            choices.0[ShockChoices::index(shock)].places = places;
        }
        ShockButton::Lasts(shock, lasts) => {
            choices.0[ShockChoices::index(shock)].lasts = lasts;
        }
        ShockButton::Strike(shock) => {
            let choice = choices.of(shock);
            let lasts = if shock == Shock::PowerCut {
                Lasts::UntilLifted
            } else {
                choice.lasts
            };
            commands.write(SceneCommand::Strike(shock, choice.places, lasts));
        }
    }
}

/// The presses of the rail's tabs and pager, the shock controls and the "Lift" buttons.
pub fn pressed(
    event: On<PointerClick>,
    buttons: Buttons,
    scene: Res<SceneRunner>,
    view: Res<PanelView>,
    mut choices: ResMut<ShockChoices>,
    mut commands: MessageWriter<SceneCommand>,
) {
    if event.button != PointerButton::Primary {
        return;
    }
    if let Ok(button) = buttons.panel.get(event.entity) {
        press_panel(*button, &scene, &view, &mut commands);
    } else if let Ok(button) = buttons.shocks.get(event.entity) {
        press_shock(*button, &mut choices, &mut commands);
    } else if let Ok(LiftButton(shock, place)) = buttons.lifts.get(event.entity) {
        commands.write(SceneCommand::Lift(*shock, *place));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_circuit_worlds::Runner;
    use std::error::Error;

    #[test]
    fn the_lower_tabs_count_what_holds() {
        assert_eq!(lower_caption(Lower::Rules, 0), "Rules");
        assert_eq!(lower_caption(Lower::Rules, 2), "Rules · 2 on");
        assert_eq!(lower_caption(Lower::Shocks, 0), "Shocks");
        assert_eq!(lower_caption(Lower::Shocks, 3), "Shocks · 3 holding");
    }

    #[test]
    fn shock_rows_tell_what_was_struck_and_when() -> Result<(), Box<dyn Error>> {
        let mut runner = Runner::open()?;
        for _ in 0..2 {
            runner.step()?;
        }
        // The book is struck before the period it holds from: periods 1 and 2 are closed, so
        // the harvest holds from 3.
        runner.strike(Shock::HarvestFails, Places::A, Lasts::TenPeriods)?;
        for _ in 0..3 {
            runner.step()?;
        }
        runner.strike(Shock::PowerCut, Places::B, Lasts::UntilLifted)?;
        for _ in 0..6 {
            runner.step()?;
        }
        assert_eq!(runner.next_period(), 12);
        let rows = shock_rows(runner.shocks(), 12);
        assert_eq!(rows.len(), 2);
        assert_eq!(
            rows[0].text,
            "SHOCK · The harvest fails in Place A · a farm makes 9 food a batch, not 10 · from period 3 · until period 13"
        );
        assert!(rows[0].holding);
        assert_eq!(rows[0].lift, Some((Shock::HarvestFails, Place::A)));
        assert_eq!(
            rows[1].text,
            "SHOCK · The power is cut in Place B · a utility makes 9 power for 10 hours, not 10 · from period 6 · holds until you start over"
        );
        assert!(rows[1].holding);
        assert_eq!(rows[1].lift, None);
        Ok(())
    }

    #[test]
    fn a_refused_strike_is_told_in_the_scene_s_words() {
        let words = |e| refusal_words(e);
        assert_eq!(
            words(ShockError::AlreadyHolds {
                shock: Shock::HarvestFails,
                place: Place::A
            }),
            "Already holds in Place A"
        );
        assert_eq!(
            words(ShockError::NotHolding {
                shock: Shock::HarvestFails,
                place: Place::B
            }),
            "Nothing to lift in Place B"
        );
        assert_eq!(
            words(ShockError::TenPeriodsOnlyForTheHarvest),
            "Ten periods is only for the harvest"
        );
        assert_eq!(
            words(ShockError::HoldsUntilStartOver),
            "A power cut holds until you start over"
        );
    }
}
