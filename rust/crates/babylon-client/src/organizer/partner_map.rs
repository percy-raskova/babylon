//! County-level aid partners and hearing notices from the organizer's admitted view.
use super::workspace::DispatchDestination;
use super::{
    ActionButton, OrganizerAction, OrganizerInspector, OrganizerSceneMode, OrganizerSubject, Scope,
};
use super::{DatedLink, Destination};
use crate::decision_surface::SurfaceId;
use crate::observer_focus::ObserverFocusTarget;
use crate::observer_map3d::symbols::GeographicSymbol;
use crate::observer_map3d::CountyAnchors;
use crate::observer_theme as theme;
use crate::observer_ui::ObserverFontRole;
use crate::organizer::partner_copy::{self, FoodMeasure, FoodReading};
use crate::production::PrimaryView;
use crate::visual_assets::{MapSymbol, VisualAssets};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use babylon_persistence::runtime_session::{
    OrganizerAidKind, OrganizerChoice, OrganizerKnownAidPartner,
};
use bevy::a11y::AccessibilityNode;
use bevy::input_focus::tab_navigation::TabGroup;
use bevy::prelude::*;

pub(super) fn county(partner: &OrganizerKnownAidPartner) -> Option<CountyGeoid> {
    match partner.location {
        Some(EconomicLocation::County(county)) => Some(county.geoid()),
        _ => None,
    }
}

pub(super) fn choice(kind: OrganizerAidKind) -> OrganizerChoice {
    match kind {
        OrganizerAidKind::Local => OrganizerChoice::LocalAid,
        OrganizerAidKind::Remote => OrganizerChoice::RemoteAid,
    }
}

#[derive(PartialEq)]
pub(super) struct PartnerMarker {
    link: DatedLink,
    name: String,
    county_name: String,
    symbol: MapSymbol,
    anchor: Vec3,
    selected: bool,
    food: Option<FoodTag>,
}

#[derive(PartialEq, Eq)]
struct FoodTag {
    report_id: [u8; 32],
    caption: String,
    description: String,
    short: bool,
}

fn food_tag(reading: FoodReading<'_>) -> FoodTag {
    let period = reading.row.observed_period;
    let (topic, amount, short) = match reading.measure {
        FoodMeasure::Opening {
            opening_stock,
            required,
        } => {
            let short = opening_stock < required;
            let amount = if opening_stock <= 9_999 && required <= 9_999 {
                format!("{opening_stock}/{required} on hand")
            } else if short {
                "Below need".into()
            } else {
                "Stock covers need".into()
            };
            ("pantry", amount, short)
        }
        FoodMeasure::Completed { unmet, .. } => {
            let amount = if unmet <= 999_999 {
                format!("{unmet} unmet")
            } else {
                "Unmet need".into()
            };
            ("food", amount, unmet > 0)
        }
    };
    FoodTag {
        report_id: reading.row.observation_id,
        caption: format!("P{period} {topic} ›\n{amount}"),
        description: format!(
            "{} · {} · observed P{period}, received P{}",
            reading.commodity.label, reading.commodity.unit_label, reading.row.acquired_period
        ),
        short,
    }
}

fn spawn_tag(parent: &mut ChildSpawnerCommands, marker: &PartnerMarker, scope: &Scope) {
    let mut tag = parent.spawn(Node {
        width: px(113),
        height: percent(100),
        padding: UiRect::horizontal(px(4)),
        align_items: AlignItems::Center,
        overflow: Overflow::clip(),
        ..default()
    });
    let (caption, color) = if let Some(food) = &marker.food {
        let description = format!(
            "Read food report from {} · {}",
            marker.name, food.description
        );
        tag.insert((
            crate::ui::pressable(),
            ActionButton(OrganizerAction::Follow(DatedLink::new(
                &scope.session,
                scope.session.viewed_tick,
                Destination::Detail(DispatchDestination::Report(food.report_id)),
            ))),
            ObserverFocusTarget::action(Some(scope.session.context())),
            Name::new(description.clone()),
            BackgroundColor(theme::PANEL),
            BorderColor::all(theme::GRAY),
        ))
        .entry::<AccessibilityNode>()
        .and_modify(move |mut node| node.set_label(description));
        (
            food.caption.as_str(),
            if food.short {
                theme::YELLOW
            } else {
                theme::PAPER
            },
        )
    } else {
        tag.insert(Pickable::IGNORE);
        ("Food report\nunavailable", theme::GRAY)
    };
    tag.with_child((
        Text::new(format!("{}\n{caption}", marker.county_name)),
        TextFont {
            font_size: FontSize::Px(14.0),
            ..default()
        },
        ObserverFontRole::Body,
        TextColor(color),
        Pickable::IGNORE,
    ));
}

fn partner_marker(
    scope: &Scope,
    anchors: &CountyAnchors,
    partner: &OrganizerKnownAidPartner,
) -> Option<PartnerMarker> {
    let id = county(partner)?;
    let anchor = anchors.county_position(id.as_str())?;
    let county_name = scope
        .atlas
        .as_ref()
        .and_then(|atlas| atlas.county(atlas.index_of_fips(id.as_str())?))
        .map_or(id.as_str(), |county| {
            county
                .name
                .split(',')
                .next()
                .unwrap_or(county.name)
                .trim_end_matches(" County")
        });
    Some(PartnerMarker {
        link: DatedLink::new(
            &scope.session,
            scope.session.viewed_tick,
            Destination::Subject(OrganizerSubject::AidPartner(partner.actor_id)),
        ),
        name: partner.label.clone(),
        county_name: county_name.to_owned(),
        food: scope.client.view.as_ref().and_then(|view| {
            partner_copy::latest_food_report(
                view,
                scope.session.viewed_tick,
                partner.actor_id,
                |_| true,
            )
            .map(food_tag)
        }),
        symbol: match partner.kind {
            OrganizerAidKind::Local => MapSymbol::LocalAid,
            OrganizerAidKind::Remote => MapSymbol::RemoteAid,
        },
        anchor,
        selected: scope.client.selected_subject
            == Some(OrganizerSubject::AidPartner(partner.actor_id)),
    })
}

fn hearing_marker(scope: &Scope, anchors: &CountyAnchors) -> Option<PartnerMarker> {
    let (county, period, kind) =
        crate::organizer::hearing::map_entry(&scope.client, &scope.session)?;
    Some(PartnerMarker {
        link: DatedLink::new(
            &scope.session,
            scope.session.viewed_tick,
            Destination::Detail(DispatchDestination::Inspector(OrganizerInspector::Hearing)),
        ),
        name: format!("{kind} · P{period}"),
        county_name: String::new(),
        symbol: MapSymbol::Hearing,
        anchor: anchors.county_position(county)?,
        selected: false,
        food: None,
    })
}

pub(super) fn paint(
    mut commands: Commands,
    scope: Scope,
    anchors: Option<Res<CountyAnchors>>,
    assets: Option<Res<VisualAssets>>,
    mut previous: Local<Vec<PartnerMarker>>,
    mut group: Local<Option<Entity>>,
) {
    let (Some(anchors), Some(assets)) = (anchors, assets) else {
        return;
    };
    if !(scope.session.is_changed()
        || scope.view.is_changed()
        || scope.ui.is_changed()
        || scope.client.is_changed()
        || anchors.is_changed()
        || assets.is_changed())
    {
        return;
    }
    let mut markers = Vec::new();
    if *scope.view == PrimaryView::Organizer
        && scope.session.organizer_enabled
        && scope.client.inspector == OrganizerInspector::Closed
        && scope.client.scene_mode == OrganizerSceneMode::Places
    {
        markers.extend(hearing_marker(&scope, &anchors));
        markers.extend(
            scope
                .client
                .known_aid_partners(&scope.session)
                .iter()
                .filter_map(|partner| partner_marker(&scope, &anchors, partner)),
        );
    }
    if *previous == markers {
        return;
    }
    if let Some(entity) = group.take() {
        commands.entity(entity).despawn();
    }
    *previous = markers;
    if previous.is_empty() {
        return;
    }
    let parent = commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                width: percent(100),
                height: percent(100),
                ..default()
            },
            Pickable::IGNORE,
            TabGroup::new(10),
            ZIndex(4),
        ))
        .id();
    *group = Some(parent);
    for marker in &previous {
        let entity = GeographicSymbol {
            anchor: marker.anchor,
            priority: u8::from(!marker.selected && marker.symbol != MapSymbol::Hearing),
            symbol: marker.symbol,
            label: format!("{} · county location", marker.name),
            view: PrimaryView::Organizer,
            surface: SurfaceId::OrganizerWorkspace,
        }
        .spawn(&mut commands, &assets, marker.selected)
        .insert((
            ChildOf(parent),
            ActionButton(OrganizerAction::Follow(marker.link)),
            ObserverFocusTarget::action(Some(scope.session.context())),
        ))
        .id();
        if marker.symbol == MapSymbol::Hearing {
            commands
                .entity(entity)
                .entry::<Node>()
                .and_modify(|mut node| {
                    node.width = px(142);
                    node.height = px(46);
                });
            commands.entity(entity).with_children(|parent| {
                parent
                    .spawn(super::text(&marker.name, 14.0, theme::PAPER))
                    .insert((
                        Node {
                            width: px(92),
                            ..default()
                        },
                        Pickable::IGNORE,
                    ));
            });
            continue;
        }
        commands
            .entity(entity)
            .entry::<Node>()
            .and_modify(|mut node| {
                node.width = px(164);
                node.height = px(62);
            });
        commands
            .entity(entity)
            .with_children(|parent| spawn_tag(parent, marker, &scope));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_persistence::runtime_session::{
        OrganizerPartnerFacts, OrganizerReport, OrganizerSnapshot, OrganizerView,
    };

    #[test]
    fn map_food_tag_keeps_the_exact_earned_report_when_an_offer_is_unavailable() {
        let mut end: OrganizerSnapshot = serde_json::from_str(include_str!(
            "../../../babylon-persistence/tests/fixtures/national_organizer_pending_v20.json"
        ))
        .expect("captured national partner observations");
        let partner = end.view.aid_partners[1].actor_id;
        end.view.aid_options.clear();
        let latest = |view: &OrganizerView, period| {
            partner_copy::latest_food_report(view, period, partner, |_| true).map(food_tag)
        };
        let opening = latest(&end.view, 0).expect("opening food assessment");
        assert_eq!(opening.caption, "P0 pantry ›\n0/4 on hand");
        assert!(opening.short);
        let current = latest(&end.view, 1).expect("completed food report");
        assert_eq!(current.caption, "P1 food ›\n4 unmet");
        assert!(current.short);
        assert_ne!(opening.report_id, current.report_id);
        let item = end
            .view
            .observations
            .iter_mut()
            .find(|r| r.observation_id == current.report_id)
            .expect("click must reference exact disclosed observation");
        assert_eq!(item.subject_id, partner);
        item.acquired_period = 2;
        let OrganizerReport::Partner {
            facts:
                OrganizerPartnerFacts::FoodProvision {
                    unmet,
                    required,
                    consumed,
                    ..
                },
            ..
        } = &mut item.report
        else {
            panic!("expected partner food provision")
        };
        *unmet = 0;
        *consumed = *required;
        assert_eq!(
            latest(&end.view, 1).expect("last earned reading").report_id,
            opening.report_id
        );
        let met = latest(&end.view, 2).expect("later acquired report");
        assert_eq!(met.caption, "P1 food ›\n0 unmet");
        assert!(!met.short);
        assert!(met.description.contains("observed P1, received P2"));
        assert!(partner_copy::latest_food_report(&end.view, 2, partner, |_| false).is_none());
        end.view.observations.retain(|r| r.subject_id != partner);
        assert!(latest(&end.view, 2).is_none());
    }
}
