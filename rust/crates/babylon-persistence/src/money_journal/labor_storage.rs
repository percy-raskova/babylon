//! Atomically stage compact labor facts and coverage under the journal's shared publish marker.
use super::labor_facts::LaborFacts;
use super::labor_positions;
use super::labor_source::LaborPublication;
use super::labor_verification;
use super::payment_storage::Admission;
use super::statement_storage::{Batch, Table};
use super::JournalError;
use crate::observer_reader::CommittedMaterialReceipts;
use postgres::types::ToSql;
use postgres::Transaction;
use serde::Serialize;
use sha2::Sha256;

#[derive(Serialize)]
struct Scoped<'a, T> {
    campaign_id: &'a str,
    resolve_tick: i64,
    #[serde(flatten)]
    fact: &'a T,
}

fn hash_rows<T: Serialize>(hash: &mut Sha256, rows: &[T]) -> Result<(), JournalError> {
    use sha2::Digest;
    hash.update(
        u64::try_from(rows.len())
            .map_err(|_| JournalError::Range)?
            .to_be_bytes(),
    );
    for row in rows {
        let bytes = serde_json::to_vec(row).map_err(|_| JournalError::Projection)?;
        hash.update(
            u64::try_from(bytes.len())
                .map_err(|_| JournalError::Range)?
                .to_be_bytes(),
        );
        hash.update(bytes);
    }
    Ok(())
}
impl LaborFacts {
    pub(crate) fn fingerprint(&self) -> Result<[u8; 32], JournalError> {
        use sha2::Digest;
        let mut hash = Sha256::new();
        hash.update(b"babylon.recorded-labor.sql-facts.v1\0");
        for work in [self.opening, self.closing, self.direct, self.released] {
            hash.update(work.to_be_bytes());
        }
        hash_rows(&mut hash, &self.nodes)?;
        hash_rows(&mut hash, &self.movements)?;
        hash_rows(&mut hash, &self.positions)?;
        Ok(hash.finalize().into())
    }
}

fn stage(
    tx: &mut Transaction<'_>,
    facts: &LaborFacts,
    campaign: &str,
    tick: i64,
    admission: Admission,
) -> Result<(), JournalError> {
    let mut batch = Batch { tx, admission };
    batch.stage(
        Table::LaborNode,
        facts.nodes.iter().map(|fact| Scoped {
            campaign_id: campaign,
            resolve_tick: tick,
            fact,
        }),
    )?;
    batch.stage(
        Table::LaborMovement,
        facts.movements.iter().map(|fact| Scoped {
            campaign_id: campaign,
            resolve_tick: tick,
            fact,
        }),
    )?;
    batch.stage(
        Table::LaborPosition,
        labor_positions::pairs(&facts.positions)?
            .iter()
            .map(|fact| Scoped {
                campaign_id: campaign,
                resolve_tick: tick,
                fact,
            }),
    )
}

pub(super) fn publish(
    tx: &mut Transaction<'_>,
    source: &CommittedMaterialReceipts,
    data: &LaborPublication,
    admission: Admission,
    retain_detail: bool,
) -> Result<(), JournalError> {
    let facts = &data.facts;
    let campaign = source.campaign_id.as_uuid();
    let tick = i64::try_from(source.identity.resolve_tick()).map_err(|_| JournalError::Range)?;
    let nodes = i64::try_from(facts.nodes.len()).map_err(|_| JournalError::Range)?;
    let movements = i64::try_from(facts.movements.len()).map_err(|_| JournalError::Range)?;
    let positions = i64::try_from(facts.positions.len()).map_err(|_| JournalError::Range)?;
    let fingerprint = facts.fingerprint()?;
    let components="campaign_id,resolve_tick,fact_sha256,checkpoint_sha256,result_world_hash,node_count,movement_count,position_count,opening_micro_hours,closing_micro_hours,direct_micro_hours,released_micro_hours";
    let terms="$1::uuid,$2::bigint,$3::bytea,$4::bytea,$5::bytea,$6::bigint,$7::bigint,$8::bigint,$9::text::numeric,$10::text::numeric,$11::text::numeric,$12::text::numeric";
    let world = source.identity.result_world_hash();
    let target = "babylon_state.labor_period_v1";
    let opening = facts.opening.to_string();
    let closing = facts.closing.to_string();
    let direct = facts.direct.to_string();
    let released = facts.released.to_string();
    let params: &[&(dyn ToSql + Sync)] = &[
        campaign,
        &tick,
        &fingerprint.as_slice(),
        &data.checkpoint.sha256.as_slice(),
        &world.as_slice(),
        &nodes,
        &movements,
        &positions,
        &opening,
        &closing,
        &direct,
        &released,
    ];
    if admission == Admission::Verify {
        let sql = format!("SELECT EXISTS(SELECT 1 FROM {target} WHERE ({components})=({terms}))");
        let valid: bool = tx
            .query_one(&sql, params)
            .map_err(|_| JournalError::Database)?
            .try_get(0)
            .map_err(|_| JournalError::Projection)?;
        if !valid {
            return Err(JournalError::Projection);
        }
        let counts = tx.query_one(
            "SELECT (SELECT count(*) FROM babylon_state.labor_node_v1
                     WHERE campaign_id=$1 AND resolve_tick=$2),
                    (SELECT count(*) FROM babylon_state.labor_movement_v1
                     WHERE campaign_id=$1 AND resolve_tick=$2),
                    (SELECT count(opening_quantity) + count(closing_quantity)
                     FROM babylon_state.labor_position_v1 WHERE campaign_id=$1 AND resolve_tick=$2)",
            &[campaign, &tick],
        ).map_err(|_| JournalError::Database)?;
        for (index, expected) in [nodes, movements, positions].into_iter().enumerate() {
            let actual: i64 = counts
                .try_get(index)
                .map_err(|_| JournalError::Projection)?;
            if actual != if retain_detail { expected } else { 0 } {
                return Err(JournalError::Projection);
            }
        }
        let checkpoint=tx.query_opt("SELECT sha256=$3 AND checkpoint_bytes=$4 FROM babylon_state.labor_checkpoint_v1 WHERE campaign_id=$1 AND resolve_tick=$2",&[campaign,&tick,&data.checkpoint.sha256.as_slice(),&data.checkpoint.bytes]).map_err(|_|JournalError::Database)?;
        let valid = checkpoint
            .map(|row| row.try_get::<_, bool>(0))
            .transpose()
            .map_err(|_| JournalError::Projection)?;
        if valid
            != if retain_detail || tick % 13 == 0 {
                Some(true)
            } else {
                None
            }
        {
            return Err(JournalError::Projection);
        }
    } else {
        let sql = format!("INSERT INTO {target} ({components}) VALUES({terms})");
        tx.execute(&sql, params)
            .map_err(|_| JournalError::Database)?;
        tx.execute("INSERT INTO babylon_state.labor_checkpoint_v1(campaign_id,resolve_tick,sha256,checkpoint_bytes) VALUES($1,$2,$3,$4)",&[campaign,&tick,&data.checkpoint.sha256.as_slice(),&data.checkpoint.bytes]).map_err(|_|JournalError::Database)?;
    }
    match admission {
        Admission::Verify if retain_detail => {
            labor_verification::period(tx, campaign, tick, facts)?;
        }
        Admission::Verify => {}
        Admission::Insert | Admission::Rebuild => {
            stage(tx, facts, &campaign.to_string(), tick, admission)?;
        }
    }
    Ok(())
}
