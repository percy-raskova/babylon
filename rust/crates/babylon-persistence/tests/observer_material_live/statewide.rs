//! Full-size persisted accounting on explicitly synthetic transport geometry.
//! Real road and intervention qualification remain separate acceptance evidence.

use super::{
    CampaignId, DisposableTarget, DurableMaterialRuntime, MichiganContentPreset,
    MichiganDeliveryPreset, ObserverEconomyReader, ObserverVisibility, Uuid,
};
use babylon_persistence::observer_reader::ObserverEconomySnapshot;
use babylon_persistence::production_observation::ProductionSnapshot;

use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_persistence::michigan_material::MichiganMaterialCatalog;
use babylon_tick::material_replay::MaterialReplaySession;
use std::collections::BTreeSet;
use std::time::Duration;
use std::time::Instant;
use synthetic::SyntheticSources;

#[path = "../fixtures/statewide_synthetic.rs"]
mod synthetic;

fn assert_projection(snapshot: &mut ObserverEconomySnapshot, runtime: &DurableMaterialRuntime) {
    assert_eq!(snapshot.resolve_tick, runtime.session().completed_tick());
    assert!(snapshot
        .production_evidence_digest()
        .expect("the evidence body has a digest")
        .is_some());
    let rows = snapshot
        .production
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert_eq!(rows.sites.len(), 397);
    assert_eq!(
        rows.sites
            .iter()
            .filter_map(babylon_persistence::production_observation::ProductionSite::county_geoid)
            .collect::<BTreeSet<_>>()
            .len(),
        83
    );
    assert_eq!(
        rows.sites
            .iter()
            .map(|site| site.processes.len())
            .sum::<usize>(),
        233
    );
    assert_eq!(rows.merchant_handling_accounts.len(), 166);
    assert_eq!(rows.staffing_accounts.len(), 397);
    assert_eq!(rows.labor_accounts.len(), 397);
    assert!(rows
        .road_source
        .as_ref()
        .expect("the fixture set the optional field before this read")
        .pbf_url
        .starts_with("synthetic://"));
    let mut pools = BTreeSet::new();
    for pool in &rows.staffing_accounts {
        assert!(pools.insert(&pool.pool_id));
        assert_eq!(pool.employed + pool.reserve, pool.labor_force);
    }
    for account in &rows.labor_accounts {
        if let Some(done) = &account.completed {
            assert_eq!(done.used + done.unused, done.opening);
            assert!(done.handling_used <= done.used);
        }
    }
    assert_final_orders(rows, runtime);
    if snapshot.resolve_tick == 0 {
        assert!(rows.material_balance.is_none());
        assert!(rows
            .merchant_handling_accounts
            .iter()
            .all(|row| row.completed.is_none()));
    } else {
        assert_stock_accounts(rows, snapshot.resolve_tick);
    }
}

fn assert_final_orders(rows: &ProductionSnapshot, runtime: &DurableMaterialRuntime) {
    let mut orders = BTreeSet::new();
    let state = runtime.session().material().state();
    for account in &rows.final_demand_accounts {
        assert_eq!(account.fulfilled + account.outstanding, account.ordered);
        assert_eq!(
            account.fulfilled,
            account
                .orders
                .iter()
                .map(|order| order.fulfilled)
                .sum::<u64>()
        );
        for order in &account.orders {
            assert!(orders.insert(&order.order_id));
            let committed = state
                .final_demand_orders
                .iter()
                .find(|row| super::identity_hex(row.order_id.as_bytes()) == order.order_id)
                .expect("the fixture holds the searched element");
            assert_eq!(order.fulfilled, committed.fulfilled);
            assert_eq!(order.ordered, committed.ordered);
        }
    }
    assert_eq!(orders.len(), 233);
}

fn assert_stock_accounts(rows: &ProductionSnapshot, period: u64) {
    let balance = rows
        .material_balance
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert_eq!(balance.period, period);
    let mut principals = BTreeSet::new();
    for row in &balance.rows {
        assert!(principals.insert((&row.site_id, &row.good_id, &row.unit_id)));
        assert_eq!(
            u128::from(row.opening)
                + u128::from(row.arrivals)
                + u128::from(row.local_received)
                + u128::from(row.produced),
            u128::from(row.consumed)
                + u128::from(row.dispatched)
                + u128::from(row.local_transferred)
                + u128::from(row.final_demand_fulfilled)
                + u128::from(row.closing),
        );
        let site = rows
            .sites
            .iter()
            .find(|site| site.id == row.site_id)
            .expect("the fixture holds the searched element");
        let closing = site
            .inventory
            .iter()
            .find(|stock| stock.good_id == row.good_id && stock.unit_id == row.unit_id)
            .map_or(0, |stock| stock.quantity);
        assert_eq!(row.closing, closing);
    }
}

fn assert_same_world(left: &DurableMaterialRuntime, right: &DurableMaterialRuntime) {
    assert_eq!(left.tail(), right.tail());
    assert_eq!(
        left.session().material().canonical_bytes(),
        right.session().material().canonical_bytes()
    );
    assert_eq!(
        left.session()
            .current_world_hash()
            .expect("the committed session publishes a world hash"),
        right
            .session()
            .current_world_hash()
            .expect("the committed session publishes a world hash")
    );
}

#[test]
#[ignore = "requires the owned PostgreSQL harness; synthetic full-roster circulation proof"]
#[allow(
    clippy::too_many_lines,
    reason = "`statewide_synthetic_circulation_survives_sixteen_persisted_periods_and_held_history` keeps one authored boundary's fixture and assertions together"
)]
fn statewide_synthetic_circulation_survives_sixteen_persisted_periods_and_held_history() {
    let mut target = DisposableTarget::create();
    let start = Instant::now();
    let sources = SyntheticSources::create();
    let catalog = MichiganMaterialCatalog::load_for_preset(
        &sources.path("defines.toml"),
        MichiganDeliveryPreset::StatewideBaseline,
    )
    .expect("the preset content loads");
    let foundation = MichiganContentPreset::new_campaign(MichiganDeliveryPreset::StatewideBaseline)
        .create_foundation(&catalog)
        .expect("the authored catalog builds the foundation");
    let foundation_digest = foundation.digest();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(29_701));
    let mut runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation)
        .expect("the test database creates the fixture campaign");
    let reference_foundation =
        MichiganContentPreset::new_campaign(MichiganDeliveryPreset::StatewideBaseline)
            .create_foundation(&synthetic::catalog())
            .expect("the authored catalog builds the foundation");
    let mut reference = reference_foundation
        .into_session()
        .expect("the fixture opens a session");
    // Saved PostgreSQL authority must outlive every current input file.
    drop(sources);
    super::install_reader_role(&target.writer).expect("the test database installs the reader role");
    super::provision_observer_role(&target.writer)
        .expect("the test database provisions the observer role");
    let config = target.login("babylon_observer", "statewidescale");
    let observer = ObserverEconomyReader::connect(&config, ObserverVisibility::FullObserver)
        .expect("the test database accepts the connection");
    let creation = start.elapsed();
    let mut held = Vec::new();
    let mut advance_time = Duration::ZERO;
    let mut projection_time = Duration::ZERO;
    let mut resume_time = Duration::ZERO;
    for period in 0..=16 {
        if period > 0 {
            let began = Instant::now();
            super::advance_material_period(&mut runtime);
            advance_reference(&mut reference);
            advance_time += began.elapsed();
            assert_eq!(
                runtime.session().material().canonical_bytes(),
                reference.material().canonical_bytes()
            );
            assert_eq!(
                runtime
                    .session()
                    .current_world_hash()
                    .expect("the committed session publishes a world hash"),
                reference
                    .current_world_hash()
                    .expect("the committed session publishes a world hash")
            );
        }
        let began = Instant::now();
        let mut snapshot = observer
            .snapshot(campaign, period)
            .unwrap_or_else(|error| panic!("statewide observation period {period}: {error:?}"));
        projection_time += began.elapsed();
        assert_projection(&mut snapshot, &runtime);
        if [0, 1, 2, 8, 16].contains(&period) {
            held.push(snapshot.clone());
        }
        if [1, 2, 16].contains(&period) {
            let began = Instant::now();
            let reopened =
                DurableMaterialRuntime::open(&target.writer, campaign, foundation_digest)
                    .expect("the fixture opens the authored source");
            resume_time += began.elapsed();
            assert_same_world(&runtime, &reopened);
            runtime = reopened;
        }
    }
    for snapshot in &held {
        let mut reopened = observer
            .snapshot(campaign, snapshot.resolve_tick)
            .expect("the fixture captures a consistent snapshot");
        assert!(reopened
            .production_evidence_digest()
            .expect("the evidence body has a digest")
            .is_some());
        assert_eq!(reopened, *snapshot);
    }
    let final_rows = held
        .last()
        .expect("the fixture sequence is non-empty")
        .production
        .as_ref()
        .expect("the fixture set the optional field before this read");
    assert!(final_rows
        .final_demand_accounts
        .iter()
        .any(|row| row.fulfilled > 0));
    assert!(final_rows
        .final_demand_accounts
        .iter()
        .any(|row| row.retail_stock_on_hand > 0));
    assert_eq!(
        observer
            .campaigns()
            .expect("the fixture lists the authored campaigns")[0]
            .durable_tick,
        16
    );
    let preview_config = target.login("babylon_reader", "statewidepreview");
    let preview = ObserverEconomyReader::connect(&preview_config, ObserverVisibility::KnownPreview)
        .expect("the test database accepts the connection");
    let mut restricted = preview
        .snapshot(campaign, 16)
        .expect("the fixture captures a consistent snapshot");
    assert!(restricted.production.is_none());
    assert!(restricted
        .production_evidence_digest()
        .expect("the evidence body has a digest")
        .is_none());
    eprintln!("synthetic statewide PostgreSQL: creation={creation:?}, advance16_with_reference={advance_time:?}, projection17={projection_time:?}, resume3={resume_time:?}");
}

fn advance_reference(reference: &mut MaterialReplaySession<HypergraphStore>) {
    use babylon_bsl::structural_verbs::CollectingSink;
    use babylon_practice_contract::OrderedPracticeActionBatch;
    use babylon_tick::replay_session::ReplayCommitDisposition;
    let actions = OrderedPracticeActionBatch::empty(
        reference.graph_session().session_identity().clone(),
        reference.completed_tick() + 1,
    )
    .expect("the empty authored batch constructs");
    let prepared = reference
        .prepare_advance(&actions)
        .expect("the session prepares the authored advance");
    reference
        .commit_prepared_and_publish(&mut CollectingSink::default(), prepared, |_, _| {
            Ok::<_, ()>(ReplayCommitDisposition::Committed)
        })
        .expect("the prepared period commits");
}
