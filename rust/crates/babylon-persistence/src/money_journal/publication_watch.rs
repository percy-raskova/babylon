//! A committed journal marker wakes observers waiting for exact missing periods.
use super::{queue, storage, JournalError, PeriodWindow};
use crate::identity::CampaignId;
use crate::observer_reader::ObserverEconomyReader;
use postgres::{Client, Transaction};
use std::time::{Duration, Instant};

const CHANNEL: &str = "babylon_economic_publication_v1";
const RECHECK: Duration = Duration::from_secs(8);

pub(super) fn notify(tx: &mut Transaction<'_>) -> Result<(), JournalError> {
    tx.batch_execute(&format!("NOTIFY {CHANNEL}"))
        .map_err(|_| JournalError::Database)?;
    Ok(())
}

/// One confined listener for missing contiguous journal coverage on the selected campaign.
pub struct JournalPublicationWatch {
    client: Client,
    campaign: CampaignId,
    first: i64,
    last: i64,
    recheck: Instant,
}

impl ObserverEconomyReader {
    /// Register before the first marker check so a commit in flight cannot be missed.
    /// # Errors
    /// Refuses restricted authority, invalid windows and database errors.
    pub fn watch_journal_periods(
        &self,
        campaign: CampaignId,
        window: PeriodWindow,
    ) -> Result<JournalPublicationWatch, JournalError> {
        let (first, last) = window.bounds()?;
        let mut client = storage::open_observer(self)?;
        client
            .batch_execute(&format!("LISTEN {CHANNEL}"))
            .map_err(|_| JournalError::Database)?;
        Ok(JournalPublicationWatch {
            client,
            campaign,
            first,
            last,
            recheck: Instant::now(),
        })
    }
}

impl JournalPublicationWatch {
    /// Wait at most one interval. An empty, untrusted signal only requests a fresh scoped check.
    /// # Errors
    /// Refuses a disconnected listener or an unreadable journal marker.
    pub fn wait(&mut self, interval: Duration) -> Result<bool, JournalError> {
        let until_check = self.recheck.saturating_duration_since(Instant::now());
        if !until_check.is_zero() {
            let notified =
                queue::wait_for_hint(&mut self.client, CHANNEL, interval.min(until_check))?;
            if !notified && Instant::now() < self.recheck {
                return Ok(false);
            }
        }
        self.recheck = Instant::now() + RECHECK;
        self.client
            .query_one(
                "SELECT count(*) = $3::bigint - $2::bigint + 1
                 FROM public.v_observer_money_journal_period_v1
                 WHERE campaign_id=$1 AND resolve_tick BETWEEN $2 AND $3",
                &[self.campaign.as_uuid(), &self.first, &self.last],
            )
            .map_err(|_| JournalError::Database)?
            .try_get(0)
            .map_err(|_| JournalError::Projection)
    }
}
