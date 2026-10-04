//! Node identity shares exact scenario/name strings, never graph tuple IDs.
use super::{db, load_matching, refuse, Error, KeyReference, KeyReferences, Lookup, CHUNK};
use crate::{identity::CampaignId, runtime::RustPersistenceRuntimeError};
use babylon_graph::stable_element::StableElementKey;
use postgres::{
    binary_copy::BinaryCopyInWriter,
    fallible_iterator::FallibleIterator as _,
    types::{ToSql, Type},
    GenericClient,
};
use std::collections::{BTreeMap, BTreeSet};

type SplitKeys = (
    BTreeMap<Vec<u8>, (String, String)>,
    BTreeSet<Vec<u8>>,
    BTreeSet<String>,
);
fn split_keys(wanted: &BTreeSet<Vec<u8>>) -> Result<SplitKeys, RustPersistenceRuntimeError> {
    let mut nodes = BTreeMap::new();
    let mut literal = BTreeSet::new();
    let mut strings = BTreeSet::new();
    for bytes in wanted {
        match StableElementKey::from_canonical_bytes(bytes).map_err(|_| refuse(Error::StableKey))? {
            StableElementKey::Node {
                scenario,
                local_name,
            } => {
                strings.insert(scenario.clone());
                strings.insert(local_name.clone());
                nodes.insert(bytes.clone(), (scenario, local_name));
            }
            StableElementKey::Edge { .. } | StableElementKey::Hyperedge { .. } => {
                literal.insert(bytes.clone());
            }
        }
    }
    Ok((nodes, literal, strings))
}
fn string_head(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
) -> Result<i64, RustPersistenceRuntimeError> {
    let row=client.query_one("SELECT count(*),coalesce(max(string_id),-1),coalesce(max(first_tick),0) FROM babylon_state.graph_string_lookup_v1 WHERE campaign_id=$1",&[campaign.as_uuid()]).map_err(|e|db("read shared event string head",&e))?;
    let count: i64 = row
        .try_get(0)
        .map_err(|e| db("decode shared event string count", &e))?;
    let maximum: i64 = row
        .try_get(1)
        .map_err(|e| db("decode shared event string tail", &e))?;
    let introduced: i64 = row
        .try_get(2)
        .map_err(|e| db("decode shared event string introduction", &e))?;
    if count < 0 || count.checked_sub(1) != Some(maximum) {
        return Err(refuse(Error::DictionaryGap));
    }
    if introduced > tick {
        return Err(refuse(Error::FutureReference));
    }
    Ok(count)
}
fn matching_strings(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    count: i64,
    wanted: &BTreeSet<String>,
) -> Result<BTreeMap<String, i64>, RustPersistenceRuntimeError> {
    let mut result = BTreeMap::new();
    let wanted: Vec<_> = wanted.iter().collect();
    for batch in wanted.chunks(CHUNK) {
        let values: Vec<String> = batch.iter().map(|s| (**s).clone()).collect();
        // MD5 is the existing fixed-size nonunique index bucket, never identity.
        let parameters: [&(dyn ToSql + Sync); 2] = [campaign.as_uuid(), &values];
        let mut rows=client.query_raw("SELECT t.string_id,t.value,t.first_tick FROM babylon_state.graph_string_lookup_v1 t JOIN unnest($2::text[]) n(value) ON t.campaign_id=$1 AND pg_catalog.md5(t.value)=pg_catalog.md5(n.value) AND t.value=n.value COLLATE pg_catalog.\"C\"", parameters).map_err(|e|db("read shared event string subset",&e))?;
        while let Some(row) = rows
            .next()
            .map_err(|e| db("stream shared event strings", &e))?
        {
            let id: i64 = row
                .try_get(0)
                .map_err(|e| db("decode shared event string ID", &e))?;
            let value: String = row
                .try_get(1)
                .map_err(|e| db("decode shared event string value", &e))?;
            let first: i64 = row
                .try_get(2)
                .map_err(|e| db("decode shared event string origin", &e))?;
            if id < 0 || id >= count {
                return Err(refuse(Error::DictionaryGap));
            }
            if first > tick {
                return Err(refuse(Error::FutureReference));
            }
            if result.insert(value, id).is_some() {
                return Err(refuse(Error::DictionaryDuplicate));
            }
        }
    }
    Ok(result)
}
fn intern_strings(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    wanted: &BTreeSet<String>,
) -> Result<BTreeMap<String, i64>, RustPersistenceRuntimeError> {
    let prior = string_head(client, campaign, tick)?;
    let mut strings = matching_strings(client, campaign, tick, prior, wanted)?;
    let mut next = prior;
    let sink=client.copy_in("COPY babylon_state.graph_string_lookup_v1(campaign_id,string_id,first_tick,value) FROM STDIN BINARY").map_err(|e|db("begin shared event strings",&e))?;
    let mut writer =
        BinaryCopyInWriter::new(sink, &[Type::UUID, Type::INT8, Type::INT8, Type::TEXT]);
    for value in wanted {
        if !strings.contains_key(value) {
            let id = next;
            next = next
                .checked_add(1)
                .ok_or_else(|| refuse(Error::IdentityOverflow))?;
            writer
                .write(&[campaign.as_uuid(), &id, &tick, value])
                .map_err(|e| db("write shared event string", &e))?;
            strings.insert(value.clone(), id);
        }
    }
    writer
        .finish()
        .map_err(|e| db("finish shared event strings", &e))?;
    Ok(strings)
}
// Caller holds the campaign graph lock before the event marker lock. No query
// per identity and no complete lifetime dictionary is loaded into native memory.
pub(super) fn admit(
    client: &mut impl GenericClient,
    campaign: CampaignId,
    tick: i64,
    wanted: &BTreeSet<Vec<u8>>,
) -> Result<(KeyReferences, i64), RustPersistenceRuntimeError> {
    client.query_one("SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.graph-lookup.v1:'||$1::uuid::text,0))",&[campaign.as_uuid()]).map_err(|e|db("lock shared event string campaign",&e))?;
    client.query_one("SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('babylon.event-marker.v1:'||$1::uuid::text||':'||$2::bigint::text,0))",&[campaign.as_uuid(),&tick]).map_err(|e|db("lock shared event string marker",&e))?;
    let (nodes, literal, wanted_strings) = split_keys(wanted)?;
    let strings = intern_strings(client, campaign, tick, &wanted_strings)?;
    let (mut literal_refs, prior) = load_matching(client, campaign, tick, Lookup::Key, &literal)?;
    let mut next = prior;
    for value in literal {
        if let std::collections::btree_map::Entry::Vacant(entry) = literal_refs.entry(value) {
            entry.insert(next);
            next = next
                .checked_add(1)
                .ok_or_else(|| refuse(Error::IdentityOverflow))?;
        }
    }
    let mut refs: KeyReferences = literal_refs
        .into_iter()
        .map(|(key, id)| (key, KeyReference::Literal(id)))
        .collect();
    for (bytes, (scenario, name)) in nodes {
        let scenario = *strings
            .get(&scenario)
            .ok_or_else(|| refuse(Error::MissingReference))?;
        let name = *strings
            .get(&name)
            .ok_or_else(|| refuse(Error::MissingReference))?;
        refs.insert(bytes, KeyReference::Node { scenario, name });
    }
    Ok((refs, prior))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn node_recipe_preserves_foreign_scope_and_all_other_key_kinds() {
        let values = [
            StableElementKey::Node {
                scenario: "first".into(),
                local_name: "same".into(),
            },
            StableElementKey::Node {
                scenario: "foreign".into(),
                local_name: "same".into(),
            },
            StableElementKey::Hyperedge {
                scenario: "first".into(),
                local_name: "same".into(),
            },
            StableElementKey::Edge {
                scenario: "foreign".into(),
                edge_type: "member-of".into(),
                source_local_name: "same".into(),
                target_local_name: "other".into(),
            },
        ];
        let wanted = values
            .iter()
            .map(|k| k.canonical_bytes().unwrap())
            .collect();
        let (nodes, literal, strings) = split_keys(&wanted).unwrap();
        assert_eq!(nodes.len(), 2);
        assert_eq!(literal.len(), 2);
        assert!(strings.contains("foreign"));
        for (bytes, (scenario, local_name)) in nodes {
            assert_eq!(
                StableElementKey::Node {
                    scenario,
                    local_name
                }
                .canonical_bytes()
                .unwrap(),
                bytes
            );
        }
        for value in &values[2..] {
            assert!(literal.contains(&value.canonical_bytes().unwrap()));
        }
        assert!(split_keys(&BTreeSet::from([vec![1, 2, 3]])).is_err());
    }
}
