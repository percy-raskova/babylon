//! The selected county's bilateral connections share the inspector's focus group and scroll area.
use super::compare::{self, Periods};
use super::freight::{Command as FreightCommand, PageKey as FreightPageKey};
use super::geographic_legs::LocationList;
use super::state::{
    self, Action, Connection, Diagram, Direction, Measure, MoneyRail, MoneyView, Observation, Page,
    Quantity, Scope, Status, Target,
};
use super::{company, freight_rail, grouping, industry};
use crate::atlas::CountyAtlas;
use crate::observer_focus::ObserverFocusTarget;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use crate::ui::{self, Interaction};
use babylon_kernel::economic_location::{EconomicLocation, ForeignCounterpart, UsDependency};
use babylon_material_circuit::CompanyId;
use babylon_persistence::money_journal::{
    FlowAmounts, FlowGroup, FlowRow, LaborAmount, LaborDirections, LaborFlowRow,
};
use bevy::a11y::AccessibilityNode;
use bevy::prelude::*;
use bevy::text::LineBreak;

pub(super) fn amount(micros: &str) -> String {
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

pub(super) fn labor_hours(micros: &str) -> String {
    micros.parse::<u128>().map_or_else(
        |_| format!("{micros} recorded microhours"),
        |value| {
            let whole = crate::human_numbers::grouped(value / 1_000_000);
            let fraction = format!("{:06}", value % 1_000_000);
            let fraction = fraction.trim_end_matches('0');
            if fraction.is_empty() {
                format!("{whole} recorded h")
            } else {
                format!("{whole}.{fraction} recorded h")
            }
        },
    )
}

fn labor_reading(labor: &LaborAmount) -> String {
    let known = labor_hours(&labor.recorded_micro_hours);
    if labor.unknown_basis_movements == "0" {
        return known;
    }
    format!(
        "{known}, unknown prior labor in {} of {} movements",
        labor.unknown_basis_movements, labor.movement_count
    )
}

pub(super) fn reading(quantity: &Quantity) -> String {
    match quantity {
        Quantity::Money(micros) => amount(micros),
        Quantity::Labor(labor) => labor_reading(labor),
    }
}

fn labor_figures(group: &LaborDirections) -> String {
    format!(
        "Received from other or unlocated endpoints {}\nSent to other or unlocated endpoints {}\nWithin county {}",
        labor_reading(&group.outbound),
        labor_reading(&group.inbound),
        labor_reading(&group.within)
    )
}

fn caption(row: &Connection, scope: &Scope, atlas: &CountyAtlas) -> String {
    let peer = grouping::peer_label(scope, row.key.peer.as_deref(), row.label.as_deref(), atlas);
    let amount = reading(&row.quantity);
    match row.key.direction {
        Direction::PaidTo if matches!(row.quantity, Quantity::Labor(_)) => {
            format!("Sent to {peer}\n{amount}")
        }
        Direction::PaidTo => format!("Paid to {peer}\n{amount}"),
        Direction::ReceivedFrom => format!("Received from {peer}\n{amount}"),
        Direction::Internal if scope.group != FlowGroup::Location => {
            format!("Within county · from {peer}\n{amount}")
        }
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

pub(super) fn label(
    text: impl Into<String>,
    size: f32,
    color: Color,
    role: ObserverFontRole,
) -> impl Bundle {
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

pub(super) fn control(
    parent: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
    action: Action,
    text: String,
) {
    let mut focus = ObserverFocusTarget::action(Some(scope.context.clone()));
    focus.available = true;
    let paired_control = matches!(
        action,
        Action::Diagram(_) | Action::Measure(_) | Action::Group(_)
    );
    let mut button = parent.spawn((
        ui::pressable(),
        focus,
        Target {
            scope: scope.clone(),
            offset: view.offset,
            action,
        },
        Node {
            width: if paired_control {
                percent(50)
            } else {
                percent(100)
            },
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
    books: (Option<u64>, bool),
    company: (Option<CompanyId>, bool, bool),
    freight: Option<FreightPageKey>,
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
        books: view.books.key(),
        company: view.company.key(),
        freight: view.freight.page_key(),
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
        .with_children(|rail| populate(rail, &view, &obs));
}

fn populate(rail: &mut ChildSpawnerCommands, view: &MoneyView, obs: &Observation) {
    if view.freight.enabled {
        if let Some(scope) = &view.scope {
            freight_rail::panel(rail, view, scope, &obs.atlas);
        }
        return;
    }
    if view
        .scope
        .as_ref()
        .is_some_and(|scope| company::panel(rail, view, scope))
    {
        return;
    }
    rail.spawn(label(
        match view.scope.as_ref().map(|scope| scope.measure) {
            Some(Measure::Labor) => "Recorded labor flows",
            _ => "Settled payments",
        },
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
    for pair in [
        [
            (Action::Measure(Measure::Money), "Money"),
            (Action::Measure(Measure::Labor), "Labor hours"),
        ],
        [
            (Action::Diagram(Diagram::Map), "Map"),
            (Action::Diagram(Diagram::Sankey), "Sankey"),
        ],
    ] {
        rail.spawn(Node {
            width: percent(100),
            flex_direction: FlexDirection::Row,
            ..default()
        })
        .with_children(|choices| {
            for (action, name) in pair {
                control(choices, view, scope, action, name.to_owned());
            }
        });
    }
    control(
        rail,
        view,
        scope,
        Action::Freight(FreightCommand::Open),
        "Freight access".into(),
    );
    if super::books::panel(rail, view, obs, scope) {
        return;
    }
    grouping::controls(rail, view, scope);
    comparison_control(rail, view, scope);
    let notice = match view.status {
        Status::Opening => Some(
            match scope.measure {
                Measure::Money => {
                    "The opening records balances. Payments begin with the first committed period."
                }
                Measure::Labor => "Recorded labor transfers begin with the first committed period.",
            }
            .to_owned(),
        ),
        Status::Waiting | Status::Loading => {
            Some(format!("Reading period {}…", scope.context.tick))
        }
        Status::Publishing if scope.periods == Periods::WithPrior => Some(format!(
            "Waiting for published flow coverage in periods {} and {}.",
            scope.context.tick - 1,
            scope.context.tick
        )),
        Status::Publishing => Some(format!(
            "Period {} has committed. Its flow report is being prepared.",
            scope.context.tick
        )),
        Status::Failed(error) => Some(format!("The flow report could not be read ({error}).")),
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
        ranked_page(rail, view, scope, &obs.atlas, page);
    }
}

fn comparison_control(rail: &mut ChildSpawnerCommands, view: &MoneyView, scope: &Scope) {
    let tick = scope.context.tick;
    if tick == 1 {
        rail.spawn(label(
            "Period 1 is the first completed period.",
            13.0,
            theme::GRAY,
            ObserverFontRole::Body,
        ));
    } else if tick > 1 {
        let (next, text) = match scope.periods {
            Periods::Current => (
                Periods::WithPrior,
                format!("Compare with period {}", tick - 1),
            ),
            Periods::WithPrior => (Periods::Current, format!("Show period {tick} only")),
        };
        control(rail, view, scope, Action::Compare(next), text);
    }
}

fn money_figures(row: &FlowRow, tick: u64) -> String {
    format!(
        "{}\n{}",
        figures(&row.current),
        compare::money_net(row, tick)
    )
}
fn recorded_figures(row: &LaborFlowRow, tick: u64) -> String {
    format!(
        "{}\n{}",
        labor_figures(&row.current),
        compare::labor_net(row, tick)
    )
}

fn ranked_page(
    rail: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
    atlas: &CountyAtlas,
    page: &Page,
) {
    let total_groups = page.total_groups();
    if total_groups == 0 {
        rail.spawn(label(
            format!(
                "No {} for this county in period {}.",
                if scope.measure == Measure::Labor {
                    "recorded labor movements"
                } else {
                    "settled payments"
                },
                scope.context.tick
            ),
            15.0,
            theme::PAPER,
            ObserverFontRole::Body,
        ));
        return;
    }
    let (visible, total, remaining_groups, remainder) = match page {
        Page::Money(p) => (
            p.groups.len(),
            money_figures(&p.total, scope.context.tick),
            p.remainder.groups,
            money_figures(&p.remainder, scope.context.tick),
        ),
        Page::Labor(p) => (
            p.groups.len(),
            recorded_figures(&p.total, scope.context.tick),
            p.remainder.groups,
            recorded_figures(&p.remainder, scope.context.tick),
        ),
    };
    rail.spawn(label(
        format!("Period {}\n{total}", scope.context.tick),
        17.0,
        theme::PAPER,
        ObserverFontRole::Exact,
    ));
    let visible = visible as u64;
    rail.spawn(label(
        format!(
            "Counterparties {}–{} of {}",
            view.offset + 1,
            view.offset + visible,
            total_groups
        ),
        15.0,
        theme::GRAY,
        ObserverFontRole::Body,
    ));
    rail.spawn(label(
        match scope.measure {
            Measure::Money => "Arrows follow the payment. Width compares amounts on this page.",
            Measure::Labor => "Arrows follow labor carried by transfers. Width shows recorded hours. Unknown prior labor appears in the list.",
        },
        13.0,
        theme::GRAY,
        ObserverFontRole::Body,
    ));
    connection_controls(rail, view, scope, atlas);
    if remaining_groups > 0 {
        rail.spawn(label(
            format!("Other {remaining_groups} counterparties\n{remainder}"),
            15.0,
            theme::GRAY,
            ObserverFontRole::Exact,
        ));
    }
    page_controls(rail, view, scope, visible, total_groups);
}

fn connection_controls(
    rail: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
    atlas: &CountyAtlas,
) {
    rail.spawn((
        label("", 15.0, theme::YELLOW, ObserverFontRole::Body),
        SelectionLabel,
        TextLayout::linebreak(LineBreak::WordOrCharacter),
        Node {
            width: percent(100),
            min_width: px(0),
            ..default()
        },
    ));
    control(
        rail,
        view,
        scope,
        Action::Follow,
        "Open counterparty county".into(),
    );
    if scope.group == FlowGroup::Industry {
        control(
            rail,
            view,
            scope,
            Action::IndustrySources,
            "Show or hide industry sources".into(),
        );
        rail.spawn((
            label("", 15.0, theme::PAPER, ObserverFontRole::Body),
            SelectionLabel,
            SourceLabel,
            Node {
                width: percent(100),
                min_width: px(0),
                ..default()
            },
        ));
    }
    if matches!(scope.group, FlowGroup::Company | FlowGroup::Counterparty) {
        control(
            rail,
            view,
            scope,
            Action::CompanyAccounts(true),
            "Company accounts".into(),
        );
    }
    if scope.group != FlowGroup::Location {
        rail.spawn((
            LocationList::default(),
            Node {
                width: percent(100),
                flex_direction: FlexDirection::Column,
                ..default()
            },
        ));
        for (delta, name) in [
            (-1, "Previous locations"),
            (1, "More locations"),
            (0, "Retry location detail"),
        ] {
            control(rail, view, scope, Action::Geography(delta), name.into());
        }
    }
    if scope.group != FlowGroup::Location
        || view.rows.iter().any(|row| {
            row.quantity.micros() != "0"
                && (row.key.direction == Direction::Internal
                    || row
                        .key
                        .peer
                        .as_deref()
                        .and_then(|key| key.strip_prefix("county:"))
                        .and_then(|peer| atlas.index_of_fips(peer))
                        .is_some())
        })
    {
        control(
            rail,
            view,
            scope,
            Action::Frame,
            "Frame connections on map".into(),
        );
    }
    for row in &view.rows {
        control(
            rail,
            view,
            scope,
            Action::Select(row.key.clone()),
            caption(row, scope, atlas),
        );
    }
}

fn page_controls(
    rail: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
    visible: u64,
    total_groups: u64,
) {
    if view.offset > 0 {
        control(
            rail,
            view,
            scope,
            Action::Page(view.offset.saturating_sub(20)),
            "Previous counterparties".into(),
        );
    }
    if view.offset + visible < total_groups {
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

#[derive(Component)]
pub(super) struct SourceLabel;

type MoneyControl = (
    &'static Target,
    Ref<'static, Interaction>,
    &'static mut BorderColor,
    &'static mut BackgroundColor,
    &'static mut Node,
    &'static mut ObserverFocusTarget,
    Option<&'static mut AccessibilityNode>,
);

fn selection_label(view: &MoneyView, atlas: &CountyAtlas) -> String {
    let empty = || {
        if view
            .scope
            .as_ref()
            .is_some_and(|s| s.group != FlowGroup::Location)
        {
            "Select a connection to inspect its reported locations.".to_owned()
        } else {
            String::new()
        }
    };
    view.selected_row()
        .zip(view.scope.as_ref())
        .map_or_else(empty, |(row, scope)| {
            let group = scope.group;
            let peer =
                grouping::peer_label(scope, row.key.peer.as_deref(), row.label.as_deref(), atlas);
            let county = location(Some(&format!("county:{}", scope.county)), atlas);
            let (from, to) = match row.key.direction {
                Direction::PaidTo => (county, peer),
                Direction::ReceivedFrom => (peer, county),
                Direction::Internal if group != FlowGroup::Location => {
                    (format!("{peer} in {county}"), county)
                }
                Direction::Internal => (county.clone(), county),
            };
            let amount = reading(&row.quantity);
            let mut text = row.key.peer.as_deref().map_or_else(
                || format!("{from} → {to}\n{amount}"),
                |key| {
                    format!(
                        "{from} → {to}\n{amount}\n{} {key}",
                        if group == FlowGroup::Location {
                            "Location code"
                        } else {
                            "Group code"
                        }
                    )
                },
            );
            if let Some(page) = &view.page {
                if let Some(net) = compare::group_net(page, &row.key, scope.context.tick) {
                    text.push_str("\nCounty net with this counterparty\n");
                    text.push_str(&net);
                }
            }
            text
        })
}

fn control_availability(target: &Target, view: &MoneyView, obs: &Observation) -> Option<bool> {
    match target.action {
        Action::IndustrySources => Some(industry::selected(view).is_some()),
        Action::CompanyAccounts(true) => Some(company::selected(view).is_some()),
        Action::Geography(delta) => Some(view.geography.can_navigate(delta)),
        Action::Frame if view.diagram != Diagram::Map => Some(false),
        Action::Frame if target.scope.group != FlowGroup::Location => {
            Some(view.geography.rows().iter().any(|r| {
                r.quantity.micros() != "0"
                    && (r.key.direction == Direction::Internal
                        || r.key
                            .peer
                            .as_deref()
                            .and_then(|k| k.strip_prefix("county:"))
                            .is_some_and(|k| obs.atlas.index_of_fips(k).is_some()))
            }))
        }
        Action::Follow | Action::FollowLeg { .. } => {
            Some(target.destination_county(obs, view).is_some())
        }
        _ => None,
    }
}

fn control_selected(target: &Target, view: &MoneyView) -> bool {
    (target.action == Action::IndustrySources && view.industry.expanded)
        || matches!(&target.action,Action::Freight(command) if view.freight.chosen(command))
        || matches!(&target.action,Action::Select(row) if view.selected_row().is_some_and(|active| &active.key == row))
        || matches!(target.action,Action::Diagram(diagram) if diagram==view.diagram)
        || matches!(target.action,Action::Group(group) if group==target.scope.group)
        || matches!(target.action,Action::Measure(measure) if measure==target.scope.measure)
}

pub(super) fn highlight(
    view: Res<MoneyView>,
    obs: Observation,
    mut labels: Query<(&mut Text, Has<SourceLabel>), With<SelectionLabel>>,
    mut targets: Query<MoneyControl>,
) {
    for (mut text, source) in &mut labels {
        if !view.is_changed() && !text.is_added() {
            continue;
        }
        let value = if source {
            if view.industry.expanded && industry::selected(&view).is_some() {
                view.industry.describe()
            } else {
                String::new()
            }
        } else {
            selection_label(&view, &obs.atlas)
        };
        text.set_if_neq(Text::new(value));
    }
    for (target, interaction, mut border, mut background, mut node, mut focus, accessibility) in
        &mut targets
    {
        if !view.is_changed()
            && !interaction.is_changed()
            && !node.is_added()
            && !obs.ui.is_changed()
        {
            continue;
        }
        if let (Action::IndustrySources, Some(mut node)) = (&target.action, accessibility) {
            if node.is_expanded() != Some(view.industry.expanded) {
                node.set_expanded(view.industry.expanded);
            }
        }
        let conditional = control_availability(target, &view, &obs);
        if let Some(available) = conditional {
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
        if conditional.is_none() && focus.available != obs.interactive() {
            focus.available = obs.interactive();
        }
        let active = control_selected(target, &view);
        border.set_if_neq(BorderColor::all(if active {
            theme::YELLOW
        } else if let (Action::Select(key), FlowGroup::Industry) =
            (&target.action, target.scope.group)
        {
            grouping::industry_color(key.peer.as_deref())
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
