//! Lossless campaign-owned territory definitions. The caller holds the campaign
//! writer lock; opening seeds precede history and tick markers are inserted last.
use crate::identity::CampaignId;
use crate::runtime::{
    bytea_copy_text, finish_csv_copy, write_bsl_csv_row, write_csv_row, RustPersistenceRuntimeError,
};
use crate::stored_tick::{decode_bsl_value, decode_stable_key};
use babylon_bsl::identity_codec::StableBslValue;
use babylon_graph::stable_state::MAX_STABLE_GRAPH_NODES;
use babylon_kernel::content_digest::sha256_of;
use babylon_tick::material_state::TerritoryStateRow;
use postgres::{types::FromSqlOwned, GenericClient, Row};
use std::collections::BTreeMap;

/// Exact territory definition admission failures.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    /// A period is negative or a tick writer attempts opening period zero.
    InvalidTick,
    /// Current territory identities are duplicated or not canonically ordered.
    RowOrder,
    /// A count or identity cannot be represented by the current SQL type.
    Bounds,
    /// Stored definition identifiers are not contiguous from zero.
    DefinitionGap,
    /// A definition originates after the period being written or read.
    DefinitionFuture,
    /// A prior definition has no durable marker at its origin period.
    DefinitionUnmarked,
    /// Stored fields do not equal the declared definition field count.
    DefinitionCount,
    /// Stored field positions or names are not strictly ordered.
    FieldOrder,
    /// Reconstructed canonical bytes do not match their recorded digest.
    DefinitionDigest,
    /// Equal digest buckets contain unequal canonical bytes.
    HashCollision,
    /// More than one stored definition contains the same canonical bytes.
    DuplicateDefinition,
}
fn refused(error: Error) -> RustPersistenceRuntimeError {
    RustPersistenceRuntimeError::TerritoryStorage(error)
}
fn column<T: FromSqlOwned>(row: &Row, index: usize) -> Result<T, RustPersistenceRuntimeError> {
    row.try_get(index).map_err(|error| {
        RustPersistenceRuntimeError::postgres("decode territory definition", &error)
    })
}
fn checked_id(value: usize) -> Result<i64, RustPersistenceRuntimeError> {
    i64::try_from(value).map_err(|_| refused(Error::Bounds))
}
struct Definition {
    id: i64,
    key: Vec<u8>,
    count: usize,
    digest: [u8; 32],
    fields: Vec<(String, StableBslValue)>,
}
impl Definition {
    fn canonical(&self) -> Result<Vec<u8>, RustPersistenceRuntimeError> {
        if self.fields.len() != self.count {
            return Err(refused(Error::DefinitionCount));
        }
        let row = TerritoryStateRow::try_new(decode_stable_key(&self.key)?, self.fields.clone())
            .map_err(|_| refused(Error::FieldOrder))?;
        if sha256_of(row.canonical_bytes()) != self.digest {
            return Err(refused(Error::DefinitionDigest));
        }
        Ok(row.canonical_bytes().to_vec())
    }
}
fn headers(
    rows: Vec<Row>,
    tick: i64,
) -> Result<BTreeMap<i64, Definition>, RustPersistenceRuntimeError> {
    let mut result = BTreeMap::new();
    for row in rows {
        let id: i64 = column(&row, 0)?;
        let first: i64 = column(&row, 1)?;
        let count: i32 = column(&row, 3)?;
        let digest: Vec<u8> = column(&row, 4)?;
        let marked: bool = column(&row, 5)?;
        if id < 0 || first < 0 || count < 0 {
            return Err(refused(Error::Bounds));
        }
        if first > tick {
            return Err(refused(Error::DefinitionFuture));
        }
        if first > 0 && first < tick && !marked {
            return Err(refused(Error::DefinitionUnmarked));
        }
        let definition = Definition {
            id,
            key: column(&row, 2)?,
            count: usize::try_from(count).map_err(|_| refused(Error::Bounds))?,
            digest: digest
                .try_into()
                .map_err(|_| refused(Error::DefinitionDigest))?,
            fields: Vec::new(),
        };
        if result.insert(id, definition).is_some() {
            return Err(refused(Error::DuplicateDefinition));
        }
    }
    Ok(result)
}
fn load_fields(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    definitions: &mut BTreeMap<i64, Definition>,
) -> Result<(), RustPersistenceRuntimeError> {
    let ids: Vec<_> = definitions.keys().copied().collect();
    if ids.is_empty() {
        return Ok(());
    }
    let rows = client.query(
        "SELECT definition_id, position, field_name, value_tag, int_value, currency_value::text, real_bits, ratio_bits, ratio_min_bits, ratio_max_bits, bool_value, enum_type, enum_member, stable_key FROM babylon_state.territory_definition_field_v1 WHERE campaign_id=$1::uuid AND definition_id=ANY($2::bigint[]) ORDER BY definition_id,position",
        &[campaign.as_uuid(), &ids],
    ).map_err(|error| RustPersistenceRuntimeError::postgres("read territory definition fields", &error))?;
    for row in rows {
        let id: i64 = column(&row, 0)?;
        let position: i32 = column(&row, 1)?;
        let name: String = column(&row, 2)?;
        let target = definitions
            .get_mut(&id)
            .ok_or_else(|| refused(Error::DefinitionCount))?;
        if position < 0
            || usize::try_from(position).ok() != Some(target.fields.len())
            || target.fields.len() >= target.count
            || target
                .fields
                .last()
                .is_some_and(|(previous, _)| previous >= &name)
        {
            return Err(refused(Error::FieldOrder));
        }
        target.fields.push((name, decode_bsl_value(&row, 3)?));
    }
    Ok(())
}
type DigestBuckets = BTreeMap<[u8; 32], (i64, Vec<u8>)>;

fn matching(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    digests: &[Vec<u8>],
) -> Result<DigestBuckets, RustPersistenceRuntimeError> {
    let stored = client.query(
        "SELECT d.definition_id,d.first_tick,d.territory_id,d.field_count,d.canonical_sha256,EXISTS(SELECT 1 FROM babylon_state.tick_commit m WHERE m.campaign_id=d.campaign_id AND m.resolve_tick=d.first_tick) FROM babylon_state.territory_definition_v1 d WHERE d.campaign_id=$1::uuid AND d.canonical_sha256=ANY($2::bytea[]) ORDER BY d.definition_id",
        &[campaign.as_uuid(), &digests],
    ).map_err(|error| RustPersistenceRuntimeError::postgres("read territory digest buckets", &error))?;
    let mut definitions = headers(stored, tick)?;
    load_fields(client, campaign, &mut definitions)?;
    let mut result = DigestBuckets::new();
    for definition in definitions.into_values() {
        let canonical = definition.canonical()?;
        if let Some((_, previous)) = result.get(&definition.digest) {
            return Err(refused(if previous == &canonical {
                Error::DuplicateDefinition
            } else {
                Error::HashCollision
            }));
        }
        result.insert(definition.digest, (definition.id, canonical));
    }
    Ok(result)
}
fn next_definition(
    client: &mut impl GenericClient,
    campaign: CampaignId,
) -> Result<i64, RustPersistenceRuntimeError> {
    let row = client.query_one("SELECT count(*)::bigint,max(definition_id) FROM babylon_state.territory_definition_v1 WHERE campaign_id=$1::uuid", &[campaign.as_uuid()])
        .map_err(|error| RustPersistenceRuntimeError::postgres("read territory definition head", &error))?;
    let count: i64 = column(&row, 0)?;
    let maximum: Option<i64> = column(&row, 1)?;
    if count < 0 || maximum != count.checked_sub(1).filter(|_| count > 0) {
        return Err(refused(Error::DefinitionGap));
    }
    Ok(count)
}
struct NewDefinition<'a> {
    id: i64,
    row: &'a TerritoryStateRow,
    key: Vec<u8>,
    digest: [u8; 32],
}
struct Prepared<'a> {
    added: Vec<NewDefinition<'a>>,
    membership: Vec<i64>,
}
fn prepare<'a>(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    rows: &'a [TerritoryStateRow],
) -> Result<Prepared<'a>, RustPersistenceRuntimeError> {
    if rows.len() > MAX_STABLE_GRAPH_NODES {
        return Err(refused(Error::Bounds));
    }
    let mut keys = Vec::with_capacity(rows.len());
    let mut digests = Vec::with_capacity(rows.len());
    for row in rows {
        let key = row
            .territory_id()
            .canonical_bytes()
            .map_err(|_| refused(Error::RowOrder))?;
        if keys.last().is_some_and(|previous| previous >= &key) {
            return Err(refused(Error::RowOrder));
        }
        i32::try_from(row.ordered_fields().len()).map_err(|_| refused(Error::Bounds))?;
        keys.push(key);
        digests.push(sha256_of(row.canonical_bytes()).to_vec());
    }
    let known = matching(client, campaign, tick, &digests)?;
    let mut next = next_definition(client, campaign)?;
    let mut prepared = Prepared {
        added: Vec::new(),
        membership: Vec::with_capacity(rows.len()),
    };
    let mut added_buckets = BTreeMap::<[u8; 32], &[u8]>::new();
    for (row, key) in rows.iter().zip(keys) {
        let digest = sha256_of(row.canonical_bytes());
        let id = if let Some((id, canonical)) = known.get(&digest) {
            if canonical != row.canonical_bytes() {
                return Err(refused(Error::HashCollision));
            }
            *id
        } else {
            if let Some(previous) = added_buckets.insert(digest, row.canonical_bytes()) {
                return Err(refused(if previous == row.canonical_bytes() {
                    Error::DuplicateDefinition
                } else {
                    Error::HashCollision
                }));
            }
            let id = next;
            next = next.checked_add(1).ok_or_else(|| refused(Error::Bounds))?;
            prepared.added.push(NewDefinition {
                id,
                row,
                key,
                digest,
            });
            id
        };
        prepared.membership.push(id);
    }
    Ok(prepared)
}
fn write_definitions(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    added: &[NewDefinition<'_>],
) -> Result<(), RustPersistenceRuntimeError> {
    if added.is_empty() {
        return Ok(());
    }
    let campaign_text = campaign.as_uuid().to_string();
    let tick_text = tick.to_string();
    let mut writer = client.copy_in("COPY babylon_state.territory_definition_v1 (campaign_id,definition_id,first_tick,territory_id,field_count,canonical_sha256) FROM STDIN WITH (FORMAT csv)")
        .map_err(|error| RustPersistenceRuntimeError::postgres("begin territory definition copy", &error))?;
    for definition in added {
        let id = definition.id.to_string();
        let key = bytea_copy_text(&definition.key);
        let count = definition.row.ordered_fields().len().to_string();
        let digest = bytea_copy_text(&definition.digest);
        write_csv_row(
            &mut writer,
            [&campaign_text, &id, &tick_text, &key, &count, &digest]
                .into_iter()
                .map(|value| Some(value.as_str())),
        )
        .map_err(|_| RustPersistenceRuntimeError::database("write territory definition copy"))?;
    }
    finish_csv_copy(writer, added.len(), "finish territory definition copy")?;
    write_fields(client, &campaign_text, added)
}
fn write_fields(
    client: &mut impl GenericClient,
    campaign: &str,
    added: &[NewDefinition<'_>],
) -> Result<(), RustPersistenceRuntimeError> {
    let mut writer = client.copy_in("COPY babylon_state.territory_definition_field_v1 (campaign_id,definition_id,position,field_name,value_tag,int_value,currency_value,real_bits,ratio_bits,ratio_min_bits,ratio_max_bits,bool_value,enum_type,enum_member,stable_key) FROM STDIN WITH (FORMAT csv)")
        .map_err(|error| RustPersistenceRuntimeError::postgres("begin territory definition field copy", &error))?;
    let mut expected = 0_usize;
    for definition in added {
        let id = definition.id.to_string();
        for (position, (name, value)) in definition.row.ordered_fields().iter().enumerate() {
            let position = i32::try_from(position)
                .map_err(|_| refused(Error::Bounds))?
                .to_string();
            write_bsl_csv_row(
                &mut writer,
                &[campaign, &id, &position, name],
                value,
                "write territory definition field copy",
            )?;
            expected = expected
                .checked_add(1)
                .ok_or_else(|| refused(Error::Bounds))?;
        }
    }
    finish_csv_copy(writer, expected, "finish territory definition field copy")
}
/// Intern exact admitted opening rows without publishing tick membership.
pub(crate) fn seed(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    rows: &[TerritoryStateRow],
) -> Result<(), RustPersistenceRuntimeError> {
    let prepared = prepare(client, campaign, 0, rows)?;
    write_definitions(client, campaign, 0, &prepared.added)
}
/// Intern current rows and publish membership plus its exact count before the marker.
pub(crate) fn insert(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    rows: &[TerritoryStateRow],
) -> Result<(), RustPersistenceRuntimeError> {
    if tick <= 0 {
        return Err(refused(Error::InvalidTick));
    }
    let prepared = prepare(client, campaign, tick, rows)?;
    write_definitions(client, campaign, tick, &prepared.added)?;
    write_membership(client, campaign, tick, &prepared.membership)
}
fn write_membership(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    ids: &[i64],
) -> Result<(), RustPersistenceRuntimeError> {
    let campaign_text = campaign.as_uuid().to_string();
    let tick_text = tick.to_string();
    let mut writer = client.copy_in("COPY babylon_state.territory_tick_membership_v1 (campaign_id,resolve_tick,definition_id) FROM STDIN WITH (FORMAT csv)")
        .map_err(|error| RustPersistenceRuntimeError::postgres("begin territory membership copy", &error))?;
    for id in ids {
        let id = id.to_string();
        write_csv_row(
            &mut writer,
            [&campaign_text, &tick_text, &id]
                .into_iter()
                .map(|value| Some(value.as_str())),
        )
        .map_err(|_| RustPersistenceRuntimeError::database("write territory membership copy"))?;
    }
    finish_csv_copy(writer, ids.len(), "finish territory membership copy")?;
    let count = checked_id(ids.len())?;
    let inserted = client.execute("INSERT INTO babylon_state.territory_tick_manifest_v1 (campaign_id,resolve_tick,territory_count) VALUES ($1::uuid,$2,$3)", &[campaign.as_uuid(),&tick,&count])
        .map_err(|error| RustPersistenceRuntimeError::postgres("insert territory membership manifest", &error))?;
    if inserted != 1 {
        return Err(RustPersistenceRuntimeError::database(
            "insert territory membership manifest",
        ));
    }
    Ok(())
}
