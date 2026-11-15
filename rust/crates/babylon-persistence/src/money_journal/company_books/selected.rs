//! Select one company from the complete source-bound financial period.
use crate::company_statements::{CompanyBookPeriod, CompanyEliminations};
use crate::identity::CampaignId;
use crate::money_journal::JournalError;
use crate::observer_reader::ObserverEconomyReader;
use crate::qualification_audit::trade;
use babylon_material_circuit::CompanyId;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SelectedCompanyAccounts {
    pub parent: CompanyBookPeriod,
    pub consolidated: CompanyBookPeriod,
    pub eliminations: CompanyEliminations,
}

impl ObserverEconomyReader {
    /// Verify the published period digest, bind it to the observed frame and select one company.
    /// # Errors
    /// Refuses restricted readers, missing company books, stale frames and changed published facts.
    pub fn company_accounts_for_frame(
        &self,
        campaign: CampaignId,
        tick: u64,
        company: CompanyId,
        foundation: &str,
        tick_hash: &str,
    ) -> Result<SelectedCompanyAccounts, JournalError> {
        let report = self.published_company_period_statements(campaign, tick)?;
        if report.foundation_sha256 != foundation || report.tick_content_hash != tick_hash {
            return Err(JournalError::SourceChanged);
        }
        let key = trade::hex(&company.as_bytes());
        let books = report
            .companies
            .into_iter()
            .find(|row| row.company == key)
            .ok_or(JournalError::Projection)?;
        Ok(SelectedCompanyAccounts {
            parent: books.parent,
            consolidated: books.consolidated,
            eliminations: books.eliminations,
        })
    }
}
