//! Real national finite-kernel decisions bind the following material close and its first cold restart.
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::{CompanyPortfolioRegister, ProcessId, SiteId};
use babylon_persistence::economic_catalog::{self, CapturedEconomicCatalog};
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_replay::{MaterialReplaySession, PreparedMaterialTick};
use babylon_tick::material_world::MaterialWorldRegister;
use babylon_tick::replay_session::ReplayCommitDisposition;
use babylon_tick::{company_graph, material_world};
use std::collections::{BTreeMap, BTreeSet};

fn first_session(capture: &CapturedEconomicCatalog) -> MaterialReplaySession<HypergraphStore> {
    CapturedEconomicCatalog::decode(capture.canonical_bytes(), capture.digest())
        .expect("reopen captured foundation inputs")
        .create_foundation(
            ReplaySessionId::try_from("company/national-replay").expect("stable campaign"),
            ReplaySeed::new(37),
        )
        .expect("current national foundation")
        .into_session()
        .expect("typed replay session")
}
fn prepare(s: &MaterialReplaySession<HypergraphStore>) -> PreparedMaterialTick<HypergraphStore> {
    let a = OrderedPracticeActionBatch::empty(
        s.graph_session().session_identity().clone(),
        s.completed_tick() + 1,
    )
    .expect("no operator actions");
    s.prepare_advance(&a).expect("native closed period")
}
/// Join the actual choice carrier, independently decoded physical evidence and the authorized whole units.
fn selected_limits(
    candidate: &PreparedMaterialTick<HypergraphStore>,
    register: &CompanyPortfolioRegister,
) -> BTreeMap<(SiteId, ProcessId), u64> {
    let choices = &candidate.graph_report().report().choice_receipts;
    let mut by_key: BTreeMap<_, _> = register
        .companies
        .iter()
        .map(|r| {
            (
                company_graph::company_key("economy/national-world", r.company),
                r,
            )
        })
        .collect();
    let mut limits = BTreeMap::new();
    for choice in choices
        .iter()
        .filter(|r| r.rule_id() == "company/portfolio-investment")
    {
        let parent = by_key
            .remove(choice.stable_carrier())
            .expect("one sample per actual parent");
        let ordinal = choice
            .branches()
            .iter()
            .position(|b| b.member == choice.selected_outcome())
            .expect("selected branch in captured order");
        assert_eq!(choice.branches().len(), 4);
        assert!(parent.weights[ordinal] > 0);
        assert!(parent.feasible[ordinal]);
        assert_eq!(parent.period, 1);
        for r in &parent.plans[ordinal] {
            limits.insert((r.site, r.process), r.replacement + r.expansion);
        }
    }
    assert!(by_key.is_empty());
    limits
}
#[test]
fn national_99_choices_bound_next_purchases_and_survive_full_checkpoint() {
    let capture =
        CapturedEconomicCatalog::capture(economic_catalog::national_catalog_input(), None)
            .expect("current company-enabled capture");
    let members: BTreeSet<_> = capture
        .national_companies()
        .expect("whole-site assignment")
        .members
        .iter()
        .map(|r| r.site)
        .collect();
    let mut live = first_session(&capture);
    let first = prepare(&live);
    let register = first
        .material()
        .register()
        .company_portfolios()
        .expect("first observations");
    assert_eq!(register.companies.len(), 99);
    let limits = selected_limits(&first, register);
    let expected_first = *first.identity();
    let expected_choices = first.graph_report().report().choice_receipts.clone();
    live.commit_prepared_and_publish(&mut CollectingSink::default(), first, |_, _| {
        Ok::<_, &str>(ReplayCommitDisposition::Committed)
    })
    .expect("publish first graph and material period");
    let second = prepare(&live);
    let receipts = material_world::decode_material_receipts(second.material().receipt_bytes())
        .expect("period-two purchases");
    let mut compared = 0;
    for r in &receipts.investment {
        if members.contains(&r.site_id) {
            let limit = limits.get(&(r.site_id, r.process_id)).copied().unwrap_or(0);
            assert!(r.admitted_units <= limit);
            compared += 1;
        }
    }
    assert!(compared > 0);
    let expected_second = *second.identity();
    let receipt_hash = second.identity().receipt_digest();
    drop(second);
    drop(live);
    let mut cold = first_session(&capture);
    let repeated = prepare(&cold);
    assert_eq!(*repeated.identity(), expected_first);
    assert_eq!(
        repeated.graph_report().report().choice_receipts,
        expected_choices
    );
    let graph = repeated.graph_report();
    let bytes = repeated.material().register().canonical_bytes().to_vec();
    let restored = MaterialWorldRegister::decode_external(cold.catalog(), bytes)
        .expect("rehydrated portfolio evidence");
    cold.restore_full_checkpoint(
        graph.result_stable_graph(),
        graph.material_state_rows(),
        graph.result_registers().canonical_bytes(),
        restored,
    )
    .expect("restore first committed graph and material register");
    drop(repeated);
    let resumed = prepare(&cold);
    assert_eq!(*resumed.identity(), expected_second);
    assert_eq!(resumed.identity().receipt_digest(), receipt_hash);
}

#[path = "support/company_scale.rs"]
mod scale;
