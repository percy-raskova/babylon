//! Exact campaign-owned dictionaries and bounded node chunks. Caller holds the
//! campaign writer lock and inserts the durable marker last in this transaction.
use crate::identity::CampaignId;
use crate::runtime::RustPersistenceRuntimeError;
use babylon_graph::stable_state::{MAX_STABLE_GRAPH_ATTRIBUTES, MAX_STABLE_GRAPH_NODES};
use postgres::binary_copy::BinaryCopyInWriter;
use postgres::types::Type;
use postgres::GenericClient;

use postgres::Error as PostgresError;
use std::collections::{BTreeMap, BTreeSet};
const CHUNK: usize = 4096;
/// Exact graph storage admission failures.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    /// Node rows exceed current stable graph admission.
    NodeLimit,
    /// Attribute rows exceed current stable graph admission.
    AttributeLimit,
    /// A local name has multiple current node rows.
    DuplicateNode,
    /// A node and qualified name occur more than once.
    DuplicateAttribute,
    /// An attribute refers to an absent current node.
    MissingNode,
    /// Persisted dictionary IDs are not contiguous from zero.
    DictionaryGap,
    /// Persisted dictionary identities are not unique.
    DictionaryDuplicate,
    /// A required dictionary identity is missing.
    DictionaryReference,
    /// A count or reference exceeds `PostgreSQL` bigint.
    IdentityOverflow,
    /// An immutable vector is absent or comes from an uncommitted future period.
    VectorReference,
}
fn validate(nodes: &[(String, String)], values: &[(String, String, u64)]) -> Result<(), Error> {
    if nodes.len() > MAX_STABLE_GRAPH_NODES {
        return Err(Error::NodeLimit);
    }
    if values.len() > MAX_STABLE_GRAPH_ATTRIBUTES {
        return Err(Error::AttributeLimit);
    }
    let names: BTreeSet<_> = nodes.iter().map(|(name, _)| name).collect();
    if names.len() != nodes.len() {
        return Err(Error::DuplicateNode);
    }
    let mut keys = BTreeSet::new();
    for (name, qname, _) in values {
        if !names.contains(name) {
            return Err(Error::MissingNode);
        }
        if !keys.insert((name, qname)) {
            return Err(Error::DuplicateAttribute);
        }
    }
    Ok(())
}
fn refused(error: Error) -> RustPersistenceRuntimeError {
    RustPersistenceRuntimeError::GraphStorage(error)
}
fn next_id(count: usize) -> Result<i64, RustPersistenceRuntimeError> {
    i64::try_from(count).map_err(|_| refused(Error::IdentityOverflow))
}

type AttributeChunk = (i64, i64, Vec<i64>, Vec<i64>);
struct Packed {
    nodes: Vec<Vec<i64>>,
    values: Vec<AttributeChunk>,
}
fn string_id(
    strings: &BTreeMap<String, i64>,
    value: &str,
) -> Result<i64, RustPersistenceRuntimeError> {
    strings
        .get(value)
        .copied()
        .ok_or_else(|| refused(Error::DictionaryReference))
}
fn pack(
    nodes: &[(String, String)],
    values: &[(String, String, u64)],
    strings: &BTreeMap<String, i64>,
    tuples: &BTreeMap<(i64, i64), i64>,
) -> Result<Packed, RustPersistenceRuntimeError> {
    let mut by_name = BTreeMap::new();
    for (name, kind) in nodes {
        let key = (string_id(strings, name)?, string_id(strings, kind)?);
        let id = tuples
            .get(&key)
            .copied()
            .ok_or_else(|| refused(Error::DictionaryReference))?;
        by_name.insert(name.as_str(), id);
    }
    let ids: Vec<_> = by_name.values().copied().collect();
    let mut grouped = BTreeMap::<i64, Vec<(&str, u64)>>::new();
    for (name, qname, bits) in values {
        grouped
            .entry(string_id(strings, qname)?)
            .or_default()
            .push((name, *bits));
    }
    let mut packed = Packed {
        nodes: ids.chunks(CHUNK).map(<[i64]>::to_vec).collect(),
        values: Vec::new(),
    };
    for (qname, mut rows) in grouped {
        rows.sort_unstable_by_key(|(name, _)| *name);
        for (ordinal, chunk) in rows.chunks(CHUNK).enumerate() {
            let ids = chunk
                .iter()
                .map(|(name, _)| {
                    by_name
                        .get(name)
                        .copied()
                        .ok_or_else(|| refused(Error::MissingNode))
                })
                .collect::<Result<Vec<_>, _>>()?;
            packed.values.push((
                qname,
                next_id(ordinal)?,
                ids,
                chunk
                    .iter()
                    .map(|(_, bits)| i64::from_ne_bytes(bits.to_ne_bytes()))
                    .collect(),
            ));
        }
    }
    Ok(packed)
}

fn db(operation: &'static str, error: &PostgresError) -> RustPersistenceRuntimeError {
    RustPersistenceRuntimeError::postgres(operation, error)
}

pub(crate) fn insert(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    nodes: &[(String, String)],
    values: &[(String, String, u64)],
) -> Result<(), RustPersistenceRuntimeError> {
    let Dictionaries { strings, tuples } = intern_inputs(client, campaign, tick, nodes, values)?;
    let packed = pack(nodes, values, &strings, &tuples)?;
    insert_chunks(client, campaign, tick, &packed)?;
    insert_manifest(client, campaign, tick, nodes.len(), values.len(), &packed)
}
struct Dictionaries {
    strings: BTreeMap<String, i64>,
    tuples: BTreeMap<(i64, i64), i64>,
}
/// Seed only the exact opening graph identities; no tick-zero memberships exist.
pub(crate) fn seed(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    nodes: &[(String, String)],
    values: &[(String, String, u64)],
) -> Result<(), RustPersistenceRuntimeError> {
    intern_inputs(client, campaign, 0, nodes, values)?;
    Ok(())
}
fn intern_inputs(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    nodes: &[(String, String)],
    values: &[(String, String, u64)],
) -> Result<Dictionaries, RustPersistenceRuntimeError> {
    validate(nodes, values).map_err(refused)?;
    let wanted = nodes
        .iter()
        .flat_map(|(name, kind)| [name.as_str(), kind.as_str()])
        .chain(values.iter().map(|(_, qname, _)| qname.as_str()))
        .collect();
    let strings = insert_strings(client, campaign, tick, wanted)?;
    let tuples = insert_nodes(client, campaign, tick, nodes, &strings)?;
    Ok(Dictionaries { strings, tuples })
}
fn insert_strings(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    wanted: BTreeSet<&str>,
) -> Result<BTreeMap<String, i64>, RustPersistenceRuntimeError> {
    // Exact UTF-8 values are lookup keys; no digest or collation-derived identity.
    let mut strings = BTreeMap::<String, i64>::new();
    for row in client.query("SELECT string_id, value FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1 ORDER BY string_id", &[campaign.as_uuid()]).map_err(|e| db("load graph strings", &e))? {
        let id: i64 = row.try_get(0).map_err(|e| db("decode graph lookup id", &e))?;
        if id != next_id(strings.len())? { return Err(refused(Error::DictionaryGap)); }
        if strings.insert(row.try_get(1).map_err(|e| db("decode graph string", &e))?,id).is_some() { return Err(refused(Error::DictionaryDuplicate)); }
    }
    let sink = client.copy_in("COPY babylon_state.graph_string_lookup_v1 (campaign_id,string_id,first_tick,value) FROM STDIN BINARY").map_err(|e| db("begin graph strings", &e))?;
    let mut writer =
        BinaryCopyInWriter::new(sink, &[Type::UUID, Type::INT8, Type::INT8, Type::TEXT]);
    for value in wanted {
        if !strings.contains_key(value) {
            let id = next_id(strings.len())?;
            writer
                .write(&[campaign.as_uuid(), &id, &tick, &value])
                .map_err(|e| db("write graph string", &e))?;
            strings.insert(value.to_owned(), id);
        }
    }
    writer
        .finish()
        .map_err(|e| db("finish graph strings", &e))?;
    Ok(strings)
}
fn insert_nodes(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    nodes: &[(String, String)],
    strings: &BTreeMap<String, i64>,
) -> Result<BTreeMap<(i64, i64), i64>, RustPersistenceRuntimeError> {
    let mut tuples = BTreeMap::<(i64, i64), i64>::new();
    for row in client.query("SELECT node_id,name_id,type_id FROM babylon_state.graph_node_lookup_v1 WHERE campaign_id=$1 ORDER BY node_id", &[campaign.as_uuid()]).map_err(|e| db("load graph tuples", &e))? {
        let id: i64 = row.try_get(0).map_err(|e| db("decode graph lookup id", &e))?;
        if id != next_id(tuples.len())? { return Err(refused(Error::DictionaryGap)); }
        if tuples.insert((row.try_get(1).map_err(|e| db("decode graph name id", &e))?,row.try_get(2).map_err(|e| db("decode graph type id", &e))?),id).is_some() { return Err(refused(Error::DictionaryDuplicate)); }
    }
    let sink = client.copy_in("COPY babylon_state.graph_node_lookup_v1 (campaign_id,node_id,first_tick,name_id,type_id) FROM STDIN BINARY").map_err(|e| db("begin graph tuples", &e))?;
    let mut writer = BinaryCopyInWriter::new(
        sink,
        &[Type::UUID, Type::INT8, Type::INT8, Type::INT8, Type::INT8],
    );
    // Assign additions in exact tuple order, independently of input row order.
    let wanted: BTreeSet<_> = nodes
        .iter()
        .map(|(name, kind)| Ok((string_id(strings, name)?, string_id(strings, kind)?)))
        .collect::<Result<_, RustPersistenceRuntimeError>>()?;
    for key in wanted {
        let id = next_id(tuples.len())?;
        if let std::collections::btree_map::Entry::Vacant(entry) = tuples.entry(key) {
            writer
                .write(&[campaign.as_uuid(), &id, &tick, &key.0, &key.1])
                .map_err(|e| db("write graph tuple", &e))?;
            entry.insert(id);
        }
    }
    writer.finish().map_err(|e| db("finish graph tuples", &e))?;
    Ok(tuples)
}
fn vector_inputs(packed: &Packed) -> BTreeSet<&Vec<i64>> {
    packed
        .nodes
        .iter()
        .chain(packed.values.iter().map(|(_, _, ids, _)| ids))
        .collect()
}
fn intern_vectors(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    packed: &Packed,
) -> Result<BTreeMap<Vec<i64>, i64>, RustPersistenceRuntimeError> {
    // The same lock used by dictionaries and the marker serializes exact lookup
    // insertion. The hash index narrows candidates; full ordered arrays decide.
    client.query_one("SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.graph-lookup.v1:'||$1::uuid::text,0))", &[campaign.as_uuid()])
        .map_err(|e| db("lock graph vectors", &e))?;
    let row = client.query_one("SELECT count(*),coalesce(max(vector_id),-1) FROM babylon_state.graph_node_vector_v1 WHERE campaign_id=$1", &[campaign.as_uuid()])
        .map_err(|e| db("count graph vectors", &e))?;
    let mut next: i64 = row.try_get(0).map_err(|e| db("decode vector count", &e))?;
    let maximum: i64 = row
        .try_get(1)
        .map_err(|e| db("decode vector maximum", &e))?;
    if maximum.checked_add(1) != Some(next) {
        return Err(refused(Error::DictionaryGap));
    }
    let mut vectors = BTreeMap::new();
    for ids in vector_inputs(packed) {
        let matches = client.query("SELECT v.vector_id,v.first_tick,EXISTS(SELECT 1 FROM babylon_state.tick_commit m WHERE m.campaign_id=v.campaign_id AND m.resolve_tick=v.first_tick) FROM babylon_state.graph_node_vector_v1 v WHERE v.campaign_id=$1 AND v.node_ids=$2::bigint[]", &[campaign.as_uuid(), ids])
            .map_err(|e| db("match exact graph vector", &e))?;
        if matches.len() > 1 {
            return Err(refused(Error::DictionaryDuplicate));
        }
        let vector_id = if let Some(row) = matches.first() {
            let first_tick: i64 = row.try_get(1).map_err(|e| db("decode vector origin", &e))?;
            let committed: bool = row.try_get(2).map_err(|e| db("decode vector marker", &e))?;
            if first_tick > tick || (first_tick != tick && !committed) {
                return Err(refused(Error::VectorReference));
            }
            row.try_get(0).map_err(|e| db("decode vector id", &e))?
        } else {
            let vector_id = next;
            next = next
                .checked_add(1)
                .ok_or_else(|| refused(Error::IdentityOverflow))?;
            client.execute("INSERT INTO babylon_state.graph_node_vector_v1(campaign_id,vector_id,first_tick,node_ids) VALUES($1,$2,$3,$4)", &[campaign.as_uuid(), &vector_id, &tick, ids])
                .map_err(|e| db("write graph vector", &e))?;
            vector_id
        };
        vectors.insert(ids.clone(), vector_id);
    }
    Ok(vectors)
}
fn insert_chunks(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    packed: &Packed,
) -> Result<(), RustPersistenceRuntimeError> {
    let vectors = intern_vectors(client, campaign, tick, packed)?;
    let sink = client.copy_in("COPY babylon_state.graph_node_chunk_v1 (campaign_id,resolve_tick,ordinal,vector_id) FROM STDIN BINARY").map_err(|e| db("begin graph node chunks", &e))?;
    let mut writer =
        BinaryCopyInWriter::new(sink, &[Type::UUID, Type::INT8, Type::INT8, Type::INT8]);
    for (ordinal, chunk) in packed.nodes.iter().enumerate() {
        let vector = vectors
            .get(chunk)
            .ok_or_else(|| refused(Error::VectorReference))?;
        writer
            .write(&[campaign.as_uuid(), &tick, &next_id(ordinal)?, vector])
            .map_err(|e| db("write graph node chunk", &e))?;
    }
    writer
        .finish()
        .map_err(|e| db("finish graph node chunks", &e))?;
    let sink = client.copy_in("COPY babylon_state.graph_node_f64_chunk_v1 (campaign_id,resolve_tick,qname_id,ordinal,vector_id,value_bits) FROM STDIN BINARY").map_err(|e| db("begin graph f64 chunks", &e))?;
    let mut writer = BinaryCopyInWriter::new(
        sink,
        &[
            Type::UUID,
            Type::INT8,
            Type::INT8,
            Type::INT8,
            Type::INT8,
            Type::INT8_ARRAY,
        ],
    );
    for (qname, ordinal, ids, bits) in &packed.values {
        let vector = vectors
            .get(ids)
            .ok_or_else(|| refused(Error::VectorReference))?;
        writer
            .write(&[campaign.as_uuid(), &tick, qname, ordinal, vector, bits])
            .map_err(|e| db("write graph f64 chunk", &e))?;
    }
    writer
        .finish()
        .map_err(|e| db("finish graph f64 chunks", &e))?;
    Ok(())
}
fn insert_manifest(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    node_count: usize,
    value_count: usize,
    packed: &Packed,
) -> Result<(), RustPersistenceRuntimeError> {
    client
        .execute(
            "INSERT INTO babylon_state.graph_node_manifest_v1 VALUES ($1,$2,$3,$4,$5,$6)",
            &[
                campaign.as_uuid(),
                &tick,
                &next_id(node_count)?,
                &next_id(value_count)?,
                &next_id(packed.nodes.len())?,
                &next_id(packed.values.len())?,
            ],
        )
        .map_err(|e| db("write graph node manifest", &e))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_vectors_share_only_complete_ordered_arrays_and_keep_boundaries() {
        let packed = Packed {
            nodes: vec![(0..4096).collect(), vec![4096]],
            values: vec![
                (0, 0, (0..4096).collect(), vec![0; 4096]),
                (1, 0, vec![4096], vec![i64::MIN]),
                (2, 0, vec![4096, 0], vec![0, i64::MIN]),
            ],
        };
        let unique = vector_inputs(&packed);
        assert_eq!(unique.len(), 3);
        assert!(unique.contains(&vec![4096, 0]));
        assert!(!unique.contains(&vec![0, 4096]));
        assert_eq!(packed.values[1].3, vec![i64::MIN]);
        let empty = Packed {
            nodes: vec![],
            values: vec![],
        };
        assert!(vector_inputs(&empty).is_empty());
        let changed = Packed {
            nodes: vec![vec![0, 2]],
            values: vec![],
        };
        assert_ne!(vector_inputs(&changed), BTreeSet::from([&vec![0, 1]]));
    }
    #[test]
    fn graph_chunks_refuse_missing_and_duplicate_nodes() {
        let nodes = vec![("a".into(), "kind".into())];
        assert_eq!(
            validate(&nodes, &[("missing".into(), "q".into(), 0)]),
            Err(Error::MissingNode)
        );
        assert_eq!(
            validate(&[nodes[0].clone(), nodes[0].clone()], &[]),
            Err(Error::DuplicateNode)
        );
        let row = ("a".into(), "q".into(), 1);
        assert_eq!(
            validate(&nodes, &[row.clone(), row]),
            Err(Error::DuplicateAttribute)
        );
    }
    #[test]
    fn graph_chunks_exact_inverse_and_order() {
        let strings: BTreeMap<String, i64> =
            [("A", 0), ("a", 1), ("type1", 2), ("type2", 3), ("q", 4)]
                .into_iter()
                .map(|(s, id)| (s.into(), id))
                .collect();
        let tuples = BTreeMap::from([((0, 2), 0), ((0, 3), 1), ((1, 2), 2)]);
        let nodes = vec![("a".into(), "type1".into()), ("A".into(), "type2".into())];
        let values = vec![
            ("a".into(), "q".into(), u64::MAX),
            ("A".into(), "q".into(), 1 << 63),
        ];
        let p = pack(&nodes, &values, &strings, &tuples).unwrap();
        assert_eq!(p.nodes, vec![vec![1, 2]]);
        let inverse: BTreeMap<_, _> = tuples.iter().map(|(key, id)| (*id, *key)).collect();
        let text: BTreeMap<_, _> = strings.iter().map(|(s, id)| (*id, s.clone())).collect();
        let recovered: Vec<_> = p
            .values
            .iter()
            .flat_map(|(q, _, ids, bits)| {
                ids.iter().zip(bits).map(|(id, bits)| {
                    (
                        text[&inverse[id].0].clone(),
                        text[q].clone(),
                        u64::from_ne_bytes(bits.to_ne_bytes()),
                    )
                })
            })
            .collect();
        assert_eq!(recovered, vec![values[1].clone(), values[0].clone()]);
        let mut reversed = nodes.clone();
        reversed.reverse();
        let mut reversed_values = values.clone();
        reversed_values.reverse();
        let other = pack(&reversed, &reversed_values, &strings, &tuples).unwrap();
        assert_eq!(other.nodes, p.nodes);
        assert_eq!(other.values, p.values);
    }
    #[test]
    fn graph_chunks_empty_and_bounded_positive_intersections() {
        assert_eq!(validate(&[], &[]), Ok(()));
        let ids = vec![0i64; CHUNK + 1];
        let chunks: Vec<_> = ids.chunks(CHUNK).collect();
        assert_eq!(
            chunks.iter().map(|c| c.len()).collect::<Vec<_>>(),
            vec![CHUNK, 1]
        );
    }
    #[test]
    fn packing_missing_dictionary_identity_refuses_without_panicking() {
        let nodes = vec![("a".into(), "kind".into())];
        assert!(matches!(
            pack(&nodes, &[], &BTreeMap::new(), &BTreeMap::new()),
            Err(RustPersistenceRuntimeError::GraphStorage(
                Error::DictionaryReference
            ))
        ));
    }
}
