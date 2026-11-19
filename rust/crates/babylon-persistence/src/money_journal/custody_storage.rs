//! Store each authenticated movement once using the opening cash book's canonical account order.
use super::{
    JournalError, MoneyEndpoint, MoneyLocationKind, MoneyMovement, MoneyReference,
    MoneyReferenceKind,
};
use crate::economic_flows::{EconomicPaymentPeriod, FlowAccount};
use postgres::Transaction;
use std::collections::BTreeMap;

type AccountKeys = BTreeMap<(&'static str, [u8; 32]), i32>;

fn account_keys(accounts: &[FlowAccount]) -> Result<AccountKeys, JournalError> {
    accounts
        .iter()
        .enumerate()
        .map(|(index, row)| {
            Ok((
                (row.account.kind.as_str(), row.account.id),
                i32::try_from(index).map_err(|_| JournalError::Range)?,
            ))
        })
        .collect()
}

fn cash(keys: &AccountKeys, endpoint: &MoneyEndpoint) -> Result<i32, JournalError> {
    keys.get(&(endpoint.kind.as_str(), endpoint.id))
        .copied()
        .ok_or(JournalError::Projection)
}

// Only the referent's own reserve can be reconstructed from its order/shift ID.
// A cash ID with identical bytes lives in a separate namespace.
fn posting(
    keys: &AccountKeys,
    endpoint: &MoneyEndpoint,
    reference: Option<&MoneyReference>,
) -> Result<Option<i32>, JournalError> {
    let kind = match endpoint.kind {
        MoneyLocationKind::DeliveryReserve => MoneyReferenceKind::Delivery,
        MoneyLocationKind::LocalFinalDemandReserve => MoneyReferenceKind::LocalFinalDemand,
        MoneyLocationKind::ServiceReserve => MoneyReferenceKind::Service,
        MoneyLocationKind::PayrollReserve => MoneyReferenceKind::Shift,
        MoneyLocationKind::SiteCash
        | MoneyLocationKind::HouseholdCash
        | MoneyLocationKind::PublicCash
        | MoneyLocationKind::CompanyCash
        | MoneyLocationKind::OrganizationCash => return cash(keys, endpoint).map(Some),
    };
    if reference.is_some_and(|r| r.kind == kind && r.id == endpoint.id) {
        Ok(None)
    } else {
        Err(JournalError::Projection)
    }
}

const INSERT: &str = include_str!("custody_insert.sql");

pub(super) fn insert(
    tx: &mut Transaction<'_>,
    economic: &EconomicPaymentPeriod,
    tick: i64,
    movements: &[MoneyMovement],
) -> Result<(), JournalError> {
    let keys = account_keys(&economic.accounts)?;
    let mut settlements = economic.settlements.iter().peekable();
    let insert = tx.prepare(INSERT).map_err(|_| JournalError::Database)?;
    for chunk in movements.chunks(1024) {
        let mut ordinals = Vec::with_capacity(chunk.len());
        let mut purposes = Vec::with_capacity(chunk.len());
        let mut references = Vec::with_capacity(chunk.len());
        let mut ids = Vec::with_capacity(chunk.len());
        let mut payers = Vec::with_capacity(chunk.len());
        let mut recipients = Vec::with_capacity(chunk.len());
        let mut amounts = Vec::with_capacity(chunk.len());
        for movement in chunk {
            let reference = movement.reference.as_ref();
            let debit = posting(&keys, &movement.debit, reference)?;
            let credit = posting(&keys, &movement.credit, reference)?;
            let payer = match settlements.next_if(|s| s.ordinal == movement.ordinal) {
                Some(s) => Some(cash(&keys, &s.payer)?),
                None => debit,
            };
            ordinals.push(i64::try_from(movement.ordinal).map_err(|_| JournalError::Range)?);
            purposes.push(movement.purpose.as_str());
            references.push(reference.map(|r| r.kind.as_str()));
            ids.push(reference.map(|r| r.id.as_slice()));
            payers.push(payer);
            recipients.push(credit);
            amounts.push(movement.amount_micros.as_str());
        }
        tx.execute(
            &insert,
            &[
                economic.source.campaign_id.as_uuid(),
                &tick,
                &ordinals,
                &purposes,
                &references,
                &ids,
                &payers,
                &recipients,
                &amounts,
            ],
        )
        .map_err(|_| JournalError::Database)?;
    }
    if settlements.next().is_some() {
        return Err(JournalError::Projection);
    }
    if !movements.is_empty() {
        analyze_missing_statistics(tx)?;
    }
    Ok(())
}

/// A new directory and its first populated custody period can become visible before
/// autovacuum has sampled either relation. Restored databases can also lack planner
/// statistics. A sample taken after retention emptied a relation can preserve every
/// column statistic while reporting zero live rows. After a nonempty write, refresh
/// either unusable estimate before the newly covered cash facts become visible.
fn analyze_missing_statistics(tx: &mut Transaction<'_>) -> Result<(), JournalError> {
    let missing = tx.query_one(
        "WITH required(tab, cols) AS (VALUES
             ('economic_flow_account_v1', ARRAY['campaign_id','account_key','account_kind','account_id','foundation_sha256']),
             ('money_movement_block_v1', ARRAY['campaign_id','resolve_tick','block_ordinal'])
         ), missing AS (
             SELECT r.tab FROM required r
             JOIN pg_catalog.pg_class c ON c.oid=pg_catalog.to_regclass('babylon_state.'||r.tab)
             WHERE c.reltuples<=0 OR EXISTS (
                 SELECT FROM unnest(r.cols) col(name) WHERE NOT EXISTS (
                     SELECT FROM pg_catalog.pg_stats s WHERE s.schemaname='babylon_state'
                     AND s.tablename=r.tab::name AND s.attname=col.name::name AND NOT s.inherited)))
         SELECT EXISTS (SELECT FROM missing WHERE tab='economic_flow_account_v1'),
                EXISTS (SELECT FROM missing WHERE tab='money_movement_block_v1')",
        &[],
    ).map_err(|_| JournalError::Database)?;
    for (index, analyze) in [
        "ANALYZE babylon_state.economic_flow_account_v1",
        "ANALYZE babylon_state.money_movement_block_v1",
    ]
    .into_iter()
    .enumerate()
    {
        if missing
            .try_get::<_, bool>(index)
            .map_err(|_| JournalError::Projection)?
        {
            tx.batch_execute(analyze)
                .map_err(|_| JournalError::Database)?;
        }
    }
    Ok(())
}

pub(super) fn verify_payers(
    tx: &mut Transaction<'_>,
    period: &EconomicPaymentPeriod,
    tick: i64,
) -> Result<(), JournalError> {
    // The independently checked custody tape hides the true payer behind escrow.
    // Compare its economic payer against the complete source ordinal sequence.
    let keys = account_keys(&period.accounts)?;
    let stored = tx.query(
        "SELECT ordinal,payer_key FROM babylon_state.money_movement_v1
         WHERE campaign_id=$1 AND resolve_tick=$2 AND payer_key IS NOT NULL AND recipient_key IS NOT NULL
         ORDER BY ordinal",
        &[period.source.campaign_id.as_uuid(), &tick],
    ).map_err(|_|JournalError::Database)?;
    if stored.len() != period.settlements.len() {
        return Err(JournalError::Projection);
    }
    for (row, source) in stored.iter().zip(&period.settlements) {
        let ordinal: i64 = row.try_get(0).map_err(|_| JournalError::Projection)?;
        let payer: i32 = row.try_get(1).map_err(|_| JournalError::Projection)?;
        if u64::try_from(ordinal).ok() != Some(source.ordinal)
            || payer != cash(&keys, &source.payer)?
        {
            return Err(JournalError::Projection);
        }
    }
    Ok(())
}
