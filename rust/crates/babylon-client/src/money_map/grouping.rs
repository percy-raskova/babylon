//! Labels come from the captured company and industry dimensions; counties use the atlas.
use super::rail;
use super::state::{Action, Measure, MoneyView, Scope};
use crate::atlas::CountyAtlas;
use crate::observer_theme as theme;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_persistence::money_journal::FlowGroup;
use bevy::prelude::*;

pub(super) fn peer_label(
    scope: &Scope,
    key: Option<&str>,
    label: Option<&str>,
    atlas: &CountyAtlas,
) -> String {
    let group = scope.group;
    if scope.measure == Measure::Labor && group == FlowGroup::Location && key.is_none() {
        return "Unlocated ledger endpoint".into();
    }
    if group == FlowGroup::Location || key.is_some_and(|k| k.starts_with("county:")) {
        return rail::location(key, atlas);
    }
    let Some(key) = key else {
        return match group {
            FlowGroup::Industry => "Industry unreported",
            FlowGroup::Company => "No represented company",
            _ => "Counterparty unreported",
        }
        .into();
    };
    if let Some(name) = label.filter(|&name| name != key) {
        return name.into();
    }
    if let Some((kind, id)) = key.split_once(':') {
        let kind = match kind {
            "household_cash" => "Household",
            "site_cash" => "Operating site",
            "public_cash" => "Public account",
            "organization_cash" => "Organization",
            "company" => "Company",
            other => other,
        };
        let short: String = id.chars().take(8).collect();
        return format!("{kind} · {short}");
    }
    key.into()
}

pub(super) fn controls(rail: &mut ChildSpawnerCommands, view: &MoneyView, scope: &Scope) {
    for pair in [
        [
            (FlowGroup::Location, "Location"),
            (FlowGroup::Industry, "Industry"),
        ],
        [
            (FlowGroup::Company, "Company"),
            (FlowGroup::Counterparty, "Counterparty"),
        ],
    ] {
        rail.spawn(Node {
            width: percent(100),
            flex_direction: FlexDirection::Row,
            ..default()
        })
        .with_children(|row| {
            for (group, label) in pair {
                rail::control(
                    row,
                    view,
                    scope,
                    Action::Group(group),
                    format!("By {label}"),
                );
            }
        });
    }
}

pub(super) fn industry_color(key: Option<&str>) -> Color {
    match key.and_then(EconomicFunction::from_source_key) {
        Some(EconomicFunction::BusinessServices) => Color::srgb_u8(193, 168, 226),
        Some(EconomicFunction::CapitalGoods) => theme::COPPER,
        Some(EconomicFunction::ConstructionHousing) => Color::srgb_u8(208, 145, 117),
        Some(EconomicFunction::DistributionTransport) => theme::BLUE,
        Some(EconomicFunction::EnergyUtilities) => theme::YELLOW,
        Some(EconomicFunction::Extraction) => Color::srgb_u8(178, 160, 134),
        Some(EconomicFunction::Food) => Color::srgb_u8(132, 194, 130),
        Some(EconomicFunction::HouseholdServices) => Color::srgb_u8(225, 154, 189),
        Some(EconomicFunction::Manufacturing) => Color::srgb_u8(132, 159, 225),
        Some(EconomicFunction::PublicProvisioning) => Color::srgb_u8(118, 191, 172),
        None => theme::GRAY,
    }
}
