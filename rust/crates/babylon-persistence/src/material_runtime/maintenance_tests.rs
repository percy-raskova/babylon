//! Captured Designed maintenance crosses the real BSL and saved checkpoint boundaries.
use super::reconstruction_tests::{persisted_graph_copy, stored_copy};
use super::*;
use crate::michigan_material::{MichiganDeliveryPreset, MichiganMaterialCatalog};
use babylon_material_circuit::{GoodId, OrderId, ProcessId, SiteId};
use babylon_tick::material_replay::{MaterialCommitError, PreparedMaterialTick};
use babylon_tick::material_world::{
    decode_material_receipts, MaterialTickReceipts, MaterialWorldRegister,
};

#[path = "../../tests/fixtures/statewide_synthetic.rs"]
mod synthetic;

type Session = MaterialReplaySession<HypergraphStore>;
type Candidate = PreparedMaterialTick<HypergraphStore>;

#[derive(Clone, Copy)]
struct Case {
    delivery: MichiganDeliveryPreset,
    employed: u64,
    opening_parts: u64,
}
impl Case {
    fn constrained(self) -> bool {
        self.employed == 0 || self.opening_parts == 0
    }
}
struct Witness {
    provider: SiteId,
    process: ProcessId,
    spares: GoodId,
    restock: OrderId,
}

fn captured_catalog() -> MichiganMaterialCatalog {
    // Real source-qualified owners on explicitly synthetic paths. The live
    // qualification separately proves the real network's exact 60 kg grant.
    let sources = synthetic::SyntheticSources::create();
    let catalog = MichiganMaterialCatalog::load_for_preset(
        &sources.path("defines.toml"),
        MichiganDeliveryPreset::StatewideMaintenanceBaseline,
    )
    .unwrap();
    for name in [
        "defines.toml",
        "statewide-qualification.json.gz",
        "statewide-physical.json.gz",
        "statewide-sources.json",
    ] {
        std::fs::remove_file(sources.path(name)).unwrap();
    }
    let original = synthetic::catalog();
    assert_eq!(original.sites().len(), 397);
    assert!(original.maintenance().is_none());
    assert_eq!(original.goods(), catalog.goods());
    assert_eq!(original.merchants(), catalog.merchants());
    assert_eq!(original.rule_source(), catalog.rule_source());
    let provider = catalog.site("owner-26163-81").unwrap();
    let observed = catalog.industry_for_site(provider).unwrap();
    assert_eq!(observed.industry_code, "811310");
    assert_eq!(
        (observed.annual_avg_estabs_count, observed.annual_avg_emplvl),
        (122, Some(1480))
    );
    assert_eq!(
        (observed.total_annual_wages, observed.annual_avg_wkly_wage),
        (Some(119_725_241), Some(1556))
    );
    assert_eq!(
        (
            catalog.sites().len(),
            catalog.processes().len(),
            catalog.merchants().len()
        ),
        (398, 233, 166)
    );
    assert!(catalog
        .processes()
        .iter()
        .all(|p| p.site_key != provider.key));
    catalog
}

fn opening_witness(
    catalog: &MichiganMaterialCatalog,
    case: Case,
    foundation: &MaterialRuntimeFoundation,
) -> Witness {
    let provider = catalog.site("owner-26163-81").unwrap();
    let seed = catalog
        .staffing()
        .pools
        .iter()
        .find(|s| s.site_key == provider.key)
        .unwrap();
    assert_eq!(
        (seed.employed, seed.reserve, seed.previous_unretained_hours),
        (case.employed, 1 - case.employed, case.employed * 160)
    );
    assert!(seed.maintenance && !seed.merchant_handling && seed.process_keys.is_empty());
    let process = catalog
        .processes()
        .iter()
        .find(|p| p.key == "26163-31-33-metal_parts")
        .unwrap();
    let consumer = catalog.site(&process.site_key).unwrap().id();
    let stock = catalog.good("metal_stock").unwrap();
    let spares = catalog.good("metal_parts").unwrap();
    let initial = foundation.initial_register().state();
    let binding = initial.maintenance_binding.as_ref().unwrap();
    assert_eq!(
        (binding.provider_site_id, binding.consumer_process_id),
        (provider.id(), process.id())
    );
    assert_eq!(
        (binding.spare_good_id, binding.spare_unit_id),
        (spares.id(), spares.unit_id())
    );
    assert_eq!(
        initial
            .maintenance_service
            .as_ref()
            .unwrap()
            .available_batches,
        16
    );
    assert_eq!(
        initial
            .inventory
            .iter()
            .find(|r| r.site_id == consumer && r.good_id == stock.id())
            .unwrap()
            .quantity,
        2560
    );
    assert_eq!(
        initial
            .inventory
            .iter()
            .find(|r| r.site_id == provider.id() && r.good_id == spares.id())
            .unwrap()
            .quantity,
        case.opening_parts
    );
    let order = initial
        .orders
        .iter()
        .find(|r| r.buyer_site_id == provider.id())
        .unwrap();
    assert_eq!(
        (order.supplier_site_id, order.good_id, order.ordered),
        (consumer, spares.id(), 256)
    );
    Witness {
        provider: provider.id(),
        process: process.id(),
        spares: spares.id(),
        restock: order.order_id,
    }
}

fn assert_close(candidate: &Candidate, case: Case, witness: &Witness, period: u64) {
    assert_eq!(
        candidate.graph_report().report().per_rule_fired,
        [("material/period".to_owned(), 1)]
    );
    let receipts = decode_material_receipts(candidate.material().receipt_bytes()).unwrap();
    let maintenance = receipts.maintenance.as_ref().unwrap();
    // No commitment has no production receipt; the maintained process is still
    // present and its physical output is zero. Bound maintenance always receipts.
    let output = receipts
        .production
        .iter()
        .find(|r| r.process_id == witness.process)
        .map_or(0, |r| r.produced_batches * 60);
    let closing = candidate.material().register().state();
    let order = closing
        .orders
        .iter()
        .find(|r| r.order_id == witness.restock)
        .unwrap();
    assert_eq!(order.ordered, 256, "replenishment demand remains finite");
    if period == 1 {
        assert_eq!(output, 960);
        assert_eq!(
            (maintenance.requested_jobs, maintenance.completed_jobs),
            (16, if case.constrained() { 0 } else { 16 })
        );
        assert_eq!(
            (
                maintenance.opening_spare_parts,
                maintenance.arrived_spare_parts,
                maintenance.available_labor_hours
            ),
            (case.opening_parts, 0, case.employed * 160)
        );
        assert!(
            order.delivered >= 16 && order.delivered <= 256,
            "finite competing grant must permit the next close"
        );
        assert_eq!(
            closing
                .inventory
                .iter()
                .find(|r| r.site_id == witness.provider && r.good_id == witness.spares)
                .unwrap()
                .quantity,
            case.opening_parts - maintenance.consumed_spare_parts + order.delivered
        );
        assert_eq!(
            closing
                .labor
                .iter()
                .find(|r| r.site_id == witness.provider && r.period == 2)
                .unwrap()
                .available,
            160
        );
    } else if period == 2 {
        assert_eq!(output, if case.constrained() { 0 } else { 960 });
        if case.constrained() {
            assert_eq!(maintenance.completed_jobs, 16);
        }
    } else if case.constrained() {
        assert_eq!(
            output, 960,
            "recovery does not restore the lost period-2 output"
        );
    }
}

fn failed_commit_retry(
    session: &mut Session,
    candidate: Candidate,
    actions: &OrderedPracticeActionBatch,
    sink: &mut CollectingSink,
) -> Candidate {
    let opening = session.material().canonical_bytes().to_vec();
    let graph = session.graph_session().stable_graph_state().unwrap();
    let hash = session.current_world_hash().unwrap();
    let identity = *candidate.identity();
    let physical = candidate.material().register().clone();
    let receipts = candidate.material().receipt_bytes().to_vec();
    assert!(matches!(
        session.commit_prepared_and_publish(
            sink,
            candidate,
            |_| Err::<ReplayCommitDisposition, _>("refused")
        ),
        Err(MaterialCommitError::Commit("refused"))
    ));
    assert_eq!(session.completed_tick(), 0);
    assert_eq!(session.material().canonical_bytes(), opening);
    assert_eq!(session.graph_session().stable_graph_state().unwrap(), graph);
    assert_eq!(session.current_world_hash().unwrap(), hash);
    assert!(sink.events.is_empty());
    let retry = session.prepare_advance(actions).unwrap();
    assert_eq!(retry.identity(), &identity);
    assert_eq!(retry.material().register(), &physical);
    assert_eq!(retry.material().receipt_bytes(), receipts);
    retry
}

fn assert_full_projection(
    catalog: &MichiganMaterialCatalog,
    register: &MaterialWorldRegister,
    opening: Option<&MaterialWorldRegister>,
    history: &[(MaterialTickReceipts, [u8; 32])],
) {
    use crate::production_observation::ProductionSiteRole;
    let snapshot = crate::production_projection::project_material_observation(
        catalog,
        catalog.preset(),
        register,
        opening,
        history,
    )
    .expect("the full observer must admit the maintenance provider and all merchant accounts");
    let maintenance = snapshot.maintenance_account.as_ref().unwrap();
    let provider = snapshot
        .sites
        .iter()
        .find(|site| site.id == maintenance.provider_site_id)
        .unwrap();
    assert_eq!(provider.role, ProductionSiteRole::Maintenance);
    assert!(provider.processes.is_empty());
    assert_eq!(provider.observed_employment, Some(1480));
    assert_eq!(snapshot.sites.len(), catalog.sites().len());
    assert_eq!(
        snapshot.merchant_handling_accounts.len(),
        catalog.merchants().len()
    );
    assert!(!snapshot
        .merchant_handling_accounts
        .iter()
        .any(|account| account.site_id == provider.id));
    assert_eq!(
        maintenance
            .completed
            .as_ref()
            .map(|done| done.completed_jobs),
        history
            .last()
            .map(|(receipt, _)| receipt.maintenance.as_ref().unwrap().completed_jobs),
        "zero and positive service completion remain visible through the full projection"
    );
}

fn qualify_case(base: &MichiganMaterialCatalog, case: Case) {
    let catalog = base.with_preset(case.delivery).unwrap();
    assert_eq!(
        catalog.graph_scenario_source() == base.graph_scenario_source(),
        case.employed == 1
    );
    let preset = crate::michigan_content::MichiganContentPreset::new_campaign(case.delivery);
    let foundation = preset.create_foundation(&catalog).unwrap();
    let witness = opening_witness(&catalog, case, &foundation);
    let mut restored = reconstruct_material_foundation(
        stored_copy(&foundation),
        persisted_graph_copy(foundation.graph_foundation()),
        foundation.digest(),
    )
    .unwrap()
    .into_session()
    .unwrap();
    let mut uninterrupted = foundation.into_session().unwrap();
    let mut sink = CollectingSink::default();
    let mut replay_sink = CollectingSink::default();
    let mut history = Vec::new();
    assert_full_projection(&catalog, uninterrupted.material(), None, &history);
    for period in 1..=3 {
        let actions = OrderedPracticeActionBatch::empty(
            uninterrupted.graph_session().session_identity().clone(),
            period,
        )
        .unwrap();
        let mut candidate = uninterrupted.prepare_advance(&actions).unwrap();
        assert_close(&candidate, case, &witness, period);
        history.push((
            decode_material_receipts(candidate.material().receipt_bytes()).unwrap(),
            candidate.identity().receipt_digest(),
        ));
        assert_full_projection(
            &catalog,
            candidate.material().register(),
            Some(uninterrupted.material()),
            &history,
        );
        if period == 1 {
            candidate = failed_commit_retry(&mut uninterrupted, candidate, &actions, &mut sink);
            let graph = candidate.graph_report();
            restored
                .restore_full_checkpoint(
                    graph.result_stable_graph(),
                    graph.material_state_rows(),
                    graph.result_registers().canonical_bytes(),
                    candidate.material().register().canonical_bytes(),
                )
                .unwrap();
        } else {
            let replay = restored.prepare_advance(&actions).unwrap();
            assert_eq!(replay.identity(), candidate.identity());
            assert_eq!(
                replay.material().receipt_bytes(),
                candidate.material().receipt_bytes()
            );
            assert_eq!(
                replay.graph_report().successful_event_batch(),
                candidate.graph_report().successful_event_batch()
            );
            assert_eq!(
                replay.graph_report().report().audit_receipts,
                candidate.graph_report().report().audit_receipts
            );
            restored
                .commit_prepared_and_publish(&mut replay_sink, replay, |_| {
                    Ok::<_, ()>(ReplayCommitDisposition::Committed)
                })
                .unwrap();
        }
        uninterrupted
            .commit_prepared_and_publish(&mut sink, candidate, |_| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .unwrap();
        assert_eq!(restored.material(), uninterrupted.material());
        assert_eq!(
            restored.current_world_hash().unwrap(),
            uninterrupted.current_world_hash().unwrap()
        );
    }
}

#[test]
fn maintenance_matrix_preserves_causal_loss_recovery_atomicity_and_saved_restart() {
    let base = captured_catalog();
    for (delivery, employed, opening_parts) in [
        (MichiganDeliveryPreset::StatewideMaintenanceBaseline, 1, 256),
        (
            MichiganDeliveryPreset::StatewideMaintenanceLaborShortage,
            0,
            256,
        ),
        (
            MichiganDeliveryPreset::StatewideMaintenancePartsShortage,
            1,
            0,
        ),
        (MichiganDeliveryPreset::StatewideMaintenanceBoth, 0, 0),
    ] {
        qualify_case(
            &base,
            Case {
                delivery,
                employed,
                opening_parts,
            },
        );
    }
}
