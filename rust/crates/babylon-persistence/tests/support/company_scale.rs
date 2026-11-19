//! Repeatable native experiment over one physical national opening and independently sampled parents.
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::{AccountId, CompanyId, EquipmentPosition, ProcessId, SiteId};
use babylon_persistence::economic_catalog::{
    self, CapturedEconomicCatalog, CatalogLogistics, EconomicCatalogError, EconomicOpening,
    EconomicSiteSeed, ResidentStaffingPoolSeed, SourceArtifact, SourceArtifactKind,
};
use babylon_persistence::national_economy::companies::{
    CompanyCaptureError, ExperimentalPopulation,
};
use babylon_persistence::national_economy::NationalOpeningError;
use babylon_persistence::qualification_audit::trade;
use babylon_tick::material_replay::PreparedMaterialTick;
use babylon_tick::material_world::MaterialTickReceipts;
use babylon_tick::replay_session::ReplayCommitDisposition;
use babylon_tick::{company_graph, material_world};
use serde_json::{json, Value};
use std::collections::BTreeMap;
use std::time::Instant;

#[path = "company_conditions.rs"]
mod conditions;
#[path = "company_divergence.rs"]
mod divergence;
use conditions::{Condition, Observed};
use divergence::Samples;
struct Physical {
    sites: Vec<EconomicSiteSeed>,
    staffing: Vec<ResidentStaffingPoolSeed>,
    equipment: EquipmentPosition,
    routes: CatalogLogistics,
}
impl Physical {
    fn new(s: &EconomicOpening) -> Self {
        Self {
            sites: s.sites.clone(),
            staffing: s.staffing.clone(),
            equipment: s.equipment_position.clone(),
            routes: s.logistics.clone(),
        }
    }
    fn verify(&self, s: &EconomicOpening) {
        assert_eq!(self.sites.len(), s.sites.len());
        for (base, site) in self.sites.iter().zip(&s.sites) {
            let mut physical_base = base.clone();
            physical_base.opening_cash = site.opening_cash;
            assert_eq!(
                &physical_base, site,
                "all operating site fields except the controlled cash condition"
            );
        }
        assert_eq!(self.staffing, s.staffing);
        assert_eq!(self.equipment, s.equipment_position);
        assert_eq!(self.routes, s.logistics);
    }
}
fn capture(
    scale: Option<ExperimentalPopulation>,
    condition: Condition,
) -> Result<CapturedEconomicCatalog, EconomicCatalogError> {
    let mut input = economic_catalog::national_catalog_input();
    let policy = input
        .sources
        .iter_mut()
        .find(|s| s.kind() == SourceArtifactKind::NationalGamePolicy)
        .expect("captured policy");
    let mut text = std::str::from_utf8(policy.bytes())
        .expect("authored policy")
        .to_owned();
    condition.change(&mut text);
    if let Some(experiment) = scale {
        text = text.replacen(
            "[companies]",
            &format!(
                "[companies]\nexperiment_controller_count = {}",
                experiment.count()
            ),
            1,
        );
    }
    *policy = SourceArtifact::capture(SourceArtifactKind::NationalGamePolicy, text.into_bytes());
    if scale.is_some() {
        assert!(
            matches!(
                CapturedEconomicCatalog::capture(input.clone(), None),
                Err(EconomicCatalogError::Identity)
            ),
            "ordinary captures refuse larger partitions"
        );
        "national-company-scale-experiment".clone_into(&mut input.preset_id);
    }
    CapturedEconomicCatalog::capture(input, None)
}

fn opening_liquidity(capture: &CapturedEconomicCatalog) -> Value {
    let finances = capture
        .national_company_finances()
        .expect("source-bound cash");
    let floors: i128 = finances
        .members
        .iter()
        .map(|r| r.cash_floor.micro_units())
        .sum();
    let original: i128 = finances
        .members
        .iter()
        .map(|r| r.original_cash.micro_units())
        .sum();
    let remaining: i128 = finances
        .members
        .iter()
        .map(|r| r.remaining_cash.micro_units())
        .sum();
    let free: i128 = finances
        .members
        .iter()
        .map(|r| (r.remaining_cash.micro_units() - r.cash_floor.micro_units()).max(0))
        .sum();
    let central: i128 = finances
        .treasuries
        .iter()
        .map(|r| r.cash.micro_units())
        .sum();
    assert_eq!(
        original,
        remaining + central,
        "member and central cash conserve the opening funds"
    );
    json!({"original_member_cash_micros":original.to_string(),"protected_member_floors_micros":floors.to_string(),
          "member_spendable_micros":free.to_string(),"treasury_cash_micros":central.to_string(),"treasury_bps":finances.sweep_bps})
}

#[derive(Default)]
struct Decisions {
    selected: BTreeMap<CompanyId, usize>,
    limits: BTreeMap<(SiteId, ProcessId), u64>,
    summary: Value,
}
fn decisions(tick: &PreparedMaterialTick<HypergraphStore>, scope: &str) -> Decisions {
    let register = tick
        .material()
        .register()
        .company_portfolios()
        .expect("admitted company evidence");
    let mut by_carrier: BTreeMap<_, _> = register
        .companies
        .iter()
        .map(|row| (company_graph::company_key(scope, row.company), row))
        .collect();
    let mut result = Decisions::default();
    let mut conditions = [0_u64; 5];
    let mut eligible = [0_u64; 4];
    let mut supported = [0_u64; 4];
    let mut selections = [0_u64; 4];
    let mut alternatives = 0;
    let mut requested = 0_u128;
    let mut funding = 0_i128;
    for receipt in tick
        .graph_report()
        .report()
        .choice_receipts
        .iter()
        .filter(|r| r.rule_id() == "company/portfolio-investment")
    {
        let row = by_carrier
            .remove(receipt.stable_carrier())
            .expect("each receipt belongs to a unique occupied controller");
        assert_eq!(receipt.branches().len(), 4);
        let which = receipt
            .branches()
            .iter()
            .position(|b| b.member == receipt.selected_outcome())
            .expect("selected branch");
        assert!(row.weights[which] > 0 && row.feasible[which]);
        conditions[row.condition as usize] += 1;
        alternatives += usize::from(row.weights.iter().filter(|&&w| w > 0).count() > 1);
        for i in 0..4 {
            eligible[i] += u64::from(row.feasible[i]);
            supported[i] += u64::from(row.weights[i] > 0);
        }
        selections[which] += 1;
        assert!(result.selected.insert(row.company, which).is_none());
        for plan in &row.plans[which] {
            let units = plan
                .replacement
                .checked_add(plan.expansion)
                .expect("whole authorized units");
            assert!(result
                .limits
                .insert((plan.site, plan.process), units)
                .is_none());
            requested += u128::from(units);
            funding = funding
                .checked_add(plan.funding.micro_units())
                .expect("finite available funding");
        }
    }
    assert!(by_carrier.is_empty());
    result.summary = json!({"condition_counts_loss_replacement_spare_unmet_unmatched":conditions,
        "eligible_by_portfolio":eligible,"positive_weights_by_portfolio":supported,"selected_by_portfolio":selections,
        "controllers_with_multiple_positive_weights":alternatives,"authorized_next_units":requested.to_string(),"authorized_next_funding_micros":funding.to_string()});
    result
}

fn realization(
    receipts: &MaterialTickReceipts,
    members: &BTreeMap<SiteId, CompanyId>,
    prior: &Decisions,
) -> Value {
    let mut units = 0_u128;
    let mut cost = 0_i128;
    let mut funding = 0_i128;
    let mut observations = 0;
    let mut per_branch = [0_u128; 4];
    for r in &receipts.investment {
        let Some(company) = members.get(&r.site_id) else {
            continue;
        };
        let limit = prior
            .limits
            .get(&(r.site_id, r.process_id))
            .copied()
            .unwrap_or(0);
        assert!(
            r.admitted_units <= limit,
            "actual commitment within its selected parent plan"
        );
        observations += 1;
        per_branch[prior.selected[company]] += u128::from(r.admitted_units);
        units += u128::from(r.admitted_units);
        cost = cost
            .checked_add(
                i128::from(r.admitted_units)
                    .checked_mul(r.unit_price.micro_units())
                    .expect("purchase cost"),
            )
            .expect("total investment cost");
    }
    for transfer in &receipts.contributions {
        if let AccountId::Company(company) = transfer.contributor {
            assert_eq!(members.get(&transfer.issuer_site_id), Some(&company));
            funding = funding
                .checked_add(transfer.paid.micro_units())
                .expect("settled contribution");
        }
    }
    json!({"member_investment_observations":observations,"admitted_units":units.to_string(),"admitted_units_by_previous_selection":per_branch.map(|u|u.to_string()),
        "admitted_cost_micros":cost.to_string(),"settled_parent_contributions_micros":funding.to_string()})
}

fn run(
    c: &CapturedEconomicCatalog,
    seed: i64,
    condition: Condition,
    count: usize,
    members: &BTreeMap<SiteId, CompanyId>,
) -> Vec<Samples> {
    let reopened = CapturedEconomicCatalog::decode(c.canonical_bytes(), c.digest())
        .expect("reopen captured national inputs");
    let first = Instant::now();
    let session =
        ReplaySessionId::try_from("company-scale/qualification").expect("fixed replay session");
    let foundation = reopened
        .create_foundation(session, ReplaySeed::new(seed))
        .expect("build foundation");
    let foundation_bytes = foundation.canonical_len().expect("encoded foundation");
    let mut live = foundation.into_session().expect("open native session");
    let session_ns = first.elapsed().as_nanos().to_string();
    let scope = live
        .graph_session()
        .stable_resolver()
        .scenario_scope()
        .to_owned();
    let mut prior = None;
    let mut initial = None;
    let mut samples = Vec::new();
    let mut realized_conditions = Observed::default();
    for n in 1..=condition.periods() {
        let start = Instant::now();
        let tick = super::prepare(&live);
        let prepare_ns = start.elapsed().as_nanos().to_string();
        let portfolio = tick
            .material()
            .register()
            .company_portfolios()
            .expect("stored evidence");
        let policy = live
            .catalog()
            .company_portfolios
            .as_ref()
            .expect("captured policy");
        let timer = Instant::now();
        for company in &portfolio.companies {
            assert_eq!(
                company
                    .recompute(policy)
                    .expect("checked replay of raw operating evidence"),
                *company
            );
        }
        let recompute_ns = timer.elapsed().as_nanos().to_string();
        let receipts = material_world::decode_material_receipts(tick.material().receipt_bytes())
            .expect("actual committed material close");
        let measurements =
            Observed::record(&tick, &receipts, members, realized_conditions.orders());
        realized_conditions.include(&measurements);
        let derived = decisions(&tick, &scope);
        assert_eq!(derived.selected.len(), count);
        samples.push(Samples::new(portfolio, &derived.selected));
        let realized = prior
            .as_ref()
            .map(|old| realization(&receipts, members, old));
        let bytes = tick.material().register().canonical_bytes().len();
        let receipt_bytes = tick.material().receipt_bytes().len();
        let hash = trade::hex(&tick.identity().result_world_hash());
        if n == 1 {
            initial = Some((derived.selected.clone(), hash.clone()));
        }
        let start = Instant::now();
        live.commit_prepared_and_publish(&mut CollectingSink::default(), tick, |_, _| {
            Ok::<_, &str>(ReplayCommitDisposition::Committed)
        })
        .expect("commit graph and material");
        println!(
            "{}",
            json!({"version":1,"experiment":"national_company_scale","controllers":count,"seed":seed,"opening_treatment":condition.label(),"period":n,
           "foundation_bytes":foundation_bytes,"material_register_bytes":bytes,"material_receipt_bytes":receipt_bytes,
           "session_build_ns":session_ns,"prepare_ns":prepare_ns,"policy_recompute_from_stored_observations_and_compare_ns":recompute_ns,"observed_conditions":measurements.report(),"commit_ns":start.elapsed().as_nanos().to_string(),
           "world_hash":hash,"decision":derived.summary,"previous_decisions_realized":realized})
        );
        prior = Some(derived);
    }
    condition.verify(&realized_conditions);
    drop(live);
    let (choices, first_hash) = initial.expect("first period");
    let duplicate = CapturedEconomicCatalog::decode(c.canonical_bytes(), c.digest())
        .expect("reopen identical capture")
        .create_foundation(
            ReplaySessionId::try_from("company-scale/qualification").expect("same session"),
            ReplaySeed::new(seed),
        )
        .expect("same foundation")
        .into_session()
        .expect("repeat");
    let repeated = super::prepare(&duplicate);
    assert_eq!(
        trade::hex(&repeated.identity().result_world_hash()),
        first_hash
    );
    assert_eq!(decisions(&repeated, &scope).selected, choices);
    samples
}

#[test]
#[ignore = "native 99/300/600 controller qualification, serial with other national gates"]
fn controller_counts_share_physical_grain_report_real_choices_and_next_commitments() {
    let only = std::env::var("BABYLON_COMPANY_SCALE_COUNT")
        .ok()
        .map(|s| s.parse::<usize>().expect("99, 300 or 600"));
    assert!(only.is_none_or(|n| matches!(n, 99 | 300 | 600)));
    let mut physical = None;
    for scale in [
        None,
        Some(ExperimentalPopulation::ThreeHundred),
        Some(ExperimentalPopulation::SixHundred),
    ] {
        let count = scale.map_or(99, |p| usize::from(p.count()));
        if scale.is_some() && only.is_some_and(|n| n != count) {
            continue;
        }
        let mut original = None;
        for condition in [Condition::Ordinary, Condition::OnePeriod] {
            let start = Instant::now();
            let c = match capture(scale, condition) {
                Ok(c) => c,
                Err(EconomicCatalogError::NationalOpening(NationalOpeningError::Companies(
                    CompanyCaptureError::ControllerCapacity {
                        requested,
                        available,
                    },
                ))) => {
                    println!(
                        "{}",
                        json!({"version":1,"experiment":"national_company_scale","status":"insufficient_occupied_sites","requested":requested,"available":available})
                    );
                    break;
                }
                Err(err) => panic!("national controller experiment refused: {err}"),
            };
            let capture_ns = start.elapsed().as_nanos().to_string();
            let fixed = physical.get_or_insert_with(|| Physical::new(c.opening()));
            fixed.verify(c.opening());
            if only.is_some_and(|n| n != count) {
                break;
            }
            let roster = c.national_companies().expect("company opening");
            assert_eq!(roster.companies.len(), count);
            assert!(roster
                .companies
                .iter()
                .all(|r| r.sites > 0 && r.employed > 0));
            let members: BTreeMap<_, _> = roster
                .members
                .iter()
                .map(|r| (r.site, r.company.id()))
                .collect();
            assert_eq!(members.len(), roster.members.len());
            let original_cash = c
                .national_company_finances()
                .expect("treasuries")
                .members
                .iter()
                .try_fold(0_i128, |n, r| n.checked_add(r.original_cash.micro_units()))
                .expect("exact cash");
            if condition == Condition::Ordinary {
                original = Some(original_cash);
            } else {
                assert_eq!(
                    original_cash.checked_mul(2),
                    original,
                    "the one-period control halves each population's opening cash"
                );
            }
            println!(
                "{}",
                json!({"version":1,"experiment":"national_company_scale","controllers":count,"opening_treatment":condition.label(),"opening_liquidity":opening_liquidity(&c),"capture_ns":capture_ns,"capture_bytes":c.canonical_bytes().len(),"capture_sha256":trade::hex(&c.digest()),"original_member_cash_micros":original_cash.to_string(),
                "sites":fixed.sites.len(),"staffing_pools":fixed.staffing.len(),"equipment_cohorts":fixed.equipment.cohorts.len(),"supplier_routes":fixed.routes.supplier_routes.len(),"member_sites":members.len()})
            );
            let first = run(&c, 37, condition, count, &members);
            if condition == Condition::Ordinary {
                let other = run(&c, 319, condition, count, &members);
                divergence::report(&first, &other, count, condition.label());
            }
        }
    }
}
