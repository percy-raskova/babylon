//! Versioned, full-observer labor history from the captured foundation and committed receipts.
use crate::identity::CampaignId;
use crate::money_journal::{self, JournalError, LaborCarry, LaborFacts};
use crate::observer_reader::ReceiptPurpose;
use crate::observer_reader::{
    ObserverEconomyError, ObserverEconomyReader, ObserverMaterialCursor, ObserverVisibility,
};
use crate::qualification_audit::trade;
use crate::recorded_labor::RecordedLaborPeriod;
use serde::Serialize;
use std::iter::FusedIterator;

/// A completed period and the exact campaign inputs that produced its derived labor trace.
#[derive(Serialize)]
pub struct CommittedLaborPeriod {
    pub version: u32,
    pub campaign: String,
    pub tick: u64,
    pub foundation_sha256: String,
    pub tick_content_hash: String,
    pub receipt_sha256: String,
    pub labor: RecordedLaborPeriod,
}

/// A sequential reader with one period of movement detail in memory. Each yielded row
/// has authenticated opening carry even when the requested window starts in a later period.
pub struct RecordedLaborWindow<'a> {
    reader: &'a ObserverEconomyReader,
    campaign: CampaignId,
    last: u64,
    next: u64,
    cursor: Option<ObserverMaterialCursor>,
    carry: Option<LaborCarry>,
}

impl ObserverEconomyReader {
    /// Read an inclusive, positive period range. Iterating authenticates the prefix
    /// and restores the nearest usable earlier labor checkpoint, or folds from the foundation.
    ///
    /// # Errors
    /// Refuses restricted readers and ranges outside the committed tick representation.
    pub fn recorded_labor_window(
        &self,
        campaign: CampaignId,
        first: u64,
        last: u64,
    ) -> Result<RecordedLaborWindow<'_>, ObserverEconomyError> {
        if self.visibility() != ObserverVisibility::FullObserver {
            return Err(ObserverEconomyError::Authority);
        }
        if first == 0 || first > last || i64::try_from(last).is_err() {
            return Err(ObserverEconomyError::TickAbsent);
        }
        Ok(RecordedLaborWindow {
            reader: self,
            campaign,
            last,
            next: first,
            cursor: None,
            carry: None,
        })
    }
}

impl RecordedLaborWindow<'_> {
    /// Last authenticated checkpoint used to seed this window, after its first successful read.
    #[must_use]
    pub fn restored_checkpoint_period(&self) -> Option<u64> {
        self.carry.as_ref().and_then(|carry| carry.restored_period)
    }

    pub(crate) fn facts_for_current(
        &self,
        report: &CommittedLaborPeriod,
    ) -> Result<LaborFacts, JournalError> {
        let cursor = self.cursor.as_ref().ok_or(JournalError::SourceChanged)?;
        let foundation = cursor
            .admission(self.campaign)
            .ok_or(JournalError::SourceChanged)?;
        if cursor.completed_tick() != report.tick
            || self.campaign.as_uuid().to_string() != report.campaign
            || trade::hex(&foundation.digest()) != report.foundation_sha256
        {
            return Err(JournalError::SourceChanged);
        }
        LaborFacts::from_report(&foundation, &report.labor)
    }

    fn read_tick(&mut self, tick: u64) -> Result<CommittedLaborPeriod, ObserverEconomyError> {
        let (carry, report) = money_journal::read_labor_through(
            self.reader,
            self.campaign,
            tick,
            &mut self.cursor,
            self.carry.take(),
            ReceiptPurpose::Observation,
            |_, _, source, labor, _| {
                let identity = &source.identity;
                Ok(CommittedLaborPeriod {
                    version: 1,
                    campaign: source.campaign_id.as_uuid().to_string(),
                    tick,
                    foundation_sha256: trade::hex(&identity.foundation_digest()),
                    tick_content_hash: trade::hex(identity.tick_content_hash().as_bytes()),
                    receipt_sha256: trade::hex(&identity.receipt_digest()),
                    labor,
                })
            },
        )?;
        self.carry = Some(carry);
        Ok(report)
    }
}

impl Iterator for RecordedLaborWindow<'_> {
    type Item = Result<CommittedLaborPeriod, ObserverEconomyError>;

    fn next(&mut self) -> Option<Self::Item> {
        if self.next > self.last {
            return None;
        }
        let tick = self.next;
        let report = self.read_tick(tick);
        self.next = if report.is_ok() {
            tick + 1
        } else {
            self.last + 1
        };
        Some(report)
    }
}

impl FusedIterator for RecordedLaborWindow<'_> {}
