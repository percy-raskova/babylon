//! Serialization controls use actual adjudicated identities, without claiming
//! national coverage or Archive admission from this small accounting fixture.
use super::audit::{BoundaryFacts, ReceiptFacts, RenewalFacts};
use super::policy::{
    AdvanceSample, MemorySample, MemorySummary, Metric, NationalSqlitePolicy, PeriodCharge,
    QualificationRun, QuerySample,
};
use super::{audit, economic, production_renewal, reader, trade};
use crate::michigan_content::MichiganContentPreset;
use crate::michigan_material::MichiganMaterialCatalog;
use crate::production_observation::ProductionSite;
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_practice_contract::OrderedPracticeActionBatch;
use babylon_tick::material_world;
use babylon_tick::replay_session::ReplayCommitDisposition;
use sha2::Digest;
use sha2::Sha256;
use std::path::Path;
use uuid::Uuid;

const MIB: u64 = 1_000_000;
const SECOND_NS: u64 = 1_000_000_000;

fn qualification_policy() -> NationalSqlitePolicy {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../contracts/national_sqlite_qualification_v1.json");
    let bytes = std::fs::read(&path).expect("the authored contract is readable");
    let digest = <[u8; 32]>::from(Sha256::digest(&bytes));
    NationalSqlitePolicy::open(&path, digest).expect("the authored contract is frozen")
}

fn advance(period: u64, total_ns: u64, chunks_visited: u64) -> AdvanceSample {
    AdvanceSample {
        period,
        judgment_ns: total_ns,
        encoding_ns: 0,
        commit_ns: 0,
        briefing_ns: 0,
        total_ns,
        chunks_visited,
    }
}

fn charge(period: u64, stored: u64, unreachable: u64) -> PeriodCharge {
    PeriodCharge {
        period,
        stored_added_bytes: stored,
        decoded_added_bytes: stored.saturating_mul(2),
        unreachable_stored_bytes: unreachable,
    }
}

fn memory(rss_bytes: u64, gap_ns: u64, samples: usize) -> MemorySummary {
    MemorySummary {
        samples: (0..samples)
            .map(|index| MemorySample {
                elapsed_ns: u64::try_from(index)
                    .expect("the fixture index fits u64")
                    .saturating_mul(gap_ns),
                rss_bytes,
            })
            .collect(),
    }
}

fn passing_run(horizon: u64) -> QualificationRun {
    QualificationRun {
        advances: (1..=horizon)
            .map(|period| advance(period, SECOND_NS, 0))
            .collect(),
        cold_open_ns: SECOND_NS,
        warm_queries: vec![QuerySample {
            elapsed_ns: 1_000_000,
            rows_visited: 4,
            chunks_visited: 0,
        }],
        cold_queries: vec![QuerySample {
            elapsed_ns: 2_000_000,
            rows_visited: 4,
            chunks_visited: 0,
        }],
        memory: memory(3_000_000_000, 250_000_000, 4),
        charges: (1..=horizon)
            .map(|period| charge(period, 1_000_000, 0))
            .collect(),
        opening_bytes: 100_000_000,
    }
}

fn metric(
    policy: &NationalSqlitePolicy,
    run: &QualificationRun,
    horizon: u64,
    which: Metric,
) -> bool {
    policy
        .evaluate(run, horizon)
        .expect("the fixture evaluation succeeds")
        .metrics
        .iter()
        .find(|decision| decision.metric == which)
        .expect("the fixture requests a decided metric")
        .passed
}

#[test]
fn ordinary_turn_over_the_interim_bar_fails_even_when_p95_passes() {
    let policy = qualification_policy();
    let mut run = passing_run(52);
    run.advances[6] = advance(7, 61 * SECOND_NS, 0);
    let verdict = policy
        .evaluate(&run, 52)
        .expect("the fixture evaluation succeeds");
    assert!(verdict.advances.p95_ns <= 60 * SECOND_NS);
    assert_eq!(verdict.advances.max_ns, 61 * SECOND_NS);
    assert_eq!(verdict.advances.over_limit_periods, vec![7]);
    assert!(!verdict.passed);
    let decision = verdict
        .metrics
        .iter()
        .find(|decision| decision.metric == Metric::Advance)
        .expect("advance is decided");
    assert!(!decision.passed);
    assert!(decision.detail.contains("over_periods=1"));
}

#[test]
fn checkpoint_deletions_cannot_cancel_new_additions() {
    let policy = qualification_policy();
    let mut run = passing_run(13);
    run.charges = (1..=13)
        .map(|period| charge(period, 12 * MIB, 50 * MIB))
        .collect();
    let verdict = policy
        .evaluate(&run, 13)
        .expect("the fixture evaluation succeeds");
    assert_eq!(run.charges[0].charged_bytes(), 12 * MIB);
    assert_eq!(verdict.growth.total_charged_bytes, 13 * 12 * MIB);
    assert_eq!(verdict.growth.total_unreachable_bytes, 13 * 50 * MIB);
    assert_eq!(verdict.growth.checkpoints.len(), 1);
    assert_eq!(verdict.growth.checkpoints[0].charged_bytes, 13 * 12 * MIB);
    assert!(!verdict.growth.checkpoints[0].passed);
    assert!(!metric(&policy, &run, 13, Metric::PeriodGrowth));
    assert!(!metric(&policy, &run, 13, Metric::CheckpointGrowth));
}

#[test]
fn combined_memory_above_four_gigabytes_fails() {
    let policy = qualification_policy();
    let mut run = passing_run(2);
    run.memory = memory(4_000_000_001, 250_000_000, 3);
    assert!(!metric(&policy, &run, 2, Metric::Memory));
    run.memory = memory(4_000_000_000, 250_000_000, 3);
    assert!(metric(&policy, &run, 2, Metric::Memory));
}

#[test]
fn sample_gap_above_the_frozen_interval_fails() {
    let policy = qualification_policy();
    let mut run = passing_run(2);
    run.memory = memory(2_000_000_000, 250_000_001, 3);
    assert!(!metric(&policy, &run, 2, Metric::MemorySampling));
    run.memory = memory(2_000_000_000, 250_000_000, 3);
    assert!(metric(&policy, &run, 2, Metric::MemorySampling));
}

#[test]
fn every_frozen_boundary_passes_at_equality() {
    let policy = qualification_policy();
    let mut run = passing_run(52);
    run.advances = (1..=52)
        .map(|period| advance(period, policy.maximum_advance_ns(), 0))
        .collect();
    run.cold_open_ns = policy.maximum_cold_open_ns();
    run.warm_queries = vec![QuerySample {
        elapsed_ns: policy.maximum_warm_query_ns(),
        rows_visited: 4,
        chunks_visited: 0,
    }];
    run.cold_queries = vec![QuerySample {
        elapsed_ns: policy.maximum_cold_query_ns(),
        rows_visited: 4,
        chunks_visited: 0,
    }];
    run.memory = memory(policy.maximum_memory_bytes(), 250_000_000, 3);
    run.charges = (1..=52)
        .map(|period| charge(period, policy.maximum_period_growth(), 0))
        .collect();
    let verdict = policy
        .evaluate(&run, 52)
        .expect("the fixture evaluation succeeds");
    assert!(verdict.passed, "{:?}", verdict.metrics);
    assert_eq!(verdict.growth.checkpoints.len(), 4);
    assert_eq!(verdict.growth.windows.len(), 1);
    assert_eq!(
        verdict.growth.windows[0].charged_bytes,
        policy.maximum_window_growth()
    );
}

#[test]
fn interim_bar_accepts_forty_second_advances_and_records_the_thirty_second_target() {
    let policy = qualification_policy();
    let mut run = passing_run(52);
    run.advances = (1..=52)
        .map(|period| advance(period, 41 * SECOND_NS, 0))
        .collect();
    let verdict = policy
        .evaluate(&run, 52)
        .expect("the fixture evaluation succeeds");
    assert!(verdict.passed, "{:?}", verdict.metrics);
    assert_eq!(verdict.advances.max_ns, 41 * SECOND_NS);
    assert!(verdict.advances.max_ns > policy.target_advance_ns());
    assert!(!verdict.meets_targets);
    let debt = verdict
        .optimization_debt
        .first()
        .expect("the interim bar records its advance debt");
    assert_eq!(debt.metric, Metric::Advance);
    assert_eq!(debt.observed, 41 * SECOND_NS);
    assert_eq!(debt.interim_limit, 60 * SECOND_NS);
    assert_eq!(debt.target_limit, 30 * SECOND_NS);
    assert!(!debt.met);
}

#[test]
fn advance_above_the_interim_bar_still_fails() {
    let policy = qualification_policy();
    let mut run = passing_run(52);
    run.advances[10] = advance(11, 60 * SECOND_NS, 0);
    assert!(metric(&policy, &run, 52, Metric::Advance));
    run.advances[10] = advance(11, 60 * SECOND_NS + 1, 0);
    let verdict = policy
        .evaluate(&run, 52)
        .expect("the fixture evaluation succeeds");
    assert_eq!(verdict.advances.over_limit_periods, vec![11]);
    assert!(!verdict.passed);
    assert!(!metric(&policy, &run, 52, Metric::Advance));
    assert!(!verdict.meets_targets);
}

#[test]
fn advancing_inside_the_thirty_second_target_clears_the_debt() {
    let policy = qualification_policy();
    let verdict = policy
        .evaluate(&passing_run(52), 52)
        .expect("the fixture evaluation succeeds");
    assert!(verdict.passed);
    assert!(verdict.meets_targets);
    assert!(verdict.optimization_debt.iter().all(|debt| debt.met));
}

#[test]
fn contract_freezes_the_chapter_nine_limits() {
    let policy = qualification_policy();
    assert_eq!(policy.maximum_advance_ns(), 60 * SECOND_NS);
    assert_eq!(policy.target_advance_ns(), 30 * SECOND_NS);
    assert_eq!(policy.maximum_cold_open_ns(), 30 * SECOND_NS);
    assert_eq!(policy.maximum_warm_query_ns(), SECOND_NS);
    assert_eq!(policy.maximum_cold_query_ns(), 2 * SECOND_NS);
    assert_eq!(policy.maximum_memory_bytes(), 4_000_000_000);
    assert_eq!(policy.maximum_period_growth(), 10 * MIB);
    assert_eq!(policy.maximum_checkpoint_growth(), 130 * MIB);
    assert_eq!(policy.maximum_window_growth(), 520 * MIB);
    assert_eq!(policy.maximum_total_growth(), 3_250 * MIB);
    assert_eq!(policy.checkpoint_periods(), 13);
    assert_eq!(policy.window_periods(), 52);
    assert_eq!(policy.qualification_periods(), 325);
    assert_eq!(policy.minimum_p95_samples(), 52);
    assert_eq!(policy.memory_sample_ns(), 250_000_000);
}

#[test]
fn subphase_sum_above_total_refuses_instead_of_substituting_a_subphase() {
    let policy = qualification_policy();
    let mut run = passing_run(2);
    let mut sample = advance(1, 10 * SECOND_NS, 0);
    sample.judgment_ns = 6 * SECOND_NS;
    sample.encoding_ns = 5 * SECOND_NS;
    run.advances[0] = sample;
    assert!(policy.evaluate(&run, 2).is_err());
}

#[test]
fn bounded_reads_and_full_horizons_are_required() {
    let policy = qualification_policy();
    let mut run = passing_run(52);
    run.warm_queries[0].chunks_visited = 1;
    assert!(!metric(&policy, &run, 52, Metric::BoundedRead));
    let mut run = passing_run(2);
    run.cold_queries.clear();
    assert!(!metric(&policy, &run, 2, Metric::ColdQuery));
    let run = passing_run(2);
    assert!(policy.evaluate(&run, 52).is_err());
}

fn sites(catalog: &MichiganMaterialCatalog) -> Vec<ProductionSite> {
    catalog
        .sites()
        .iter()
        .map(|site| ProductionSite {
            id: audit::hex(&site.id().as_bytes()),
            location: format!("county:{}", site.county_geoid)
                .parse()
                .expect("the authored literal parses as the declared type"),
            name: site.label.clone(),
            industry_code: Some(site.naics.clone()),
            observed_employment: None,
            roles: vec![],
            sector_code: Some(site.sector_code.clone()),
            function: "manufacturing".into(),
            processes: vec![],
            inventory: vec![],
        })
        .collect()
}

#[test]
#[allow(
    clippy::too_many_lines,
    reason = "`serialized_boundary_binds_every_fold_to_seed_and_current_receipt` keeps one authored boundary's fixture and assertions together"
)]
fn serialized_boundary_binds_every_fold_to_seed_and_current_receipt() {
    let catalog = crate::test_support::catalog();
    let sites = sites(&catalog);
    let mut session = MichiganContentPreset::FourWeekStandard
        .create_foundation(&catalog)
        .expect("the authored catalog builds the foundation")
        .into_session()
        .expect("the fixture opens a session");
    let mut economic = economic::Audit::default();
    let mut trade = trade::Audit::default();
    let mut renewal = None;
    let mut previous = None;
    for tick in 1..=2 {
        let actions = OrderedPracticeActionBatch::empty(
            session.graph_session().session_identity().clone(),
            tick,
        )
        .expect("the empty authored batch constructs");
        let prepared = session
            .prepare_advance(&actions)
            .expect("the session prepares the authored advance");
        let identity = prepared.identity();
        let receipts =
            material_world::decode_material_receipts(prepared.material().receipt_bytes())
                .expect("the canonical bytes decode into the declared type");
        let register = prepared.material().register();
        assert_eq!(
            identity.receipt_digest().as_slice(),
            Sha256::digest(prepared.material().receipt_bytes()).as_slice()
        );
        let renewal_evidence = if tick == 1 {
            let audit = production_renewal::Audit::seed(
                session.catalog(),
                register.state(),
                tick,
                register.digest(),
            )
            .expect("the fixture seeds the authored rows");
            let evidence = audit
                .evidence()
                .expect("the fixture call `evidence` succeeds for the authored inputs");
            renewal = Some(audit);
            evidence
        } else {
            renewal
                .as_mut()
                .expect("the fixture set the optional field before this borrow")
                .read(&receipts)
                .expect("the fixture reader returns its authored facts")
        };
        let facts = BoundaryFacts {
            version: 1,
            campaign: Uuid::from_u128(342).to_string(),
            foundation_sha256: audit::hex(&identity.foundation_digest()),
            policy_sha256: audit::hex(&[1; 32]),
            tick,
            tick_content_hash: audit::hex(identity.tick_content_hash().as_bytes()),
            envelope_digest: audit::hex(&[2; 32]),
            canonical_receipt_sha256: audit::hex(&identity.receipt_digest()),
            nominal_world_hash: audit::hex(&identity.result_world_hash()),
            material_register_sha256: audit::hex(&register.digest()),
            material_register_bytes: register.canonical_bytes().len(),
            production_evidence_sha256: audit::hex(&[3; 32]),
            production_evidence_body_bytes: 1,
            county_roster_sha256: audit::hex(&[4; 32]),
            economic: ReceiptFacts::new(
                economic
                    .read(&receipts)
                    .expect("the fixture reader returns its authored facts"),
                identity,
            ),
            trade: ReceiptFacts::new(
                trade
                    .read(&receipts, &sites)
                    .expect("the fixture reader returns its authored facts"),
                identity,
            ),
            production_renewal: Some(RenewalFacts::new(renewal_evidence, identity)),
        };
        let read = reader::BoundaryRead {
            version: 1,
            scope: "authenticated_material_and_archive_facts_only",
            archive: reader::ArchiveFacts {
                expected_tick: tick,
                durable_tick: tick,
                processed_tick: tick,
                pending_count: 0,
                pending_scope: "requested_prefix",
                observation_mode: "live_latest",
                captured_tail_tick: tick,
                captured_tail_tick_content_hash: facts.tick_content_hash.clone(),
                dossier_sha256: audit::hex(&[5; 32]),
            },
            facts,
            production_read_elapsed_ns: 0,
            audit_elapsed_ns: 0,
        };
        let encoded = serde_json::to_value(read).expect("the value serializes to JSON");
        let facts = &encoded["facts"];
        for fold in ["economic", "trade", "production_renewal"] {
            let key = if fold == "production_renewal" {
                "through_tick_content_hash"
            } else {
                "tick_content_hash"
            };
            assert_eq!(facts[fold][key], facts["tick_content_hash"], "{fold}");
            assert_eq!(
                facts[fold]["canonical_receipt_sha256"], facts["canonical_receipt_sha256"],
                "{fold}"
            );
        }
        assert_eq!(facts["production_renewal"]["through_period"], tick);
        if let Some(prior) = previous.replace(facts["tick_content_hash"].clone()) {
            assert_ne!(facts["tick_content_hash"], prior);
        }
        session
            .commit_prepared_and_publish(&mut CollectingSink::default(), prepared, |_, _| {
                Ok::<_, ()>(ReplayCommitDisposition::Committed)
            })
            .expect("the prepared period commits");
    }
}
