//! Labels come from the captured company and industry dimensions; counties use the atlas.
use super::rail;
use super::state::{Action, Measure, MoneyView, Scope};
use crate::atlas::CountyAtlas;
use crate::observer_theme as theme;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_persistence::money_journal::FlowGroup;
use bevy::prelude::*;

pub(super) fn group_names(group: FlowGroup) -> (&'static str, &'static str) {
    match group {
        FlowGroup::Account => ("account", "accounts"),
        FlowGroup::Location => ("location", "locations"),
        FlowGroup::Catchment => ("catchment", "catchments"),
        FlowGroup::Industry => ("industry", "industries"),
        FlowGroup::Company => ("company", "companies"),
        FlowGroup::Counterparty => ("counterparty", "counterparties"),
    }
}

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
    if group == FlowGroup::Industry {
        if let Some(function) = EconomicFunction::from_source_key(key) {
            return function.label().into();
        }
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
    if scope.measure == Measure::Money {
        rail::control(
            rail,
            view,
            scope,
            Action::Group(FlowGroup::Account),
            "By Account".into(),
        );
    }
}

pub(super) fn industry_color(key: Option<&str>) -> Color {
    match key.and_then(EconomicFunction::from_source_key) {
        Some(EconomicFunction::BusinessServices) => Color::srgb_u8(193, 168, 226),
        Some(EconomicFunction::CapitalGoods) => theme::COPPER,
        Some(EconomicFunction::ConstructionHousing) => Color::srgb_u8(208, 145, 117),
        Some(EconomicFunction::ConsumerGoods) => Color::srgb_u8(214, 112, 92),
        Some(EconomicFunction::DistributionTransport) => theme::BLUE,
        Some(EconomicFunction::EnergyUtilities) => theme::YELLOW,
        Some(EconomicFunction::Extraction) => Color::srgb_u8(178, 160, 134),
        Some(EconomicFunction::Food) => Color::srgb_u8(132, 194, 130),
        Some(EconomicFunction::HouseholdServices) => Color::srgb_u8(225, 154, 189),
        Some(EconomicFunction::LeisureHospitality) => Color::srgb_u8(236, 192, 98),
        Some(EconomicFunction::Manufacturing) => Color::srgb_u8(132, 159, 225),
        Some(EconomicFunction::PublicProvisioning) => Color::srgb_u8(118, 191, 172),
        None => theme::GRAY,
    }
}

#[cfg(test)]
mod tests {
    use super::industry_color;
    use crate::observer_theme as theme;
    use babylon_kernel::economic_identity::TradeSet;

    #[test]
    fn industry_colors_are_distinct_for_twelve_trades() {
        let colors: Vec<_> = TradeSet::Twelve
            .functions()
            .iter()
            .map(|function| industry_color(Some(function.source_key())))
            .collect();
        assert_eq!(colors.len(), 12);
        for (index, color) in colors.iter().enumerate() {
            assert_ne!(*color, theme::GRAY);
            assert!(colors[..index].iter().all(|other| other != color));
        }
    }
}
