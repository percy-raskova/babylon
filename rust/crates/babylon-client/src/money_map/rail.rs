//! The selected county's bilateral connections share the inspector's focus group and scroll area.
use super::state::{
    self, Action, Connection, Direction, MoneyRail, MoneyView, Observation, Scope, Status, Target,
};
use crate::atlas::CountyAtlas;
use crate::observer_focus::ObserverFocusTarget;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use crate::ui::{self, Interaction};
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart, UsDependency};
use babylon_persistence::money_journal::{FlowAmounts, FlowPage};
use bevy::a11y::AccessibilityNode;
use bevy::prelude::*;

fn amount(micros: &str) -> String {
    // A period sum may exceed one posting's currency range. Keep its complete decimal then.
    micros.parse::<i128>().map_or_else(
        |_| format!("{micros} micros"),
        crate::human_numbers::currency,
    )
}

pub(super) fn location(key: Option<&str>, atlas: &CountyAtlas) -> String {
    let Some(key) = key else {
        return "Location unreported".into();
    };
    match key.parse::<EconomicLocation>() {
        Ok(EconomicLocation::County(_)) => {
            let geoid = &key["county:".len()..];
            atlas
                .index_of_fips(geoid)
                .and_then(|index| atlas.county(index))
                .map_or_else(
                    || format!("County {geoid}"),
                    |c| format!("{} · {geoid}", c.name),
                )
        }
        Ok(EconomicLocation::Foreign(region)) => match region {
            ForeignCounterpart::Canada => "Canada",
            ForeignCounterpart::Mexico => "Mexico",
            ForeignCounterpart::China => "China",
            ForeignCounterpart::Russia => "Russia",
            ForeignCounterpart::India => "India",
            ForeignCounterpart::Japan => "Japan",
            ForeignCounterpart::EuropeanUnion => "European Union",
            ForeignCounterpart::RemainingEurope => "Remaining Europe",
            ForeignCounterpart::LatinAmericaCaribbean => "Latin America and the Caribbean",
            ForeignCounterpart::WestAsiaNorthAfrica => "West Asia and North Africa",
            ForeignCounterpart::SubSaharanAfrica => "Sub-Saharan Africa",
            ForeignCounterpart::RemainingAsiaPacific => "Remaining Asia-Pacific",
        }
        .into(),
        Ok(EconomicLocation::Dependency(region)) => match region {
            UsDependency::AmericanSamoa => "American Samoa",
            UsDependency::Guam => "Guam",
            UsDependency::NorthernMarianaIslands => "Northern Mariana Islands",
            UsDependency::PuertoRico => "Puerto Rico",
            UsDependency::MinorOutlyingIslands => "US Minor Outlying Islands",
            UsDependency::VirginIslands => "US Virgin Islands",
        }
        .into(),
        Err(_) => format!("Unrecognized location ({key})"),
    }
}

fn caption(row: &Connection, atlas: &CountyAtlas) -> String {
    let peer = location(row.key.peer.as_deref(), atlas);
    let amount = amount(&row.micros);
    match row.key.direction {
        Direction::PaidTo => format!("Paid to {peer}\n{amount}"),
        Direction::ReceivedFrom => format!("Received from {peer}\n{amount}"),
        Direction::Internal => format!("Within county\n{amount}"),
    }
}

fn figures(group: &FlowAmounts) -> String {
    format!(
        "Received {}\nPaid {}\nWithin county {}",
        amount(&group.outflow_micros),
        amount(&group.inflow_micros),
        amount(&group.internal_micros)
    )
}

fn label(text: impl Into<String>, size: f32, color: Color, role: ObserverFontRole) -> impl Bundle {
    (
        Text::new(text),
        TextFont {
            font_size: FontSize::Px(size),
            ..default()
        },
        TextColor(color),
        role,
        Pickable::IGNORE,
    )
}

fn control(
    parent: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
    action: Action,
    text: String,
) {
    let mut focus = ObserverFocusTarget::action(Some(scope.context.clone()));
    focus.available = true;
    let mut button = parent.spawn((
        ui::pressable(),
        focus,
        Target {
            scope: scope.clone(),
            offset: view.offset,
            action,
        },
        Node {
            width: percent(100),
            min_width: px(0),
            flex_shrink: 0.0,
            padding: UiRect::axes(px(8), px(5)),
            border: UiRect::left(px(3)),
            ..default()
        },
        BorderColor::all(theme::GRAY),
        BackgroundColor(theme::INK),
    ));
    let name = text.clone();
    button
        .entry::<AccessibilityNode>()
        .and_modify(move |mut node| node.set_label(name));
    button.observe(state::keyboard).with_child(label(
        text,
        15.0,
        theme::PAPER,
        ObserverFontRole::Body,
    ));
}

#[derive(PartialEq, Eq)]
pub(super) struct RailKey {
    scope: Option<Scope>,
    offset: u64,
    status: Status,
    active: bool,
}

pub(super) fn paint(
    mut commands: Commands,
    obs: Observation,
    view: Res<MoneyView>,
    mut rails: Query<(Entity, &mut Node), With<MoneyRail>>,
    mut previous: Local<Option<RailKey>>,
) {
    let Ok((panel, mut node)) = rails.single_mut() else {
        return;
    };
    if !(view.is_changed()
        || obs.ui.is_changed()
        || obs.primary.is_changed()
        || obs.session.is_changed()
        || node.is_added())
    {
        return;
    }
    let active = obs.active();
    let key = RailKey {
        scope: view.scope.clone(),
        offset: view.offset,
        status: view.status,
        active,
    };
    if previous.as_ref() == Some(&key) {
        return;
    }
    *previous = Some(key);
    commands.entity(panel).despawn_children();
    let display = if active { Display::Flex } else { Display::None };
    if node.display != display {
        node.display = display;
    }
    if !active {
        return;
    }
    commands
        .entity(panel)
        .with_children(|rail| populate(rail, &view, &obs.atlas));
}

fn populate(rail: &mut ChildSpawnerCommands, view: &MoneyView, atlas: &CountyAtlas) {
    rail.spawn(label(
        "Settled payments",
        22.0,
        theme::PAPER,
        ObserverFontRole::Display,
    ));
    let Some(scope) = &view.scope else {
        rail.spawn(label(
            "Waiting for the county observation.",
            15.0,
            theme::GRAY,
            ObserverFontRole::Body,
        ));
        return;
    };
    let notice = match view.status {
        Status::Opening => Some(
            "The opening records balances. Payments begin with the first committed period."
                .to_owned(),
        ),
        Status::Waiting | Status::Loading => {
            Some(format!("Reading period {}…", scope.context.tick))
        }
        Status::Publishing => Some(format!(
            "Period {} has committed. Its payment report is being prepared.",
            scope.context.tick
        )),
        Status::Failed(error) => Some(format!("The payment report could not be read ({error}).")),
        Status::Ready => None,
    };
    if let Some(notice) = notice {
        rail.spawn(label(notice, 15.0, theme::GRAY, ObserverFontRole::Body));
        if matches!(view.status, Status::Failed(_)) {
            control(rail, view, scope, Action::Retry, "Retry report".into());
        }
        return;
    }
    if let Some(page) = &view.page {
        ranked_page(rail, view, scope, atlas, page);
    }
}

fn ranked_page(
    rail: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
    atlas: &CountyAtlas,
    page: &FlowPage,
) {
    if page.total.groups == 0 {
        rail.spawn(label(
            format!(
                "No settled payments for this county in period {}.",
                scope.context.tick
            ),
            15.0,
            theme::PAPER,
            ObserverFontRole::Body,
        ));
        return;
    }
    rail.spawn(label(
        format!(
            "Period {}\n{}",
            scope.context.tick,
            figures(&page.total.current)
        ),
        17.0,
        theme::PAPER,
        ObserverFontRole::Exact,
    ));
    let visible = page.groups.len() as u64;
    rail.spawn(label(
        format!(
            "Counterparties {}–{} of {}",
            view.offset + 1,
            view.offset + visible,
            page.total.groups
        ),
        15.0,
        theme::GRAY,
        ObserverFontRole::Body,
    ));
    rail.spawn(label(
        "Arrows follow the payment. Width compares amounts on this page.",
        13.0,
        theme::GRAY,
        ObserverFontRole::Body,
    ));
    rail.spawn((
        label("", 15.0, theme::YELLOW, ObserverFontRole::Body),
        SelectionLabel,
    ));
    control(
        rail,
        view,
        scope,
        Action::Follow,
        "Open counterparty county".into(),
    );
    for row in &view.rows {
        control(
            rail,
            view,
            scope,
            Action::Select(row.key.clone()),
            caption(row, atlas),
        );
    }
    if page.remainder.groups > 0 {
        rail.spawn(label(
            format!(
                "Other {} counterparties\n{}",
                page.remainder.groups,
                figures(&page.remainder.current)
            ),
            15.0,
            theme::GRAY,
            ObserverFontRole::Exact,
        ));
    }
    if view.offset > 0 {
        control(
            rail,
            view,
            scope,
            Action::Page(view.offset.saturating_sub(20)),
            "Previous counterparties".into(),
        );
    }
    if view.offset + visible < page.total.groups {
        control(
            rail,
            view,
            scope,
            Action::Page(view.offset + visible),
            "More counterparties".into(),
        );
    }
}

#[derive(Component)]
pub(super) struct SelectionLabel;

type MoneyControl = (
    &'static Target,
    Ref<'static, Interaction>,
    &'static mut BorderColor,
    &'static mut BackgroundColor,
    &'static mut Node,
    &'static mut ObserverFocusTarget,
);

pub(super) fn highlight(
    view: Res<MoneyView>,
    obs: Observation,
    mut labels: Query<&mut Text, With<SelectionLabel>>,
    mut targets: Query<MoneyControl>,
) {
    for mut text in &mut labels {
        if !view.is_changed() && !text.is_added() {
            continue;
        }
        let value = view.selected_row().map_or_else(String::new, |row| {
            let peer = location(row.key.peer.as_deref(), &obs.atlas);
            let county = view.scope.as_ref().map_or_else(String::new, |s| {
                location(Some(&format!("county:{}", s.county)), &obs.atlas)
            });
            let (from, to) = match row.key.direction {
                Direction::PaidTo => (county, peer),
                Direction::ReceivedFrom => (peer, county),
                Direction::Internal => (county.clone(), county),
            };
            let amount = amount(&row.micros);
            row.key.peer.as_deref().map_or_else(
                || format!("{from} → {to}\n{amount}"),
                |key| format!("{from} → {to}\n{amount}\nLocation code {key}"),
            )
        });
        text.set_if_neq(Text::new(value));
    }
    for (target, interaction, mut border, mut background, mut node, mut focus) in &mut targets {
        if !view.is_changed()
            && !interaction.is_changed()
            && !node.is_added()
            && !obs.ui.is_changed()
        {
            continue;
        }
        if target.action == Action::Follow {
            let available = view
                .selected_row()
                .and_then(|row| row.key.peer.as_deref())
                .and_then(|key| key.strip_prefix("county:"))
                .is_some_and(|geoid| {
                    geoid != target.scope.county
                        && obs
                            .atlas
                            .index_of_fips(geoid)
                            .is_some_and(|idx| obs.counties.contains(idx))
                });
            let enabled = available && obs.interactive();
            if focus.available != enabled {
                focus.available = enabled;
            }
            let display = if available {
                Display::Flex
            } else {
                Display::None
            };
            if node.display != display {
                node.display = display;
            }
        }
        if target.action != Action::Follow && focus.available != obs.interactive() {
            focus.available = obs.interactive();
        }
        let active = matches!(&target.action,Action::Select(row) if view.selected_row().is_some_and(|active| &active.key == row));
        border.set_if_neq(BorderColor::all(if active {
            theme::YELLOW
        } else {
            theme::GRAY
        }));
        background.set_if_neq(BackgroundColor(
            if active || *interaction != Interaction::None {
                theme::PANEL
            } else {
                theme::INK
            },
        ));
    }
}
