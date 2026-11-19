//! Display the selected site's authenticated income, balance sheet and cash-flow totals.
use babylon_kernel::currency::Currency;
use babylon_material_circuit::SiteId;
use babylon_persistence::money_journal::{JournalError, PublishedSitePeriod};
use babylon_persistence::observer_reader::ObserverEconomyReader;
use babylon_persistence::site_financial_statements::{SiteBalanceSheet, SiteStatementSummary};
use std::fmt::Write as _;

use crate::company_investment::ProcessLabel;
use crate::human_numbers;
use crate::observer::ObservationContext;

#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) struct Scope {
    pub(super) reading: Reading,
    pub(super) context: ObservationContext,
    pub(super) site: SiteId,
    pub(super) foundation: [u8; 32],
    pub(super) tick_hash: [u8; 32],
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(super) enum Reading {
    Accounts,
    Investment(Vec<ProcessLabel>),
}

impl Scope {
    pub(super) fn read_accounts(&self) -> Result<String, JournalError> {
        let reader = ObserverEconomyReader::from_observer_env().map_err(JournalError::Observer)?;
        let period =
            reader.published_site_period(self.context.campaign, self.context.tick, self.site)?;
        self.describe(&period)
    }

    pub(super) fn describe(&self, period: &PublishedSitePeriod) -> Result<String, JournalError> {
        if period.campaign_id != self.context.campaign
            || period.resolve_tick != self.context.tick
            || period.site_id != self.site
            || period.foundation_sha256 != self.foundation
            || period.tick_content_hash != self.tick_hash
        {
            return Err(JournalError::SourceChanged);
        }
        let Some(books) = &period.statement else {
            return Ok(format!(
                "Physical books only\n{} physical stock lines. This period has no monetary statements.",
                period.stocks.len()
            ));
        };
        let change = books
            .closing
            .cash
            .checked_sub(books.opening.cash)
            .map_err(|_| JournalError::Projection)?;

        let mut text = String::from("Balance sheet · opening → closing\n");
        balance_sheet(&mut text, &books.opening, &books.closing);
        text.push_str("\nIncome statement\n");
        income_statement(&mut text, books);
        text.push_str("\nCash flow · spendable cash\n");
        let flow = &books.cash_flow;
        for (label, amount) in [
            ("Operating", flow.operating),
            ("Investing", flow.investing),
            ("Financing", flow.financing),
            ("Reserve reclassification", flow.reserve_reclassification),
            ("Change in cash", change),
        ] {
            amount_line(&mut text, label, amount);
        }
        text.push_str("Spendable cash excludes purchase and payroll reserves.");
        Ok(text)
    }
}

fn balance_sheet(text: &mut String, opening: &SiteBalanceSheet, closing: &SiteBalanceSheet) {
    for (label, start, end) in [
        ("Spendable cash", opening.cash, closing.cash),
        (
            "Purchase reserves",
            opening.purchase_reserves,
            closing.purchase_reserves,
        ),
        (
            "Payroll reserves",
            opening.payroll_reserves,
            closing.payroll_reserves,
        ),
        ("Inventory", opening.inventory, closing.inventory),
        ("Cargo in transit", opening.freight, closing.freight),
        ("Equipment", opening.equipment, closing.equipment),
        (
            "Wage receivables",
            opening.wage_receivables,
            closing.wage_receivables,
        ),
        (
            "Equity investments",
            opening.equity_investments,
            closing.equity_investments,
        ),
        ("Assets", opening.total_assets, closing.total_assets),
        (
            "Wage payables",
            opening.wage_payables,
            closing.wage_payables,
        ),
        (
            "Liabilities",
            opening.total_liabilities,
            closing.total_liabilities,
        ),
        (
            "Opening capital",
            opening.opening_capital,
            closing.opening_capital,
        ),
        (
            "Contributed capital",
            opening.contributed_capital,
            closing.contributed_capital,
        ),
        (
            "Retained earnings",
            opening.retained_earnings,
            closing.retained_earnings,
        ),
        ("Equity", opening.total_equity, closing.total_equity),
    ] {
        writeln!(text, "{label}  {} → {}", money(start), money(end)).expect("String write");
    }
}

fn income_statement(text: &mut String, books: &SiteStatementSummary) {
    let income = &books.income;
    let statement = &income.statement;
    amount_line(text, "Sales", statement.sales);
    amount_line(text, "Cost of goods sold", statement.cost_of_goods_sold);
    amount_line(text, "Tax expense", statement.tax_expense);
    for (label, amount) in [
        ("Wage income", statement.wage_income),
        ("Tax income", statement.tax_income),
        (
            "Public transfers received",
            statement.public_transfer_income,
        ),
        ("Distributions received", statement.distribution_income),
        ("Gifts received", statement.gift_income),
        ("Idle labor expense", statement.idle_labor_expense),
        ("Handling expense", statement.handling_expense),
        (
            "Maintenance labor expense",
            statement.maintenance_labor_expense,
        ),
        (
            "Maintenance material expense",
            statement.maintenance_material_expense,
        ),
        ("Freight loss expense", statement.freight_loss_expense),
        ("Consumption expense", statement.consumption_expense),
        ("Final demand outlay", statement.final_demand_outlay),
        ("Unused service expense", statement.unused_service_expense),
        ("Public transfers paid", statement.public_transfer_expense),
        ("Gift expense", statement.gift_expense),
        (
            "Agency observation labor expense",
            statement.agency_observation_labor_expense,
        ),
    ] {
        if amount.micro_units() != 0 {
            amount_line(text, label, amount);
        }
    }
    amount_line(text, "Net profit or loss", income.net_income);
    supplemental_section(
        text,
        "Capitalized costs",
        [
            (
                "Production labor capitalized",
                statement.productive_labor_capitalized,
            ),
            (
                "Installation labor capitalized",
                statement.installation_labor_capitalized,
            ),
            (
                "Equipment wear capitalized",
                statement.equipment_wear_capitalized,
            ),
        ],
    );
    supplemental_section(
        text,
        "Equity movements",
        [
            (
                "Capital contributions received",
                income.contributions_received,
            ),
            ("Distributions paid", income.distributions_paid),
            ("Change in equity", books.change_in_equity),
        ],
    );
}

fn supplemental_section(text: &mut String, title: &str, rows: [(&str, Currency); 3]) {
    let mut nonzero = rows
        .into_iter()
        .filter(|(_, amount)| amount.micro_units() != 0)
        .peekable();
    if nonzero.peek().is_some() {
        writeln!(text, "\n{title}").expect("String write");
        for (label, amount) in nonzero {
            amount_line(text, label, amount);
        }
    }
}

fn amount_line(text: &mut String, label: &str, value: Currency) {
    writeln!(text, "{label}  {}", money(value)).expect("String write");
}

fn money(amount: Currency) -> String {
    human_numbers::currency(amount.micro_units())
}
