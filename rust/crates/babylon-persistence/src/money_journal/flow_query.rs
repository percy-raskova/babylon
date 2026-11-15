//! Read-only SQL ranking over retained settlements and reauthenticated expired periods.
use super::{
    model, payment_storage, storage, FlowPage, FlowQuery, FlowViewport, JournalError, PeriodWindow,
};
use crate::identity::CampaignId;
use crate::observer_reader::ObserverEconomyReader;
use crate::qualification_audit::trade;
use postgres::{Client, IsolationLevel, Transaction};
use serde::Serialize;
use std::collections::BTreeMap;

const GROUPS_SQL: &str = include_str!("flow_groups.sql");
const COVERAGE_SQL: &str = "SELECT p.resolve_tick,p.detail_retained,p.source_identity_bytes,p.payment_sha256,p.payment_count, \
 (SELECT count(*) FROM public.v_observer_economic_payment_v1 d WHERE d.campaign_id=p.campaign_id AND d.resolve_tick=p.resolve_tick) AS stored \
 FROM public.v_observer_money_journal_period_v1 p WHERE p.campaign_id=$1 AND \
 (p.resolve_tick BETWEEN $2::bigint AND $3::bigint OR p.resolve_tick BETWEEN $4::bigint AND $5::bigint) ORDER BY p.resolve_tick";

#[derive(Debug, PartialEq, Eq)]
struct ExpiredBinding {
    identity: Vec<u8>,
    digest: Vec<u8>,
    count: i64,
}

struct Bounds {
    first: i64,
    last: i64,
    compare_first: Option<i64>,
    compare_last: Option<i64>,
    offset: i64,
    viewport: Option<Vec<f64>>,
}
impl Bounds {
    fn new(request: &FlowQuery) -> Result<Self, JournalError> {
        let (first, last) = request.window.bounds()?;
        let comparison = request.comparison.map(PeriodWindow::bounds).transpose()?;
        let offset = i64::try_from(request.offset).map_err(|_| JournalError::Range)?;
        if offset > i64::MAX - 20 {
            return Err(JournalError::Range);
        }
        let viewport = request
            .viewport_4269
            .map(FlowViewport::coordinates)
            .transpose()?;
        Ok(Self {
            first,
            last,
            compare_first: comparison.map(|c| c.0),
            compare_last: comparison.map(|c| c.1),
            offset,
            viewport,
        })
    }
}

fn coverage(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    b: &Bounds,
) -> Result<BTreeMap<i64, ExpiredBinding>, JournalError> {
    let mut expired = BTreeMap::new();
    let mut current_count = 0_i64;
    let mut comparison_count = 0_i64;
    for row in tx
        .query(
            COVERAGE_SQL,
            &[
                campaign.as_uuid(),
                &b.first,
                &b.last,
                &b.compare_first,
                &b.compare_last,
            ],
        )
        .map_err(|_| JournalError::Database)?
    {
        let period: i64 = row
            .try_get("resolve_tick")
            .map_err(|_| JournalError::Projection)?;
        if (b.first..=b.last).contains(&period) {
            current_count += 1;
        }
        if b.compare_first
            .zip(b.compare_last)
            .is_some_and(|(first, last)| (first..=last).contains(&period))
        {
            comparison_count += 1;
        }
        let retained: bool = row
            .try_get("detail_retained")
            .map_err(|_| JournalError::Projection)?;
        let count: i64 = row
            .try_get("payment_count")
            .map_err(|_| JournalError::Projection)?;
        let stored: i64 = row
            .try_get("stored")
            .map_err(|_| JournalError::Projection)?;
        if (retained && stored != count) || (!retained && stored != 0) {
            return Err(JournalError::Projection);
        }
        if !retained {
            expired.insert(
                period,
                ExpiredBinding {
                    identity: row
                        .try_get("source_identity_bytes")
                        .map_err(|_| JournalError::Projection)?,
                    digest: row
                        .try_get("payment_sha256")
                        .map_err(|_| JournalError::Projection)?,
                    count,
                },
            );
        }
    }
    if current_count != b.last - b.first + 1
        || b.compare_first
            .zip(b.compare_last)
            .is_some_and(|(f, l)| comparison_count != l - f + 1)
    {
        return Err(JournalError::CoverageAbsent);
    }
    Ok(expired)
}

#[derive(Serialize)]
struct HistoricalPayment<'a> {
    t: i64,
    pk: &'static str,
    p: String,
    rk: &'static str,
    r: String,
    n: &'a str,
}

/// The retained accumulator holds six exact numeric totals per grouping key.
struct Ranking<'a> {
    campaign: CampaignId,
    bounds: Bounds,
    request: &'a FlowQuery,
}

#[derive(Clone, Copy)]
enum Stage<'a> {
    Fold {
        period: &'a str,
        accumulated: &'a str,
    },
    Page {
        accumulated: &'a str,
    },
}

impl Ranking<'_> {
    fn check_frame(
        &self,
        tx: &mut Transaction<'_>,
        expected: Option<(&str, &str)>,
    ) -> Result<(), JournalError> {
        let Some((foundation, tick_hash)) = expected else {
            return Ok(());
        };
        let row = tx.query_opt(
            "SELECT 1 FROM public.v_observer_money_journal_period_v1 WHERE campaign_id=$1 AND resolve_tick=$2 AND encode(foundation_sha256,'hex')=$3 AND encode(tick_content_hash,'hex')=$4",
            &[self.campaign.as_uuid(), &self.bounds.last, &foundation, &tick_hash],
        ).map_err(|_| JournalError::Database)?;
        row.ok_or(JournalError::SourceChanged)?;
        Ok(())
    }

    fn run(&self, tx: &mut Transaction<'_>, stage: Stage<'_>) -> Result<String, JournalError> {
        let (period, accumulated, op) = match stage {
            Stage::Fold {
                period,
                accumulated,
            } => (period, accumulated, "fold"),
            Stage::Page { accumulated } => ("[]", accumulated, "page"),
        };
        let b = &self.bounds;
        let row = tx
            .query_one(
                GROUPS_SQL,
                &[
                    self.campaign.as_uuid(),
                    &b.first,
                    &b.last,
                    &b.compare_first,
                    &b.compare_last,
                    &self.request.group.key(),
                    &b.offset,
                    &b.viewport,
                    &period,
                    &self.request.focus,
                    &accumulated,
                    &op,
                ],
            )
            .map_err(|_| JournalError::Database)?;
        if !row
            .try_get::<_, bool>("valid")
            .map_err(|_| JournalError::Projection)?
        {
            return Err(JournalError::Projection);
        }
        row.try_get("result").map_err(|_| JournalError::Projection)
    }

    fn page(&self, tx: &mut Transaction<'_>, accumulated: &str) -> Result<FlowPage, JournalError> {
        let json = self.run(tx, Stage::Page { accumulated })?;
        serde_json::from_str(&json).map_err(|_| JournalError::Projection)
    }

    fn fold_history(
        &self,
        reader: &ObserverEconomyReader,
        client: &mut Client,
        expired: &BTreeMap<i64, ExpiredBinding>,
    ) -> Result<String, JournalError> {
        let mut accumulated = String::from("[]");
        let mut cursor = None;
        for (&period, binding) in expired {
            let tick = u64::try_from(period).map_err(|_| JournalError::Range)?;
            let read = reader
                .committed_economic_payments_with_cursor(self.campaign, tick, &mut cursor)
                .map_err(JournalError::Observer)?;
            let moves = model::derive_movements(&read.source)?;
            if read.source.identity.canonical_bytes() != binding.identity
                || payment_storage::fingerprint(&read.settlements, &moves)?.as_slice()
                    != binding.digest
                || i64::try_from(read.settlements.len()).map_err(|_| JournalError::Range)?
                    != binding.count
            {
                return Err(JournalError::SourceChanged);
            }
            let mut inputs = Vec::with_capacity(read.settlements.len());
            for s in read.settlements {
                let index = usize::try_from(s.ordinal).map_err(|_| JournalError::Range)?;
                let n = &moves
                    .get(index)
                    .ok_or(JournalError::Projection)?
                    .amount_micros;
                inputs.push(HistoricalPayment {
                    t: period,
                    pk: s.payer.kind.as_str(),
                    p: trade::hex(&s.payer.id),
                    rk: s.recipient.kind.as_str(),
                    r: trade::hex(&s.recipient.id),
                    n,
                });
            }
            let rows = serde_json::to_string(&inputs).map_err(|_| JournalError::Projection)?;
            let mut tx = snapshot(client)?;
            accumulated = self.run(
                &mut tx,
                Stage::Fold {
                    period: &rows,
                    accumulated: &accumulated,
                },
            )?;
            tx.commit().map_err(|_| JournalError::Database)?;
        }
        Ok(accumulated)
    }
}

fn snapshot(client: &mut Client) -> Result<Transaction<'_>, JournalError> {
    client
        .build_transaction()
        .isolation_level(IsolationLevel::RepeatableRead)
        .read_only(true)
        .start()
        .map_err(|_| JournalError::Database)
}

impl ObserverEconomyReader {
    /// Rank economic payment groups by gross external inflow, external outflow and internal circulation.
    /// Each page includes the exact complement and full totals. An optional comparison uses the
    /// same grouping, focus and viewport. Expired source periods are authenticated before ranking.
    /// # Errors
    /// Refuses non-observer credentials, incomplete or changing coverage, and invalid bounds.
    pub fn economic_payment_flows(
        &self,
        campaign: CampaignId,
        query: &FlowQuery,
    ) -> Result<FlowPage, JournalError> {
        self.bound_payment_flows(campaign, query, None)
    }

    /// Read a page only if its last period matches an installed observer frame.
    /// The page and its foundation and period hashes share one database snapshot.
    /// # Errors
    /// Refuses stale frame identities and all failures of the ordinary flow query.
    pub fn economic_payment_flows_for_frame(
        &self,
        campaign: CampaignId,
        query: &FlowQuery,
        foundation_sha256: &str,
        tick_content_hash: &str,
    ) -> Result<FlowPage, JournalError> {
        self.bound_payment_flows(
            campaign,
            query,
            Some((foundation_sha256, tick_content_hash)),
        )
    }

    fn bound_payment_flows(
        &self,
        campaign: CampaignId,
        query: &FlowQuery,
        expected: Option<(&str, &str)>,
    ) -> Result<FlowPage, JournalError> {
        let ranking = Ranking {
            campaign,
            bounds: Bounds::new(query)?,
            request: query,
        };
        let mut client = storage::open_observer(self)?;
        let mut tx = snapshot(&mut client)?;
        let mut expired = coverage(&mut tx, campaign, &ranking.bounds)?;
        if expired.is_empty() {
            ranking.check_frame(&mut tx, expected)?;
            let report = ranking.page(&mut tx, "[]")?;
            tx.commit().map_err(|_| JournalError::Database)?;
            return Ok(report);
        }
        tx.commit().map_err(|_| JournalError::Database)?;
        // Never leave an idle transaction open across a long replay. A second snapshot
        // reconciles a concurrently moving retention boundary before combining facts.
        for _ in 0..2 {
            let history = ranking.fold_history(self, &mut client, &expired)?;
            let mut tx = snapshot(&mut client)?;
            let latest = coverage(&mut tx, campaign, &ranking.bounds)?;
            if latest == expired {
                ranking.check_frame(&mut tx, expected)?;
                let report = ranking.page(&mut tx, &history)?;
                tx.commit().map_err(|_| JournalError::Database)?;
                return Ok(report);
            }
            tx.commit().map_err(|_| JournalError::Database)?;
            expired = latest;
        }
        Err(JournalError::SourceChanged)
    }
}
