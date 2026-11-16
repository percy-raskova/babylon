//! Committed food use for resident cohorts represented on the national economic map.
use super::{
    Active, EconomyEntity, Group, LegendFocus, NetworkProjection, RelationshipObservation,
    Selection,
};
use crate::cli;
use crate::decision_surface::SurfaceId;
use crate::human_numbers;
use crate::observer_focus::ObserverFocusTarget;
use crate::observer_map3d::symbols::GeographicSymbol;
use crate::observer_theme as theme;
use crate::production::{PrimaryView, ProductionCommand};
use crate::visual_assets::{MapSymbol, VisualAssets};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_material_circuit::FinalDemandPrincipalId;
use babylon_persistence::national_economy;
use babylon_persistence::production_observation::ProductionSnapshot;
use babylon_persistence::{ProductionHouseholdAccount, ProductionHouseholdKind};
use bevy::a11y::AccessibilityNode;
use bevy::input_focus::tab_navigation::TabGroup;
use bevy::prelude::*;
use std::collections::BTreeMap;

#[derive(Default)]
struct Balance<'a> {
    unit: &'a str,
    unit_id: Option<&'a str>,
    cohorts: usize,
    required: u128,
    consumed: u128,
    unmet: u128,
    opening: u128,
    purchases: u128,
    gifts_in: u128,
    gifts_out: u128,
    closing: u128,
    example: Option<(&'a ProductionHouseholdAccount, u64)>,
}

enum Food<'a> {
    Opening,
    Unavailable,
    Closed(Balance<'a>),
}

impl<'a> Food<'a> {
    fn record(&mut self, row: &'a ProductionHouseholdAccount, period: u64) {
        let Self::Closed(result) = self else {
            return;
        };
        let Some(done) = row.completed.as_ref().filter(|done| done.period == period) else {
            *self = Self::Unavailable;
            return;
        };
        if result.unit_id.is_some_and(|id| id != row.unit_id)
            || done.consumed.checked_add(done.unmet) != Some(done.required)
        {
            *self = Self::Unavailable;
            return;
        }
        result.unit_id = Some(&row.unit_id);
        result.unit = &row.unit;
        result.cohorts += 1;
        result.required += u128::from(done.required);
        result.consumed += u128::from(done.consumed);
        result.unmet += u128::from(done.unmet);
        result.opening += u128::from(done.opening_stock);
        result.purchases += u128::from(done.received);
        result.gifts_in += u128::from(done.support_granted);
        result.gifts_out += u128::from(done.support_dispatched);
        result.closing += u128::from(done.closing_stock);
        if done.unmet > 0
            && result.example.is_none_or(|(old, amount)| {
                done.unmet > amount
                    || (done.unmet == amount && row.demand_principal_id < old.demand_principal_id)
            })
        {
            result.example = Some((row, done.unmet));
        }
    }

    fn short(&self) -> bool {
        matches!(self, Self::Closed(balance) if balance.unmet > 0)
    }
    fn caption(&self, period: u64) -> String {
        match self {
            Self::Opening => "Opening · food consumption begins in P1".into(),
            Self::Unavailable => format!("P{period} · no household food reading here"),
            Self::Closed(balance) if balance.unmet > 0 => format!(
                "P{period} food shortage · {} of {} unmet · {}",
                human_numbers::grouped(balance.unmet),
                human_numbers::grouped(balance.required),
                balance.unit
            ),
            Self::Closed(_) => format!("P{period} · no unmet food need recorded"),
        }
    }

    fn details(&self) -> Option<String> {
        let Self::Closed(balance) = self else {
            return None;
        };
        Some(format!(
            "{} resident cohorts · {}\n{} required · {} consumed · {} unmet\nPantry · {} opening · {} purchased · {} closing\nMaterial support · {} received · {} sent\nRegional cohorts include residents of other counties, shown at their hub.",
            human_numbers::grouped(balance.cohorts as u128), balance.unit,
            human_numbers::grouped(balance.required), human_numbers::grouped(balance.consumed),
            human_numbers::grouped(balance.unmet), human_numbers::grouped(balance.opening),
            human_numbers::grouped(balance.purchases), human_numbers::grouped(balance.closing),
            human_numbers::grouped(balance.gifts_in), human_numbers::grouped(balance.gifts_out),
        ))
    }

    fn example(&self) -> Option<(&'a ProductionHouseholdAccount, u64)> {
        match self {
            Self::Closed(balance) => balance.example,
            _ => None,
        }
    }
}

pub(super) struct FoodPanel<'a> {
    county_name: &'a str,
    snapshot: &'a ProductionSnapshot,
    food: Food<'a>,
    title: String,
    target: Selection,
    open: bool,
}

impl<'a> FoodPanel<'a> {
    /// Scan the authenticated household balances once. Network sites and buyers can share a residence.
    pub(super) fn represented(
        obs: &'a RelationshipObservation<'_>,
        network: &NetworkProjection,
        active: &Active,
    ) -> BTreeMap<&'a str, Self> {
        let mut panels = BTreeMap::new();
        let Some(snapshot) = super::super::super::disclosed_snapshot(&obs.frame, &obs.session)
        else {
            return panels;
        };
        let Some(selected) = obs.selected_place() else {
            return panels;
        };
        if snapshot.scenario_label != "national-world" || obs.session.organizer_enabled {
            return panels;
        }
        let period = obs.session.viewed_tick;
        for (county, county_name) in
            std::iter::once(selected).chain(network.nodes.values().filter_map(|node| {
                obs.anchors
                    .0
                    .get_key_value(&node.county)
                    .map(|(county, anchor)| (county.as_str(), anchor.name.as_str()))
            }))
        {
            panels.entry(county).or_insert_with(|| {
                let target = Selection {
                    context: obs.session.context(),
                    scope: obs.selected.0,
                    group: Group {
                        county: county.to_owned(),
                        kind: MapSymbol::FoodShortage,
                    },
                };
                Self {
                    county_name,
                    snapshot,
                    food: if period == 0 {
                        Food::Opening
                    } else {
                        Food::Closed(Balance::default())
                    },
                    title: String::new(),
                    open: active.0.as_ref() == Some(&target),
                    target,
                }
            });
        }
        if period > 0 {
            let food_id = national_economy::commodity_good_id("food").as_bytes();
            for row in &snapshot.household_accounts {
                let EconomicLocation::County(residence) = row.location else {
                    continue;
                };
                if let Some(panel) = panels.get_mut(residence.geoid().as_str()) {
                    if cli::identity_bytes(&row.good_id) == Some(food_id) {
                        panel.food.record(row, period);
                    }
                }
            }
        }
        for panel in panels.values_mut() {
            if matches!(&panel.food, Food::Closed(balance) if balance.cohorts == 0) {
                panel.food = Food::Unavailable;
            }
            panel.title = panel.food.caption(period);
        }
        panels
    }

    pub(super) fn spawn_marker(
        &self,
        commands: &mut Commands,
        obs: &RelationshipObservation,
        visual: &VisualAssets,
    ) {
        if !self.food.short() {
            return;
        }
        let Some(anchor) = obs.anchors.county_position(&self.target.group.county) else {
            return;
        };
        let mut focus = ObserverFocusTarget::action(Some(self.target.context.clone()));
        focus.available = true;
        let marker = GeographicSymbol {
            anchor,
            symbol: MapSymbol::FoodShortage,
            view: PrimaryView::Map,
            surface: SurfaceId::ObserverProduction,
            label: format!("{} · {}", self.county_name, self.title),
            priority: u8::from(
                obs.selected_place()
                    .is_none_or(|(county, _)| county != self.target.group.county),
            ),
        }
        .spawn(commands, visual, self.open)
        .insert((self.target.clone(), focus))
        .observe(super::pointer)
        .observe(super::keyboard)
        .id();
        // A tabbable screen-space marker needs its own root at the viewport origin.
        commands
            .spawn((
                Node {
                    position_type: PositionType::Absolute,
                    ..default()
                },
                TabGroup::new(23),
                Pickable::IGNORE,
                EconomyEntity,
            ))
            .add_child(marker);
    }

    pub(super) fn spawn_reading(
        &self,
        panel: &mut ChildSpawnerCommands,
        visual: &VisualAssets,
        keyboard: &mut LegendFocus,
    ) {
        if !matches!(self.food, Food::Closed(_)) {
            panel.spawn(super::caption(&self.title, theme::GRAY));
            return;
        }
        let button = food_button(
            panel,
            self.target.clone(),
            &self.title,
            self.county_name,
            visual,
            &self.food,
        );
        keyboard.restore(&self.target, self.open, button);
        if !self.open {
            return;
        }
        if let Some(detail) = self.food.details() {
            panel.spawn(super::caption(
                format!("{} · household food\n{detail}", self.county_name),
                theme::PAPER,
            ));
        }
        if let Some((account, unmet)) = self.food.example() {
            let id = account
                .demand_principal_id
                .get(..8)
                .unwrap_or(&account.demand_principal_id);
            let households = match account.kind {
                ProductionHouseholdKind::Ordinary => format!(
                    "{} households",
                    human_numbers::grouped(u128::from(account.household_count))
                ),
                ProductionHouseholdKind::CollectiveResidence => "Collective residence".into(),
            };
            panel.spawn(super::caption(format!("Largest food gap · {households} · {} residents at close · cohort {id}\n{} unmet",
                human_numbers::grouped(u128::from(account.person_count)), human_numbers::grouped(u128::from(unmet))), theme::YELLOW));
            if let Some(done) = &account.completed {
                panel.spawn(super::caption(
                    format!(
                        "Food order · {} requested · {} within budget · {} bought · {} expired",
                        human_numbers::grouped(u128::from(done.requested)),
                        human_numbers::grouped(u128::from(done.admitted)),
                        human_numbers::grouped(u128::from(done.fulfilled)),
                        human_numbers::grouped(u128::from(done.expired))
                    ),
                    theme::PAPER,
                ));
            }
            if let Some(site) = self
                .snapshot
                .sites
                .iter()
                .find(|site| site.id == account.retailer_site_id)
            {
                if let Some(principal) = cli::identity_bytes(&account.demand_principal_id) {
                    crate::production::button(
                        panel,
                        "Open household receipt",
                        ProductionCommand::ResidentReceipt {
                            county: self.target.group.county.clone(),
                            site_id: site.id.clone(),
                            principal: FinalDemandPrincipalId::from_bytes(principal),
                            context: self.target.context.clone(),
                        },
                    );
                }
                crate::production::button(
                    panel,
                    &format!("Trace food retailer · {}", site.name),
                    ProductionCommand::Select {
                        site_id: site.id.clone(),
                        context: self.target.context.clone(),
                    },
                );
            }
        }
    }
}
fn food_button(
    panel: &mut ChildSpawnerCommands,
    target: Selection,
    caption_text: &str,
    county_name: &str,
    visual: &VisualAssets,
    food: &Food<'_>,
) -> Entity {
    let mut focus = ObserverFocusTarget::action(Some(target.context.clone()));
    focus.available = true;
    let description = format!("{county_name} · {caption_text}");
    let mut button = panel.spawn((
        crate::ui::pressable(),
        Name::new(description.clone()),
        focus,
        target,
        Node {
            align_items: AlignItems::Center,
            column_gap: px(6),
            flex_shrink: 0.0,
            ..default()
        },
        BackgroundColor(theme::PANEL),
    ));
    button
        .entry::<AccessibilityNode>()
        .and_modify(move |mut node| node.set_label(description));
    button
        .observe(super::pointer)
        .observe(super::keyboard)
        .with_children(|row| {
            if food.short() {
                row.spawn((
                    MapSymbol::FoodShortage.image(visual),
                    Node {
                        width: px(25),
                        height: px(25),
                        flex_shrink: 0.0,
                        ..default()
                    },
                    Pickable::IGNORE,
                ));
            }
            row.spawn(super::caption(caption_text, theme::PAPER));
        });
    button.id()
}
