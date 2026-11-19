//! Foundation-bound account attributes and economic principals of settled custody postings.
use super::{JournalError, MoneyMovement, MoneyPurpose};
use crate::economic_flows::{EconomicPaymentPeriod, FlowAccount, Settlement};
use crate::qualification_audit::trade;
use babylon_kernel::economic_identity::EconomicFunction;
use postgres::types::ToSql;
use postgres::Transaction;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;

#[derive(Clone, Copy, PartialEq, Eq)]
pub(super) enum Admission {
    Insert,
    Rebuild,
    Verify,
}

#[derive(Serialize)]
struct AccountRow<'a> {
    account_key: i32,
    kind: &'static str,
    id: String,
    location: Option<&'a str>,
    catchment: Option<&'a str>,
    industry: Option<&'a str>,
    label: Option<&'static str>,
    lon: Option<&'a str>,
    lat: Option<&'a str>,
}
impl<'a> AccountRow<'a> {
    fn from_source(index: usize, row: &'a FlowAccount) -> Result<Self, JournalError> {
        let industry = row.industry.as_deref();
        let label = industry
            .map(|key| EconomicFunction::from_source_key(key).ok_or(JournalError::Projection))
            .transpose()?
            .map(EconomicFunction::label);
        let point = row.county_internal_point.as_ref();
        Ok(Self {
            account_key: i32::try_from(index).map_err(|_| JournalError::Range)?,
            kind: row.account.kind.as_str(),
            id: trade::hex(&row.account.id),
            location: row.location.as_deref(),
            catchment: row.catchment.as_deref(),
            industry,
            label,
            lon: point.map(|p| p.longitude.as_str()),
            lat: point.map(|p| p.latitude.as_str()),
        })
    }
}

const ACCOUNT_SOURCE: &str = "
    WITH raw AS (
        SELECT * FROM jsonb_to_recordset($3::text::jsonb) AS x(
            account_key integer, kind text, id text, location text, catchment text,
            industry text, label text, lon numeric, lat numeric
        )
    ),
    a AS (
        SELECT account_key, kind, decode(id, 'hex') AS id, location, catchment, industry, label FROM raw
    ),
    g AS (
        SELECT DISTINCT location, lon, lat FROM raw WHERE lon IS NOT NULL
    )";

// A missing primary key yields NULL. IS NOT TRUE rejects absence along with
// mismatched foundation, nullable account attributes, or county coordinates.
const VERIFY_ACCOUNTS: &str = "
    SELECT NOT EXISTS (
        SELECT FROM a WHERE (
            SELECT d.foundation_sha256 = $2 AND (d.account_kind,d.account_id)=(a.kind,a.id)
                AND (d.location_key, d.catchment_key, d.industry_key, d.industry_label)
                    IS NOT DISTINCT FROM (a.location, a.catchment, a.industry, a.label)
            FROM babylon_state.economic_flow_account_v1 d
            WHERE d.campaign_id = $1 AND d.account_key = a.account_key
        ) IS NOT TRUE
    ) AND NOT EXISTS (
        SELECT FROM g WHERE (
            SELECT l.foundation_sha256 = $2
                AND record_send(ROW(l.longitude,l.latitude)) = record_send(ROW(g.lon,g.lat))
            FROM babylon_state.economic_flow_location_v1 l
            WHERE l.campaign_id = $1 AND l.location_key = g.location
        ) IS NOT TRUE
    )";

fn accounts_upsert(mode: Admission) -> Option<String> {
    let (point_conflict, account_conflict) = match mode {
        Admission::Verify => return None,
        Admission::Insert => ("DO NOTHING", "DO NOTHING"),
        Admission::Rebuild => (
            "DO UPDATE SET foundation_sha256 = EXCLUDED.foundation_sha256,
                 longitude = EXCLUDED.longitude, latitude = EXCLUDED.latitude
             WHERE l.foundation_sha256 <> EXCLUDED.foundation_sha256 OR
                 record_send(ROW(l.longitude,l.latitude)) <> record_send(ROW(EXCLUDED.longitude,EXCLUDED.latitude))",
            "DO UPDATE SET account_kind=EXCLUDED.account_kind, account_id=EXCLUDED.account_id,
                 foundation_sha256=EXCLUDED.foundation_sha256, location_key = EXCLUDED.location_key, catchment_key = EXCLUDED.catchment_key,
                 industry_key = EXCLUDED.industry_key, industry_label = EXCLUDED.industry_label
             WHERE (d.account_kind,d.account_id,d.foundation_sha256,d.location_key, d.catchment_key, d.industry_key, d.industry_label)
                 IS DISTINCT FROM (EXCLUDED.account_kind,EXCLUDED.account_id,EXCLUDED.foundation_sha256,EXCLUDED.location_key, EXCLUDED.catchment_key,
                                   EXCLUDED.industry_key, EXCLUDED.industry_label)",
        ),
    };
    Some(format!(
        "{ACCOUNT_SOURCE}, points AS (
             INSERT INTO babylon_state.economic_flow_location_v1 AS l
                 (campaign_id, foundation_sha256, location_key, longitude, latitude)
             SELECT $1, $2, location, lon, lat FROM g
             ON CONFLICT (campaign_id, location_key) {point_conflict}
         )
         INSERT INTO babylon_state.economic_flow_account_v1 AS d
             (campaign_id, account_key, foundation_sha256, account_kind, account_id,
              location_key, catchment_key, industry_key, industry_label)
         SELECT $1, account_key, $2, kind, id, location, catchment, industry, label FROM a
         ON CONFLICT (campaign_id, account_key) {account_conflict}"
    ))
}

// Return whether the selected campaign already owns any account rows. The
// occupied flag only chooses which statement to attempt first. Row admission
// still checks the full source ordinal, identity, attributes and numeric point.
fn admit_directory_extent(
    tx: &mut Transaction<'_>,
    period: &EconomicPaymentPeriod,
    mode: Admission,
) -> Result<bool, JournalError> {
    let campaign = period.source.campaign_id.as_uuid();
    let count = i32::try_from(period.accounts.len()).map_err(|_| JournalError::Range)?;
    let mut locations = BTreeSet::new();
    for account in &period.accounts {
        if account.county_internal_point.is_some() {
            locations.insert(
                account
                    .location
                    .as_deref()
                    .ok_or(JournalError::Projection)?,
            );
        }
    }
    let locations: Vec<_> = locations.into_iter().collect();
    let extent = tx
        .query_one(
            "SELECT (SELECT max(account_key) FROM babylon_state.economic_flow_account_v1 WHERE campaign_id=$1),
                    ARRAY(SELECT location_key FROM babylon_state.economic_flow_location_v1 WHERE campaign_id=$1
                          EXCEPT SELECT unnest($2::text[]))",
            &[campaign, &locations],
        )
        .map_err(|_| JournalError::Database)?;
    let last_key: Option<i32> = extent.try_get(0).map_err(|_| JournalError::Projection)?;
    let extra_points: Vec<String> = extent.try_get(1).map_err(|_| JournalError::Projection)?;
    let extra_accounts = last_key.is_some_and(|key| key >= count);
    if mode != Admission::Rebuild && (extra_accounts || !extra_points.is_empty()) {
        return Err(JournalError::Projection);
    }
    if extra_accounts {
        tx.execute(
            "DELETE FROM babylon_state.economic_flow_account_v1 WHERE campaign_id=$1 AND account_key >= $2",
            &[campaign, &count],
        )
        .map_err(|_| JournalError::Database)?;
    }
    if !extra_points.is_empty() {
        tx.execute(
            "DELETE FROM babylon_state.economic_flow_location_v1 WHERE campaign_id=$1 AND location_key=ANY($2)",
            &[campaign, &extra_points],
        )
        .map_err(|_| JournalError::Database)?;
    }
    Ok(last_key.is_some())
}

pub(super) fn accounts(
    tx: &mut Transaction<'_>,
    period: &EconomicPaymentPeriod,
    mode: Admission,
) -> Result<(), JournalError> {
    let campaign = period.source.campaign_id;
    let occupied = admit_directory_extent(tx, period, mode)?;
    if period.accounts.is_empty() {
        return Ok(());
    }
    let digest = period.source.identity.foundation_digest();
    let upsert = accounts_upsert(mode)
        .map(|sql| tx.prepare(&sql))
        .transpose()
        .map_err(|_| JournalError::Database)?;
    let verify = tx
        .prepare(&format!("{ACCOUNT_SOURCE} {VERIFY_ACCOUNTS}"))
        .map_err(|_| JournalError::Database)?;
    let mut account_index = 0;
    for chunk in period.accounts.chunks(1024) {
        let accounts: Vec<_> = chunk
            .iter()
            .enumerate()
            .map(|(i, row)| AccountRow::from_source(account_index + i, row))
            .collect::<Result<_, _>>()?;
        account_index += chunk.len();
        let data = serde_json::to_string(&accounts).map_err(|_| JournalError::Projection)?;
        let params: &[&(dyn ToSql + Sync)] = &[campaign.as_uuid(), &digest.as_slice(), &data];
        let matches = |tx: &mut Transaction<'_>| {
            tx.query_one(&verify, params)
                .map_err(|_| JournalError::Database)?
                .try_get::<_, bool>(0)
                .map_err(|_| JournalError::Projection)
        };
        if let Some(statement) = &upsert {
            // Later periods usually share every opening account and county point.
            // A missing or different value must follow the original write and recheck.
            if mode == Admission::Insert && occupied && matches(tx)? {
                continue;
            }
            tx.execute(statement, params)
                .map_err(|_| JournalError::Database)?;
        }
        if !matches(tx)? {
            return Err(JournalError::Projection);
        }
    }
    Ok(())
}

fn settled(purpose: MoneyPurpose) -> bool {
    !matches!(
        purpose,
        MoneyPurpose::PurchaseReservation
            | MoneyPurpose::PurchaseRefund
            | MoneyPurpose::ShiftReservation
            | MoneyPurpose::ShiftCancellation
    )
}

/// The custody movement digest already binds the amount, purpose and credited endpoint.
pub(super) fn fingerprint(
    settlements: &[Settlement],
    moves: &[MoneyMovement],
) -> Result<[u8; 32], JournalError> {
    let mut valid = moves.iter().filter(|m| settled(m.purpose));
    let mut hash = Sha256::new();
    hash.update(b"babylon.economic-payments.v1\0");
    for row in settlements {
        let movement = valid.next().ok_or(JournalError::Projection)?;
        if row.ordinal != movement.ordinal
            || row.recipient != movement.credit
            || (movement.reference.is_none() && row.payer != movement.debit)
        {
            return Err(JournalError::Projection);
        }
        hash.update(row.ordinal.to_be_bytes());
        hash.update(row.payer.kind.as_str().as_bytes());
        hash.update([0]);
        hash.update(row.payer.id);
    }
    if valid.next().is_some() {
        return Err(JournalError::Projection);
    }
    Ok(hash.finalize().into())
}
