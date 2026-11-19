//! The deferred journal marker commits the company coverage, three statements and source entries together.
use super::{rows, CompanyPublication};
use crate::money_journal::payment_storage::Admission;
use crate::money_journal::statement_storage::Batch;
use crate::money_journal::JournalError;
use crate::observer_reader::CommittedMaterialReceipts;
use postgres::types::ToSql;
use postgres::Transaction;

const FIND_PERIOD: &str = "
    SELECT 1 FROM babylon_state.company_accounting_period_v1
    WHERE campaign_id = $1 AND resolve_tick = $2";

const VERIFY_PERIOD: &str = "
    SELECT fact_sha256 = $3 AND checkpoint_sha256 = $4 AND result_world_hash = $5
            AND company_count = $6 AND entry_count = $7
        AND (SELECT count(*) FROM babylon_state.company_statement_balance_v1
             WHERE campaign_id = $1 AND resolve_tick = $2) = 6 * $6
        AND (SELECT count(*) FROM babylon_state.company_statement_income_v1
             WHERE campaign_id = $1 AND resolve_tick = $2) = 3 * $6
        AND (SELECT count(*) FROM babylon_state.company_statement_cash_flow_v1
             WHERE campaign_id = $1 AND resolve_tick = $2) = 3 * $6
        AND (SELECT count(*) FROM babylon_state.company_elimination_v1
             WHERE campaign_id = $1 AND resolve_tick = $2) = $6
        AND (SELECT count(*) FROM babylon_state.company_realization_entry_v1
             WHERE campaign_id = $1 AND resolve_tick = $2) = $7
    FROM babylon_state.company_accounting_period_v1
    WHERE campaign_id = $1 AND resolve_tick = $2";

const INSERT_PERIOD: &str = "
    INSERT INTO babylon_state.company_accounting_period_v1
        (campaign_id, resolve_tick, fact_sha256, checkpoint_sha256, result_world_hash,
         company_count, entry_count)
    VALUES ($1, $2, $3, $4, $5, $6, $7)";

const VERIFY_CHECKPOINT: &str = "
    SELECT checkpoint_bytes = $3 FROM babylon_state.company_accounting_checkpoint_v1
    WHERE campaign_id = $1 AND resolve_tick = $2";

const INSERT_CHECKPOINT: &str = "
    INSERT INTO babylon_state.company_accounting_checkpoint_v1
        (campaign_id, resolve_tick, checkpoint_bytes)
    VALUES ($1, $2, $3)";

pub(in crate::money_journal) fn publish(
    tx: &mut Transaction<'_>,
    source: &CommittedMaterialReceipts,
    data: Option<&CompanyPublication>,
    mode: Admission,
    retained: bool,
) -> Result<(), JournalError> {
    let campaign = source.campaign_id.as_uuid();
    let tick = i64::try_from(source.identity.resolve_tick()).map_err(|_| JournalError::Range)?;
    let Some(publication) = data else {
        if mode == Admission::Verify
            && tx
                .query_opt(FIND_PERIOD, &[campaign, &tick])
                .map_err(|_| JournalError::Database)?
                .is_some()
        {
            return Err(JournalError::Projection);
        }
        return Ok(());
    };
    let facts = rows::fingerprint(source.campaign_id, &source.identity, &publication.companies)?;
    let company_count =
        i64::try_from(publication.companies.len()).map_err(|_| JournalError::Range)?;
    let entry_count = publication
        .companies
        .iter()
        .try_fold(0_i64, |total, company| {
            total.checked_add(i64::try_from(company.entries.len()).ok()?)
        })
        .ok_or(JournalError::Range)?;
    let world = source.identity.result_world_hash();
    let period_fields: &[&(dyn ToSql + Sync)] = &[
        campaign,
        &tick,
        &facts.as_slice(),
        &publication.checkpoint_sha256.as_slice(),
        &world.as_slice(),
        &company_count,
        &entry_count,
    ];
    let checkpoint_fields: &[&(dyn ToSql + Sync)] = &[campaign, &tick, &publication.checkpoint];

    if mode == Admission::Verify {
        let marker = tx
            .query_opt(VERIFY_PERIOD, period_fields)
            .map_err(|_| JournalError::Database)?
            .ok_or(JournalError::Projection)?;
        if !marker
            .try_get::<_, bool>(0)
            .map_err(|_| JournalError::Projection)?
        {
            return Err(JournalError::Projection);
        }
        let matches = tx
            .query_opt(VERIFY_CHECKPOINT, checkpoint_fields)
            .map_err(|_| JournalError::Database)?
            .map(|row| row.try_get::<_, bool>(0))
            .transpose()
            .map_err(|_| JournalError::Projection)?;
        let expects_checkpoint = retained || tick % 13 == 0;
        if matches != expects_checkpoint.then_some(true) {
            return Err(JournalError::Projection);
        }
    } else {
        tx.execute(INSERT_PERIOD, period_fields)
            .map_err(|_| JournalError::Database)?;
        tx.execute(INSERT_CHECKPOINT, checkpoint_fields)
            .map_err(|_| JournalError::Database)?;
    }
    rows::store(
        &mut Batch {
            tx,
            admission: mode,
        },
        &campaign.to_string(),
        tick,
        &publication.companies,
    )
}
