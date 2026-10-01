//! Bounded immutable source evidence and a Designed national transport graph.
//!
//! All counties remain actors. Mode compatibility and directed missing bulk
//! access are explicit. Capacity, timing and costs are Designed; costs are
//! unexecuted context until an authoritative monetary consumer pays a carrier.
//! This reference initializes no campaign and proves no adequate supply.

use babylon_kernel::{
    content_digest::sha256_of,
    economic_location::{EconomicLocation, ForeignCounterpart, UsDependency},
    geography::CountyGeoid,
};
use std::{collections::BTreeMap, fmt::Write, io::Read, sync::OnceLock};
mod model;
mod raw;
#[cfg(test)]
mod tests;
mod validate;
pub use model::*;

const ARTIFACT: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../src/babylon/data/reference/transport/national_transport_reference_2024.json.gz"
));
const POLICY: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../contracts/national_transport_policy_v1.json"
));
const SOURCES: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../tools/national_transport_2024_sources.json"
));
const ARTIFACT_SHA256: [u8; 32] = [
    208, 133, 82, 11, 182, 142, 101, 146, 124, 109, 94, 57, 95, 73, 52, 152, 209, 252, 207, 57, 79,
    94, 230, 74, 124, 6, 80, 126, 129, 107, 26, 179,
];
const MAX_COMPRESSED_BYTES: usize = 2_097_152;
const MAX_DECODED_BYTES: usize = 16_777_216;
static REFERENCE: OnceLock<Result<NationalTransportReference, NationalTransportError>> =
    OnceLock::new();

/// Immutable qualified graph and source evidence; no runtime effects are executed.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalTransportReference {
    nodes: Box<[TransportNode]>,
    links: Box<[TransportLink]>,
    outgoing: BTreeMap<String, Box<[usize]>>,
    pools: Box<[TransportPool]>,
    access: Box<[CountyTransportAccess]>,
    factors: Box<[CountyAllocationFactor]>,
    sources: Box<[TransportSource]>,
    facilities: Box<[TransportFacility]>,
    border: Box<[BTreeMap<String, String>]>,
    flows: TransportFlows,
    services: BTreeMap<String, TransportService>,
    bulk: Box<[UnavailableBulkAccess]>,
    period_days: u16,
    diameter: usize,
}
impl NationalTransportReference {
    /// Admit only the qualified gzip bytes; no repair or legacy fallback.
    ///
    /// # Errors
    /// Refuses altered/bounded bytes, malformed data or contradictory graph/source claims.
    pub fn decode_pinned(bytes: &[u8]) -> Result<Self, NationalTransportError> {
        if bytes.len() > MAX_COMPRESSED_BYTES {
            return Err(NationalTransportError::Bound);
        }
        if sha256_of(bytes) != ARTIFACT_SHA256 {
            return Err(NationalTransportError::ArtifactDigest);
        }
        parse(&decode_gzip(bytes)?)
    }
    /// Every county, infrastructure, counterpart and dependency node.
    #[must_use]
    pub fn nodes(&self) -> &[TransportNode] {
        &self.nodes
    }
    /// Every directed mode-compatible edge in canonical source order.
    #[must_use]
    pub fn links(&self) -> &[TransportLink] {
        &self.links
    }
    /// Finite shared resource pools.
    #[must_use]
    pub fn pools(&self) -> &[TransportPool] {
        &self.pools
    }
    /// Explicit county access and independent FAF membership.
    #[must_use]
    pub fn county_access(&self) -> &[CountyTransportAccess] {
        &self.access
    }
    /// Exact source factors: mode,direction,county,FAFzone,SCTG5,decimal token,original row multiplicity.
    #[must_use]
    pub fn county_factors(&self) -> &[CountyAllocationFactor] {
        &self.factors
    }
    /// Source hashes and provenance, retained independently of Designed service values.
    #[must_use]
    pub fn sources(&self) -> &[TransportSource] {
        &self.sources
    }
    /// Literal retained facility records; no inferred installed throughput.
    #[must_use]
    pub fn facilities(&self) -> &[TransportFacility] {
        &self.facilities
    }
    /// Only observed inbound truck rows; missing/outbound values are not zero.
    #[must_use]
    pub fn border_inbound_2024(&self) -> &[BTreeMap<String, String>] {
        &self.border
    }
    /// Source annual flow evidence; native units and directions stay separate.
    #[must_use]
    pub const fn flows(&self) -> &TransportFlows {
        &self.flows
    }
    /// Unexecuted finite Designed profiles, including exact cost units.
    #[must_use]
    pub fn services(&self) -> &BTreeMap<String, TransportService> {
        &self.services
    }
    /// Explicit incomplete directed bulk paths.
    #[must_use]
    pub fn unavailable_bulk_access(&self) -> &[UnavailableBulkAccess] {
        &self.bulk
    }
    /// Source policy service period; a consumer must capture a matching basis.
    #[must_use]
    pub const fn period_days(&self) -> u16 {
        self.period_days
    }
    /// Verified all-actor general-cargo hop diameter; not adequate flow capacity.
    #[must_use]
    pub const fn general_diameter(&self) -> usize {
        self.diameter
    }
    /// Exact graph node identity lookup.
    #[must_use]
    pub fn node(&self, id: &str) -> Option<&TransportNode> {
        self.nodes
            .binary_search_by(|row| row.id().cmp(id))
            .ok()
            .map(|index| &self.nodes[index])
    }
    /// Actor node for a typed location; infrastructure nodes do not shadow actors.
    #[must_use]
    pub fn location_node(&self, location: EconomicLocation) -> Option<&TransportNode> {
        self.nodes.iter().find(|row| {
            row.location() == location
                && matches!(
                    row.kind(),
                    TransportNodeKind::County
                        | TransportNodeKind::Foreign
                        | TransportNodeKind::Dependency
                )
        })
    }
    /// Domestic actor, present only for an admitted county.
    #[must_use]
    pub fn county_node(&self, county: CountyGeoid) -> Option<&TransportNode> {
        self.node(&format!("county:{county}"))
    }
    /// Exact counterpart actor; no sovereignty or ownership inference.
    #[must_use]
    pub fn counterpart_node(&self, counterpart: ForeignCounterpart) -> Option<&TransportNode> {
        self.node(&format!("foreign:{}", counterpart.as_str()))
    }
    /// Exact dependency actor, independent of external counterpart markets.
    #[must_use]
    pub fn dependency_node(&self, dependency: UsDependency) -> Option<&TransportNode> {
        self.node(&format!("dependency:{}", dependency.m49()))
    }
    /// Indexed outgoing edges, retaining source order without a second engine.
    pub fn outgoing<'a>(&'a self, node: &str) -> impl Iterator<Item = &'a TransportLink> {
        self.outgoing
            .get(node)
            .into_iter()
            .flat_map(|indices| indices.iter())
            .map(|&index| &self.links[index])
    }
    /// Exact qualified gzip hash.
    #[must_use]
    pub const fn artifact_sha256(&self) -> [u8; 32] {
        ARTIFACT_SHA256
    }
}
/// Specific source/capture refusals, never an inferred zero or partial graph.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum NationalTransportError {
    /// Byte, row or path bound exceeded.
    Bound,
    /// Bytes differ from the qualified artifact.
    ArtifactDigest,
    /// Invalid gzip, UTF-8 or trailing compressed member.
    Compression,
    /// Malformed/unknown JSON field or enum.
    Json,
    /// Policy content or digest differs from the compiled capture policy.
    Policy,
    /// Source identities/digests differ from their pinned manifest.
    Source,
    /// Invalid county syntax or nonroster county.
    County,
    /// Invalid actor location or point.
    Location,
    /// Invalid, duplicate or noncanonical node identity.
    Node,
    /// Invalid, duplicate or noncanonical link identity.
    Link,
    /// Missing or self-referential endpoint.
    Endpoint,
    /// Invalid finite service profile.
    Profile,
    /// Incompatible cargo/mode or noncanonical class membership.
    ModeCargo,
    /// Invalid, duplicate or missing shared pool.
    Pool,
    /// Missing/wrong county or external coverage.
    Coverage,
    /// Invalid explicit county gateway access.
    Access,
    /// Invalid decimal token; source precision is never repaired.
    Decimal,
    /// Invalid flow dimensions, counts or missingness.
    Flow,
    /// Invalid source factor membership or coverage.
    Factor,
    /// General actor unreachable or exceeds the sixteen-stage bound.
    Reachability,
    /// Claimed audit differs from recomputed graph paths.
    Audit,
}
impl std::fmt::Display for NationalTransportError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "national transport capture refused: {self:?}")
    }
}
impl std::error::Error for NationalTransportError {}
/// Cache one immutable source capture; initializes no game-managed state.
///
/// # Errors
/// Returns the qualified source/capture refusal without a fallback.
pub fn national_transport_reference(
) -> Result<&'static NationalTransportReference, NationalTransportError> {
    REFERENCE
        .get_or_init(|| NationalTransportReference::decode_pinned(ARTIFACT))
        .as_ref()
        .map_err(Clone::clone)
}
fn decode_gzip(bytes: &[u8]) -> Result<String, NationalTransportError> {
    let mut decoder = flate2::bufread::GzDecoder::new(bytes);
    let mut text = String::new();
    decoder
        .by_ref()
        .take((MAX_DECODED_BYTES + 1) as u64)
        .read_to_string(&mut text)
        .map_err(|_| NationalTransportError::Compression)?;
    if text.len() > MAX_DECODED_BYTES {
        return Err(NationalTransportError::Bound);
    }
    if !decoder.into_inner().is_empty() {
        return Err(NationalTransportError::Compression);
    }
    Ok(text)
}
fn parse(text: &str) -> Result<NationalTransportReference, NationalTransportError> {
    let document: raw::Document =
        serde_json::from_str(text).map_err(|_| NationalTransportError::Json)?;
    qualify(&document)?;
    let nodes = validate::nodes(document.nodes)?;
    validate::links(
        &document.links,
        &nodes,
        &document.pools,
        &document.policy.service_profiles,
    )?;
    let access = validate::access(document.county_access, &nodes)?;
    let factors = validate::factors(&document.county_factors, &access)?;
    validate::flows(&document.flows, &access)?;
    let bulk = validate::audit(&document.audit, &nodes, &document.links, &access)?;
    let mut outgoing: BTreeMap<String, Vec<usize>> = BTreeMap::new();
    for (index, link) in document.links.iter().enumerate() {
        outgoing.entry(link.from.clone()).or_default().push(index);
    }
    Ok(NationalTransportReference {
        nodes: nodes.into_boxed_slice(),
        links: document.links.into_boxed_slice(),
        outgoing: outgoing
            .into_iter()
            .map(|(key, rows)| (key, rows.into_boxed_slice()))
            .collect(),
        pools: document.pools.into_boxed_slice(),
        access: access.into_boxed_slice(),
        factors: factors.into_boxed_slice(),
        sources: document.sources.into_boxed_slice(),
        facilities: document.facilities.into_boxed_slice(),
        border: document.border_inbound_2024.into_boxed_slice(),
        flows: document.flows,
        services: document.policy.service_profiles,
        bulk: bulk.into_boxed_slice(),
        period_days: document.policy.period_days,
        diameter: document.audit.general_diameter,
    })
}
fn qualify(document: &raw::Document) -> Result<(), NationalTransportError> {
    let policy: raw::Policy =
        serde_json::from_slice(POLICY).map_err(|_| NationalTransportError::Policy)?;
    let mut digest = String::with_capacity(64);
    for value in sha256_of(POLICY) {
        write!(digest, "{value:02x}").map_err(|_| NationalTransportError::Policy)?;
    }
    if document.schema != "NationalTransportReferenceV1"
        || document.policy != policy
        || document.policy_sha256 != digest
    {
        return Err(NationalTransportError::Policy);
    }
    if document.nodes.len() > 4000
        || document.links.len() > 12_000
        || document.pools.len() > 16_000
        || document.facilities.len() > 1000
        || document.border_inbound_2024.len() > 1000
    {
        return Err(NationalTransportError::Bound);
    }
    let manifest: serde_json::Value =
        serde_json::from_slice(SOURCES).map_err(|_| NationalTransportError::Source)?;
    let expected: Vec<TransportSource> = serde_json::from_value(manifest["sources"].clone())
        .map_err(|_| NationalTransportError::Source)?;
    if document.sources != expected {
        return Err(NationalTransportError::Source);
    }
    Ok(())
}
