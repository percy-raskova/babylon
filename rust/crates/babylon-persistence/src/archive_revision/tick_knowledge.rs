//! Frozen disclosure sets reconstructed from authenticated bases and actual admissions.

use super::storage::{signed, unsigned};
use super::ArchiveReadScope;
use crate::archive::{database, decode, decode_digest, decode_subject_kind, read_knowledge};
use crate::{
    ArchiveCitation, ArchiveKnowledge, ArchiveKnowledgeGrant, ArchivePageRef, SemanticArchiveError,
};
use postgres::GenericClient;

/// Designed storage cadence, not a game period rule. SQL bounds the same segment.
pub(super) const ARCHIVE_KNOWLEDGE_CHECKPOINT_PERIODS: u64 = 13;

/// Existing publication pins remain the authority even after backdated grants.
pub(super) fn capture(
    client: &mut impl GenericClient,
    scope: &ArchiveReadScope,
) -> Result<ArchiveKnowledge, SemanticArchiveError> {
    let campaign = scope.campaign_id();
    let tick = signed(scope.tick())?;
    let pinned = client.query_opt(
        "SELECT 1 FROM babylon_meta.archive_tick_knowledge_v3 WHERE campaign_id=$1 AND resolve_tick=$2",
        &[campaign.as_uuid(), &tick],
    ).map_err(|error| database("inspect Archive production knowledge", &error))?;
    if pinned.is_some() {
        load(client, scope)
    } else {
        read_knowledge(client, campaign, tick)
    }
}

pub(super) fn pin_prepared(
    client: &mut impl GenericClient,
    scope: &ArchiveReadScope,
    prepared: &ArchiveKnowledge,
) -> Result<(), SemanticArchiveError> {
    if capture(client, scope)? != *prepared || pin(client, scope)? != *prepared {
        return Err(SemanticArchiveError::ReceiptConflict);
    }
    Ok(())
}

fn checkpoint_for_tick(tick: u64, previous: Option<u64>) -> Result<u64, SemanticArchiveError> {
    match previous {
        None if tick > 0 => Ok(tick),
        Some(checkpoint) if checkpoint > 0 => {
            let span = tick
                .checked_sub(checkpoint)
                .ok_or(SemanticArchiveError::StoredPageMismatch)?;
            Ok(if span >= ARCHIVE_KNOWLEDGE_CHECKPOINT_PERIODS {
                tick
            } else {
                checkpoint
            })
        }
        _ => Err(SemanticArchiveError::StoredPageMismatch),
    }
}

fn previous_pin(
    client: &mut impl GenericClient,
    scope: &ArchiveReadScope,
) -> Result<Option<(u64, ArchiveKnowledge)>, SemanticArchiveError> {
    let row = client
        .query_opt(
            "SELECT pin.resolve_tick,pin.checkpoint_tick,marker.tick_content_hash \
         FROM babylon_meta.archive_tick_knowledge_v3 pin JOIN babylon_state.tick_commit marker \
         USING(campaign_id,resolve_tick) WHERE pin.campaign_id=$1 AND pin.resolve_tick<$2 \
         ORDER BY pin.resolve_tick DESC LIMIT 1",
            &[scope.campaign_id().as_uuid(), &signed(scope.tick())?],
        )
        .map_err(|error| database("read preceding frozen Archive membership", &error))?;
    row.map(|row| {
        let preceding = ArchiveReadScope::committed(
            scope.campaign_id(),
            unsigned(decode(&row, 0)?)?,
            decode_digest(&row, 2)?,
        )?;
        Ok((unsigned(decode(&row, 1)?)?, load(client, &preceding)?))
    })
    .transpose()
}

fn admissions(
    knowledge: &ArchiveKnowledge,
    previous: Option<&ArchiveKnowledge>,
    checkpoint: bool,
) -> Result<ArchiveKnowledge, SemanticArchiveError> {
    if let Some(previous) = previous {
        if previous
            .rows()
            .any(|grant| knowledge.grant(&grant.page_ref, &grant.grant_key) != Some(grant))
        {
            return Err(SemanticArchiveError::ReceiptConflict);
        }
    }
    ArchiveKnowledge::try_new(
        knowledge
            .rows()
            .filter(|grant| {
                checkpoint
                    || previous
                        .is_none_or(|old| old.grant(&grant.page_ref, &grant.grant_key).is_none())
            })
            .cloned()
            .collect(),
    )
}

pub(super) fn pin(
    client: &mut impl GenericClient,
    scope: &ArchiveReadScope,
) -> Result<ArchiveKnowledge, SemanticArchiveError> {
    let campaign = scope.campaign_id();
    let tick = signed(scope.tick())?;
    let exists = client.query_opt(
        "SELECT 1 FROM babylon_meta.archive_tick_knowledge_v3 WHERE campaign_id=$1 AND resolve_tick=$2",
        &[campaign.as_uuid(), &tick],
    ).map_err(|error| database("inspect pinned Archive knowledge", &error))?.is_some();
    if !exists {
        let knowledge = read_knowledge(client, campaign, tick)?;
        let previous = previous_pin(client, scope)?;
        let checkpoint =
            checkpoint_for_tick(scope.tick(), previous.as_ref().map(|(tick, _)| *tick))?;
        let admitted = admissions(
            &knowledge,
            previous.as_ref().map(|(_, known)| known),
            checkpoint == scope.tick(),
        )?;
        insert_pin(client, scope, checkpoint, &knowledge, &admitted)?;
    }
    load(client, scope)
}

fn insert_pin(
    client: &mut impl GenericClient,
    scope: &ArchiveReadScope,
    checkpoint: u64,
    knowledge: &ArchiveKnowledge,
    admitted: &ArchiveKnowledge,
) -> Result<(), SemanticArchiveError> {
    let campaign = scope.campaign_id();
    let tick = signed(scope.tick())?;
    let checkpoint = signed(checkpoint)?;
    let count = i32::try_from(knowledge.rows().count())
        .map_err(|_| SemanticArchiveError::CollectionBound)?;
    let admitted_count = i32::try_from(admitted.rows().count())
        .map_err(|_| SemanticArchiveError::CollectionBound)?;
    let hash = scope
        .tick_content_hash()
        .ok_or(SemanticArchiveError::InvalidVerifiedTick)?;
    client.execute("INSERT INTO babylon_meta.archive_tick_knowledge_v3 \
        (campaign_id,resolve_tick,checkpoint_tick,tick_content_hash,worker_contract_sha256,knowledge_sha256,grant_count,admitted_sha256,admitted_count) \
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)",
        &[campaign.as_uuid(),&tick,&checkpoint,&&hash[..],&&crate::archive_worker_contract_sha256()[..],
          &&knowledge.sha256()[..],&count,&&admitted.sha256()[..],&admitted_count])
        .map_err(|error|database("pin exact Archive knowledge and admission identity",&error))?;
    let mut subject_kinds = Vec::new();
    let mut subject_ids = Vec::new();
    let mut grant_keys = Vec::new();
    for grant in admitted.rows() {
        subject_kinds.push(grant.page_ref.kind().as_str());
        subject_ids.push(grant.page_ref.id());
        grant_keys.push(grant.grant_key.as_str());
    }
    let inserted = client.execute("INSERT INTO babylon_meta.archive_knowledge_membership_v3 \
        (campaign_id,checkpoint_tick,admitted_at_tick,subject_kind,subject_id,grant_key) \
        SELECT $1,$2,$3,membership.subject_kind,membership.subject_id,membership.grant_key \
        FROM UNNEST($4::text[],$5::text[],$6::text[]) AS membership(subject_kind,subject_id,grant_key)",
        &[campaign.as_uuid(),&checkpoint,&tick,&subject_kinds,&subject_ids,&grant_keys])
        .map_err(|error|database("pin exact Archive membership admissions",&error))?;
    if inserted
        != u64::try_from(admitted_count).map_err(|_| SemanticArchiveError::CollectionBound)?
    {
        return Err(SemanticArchiveError::StoredPageMismatch);
    }
    // Avoid an empty-table estimate turning authentication into a quadratic join.
    client
        .batch_execute(
            "ANALYZE babylon_meta.archive_knowledge_grant_v1; \
        ANALYZE babylon_meta.archive_tick_knowledge_v3; \
        ANALYZE babylon_meta.archive_knowledge_membership_v3",
        )
        .map_err(|error| database("refresh frozen Archive membership statistics", &error))?;
    Ok(())
}

pub(super) fn load(
    client: &mut impl GenericClient,
    scope: &ArchiveReadScope,
) -> Result<ArchiveKnowledge, SemanticArchiveError> {
    let campaign = scope.campaign_id();
    let tick = signed(scope.tick())?;
    let header = client.query_opt(
        "SELECT pin.tick_content_hash,pin.worker_contract_sha256,pin.knowledge_sha256,pin.grant_count,verified.valid IS TRUE \
         FROM babylon_meta.archive_tick_knowledge_v3 pin JOIN public.v_archive_tick_knowledge_v2 verified \
         USING(campaign_id,resolve_tick) WHERE pin.campaign_id=$1 AND pin.resolve_tick=$2",
        &[campaign.as_uuid(), &tick],
    ).map_err(|error| database("read authenticated frozen Archive knowledge identity", &error))?
        .ok_or(SemanticArchiveError::StoredPageMismatch)?;
    if Some(decode_digest(&header, 0)?) != scope.tick_content_hash()
        || decode_digest(&header, 1)? != crate::archive_worker_contract_sha256()
    {
        return Err(SemanticArchiveError::ReceiptConflict);
    }
    if !decode::<bool>(&header, 4)? {
        return Err(SemanticArchiveError::StoredPageMismatch);
    }
    let rows = client.query("SELECT member.subject_kind,member.subject_id,member.grant_key, \
        grant_row.granted_tick,grant_row.provenance_source_id,grant_row.provenance_locator \
        FROM babylon_meta.archive_knowledge_membership_scope_v3 member JOIN babylon_meta.archive_knowledge_grant_v1 grant_row \
        USING(campaign_id,subject_kind,subject_id,grant_key) WHERE member.campaign_id=$1 AND member.resolve_tick=$2 \
        ORDER BY member.subject_kind,member.subject_id,member.grant_key LIMIT 65536", &[campaign.as_uuid(),&tick])
        .map_err(|error|database("read frozen Archive membership projection",&error))?;
    let count = usize::try_from(decode::<i32>(&header, 3)?)
        .map_err(|_| SemanticArchiveError::StoredPageMismatch)?;
    if count > 65535 || count != rows.len() {
        return Err(SemanticArchiveError::StoredPageMismatch);
    }
    let grants = rows
        .iter()
        .map(|row| {
            let granted_tick = unsigned(decode(row, 3)?)?;
            if granted_tick > scope.tick() {
                return Err(SemanticArchiveError::StoredPageMismatch);
            }
            ArchiveKnowledgeGrant::try_new(
                ArchivePageRef::try_new(
                    decode_subject_kind(&decode::<String>(row, 0)?)?,
                    decode(row, 1)?,
                )?,
                decode(row, 2)?,
                granted_tick,
                ArchiveCitation::try_new(decode(row, 4)?, decode(row, 5)?)?,
            )
        })
        .collect::<Result<Vec<_>, _>>()?;
    let knowledge = ArchiveKnowledge::try_new(grants)?;
    if knowledge.sha256() != decode_digest(&header, 2)? {
        return Err(SemanticArchiveError::StoredPageMismatch);
    }
    Ok(knowledge)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn checkpoint_cadence_bounds_segments_and_rejects_future_bases() {
        assert_eq!(ARCHIVE_KNOWLEDGE_CHECKPOINT_PERIODS, 13);
        assert_eq!(checkpoint_for_tick(1, None), Ok(1));
        assert_eq!(checkpoint_for_tick(13, Some(1)), Ok(1));
        assert_eq!(checkpoint_for_tick(14, Some(1)), Ok(14));
        assert_eq!(checkpoint_for_tick(27, Some(14)), Ok(27));
        assert_eq!(checkpoint_for_tick(20, None), Ok(20));
        assert_eq!(
            checkpoint_for_tick(3, Some(4)),
            Err(SemanticArchiveError::StoredPageMismatch)
        );
    }
}
