//! Display independently authenticated income, balance sheet and cash-flow totals.
use babylon_kernel::currency::Currency;
use babylon_material_circuit::SiteId;
use babylon_persistence::money_journal::{JournalError, PublishedSitePeriod};
use babylon_persistence::observer_reader::ObserverEconomyReader;

use crate::company_investment::{self, ProcessLabel, Subject};
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
    pub(super) fn read(&self) -> Result<String, JournalError> {
        let reader = ObserverEconomyReader::from_observer_env().map_err(JournalError::Observer)?;
        if let Reading::Investment(labels) = &self.reading {
            return company_investment::read(
                &reader,
                &self.context,
                self.foundation,
                self.tick_hash,
                Subject::Site(self.site, labels),
            );
        }
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
        let opening = &books.opening;
        let closing = &books.closing;
        let income = &books.income;
        let flows = &books.cash_flow;
        let change = closing
            .cash
            .checked_sub(opening.cash)
            .map_err(|_| JournalError::Projection)?;
        Ok(format!(
            "Spendable cash  {}\nOpening cash  {}\nChange in cash  {}\n\nIncome statement\nSales  {}\nCost of goods sold  {}\nNet profit or loss  {}\n\nClosing balance sheet\nAssets  {}\nLiabilities  {}\nEquity  {}\nRetained earnings  {}\n\nCash flow\nOperating  {}\nInvesting  {}\nFinancing  {}\nReserve reclassification  {}",
            money(closing.cash), money(opening.cash), money(change), money(income.statement.sales),
            money(income.statement.cost_of_goods_sold), money(income.net_income),
            money(closing.total_assets), money(closing.total_liabilities), money(closing.total_equity),
            money(closing.retained_earnings), money(flows.operating), money(flows.investing),
            money(flows.financing), money(flows.reserve_reclassification),
        ))
    }
}

fn money(amount: Currency) -> String {
    human_numbers::currency(amount.micro_units())
}
