use super::state::{self, Direction};
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
                row.micros.as_str(),
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
        view.rows[0].micros = "237".into();
        assert_eq!(
            view.selected_row().map(|row| row.micros.as_str()),
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
