use super::reading::{Reading, Scope};
use super::worker::{AccountsView, Selection};
use crate::observer::{ObservationContext, Perspective};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{AccountId, IncomeReceipt, IncomeStatement, SiteId};
use babylon_persistence::identity::CampaignId;
use babylon_persistence::money_journal::{JournalError, PublishedSitePeriod};
use babylon_persistence::site_financial_statements::{
    SiteBalanceSheet, SiteCashFlowTotals, SiteStatementSummary,
};
use uuid::Uuid;

fn scope() -> Scope {
    Scope {
        reading: Reading::Accounts,
        context: ObservationContext {
            campaign: CampaignId::from_uuid(Uuid::from_u128(42)),
            perspective: Perspective::FullObserver,
            tick: 3,
            generation: 7,
        },
        site: SiteId::from_bytes([4; 32]),
        foundation: [5; 32],
        tick_hash: [6; 32],
    }
}

fn period(scope: &Scope) -> PublishedSitePeriod {
    PublishedSitePeriod {
        campaign_id: scope.context.campaign,
        site_id: scope.site,
        resolve_tick: scope.context.tick,
        foundation_sha256: scope.foundation,
        tick_content_hash: scope.tick_hash,
        receipt_sha256: [7; 32],
        statement: None,
        stocks: Vec::new(),
    }
}

#[test]
fn physical_books_keep_cash_unknown_and_replies_follow_the_selected_generation() {
    let scope = scope();
    let mut published = period(&scope);
    let physical = scope.describe(&published).expect("same committed frame");
    assert!(physical.contains("Physical books only"));
    assert!(!physical.contains('$'));
    published.tick_content_hash[0] ^= 1;
    assert_eq!(scope.describe(&published), Err(JournalError::SourceChanged));
    let mut view = AccountsView::default();
    let mut later = scope.clone();
    later.context.generation += 1;
    view.select(Selection::Period(later.clone()));
    view.receive(&scope, Ok(physical.clone()));
    assert!(!view.text().contains("Physical books only"));
    view.receive(&later, Err(JournalError::CoverageAbsent));
    assert!(view.text().contains("have not been published"));
    view.receive(&later, Ok(physical));
    assert!(view.text().contains("Physical books only"));
    let mut investment = later.clone();
    investment.reading = Reading::Investment(Vec::new());
    view.select(Selection::Period(investment.clone()));
    view.receive(&later, Ok("Stale financial statements".into()));
    assert_eq!(view.text(), "Reading the company’s investment decision…");
    view.receive(&investment, Ok("Committed investment choice".into()));
    assert_eq!(view.text(), "Committed investment choice");
    view.select(Selection::Opening);
    assert!(view.text().contains("first completed period"));
}

fn cash_sheet(cash: i128, purchase_reserves: i128, earnings: i128) -> SiteBalanceSheet {
    let zero = Currency::from_micro_units(0);
    let assets = cash + purchase_reserves + 9_750_000;
    SiteBalanceSheet {
        cash: Currency::from_micro_units(cash),
        purchase_reserves: Currency::from_micro_units(purchase_reserves),
        payroll_reserves: Currency::from_micro_units(250_000),
        wage_receivables: Currency::from_micro_units(500_000),
        inventory: Currency::from_micro_units(2_000_000),
        freight: Currency::from_micro_units(4_000_000),
        equity_investments: zero,
        equipment: Currency::from_micro_units(3_000_000),
        total_assets: Currency::from_micro_units(assets),
        wage_payables: Currency::from_micro_units(300_000),
        total_liabilities: Currency::from_micro_units(300_000),
        opening_capital: Currency::from_micro_units(19_450_000),
        contributed_capital: zero,
        retained_earnings: Currency::from_micro_units(earnings),
        total_equity: Currency::from_micro_units(assets - 300_000),
    }
}

fn sale_with_cash_dividend(site: SiteId) -> IncomeReceipt {
    let zero = Currency::from_micro_units(0);
    let sale = Currency::from_micro_units(2_000_001);
    IncomeReceipt {
        account: AccountId::Site(site),
        period: 3,
        opening_capital: Currency::from_micro_units(19_450_000),
        opening_retained_earnings: zero,
        opening_contributed_capital: zero,
        contributions_received: zero,
        closing_contributed_capital: zero,
        distributions_paid: Currency::from_micro_units(3_000_000),
        net_income: Currency::from_micro_units(1_250_001),
        closing_retained_earnings: Currency::from_micro_units(-1_749_999),
        statement: IncomeStatement {
            sales: sale,
            wage_income: zero,
            cost_of_goods_sold: zero,
            productive_labor_capitalized: Currency::from_micro_units(750_000),
            installation_labor_capitalized: zero,
            equipment_wear_capitalized: zero,
            idle_labor_expense: zero,
            handling_expense: zero,
            maintenance_labor_expense: Currency::from_micro_units(250_000),
            maintenance_material_expense: zero,
            freight_loss_expense: zero,
            consumption_expense: zero,
            final_demand_outlay: zero,
            unused_service_expense: zero,
            tax_income: zero,
            tax_expense: Currency::from_micro_units(500_000),
            public_transfer_income: zero,
            public_transfer_expense: zero,
            distribution_income: zero,
            gift_income: zero,
            gift_expense: zero,
            agency_observation_labor_expense: zero,
        },
    }
}

#[test]
fn cash_dividend_separates_profit_from_cash_change_and_earnings() {
    let scope = scope();
    let mut published = period(&scope);
    let income = sale_with_cash_dividend(scope.site);
    let zero = Currency::from_micro_units(0);
    published.statement = Some(SiteStatementSummary {
        site_id: scope.site,
        opening: cash_sheet(10_000_000, 0, 0),
        closing: cash_sheet(7_250_001, 1_000_000, -1_749_999),
        change_in_equity: income.closing_retained_earnings,
        cash_flow: SiteCashFlowTotals {
            operating: income.net_income,
            investing: zero,
            financing: Currency::from_micro_units(-3_000_000),
            reserve_reclassification: Currency::from_micro_units(-1_000_000),
        },
        income,
    });
    let text = scope.describe(&published).expect("admitted site and frame");
    assert!(text.contains(concat!(
        "Net profit or loss  $1.250001\n\n",
        "Capitalized costs\n",
        "Production labor capitalized  $0.75\n\n",
        "Equity movements\n",
        "Distributions paid  $3.00\n",
        "Change in equity  -$1.749999\n\n",
        "Cash flow · spendable cash\n",
    )));
    for line in [
        "Spendable cash  $10.00 → $7.250001",
        "Change in cash  -$2.749999",
        "Tax expense  $0.50",
        "Net profit or loss  $1.250001",
        "Distributions paid  $3.00",
        "Assets  $19.75 → $18.000001",
        "Retained earnings  $0.00 → -$1.749999",
        "Operating  $1.250001",
        "Financing  -$3.00",
        "Purchase reserves  $0.00 → $1.00",
        "Payroll reserves  $0.25 → $0.25",
        "Wage receivables  $0.50 → $0.50",
        "Wage payables  $0.30 → $0.30",
        "Equipment  $3.00 → $3.00",
        "Inventory  $2.00 → $2.00",
        "Cargo in transit  $4.00 → $4.00",
        "Maintenance labor expense  $0.25",
        "Reserve reclassification  -$1.00",
    ] {
        assert!(text.lines().any(|actual| actual == line), "{line}");
    }
}
