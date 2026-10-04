//! Exact event dictionaries and native typed array chunks. Caller holds campaign
//! writer ownership and writes the durable marker last in the same transaction.
mod node_keys;
use crate::{identity::CampaignId, runtime::RustPersistenceRuntimeError};
use babylon_bsl::identity_codec::StableBslValue;
use babylon_tick::replay_session::SuccessfulEvent;
use postgres::{
    binary_copy::BinaryCopyInWriter,
    fallible_iterator::FallibleIterator as _,
    types::{FromSqlOwned, ToSql, Type},
    GenericClient,
};
use std::collections::{BTreeMap, BTreeSet};
use std::io::Write;
const CHUNK: usize = 4096;
/// Exact event storage admission failure, before durable publication.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    /// A lookup or event identity exceeds its native integer representation.
    IdentityOverflow,
    /// The lookup IDs are not a dense zero-based sequence.
    DictionaryGap,
    /// More than one lookup row stores the same exact value.
    DictionaryDuplicate,
    /// Event fields are duplicated or out of canonical name order.
    NoncanonicalFields,
    /// A native stable element key cannot be canonically encoded.
    StableKey,
    /// A required exact lookup value is absent.
    MissingReference,
    /// A lookup value was introduced after the period being written.
    FutureReference,
}
fn refuse(e: Error) -> RustPersistenceRuntimeError {
    RustPersistenceRuntimeError::EventStorage(e)
}
fn id(n: usize) -> Result<i64, RustPersistenceRuntimeError> {
    i64::try_from(n).map_err(|_| refuse(Error::IdentityOverflow))
}
fn db(op: &'static str, e: &postgres::Error) -> RustPersistenceRuntimeError {
    RustPersistenceRuntimeError::postgres(op, e)
}
fn bits(v: u64) -> i64 {
    i64::from_ne_bytes(v.to_ne_bytes())
}
#[derive(Debug, Clone, PartialEq, Eq)]
struct Field {
    ordinal: i64,
    position: i64,
    name: i64,
    tag: i16,
    int: Option<i64>,
    currency: Option<i128>,
    real: Option<i64>,
    ratio: Option<i64>,
    floor: Option<i64>,
    cap: Option<i64>,
    boolean: Option<bool>,
    enum_type: Option<i64>,
    member: Option<i64>,
    key: Option<i64>,
    key_scenario: Option<i64>,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum KeyReference {
    Node { scenario: i64, name: i64 },
    Literal(i64),
}
type KeyReferences = BTreeMap<Vec<u8>, KeyReference>;
fn project(
    ordinal: i64,
    position: i64,
    name: i64,
    value: &StableBslValue,
    text: &BTreeMap<String, i64>,
    keys: &KeyReferences,
) -> Result<Field, RustPersistenceRuntimeError> {
    let mut f = Field {
        ordinal,
        position,
        name,
        tag: 0,
        int: None,
        currency: None,
        real: None,
        ratio: None,
        floor: None,
        cap: None,
        boolean: None,
        enum_type: None,
        member: None,
        key: None,
        key_scenario: None,
    };
    match value {
        StableBslValue::Int(v) => {
            f.tag = 1;
            f.int = Some(*v);
        }
        StableBslValue::CurrencyMicroUnits(v) => {
            f.tag = 2;
            f.currency = Some(*v);
        }
        StableBslValue::RealBits(v) => {
            f.tag = 3;
            f.real = Some(bits(*v));
        }
        StableBslValue::RatioBits { value, floor, cap } => {
            f.tag = 4;
            f.ratio = Some(bits(*value));
            f.floor = floor.map(bits);
            f.cap = cap.map(bits);
        }
        StableBslValue::Bool(v) => {
            f.tag = 5;
            f.boolean = Some(*v);
        }
        StableBslValue::Enum { enum_type, member } => {
            f.tag = 6;
            f.enum_type = Some(reference(text, enum_type)?);
            f.member = Some(reference(text, member)?);
        }
        StableBslValue::Node(k) | StableBslValue::Hyperedge(k) | StableBslValue::Edge(k) => {
            f.tag = match value {
                StableBslValue::Node(_) => 7,
                StableBslValue::Hyperedge(_) => 8,
                _ => 9,
            };
            let proper = matches!(
                (value, k),
                (
                    StableBslValue::Node(_),
                    babylon_graph::stable_element::StableElementKey::Node { .. }
                ) | (
                    StableBslValue::Hyperedge(_),
                    babylon_graph::stable_element::StableElementKey::Hyperedge { .. }
                ) | (
                    StableBslValue::Edge(_),
                    babylon_graph::stable_element::StableElementKey::Edge { .. }
                )
            );
            if !proper {
                return Err(refuse(Error::StableKey));
            }
            let bytes = k.canonical_bytes().map_err(|_| refuse(Error::StableKey))?;
            match keys
                .get(&bytes)
                .ok_or_else(|| refuse(Error::MissingReference))?
            {
                KeyReference::Node { scenario, name } if f.tag == 7 => {
                    f.key = Some(*name);
                    f.key_scenario = Some(*scenario);
                }
                KeyReference::Literal(id) if matches!(f.tag, 8 | 9) => {
                    f.key = Some(*id);
                }
                _ => return Err(refuse(Error::StableKey)),
            }
        }
    }
    Ok(f)
}
fn array<T: std::fmt::Display>(values: impl Iterator<Item = Option<T>>) -> String {
    let parts: Vec<_> = values
        .map(|v| v.map_or_else(|| "NULL".into(), |v| v.to_string()))
        .collect();
    format!("\"{{{}}}\"", parts.join(","))
}
fn lane<T: std::fmt::Display>(
    active: bool,
    rows: &[Field],
    get: impl Fn(&Field) -> Option<T>,
) -> String {
    if active {
        array(rows.iter().map(get))
    } else {
        String::new()
    }
}
fn field_csv(campaign: &str, tick: i64, chunk: i64, tag: i16, rows: &[Field]) -> String {
    [
        campaign.to_owned(),
        tick.to_string(),
        chunk.to_string(),
        tag.to_string(),
        array(rows.iter().map(|r| Some(r.ordinal))),
        array(rows.iter().map(|r| Some(r.position))),
        array(rows.iter().map(|r| Some(r.name))),
        lane(tag == 1, rows, |r| r.int),
        lane(tag == 2, rows, |r| r.currency),
        lane(tag == 3, rows, |r| r.real),
        lane(tag == 4, rows, |r| r.ratio),
        lane(tag == 4, rows, |r| r.floor),
        lane(tag == 4, rows, |r| r.cap),
        lane(tag == 5, rows, |r| {
            r.boolean.map(|v| if v { "t" } else { "f" })
        }),
        lane(tag == 6, rows, |r| r.enum_type),
        lane(tag == 6, rows, |r| r.member),
        lane(tag >= 7, rows, |r| r.key),
        lane(tag == 7, rows, |r| r.key_scenario),
    ]
    .join(",")
        + "\n"
}
#[derive(Clone, Copy)]
enum Lookup {
    Text,
    Key,
}
impl Lookup {
    fn head(self) -> &'static str {
        match self {
 Self::Text=>"SELECT count(*),coalesce(max(text_id),-1),coalesce(max(first_tick),0) FROM babylon_state.event_text_lookup_v1 WHERE campaign_id=$1",
 Self::Key=>"SELECT count(*),coalesce(max(key_id),-1),coalesce(max(first_tick),0) FROM babylon_state.event_key_lookup_v1 WHERE campaign_id=$1"}
    }
    fn matching(self) -> &'static str {
        match self {
 Self::Text=>"SELECT text_id,value FROM babylon_state.event_text_lookup_v1 WHERE campaign_id=$1 AND value=ANY($2::text[])",
 Self::Key=>"SELECT key_id,value FROM babylon_state.event_key_lookup_v1 WHERE campaign_id=$1 AND value=ANY($2::bytea[])"}
    }
}
// Transfer batches target one MiB, with one larger allowed native value alone;
// this is physical batching, not a new admissible text/key byte ceiling.
trait LookupValue: Ord + Clone + Sync + FromSqlOwned {
    fn storage_bytes(&self) -> usize;
}
impl LookupValue for String {
    fn storage_bytes(&self) -> usize {
        self.len()
    }
}
impl LookupValue for Vec<u8> {
    fn storage_bytes(&self) -> usize {
        self.len()
    }
}
fn load_matching<T>(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    kind: Lookup,
    wanted: &BTreeSet<T>,
) -> Result<(BTreeMap<T, i64>, i64), RustPersistenceRuntimeError>
where
    T: LookupValue,
    Vec<T>: ToSql,
{
    let head = client
        .query_one(kind.head(), &[campaign.as_uuid()])
        .map_err(|e| db("read event lookup head", &e))?;
    let count: i64 = head
        .try_get(0)
        .map_err(|e| db("decode event lookup count", &e))?;
    let last: i64 = head
        .try_get(1)
        .map_err(|e| db("decode event lookup tail", &e))?;
    let introduced: i64 = head
        .try_get(2)
        .map_err(|e| db("decode event lookup introduction", &e))?;
    if count < 0 || count.checked_sub(1) != Some(last) {
        return Err(refuse(Error::DictionaryGap));
    }
    if introduced > tick {
        return Err(refuse(Error::FutureReference));
    }
    let mut result = BTreeMap::new();
    let mut wanted = wanted.iter().peekable();
    loop {
        let mut batch = Vec::new();
        let mut bytes = 0usize;
        while let Some(value) = wanted.peek() {
            if batch.len() == CHUNK
                || (!batch.is_empty()
                    && value.storage_bytes() > 1_048_576usize.saturating_sub(bytes))
            {
                break;
            }
            let Some(value) = wanted.next() else {
                break;
            };
            bytes = bytes
                .checked_add(value.storage_bytes())
                .ok_or_else(|| refuse(Error::IdentityOverflow))?;
            batch.push(value.clone());
        }
        if batch.is_empty() {
            break;
        }

        let params: [&(dyn ToSql + Sync); 2] = [campaign.as_uuid(), &batch];
        let mut rows = client
            .query_raw(kind.matching(), params)
            .map_err(|e| db("read exact event lookup subset", &e))?;
        while let Some(row) = rows
            .next()
            .map_err(|e| db("stream event lookup subset", &e))?
        {
            let n: i64 = row
                .try_get(0)
                .map_err(|e| db("decode event lookup ID", &e))?;
            let value: T = row
                .try_get(1)
                .map_err(|e| db("decode exact event lookup value", &e))?;
            if n < 0 || n >= count {
                return Err(refuse(Error::DictionaryGap));
            }
            if result.insert(value, n).is_some() {
                return Err(refuse(Error::DictionaryDuplicate));
            }
        }
    }
    Ok((result, count))
}
fn reference<T, Q: Ord + ?Sized>(
    lookup: &BTreeMap<T, i64>,
    key: &Q,
) -> Result<i64, RustPersistenceRuntimeError>
where
    T: Ord + std::borrow::Borrow<Q>,
{
    lookup
        .get(key)
        .copied()
        .ok_or_else(|| refuse(Error::MissingReference))
}
type Wanted = (BTreeSet<String>, BTreeSet<Vec<u8>>);
fn collect_wanted(events: &[SuccessfulEvent]) -> Result<Wanted, RustPersistenceRuntimeError> {
    // BTreeMap iteration assigns exact deterministic additions; values are owned
    // only once per lookup. No assumption that names or emitted inventory stay fixed.
    let mut wanted_text = BTreeSet::<String>::new();
    let mut wanted_keys = BTreeSet::<Vec<u8>>::new();
    for event in events {
        wanted_text.insert(event.event_type().to_owned());
        wanted_text.insert(event.emitting_rule().to_owned());
        if event.fields().windows(2).any(|p| p[0].0 >= p[1].0) {
            return Err(refuse(Error::NoncanonicalFields));
        }
        for (name, value) in event.fields() {
            wanted_text.insert(name.clone());
            match value {
                StableBslValue::Enum { enum_type, member } => {
                    wanted_text.insert(enum_type.clone());
                    wanted_text.insert(member.clone());
                }
                StableBslValue::Node(k)
                | StableBslValue::Hyperedge(k)
                | StableBslValue::Edge(k) => {
                    wanted_keys.insert(k.canonical_bytes().map_err(|_| refuse(Error::StableKey))?);
                }
                _ => {}
            }
        }
    }
    Ok((wanted_text, wanted_keys))
}
fn write_lookups(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    texts: &BTreeMap<String, i64>,
    prior_text: i64,
    keys: &KeyReferences,
    prior_keys: i64,
) -> Result<(), RustPersistenceRuntimeError> {
    let sink=client.copy_in("COPY babylon_state.event_text_lookup_v1(campaign_id,text_id,first_tick,value) FROM STDIN BINARY").map_err(|e|db("begin event text lookup",&e))?;
    let mut writer =
        BinaryCopyInWriter::new(sink, &[Type::UUID, Type::INT8, Type::INT8, Type::TEXT]);
    for (value, n) in texts {
        if *n >= prior_text {
            writer
                .write(&[campaign.as_uuid(), n, &tick, value])
                .map_err(|e| db("write event text lookup", &e))?;
        }
    }
    writer
        .finish()
        .map_err(|e| db("finish event text lookup", &e))?;
    let sink=client.copy_in("COPY babylon_state.event_key_lookup_v1(campaign_id,key_id,first_tick,value) FROM STDIN BINARY").map_err(|e|db("begin event key lookup",&e))?;
    let mut writer =
        BinaryCopyInWriter::new(sink, &[Type::UUID, Type::INT8, Type::INT8, Type::BYTEA]);
    for (value, reference) in keys {
        if let KeyReference::Literal(n) = reference {
            if *n >= prior_keys {
                writer
                    .write(&[campaign.as_uuid(), n, &tick, value])
                    .map_err(|e| db("write event key lookup", &e))?;
            }
        }
    }
    writer
        .finish()
        .map_err(|e| db("finish event key lookup", &e))?;
    Ok(())
}
fn write_parents(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    events: &[SuccessfulEvent],
    texts: &BTreeMap<String, i64>,
) -> Result<(), RustPersistenceRuntimeError> {
    let sink=client.copy_in("COPY babylon_state.event_parent_chunk_v1(campaign_id,resolve_tick,chunk,event_ordinals,type_ids,rule_ids,choice_ordinals) FROM STDIN BINARY").map_err(|e|db("begin event parent chunks",&e))?;
    let mut writer = BinaryCopyInWriter::new(
        sink,
        &[
            Type::UUID,
            Type::INT8,
            Type::INT8,
            Type::INT8_ARRAY,
            Type::INT8_ARRAY,
            Type::INT8_ARRAY,
            Type::INT8_ARRAY,
        ],
    );
    for (chunk, rows) in events.chunks(CHUNK).enumerate() {
        let ordinals: Vec<_> = (0..rows.len())
            .map(|n| {
                chunk
                    .checked_mul(CHUNK)
                    .and_then(|base| base.checked_add(n))
                    .ok_or_else(|| refuse(Error::IdentityOverflow))
                    .and_then(id)
            })
            .collect::<Result<_, _>>()?;
        if ordinals.iter().any(|n| *n > i64::from(u32::MAX)) {
            return Err(refuse(Error::IdentityOverflow));
        }
        let types: Vec<_> = rows
            .iter()
            .map(|e| reference(texts, e.event_type()))
            .collect::<Result<_, _>>()?;
        let rules: Vec<_> = rows
            .iter()
            .map(|e| reference(texts, e.emitting_rule()))
            .collect::<Result<_, _>>()?;
        let choices: Vec<Option<i64>> = rows
            .iter()
            .map(|e| e.choice_receipt().map(|r| i64::from(r.encounter_ordinal())))
            .collect();
        writer
            .write(&[
                campaign.as_uuid(),
                &tick,
                &id(chunk)?,
                &ordinals,
                &types,
                &rules,
                &choices,
            ])
            .map_err(|e| db("write event parent chunk", &e))?;
    }
    writer
        .finish()
        .map_err(|e| db("finish event parent chunks", &e))?;
    Ok(())
}
fn write_fields(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    events: &[SuccessfulEvent],
    texts: &BTreeMap<String, i64>,
    keys: &KeyReferences,
) -> Result<usize, RustPersistenceRuntimeError> {
    let mut sink=client.copy_in("COPY babylon_state.event_field_chunk_v1(campaign_id,resolve_tick,chunk,value_tag,event_ordinals,positions,name_ids,int_values,currency_values,real_bits,ratio_bits,ratio_mins,ratio_maxs,bool_values,enum_types,enum_members,key_ids,key_scenario_ids) FROM STDIN WITH(FORMAT csv)").map_err(|e|db("begin event field chunks",&e))?;
    let mut chunks = 0usize;
    let campaign_text = campaign.as_uuid().to_string();
    // Nine bounded passes avoid retaining one additional heap record per field.
    // Original ordinals/positions remain explicit when tags cross chunk boundaries.
    for tag in 1..=9 {
        let mut buffer = Vec::new();
        buffer
            .try_reserve_exact(CHUNK)
            .map_err(|_| RustPersistenceRuntimeError::Allocation {
                field: "event field chunk",
                requested: CHUNK,
            })?;
        for (ordinal, event) in events.iter().enumerate() {
            for (position, (name, value)) in event.fields().iter().enumerate() {
                let actual_tag = match value {
                    StableBslValue::Int(_) => 1,
                    StableBslValue::CurrencyMicroUnits(_) => 2,
                    StableBslValue::RealBits(_) => 3,
                    StableBslValue::RatioBits { .. } => 4,
                    StableBslValue::Bool(_) => 5,
                    StableBslValue::Enum { .. } => 6,
                    StableBslValue::Node(_) => 7,
                    StableBslValue::Hyperedge(_) => 8,
                    StableBslValue::Edge(_) => 9,
                };
                if actual_tag != tag {
                    continue;
                }
                let position = i64::from(
                    u32::try_from(position).map_err(|_| refuse(Error::IdentityOverflow))?,
                );
                buffer.push(project(
                    id(ordinal)?,
                    position,
                    reference(texts, name)?,
                    value,
                    texts,
                    keys,
                )?);
                if buffer.len() == CHUNK {
                    let csv = field_csv(&campaign_text, tick, id(chunks)?, tag, &buffer);
                    sink.write_all(csv.as_bytes()).map_err(|_| {
                        RustPersistenceRuntimeError::Database {
                            operation: "write event field chunk",
                            diagnostic: None,
                        }
                    })?;
                    chunks = chunks
                        .checked_add(1)
                        .ok_or_else(|| refuse(Error::IdentityOverflow))?;
                    buffer.clear();
                }
            }
        }
        if !buffer.is_empty() {
            let csv = field_csv(&campaign_text, tick, id(chunks)?, tag, &buffer);
            sink.write_all(csv.as_bytes())
                .map_err(|_| RustPersistenceRuntimeError::Database {
                    operation: "write event field chunk",
                    diagnostic: None,
                })?;
            chunks = chunks
                .checked_add(1)
                .ok_or_else(|| refuse(Error::IdentityOverflow))?;
        }
    }
    sink.finish()
        .map_err(|e| db("finish event field chunks", &e))?;
    Ok(chunks)
}
pub(crate) fn insert(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    events: &[SuccessfulEvent],
) -> Result<(), RustPersistenceRuntimeError> {
    // Exact string/byte keys, not digest identities. Source fields are canonical
    // before publication; retain their explicit positions rather than resort them.
    // Reuse the qualified graph campaign-lookup lock before the per-tick lock.
    // Shared ordering also covers graph-first writer dispatch and marker hooks.
    client.query_one("SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.graph-lookup.v1:'||$1::uuid::text,0))",&[campaign.as_uuid()]).map_err(|e|db("lock event campaign lookup",&e))?;
    client.query_one("SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.event-marker.v1:'||$1::uuid::text||':'||$2::bigint::text,0))",&[campaign.as_uuid(),&tick]).map_err(|e|db("lock event marker",&e))?;
    let (wanted_text, wanted_keys) = collect_wanted(events)?;
    let (mut texts, prior_text) =
        load_matching(client, campaign, tick, Lookup::Text, &wanted_text)?;
    let (keys, prior_keys) = node_keys::admit(client, campaign, tick, &wanted_keys)?;
    let mut next_text = prior_text;

    for value in wanted_text {
        if let std::collections::btree_map::Entry::Vacant(entry) = texts.entry(value) {
            entry.insert(next_text);
            next_text = next_text
                .checked_add(1)
                .ok_or_else(|| refuse(Error::IdentityOverflow))?;
        }
    }
    write_lookups(
        client, campaign, tick, &texts, prior_text, &keys, prior_keys,
    )?;
    write_parents(client, campaign, tick, events, &texts)?;
    let field_count = events.iter().try_fold(0usize, |n, e| {
        n.checked_add(e.fields().len())
            .ok_or_else(|| refuse(Error::IdentityOverflow))
    })?;
    let chunks = write_fields(client, campaign, tick, events, &texts, &keys)?;
    client
        .execute(
            "INSERT INTO babylon_state.event_manifest_v1 VALUES($1,$2,$3,$4,$5,$6)",
            &[
                campaign.as_uuid(),
                &tick,
                &id(events.len())?,
                &id(field_count)?,
                &id(events.len().div_ceil(CHUNK))?,
                &id(chunks)?,
            ],
        )
        .map_err(|e| db("write event manifest", &e))?;
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn event_payloads_preserve_i128_and_binary64_lanes() {
        let names = BTreeMap::new();
        let keys = BTreeMap::new();
        let currency = project(
            0,
            0,
            0,
            &StableBslValue::CurrencyMicroUnits(i128::MIN),
            &names,
            &keys,
        )
        .unwrap();
        assert_eq!(currency.currency, Some(i128::MIN));
        assert_eq!(currency.int, None);
        let real = project(1, 0, 0, &StableBslValue::RealBits(1 << 63), &names, &keys).unwrap();
        assert_eq!(real.real, Some(i64::MIN));
        let ratio = project(
            1,
            1,
            0,
            &StableBslValue::RatioBits {
                value: 1,
                floor: None,
                cap: Some(u64::MAX),
            },
            &names,
            &keys,
        )
        .unwrap();
        let csv = field_csv("00000000-0000-0000-0000-000000000001", 1, 0, 4, &[ratio]);
        assert!(csv.contains("\"{NULL}\""));
        assert!(csv.contains("\"{-1}\""));
    }
    #[test]
    fn event_enum_identity_and_false_boolean_are_not_null() {
        let names = BTreeMap::from([("Type".into(), 2), ("false".into(), 3)]);
        let keys = BTreeMap::new();
        let enum_value = project(
            0,
            0,
            1,
            &StableBslValue::Enum {
                enum_type: "Type".into(),
                member: "false".into(),
            },
            &names,
            &keys,
        )
        .unwrap();
        assert_eq!(
            (enum_value.enum_type, enum_value.member),
            (Some(2), Some(3))
        );
        let boolean = project(0, 1, 1, &StableBslValue::Bool(false), &names, &keys).unwrap();
        assert_eq!(boolean.boolean, Some(false));
        assert!(field_csv("id", 1, 0, 5, &[boolean]).contains("\"{f}\""));
    }
}

#[cfg(test)]
mod key_controls {
    use super::*;
    use babylon_graph::stable_element::StableElementKey;
    #[test]
    fn event_key_kind_and_exact_bytes_survive_lookup_refs() {
        let variants = [
            StableElementKey::Node {
                scenario: "proof".into(),
                local_name: "member".into(),
            },
            StableElementKey::Hyperedge {
                scenario: "proof".into(),
                local_name: "group".into(),
            },
            StableElementKey::Edge {
                scenario: "proof".into(),
                edge_type: "member-of".into(),
                source_local_name: "member".into(),
                target_local_name: "group".into(),
            },
        ];
        let mut keys = BTreeMap::new();
        for (n, k) in variants.iter().enumerate() {
            keys.insert(
                k.canonical_bytes().unwrap(),
                if n == 0 {
                    KeyReference::Node {
                        scenario: 13,
                        name: 0,
                    }
                } else {
                    KeyReference::Literal(i64::try_from(n).unwrap())
                },
            );
        }
        let values = [
            StableBslValue::Node(variants[0].clone()),
            StableBslValue::Hyperedge(variants[1].clone()),
            StableBslValue::Edge(variants[2].clone()),
        ];
        for (n, v) in values.iter().enumerate() {
            let row = project(2, i64::try_from(n).unwrap(), 4, v, &BTreeMap::new(), &keys).unwrap();
            assert_eq!(row.tag, i16::try_from(n).unwrap() + 7);
            assert_eq!(row.key, Some(i64::try_from(n).unwrap()));
            let original = variants[n].canonical_bytes().unwrap();
            let resolved = if let Some(scenario) = row.key_scenario {
                KeyReference::Node {
                    scenario,
                    name: row.key.unwrap(),
                }
            } else {
                KeyReference::Literal(row.key.unwrap())
            };
            assert_eq!(keys.get(&original).copied(), Some(resolved));
            assert_eq!(
                StableElementKey::from_canonical_bytes(&original).unwrap(),
                variants[n]
            );
        }
    }
}

#[cfg(test)]
mod missing_controls {
    use super::*;
    #[test]
    fn event_missing_enum_ref_is_a_specific_refusal() {
        let value = StableBslValue::Enum {
            enum_type: "Type".into(),
            member: "member".into(),
        };
        assert_eq!(
            project(0, 0, 0, &value, &BTreeMap::new(), &BTreeMap::new()),
            Err(refuse(Error::MissingReference))
        );
    }
}

#[cfg(test)]
mod live_payload_controls {
    use super::*;
    use babylon_graph::stable_element::StableElementKey;
    use postgres::{Config, NoTls};
    use std::str::FromStr;
    use uuid::Uuid;

    fn disposable_config() -> Config {
        assert_eq!(
            std::env::var("BABYLON_POSTGRES_DISPOSABLE_ACK").as_deref(),
            Ok("I_UNDERSTAND_THIS_DISPOSABLE_RUNTIME_DROPS_ITS_SCRATCH_DATABASES_AND_ROLES")
        );
        let canary = std::env::var("BABYLON_POSTGRES_DISPOSABLE_CANARY").unwrap();
        assert_eq!(canary.len(), 32);
        let mut config =
            Config::from_str(&std::env::var("BABYLON_POSTGRES_TEST_DSN").unwrap()).unwrap();
        crate::postgres_catalog::validate_connection_target(&config).unwrap();
        assert_eq!(config.get_user(), Some("test"));
        assert_eq!(config.get_dbname(), Some("postgres"));
        let actual: Option<String> = config
            .connect(NoTls)
            .unwrap()
            .query_one(
                "SELECT pg_catalog.current_setting('babylon.disposable_runtime',true)",
                &[],
            )
            .unwrap()
            .get(0);
        assert_eq!(actual.as_deref(), Some(canary.as_str()));
        let database = std::env::var("BABYLON_EVENT_COPY_DATABASE").unwrap();
        assert!(database.starts_with("per337_event_continuity_"));
        config.dbname(&database);
        config
    }

    fn payloads() -> Vec<(String, StableBslValue)> {
        let node = StableElementKey::Node {
            scenario: "proof".into(),
            local_name: "member".into(),
        };
        let hyperedge = StableElementKey::Hyperedge {
            scenario: "proof".into(),
            local_name: "group".into(),
        };
        let edge = StableElementKey::Edge {
            scenario: "proof".into(),
            edge_type: "member-of".into(),
            source_local_name: "member".into(),
            target_local_name: "group".into(),
        };
        vec![
            ("01_int_min".into(), StableBslValue::Int(i64::MIN)),
            ("02_int_max".into(), StableBslValue::Int(i64::MAX)),
            (
                "03_currency_min".into(),
                StableBslValue::CurrencyMicroUnits(i128::MIN),
            ),
            (
                "04_currency_max".into(),
                StableBslValue::CurrencyMicroUnits(i128::MAX),
            ),
            (
                "05_negative_zero".into(),
                StableBslValue::RealBits((-0.0_f64).to_bits()),
            ),
            (
                "06_ratio_null_floor".into(),
                StableBslValue::RatioBits {
                    value: 1.0_f64.to_bits(),
                    floor: None,
                    cap: Some(2.0_f64.to_bits()),
                },
            ),
            (
                "07_ratio_null_cap".into(),
                StableBslValue::RatioBits {
                    value: 1.0_f64.to_bits(),
                    floor: Some(0.25_f64.to_bits()),
                    cap: None,
                },
            ),
            ("08_false".into(), StableBslValue::Bool(false)),
            (
                "09_enum".into(),
                StableBslValue::Enum {
                    enum_type: "型λ\\,\"\n".repeat(2048),
                    member: "成员false\\,\"\n".repeat(2048),
                },
            ),
            ("10_node".into(), StableBslValue::Node(node)),
            ("11_hyperedge".into(), StableBslValue::Hyperedge(hyperedge)),
            ("12_edge".into(), StableBslValue::Edge(edge)),
        ]
    }

    struct OriginalRow {
        tag: i16,
        int: Option<i64>,
        currency: Option<String>,
        real: Option<i64>,
        ratio: Option<i64>,
        floor: Option<i64>,
        cap: Option<i64>,
        boolean: Option<bool>,
        enum_type: Option<String>,
        member: Option<String>,
        key: Option<Vec<u8>>,
    }
    fn original_projection(value: &StableBslValue) -> OriginalRow {
        let mut row = OriginalRow {
            tag: 0,
            int: None,
            currency: None,
            real: None,
            ratio: None,
            floor: None,
            cap: None,
            boolean: None,
            enum_type: None,
            member: None,
            key: None,
        };
        let signed = |value: u64| i64::from_be_bytes(value.to_be_bytes());
        match value {
            StableBslValue::Int(value) => {
                row.tag = 1;
                row.int = Some(*value);
            }
            StableBslValue::CurrencyMicroUnits(value) => {
                row.tag = 2;
                row.currency = Some(value.to_string());
            }
            StableBslValue::RealBits(value) => {
                row.tag = 3;
                row.real = Some(signed(*value));
            }
            StableBslValue::RatioBits { value, floor, cap } => {
                row.tag = 4;
                row.ratio = Some(signed(*value));
                row.floor = floor.map(signed);
                row.cap = cap.map(signed);
            }
            StableBslValue::Bool(value) => {
                row.tag = 5;
                row.boolean = Some(*value);
            }
            StableBslValue::Enum { enum_type, member } => {
                row.tag = 6;
                row.enum_type = Some(enum_type.clone());
                row.member = Some(member.clone());
            }
            StableBslValue::Node(key) => {
                row.tag = 7;
                row.key = Some(key.canonical_bytes().unwrap());
            }
            StableBslValue::Hyperedge(key) => {
                row.tag = 8;
                row.key = Some(key.canonical_bytes().unwrap());
            }
            StableBslValue::Edge(key) => {
                row.tag = 9;
                row.key = Some(key.canonical_bytes().unwrap());
            }
        }
        row
    }

    fn reference_rows(
        tx: &mut postgres::Transaction<'_>,
        campaign: CampaignId,
        values: &[(String, StableBslValue)],
    ) {
        tx.batch_execute("CREATE TEMP TABLE payload_reference(campaign_id uuid,resolve_tick bigint,ordinal bigint,position bigint,field_name text COLLATE pg_catalog.\"C\",value_tag smallint,int_value bigint,currency_value numeric(39,0),real_bits bigint,ratio_bits bigint,ratio_min_bits bigint,ratio_max_bits bigint,bool_value boolean,enum_type text COLLATE pg_catalog.\"C\",enum_member text COLLATE pg_catalog.\"C\",stable_key bytea) ON COMMIT DROP").unwrap();
        for (position, (name, value)) in values.iter().enumerate() {
            let row = original_projection(value);
            let position = i64::try_from(position).unwrap();
            tx.execute("INSERT INTO pg_temp.payload_reference VALUES($1,1,0,$2,$3,$4,$5,$6::text::numeric,$7,$8,$9,$10,$11,$12,$13,$14)",&[campaign.as_uuid(),&position,name,&row.tag,&row.int,&row.currency,&row.real,&row.ratio,&row.floor,&row.cap,&row.boolean,&row.enum_type,&row.member,&row.key]).unwrap();
        }
    }

    struct PayloadLookups {
        texts: BTreeMap<String, i64>,
        keys: KeyReferences,
    }

    fn admitted_lookups(
        tx: &mut postgres::Transaction<'_>,
        campaign: CampaignId,
        values: &[(String, StableBslValue)],
    ) -> PayloadLookups {
        let mut wanted = BTreeSet::new();
        let mut raw_keys = BTreeSet::new();
        for (name, value) in values {
            wanted.insert(name.clone());
            match value {
                StableBslValue::Enum { enum_type, member } => {
                    wanted.insert(enum_type.clone());
                    wanted.insert(member.clone());
                }
                StableBslValue::Node(key)
                | StableBslValue::Hyperedge(key)
                | StableBslValue::Edge(key) => {
                    raw_keys.insert(key.canonical_bytes().unwrap());
                }
                _ => {}
            }
        }
        let (mut texts, mut next_text) =
            load_matching(tx, campaign, 1, Lookup::Text, &wanted).unwrap();
        let (keys, prior_key) = node_keys::admit(tx, campaign, 1, &raw_keys).unwrap();
        let prior_text = next_text;

        for value in wanted {
            if let std::collections::btree_map::Entry::Vacant(entry) = texts.entry(value) {
                entry.insert(next_text);
                next_text += 1;
            }
        }
        write_lookups(tx, campaign, 1, &texts, prior_text, &keys, prior_key).unwrap();
        PayloadLookups { texts, keys }
    }

    fn write_projected_csv(
        tx: &mut postgres::Transaction<'_>,
        campaign: CampaignId,
        values: &[(String, StableBslValue)],
        texts: &BTreeMap<String, i64>,
        keys: &KeyReferences,
    ) {
        let mut grouped = BTreeMap::<i16, Vec<Field>>::new();
        for (position, (name, value)) in values.iter().enumerate() {
            let field = project(
                0,
                i64::try_from(position).unwrap(),
                *texts.get(name).unwrap(),
                value,
                texts,
                keys,
            )
            .unwrap();
            grouped.entry(field.tag).or_default().push(field);
        }
        assert_eq!(grouped.len(), 9);
        let mut sink=tx.copy_in("COPY babylon_state.event_field_chunk_v1(campaign_id,resolve_tick,chunk,value_tag,event_ordinals,positions,name_ids,int_values,currency_values,real_bits,ratio_bits,ratio_mins,ratio_maxs,bool_values,enum_types,enum_members,key_ids,key_scenario_ids) FROM STDIN WITH(FORMAT csv)").unwrap();
        let campaign = campaign.as_uuid().to_string();
        for (chunk, (tag, rows)) in grouped.into_iter().enumerate() {
            sink.write_all(
                field_csv(&campaign, 1, i64::try_from(chunk).unwrap(), tag, &rows).as_bytes(),
            )
            .unwrap();
        }
        assert_eq!(sink.finish().unwrap(), 9);
    }

    fn raw_counts(client: &mut impl GenericClient, campaign: CampaignId) -> Vec<i64> {
        [
            "event_text_lookup_v1",
            "event_key_lookup_v1",
            "event_field_chunk_v1",
            "event_manifest_v1",
            "tick_commit",
            "graph_string_lookup_v1",
            "graph_node_lookup_v1",
        ]
        .iter()
        .map(|table| {
            client
                .query_one(
                    &format!("SELECT count(*) FROM babylon_state.{table} WHERE campaign_id=$1"),
                    &[campaign.as_uuid()],
                )
                .unwrap()
                .get(0)
        })
        .collect()
    }

    fn campaign_rows(client: &mut impl GenericClient, campaign: CampaignId, table: &str) -> i64 {
        client
            .query_one(
                &format!("SELECT count(*) FROM babylon_state.{table} WHERE campaign_id=$1"),
                &[campaign.as_uuid()],
            )
            .unwrap()
            .get(0)
    }

    #[test]
    #[ignore = "requires the task-owned disposable PostgreSQL runtime"]
    fn live_all_nine_event_payload_tags_match_independent_typed_reference() {
        let config = disposable_config();
        let campaign = CampaignId::from_uuid(Uuid::from_u128(
            (u128::from(std::process::id()) << 64) | 0x337_9a11,
        ));
        let foundation = crate::michigan_content::MichiganContentPreset::new_campaign(
            crate::michigan_material::MichiganDeliveryPreset::Standard,
        )
        .create_foundation(&crate::test_support::catalog())
        .unwrap();
        let _runtime =
            crate::material_runtime::DurableMaterialRuntime::create(&config, campaign, foundation)
                .unwrap();
        let mut client = config.connect(NoTls).unwrap();
        let before = raw_counts(&mut client, campaign);
        let values = payloads();
        let mut tx = client.transaction().unwrap();
        reference_rows(&mut tx, campaign, &values);
        let PayloadLookups { texts, keys } = admitted_lookups(&mut tx, campaign, &values);
        write_projected_csv(&mut tx, campaign, &values, &texts, &keys);
        assert_eq!(
            tx.query_one(
                "SELECT count(*) FROM babylon_state.event_key_lookup_v1 WHERE campaign_id=$1",
                &[campaign.as_uuid()]
            )
            .unwrap()
            .get::<_, i64>(0),
            2,
            "Node keys use no duplicate literal dictionary row"
        );
        assert_eq!(
            tx.query_one(
                "SELECT count(*) FROM babylon_state.graph_node_lookup_v1 WHERE campaign_id=$1",
                &[campaign.as_uuid()]
            )
            .unwrap()
            .get::<_, i64>(0),
            *before.last().unwrap(),
            "native key identity does not acquire graph tuple membership"
        );
        let snapshot = |tx: &mut postgres::Transaction<'_>, relation: &str| -> String {
            tx.query_one(&format!("SELECT jsonb_agg(to_jsonb(row) ORDER BY position)::text FROM {relation} row WHERE campaign_id=$1"),&[campaign.as_uuid()]).unwrap().get(0)
        };
        assert_eq!(
            snapshot(&mut tx, "babylon_state.event_field_expanded_v1"),
            snapshot(&mut tx, "pg_temp.payload_reference")
        );
        assert_eq!(
            tx.query_one(
                "SELECT count(*) FROM babylon_state.event_field_expanded_v1 WHERE campaign_id=$1",
                &[campaign.as_uuid()]
            )
            .unwrap()
            .get::<_, i64>(0),
            12
        );
        assert_eq!(
            tx.query_one(
                "SELECT count(*) FROM babylon_state.tick_event_field_v2 WHERE campaign_id=$1",
                &[campaign.as_uuid()]
            )
            .unwrap()
            .get::<_, i64>(0),
            0
        );
        tx.rollback().unwrap();
        assert_eq!(raw_counts(&mut client, campaign), before);
    }
    #[test]
    #[ignore = "requires the task-owned disposable PostgreSQL runtime"]
    fn live_node_refs_share_exact_names_and_preserve_foreign_scenarios() {
        let config = disposable_config();
        let campaign = CampaignId::from_uuid(Uuid::from_u128(
            (u128::from(std::process::id()) << 64) | 0x337_9a12,
        ));
        let foundation = crate::michigan_content::MichiganContentPreset::new_campaign(
            crate::michigan_material::MichiganDeliveryPreset::Standard,
        )
        .create_foundation(&crate::test_support::catalog())
        .unwrap();
        let _runtime =
            crate::material_runtime::DurableMaterialRuntime::create(&config, campaign, foundation)
                .unwrap();
        let mut client = config.connect(NoTls).unwrap();
        let before = raw_counts(&mut client, campaign);
        let row=client.query_one("SELECT s.string_id,s.value FROM babylon_state.graph_node_lookup_v1 n JOIN babylon_state.graph_string_lookup_v1 s ON s.campaign_id=n.campaign_id AND s.string_id=n.name_id WHERE n.campaign_id=$1 ORDER BY n.node_id LIMIT 1",&[campaign.as_uuid()]).unwrap();
        let name_id: i64 = row.get(0);
        let name: String = row.get(1);
        let originals = [
            StableElementKey::Node {
                scenario: "proof".into(),
                local_name: name.clone(),
            },
            StableElementKey::Node {
                scenario: "foreign".into(),
                local_name: name,
            },
        ];
        let wanted = originals
            .iter()
            .map(|k| k.canonical_bytes().unwrap())
            .collect();
        let mut tx = client.transaction().unwrap();
        let (refs, prior) = node_keys::admit(&mut tx, campaign, 1, &wanted).unwrap();
        assert_eq!(prior, 0);
        let string_count: i64 = tx
            .query_one(
                "SELECT count(*) FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1",
                &[campaign.as_uuid()],
            )
            .unwrap()
            .get(0);
        let (again, again_prior) = node_keys::admit(&mut tx, campaign, 1, &wanted).unwrap();
        assert_eq!(again, refs);
        assert_eq!(again_prior, prior);
        assert_eq!(
            tx.query_one(
                "SELECT count(*) FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1",
                &[campaign.as_uuid()]
            )
            .unwrap()
            .get::<_, i64>(0),
            string_count,
            "exact scenario/name values are introduced only once"
        );
        let rows: Vec<_> = originals
            .iter()
            .enumerate()
            .map(|(position, key)| {
                project(
                    0,
                    i64::try_from(position).unwrap(),
                    0,
                    &StableBslValue::Node(key.clone()),
                    &BTreeMap::new(),
                    &refs,
                )
                .unwrap()
            })
            .collect();
        assert!(rows.iter().all(|r| r.key == Some(name_id)));
        assert_ne!(rows[0].key_scenario, rows[1].key_scenario);
        let mut sink=tx.copy_in("COPY babylon_state.event_field_chunk_v1(campaign_id,resolve_tick,chunk,value_tag,event_ordinals,positions,name_ids,int_values,currency_values,real_bits,ratio_bits,ratio_mins,ratio_maxs,bool_values,enum_types,enum_members,key_ids,key_scenario_ids) FROM STDIN WITH(FORMAT csv)").unwrap();
        sink.write_all(field_csv(&campaign.as_uuid().to_string(), 1, 0, 7, &rows).as_bytes())
            .unwrap();
        assert_eq!(sink.finish().unwrap(), 1);
        let expanded=tx.query("SELECT stable_key FROM babylon_state.event_field_expanded_v1 WHERE campaign_id=$1 ORDER BY position",&[campaign.as_uuid()]).unwrap();
        assert_eq!(expanded.len(), 2);
        let recovered: Vec<Vec<u8>> = expanded.iter().map(|row| row.get(0)).collect();
        let expected: Vec<_> = originals
            .iter()
            .map(|key| key.canonical_bytes().unwrap())
            .collect();
        assert_eq!(recovered, expected);
        assert_eq!(campaign_rows(&mut tx, campaign, "event_key_lookup_v1"), 0);
        assert_eq!(campaign_rows(&mut tx, campaign, "tick_event_field_v2"), 0);
        tx.rollback().unwrap();
        assert_eq!(raw_counts(&mut client, campaign), before);
    }
}

#[cfg(test)]
mod marker_integrity_controls {
    use crate::identity::CampaignId;
    use postgres::{Config, GenericClient, NoTls};
    use std::str::FromStr;
    use uuid::Uuid;
    fn validated_base_config() -> Config {
        assert_eq!(
            std::env::var("BABYLON_POSTGRES_DISPOSABLE_ACK").as_deref(),
            Ok("I_UNDERSTAND_THIS_DISPOSABLE_RUNTIME_DROPS_ITS_SCRATCH_DATABASES_AND_ROLES")
        );
        let canary = std::env::var("BABYLON_POSTGRES_DISPOSABLE_CANARY")
            .expect("runner supplies the disposable canary");
        assert_eq!(canary.len(), 32);
        let dsn =
            std::env::var("BABYLON_POSTGRES_TEST_DSN").expect("runner supplies the disposable DSN");
        let config = Config::from_str(&dsn).expect("runner DSN parses");
        crate::postgres_catalog::validate_connection_target(&config).expect("loopback target");
        assert_eq!(config.get_user(), Some("test"));
        assert_eq!(config.get_dbname(), Some("postgres"));
        let actual: Option<String> = config
            .connect(NoTls)
            .expect("canary connection")
            .query_one(
                "SELECT pg_catalog.current_setting('babylon.disposable_runtime', true)",
                &[],
            )
            .expect("canary query")
            .try_get(0)
            .expect("canary decode");
        assert_eq!(actual.as_deref(), Some(canary.as_str()));
        config
    }
    fn insert_event_test_marker(client: &mut impl GenericClient, campaign: CampaignId) {
        // This rollback-only event fixture deliberately has no territory rows.
        client
            .execute(
                "INSERT INTO babylon_state.territory_tick_manifest_v1 (campaign_id,resolve_tick,territory_count) VALUES($1,1,0)",
                &[campaign.as_uuid()],
            )
            .unwrap();
        client.execute("INSERT INTO babylon_state.material_tick_v3(campaign_id,resolve_tick,identity_bytes,register_storage_bytes,receipt_storage_bytes,lookup_delta_bytes) VALUES($1,1,$2,$2,$2,$2)", &[campaign.as_uuid(),&&[1_u8;32][..]]).unwrap();
        client
            .execute(
                "INSERT INTO babylon_state.graph_node_manifest_v1 VALUES($1,1,0,0,0,0)",
                &[campaign.as_uuid()],
            )
            .unwrap();
        client
            .execute(
                "INSERT INTO babylon_state.tick_commit VALUES($1,1,3,$2,$2)",
                &[campaign.as_uuid(), &&[1_u8; 32][..]],
            )
            .unwrap();
    }

    fn insert_key_case(tx: &mut impl GenericClient, campaign: CampaignId, case: &str) {
        if matches!(case, "duplicate_key" | "key_gap" | "future_key") {
            let first_tick = if case == "future_key" { 2_i64 } else { 1 };
            tx.execute("INSERT INTO babylon_state.event_key_lookup_v1(campaign_id,key_id,first_tick,value) VALUES($1,0,$2,$3)",&[campaign.as_uuid(),&first_tick,&&[1_u8][..]]).unwrap();
            if case != "future_key" {
                let id = if case == "key_gap" { 2_i64 } else { 1 };
                let value = if case == "key_gap" { 2_u8 } else { 1 };
                tx.execute("INSERT INTO babylon_state.event_key_lookup_v1(campaign_id,key_id,first_tick,value) VALUES($1,$2,1,$3)",&[campaign.as_uuid(),&id,&&[value][..]]).unwrap();
            }
        }
        if matches!(case, "missing_key" | "future_key") {
            let key = if case == "missing_key" { 999_i64 } else { 0 };
            tx.execute("INSERT INTO babylon_state.event_field_chunk_v1(campaign_id,resolve_tick,chunk,value_tag,event_ordinals,positions,name_ids,key_ids) VALUES($1,1,0,8,ARRAY[0::bigint],ARRAY[0::bigint],ARRAY[1::bigint],ARRAY[$2::bigint])",&[campaign.as_uuid(),&key]).unwrap();
        }
        if matches!(
            case,
            "missing_node_name"
                | "missing_node_scenario"
                | "future_node_name"
                | "future_node_scenario"
        ) {
            let head:i64=tx.query_one("SELECT count(*) FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1",&[campaign.as_uuid()]).unwrap().get(0);
            let scenario_tick = if case == "future_node_scenario" {
                2_i64
            } else {
                1
            };
            let name_tick = if case == "future_node_name" { 2_i64 } else { 1 };
            tx.execute("INSERT INTO babylon_state.graph_string_lookup_v1(campaign_id,string_id,first_tick,value) VALUES($1,$2,$3,$4),($1,$5,$6,$7)",&[campaign.as_uuid(),&head,&scenario_tick,&format!("proof-{case}"),&(head+1),&name_tick,&format!("name-{case}")]).unwrap();
            let scenario = if case == "missing_node_scenario" {
                i64::MAX
            } else {
                head
            };
            let name = if case == "missing_node_name" {
                i64::MAX
            } else {
                head + 1
            };
            tx.execute("INSERT INTO babylon_state.event_field_chunk_v1(campaign_id,resolve_tick,chunk,value_tag,event_ordinals,positions,name_ids,key_ids,key_scenario_ids) VALUES($1,1,0,7,ARRAY[0::bigint],ARRAY[0::bigint],ARRAY[1::bigint],ARRAY[$2::bigint],ARRAY[$3::bigint])",&[campaign.as_uuid(),&name,&scenario]).unwrap();
        }
        if case == "key_wrong_kind" {
            let key = babylon_graph::stable_element::StableElementKey::Edge {
                scenario: "proof".into(),
                edge_type: "member-of".into(),
                source_local_name: "member".into(),
                target_local_name: "group".into(),
            }
            .canonical_bytes()
            .unwrap();
            tx.execute("INSERT INTO babylon_state.event_key_lookup_v1(campaign_id,key_id,first_tick,value) VALUES($1,0,1,$2)",&[campaign.as_uuid(),&key]).unwrap();
            tx.execute("INSERT INTO babylon_state.event_field_chunk_v1(campaign_id,resolve_tick,chunk,value_tag,event_ordinals,positions,name_ids,key_ids) VALUES($1,1,0,8,ARRAY[0::bigint],ARRAY[0::bigint],ARRAY[1::bigint],ARRAY[0::bigint])",&[campaign.as_uuid()]).unwrap();
        }
    }

    fn insert_case(tx: &mut impl GenericClient, campaign: CampaignId, case: &str) {
        if case != "manifest" {
            let fields = if matches!(case, "duplicate_name" | "name_order") {
                2_i64
            } else {
                i64::from(matches!(
                    case,
                    "missing_key"
                        | "future_key"
                        | "missing_node_name"
                        | "missing_node_scenario"
                        | "future_node_name"
                        | "future_node_scenario"
                        | "key_wrong_kind"
                ))
            };
            let events = i64::from(case != "empty");
            let parent_chunks = i64::from(!matches!(case, "empty" | "parent_count"));
            let declared_fields = if case == "field_count" { 1 } else { fields };
            let field_chunks = i64::from(fields > 0);
            tx.execute(
                "INSERT INTO babylon_state.event_manifest_v1 VALUES($1,1,$2,$3,$4,$5)",
                &[
                    campaign.as_uuid(),
                    &events,
                    &declared_fields,
                    &parent_chunks,
                    &field_chunks,
                ],
            )
            .unwrap();
            if parent_chunks > 0 {
                let first_tick = if case == "future_text" { 2_i64 } else { 1 };
                tx.execute("INSERT INTO babylon_state.event_text_lookup_v1 VALUES($1,0,$2,DEFAULT,'type'),($1,1,1,DEFAULT,'z'),($1,2,1,DEFAULT,'a')",&[campaign.as_uuid(),&first_tick]).unwrap();
                let type_id = if case == "missing_text" { 999_i64 } else { 0 };
                let choice = if matches!(case, "wrong_choice" | "current_choice") {
                    Some(0_i64)
                } else {
                    None
                };
                tx.execute("INSERT INTO babylon_state.event_parent_chunk_v1 VALUES($1,1,0,ARRAY[0::bigint],ARRAY[$2::bigint],ARRAY[0::bigint],ARRAY[$3::bigint])",&[campaign.as_uuid(),&type_id,&choice]).unwrap();
                if matches!(case, "duplicate_text" | "text_gap") {
                    let id = if case == "text_gap" { 4_i64 } else { 3 };
                    let value = if case == "duplicate_text" {
                        "type"
                    } else {
                        "gap"
                    };
                    tx.execute("INSERT INTO babylon_state.event_text_lookup_v1(campaign_id,text_id,first_tick,value) VALUES($1,$2,1,$3)",&[campaign.as_uuid(),&id,&value]).unwrap();
                }
                insert_key_case(tx, campaign, case);
                if fields == 2 {
                    let second = if case == "duplicate_name" { 1_i64 } else { 2 };
                    tx.execute("INSERT INTO babylon_state.event_field_chunk_v1(campaign_id,resolve_tick,chunk,value_tag,event_ordinals,positions,name_ids,int_values) VALUES($1,1,0,1,ARRAY[0,0]::bigint[],ARRAY[0,1]::bigint[],ARRAY[1::bigint,$2::bigint],ARRAY[7,8]::bigint[])",&[campaign.as_uuid(),&second]).unwrap();
                }
                if choice.is_some() {
                    let tick = if case == "wrong_choice" { 2_i64 } else { 1 };
                    tx.execute("INSERT INTO babylon_state.tick_choice_receipt_v1 VALUES($1,$2,0,'sql-control','sql-control',0,'sql-control',$3,0,'sql-control',$4,$4)",&[campaign.as_uuid(),&tick,&&[1_u8][..],&&[1_u8;32][..]]).unwrap();
                }
            }
        }
    }

    const CASES: [(&str, Option<&str>); 21] = [
        ("manifest", Some("event_storage_manifest_missing")),
        (
            "parent_count",
            Some("event_storage_parent_chunk_count_or_gap"),
        ),
        (
            "field_count",
            Some("event_storage_field_chunk_count_or_gap"),
        ),
        (
            "missing_text",
            Some("event_storage_parent_field_choice_or_order"),
        ),
        ("future_text", Some("event_storage_lookup_reference")),
        (
            "missing_key",
            Some("event_storage_parent_field_choice_or_order"),
        ),
        ("future_key", Some("event_storage_lookup_reference")),
        (
            "duplicate_text",
            Some("event_storage_text_lookup_duplicate_or_gap"),
        ),
        (
            "text_gap",
            Some("event_storage_text_lookup_duplicate_or_gap"),
        ),
        (
            "duplicate_key",
            Some("event_storage_key_lookup_duplicate_or_gap"),
        ),
        ("key_gap", Some("event_storage_key_lookup_duplicate_or_gap")),
        (
            "duplicate_name",
            Some("event_storage_parent_field_choice_or_order"),
        ),
        (
            "name_order",
            Some("event_storage_parent_field_choice_or_order"),
        ),
        (
            "wrong_choice",
            Some("event_storage_parent_field_choice_or_order"),
        ),
        ("current_choice", None),
        ("empty", None),
        (
            "missing_node_name",
            Some("event_storage_parent_field_choice_or_order"),
        ),
        (
            "missing_node_scenario",
            Some("event_storage_parent_field_choice_or_order"),
        ),
        ("future_node_name", Some("event_storage_lookup_reference")),
        (
            "future_node_scenario",
            Some("event_storage_lookup_reference"),
        ),
        ("key_wrong_kind", Some("event_storage_key_kind")),
    ];

    // SQL relational controls only: all placeholder material/choice/key bytes
    // remain uncommitted. Native canonical validation is tested separately.
    #[test]
    #[ignore = "requires the task-owned disposable PostgreSQL runtime"]
    fn live_event_deferred_marker_integrity_table() {
        let mut config = validated_base_config();
        let database = std::env::var("BABYLON_EVENT_COPY_DATABASE").unwrap();
        assert!(database.starts_with("per337_event_continuity_"));
        config.dbname(&database);
        let foundation = crate::michigan_content::MichiganContentPreset::new_campaign(
            crate::michigan_material::MichiganDeliveryPreset::Standard,
        )
        .create_foundation(&crate::test_support::catalog())
        .unwrap();
        let campaign = CampaignId::from_uuid(Uuid::from_u128(
            (u128::from(std::process::id()) << 64) | 0x337_e1ad,
        ));
        let runtime =
            crate::material_runtime::DurableMaterialRuntime::create(&config, campaign, foundation)
                .unwrap();
        let mut client = config.connect(NoTls).unwrap();
        let relations = [
            "event_text_lookup_v1",
            "event_key_lookup_v1",
            "event_manifest_v1",
            "event_parent_chunk_v1",
            "event_field_chunk_v1",
            "tick_choice_receipt_v1",
            "tick_commit",
            "material_tick_v3",
            "graph_node_manifest_v1",
            "territory_tick_manifest_v1",
            "territory_tick_membership_v1",
        ];
        let counts = |c: &mut postgres::Client| -> Vec<i64> {
            relations
                .iter()
                .map(|r| {
                    c.query_one(
                        &format!("SELECT count(*) FROM babylon_state.{r} WHERE campaign_id=$1"),
                        &[campaign.as_uuid()],
                    )
                    .unwrap()
                    .try_get(0)
                    .unwrap()
                })
                .collect()
        };
        let before = counts(&mut client);
        assert_eq!(
            &before[..2],
            &[0, 0],
            "fresh foundation has no event lookups"
        );
        for (case, expected) in CASES {
            let mut tx = client.transaction().unwrap();
            insert_case(&mut tx, campaign, case);
            insert_event_test_marker(&mut tx, campaign);
            let result = tx.batch_execute(
                "SET CONSTRAINTS babylon_state.event_storage_marker_complete_v1 IMMEDIATE",
            );
            if let Some(message) = expected {
                let error = result.expect_err(case);
                let db = error.as_db_error().unwrap();
                assert_eq!(
                    db.code(),
                    &postgres::error::SqlState::RAISE_EXCEPTION,
                    "{case}"
                );
                assert_eq!(db.message(), message, "{case}");
            } else {
                result.unwrap();
            }
            tx.rollback().unwrap();
            assert_eq!(counts(&mut client), before, "{case}");
        }
        assert_eq!(runtime.campaign_id(), campaign);
    }
}
