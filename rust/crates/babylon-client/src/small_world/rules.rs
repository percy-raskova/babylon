//! The closest form's rules in the scene: the list of switches in the rail's lower part, its
//! rows, the press of a row and the refusals' words. The runner decides what a switch does; this
//! module only shows where each stands and asks it to turn on.

use super::controls;
use super::panel;
use super::scene::{SceneCommand, SceneRunner};
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use crate::ui;
use babylon_circuit_worlds::{RuleError, Runner, Switch, World};
use babylon_material_circuit::AdjustmentRule;
use bevy::picking::pointer::PointerButton;
use bevy::prelude::*;

/// A rule of the closest form as the scene names it: the kinds of `World::switches`, in the order of
/// `AdjustmentRule`.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum SceneRule {
    HiringWithinMeans,
    SeekingInPlace,
    StopWithoutPay,
    RestingPrice,
    OwnerRestart,
    GoodsStepDown,
}

impl SceneRule {
    /// Every rule, in the order of `AdjustmentRule`.
    pub const ALL: [SceneRule; 6] = [
        Self::HiringWithinMeans,
        Self::SeekingInPlace,
        Self::StopWithoutPay,
        Self::RestingPrice,
        Self::OwnerRestart,
        Self::GoodsStepDown,
    ];

    /// The order of the list on screen, which is the order the rules are built and the order of the list the
    /// Director picked: the seekers, the bound, the stop rule, the resting price, the restart, the step down.
    pub const LISTED: [SceneRule; 6] = [
        Self::SeekingInPlace,
        Self::HiringWithinMeans,
        Self::StopWithoutPay,
        Self::RestingPrice,
        Self::OwnerRestart,
        Self::GoodsStepDown,
    ];

    /// Its place in `World::switches`: 0 to 5 in the order of `ALL`.
    #[must_use]
    pub const fn index(self) -> usize {
        match self {
            Self::HiringWithinMeans => 0,
            Self::SeekingInPlace => 1,
            Self::StopWithoutPay => 2,
            Self::RestingPrice => 3,
            Self::OwnerRestart => 4,
            Self::GoodsStepDown => 5,
        }
    }

    /// The name a script gives the rule.
    #[must_use]
    pub const fn script_name(self) -> &'static str {
        match self {
            Self::HiringWithinMeans => "hiring_within_means",
            Self::SeekingInPlace => "seeking_in_place",
            Self::StopWithoutPay => "stop_without_pay",
            Self::RestingPrice => "resting_price",
            Self::OwnerRestart => "owner_restart",
            Self::GoodsStepDown => "goods_step_down",
        }
    }

    /// The script's name read back.
    #[must_use]
    pub fn named(name: &str) -> Option<SceneRule> {
        Self::ALL
            .into_iter()
            .find(|rule| rule.script_name() == name)
    }

    /// The rule of this kind that `world` turns on: `world.switches()[self.index()]`.
    #[must_use]
    pub fn rule(self, world: &World) -> AdjustmentRule {
        world.switches()[self.index()]
    }

    /// The kind of a rule (`OwnerRestart` with any `outlay_periods`).
    #[must_use]
    pub const fn of(rule: AdjustmentRule) -> SceneRule {
        match rule {
            AdjustmentRule::HiringWithinMeans => Self::HiringWithinMeans,
            AdjustmentRule::SeekingInPlace => Self::SeekingInPlace,
            AdjustmentRule::StopWithoutPay => Self::StopWithoutPay,
            AdjustmentRule::RestingPrice => Self::RestingPrice,
            AdjustmentRule::OwnerRestart { .. } => Self::OwnerRestart,
            AdjustmentRule::GoodsStepDown => Self::GoodsStepDown,
        }
    }
}

/// The rules whose switches the scene shows: the first of `SceneRule::LISTED`, as far as they are built. Each
/// rule's companion task appends its own; nothing else does.
pub const SHOWN_RULES: &[SceneRule] = &[];
/// Whether the rail has the rules' tab: every other place reads this, not `SHOWN_RULES.is_empty()`.
#[allow(clippy::const_is_empty, reason = "the list grows task by task")]
pub const RULES_SHOWN: bool = !SHOWN_RULES.is_empty();
/// The title of the list's one column.
pub const FROM_LINE: &str = "on from period";
/// The standing lines under the list.
pub const RULES_LINE: &str =
    "Turned on, a rule stays until you start over. A rule that needs another waits for it.";

const ROW_HEIGHT: f32 = 28.0;
const FROM_WIDTH: f32 = 44.0;

/// A rule's switch: the button of its row in the rules' tab.
#[derive(Component, Clone, Copy, Debug, PartialEq, Eq)]
pub struct RuleButton(pub SceneRule);

/// The list of the rules' tab, rebuilt when the runner changes.
#[derive(Component)]
pub struct RulesBody;

/// One row of the list as it is drawn.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SwitchRow {
    pub rule: SceneRule,
    /// `rule_name` of the world's rule of this kind.
    pub name: &'static str,
    /// The first period closed under it, while it is on.
    pub from: Option<u64>,
    /// "(needs: {names})" while it waits: each name with its first letter in lower case, joined by "; ".
    pub needs: Option<String>,
}

/// A name with its first letter in lower case.
fn lower_first(name: &str) -> String {
    let mut chars = name.chars();
    chars.next().map_or_else(String::new, |first| {
        first.to_lowercase().chain(chars).collect()
    })
}

/// The row of one rule from where its switch stands.
#[must_use]
pub fn switch_row(rule: SceneRule, name: &'static str, switch: &Switch) -> SwitchRow {
    let (from, needs) = match switch {
        Switch::On { from } => (Some(*from), None),
        Switch::Ready => (None, None),
        Switch::Waits { needs } => {
            let names: Vec<String> = needs
                .iter()
                .map(|need| lower_first(babylon_circuit_worlds::rule_name(*need)))
                .collect();
            (None, Some(format!("(needs: {})", names.join("; "))))
        }
    };
    SwitchRow {
        rule,
        name,
        from,
        needs,
    }
}

/// A row for each of `SHOWN_RULES`, in order: `switch_row` of `runner.switch(rule.rule(runner.world()))`.
#[must_use]
pub fn switch_rows(runner: &Runner) -> Vec<SwitchRow> {
    SHOWN_RULES
        .iter()
        .map(|rule| {
            let wanted = rule.rule(runner.world());
            switch_row(
                *rule,
                babylon_circuit_worlds::rule_name(wanted),
                &runner.switch(wanted),
            )
        })
        .collect()
}

/// The runner's refusal in its own words, the first letter in upper case.
#[must_use]
pub fn rule_refusal_words(error: &RuleError) -> String {
    let words = error.to_string();
    let mut chars = words.chars();
    chars.next().map_or_else(String::new, |first| {
        first.to_uppercase().chain(chars).collect()
    })
}

/// The rules' tab: `RulesBody`, then `RULES_LINE`, then a `NoticeLine`.
pub fn spawn_rules_tab(body: &mut ChildSpawnerCommands) {
    body.spawn((
        RulesBody,
        Node {
            flex_direction: FlexDirection::Column,
            row_gap: px(2),
            ..default()
        },
    ));
    body.spawn((
        controls::text(RULES_LINE, 11.0, theme::GRAY, ObserverFontRole::Body),
        Node {
            margin: UiRect::top(px(6)),
            ..default()
        },
    ));
    body.spawn((
        controls::text("", 12.0, theme::RED, ObserverFontRole::Body),
        panel::NoticeLine,
        Node {
            margin: UiRect::top(px(4)),
            ..default()
        },
    ));
}

fn spawn_row(list: &mut ChildSpawnerCommands, row: &SwitchRow) {
    let on = row.from.is_some();
    let waiting = row.needs.is_some();
    let color = if waiting { theme::GRAY } else { theme::PAPER };
    list.spawn(Node {
        flex_direction: FlexDirection::Column,
        ..default()
    })
    .with_children(|group| {
        group
            .spawn(Node {
                column_gap: px(4),
                align_items: AlignItems::Center,
                ..default()
            })
            .with_children(|line| {
                let mut node = Node {
                    height: px(ROW_HEIGHT),
                    flex_grow: 1.0,
                    border: UiRect::all(px(1)),
                    padding: UiRect::horizontal(px(8)),
                    align_items: AlignItems::Center,
                    ..default()
                };
                let mut border = BorderColor::all(theme::PAPER);
                panel::mark(&mut node, &mut border, on);
                line.spawn((
                    ui::pressable(),
                    RuleButton(row.rule),
                    node,
                    border,
                    BackgroundColor(Color::NONE),
                ))
                .with_child(controls::text(
                    row.name,
                    13.0,
                    color,
                    ObserverFontRole::Body,
                ));
                line.spawn(Node {
                    width: px(FROM_WIDTH),
                    justify_content: JustifyContent::FlexEnd,
                    ..default()
                })
                .with_children(|from| {
                    if let Some(period) = row.from {
                        from.spawn(controls::text(
                            period.to_string(),
                            13.0,
                            theme::PAPER,
                            ObserverFontRole::Body,
                        ));
                    }
                });
            });
        if let Some(needs) = &row.needs {
            group.spawn((
                controls::text(needs, 11.0, theme::GRAY, ObserverFontRole::Body),
                Node {
                    margin: UiRect::left(px(12)),
                    ..default()
                },
            ));
        }
    });
}

/// Rebuild the list when the runner changed.
pub fn paint_rules(
    mut commands: Commands,
    scene: Res<SceneRunner>,
    body: Query<Entity, With<RulesBody>>,
) {
    if !scene.is_changed() {
        return;
    }
    let Ok(body) = body.single() else {
        return;
    };
    let rows = switch_rows(&scene.runner);
    commands.entity(body).despawn_related::<Children>();
    commands.entity(body).with_children(|list| {
        list.spawn(Node {
            width: percent(100),
            justify_content: JustifyContent::FlexEnd,
            ..default()
        })
        .with_child(controls::text(
            FROM_LINE,
            11.0,
            theme::GRAY,
            ObserverFontRole::Body,
        ));
        for row in &rows {
            spawn_row(list, row);
        }
    });
}

/// A press of a rule's row.
pub fn pressed(
    event: On<PointerClick>,
    buttons: Query<&RuleButton>,
    mut commands: MessageWriter<SceneCommand>,
) {
    if event.button != PointerButton::Primary {
        return;
    }
    if let Ok(RuleButton(rule)) = buttons.get(event.entity) {
        commands.write(SceneCommand::TurnOn(*rule));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::error::Error;

    #[test]
    fn scene_rules_follow_the_world_s_switches() {
        for (place, rule) in SceneRule::ALL.into_iter().enumerate() {
            assert_eq!(rule.index(), place);
            assert_eq!(SceneRule::ALL[rule.index()], rule);
            assert_eq!(SceneRule::of(World::scene().switches()[rule.index()]), rule);
            assert_eq!(SceneRule::named(rule.script_name()), Some(rule));
        }
        assert_eq!(
            SceneRule::OwnerRestart.rule(&World::scene()),
            AdjustmentRule::OwnerRestart { outlay_periods: 1 }
        );
        assert!(SceneRule::ALL.windows(2).all(|pair| pair[0] < pair[1]));
        assert_eq!(
            SceneRule::LISTED,
            [
                SceneRule::SeekingInPlace,
                SceneRule::HiringWithinMeans,
                SceneRule::StopWithoutPay,
                SceneRule::RestingPrice,
                SceneRule::OwnerRestart,
                SceneRule::GoodsStepDown,
            ]
        );
        assert_eq!(SHOWN_RULES, &SceneRule::LISTED[..SHOWN_RULES.len()]);
        let names: Vec<&str> = SceneRule::ALL.iter().map(|r| r.script_name()).collect();
        assert_eq!(
            names,
            [
                "hiring_within_means",
                "seeking_in_place",
                "stop_without_pay",
                "resting_price",
                "owner_restart",
                "goods_step_down",
            ]
        );
        assert_eq!(SceneRule::named("everything"), None);
    }

    #[test]
    fn a_rule_s_refusal_is_told_in_the_runner_s_words() {
        assert_eq!(
            rule_refusal_words(&RuleError::Waits {
                rule: AdjustmentRule::StopWithoutPay,
                needs: vec![AdjustmentRule::SeekingInPlace],
            }),
            "No money, no work waits for people look for work in their place"
        );
        assert_eq!(
            rule_refusal_words(&RuleError::AlreadyOn {
                rule: AdjustmentRule::SeekingInPlace,
                from: 14,
            }),
            "People look for work in their place is on from period 14 and holds until you start over"
        );
        assert_eq!(
            rule_refusal_words(&RuleError::Stopped),
            "The run is stopped"
        );
    }

    #[test]
    fn a_row_says_where_its_switch_stands() -> Result<(), Box<dyn Error>> {
        let seekers = babylon_circuit_worlds::rule_name(AdjustmentRule::SeekingInPlace);
        assert_eq!(seekers, "People look for work in their place");
        let on = switch_row(SceneRule::SeekingInPlace, seekers, &Switch::On { from: 14 });
        assert_eq!((on.from, on.needs), (Some(14), None));
        let ready = switch_row(SceneRule::SeekingInPlace, seekers, &Switch::Ready);
        assert_eq!((ready.from, ready.needs), (None, None));
        let stop = babylon_circuit_worlds::rule_name(AdjustmentRule::StopWithoutPay);
        let waits = switch_row(
            SceneRule::StopWithoutPay,
            stop,
            &Switch::Waits {
                needs: vec![AdjustmentRule::SeekingInPlace],
            },
        );
        assert_eq!(
            waits.needs.as_deref(),
            Some("(needs: people look for work in their place)")
        );
        let many = switch_row(
            SceneRule::OwnerRestart,
            babylon_circuit_worlds::rule_name(AdjustmentRule::OwnerRestart { outlay_periods: 1 }),
            &Switch::Waits {
                needs: vec![
                    AdjustmentRule::HiringWithinMeans,
                    AdjustmentRule::StopWithoutPay,
                    AdjustmentRule::RestingPrice,
                ],
            },
        );
        assert_eq!(
            many.needs.as_deref(),
            Some("(needs: a bound on hiring; no money, no work; a resting price)")
        );
        let runner = Runner::open()?;
        let rows = switch_rows(&runner);
        assert_eq!(rows.len(), SHOWN_RULES.len());
        for (row, rule) in rows.iter().zip(SHOWN_RULES) {
            assert_eq!(row.rule, *rule);
            assert_eq!(
                row.name,
                babylon_circuit_worlds::rule_name(rule.rule(runner.world()))
            );
        }
        Ok(())
    }
}
