//! Foundation-bound account attributes and economic principals of settled custody postings.
use super::{JournalError, MoneyMovement, MoneyPurpose};
use crate::economic_flows::{EconomicPaymentPeriod, FlowAccount, Settlement};
use crate::identity::CampaignId;
use crate::qualification_audit::trade;
use babylon_kernel::economic_identity::EconomicFunction;
use postgres::types::ToSql;
use postgres::Transaction;
use serde::Serialize;
use sha2::{Digest, Sha256};

#[derive(Clone, Copy, PartialEq, Eq)]
pub(super) enum Admission {
    Insert,
    Rebuild,
    Verify,
}

#[derive(Serialize)]
struct AccountRow<'a> {
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
    fn from_source(row: &'a FlowAccount) -> Result<Self, JournalError> {
        let industry = row.industry.as_deref();
        let label = industry
            .map(|key| EconomicFunction::from_source_key(key).ok_or(JournalError::Projection))
            .transpose()?
            .map(EconomicFunction::label);
        let point = row.county_internal_point.as_ref();
        Ok(Self {
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
            kind text, id text, location text, catchment text,
            industry text, label text, lon numeric, lat numeric
        )
    ),
    a AS (
        SELECT kind, decode(id, 'hex') AS id, location, catchment, industry, label FROM raw
    ),
    g AS (
        SELECT DISTINCT location, lon, lat FROM raw WHERE lon IS NOT NULL
    )";

// A missing primary key yields NULL. IS NOT TRUE rejects absence along with
// mismatched foundation, nullable account attributes, or county coordinates.
const VERIFY_ACCOUNTS: &str = "
    SELECT NOT EXISTS (
        SELECT FROM a WHERE (
            SELECT d.foundation_sha256 = $2
                AND (d.location_key, d.catchment_key, d.industry_key, d.industry_label)
                    IS NOT DISTINCT FROM (a.location, a.catchment, a.industry, a.label)
            FROM babylon_state.economic_flow_account_v1 d
            WHERE d.campaign_id = $1 AND d.account_kind = a.kind AND d.account_id = a.id
        ) IS NOT TRUE
    ) AND NOT EXISTS (
        SELECT FROM g WHERE (
            SELECT l.foundation_sha256 = $2
                AND (l.longitude, l.latitude) IS NOT DISTINCT FROM (g.lon, g.lat)
            FROM babylon_state.economic_flow_location_v1 l
            WHERE l.campaign_id = $1 AND l.location_key = g.location
        ) IS NOT TRUE
    )";

fn accounts_upsert(mode: Admission) -> Option<String> {
    let (point_conflict, account_conflict) = match mode {
        Admission::Verify => return None,
        Admission::Insert => ("DO NOTHING", "DO NOTHING"),
        Admission::Rebuild => (
            "DO UPDATE SET longitude = EXCLUDED.longitude, latitude = EXCLUDED.latitude
             WHERE (l.longitude, l.latitude) IS DISTINCT FROM (EXCLUDED.longitude, EXCLUDED.latitude)",
            "DO UPDATE SET location_key = EXCLUDED.location_key, catchment_key = EXCLUDED.catchment_key,
                 industry_key = EXCLUDED.industry_key, industry_label = EXCLUDED.industry_label
             WHERE (d.location_key, d.catchment_key, d.industry_key, d.industry_label)
                 IS DISTINCT FROM (EXCLUDED.location_key, EXCLUDED.catchment_key,
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
             (campaign_id, foundation_sha256, account_kind, account_id,
              location_key, catchment_key, industry_key, industry_label)
         SELECT $1, $2, kind, id, location, catchment, industry, label FROM a
         ON CONFLICT (campaign_id, account_kind, account_id) {account_conflict}"
    ))
}

pub(super) fn accounts(
    tx: &mut Transaction<'_>,
    period: &EconomicPaymentPeriod,
    mode: Admission,
) -> Result<(), JournalError> {
    if period.accounts.is_empty() {
        return Ok(());
    }
    let campaign = period.source.campaign_id;
    let digest = period.source.identity.foundation_digest();
    let upsert = accounts_upsert(mode)
        .map(|sql| tx.prepare(&sql))
        .transpose()
        .map_err(|_| JournalError::Database)?;
    let verify = tx
        .prepare(&format!("{ACCOUNT_SOURCE} {VERIFY_ACCOUNTS}"))
        .map_err(|_| JournalError::Database)?;
    for chunk in period.accounts.chunks(1024) {
        let accounts: Vec<_> = chunk
            .iter()
            .map(AccountRow::from_source)
            .collect::<Result<_, _>>()?;
        let data = serde_json::to_string(&accounts).map_err(|_| JournalError::Projection)?;
        let params: &[&(dyn ToSql + Sync)] = &[campaign.as_uuid(), &digest.as_slice(), &data];
        if let Some(statement) = &upsert {
            tx.execute(statement, params)
                .map_err(|_| JournalError::Database)?;
        }
        let valid: bool = tx
            .query_one(&verify, params)
            .map_err(|_| JournalError::Database)?
            .try_get(0)
            .map_err(|_| JournalError::Projection)?;
        if !valid {
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
        if row.ordinal != movement.ordinal || row.recipient != movement.credit {
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

pub(super) fn payments(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    tick: i64,
    settlements: &[Settlement],
    mode: Admission,
) -> Result<(), JournalError> {
    if mode == Admission::Verify {
        let count: i64 = tx.query_one("SELECT count(*) FROM babylon_state.economic_payment_v1 WHERE campaign_id=$1 AND resolve_tick=$2",
          &[campaign.as_uuid(), &tick]).map_err(|_|JournalError::Database)?.try_get(0).map_err(|_|JournalError::Projection)?;
        if usize::try_from(count).ok() != Some(settlements.len()) {
            return Err(JournalError::Projection);
        }
    }
    for chunk in settlements.chunks(1024) {
        let mut ordinals = Vec::with_capacity(chunk.len());
        let mut kinds = Vec::with_capacity(chunk.len());
        let mut ids = Vec::with_capacity(chunk.len());
        for row in chunk {
            ordinals.push(i64::try_from(row.ordinal).map_err(|_| JournalError::Range)?);
            kinds.push(row.payer.kind.as_str());
            ids.push(row.payer.id.as_slice());
        }
        let params: &[&(dyn ToSql + Sync)] = &[campaign.as_uuid(), &tick, &ordinals, &kinds, &ids];
        if mode == Admission::Verify {
            let equal: bool = tx
                .query_one(
                    "SELECT NOT EXISTS (SELECT * FROM unnest($3::bigint[],$4::text[],$5::bytea[]) \
              EXCEPT SELECT ordinal,payer_kind,payer_id FROM babylon_state.economic_payment_v1 \
              WHERE campaign_id=$1 AND resolve_tick=$2 AND ordinal=ANY($3))",
                    params,
                )
                .map_err(|_| JournalError::Database)?
                .try_get(0)
                .map_err(|_| JournalError::Projection)?;
            if !equal {
                return Err(JournalError::Projection);
            }
        } else {
            tx.execute("INSERT INTO babylon_state.economic_payment_v1 SELECT $1,$2,r.* FROM unnest($3::bigint[],$4::text[],$5::bytea[]) AS r",
              params).map_err(|_|JournalError::Database)?;
        }
    }
    Ok(())
}
