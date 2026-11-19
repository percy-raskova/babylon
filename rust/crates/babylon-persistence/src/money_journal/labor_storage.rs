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
use std::collections::BTreeSet;

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

// Allocate each captured product/unit pair once under the journal's campaign lock.
fn prepare_products(
    tx: &mut Transaction<'_>,
    facts: &LaborFacts,
    campaign: &str,
) -> Result<(), JournalError> {
    let products: BTreeSet<_> = facts
        .nodes
        .iter()
        .filter_map(|node| node.unit_id.map(|unit| (node.good_id, unit)))
        .collect();
    if products.is_empty() {
        return Ok(());
    }
    let source = serde_json::to_string(&products).map_err(|_| JournalError::Projection)?;
    tx.execute(
        "WITH expected AS (SELECT decode(pair->>0,'hex') AS good_id,decode(pair->>1,'hex') AS unit_id
              FROM jsonb_array_elements($2::text::jsonb) AS pair),
         missing AS (SELECT e.* FROM expected e WHERE NOT EXISTS (
              SELECT FROM babylon_state.labor_product_v1 g WHERE g.campaign_id=$1::text::uuid
                AND g.good_id IS NOT DISTINCT FROM e.good_id AND g.unit_id=e.unit_id)),
         last_key AS (SELECT coalesce(max(product_key),0) AS key FROM babylon_state.labor_product_v1 WHERE campaign_id=$1::text::uuid)
         INSERT INTO babylon_state.labor_product_v1(campaign_id,product_key,good_id,unit_id)
         SELECT $1::text::uuid,(key+row_number() OVER (ORDER BY good_id NULLS FIRST,unit_id))::integer,good_id,unit_id
         FROM missing CROSS JOIN last_key",
        &[&campaign, &source],
    )
    .map_err(|_| JournalError::Database)?;
    Ok(())
}

fn stage(
    tx: &mut Transaction<'_>,
    facts: &LaborFacts,
    campaign: &str,
    tick: i64,
    admission: Admission,
) -> Result<(), JournalError> {
    prepare_products(tx, facts, campaign)?;
    let mut batch = Batch { tx, admission };
    batch.stage(
        Table::LaborNode,
        labor_positions::attach(&facts.nodes, &facts.positions)?
            .iter()
            .map(|fact| Scoped {
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
    )
}

/// A plan prepared against an empty dictionary can scan the whole campaign for
/// each new digest. Give the first full source batch real column statistics.
pub(super) fn prepare_descriptor_lookup(tx: &mut Transaction<'_>) -> Result<(), JournalError> {
    let missing: bool = tx
        .query_one(
            "SELECT NOT EXISTS (SELECT FROM pg_catalog.pg_stats
             WHERE schemaname='babylon_state' AND tablename='labor_node_identity_v1'
             AND attname='descriptor_sha256' AND NOT inherited)
             OR (SELECT reltuples<=0 FROM pg_catalog.pg_class
                 WHERE oid='babylon_state.labor_node_identity_v1'::regclass)",
            &[],
        )
        .and_then(|row| row.try_get(0))
        .map_err(|_| JournalError::Database)?;
    if missing {
        tx.batch_execute(
            "ANALYZE babylon_state.labor_node_identity_v1;
             ANALYZE babylon_state.labor_product_v1",
        )
        .map_err(|_| JournalError::Database)?;
    }
    Ok(())
}

/// Verify the planner has statistics for new or restored block and descriptor rows.
fn prepare_node_checks(tx: &mut Transaction<'_>, nodes: i64) -> Result<(), JournalError> {
    if nodes == 0 {
        return Ok(());
    }
    let needs_statistics: bool = tx
        .query_one(
            "WITH parents(rel,minimum,cols) AS (VALUES
              ('babylon_state.labor_node_block_v1'::regclass,1+($1::bigint-1)/256,ARRAY['campaign_id','resolve_tick','block_ordinal']),
              ('babylon_state.labor_node_identity_v1'::regclass,$1::bigint,ARRAY['campaign_id','descriptor_key','descriptor_sha256']))
             SELECT EXISTS (SELECT FROM parents p JOIN pg_catalog.pg_class c ON c.oid=p.rel
               WHERE c.reltuples < p.minimum OR EXISTS (SELECT FROM unnest(p.cols) k(name)
                 WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_stats s
                   WHERE s.schemaname='babylon_state' AND s.tablename=c.relname
                     AND s.attname=k.name::name AND NOT s.inherited)))",
            &[&nodes],
        )
        .and_then(|row| row.try_get(0))
        .map_err(|_| JournalError::Database)?;
    if needs_statistics {
        tx.batch_execute(
            "ANALYZE babylon_state.labor_node_block_v1 (campaign_id,resolve_tick,block_ordinal,descriptor_keys);
             ANALYZE babylon_state.labor_node_identity_v1 (campaign_id,descriptor_key,descriptor_sha256)",
        )
        .map_err(|_| JournalError::Database)?;
    }
    Ok(())
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
        let counts = tx
            .query_one(
                "SELECT count(*), (SELECT count(*) FROM babylon_state.labor_movement_v1
                     WHERE campaign_id=$1 AND resolve_tick=$2),
                    count(opening_quantity) + count(closing_quantity)
             FROM babylon_state.labor_node_v1 WHERE campaign_id=$1 AND resolve_tick=$2",
                &[campaign, &tick],
            )
            .map_err(|_| JournalError::Database)?;
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
            prepare_node_checks(tx, nodes)?;
        }
    }
    Ok(())
}
