//! Source-grounded legal and consolidated company reports.
mod carrying;
mod checkpoint;
mod entries;
pub use entries::{CompanyEntry, CompanyEntryKind};
mod cash;
mod endpoint;
mod income;
mod model;
mod period;
mod reader;
mod statements;
pub use period::CompanyBooks;
pub use statements::{
    CompanyBookPeriod, CompanyCashFlow, CompanyEliminations, CompanyIncome, CompanyPeriod,
    CompanyPeriodReport,
};
mod opening;
mod wire;

pub use model::{
    CompanyBalance, CompanyOpening, CompanyOpeningReport, CompanyStatementsError, EliminatedMember,
};
pub use opening::project_opening;
#[cfg(test)]
mod carrying_tests;
