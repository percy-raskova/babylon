//! Full-observer replay of the signed historical-cost difference through the selected close.
use super::{CompanyBooks, CompanyPeriodReport, CompanyStatementsError};
use crate::identity::CampaignId;
use crate::michigan_economy;
use crate::observer_reader::{ObserverEconomyError, ObserverEconomyReader, ObserverVisibility};

impl ObserverEconomyReader {
    /// Read the three parent and group statements for one committed positive period.
    /// # Errors
    /// Refuses a restricted observer, uncaptured company books or a broken source or equity bridge.
    pub fn company_period_statements(
        &self,
        campaign: CampaignId,
        period: u64,
    ) -> Result<CompanyPeriodReport, CompanyStatementsError> {
        if self.visibility() != ObserverVisibility::FullObserver {
            return Err(ObserverEconomyError::Authority.into());
        }
        if period == 0 || i64::try_from(period).is_err() {
            return Err(CompanyStatementsError::PeriodMismatch);
        }
        let mut cursor = None;
        let mut books = None;
        for tick in 1..=period {
            let report = self.with_committed_receipts(
                campaign,
                tick,
                &mut cursor,
                |cursor, foundation, source| {
                    let before = cursor.labor_opening(foundation)?.state();
                    let after = cursor
                        .current_register()
                        .ok_or(ObserverEconomyError::InvalidProjection)?
                        .state();
                    let capture = foundation
                        .foundation()
                        .graph_foundation()
                        .content_bundle()
                        .economic_catalog()
                        .ok_or(ObserverEconomyError::ScenarioMismatch)?;
                    let result = (|| {
                        if books.is_none() {
                            books = Some(CompanyBooks::open(
                                capture,
                                foundation.initial_register().state(),
                            )?);
                        }
                        let books = books
                            .as_mut()
                            .ok_or(CompanyStatementsError::PeriodMismatch)?;
                        if tick < period {
                            books.replay_earlier(before, after, &source.receipts)?;
                            return Ok(None);
                        }
                        let companies = books.close(before, after, &source.receipts)?;
                        Ok::<_, CompanyStatementsError>(Some(CompanyPeriodReport {
                            version: 1,
                            campaign: campaign.as_uuid().to_string(),
                            resolve_tick: tick,
                            foundation_sha256: michigan_economy::digest_hex(&foundation.digest()),
                            tick_content_hash: michigan_economy::digest_hex(
                                source.identity.tick_content_hash().as_bytes(),
                            ),
                            receipt_sha256: michigan_economy::digest_hex(
                                &source.identity.receipt_digest(),
                            ),
                            currency_unit: "micro".into(),
                            companies,
                        }))
                    })();
                    Ok(result)
                },
            )??;
            if let Some(report) = report {
                return Ok(report);
            }
        }
        Err(CompanyStatementsError::PeriodMismatch)
    }
}
