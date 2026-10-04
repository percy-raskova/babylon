use crate::national_counties::AcsEstimate;
use babylon_kernel::geography::CountyGeoid;

/// Disjoint B11001 household-type leaves; these are not classes or person counts.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum HouseholdType {
    /// Married-couple family households (line 003).
    MarriedCoupleFamily,
    /// Male householder, no spouse present, family households (line 005).
    MaleHouseholderFamily,
    /// Female householder, no spouse present, family households (line 006).
    FemaleHouseholderFamily,
    /// Nonfamily households whose householder lives alone (line 008).
    LivingAlone,
    /// Nonfamily households whose householder does not live alone (line 009).
    NonfamilyNotAlone,
}
impl HouseholdType {
    /// The five disjoint type leaves in source order; excludes parent subtotals.
    pub const ALL: [Self; 5] = [
        Self::MarriedCoupleFamily,
        Self::MaleHouseholderFamily,
        Self::FemaleHouseholderFamily,
        Self::LivingAlone,
        Self::NonfamilyNotAlone,
    ];
    const fn index(self) -> usize {
        match self {
            Self::MarriedCoupleFamily => 2,
            Self::MaleHouseholderFamily => 4,
            Self::FemaleHouseholderFamily => 5,
            Self::LivingAlone => 7,
            Self::NonfamilyNotAlone => 8,
        }
    }
}

/// B19001 annual household income bands in 2024 inflation-adjusted USD.
/// These count households; they are not current wages, wealth or game cash.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(usize)]
pub enum IncomeBand {
    /// Below USD 10,000, including negative and zero income.
    Under10000,
    /// USD 10,000 through 14,999.
    From10000To15000,
    /// USD 15,000 through 19,999.
    From15000To20000,
    /// USD 20,000 through 24,999.
    From20000To25000,
    /// USD 25,000 through 29,999.
    From25000To30000,
    /// USD 30,000 through 34,999.
    From30000To35000,
    /// USD 35,000 through 39,999.
    From35000To40000,
    /// USD 40,000 through 44,999.
    From40000To45000,
    /// USD 45,000 through 49,999.
    From45000To50000,
    /// USD 50,000 through 59,999.
    From50000To60000,
    /// USD 60,000 through 74,999.
    From60000To75000,
    /// USD 75,000 through 99,999.
    From75000To100000,
    /// USD 100,000 through 124,999.
    From100000To125000,
    /// USD 125,000 through 149,999.
    From125000To150000,
    /// USD 150,000 through 199,999.
    From150000To200000,
    /// USD 200,000 or more.
    AtLeast200000,
}
impl IncomeBand {
    /// Sixteen disjoint source bands in ascending income order.
    pub const ALL: [Self; 16] = [
        Self::Under10000,
        Self::From10000To15000,
        Self::From15000To20000,
        Self::From20000To25000,
        Self::From25000To30000,
        Self::From30000To35000,
        Self::From35000To40000,
        Self::From40000To45000,
        Self::From45000To50000,
        Self::From50000To60000,
        Self::From60000To75000,
        Self::From75000To100000,
        Self::From100000To125000,
        Self::From125000To150000,
        Self::From150000To200000,
        Self::AtLeast200000,
    ];
    /// Inclusive lower and exclusive upper bounds; `None` means open-ended.
    /// In particular, the first band has no invented zero-income floor.
    #[must_use]
    pub const fn annual_usd_bounds(self) -> (Option<u64>, Option<u64>) {
        const EDGES: [u64; 15] = [
            10_000, 15_000, 20_000, 25_000, 30_000, 35_000, 40_000, 45_000, 50_000, 60_000, 75_000,
            100_000, 125_000, 150_000, 200_000,
        ];
        let index = self as usize;
        (
            if index == 0 {
                None
            } else {
                Some(EDGES[index - 1])
            },
            if index == 15 {
                None
            } else {
                Some(EDGES[index])
            },
        )
    }
}

/// Historical household earnings in the twelve months covered by B19051.
/// This status is not current employment, wage income, ownership or game cash.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum HistoricalEarnings {
    /// At least one source of household earnings in the historical period.
    WithEarnings,
    /// No household earnings in the historical period; other income may exist.
    NoEarnings,
}

/// Separate county household marginals with their original source uncertainty.
/// No household type/income/person joint distribution is inferred.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CountyHouseholdMargins {
    pub(super) geoid: CountyGeoid,
    pub(super) household_types: Box<[AcsEstimate; 9]>,
    pub(super) household_persons: Box<[AcsEstimate; 12]>,
    pub(super) income_households: Box<[AcsEstimate; 17]>,
    pub(super) earnings_households: Box<[AcsEstimate; 3]>,
    pub(super) population: AcsEstimate,
    pub(super) group_quarters: Option<u64>,
}
impl CountyHouseholdMargins {
    /// Residence county in the exact captured domestic roster.
    #[must_use]
    pub const fn geoid(&self) -> CountyGeoid {
        self.geoid
    }
    /// Total households from B11001, exactly reconciled to the county foundation.
    #[must_use]
    pub fn total_households(&self) -> &AcsEstimate {
        &self.household_types[0]
    }
    /// One disjoint household-type estimate, in households.
    #[must_use]
    pub fn households(&self, kind: HouseholdType) -> &AcsEstimate {
        &self.household_types[kind.index()]
    }
    /// Total persons in households from B11002; excludes group quarters.
    #[must_use]
    pub fn persons_in_households(&self) -> &AcsEstimate {
        &self.household_persons[0]
    }
    /// All resident persons and their own MOE from the captured B01003 control.
    #[must_use]
    pub const fn population_persons(&self) -> &AcsEstimate {
        &self.population
    }
    /// B01003 total minus B11002 household persons: a Derived residual, not a new
    /// source cell. Absent if either estimate is unavailable; no MOE is invented.
    #[must_use]
    pub const fn derived_group_quarters_persons(&self) -> Option<u64> {
        self.group_quarters
    }
    /// Households in the specified annual income band, with original source MOE.
    #[must_use]
    pub fn income_households(&self, band: IncomeBand) -> &AcsEstimate {
        &self.income_households[1 + band as usize]
    }
    /// Historical with/no-earnings household count, retaining its own source MOE.
    #[must_use]
    pub fn historical_earnings_households(&self, status: HistoricalEarnings) -> &AcsEstimate {
        let index = match status {
            HistoricalEarnings::WithEarnings => 1,
            HistoricalEarnings::NoEarnings => 2,
        };
        &self.earnings_households[index]
    }
    /// All three B19051 pairs: total, with earnings, no earnings in past twelve months.
    #[must_use]
    pub fn earnings_source_observations(&self) -> &[AcsEstimate; 3] {
        &self.earnings_households
    }
    /// All nine B11001 pairs, including non-additive parent controls, in line order.
    #[must_use]
    pub fn household_source_observations(&self) -> &[AcsEstimate; 9] {
        &self.household_types
    }
    /// All twelve B11002 pairs, including relatives/nonrelatives, in line order.
    #[must_use]
    pub fn person_source_observations(&self) -> &[AcsEstimate; 12] {
        &self.household_persons
    }
    /// All seventeen B19001 pairs, total followed by sixteen income bins.
    #[must_use]
    pub fn income_source_observations(&self) -> &[AcsEstimate; 17] {
        &self.income_households
    }
}
