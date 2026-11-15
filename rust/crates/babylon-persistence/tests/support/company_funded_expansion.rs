//! A separately captured national manufacturing stress case follows one real company decision.
use babylon_bsl::structural_verbs::CollectingSink;
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_material_circuit::{
    AccountId, CashTransferPurpose, CircuitAccounting, CompanyCondition, CompanyId,
    CompanyProcessPlan, MoneyLocation, MoneyTransferPurpose, OutboundOrderId, SiteId,
};
use babylon_persistence::company_statements::{CompanyBooks, CompanyEntryKind, CompanyPeriod};
use babylon_persistence::economic_catalog::{
    self, CapturedEconomicCatalog, SourceArtifact, SourceArtifactKind,
};
use babylon_persistence::site_financial_statements;
use babylon_tick::company_graph;
use babylon_tick::material_replay::PreparedMaterialTick;
use babylon_tick::material_world::{self, MaterialTickReceipts};
use babylon_tick::replay_session::ReplayCommitDisposition;
use serde_json::json;

fn replace(text: &mut String, old: &str, new: &str) {
    assert_eq!(
        text.matches(old).count(),
        1,
        "unique national policy term {old}"
    );
    *text = text.replacen(old, new, 1);
}

fn reprice(text: &mut String, good: &str, multiple: u64) {
    let start = text
        .find(&format!("[commodity.{good}]\n"))
        .expect("authored commodity");
    let end = start + text[start..].find("\n\n").expect("end of commodity");
    let mut table = text[start..end].to_owned();
    for field in [
        "opening_price_micros",
        "minimum_price_micros",
        "maximum_price_micros",
        "price_step_micros",
    ] {
        let value = table
            .lines()
            .find_map(|line| line.strip_prefix(&format!("{field} = ")))
            .expect("authored price")
            .parse::<u64>()
            .expect("integer micros");
        replace(
            &mut table,
            &format!("{field} = {value}"),
            &format!("{field} = {}", value * multiple),
        );
    }
    text.replace_range(start..end, &table);
}

fn capture() -> CapturedEconomicCatalog {
    let mut input = economic_catalog::national_catalog_input();
    let source = input
        .sources
        .iter_mut()
        .find(|s| s.kind() == SourceArtifactKind::NationalGamePolicy)
        .expect("national policy");
    let mut text = std::str::from_utf8(source.bytes())
        .expect("policy text")
        .to_owned();
    // Scarce supplies made from costly feedstock sustain funded orders for the manufacturer.
    replace(
        &mut text,
        "inputs = { resource_deposit = 8, utility = 1, business_services = 1 }",
        "inputs = { resource_deposit = 8 }",
    );
    replace(
        &mut text,
        "[process.manufacturing]\noutput = \"materials\"\noutput_units_per_batch = 8",
        "[process.manufacturing]\noutput = \"materials\"\noutput_units_per_batch = 1",
    );
    replace(
        &mut text,
        "inputs = { resources = 8, utility = 2, business_services = 1 }",
        "inputs = { resources = 1 }",
    );
    reprice(&mut text, "resources", 12);
    reprice(&mut text, "materials", 10);
    // Smaller, more expensive machines increase the capital required to serve the backlog.
    // The founding sweep pools the opening surplus and protects the usual payroll floors.
    reprice(&mut text, "equipment", 4);
    for (old, new) in [
        (
            "batches_per_unit_per_period = 40",
            "batches_per_unit_per_period = 1",
        ),
        (
            "installation_workforce_hours_bps = 625",
            "installation_workforce_hours_bps = 5000",
        ),
        (
            "expansion_earnings_fraction_bps = 2500",
            "expansion_earnings_fraction_bps = 10000",
        ),
        (
            "opening_treasury_bps = 1000",
            "opening_treasury_bps = 10000",
        ),
    ] {
        replace(&mut text, old, new);
    }
    *source = SourceArtifact::capture(source.kind(), text.into_bytes());
    CapturedEconomicCatalog::capture(input, None)
        .expect("separately identified national company capture")
}

#[test]
#[ignore = "five complete national material and financial closes"]
fn high_demand_company_funds_an_admitted_equipment_purchase() {
    let c = capture();
    let roster = c.national_companies().expect("company capture");
    assert_eq!(roster.companies.len(), 99);
    let company = roster
        .companies
        .iter()
        .find(|c| c.key.label() == "Manufacturing · West South Central")
        .expect("named regional manufacturer")
        .key
        .id();
    let site = c
        .opening()
        .sites
        .iter()
        .find(|s| {
            babylon_tick::hex(&s.site_id.as_bytes())
                == "ca0e59c3dbccc25e466dc7738da5f4ea4ac8d2ec8d454dae7e372f9091dc914b"
        })
        .expect("funded operating site");
    let member = roster
        .members
        .iter()
        .find(|r| r.site == site.site_id)
        .expect("site belongs to the capture");
    assert_eq!(member.company.id(), company);
    let params = CapturedEconomicCatalog::decode(c.canonical_bytes(), c.digest())
        .expect("reopen controlled inputs");
    let mut live = params
        .create_foundation(
            ReplaySessionId::try_from("company-scale/qualification")
                .expect("stable replay session"),
            ReplaySeed::new(2),
        )
        .expect("new national foundation")
        .into_session()
        .expect("live material session");
    let mut books =
        CompanyBooks::open(&c, live.material().state()).expect("opening legal and group accounts");
    let mut prior_plan = None;
    for period in 1..=5 {
        let tick = super::prepare(&live);
        let opening = live.material().state();
        let closed = tick.material().register();
        let receipts = material_world::decode_material_receipts(tick.material().receipt_bytes())
            .expect("verified material receipt contents");
        let report = books
            .close(opening, closed.state(), &receipts)
            .expect("company books reconcile every period")
            .into_iter()
            .find(|r| r.company == babylon_tick::hex(&company.as_bytes()))
            .expect("company report");
        if period == 4 {
            println!(
                "{}",
                json!({"capture":babylon_tick::hex(&c.digest()), "county":member.county.as_str(), "site":site.label})
            );
            prior_plan = Some(decision(
                &tick,
                live.graph_session().stable_resolver().scenario_scope(),
                company,
                site.site_id,
                &report,
            ));
        }
        if period == 5 {
            let plan = prior_plan.as_ref().expect("previous portfolio plan");
            let summary =
                site_financial_statements::project_period(opening, closed.state(), &receipts)
                    .expect("site accounts reconcile")
                    .statements
                    .expect("monetary site statements")
                    .into_iter()
                    .find(|r| r.site_id == site.site_id)
                    .expect("funded site's statement");
            let paid = settlement(&receipts, company, plan, &report);
            assert_eq!(summary.income.contributions_received.micro_units(), paid);
            println!(
                "{}",
                json!({
                    "period":period,
                    "world":babylon_tick::hex(&tick.identity().result_world_hash()),
                    "receipts":babylon_tick::hex(&tick.identity().receipt_digest()),
                    "site_opening_cash_micros":summary.opening.cash.micro_units().to_string(),
                    "site_closing_cash_micros":summary.closing.cash.micro_units().to_string(),
                    "site_investing_micros":summary.cash_flow.investing.micro_units().to_string(),
                    "parent_profit_micros":report.parent.income.profit.micro_units().to_string(),
                    "consolidated_profit_micros":report.consolidated.income.profit.micro_units().to_string(),
                    "consolidated_contribution_micros":report.consolidated.income.contributions.micro_units().to_string()
                })
            );
        }
        live.commit_prepared_and_publish(&mut CollectingSink::default(), tick, |_, _| {
            Ok::<_, &str>(ReplayCommitDisposition::Committed)
        })
        .expect("publish real close");
    }
}

fn decision(
    tick: &PreparedMaterialTick<HypergraphStore>,
    scope: &str,
    company: CompanyId,
    site: SiteId,
    report: &CompanyPeriod,
) -> CompanyProcessPlan {
    let closed = tick.material().register();
    let period = tick.identity().resolve_tick();
    let row = closed
        .company_portfolios()
        .expect("portfolio evidence")
        .companies
        .iter()
        .find(|r| r.company == company)
        .expect("regional manufacturer's portfolio evidence");
    let use_batches: u64 = row.processes.iter().map(|p| p.produced_batches).sum();
    let capacity: u64 = row.processes.iter().map(|p| p.capacity_batches).sum();
    let unmet: u64 = row.processes.iter().map(|p| p.unmet_accepted_units).sum();
    let income: i128 = row.history.iter().map(|v| v.micro_units()).sum();
    assert_eq!(row.history.len(), 3);
    assert!(income > 0 && u128::from(use_batches) * 100 >= u128::from(capacity) * 80 && unmet > 0);
    assert_eq!(row.condition, CompanyCondition::UnmetDemand);
    assert_eq!(row.original_weights, [10, 10, 60, 20]);
    assert_eq!(row.weights, [10, 0, 60, 20]);
    assert_eq!(row.feasible, [true, false, true, true]);
    let carrier = company_graph::company_key(scope, company);
    let choice = tick
        .graph_report()
        .report()
        .choice_receipts
        .iter()
        .find(|r| r.rule_id() == "company/portfolio-investment" && r.stable_carrier() == &carrier)
        .expect("recorded company draw");
    assert_eq!(choice.branches().len(), 4);
    assert_eq!(choice.selected_outcome(), "LARGER_EXPANSION");
    let plan = row.plans[3]
        .iter()
        .find(|p| p.site == site)
        .expect("selected site plan");
    let need = row
        .processes
        .iter()
        .find(|p| p.site == plan.site && p.process == plan.process)
        .expect("selected process has recorded need");
    assert_eq!(plan.replacement, 0);
    assert!(plan.expansion > 0 && plan.funding.micro_units() > 0);
    let cost = i128::from(plan.expansion) * need.unit_price.micro_units();
    assert_eq!(
        cost,
        need.free_cash.micro_units() + plan.funding.micro_units()
    );
    assert!(row.treasury_available >= plan.funding);
    let CircuitAccounting::Monetary(money) = &closed.state().accounting else {
        panic!("national monetary books")
    };
    assert!(
        !money
            .financial
            .contributions
            .iter()
            .any(|order| order.issuer_site_id == plan.site
                && order.contributor == AccountId::Company(company)),
        "no standing capital contribution before the portfolio"
    );
    println!(
        "{}",
        json!({
            "period":period,
            "seed":2,
            "world":babylon_tick::hex(&tick.identity().result_world_hash()),
            "receipts":babylon_tick::hex(&tick.identity().receipt_digest()),
            "company":"Manufacturing · West South Central",
            "company_id":report.company,
            "site_id":babylon_tick::hex(&site.as_bytes()),
            "process":babylon_tick::hex(&plan.process.as_bytes()),
            "produced_batches":use_batches,
            "capacity_batches":capacity,
            "unmet_accepted_units":unmet,
            "member_operating_income_micros":row.history.iter().map(|v|v.micro_units().to_string()).collect::<Vec<_>>(),
            "consolidated_current_profit_micros":report.consolidated.income.profit.micro_units().to_string(),
            "designed_weights":row.original_weights,
            "eligible_weights":row.weights,
            "draw":choice.draw_ticket(),
            "selection":choice.selected_outcome(),
            "site_requested_expansion":need.expansion,
            "selected_expansion_limit":plan.expansion,
            "site_spendable_micros":need.free_cash.micro_units().to_string(),
            "treasury_available_micros":row.treasury_available.micro_units().to_string(),
            "selected_funding_micros":plan.funding.micro_units().to_string(),
            "price_micros":need.unit_price.micro_units().to_string()
        })
    );
    plan.clone()
}

fn settlement(
    receipts: &MaterialTickReceipts,
    company: CompanyId,
    plan: &CompanyProcessPlan,
    report: &CompanyPeriod,
) -> i128 {
    let site = plan.site;
    let mut entries =
        receipts.contributions.iter().enumerate().filter(|(_, r)| {
            r.contributor == AccountId::Company(company) && r.issuer_site_id == site
        });
    let (ordinal, contribution) = entries.next().expect("capital contribution");
    assert!(entries.next().is_none());
    assert_eq!(contribution.requested, plan.funding);
    assert_eq!(contribution.paid, plan.funding);
    assert_eq!(contribution.unfunded.micro_units(), 0);
    let paid = contribution.paid.micro_units();
    let posting = receipts
        .money_transfers
        .iter()
        .find(|r| {
            r.purpose == MoneyTransferPurpose::Cash(CashTransferPurpose::CapitalContribution)
                && r.credit.location == MoneyLocation::Cash(AccountId::Site(site))
                && r.debit.location == MoneyLocation::Cash(AccountId::Company(company))
        })
        .expect("parent cash debited and site credited");
    assert_eq!(posting.debit.delta.micro_units(), -paid);
    assert_eq!(posting.credit.delta.micro_units(), paid);
    let elimination = report
        .entries
        .iter()
        .find(|e| {
            e.family == 27
                && e.ordinal == ordinal as u64
                && e.kind == CompanyEntryKind::Contribution
        })
        .expect("internal contribution removed");
    assert_eq!(elimination.amount_micros, paid.to_string());
    assert_eq!(report.consolidated.income.contributions.micro_units(), 0);
    assert_eq!(
        report.parent.closing.cash.micro_units() + report.subsidiaries.closing.cash.micro_units(),
        report.consolidated.closing.cash.micro_units()
    );
    let purchase = receipts
        .investment
        .iter()
        .find(|r| r.site_id == site && r.process_id == plan.process)
        .expect("member investment receipt");
    assert!(purchase.admitted_units > 0 && purchase.admitted_units <= plan.expansion);
    assert_eq!(purchase.replacement_requested_units, 0);
    let amount = i128::from(purchase.admitted_units) * purchase.unit_price.micro_units();
    let reservation = receipts
        .money_transfers
        .iter()
        .find(|r| {
            r.purpose
                == MoneyTransferPurpose::PurchaseReservation(OutboundOrderId::Delivery(
                    purchase.order_id,
                ))
        })
        .expect("cash actually reserved against the new order");
    assert_eq!(
        reservation.debit.location,
        MoneyLocation::Cash(AccountId::Site(site))
    );
    assert_eq!(reservation.debit.delta.micro_units(), -amount);
    println!(
        "{}",
        json!({
            "period":receipts.resolve_tick,
            "contribution_id":babylon_tick::hex(&contribution.id.as_bytes()),
            "order_id":babylon_tick::hex(&purchase.order_id.as_bytes()),
            "requested_contribution_micros":contribution.requested.micro_units().to_string(),
            "paid_contribution_micros":paid.to_string(),
            "group_eliminated_contributions_micros":report.eliminations.contributions.micro_units().to_string(),
            "equipment_requested":purchase.expansion_requested_units,
            "equipment_admitted":purchase.admitted_units,
            "unit_price_micros":purchase.unit_price.micro_units().to_string(),
            "cash_reserved_micros":amount.to_string()
        })
    );
    paid
}
