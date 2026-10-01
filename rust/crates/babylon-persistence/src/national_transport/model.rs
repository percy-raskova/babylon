use babylon_kernel::{economic_location::EconomicLocation, geography::CountyGeoid};
use serde::Deserialize;
use std::collections::BTreeMap;

/// Explicit physical service mode; context-only FAF modes are never executable edges.
#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "snake_case")]
pub enum TransportMode {
    /// Aircraft service; general cargo only.
    Air,
    /// Local transfer/terminal handling, not proof of a road.
    Handling,
    /// Directed crude-oil pipeline service.
    Pipeline,
    /// Vessel service, with a finite shared pool.
    Sea,
    /// Designed road corridor or source-qualified local road.
    Truck,
}
/// Closed compatibility classes; assignment of a game good remains a compiler decision.
#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "snake_case")]
pub enum CargoClass {
    /// Crude oil; distinct from refined products.
    CrudeOil,
    /// Ores, coal and other dry bulk; never airborne here.
    DryBulk,
    /// Air-compatible general cargo.
    General,
    /// Refined liquid products; cannot use the TAPS crude pipeline.
    RefinedLiquid,
}
/// A source location or explicitly Designed infrastructure/market grouping.
#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum TransportNodeKind {
    /// Source public/open airport.
    Airport,
    /// BTS border reporting gateway, not exact bridge geometry.
    Border,
    /// Source-qualified bulk port or port-complex scope.
    Bulk,
    /// One of the 3,144 domestic county actors.
    County,
    /// Separately accounted US dependency.
    Dependency,
    /// Source FAF zone used as a Designed routing hub.
    Faf,
    /// One of twelve Designed counterpart markets.
    Foreign,
    /// Source pipeline/sea terminal with explicit product flags.
    Liquid,
    /// Selected NTAD roll-on/roll-off general-cargo gateway.
    Marine,
    /// One of eight Designed continental trunk hubs.
    Trunk,
}
/// Immutable source/topology node; no productive capacity follows from its existence.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct TransportNode {
    pub(super) id: String,
    pub(super) kind: TransportNodeKind,
    pub(super) location: EconomicLocation,
    pub(super) latitude: Option<String>,
    pub(super) longitude: Option<String>,
    pub(super) source_id: String,
    pub(super) source_key: String,
}
impl TransportNode {
    /// Stable source-scoped graph identifier.
    #[must_use]
    pub fn id(&self) -> &str {
        &self.id
    }
    /// Infrastructure/actor role.
    #[must_use]
    pub const fn kind(&self) -> TransportNodeKind {
        self.kind
    }
    /// Typed actor geography; source membership is checked independently.
    #[must_use]
    pub const fn location(&self) -> EconomicLocation {
        self.location
    }
    /// Source point, absent for an aggregate without a point; not a route geometry.
    #[must_use]
    pub fn point(&self) -> Option<(&str, &str)> {
        self.latitude.as_deref().zip(self.longitude.as_deref())
    }
    /// Exact captured source and its record key.
    #[must_use]
    pub fn source(&self) -> (&str, &str) {
        (&self.source_id, &self.source_key)
    }
}
/// One Designed directed edge; no transport operator is paid by this reference.
#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct TransportLink {
    pub(super) id: String,
    pub(super) from: String,
    pub(super) to: String,
    pub(super) mode: TransportMode,
    pub(super) cargo: Vec<CargoClass>,
    pub(super) profile: String,
    pub(super) pools: Vec<String>,
    pub(super) evidence: Vec<String>,
}
impl TransportLink {
    /// Stable edge identity.
    #[must_use]
    pub fn id(&self) -> &str {
        &self.id
    }
    /// Exact endpoint node identities.
    #[must_use]
    pub fn endpoints(&self) -> (&str, &str) {
        (&self.from, &self.to)
    }
    /// Physical service mode.
    #[must_use]
    pub const fn mode(&self) -> TransportMode {
        self.mode
    }
    /// Compatible cargo classes, in canonical order.
    #[must_use]
    pub fn cargo(&self) -> &[CargoClass] {
        &self.cargo
    }
    /// Designed numeric profile key.
    #[must_use]
    pub fn profile(&self) -> &str {
        &self.profile
    }
    /// Every finite shared pool consumed by this leg.
    #[must_use]
    pub fn pools(&self) -> &[String] {
        &self.pools
    }
    /// Source IDs and/or the explicit policy marker supporting the edge.
    #[must_use]
    pub fn evidence(&self) -> &[String] {
        &self.evidence
    }
}
/// Exact finite Designed throughput for one shared service period.
#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct TransportPool {
    /// Stable resource identity, shared by opposite directions when declared.
    pub id: String,
    /// Finite positive grams, never inferred from a count of facilities.
    pub capacity_grams: u64,
}
/// Designed opening service values. Costs are context until a monetary consumer pays a carrier.
#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct TransportService {
    /// Exact physical mode.
    pub mode: TransportMode,
    /// Positive service periods, distinct from administrative hops.
    pub travel_periods: u16,
    /// Finite grams per captured service period.
    pub capacity_grams: u64,
    /// Unexecuted currency micros per metric tonne, not an already paid charge.
    pub cost_micros_per_tonne: u64,
    /// Designed physical loss parts per million.
    pub loss_ppm: u32,
}
/// Source county allocation; a FAF factor does not prove road access.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountyTransportAccess {
    /// Independently roster-admitted county.
    pub county: CountyGeoid,
    /// Three-digit truck-factor FAF membership used for the Designed routing hub.
    pub zone: String,
    /// Explicit FAA gateway for the island/noncontiguous override, otherwise absent.
    pub airport: Option<String>,
}
/// Explicit missing bulk access, not zero production or an airborne workaround.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct UnavailableBulkAccess {
    /// Roster-admitted county.
    pub county: CountyGeoid,
    /// A bulk class with an incomplete path.
    pub cargo: CargoClass,
    /// Directed reachability from the continental control node.
    pub can_receive: bool,
    /// Directed reachability to the continental control node.
    pub can_supply: bool,
}
/// Exact captured source file identity.
#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct TransportSource {
    /// Stable source key.
    pub id: String,
    /// Provenance location, never read by the native capture.
    pub path: String,
    /// Exact lowercase SHA-256 source bytes.
    pub sha256: String,
    /// Source size before selection/aggregation.
    pub bytes: u64,
    /// Material relation and vintage qualification.
    pub relation: String,
}
/// Exact decimal known sum with publication count; no binary-float normalization.
#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct FlowValue {
    /// Sum of available source decimal tokens, preserving decimal precision.
    pub known_sum: String,
    /// Members publishing this measure, which may be fewer than the group's rows.
    pub published: u64,
}
/// Selected flow evidence in native units, never an installed capacity or realized game flow.
#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct FlowEvidence {
    /// Explicit native dimension tuple documented by its containing collection.
    pub key: Vec<String>,
    /// Number of original source rows represented by this aggregate.
    pub rows: u64,
    /// Tons(thousands), value(2017USD millions), currentUSD millions, ton-miles(millions).
    pub values: [FlowValue; 4],
}
/// Source-qualified flow collections; foreign dimensions remain FAF8, not twelve markets.
#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct TransportFlows {
    /// Full scanned source row count.
    pub source_rows: u64,
    /// Number of all domestic aggregates before deterministic selection.
    pub domestic_aggregate_rows: u64,
    /// Selected keys: origin, destination, domestic mode, SCTG5.
    pub domestic: Vec<FlowEvidence>,
    /// Complete keys: trade direction, FAF foreign region, foreign mode, domestic mode, SCTG5.
    pub foreign: Vec<FlowEvidence>,
    /// Complete keys: trade direction, domestic mode, SCTG5; non-additive with detail.
    pub controls: Vec<FlowEvidence>,
}
/// Selected literal facility fields; vintage and original obsolete county labels remain intact.
#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct TransportFacility {
    /// Exact source file key.
    pub source_id: String,
    /// Native source record identifier.
    pub key: String,
    /// Literal source fields, including status/product/access flags and vintage.
    pub fields: BTreeMap<String, Option<String>>,
}

/// Mode of an experimental county-allocation factor; not an executable route.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AllocationMode {
    /// Truck source estimates.
    Truck,
    /// Rail source estimates; no national rail route inferred.
    Rail,
    /// Water source estimates; no access/berth inferred.
    Water,
    /// Pipeline source estimates; no pipeline edge inferred.
    Pipeline,
}
/// Independent source direction; origins and destinations are never netted.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AllocationDirection {
    /// Origin allocation.
    Origin,
    /// Destination allocation.
    Destination,
}
/// Typed source allocation factor with original duplicate multiplicity preserved.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountyAllocationFactor {
    /// Source estimation mode.
    pub mode: AllocationMode,
    /// Independent source direction.
    pub direction: AllocationDirection,
    /// Roster-admitted source county.
    pub county: CountyGeoid,
    /// Exact three-digit source zone, independent of road connectivity.
    pub zone: String,
    /// One of five original SCTG group keys, validated without regrouping commodities.
    pub commodity_group: String,
    /// Original nonnegative decimal, never rounded or normalized here.
    pub decimal_factor: String,
    /// Original source rows having this exact key and identical factor. Never sum twice.
    pub source_rows: u8,
}
