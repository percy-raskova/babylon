//! Synthetic scale and accounting evidence, never real infrastructure qualification.
//! Regenerate the small fixture with `fixtures/generate_statewide_synthetic.py`.

use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::content_digest::sha256_of;
use babylon_material_circuit::{
    GoodId, MaterialCircuitState, MerchantRole, OrderId, SiteId, UnitId, MAX_MATERIAL_CIRCUIT_ROWS,
};
use babylon_persistence::material_runtime::MAX_MATERIAL_FOUNDATION_BYTES;
use babylon_persistence::michigan_content::MichiganContentPreset;
use babylon_persistence::michigan_material::{
    MichiganDeliveryPreset, MichiganMaterialCatalog, MAX_MICHIGAN_SOURCE_BYTES,
};

use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_replay::{MaterialReplaySession, PreparedMaterialTick};
use babylon_tick::material_world::{
    MaterialTickReceipts, MaterialWorldRegister, MAX_MATERIAL_TICK_RECEIPT_BYTES,
    MAX_MATERIAL_WORLD_REGISTER_BYTES,
};
use babylon_tick::replay_session::ReplayCommitDisposition;

use babylon_persistence::economic_catalog::CapturedEconomicCatalog;
use babylon_persistence::economic_catalog::SourceArtifactKind;
use babylon_persistence::economic_content;
use babylon_tick::material_world;
use std::collections::BTreeMap;
use std::time::Instant;
use synthetic::SyntheticSources;

type Session = MaterialReplaySession<HypergraphStore>;
type Goods = BTreeMap<(GoodId, UnitId), u128>;

#[path = "fixtures/statewide_synthetic.rs"]
mod synthetic;

#[test]
fn physical_paths_require_all_overlapping_capacity_memberships_and_preserve_identity() {
    use babylon_persistence::michigan_material::MichiganMaterialPath;
    let fixture = synthetic::load();
    let qualification = serde_json::to_vec(&fixture.qualification)
        .expect("the value serializes to canonical JSON bytes");
    let mut physical = fixture.physical;
    let mut overlap = physical.capacity_groups[0].clone();
    overlap.key = "second-shared-road-service".to_owned();
    overlap.label = "Second Designed road service".to_owned();
    physical.capacity_groups.push(overlap);
    let compile = |network| {
        MichiganMaterialCatalog::from_statewide_qualification(
            include_str!("../../../../content/scenarios/michigan/defines.toml"),
            &qualification,
            network,
            Vec::new(),
        )
    };
    let physical_bytes =
        serde_json::to_vec(&physical).expect("the value serializes to canonical JSON bytes");
    let catalog = compile(physical.clone()).expect("the authored scenario compiles");
    let mut routed = 0;
    for route in catalog.routes() {
        if let MichiganMaterialPath::Routed { capacity_keys, .. } = &route.path {
            assert_eq!(
                capacity_keys,
                &["second-shared-road-service", "synthetic-shared-road"]
            );
            routed += 1;
        }
    }
    assert!(routed > 0);
    physical.edges.reverse();
    physical.capacity_groups.reverse();
    for group in &mut physical.capacity_groups {
        group.edge_keys.reverse();
    }
    let reordered_bytes =
        serde_json::to_vec(&physical).expect("the value serializes to canonical JSON bytes");
    let reordered = compile(physical.clone()).expect("the authored scenario compiles");
    // Raw supplied source ordering stays evidence. Compare the complete resolved
    // inputs and regenerated initialization separately from that source identity.
    assert_eq!(
        serde_json::to_value(catalog.resolved_report()).expect("the value serializes to JSON"),
        serde_json::to_value(reordered.resolved_report()).expect("the value serializes to JSON")
    );
    assert_eq!(catalog.preset(), reordered.preset());
    assert_eq!(
        catalog.graph_scenario_source(),
        reordered.graph_scenario_source()
    );
    assert_eq!(catalog.rule_source(), reordered.rule_source());
    let original_opening = babylon_persistence::economic_catalog::import_michigan_opening(&catalog)
        .expect("the fixture call `import_michigan_opening` succeeds for the authored inputs");
    let reordered_opening =
        babylon_persistence::economic_catalog::import_michigan_opening(&reordered)
            .expect("the fixture call `import_michigan_opening` succeeds for the authored inputs");
    assert_eq!(original_opening, reordered_opening);
    assert_eq!(
        original_opening
            .compile()
            .expect("the authored scenario compiles")
            .state,
        reordered_opening
            .compile()
            .expect("the authored scenario compiles")
            .state
    );
    let original_capture = CapturedEconomicCatalog::from_michigan(&catalog)
        .expect("the Michigan fixture content loads");
    let reordered_capture = CapturedEconomicCatalog::from_michigan(&reordered)
        .expect("the Michigan fixture content loads");
    let source_kind = SourceArtifactKind::MichiganPhysicalNetworkJson;
    assert_eq!(
        original_capture.source(source_kind),
        Some(physical_bytes.as_slice())
    );
    assert_eq!(
        reordered_capture.source(source_kind),
        Some(reordered_bytes.as_slice())
    );
    assert_ne!(sha256_of(&physical_bytes), sha256_of(&reordered_bytes));
    assert_ne!(original_capture.digest(), reordered_capture.digest());
    let uncovered = physical.edges[0].id.clone();
    for group in &mut physical.capacity_groups {
        group.edge_keys.retain(|key| key != &uncovered);
    }
    assert!(
        compile(physical).is_err(),
        "a routed edge needs its capacity membership"
    );
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

fn stock_and_transit(state: &MaterialCircuitState) -> Goods {
    let mut totals = Goods::new();
    for row in &state.inventory {
        *totals.entry((row.good_id, row.unit_id)).or_default() += u128::from(row.quantity);
    }
    for row in &state.freight {
        *totals.entry((row.good_id, row.unit_id)).or_default() += u128::from(row.quantity);
    }
    totals
}

fn assert_goods_conserved(
    opening: &MaterialCircuitState,
    closing: &MaterialCircuitState,
    receipts: &MaterialTickReceipts,
) {
    let mut available = stock_and_transit(opening);
    let mut accounted = stock_and_transit(closing);
    for receipt in &receipts.production {
        let output = opening
            .process_outputs
            .iter()
            .find(|row| row.process_id == receipt.process_id)
            .expect("the fixture holds the searched element");
        assert_eq!(receipt.site_id, output.site_id);
        *available
            .entry((output.good_id, output.unit_id))
            .or_default() +=
            u128::from(output.quantity_per_batch) * u128::from(receipt.produced_batches);
        for input in opening
            .input_coefficients
            .iter()
            .filter(|row| row.process_id == receipt.process_id)
        {
            *accounted.entry((input.good_id, input.unit_id)).or_default() +=
                u128::from(input.quantity_per_batch) * u128::from(receipt.produced_batches);
        }
    }
    for receipt in &receipts.losses {
        let order = opening
            .orders
            .iter()
            .find(|row| row.order_id == receipt.order_id)
            .expect("the fixture holds the searched element");
        *accounted.entry((order.good_id, order.unit_id)).or_default() +=
            u128::from(receipt.quantity);
    }
    for receipt in &receipts.local_fulfillments {
        *accounted
            .entry((receipt.good_id, receipt.unit_id))
            .or_default() += u128::from(receipt.quantity);
    }
    available.retain(|_, value| *value != 0);
    accounted.retain(|_, value| *value != 0);
    assert_eq!(
        available, accounted,
        "period {} must balance each native good-unit separately; internal transfers are not sinks",
        opening.period
    );
}

fn assert_order_accounts(
    opening: &MaterialCircuitState,
    state: &MaterialCircuitState,
    receipts: &MaterialTickReceipts,
    fulfilled: &mut BTreeMap<OrderId, u128>,
) {
    for receipt in &receipts.local_fulfillments {
        let order = state
            .final_demand_orders
            .iter()
            .find(|row| row.order_id == receipt.order_id)
            .expect("the fixture holds the searched element");
        assert_eq!(receipt.retailer_site_id, order.retailer_site_id);
        assert_eq!(receipt.demand_principal_id, order.demand_principal_id);
        assert_eq!(
            (receipt.good_id, receipt.unit_id),
            (order.good_id, order.unit_id)
        );
        *fulfilled.entry(receipt.order_id).or_default() += u128::from(receipt.quantity);
    }
    assert_eq!(
        state.final_demand_orders.len(),
        opening.final_demand_orders.len()
    );
    for (order, prior) in state
        .final_demand_orders
        .iter()
        .zip(&opening.final_demand_orders)
    {
        assert_eq!(order.order_id, prior.order_id);
        assert_eq!(order.ordered, prior.ordered, "finite demand never renews");
        assert!(order.fulfilled <= order.ordered);
        assert_eq!(
            u128::from(order.fulfilled),
            fulfilled.get(&order.order_id).copied().unwrap_or(0),
            "the finite order is credited exactly once for each receipted handoff"
        );
    }
    for order in &state.orders {
        let transit = state
            .freight
            .iter()
            .filter(|lot| lot.order_id == order.order_id)
            .map(|lot| u128::from(lot.quantity))
            .sum::<u128>();
        assert_eq!(
            u128::from(order.shipped),
            u128::from(order.delivered) + u128::from(order.lost) + transit
        );
        assert_eq!(order.realized, order.delivered);
        assert!(order.shipped <= order.ordered);
    }
}

fn assert_opening_labor_limits(opening: &MaterialCircuitState, receipts: &MaterialTickReceipts) {
    let mut used: BTreeMap<(SiteId, UnitId), u128> = BTreeMap::new();
    for receipt in &receipts.production {
        let coefficient = opening
            .labor_coefficients
            .iter()
            .find(|row| row.process_id == receipt.process_id)
            .expect("the fixture holds the searched element");
        *used
            .entry((receipt.site_id, coefficient.unit_id))
            .or_default() +=
            u128::from(receipt.produced_batches) * u128::from(coefficient.quantity_per_batch);
    }
    for receipt in &receipts.handling {
        let merchant = opening
            .merchants
            .iter()
            .find(|row| row.site_id == receipt.site_id)
            .expect("the fixture holds the searched element");
        *used
            .entry((receipt.site_id, merchant.labor_unit_id))
            .or_default() += u128::from(receipt.used_hours);
    }
    for ((site, unit), hours) in used {
        let budget = opening
            .labor
            .iter()
            .find(|row| row.site_id == site && row.unit_id == unit && row.period == opening.period)
            .map_or(0, |row| row.available);
        assert!(
            hours <= u128::from(budget),
            "one owner shares one opening labor budget"
        );
    }
}

fn maximum_row_count(state: &MaterialCircuitState) -> usize {
    [
        state.site_logistics_nodes.len(),
        state.process_outputs.len(),
        state.input_coefficients.len(),
        state.labor_coefficients.len(),
        state.commodities.len(),
        state.supplier_routes.len(),
        state.route_stages.len(),
        state.route_stage_capacities.len(),
        state.inventory.len(),
        state.orders.len(),
        state.backlog.len(),
        state.freight.len(),
        state.corridor_capacities.len(),
        state.capacities.len(),
        state.labor.len(),
        state.production_commitments.len(),
        state.merchants.len(),
        state.handling_coefficients.len(),
        state.final_demand_principals.len(),
        state.final_demand_orders.len(),
    ]
    .into_iter()
    .max()
    .expect("the fixture call `max` succeeds for the authored inputs")
}

#[test]
fn synthetic_statewide_roster_completes_sixteen_authenticated_periods_with_native_accounting() {
    let started = Instant::now();
    let catalog = synthetic::catalog();
    assert_eq!(catalog.sites().len(), 397);
    assert_eq!(catalog.owners().len(), 397);
    assert_eq!(catalog.processes().len(), 233);
    assert_eq!(catalog.merchants().len(), 166);
    assert_eq!(catalog.final_demands().len(), 233);
    assert_eq!(catalog.staffing().pools.len(), 397);
    assert!(catalog.routes().len() > 500);
    assert!(
        CapturedEconomicCatalog::from_michigan(&catalog)
            .expect("the Michigan fixture content loads")
            .canonical_bytes()
            .len()
            < MAX_MICHIGAN_SOURCE_BYTES
    );
    let (mut session, foundation_bytes) = captured_session(&catalog);
    let compile_time = started.elapsed();
    let mut fulfilled = BTreeMap::new();
    let mut maximum_register_bytes = session.material().canonical_bytes().len();
    let mut maximum_receipt_bytes = 0;
    let mut maximum_rows = maximum_row_count(session.material().state());
    let mut dispatch_count = 0;
    let mut local_count = 0;
    let advancing = Instant::now();
    for period in 1..=16 {
        let prepared = prepare(&session);
        let bytes = prepared.material().receipt_bytes();
        assert_eq!(sha256_of(bytes), prepared.identity().receipt_digest());
        let receipts = material_world::decode_material_receipts(bytes)
            .expect("the canonical bytes decode into the declared type");
        assert_eq!(receipts.resolve_tick, period);
        let register = prepared.material().register();
        assert_eq!(
            MaterialWorldRegister::decode(register.canonical_bytes())
                .expect("the committed canonical bytes decode"),
            *register
        );
        maximum_register_bytes = maximum_register_bytes.max(register.canonical_bytes().len());
        maximum_receipt_bytes = maximum_receipt_bytes.max(bytes.len());
        maximum_rows = maximum_rows.max(maximum_row_count(register.state()));
        assert_goods_conserved(session.material().state(), register.state(), &receipts);
        assert_order_accounts(
            session.material().state(),
            register.state(),
            &receipts,
            &mut fulfilled,
        );
        assert_opening_labor_limits(session.material().state(), &receipts);
        dispatch_count += receipts.dispatches.len();
        local_count += receipts.local_transfers.len();
        session
            .commit_prepared_and_publish(&mut CollectingSink::default(), prepared, |_| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .expect("the prepared period commits");
    }
    assert!(maximum_register_bytes < MAX_MATERIAL_WORLD_REGISTER_BYTES);
    assert!(maximum_receipt_bytes < MAX_MATERIAL_TICK_RECEIPT_BYTES);
    assert!(maximum_rows < MAX_MATERIAL_CIRCUIT_ROWS);
    assert!(dispatch_count > 0 && local_count > 0 && !fulfilled.is_empty());
    let state = session.material().state();
    let unsold = unsold_merchandise(state);
    assert!(unsold.values().any(|quantity| *quantity > 0));
    let named_unsold = named_goods(&catalog, &unsold);
    let unfilled = state
        .final_demand_orders
        .iter()
        .filter(|r| r.fulfilled < r.ordered)
        .count();
    let before = session
        .current_world_hash()
        .expect("the committed session publishes a world hash");
    let actions =
        OrderedPracticeActionBatch::empty(session.graph_session().session_identity().clone(), 17)
            .expect("the empty authored batch constructs");
    assert!(session.prepare_advance(&actions).is_ok());
    assert_eq!(
        before,
        session
            .current_world_hash()
            .expect("the committed session publishes a world hash")
    );
    assert_eq!(session.completed_tick(), 16);
    eprintln!(
        "SYNTHETIC SCALE ONLY: owners=397 counties=83 processes=233 routes={} captured_bytes={} foundation_bytes={foundation_bytes} max_register_bytes={maximum_register_bytes} max_receipt_bytes={maximum_receipt_bytes} max_rows={maximum_rows} dispatches={dispatch_count} local_transfers={local_count} fulfilled_orders={} unfilled_orders={unfilled} compile_and_admit_ms={} advance_16_ms={} unsold_native_by_good={named_unsold:?}",
        catalog.routes().len(), CapturedEconomicCatalog::from_michigan(&catalog).expect("the Michigan fixture content loads").canonical_bytes().len(), fulfilled.len(),
        compile_time.as_millis(), advancing.elapsed().as_millis(),
    );
}

fn unsold_merchandise(state: &MaterialCircuitState) -> Goods {
    let merchants: BTreeMap<_, _> = state
        .merchants
        .iter()
        .map(|m| (m.site_id, m.role))
        .collect();
    let mut unsold = Goods::new();
    for row in &state.inventory {
        if matches!(
            merchants.get(&row.site_id),
            Some(MerchantRole::Wholesale | MerchantRole::Retail)
        ) {
            *unsold.entry((row.good_id, row.unit_id)).or_default() += u128::from(row.quantity);
        }
    }
    unsold
}

fn captured_session(catalog: &MichiganMaterialCatalog) -> (Session, usize) {
    let preset = MichiganContentPreset::new_campaign(MichiganDeliveryPreset::StatewideBaseline);
    let foundation = preset
        .create_foundation(catalog)
        .expect("the authored catalog builds the foundation");
    let foundation_bytes = foundation
        .canonical_len()
        .expect("the fixture call `canonical_len` succeeds for the authored inputs");
    assert!(foundation_bytes < MAX_MATERIAL_FOUNDATION_BYTES);
    assert_eq!(
        foundation
            .initial_register()
            .state()
            .final_demand_principals
            .len(),
        83
    );
    let state = foundation.initial_register().state();
    assert_eq!(state.site_logistics_nodes.len(), 397);
    assert_eq!(state.process_outputs.len(), 233);
    assert_eq!(state.merchants.len(), 166);
    assert_eq!(state.supplier_routes.len(), catalog.routes().len());
    assert_eq!(state.final_demand_orders.len(), 233);
    assert_eq!(state.labor.len(), 397);
    let admitted = economic_content::admit_economic_content(
        preset.id(),
        foundation.spec().duration,
        &foundation.spec().content_digest,
        &foundation.digest(),
        0,
        &foundation
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes"),
    )
    .expect("the fixture admits the economic content");
    assert_eq!(admitted.digest(), foundation.digest());
    let mut corrupted = foundation
        .export_canonical_bytes()
        .expect("the content exports its canonical bytes");
    *corrupted
        .last_mut()
        .expect("the fixture sequence is non-empty") ^= 1;
    assert!(economic_content::admit_economic_content(
        preset.id(),
        foundation.spec().duration,
        &foundation.spec().content_digest,
        &foundation.digest(),
        0,
        &corrupted,
    )
    .is_err());
    (
        foundation
            .into_session()
            .expect("the fixture opens a session"),
        foundation_bytes,
    )
}

fn named_goods(
    catalog: &MichiganMaterialCatalog,
    quantities: &Goods,
) -> Vec<(String, String, u128)> {
    catalog
        .goods()
        .iter()
        .filter_map(|good| {
            let quantity = quantities
                .get(&(good.id(), good.unit_id()))
                .copied()
                .unwrap_or(0);
            (quantity > 0).then(|| (good.key.clone(), good.unit_key.clone(), quantity))
        })
        .collect()
}

#[test]
fn new_reads_pinned_siblings_and_saved_open_survives_changed_or_missing_source_files() {
    use babylon_persistence::michigan_material::MichiganMaterialError;
    use babylon_persistence::MichiganDefinesError;
    let sources = SyntheticSources::create();
    let defines_path = sources.path("defines.toml");
    let delivery = MichiganDeliveryPreset::StatewideBoth;
    let preset = MichiganContentPreset::new_campaign(delivery);
    let catalog = MichiganMaterialCatalog::load_for_preset(&defines_path, delivery)
        .expect("the preset content loads");
    let selected = catalog
        .with_preset(delivery)
        .expect("the fixture builder accepts the authored options");
    assert_eq!(selected.sites().len(), 397);
    assert_eq!(
        selected
            .corridors()
            .iter()
            .find(|row| row.key == "synthetic-shared-road")
            .expect("the fixture holds the searched element")
            .capacity_grams_per_period,
        50_000_000
    );
    assert!(selected.processes().iter().any(|process| {
        process.output_good_key == "prepared_food"
            && process
                .inputs
                .iter()
                .any(|input| input.good_key == "paper_packaging" && input.opening_quantity == 0)
    }));
    let foundation = preset
        .create_foundation(&catalog)
        .expect("the authored catalog builds the foundation");
    for name in [
        "statewide-qualification.json.gz",
        "statewide-physical.json.gz",
    ] {
        let path = sources.path(name);
        let original = std::fs::read(&path).expect("the fixture reader returns its authored facts");
        let mut changed = original.clone();
        *changed
            .last_mut()
            .expect("the fixture sequence is non-empty") ^= 1;
        std::fs::write(&path, changed).expect("the fixture sink accepts the authored bytes");
        assert!(matches!(
            MichiganMaterialCatalog::load_for_preset(&defines_path, delivery),
            Err(MichiganDefinesError::Material(
                MichiganMaterialError::ArtifactDigest
            ))
        ));
        std::fs::write(path, original).expect("the fixture sink accepts the authored bytes");
    }
    // All current source files become unavailable. Open only receives the
    // admitted campaign header and its captured foundation, including overrides.
    for name in [
        "defines.toml",
        "statewide-sources.json",
        "statewide-qualification.json.gz",
        "statewide-physical.json.gz",
    ] {
        std::fs::remove_file(sources.path(name)).expect("the fixture file exists before removal");
    }
    assert!(MichiganMaterialCatalog::load_for_preset(&defines_path, delivery).is_err());
    let opened = economic_content::admit_economic_content(
        preset.id(),
        foundation.spec().duration,
        &foundation.spec().content_digest,
        &foundation.digest(),
        0,
        &foundation
            .export_canonical_bytes()
            .expect("the content exports its canonical bytes"),
    )
    .expect("the fixture admits the economic content");
    assert_eq!(opened.preset_id(), preset.id());
    assert_eq!(opened.digest(), foundation.digest());
}
