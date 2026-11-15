//! A three-period opening feedstock supply lets two manufacturing companies reach distinct
//! financing and admission outcomes under the current first-applicable portfolio policy.
use super::{manufacturing_capture, paid_contribution, settlement};
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::{
    CompanyCondition, CompanyId, CompanyPortfolioEvidence, CompanyProcessPlan, InvestmentReceipt,
    MaterialCircuitState, MoneyTransferPurpose, OrderRow, OutboundOrderId, SiteId,
};
use babylon_persistence::company_statements::{CompanyBooks, CompanyPeriod};
use babylon_persistence::economic_catalog::CapturedEconomicCatalog;
use babylon_persistence::site_financial_statements;
use babylon_tick::company_graph;
use babylon_tick::material_replay::PreparedMaterialTick;
use babylon_tick::material_world::{self, MaterialTickReceipts};
use babylon_tick::replay_session::ReplayCommitDisposition;

fn manufacturer(
    capture: &CapturedEconomicCatalog,
    company: &str,
    site: &str,
) -> (CompanyId, SiteId) {
    let roster = capture
        .national_companies()
        .expect("captured company register");
    let company = roster
        .companies
        .iter()
        .find(|r| r.key.label() == company)
        .expect("named company")
        .key
        .id();
    let site = capture
        .opening()
        .sites
        .iter()
        .find(|r| r.label == site)
        .expect("named manufacturing site")
        .site_id;
    assert!(roster
        .members
        .iter()
        .any(|r| r.site == site && r.company.id() == company));
    (company, site)
}

fn selected_plan<'a>(
    tick: &'a PreparedMaterialTick<HypergraphStore>,
    scope: &str,
    member: (CompanyId, SiteId),
    expected: &str,
) -> (&'a CompanyPortfolioEvidence, &'a CompanyProcessPlan) {
    let row = tick
        .material()
        .register()
        .company_portfolios()
        .expect("portfolio register")
        .companies
        .iter()
        .find(|r| r.company == member.0)
        .expect("company evidence");
    let carrier = company_graph::company_key(scope, member.0);
    let draw = tick
        .graph_report()
        .report()
        .choice_receipts
        .iter()
        .find(|r| r.rule_id() == "company/portfolio-investment" && r.stable_carrier() == &carrier)
        .expect("real company choice");
    assert_eq!(draw.selected_outcome(), expected);
    let index = draw
        .branches()
        .iter()
        .position(|b| b.member == draw.selected_outcome())
        .expect("selected portfolio");
    assert!(row.weights[index] > 0 && row.feasible[index]);
    let plan = row.plans[index]
        .iter()
        .find(|r| r.site == member.1)
        .expect("selected plan for member");
    let need = row
        .processes
        .iter()
        .find(|r| r.site == plan.site && r.process == plan.process)
        .expect("selected process evidence");
    assert_eq!(need.free_cash.micro_units(), 0);
    assert_eq!(plan.replacement, 0);
    assert_eq!(
        plan.funding.micro_units(),
        i128::from(plan.expansion) * need.unit_price.micro_units()
    );
    assert!(row.treasury_available >= plan.funding);
    (row, plan)
}

fn investment<'a>(
    receipts: &'a MaterialTickReceipts,
    plan: &CompanyProcessPlan,
) -> &'a InvestmentReceipt {
    receipts
        .investment
        .iter()
        .find(|r| r.site_id == plan.site && r.process_id == plan.process)
        .expect("member equipment admission")
}

#[test]
#[ignore = "six complete national material and financial closes"]
fn governed_expansion_settles_at_the_site_and_follows_its_equipment_order() {
    let c = manufacturing_capture("opening_input_periods = 2", "opening_input_periods = 3");
    assert_eq!(c.compiler_version(), "national-world-v9");
    assert_eq!(
        babylon_tick::hex(&c.digest()),
        "c1cb5815ba16a9e9a02ccdb75cf45f4c5cf497aecbb26b0813fad712dff9868f"
    );
    let philadelphia = manufacturer(
        &c,
        "Manufacturing · Middle Atlantic",
        "representative manufacturing — Philadelphia County/BelowCellReserveRate",
    );
    let kodiak = manufacturer(
        &c,
        "Manufacturing · National 1",
        "representative manufacturing — Kodiak Island Borough/AtCellReserveRate",
    );
    let mut live = CapturedEconomicCatalog::decode(c.canonical_bytes(), c.digest())
        .expect("reopen national inputs")
        .create_foundation(
            ReplaySessionId::try_from("company-scale/qualification").expect("replay session"),
            ReplaySeed::new(2),
        )
        .expect("new national foundation")
        .into_session()
        .expect("live material session");
    let scope = live
        .graph_session()
        .stable_resolver()
        .scenario_scope()
        .to_owned();
    let mut books = CompanyBooks::open(&c, live.material().state()).expect("opening accounts");
    let mut philadelphia_plan = None;
    let mut kodiak_plan = None;
    let mut pending_order = None;

    for period in 1..=6 {
        let tick = super::super::prepare(&live);
        let opening = live.material().state();
        let closing = tick.material().register().state();
        let receipts = material_world::decode_material_receipts(tick.material().receipt_bytes())
            .expect("verified receipts");
        let reports = books
            .close(opening, closing, &receipts)
            .expect("reconcile all company accounts");
        let report = |company: CompanyId| {
            reports
                .iter()
                .find(|r| r.company == babylon_tick::hex(&company.as_bytes()))
                .expect("closed company accounts")
        };
        match period {
            3 => philadelphia_plan = Some(full_capacity_plan(&tick, &scope, philadelphia)),
            4 => {
                verify_refusal(
                    closing,
                    &receipts,
                    philadelphia.0,
                    philadelphia_plan.as_ref().expect("P3 Philadelphia plan"),
                    report(philadelphia.0),
                );
                kodiak_plan = Some(spare_capacity_plan(&tick, &scope, kodiak));
            }
            5 => {
                pending_order = Some(verify_purchase(
                    opening,
                    closing,
                    &receipts,
                    kodiak.0,
                    kodiak_plan.as_ref().expect("P4 Kodiak plan"),
                    report(kodiak.0),
                ))
            }
            6 => verify_local_transfer(
                &receipts,
                pending_order.as_ref().expect("P5 Kodiak equipment order"),
            ),
            _ => {}
        }
        live.commit_prepared_and_publish(&mut CollectingSink::default(), tick, |_, _| {
            Ok::<_, &str>(ReplayCommitDisposition::Committed)
        })
        .expect("publish closed period");
    }
}

fn full_capacity_plan(
    tick: &PreparedMaterialTick<HypergraphStore>,
    scope: &str,
    member: (CompanyId, SiteId),
) -> CompanyProcessPlan {
    let (row, plan) = selected_plan(tick, scope, member, "LARGER_EXPANSION");
    assert_eq!(row.condition, CompanyCondition::UnmetDemand);
    let produced: u64 = row.processes.iter().map(|p| p.produced_batches).sum();
    let capacity: u64 = row.processes.iter().map(|p| p.capacity_batches).sum();
    assert_eq!(produced, 2_132_920);
    assert_eq!(produced, capacity);
    assert_eq!(
        row.processes
            .iter()
            .map(|p| p.unmet_accepted_units)
            .sum::<u64>(),
        12_050_627
    );
    assert_eq!(row.history.len(), 3);
    assert!(row.history.iter().map(|r| r.micro_units()).sum::<i128>() > 0);
    assert_eq!(row.original_weights, [10, 10, 60, 20]);
    assert_eq!(row.weights, [10, 0, 60, 20]);
    assert_eq!(plan.expansion, 13_775);
    assert_eq!(plan.funding.micro_units(), 220_400_000_000_000);
    plan.clone()
}

fn verify_refusal(
    closing: &MaterialCircuitState,
    receipts: &MaterialTickReceipts,
    company: CompanyId,
    plan: &CompanyProcessPlan,
    group: &CompanyPeriod,
) {
    paid_contribution(receipts, company, plan, group);
    let declined = investment(receipts, plan);
    assert_eq!(declined.expansion_requested_units, 20_455);
    assert!(declined.earnings_budget.micro_units() >= declined.unit_price.micro_units());
    assert_eq!(declined.free_cash.micro_units(), 0);
    assert_eq!(declined.admitted_units, 0);
    assert!(!closing
        .orders
        .iter()
        .any(|r| r.order_id == declined.order_id));
    assert!(!receipts.money_transfers.iter().any(|r| r.purpose
        == MoneyTransferPurpose::PurchaseReservation(OutboundOrderId::Delivery(
            declined.order_id
        ))));
}

fn spare_capacity_plan(
    tick: &PreparedMaterialTick<HypergraphStore>,
    scope: &str,
    member: (CompanyId, SiteId),
) -> CompanyProcessPlan {
    let (row, plan) = selected_plan(tick, scope, member, "MODEST_EXPANSION");
    assert_eq!(row.condition, CompanyCondition::Spare);
    assert!(row
        .processes
        .iter()
        .any(|p| p.produced_batches < p.capacity_batches));
    assert_eq!(row.original_weights, [60, 25, 15, 0]);
    assert_eq!(row.weights, [60, 0, 15, 0]);
    assert_eq!(plan.expansion, 22);
    assert_eq!(plan.funding.micro_units(), 352_000_000_000);
    plan.clone()
}

fn verify_purchase(
    opening: &MaterialCircuitState,
    closing: &MaterialCircuitState,
    receipts: &MaterialTickReceipts,
    company: CompanyId,
    plan: &CompanyProcessPlan,
    group: &CompanyPeriod,
) -> OrderRow {
    let paid = settlement(receipts, company, plan, group);
    let purchase = investment(receipts, plan);
    assert_eq!(purchase.expansion_requested_units, 15);
    assert_eq!(purchase.free_cash.micro_units(), 24_506_887_187);
    assert_eq!(purchase.admitted_units, 1);
    assert_eq!(purchase.unit_price.micro_units(), 16_000_000_000);
    let site = site_financial_statements::project_period(opening, closing, receipts)
        .expect("reconcile site accounts")
        .statements
        .expect("monetary site accounts")
        .into_iter()
        .find(|r| r.site_id == plan.site)
        .expect("Kodiak statements");
    assert_eq!(site.income.contributions_received.micro_units(), paid);
    assert_eq!(site.cash_flow.investing.micro_units(), -16_000_000_000);
    let flows = site.cash_flow;
    assert_eq!(
        site.closing.cash.micro_units() - site.opening.cash.micro_units(),
        [
            flows.operating,
            flows.investing,
            flows.financing,
            flows.reserve_reclassification
        ]
        .iter()
        .map(|v| v.micro_units())
        .sum::<i128>()
    );
    println!("P5 Kodiak cash opened {} and closed {} micros, group cash opened {} and closed {} micros, group profit {} micros",
        site.opening.cash.micro_units(),site.closing.cash.micro_units(),
        group.consolidated.opening.cash.micro_units(), group.consolidated.closing.cash.micro_units(), group.consolidated.income.profit.micro_units());
    let order = closing
        .orders
        .iter()
        .find(|r| r.order_id == purchase.order_id)
        .expect("pending order");
    assert_eq!(order.buyer_site_id, plan.site);
    assert_eq!(order.supplier_site_id, purchase.supplier_site_id);
    assert_eq!((order.ordered, order.shipped, order.delivered), (1, 0, 0));
    order.clone()
}

fn verify_local_transfer(receipts: &MaterialTickReceipts, order: &OrderRow) {
    let transfers: Vec<_> = receipts
        .local_transfers
        .iter()
        .filter(|r| r.order_id == order.order_id)
        .collect();
    let [transfer] = transfers.as_slice() else {
        panic!("one identified local equipment transfer")
    };
    assert_eq!(transfer.buyer_site_id, order.buyer_site_id);
    assert_eq!(transfer.supplier_site_id, order.supplier_site_id);
    assert_eq!(
        (transfer.good_id, transfer.unit_id),
        (order.good_id, order.unit_id)
    );
    assert_eq!(transfer.quantity, order.ordered);
}
