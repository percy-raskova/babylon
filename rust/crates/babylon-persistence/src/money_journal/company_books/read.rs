//! Read permanent statements and elimination entries under one full-observer snapshot.
use super::{rows, source};
use crate::company_statements::{CompanyPeriod, CompanyPeriodReport};
use crate::identity::CampaignId;
use crate::money_journal::{storage, JournalError};
use crate::observer_reader::{ObserverEconomyReader, MATERIAL_READ_TRANSACTION_OPTIONS};
use crate::qualification_audit::trade;
use postgres::{IsolationLevel, Transaction};
use serde_json::{json, Value};
use std::collections::BTreeMap;

const AMOUNTS: &str = "(
    SELECT jsonb_object_agg(left(k, -7), v)::text
    FROM jsonb_each_text(to_jsonb(s)) AS fields(k,v)
    WHERE right(k, 7) = '_micros')";

const ENTRIES: &str = "
    SELECT encode(company_id, 'hex'), jsonb_build_object(
        'family', family,
        'ordinal', ordinal,
        'kind', kind,
        'from_kind', from_kind,
        'from_id', encode(from_id, 'hex'),
        'to_kind', to_kind,
        'to_id', encode(to_id, 'hex'),
        'amount_micros', amount_micros::text,
        'legal_cost_micros', legal_cost_micros::text,
        'group_cost_micros', group_cost_micros::text,
        'margin_created_micros', margin_created_micros::text,
        'margin_realized_micros', margin_realized_micros::text
    )::text
    FROM public.v_observer_company_realization_entry_v1
    WHERE campaign_id = $1 AND resolve_tick = $2
    ORDER BY company_id, family, ordinal";

const PERIOD: &str = "
    SELECT * FROM public.v_observer_company_accounting_period_v1
    WHERE campaign_id = $1 AND resolve_tick = $2";

const COVERAGE: &str = "
    SELECT EXISTS (
        SELECT FROM public.v_observer_money_journal_period_v1
        WHERE campaign_id = $1 AND resolve_tick = $2),
        EXISTS (
        SELECT FROM public.v_observer_economic_company_v1 WHERE campaign_id = $1)";

fn assemble(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    tick: i64,
) -> Result<Vec<CompanyPeriod>, JournalError> {
    let mut groups = BTreeMap::<String, Value>::new();
    let params: &[&(dyn postgres::types::ToSql + Sync)] = &[campaign.as_uuid(), &tick];
    for (table, category) in [
        ("company_elimination_v1", "eliminations"),
        ("company_statement_balance_v1", "balance"),
        ("company_statement_cash_flow_v1", "cash_flow"),
        ("company_statement_income_v1", "income"),
    ] {
        let (scope, side) = match category {
            "eliminations" => ("''::text", "''::text"),
            "balance" => ("scope", "boundary"),
            _ => ("scope", "''::text"),
        };
        let sql = format!(
            "SELECT encode(company_id, 'hex'), {scope}, {side}, {AMOUNTS}
             FROM public.v_observer_{table} s
             WHERE campaign_id = $1 AND resolve_tick = $2"
        );
        for row in tx.query(&sql, params).map_err(|_| JournalError::Database)? {
            let company: String = row.try_get(0).map_err(|_| JournalError::Projection)?;
            let scope: &str = row.try_get(1).map_err(|_| JournalError::Projection)?;
            let side: &str = row.try_get(2).map_err(|_| JournalError::Projection)?;
            let data = serde_json::from_str(
                row.try_get::<_, &str>(3)
                    .map_err(|_| JournalError::Projection)?,
            )
            .map_err(|_| JournalError::Projection)?;
            let node = groups
                .entry(company.clone())
                .or_insert_with(|| json!({"company": company, "entries": []}));
            if scope.is_empty() {
                node[category] = data;
            } else if side.is_empty() {
                node[scope][category] = data;
            } else {
                node[scope][side] = data;
            }
        }
    }
    for row in tx
        .query(ENTRIES, params)
        .map_err(|_| JournalError::Database)?
    {
        let company: &str = row.try_get(0).map_err(|_| JournalError::Projection)?;
        let data = serde_json::from_str(
            row.try_get::<_, &str>(1)
                .map_err(|_| JournalError::Projection)?,
        )
        .map_err(|_| JournalError::Projection)?;
        groups
            .get_mut(company)
            .and_then(|r| r.get_mut("entries"))
            .and_then(Value::as_array_mut)
            .ok_or(JournalError::Projection)?
            .push(data);
    }
    groups
        .into_values()
        .map(|r| serde_json::from_value(r).map_err(|_| JournalError::Projection))
        .collect()
}
impl ObserverEconomyReader {
    /// Read all legal and consolidated statements from permanent SQL facts and verify the source-bound digest.
    /// # Errors
    /// Refuses restricted credentials, missing company coverage or modified fact content.
    pub fn published_company_period_statements(
        &self,
        campaign: CampaignId,
        period: u64,
    ) -> Result<CompanyPeriodReport, JournalError> {
        let mut client = storage::open_observer(self)?;
        let tick = i64::try_from(period).map_err(|_| JournalError::Range)?;
        if tick == 0 {
            return Err(JournalError::Range);
        }
        let mut tx = client
            .build_transaction()
            .isolation_level(IsolationLevel::RepeatableRead)
            .read_only(true)
            .start()
            .map_err(|_| JournalError::Database)?;
        tx.batch_execute(MATERIAL_READ_TRANSACTION_OPTIONS)
            .map_err(|_| JournalError::Database)?;
        let period_key: &[&(dyn postgres::types::ToSql + Sync)] = &[campaign.as_uuid(), &tick];
        let marker = tx
            .query_opt(PERIOD, period_key)
            .map_err(|_| JournalError::Database)?;
        let Some(row) = marker else {
            let status = tx
                .query_one(COVERAGE, period_key)
                .map_err(|_| JournalError::Database)?;
            return Err(
                match (
                    status.try_get(0).map_err(|_| JournalError::Projection)?,
                    status.try_get(1).map_err(|_| JournalError::Projection)?,
                ) {
                    (true, false) => JournalError::CompanyBooksNotCaptured,
                    (true, true) => JournalError::Projection,
                    _ => JournalError::CoverageAbsent,
                },
            );
        };
        let id = source::identity(&row)?;
        if id.result_world_hash() != source::digest(&row, "result_world_hash")? {
            return Err(JournalError::SourceChanged);
        }
        let companies = assemble(&mut tx, campaign, tick)?;
        let entries: usize = companies.iter().map(|c| c.entries.len()).sum();
        if i64::try_from(companies.len()).ok()
            != Some(
                row.try_get("company_count")
                    .map_err(|_| JournalError::Projection)?,
            )
            || i64::try_from(entries).ok()
                != Some(
                    row.try_get("entry_count")
                        .map_err(|_| JournalError::Projection)?,
                )
            || rows::fingerprint(campaign, &id, &companies)? != source::digest(&row, "fact_sha256")?
        {
            return Err(JournalError::Projection);
        }
        let report = CompanyPeriodReport {
            version: 1,
            campaign: campaign.as_uuid().to_string(),
            resolve_tick: period,
            foundation_sha256: trade::hex(&id.foundation_digest()),
            tick_content_hash: trade::hex(id.tick_content_hash().as_bytes()),
            receipt_sha256: trade::hex(&id.receipt_digest()),
            currency_unit: "micro".into(),
            companies,
        };
        tx.commit().map_err(|_| JournalError::Database)?;
        Ok(report)
    }
}
