//! Fixed geographic and company identities, Designed targets, and achieved opening quantities.
use babylon_kernel::content_digest;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::CompanyPortfolioPolicy;
use babylon_material_circuit::{CompanyId, SiteId};
use std::num::NonZeroU16;

/// Census geographic division codes for the fifty states and the District of Columbia.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum CensusDivision {
    NewEngland = 1,
    MiddleAtlantic,
    EastNorthCentral,
    WestNorthCentral,
    SouthAtlantic,
    EastSouthCentral,
    WestSouthCentral,
    Mountain,
    Pacific,
}
impl CensusDivision {
    #[must_use]
    pub const fn label(self) -> &'static str {
        match self {
            Self::NewEngland => "New England",
            Self::MiddleAtlantic => "Middle Atlantic",
            Self::EastNorthCentral => "East North Central",
            Self::WestNorthCentral => "West North Central",
            Self::SouthAtlantic => "South Atlantic",
            Self::EastSouthCentral => "East South Central",
            Self::WestSouthCentral => "West South Central",
            Self::Mountain => "Mountain",
            Self::Pacific => "Pacific",
        }
    }
    pub const ALL: [Self; 9] = [
        Self::NewEngland,
        Self::MiddleAtlantic,
        Self::EastNorthCentral,
        Self::WestNorthCentral,
        Self::SouthAtlantic,
        Self::EastSouthCentral,
        Self::WestSouthCentral,
        Self::Mountain,
        Self::Pacific,
    ];
    /// Division of the actual site or representative hub county.
    /// # Errors
    /// Refuses state FIPS outside the domestic national opening.
    pub fn from_county(county: CountyGeoid) -> Result<Self, CompanyCaptureError> {
        Ok(match &county.state_fips() {
            b"09" | b"23" | b"25" | b"33" | b"44" | b"50" => Self::NewEngland,
            b"34" | b"36" | b"42" => Self::MiddleAtlantic,
            b"17" | b"18" | b"26" | b"39" | b"55" => Self::EastNorthCentral,
            b"19" | b"20" | b"27" | b"29" | b"31" | b"38" | b"46" => Self::WestNorthCentral,
            b"10" | b"11" | b"12" | b"13" | b"24" | b"37" | b"45" | b"51" | b"54" => {
                Self::SouthAtlantic
            }
            b"01" | b"21" | b"28" | b"47" => Self::EastSouthCentral,
            b"05" | b"22" | b"40" | b"48" => Self::WestSouthCentral,
            b"04" | b"08" | b"16" | b"30" | b"32" | b"35" | b"49" | b"56" => Self::Mountain,
            b"02" | b"06" | b"15" | b"41" | b"53" => Self::Pacific,
            _ => return Err(CompanyCaptureError::UnknownDivision(county)),
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum CompanyBand {
    FirstNational,
    SecondNational,
    Regional(CensusDivision),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct CompanyKey {
    pub function: EconomicFunction,
    pub band: CompanyBand,
    /// Only a separately captured controller-count experiment subdivides the original stratum.
    pub experiment_partition: Option<NonZeroU16>,
}
impl CompanyKey {
    /// Display the modeled function and captured scope without inventing a brand or headquarters.
    #[must_use]
    pub fn label(self) -> String {
        let scope = match self.band {
            CompanyBand::FirstNational => "National 1",
            CompanyBand::SecondNational => "National 2",
            CompanyBand::Regional(division) => division.label(),
        };
        let label = format!("{} · {scope}", self.function.label());
        match self.experiment_partition {
            Some(n) => format!("{label} · experiment {n}"),
            None => label,
        }
    }
    /// Native treasury and issuer identity for this versioned company.
    #[must_use]
    pub fn id(self) -> CompanyId {
        CompanyId::from_bytes(self.identity())
    }

    /// Canonical company identity in the national company-opening namespace.
    #[must_use]
    pub fn identity(self) -> [u8; 32] {
        let mut bytes = b"NationalCompanyV1\0".to_vec();
        bytes.extend_from_slice(self.function.source_key().as_bytes());
        let class = match self.band {
            CompanyBand::FirstNational => [0, 0],
            CompanyBand::SecondNational => [1, 0],
            CompanyBand::Regional(division) => [2, division as u8],
        };
        bytes.extend_from_slice(&class);
        if let Some(partition) = self.experiment_partition {
            bytes.extend_from_slice(b"ExperimentPartitionV1\0");
            bytes.extend_from_slice(&partition.get().to_be_bytes());
        }
        content_digest::sha256_of(&bytes)
    }
}

/// Positive employment shares in basis points, in first national, second national, regional order.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EmploymentTargets([u16; 3]);
impl EmploymentTargets {
    /// # Errors
    /// Refuses an empty target or a total other than 10,000 basis points.
    pub fn try_new(shares: [u16; 3]) -> Result<Self, CompanyCaptureError> {
        if shares.contains(&0) || shares.into_iter().map(u32::from).sum::<u32>() != 10_000 {
            return Err(CompanyCaptureError::InvalidTargets);
        }
        Ok(Self(shares))
    }
    #[must_use]
    pub const fn basis_points(self) -> [u16; 3] {
        self.0
    }
}

/// Explicit controller populations allowed only under the isolated national experiment preset.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExperimentalPopulation {
    ThreeHundred,
    SixHundred,
}
impl ExperimentalPopulation {
    #[must_use]
    pub const fn count(self) -> u16 {
        match self {
            Self::ThreeHundred => 300,
            Self::SixHundred => 600,
        }
    }
    #[must_use]
    pub const fn from_count(n: u16) -> Option<Self> {
        match n {
            300 => Some(Self::ThreeHundred),
            600 => Some(Self::SixHundred),
            _ => None,
        }
    }
}

/// Designed terms decoded only from a company-enabled national policy.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CompanyPolicy {
    pub employment: EmploymentTargets,
    pub treasury_bps: u16,
    pub portfolio: CompanyPortfolioPolicy,
    pub experiment: Option<ExperimentalPopulation>,
}
impl CompanyPolicy {
    /// # Errors
    /// Refuses an invalid employment distribution or treasury rate outside [0, 10,000].
    pub fn try_new(
        employment: [u16; 3],
        treasury_bps: u16,
        portfolio: CompanyPortfolioPolicy,
    ) -> Result<Self, CompanyCaptureError> {
        if treasury_bps > 10_000 || portfolio.validate().is_err() {
            return Err(CompanyCaptureError::InvalidTargets);
        }
        Ok(Self {
            employment: EmploymentTargets::try_new(employment)?,
            treasury_bps,
            portfolio,
            experiment: None,
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompanyCaptureError {
    InvalidTargets,
    UnknownDivision(CountyGeoid),
    InvalidSource(SiteId),
    DuplicateSite(SiteId),
    NoOperatingSite {
        function: EconomicFunction,
        division: CensusDivision,
    },
    TooFewOperatingSites(EconomicFunction),
    ControllerCapacity {
        requested: u16,
        available: usize,
    },
    Arithmetic,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CompanyMember {
    pub site: SiteId,
    pub company: CompanyKey,
    pub county: CountyGeoid,
    pub employed: u64,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CompanyPopulation {
    pub key: CompanyKey,
    pub employed: u64,
    pub sites: u64,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DivisionPopulation {
    pub function: EconomicFunction,
    pub division: CensusDivision,
    pub eligible_employed: u64,
    /// Occupied employment counts in the same order as the captured targets.
    pub assigned_employed: [u64; 3],
    pub assigned_sites: [u64; 3],
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompanyCapture {
    pub targets: EmploymentTargets,
    pub companies: Vec<CompanyPopulation>,
    pub members: Vec<CompanyMember>,
    pub cells: Vec<DivisionPopulation>,
}
