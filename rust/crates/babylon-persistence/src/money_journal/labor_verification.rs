//! Compare retained labor with its authenticated source in bounded, ordered batches.
use super::labor_facts::LaborFacts;
use super::statement_storage::Table;
use super::JournalError;
use postgres::Transaction;
use serde::Serialize;
use uuid::Uuid;

const BATCH: u16 = 256;

pub(super) fn period(
    tx: &mut Transaction<'_>,
    campaign: &Uuid,
    tick: i64,
    facts: &LaborFacts,
) -> Result<(), JournalError> {
    let scope = Scope { campaign, tick };
    scope.verify(tx, Table::LaborNode, "node_ordinal", &facts.nodes)?;
    scope.verify(tx, Table::LaborMovement, "ordinal", &facts.movements)?;
    // The source ledger emits opening, then closing, in ascending native node order.
    scope.verify(
        tx,
        Table::LaborPosition,
        "(side = 'opening') DESC, node_ordinal",
        &facts.positions,
    )
}

struct Scope<'a> {
    campaign: &'a Uuid,
    tick: i64,
}
impl Scope<'_> {
    fn verify<T: Serialize>(
        &self,
        tx: &mut Transaction<'_>,
        table: Table,
        order: &str,
        facts: &[T],
    ) -> Result<(), JournalError> {
        let (table, _) = table.relation();
        // This cursor reads the campaign period once, even when the planner
        // selects a secondary index. Each fetch continues the same execution.
        let scan = format!(
            "SELECT d::text FROM {table} d
             WHERE campaign_id = $1 AND resolve_tick = $2 ORDER BY {order}"
        );
        let stored = tx
            .bind(&scan, &[self.campaign, &self.tick])
            .map_err(|_| JournalError::Database)?;
        // PostgreSQL casts both inputs to the same composite. All fields, NULLs,
        // and exact numeric values take part regardless of display formatting.
        let compare = format!(
            "SELECT NOT EXISTS (
                 SELECT e FROM jsonb_populate_recordset(
                     jsonb_populate_record(NULL::{table},
                         jsonb_build_object('campaign_id', $3::uuid, 'resolve_tick', $4::bigint)),
                     $1::text::jsonb) e
                 EXCEPT ALL
                 SELECT r.value::{table} FROM unnest($2::text[]) AS r(value)
             )"
        );
        let compare = tx.prepare(&compare).map_err(|_| JournalError::Database)?;
        for chunk in facts.chunks(usize::from(BATCH)) {
            let rows = tx
                .query_portal(&stored, i32::from(BATCH))
                .map_err(|_| JournalError::Database)?;
            if rows.len() != chunk.len() {
                return Err(JournalError::Projection);
            }
            let actual = rows
                .iter()
                .map(|row| row.try_get::<_, &str>(0))
                .collect::<Result<Vec<_>, _>>()
                .map_err(|_| JournalError::Projection)?;
            let expected = serde_json::to_string(chunk).map_err(|_| JournalError::Projection)?;
            let matches: bool = tx
                .query_one(&compare, &[&expected, &actual, self.campaign, &self.tick])
                .map_err(|_| JournalError::Database)?
                .try_get(0)
                .map_err(|_| JournalError::Projection)?;
            if !matches {
                return Err(JournalError::Projection);
            }
        }
        if facts.len().is_multiple_of(usize::from(BATCH))
            && !tx
                .query_portal(&stored, 1)
                .map_err(|_| JournalError::Database)?
                .is_empty()
        {
            return Err(JournalError::Projection);
        }
        Ok(())
    }
}
