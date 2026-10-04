//! Exact immutable publication persistence for the writer and confined reader.

use postgres::{GenericClient, Row};

use super::record::{CheckedRevision, GrantDependency, RevisionRecord};
use super::ArchiveReadScope;
use crate::archive::{database, decode, decode_digest, decode_stored_atom, decode_subject_kind};
use crate::{identity::CampaignId, ArchiveCitation, ArchivePageRef, SemanticArchiveError};

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
    Writer,
    Confined,
}

impl ReadAuthority {
    fn grant(self) -> &'static str {
        match self {
            Self::Writer => "babylon_meta.archive_revision_grant_v2",
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
    pub(super) fn body(&self) -> Result<super::body_encoding::EncodedBody, SemanticArchiveError> {
        let length = decode::<i32>(&self.row, 13)?;
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
        Ok(super::body_encoding::EncodedBody {
            encoding: decode(&self.row, 12)?,
            decoded_length,
            decoded_sha256: decode_digest(&self.row, 14)?,
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
            || decode::<uuid::Uuid>(&self.row, 0)? != *record.source.campaign_id().as_uuid()
            || decode::<String>(&self.row, 1)? != record.subject.kind().as_str()
            || decode::<String>(&self.row, 2)? != record.subject.id()
            || unsigned(decode(&self.row, 3)?)? != record.effective_tick
            || unsigned(decode(&self.row, 4)?)? != record.source.tick()
            || Some(decode_digest(&self.row, 5)?) != record.source.tick_content_hash()
            || decode_digest(&self.row, 6)? != record.template_sha256
            || decode_digest(&self.row, 7)? != record.content_sha256
            || decode_digest(&self.row, 8)? != checked.digest()
            || decode::<String>(&self.row, 9)? != record.search_text
            || usize::try_from(decode::<i32>(&self.row, 10)?).ok() != Some(record.atoms.len())
            || usize::try_from(decode::<i32>(&self.row, 11)?).ok() != Some(record.grants.len())
            || self.atoms.len() != record.atoms.len()
            || self.grants.len() != record.grants.len()
        {
            return Ok(false);
        }
        for (position, (row, expected)) in self.atoms.iter().zip(&record.atoms).enumerate() {
            if usize::try_from(decode::<i32>(row, 15)?).ok() != Some(position)
                || decode_stored_atom(row)? != *expected
            {
                return Ok(false);
            }
        }
        for (position, (row, expected)) in self.grants.iter().zip(&record.grants).enumerate() {
            if usize::try_from(decode::<i32>(row, 6)?).ok() != Some(position)
                || decode::<String>(row, 0)? != expected.subject.kind().as_str()
                || decode::<String>(row, 1)? != expected.subject.id()
                || decode::<String>(row, 2)? != expected.key
                || unsigned(decode(row, 3)?)? != expected.granted_tick
                || decode::<String>(row, 4)? != expected.citation.source_id()
                || decode::<String>(row, 5)? != expected.citation.locator()
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
        let campaign = CampaignId::from_uuid(decode(&self.row, 0)?);
        let subject = ArchivePageRef::try_new(
            decode_subject_kind(&decode::<String>(&self.row, 1)?)?,
            decode(&self.row, 2)?,
        )?;
        let body = self.body()?;
        let decoded = super::body_encoding::decode(
            body.encoding,
            body.decoded_length,
            body.decoded_sha256,
            &body.bytes,
        )
        .map_err(super::body_encoding::Error::into_semantic)?;
        if decoded.search_text != decode::<String>(&self.row, 9)? {
            return Err(SemanticArchiveError::StoredPageMismatch);
        }
        let mut record = RevisionRecord {
            source: ArchiveReadScope::committed(
                campaign,
                unsigned(decode(&self.row, 4)?)?,
                decode_digest(&self.row, 5)?,
            )?,
            subject,
            effective_tick: unsigned(decode(&self.row, 3)?)?,
            template_sha256: decode_digest(&self.row, 6)?,
            content_sha256: decode_digest(&self.row, 7)?,
            title: decoded.title,
            markdown: decoded.markdown,
            search_text: decoded.search_text,
            provenance_json: decoded.provenance_json,
            atoms: Vec::new(),
            grants: Vec::new(),
            emission: super::emission::ArchiveEmissionManifest::decode(&decoded.emission_json)?,
        };
        let counts = (decode::<i32>(&self.row, 10)?, decode::<i32>(&self.row, 11)?);
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
        Ok((record, decode_digest(&self.row, 8)?))
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
    let campaign = CampaignId::from_uuid(decode(&row, 0)?);
    let subject = ArchivePageRef::try_new(
        decode_subject_kind(&decode::<String>(&row, 1)?)?,
        decode(&row, 2)?,
    )?;
    let tick = decode::<i64>(&row, 3)?;
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
        ReadAuthority::Writer => format!("SELECT {ATOM_COLUMNS} FROM babylon_meta.archive_revision_atom_v2 membership \
            JOIN babylon_meta.archive_atom_v1 atom USING(atom_id) WHERE membership.campaign_id=$1 \
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
        .map_err(|error| database("read retained Archive membership", &error))?;
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
        .map_err(|error| database("read retained Archive grant dependencies", &error))?;
    Ok((atoms, grants))
}

fn decode_membership(
    record: &mut RevisionRecord,
    atoms: &[Row],
    grants: &[Row],
) -> Result<(), SemanticArchiveError> {
    for (position, row) in atoms.iter().enumerate() {
        if decode::<i32>(row, 15)?
            != i32::try_from(position).map_err(|_| SemanticArchiveError::CollectionBound)?
        {
            return Err(SemanticArchiveError::StoredPageMismatch);
        }
        record.atoms.push(decode_stored_atom(row)?);
    }
    for (position, row) in grants.iter().enumerate() {
        if decode::<i32>(row, 6)?
            != i32::try_from(position).map_err(|_| SemanticArchiveError::CollectionBound)?
        {
            return Err(SemanticArchiveError::StoredPageMismatch);
        }
        record.grants.push(GrantDependency {
            subject: ArchivePageRef::try_new(
                decode_subject_kind(&decode::<String>(row, 0)?)?,
                decode(row, 1)?,
            )?,
            key: decode(row, 2)?,
            granted_tick: unsigned(decode(row, 3)?)?,
            citation: ArchiveCitation::try_new(decode(row, 4)?, decode(row, 5)?)?,
        });
    }
    Ok(())
}

pub(super) fn insert(
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
    let inserted = client
        .execute(
            &format!(
                "INSERT INTO babylon_meta.archive_page_revision_v2 ({COLUMNS}) \
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16) \
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
            ],
        )
        .map_err(|error| database("insert immutable Archive publication", &error))?
        == 1;
    if inserted {
        insert_membership(client, record)?;
    }
    let row = client
        .query_opt(
            &format!(
                "SELECT {COLUMNS} FROM babylon_meta.archive_page_revision_v2 WHERE {KEY_PREDICATE}"
            ),
            &[
                campaign.as_uuid(),
                &record.subject.kind().as_str(),
                &record.subject.id(),
                &effective,
            ],
        )
        .map_err(|error| database("reconcile checked Archive revision", &error))?
        .ok_or(SemanticArchiveError::ReceiptConflict)?;
    if !capture_record(client, row, ReadAuthority::Writer)?.matches_prepared_bytes(checked)? {
        return Err(SemanticArchiveError::ReceiptConflict);
    }
    Ok(inserted)
}

fn insert_membership(
    client: &mut impl GenericClient,
    record: &RevisionRecord,
) -> Result<(), SemanticArchiveError> {
    let campaign = record.source.campaign_id();
    let effective = signed(record.effective_tick)?;
    for (position, atom) in record.atoms.iter().enumerate() {
        let position =
            i32::try_from(position).map_err(|_| SemanticArchiveError::CollectionBound)?;
        client
            .execute(
                "INSERT INTO babylon_meta.archive_revision_atom_v2 \
            (campaign_id,subject_kind,subject_id,effective_tick,position,atom_id) \
            VALUES ($1,$2,$3,$4,$5,$6)",
                &[
                    campaign.as_uuid(),
                    &record.subject.kind().as_str(),
                    &record.subject.id(),
                    &effective,
                    &position,
                    &&atom.atom_id()[..],
                ],
            )
            .map_err(|error| database("insert immutable Archive membership", &error))?;
    }
    for (position, grant) in record.grants.iter().enumerate() {
        let position =
            i32::try_from(position).map_err(|_| SemanticArchiveError::CollectionBound)?;
        let granted = signed(grant.granted_tick)?;
        client
            .execute(
                "INSERT INTO babylon_meta.archive_revision_grant_v2 \
            (campaign_id,subject_kind,subject_id,effective_tick,position,grant_subject_kind, \
            grant_subject_id,grant_key,granted_tick,provenance_source_id,provenance_locator) \
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)",
                &[
                    campaign.as_uuid(),
                    &record.subject.kind().as_str(),
                    &record.subject.id(),
                    &effective,
                    &position,
                    &grant.subject.kind().as_str(),
                    &grant.subject.id(),
                    &grant.key,
                    &granted,
                    &grant.citation.source_id(),
                    &grant.citation.locator(),
                ],
            )
            .map_err(|error| database("insert immutable Archive grant dependency", &error))?;
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
        .map_err(|error| database("capture exact producer comparison revisions", &error))?;
    let mut captures = Vec::with_capacity(rows.len());
    let mut positions = std::collections::BTreeSet::new();
    for row in rows {
        let position = comparison_position(&row, 16, subjects.len())?;
        let subject = ArchivePageRef::try_new(
            decode_subject_kind(&decode::<String>(&row, 1)?)?,
            decode(&row, 2)?,
        )?;
        if decode::<uuid::Uuid>(&row, 0)? != *campaign.as_uuid()
            || subject != subjects[position]
            || unsigned(decode(&row, 3)?)? > through
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
    capture_comparison_memberships(client, campaign, &mut captures)?;
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
    let index = decode::<i64>(row, column)?
        .checked_sub(1)
        .and_then(|value| usize::try_from(value).ok())
        .filter(|value| *value < length)
        .ok_or(SemanticArchiveError::StoredPageMismatch)?;
    Ok(index)
}

fn capture_comparison_memberships(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    captures: &mut [(usize, CapturedRevision)],
) -> Result<(), SemanticArchiveError> {
    if captures.is_empty() {
        return Ok(());
    }
    let kinds = captures
        .iter()
        .map(|(_, c)| decode::<String>(&c.row, 1))
        .collect::<Result<Vec<_>, _>>()?;
    let ids = captures
        .iter()
        .map(|(_, c)| decode::<String>(&c.row, 2))
        .collect::<Result<Vec<_>, _>>()?;
    let ticks = captures
        .iter()
        .map(|(_, c)| decode::<i64>(&c.row, 3))
        .collect::<Result<Vec<_>, _>>()?;
    let params: &[&(dyn postgres::types::ToSql + Sync)] =
        &[campaign.as_uuid(), &kinds, &ids, &ticks];
    #[cfg(test)]
    record_capture_query();
    let atoms = client.query(&format!("SELECT captured.*, wanted.ordinality \
        FROM unnest($2::text[], $3::text[], $4::bigint[]) WITH ORDINALITY \
        AS wanted(subject_kind,subject_id,effective_tick,ordinality) \
        JOIN LATERAL (SELECT {ATOM_COLUMNS} FROM babylon_meta.archive_revision_atom_v2 membership \
        JOIN babylon_meta.archive_atom_v1 atom USING(atom_id) \
        WHERE membership.campaign_id=$1 AND membership.subject_kind=wanted.subject_kind \
        AND membership.subject_id=wanted.subject_id AND membership.effective_tick=wanted.effective_tick \
        ORDER BY membership.position LIMIT 514) captured ON true \
        ORDER BY wanted.ordinality,captured.position"), params)
        .map_err(|error| database("capture producer comparison atom memberships", &error))?;
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
        FROM babylon_meta.archive_revision_grant_v2 membership \
        WHERE membership.campaign_id=$1 AND membership.subject_kind=wanted.subject_kind \
        AND membership.subject_id=wanted.subject_id AND membership.effective_tick=wanted.effective_tick \
        ORDER BY position LIMIT 514) captured ON true \
        ORDER BY wanted.ordinality,captured.position", params)
        .map_err(|error| database("capture producer comparison grant memberships", &error))?;
    for row in grants {
        let index = comparison_position(&row, 7, captures.len())?;
        captures[index].1.grants.push(row);
    }
    Ok(())
}
