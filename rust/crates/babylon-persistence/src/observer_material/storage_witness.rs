//! Fresh equality of the exact inputs to an already admitted material-history fold.

use postgres::GenericClient;
use sha2::{Digest, Sha256};

use super::{CampaignId, MaterialObservationRow, ObserverEconomyError};

const ROW_DOMAIN: &[u8] = b"babylon.observer-material-storage.v1\0";
const PREFIX_DOMAIN: &[u8] = b"babylon.observer-material-prefix.v1\0";
const PAGE_ROWS: i64 = 128;

pub(super) fn seed() -> [u8; 32] {
    Sha256::digest(PREFIX_DOMAIN).into()
}

pub(super) fn append(prefix: [u8; 32], row: [u8; 32]) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(PREFIX_DOMAIN);
    hash.update(prefix);
    hash.update(row);
    hash.finalize().into()
}

pub(super) fn fingerprint(row: &MaterialObservationRow) -> Result<[u8; 32], ObserverEconomyError> {
    let mut hash = Sha256::new();
    hash.update(ROW_DOMAIN);
    hash.update(row.row_campaign.as_bytes());
    hash.update(row.row_tick.to_be_bytes());
    for field in [
        Some(row.register_storage_bytes.as_slice()),
        row.receipts.as_deref(),
        row.identity.as_deref(),
        row.lookup_delta.as_deref(),
        row.content_hash.as_deref(),
    ] {
        if let Some(bytes) = field {
            hash.update([1]);
            let length =
                i64::try_from(bytes.len()).map_err(|_| ObserverEconomyError::InvalidProjection)?;
            hash.update(length.to_be_bytes());
            hash.update(Sha256::digest(bytes));
        } else {
            hash.update([0]);
        }
    }
    Ok(hash.finalize().into())
}

/// No historical package leaves `PostgreSQL`. The server still hashes its exact
/// bytes; this is a decode cache, not a substitute for authenticated input.
pub(super) fn verify_prefix(
    transaction: &mut impl GenericClient,
    campaign: CampaignId,
    through: u64,
    expected: [u8; 32],
) -> Result<(), ObserverEconomyError> {
    let through = i64::try_from(through).map_err(|_| ObserverEconomyError::TickAbsent)?;
    let frames = [
        "register_storage_bytes",
        "receipt_storage_bytes",
        "identity_bytes",
        "lookup_delta_bytes",
        "tick_content_hash",
    ]
    .map(|column| {
        format!(
            "CASE WHEN {column} IS NULL THEN pg_catalog.decode('00','hex') \
             ELSE pg_catalog.decode('01','hex') \
             || pg_catalog.int8send(pg_catalog.octet_length({column})::bigint) \
             || pg_catalog.sha256({column}) END"
        )
    })
    .join(" || ");
    let query = format!(
        "SELECT resolve_tick, pg_catalog.sha256($3::bytea \
         || pg_catalog.uuid_send(campaign_id) || pg_catalog.int8send(resolve_tick) || {frames}) \
         FROM public.v_observer_material_state_v1 \
         WHERE campaign_id=$1 AND resolve_tick BETWEEN $2 AND $4 \
         ORDER BY resolve_tick LIMIT 129"
    );
    let mut prefix = seed();
    let mut start = 0_i64;
    loop {
        let end = start
            .checked_add((through - start).min(PAGE_ROWS - 1))
            .ok_or(ObserverEconomyError::TickAbsent)?;
        let rows = transaction
            .query(&query, &[campaign.as_uuid(), &start, &ROW_DOMAIN, &end])
            .map_err(|_| ObserverEconomyError::Database)?;
        let count = usize::try_from(end - start + 1)
            .map_err(|_| ObserverEconomyError::InvalidProjection)?;
        if rows.len() != count {
            return Err(ObserverEconomyError::InvalidProjection);
        }
        for (offset, row) in rows.iter().enumerate() {
            let tick: i64 = row
                .try_get(0)
                .map_err(|_| ObserverEconomyError::InvalidProjection)?;
            let digest: Vec<u8> = row
                .try_get(1)
                .map_err(|_| ObserverEconomyError::InvalidProjection)?;
            let offset =
                i64::try_from(offset).map_err(|_| ObserverEconomyError::InvalidProjection)?;
            if Some(tick) != start.checked_add(offset) {
                return Err(ObserverEconomyError::InvalidProjection);
            }
            prefix = append(
                prefix,
                digest
                    .try_into()
                    .map_err(|_| ObserverEconomyError::InvalidProjection)?,
            );
        }
        if end == through {
            break;
        }
        start = end.checked_add(1).ok_or(ObserverEconomyError::TickAbsent)?;
    }
    if prefix != expected {
        return Err(ObserverEconomyError::InvalidProjection);
    }
    Ok(())
}
