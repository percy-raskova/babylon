//! One ordered atomic publication path; no mutable-head write remains.

use super::{
    knowledge,
    record::{is_link, parse_page_key, CheckedRevision, GrantDependency, RevisionRecord},
    storage, tick_knowledge, ArchiveReadScope,
};
use crate::archive::{database, decode, decode_digest, mint_page_atoms, persist_atom_rows};
use crate::{
    identity::CampaignId, ArchiveDirtyBatch, ArchiveKnowledge, ArchiveMaterializeDisposition,
    ArchiveMaterializeMode, ArchiveMaterializeReport, ArchivePageInput, FogSafeArchiveRenderer,
    MaterializedArchivePage, PendingArchiveReceipt, RenderedArchivePage, SemanticArchiveError,
    SemanticArchiveStore,
};
use postgres::{Client, GenericClient, IsolationLevel};
use sha2::{Digest as _, Sha256};

pub(super) fn with_campaign_lock<T>(
    client: &mut Client,
    campaign: CampaignId,
    operation: impl FnOnce(&mut Client) -> Result<T, SemanticArchiveError>,
) -> Result<T, SemanticArchiveError> {
    let mut hash = Sha256::new();
    hash.update(b"babylon.archive-campaign-lock.v2\0");
    hash.update(campaign.canonical_bytes());
    let bytes: [u8; 32] = hash.finalize().into();
    let key = i64::from_be_bytes(
        bytes[..8]
            .try_into()
            .map_err(|_| SemanticArchiveError::InvalidIdentity)?,
    );
    client
        .query_one("SELECT pg_catalog.pg_advisory_lock($1)", &[&key])
        .map_err(|error| database("lock ordered Archive campaign publication", &error))?;
    let result = operation(client);
    let unlocked = client
        .query_one("SELECT pg_catalog.pg_advisory_unlock($1)", &[&key])
        .map_err(|error| database("unlock ordered Archive campaign publication", &error))
        .and_then(|row| decode::<bool>(&row, 0));
    match (result, unlocked) {
        (Err(error), _) | (Ok(_), Err(error)) => Err(error),
        (Ok(value), Ok(true)) => Ok(value),
        (Ok(_), Ok(false)) => Err(SemanticArchiveError::SchemaMismatch),
    }
}

pub(super) fn next_receipt(
    client: &mut impl GenericClient,
    campaign: CampaignId,
) -> Result<Option<PendingArchiveReceipt>, SemanticArchiveError> {
    let pending=client.query_opt("SELECT marker.resolve_tick,marker.tick_content_hash,dirty.tick_content_hash \
        FROM babylon_state.tick_commit marker LEFT JOIN babylon_state.archive_dirty_receipt_v1 dirty \
        USING(campaign_id,resolve_tick) LEFT JOIN babylon_meta.archive_receipt_consumption_v1 consumed \
        ON consumed.campaign_id=marker.campaign_id AND consumed.resolve_tick=marker.resolve_tick \
        AND consumed.tick_content_hash=marker.tick_content_hash \
        WHERE marker.campaign_id=$1 AND consumed.campaign_id IS NULL ORDER BY marker.resolve_tick LIMIT 1", &[campaign.as_uuid()])
        .map_err(|error|database("read earliest unsettled Archive marker",&error))?;
    let pending = pending
        .map(|row| {
            let hash = decode_digest(&row, 1)?;
            if decode_digest(&row, 2)? != hash {
                return Err(SemanticArchiveError::ReceiptMismatch);
            }
            PendingArchiveReceipt::try_new(storage::unsigned(decode(&row, 0)?)?, hash)
        })
        .transpose()?;
    Ok(pending)
}

pub(crate) fn materialize(
    store: &SemanticArchiveStore,
    campaign: CampaignId,
    batch: &ArchiveDirtyBatch,
    mode: ArchiveMaterializeMode,
) -> Result<ArchiveMaterializeReport, SemanticArchiveError> {
    let mut client = store.connect("connect immutable Archive materializer")?;
    with_campaign_lock(&mut client, campaign, |client| {
        let scope = ArchiveReadScope::committed(
            campaign,
            batch.resolve_tick(),
            *batch.tick_content_hash(),
        )?;
        let mut capture = client
            .build_transaction()
            .isolation_level(IsolationLevel::Serializable)
            .read_only(true)
            .start()
            .map_err(|error| database("begin immutable Archive input capture", &error))?;
        crate::current_schema::require_current_schema(&mut capture)
            .map_err(SemanticArchiveError::CurrentSchema)?;
        validate_receipt_identity(&mut capture, &scope, false)?;
        let known = tick_knowledge::capture(&mut capture, &scope)?;
        capture
            .commit()
            .map_err(|error| database("finish immutable Archive input capture", &error))?;
        let receipt =
            PendingArchiveReceipt::try_new(batch.resolve_tick(), *batch.tick_content_hash())?;
        let mut prepared = prepare(campaign, &receipt, batch, &known)?;
        authenticate_existing(client, &mut prepared)?;
        let mut tx = client
            .build_transaction()
            .isolation_level(IsolationLevel::Serializable)
            .read_only(false)
            .start()
            .map_err(|error| database("begin immutable Archive batch", &error))?;
        crate::current_schema::require_current_schema(&mut tx)
            .map_err(SemanticArchiveError::CurrentSchema)?;
        validate_receipt(&mut tx, &scope)?;
        tick_knowledge::pin_prepared(&mut tx, &scope, &known)?;
        let report = publish(&mut tx, prepared, mode)?;
        tx.commit()
            .map_err(|error| database("commit immutable Archive batch", &error))?;
        Ok(report)
    })
}

/// Authenticate the prepared identity and ordered head before pin insertion.
pub(super) fn revalidate_prepared(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    receipt: &PendingArchiveReceipt,
) -> Result<(), SemanticArchiveError> {
    let scope = ArchiveReadScope::committed(
        campaign,
        receipt.resolve_tick(),
        *receipt.tick_content_hash(),
    )?;
    validate_receipt(client, &scope)?;
    if next_receipt(client, campaign)?.as_ref() != Some(receipt) {
        return Err(SemanticArchiveError::ArchiveOrderViolation);
    }
    Ok(())
}

/// Owned canonical rendering; construction requires no database client.
/// Private fields bind each rendered page to the exact batch and frozen knowledge.
pub(super) struct PreparedPublication {
    scope: ArchiveReadScope,
    receipt: PendingArchiveReceipt,
    batch: ArchiveDirtyBatch,
    known: ArchiveKnowledge,
    pages: Vec<(CheckedRevision, RenderedArchivePage)>,
}

pub(super) fn prepare(
    campaign: CampaignId,
    receipt: &PendingArchiveReceipt,
    batch: &ArchiveDirtyBatch,
    known: &ArchiveKnowledge,
) -> Result<PreparedPublication, SemanticArchiveError> {
    crate::archive_batch_matches_receipt(batch, receipt)?;
    let scope = ArchiveReadScope::committed(
        campaign,
        receipt.resolve_tick(),
        *receipt.tick_content_hash(),
    )?;
    let renderer = FogSafeArchiveRenderer::new()?;
    let pages = batch
        .pages()
        .iter()
        .map(|input| prepare_page(&renderer, &scope, input, known))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(PreparedPublication {
        scope,
        receipt: receipt.clone(),
        batch: batch.clone(),
        known: known.clone(),
        pages,
    })
}

/// Capture existing exact-tick candidates under one short snapshot; admit detached.
pub(super) fn authenticate_existing(
    client: &mut postgres::Client,
    prepared: &mut PreparedPublication,
) -> Result<(), SemanticArchiveError> {
    let mut tx = client
        .build_transaction()
        .isolation_level(IsolationLevel::Serializable)
        .read_only(true)
        .start()
        .map_err(|e| database("capture prepared Archive replay bodies", &e))?;
    let subjects = prepared
        .pages
        .iter()
        .map(|(checked, _)| checked.record().subject.clone())
        .collect::<Vec<_>>();
    let captured = storage::capture_comparison_records(
        &mut tx,
        prepared.scope.campaign_id(),
        prepared.scope.tick(),
        &subjects,
    )?;
    tx.commit()
        .map_err(|e| database("finish prepared Archive replay body capture", &e))?;
    for ((checked, _), existing) in prepared.pages.iter_mut().zip(captured) {
        if let Some(existing) = existing {
            let body = existing.body()?;
            // Older quiet revisions are not conflicts with a newly selected tick.
            let admitted = existing.admit()?;
            if admitted.effective_tick == checked.record().effective_tick {
                if admitted != *checked.record() || admitted.digest()? != checked.digest() {
                    return Err(SemanticArchiveError::ReceiptConflict);
                }
                checked.bind_replay_body(body);
            }
        }
    }
    Ok(())
}

pub(super) fn publish(
    client: &mut impl GenericClient,
    prepared: PreparedPublication,
    mode: ArchiveMaterializeMode,
) -> Result<ArchiveMaterializeReport, SemanticArchiveError> {
    #[cfg(test)]
    let _publication_observation = super::body_encoding::PublicationObservation::enter();
    let PreparedPublication {
        scope,
        receipt,
        batch,
        known,
        pages,
    } = prepared;
    let campaign = scope.campaign_id();
    validate_receipt(client, &scope)?;
    // Keep campaign deletion ordered after this publication and its final claim,
    // while allowing the runtime to advance the campaign's non-key tick fields.
    // Receipt ordering is already held by the separate Archive campaign lock.
    client
        .query_one(
            "SELECT campaign_id FROM babylon_meta.campaign WHERE campaign_id=$1 FOR KEY SHARE",
            &[campaign.as_uuid()],
        )
        .map_err(|error| database("hold Archive campaign during publication", &error))?;
    if reconcile(client, campaign, &batch, &known)? {
        return Ok(ArchiveMaterializeReport {
            disposition: ArchiveMaterializeDisposition::AlreadyConsumed,
            pages: Vec::new(),
        });
    }
    if next_receipt(client, campaign)?.as_ref() != Some(&receipt) {
        return Err(SemanticArchiveError::ArchiveOrderViolation);
    }
    if tick_knowledge::load(client, &scope)? != known {
        return Err(SemanticArchiveError::ReceiptConflict);
    }
    let pages = pages
        .into_iter()
        .map(|(record, page)| publish_page(client, &record, page))
        .collect::<Result<Vec<_>, _>>()?;
    if mode == ArchiveMaterializeMode::Consume {
        claim(client, campaign, &batch, &known)?;
    }
    Ok(ArchiveMaterializeReport {
        disposition: ArchiveMaterializeDisposition::Applied,
        pages,
    })
}

fn validate_receipt(
    client: &mut impl GenericClient,
    scope: &ArchiveReadScope,
) -> Result<(), SemanticArchiveError> {
    validate_receipt_identity(client, scope, true)
}

fn validate_receipt_identity(
    client: &mut impl GenericClient,
    scope: &ArchiveReadScope,
    lock: bool,
) -> Result<(), SemanticArchiveError> {
    let campaign = scope.campaign_id();
    let locking = if lock {
        " FOR SHARE OF dirty,marker"
    } else {
        ""
    };
    let row = client
        .query_opt(
            &format!("SELECT dirty.tick_content_hash,marker.tick_content_hash \
        FROM babylon_state.archive_dirty_receipt_v1 dirty JOIN babylon_state.tick_commit marker \
        USING(campaign_id,resolve_tick) WHERE dirty.campaign_id=$1 AND dirty.resolve_tick=$2{locking}"),
            &[campaign.as_uuid(), &storage::signed(scope.tick())?],
        )
        .map_err(|error| database("validate ordered Archive source receipt", &error))?
        .ok_or(SemanticArchiveError::MissingCommittedReceipt)?;
    if Some(decode_digest(&row, 0)?) != scope.tick_content_hash()
        || Some(decode_digest(&row, 1)?) != scope.tick_content_hash()
    {
        return Err(SemanticArchiveError::ReceiptMismatch);
    }
    Ok(())
}

fn prepare_page(
    renderer: &FogSafeArchiveRenderer,
    scope: &ArchiveReadScope,
    input: &ArchivePageInput,
    known: &ArchiveKnowledge,
) -> Result<(CheckedRevision, RenderedArchivePage), SemanticArchiveError> {
    let (page, emission) = renderer.render_with_emission(input, known)?;
    let atoms = mint_page_atoms(scope.campaign_id(), scope.tick(), input, known)?;
    let mut record = RevisionRecord {
        source: scope.clone(),
        subject: input.subject().page_ref().clone(),
        effective_tick: scope.tick(),
        title: input.subject().title().to_owned(),
        template_sha256: crate::ARCHIVE_PAGE_TEMPLATE_SHA256,
        content_sha256: page.sha256(),
        markdown: page.markdown().to_owned(),
        search_text: page.search_text().to_owned(),
        provenance_json: serde_json::to_string(page.citations())
            .map_err(|_| SemanticArchiveError::InvalidText)?,
        atoms,
        grants: Vec::new(),
        emission,
    };
    let mut keys = std::collections::BTreeSet::new();
    keys.insert((record.subject.clone(), "subject".to_owned()));
    for atom in &record.atoms {
        let subject = if is_link(atom) {
            let crate::ArchiveAtomValue::Text(target) = atom.value() else {
                return Err(SemanticArchiveError::StoredPageMismatch);
            };
            parse_page_key(target)?
        } else {
            record.subject.clone()
        };
        keys.insert((subject, atom.grant_key().to_owned()));
    }
    record.grants = keys
        .into_iter()
        .map(|(subject, key)| {
            let grant = known
                .grant(&subject, &key)
                .ok_or(SemanticArchiveError::UnknownSubject)?;
            Ok(GrantDependency {
                subject,
                key,
                granted_tick: grant.granted_tick,
                citation: grant.citation.clone(),
            })
        })
        .collect::<Result<Vec<_>, SemanticArchiveError>>()?;
    record.grants.sort_by(|a, b| {
        (a.subject.kind().as_str(), a.subject.id(), &a.key).cmp(&(
            b.subject.kind().as_str(),
            b.subject.id(),
            &b.key,
        ))
    });
    Ok((CheckedRevision::new(record)?, page))
}

fn publish_page(
    client: &mut impl GenericClient,
    checked: &CheckedRevision,
    page: RenderedArchivePage,
) -> Result<MaterializedArchivePage, SemanticArchiveError> {
    let record = checked.record();
    if knowledge::capture(client, record)? != record.grants {
        return Err(SemanticArchiveError::ReceiptConflict);
    }
    let minted = persist_atom_rows(client, record.source.campaign_id(), &record.atoms)?;
    let persisted = storage::insert(client, checked)?;
    Ok(MaterializedArchivePage {
        page_ref: record.subject.clone(),
        page,
        persisted,
        atoms: minted,
    })
}

fn reconcile(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    batch: &ArchiveDirtyBatch,
    known: &ArchiveKnowledge,
) -> Result<bool, SemanticArchiveError> {
    let row = client
        .query_opt(
            "SELECT tick_content_hash,batch_sha256,worker_contract_sha256,knowledge_sha256 \
        FROM babylon_meta.archive_receipt_consumption_v1 WHERE campaign_id=$1 AND resolve_tick=$2",
            &[campaign.as_uuid(), &storage::signed(batch.resolve_tick())?],
        )
        .map_err(|error| database("reconcile immutable Archive receipt", &error))?;
    let Some(row) = row else {
        return Ok(false);
    };
    if decode_digest(&row, 0)? != *batch.tick_content_hash()
        || decode_digest(&row, 1)? != batch.sha256()
        || decode_digest(&row, 2)? != crate::archive_worker_contract_sha256()
        || decode_digest(&row, 3)? != known.sha256()
    {
        return Err(SemanticArchiveError::ReceiptConflict);
    }
    Ok(true)
}

fn claim(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    batch: &ArchiveDirtyBatch,
    known: &ArchiveKnowledge,
) -> Result<(), SemanticArchiveError> {
    client.execute("INSERT INTO babylon_meta.archive_receipt_consumption_v1 \
        (campaign_id,resolve_tick,tick_content_hash,batch_sha256,worker_contract_sha256,knowledge_sha256) \
        VALUES($1,$2,$3,$4,$5,$6)", &[campaign.as_uuid(),&storage::signed(batch.resolve_tick())?,
        &&batch.tick_content_hash()[..],&&batch.sha256()[..],&&crate::archive_worker_contract_sha256()[..],&&known.sha256()[..]])
        .map_err(|error|database("claim ordered immutable Archive receipt",&error))?;
    Ok(())
}

/// Compare the full emitted profile at the original source K. This preserves a
/// quiet page's K and citations while detecting changes in values, labels,
/// question, unknown links, and the pinned knowledge projection at current T.
pub(crate) fn select_dirty_pages<T>(
    config: &postgres::Config,
    campaign: CampaignId,
    receipt: &PendingArchiveReceipt,
    known: &ArchiveKnowledge,
    plans: &[T],
    budget: usize,
    make: impl Fn(&T, u64, [u8; 32]) -> Result<ArchivePageInput, SemanticArchiveError>,
) -> Result<crate::ArchiveProducerOutcome, SemanticArchiveError> {
    let inputs = plans
        .iter()
        .map(|plan| {
            make(plan, receipt.resolve_tick(), *receipt.tick_content_hash())
                .map(|input| (plan, input))
        })
        .collect::<Result<Vec<_>, _>>()?;
    let mut client =
        SemanticArchiveStore::new(config).connect("connect retained producer comparison")?;
    let mut tx = client
        .build_transaction()
        .isolation_level(IsolationLevel::RepeatableRead)
        .read_only(true)
        .start()
        .map_err(|error| database("begin retained producer comparison", &error))?;
    let inputs = inputs
        .into_iter()
        .filter(|(_, input)| known.knows_subject(input.subject().page_ref()))
        .collect::<Vec<_>>();
    let subjects = inputs
        .iter()
        .map(|(_, input)| input.subject().page_ref().clone())
        .collect::<Vec<_>>();
    let captured =
        storage::capture_comparison_records(&mut tx, campaign, receipt.resolve_tick(), &subjects)?;
    let candidates = inputs
        .into_iter()
        .zip(captured)
        .map(|((plan, input), stored)| (plan, input, stored))
        .collect::<Vec<_>>();
    tx.commit()
        .map_err(|error| database("commit retained producer comparison read", &error))?;
    let renderer = FogSafeArchiveRenderer::new()?;
    let mut pages = Vec::new();
    let mut remaining = 0usize;
    for (plan, input, stored) in candidates {
        let quiet = if let Some(captured) = stored {
            let record = captured.admit()?;
            let old = make(
                plan,
                record.source.tick(),
                record
                    .source
                    .tick_content_hash()
                    .ok_or(SemanticArchiveError::StoredPageMismatch)?,
            )?;
            let (expected, witness) = renderer.render_with_emission(&old, known)?;
            record.title == old.subject().title()
                && record.markdown == expected.markdown()
                && record.search_text == expected.search_text()
                && record.emission == witness
                && record.provenance_json
                    == serde_json::to_string(expected.citations())
                        .map_err(|_| SemanticArchiveError::InvalidText)?
        } else {
            false
        };
        if !quiet {
            if pages.len() < budget.min(ArchiveDirtyBatch::MAX_PAGES) {
                pages.push(input);
            } else {
                remaining = remaining
                    .checked_add(1)
                    .ok_or(SemanticArchiveError::CollectionBound)?;
            }
        }
    }
    Ok(crate::ArchiveProducerOutcome::new(
        ArchiveDirtyBatch::try_new(receipt.resolve_tick(), *receipt.tick_content_hash(), pages)?,
        remaining,
    ))
}
