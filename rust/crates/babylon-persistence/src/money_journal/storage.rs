//! Atomic owner publication and full-observer SQL access.
use super::payment_storage::Admission;
use super::{
    model, payment_storage, statement_storage, JournalError, MoneyEndpoint, MoneyLocationKind,
    MoneyMovement, MoneyPurpose, MoneyReference, MoneyReferenceKind, MoneyTotal, PublishReport,
};
use crate::identity::CampaignId;
use crate::observer_reader::{
    CommittedMaterialReceipts, ObserverEconomyReader, ObserverMaterialCursor, ObserverVisibility,
};
use postgres::{Client, Config, GenericClient, IsolationLevel, NoTls, Row, Transaction};
use sha2::{Digest, Sha256};

const JOURNAL_LOCK_KEY: i64 = 0xbab1_4d01;

/// Separate publication authority; constructor admission alone never grants a write.
pub struct MoneyJournalWriter {
    config: Config,
}

pub(crate) const VIEWS: [&str; 8] = [
    "public.v_observer_money_journal_period_v1",
    "public.v_observer_money_movement_v1",
    "public.v_observer_money_movement_total_v1",
    "public.v_observer_economic_flow_location_v1",
    "public.v_observer_economic_flow_account_v1",
    "public.v_observer_economic_payment_v1",
    "public.v_observer_site_statement_v1",
    "public.v_observer_site_stock_balance_v1",
];
const COLUMNS: &str = "ordinal, purpose, reference_kind, reference_id, debit_kind, debit_id, credit_kind, credit_id, amount_micros::text";
const KEEP_PERIODS: i64 = 13;

/// Owner-only detail pruning shared with bounded SQL retention controls.
/// Parameters are campaign UUID and the inclusive expired-period cutoff.
/// Publication derives that cutoff from the latest committed source period minus thirteen.
/// Permanent coverage and purpose totals survive this statement.
pub const MONEY_DETAIL_RETENTION_SQL: &str = "WITH removed AS (\
    DELETE FROM babylon_state.money_movement_v1 WHERE campaign_id=$1 AND resolve_tick<=$2) \
    UPDATE babylon_state.money_journal_period_v1 SET detail_retained=false \
    WHERE campaign_id=$1 AND resolve_tick<=$2 AND detail_retained";

fn digest(rows: &[MoneyMovement]) -> [u8; 32] {
    let mut hash = Sha256::new();
    hash.update(b"babylon.money-movements.v1\0");
    for row in rows {
        hash.update(row.ordinal.to_be_bytes());
        hash.update(row.purpose.as_str().as_bytes());
        hash.update([0]);
        if let Some(reference) = &row.reference {
            hash.update(reference.kind.as_str().as_bytes());
            hash.update([0]);
            hash.update(reference.id);
        } else {
            hash.update([0]);
        }
        for endpoint in [&row.debit, &row.credit] {
            hash.update(endpoint.kind.as_str().as_bytes());
            hash.update([0]);
            hash.update(endpoint.id);
        }
        hash.update(row.amount_micros.as_bytes());
        hash.update([0]);
    }
    hash.finalize().into()
}
fn bytes(row: &Row, key: &str) -> Result<[u8; 32], JournalError> {
    let bytes: Vec<u8> = row.try_get(key).map_err(|_| JournalError::Projection)?;
    bytes.try_into().map_err(|_| JournalError::Projection)
}
fn rows(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
) -> Result<Vec<MoneyMovement>, JournalError> {
    let sql = format!("SELECT {COLUMNS} FROM public.v_observer_money_movement_v1 WHERE campaign_id=$1 AND resolve_tick=$2 ORDER BY ordinal");
    let mut result = Vec::new();
    for row in client
        .query(&sql, &[campaign.as_uuid(), &tick])
        .map_err(|_| JournalError::Database)?
    {
        let reference_kind: Option<String> = row
            .try_get("reference_kind")
            .map_err(|_| JournalError::Projection)?;
        let reference = match reference_kind {
            Some(kind) => Some(MoneyReference {
                kind: MoneyReferenceKind::parse(&kind)?,
                id: bytes(&row, "reference_id")?,
            }),
            None => None,
        };
        let ordinal: i64 = row
            .try_get("ordinal")
            .map_err(|_| JournalError::Projection)?;
        let amount: String = row
            .try_get("amount_micros")
            .map_err(|_| JournalError::Projection)?;
        if amount
            .parse::<i128>()
            .map_err(|_| JournalError::Projection)?
            <= 0
        {
            return Err(JournalError::Projection);
        }
        result.push(MoneyMovement {
            ordinal: u64::try_from(ordinal).map_err(|_| JournalError::Projection)?,
            purpose: MoneyPurpose::parse(
                row.try_get("purpose")
                    .map_err(|_| JournalError::Projection)?,
            )?,
            reference,
            debit: MoneyEndpoint {
                kind: MoneyLocationKind::parse(
                    row.try_get("debit_kind")
                        .map_err(|_| JournalError::Projection)?,
                )?,
                id: bytes(&row, "debit_id")?,
            },
            credit: MoneyEndpoint {
                kind: MoneyLocationKind::parse(
                    row.try_get("credit_kind")
                        .map_err(|_| JournalError::Projection)?,
                )?,
                id: bytes(&row, "credit_id")?,
            },
            amount_micros: amount,
        });
    }
    Ok(result)
}
// Compare summaries to freshly authenticated movements even after detail expiration.
// PostgreSQL NUMERIC preserves per-purpose sums beyond the individual i128 bound.
fn verify_totals(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    movements: &[MoneyMovement],
) -> Result<(), JournalError> {
    let purposes: Vec<_> = movements.iter().map(|row| row.purpose.as_str()).collect();
    let amounts: Vec<_> = movements
        .iter()
        .map(|row| row.amount_micros.as_str())
        .collect();
    let row = client.query_one("WITH expected AS (\
        SELECT purpose,count(*) AS movement_count,sum(amount::numeric) AS amount_micros \
        FROM unnest($3::text[],$4::text[]) AS movement(purpose,amount) GROUP BY purpose), \
        stored AS (SELECT purpose,movement_count,amount_micros FROM babylon_state.money_movement_total_v1 \
        WHERE campaign_id=$1 AND resolve_tick=$2) \
        SELECT NOT EXISTS (SELECT 1 FROM expected FULL JOIN stored USING(purpose) \
        WHERE expected.movement_count IS DISTINCT FROM stored.movement_count \
        OR expected.amount_micros IS DISTINCT FROM stored.amount_micros)",
        &[campaign.as_uuid(), &tick, &purposes, &amounts]).map_err(|_| JournalError::Database)?;
    if !row
        .try_get::<_, bool>(0)
        .map_err(|_| JournalError::Projection)?
    {
        return Err(JournalError::Projection);
    }
    Ok(())
}

fn insert_rows(
    tx: &mut Transaction<'_>,
    campaign: CampaignId,
    tick: i64,
    rows: &[MoneyMovement],
) -> Result<(), JournalError> {
    for chunk in rows.chunks(1024) {
        let mut ordinals = Vec::with_capacity(chunk.len());
        let mut purposes = Vec::with_capacity(chunk.len());
        let mut references = Vec::with_capacity(chunk.len());
        let mut reference_ids = Vec::with_capacity(chunk.len());
        let mut debits = Vec::with_capacity(chunk.len());
        let mut debit_ids = Vec::with_capacity(chunk.len());
        let mut credits = Vec::with_capacity(chunk.len());
        let mut credit_ids = Vec::with_capacity(chunk.len());
        let mut amounts = Vec::with_capacity(chunk.len());
        for row in chunk {
            ordinals.push(i64::try_from(row.ordinal).map_err(|_| JournalError::Range)?);
            purposes.push(row.purpose.as_str());
            references.push(row.reference.as_ref().map(|r| r.kind.as_str()));
            reference_ids.push(row.reference.as_ref().map(|r| r.id.to_vec()));
            debits.push(row.debit.kind.as_str());
            debit_ids.push(row.debit.id.to_vec());
            credits.push(row.credit.kind.as_str());
            credit_ids.push(row.credit.id.to_vec());
            amounts.push(row.amount_micros.as_str());
        }
        tx.execute("INSERT INTO babylon_state.money_movement_v1 SELECT $1,$2,r.ordinal,r.purpose,r.reference_kind,r.reference_id,r.debit_kind,r.debit_id,r.credit_kind,r.credit_id,n.amount_micros FROM \
            unnest($3::bigint[],$4::text[],$5::text[],$6::bytea[],$7::text[],$8::bytea[],$9::text[],$10::bytea[],$11::text[]) \
            AS r(ordinal,purpose,reference_kind,reference_id,debit_kind,debit_id,credit_kind,credit_id,amount) \
            CROSS JOIN LATERAL (SELECT r.amount::numeric AS amount_micros) n",
            &[campaign.as_uuid(), &tick, &ordinals, &purposes, &references, &reference_ids, &debits, &debit_ids, &credits, &credit_ids, &amounts])
            .map_err(|_| JournalError::Database)?;
    }
    Ok(())
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Publication {
    Publish,
    Rebuild,
}

impl MoneyJournalWriter {
    /// Admit a bounded local target. Actual database-owner and schema authority is checked per publication.
    /// # Errors
    /// Refuses an external target or caller-controlled startup options.
    pub fn connect(config: &Config) -> Result<Self, JournalError> {
        crate::postgres_catalog::validate_connection_target(config)
            .map_err(|_| JournalError::Target)?;
        Ok(Self {
            config: config.clone(),
        })
    }
    pub(super) fn require_target(
        &self,
        observer: &ObserverEconomyReader,
    ) -> Result<(), JournalError> {
        // A different credential may read, but the source and writer must name the same server/database.
        if self.config.get_hosts() != observer.config.get_hosts()
            || self.config.get_ports() != observer.config.get_ports()
            || self.config.get_dbname() != observer.config.get_dbname()
        {
            return Err(JournalError::TargetMismatch);
        }
        Ok(())
    }

    /// Publish one freshly authenticated committed period; identical rows are idempotent.
    /// # Errors
    /// Refuses unauthenticated receipts, different targets, non-owner authority or storage drift.
    pub fn publish(
        &self,
        observer: &ObserverEconomyReader,
        campaign: CampaignId,
        period: u64,
    ) -> Result<PublishReport, JournalError> {
        self.publish_with_cursor(observer, campaign, period, &mut None)
    }
    /// Publish the next period while reusing freshly reauthenticated receipt history.
    /// The caller's cursor advances only after the journal transaction commits.
    /// # Errors
    /// Refuses the same authority and source failures as publication.
    pub fn publish_with_cursor(
        &self,
        observer: &ObserverEconomyReader,
        campaign: CampaignId,
        period: u64,
        cursor: &mut Option<ObserverMaterialCursor>,
    ) -> Result<PublishReport, JournalError> {
        self.write(observer, campaign, period, Publication::Publish, cursor)
    }
    /// Replace derived facts from freshly authenticated source, including permanent historical totals.
    /// Old detail is reconstructed for the transaction and pruned again to the latest thirteen source periods.
    /// # Errors
    /// Refuses the same authority and source failures as publication.
    pub fn rebuild(
        &self,
        observer: &ObserverEconomyReader,
        campaign: CampaignId,
        period: u64,
    ) -> Result<PublishReport, JournalError> {
        self.rebuild_with_cursor(observer, campaign, period, &mut None)
    }
    /// Rebuild the next period while reusing freshly reauthenticated receipt history.
    /// The caller's cursor advances only after the journal transaction commits.
    /// # Errors
    /// Refuses the same authority and source failures as rebuild.
    pub fn rebuild_with_cursor(
        &self,
        observer: &ObserverEconomyReader,
        campaign: CampaignId,
        period: u64,
        cursor: &mut Option<ObserverMaterialCursor>,
    ) -> Result<PublishReport, JournalError> {
        self.write(observer, campaign, period, Publication::Rebuild, cursor)
    }
    fn write(
        &self,
        observer: &ObserverEconomyReader,
        campaign: CampaignId,
        period: u64,
        operation: Publication,
        cursor: &mut Option<ObserverMaterialCursor>,
    ) -> Result<PublishReport, JournalError> {
        self.require_target(observer)?;
        let mut candidate = cursor.clone();
        let period_source = observer
            .committed_journal_period(campaign, period, &mut candidate)
            .map_err(JournalError::Observer)?;
        let economic = &period_source.payments;
        let source = &economic.source;
        let movements = model::derive_movements(source)?;
        let payment_digest = payment_storage::fingerprint(&economic.settlements, &movements)?;
        let payment_count =
            i64::try_from(economic.settlements.len()).map_err(|_| JournalError::Range)?;
        let tick = i64::try_from(period).map_err(|_| JournalError::Range)?;
        let count = i64::try_from(movements.len()).map_err(|_| JournalError::Range)?;
        let digest = digest(&movements);
        let mut client = crate::current_schema::bounded_config(&self.config)
            .connect(NoTls)
            .map_err(|_| JournalError::Database)?;
        let mut tx = begin_publication(&mut client)?;
        let existing = tx.query_opt("SELECT movement_sha256,movement_count,payment_count,payment_sha256,detail_retained FROM babylon_state.money_journal_period_v1 WHERE campaign_id=$1 AND resolve_tick=$2", &[campaign.as_uuid(), &tick]).map_err(|_| JournalError::Database)?;
        let changed = existing.is_none() || operation == Publication::Rebuild;
        let mode = if operation == Publication::Rebuild {
            Admission::Rebuild
        } else if changed {
            Admission::Insert
        } else {
            Admission::Verify
        };
        payment_storage::accounts(&mut tx, economic, mode)?;
        if let Some(existing) = existing {
            if operation == Publication::Publish {
                let retained: bool = existing
                    .try_get("detail_retained")
                    .map_err(|_| JournalError::Projection)?;
                if bytes(&existing, "payment_sha256")? != payment_digest
                    || existing
                        .try_get::<_, i64>("payment_count")
                        .map_err(|_| JournalError::Projection)?
                        != payment_count
                    || bytes(&existing, "movement_sha256")? != digest
                    || existing
                        .try_get::<_, i64>("movement_count")
                        .map_err(|_| JournalError::Projection)?
                        != count
                    || (retained && rows(&mut tx, campaign, tick)? != movements)
                {
                    return Err(JournalError::Projection);
                }
                if retained {
                    payment_storage::payments(
                        &mut tx,
                        campaign,
                        tick,
                        &economic.settlements,
                        mode,
                    )?;
                }
                verify_totals(&mut tx, campaign, tick, &movements)?;
            } else {
                tx.execute("DELETE FROM babylon_state.money_journal_period_v1 WHERE campaign_id=$1 AND resolve_tick=$2", &[campaign.as_uuid(), &tick]).map_err(|_| JournalError::Database)?;
            }
        }
        if changed {
            // Deferred FK permits staging all detail and SQL totals before the publication marker.
            insert_rows(&mut tx, campaign, tick, &movements)?;
            payment_storage::payments(&mut tx, campaign, tick, &economic.settlements, mode)?;
            tx.execute("INSERT INTO babylon_state.money_movement_total_v1 SELECT campaign_id,resolve_tick,purpose,count(*),sum(amount_micros) \
                FROM babylon_state.money_movement_v1 WHERE campaign_id=$1 AND resolve_tick=$2 GROUP BY campaign_id,resolve_tick,purpose", &[campaign.as_uuid(), &tick]).map_err(|_| JournalError::Database)?;
        }
        let site = statement_storage::publish(&mut tx, &period_source, mode)?;
        let binding = pin_after_pruning(&mut tx, source, tick)?;
        if changed {
            tx.execute("INSERT INTO babylon_state.money_journal_period_v1 (campaign_id,resolve_tick,journal_version,tick_content_hash,envelope_digest,schema_sha256,foundation_sha256,content_sha256,source_identity_bytes,receipt_sha256,movement_sha256,movement_count,detail_retained,payment_sha256,payment_count,site_accounting_sha256,site_monetary_books,site_count,site_stock_count,site_accounting_directory) \
                VALUES ($1,$2,1,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)", &[campaign.as_uuid(), &tick,
                    &source.identity.tick_content_hash().as_bytes().as_slice(), &binding.envelope.as_slice(), &crate::current_schema_sha256().as_slice(),
                    &source.identity.foundation_digest().as_slice(), &binding.content.as_slice(), &source.identity.canonical_bytes(),
                    &source.identity.receipt_digest().as_slice(), &digest.as_slice(), &count, &binding.detail_retained,&payment_digest.as_slice(),&payment_count,
                    &site.digest.as_slice(),&site.monetary,&site.sites,&site.stocks,&site.directory]).map_err(|_| JournalError::Database)?;
        } else {
            verify_period(&mut tx, source, &digest, count)?;
        }
        tx.commit().map_err(|_| JournalError::Database)?;
        *cursor = candidate;
        Ok(PublishReport {
            period,
            movement_count: u64::try_from(count).map_err(|_| JournalError::Range)?,
            changed,
        })
    }
}

fn begin_publication(client: &mut Client) -> Result<Transaction<'_>, JournalError> {
    // READ COMMITTED gets a fresh snapshot after the serialization lock, so concurrent identical
    // publishers observe the first committed marker rather than failing on a stale snapshot.
    let mut tx = client
        .build_transaction()
        .isolation_level(IsolationLevel::ReadCommitted)
        .read_only(false)
        .start()
        .map_err(|_| JournalError::Database)?;
    tx.batch_execute(
        "SET LOCAL statement_timeout='120s'; SET LOCAL idle_in_transaction_session_timeout='120s'",
    )
    .map_err(|_| JournalError::Database)?;
    tx.query_one(
        "SELECT pg_catalog.pg_advisory_xact_lock($1)",
        &[&JOURNAL_LOCK_KEY],
    )
    .map_err(|_| JournalError::Database)?;
    crate::current_schema::require_current_schema(&mut tx).map_err(|_| JournalError::Schema)?;
    Ok(tx)
}

struct JournalBinding {
    content: [u8; 32],
    envelope: [u8; 32],
    detail_retained: bool,
}

fn pin_after_pruning(
    tx: &mut Transaction<'_>,
    source: &CommittedMaterialReceipts,
    tick: i64,
) -> Result<JournalBinding, JournalError> {
    let campaign = source.campaign_id;
    let mut cutoff = retention_cutoff(tx, campaign)?;
    loop {
        tx.execute(MONEY_DETAIL_RETENTION_SQL, &[campaign.as_uuid(), &cutoff])
            .map_err(|_| JournalError::Database)?;
        // The runtime locks the foundation to publish a tick. Pin its row only after
        // bulk writes and pruning. A savepoint releases these locks if the tail moved.
        let mut pin = tx.transaction().map_err(|_| JournalError::Database)?;
        let binding = pin.query_opt("SELECT f.foundation_sha256,f.content_sha256,m.identity_bytes,t.tick_content_hash,t.envelope_digest \
            FROM babylon_state.material_campaign_foundation_v3 f JOIN babylon_state.material_tick_v3 m USING(campaign_id) \
            JOIN babylon_state.tick_commit t USING(campaign_id,resolve_tick) WHERE f.campaign_id=$1 AND m.resolve_tick=$2 \
            FOR SHARE OF f,m,t", &[source.campaign_id.as_uuid(), &tick]).map_err(|_| JournalError::Database)?.ok_or(JournalError::SourceChanged)?;
        if bytes(&binding, "foundation_sha256")? != source.identity.foundation_digest()
            || binding
                .try_get::<_, Vec<u8>>("identity_bytes")
                .map_err(|_| JournalError::Projection)?
                != source.identity.canonical_bytes()
            || bytes(&binding, "tick_content_hash")?
                != *source.identity.tick_content_hash().as_bytes()
        {
            return Err(JournalError::SourceChanged);
        }
        let pinned_cutoff = retention_cutoff(&mut pin, campaign)?;
        if pinned_cutoff < cutoff {
            return Err(JournalError::SourceChanged);
        }
        if pinned_cutoff == cutoff {
            let binding = JournalBinding {
                content: bytes(&binding, "content_sha256")?,
                envelope: bytes(&binding, "envelope_digest")?,
                detail_retained: tick > cutoff,
            };
            pin.commit().map_err(|_| JournalError::Database)?;
            return Ok(binding);
        }
        pin.rollback().map_err(|_| JournalError::Database)?;
        cutoff = pinned_cutoff;
    }
}

fn retention_cutoff(tx: &mut Transaction<'_>, campaign: CampaignId) -> Result<i64, JournalError> {
    let latest: i64 = tx
        .query_one(
            "SELECT max(resolve_tick) FROM babylon_state.tick_commit WHERE campaign_id=$1",
            &[campaign.as_uuid()],
        )
        .map_err(|_| JournalError::Database)?
        .try_get(0)
        .map_err(|_| JournalError::Projection)?;
    Ok((latest - KEEP_PERIODS).max(0))
}

pub(super) fn open_observer(observer: &ObserverEconomyReader) -> Result<Client, JournalError> {
    if observer.visibility != ObserverVisibility::FullObserver {
        return Err(JournalError::Authority);
    }
    let mut client = crate::current_schema::bounded_config(&observer.config)
        .connect(NoTls)
        .map_err(|_| JournalError::Database)?;
    crate::observer_reader::confine_authority(&mut client, ObserverVisibility::FullObserver)
        .map_err(JournalError::Observer)?;
    Ok(client)
}
fn verify_period(
    client: &mut impl GenericClient,
    source: &CommittedMaterialReceipts,
    movement_digest: &[u8; 32],
    movement_count: i64,
) -> Result<(), JournalError> {
    let tick = i64::try_from(source.identity.resolve_tick()).map_err(|_| JournalError::Range)?;
    let row = client.query_opt("SELECT source_identity_bytes,receipt_sha256,movement_sha256,movement_count FROM public.v_observer_money_journal_period_v1 WHERE campaign_id=$1 AND resolve_tick=$2", &[source.campaign_id.as_uuid(), &tick]).map_err(|_| JournalError::Database)?.ok_or(JournalError::CoverageAbsent)?;
    if row
        .try_get::<_, Vec<u8>>("source_identity_bytes")
        .map_err(|_| JournalError::Projection)?
        != source.identity.canonical_bytes()
        || bytes(&row, "receipt_sha256")? != source.identity.receipt_digest()
        || bytes(&row, "movement_sha256")? != *movement_digest
        || row
            .try_get::<_, i64>("movement_count")
            .map_err(|_| JournalError::Projection)?
            != movement_count
    {
        return Err(JournalError::Projection);
    }
    Ok(())
}

fn totals(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    first: i64,
    last: i64,
) -> Result<Vec<MoneyTotal>, JournalError> {
    let mut result = Vec::new();
    for row in client.query("SELECT purpose,sum(movement_count)::bigint AS movement_count,sum(amount_micros)::text AS amount_micros \
        FROM public.v_observer_money_movement_total_v1 WHERE campaign_id=$1 AND resolve_tick BETWEEN $2 AND $3 GROUP BY purpose ORDER BY purpose COLLATE pg_catalog.\"C\"", &[campaign.as_uuid(), &first, &last]).map_err(|_| JournalError::Database)? {
        let count: i64 = row.try_get("movement_count").map_err(|_| JournalError::Projection)?;
        result.push(MoneyTotal { purpose: MoneyPurpose::parse(row.try_get("purpose").map_err(|_| JournalError::Projection)?)?,
            movement_count: u64::try_from(count).map_err(|_| JournalError::Range)?, amount_micros: row.try_get("amount_micros").map_err(|_| JournalError::Projection)? });
    }
    Ok(result)
}
impl ObserverEconomyReader {
    /// Read retained SQL detail; only pruned historical detail reopens authenticated receipts.
    /// # Errors
    /// Refuses preview authority, missing coverage and inconsistent published/source evidence.
    pub fn money_movements(
        &self,
        campaign: CampaignId,
        period: u64,
    ) -> Result<Vec<MoneyMovement>, JournalError> {
        if period == 0 {
            return Err(JournalError::Range);
        }
        let tick = i64::try_from(period).map_err(|_| JournalError::Range)?;
        let mut client = open_observer(self)?;
        let mut tx = client
            .build_transaction()
            .isolation_level(IsolationLevel::RepeatableRead)
            .read_only(true)
            .start()
            .map_err(|_| JournalError::Database)?;
        let marker = tx.query_opt("SELECT movement_sha256,movement_count,detail_retained,source_identity_bytes,receipt_sha256 FROM public.v_observer_money_journal_period_v1 WHERE campaign_id=$1 AND resolve_tick=$2", &[campaign.as_uuid(), &tick]).map_err(|_| JournalError::Database)?.ok_or(JournalError::CoverageAbsent)?;
        let retained: bool = marker
            .try_get("detail_retained")
            .map_err(|_| JournalError::Projection)?;
        let result = if retained {
            rows(&mut tx, campaign, tick)?
        } else {
            let source = self
                .committed_material_receipts(campaign, period)
                .map_err(JournalError::Observer)?;
            if marker
                .try_get::<_, Vec<u8>>("source_identity_bytes")
                .map_err(|_| JournalError::Projection)?
                != source.identity.canonical_bytes()
                || bytes(&marker, "receipt_sha256")? != source.identity.receipt_digest()
            {
                return Err(JournalError::SourceChanged);
            }
            model::derive_movements(&source)?
        };
        if bytes(&marker, "movement_sha256")? != digest(&result)
            || marker
                .try_get::<_, i64>("movement_count")
                .map_err(|_| JournalError::Projection)?
                != i64::try_from(result.len()).map_err(|_| JournalError::Range)?
        {
            return Err(JournalError::Projection);
        }
        tx.commit().map_err(|_| JournalError::Database)?;
        Ok(result)
    }
    /// Aggregate SQL facts across completely published periods without reopening packed receipts.
    /// Reservations and cancellations remain separate purposes and never become second sales.
    /// # Errors
    /// Refuses coverage gaps, preview authority, stale source markers or invalid period arguments.
    pub fn money_totals(
        &self,
        campaign: CampaignId,
        first: u64,
        last: u64,
    ) -> Result<Vec<MoneyTotal>, JournalError> {
        if first == 0 || last < first {
            return Err(JournalError::Range);
        }
        let first_tick = i64::try_from(first).map_err(|_| JournalError::Range)?;
        let last_tick = i64::try_from(last).map_err(|_| JournalError::Range)?;
        let wanted = last_tick
            .checked_sub(first_tick)
            .and_then(|v| v.checked_add(1))
            .ok_or(JournalError::Range)?;
        let mut client = open_observer(self)?;
        let mut tx = client
            .build_transaction()
            .isolation_level(IsolationLevel::RepeatableRead)
            .read_only(true)
            .start()
            .map_err(|_| JournalError::Database)?;
        let coverage = tx.query_one("SELECT count(*) AS covered,coalesce(bool_and(p.movement_count=coalesce(t.n,0)),true) AS complete \
            FROM public.v_observer_money_journal_period_v1 p LEFT JOIN \
            (SELECT resolve_tick,sum(movement_count) AS n FROM public.v_observer_money_movement_total_v1 WHERE campaign_id=$1 AND resolve_tick BETWEEN $2 AND $3 GROUP BY resolve_tick) t USING(resolve_tick) \
            WHERE p.campaign_id=$1 AND p.resolve_tick BETWEEN $2 AND $3", &[campaign.as_uuid(), &first_tick, &last_tick]).map_err(|_| JournalError::Database)?;
        if coverage
            .try_get::<_, i64>("covered")
            .map_err(|_| JournalError::Projection)?
            != wanted
        {
            return Err(JournalError::CoverageAbsent);
        }
        if !coverage
            .try_get::<_, bool>("complete")
            .map_err(|_| JournalError::Projection)?
        {
            return Err(JournalError::Projection);
        }
        let result = totals(&mut tx, campaign, first_tick, last_tick)?;
        tx.commit().map_err(|_| JournalError::Database)?;
        Ok(result)
    }
}
