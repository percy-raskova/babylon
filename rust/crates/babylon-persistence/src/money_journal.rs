//! Versioned PostgreSQL money movement facts from authenticated committed receipts.
//! The database owner publishes; the full observer can only read. This journal never
//! participates in adjudication. All micros and SQL sums are exact decimal strings.
mod company_books;
mod company_dimensions;

mod county_accounts;
mod flow_model;
mod flow_query;
#[cfg(test)]
mod labor_fact_tests;
mod labor_facts;
mod labor_flows;
mod labor_replay;
mod labor_source;
mod labor_storage;
mod labor_verification;
mod model;
mod payment_storage;
mod queue;
mod statement_integrity;
mod statement_lines;
mod statement_read;
mod statement_storage;
mod storage;
#[cfg(test)]
mod tests;

pub use company_books::SelectedCompanyAccounts;
pub use county_accounts::{CountySiteAccounts, CountySitePage};
pub use flow_model::{
    FlowAmounts, FlowDirection, FlowGroup, FlowPage, FlowPeer, FlowQuery, FlowRow, FlowViewport,
    PeriodWindow,
};
pub(crate) use labor_facts::LaborFacts;
pub use labor_flows::{LaborAmount, LaborDirections, LaborFlowPage, LaborFlowRow};
pub(crate) use labor_replay::{through as read_labor_through, LaborCarry};
pub use model::{
    derive_movements, JournalError, MoneyEndpoint, MoneyLocationKind, MoneyMovement, MoneyPurpose,
    MoneyReference, MoneyReferenceKind, MoneyTotal, PublishReport,
};
pub use queue::{JournalQueue, JournalQueueError};
pub use statement_read::PublishedSitePeriod;
pub(crate) use statement_storage::JournalPeriodSource;
pub(crate) use storage::VIEWS;
pub use storage::{prune_money_journal_detail, MoneyJournalWriter};
