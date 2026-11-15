//! Publish compact statement and stock facts in the source journal's transaction.
use super::payment_storage::Admission;
use super::statement_integrity::SiteEvidence;
use super::statement_lines::Lines;
use super::JournalError;
use crate::economic_content::EconomicContentHandle;
use crate::economic_flows::EconomicPaymentPeriod;
use crate::identity::CampaignId;
use crate::qualification_audit::trade;
use crate::site_financial_statements::{SiteAccountingPeriod, SiteStockBalance, SiteStockPosition};
use babylon_material_circuit::SiteId;
use postgres::{Statement, Transaction};
use serde::Serialize;
use sha2::{Digest, Sha256};

pub(crate) struct JournalPeriodSource {
    pub foundation: EconomicContentHandle,
    pub payments: EconomicPaymentPeriod,
    pub accounting: SiteAccountingPeriod,
    /// All admitted sites, including physical-control sites without stock at either boundary.
    pub sites: Vec<SiteId>,
}

pub(super) struct SiteBinding {
    pub directory: Vec<u8>,
    pub digest: [u8; 32],
    pub monetary: bool,
    pub sites: i64,
    pub stocks: i64,
}

#[derive(Serialize)]
struct StatementRow<'a> {
    site_ordinal: usize,
    campaign_id: &'a str,
    resolve_tick: u64,
    site_id: String,
    #[serde(flatten)]
    lines: Lines,
}

#[derive(Serialize)]
struct StockRow<'a> {
    campaign_id: &'a str,
    resolve_tick: u64,
    site_id: String,
    good_id: String,
    unit_id: String,
    opening_quantity: Option<u64>,
    closing_quantity: Option<u64>,
    opening_carrying_cost_micros: Option<String>,
    closing_carrying_cost_micros: Option<String>,
}

pub(super) fn bytea(id: &[u8; 32]) -> String {
    format!("\\x{}", trade::hex(id))
}

impl<'a> StockRow<'a> {
    fn from_source(campaign_id: &'a str, resolve_tick: u64, row: &SiteStockBalance) -> Self {
        fn cost(position: SiteStockPosition) -> Option<String> {
            position.carrying_cost.map(|v| v.micro_units().to_string())
        }
        Self {
            campaign_id,
            resolve_tick,
            site_id: bytea(&row.site_id.as_bytes()),
            good_id: bytea(&row.good_id.as_bytes()),
            unit_id: bytea(&row.unit_id.as_bytes()),
            opening_quantity: row.opening.map(|v| v.quantity),
            closing_quantity: row.closing.map(|v| v.quantity),
            opening_carrying_cost_micros: row.opening.and_then(cost),
            closing_carrying_cost_micros: row.closing.and_then(cost),
        }
    }
}

#[derive(Clone, Copy)]
pub(super) enum Table {
    CompanyBalance,
    CompanyIncome,
    CompanyCash,
    CompanyElimination,
    CompanyEntry,

    Company,
    CompanyMember,
    CompanyClaim,
    CompanyClaimSource,

    LaborNode,
    LaborMovement,
    LaborPosition,
    Statement,
    Stock,
}
impl Table {
    pub(super) fn relation(self) -> (&'static str, &'static str) {
        match self {
            Self::CompanyBalance => (
                "babylon_state.company_statement_balance_v1",
                "campaign_id,resolve_tick,company_id,scope,boundary",
            ),
            Self::CompanyIncome => (
                "babylon_state.company_statement_income_v1",
                "campaign_id,resolve_tick,company_id,scope",
            ),
            Self::CompanyCash => (
                "babylon_state.company_statement_cash_flow_v1",
                "campaign_id,resolve_tick,company_id,scope",
            ),
            Self::CompanyElimination => (
                "babylon_state.company_elimination_v1",
                "campaign_id,resolve_tick,company_id",
            ),
            Self::CompanyEntry => (
                "babylon_state.company_realization_entry_v1",
                "campaign_id,resolve_tick,company_id,family,ordinal",
            ),

            Self::Company => (
                "babylon_state.economic_company_v1",
                "campaign_id,company_id",
            ),
            Self::CompanyMember => (
                "babylon_state.economic_company_member_v1",
                "campaign_id,site_id",
            ),
            Self::CompanyClaim => (
                "babylon_state.economic_company_claim_v1",
                "campaign_id,company_id,beneficiary_kind,beneficiary_id",
            ),
            Self::CompanyClaimSource => (
                "babylon_state.economic_company_claim_source_v1",
                "campaign_id,site_id,beneficiary_kind,beneficiary_id",
            ),

            Self::LaborNode => (
                "babylon_state.labor_node_v1",
                "campaign_id,resolve_tick,node_ordinal",
            ),
            Self::LaborMovement => (
                "babylon_state.labor_movement_v1",
                "campaign_id,resolve_tick,ordinal",
            ),
            Self::LaborPosition => (
                "babylon_state.labor_position_v1",
                "campaign_id,resolve_tick,side,node_ordinal",
            ),
            Self::Statement => (
                "babylon_state.site_statement_v1",
                "campaign_id,resolve_tick,site_id",
            ),
            Self::Stock => (
                "babylon_state.site_stock_balance_v1",
                "campaign_id,resolve_tick,site_id,good_id,unit_id",
            ),
        }
    }

    fn sql(self, admission: Admission) -> String {
        let (table, keys) = self.relation();
        let input = format!("jsonb_populate_recordset(NULL::{table},$1::text::jsonb)");
        if admission == Admission::Verify {
            // Each expected composite gets one scalar lookup by the full primary key.
            // An absent row is NULL. IS DISTINCT FROM also compares nullable fields.
            let lookup = keys
                .split(',')
                .map(|key| format!("d.{key}=e.{key}"))
                .collect::<Vec<_>>()
                .join(" AND ");
            format!(
                "SELECT NOT EXISTS (
                     SELECT FROM {input} e WHERE e IS DISTINCT FROM (
                         SELECT d FROM {table} d WHERE {lookup}
                     )
                 )"
            )
        } else {
            format!("INSERT INTO {table} SELECT * FROM {input}")
        }
    }
}

pub(super) struct Batch<'a, 'b> {
    pub(super) tx: &'a mut Transaction<'b>,
    pub(super) admission: Admission,
}

impl Batch<'_, '_> {
    pub(super) fn stage<T: Serialize>(
        &mut self,
        table: Table,
        rows: impl Iterator<Item = T>,
    ) -> Result<(), JournalError> {
        let sql = table.sql(self.admission);
        let prepared = self.tx.prepare(&sql).map_err(|_| JournalError::Database)?;
        let mut payload = String::from("[");
        let mut count = 0;
        for row in rows {
            let json = serde_json::to_string(&row).map_err(|_| JournalError::Projection)?;
            if count != 0 {
                payload.push(',');
            }
            payload.push_str(&json);
            count += 1;
            if count == 256 {
                self.send(&prepared, &mut payload)?;
                count = 0;
            }
        }
        if count != 0 {
            self.send(&prepared, &mut payload)?;
        }
        Ok(())
    }

    fn send(&mut self, query: &Statement, payload: &mut String) -> Result<(), JournalError> {
        payload.push(']');
        if self.admission == Admission::Verify {
            let valid: bool = self
                .tx
                .query_one(query, &[payload])
                .map_err(|_| JournalError::Database)?
                .try_get(0)
                .map_err(|_| JournalError::Projection)?;
            if !valid {
                return Err(JournalError::Projection);
            }
        } else {
            self.tx
                .execute(query, &[payload])
                .map_err(|_| JournalError::Database)?;
        }
        payload.clear();
        payload.push('[');
        Ok(())
    }
}

pub(super) fn publish(
    tx: &mut Transaction<'_>,
    source: &JournalPeriodSource,
    admission: Admission,
) -> Result<SiteBinding, JournalError> {
    let period = &source.accounting;
    let receipts = &source.payments.source;
    let campaign = receipts.campaign_id;
    let tick = period.resolve_tick;
    let monetary = period.statements.is_some();
    if tick != receipts.identity.resolve_tick() {
        return Err(JournalError::Projection);
    }
    if let Some(rows) = &period.statements {
        if !rows
            .iter()
            .map(|row| row.site_id)
            .eq(source.sites.iter().copied())
        {
            return Err(JournalError::Projection);
        }
    }
    let campaign_text = campaign.as_uuid().to_string();
    let evidence = SiteEvidence {
        campaign,
        tick,
        foundation: receipts.identity.foundation_digest(),
        content: *receipts.identity.tick_content_hash().as_bytes(),
        receipts: receipts.identity.receipt_digest(),
    };
    let directory = directory(source, &evidence)?;
    let mut batch = Batch { tx, admission };
    let mut summaries = period.statements.as_deref().unwrap_or_default().iter();
    batch.stage(
        Table::Statement,
        source
            .sites
            .iter()
            .enumerate()
            .map(|(ordinal, site)| StatementRow {
                site_ordinal: ordinal,
                campaign_id: &campaign_text,
                resolve_tick: tick,
                site_id: bytea(&site.as_bytes()),
                lines: summaries
                    .next()
                    .map(Lines::from_summary)
                    .unwrap_or_default(),
            }),
    )?;
    batch.stage(
        Table::Stock,
        period
            .stocks
            .iter()
            .map(|row| StockRow::from_source(&campaign_text, tick, row)),
    )?;
    let binding = SiteBinding {
        digest: Sha256::digest(&directory).into(),
        directory,
        monetary,
        sites: i64::try_from(source.sites.len()).map_err(|_| JournalError::Range)?,
        stocks: i64::try_from(period.stocks.len()).map_err(|_| JournalError::Range)?,
    };
    if admission == Admission::Verify {
        verify_binding(tx, campaign, tick, &binding)?;
    }
    Ok(binding)
}

fn directory(
    source: &JournalPeriodSource,
    evidence: &SiteEvidence,
) -> Result<Vec<u8>, JournalError> {
    // One ID and one digest per site, independent of the number of stock lines.
    let length = source
        .sites
        .len()
        .checked_mul(64)
        .filter(|len| *len < 1 << 30)
        .ok_or(JournalError::Range)?;
    let mut bytes = Vec::with_capacity(length);
    let mut stocks = source.accounting.stocks.as_slice();
    let mut summaries = source
        .accounting
        .statements
        .as_deref()
        .unwrap_or_default()
        .iter();
    for &site in &source.sites {
        let count = stocks.iter().take_while(|s| s.site_id == site).count();
        let (positions, remaining) = stocks.split_at(count);
        bytes.extend_from_slice(&site.as_bytes());
        bytes.extend_from_slice(&evidence.fingerprint(site, summaries.next(), positions)?);
        stocks = remaining;
    }
    if !stocks.is_empty() {
        return Err(JournalError::Projection);
    }
    Ok(bytes)
}

fn verify_binding(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    tick: u64,
    source: &SiteBinding,
) -> Result<(), JournalError> {
    let tick = i64::try_from(tick).map_err(|_| JournalError::Range)?;
    let row = tx
        .query_one(
            "SELECT site_accounting_sha256 = $3 AND site_monetary_books = $4 AND site_count = $5
                AND site_stock_count = $6 AND site_accounting_directory = $7
                AND site_count = (SELECT count(*) FROM babylon_state.site_statement_v1
                                   WHERE campaign_id = $1 AND resolve_tick = $2)
                AND site_stock_count = (SELECT count(*) FROM babylon_state.site_stock_balance_v1
                                         WHERE campaign_id = $1 AND resolve_tick = $2)
           FROM babylon_state.money_journal_period_v1 WHERE campaign_id = $1 AND resolve_tick = $2",
            &[
                campaign.as_uuid(),
                &tick,
                &source.digest.as_slice(),
                &source.monetary,
                &source.sites,
                &source.stocks,
                &source.directory,
            ],
        )
        .map_err(|_| JournalError::Database)?;
    let valid: bool = row.try_get(0).map_err(|_| JournalError::Projection)?;
    if !valid {
        return Err(JournalError::Projection);
    }
    Ok(())
}
