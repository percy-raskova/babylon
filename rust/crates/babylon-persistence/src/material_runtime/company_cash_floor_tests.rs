//! National counterfactual using the existing operating cash floor on a typed opening.
//! Every opening balance, price, good, employee, membership and route remains under its captured identity.
use super::MaterialRuntimeFoundation;
use crate::economic_catalog::{self, CapturedEconomicCatalog, SourceArtifact, SourceArtifactKind};
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::content_digest;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::{CircuitAccounting, CompanyId, ProcessId, SiteId};
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::company_graph;
use babylon_tick::material_replay::{MaterialReplaySession, PreparedMaterialTick};
use babylon_tick::material_world::{self, MaterialWorldRegister};
use babylon_tick::replay_session::ReplayCommitDisposition;
use serde_json::json;
use std::collections::BTreeMap;

fn no_pool_capture() -> CapturedEconomicCatalog {
    let mut inputs = economic_catalog::national_catalog_input();
    let artifact = inputs
        .sources
        .iter_mut()
        .find(|s| s.kind() == SourceArtifactKind::NationalGamePolicy)
        .expect("captured financial policy");
    let mut text = std::str::from_utf8(artifact.bytes())
        .expect("authored policy")
        .to_owned();
    for (term, replacement) in [
        (
            "working_capital_periods = 2\n",
            "working_capital_periods = 1\n",
        ),
        (
            "opening_treasury_bps = 1000\n",
            "opening_treasury_bps = 0\n",
        ),
    ] {
        assert_eq!(text.matches(term).count(), 1);
        text = text.replacen(term, replacement, 1);
    }
    *artifact = SourceArtifact::capture(SourceArtifactKind::NationalGamePolicy, text.into_bytes());
    CapturedEconomicCatalog::capture(inputs, None)
        .expect("ordinary capture with the matched cash control's terms")
}

fn restricted_session(
    foundation: MaterialRuntimeFoundation,
    members: &BTreeMap<SiteId, CompanyId>,
) -> MaterialReplaySession<HypergraphStore> {
    let baseline = foundation.initial_register().state();
    let mut state = baseline.clone();
    let CircuitAccounting::Monetary(money) = &mut state.accounting else {
        panic!("monetary source")
    };
    // Protect all opening cash from company investment and distributions. The economy's
    // own closed money supply bounds any individual positive balance in every future close.
    let total = money
        .book
        .total_cash_and_reserves()
        .expect("closed money supply");
    let mut changed = 0;
    for row in &mut money.financial.distributions {
        if members.contains_key(&row.issuer_site_id) {
            assert!(row.cash_floor < total);
            row.cash_floor = total;
            changed += 1;
        }
    }
    assert_eq!(changed, members.len());
    let register = MaterialWorldRegister::try_new(foundation.material_catalog(), 0, state)
        .expect("the established financial policy admits the protected cash floors");
    let mut restored = register.state().clone();
    let (CircuitAccounting::Monetary(before), CircuitAccounting::Monetary(after)) =
        (&baseline.accounting, &mut restored.accounting)
    else {
        panic!("monetary states")
    };
    assert_eq!(after.book, before.book, "all cash and reserves by account");
    for (original, restricted) in before
        .financial
        .distributions
        .iter()
        .zip(&mut after.financial.distributions)
    {
        restricted.cash_floor = original.cash_floor;
    }
    assert_eq!(
        &restored, baseline,
        "all other opening state bytes after restoring only the floors"
    );
    let mut basis = b"NationalCompanyOperatingFloorExperimentV1\0".to_vec();
    basis.extend(foundation.digest());
    basis.extend(register.digest());
    let digest = content_digest::sha256_of(&basis);
    println!(
        "{}",
        json!({"experiment":"national_company_operating_cash_floor","record":"controlled_opening",
        "seed":i64::from_be_bytes(foundation.graph_foundation().rng_seed().to_be_bytes()),
        "matched_capture_sha256":babylon_tick::hex(&foundation.spec().content_digest),
        "matched_foundation_sha256":babylon_tick::hex(&foundation.digest()),
        "test_foundation_sha256":babylon_tick::hex(&digest),
        "material_register_sha256":babylon_tick::hex(&register.digest()),
        "member_sites":changed,"protected_cash_floor_per_member_micros":total.micro_units().to_string(),
        "conserved_total_cash_and_reserves_micros":total.micro_units().to_string()})
    );
    MaterialReplaySession::new(
        foundation.graph,
        register,
        foundation.catalog,
        digest,
        foundation.spec.duration,
        foundation.labor,
    )
    .expect("normal material host with separately identified controlled opening")
}

fn record_decisions(
    tick: &PreparedMaterialTick<HypergraphStore>,
    scope: &str,
    prior_limits: &mut BTreeMap<(SiteId, ProcessId), u64>,
    seed: i64,
    period: u64,
    admitted_units: u64,
) -> u64 {
    let portfolios = tick
        .material()
        .register()
        .company_portfolios()
        .expect("retained prior conditions");
    let mut by_carrier: BTreeMap<_, _> = portfolios
        .companies
        .iter()
        .map(|c| (company_graph::company_key(scope, c.company), c))
        .collect();
    assert_eq!(by_carrier.len(), 99);
    let mut choices = [0_u64; 4];
    let mut eligible = [0_u64; 4];
    let mut supported = [0_u64; 4];
    let mut requested = 0_u64;
    let mut unaffordable = 0_u64;
    let mut permitted = 0_u64;
    prior_limits.clear();
    for choice in tick
        .graph_report()
        .report()
        .choice_receipts
        .iter()
        .filter(|r| r.rule_id() == "company/portfolio-investment")
    {
        let c = by_carrier
            .remove(choice.stable_carrier())
            .expect("one choice per parent");
        let branch = choice
            .branches()
            .iter()
            .position(|r| r.member == choice.selected_outcome())
            .expect("actual branch");
        assert!(c.feasible[branch] && c.weights[branch] > 0);
        choices[branch] += 1;
        for i in 0..4 {
            eligible[i] += u64::from(c.feasible[i]);
            supported[i] += u64::from(c.weights[i] > 0);
        }
        for r in &c.processes {
            assert_eq!(r.free_cash.micro_units(), 0);
            assert_eq!(c.treasury_available.micro_units(), 0);
            let units = r.replacement + r.expansion;
            requested += units;
            if units > 0
                && r.free_cash
                    .checked_add(c.treasury_available)
                    .expect("legal funding")
                    < r.unit_price
            {
                unaffordable += 1;
            }
        }
        for plan in &c.plans[branch] {
            let units = plan.replacement + plan.expansion;
            assert!(prior_limits
                .insert((plan.site, plan.process), units)
                .is_none());
            permitted += units;
        }
    }
    assert_eq!(choices.iter().sum::<u64>(), 99);
    assert!(by_carrier.is_empty());
    println!(
        "{}",
        json!({"experiment":"national_company_operating_cash_floor","record":"close","seed":seed,"period":period,
        "requested_units":requested,"requests_unaffordable_even_with_treasury":unaffordable,"eligible":eligible,"positive_weights":supported,
        "selected":choices,"authorized_following_period_units":permitted,"admitted_from_prior_units":admitted_units,
        "world_hash":babylon_tick::hex(&tick.identity().result_world_hash())})
    );
    unaffordable
}

fn observed(
    seed: i64,
    source: &CapturedEconomicCatalog,
    members: &BTreeMap<SiteId, CompanyId>,
) -> u64 {
    let scope = ReplaySessionId::try_from("company-scale/qualification")
        .expect("same capture and seeds as the independent control");
    let foundation = CapturedEconomicCatalog::decode(source.canonical_bytes(), source.digest())
        .expect("reopen")
        .create_foundation(scope, ReplaySeed::new(seed))
        .expect("opening");
    let mut live = restricted_session(foundation, members);
    let mut prior_limits = BTreeMap::new();
    let mut unaffordable_followed = 0;
    let mut prior_unaffordable = 0;
    for period in 1..=5 {
        let actions = OrderedPracticeActionBatch::empty(
            live.graph_session().session_identity().clone(),
            period,
        )
        .expect("empty actions");
        let tick = live
            .prepare_advance(&actions)
            .expect("normal graph and economic close");
        let receipts = material_world::decode_material_receipts(tick.material().receipt_bytes())
            .expect("closed investment receipts");
        let mut admitted_units = 0;
        if period > 1 {
            for row in receipts
                .investment
                .iter()
                .filter(|r| members.contains_key(&r.site_id))
            {
                assert!(
                    row.admitted_units
                        <= *prior_limits
                            .get(&(row.site_id, row.process_id))
                            .unwrap_or(&0)
                );
                admitted_units += row.admitted_units;
            }
            unaffordable_followed += prior_unaffordable;
        }
        prior_unaffordable = record_decisions(
            &tick,
            live.graph_session().stable_resolver().scenario_scope(),
            &mut prior_limits,
            seed,
            period,
            admitted_units,
        );
        live.commit_prepared_and_publish(&mut CollectingSink::default(), tick, |_, _| {
            Ok::<_, &str>(ReplayCommitDisposition::Committed)
        })
        .expect("advance");
    }
    unaffordable_followed
}

#[test]
#[ignore = "national controlled operating-funds experiment; serial with other national runs"]
fn protected_member_cash_limits_observed_requests_and_the_following_real_committed_purchases() {
    let source = no_pool_capture();
    let members = source
        .national_companies()
        .expect("whole operating sites")
        .members
        .iter()
        .map(|r| (r.site, r.company.id()))
        .collect();
    let witnesses = [37, 319].map(|seed| observed(seed, &source, &members));
    assert!(
        witnesses.iter().all(|&n| n > 0),
        "each seed needs an unaffordable request and its following actual close: {witnesses:?}"
    );
}
