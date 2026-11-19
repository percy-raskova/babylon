//! Named native NUMERIC columns shared by the bulk serializer and selected-site reader.
use super::JournalError;
use crate::site_financial_statements::{
    SiteBalanceSheet, SiteCashFlowTotals, SiteStatementSummary,
};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{AccountId, IncomeReceipt, IncomeStatement, SiteId};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

#[derive(Default, Serialize, Deserialize)]
#[serde(transparent)]
pub(super) struct Lines(BTreeMap<String, String>);
impl Lines {
    fn put(&mut self, name: String, value: Currency) {
        self.0.insert(name, value.micro_units().to_string());
    }
    fn money(&self, name: &str) -> Result<Currency, JournalError> {
        self.0
            .get(name)
            .ok_or(JournalError::Projection)?
            .parse::<i128>()
            .map(Currency::from_micro_units)
            .map_err(|_| JournalError::Projection)
    }
}

trait MoneyLines: Sized {
    fn write(&self, prefix: &str, target: &mut Lines);
    fn read(prefix: &str, source: &Lines) -> Result<Self, JournalError>;
}

// Each domain field is declared once for the two directions of the v1 SQL contract.
macro_rules! money_lines {
    ($row:ty, $($field:ident),+ $(,)?) => {
        impl MoneyLines for $row {
            fn write(&self, prefix: &str, target: &mut Lines) {
                $(target.put(format!("{prefix}_{}_micros", stringify!($field)), self.$field);)+
            }
            fn read(prefix: &str, source: &Lines) -> Result<Self, JournalError> {
                Ok(Self { $($field: source.money(&format!("{prefix}_{}_micros", stringify!($field)))?,)+ })
            }
        }
    };
}
money_lines!(
    SiteBalanceSheet,
    cash,
    purchase_reserves,
    payroll_reserves,
    wage_receivables,
    inventory,
    freight,
    equity_investments,
    equipment,
    total_assets,
    wage_payables,
    total_liabilities,
    opening_capital,
    contributed_capital,
    retained_earnings,
    total_equity
);
money_lines!(
    IncomeStatement,
    sales,
    wage_income,
    cost_of_goods_sold,
    productive_labor_capitalized,
    installation_labor_capitalized,
    equipment_wear_capitalized,
    idle_labor_expense,
    handling_expense,
    maintenance_labor_expense,
    maintenance_material_expense,
    freight_loss_expense,
    consumption_expense,
    final_demand_outlay,
    unused_service_expense,
    tax_income,
    tax_expense,
    public_transfer_income,
    public_transfer_expense,
    distribution_income,
    gift_income,
    gift_expense,
    agency_observation_labor_expense
);
money_lines!(
    SiteCashFlowTotals,
    operating,
    investing,
    financing,
    reserve_reclassification
);

impl Lines {
    pub(super) fn from_summary(row: &SiteStatementSummary) -> Self {
        let mut lines = Self::default();
        row.opening.write("opening", &mut lines);
        row.closing.write("closing", &mut lines);
        row.income.statement.write("income", &mut lines);
        row.cash_flow.write("cash_flow", &mut lines);
        for (name, amount) in [
            ("net_income_micros", row.income.net_income),
            (
                "contributions_received_micros",
                row.income.contributions_received,
            ),
            ("distributions_paid_micros", row.income.distributions_paid),
            ("change_in_equity_micros", row.change_in_equity),
        ] {
            lines.put(name.to_owned(), amount);
        }
        lines
    }

    pub(super) fn to_summary(
        &self,
        site_id: SiteId,
        period: u64,
    ) -> Result<SiteStatementSummary, JournalError> {
        let opening = SiteBalanceSheet::read("opening", self)?;
        let closing = SiteBalanceSheet::read("closing", self)?;
        // The authenticated income bridge equates these five capital/earnings figures to the sheets.
        let income = IncomeReceipt {
            account: AccountId::Site(site_id),
            period,
            opening_capital: opening.opening_capital,
            opening_contributed_capital: opening.contributed_capital,
            closing_contributed_capital: closing.contributed_capital,
            opening_retained_earnings: opening.retained_earnings,
            closing_retained_earnings: closing.retained_earnings,
            contributions_received: self.money("contributions_received_micros")?,
            distributions_paid: self.money("distributions_paid_micros")?,
            net_income: self.money("net_income_micros")?,
            statement: IncomeStatement::read("income", self)?,
        };
        income.validate().map_err(|_| JournalError::Projection)?;
        Ok(SiteStatementSummary {
            site_id,
            opening,
            closing,
            income,
            change_in_equity: self.money("change_in_equity_micros")?,
            cash_flow: SiteCashFlowTotals::read("cash_flow", self)?,
        })
    }
}
