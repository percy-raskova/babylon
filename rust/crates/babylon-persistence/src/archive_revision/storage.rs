//! Exact immutable publication persistence for the writer and confined reader.

use postgres::{GenericClient, Row};

use super::body_encoding::EncodedBody;
use super::body_encoding::Error;
use super::emission::ArchiveEmissionManifest;
use super::record::{CheckedRevision, GrantDependency, RevisionRecord};
use super::ArchiveReadScope;
use crate::archive;
use crate::identity::CampaignId;
use crate::production_projection::diagnostics::{Stage, Timing};
use crate::ArchiveDirtyBatch;
use crate::{ArchiveCitation, ArchivePageRef, SemanticArchiveError};
use std::collections::BTreeSet;
use uuid::Uuid;

pub(super) const COLUMNS: &str = "campaign_id, subject_kind, subject_id, effective_tick, \
    source_tick, source_content_hash, template_sha256, content_sha256, revision_sha256, \
    search_text, atom_count, grant_count, body_encoding, body_decoded_length, body_decoded_sha256, body_bytes";
const ATOM_COLUMNS: &str =
    "atom.campaign_id, atom.subject_kind, atom.subject_id, atom.signal_key, \
    atom.grant_key, atom.evidence_class, atom.value_kind, atom.value_text, atom.value_f64, \
    atom.value_u64, atom.value_bool, atom.provenance_source_id, atom.provenance_locator, \
    atom.valid_tick, atom.atom_id, membership.position";
const KEY_PREDICATE: &str = "campaign_id=$1 AND subject_kind=$2 AND subject_id=$3 \
    AND effective_tick=$4";

#[derive(Clone, Copy)]
pub(super) enum ReadAuthority {
    #[cfg(test)]
    Writer,
    Confined,
}

impl ReadAuthority {
    fn grant(self) -> &'static str {
        match self {
            #[cfg(test)]
            Self::Writer => "babylon_meta.archive_revision_grant_members_v3",
            Self::Confined => "public.v_archive_revision_grant_v2",
        }
    }
}

/// SQL-owned rows; decoding and emission authentication can happen after commit.
pub(super) struct CapturedRevision {
    row: Row,
    atoms: Vec<Row>,
    grants: Vec<Row>,
}

impl CapturedRevision {
    pub(super) fn body(&self) -> Result<EncodedBody, SemanticArchiveError> {
        let length = archive::decode::<i32>(&self.row, 13)?;
        let decoded_length =
            u32::try_from(length).map_err(|_| SemanticArchiveError::CollectionBound)?;
        if usize::try_from(decoded_length).map_err(|_| SemanticArchiveError::CollectionBound)?
            > super::body_encoding::MAX_BODY_BYTES
        {
            return Err(SemanticArchiveError::CollectionBound);
        }
        let stored: &[u8] = self
            .row
            .try_get(15)
            .map_err(|_| SemanticArchiveError::StoredPageMismatch)?;
        if stored.len() > super::body_encoding::MAX_ENCODED_BYTES {
            return Err(SemanticArchiveError::CollectionBound);
        }
        let mut bytes = Vec::new();
        bytes
            .try_reserve_exact(stored.len())
            .map_err(|_| SemanticArchiveError::CollectionBound)?;
        bytes.extend_from_slice(stored);
        Ok(EncodedBody {
            encoding: archive::decode(&self.row, 12)?,
            decoded_length,
            decoded_sha256: archive::decode_digest(&self.row, 14)?,
            bytes,
        })
    }

    // Existing bodies were fully admitted outside the write transaction. New
    // bodies were encoded from CheckedRevision. Recheck the exact captured bytes
    // and every scalar/member before publication; no decompression occurs here.
    fn matches_prepared_bytes(
        self,
        checked: &CheckedRevision,
    ) -> Result<bool, SemanticArchiveError> {
        let record = checked.record();
        if self.body()? != *checked.accepted_body()
            || archive::decode::<Uuid>(&self.row, 0)? != *record.source.campaign_id().as_uuid()
            || archive::decode::<String>(&self.row, 1)? != record.subject.kind().as_str()
            || archive::decode::<String>(&self.row, 2)? != record.subject.id()
            || unsigned(archive::decode(&self.row, 3)?)? != record.effective_tick
            || unsigned(archive::decode(&self.row, 4)?)? != record.source.tick()
            || Some(archive::decode_digest(&self.row, 5)?) != record.source.tick_content_hash()
            || archive::decode_digest(&self.row, 6)? != record.template_sha256
            || archive::decode_digest(&self.row, 7)? != record.content_sha256
            || archive::decode_digest(&self.row, 8)? != checked.digest()
            || archive::decode::<String>(&self.row, 9)? != record.search_text
            || usize::try_from(archive::decode::<i32>(&self.row, 10)?).ok()
                != Some(record.atoms.len())
            || usize::try_from(archive::decode::<i32>(&self.row, 11)?).ok()
                != Some(record.grants.len())
            || self.atoms.len() != record.atoms.len()
            || self.grants.len() != record.grants.len()
        {
            return Ok(false);
        }
        for (position, (row, expected)) in self.atoms.iter().zip(&record.atoms).enumerate() {
            if usize::try_from(archive::decode::<i32>(row, 15)?).ok() != Some(position)
                || archive::decode_stored_atom(row)? != *expected
            {
                return Ok(false);
            }
        }
        for (position, (row, expected)) in self.grants.iter().zip(&record.grants).enumerate() {
            if usize::try_from(archive::decode::<i32>(row, 6)?).ok() != Some(position)
                || archive::decode::<String>(row, 0)? != expected.subject.kind().as_str()
                || archive::decode::<String>(row, 1)? != expected.subject.id()
                || archive::decode::<String>(row, 2)? != expected.key
                || unsigned(archive::decode(row, 3)?)? != expected.granted_tick
                || archive::decode::<String>(row, 4)? != expected.citation.source_id()
                || archive::decode::<String>(row, 5)? != expected.citation.locator()
            {
                return Ok(false);
            }
        }
        Ok(true)
    }

    pub(super) fn admit(self) -> Result<RevisionRecord, SemanticArchiveError> {
        let (record, digest) = self.decode()?;
        if record.digest()? != digest {
            return Err(SemanticArchiveError::StoredPageMismatch);
        }
        Ok(record)
    }

    fn decode(self) -> Result<(RevisionRecord, [u8; 32]), SemanticArchiveError> {
        let campaign = CampaignId::from_uuid(archive::decode(&self.row, 0)?);
        let subject = ArchivePageRef::try_new(
            archive::decode_subject_kind(&archive::decode::<String>(&self.row, 1)?)?,
            archive::decode(&self.row, 2)?,
        )?;
        let body = self.body()?;
        let decoded = super::body_encoding::decode(
            body.encoding,
            body.decoded_length,
            body.decoded_sha256,
            &body.bytes,
        )
        .map_err(Error::into_semantic)?;
        if decoded.search_text != archive::decode::<String>(&self.row, 9)? {
            return Err(SemanticArchiveError::StoredPageMismatch);
        }
        let mut record = RevisionRecord {
            source: ArchiveReadScope::committed(
                campaign,
                unsigned(archive::decode(&self.row, 4)?)?,
                archive::decode_digest(&self.row, 5)?,
            )?,
            subject,
            effective_tick: unsigned(archive::decode(&self.row, 3)?)?,
            template_sha256: archive::decode_digest(&self.row, 6)?,
            content_sha256: archive::decode_digest(&self.row, 7)?,
            title: decoded.title,
            markdown: decoded.markdown,
            search_text: decoded.search_text,
            provenance_json: decoded.provenance_json,
            atoms: Vec::new(),
            grants: Vec::new(),
            emission: ArchiveEmissionManifest::decode(&decoded.emission_json)?,
        };
        let counts = (
            archive::decode::<i32>(&self.row, 10)?,
            archive::decode::<i32>(&self.row, 11)?,
        );
        if !(1..=513).contains(&counts.0) || !(1..=513).contains(&counts.1) {
            return Err(SemanticArchiveError::StoredPageMismatch);
        }
        decode_membership(&mut record, &self.atoms, &self.grants)?;
        if record.atoms.len()
            != usize::try_from(counts.0).map_err(|_| SemanticArchiveError::CollectionBound)?
            || record.grants.len()
                != usize::try_from(counts.1).map_err(|_| SemanticArchiveError::CollectionBound)?
        {
            return Err(SemanticArchiveError::StoredPageMismatch);
        }
        Ok((record, archive::decode_digest(&self.row, 8)?))
    }
}

pub(super) fn decode_record(
    client: &mut impl GenericClient,
    row: &Row,
    authority: ReadAuthority,
) -> Result<RevisionRecord, SemanticArchiveError> {
    capture_record(client, row.clone(), authority)?.admit()
}

pub(super) fn capture_record(
    client: &mut impl GenericClient,
    row: Row,
    authority: ReadAuthority,
) -> Result<CapturedRevision, SemanticArchiveError> {
    let campaign = CampaignId::from_uuid(archive::decode(&row, 0)?);
    let subject = ArchivePageRef::try_new(
        archive::decode_subject_kind(&archive::decode::<String>(&row, 1)?)?,
        archive::decode(&row, 2)?,
    )?;
    let tick = archive::decode::<i64>(&row, 3)?;
    unsigned(tick)?;
    let (atoms, grants) = capture_membership(client, campaign, &subject, tick, authority)?;
    Ok(CapturedRevision { row, atoms, grants })
}

#[cfg(test)]
thread_local! {
    static CAPTURE_QUERY_COUNT: std::cell::Cell<usize> = const { std::cell::Cell::new(0) };
}

// Count actual client SQL invocations in this capture path, not elapsed guesses.
#[cfg(test)]
pub(super) fn record_capture_query() {
    CAPTURE_QUERY_COUNT.with(|count| count.set(count.get() + 1));
}

#[cfg(test)]
pub(super) fn reset_capture_queries() -> usize {
    CAPTURE_QUERY_COUNT.with(|count| count.replace(0))
}

fn capture_membership(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    subject: &ArchivePageRef,
    tick: i64,
    authority: ReadAuthority,
) -> Result<(Vec<Row>, Vec<Row>), SemanticArchiveError> {
    let atom_query = match authority {
        #[cfg(test)]
        ReadAuthority::Writer => format!("SELECT {ATOM_COLUMNS} FROM babylon_meta.archive_revision_atom_members_v3 membership \
            JOIN babylon_meta.archive_atom_witness_v1 atom USING(atom_id) WHERE membership.campaign_id=$1 \
            AND membership.subject_kind=$2 AND membership.subject_id=$3 AND membership.effective_tick=$4 \
            ORDER BY membership.position LIMIT 514"),
        ReadAuthority::Confined => format!("SELECT {} FROM public.v_archive_revision_atom_v2 atom \
            WHERE {KEY_PREDICATE} ORDER BY position LIMIT 514", ATOM_COLUMNS.replace("membership.position", "atom.position")),
    };
    let params: &[&(dyn postgres::types::ToSql + Sync)] = &[
        campaign.as_uuid(),
        &subject.kind().as_str(),
        &subject.id(),
        &tick,
    ];
    #[cfg(test)]
    record_capture_query();
    let atoms = client
        .query(&atom_query, params)
        .map_err(|error| archive::database("read retained Archive membership", &error))?;
    #[cfg(test)]
    record_capture_query();
    let grants = client
        .query(
            &format!(
                "SELECT grant_subject_kind, grant_subject_id, grant_key, \
        granted_tick, provenance_source_id, provenance_locator, position FROM {} \
        WHERE {KEY_PREDICATE} ORDER BY position LIMIT 514",
                authority.grant()
            ),
            params,
        )
        .map_err(|error| archive::database("read retained Archive grant dependencies", &error))?;
    Ok((atoms, grants))
}

fn decode_membership(
    record: &mut RevisionRecord,
    atoms: &[Row],
    grants: &[Row],
) -> Result<(), SemanticArchiveError> {
    for (position, row) in atoms.iter().enumerate() {
        if archive::decode::<i32>(row, 15)?
            != i32::try_from(position).map_err(|_| SemanticArchiveError::CollectionBound)?
        {
            return Err(SemanticArchiveError::StoredPageMismatch);
        }
        record.atoms.push(archive::decode_stored_atom(row)?);
    }
    for (position, row) in grants.iter().enumerate() {
        if archive::decode::<i32>(row, 6)?
            != i32::try_from(position).map_err(|_| SemanticArchiveError::CollectionBound)?
        {
            return Err(SemanticArchiveError::StoredPageMismatch);
        }
        record.grants.push(GrantDependency {
            subject: ArchivePageRef::try_new(
                archive::decode_subject_kind(&archive::decode::<String>(row, 0)?)?,
                archive::decode(row, 1)?,
            )?,
            key: archive::decode(row, 2)?,
            granted_tick: unsigned(archive::decode(row, 3)?)?,
            citation: ArchiveCitation::try_new(archive::decode(row, 4)?, archive::decode(row, 5)?)?,
        });
    }
    Ok(())
}

/// Insert one bounded publication and authenticate every exact conflict before
/// its caller can claim the receipt. The returned flags preserve input order.
pub(super) fn insert_batch(
    client: &mut impl GenericClient,
    checked: &[&CheckedRevision],
) -> Result<Vec<bool>, SemanticArchiveError> {
    let Some(first) = checked.first() else {
        return Ok(Vec::new());
    };
    if checked.len() > ArchiveDirtyBatch::MAX_PAGES {
        return Err(SemanticArchiveError::CollectionBound);
    }
    let mut subjects = BTreeSet::new();
    for revision in checked {
        if revision.record().source != first.record().source {
            return Err(SemanticArchiveError::ReceiptMismatch);
        }
        if !subjects.insert(&revision.record().subject) {
            return Err(SemanticArchiveError::DuplicateKey);
        }
    }
    let inserted = checked
        .iter()
        .map(|revision| insert_row(client, revision))
        .collect::<Result<Vec<_>, _>>()?;
    reconcile_batch(client, checked)?;
    Ok(inserted)
}

fn insert_row(
    client: &mut impl GenericClient,
    checked: &CheckedRevision,
) -> Result<bool, SemanticArchiveError> {
    let record = checked.record();
    let digest = checked.digest();
    let campaign = record.source.campaign_id();
    let effective = signed(record.effective_tick)?;
    let source = signed(record.source.tick())?;
    let source_hash = record
        .source
        .tick_content_hash()
        .ok_or(SemanticArchiveError::InvalidVerifiedTick)?;
    let atoms =
        i32::try_from(record.atoms.len()).map_err(|_| SemanticArchiveError::CollectionBound)?;
    let grants =
        i32::try_from(record.grants.len()).map_err(|_| SemanticArchiveError::CollectionBound)?;
    let body = checked.body();
    let body_length =
        i32::try_from(body.decoded_length).map_err(|_| SemanticArchiveError::CollectionBound)?;
    let atom_ids = record
        .atoms
        .iter()
        .map(|atom| atom.atom_id().to_vec())
        .collect::<Vec<_>>();
    let grant_kinds = record
        .grants
        .iter()
        .map(|grant| grant.subject.kind().as_str())
        .collect::<Vec<_>>();
    let grant_ids = record
        .grants
        .iter()
        .map(|grant| grant.subject.id())
        .collect::<Vec<_>>();
    let grant_keys = record
        .grants
        .iter()
        .map(|grant| grant.key.as_str())
        .collect::<Vec<_>>();
    let grant_ticks = record
        .grants
        .iter()
        .map(|grant| signed(grant.granted_tick))
        .collect::<Result<Vec<_>, _>>()?;
    let citations = record
        .grants
        .iter()
        .map(|grant| &grant.citation)
        .collect::<Vec<_>>();
    let grant_provenance_refs = {
        let _timing = Timing::start(Stage::ArchiveProvenanceResolution, record.source.tick());
        crate::archive_provenance::resolve_ordered(client, campaign, &citations)?
    };
    let insertion_timing = Timing::start(Stage::ArchiveRevisionInsert, record.source.tick());
    let inserted = client
        .execute(
            &format!(
                "INSERT INTO babylon_meta.archive_page_revision_v2 ({COLUMNS},atom_ids, \
        grant_subject_kinds,grant_subject_ids,grant_keys,grant_ticks,grant_provenance_refs) \
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22) \
        ON CONFLICT (campaign_id,subject_kind,subject_id,effective_tick) DO NOTHING"
            ),
            &[
                campaign.as_uuid(),
                &record.subject.kind().as_str(),
                &record.subject.id(),
                &effective,
                &source,
                &&source_hash[..],
                &&record.template_sha256[..],
                &&record.content_sha256[..],
                &&digest[..],
                &record.search_text,
                &atoms,
                &grants,
                &body.encoding,
                &body_length,
                &&body.decoded_sha256[..],
                &body.bytes,
                &atom_ids,
                &grant_kinds,
                &grant_ids,
                &grant_keys,
                &grant_ticks,
                &grant_provenance_refs,
            ],
        )
        .map_err(|error| archive::database("insert immutable Archive publication", &error))?
        == 1;
    drop(insertion_timing);
    Ok(inserted)
}

fn reconcile_batch(
    client: &mut impl GenericClient,
    checked: &[&CheckedRevision],
) -> Result<(), SemanticArchiveError> {
    let first = checked
        .first()
        .ok_or(SemanticArchiveError::CollectionBound)?;
    let record = first.record();
    let campaign = record.source.campaign_id();
    let effective = signed(record.effective_tick)?;
    let kinds = checked
        .iter()
        .map(|revision| revision.record().subject.kind().as_str())
        .collect::<Vec<_>>();
    let ids = checked
        .iter()
        .map(|revision| revision.record().subject.id())
        .collect::<Vec<_>>();
    let params: &[&(dyn postgres::types::ToSql + Sync)] =
        &[campaign.as_uuid(), &kinds, &ids, &effective];
    // Arrays replace association FKs. Revalidate authoritative references in
    // the same publication transaction, including ON CONFLICT retries, before
    // reconciling every ordered member and exact body against its prepared page.
    // All checked sources are equal: the common tick is an exact key, never an
    // as-of fallback. Ordinals must be unique, complete and in caller order.
    // Keep the exact keys inside each correlated visibility probe. A second
    // result is a duplicate witness; the cardinality and ordinal checks refuse
    // it without hiding corruption behind a one-row limit.
    let visibility_timing = Timing::start(Stage::ArchiveReferenceVisibility, record.source.tick());
    #[cfg(test)]
    record_capture_query();
    let visible = client
        .query(
            "SELECT wanted.ordinality \
        FROM unnest($2::text[], $3::text[]) WITH ORDINALITY \
        AS wanted(subject_kind,subject_id,ordinality) \
        JOIN LATERAL (SELECT 1 FROM public.v_archive_revision_known_v2 revision \
        WHERE revision.campaign_id=$1 AND revision.subject_kind=wanted.subject_kind \
        AND revision.subject_id=wanted.subject_id AND revision.effective_tick=$4 \
        LIMIT 2) visible ON true \
        ORDER BY wanted.ordinality",
            params,
        )
        .map_err(|error| {
            archive::database("validate immutable Archive batch references", &error)
        })?;
    drop(visibility_timing);
    if visible.len() != checked.len() {
        return Err(SemanticArchiveError::ReceiptConflict);
    }
    for (index, row) in visible.iter().enumerate() {
        if comparison_position(row, 0, checked.len())? != index {
            return Err(SemanticArchiveError::ReceiptConflict);
        }
    }
    let _timing = Timing::start(Stage::ArchiveRevisionReconciliation, record.source.tick());
    #[cfg(test)]
    record_capture_query();
    let rows = client
        .query(
            &format!(
                "SELECT captured.*, wanted.ordinality \
        FROM unnest($2::text[], $3::text[]) WITH ORDINALITY \
        AS wanted(subject_kind,subject_id,ordinality) \
        JOIN LATERAL (SELECT {COLUMNS} FROM babylon_meta.archive_page_revision_v2 revision \
        WHERE revision.campaign_id=$1 AND revision.subject_kind=wanted.subject_kind \
        AND revision.subject_id=wanted.subject_id AND revision.effective_tick=$4) captured ON true \
        ORDER BY wanted.ordinality"
            ),
            params,
        )
        .map_err(|error| archive::database("reconcile checked Archive batch", &error))?;
    if rows.len() != checked.len() {
        return Err(SemanticArchiveError::ReceiptConflict);
    }
    let mut captured = Vec::with_capacity(rows.len());
    for (index, row) in rows.into_iter().enumerate() {
        if comparison_position(&row, 16, checked.len())? != index
            || archive::decode::<Uuid>(&row, 0)? != *campaign.as_uuid()
            || archive::decode::<String>(&row, 1)? != kinds[index]
            || archive::decode::<String>(&row, 2)? != ids[index]
            || archive::decode::<i64>(&row, 3)? != effective
        {
            return Err(SemanticArchiveError::ReceiptConflict);
        }
        captured.push((
            index,
            CapturedRevision {
                row,
                atoms: Vec::new(),
                grants: Vec::new(),
            },
        ));
    }
    capture_batch_memberships(client, campaign, &mut captured)?;
    for (index, revision) in captured {
        if !revision.matches_prepared_bytes(checked[index])? {
            return Err(SemanticArchiveError::ReceiptConflict);
        }
    }
    Ok(())
}

pub(super) fn unsigned(value: i64) -> Result<u64, SemanticArchiveError> {
    u64::try_from(value).map_err(|_| SemanticArchiveError::StoredPageMismatch)
}

pub(super) fn signed(value: u64) -> Result<i64, SemanticArchiveError> {
    i64::try_from(value).map_err(|_| SemanticArchiveError::InvalidVerifiedTick)
}

/// Capture all exact retained comparison witnesses in one coherent snapshot.
/// A lateral limit retains the existing 514-row overflow witness per membership;
/// no page budget truncates authentication of a desired subject outside the head.
pub(super) fn capture_comparison_records(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    through: u64,
    subjects: &[ArchivePageRef],
) -> Result<Vec<Option<CapturedRevision>>, SemanticArchiveError> {
    if subjects.is_empty() {
        return Ok(Vec::new());
    }
    let kinds = subjects
        .iter()
        .map(|s| s.kind().as_str().to_owned())
        .collect::<Vec<_>>();
    let ids = subjects
        .iter()
        .map(|s| s.id().to_owned())
        .collect::<Vec<_>>();
    #[cfg(test)]
    record_capture_query();
    let rows = client
        .query(
            &format!(
                "SELECT captured.*, wanted.ordinality \
        FROM unnest($2::text[], $3::text[]) WITH ORDINALITY \
        AS wanted(subject_kind,subject_id,ordinality) \
        JOIN LATERAL (SELECT {COLUMNS} FROM babylon_meta.archive_page_revision_v2 revision \
        WHERE revision.campaign_id=$1 AND revision.subject_kind=wanted.subject_kind \
        AND revision.subject_id=wanted.subject_id AND revision.effective_tick<=$4 \
        ORDER BY revision.effective_tick DESC LIMIT 1) captured ON true \
        ORDER BY wanted.ordinality"
            ),
            &[campaign.as_uuid(), &kinds, &ids, &signed(through)?],
        )
        .map_err(|error| {
            archive::database("capture exact producer comparison revisions", &error)
        })?;
    let mut captures = Vec::with_capacity(rows.len());
    let mut positions = BTreeSet::new();
    for row in rows {
        let position = comparison_position(&row, 16, subjects.len())?;
        let subject = ArchivePageRef::try_new(
            archive::decode_subject_kind(&archive::decode::<String>(&row, 1)?)?,
            archive::decode(&row, 2)?,
        )?;
        if archive::decode::<Uuid>(&row, 0)? != *campaign.as_uuid()
            || subject != subjects[position]
            || unsigned(archive::decode(&row, 3)?)? > through
            || !positions.insert(position)
        {
            return Err(SemanticArchiveError::StoredPageMismatch);
        }
        captures.push((
            position,
            CapturedRevision {
                row,
                atoms: Vec::new(),
                grants: Vec::new(),
            },
        ));
    }
    capture_batch_memberships(client, campaign, &mut captures)?;
    let mut result = (0..subjects.len()).map(|_| None).collect::<Vec<_>>();
    for (position, captured) in captures {
        result[position] = Some(captured);
    }
    Ok(result)
}

fn comparison_position(
    row: &Row,
    column: usize,
    length: usize,
) -> Result<usize, SemanticArchiveError> {
    let index = archive::decode::<i64>(row, column)?
        .checked_sub(1)
        .and_then(|value| usize::try_from(value).ok())
        .filter(|value| *value < length)
        .ok_or(SemanticArchiveError::StoredPageMismatch)?;
    Ok(index)
}

fn capture_batch_memberships(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    captures: &mut [(usize, CapturedRevision)],
) -> Result<(), SemanticArchiveError> {
    if captures.is_empty() {
        return Ok(());
    }
    let kinds = captures
        .iter()
        .map(|(_, c)| archive::decode::<String>(&c.row, 1))
        .collect::<Result<Vec<_>, _>>()?;
    let ids = captures
        .iter()
        .map(|(_, c)| archive::decode::<String>(&c.row, 2))
        .collect::<Result<Vec<_>, _>>()?;
    let ticks = captures
        .iter()
        .map(|(_, c)| archive::decode::<i64>(&c.row, 3))
        .collect::<Result<Vec<_>, _>>()?;
    let params: &[&(dyn postgres::types::ToSql + Sync)] =
        &[campaign.as_uuid(), &kinds, &ids, &ticks];
    #[cfg(test)]
    record_capture_query();
    let atoms = client.query(&format!("SELECT captured.*, wanted.ordinality \
        FROM unnest($2::text[], $3::text[], $4::bigint[]) WITH ORDINALITY \
        AS wanted(subject_kind,subject_id,effective_tick,ordinality) \
        JOIN LATERAL (SELECT {ATOM_COLUMNS} FROM babylon_meta.archive_revision_atom_members_v3 membership \
        JOIN babylon_meta.archive_atom_witness_v1 atom USING(atom_id) \
        WHERE membership.campaign_id=$1 AND membership.subject_kind=wanted.subject_kind \
        AND membership.subject_id=wanted.subject_id AND membership.effective_tick=wanted.effective_tick \
        ORDER BY membership.position LIMIT 514) captured ON true \
        ORDER BY wanted.ordinality,captured.position"), params)
        .map_err(|error| archive::database("capture exact Archive atom memberships", &error))?;
    for row in atoms {
        let index = comparison_position(&row, 16, captures.len())?;
        captures[index].1.atoms.push(row);
    }
    #[cfg(test)]
    record_capture_query();
    let grants = client.query("SELECT captured.*, wanted.ordinality \
        FROM unnest($2::text[], $3::text[], $4::bigint[]) WITH ORDINALITY \
        AS wanted(subject_kind,subject_id,effective_tick,ordinality) \
        JOIN LATERAL (SELECT grant_subject_kind,grant_subject_id,grant_key,granted_tick, \
        provenance_source_id,provenance_locator,position \
        FROM babylon_meta.archive_revision_grant_members_v3 membership \
        WHERE membership.campaign_id=$1 AND membership.subject_kind=wanted.subject_kind \
        AND membership.subject_id=wanted.subject_id AND membership.effective_tick=wanted.effective_tick \
        ORDER BY position LIMIT 514) captured ON true \
        ORDER BY wanted.ordinality,captured.position", params)
        .map_err(|error| archive::database("capture exact Archive grant memberships", &error))?;
    for row in grants {
        let index = comparison_position(&row, 7, captures.len())?;
        captures[index].1.grants.push(row);
    }
    Ok(())
}
