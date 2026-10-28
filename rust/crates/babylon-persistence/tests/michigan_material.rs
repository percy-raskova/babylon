use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_material_circuit::{
    decode_material_circuit_state, MaterialCatalog, MaterialCircuitState,
};
use babylon_persistence::michigan_content::MichiganContentPreset;
use babylon_persistence::michigan_material::MichiganMaterialCatalog;
use babylon_persistence::michigan_material::{MichiganDeliveryPreset, MichiganMaterialSite};
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_replay::{MaterialReplaySession, PreparedMaterialTick};
use babylon_tick::material_world;
use babylon_tick::material_world::{MaterialTickReceipts, MaterialWorldRegister};
use babylon_tick::replay_session::ReplayCommitDisposition;

type Session = MaterialReplaySession<HypergraphStore>;

fn session(preset: MichiganDeliveryPreset) -> Session {
    MichiganContentPreset::new_campaign(preset)
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation")
        .into_session()
        .expect("the fixture opens a session")
}

fn prepare(session: &Session) -> PreparedMaterialTick<HypergraphStore> {
    let actions = OrderedPracticeActionBatch::empty(
        session.graph_session().session_identity().clone(),
        session.completed_tick() + 1,
    )
    .expect("the empty authored batch constructs");
    session
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance")
}

fn commit(session: &mut Session, candidate: PreparedMaterialTick<HypergraphStore>) {
    session
        .commit_prepared_and_publish(&mut CollectingSink::default(), candidate, |_, _| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("the prepared period commits");
}

fn advance(session: &mut Session) -> MaterialTickReceipts {
    let candidate = prepare(session);
    let receipts = material_world::decode_material_receipts(candidate.material().receipt_bytes())
        .expect("the canonical bytes decode into the declared type");
    commit(session, candidate);
    receipts
}

#[test]
fn shared_freight_capacity_changes_two_chains_through_the_authoritative_session() {
    for (name, sheet, meal, panels) in [
        ("michigan-material-shared-freight-ample-v7", 320, 80, 32),
        (
            "michigan-material-shared-freight-constrained-v7",
            120,
            40,
            12,
        ),
    ] {
        let preset = MichiganContentPreset::from_id(name)
            .expect("shared freight must be admitted campaign content");
        let mut session = preset
            .create_foundation(&crate::test_support::catalog())
            .expect("the authored catalog builds the foundation")
            .into_session()
            .expect("the fixture opens a session");
        let catalog = crate::test_support::catalog();
        advance(&mut session);
        let shipped = |key: &str| {
            let id = catalog
                .routes()
                .iter()
                .find(|r| r.key == key)
                .expect("the fixture holds the searched element")
                .order_id();
            session
                .material()
                .state()
                .orders
                .iter()
                .find(|r| r.order_id == id)
                .expect("the fixture holds the searched element")
                .shipped
        };
        assert_eq!(shipped("sheet-transfer"), sheet);
        assert_eq!(shipped("food-transfer"), meal);
        assert_material_conserved(session.material().state());
        advance(&mut session);
        let third = advance(&mut session);
        let produced = |key: &str| {
            let id = catalog
                .processes()
                .iter()
                .find(|p| p.key == key)
                .expect("the fixture holds the searched element")
                .id();
            third
                .production
                .iter()
                .filter(|r| r.process_id == id)
                .map(|r| {
                    r.produced_batches
                        * catalog
                            .processes()
                            .iter()
                            .find(|p| p.id() == id)
                            .expect("the fixture holds the searched element")
                            .output_quantity_per_batch
                })
                .sum::<u64>()
        };
        assert_eq!(produced("panel-forming"), panels);
        assert_eq!(produced("meal-packaging"), meal);
        assert_material_conserved(session.material().state());
    }
}

#[test]
fn shared_freight_has_one_capacity_principal_and_competing_order_demand() {
    let catalog = crate::test_support::catalog();
    let opening = |preset| {
        MichiganContentPreset::new_campaign(preset)
            .create_foundation(&catalog)
            .expect("the authored catalog builds the foundation")
            .initial_register()
            .state()
            .clone()
    };
    let ample = opening(MichiganDeliveryPreset::SharedFreightAmple);
    let mut constrained = opening(MichiganDeliveryPreset::SharedFreightConstrained);
    assert_eq!(ample.corridor_capacities.len(), 2 * 16);
    let sheet = catalog
        .routes()
        .iter()
        .find(|r| r.key == "sheet-transfer")
        .expect("the fixture holds the searched element");
    let shared = ample
        .route_stage_capacities
        .iter()
        .find(|row| row.route_id == sheet.id())
        .expect("the fixture holds the searched element")
        .corridor_id;
    for row in &mut constrained.corridor_capacities {
        if row.corridor_id == shared {
            assert_eq!(row.available_grams, 160_000);
            row.available_grams = 800_000;
        }
    }
    assert_eq!(
        ample, constrained,
        "capacity is the only changed material input"
    );

    let text = include_str!("../../../../content/scenarios/michigan/defines.toml")
        .replace("ORDERED_UNITS = 200", "ORDERED_UNITS = 80");
    let changed = MichiganMaterialCatalog::from_defines_toml(&text)
        .expect("the authored input admits the derived value");
    let mut session =
        MichiganContentPreset::new_campaign(MichiganDeliveryPreset::SharedFreightConstrained)
            .create_foundation(&changed)
            .expect("the authored catalog builds the foundation")
            .into_session()
            .expect("the fixture opens a session");
    let receipts = advance(&mut session);
    let dispatched = |key| {
        let route = changed
            .routes()
            .iter()
            .find(|r| r.key == key)
            .expect("the fixture holds the searched element");
        receipts
            .dispatches
            .iter()
            .filter(|r| r.order_id == route.order_id())
            .map(|r| {
                assert_eq!(r.route_id, route.id());
                r.quantity
            })
            .sum::<u64>()
    };
    assert_eq!(dispatched("sheet-transfer"), 141);
    // ADR285 assigns the last feasible whole-native residual to this food order.
    assert_eq!(dispatched("food-transfer"), 19);
    let dispatched_grams: u64 = ["sheet-transfer", "food-transfer"]
        .into_iter()
        .map(|key| {
            let route = changed
                .routes()
                .iter()
                .find(|r| r.key == key)
                .expect("the fixture holds the searched element");
            dispatched(key)
                .checked_mul(
                    changed
                        .good(&route.good_key)
                        .expect("the fixture catalog holds the addressed good")
                        .grams_per_unit,
                )
                .expect("the fixture arithmetic stays in range")
        })
        .sum();
    assert_eq!(dispatched_grams, 160_000);
    assert_material_conserved(session.material().state());
}

fn inventory(state: &MaterialCircuitState, site: &str, good: &str) -> u64 {
    let catalog = crate::test_support::catalog();
    let site_id = catalog
        .site(site)
        .expect("the fixture catalog holds the addressed site")
        .id();
    let good_id = catalog
        .good(good)
        .expect("the fixture catalog holds the addressed good")
        .id();
    state
        .inventory
        .iter()
        .find(|row| row.site_id == site_id && row.good_id == good_id)
        .map_or(0, |row| row.quantity)
}

fn assert_material_conserved(state: &MaterialCircuitState) {
    let catalog = crate::test_support::catalog();
    let mut metal = 0;
    let mut food = 0;
    for (good_key, scale, is_metal) in [
        ("billet", 1, true),
        ("sheet", 1, true),
        ("panel", 10, true),
        ("subassembly", 20, true),
        ("grain", 1, false),
        ("meal", 1, false),
        ("packaged-meal", 1, false),
    ] {
        let good_id = catalog
            .good(good_key)
            .expect("the fixture catalog holds the addressed good")
            .id();
        let on_hand: u64 = state
            .inventory
            .iter()
            .filter(|row| row.good_id == good_id)
            .map(|row| row.quantity)
            .sum();
        let in_transit: u64 = state
            .freight
            .iter()
            .filter(|row| row.good_id == good_id)
            .map(|row| row.quantity)
            .sum();
        if is_metal {
            metal += (on_hand + in_transit) * scale;
        } else {
            food += (on_hand + in_transit) * scale;
        }
    }
    assert_eq!(
        metal, 600,
        "metal input-equivalent kg at opening {}",
        state.period
    );
    assert_eq!(food, 200, "food kg at opening {}", state.period);
}

fn assert_second_period_delivery_delay(
    standard: &MaterialCircuitState,
    delayed: &MaterialCircuitState,
) {
    assert_eq!(inventory(standard, "macomb-fabricated-metal", "sheet"), 320);
    assert_eq!(inventory(delayed, "macomb-fabricated-metal", "sheet"), 0);
    let catalog = crate::test_support::catalog();
    let transformer = catalog
        .processes()
        .iter()
        .find(|row| row.key == "panel-forming")
        .expect("the fixture holds the searched element");
    assert_eq!(
        standard
            .production_commitments
            .iter()
            .find(|row| row.process_id == transformer.id())
            .expect("the fixture holds the searched element")
            .planned_batches,
        32
    );
    assert_eq!(
        delayed
            .production_commitments
            .iter()
            .find(|row| row.process_id == transformer.id())
            .map_or(0, |row| row.planned_batches),
        0
    );
    assert_eq!(inventory(standard, "wayne-vehicle-parts", "subassembly"), 0);
}

#[test]
fn presets_share_exact_setup_except_the_single_declared_delay() {
    let standard_foundation = MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Standard)
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let standard_catalog = standard_foundation.material_catalog().clone();
    let standard = standard_foundation.initial_register().state().clone();
    let delayed_foundation = MichiganContentPreset::new_campaign(MichiganDeliveryPreset::Delayed)
        .create_foundation(&crate::test_support::catalog())
        .expect("the authored catalog builds the foundation");
    let mut delayed_catalog = delayed_foundation
        .material_catalog()
        .clone()
        .into_definition();
    let delayed = delayed_foundation.initial_register().state().clone();
    let catalog = crate::test_support::catalog();
    let route = catalog
        .routes()
        .iter()
        .find(|route| route.key == "sheet-transfer")
        .expect("the fixture holds the searched element");
    let changed = delayed_catalog
        .route_stages
        .iter_mut()
        .find(|row| row.route_id == route.id())
        .expect("the fixture holds the searched element");
    assert_eq!(changed.travel_periods, 3);
    changed.travel_periods = 1;
    let delayed_catalog = MaterialCatalog::try_new(delayed_catalog)
        .expect("the edited fixture catalog canonicalizes");
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&standard_catalog, &standard)
            .expect("the canonical material state encodes"),
        babylon_material_circuit::encode_material_circuit_state(&delayed_catalog, &delayed)
            .expect("the canonical material state encodes")
    );
    assert_eq!(standard.period, 1);
    assert_eq!(standard.capacities.len(), 5 * 16);
    // Only current opening hours are authored. Following openings come from
    // the graph-owned workforce through the real Staffed composition.
    assert_eq!(standard.labor.len(), 5);
    assert!(standard.labor.iter().all(|row| row.period == 1));
    assert_eq!(catalog.staffing().hours_per_worker_period, 160);
    for (key, hours) in [
        ("sheet-rolling", 3200),
        ("panel-forming", 640),
        ("subassembly-making", 640),
        ("meal-milling", 160),
        ("meal-packaging", 320),
    ] {
        let process = catalog
            .processes()
            .iter()
            .find(|row| row.key == key)
            .expect("the fixture holds the searched element");
        let row = standard
            .labor
            .iter()
            .find(|row| row.site_id == process.site_id())
            .expect("the fixture holds the searched element");
        assert_eq!(row.available, hours, "{key}");
        let seed = catalog
            .staffing()
            .pools
            .iter()
            .find(|pool| pool.process_keys.iter().any(|process| process == key))
            .expect("the fixture holds the searched element");
        assert_eq!(row.available, seed.employed * 160);
    }
    assert_eq!(standard.corridor_capacities.len(), 3 * 16);
    assert_eq!(catalog.terminal_output_disposition(), "on_hand_unsold");
    for site in catalog.sites() {
        let source = catalog
            .industry_for_site(site)
            .expect("the fixture call `industry_for_site` succeeds for the authored inputs");
        assert_eq!(source.area_fips, site.county_geoid);
        assert_eq!(source.industry_code, site.naics);
        assert_eq!(source.disclosure_code.len(), 0);
    }
}

fn assert_food_disconnected(
    standard: &MaterialCircuitState,
    a: &MaterialTickReceipts,
    delayed: &MaterialCircuitState,
    b: &MaterialTickReceipts,
) {
    let catalog = crate::test_support::catalog();
    let food_sites: Vec<_> = catalog
        .sites()
        .iter()
        .filter(|site| site.naics == "311")
        .map(MichiganMaterialSite::id)
        .collect();
    let food_route = catalog
        .routes()
        .iter()
        .find(|route| route.key == "food-transfer")
        .expect("the fixture holds the searched element");
    assert_eq!(
        a.production
            .iter()
            .filter(|row| food_sites.contains(&row.site_id))
            .collect::<Vec<_>>(),
        b.production
            .iter()
            .filter(|row| food_sites.contains(&row.site_id))
            .collect::<Vec<_>>(),
    );
    assert_eq!(
        standard
            .inventory
            .iter()
            .filter(|row| food_sites.contains(&row.site_id))
            .collect::<Vec<_>>(),
        delayed
            .inventory
            .iter()
            .filter(|row| food_sites.contains(&row.site_id))
            .collect::<Vec<_>>(),
    );
    assert_eq!(
        standard
            .freight
            .iter()
            .filter(|row| row.route_id == food_route.id())
            .collect::<Vec<_>>(),
        delayed
            .freight
            .iter()
            .filter(|row| row.route_id == food_route.id())
            .collect::<Vec<_>>(),
    );
    assert_eq!(
        standard
            .orders
            .iter()
            .find(|row| row.order_id == food_route.order_id()),
        delayed
            .orders
            .iter()
            .find(|row| row.order_id == food_route.order_id()),
    );
    assert_eq!(
        standard
            .labor
            .iter()
            .filter(|row| food_sites.contains(&row.site_id))
            .collect::<Vec<_>>(),
        delayed
            .labor
            .iter()
            .filter(|row| food_sites.contains(&row.site_id))
            .collect::<Vec<_>>(),
    );
}

#[test]
fn delivery_delay_changes_following_period_output_with_food_causally_disconnected() {
    let mut standard = session(MichiganDeliveryPreset::Standard);
    let mut delayed = session(MichiganDeliveryPreset::Delayed);
    let mut first_standard_output = None;
    let mut first_delayed_output = None;
    for period in 1..=crate::test_support::catalog()
        .duration()
        .final_period()
        .expect("finite control")
    {
        let a = advance(&mut standard);
        let b = advance(&mut delayed);
        let standard = standard.material().state();
        let delayed = delayed.material().state();
        assert_food_disconnected(standard, &a, delayed, &b);
        assert_material_conserved(standard);
        assert_material_conserved(delayed);
        if inventory(standard, "wayne-vehicle-parts", "subassembly") > 0 {
            first_standard_output.get_or_insert(period);
        }
        if inventory(delayed, "wayne-vehicle-parts", "subassembly") > 0 {
            first_delayed_output.get_or_insert(period);
        }
        if period == 2 {
            assert_second_period_delivery_delay(standard, delayed);
        }
    }
    assert_eq!(first_standard_output, Some(5));
    assert_eq!(first_delayed_output, Some(7));
    for state in [standard.material().state(), delayed.material().state()] {
        assert_eq!(inventory(state, "wayne-vehicle-parts", "subassembly"), 30);
        assert_eq!(inventory(state, "oakland-food", "packaged-meal"), 200);
        assert_eq!(state.freight.len(), 0);
        assert!(state
            .orders
            .iter()
            .all(|order| order.ordered == order.delivered
                && order.realized == order.delivered
                && order.lost == 0));
        assert_eq!(state.period, 17);
    }
}

#[test]
fn every_dispatch_transit_arrival_restart_reproduces_exact_continuation() {
    for preset in [
        MichiganDeliveryPreset::Standard,
        MichiganDeliveryPreset::Delayed,
        MichiganDeliveryPreset::SharedFreightAmple,
        MichiganDeliveryPreset::SharedFreightConstrained,
    ] {
        let mut uninterrupted = session(preset);
        let mut next = Some(prepare(&uninterrupted));
        for period in 1..=crate::test_support::catalog()
            .duration()
            .final_period()
            .expect("finite control")
        {
            // The previous restart comparison already prepared this exact
            // continuation. Retain it while still rebuilding every restored
            // session from a fresh foundation below.
            let candidate = next
                .take()
                .expect("the fixture call `take` succeeds for the authored inputs");
            // Restore the complete graph+register checkpoint, including people
            // and retention. The physical state alone is no longer an owner.
            let mut restored = session(preset);
            restored
                .restore_full_checkpoint(
                    candidate.graph_report().result_stable_graph(),
                    candidate.graph_report().material_state_rows(),
                    candidate
                        .graph_report()
                        .result_registers()
                        .canonical_bytes(),
                    MaterialWorldRegister::decode_external(
                        restored.catalog(),
                        candidate.material().register().canonical_bytes().to_vec(),
                    )
                    .expect("the committed canonical bytes decode"),
                )
                .expect("the committed checkpoint restores");
            let encoded = babylon_material_circuit::encode_material_circuit_state(
                restored.catalog(),
                candidate.material().register().state(),
            )
            .expect("the canonical material state encodes");
            assert_eq!(
                decode_material_circuit_state(restored.catalog(), &encoded)
                    .expect("the canonical material bytes decode"),
                *restored.material().state()
            );
            commit(&mut uninterrupted, candidate);
            assert_eq!(
                restored
                    .current_world_hash()
                    .expect("the committed session publishes a world hash"),
                uninterrupted
                    .current_world_hash()
                    .expect("the committed session publishes a world hash")
            );
            assert_eq!(restored.material(), uninterrupted.material());
            if period
                < crate::test_support::catalog()
                    .duration()
                    .final_period()
                    .expect("finite control")
            {
                let expected = prepare(&uninterrupted);
                let actual = prepare(&restored);
                assert_eq!(actual.identity(), expected.identity());
                assert_eq!(
                    actual.graph_report().successful_event_batch(),
                    expected.graph_report().successful_event_batch()
                );
                assert_eq!(
                    actual.graph_report().report().audit_receipts,
                    expected.graph_report().report().audit_receipts
                );
                assert_eq!(actual.material().register(), expected.material().register());
                assert_eq!(
                    actual.material().receipt_bytes(),
                    expected.material().receipt_bytes()
                );
                next = Some(expected);
            }
        }
    }
}

// These controls qualify exact sixteen-period schedules, not the continuous
// shipped campaign. Keep the horizon explicit in their captured input.
mod test_support {
    use babylon_persistence::michigan_material::MichiganMaterialCatalog;
    pub fn catalog() -> MichiganMaterialCatalog {
        MichiganMaterialCatalog::from_defines_toml(
            &include_str!("../../../../content/scenarios/michigan/defines.toml").replace(
                "DURATION = { kind = \"continuous\" }",
                "DURATION = { kind = \"finite\", final_period = 16 }",
            ),
        )
        .expect("finite sixteen-period material control")
    }
}
