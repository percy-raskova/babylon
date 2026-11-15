use super::state::{self, Direction, Quantity};
use babylon_persistence::money_journal::{FlowAmounts, FlowDirection, FlowGroup, FlowRow};

pub(super) fn counterparty(
    key: Option<&str>,
    incoming: &str,
    outgoing: &str,
    internal: &str,
) -> FlowRow {
    FlowRow {
        key: key.map(str::to_owned),
        label: None,
        rank: Some(1),
        groups: 1,
        current: FlowAmounts {
            inflow_micros: incoming.into(),
            outflow_micros: outgoing.into(),
            internal_micros: internal.into(),
            net_micros: "0".into(),
        },
        comparison: None,
        net_change_micros: None,
    }
}

#[test]
fn focused_counterparty_receipts_preserve_both_directions_internal_and_missing_geography() {
    let outside = counterparty(Some("county:26099"), "12000001", "8000002", "0");
    let inside = counterparty(Some("county:26163"), "0", "0", "17");
    let missing = counterparty(None, "0", "3", "0");
    let zero = counterparty(Some("county:26001"), "0", "0", "0");
    let rows = state::connections(&[outside, inside, missing, zero]);
    let observed: Vec<_> = rows
        .iter()
        .map(|row| {
            (
                row.key.peer.as_deref(),
                row.key.direction,
                row.quantity.micros(),
            )
        })
        .collect();
    assert_eq!(
        observed,
        [
            (Some("county:26099"), Direction::PaidTo, "12000001"),
            (Some("county:26099"), Direction::ReceivedFrom, "8000002"),
            (Some("county:26163"), Direction::Internal, "17"),
            (None, Direction::ReceivedFrom, "3"),
        ]
    );
}

#[test]
fn payment_locations_name_foreign_and_dependency_markets() {
    use super::rail;
    let (app, _, _, _) = interaction_fixture();
    let atlas = app.world().resource::<CountyAtlas>();
    assert_eq!(
        rail::location(Some("foreign:sub_saharan_africa"), atlas),
        "Sub-Saharan Africa"
    );
    assert_eq!(rail::location(Some("foreign:canada"), atlas), "Canada");
    assert_eq!(rail::location(Some("dependency:630"), atlas), "Puerto Rico");
    assert_eq!(rail::location(None, atlas), "Location unreported");
}

use super::state::{Action, Connection, ConnectionKey, MoneyView, Page, Scope, Status, Target};
use crate::atlas::CountyAtlas;
use crate::map::{CountyMapScope, SelectedCounty};
use crate::map_economy_lens::MapLens;
use crate::observer::{ObserverSession, Perspective};
use crate::observer_focus::ObserverKeyboardActivate;
use crate::observer_io::tests as observer_io_tests;
use crate::observer_ui::{ObserverFrame, ObserverUiState};
use crate::production::PrimaryView;
use babylon_persistence::identity::CampaignId;
use bevy::a11y::AccessibilityNode;
use bevy::picking::backend::HitData;
use bevy::picking::pointer::{Location, PointerButton, PointerId};
use bevy::prelude::*;
use std::time::Duration;
use uuid::Uuid;

pub(super) fn interaction_fixture() -> (App, Entity, Scope, Connection) {
    let mut app = App::new();
    let atlas = CountyAtlas::parse(include_bytes!(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../../../assets/map/county_atlas.bin"
    )))
    .expect("installed atlas");
    let county = atlas.index_of_fips("26163").expect("Wayne");
    let mut session = ObserverSession::new(CampaignId::from_uuid(Uuid::from_u128(71)));
    session.viewed_tick = 1;
    session.durable_tick = 1;
    session.foundation_digest = Some("foundation".into());
    session.content_hash = Some("committed tick".into());
    let scope = Scope {
        group: FlowGroup::Location,
        periods: super::compare::Periods::Current,
        measure: state::Measure::Money,
        context: session.context(),
        county: "26163".into(),
        foundation: "foundation".into(),
        tick_hash: session.content_hash.clone(),
    };
    let frame = observer_io_tests::snapshot_with_event(&session, "delivery", 1);
    let rows = state::connections(&[counterparty(Some("county:26099"), "111", "4", "0")]);
    let chosen = rows[0].clone();
    app.insert_resource(atlas)
        .insert_resource(session)
        .insert_resource(ObserverFrame(Some(frame), None))
        .insert_resource(SelectedCounty(Some(county)))
        .init_resource::<CountyMapScope>()
        .init_resource::<PrimaryView>()
        .insert_resource(ObserverUiState {
            lens: MapLens::Money,
            menu_open: false,
            splash_visible: false,
            ..default()
        })
        .insert_resource(MoneyView {
            scope: Some(scope.clone()),
            rows,
            status: Status::Ready,
            ..default()
        });
    let entity = app
        .world_mut()
        .spawn(Target {
            scope: scope.clone(),
            offset: 0,
            action: Action::Select(chosen.key.clone()),
        })
        .observe(state::pointer)
        .observe(state::keyboard)
        .id();
    (app, entity, scope, chosen)
}

#[test]
fn pointer_and_keyboard_select_the_same_receipt_connection_and_refuse_stale_authority() {
    let (mut app, entity, scope, chosen) = interaction_fixture();
    let click = || PointerClick {
        entity,
        pointer: Pointer::new(
            PointerId::Mouse,
            Location {
                target: bevy::camera::NormalizedRenderTarget::None {
                    width: 0,
                    height: 0,
                },
                position: Vec2::ZERO,
            },
        ),
        button: PointerButton::Primary,
        hit: HitData::new(Entity::PLACEHOLDER, 1.0, Some(Vec3::ZERO), Some(Vec3::Y)),
        duration: Duration::ZERO,
        count: 1,
    };
    let press = || ObserverKeyboardActivate {
        entity,
        context: Some(scope.context.clone()),
    };
    app.world_mut().trigger(click());
    assert_eq!(
        app.world().resource::<MoneyView>().selected_row().cloned(),
        Some(chosen.clone())
    );
    app.world_mut().resource_mut::<MoneyView>().selected = None;
    app.world_mut().trigger(press());
    assert_eq!(
        app.world().resource::<MoneyView>().selected_row().cloned(),
        Some(chosen)
    );
    {
        let mut view = app.world_mut().resource_mut::<MoneyView>();
        view.rows[0].quantity = Quantity::Money("237".into());
        assert_eq!(
            view.selected_row().map(|row| row.quantity.micros()),
            Some("237")
        );
        view.selected = None;
    }
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .perspective = Perspective::PlayerKnowledge;
    app.world_mut().trigger(click());
    app.world_mut().trigger(press());
    assert!(app.world().resource::<MoneyView>().selected.is_none());
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .perspective = Perspective::FullObserver;
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .foundation_digest = Some("other".into());
    app.world_mut().trigger(press());
    assert!(app.world().resource::<MoneyView>().selected.is_none());
}

#[test]
fn a_pressed_rail_row_selects_once_and_receives_keyboard_focus() {
    use crate::ui::Interaction;
    use bevy::input_focus::InputFocus;

    let (mut app, entity, _, chosen) = interaction_fixture();
    app.init_resource::<InputFocus>()
        .add_systems(Update, state::press_rail);
    app.world_mut()
        .entity_mut(entity)
        .insert(Interaction::Hovered);
    app.update();
    assert!(app.world().resource::<MoneyView>().selected.is_none());

    app.world_mut()
        .entity_mut(entity)
        .insert(Interaction::Pressed);
    app.update();
    assert_eq!(
        app.world().resource::<MoneyView>().selected_row(),
        Some(&chosen)
    );
    assert_eq!(app.world().resource::<InputFocus>().get(), Some(entity));

    app.world_mut().resource_mut::<MoneyView>().selected = None;
    app.update();
    assert!(app.world().resource::<MoneyView>().selected.is_none());
    app.world_mut()
        .entity_mut(entity)
        .insert(Interaction::Hovered);
    app.update();
    assert!(app.world().resource::<MoneyView>().selected.is_none());

    app.world_mut()
        .resource_mut::<ObserverSession>()
        .perspective = Perspective::PlayerKnowledge;
    app.world_mut().resource_mut::<InputFocus>().clear();
    app.world_mut()
        .entity_mut(entity)
        .insert(Interaction::Pressed);
    app.update();
    assert!(app.world().resource::<MoneyView>().selected.is_none());
    assert_eq!(app.world().resource::<InputFocus>().get(), None);
}

#[test]
fn money_switch_preserves_the_ranked_page_and_routes_payers_to_distinct_recipient_nodes() {
    use super::sankey_layout;
    use super::state::Diagram;
    let (mut app, row, scope, chosen) = interaction_fixture();
    let groups = [
        counterparty(Some("county:26099"), "111", "4", "0"),
        counterparty(Some("county:26163"), "0", "0", "17"),
    ];
    let page_rows = state::connections(&groups);
    let world = app.world_mut();
    world.resource_mut::<MoneyView>().rows = page_rows.clone();
    world.trigger(ObserverKeyboardActivate {
        entity: row,
        context: Some(scope.context.clone()),
    });
    world.resource_mut::<MoneyView>().offset = 20;
    let toggle = world
        .spawn(Target {
            scope: scope.clone(),
            offset: 20,
            action: Action::Diagram(Diagram::Sankey),
        })
        .observe(state::keyboard)
        .id();
    world.trigger(ObserverKeyboardActivate {
        entity: toggle,
        context: Some(scope.context.clone()),
    });
    let view = world.resource::<MoneyView>();
    assert_eq!(view.diagram, Diagram::Sankey);
    assert_eq!(view.offset, 20);
    assert_eq!(view.scope.as_ref(), Some(&scope));
    assert_eq!(view.rows, page_rows);
    assert_eq!(view.selected_row(), Some(&chosen));
    let diagram = sankey_layout::layout(&scope.county, &view.rows);
    let home = Some("county:26163");
    let peer = Some("county:26099");
    let endpoints: Vec<_> = diagram
        .bands
        .iter()
        .map(|b| {
            (
                diagram.payers[b.payer].key.as_deref(),
                diagram.recipients[b.recipient].key.as_deref(),
            )
        })
        .collect();
    assert_eq!(endpoints, [(home, peer), (peer, home), (home, home)]);
    assert!((diagram.bands[0].thickness / diagram.bands[1].thickness - 111.0 / 4.0).abs() < 0.0001);
    let reverse = world
        .spawn(Target {
            scope: scope.clone(),
            offset: 20,
            action: Action::Diagram(Diagram::Map),
        })
        .observe(state::pointer)
        .id();
    world.trigger(PointerClick {
        entity: reverse,
        pointer: Pointer::new(
            PointerId::Mouse,
            Location {
                target: bevy::camera::NormalizedRenderTarget::None {
                    width: 0,
                    height: 0,
                },
                position: Vec2::ZERO,
            },
        ),
        button: PointerButton::Primary,
        hit: HitData::new(Entity::PLACEHOLDER, 1.0, None, None),
        duration: Duration::ZERO,
        count: 1,
    });
    assert_eq!(world.resource::<MoneyView>().diagram, Diagram::Map);
    assert_eq!(world.resource::<MoneyView>().selected_row(), Some(&chosen));
}

#[test]
fn labor_mode_rejects_old_targets_and_leaves_unknown_basis_out_of_ribbon_width() {
    use super::state::Measure;
    use super::{rail, sankey_layout};
    use babylon_persistence::money_journal::{LaborAmount, LaborDirections, LaborFlowRow};

    let (mut app, old_row, scope, _) = interaction_fixture();
    let world = app.world_mut();
    world.resource_mut::<MoneyView>().offset = 20;
    let switch = world
        .spawn(Target {
            scope: scope.clone(),
            offset: 20,
            action: Action::Measure(Measure::Labor),
        })
        .observe(state::keyboard)
        .id();
    world.trigger(ObserverKeyboardActivate {
        entity: switch,
        context: Some(scope.context.clone()),
    });
    let view = world.resource::<MoneyView>();
    assert_eq!(
        view.scope.as_ref().expect("observed county").measure,
        Measure::Labor
    );
    assert!(view.rows.is_empty() && view.selected_row().is_none());
    assert_eq!(view.offset, 0);
    let amount = |hours: &str, unknown: &str, count: &str| LaborAmount {
        recorded_micro_hours: hours.into(),
        unknown_basis_movements: unknown.into(),
        movement_count: count.into(),
    };
    let group = LaborFlowRow {
        key: Some("county:26099".into()),
        label: None,
        rank: Some(1),
        groups: 1,
        current: LaborDirections {
            inbound: amount("0", "3", "3"),
            outbound: amount("1250000", "1", "2"),
            within: amount("0", "0", "0"),
            net_recorded_micro_hours: "-1250000".into(),
        },
        comparison: None,
        net_change_recorded_micro_hours: None,
    };
    let mut compared = group.clone();
    compared.comparison = Some(LaborDirections {
        inbound: amount("0", "2", "2"),
        outbound: amount("3000000", "1", "4"),
        within: amount("0", "0", "0"),
        net_recorded_micro_hours: "-3000000".into(),
    });
    compared.net_change_recorded_micro_hours = Some("1750000".into());
    let summary = super::compare::labor_net(&compared, 2);
    for reading in [
        "Net recorded hours\n+1.25 recorded h",
        "Period 1 net\n+3 recorded h",
        "Change in recorded net\n-1.75 recorded h",
        "Period 2 unknown prior labor in movements, received 1, sent 3",
        "Period 1 unknown prior labor in movements, received 1, sent 2",
    ] {
        assert!(summary.contains(reading), "{summary}");
    }
    let rows = state::labor_connections(&[group]);
    assert_eq!(rows.len(), 2);
    assert_eq!(rows[0].key.direction, Direction::PaidTo);
    assert_eq!(rows[1].key.direction, Direction::ReceivedFrom);
    assert!(rail::reading(&rows[0].quantity).contains("3 of 3 movements"));
    assert!(rail::reading(&rows[1].quantity).contains("1.25 recorded h"));
    let chart = sankey_layout::layout(&scope.county, &rows);
    assert_eq!(chart.bands.len(), 1);
    assert_eq!(chart.bands[0].row, 1);
    world.resource_mut::<MoneyView>().rows = rows;
    world.trigger(ObserverKeyboardActivate {
        entity: old_row,
        context: Some(scope.context),
    });
    assert!(world.resource::<MoneyView>().selected.is_none());
}

#[test]
fn county_accounts_disclosure_accepts_the_current_site_page_and_refuses_stale_controls() {
    let (mut app, entity, scope, _) = interaction_fixture();
    let press = || ObserverKeyboardActivate {
        entity,
        context: Some(scope.context.clone()),
    };
    app.world_mut().entity_mut(entity).insert(Target {
        scope: scope.clone(),
        offset: 0,
        action: Action::Books {
            from: None,
            to: Some(0),
        },
    });
    app.world_mut().trigger(press());
    assert_eq!(app.world().resource::<MoneyView>().books.offset, Some(0));
    app.world_mut().entity_mut(entity).insert(Target {
        scope: scope.clone(),
        offset: 0,
        action: Action::Books {
            from: Some(6),
            to: None,
        },
    });
    app.world_mut().trigger(press());
    assert_eq!(app.world().resource::<MoneyView>().books.offset, Some(0));
    app.world_mut().entity_mut(entity).insert(Target {
        scope: scope.clone(),
        offset: 0,
        action: Action::Books {
            from: Some(0),
            to: None,
        },
    });
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .perspective = Perspective::PlayerKnowledge;
    app.world_mut().trigger(press());
    assert_eq!(app.world().resource::<MoneyView>().books.offset, Some(0));
}

#[test]
fn frame_connections_centers_the_actual_endpoints_and_preserves_manual_reset() {
    use super::super::MapOrbit;
    use super::geometry;
    let mut orbit = MapOrbit::new(5000.0);
    let initial = orbit.clone();
    let a = Vec3::new(-1162.0, 12.0, 1363.0);
    let b = Vec3::new(-1461.0, 12.0, 1259.0);
    geometry::frame_bounds(&mut orbit, a.min(b), a.max(b), 1.5);
    assert_eq!(orbit.target.x.to_bits(), a.midpoint(b).x.to_bits());
    assert_eq!(orbit.target.z.to_bits(), a.midpoint(b).z.to_bits());
    assert!(orbit.distance < initial.distance * 0.2);
    assert_eq!(
        orbit.fitted_distance.to_bits(),
        initial.fitted_distance.to_bits()
    );
    geometry::frame_bounds(&mut orbit, a, a, 0.55);
    assert!(orbit.distance.is_finite() && orbit.distance >= initial.fitted_distance * 0.08);
}

#[test]
fn prior_period_change_uses_the_countys_sign_and_prior_only_rows_have_no_width() {
    use super::compare::{self, Periods};
    use babylon_persistence::money_journal::PeriodWindow;
    assert_eq!(Periods::WithPrior.window(0), None);
    assert_eq!(Periods::WithPrior.window(1), None);
    assert_eq!(Periods::Current.window(2), None);
    assert_eq!(
        Periods::WithPrior.window(3),
        Some(PeriodWindow { first: 2, last: 2 })
    );
    let mut prior_only = counterparty(Some("county:02020"), "0", "0", "0");
    let mut prior = prior_only.current.clone();
    prior.inflow_micros = "8000000".into();
    prior.net_micros = "8000000".into();
    prior_only.comparison = Some(prior);
    prior_only.net_change_micros = Some("-8000000".into());
    let summary = compare::money_net(&prior_only, 3);
    assert!(summary.contains("Period 2 net\n-$8.00"));
    assert!(summary.contains("Change in net\n+$8.00"));
    let mut wayne = counterparty(Some("county:26163"), "0", "0", "0");
    wayne.current.net_micros = "267567952828417".into();
    assert_eq!(
        compare::money_net(&wayne, 2),
        "Net received\n-$267,567,952.828417"
    );
    let rows = state::connections(&[prior_only]);
    assert_eq!(rows.len(), 1);
    assert_eq!(rows[0].key.direction, Direction::PaidTo);
    assert_eq!(rows[0].quantity.micros(), "0");
}

#[test]
fn stale_comparison_buttons_cannot_replace_a_new_period_query() {
    use super::compare::Periods;
    let (mut app, entity, mut scope, _) = interaction_fixture();
    let mut session = app.world_mut().resource_mut::<ObserverSession>();
    session.viewed_tick = 2;
    session.durable_tick = 2;
    scope.context = session.context();
    let frame = observer_io_tests::snapshot_with_event(&session, "delivery", 2);
    app.world_mut()
        .insert_resource(ObserverFrame(Some(frame), None));
    app.world_mut().resource_mut::<MoneyView>().scope = Some(scope.clone());
    app.world_mut().entity_mut(entity).insert(Target {
        scope: scope.clone(),
        offset: 0,
        action: Action::Compare(Periods::WithPrior),
    });
    let press = || ObserverKeyboardActivate {
        entity,
        context: Some(scope.context.clone()),
    };
    app.world_mut().trigger(press());
    let compared = app
        .world()
        .resource::<MoneyView>()
        .scope
        .as_ref()
        .expect("comparing")
        .clone();
    assert_eq!(compared.periods, Periods::WithPrior);
    app.world_mut().entity_mut(entity).insert(Target {
        scope: scope.clone(),
        offset: 0,
        action: Action::Compare(Periods::Current),
    });
    app.world_mut().trigger(press());
    assert_eq!(
        app.world().resource::<MoneyView>().scope.as_ref(),
        Some(&compared)
    );
}

#[test]
fn grouping_ranks_the_same_county_and_draws_only_the_selected_groups_actual_locations() {
    let (mut app, _, original, _) = interaction_fixture();
    let change = app
        .world_mut()
        .spawn(Target {
            scope: original.clone(),
            offset: 0,
            action: Action::Group(FlowGroup::Company),
        })
        .observe(state::keyboard)
        .id();
    app.world_mut().trigger(ObserverKeyboardActivate {
        entity: change,
        context: Some(original.context.clone()),
    });
    let view = app.world().resource::<MoneyView>();
    let scope = view.scope.as_ref().expect("same geographic workspace");
    assert_eq!(scope.group, FlowGroup::Company);
    assert_eq!(scope.county, original.county);
    assert_eq!(scope.context, original.context);
    assert_eq!(scope.periods, original.periods);
    let query = state::flow_query(scope, 0);
    assert_eq!(query.focus_group, Some(FlowGroup::Location));
    assert_eq!(query.focus.as_deref(), Some("county:26163"));
    assert_eq!(query.group, FlowGroup::Company);
    let mut group = counterparty(Some("company:0011"), "111", "0", "0");
    group.label = Some("Fuel · National 1".into());
    let grouped = state::connections(&[group]);
    let key = grouped[0].key.clone();
    let query = super::geographic_legs::request(scope, &key, 0);
    assert_eq!(query.group, FlowGroup::Location);
    let peer = query.peer.expect("exact peer constraint");
    assert_eq!(peer.group, FlowGroup::Company);
    assert_eq!(peer.key, key.peer);
    assert_eq!(peer.direction, FlowDirection::Inbound);
    assert_eq!(
        super::grouping::peer_label(
            scope,
            key.peer.as_deref(),
            grouped[0].label.as_deref(),
            app.world().resource::<CountyAtlas>()
        ),
        "Fuel · National 1"
    );
}

#[test]
fn company_statements_require_a_selected_represented_company_and_a_current_full_observer() {
    let (mut app, select, mut scope, _) = interaction_fixture();
    scope.group = FlowGroup::Company;
    let company = format!("company:{}", "34".repeat(32));
    let rows = state::connections(&[counterparty(Some(&company), "12", "0", "0")]);
    let key = rows[0].key.clone();
    {
        let mut view = app.world_mut().resource_mut::<MoneyView>();
        view.scope = Some(scope.clone());
        view.rows = rows;
    }
    *app.world_mut()
        .get_mut::<Target>(select)
        .expect("connection") = Target {
        scope: scope.clone(),
        offset: 0,
        action: Action::Select(key),
    };
    let open = app
        .world_mut()
        .spawn(Target {
            scope: scope.clone(),
            offset: 0,
            action: Action::CompanyAccounts(true),
        })
        .observe(state::keyboard)
        .id();
    let press = |entity| ObserverKeyboardActivate {
        entity,
        context: Some(scope.context.clone()),
    };
    app.world_mut().trigger(press(open));
    assert!(!app.world().resource::<MoneyView>().company.is_open());
    app.world_mut().trigger(press(select));
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .perspective = Perspective::PlayerKnowledge;
    app.world_mut().trigger(press(open));
    assert!(!app.world().resource::<MoneyView>().company.is_open());
    app.world_mut()
        .resource_mut::<ObserverSession>()
        .perspective = Perspective::FullObserver;
    app.world_mut().trigger(press(open));
    assert!(app.world().resource::<MoneyView>().company.is_open());
}

use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;
use babylon_persistence::freight_access::{
    Access, AccessDirection, AccessError, AccessRow, Reference,
};
use babylon_persistence::observer_reader::{ObserverEconomySnapshot, ObserverVisibility};
use babylon_persistence::production_observation::{ProductionPhysicalEdge, ProductionRoadSource};

fn check_captured_road_fallback(
    mut frame: ObserverEconomySnapshot,
    reference: &Reference,
    origin: CountyGeoid,
    canada: EconomicLocation,
    outgoing: &[AccessRow],
) {
    use std::path::Path;

    let refused = Reference::load(Some(Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/Cargo.toml"
    ))))
    .expect("independent captured corridor source");
    assert_eq!(refused.supplement_error, Some(AccessError::Digest));
    assert_eq!(
        refused
            .connections(&frame, origin, AccessDirection::Outbound)
            .expect("captured connections survive an invalid road matrix")
            .as_slice(),
        outgoing
    );
    let campaign = frame
        .production
        .as_mut()
        .expect("captured production frame");
    campaign.road_source = Some(ProductionRoadSource {
        graph_sha256: "different captured graph".into(),
        pbf_sha256: String::new(),
        pbf_bytes: 0,
        pbf_url: String::new(),
        replication_timestamp: String::new(),
        footprint_sha256: String::new(),
        buffer_degrees_e7: 0,
        extraction_version: String::new(),
        distance_version: String::new(),
        routing_profile_version: String::new(),
    });
    campaign.physical_routes[0].physical_edge_ids = vec!["actual-captured-corridor".to_owned()];
    campaign.physical_routes[0].distance_mm = Some(1000);
    campaign.physical_edges.push(ProductionPhysicalEdge {
        id: "actual-captured-corridor".into(),
        shape_e7: vec![[-830_400_000, 423_000_000], [-830_400_100, 423_000_000]],
        distance_mm: 1000,
    });
    assert!(!reference.graph_matches(campaign));
    let preserved = reference
        .connections(&frame, origin, AccessDirection::Outbound)
        .expect("alternative capture");
    assert_eq!(
        preserved
            .iter()
            .find(|r| r.peer == canada)
            .expect("captured foreign endpoint")
            .corridors[0]
            .distance_mm,
        Some(1000)
    );
    assert!(preserved
        .iter()
        .filter(|r| r.peer != canada)
        .all(|r| r.access == Access::Unqualified));
    let incoming = reference
        .connections(&frame, origin, AccessDirection::Inbound)
        .expect("inbound freight access");
    assert!(incoming.iter().all(|r| r.peer != canada));
    frame.visibility = ObserverVisibility::KnownPreview;
    assert!(reference
        .connections(&frame, origin, AccessDirection::Outbound)
        .is_err());
}

#[test]
fn freight_map_and_network_share_typed_foreign_corridor_without_an_invented_road_path() {
    use super::freight::Command;
    use super::state::Diagram;
    let (mut app, _, scope, _) = interaction_fixture();
    let mut snapshot = crate::production::tests::snapshot();
    let wayne = "county:26163".parse().expect("Wayne location");
    let canada = "foreign:canada".parse().expect("Canada location");
    snapshot.sites[0].location = wayne;
    snapshot.sites[1].location = canada;
    let mut frame = app
        .world()
        .resource::<ObserverFrame>()
        .0
        .clone()
        .expect("fixture observer frame");
    frame.production = Some(snapshot);
    let reference = Reference::load(None).expect("bundled regional baseline");
    let origin = "26163".parse().expect("Wayne county");
    let outgoing = reference
        .connections(&frame, origin, AccessDirection::Outbound)
        .expect("outbound freight access");
    assert_eq!(outgoing.len(), 84);
    let foreign = outgoing
        .iter()
        .find(|r| r.peer == canada)
        .expect("Canada endpoint");
    assert_eq!(foreign.access, Access::OutsideCoverage);
    assert_eq!(foreign.corridors[0].route_id, "a-b");
    assert_eq!(foreign.corridors[0].distance_mm, None);
    assert!(outgoing
        .iter()
        .filter(|r| r.peer != canada)
        .all(|r| r.access == Access::Unqualified));
    check_captured_road_fallback(frame, &reference, origin, canada, &outgoing);

    let run = |world: &mut World, action: Action| {
        let entity = world
            .spawn(Target {
                scope: scope.clone(),
                offset: 0,
                action,
            })
            .observe(state::keyboard)
            .id();
        world.trigger(ObserverKeyboardActivate {
            entity,
            context: Some(scope.context.clone()),
        });
    };
    let world = app.world_mut();
    run(world, Action::Freight(Command::Open));
    assert_eq!(world.resource::<MoneyView>().freight.origin, Some(origin));
    world.resource_mut::<MoneyView>().freight.rows = Some(Ok(outgoing));
    let pick = world.resource::<MoneyView>().freight.selection(canada);
    run(world, Action::Freight(pick));
    for diagram in [Diagram::Sankey, Diagram::Map] {
        run(world, Action::Diagram(diagram));
        let view = world.resource::<MoneyView>();
        assert_eq!(view.diagram, diagram);
        assert_eq!(view.freight.selected, Some(canada));
        assert_eq!(view.freight.origin, Some(origin));
    }
}

#[test]
fn freight_and_economic_diagrams_have_separate_native_sample_windows() {
    use crate::observer_performance::RenderMode;
    let (mut app, _, _, _) = interaction_fixture();
    let mut view = app.world_mut().resource_mut::<MoneyView>();
    assert_eq!(view.render_mode(), RenderMode::MoneyMap);
    view.measure = state::Measure::Labor;
    assert_eq!(view.render_mode(), RenderMode::LaborMap);
    view.diagram = state::Diagram::Sankey;
    assert_eq!(view.render_mode(), RenderMode::LaborSankey);
    view.freight.enabled = true;
    assert_eq!(view.render_mode(), RenderMode::FreightNetwork);
    view.diagram = state::Diagram::Map;
    assert_eq!(view.render_mode(), RenderMode::FreightMap);
    view.scope = None;
    assert_eq!(view.render_mode(), RenderMode::Map3d);
}

#[test]
fn ranked_remainder_reports_all_off_page_groups_and_keeps_paging_directional() {
    use super::rail;
    use babylon_persistence::money_journal::FlowPage;

    let (mut app, _, _, _) = interaction_fixture();
    app.world_mut().spawn((state::MoneyRail, Node::default()));
    app.add_systems(Update, rail::paint);
    for (offset, count, outside) in [(0, 20, 5), (20, 5, 20)] {
        let groups: Vec<_> = (offset..offset + count)
            .map(|n| {
                counterparty(
                    Some(&format!("county:{:05}", 26001 + n * 2)),
                    "1000000",
                    "0",
                    "0",
                )
            })
            .collect();
        let mut total = counterparty(None, "25000000", "0", "0");
        total.groups = 25;
        let mut remainder = counterparty(None, &(outside * 1_000_000).to_string(), "0", "0");
        remainder.groups = outside;
        {
            let mut view = app.world_mut().resource_mut::<MoneyView>();
            view.offset = offset;
            view.rows = state::connections(&groups);
            view.page = Some(Page::Money(Box::new(FlowPage {
                groups,
                total,
                remainder,
            })));
        }
        app.update();
        let world = app.world_mut();
        let expected =
            format!("{outside} locations outside this page\nReceived $0.00\nPaid ${outside}.00");
        assert!(
            world
                .query::<&Text>()
                .iter(world)
                .any(|text| text.contains(&expected)),
            "{expected}"
        );
        let targets: Vec<_> = world
            .query::<&Target>()
            .iter(world)
            .filter_map(|target| match target.action {
                Action::Page(to) => Some(to),
                _ => None,
            })
            .collect();
        assert_eq!(targets, [if offset == 0 { 20 } else { 0 }]);
    }
}

fn set_industry_page(view: &mut MoneyView, scope: Scope) -> (ConnectionKey, ConnectionKey) {
    use babylon_persistence::money_journal::FlowPage;

    let mut groups = [
        counterparty(Some("food"), "12", "0", "0"),
        counterparty(None, "9", "0", "0"),
    ];
    for group in &mut groups {
        group
            .current
            .net_micros
            .clone_from(&group.current.inflow_micros);
    }
    let rows = state::connections(&groups);
    let food = rows[0].key.clone();
    let unreported = rows[1].key.clone();
    view.scope = Some(scope);
    view.rows = rows;
    let mut total = counterparty(None, "21", "0", "0");
    total.current.net_micros = "21".into();
    total.groups = 2;
    let mut remainder = counterparty(None, "0", "0", "0");
    remainder.groups = 0;
    view.page = Some(Page::Money(Box::new(FlowPage {
        groups: groups.into(),
        total,
        remainder,
    })));
    (food, unreported)
}

#[test]
fn industry_sources_expand_and_collapse_for_the_current_typed_peer_only() {
    use super::rail;
    let (mut app, select, mut scope, _) = interaction_fixture();
    scope.group = FlowGroup::Industry;
    let (food, unreported) = set_industry_page(
        &mut app.world_mut().resource_mut::<MoneyView>(),
        scope.clone(),
    );
    app.world_mut().spawn((state::MoneyRail, Node::default()));
    app.add_systems(Update, (rail::paint, rail::highlight).chain());
    let has_text = |app: &mut App, expected: &str| {
        let world = app.world_mut();
        world
            .query::<&Text>()
            .iter(world)
            .any(|text| text.contains(expected))
    };
    let button = |app: &mut App, action| {
        app.world_mut()
            .spawn(Target {
                scope: scope.clone(),
                offset: 0,
                action,
            })
            .observe(state::keyboard)
            .id()
    };
    let pressed = |app: &mut App, action: Action| {
        let world = app.world_mut();
        world
            .query::<(&Target, &AccessibilityNode)>()
            .iter(world)
            .find(|(target, _)| target.action == action)
            .expect("named inspector control")
            .1
            .toggled()
    };
    let toggle = button(&mut app, Action::IndustrySources);
    let unknown = button(&mut app, Action::Select(unreported.clone()));
    let press = |entity| ObserverKeyboardActivate {
        entity,
        context: Some(scope.context.clone()),
    };
    *app.world_mut()
        .get_mut::<Target>(select)
        .expect("connection") = Target {
        scope: scope.clone(),
        offset: 0,
        action: Action::Select(food.clone()),
    };
    app.world_mut().trigger(press(toggle));
    assert!(!app.world().resource::<MoneyView>().industry.expanded);
    app.world_mut().trigger(press(select));
    app.update();
    for (action, active) in [
        (Action::Select(food.clone()), true),
        (Action::Select(unreported.clone()), false),
        (Action::Measure(state::Measure::Money), true),
        (Action::Measure(state::Measure::Labor), false),
        (Action::Group(FlowGroup::Industry), true),
        (Action::Group(FlowGroup::Company), false),
        (Action::Diagram(state::Diagram::Map), true),
        (Action::Diagram(state::Diagram::Sankey), false),
    ] {
        assert_eq!(pressed(&mut app, action), Some(active.into()));
    }
    assert_eq!(pressed(&mut app, Action::Follow), None);
    assert!(has_text(&mut app, "Showing industries 1–2 of 2"));
    assert!(has_text(
        &mut app,
        "→ Food\n$0.000012\nCounty net with this industry\nNet received\n-$0.000012"
    ));
    assert!(!has_text(&mut app, "code food"));
    app.world_mut().trigger(press(toggle));
    app.update();
    assert!(has_text(
        &mut app,
        "Industry code food\nReading the captured industry sources…"
    ));
    assert!(app.world().resource::<MoneyView>().industry.expanded);
    app.world_mut().trigger(press(toggle));
    assert!(!app.world().resource::<MoneyView>().industry.expanded);
    app.update();
    assert!(!has_text(&mut app, "code food"));
    app.world_mut().trigger(press(unknown));
    app.world_mut().trigger(press(toggle));
    assert!(!app.world().resource::<MoneyView>().industry.expanded);
    app.update();
    assert_eq!(pressed(&mut app, Action::Select(food)), Some(false.into()));
    assert_eq!(
        pressed(&mut app, Action::Select(unreported)),
        Some(true.into())
    );
    assert!(has_text(&mut app, "→ Industry unreported\n$0.000009"));
}

#[test]
fn labor_sankey_keeps_both_boundary_balances_visible_without_current_transfers() {
    use babylon_persistence::money_journal::{
        CountyLaborCarry, LaborAmount, LaborCarryAmount, LaborDirections, LaborFlowPage,
        LaborFlowRow,
    };
    let (mut app, _, mut scope, _) = interaction_fixture();
    scope.measure = state::Measure::Labor;
    let empty = LaborAmount {
        recorded_micro_hours: "0".into(),
        unknown_basis_movements: "0".into(),
        movement_count: "0".into(),
    };
    let row = LaborFlowRow {
        key: None,
        label: None,
        rank: None,
        groups: 0,
        current: LaborDirections {
            inbound: empty.clone(),
            outbound: empty.clone(),
            within: empty,
            net_recorded_micro_hours: "0".into(),
        },
        comparison: None,
        net_change_recorded_micro_hours: None,
    };
    let page = LaborFlowPage {
        groups: Vec::new(),
        remainder: row.clone(),
        total: row,
        county_carry: Some(CountyLaborCarry {
            opening: LaborCarryAmount {
                recorded_micro_hours: 0,
                positions: 2,
                unknown_positions: 2,
            },
            closing: LaborCarryAmount {
                recorded_micro_hours: 1_000_001,
                positions: 3,
                unknown_positions: 0,
            },
        }),
    };
    assert_eq!(
        super::grouping::peer_label(&scope, None, None, app.world().resource::<CountyAtlas>()),
        "Unlocated ledger endpoint"
    );
    scope.group = FlowGroup::Company;
    assert_eq!(
        super::grouping::peer_label(&scope, None, None, app.world().resource::<CountyAtlas>()),
        "No represented company"
    );
    app.insert_resource(MoneyView {
        scope: Some(scope),
        diagram: state::Diagram::Sankey,
        measure: state::Measure::Labor,
        page: Some(Page::Labor(Box::new(page))),
        status: Status::Ready,
        ..default()
    })
    .init_resource::<Assets<Image>>()
    .add_systems(Update, super::sankey::paint);
    app.update();
    let world = app.world_mut();
    // A county can have opening and closing stock without a single transfer on this page.
    let mut children = world.query::<&Children>();
    let mut bars = children
        .iter(world)
        .filter_map(|siblings| {
            let mut ids = siblings.iter();
            let text = world.get::<Text>(ids.next()?)?;
            let node = world.get::<Node>(ids.next()?)?;
            (text.0.starts_with("Opening carry") || text.0.starts_with("Closing carry"))
                .then_some((text.0.as_str(), node.width))
        })
        .collect::<Vec<_>>();
    bars.sort_by_key(|(label, _)| label.starts_with("Closing"));
    assert_eq!(
        bars,
        [
            (
                "Opening carry · 0 recorded h across 2 located positions · unknown prior labor in 2 positions",
                percent(0)
            ),
            (
                "Closing carry · 1.000001 recorded h across 3 located positions",
                percent(100)
            ),
        ]
    );
    let mut labels = world.query::<&Text>();
    assert!(labels
        .iter(world)
        .any(|t| t.0 == "No recorded labor movements on this page."));
    assert!(world.query::<&ImageNode>().iter(world).next().is_none());
}
