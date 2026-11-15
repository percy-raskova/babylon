//! Bind compact site keys to the campaign's immutable physical opening roster.
use super::payment_storage::Admission;
use super::statement_storage::JournalPeriodSource;
use super::JournalError;
use babylon_material_circuit::SiteId;
use postgres::types::ToSql;
use postgres::Transaction;
use std::collections::BTreeMap;
use uuid::Uuid;

const VERIFY: &str = "
    SELECT count(*),
           count(*)=cardinality($3::bytea[])
           AND coalesce(min(site_key),0)=0
           AND coalesce(max(site_key),-1)=cardinality($3)-1
           AND coalesce(bool_and(foundation_sha256=$2), true)
           AND coalesce(array_agg(site_id ORDER BY site_key), ARRAY[]::bytea[])=$3
    FROM babylon_state.site_principal_v1 WHERE campaign_id=$1";

const WRITE: &str = "
    INSERT INTO babylon_state.site_principal_v1 AS known (campaign_id,site_key,foundation_sha256,site_id)
    SELECT $1,(r.n-1)::integer,$2,r.site_id FROM unnest($3::bytea[]) WITH ORDINALITY AS r(site_id,n)
    ON CONFLICT (campaign_id,site_key) DO UPDATE SET
        site_id=EXCLUDED.site_id, foundation_sha256=EXCLUDED.foundation_sha256
    WHERE (known.site_id,known.foundation_sha256) IS DISTINCT FROM (EXCLUDED.site_id,EXCLUDED.foundation_sha256)";

fn admit_roster(
    tx: &mut Transaction<'_>,
    campaign: &Uuid,
    mode: Admission,
) -> Result<(), JournalError> {
    let row = tx.query_one(
        "WITH source AS MATERIALIZED (SELECT * FROM babylon_state.site_roster_source_v1 WHERE campaign_id=$1),
              stored AS MATERIALIZED (SELECT * FROM babylon_state.site_roster_block_v1 WHERE campaign_id=$1)
         SELECT EXISTS(TABLE stored), NOT EXISTS(SELECT FROM ((TABLE stored EXCEPT TABLE source)
             UNION ALL (TABLE source EXCEPT TABLE stored)) AS difference)", &[campaign])
        .map_err(|_| JournalError::Database)?;
    let valid: bool = row.try_get(1).map_err(|_| JournalError::Projection)?;
    if valid {
        return Ok(());
    }
    let exists: bool = row.try_get(0).map_err(|_| JournalError::Projection)?;
    if mode == Admission::Verify || (exists && mode == Admission::Insert) {
        return Err(JournalError::Projection);
    }
    if mode == Admission::Rebuild {
        tx.execute(
            "DELETE FROM babylon_state.site_roster_block_v1 b WHERE b.campaign_id=$1
             AND NOT EXISTS(SELECT FROM babylon_state.site_principal_v1 k
                 WHERE k.campaign_id=b.campaign_id AND k.site_key/32=b.block_key)",
            &[campaign],
        )
        .map_err(|_| JournalError::Database)?;
    }
    tx.execute("INSERT INTO babylon_state.site_roster_block_v1 AS b
         SELECT * FROM babylon_state.site_roster_source_v1 WHERE campaign_id=$1 ORDER BY block_key
         ON CONFLICT(campaign_id,block_key) DO UPDATE SET members=excluded.members,sha256=excluded.sha256
           WHERE (b.members,b.sha256) IS DISTINCT FROM (excluded.members,excluded.sha256)", &[campaign])
        .map_err(|_| JournalError::Database)?;
    Ok(())
}

pub(super) fn admit(
    tx: &mut Transaction<'_>,
    source: &JournalPeriodSource,
    mode: Admission,
) -> Result<BTreeMap<SiteId, i32>, JournalError> {
    // A period's directory ordinal indexes its evidence. The site key indexes
    // this foundation roster independently, including when a period selects a subset.
    let mut sites: Vec<_> = source
        .foundation
        .view()
        .opening
        .sites
        .iter()
        .map(|s| s.site_id)
        .collect();
    sites.sort_unstable();
    if sites.len() > 16_777_215 || sites.windows(2).any(|pair| pair[0] == pair[1]) {
        return Err(JournalError::Projection);
    }
    let raw: Vec<_> = sites.iter().map(|s| s.as_bytes().to_vec()).collect();
    let campaign = source.payments.source.campaign_id.as_uuid();
    let foundation = source.payments.source.identity.foundation_digest();
    let params: &[&(dyn ToSql + Sync)] = &[campaign, &foundation.as_slice(), &raw];
    let check = tx
        .query_one(VERIFY, params)
        .map_err(|_| JournalError::Database)?;
    let valid: bool = check.try_get(1).map_err(|_| JournalError::Projection)?;
    if !valid {
        let count: i64 = check.try_get(0).map_err(|_| JournalError::Projection)?;
        if mode == Admission::Verify || (mode == Admission::Insert && count != 0) {
            return Err(JournalError::Projection);
        }
        let length = i32::try_from(raw.len()).map_err(|_| JournalError::Range)?;
        if mode == Admission::Rebuild {
            tx.execute(
                "DELETE FROM babylon_state.site_principal_v1 WHERE campaign_id=$1 AND site_key>=$2",
                &[campaign, &length],
            )
            .map_err(|_| JournalError::Database)?;
        }
        tx.execute(WRITE, params)
            .map_err(|_| JournalError::Database)?;
    }
    admit_roster(tx, campaign, mode)?;
    sites
        .into_iter()
        .enumerate()
        .map(|(n, id)| Ok((id, i32::try_from(n).map_err(|_| JournalError::Range)?)))
        .collect()
}
