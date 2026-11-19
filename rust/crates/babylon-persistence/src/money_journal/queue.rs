//! Discover gaps in committed material history and publish them on a separate connection.
use super::{storage, JournalError, MoneyJournalWriter};
use crate::identity::CampaignId;
use crate::observer_reader::{
    self, ObserverEconomyError, ObserverEconomyReader, ObserverMaterialCursor, ObserverVisibility,
};
use crate::production_projection::diagnostics::{Stage, Timing};
use crate::ARCHIVE_WAKEUP_CHANNEL;
use postgres::fallible_iterator::FallibleIterator as _;
use postgres::Client;
use std::fmt::{Display, Formatter, Result as FmtResult};
use std::time::Duration;
use uuid::Uuid;

const BATCH_SIZE: i64 = 8;
const MAX_OPENINGS: usize = 64;
const PENDING: &str = "SELECT t.campaign_id,t.resolve_tick
    FROM public.v_committed_tick_status_v1 t
    JOIN public.v_material_campaign_identity_v2 f USING (campaign_id)
    WHERE t.envelope_layout_version=3 AND t.resolve_tick>0
      AND ($1::uuid IS NULL OR t.campaign_id=$1)
      AND ($2::uuid IS NULL OR (t.campaign_id,t.resolve_tick)>($2,$3::bigint))
      AND NOT EXISTS (SELECT 1 FROM public.v_observer_money_journal_period_v1 p
          WHERE p.campaign_id=t.campaign_id AND p.resolve_tick=t.resolve_tick)
    ORDER BY t.campaign_id,t.resolve_tick LIMIT $4";

// The latest canonical commit must already be covered. On a long-lived save a
// speculative read covers at most one material-history page, including opening.
const REOPENED: &str = "
    SELECT seed.resolve_tick, seed.source_identity_bytes, seed.receipt_sha256 FROM (
        SELECT t.resolve_tick FROM public.v_committed_tick_status_v1 t
        JOIN public.v_material_campaign_identity_v2 f USING(campaign_id)
        WHERE t.campaign_id=$1 AND t.envelope_layout_version=3 AND f.preset_id='national-world'
        ORDER BY t.resolve_tick DESC LIMIT 1
    ) latest
    JOIN public.v_observer_money_journal_period_v1 tail
        ON tail.campaign_id=$1 AND tail.resolve_tick=latest.resolve_tick
    JOIN public.v_observer_money_journal_period_v1 seed
        ON seed.campaign_id=$1 AND seed.resolve_tick=least(latest.resolve_tick,$2::bigint)";

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
    national_openings: Option<Vec<Uuid>>,
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
            national_openings: None,
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

    /// Warm a single launcher-selected continuation after ordinary catchup. Coverage
    /// and the canonical receipt must agree; no journal row is published by this read.
    /// Returns the newly admitted boundary, if one was needed.
    /// # Errors
    /// Refuses the wrong scope, changed coverage, or a failed source admission.
    pub fn warm_reopened_campaign(
        &mut self,
        campaign: CampaignId,
    ) -> Result<Option<u64>, JournalError> {
        if self.scope.is_some_and(|scope| scope != campaign) {
            return Err(JournalError::Authority);
        }
        observer_reader::confine_authority(&mut self.listener, ObserverVisibility::FullObserver)
            .map_err(JournalError::Observer)?;
        let last = i64::try_from(crate::observer_material::MATERIAL_PAGE_ROWS - 1)
            .map_err(|_| JournalError::Range)?;
        let Some(seed) = self
            .listener
            .query_opt(REOPENED, &[campaign.as_uuid(), &last])
            .map_err(|_| JournalError::Database)?
        else {
            return Ok(None);
        };
        let period = u64::try_from(
            seed.try_get::<_, i64>(0)
                .map_err(|_| JournalError::Projection)?,
        )
        .map_err(|_| JournalError::Projection)?;
        if self
            .cursor
            .as_ref()
            .is_some_and(|c| c.admission(campaign).is_some() && c.completed_tick() >= period)
        {
            return Ok(None);
        }
        let identity: Vec<u8> = seed.try_get(1).map_err(|_| JournalError::Projection)?;
        let receipt: Vec<u8> = seed.try_get(2).map_err(|_| JournalError::Projection)?;
        let _timing = Timing::start(Stage::JournalWarmup, period);
        let mut cursor = None;
        self.observer
            .with_committed_receipts(campaign, period, &mut cursor, |_, _, source| {
                if source.identity.canonical_bytes() != identity
                    || source.identity.receipt_digest().as_slice() != receipt
                {
                    return Err(ObserverEconomyError::InvalidProjection);
                }
                Ok(())
            })
            .map_err(JournalError::Observer)?;
        self.cursor = cursor;
        Ok(Some(period))
    }

    /// Reconcile the ordinary enrollment wakeup after all committed gaps have had a turn.
    /// An initial New carries its launcher-minted UUID, even when founding beat LISTEN.
    /// Later discoveries compare complete, bounded P0 sets so preexisting saves stay cold.
    /// # Errors
    /// Refuses unconfined readers, database errors, or unauthenticated foundations.
    pub fn warm_new_opening(
        &mut self,
        initial: Option<CampaignId>,
    ) -> Result<Option<CampaignId>, JournalError> {
        // The retained listener was confined at connect. This cheap nomination reads only
        // catalog identities; admission rechecks the full role on its own fresh connection.
        let scope = self.scope.map(|campaign| *campaign.as_uuid());
        let current = self.listener.query(
            "SELECT f.campaign_id FROM public.v_material_campaign_identity_v2 f
             WHERE f.preset_id='national-world' AND ($1::uuid IS NULL OR f.campaign_id=$1)
               AND NOT EXISTS (SELECT 1 FROM public.v_committed_tick_status_v1 t WHERE t.campaign_id=f.campaign_id)
             ORDER BY f.campaign_id LIMIT 65", &[&scope],
        ).map_err(|_| JournalError::Database)?.into_iter().map(|row| row.try_get::<_,Uuid>(0))
          .collect::<Result<Vec<_>,_>>().map_err(|_| JournalError::Projection)?;
        let previous = self.national_openings.take();
        let candidate = initial
            .filter(|id| current.contains(id.as_uuid()))
            .or_else(|| {
                let previous = previous.as_ref()?;
                if current.len() > MAX_OPENINGS {
                    return None;
                }
                current
                    .iter()
                    .find(|id| previous.binary_search(id).is_err())
                    .copied()
                    .map(CampaignId::from_uuid)
            });
        // An oversized set cannot distinguish a new foundation from an old UUID outside the page.
        self.national_openings = (current.len() <= MAX_OPENINGS).then_some(current);
        match candidate {
            Some(campaign)
                if self
                    .observer
                    .warm_new_national_opening(campaign)
                    .map_err(JournalError::Observer)? =>
            {
                Ok(Some(campaign))
            }
            _ => Ok(None),
        }
    }

    /// Receive an untrusted wakeup hint. The next discovery query verifies the durable marker.
    /// # Errors
    /// A disconnected listener must register again and perform a fresh pass.
    pub fn wait(&mut self, duration: Duration) -> Result<bool, JournalError> {
        wait_for_hint(&mut self.listener, ARCHIVE_WAKEUP_CHANNEL, duration)
    }
}

pub(super) fn wait_for_hint(
    client: &mut Client,
    channel: &str,
    duration: Duration,
) -> Result<bool, JournalError> {
    let notified = {
        let mut hints = client.notifications();
        let first = hints
            .timeout_iter(duration)
            .next()
            .map_err(|_| JournalError::Database)?;
        let mut notified = first.is_some_and(|n| n.channel() == channel && n.payload().is_empty());
        let mut buffered = hints.iter();
        for _ in 0..64 {
            let Some(hint) = buffered.next().map_err(|_| JournalError::Database)? else {
                break;
            };
            notified |= hint.channel() == channel && hint.payload().is_empty();
        }
        notified
    };
    if client.is_closed() {
        return Err(JournalError::Database);
    }
    Ok(notified)
}
