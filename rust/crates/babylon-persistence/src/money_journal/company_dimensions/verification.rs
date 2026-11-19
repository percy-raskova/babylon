//! Compare reconstructed claims to admitted source rows in their native owner order.
use crate::money_journal::statement_storage::Table;
use crate::money_journal::JournalError;
use postgres::Transaction;
use serde::Serialize;
use serde_json::Value;
use uuid::Uuid;

const BATCH: u16 = 256;
const OWNER_ORDER: &str = "array_position(ARRAY['site_cash','household_cash','organization_cash','public_cash'],beneficiary_kind),beneficiary_id";

pub(super) fn verify<T: Serialize>(
    tx: &mut Transaction<'_>,
    table: Table,
    campaign: &Uuid,
    mut expected: impl Iterator<Item = T>,
) -> Result<(), JournalError> {
    // Encode micros and beneficial weights as decimal strings, matching the typed
    // source. Ownership shares fit u64 and retain their JSON integer representation.
    let (first, decimals) = match table {
        Table::CompanyClaim => ("company_id", "'weight', d.weight::text"),
        Table::CompanyClaimSource => ("site_id", "'capital_micros', d.capital_micros::text, 'original_carrying_micros', d.original_carrying_micros::text"),
        _ => return Err(JournalError::Projection),
    };
    let (name, _) = table.relation();
    let scan = format!(
        "SELECT (to_jsonb(d) || jsonb_build_object({decimals}))::text FROM {name} d
         WHERE campaign_id=$1 ORDER BY {first},{OWNER_ORDER}"
    );
    let cursor = tx
        .bind(&scan, &[campaign])
        .map_err(|_| JournalError::Database)?;
    loop {
        let fetched = tx
            .query_portal(&cursor, i32::from(BATCH))
            .map_err(|_| JournalError::Database)?;
        for row in &fetched {
            let source = expected.next().ok_or(JournalError::Projection)?;
            let source = serde_json::to_value(source).map_err(|_| JournalError::Projection)?;
            let text: &str = row.try_get(0).map_err(|_| JournalError::Projection)?;
            let stored: Value = serde_json::from_str(text).map_err(|_| JournalError::Projection)?;
            if source != stored {
                return Err(JournalError::Projection);
            }
        }
        if fetched.len() < usize::from(BATCH) {
            break;
        }
    }
    if expected.next().is_some() {
        return Err(JournalError::Projection);
    }
    Ok(())
}
