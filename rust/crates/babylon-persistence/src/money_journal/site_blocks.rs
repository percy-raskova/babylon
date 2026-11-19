//! Pack one authenticated period from its typed rows and verify the same representation on retry.
use super::payment_storage::Admission;
use super::JournalError;
use crate::identity::CampaignId;
use postgres::Transaction;

pub(super) fn prepare(tx: &mut Transaction<'_>) -> Result<(), JournalError> {
    // The source is streamed in bounded JSON batches. A period may omit sites and
    // a commodity may cross any batch boundary, so group only after both sources end.
    tx.batch_execute(include_str!("site_sources.sql"))
        .map_err(|_| JournalError::Database)
}

pub(super) fn publish(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    tick: u64,
    mode: Admission,
) -> Result<(), JournalError> {
    let tick = i64::try_from(tick).map_err(|_| JournalError::Range)?;
    tx.batch_execute("ANALYZE pg_temp.site_statement_source; ANALYZE pg_temp.site_stock_source")
        .map_err(|_| JournalError::Database)?;
    let scope = tx
        .query_one(
            "SELECT NOT EXISTS(SELECT FROM pg_temp.site_statement_source WHERE (campaign_id,resolve_tick)<>($1,$2))
               AND NOT EXISTS(SELECT FROM pg_temp.site_stock_source WHERE (campaign_id,resolve_tick)<>($1,$2))",
            &[campaign.as_uuid(), &tick],
        )
        .map_err(|_| JournalError::Database)?;
    if !scope
        .try_get::<_, bool>(0)
        .map_err(|_| JournalError::Projection)?
    {
        return Err(JournalError::Projection);
    }
    for (table, source, order) in [
        (
            "babylon_state.site_statement_block_v1",
            include_str!("site_statement_blocks.sql"),
            "block_key",
        ),
        (
            "babylon_state.site_stock_block_v1",
            include_str!("site_stock_blocks.sql"),
            "block_key,commodity_ordinal",
        ),
    ] {
        let params: &[&(dyn postgres::types::ToSql + Sync)] = &[campaign.as_uuid(), &tick];
        if mode == Admission::Verify {
            let query = format!(
                "WITH expected AS MATERIALIZED ({source}), stored AS MATERIALIZED
                 (SELECT * FROM {table} WHERE campaign_id=$1 AND resolve_tick=$2)
                 SELECT NOT EXISTS(SELECT FROM ((TABLE expected EXCEPT ALL TABLE stored)
                     UNION ALL (TABLE stored EXCEPT ALL TABLE expected)) AS difference)"
            );
            let valid: bool = tx
                .query_one(&query, params)
                .map_err(|_| JournalError::Database)?
                .try_get(0)
                .map_err(|_| JournalError::Projection)?;
            if !valid {
                return Err(JournalError::Projection);
            }
        } else {
            let query =
                format!("INSERT INTO {table} SELECT * FROM ({source}) AS blocks ORDER BY {order}");
            tx.execute(&query, params)
                .map_err(|_| JournalError::Database)?;
        }
    }
    Ok(())
}
