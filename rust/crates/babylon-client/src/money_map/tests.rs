use super::state::{self, Direction, Quantity};
use babylon_persistence::money_journal::{FlowAmounts, FlowRow};

fn counterparty(key: Option<&str>, incoming: &str, outgoing: &str, internal: &str) -> FlowRow {
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

use super::state::{Action, Connection, MoneyView, Scope, Status, Target};
use crate::atlas::CountyAtlas;
use crate::map::{CountyMapScope, SelectedCounty};
use crate::map_economy_lens::MapLens;
use crate::observer::{ObserverSession, Perspective};
use crate::observer_focus::ObserverKeyboardActivate;
use crate::observer_io::tests as observer_io_tests;
use crate::observer_ui::{ObserverFrame, ObserverUiState};
use crate::production::PrimaryView;
use babylon_persistence::identity::CampaignId;
use bevy::picking::backend::HitData;
use bevy::picking::pointer::{Location, PointerButton, PointerId};
use bevy::prelude::*;
use std::time::Duration;
use uuid::Uuid;

fn interaction_fixture() -> (App, Entity, Scope, Connection) {
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
        "Net recorded hours  +1.25 recorded h",
        "Period 1 net  +3 recorded h",
        "Change in recorded net  -1.75 recorded h",
        "Period 2 unknown prior labor in movements · received 1, sent 3",
        "Period 1 unknown prior labor in movements · received 1, sent 2",
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
    assert!(summary.contains("Period 2 net  -$8.00"));
    assert!(summary.contains("Change in net  +$8.00"));
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
