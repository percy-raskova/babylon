//! Rank immediate recorded-labor movements. Count unresolved opening prehistory separately.
use super::model::LaborFlowPage;
use crate::identity::CampaignId;
use crate::money_journal::flow_query::{self, Bounds};
use crate::money_journal::{storage, FlowQuery, JournalError};
use crate::observer_reader::ObserverEconomyReader;
use postgres::{Client, Transaction};
use std::collections::BTreeMap;

const GROUPS_SQL: &str = include_str!("groups.sql");
const COVERAGE_SQL: &str = "SELECT p.resolve_tick, p.detail_retained, p.movement_count, p.node_count,
    p.fact_sha256, encode(p.foundation_sha256,'hex'), encode(p.tick_content_hash,'hex'), encode(p.receipt_sha256,'hex'),
    (SELECT count(*) FROM public.v_observer_labor_movement_v1 m WHERE m.campaign_id=$1 AND m.resolve_tick=p.resolve_tick),
    (SELECT count(*) FROM public.v_observer_labor_node_v1 n WHERE n.campaign_id=$1 AND n.resolve_tick=p.resolve_tick)
    FROM public.v_observer_labor_period_v1 p WHERE p.campaign_id=$1 AND
    (p.resolve_tick BETWEEN $2 AND $3 OR p.resolve_tick BETWEEN $4 AND $5) ORDER BY p.resolve_tick";

#[derive(PartialEq, Eq)]
struct Period {
    digest: Vec<u8>,
    foundation: String,
    content: String,
    receipts: String,
    nodes: i64,
    movements: i64,
    retained: bool,
}

struct Ranking<'a> {
    campaign: CampaignId,
    request: &'a FlowQuery,
    bounds: Bounds,
}

#[derive(Clone, Copy)]
enum Stage<'a> {
    Page,
    Fold {
        tick: i64,
        nodes: &'a str,
        movements: &'a str,
    },
}

impl Ranking<'_> {
    fn coverage(&self, tx: &mut Transaction<'_>) -> Result<BTreeMap<u64, Period>, JournalError> {
        let b = &self.bounds;
        let rows = tx
            .query(
                COVERAGE_SQL,
                &[
                    self.campaign.as_uuid(),
                    &b.first,
                    &b.last,
                    &b.compare_first,
                    &b.compare_last,
                ],
            )
            .map_err(|_| JournalError::Database)?;
        let mut current = 0_i64;
        let mut comparison = 0_i64;
        let mut result = BTreeMap::new();
        for row in rows {
            let get = |_| JournalError::Projection;
            let tick: i64 = row.try_get(0).map_err(get)?;
            current += i64::from((b.first..=b.last).contains(&tick));
            comparison += i64::from(
                b.compare_first
                    .zip(b.compare_last)
                    .is_some_and(|(f, l)| (f..=l).contains(&tick)),
            );
            let period = Period {
                retained: row.try_get(1).map_err(get)?,
                movements: row.try_get(2).map_err(get)?,
                nodes: row.try_get(3).map_err(get)?,
                digest: row.try_get(4).map_err(get)?,
                foundation: row.try_get(5).map_err(get)?,
                content: row.try_get(6).map_err(get)?,
                receipts: row.try_get(7).map_err(get)?,
            };
            if period.retained
                && (period.movements != row.try_get::<_, i64>(8).map_err(get)?
                    || period.nodes != row.try_get::<_, i64>(9).map_err(get)?)
            {
                return Err(JournalError::Projection);
            }
            let key = u64::try_from(tick).map_err(|_| JournalError::Range)?;
            result.insert(key, period);
        }
        if current != b.last - b.first + 1
            || b.compare_first
                .zip(b.compare_last)
                .is_some_and(|(f, l)| comparison != l - f + 1)
        {
            return Err(JournalError::CoverageAbsent);
        }
        Ok(result)
    }

    fn run(
        &self,
        tx: &mut Transaction<'_>,
        stage: Stage<'_>,
        prior: &str,
    ) -> Result<String, JournalError> {
        let (operation, tick, nodes, movements) = match stage {
            Stage::Page => ("page", None, "[]", "[]"),
            Stage::Fold {
                tick,
                nodes,
                movements,
            } => ("fold", Some(tick), nodes, movements),
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
                    &self.request.focus,
                    &b.offset,
                    &b.viewport,
                    &prior,
                    &nodes,
                    &movements,
                    &operation,
                    &tick,
                    &self.request.focus_group.unwrap_or(self.request.group).key(),
                    &self.request.peer.as_ref().map(|p| p.group.key()),
                    &self.request.peer.as_ref().and_then(|p| p.key.as_deref()),
                    &self.request.peer.as_ref().map(|p| p.direction.key()),
                ],
            )
            .map_err(|_| JournalError::Database)?;
        if !row
            .try_get::<_, bool>("valid")
            .map_err(|_| JournalError::Projection)?
        {
            return Err(JournalError::Projection);
        }
        row.try_get("data").map_err(|_| JournalError::Projection)
    }

    fn history(
        &self,
        reader: &ObserverEconomyReader,
        client: &mut Client,
        periods: &BTreeMap<u64, Period>,
    ) -> Result<String, JournalError> {
        let mut expired = periods
            .iter()
            .filter(|(_, p)| !p.retained)
            .map(|(&tick, _)| tick);
        let Some(first) = expired.next() else {
            return Ok("[]".into());
        };
        let last = expired.next_back().unwrap_or(first);
        let mut window = reader
            .recorded_labor_window(self.campaign, first, last)
            .map_err(JournalError::Observer)?;
        let mut prior = String::from("[]");
        while let Some(result) = window.next() {
            let report = result.map_err(JournalError::Observer)?;
            let Some(p) = periods.get(&report.tick).filter(|p| !p.retained) else {
                continue;
            };
            let facts = window.facts_for_current(&report)?;
            if p.foundation != report.foundation_sha256
                || p.content != report.tick_content_hash
                || p.receipts != report.receipt_sha256
                || facts.fingerprint()?.as_slice() != p.digest
                || i64::try_from(facts.nodes.len()).map_err(|_| JournalError::Range)? != p.nodes
                || i64::try_from(facts.movements.len()).map_err(|_| JournalError::Range)?
                    != p.movements
            {
                return Err(JournalError::SourceChanged);
            }
            let nodes =
                serde_json::to_string(&facts.nodes).map_err(|_| JournalError::Projection)?;
            let moves =
                serde_json::to_string(&facts.movements).map_err(|_| JournalError::Projection)?;
            let mut tx = flow_query::snapshot(client)?;
            let tick = i64::try_from(report.tick).map_err(|_| JournalError::Range)?;
            prior = self.run(
                &mut tx,
                Stage::Fold {
                    tick,
                    nodes: &nodes,
                    movements: &moves,
                },
                &prior,
            )?;
            tx.commit().map_err(|_| JournalError::Database)?;
        }
        Ok(prior)
    }

    fn page(&self, tx: &mut Transaction<'_>, history: &str) -> Result<LaborFlowPage, JournalError> {
        serde_json::from_str(&self.run(tx, Stage::Page, history)?)
            .map_err(|_| JournalError::Projection)
    }
}

impl ObserverEconomyReader {
    /// Compare immediate labor movements using the same windows, geographic scope and pages as payments.
    /// The sum of transfers describes movement through stages. Direct work and balances are reported by the period ledger.
    /// # Errors
    /// Refuses restricted access, missing publications, mismatched source identities and incomplete detail.
    pub fn recorded_labor_flows(
        &self,
        campaign: CampaignId,
        request: &FlowQuery,
    ) -> Result<LaborFlowPage, JournalError> {
        self.bound_labor_flows(campaign, request, None)
    }
    /// Pin the last period to the native observer frame before showing its labor movements.
    /// # Errors
    /// Refuses a mismatched frame and all failures of the ordinary scoped flow query.
    pub fn recorded_labor_flows_for_frame(
        &self,
        campaign: CampaignId,
        request: &FlowQuery,
        foundation: &str,
        content: &str,
    ) -> Result<LaborFlowPage, JournalError> {
        self.bound_labor_flows(campaign, request, Some((foundation, content)))
    }

    fn bound_labor_flows(
        &self,
        campaign: CampaignId,
        request: &FlowQuery,
        expected: Option<(&str, &str)>,
    ) -> Result<LaborFlowPage, JournalError> {
        let rank = Ranking {
            campaign,
            request,
            bounds: Bounds::new(request)?,
        };
        let mut client = storage::open_observer(self)?;
        for _ in 0..2 {
            let mut tx = flow_query::snapshot(&mut client)?;
            let periods = rank.coverage(&mut tx)?;
            if let Some((foundation, content)) = expected {
                if !periods
                    .get(&request.window.last)
                    .is_some_and(|p| p.foundation == foundation && p.content == content)
                {
                    return Err(JournalError::SourceChanged);
                }
            }
            if periods.values().all(|p| p.retained) {
                let page = rank.page(&mut tx, "[]")?;
                tx.commit().map_err(|_| JournalError::Database)?;
                return Ok(page);
            }
            tx.commit().map_err(|_| JournalError::Database)?;
            let accumulated = rank.history(self, &mut client, &periods)?;
            let mut tx = flow_query::snapshot(&mut client)?;
            if rank.coverage(&mut tx)? == periods {
                let page = rank.page(&mut tx, &accumulated)?;
                tx.commit().map_err(|_| JournalError::Database)?;
                return Ok(page);
            }
            tx.commit().map_err(|_| JournalError::Database)?;
        }
        Err(JournalError::SourceChanged)
    }
}
