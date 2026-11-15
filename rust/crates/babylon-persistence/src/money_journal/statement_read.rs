//! Selected-site compact history from permanent, authenticated journal coverage.
use super::statement_integrity::{self, SiteEvidence};
use super::statement_lines::Lines;
use super::{storage, JournalError, PeriodWindow};
use crate::identity::CampaignId;
use crate::observer_reader::{ObserverEconomyReader, MATERIAL_READ_TRANSACTION_OPTIONS};
use crate::qualification_audit::trade;
use crate::site_financial_statements::{SiteStatementSummary, SiteStockBalance, SiteStockPosition};
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{GoodId, SiteId, UnitId};
use postgres::types::ToSql;
use postgres::{IsolationLevel, Row, Transaction};
use serde::{Serialize, Serializer};
use serde_json::Value;
use std::str::FromStr;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PublishedSitePeriod {
    pub campaign_id: CampaignId,
    pub site_id: SiteId,
    pub resolve_tick: u64,
    pub foundation_sha256: [u8; 32],
    pub tick_content_hash: [u8; 32],
    pub receipt_sha256: [u8; 32],
    /// None when the captured period has only physical books.
    pub statement: Option<SiteStatementSummary>,
    pub stocks: Vec<SiteStockBalance>,
}

// Decimal strings preserve u64 quantities and i128 currency on JSON clients.
fn stock_point(position: SiteStockPosition) -> Value {
    serde_json::json!({
        "quantity": position.quantity.to_string(),
        "carrying_cost_micros": position.carrying_cost.map(|cost| cost.micro_units().to_string()),
    })
}

impl Serialize for PublishedSitePeriod {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        let stocks: Vec<_> = self
            .stocks
            .iter()
            .map(|stock| {
                serde_json::json!({
                    "good_id": trade::hex(&stock.good_id.as_bytes()),
                    "unit_id": trade::hex(&stock.unit_id.as_bytes()),
                    "opening": stock.opening.map(stock_point),
                    "closing": stock.closing.map(stock_point),
                })
            })
            .collect();
        serde_json::json!({
            "campaign": self.campaign_id.as_uuid().to_string(),
            "site_id": trade::hex(&self.site_id.as_bytes()),
            "resolve_tick": self.resolve_tick,
            "foundation_sha256": trade::hex(&self.foundation_sha256),
            "tick_content_hash": trade::hex(&self.tick_content_hash),
            "receipt_sha256": trade::hex(&self.receipt_sha256),
            "statement": self.statement.as_ref().map(Lines::from_summary),
            "stocks": stocks,
        })
        .serialize(serializer)
    }
}

const STATEMENTS: &str = "
    SELECT p.resolve_tick, p.site_monetary_books, p.foundation_sha256,
           p.tick_content_hash, p.receipt_sha256,
           substring(p.site_accounting_directory FROM 64 * s.site_ordinal + 1 FOR 64) AS entry,
           (SELECT jsonb_object_agg(k, v)::text
              FROM jsonb_each_text(to_jsonb(s)) x(k, v)
             WHERE right(k, 7) = '_micros' AND v IS NOT NULL) AS lines
      FROM public.v_observer_money_journal_period_v1 p
      LEFT JOIN public.v_observer_site_statement_v1 s
        ON (s.campaign_id, s.resolve_tick) = (p.campaign_id, p.resolve_tick) AND s.site_id = $4
     WHERE p.campaign_id = $1 AND p.resolve_tick BETWEEN $2 AND $3
     ORDER BY p.resolve_tick";

const STOCKS: &str = "
    SELECT resolve_tick, good_id, unit_id, opening_quantity::text, closing_quantity::text,
           opening_carrying_cost_micros::text, closing_carrying_cost_micros::text
      FROM public.v_observer_site_stock_balance_v1
     WHERE campaign_id = $1 AND resolve_tick BETWEEN $2 AND $3 AND site_id = $4
     ORDER BY resolve_tick, good_id, unit_id";

fn bytes(row: &Row, column: &str) -> Result<[u8; 32], JournalError> {
    row.try_get::<_, &[u8]>(column)
        .map_err(|_| JournalError::Projection)?
        .try_into()
        .map_err(|_| JournalError::Projection)
}
fn period(row: &Row) -> Result<u64, JournalError> {
    u64::try_from(
        row.try_get::<_, i64>("resolve_tick")
            .map_err(|_| JournalError::Projection)?,
    )
    .map_err(|_| JournalError::Range)
}
fn site_period(
    campaign_id: CampaignId,
    site_id: SiteId,
    row: &Row,
) -> Result<PublishedSitePeriod, JournalError> {
    let resolve_tick = period(row)?;
    let monetary: bool = row
        .try_get("site_monetary_books")
        .map_err(|_| JournalError::Projection)?;
    let lines: Option<&str> = row.try_get("lines").map_err(|_| JournalError::Projection)?;
    if monetary != lines.is_some() {
        return Err(JournalError::Projection);
    }
    let statement = lines
        .map(|json| {
            serde_json::from_str::<Lines>(json)
                .map_err(|_| JournalError::Projection)?
                .to_summary(site_id, resolve_tick)
        })
        .transpose()?;
    Ok(PublishedSitePeriod {
        campaign_id,
        site_id,
        resolve_tick,
        foundation_sha256: bytes(row, "foundation_sha256")?,
        tick_content_hash: bytes(row, "tick_content_hash")?,
        receipt_sha256: bytes(row, "receipt_sha256")?,
        statement,
        stocks: Vec::new(),
    })
}

fn optional_number<T: FromStr>(row: &Row, key: &str) -> Result<Option<T>, JournalError> {
    row.try_get::<_, Option<&str>>(key)
        .map_err(|_| JournalError::Projection)?
        .map(str::parse)
        .transpose()
        .map_err(|_| JournalError::Projection)
}
fn position(
    row: &Row,
    quantity: &str,
    basis: &str,
    monetary: bool,
) -> Result<Option<SiteStockPosition>, JournalError> {
    let units = optional_number(row, quantity)?;
    let cost = optional_number(row, basis)?.map(Currency::from_micro_units);
    if cost.is_some() != (units.is_some() && monetary) {
        return Err(JournalError::Projection);
    }
    Ok(units.map(|quantity| SiteStockPosition {
        quantity,
        carrying_cost: cost,
    }))
}

fn verified_site(
    tx: &mut Transaction<'_>,
    headers: &[Row],
    campaign: CampaignId,
    site: SiteId,
) -> Result<(), JournalError> {
    for row in headers {
        if row
            .try_get::<_, Option<&[u8]>>("entry")
            .map_err(|_| JournalError::Projection)?
            .is_none()
        {
            // Missing rows have no ordinal. Check the independent directory once on this error path.
            let tick = row
                .try_get::<_, i64>("resolve_tick")
                .map_err(|_| JournalError::Projection)?;
            let marker = tx
                .query_one(
                    "SELECT site_accounting_directory, site_accounting_sha256
                   FROM public.v_observer_money_journal_period_v1
                  WHERE campaign_id = $1 AND resolve_tick = $2",
                    &[campaign.as_uuid(), &tick],
                )
                .map_err(|_| JournalError::Database)?;
            let directory = marker
                .try_get::<_, &[u8]>(0)
                .map_err(|_| JournalError::Projection)?;
            let expected = bytes(&marker, "site_accounting_sha256")?;
            return Err(
                if statement_integrity::contains(directory, &expected, site)? {
                    JournalError::Projection
                } else {
                    JournalError::SiteAbsent
                },
            );
        }
    }
    Ok(())
}

fn verify(entry: &PublishedSitePeriod, header: &Row) -> Result<(), JournalError> {
    let context = SiteEvidence {
        campaign: entry.campaign_id,
        tick: entry.resolve_tick,
        foundation: entry.foundation_sha256,
        content: entry.tick_content_hash,
        receipts: entry.receipt_sha256,
    };
    let actual = context.fingerprint(entry.site_id, entry.statement.as_ref(), &entry.stocks)?;
    let expected = header
        .try_get::<_, &[u8]>("entry")
        .map_err(|_| JournalError::Projection)?;
    if !statement_integrity::matches(expected, entry.site_id, &actual) {
        return Err(JournalError::Projection);
    }
    Ok(())
}

impl ObserverEconomyReader {
    /// Read one covered site's financial statements and native-unit stocks.
    /// # Errors
    /// Refuses restricted readers, missing coverage or site, and malformed facts.
    pub fn published_site_period(
        &self,
        campaign: CampaignId,
        tick: u64,
        site: SiteId,
    ) -> Result<PublishedSitePeriod, JournalError> {
        self.published_site_history(
            campaign,
            PeriodWindow {
                first: tick,
                last: tick,
            },
            site,
        )?
        .pop()
        .ok_or(JournalError::CoverageAbsent)
    }

    /// Read inclusive compact history for a single authenticated site in ascending period order.
    /// These permanent facts remain available after the thirteen-period transfer detail expires.
    /// # Errors
    /// Refuses a missing period anywhere in the range, an unknown site, and invalid facts or authority.
    pub fn published_site_history(
        &self,
        campaign: CampaignId,
        window: PeriodWindow,
        site: SiteId,
    ) -> Result<Vec<PublishedSitePeriod>, JournalError> {
        let (first, last) = window.bounds()?;
        let mut client = storage::open_observer(self)?;
        let mut tx = client
            .build_transaction()
            .isolation_level(IsolationLevel::RepeatableRead)
            .read_only(true)
            .start()
            .map_err(|_| JournalError::Database)?;
        tx.batch_execute(MATERIAL_READ_TRANSACTION_OPTIONS)
            .map_err(|_| JournalError::Database)?;
        let id = site.as_bytes();
        let params: &[&(dyn ToSql + Sync)] = &[campaign.as_uuid(), &first, &last, &id.as_slice()];
        let headers = tx
            .query(STATEMENTS, params)
            .map_err(|_| JournalError::Database)?;
        let expected = usize::try_from(last - first + 1).map_err(|_| JournalError::Range)?;
        if headers.len() != expected {
            return Err(JournalError::CoverageAbsent);
        }
        verified_site(&mut tx, &headers, campaign, site)?;
        let stocks = tx
            .query(STOCKS, params)
            .map_err(|_| JournalError::Database)?;
        tx.commit().map_err(|_| JournalError::Database)?;
        let mut history = headers
            .iter()
            .map(|r| site_period(campaign, site, r))
            .collect::<Result<Vec<_>, _>>()?;
        for row in stocks {
            let offset = period(&row)?
                .checked_sub(window.first)
                .ok_or(JournalError::Projection)?;
            let entry = history
                .get_mut(usize::try_from(offset).map_err(|_| JournalError::Range)?)
                .ok_or(JournalError::Projection)?;
            let monetary = entry.statement.is_some();
            entry.stocks.push(SiteStockBalance {
                site_id: site,
                good_id: GoodId::from_bytes(bytes(&row, "good_id")?),
                unit_id: UnitId::from_bytes(bytes(&row, "unit_id")?),
                opening: position(
                    &row,
                    "opening_quantity",
                    "opening_carrying_cost_micros",
                    monetary,
                )?,
                closing: position(
                    &row,
                    "closing_quantity",
                    "closing_carrying_cost_micros",
                    monetary,
                )?,
            });
        }
        for (entry, header) in history.iter().zip(&headers) {
            verify(entry, header)?;
        }
        Ok(history)
    }
}
