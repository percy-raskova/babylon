//! Four bounded maintenance experiments against admitted statewide content and owned `PostgreSQL`.
use super::{
    advance_pair, assert_history_and_preview, identity_hex, install_reader_role, observe,
    provision_observer_role, reopen_runtime, witnessed_output, CampaignId, CollectingSink,
    DisposableTarget, DurableMaterialRuntime, Measurements, MichiganContentPreset,
    MichiganDeliveryPreset, MichiganMaterialCatalog, NoTls, ObserverEconomyReader,
    ObserverVisibility, OrderedPracticeActionBatch, ProductionSnapshot, ReplayCommitDisposition,
    Session, SourceCopies, Uuid, MAX_MATERIAL_WORLD_REGISTER_BYTES,
    MAX_MICHIGAN_CAPTURED_CONTENT_BYTES,
};
use babylon_bsl::causal_contract::EvidenceClass;
use babylon_graph::state_hash::CanonicalState;
use babylon_material_circuit::MaintenanceReceipt;
use babylon_persistence::{
    material_runtime::MaterialRuntimeError,
    michigan_material::MichiganSiteRole,
    production_observation::{CompletedProductionMaintenance, ProductionSiteRole},
};
use babylon_tick::material_replay::MaterialCommitError;
use std::time::Instant;

const PROVIDER: &str = "owner-26163-81";
const CONSUMER: &str = "26163-31-33-metal_parts";
const INDUSTRY_SOURCE_SHA256: &str =
    "1382b5821ac95ca6f344e50f76b6846f76f841b0bc32ebf69ee8fbadc545481a";

#[derive(Clone, Copy)]
struct Case {
    preset: MichiganDeliveryPreset,
    opening_parts: u64,
    opening_employed: u64,
}
impl Case {
    fn shortage(self) -> bool {
        self.opening_parts == 0 || self.opening_employed == 0
    }
}

#[test]
#[ignore = "requires actual qualified canonical siblings and the statewide_qualified PostgreSQL focus"]
fn actual_maintenance_sources_survive_four_persisted_three_period_campaigns() {
    for (index, case) in [
        Case {
            preset: MichiganDeliveryPreset::StatewideMaintenanceBaseline,
            opening_parts: 256,
            opening_employed: 1,
        },
        Case {
            preset: MichiganDeliveryPreset::StatewideMaintenanceLaborShortage,
            opening_parts: 256,
            opening_employed: 0,
        },
        Case {
            preset: MichiganDeliveryPreset::StatewideMaintenancePartsShortage,
            opening_parts: 0,
            opening_employed: 1,
        },
        Case {
            preset: MichiganDeliveryPreset::StatewideMaintenanceBoth,
            opening_parts: 0,
            opening_employed: 0,
        },
    ]
    .into_iter()
    .enumerate()
    {
        qualify(case, u128::try_from(index).unwrap());
    }
}

fn qualify(case: Case, index: u128) {
    let began = Instant::now();
    let copies = SourceCopies::capture();
    let catalog = MichiganMaterialCatalog::load_for_preset(&copies.defines(), case.preset).expect(
        "admit the actual statewide physical sources and pinned repair-industry observation",
    );
    assert_admitted_source_and_design(&catalog, case);
    let preset = MichiganContentPreset::new_campaign(case.preset);
    let foundation = preset.create_foundation(&catalog).unwrap();
    let foundation_digest = foundation.digest();
    let twin = preset.create_foundation(&catalog).unwrap();
    assert_eq!(foundation.canonical_bytes(), twin.canonical_bytes());
    let mut reference = twin.into_session().unwrap();
    let mut measured = Measurements {
        captured_bytes: catalog.defines_bytes().len(),
        foundation_bytes: foundation.canonical_bytes().len(),
        ..Measurements::default()
    };
    assert!(measured.captured_bytes < MAX_MICHIGAN_CAPTURED_CONTENT_BYTES);
    assert!(measured.foundation_bytes < MAX_MATERIAL_WORLD_REGISTER_BYTES);
    let mut target = DisposableTarget::create();
    let campaign = CampaignId::from_uuid(Uuid::from_u128(30_100 + index));
    let mut runtime = DurableMaterialRuntime::create(&target.writer, campaign, foundation).unwrap();
    install_reader_role(&target.writer).unwrap();
    provision_observer_role(&target.writer).unwrap();
    let config = target.login("babylon_observer", "actualmaintenance");
    let observer =
        ObserverEconomyReader::connect(&config, ObserverVisibility::FullObserver).unwrap();
    let mut sql = target.writer.connect(NoTls).unwrap();
    measured.create_with_reference = began.elapsed();
    let mut held = Vec::new();
    let rows = observe(
        &observer,
        campaign,
        &runtime,
        &catalog,
        None,
        &mut measured,
        &mut held,
    );
    assert_foundation(&rows, &catalog, case);
    if index == 0 {
        assert_commit_refusal_preserves_candidate(&mut reference);
        assert_sql_marker_refusal(&mut sql, campaign, &mut runtime);
    }
    for period in 1..=3 {
        let opening_capacities = reference
            .material()
            .state()
            .corridor_capacities
            .iter()
            .filter(|row| row.period == period)
            .map(|row| {
                (
                    identity_hex(row.corridor_id.as_bytes()),
                    row.available_grams,
                )
            })
            .collect();
        let receipts = advance_pair(
            &mut runtime,
            &mut reference,
            &mut sql,
            campaign,
            &mut measured,
        );
        let rows = observe(
            &observer,
            campaign,
            &runtime,
            &catalog,
            Some((&receipts, &opening_capacities)),
            &mut measured,
            &mut held,
        );
        let maintenance = receipts
            .maintenance
            .as_ref()
            .expect("committed zero jobs remain explicit evidence");
        assert_completed(&rows, &catalog, maintenance, case, period);
        if period == 1 {
            copies.change();
        }
        if period == 2 {
            copies.remove();
        }
        assert!(MichiganMaterialCatalog::load_for_preset(&copies.defines(), case.preset).is_err());
        reopen_runtime(
            &mut runtime,
            &target,
            campaign,
            foundation_digest,
            &mut measured,
        );
        eprintln!("actual maintenance {}: period {period}/3", preset.id());
    }
    assert_history_and_preview(&observer, &mut target, campaign, &held, 3, &mut measured);
    assert_persisted_totals(&mut sql, campaign, preset.id(), &measured);
}

fn assert_persisted_totals(
    sql: &mut postgres::Client,
    campaign: CampaignId,
    preset: &str,
    measured: &Measurements,
) {
    let commits: i64 = sql
        .query_one(
            "SELECT count(*) FROM babylon_state.material_tick_v3 WHERE campaign_id=$1::uuid",
            &[campaign.as_uuid()],
        )
        .unwrap()
        .get(0);
    assert_eq!(commits, 3);
    assert!(measured.maximum_family_rows < 65_536);
    assert!(measured.maximum_register_bytes < MAX_MATERIAL_WORLD_REGISTER_BYTES);
    assert!(measured.maximum_receipt_bytes < MAX_MATERIAL_WORLD_REGISTER_BYTES);
    eprintln!("actual maintenance PostgreSQL {preset}: {measured:?}");
}

fn assert_admitted_source_and_design(catalog: &MichiganMaterialCatalog, case: Case) {
    assert_eq!(catalog.preset(), case.preset);
    assert_eq!(
        (
            catalog.sites().len(),
            catalog.owners().len(),
            catalog.staffing().pools.len()
        ),
        (398, 398, 398)
    );
    assert_eq!(
        (
            catalog.processes().len(),
            catalog.merchants().len(),
            catalog.final_demands().len()
        ),
        (233, 166, 233)
    );
    let physical = catalog.physical_network().unwrap();
    assert!(physical.source.pbf_url.starts_with("https://"));
    assert_eq!(physical.terminals.len(), 83);
    assert!(!physical.edges.is_empty());
    assert_provider_source(catalog);
    assert_eq!(catalog.physical_evidence_class(), EvidenceClass::Designed);
    assert_eq!(catalog.staffing().evidence_class, "Designed");
    let crew = catalog
        .staffing()
        .pools
        .iter()
        .find(|pool| pool.site_key == PROVIDER)
        .unwrap();
    assert!(crew.maintenance && !crew.merchant_handling && crew.process_keys.is_empty());
    assert_eq!(
        (crew.employed, crew.reserve),
        (case.opening_employed, 1 - case.opening_employed)
    );
    let maintenance = catalog.maintenance().unwrap();
    assert_eq!(maintenance.provider_site_key, PROVIDER);
    assert_eq!(maintenance.consumer_process_key, CONSUMER);
    assert_eq!(maintenance.opening_spare_parts, case.opening_parts);
    assert_eq!(
        (
            maintenance.spare_units_per_job,
            maintenance.labor_units_per_job,
            maintenance.enabled_batches_per_job,
            maintenance.maximum_jobs_per_period,
            maintenance.opening_service_batches
        ),
        (1, 10, 1, 16, 16)
    );
    let consumer = catalog
        .processes()
        .iter()
        .find(|row| row.key == CONSUMER)
        .unwrap();
    assert_eq!(
        consumer
            .inputs
            .iter()
            .find(|row| row.good_key == "metal_stock")
            .unwrap()
            .opening_quantity,
        2560
    );
    let replenishment = catalog
        .routes()
        .iter()
        .find(|row| row.key == "26163-metal-parts-maintenance-replenishment")
        .unwrap();
    assert_eq!(replenishment.ordered_quantity, 256);
    assert_eq!(replenishment.buyer_site_key, PROVIDER);
    assert_eq!(replenishment.supplier_site_key, consumer.site_key);
}

fn assert_provider_source(catalog: &MichiganMaterialCatalog) {
    let provider = catalog.site(PROVIDER).unwrap();
    assert_eq!(
        (
            provider.county_geoid.as_str(),
            provider.sector_code.as_str(),
            provider.naics.as_str()
        ),
        ("26163", "81", "811310")
    );
    assert_eq!(provider.role, MichiganSiteRole::Maintenance);
    let observed = catalog.industry_for_site(provider).unwrap();
    assert_eq!(catalog.source_evidence_class(), EvidenceClass::Observed);
    assert_eq!(observed.source_sha256, INDUSTRY_SOURCE_SHA256);
    assert_eq!(observed.annual_avg_estabs_count, 122);
    assert_eq!(observed.annual_avg_emplvl, Some(1480));
    assert_eq!(observed.total_annual_wages, Some(119_725_241));
    assert_eq!(observed.annual_avg_wkly_wage, Some(1556));
    assert_eq!(
        (
            observed.own_code.as_str(),
            observed.agglvl_code.as_str(),
            observed.disclosure_code.as_str()
        ),
        ("5", "78", "")
    );
}

fn assert_foundation(rows: &ProductionSnapshot, catalog: &MichiganMaterialCatalog, case: Case) {
    let account = rows.maintenance_account.as_ref().unwrap();
    assert!(account.completed.is_none());
    assert_eq!(
        (account.next_service_period, account.next_service_batches),
        (1, 16)
    );
    assert_eq!(
        (
            account.spare_unit.as_str(),
            account.labor_unit.as_str(),
            account.output_unit.as_str()
        ),
        ("kg", "labor-hours", "kg")
    );
    let provider = rows
        .sites
        .iter()
        .find(|site| site.id == account.provider_site_id)
        .unwrap();
    assert_eq!(provider.role, ProductionSiteRole::Maintenance);
    assert!(provider.processes.is_empty());
    assert_eq!(provider.observed_employment, Some(1480));
    assert_eq!(
        provider.id,
        identity_hex(catalog.site(PROVIDER).unwrap().id().as_bytes())
    );
    let crew = rows
        .staffing_accounts
        .iter()
        .find(|row| row.site_id == provider.id)
        .unwrap();
    assert_eq!(
        (crew.employed, crew.reserve, crew.labor_force),
        (case.opening_employed, 1 - case.opening_employed, 1)
    );
    assert_eq!(crew.next_opening_hours, case.opening_employed * 160);
    let parts = provider
        .inventory
        .iter()
        .find(|row| row.good_id == account.spare_good_id)
        .map_or(0, |row| row.quantity);
    assert_eq!(parts, case.opening_parts);
}

fn assert_completed(
    rows: &ProductionSnapshot,
    catalog: &MichiganMaterialCatalog,
    receipt: &MaintenanceReceipt,
    case: Case,
    period: u64,
) {
    let account = rows.maintenance_account.as_ref().unwrap();
    assert_eq!(
        account.provider_site_id,
        identity_hex(receipt.binding.provider_site_id.as_bytes())
    );
    assert_eq!(
        account.consumer_process_id,
        identity_hex(receipt.binding.consumer_process_id.as_bytes())
    );
    assert_eq!(
        account.spare_good_id,
        identity_hex(receipt.binding.spare_good_id.as_bytes())
    );
    assert_eq!(
        account.spare_unit_id,
        identity_hex(receipt.binding.spare_unit_id.as_bytes())
    );
    assert_eq!(
        account.labor_unit_id,
        identity_hex(receipt.binding.labor_unit_id.as_bytes())
    );
    assert_eq!(
        (account.next_service_period, account.next_service_batches),
        (period + 1, receipt.next_service.available_batches)
    );
    assert_eq!(
        account.completed,
        Some(CompletedProductionMaintenance {
            period: receipt.period,
            opening_service_batches: receipt.opening_service_batches,
            consumed_service_batches: receipt.consumed_service_batches,
            expired_service_batches: receipt.expired_service_batches,
            prospective_batches: receipt.prospective_batches,
            requested_jobs: receipt.requested_jobs,
            opening_spare_parts: receipt.opening_spare_parts,
            arrived_spare_parts: receipt.arrived_spare_parts,
            available_spare_parts: receipt.available_spare_parts,
            available_labor_hours: receipt.available_labor_hours,
            completed_jobs: receipt.completed_jobs,
            consumed_spare_parts: receipt.consumed_spare_parts,
            consumed_labor_hours: receipt.consumed_labor_hours,
        })
    );
    let output = witnessed_output(rows, catalog, CONSUMER, "kg");
    assert_period_witness(output, receipt, case, period);
    assert_eq!(receipt.consumed_spare_parts, receipt.completed_jobs);
    assert_eq!(receipt.consumed_labor_hours, receipt.completed_jobs * 10);
    assert_eq!(
        receipt.next_service.available_batches,
        receipt.completed_jobs
    );
    assert_eq!(receipt.consumed_service_batches * 60, output);
    assert_eq!(
        receipt.consumed_service_batches + receipt.expired_service_batches,
        receipt.opening_service_batches
    );
    assert!(receipt.completed_jobs <= receipt.requested_jobs && receipt.completed_jobs <= 16);
    assert_provider_accounts(rows, receipt, period);
}

fn assert_period_witness(output: u64, receipt: &MaintenanceReceipt, case: Case, period: u64) {
    if period == 1 {
        assert_eq!(receipt.requested_jobs, 16);
        assert_eq!(receipt.completed_jobs, if case.shortage() { 0 } else { 16 });
        assert_eq!(receipt.available_spare_parts, case.opening_parts);
        assert_eq!(receipt.available_labor_hours, case.opening_employed * 160);
        assert_eq!(output, 960);
    } else if period == 2 {
        assert_eq!(output, if case.shortage() { 0 } else { 960 });
        if case.shortage() {
            assert_eq!(receipt.completed_jobs, 16);
        }
    } else if case.shortage() {
        assert_eq!(output, 960);
    }
}

fn assert_provider_accounts(rows: &ProductionSnapshot, receipt: &MaintenanceReceipt, period: u64) {
    let account = rows.maintenance_account.as_ref().unwrap();
    let stock = rows
        .material_balance
        .as_ref()
        .unwrap()
        .rows
        .iter()
        .find(|row| {
            row.site_id == account.provider_site_id
                && row.good_id == account.spare_good_id
                && row.unit_id == account.spare_unit_id
        })
        .unwrap();
    assert_eq!(stock.opening, receipt.opening_spare_parts);
    assert_eq!(stock.arrivals, receipt.arrived_spare_parts);
    assert_eq!(stock.maintenance_consumed, receipt.consumed_spare_parts);
    assert_eq!(
        (
            stock.consumed,
            stock.produced,
            stock.dispatched,
            stock.local_transferred,
            stock.final_demand_fulfilled
        ),
        (0, 0, 0, 0, 0)
    );
    if period == 1 {
        assert_eq!(
            stock.local_received, 60,
            "finite 256kg maintenance order competes with 3840kg wholesale order"
        );
    }
    assert_eq!(
        stock.closing,
        stock.opening + stock.arrivals + stock.local_received - stock.maintenance_consumed
    );
    let labor = rows
        .labor_accounts
        .iter()
        .find(|row| row.site_id == account.provider_site_id)
        .unwrap()
        .completed
        .as_ref()
        .unwrap();
    assert_eq!(
        (
            labor.opening,
            labor.maintenance_needed,
            labor.maintenance_used
        ),
        (
            receipt.available_labor_hours,
            receipt.requested_jobs * 10,
            receipt.consumed_labor_hours
        )
    );
    assert_eq!(labor.used, labor.maintenance_used);
    assert_eq!(labor.used + labor.unused, labor.opening);
    assert_eq!((labor.handling_needed, labor.handling_used), (0, 0));
    if period == 1 {
        let crew = rows
            .staffing_accounts
            .iter()
            .find(|row| row.site_id == account.provider_site_id)
            .unwrap();
        assert_eq!(
            (crew.employed, crew.reserve, crew.next_opening_hours),
            (1, 0, 160)
        );
    }
}

fn assert_commit_refusal_preserves_candidate(reference: &mut Session) {
    // Reuse the public commit callback seam from tests/material_runtime.rs;
    // this proves candidate publication atomicity, not an injected SQL failure.
    let graph = reference.graph_session().graph().state_hash().unwrap();
    let register = reference.material().canonical_bytes().to_vec();
    let world = reference.current_world_hash().unwrap();
    let actions =
        OrderedPracticeActionBatch::empty(reference.graph_session().session_identity().clone(), 1)
            .unwrap();
    let candidate = reference.prepare_advance(&actions).unwrap();
    let bytes = candidate.material().receipt_bytes().to_vec();
    let digest = candidate.identity().tick_content_hash();
    let mut sink = CollectingSink::default();
    let refused = reference.commit_prepared_and_publish(&mut sink, candidate, |_| {
        Err::<ReplayCommitDisposition, _>("refused before marker")
    });
    assert!(matches!(
        refused,
        Err(MaterialCommitError::Commit("refused before marker"))
    ));
    assert_eq!(reference.completed_tick(), 0);
    assert_eq!(reference.material().canonical_bytes(), register);
    assert_eq!(
        reference.graph_session().graph().state_hash().unwrap(),
        graph
    );
    assert_eq!(reference.current_world_hash().unwrap(), world);
    assert!(sink.events.is_empty());
    let retry = reference.prepare_advance(&actions).unwrap();
    assert_eq!(retry.identity().tick_content_hash(), digest);
    assert_eq!(retry.material().receipt_bytes(), bytes);
}

fn assert_sql_marker_refusal(
    owner: &mut postgres::Client,
    campaign: CampaignId,
    runtime: &mut DurableMaterialRuntime,
) {
    // SHARE permits schema/tail reads and foreign-key row locks, but refuses the
    // final marker INSERT's ROW EXCLUSIVE lock after all candidate rows are written.
    // Reuse the writer's bounded lock refusal without changing the schema census.
    assert_eq!(runtime.session().completed_tick(), 0);
    let graph = runtime
        .session()
        .graph_session()
        .graph()
        .state_hash()
        .unwrap();
    let material = runtime.session().material().canonical_bytes().to_vec();
    let world = runtime.session().current_world_hash().unwrap();
    let actions = OrderedPracticeActionBatch::empty(
        runtime.session().graph_session().session_identity().clone(),
        1,
    )
    .unwrap();
    let mut sink = CollectingSink::default();
    let mut blocker = owner.transaction().unwrap();
    blocker
        .batch_execute("LOCK TABLE babylon_state.tick_commit IN SHARE MODE")
        .unwrap();
    let refused = runtime.advance_and_commit(&mut sink, &actions);
    blocker.rollback().unwrap();
    let error = refused.expect_err("the final marker INSERT must honor the writer lock timeout");
    let MaterialRuntimeError::DatabaseLockRefused(error) = error else {
        panic!("expected late marker SQL lock refusal, got {error:?}");
    };
    let database = error
        .as_db_error()
        .expect("server-side marker lock refusal");
    assert_eq!(
        database.code(),
        &postgres::error::SqlState::LOCK_NOT_AVAILABLE
    );
    assert_eq!(
        database.message(),
        "canceling statement due to lock timeout"
    );
    assert_eq!(runtime.session().completed_tick(), 0);
    assert_eq!(runtime.session().graph_session().completed_tick(), 0);
    assert_eq!(runtime.session().current_world_hash().unwrap(), world);
    assert_eq!(runtime.session().material().canonical_bytes(), material);
    assert_eq!(
        runtime
            .session()
            .graph_session()
            .graph()
            .state_hash()
            .unwrap(),
        graph
    );
    assert!(runtime.tail().is_none());
    assert!(sink.events.is_empty());
    assert_no_maintenance_tick_rows(owner, campaign);
    // The existing advance_pair immediately below this call retries the same
    // opening and compares durable register/receipt bytes with the untouched twin.
}

fn assert_no_maintenance_tick_rows(owner: &mut postgres::Client, campaign: CampaignId) {
    // Exact per-tick tables written by the shared marker-last persistence path.
    // Foundation rows, if present at tick zero, remain outside the failed close.
    for table in [
        "tick_commit",
        "material_tick_v3",
        "world_register_v1",
        "archive_dirty_receipt_v1",
        "tick_action_batch_v1",
        "graph_node_v1",
        "graph_node_f64_v1",
        "graph_node_currency_v1",
        "graph_edge_v1",
        "graph_edge_f64_v1",
        "graph_hyperedge_v1",
        "graph_hyperedge_member_v1",
        "graph_hyperedge_f64_v1",
        "hex_state_delta_v1",
        "territory_state_v1",
        "territory_state_field_v1",
        "organization_state_v1",
        "organization_state_field_v1",
        "organization_territory_v1",
        "tick_choice_receipt_v1",
        "tick_choice_receipt_branch_v1",
        "tick_choice_receipt_carrier_element_v1",
        "tick_event_v2",
        "tick_event_field_v2",
        "checkpoint_manifest",
        "checkpoint_section_v1",
    ] {
        let count: i64 = owner.query_one(
            &format!("SELECT count(*) FROM babylon_state.{table} WHERE campaign_id=$1::uuid AND resolve_tick>0"),
            &[campaign.as_uuid()],
        ).unwrap().get(0);
        assert_eq!(count, 0, "maintenance pre-marker rollback {table}");
    }
    let catalog_tick: i64 = owner
        .query_one(
            "SELECT last_tick FROM babylon_meta.campaign WHERE campaign_id=$1::uuid",
            &[campaign.as_uuid()],
        )
        .unwrap()
        .get(0);
    assert_eq!(catalog_tick, 0);
}
