//! Runtime-handle-free graph-state bytes and digest.

use std::collections::BTreeSet;
use std::collections::TryReserveError;

use babylon_kernel::{sha256_of, Currency};

use crate::stable_element::StableIdentityError;
use crate::stable_element::{validate_qname, StableElementKeyV1, StableElementResolverV1};
use crate::state_hash::CanonicalState;
use crate::substrate::{HyperedgeId, NodeId};

/// Stable graph-state layout version.
pub const STABLE_GRAPH_STATE_LAYOUT_VERSION_V1: u32 = 1;
/// Maximum node, edge, or hyperedge rows in stable graph state.
pub const MAX_STABLE_GRAPH_ELEMENTS_V1: usize = 65_536;
/// Maximum rows in one stable graph attribute section.
pub const MAX_STABLE_GRAPH_ATTRIBUTES_V1: usize = 524_288;
/// Maximum members in one stable hyperedge.
pub const MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS_V1: usize = 65_534;
/// Maximum rows plus nested member references in stable graph state.
pub const MAX_STABLE_GRAPH_FACT_UNITS_V1: usize = 1_048_576;
/// Maximum complete stable graph-state canonical byte length.
pub const MAX_STABLE_GRAPH_STATE_BYTES_V1: usize = 67_108_864;

const STABLE_GRAPH_DOMAIN: &[u8] = b"babylon.stable-graph";

type NodeRow = (String, String);
type NodeF64Row = (String, String, u64);
type EdgeRow = (String, String, String, u64);
type HyperedgeRow = (String, String, Vec<String>);
type EdgeF64Row = (String, String, String, String, u64);
type NodeCurrencyRow = (String, String, i128);
type HyperedgeF64Row = (String, String, u64);

struct Listings {
    nodes: Vec<(NodeId, String)>,
    node_f64: Vec<(NodeId, String, f64)>,
    edges: Vec<(String, NodeId, NodeId, f64)>,
    hyperedges: Vec<(HyperedgeId, String, Vec<NodeId>)>,
    edge_f64: Vec<(String, NodeId, NodeId, String, f64)>,
    node_currency: Vec<(NodeId, String, Currency)>,
    hyperedge_f64: Vec<(HyperedgeId, String, f64)>,
}

struct StableRows {
    nodes: Vec<NodeRow>,
    node_f64: Vec<NodeF64Row>,
    edges: Vec<EdgeRow>,
    hyperedges: Vec<HyperedgeRow>,
    edge_f64: Vec<EdgeF64Row>,
    node_currency: Vec<NodeCurrencyRow>,
    hyperedge_f64: Vec<HyperedgeF64Row>,
}

/// SHA-256 identity of exact stable graph-state bytes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct StableGraphStateHashV1([u8; 32]);

impl StableGraphStateHashV1 {
    /// Borrow the exact digest bytes.
    #[must_use]
    pub const fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }

    /// Return the exact digest bytes.
    #[must_use]
    pub const fn into_bytes(self) -> [u8; 32] {
        self.0
    }
}

/// Exact canonical stable graph-state identity.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StableGraphStateV1 {
    canonical_bytes: Vec<u8>,
    digest: StableGraphStateHashV1,
}

impl StableGraphStateV1 {
    /// Borrow the exact canonical bytes.
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8] {
        &self.canonical_bytes
    }

    /// Return SHA-256 of the exact canonical bytes.
    #[must_use]
    pub const fn digest(&self) -> StableGraphStateHashV1 {
        self.digest
    }
}

/// Encode one graph using authored stable identities rather than runtime handles.
///
/// # Errors
/// Returns the first topology, semantic, numeric, bound, arithmetic, or
/// allocation failure before exposing any partial canonical bytes.
pub fn encode_stable_graph_state_v1<G: CanonicalState>(
    graph: &G,
    resolver: &StableElementResolverV1,
) -> Result<StableGraphStateV1, StableIdentityError> {
    let listings = collect_listings(graph);
    validate_listing_bounds(&listings)?;
    resolver.validate_topology(graph)?;
    let rows = resolve_rows(&listings, resolver)?;
    let capacity = stable_state_capacity(resolver.scenario_scope(), &rows)?;
    validate_state_byte_size(capacity)?;
    let canonical_bytes = encode_rows(resolver.scenario_scope(), &rows, capacity)?;
    let digest = StableGraphStateHashV1(sha256_of(&canonical_bytes));
    Ok(StableGraphStateV1 {
        canonical_bytes,
        digest,
    })
}

fn collect_listings<G: CanonicalState>(graph: &G) -> Listings {
    Listings {
        nodes: graph.all_nodes(),
        node_f64: graph.all_attributes(),
        edges: graph.all_edges(),
        hyperedges: graph.all_hyperedges(),
        edge_f64: graph.all_edge_attributes(),
        node_currency: graph.all_currency_attributes(),
        hyperedge_f64: graph.all_hyperedge_attributes(),
    }
}

fn validate_listing_bounds(value: &Listings) -> Result<(), StableIdentityError> {
    validate_section("nodes", value.nodes.len(), MAX_STABLE_GRAPH_ELEMENTS_V1)?;
    validate_section(
        "node f64 attributes",
        value.node_f64.len(),
        MAX_STABLE_GRAPH_ATTRIBUTES_V1,
    )?;
    validate_section("edges", value.edges.len(), MAX_STABLE_GRAPH_ELEMENTS_V1)?;
    validate_section(
        "hyperedges",
        value.hyperedges.len(),
        MAX_STABLE_GRAPH_ELEMENTS_V1,
    )?;
    validate_section(
        "edge f64 attributes",
        value.edge_f64.len(),
        MAX_STABLE_GRAPH_ATTRIBUTES_V1,
    )?;
    validate_section(
        "node Currency attributes",
        value.node_currency.len(),
        MAX_STABLE_GRAPH_ATTRIBUTES_V1,
    )?;
    validate_section(
        "hyperedge f64 attributes",
        value.hyperedge_f64.len(),
        MAX_STABLE_GRAPH_ATTRIBUTES_V1,
    )?;
    let mut fact_units = listing_row_count(value)?;
    for (_, _, members) in value
        .hyperedges
        .iter()
        .take(MAX_STABLE_GRAPH_ELEMENTS_V1 + 1)
    {
        validate_section(
            "hyperedge members",
            members.len(),
            MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS_V1,
        )?;
        fact_units = checked_add("stable graph fact units", fact_units, members.len())?;
    }
    validate_fact_units(fact_units)
}

fn validate_fact_units(fact_units: usize) -> Result<(), StableIdentityError> {
    if fact_units > MAX_STABLE_GRAPH_FACT_UNITS_V1 {
        return Err(StableIdentityError::FactUnitLimit {
            actual: fact_units,
            maximum: MAX_STABLE_GRAPH_FACT_UNITS_V1,
        });
    }
    Ok(())
}

fn listing_row_count(value: &Listings) -> Result<usize, StableIdentityError> {
    let counts = [
        value.nodes.len(),
        value.node_f64.len(),
        value.edges.len(),
        value.hyperedges.len(),
        value.edge_f64.len(),
        value.node_currency.len(),
        value.hyperedge_f64.len(),
    ];
    let mut total = 0usize;
    for count in counts {
        total = checked_add("stable graph fact units", total, count)?;
    }
    Ok(total)
}

fn validate_section(
    section: &'static str,
    actual: usize,
    maximum: usize,
) -> Result<(), StableIdentityError> {
    if actual <= maximum {
        Ok(())
    } else {
        Err(StableIdentityError::StateSectionLimit {
            section,
            actual,
            maximum,
        })
    }
}

fn validate_state_byte_size(actual: usize) -> Result<(), StableIdentityError> {
    if actual <= MAX_STABLE_GRAPH_STATE_BYTES_V1 {
        Ok(())
    } else {
        Err(StableIdentityError::ByteLimit {
            field: "stable graph state",
            actual,
            maximum: MAX_STABLE_GRAPH_STATE_BYTES_V1,
        })
    }
}

fn resolve_rows(
    value: &Listings,
    resolver: &StableElementResolverV1,
) -> Result<StableRows, StableIdentityError> {
    let mut rows = StableRows {
        nodes: resolve_nodes(&value.nodes, resolver)?,
        node_f64: resolve_node_f64(&value.node_f64, resolver)?,
        edges: resolve_edges(&value.edges, resolver)?,
        hyperedges: resolve_hyperedges(&value.hyperedges, resolver)?,
        edge_f64: resolve_edge_f64(&value.edge_f64, resolver)?,
        node_currency: resolve_node_currency(&value.node_currency, resolver)?,
        hyperedge_f64: resolve_hyperedge_f64(&value.hyperedge_f64, resolver)?,
    };
    sort_and_validate(&mut rows)?;
    Ok(rows)
}

fn resolve_nodes(
    source: &[(NodeId, String)],
    resolver: &StableElementResolverV1,
) -> Result<Vec<NodeRow>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph nodes", source.len())?;
    for (node, node_type) in source.iter().take(MAX_STABLE_GRAPH_ELEMENTS_V1 + 1) {
        rows.push((
            resolver.node_local_name(*node)?.to_owned(),
            node_type.clone(),
        ));
    }
    Ok(rows)
}

fn resolve_node_f64(
    source: &[(NodeId, String, f64)],
    resolver: &StableElementResolverV1,
) -> Result<Vec<NodeF64Row>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph node attributes", source.len())?;
    for (node, qname, value) in source.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES_V1 + 1) {
        validate_qname("node attribute qname", qname)?;
        rows.push((
            resolver.node_local_name(*node)?.to_owned(),
            qname.clone(),
            finite_bits(*value, "node f64 attributes")?,
        ));
    }
    Ok(rows)
}

fn resolve_edges(
    source: &[(String, NodeId, NodeId, f64)],
    resolver: &StableElementResolverV1,
) -> Result<Vec<EdgeRow>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph edges", source.len())?;
    for (edge_type, from, to, strength) in source.iter().take(MAX_STABLE_GRAPH_ELEMENTS_V1 + 1) {
        let key = resolver.edge_key(edge_type, *from, *to)?;
        let StableElementKeyV1::Edge {
            edge_type,
            source_local_name,
            target_local_name,
            ..
        } = key
        else {
            return Err(StableIdentityError::ElementNotSealed);
        };
        rows.push((
            edge_type,
            source_local_name,
            target_local_name,
            finite_bits(*strength, "edges")?,
        ));
    }
    Ok(rows)
}

fn resolve_hyperedges(
    source: &[(HyperedgeId, String, Vec<NodeId>)],
    resolver: &StableElementResolverV1,
) -> Result<Vec<HyperedgeRow>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph hyperedges", source.len())?;
    for (hyperedge, hyperedge_type, members) in source.iter().take(MAX_STABLE_GRAPH_ELEMENTS_V1 + 1)
    {
        let StableElementKeyV1::Hyperedge { local_name, .. } =
            resolver.hyperedge_key(*hyperedge)?
        else {
            return Err(StableIdentityError::ElementNotSealed);
        };
        let mut member_names = reserve_rows("stable graph hyperedge members", members.len())?;
        for member in members
            .iter()
            .take(MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS_V1 + 1)
        {
            member_names.push(resolver.node_local_name(*member)?.to_owned());
        }
        member_names.sort_unstable();
        ensure_unique("hyperedge members", &member_names, |left, right| {
            left == right
        })?;
        rows.push((local_name.clone(), hyperedge_type.clone(), member_names));
    }
    Ok(rows)
}

fn resolve_edge_f64(
    source: &[(String, NodeId, NodeId, String, f64)],
    resolver: &StableElementResolverV1,
) -> Result<Vec<EdgeF64Row>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph edge attributes", source.len())?;
    for (edge_type, from, to, qname, value) in
        source.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES_V1 + 1)
    {
        validate_qname("edge attribute qname", qname)?;
        if qname.ends_with("/strength") {
            return Err(StableIdentityError::StrengthAttribute);
        }
        let key = resolver.edge_key(edge_type, *from, *to)?;
        let StableElementKeyV1::Edge {
            edge_type,
            source_local_name,
            target_local_name,
            ..
        } = key
        else {
            return Err(StableIdentityError::ElementNotSealed);
        };
        rows.push((
            edge_type,
            source_local_name,
            target_local_name,
            qname.clone(),
            finite_bits(*value, "edge f64 attributes")?,
        ));
    }
    Ok(rows)
}

fn resolve_node_currency(
    source: &[(NodeId, String, Currency)],
    resolver: &StableElementResolverV1,
) -> Result<Vec<NodeCurrencyRow>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph Currency attributes", source.len())?;
    for (node, qname, value) in source.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES_V1 + 1) {
        validate_qname("Currency attribute qname", qname)?;
        rows.push((
            resolver.node_local_name(*node)?.to_owned(),
            qname.clone(),
            value.micro_units(),
        ));
    }
    Ok(rows)
}

fn resolve_hyperedge_f64(
    source: &[(HyperedgeId, String, f64)],
    resolver: &StableElementResolverV1,
) -> Result<Vec<HyperedgeF64Row>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph hyperedge attributes", source.len())?;
    for (hyperedge, qname, value) in source.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES_V1 + 1) {
        validate_qname("hyperedge attribute qname", qname)?;
        let StableElementKeyV1::Hyperedge { local_name, .. } =
            resolver.hyperedge_key(*hyperedge)?
        else {
            return Err(StableIdentityError::ElementNotSealed);
        };
        rows.push((
            local_name.clone(),
            qname.clone(),
            finite_bits(*value, "hyperedge f64 attributes")?,
        ));
    }
    Ok(rows)
}

fn sort_and_validate(rows: &mut StableRows) -> Result<(), StableIdentityError> {
    rows.nodes.sort_unstable();
    ensure_unique("nodes", &rows.nodes, |left, right| left.0 == right.0)?;
    rows.node_f64
        .sort_unstable_by(|a, b| (&a.0, &a.1).cmp(&(&b.0, &b.1)));
    ensure_unique("node f64 attributes", &rows.node_f64, |left, right| {
        left.0 == right.0 && left.1 == right.1
    })?;
    rows.edges
        .sort_unstable_by(|a, b| (&a.0, &a.1, &a.2).cmp(&(&b.0, &b.1, &b.2)));
    ensure_unique("edges", &rows.edges, |left, right| {
        left.0 == right.0 && left.1 == right.1 && left.2 == right.2
    })?;
    rows.hyperedges.sort_unstable_by(|a, b| a.0.cmp(&b.0));
    ensure_unique("hyperedges", &rows.hyperedges, |left, right| {
        left.0 == right.0
    })?;
    rows.edge_f64
        .sort_unstable_by(|a, b| (&a.0, &a.1, &a.2, &a.3).cmp(&(&b.0, &b.1, &b.2, &b.3)));
    ensure_unique("edge f64 attributes", &rows.edge_f64, |left, right| {
        left.0 == right.0 && left.1 == right.1 && left.2 == right.2 && left.3 == right.3
    })?;
    rows.node_currency
        .sort_unstable_by(|a, b| (&a.0, &a.1).cmp(&(&b.0, &b.1)));
    ensure_unique(
        "node Currency attributes",
        &rows.node_currency,
        |left, right| left.0 == right.0 && left.1 == right.1,
    )?;
    rows.hyperedge_f64
        .sort_unstable_by(|a, b| (&a.0, &a.1).cmp(&(&b.0, &b.1)));
    ensure_unique(
        "hyperedge f64 attributes",
        &rows.hyperedge_f64,
        |left, right| left.0 == right.0 && left.1 == right.1,
    )?;
    validate_numeric_lanes(rows)
}

fn ensure_unique<T, F: Fn(&T, &T) -> bool>(
    section: &'static str,
    rows: &[T],
    equal_key: F,
) -> Result<(), StableIdentityError> {
    for pair in rows.windows(2).take(rows.len()) {
        if equal_key(&pair[0], &pair[1]) {
            return Err(StableIdentityError::DuplicateFact { section });
        }
    }
    Ok(())
}

fn validate_numeric_lanes(rows: &StableRows) -> Result<(), StableIdentityError> {
    let mut f64_keys = BTreeSet::new();
    for (node, qname, _) in rows
        .node_f64
        .iter()
        .take(MAX_STABLE_GRAPH_ATTRIBUTES_V1 + 1)
    {
        f64_keys.insert((node.as_str(), qname.as_str()));
    }
    for (node, qname, _) in rows
        .node_currency
        .iter()
        .take(MAX_STABLE_GRAPH_ATTRIBUTES_V1 + 1)
    {
        if f64_keys.contains(&(node.as_str(), qname.as_str())) {
            return Err(StableIdentityError::NumericLaneCollision {
                node_local_name: node.clone(),
                qname: qname.clone(),
            });
        }
    }
    Ok(())
}

fn finite_bits(value: f64, section: &'static str) -> Result<u64, StableIdentityError> {
    if !value.is_finite() {
        return Err(StableIdentityError::NonFiniteValue { section });
    }
    Ok(if value == 0.0 { 0 } else { value.to_bits() })
}

fn stable_state_capacity(scenario: &str, rows: &StableRows) -> Result<usize, StableIdentityError> {
    let mut size = checked_add("stable graph bytes", STABLE_GRAPH_DOMAIN.len(), 1 + 4)?;
    size = add_section_header(size, scenario.len())?;
    size = add_rows_capacity(size, &rows.nodes, |row| strings_capacity(&[&row.0, &row.1]))?;
    size = add_rows_capacity(size, &rows.node_f64, |row| {
        add_fixed(strings_capacity(&[&row.0, &row.1])?, 8)
    })?;
    size = add_rows_capacity(size, &rows.edges, |row| {
        add_fixed(strings_capacity(&[&row.0, &row.1, &row.2])?, 8)
    })?;
    size = add_rows_capacity(size, &rows.hyperedges, hyperedge_capacity)?;
    size = add_rows_capacity(size, &rows.edge_f64, |row| {
        add_fixed(strings_capacity(&[&row.0, &row.1, &row.2, &row.3])?, 8)
    })?;
    size = add_rows_capacity(size, &rows.node_currency, |row| {
        add_fixed(strings_capacity(&[&row.0, &row.1])?, 16)
    })?;
    add_rows_capacity(size, &rows.hyperedge_f64, |row| {
        add_fixed(strings_capacity(&[&row.0, &row.1])?, 8)
    })
}

fn add_section_header(size: usize, row_bytes: usize) -> Result<usize, StableIdentityError> {
    checked_add("stable graph bytes", size, 1 + 4 + row_bytes)
}

fn add_rows_capacity<T, F>(
    mut size: usize,
    rows: &[T],
    row_size: F,
) -> Result<usize, StableIdentityError>
where
    F: Fn(&T) -> Result<usize, StableIdentityError>,
{
    size = checked_add("stable graph bytes", size, 1 + 4)?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES_V1 + 1) {
        size = checked_add("stable graph bytes", size, row_size(row)?)?;
    }
    Ok(size)
}

fn hyperedge_capacity(row: &HyperedgeRow) -> Result<usize, StableIdentityError> {
    let mut size = add_fixed(strings_capacity(&[&row.0, &row.1])?, 4)?;
    for member in row.2.iter().take(MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS_V1 + 1) {
        size = checked_add("stable graph bytes", size, 4 + member.len())?;
    }
    Ok(size)
}

fn strings_capacity(values: &[&String]) -> Result<usize, StableIdentityError> {
    let mut size = 0usize;
    for value in values.iter().take(4) {
        size = checked_add("stable graph bytes", size, 4 + value.len())?;
    }
    Ok(size)
}

fn add_fixed(size: usize, fixed: usize) -> Result<usize, StableIdentityError> {
    checked_add("stable graph bytes", size, fixed)
}

fn encode_rows(
    scenario: &str,
    rows: &StableRows,
    capacity: usize,
) -> Result<Vec<u8>, StableIdentityError> {
    let mut output = reserve_bytes("stable graph state", capacity)?;
    output.extend_from_slice(STABLE_GRAPH_DOMAIN);
    output.push(0);
    output.extend_from_slice(&STABLE_GRAPH_STATE_LAYOUT_VERSION_V1.to_be_bytes());
    output.push(0x01);
    append_str32(&mut output, "stable graph scenario", scenario)?;
    append_nodes(&mut output, &rows.nodes)?;
    append_node_f64(&mut output, &rows.node_f64)?;
    append_edges(&mut output, &rows.edges)?;
    append_hyperedges(&mut output, &rows.hyperedges)?;
    append_edge_f64(&mut output, &rows.edge_f64)?;
    append_node_currency(&mut output, &rows.node_currency)?;
    append_hyperedge_f64(&mut output, &rows.hyperedge_f64)?;
    debug_assert_eq!(output.len(), capacity);
    Ok(output)
}

fn append_count(output: &mut Vec<u8>, tag: u8, count: usize) -> Result<(), StableIdentityError> {
    output.push(tag);
    output.extend_from_slice(&checked_u32("stable graph section count", count)?.to_be_bytes());
    Ok(())
}

fn append_nodes(output: &mut Vec<u8>, rows: &[NodeRow]) -> Result<(), StableIdentityError> {
    append_count(output, 0x02, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ELEMENTS_V1 + 1) {
        append_str32(output, "stable node name", &row.0)?;
        append_str32(output, "stable node type", &row.1)?;
    }
    Ok(())
}

fn append_node_f64(output: &mut Vec<u8>, rows: &[NodeF64Row]) -> Result<(), StableIdentityError> {
    append_count(output, 0x03, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES_V1 + 1) {
        append_str32(output, "stable node name", &row.0)?;
        append_str32(output, "stable node attribute", &row.1)?;
        output.extend_from_slice(&row.2.to_be_bytes());
    }
    Ok(())
}

fn append_edges(output: &mut Vec<u8>, rows: &[EdgeRow]) -> Result<(), StableIdentityError> {
    append_count(output, 0x04, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ELEMENTS_V1 + 1) {
        append_str32(output, "stable edge type", &row.0)?;
        append_str32(output, "stable edge source", &row.1)?;
        append_str32(output, "stable edge target", &row.2)?;
        output.extend_from_slice(&row.3.to_be_bytes());
    }
    Ok(())
}

fn append_hyperedges(
    output: &mut Vec<u8>,
    rows: &[HyperedgeRow],
) -> Result<(), StableIdentityError> {
    append_count(output, 0x05, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ELEMENTS_V1 + 1) {
        append_str32(output, "stable hyperedge name", &row.0)?;
        append_str32(output, "stable hyperedge type", &row.1)?;
        output.extend_from_slice(
            &checked_u32("stable hyperedge member count", row.2.len())?.to_be_bytes(),
        );
        for member in row.2.iter().take(MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS_V1 + 1) {
            append_str32(output, "stable hyperedge member", member)?;
        }
    }
    Ok(())
}

fn append_edge_f64(output: &mut Vec<u8>, rows: &[EdgeF64Row]) -> Result<(), StableIdentityError> {
    append_count(output, 0x06, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES_V1 + 1) {
        append_str32(output, "stable edge type", &row.0)?;
        append_str32(output, "stable edge source", &row.1)?;
        append_str32(output, "stable edge target", &row.2)?;
        append_str32(output, "stable edge attribute", &row.3)?;
        output.extend_from_slice(&row.4.to_be_bytes());
    }
    Ok(())
}

fn append_node_currency(
    output: &mut Vec<u8>,
    rows: &[NodeCurrencyRow],
) -> Result<(), StableIdentityError> {
    append_count(output, 0x07, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES_V1 + 1) {
        append_str32(output, "stable node name", &row.0)?;
        append_str32(output, "stable Currency attribute", &row.1)?;
        output.extend_from_slice(&row.2.to_be_bytes());
    }
    Ok(())
}

fn append_hyperedge_f64(
    output: &mut Vec<u8>,
    rows: &[HyperedgeF64Row],
) -> Result<(), StableIdentityError> {
    append_count(output, 0x08, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES_V1 + 1) {
        append_str32(output, "stable hyperedge name", &row.0)?;
        append_str32(output, "stable hyperedge attribute", &row.1)?;
        output.extend_from_slice(&row.2.to_be_bytes());
    }
    Ok(())
}

fn append_str32(
    output: &mut Vec<u8>,
    field: &'static str,
    value: &str,
) -> Result<(), StableIdentityError> {
    output.extend_from_slice(&checked_u32(field, value.len())?.to_be_bytes());
    output.extend_from_slice(value.as_bytes());
    Ok(())
}

fn checked_u32(field: &'static str, value: usize) -> Result<u32, StableIdentityError> {
    u32::try_from(value).map_err(|_| StableIdentityError::IntegerConversion { field, value })
}

fn checked_add(
    field: &'static str,
    left: usize,
    right: usize,
) -> Result<usize, StableIdentityError> {
    left.checked_add(right)
        .ok_or(StableIdentityError::CapacityOverflow { field })
}

fn reserve_rows<T>(field: &'static str, count: usize) -> Result<Vec<T>, StableIdentityError> {
    let mut output = Vec::new();
    output
        .try_reserve_exact(count)
        .map_err(|_: TryReserveError| StableIdentityError::Allocation {
            field,
            requested: count,
        })?;
    Ok(output)
}

fn reserve_bytes(field: &'static str, capacity: usize) -> Result<Vec<u8>, StableIdentityError> {
    let mut output = Vec::new();
    output
        .try_reserve_exact(capacity)
        .map_err(|_: TryReserveError| StableIdentityError::Allocation {
            field,
            requested: capacity,
        })?;
    Ok(output)
}

#[cfg(test)]
mod tests {
    use super::{
        finite_bits, validate_fact_units, validate_section, validate_state_byte_size,
        MAX_STABLE_GRAPH_ATTRIBUTES_V1, MAX_STABLE_GRAPH_ELEMENTS_V1,
        MAX_STABLE_GRAPH_FACT_UNITS_V1, MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS_V1,
        MAX_STABLE_GRAPH_STATE_BYTES_V1,
    };
    use crate::stable_element::StableIdentityError;

    #[test]
    fn every_stable_state_ceiling_accepts_maximum_and_refuses_plus_one() {
        let section_limits = [
            ("nodes", MAX_STABLE_GRAPH_ELEMENTS_V1),
            ("edges", MAX_STABLE_GRAPH_ELEMENTS_V1),
            ("hyperedges", MAX_STABLE_GRAPH_ELEMENTS_V1),
            ("node f64 attributes", MAX_STABLE_GRAPH_ATTRIBUTES_V1),
            ("edge f64 attributes", MAX_STABLE_GRAPH_ATTRIBUTES_V1),
            ("node Currency attributes", MAX_STABLE_GRAPH_ATTRIBUTES_V1),
            ("hyperedge f64 attributes", MAX_STABLE_GRAPH_ATTRIBUTES_V1),
            ("hyperedge members", MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS_V1),
        ];
        for (section, maximum) in section_limits {
            assert_eq!(validate_section(section, maximum, maximum), Ok(()));
            assert_eq!(
                validate_section(section, maximum + 1, maximum),
                Err(StableIdentityError::StateSectionLimit {
                    section,
                    actual: maximum + 1,
                    maximum,
                })
            );
        }
        assert_eq!(validate_fact_units(MAX_STABLE_GRAPH_FACT_UNITS_V1), Ok(()));
        assert_eq!(
            validate_fact_units(MAX_STABLE_GRAPH_FACT_UNITS_V1 + 1),
            Err(StableIdentityError::FactUnitLimit {
                actual: MAX_STABLE_GRAPH_FACT_UNITS_V1 + 1,
                maximum: MAX_STABLE_GRAPH_FACT_UNITS_V1,
            })
        );
        assert_eq!(
            validate_state_byte_size(MAX_STABLE_GRAPH_STATE_BYTES_V1),
            Ok(())
        );
        assert_eq!(
            validate_state_byte_size(MAX_STABLE_GRAPH_STATE_BYTES_V1 + 1),
            Err(StableIdentityError::ByteLimit {
                field: "stable graph state",
                actual: MAX_STABLE_GRAPH_STATE_BYTES_V1 + 1,
                maximum: MAX_STABLE_GRAPH_STATE_BYTES_V1,
            })
        );
    }

    #[test]
    fn finite_bits_normalize_both_zeros_and_refuse_nan_and_infinity() {
        assert_eq!(finite_bits(0.0, "test"), Ok(0));
        assert_eq!(finite_bits(-0.0, "test"), Ok(0));
        assert_eq!(
            finite_bits(f64::NAN, "test"),
            Err(StableIdentityError::NonFiniteValue { section: "test" })
        );
        assert_eq!(
            finite_bits(f64::INFINITY, "test"),
            Err(StableIdentityError::NonFiniteValue { section: "test" })
        );
    }
}
