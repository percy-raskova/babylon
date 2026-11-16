//! Scrollable, keyboard-operable freight access and exact route detail.
use super::freight::{Command, Freight, Point, PAGE};
use super::rail;
use super::state::{Action, Diagram, MoneyView, Scope};
use crate::atlas::CountyAtlas;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use babylon_persistence::freight_access::{self, Access, AccessDirection, AccessError, AccessRow};
use bevy::prelude::*;

pub(super) fn km(mm: u64) -> String {
    let fraction = format!("{:06}", mm % 1_000_000);
    let decimal = fraction.trim_end_matches('0');
    if decimal.is_empty() {
        format!("{} km", mm / 1_000_000)
    } else {
        format!("{}.{decimal} km", mm / 1_000_000)
    }
}

pub(super) fn reading(row: &AccessRow) -> String {
    let status = match row.access {
        Access::Reachable { distance_mm } => format!(
            "Shortest permitted truck path {} · {}",
            km(distance_mm),
            freight_access::distance_band(distance_mm)
        ),
        Access::NoPermittedPath => "No permitted directed truck path".into(),
        Access::Unqualified => "Regional path unverified".into(),
        Access::OutsideCoverage => "Outside Michigan terminal coverage".into(),
    };
    if row.corridors.is_empty() {
        status
    } else {
        format!("{status} · {} captured corridors", row.corridors.len())
    }
}
pub(super) fn peer_name(row: &AccessRow, atlas: &CountyAtlas) -> String {
    rail::location(Some(&row.peer.to_string()), atlas)
}

pub(super) fn origin_name(freight: &Freight, atlas: &CountyAtlas) -> String {
    freight.origin.map_or_else(String::new, |county| {
        rail::location(Some(&format!("county:{county}")), atlas)
    })
}

#[derive(Component)]
pub(super) struct Detail;

pub(super) fn detail(
    view: Res<MoneyView>,
    atlas: Res<CountyAtlas>,
    mut labels: Query<&mut Text, With<Detail>>,
) {
    for mut label in &mut labels {
        if !view.is_changed() && !label.is_added() {
            continue;
        }
        if let Some(point) = &view.freight.point {
            label.0 = match point {
                Point::Origin => format!("Comparison origin · {}\nThe compass marks the county anchor. Select an endpoint for its terminal attachment.", origin_name(&view.freight, &atlas)),
                Point::Airport(id) => view.freight.airports.iter().find(|p| &p.id==id).map_or_else(String::new, |p| format!("{} · {}\nFAA facility point {}, {} · effective {}. Road attachment and dated air service unverified.",p.name,p.id,p.latitude,p.longitude,p.effective_date)),
            };
            continue;
        }
        let Some(row) = view
            .freight
            .all_rows()
            .iter()
            .find(|r| Some(r.peer) == view.freight.selected)
        else {
            label.0.clear();
            continue;
        };
        let endpoint = |name: String, distance_mm: Option<u64>| match distance_mm {
            Some(mm) => format!("{name} · Designed anchor to assigned road node {}", km(mm)),
            None => name,
        };
        let origin = endpoint(origin_name(&view.freight, &atlas), row.origin_attachment_mm);
        let peer = endpoint(peer_name(row, &atlas), row.peer_attachment_mm);
        let (from, to) = match view.freight.direction {
            AccessDirection::Outbound => (origin, peer),
            AccessDirection::Inbound => (peer, origin),
        };
        let ids: Vec<_> = row
            .corridors
            .iter()
            .map(|c| match c.distance_mm {
                Some(mm) => format!("{} · captured route length {}", c.route_id, km(mm)),
                None => format!("{} · physical distance unreported", c.route_id),
            })
            .collect();
        label.0 = format!("From {from}\nTo {to}\n{}\n{}", reading(row), ids.join("\n"));
    }
}

fn notice(parent: &mut ChildSpawnerCommands, text: impl Into<String>) {
    parent.spawn(rail::label(text, 14.0, theme::GRAY, ObserverFontRole::Body));
}
fn controls(
    parent: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
    action: Command,
    label: impl Into<String>,
) {
    rail::control(parent, view, scope, Action::Freight(action), label.into());
}

fn show_reference_status(
    parent: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
) -> bool {
    let freight = &view.freight;
    if !freight.source.is_empty() {
        notice(parent, freight.source.clone());
    }
    notice(
        parent,
        "Compass: comparison origin · crane: county freight endpoint · aircraft: FAA point. Solid gold arrows show captured economic corridors. Dashed blue arrows show independent truck access. Small diamonds mark other endpoints. Arrows join county anchors schematically.",
    );
    if !freight.source.is_empty() {
        if freight.airports.is_empty() {
            notice(
                parent,
                "The selected FAA facility reference has no airport point for this origin.",
            );
        }
        if let Some(origin) = freight.origin {
            for point in &freight.airports {
                controls(
                    parent,
                    view,
                    scope,
                    Command::Point(origin, Point::Airport(point.id.clone())),
                    format!("Airport · {}", point.name),
                );
            }
        }
    }
    match &freight.rows {
        None => {
            notice(parent, "Reading the regional reference…");
            return false;
        }
        Some(Err(error)) => {
            let message = match error {
                AccessError::Read => "The configured road matrix could not be read.",
                AccessError::Digest => {
                    "The configured matrix or regional source differs from the pinned digest."
                }
                AccessError::Source => "The routing source differs from the regional reference.",
                _ => "The freight source could not be qualified.",
            };
            notice(parent, format!("{message} ({error:?})"));
            return false;
        }
        Some(Ok(rows)) => {
            let corridors = rows.iter().map(|r| r.corridors.len()).sum::<usize>();
            let reachable = rows
                .iter()
                .filter(|r| matches!(r.access, Access::Reachable { .. }))
                .count();
            let unreachable = rows
                .iter()
                .filter(|r| r.access == Access::NoPermittedPath)
                .count();
            let unverified = rows
                .iter()
                .filter(|r| r.access == Access::Unqualified)
                .count();
            notice(
                parent,
                format!(
                    "{} endpoints · {corridors} captured corridors\n\
                     {reachable} reachable · {unreachable} without a directed path · \
                     {unverified} unverified",
                    rows.len(),
                ),
            );
        }
    }
    true
}

pub(super) fn panel(
    parent: &mut ChildSpawnerCommands,
    view: &MoneyView,
    scope: &Scope,
    atlas: &CountyAtlas,
) {
    let freight = &view.freight;
    let name = origin_name(freight, atlas);
    parent.spawn(rail::label(
        format!("Freight access · {name}"),
        22.0,
        theme::PAPER,
        ObserverFontRole::Display,
    ));
    controls(
        parent,
        view,
        scope,
        Command::Leave,
        "Return to economic flows",
    );
    for (diagram, label) in [
        (Diagram::Map, "Geographic map"),
        (Diagram::Sankey, "Terminal network"),
    ] {
        rail::control(parent, view, scope, Action::Diagram(diagram), label.into());
    }
    for (direction, label) in [
        (AccessDirection::Outbound, "Outbound from origin"),
        (AccessDirection::Inbound, "Inbound to origin"),
    ] {
        controls(parent, view, scope, Command::Direction(direction), label);
    }
    for (county, label) in [
        (scope.county.as_str(), "Use map-selected county as origin"),
        ("26163", "Use Wayne as origin"),
    ] {
        if let Ok(id) = county.parse() {
            if freight.origin != Some(id) {
                controls(parent, view, scope, Command::Origin(id), label);
            }
        }
    }
    if let Some(origin) = freight.origin {
        controls(
            parent,
            view,
            scope,
            Command::Point(origin, Point::Origin),
            format!("Inspect origin · {name}"),
        );
    }
    rail::control(
        parent,
        view,
        scope,
        Action::Frame,
        "Frame freight endpoints".into(),
    );
    if !show_reference_status(parent, view, scope) {
        return;
    }
    parent.spawn((
        rail::label("", 14.0, theme::YELLOW, ObserverFontRole::Body),
        TextLayout::linebreak(LineBreak::WordOrCharacter),
        Node {
            width: percent(100),
            min_width: px(0),
            ..default()
        },
        Detail,
    ));
    for row in freight.visible() {
        controls(
            parent,
            view,
            scope,
            freight.selection(row.peer),
            format!("{}\n{}", peer_name(row, atlas), reading(row)),
        );
    }
    if freight.offset > 0 {
        controls(
            parent,
            view,
            scope,
            Command::Page(freight.offset - PAGE),
            "Previous endpoints",
        );
    }
    if freight.offset + PAGE < freight.all_rows().len() {
        controls(
            parent,
            view,
            scope,
            Command::Page(freight.offset + PAGE),
            "More endpoints",
        );
    }
}
