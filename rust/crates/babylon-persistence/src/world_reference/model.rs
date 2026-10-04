//! Geographic source coverage is distinct from finite game accounts.

use babylon_kernel::economic_location::{ForeignCounterpart, UsDependency};

/// Pinned reporting membership; domestic population is context, not ACS replacement.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum WorldScope {
    /// One of the twelve Designed foreign market aggregations.
    Foreign(ForeignCounterpart),
    /// Explicit US dependency, excluded from foreign counterparts.
    Dependency(UsDependency),
    /// US national source control; the domestic campaign uses its county ACS capture.
    DomesticContext,
    /// A reporting identity outside the market aggregations.
    Nonmarket,
}

/// Source relationship to the US, independent of a foreign market aggregation.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum UsRelationship {
    /// No special US relationship in the captured classification.
    None,
    /// US domestic context.
    Domestic,
    /// Explicit dependency scope.
    Dependency,
    /// Micronesia, Marshall Islands or Palau; a foreign state, not a dependency.
    FreelyAssociatedState,
}

/// Population availability and scope qualification; no variant implies a fallback.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PopulationStatus {
    /// Integral persons derived from a UN medium-variant projection, not a census.
    SourceProjection,
    /// The Finland/Åland scope allocation explicitly recorded in the Designed policy.
    DesignedScopeApportionment,
    /// Counted only in a named parent in the same economic counterpart.
    IncludedInParent,
    /// No independently published population in this capture.
    NotPublished,
    /// A disjoint trade child of a population parent, never another population.
    TradeOnly,
}

/// Exact UN projection receipt; its raw unit is thousands of persons.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PopulationSource {
    /// Source variant, explicitly distinct from an observed census.
    pub kind: String,
    /// Date of the source projection, not the artifact build date.
    pub date: String,
    /// Original workbook sheet name.
    pub sheet: String,
    /// Original one-based workbook row.
    pub row: u64,
    /// Original country/area name.
    pub area_name: String,
    /// Source scope-note numbers, retained for the pinned metadata's explanations.
    pub notes: String,
    /// Literal numeric XML token, before conversion into integral persons.
    pub thousands_raw: String,
}

/// One population measure with explicit absent or parent-accounted values.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PopulationReference {
    pub(super) status: PopulationStatus,
    pub(super) persons: Option<u64>,
    pub(super) accounted_in: Option<String>,
    pub(super) source: Option<PopulationSource>,
}
impl PopulationReference {
    /// Availability or Designed allocation qualification.
    #[must_use]
    pub const fn status(&self) -> PopulationStatus {
        self.status
    }
    /// Independently additive persons; absence is never an observed zero.
    #[must_use]
    pub const fn persons(&self) -> Option<u64> {
        self.persons
    }
    /// Source identity carrying these persons, including self for independent rows.
    #[must_use]
    pub fn accounted_in_identity(&self) -> Option<&str> {
        self.accounted_in.as_deref()
    }
    /// Original UN projection receipt, when present; allocation policy is separate.
    #[must_use]
    pub const fn source(&self) -> Option<&PopulationSource> {
        self.source.as_ref()
    }
    /// Literal original thousands, which can differ from a Designed scoped allocation.
    #[must_use]
    pub fn source_thousands_raw(&self) -> Option<&str> {
        self.source
            .as_ref()
            .map(|source| source.thousands_raw.as_str())
    }
}

/// Availability of an annual goods-trade observation, distinct from a zero token.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TradeStatus {
    /// A published annual observation.
    Published,
    /// A published reporter with an absent annual cell.
    MissingCell,
    /// No selected published reporter row.
    NotPublished,
}

/// Literal 2024 goods-trade observations in millions of nominal USD.
/// These strings are source evidence, not cash, credit or physical quantities.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct GoodsTradeReference {
    pub(super) imports: Option<String>,
    pub(super) exports: Option<String>,
    pub(super) imports_status: TradeStatus,
    pub(super) exports_status: TradeStatus,
    pub(super) census_code: Option<String>,
}
impl GoodsTradeReference {
    /// Goods entering the US from this reporting area, original annual XML token.
    #[must_use]
    pub fn us_imports_annual_millions_raw(&self) -> Option<&str> {
        self.imports.as_deref()
    }
    /// Goods leaving the US for this reporting area, original annual XML token.
    #[must_use]
    pub fn us_exports_annual_millions_raw(&self) -> Option<&str> {
        self.exports.as_deref()
    }
    /// Import observation availability, separate from value.
    #[must_use]
    pub const fn imports_status(&self) -> TradeStatus {
        self.imports_status
    }
    /// Export observation availability, separate from value.
    #[must_use]
    pub const fn exports_status(&self) -> TradeStatus {
        self.exports_status
    }
    /// Schedule C reporting code, not universally an ISO identifier.
    #[must_use]
    pub fn census_code(&self) -> Option<&str> {
        self.census_code.as_deref()
    }
}

/// One source reporting identity assigned exactly once to a scope.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WorldMember {
    pub(super) identity: String,
    pub(super) name: String,
    pub(super) scope: WorldScope,
    pub(super) us_relationship: UsRelationship,
    pub(super) population: PopulationReference,
    pub(super) trade: GoodsTradeReference,
}
impl WorldMember {
    /// Pinned `m49:NNN` or explicit `census:NNNN` source identity.
    #[must_use]
    pub fn identity(&self) -> &str {
        &self.identity
    }
    /// Reporting-area name, without a sovereignty or class inference.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }
    /// Independent geographic membership axis.
    #[must_use]
    pub const fn scope(&self) -> WorldScope {
        self.scope
    }
    /// Source relationship kept separate from counterpart membership.
    #[must_use]
    pub const fn us_relationship(&self) -> UsRelationship {
        self.us_relationship
    }
    /// Population source and scope qualification.
    #[must_use]
    pub const fn population(&self) -> &PopulationReference {
        &self.population
    }
    /// Both goods-trade directions, preserved without netting.
    #[must_use]
    pub const fn goods_trade(&self) -> &GoodsTradeReference {
        &self.trade
    }
}

/// Known persons in a counterpart and independently missing source identities.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PopulationSubtotal {
    pub(super) known_persons: u64,
    pub(super) missing: Vec<String>,
}
impl PopulationSubtotal {
    /// Sum of additive known rows only; not an imputed complete population.
    #[must_use]
    pub const fn known_persons(&self) -> u64 {
        self.known_persons
    }
    /// Absent independent observations; parent-counted rows are not missing twice.
    #[must_use]
    pub fn missing_identities(&self) -> &[String] {
        &self.missing
    }
}

/// One of exactly twelve independently admitted population subtotals.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CounterpartReference {
    pub(super) id: ForeignCounterpart,
    pub(super) population: PopulationSubtotal,
}
impl CounterpartReference {
    /// Closed game market identity.
    #[must_use]
    pub const fn id(&self) -> ForeignCounterpart {
        self.id
    }
    /// Additive source population with missingness, not labor-force capacity.
    #[must_use]
    pub const fn population(&self) -> &PopulationSubtotal {
        &self.population
    }
}
