//! Operating-site statements grouped by their foundation-bound county of operation.
use super::{storage, JournalError};
use crate::identity::CampaignId;
use crate::observer_reader::{ObserverEconomyReader, MATERIAL_READ_TRANSACTION_OPTIONS};
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::SiteId;
use postgres::IsolationLevel;

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum CountySiteAccounts {
    /// This committed period has physical books and no monetary statements.
    PhysicalOnly,
    Monetary(CountySitePage),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountySitePage {
    pub site_count: u64,
    /// Closing spendable cash less opening spendable cash.
    pub cash_change_micros: String,
    pub period_profit_micros: String,
    pub closing_retained_earnings_micros: String,
    /// At most six actual operating sites. All totals cover every included site.
    pub sites: Vec<SiteId>,
}

const BOOKS: &str = "
    WITH sites AS MATERIALIZED (
        SELECT a.account_id AS site, s.site_id, s.closing_cash_micros - s.opening_cash_micros AS cash_change,
               s.net_income_micros AS profit, s.closing_retained_earnings_micros AS earnings
          FROM public.v_observer_economic_flow_account_v1 a
          LEFT JOIN public.v_observer_site_statement_v1 s
            ON s.campaign_id=a.campaign_id AND s.resolve_tick=$2 AND s.site_id=a.account_id
         WHERE a.campaign_id=$1 AND a.account_kind='site_cash' AND a.location_key=$3)
    SELECT count(*) AS sites,
           count(*)=count(site_id) AND count(*)=count(cash_change)
               AND count(*)=count(profit) AND count(*)=count(earnings) AS complete,
           coalesce(sum(cash_change),0)::text AS cash, coalesce(sum(profit),0)::text AS profit,
           coalesce(sum(earnings),0)::text AS earnings,
           ARRAY(SELECT site FROM sites ORDER BY site LIMIT 6 OFFSET $4) AS members
      FROM sites";

impl ObserverEconomyReader {
    /// Sum complete operating-site statements for one selected county and committed observer frame.
    /// Each site contributes once. The six-site page is ordered by captured site identity.
    /// # Errors
    /// Refuses insufficient authority, missing publication, stale frames, incomplete statements and invalid offsets.
    pub fn county_site_accounts_for_frame(
        &self,
        campaign: CampaignId,
        tick: u64,
        county: CountyGeoid,
        foundation: &str,
        tick_hash: &str,
        offset: u64,
    ) -> Result<CountySiteAccounts, JournalError> {
        let mut client = storage::open_observer(self)?;
        let tick = i64::try_from(tick).map_err(|_| JournalError::Range)?;
        let start = i64::try_from(offset).map_err(|_| JournalError::Range)?;
        let mut tx = client
            .build_transaction()
            .isolation_level(IsolationLevel::RepeatableRead)
            .read_only(true)
            .start()
            .map_err(|_| JournalError::Database)?;
        tx.batch_execute(MATERIAL_READ_TRANSACTION_OPTIONS)
            .map_err(|_| JournalError::Database)?;
        let header = tx.query_opt(
            "SELECT site_monetary_books, encode(foundation_sha256,'hex')=$3 AND encode(tick_content_hash,'hex')=$4
               FROM public.v_observer_money_journal_period_v1 WHERE campaign_id=$1 AND resolve_tick=$2",
            &[campaign.as_uuid(), &tick, &foundation, &tick_hash],
        ).map_err(|_|JournalError::Database)?.ok_or(JournalError::CoverageAbsent)?;
        if !header
            .try_get::<_, bool>(1)
            .map_err(|_| JournalError::Projection)?
        {
            return Err(JournalError::SourceChanged);
        }
        let monetary = header
            .try_get::<_, bool>(0)
            .map_err(|_| JournalError::Projection)?;
        if !monetary {
            tx.commit().map_err(|_| JournalError::Database)?;
            return Ok(CountySiteAccounts::PhysicalOnly);
        }
        let key = format!("county:{}", county.as_str());
        let totals = tx
            .query_one(BOOKS, &[campaign.as_uuid(), &tick, &key, &start])
            .map_err(|_| JournalError::Database)?;
        if !totals
            .try_get::<_, bool>("complete")
            .map_err(|_| JournalError::Projection)?
        {
            return Err(JournalError::Projection);
        }
        let count = totals
            .try_get::<_, i64>("sites")
            .map_err(|_| JournalError::Projection)?;
        if start > 0 && start >= count {
            return Err(JournalError::Range);
        }
        let ids = totals
            .try_get::<_, Vec<Vec<u8>>>("members")
            .map_err(|_| JournalError::Projection)?;
        let members = ids
            .into_iter()
            .map(|id| {
                id.try_into()
                    .map(SiteId::from_bytes)
                    .map_err(|_| JournalError::Projection)
            })
            .collect::<Result<_, _>>()?;
        tx.commit().map_err(|_| JournalError::Database)?;
        Ok(CountySiteAccounts::Monetary(CountySitePage {
            site_count: u64::try_from(count).map_err(|_| JournalError::Projection)?,
            cash_change_micros: totals
                .try_get("cash")
                .map_err(|_| JournalError::Projection)?,
            period_profit_micros: totals
                .try_get("profit")
                .map_err(|_| JournalError::Projection)?,
            closing_retained_earnings_micros: totals
                .try_get("earnings")
                .map_err(|_| JournalError::Projection)?,
            sites: members,
        }))
    }
}
