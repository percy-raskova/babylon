//! Shared, dated resource chips over authenticated organizer disclosures.

use super::ui;
use super::workspace::{self, ResourceSummary};
use super::OrganizerClient;
use crate::observer::ObserverSession;
use crate::observer_io::ObserverSet;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use bevy::prelude::*;

pub(crate) const GOLD: Color = theme::YELLOW;
pub(crate) const CYAN: Color = theme::BLUE;
pub(crate) const VIOLET: Color = Color::srgb_u8(191, 159, 247);
pub(crate) const GREEN: Color = Color::srgb_u8(132, 216, 158);

/// Stable interface-tour anchor for the shared resource strip.
#[derive(Component)]
pub(crate) struct ResourceHud;

/// Labeled readings remain distinct from the costs of a draft action.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ResourceChip {
    Cash,
    OrganizerHours,
    HouseholdTime,
}

#[derive(Component)]
struct Amount(ResourceChip);
#[derive(Component)]
struct Period(ResourceChip);

impl ResourceChip {
    fn label(self) -> &'static str {
        match self {
            Self::Cash => "Cash",
            Self::OrganizerHours => "Organizer-hours",
            Self::HouseholdTime => "Household time",
        }
    }
    fn color(self) -> Color {
        match self {
            Self::Cash => GOLD,
            Self::OrganizerHours => CYAN,
            Self::HouseholdTime => VIOLET,
        }
    }
    fn reading(self, means: Option<ResourceSummary>, viewed_period: u64) -> (String, String) {
        let Some(means) = means else {
            return (
                "Unavailable".into(),
                if self == Self::HouseholdTime {
                    "closed-period reading unavailable · next period unknown".into()
                } else {
                    format!("P{viewed_period} · current disclosure unavailable")
                },
            );
        };
        match self {
            Self::Cash => (
                means
                    .cash_micros
                    .map_or_else(|| "Unavailable".into(), crate::human_numbers::currency),
                format!("P{} committed · currency", means.period),
            ),
            Self::OrganizerHours => (
                format!(
                    "{} h pledged",
                    crate::observer_ui::grouped(means.organizer_hours)
                ),
                format!("P{} committed", means.period),
            ),
            Self::HouseholdTime => means.shared_time.map_or_else(
                || {
                    (
                        "Unavailable".into(),
                        "closed-period reading unavailable · next period unknown".into(),
                    )
                },
                |(period, hours)| {
                    (
                        format!(
                            "{} h remaining · closed P{period}",
                            crate::observer_ui::grouped(hours)
                        ),
                        "next period unknown".into(),
                    )
                },
            ),
        }
    }
}

/// Spawn the same strip in the organizer, its inspectors and connected shell.
pub(crate) fn spawn(parent: &mut ChildSpawnerCommands) -> Entity {
    parent
        .spawn((
            ResourceHud,
            Name::new("wayne.resources"),
            Node {
                width: percent(100),
                height: px(60),
                column_gap: px(8),
                flex_shrink: 0.0,
                min_width: px(0),
                ..default()
            },
        ))
        .with_children(|row| {
            for chip in [
                ResourceChip::Cash,
                ResourceChip::OrganizerHours,
                ResourceChip::HouseholdTime,
            ] {
                row.spawn((
                    Node {
                        flex_grow: 1.0,
                        flex_basis: px(0),
                        min_width: px(0),
                        padding: UiRect::axes(px(7), px(2)),
                        column_gap: px(7),
                        border: UiRect::left(px(3)),
                        ..default()
                    },
                    BackgroundColor(chip.color().with_alpha(0.09)),
                    BorderColor::all(chip.color()),
                ))
                .with_children(|card| {
                    // Native shapes remain recognizable without a downloaded icon font.
                    card.spawn((
                        Node {
                            width: px(9),
                            height: px(9),
                            margin: UiRect::top(px(3)),
                            flex_shrink: 0.0,
                            border_radius: if chip == ResourceChip::Cash {
                                BorderRadius::MAX
                            } else {
                                BorderRadius::ZERO
                            },
                            ..default()
                        },
                        BackgroundColor(chip.color()),
                        Pickable::IGNORE,
                    ));
                    card.spawn(ui::text(format!("{}  ", chip.label()), 12.0, chip.color()))
                        .insert((
                            chip,
                            Node {
                                flex_grow: 1.0,
                                flex_basis: px(0),
                                min_width: px(0),
                                ..default()
                            },
                        ))
                        .with_children(|text| {
                            text.spawn((
                                TextSpan::new("Unavailable"),
                                Amount(chip),
                                TextFont {
                                    font_size: FontSize::Px(13.0),
                                    weight: FontWeight::BOLD,
                                    ..default()
                                },
                                TextColor(theme::PAPER),
                                ObserverFontRole::Body,
                            ));
                            text.spawn((
                                TextSpan::new(""),
                                Period(chip),
                                TextFont {
                                    font_size: FontSize::Px(10.0),
                                    ..default()
                                },
                                TextColor(theme::GRAY),
                                ObserverFontRole::Body,
                            ));
                        });
                });
            }
        })
        .id()
}

fn paint(
    client: Option<Res<OrganizerClient>>,
    session: Res<ObserverSession>,
    mut roots: Query<&mut Node, With<ResourceHud>>,
    mut amounts: Query<(&Amount, &mut TextSpan), Without<Period>>,
    mut periods: Query<(&Period, &mut TextSpan), Without<Amount>>,
) {
    for mut node in &mut roots {
        let display = if session.organizer_enabled {
            Display::Flex
        } else {
            Display::None
        };
        if node.display != display {
            node.display = display;
        }
    }
    let means = client
        .as_deref()
        .and_then(|client| workspace::resources(client, &session));
    for (amount, mut span) in &mut amounts {
        let (value, _) = amount.0.reading(means, session.viewed_tick);
        if span.0 != value {
            span.0 = value;
        }
    }
    for (period, mut span) in &mut periods {
        let (_, caption) = period.0.reading(means, session.viewed_tick);
        let value = format!("\n{caption}");
        if span.0 != value {
            span.0 = value;
        }
    }
}

pub(super) fn install(app: &mut App) {
    app.add_systems(Update, paint.in_set(ObserverSet::Paint));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn missing_and_stale_resources_never_turn_into_zero_or_future_capacity() {
        let (client, mut session) = super::super::tests::ready();
        session.viewed_tick = 2;
        let means = workspace::resources(&client, &session);
        assert!(
            means.is_none(),
            "historical inspection cannot spend retained live resources"
        );
        for chip in [
            ResourceChip::Cash,
            ResourceChip::OrganizerHours,
            ResourceChip::HouseholdTime,
        ] {
            let (amount, caption) = chip.reading(means, session.viewed_tick);
            assert_eq!(amount, "Unavailable", "missing {chip:?} is never zero");
            assert!(caption.contains("unavailable"), "{chip:?}: {caption}");
        }
        let (_, caption) = ResourceChip::HouseholdTime.reading(None, 2);
        assert!(
            caption.contains("next period unknown"),
            "household hours are a dated reading"
        );
    }

    #[test]
    fn exact_resource_extremes_remain_dated_and_separate_from_action_costs() {
        let means = ResourceSummary {
            period: 3,
            cash_micros: Some(i128::MIN),
            organizer_hours: u64::MAX,
            standing_authorized: true,
            shared_time: Some((3, u64::MAX)),
        };
        let (cash, _) = ResourceChip::Cash.reading(Some(means), 3);
        assert_eq!(
            cash, "-$170,141,183,460,469,231,731,687,303,715,884.105728",
            "no rounded treasury balance"
        );
        let (hours, _) = ResourceChip::OrganizerHours.reading(Some(means), 3);
        assert_eq!(
            hours, "18,446,744,073,709,551,615 h pledged",
            "exact organizer pledge"
        );
        let (household, period) = ResourceChip::HouseholdTime.reading(Some(means), 3);
        assert!(household.contains("closed P3"), "closed period is explicit");
        assert_eq!(
            period, "next period unknown",
            "reading is never a future allowance"
        );
    }
}
