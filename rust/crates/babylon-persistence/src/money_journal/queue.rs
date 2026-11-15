//! Discover gaps in committed material history and publish them on a separate connection.
use super::{storage, JournalError, MoneyJournalWriter};
use crate::identity::CampaignId;
use crate::observer_reader::{
    self, ObserverEconomyReader, ObserverMaterialCursor, ObserverVisibility,
};
use crate::ARCHIVE_WAKEUP_CHANNEL;
use postgres::fallible_iterator::FallibleIterator as _;
use postgres::Client;
use std::fmt::{Display, Formatter, Result as FmtResult};
use std::time::Duration;
use uuid::Uuid;

const BATCH_SIZE: i64 = 8;
const PENDING: &str = "SELECT t.campaign_id,t.resolve_tick
    FROM public.v_committed_tick_status_v1 t
    JOIN public.v_material_campaign_identity_v2 f USING (campaign_id)
    WHERE t.envelope_layout_version=3 AND t.resolve_tick>0
      AND ($1::uuid IS NULL OR t.campaign_id=$1)
      AND ($2::uuid IS NULL OR (t.campaign_id,t.resolve_tick)>($2,$3::bigint))
      AND NOT EXISTS (SELECT 1 FROM public.v_observer_money_journal_period_v1 p
          WHERE p.campaign_id=t.campaign_id AND p.resolve_tick=t.resolve_tick)
    ORDER BY t.campaign_id,t.resolve_tick LIMIT $4";

#[derive(Debug)]
pub enum JournalQueueError {
    Discovery(JournalError),
    Publication {
        campaign: CampaignId,
        period: u64,
        cause: JournalError,
    },
}
impl Display for JournalQueueError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::Discovery(cause) => write!(f, "projection discovery: {cause}"),
            Self::Publication {
                campaign,
                period,
                cause,
            } => write!(
                f,
                "projection campaign {} period {period}: {cause}",
                campaign.as_uuid()
            ),
        }
    }
}
impl std::error::Error for JournalQueueError {}

/// The database owns coverage. This bounded bookmark only spreads one pass across batches.
pub struct JournalQueue<'a> {
    listener: Client,
    observer: &'a ObserverEconomyReader,
    writer: &'a MoneyJournalWriter,
    scope: Option<CampaignId>,
    after: Option<(Uuid, i64)>,
    cursor: Option<ObserverMaterialCursor>,
}

impl<'a> JournalQueue<'a> {
    /// Register for post-commit wakeups before the first discovery snapshot.
    /// Pass a campaign to restrict discovery to that exact recorded identity.
    /// # Errors
    /// Refuses a different writer target, an unconfined observer, or a connection failure.
    pub fn connect(
        observer: &'a ObserverEconomyReader,
        writer: &'a MoneyJournalWriter,
        scope: Option<CampaignId>,
    ) -> Result<Self, JournalError> {
        writer.require_target(observer)?;
        let mut listener = storage::open_observer(observer)?;
        listener
            .batch_execute(&format!("LISTEN {ARCHIVE_WAKEUP_CHANNEL}"))
            .map_err(|_| JournalError::Database)?;
        Ok(Self {
            listener,
            observer,
            writer,
            scope,
            after: None,
            cursor: None,
        })
    }

    /// Publish at most eight uncovered periods. Zero ends this pass; the next call
    /// looks from the beginning so earlier missing coverage can be recovered.
    /// # Errors
    /// A refused campaign is skipped for the rest of this pass. Discovery failures
    /// require a fresh connection, which starts a new pass from durable markers.
    pub fn publish_batch(&mut self) -> Result<usize, JournalQueueError> {
        use JournalQueueError::Discovery;
        observer_reader::confine_authority(&mut self.listener, ObserverVisibility::FullObserver)
            .map_err(|e| Discovery(JournalError::Observer(e)))?;
        let scope = self.scope.map(|c| *c.as_uuid());
        let (campaign, period) = self.after.unzip();
        let rows = self
            .listener
            .query(PENDING, &[&scope, &campaign, &period, &BATCH_SIZE])
            .map_err(|_| Discovery(JournalError::Database))?;
        if rows.is_empty() {
            self.after = None;
            return Ok(0);
        }
        for row in &rows {
            let id: Uuid = row
                .try_get(0)
                .map_err(|_| Discovery(JournalError::Projection))?;
            let stored: i64 = row
                .try_get(1)
                .map_err(|_| Discovery(JournalError::Projection))?;
            let period = u64::try_from(stored).map_err(|_| Discovery(JournalError::Range))?;
            let campaign = CampaignId::from_uuid(id);
            if let Err(cause) =
                self.writer
                    .publish_with_cursor(self.observer, campaign, period, &mut self.cursor)
            {
                self.after = Some((id, i64::MAX));
                return Err(JournalQueueError::Publication {
                    campaign,
                    period,
                    cause,
                });
            }
            self.after = Some((id, stored));
        }
        Ok(rows.len())
    }

    /// Receive an untrusted wakeup hint. The next discovery query verifies the durable marker.
    /// # Errors
    /// A disconnected listener must register again and perform a fresh pass.
    pub fn wait(&mut self, duration: Duration) -> Result<bool, JournalError> {
        let notified = {
            let mut hints = self.listener.notifications();
            let first = hints
                .timeout_iter(duration)
                .next()
                .map_err(|_| JournalError::Database)?;
            let mut notified = first
                .is_some_and(|n| n.channel() == ARCHIVE_WAKEUP_CHANNEL && n.payload().is_empty());
            let mut buffered = hints.iter();
            for _ in 0..64 {
                let Some(hint) = buffered.next().map_err(|_| JournalError::Database)? else {
                    break;
                };
                notified |= hint.channel() == ARCHIVE_WAKEUP_CHANNEL && hint.payload().is_empty();
            }
            notified
        };
        if self.listener.is_closed() {
            return Err(JournalError::Database);
        }
        Ok(notified)
    }
}
