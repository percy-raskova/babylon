//! Runtime-handle-free graph-state bytes and digest.

use std::collections::BTreeSet;
use std::collections::TryReserveError;

use babylon_kernel::content_digest;
use babylon_kernel::currency::Currency;

use crate::stable_element::StableIdentityError;
use crate::stable_element::{StableElementKey, StableElementResolver};
use crate::state_hash::CanonicalState;
use crate::substrate::{HyperedgeId, NodeId};

/// Stable graph-state layout version.
pub const STABLE_GRAPH_STATE_LAYOUT_VERSION: u32 = 1;
/// Maximum rows in each edge or hyperedge section of stable graph state.
pub const MAX_STABLE_GRAPH_ELEMENTS: usize = 65_536;
/// Maximum aggregate actor and territory nodes in a current national graph.
pub const MAX_STABLE_GRAPH_NODES: usize = 262_144;
/// Maximum rows in one stable graph attribute section.
pub const MAX_STABLE_GRAPH_ATTRIBUTES: usize = 524_288;
/// Maximum members in one stable hyperedge.
pub const MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS: usize = 65_534;
/// Maximum rows plus nested member references in stable graph state.
pub const MAX_STABLE_GRAPH_FACT_UNITS: usize = 1_048_576;
/// Maximum complete stable graph-state canonical byte length.
pub const MAX_STABLE_GRAPH_STATE_BYTES: usize = 67_108_864;

const STABLE_GRAPH_DOMAIN: &[u8] = b"babylon.stable-graph";

/// One stable graph node row: `(local_name, node_type)`.
pub type StableGraphNodeRow = (String, String);
/// One stable graph binary64 node-attribute row: `(local_name, qname, bits)`.
pub type StableGraphNodeF64Row = (String, String, u64);
/// One stable graph edge row: `(edge_type, source, target, strength_bits)`.
pub type StableGraphEdgeRow = (String, String, String, u64);
/// One stable graph hyperedge row: `(local_name, type, ordered_members)`.
pub type StableGraphHyperedgeRow = (String, String, Vec<String>);
/// One stable graph binary64 edge-attribute row.
pub type StableGraphEdgeF64Row = (String, String, String, String, u64);
/// One stable graph Currency node-attribute row in micro-units.
pub type StableGraphNodeCurrencyRow = (String, String, i128);
/// One stable graph binary64 hyperedge-attribute row.
pub type StableGraphHyperedgeF64Row = (String, String, u64);

struct Listings {
    nodes: Vec<(NodeId, String)>,
    node_f64: Vec<(NodeId, String, f64)>,
    edges: Vec<(String, NodeId, NodeId, f64)>,
    hyperedges: Vec<(HyperedgeId, String, Vec<NodeId>)>,
    edge_f64: Vec<(String, NodeId, NodeId, String, f64)>,
    node_currency: Vec<(NodeId, String, Currency)>,
    hyperedge_f64: Vec<(HyperedgeId, String, f64)>,
}

/// Typed stable graph rows in the same canonical order as the identity bytes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StableGraphStateRows {
    nodes: Vec<StableGraphNodeRow>,
    node_f64: Vec<StableGraphNodeF64Row>,
    edges: Vec<StableGraphEdgeRow>,
    hyperedges: Vec<StableGraphHyperedgeRow>,
    edge_f64: Vec<StableGraphEdgeF64Row>,
    node_currency: Vec<StableGraphNodeCurrencyRow>,
    hyperedge_f64: Vec<StableGraphHyperedgeF64Row>,
}

/// Owned stable graph rows loaded from an external typed store.
///
/// The constructor that consumes this value applies the same bounds,
/// ordering, numeric, and canonical-byte rules as the live graph encoder.
#[derive(Debug)]
pub struct StableGraphStateRowsInput {
    /// Stable node rows.
    pub nodes: Vec<StableGraphNodeRow>,
    /// Stable binary64 node-attribute rows.
    pub node_f64: Vec<StableGraphNodeF64Row>,
    /// Stable dyadic-edge rows.
    pub edges: Vec<StableGraphEdgeRow>,
    /// Stable hyperedge rows.
    pub hyperedges: Vec<StableGraphHyperedgeRow>,
    /// Stable binary64 edge-attribute rows.
    pub edge_f64: Vec<StableGraphEdgeF64Row>,
    /// Stable Currency node-attribute rows.
    pub node_currency: Vec<StableGraphNodeCurrencyRow>,
    /// Stable binary64 hyperedge-attribute rows.
    pub hyperedge_f64: Vec<StableGraphHyperedgeF64Row>,
}

impl StableGraphStateRows {
    /// Borrow stable node rows in canonical order.
    #[must_use]
    pub fn nodes(&self) -> &[StableGraphNodeRow] {
        &self.nodes
    }

    /// Borrow stable binary64 node-attribute rows in canonical order.
    #[must_use]
    pub fn node_f64(&self) -> &[StableGraphNodeF64Row] {
        &self.node_f64
    }

    /// Borrow stable edge rows in canonical order.
    #[must_use]
    pub fn edges(&self) -> &[StableGraphEdgeRow] {
        &self.edges
    }

    /// Borrow stable hyperedge rows in canonical order.
    #[must_use]
    pub fn hyperedges(&self) -> &[StableGraphHyperedgeRow] {
        &self.hyperedges
    }

    /// Borrow stable binary64 edge-attribute rows in canonical order.
    #[must_use]
    pub fn edge_f64(&self) -> &[StableGraphEdgeF64Row] {
        &self.edge_f64
    }

    /// Borrow stable Currency node-attribute rows in canonical order.
    #[must_use]
    pub fn node_currency(&self) -> &[StableGraphNodeCurrencyRow] {
        &self.node_currency
    }

    /// Borrow stable binary64 hyperedge-attribute rows in canonical order.
    #[must_use]
    pub fn hyperedge_f64(&self) -> &[StableGraphHyperedgeF64Row] {
        &self.hyperedge_f64
    }
}

/// SHA-256 identity of exact stable graph-state bytes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct StableGraphStateHash([u8; 32]);

impl StableGraphStateHash {
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
pub struct StableGraphState {
    scenario_scope: String,
    canonical_bytes: Vec<u8>,
    digest: StableGraphStateHash,
    rows: StableGraphStateRows,
}

impl StableGraphState {
    /// Borrow the exact authored scenario scope encoded into this state.
    #[must_use]
    pub fn scenario_scope(&self) -> &str {
        &self.scenario_scope
    }

    /// Borrow the exact canonical bytes.
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8] {
        &self.canonical_bytes
    }

    /// Return SHA-256 of the exact canonical bytes.
    #[must_use]
    pub const fn digest(&self) -> StableGraphStateHash {
        self.digest
    }

    /// Borrow the typed rows whose canonical encoding produced this state.
    #[must_use]
    pub const fn rows(&self) -> &StableGraphStateRows {
        &self.rows
    }
}

/// Encode one graph using authored stable identities rather than runtime handles.
///
/// # Errors
/// Returns the first topology, semantic, numeric, bound, arithmetic, or
/// allocation failure before exposing any partial canonical bytes.
pub fn encode_stable_graph_state<G: CanonicalState>(
    graph: &G,
    resolver: &StableElementResolver,
) -> Result<StableGraphState, StableIdentityError> {
    let listings = collect_listings(graph);
    validate_listing_bounds(&listings)?;
    resolver.validate_topology(graph)?;
    let rows = resolve_rows(&listings, resolver)?;
    let scenario_scope = copy_stable_string("stable graph scenario", resolver.scenario_scope())?;
    let capacity = stable_state_capacity(&scenario_scope, &rows)?;
    validate_state_byte_size(capacity)?;
    let canonical_bytes = encode_rows(&scenario_scope, &rows, capacity)?;
    let digest = StableGraphStateHash(content_digest::sha256_of(&canonical_bytes));
    Ok(StableGraphState {
        scenario_scope,
        canonical_bytes,
        digest,
        rows,
    })
}

/// Compose canonical stable graph state from typed, externally loaded rows.
///
/// This is the inverse boundary used by durable checkpoint readers. It does
/// not trust database ordering: rows are sorted and duplicate semantic keys
/// are refused before canonical bytes are exposed. A caller must still bind
/// the resulting state to a sealed live topology before using it as runtime
/// state.
///
/// # Errors
/// Returns the first scenario, qname, numeric, ordering, bound, arithmetic,
/// or allocation refusal.
pub fn compose_stable_graph_state_from_rows(
    scenario: &str,
    input: StableGraphStateRowsInput,
) -> Result<StableGraphState, StableIdentityError> {
    crate::stable_element::validate_qname("stable graph scenario", scenario)?;
    let mut rows = StableGraphStateRows {
        nodes: input.nodes,
        node_f64: input.node_f64,
        edges: input.edges,
        hyperedges: input.hyperedges,
        edge_f64: input.edge_f64,
        node_currency: input.node_currency,
        hyperedge_f64: input.hyperedge_f64,
    };
    validate_loaded_rows(&mut rows)?;
    let capacity = stable_state_capacity(scenario, &rows)?;
    validate_state_byte_size(capacity)?;
    let canonical_bytes = encode_rows(scenario, &rows, capacity)?;
    let digest = StableGraphStateHash(content_digest::sha256_of(&canonical_bytes));
    Ok(StableGraphState {
        scenario_scope: copy_stable_string("stable graph scenario", scenario)?,
        canonical_bytes,
        digest,
        rows,
    })
}

impl StableGraphState {
    /// Decode one exact canonical stable graph-state frame.
    ///
    /// This is the strict inverse of [`encode_stable_graph_state`] and
    /// [`compose_stable_graph_state_from_rows`]: the decoded rows re-encode to
    /// the exact input bytes, and every frame the encoder could not produce is
    /// refused rather than normalized.
    ///
    /// # Errors
    /// Returns the first framing, scenario, numeric, ordering, bound,
    /// arithmetic, or allocation refusal.
    pub fn decode(bytes: &[u8]) -> Result<Self, StableIdentityError> {
        let mut cursor = GraphStateCursor { bytes, position: 0 };
        if cursor.take(STABLE_GRAPH_DOMAIN.len())? != STABLE_GRAPH_DOMAIN {
            return Err(canonical_refusal("stable graph domain"));
        }
        if cursor.byte()? != 0 {
            return Err(canonical_refusal("stable graph header flag"));
        }
        if cursor.u32()? != STABLE_GRAPH_STATE_LAYOUT_VERSION {
            return Err(canonical_refusal("stable graph layout version"));
        }
        if cursor.byte()? != 0x01 {
            return Err(canonical_refusal("stable graph scenario tag"));
        }
        let scenario = cursor.string("stable graph scenario")?;
        let input = decode_state_rows(&mut cursor)?;
        if cursor.position != bytes.len() {
            return Err(canonical_refusal("stable graph trailing bytes"));
        }
        let state = compose_stable_graph_state_from_rows(&scenario, input)?;
        if state.canonical_bytes.as_slice() != bytes {
            return Err(canonical_refusal("stable graph canonical order"));
        }
        Ok(state)
    }
}

fn decode_state_rows(
    cursor: &mut GraphStateCursor<'_>,
) -> Result<StableGraphStateRowsInput, StableIdentityError> {
    let nodes = cursor.section("nodes", 0x02, MAX_STABLE_GRAPH_NODES, |cursor| {
        Ok((
            cursor.string("stable node name")?,
            cursor.string("stable node type")?,
        ))
    })?;
    let node_f64 = cursor.section(
        "node f64 attributes",
        0x03,
        MAX_STABLE_GRAPH_ATTRIBUTES,
        |cursor| {
            Ok((
                cursor.string("stable node name")?,
                cursor.string("stable node attribute")?,
                cursor.u64()?,
            ))
        },
    )?;
    let edges = cursor.section("edges", 0x04, MAX_STABLE_GRAPH_ELEMENTS, |cursor| {
        Ok((
            cursor.string("stable edge type")?,
            cursor.string("stable edge source")?,
            cursor.string("stable edge target")?,
            cursor.u64()?,
        ))
    })?;
    let hyperedges = cursor.section("hyperedges", 0x05, MAX_STABLE_GRAPH_ELEMENTS, |cursor| {
        let local_name = cursor.string("stable hyperedge name")?;
        let hyperedge_type = cursor.string("stable hyperedge type")?;
        let members = cursor.section_rows(
            "hyperedge members",
            MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS,
            |cursor| cursor.string("stable hyperedge member"),
        )?;
        Ok((local_name, hyperedge_type, members))
    })?;
    let edge_f64 = cursor.section(
        "edge f64 attributes",
        0x06,
        MAX_STABLE_GRAPH_ATTRIBUTES,
        |cursor| {
            Ok((
                cursor.string("stable edge type")?,
                cursor.string("stable edge source")?,
                cursor.string("stable edge target")?,
                cursor.string("stable edge attribute")?,
                cursor.u64()?,
            ))
        },
    )?;
    let node_currency = cursor.section(
        "node Currency attributes",
        0x07,
        MAX_STABLE_GRAPH_ATTRIBUTES,
        |cursor| {
            Ok((
                cursor.string("stable node name")?,
                cursor.string("stable Currency attribute")?,
                cursor.i128()?,
            ))
        },
    )?;
    let hyperedge_f64 = cursor.section(
        "hyperedge f64 attributes",
        0x08,
        MAX_STABLE_GRAPH_ATTRIBUTES,
        |cursor| {
            Ok((
                cursor.string("stable hyperedge name")?,
                cursor.string("stable hyperedge attribute")?,
                cursor.u64()?,
            ))
        },
    )?;
    Ok(StableGraphStateRowsInput {
        nodes,
        node_f64,
        edges,
        hyperedges,
        edge_f64,
        node_currency,
        hyperedge_f64,
    })
}

fn canonical_refusal(field: &'static str) -> StableIdentityError {
    StableIdentityError::CanonicalBytes { field }
}

struct GraphStateCursor<'a> {
    bytes: &'a [u8],
    position: usize,
}

impl GraphStateCursor<'_> {
    fn take(&mut self, count: usize) -> Result<&[u8], StableIdentityError> {
        let end =
            self.position
                .checked_add(count)
                .ok_or(StableIdentityError::CapacityOverflow {
                    field: "stable graph offset",
                })?;
        let slice = self
            .bytes
            .get(self.position..end)
            .ok_or_else(|| canonical_refusal("stable graph truncated"))?;
        self.position = end;
        Ok(slice)
    }

    fn byte(&mut self) -> Result<u8, StableIdentityError> {
        let mut value = [0_u8; 1];
        value.copy_from_slice(self.take(1)?);
        Ok(value[0])
    }

    fn u32(&mut self) -> Result<u32, StableIdentityError> {
        let mut value = [0_u8; 4];
        value.copy_from_slice(self.take(4)?);
        Ok(u32::from_be_bytes(value))
    }

    fn u64(&mut self) -> Result<u64, StableIdentityError> {
        let mut value = [0_u8; 8];
        value.copy_from_slice(self.take(8)?);
        Ok(u64::from_be_bytes(value))
    }

    fn i128(&mut self) -> Result<i128, StableIdentityError> {
        let mut value = [0_u8; 16];
        value.copy_from_slice(self.take(16)?);
        Ok(i128::from_be_bytes(value))
    }

    fn string(&mut self, field: &'static str) -> Result<String, StableIdentityError> {
        let length = usize::try_from(self.u32()?).unwrap_or(usize::MAX);
        let text = std::str::from_utf8(self.take(length)?).map_err(|_| canonical_refusal(field))?;
        copy_stable_string(field, text)
    }

    fn section<T, F>(
        &mut self,
        section: &'static str,
        tag: u8,
        maximum: usize,
        row: F,
    ) -> Result<Vec<T>, StableIdentityError>
    where
        F: Fn(&mut Self) -> Result<T, StableIdentityError>,
    {
        if self.byte()? != tag {
            return Err(canonical_refusal("stable graph section tag"));
        }
        self.section_rows(section, maximum, row)
    }

    fn section_rows<T, F>(
        &mut self,
        section: &'static str,
        maximum: usize,
        row: F,
    ) -> Result<Vec<T>, StableIdentityError>
    where
        F: Fn(&mut Self) -> Result<T, StableIdentityError>,
    {
        let actual = usize::try_from(self.u32()?).unwrap_or(usize::MAX);
        if actual > maximum {
            return Err(StableIdentityError::StateSectionLimit {
                section,
                actual,
                maximum,
            });
        }
        if actual > self.bytes.len() {
            return Err(canonical_refusal("stable graph section count"));
        }
        let mut rows = reserve_rows(section, actual)?;
        for _ in 0..actual {
            rows.push(row(self)?);
        }
        Ok(rows)
    }
}

fn copy_stable_string(field: &'static str, source: &str) -> Result<String, StableIdentityError> {
    let mut output = String::new();
    output
        .try_reserve_exact(source.len())
        .map_err(|_: TryReserveError| StableIdentityError::Allocation {
            field,
            requested: source.len(),
        })?;
    output.push_str(source);
    Ok(output)
}

fn validate_loaded_rows(rows: &mut StableGraphStateRows) -> Result<(), StableIdentityError> {
    validate_section("nodes", rows.nodes.len(), MAX_STABLE_GRAPH_NODES)?;
    validate_section(
        "node f64 attributes",
        rows.node_f64.len(),
        MAX_STABLE_GRAPH_ATTRIBUTES,
    )?;
    validate_section("edges", rows.edges.len(), MAX_STABLE_GRAPH_ELEMENTS)?;
    validate_section(
        "hyperedges",
        rows.hyperedges.len(),
        MAX_STABLE_GRAPH_ELEMENTS,
    )?;
    validate_section(
        "edge f64 attributes",
        rows.edge_f64.len(),
        MAX_STABLE_GRAPH_ATTRIBUTES,
    )?;
    validate_section(
        "node Currency attributes",
        rows.node_currency.len(),
        MAX_STABLE_GRAPH_ATTRIBUTES,
    )?;
    validate_section(
        "hyperedge f64 attributes",
        rows.hyperedge_f64.len(),
        MAX_STABLE_GRAPH_ATTRIBUTES,
    )?;
    let mut fact_units = [
        rows.nodes.len(),
        rows.node_f64.len(),
        rows.edges.len(),
        rows.hyperedges.len(),
        rows.edge_f64.len(),
        rows.node_currency.len(),
        rows.hyperedge_f64.len(),
    ]
    .into_iter()
    .try_fold(0_usize, |total, count| {
        checked_add("stable graph fact units", total, count)
    })?;
    for (_, _, members) in &rows.hyperedges {
        validate_section(
            "hyperedge members",
            members.len(),
            MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS,
        )?;
        fact_units = checked_add("stable graph fact units", fact_units, members.len())?;
    }
    validate_fact_units(fact_units)?;
    for (_, qname, bits) in &mut rows.node_f64 {
        crate::stable_element::validate_qname("node attribute qname", qname)?;
        *bits = finite_bits(f64::from_bits(*bits), "node f64 attributes")?;
    }
    for (_, _, _, bits) in &mut rows.edges {
        *bits = finite_bits(f64::from_bits(*bits), "edges")?;
    }
    for (_, _, _, qname, bits) in &mut rows.edge_f64 {
        crate::stable_element::validate_qname("edge attribute qname", qname)?;
        if qname.ends_with("/strength") {
            return Err(StableIdentityError::StrengthAttribute);
        }
        *bits = finite_bits(f64::from_bits(*bits), "edge f64 attributes")?;
    }
    for (_, qname, _) in &rows.node_currency {
        crate::stable_element::validate_qname("Currency attribute qname", qname)?;
    }
    for (_, qname, bits) in &mut rows.hyperedge_f64 {
        crate::stable_element::validate_qname("hyperedge attribute qname", qname)?;
        *bits = finite_bits(f64::from_bits(*bits), "hyperedge f64 attributes")?;
    }
    for (_, _, members) in &mut rows.hyperedges {
        members.sort_unstable();
        ensure_unique("hyperedge members", members, |left, right| left == right)?;
    }
    sort_and_validate(rows)
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
    validate_section("nodes", value.nodes.len(), MAX_STABLE_GRAPH_NODES)?;
    validate_section(
        "node f64 attributes",
        value.node_f64.len(),
        MAX_STABLE_GRAPH_ATTRIBUTES,
    )?;
    validate_section("edges", value.edges.len(), MAX_STABLE_GRAPH_ELEMENTS)?;
    validate_section(
        "hyperedges",
        value.hyperedges.len(),
        MAX_STABLE_GRAPH_ELEMENTS,
    )?;
    validate_section(
        "edge f64 attributes",
        value.edge_f64.len(),
        MAX_STABLE_GRAPH_ATTRIBUTES,
    )?;
    validate_section(
        "node Currency attributes",
        value.node_currency.len(),
        MAX_STABLE_GRAPH_ATTRIBUTES,
    )?;
    validate_section(
        "hyperedge f64 attributes",
        value.hyperedge_f64.len(),
        MAX_STABLE_GRAPH_ATTRIBUTES,
    )?;
    let mut fact_units = listing_row_count(value)?;
    for (_, _, members) in value.hyperedges.iter().take(MAX_STABLE_GRAPH_ELEMENTS + 1) {
        validate_section(
            "hyperedge members",
            members.len(),
            MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS,
        )?;
        fact_units = checked_add("stable graph fact units", fact_units, members.len())?;
    }
    validate_fact_units(fact_units)
}

fn validate_fact_units(fact_units: usize) -> Result<(), StableIdentityError> {
    if fact_units > MAX_STABLE_GRAPH_FACT_UNITS {
        return Err(StableIdentityError::FactUnitLimit {
            actual: fact_units,
            maximum: MAX_STABLE_GRAPH_FACT_UNITS,
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
    if actual <= MAX_STABLE_GRAPH_STATE_BYTES {
        Ok(())
    } else {
        Err(StableIdentityError::ByteLimit {
            field: "stable graph state",
            actual,
            maximum: MAX_STABLE_GRAPH_STATE_BYTES,
        })
    }
}

fn resolve_rows(
    value: &Listings,
    resolver: &StableElementResolver,
) -> Result<StableGraphStateRows, StableIdentityError> {
    let mut rows = StableGraphStateRows {
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
    resolver: &StableElementResolver,
) -> Result<Vec<StableGraphNodeRow>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph nodes", source.len())?;
    for (node, node_type) in source.iter().take(MAX_STABLE_GRAPH_NODES + 1) {
        rows.push((
            resolver.node_local_name(*node)?.to_owned(),
            node_type.clone(),
        ));
    }
    Ok(rows)
}

fn resolve_node_f64(
    source: &[(NodeId, String, f64)],
    resolver: &StableElementResolver,
) -> Result<Vec<StableGraphNodeF64Row>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph node attributes", source.len())?;
    for (node, qname, value) in source.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES + 1) {
        crate::stable_element::validate_qname("node attribute qname", qname)?;
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
    resolver: &StableElementResolver,
) -> Result<Vec<StableGraphEdgeRow>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph edges", source.len())?;
    for (edge_type, from, to, strength) in source.iter().take(MAX_STABLE_GRAPH_ELEMENTS + 1) {
        let key = resolver.edge_key(edge_type, *from, *to)?;
        let StableElementKey::Edge {
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
    resolver: &StableElementResolver,
) -> Result<Vec<StableGraphHyperedgeRow>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph hyperedges", source.len())?;
    for (hyperedge, hyperedge_type, members) in source.iter().take(MAX_STABLE_GRAPH_ELEMENTS + 1) {
        let StableElementKey::Hyperedge { local_name, .. } = resolver.hyperedge_key(*hyperedge)?
        else {
            return Err(StableIdentityError::ElementNotSealed);
        };
        let mut member_names = reserve_rows("stable graph hyperedge members", members.len())?;
        for member in members.iter().take(MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS + 1) {
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
    resolver: &StableElementResolver,
) -> Result<Vec<StableGraphEdgeF64Row>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph edge attributes", source.len())?;
    for (edge_type, from, to, qname, value) in source.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES + 1) {
        crate::stable_element::validate_qname("edge attribute qname", qname)?;
        if qname.ends_with("/strength") {
            return Err(StableIdentityError::StrengthAttribute);
        }
        let key = resolver.edge_key(edge_type, *from, *to)?;
        let StableElementKey::Edge {
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
    resolver: &StableElementResolver,
) -> Result<Vec<StableGraphNodeCurrencyRow>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph Currency attributes", source.len())?;
    for (node, qname, value) in source.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES + 1) {
        crate::stable_element::validate_qname("Currency attribute qname", qname)?;
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
    resolver: &StableElementResolver,
) -> Result<Vec<StableGraphHyperedgeF64Row>, StableIdentityError> {
    let mut rows = reserve_rows("stable graph hyperedge attributes", source.len())?;
    for (hyperedge, qname, value) in source.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES + 1) {
        crate::stable_element::validate_qname("hyperedge attribute qname", qname)?;
        let StableElementKey::Hyperedge { local_name, .. } = resolver.hyperedge_key(*hyperedge)?
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

fn sort_and_validate(rows: &mut StableGraphStateRows) -> Result<(), StableIdentityError> {
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

fn validate_numeric_lanes(rows: &StableGraphStateRows) -> Result<(), StableIdentityError> {
    let mut f64_keys = BTreeSet::new();
    for (node, qname, _) in rows.node_f64.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES + 1) {
        f64_keys.insert((node.as_str(), qname.as_str()));
    }
    for (node, qname, _) in rows
        .node_currency
        .iter()
        .take(MAX_STABLE_GRAPH_ATTRIBUTES + 1)
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

fn stable_state_capacity(
    scenario: &str,
    rows: &StableGraphStateRows,
) -> Result<usize, StableIdentityError> {
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
    for row in rows.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES + 1) {
        size = checked_add("stable graph bytes", size, row_size(row)?)?;
    }
    Ok(size)
}

fn hyperedge_capacity(row: &StableGraphHyperedgeRow) -> Result<usize, StableIdentityError> {
    let mut size = add_fixed(strings_capacity(&[&row.0, &row.1])?, 4)?;
    for member in row.2.iter().take(MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS + 1) {
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
    rows: &StableGraphStateRows,
    capacity: usize,
) -> Result<Vec<u8>, StableIdentityError> {
    let mut output = reserve_bytes("stable graph state", capacity)?;
    output.extend_from_slice(STABLE_GRAPH_DOMAIN);
    output.push(0);
    output.extend_from_slice(&STABLE_GRAPH_STATE_LAYOUT_VERSION.to_be_bytes());
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

fn append_nodes(
    output: &mut Vec<u8>,
    rows: &[StableGraphNodeRow],
) -> Result<(), StableIdentityError> {
    append_count(output, 0x02, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_NODES + 1) {
        append_str32(output, "stable node name", &row.0)?;
        append_str32(output, "stable node type", &row.1)?;
    }
    Ok(())
}

fn append_node_f64(
    output: &mut Vec<u8>,
    rows: &[StableGraphNodeF64Row],
) -> Result<(), StableIdentityError> {
    append_count(output, 0x03, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES + 1) {
        append_str32(output, "stable node name", &row.0)?;
        append_str32(output, "stable node attribute", &row.1)?;
        output.extend_from_slice(&row.2.to_be_bytes());
    }
    Ok(())
}

fn append_edges(
    output: &mut Vec<u8>,
    rows: &[StableGraphEdgeRow],
) -> Result<(), StableIdentityError> {
    append_count(output, 0x04, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ELEMENTS + 1) {
        append_str32(output, "stable edge type", &row.0)?;
        append_str32(output, "stable edge source", &row.1)?;
        append_str32(output, "stable edge target", &row.2)?;
        output.extend_from_slice(&row.3.to_be_bytes());
    }
    Ok(())
}

fn append_hyperedges(
    output: &mut Vec<u8>,
    rows: &[StableGraphHyperedgeRow],
) -> Result<(), StableIdentityError> {
    append_count(output, 0x05, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ELEMENTS + 1) {
        append_str32(output, "stable hyperedge name", &row.0)?;
        append_str32(output, "stable hyperedge type", &row.1)?;
        output.extend_from_slice(
            &checked_u32("stable hyperedge member count", row.2.len())?.to_be_bytes(),
        );
        for member in row.2.iter().take(MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS + 1) {
            append_str32(output, "stable hyperedge member", member)?;
        }
    }
    Ok(())
}

fn append_edge_f64(
    output: &mut Vec<u8>,
    rows: &[StableGraphEdgeF64Row],
) -> Result<(), StableIdentityError> {
    append_count(output, 0x06, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES + 1) {
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
    rows: &[StableGraphNodeCurrencyRow],
) -> Result<(), StableIdentityError> {
    append_count(output, 0x07, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES + 1) {
        append_str32(output, "stable node name", &row.0)?;
        append_str32(output, "stable Currency attribute", &row.1)?;
        output.extend_from_slice(&row.2.to_be_bytes());
    }
    Ok(())
}

fn append_hyperedge_f64(
    output: &mut Vec<u8>,
    rows: &[StableGraphHyperedgeF64Row],
) -> Result<(), StableIdentityError> {
    append_count(output, 0x08, rows.len())?;
    for row in rows.iter().take(MAX_STABLE_GRAPH_ATTRIBUTES + 1) {
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
        MAX_STABLE_GRAPH_ATTRIBUTES, MAX_STABLE_GRAPH_ELEMENTS, MAX_STABLE_GRAPH_FACT_UNITS,
        MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS, MAX_STABLE_GRAPH_NODES, MAX_STABLE_GRAPH_STATE_BYTES,
    };
    use crate::stable_element::StableIdentityError;

    #[test]
    fn every_stable_state_ceiling_accepts_maximum_and_refuses_plus_one() {
        let section_limits = [
            ("nodes", MAX_STABLE_GRAPH_NODES),
            ("edges", MAX_STABLE_GRAPH_ELEMENTS),
            ("hyperedges", MAX_STABLE_GRAPH_ELEMENTS),
            ("node f64 attributes", MAX_STABLE_GRAPH_ATTRIBUTES),
            ("edge f64 attributes", MAX_STABLE_GRAPH_ATTRIBUTES),
            ("node Currency attributes", MAX_STABLE_GRAPH_ATTRIBUTES),
            ("hyperedge f64 attributes", MAX_STABLE_GRAPH_ATTRIBUTES),
            ("hyperedge members", MAX_STABLE_GRAPH_HYPEREDGE_MEMBERS),
        ];
        for (section, maximum) in section_limits {
            assert_eq!(super::validate_section(section, maximum, maximum), Ok(()));
            assert_eq!(
                super::validate_section(section, maximum + 1, maximum),
                Err(StableIdentityError::StateSectionLimit {
                    section,
                    actual: maximum + 1,
                    maximum,
                })
            );
        }
        assert_eq!(
            super::validate_fact_units(MAX_STABLE_GRAPH_FACT_UNITS),
            Ok(())
        );
        assert_eq!(
            super::validate_fact_units(MAX_STABLE_GRAPH_FACT_UNITS + 1),
            Err(StableIdentityError::FactUnitLimit {
                actual: MAX_STABLE_GRAPH_FACT_UNITS + 1,
                maximum: MAX_STABLE_GRAPH_FACT_UNITS,
            })
        );
        assert_eq!(
            super::validate_state_byte_size(MAX_STABLE_GRAPH_STATE_BYTES),
            Ok(())
        );
        assert_eq!(
            super::validate_state_byte_size(MAX_STABLE_GRAPH_STATE_BYTES + 1),
            Err(StableIdentityError::ByteLimit {
                field: "stable graph state",
                actual: MAX_STABLE_GRAPH_STATE_BYTES + 1,
                maximum: MAX_STABLE_GRAPH_STATE_BYTES,
            })
        );
    }

    #[test]
    fn finite_bits_normalize_both_zeros_and_refuse_nan_and_infinity() {
        assert_eq!(super::finite_bits(0.0, "test"), Ok(0));
        assert_eq!(super::finite_bits(-0.0, "test"), Ok(0));
        assert_eq!(
            super::finite_bits(f64::NAN, "test"),
            Err(StableIdentityError::NonFiniteValue { section: "test" })
        );
        assert_eq!(
            super::finite_bits(f64::INFINITY, "test"),
            Err(StableIdentityError::NonFiniteValue { section: "test" })
        );
    }

    fn authored_state() -> crate::stable_state::StableGraphState {
        use crate::stable_state::{
            compose_stable_graph_state_from_rows, StableGraphStateRowsInput,
        };
        compose_stable_graph_state_from_rows(
            "test/stable-state",
            StableGraphStateRowsInput {
                nodes: vec![
                    ("node-a".to_owned(), "NodeType/TERRITORY".to_owned()),
                    ("node-b".to_owned(), "NodeType/ORGANIZATION".to_owned()),
                ],
                node_f64: vec![(
                    "node-a".to_owned(),
                    "social-class/probability".to_owned(),
                    0.5_f64.to_bits(),
                )],
                edges: vec![(
                    "PRESENCE".to_owned(),
                    "node-b".to_owned(),
                    "node-a".to_owned(),
                    1.0_f64.to_bits(),
                )],
                hyperedges: vec![(
                    "hyperedge-a".to_owned(),
                    "HyperedgeType/MARKET".to_owned(),
                    vec!["node-b".to_owned(), "node-a".to_owned()],
                )],
                edge_f64: vec![(
                    "PRESENCE".to_owned(),
                    "node-b".to_owned(),
                    "node-a".to_owned(),
                    "business/probability".to_owned(),
                    0.25_f64.to_bits(),
                )],
                node_currency: vec![(
                    "node-b".to_owned(),
                    "business/revenue".to_owned(),
                    i128::from(42_i64),
                )],
                hyperedge_f64: vec![(
                    "hyperedge-a".to_owned(),
                    "market/probability".to_owned(),
                    0.75_f64.to_bits(),
                )],
            },
        )
        .expect("the authored rows compose one canonical state")
    }

    #[test]
    fn stable_graph_decoder_is_the_exact_inverse_of_the_encoder() {
        let state = authored_state();
        let decoded = super::StableGraphState::decode(state.canonical_bytes())
            .expect("every canonical graph state decodes");
        assert_eq!(decoded, state, "the decoder returns the encoded state");
        assert_eq!(
            decoded.canonical_bytes(),
            state.canonical_bytes(),
            "the decoded state preserves the exact canonical bytes"
        );
        assert_eq!(
            decoded.digest(),
            state.digest(),
            "the decoded state preserves its identity digest"
        );
    }

    #[test]
    fn stable_graph_decoder_refuses_wrong_header_trailing_and_unsorted_bytes() {
        let state = authored_state();
        let bytes = state.canonical_bytes();
        let mut wrong_domain = bytes.to_vec();
        wrong_domain[0] ^= 0xff;
        assert_eq!(
            super::StableGraphState::decode(&wrong_domain),
            Err(StableIdentityError::CanonicalBytes {
                field: "stable graph domain"
            })
        );
        let mut trailing = bytes.to_vec();
        trailing.push(0);
        assert_eq!(
            super::StableGraphState::decode(&trailing),
            Err(StableIdentityError::CanonicalBytes {
                field: "stable graph trailing bytes"
            })
        );
        let mut unsorted = bytes.to_vec();
        let position = unsorted
            .windows(9)
            .position(|window| window == b"node-a\0\0\0")
            .expect("the fixture encodes its first node name once");
        unsorted[position] = b'z';
        assert_eq!(
            super::StableGraphState::decode(&unsorted),
            Err(StableIdentityError::CanonicalBytes {
                field: "stable graph canonical order"
            })
        );
    }
}
