use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership};
use babylon_kernel::economic_location::EconomicLocation;
use babylon_kernel::geography::CountyGeoid;

/// Disjoint source grouping; `None` means unclassified evidence, never an executable function.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct CohortKey {
    /// Exact membership identity from the independent county roster.
    pub county: CountyGeoid,
    /// Designed source function; no code 99 fallback assignment.
    pub function: Option<EconomicFunction>,
    /// Source ownership axis, independent of technical function.
    pub ownership: QcewOwnership,
}
/// One counted background workplace identity; source axes never blend.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct WorkplaceCohortKey {
    /// Fixed county or bounded external location.
    pub location: EconomicLocation,
    /// Technical function, independent of ownership.
    pub function: EconomicFunction,
    /// Source ownership axis; `None` is an explicitly Designed workplace.
    pub ownership: Option<QcewOwnership>,
}
impl WorkplaceCohortKey {
    /// Pair one captured source cohort with its admitted location.
    #[must_use]
    pub fn source_backed(key: CohortKey, location: EconomicLocation) -> Option<Self> {
        if EconomicLocation::domestic_county(key.county).ok()? != location {
            return None;
        }
        Some(Self {
            location,
            function: key.function?,
            ownership: Some(key.ownership),
        })
    }
    /// Name a Designed workplace without inventing a QCEW ownership claim.
    #[must_use]
    pub const fn designed(location: EconomicLocation, function: EconomicFunction) -> Self {
        Self {
            location,
            function,
            ownership: None,
        }
    }
    /// Whether two admitted sites share one counted background workplace row.
    /// Every causal axis (location, function, source ownership) must agree; the
    /// individual site identity stays foreground-only.
    #[must_use]
    pub fn equivalent_for_consolidation(&self, other: &Self) -> bool {
        self.location == other.location
            && self.function == other.function
            && self.ownership == other.ownership
    }
}

/// Availability of source jobs, payroll and weekly mean wage.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum QcewDisclosure {
    /// Blank source disclosure code; all selected measures are published.
    Published,
    /// Source code N; establishments remain published, other measures unknown.
    Suppressed,
}
impl QcewDisclosure {
    /// Original QCEW disclosure code, distinct from the compact P marker.
    #[must_use]
    pub const fn source_code(self) -> &'static str {
        match self {
            Self::Published => "",
            Self::Suppressed => "N",
        }
    }
}
/// One member of the disjoint source NAICS cut; all amounts retain source units.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SourceMember {
    /// Exact source NAICS identity, including the 44-45 and 48-49 group codes.
    pub naics_code: String,
    /// Original publication/suppression distinction.
    pub disclosure: QcewDisclosure,
    /// Published annual-average establishments, including source-rounded zeros.
    pub annual_average_establishments: u64,
    /// Annual-average covered workplace jobs; not a count of distinct persons.
    pub annual_average_jobs: Option<u64>,
    /// Annual payroll in USD; unknown under suppression, never estimated from means.
    pub annual_payroll_usd: Option<u64>,
    /// Published mean weekly wage in USD. Means are never additive across members.
    pub mean_weekly_wage_usd: Option<u64>,
}
/// Exact checked sum of the published members of one additive measure.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct KnownSubtotal {
    pub(super) known_sum: u64,
    pub(super) published_members: usize,
    pub(super) member_count: usize,
}
impl KnownSubtotal {
    /// Sum of available values; zero is not a claim that missing members were zero.
    #[must_use]
    pub const fn known_subtotal(self) -> u64 {
        self.known_sum
    }
    /// Number of source members publishing this particular measure.
    #[must_use]
    pub const fn published_members(self) -> usize {
        self.published_members
    }
    /// Number of source members missing this particular measure.
    #[must_use]
    pub const fn missing_members(self) -> usize {
        self.member_count - self.published_members
    }
    /// Complete total only when every captured source member publishes the measure.
    #[must_use]
    pub const fn complete_total(self) -> Option<u64> {
        if self.published_members == self.member_count {
            Some(self.known_sum)
        } else {
            None
        }
    }
}
/// One immutable source group with independent per-measure completeness.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CohortReference {
    pub(super) key: CohortKey,
    pub(super) admitted: bool,
    pub(super) establishments: KnownSubtotal,
    pub(super) jobs: KnownSubtotal,
    pub(super) annual_payroll_usd: KnownSubtotal,
    pub(super) members: Box<[SourceMember]>,
}
impl CohortReference {
    /// Disjoint source identity; not a generated game firm or workplace.
    #[must_use]
    pub const fn key(&self) -> CohortKey {
        self.key
    }
    /// Positive-source-activity eligibility for a later compiler; no runtime allocation.
    #[must_use]
    pub const fn is_admitted(&self) -> bool {
        self.admitted
    }
    /// Source-supported establishment subtotal and its independent completeness.
    #[must_use]
    pub const fn establishments(&self) -> KnownSubtotal {
        self.establishments
    }
    /// Source-supported workplace-job subtotal; not distinct resident persons.
    #[must_use]
    pub const fn jobs(&self) -> KnownSubtotal {
        self.jobs
    }
    /// Source-supported annual USD payroll subtotal and completeness.
    #[must_use]
    pub const fn annual_payroll_usd(&self) -> KnownSubtotal {
        self.annual_payroll_usd
    }
    /// Every source member exactly once, in strict lexical NAICS order.
    #[must_use]
    pub fn members(&self) -> &[SourceMember] {
        &self.members
    }
}
