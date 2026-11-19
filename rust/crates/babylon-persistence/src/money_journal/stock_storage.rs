//! Period stock amounts reference reversible site and native commodity identities.
use super::payment_storage::Admission;
use super::statement_storage::{self, Batch, Table};
use super::JournalError;
use crate::identity::CampaignId;
use crate::site_financial_statements::{SiteStockBalance, SiteStockPosition};
use babylon_material_circuit::SiteId;
use serde::Serialize;
use std::collections::BTreeMap;

#[derive(Serialize)]
struct StockKey<'a> {
    campaign_id: &'a str,
    resolve_tick: u64,
    commodity_ordinal: i32,
    good_id: String,
    unit_id: String,
}

#[derive(Serialize)]
struct Stock<'a> {
    campaign_id: &'a str,
    resolve_tick: u64,
    site_key: i32,
    commodity_ordinal: i32,
    opening_quantity: Option<u64>,
    closing_quantity: Option<u64>,
    opening_carrying_cost_micros: Option<String>,
    closing_carrying_cost_micros: Option<String>,
}

fn cost(position: SiteStockPosition) -> Option<String> {
    position.carrying_cost.map(|v| v.micro_units().to_string())
}

pub(super) fn stage(
    batch: &mut Batch<'_, '_>,
    campaign: CampaignId,
    tick: u64,
    sites: &BTreeMap<SiteId, i32>,
    stocks: &[SiteStockBalance],
) -> Result<(), JournalError> {
    let id = campaign.as_uuid().to_string();
    let mut keys = BTreeMap::new();
    let mut ordinals = Vec::with_capacity(stocks.len());
    for row in stocks {
        let next = i32::try_from(keys.len()).map_err(|_| JournalError::Range)?;
        let commodity = *keys.entry((row.good_id, row.unit_id)).or_insert(next);
        let site = sites
            .get(&row.site_id)
            .copied()
            .ok_or(JournalError::Projection)?;
        ordinals.push((site, commodity));
    }
    batch.stage(
        Table::StockKey,
        keys.iter().map(|((good, unit), &ordinal)| StockKey {
            campaign_id: &id,
            resolve_tick: tick,
            commodity_ordinal: ordinal,
            good_id: statement_storage::bytea(&good.as_bytes()),
            unit_id: statement_storage::bytea(&unit.as_bytes()),
        }),
    )?;
    if batch.admission == Admission::Verify {
        let tick = i64::try_from(tick).map_err(|_| JournalError::Range)?;
        let row=batch.tx.query_one("SELECT count(*) FROM babylon_state.site_stock_key_v1 WHERE campaign_id=$1 AND resolve_tick=$2",
            &[campaign.as_uuid(),&tick]).map_err(|_|JournalError::Database)?;
        let count: i64 = row.try_get(0).map_err(|_| JournalError::Projection)?;
        if count != i64::try_from(keys.len()).map_err(|_| JournalError::Range)? {
            return Err(JournalError::Projection);
        }
    }
    batch.stage(
        Table::Stock,
        stocks
            .iter()
            .zip(ordinals)
            .map(|(row, (site_key, commodity_ordinal))| Stock {
                campaign_id: &id,
                resolve_tick: tick,
                site_key,
                commodity_ordinal,
                opening_quantity: row.opening.map(|v| v.quantity),
                closing_quantity: row.closing.map(|v| v.quantity),
                opening_carrying_cost_micros: row.opening.and_then(cost),
                closing_carrying_cost_micros: row.closing.and_then(cost),
            }),
    )
}
