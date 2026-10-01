use crate::national_counties::AcsEstimate;
use babylon_kernel::geography::CountyGeoid;

/// Disjoint published classes of civilian employed residents aged sixteen and over.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum WorkerClass {
    /// Employee of a private for-profit company.
    PrivateCompanyEmployee,
    /// Self-employed in an incorporated business.
    IncorporatedSelfEmployed,
    /// Employee of a private nonprofit organization.
    NonprofitEmployee,
    /// Local government employee.
    LocalGovernmentEmployee,
    /// State government employee.
    StateGovernmentEmployee,
    /// Federal government employee.
    FederalGovernmentEmployee,
    /// Self-employed in an unincorporated business.
    UnincorporatedSelfEmployed,
    /// Unpaid family worker.
    UnpaidFamilyWorker,
}
impl WorkerClass {
    /// The eight disjoint classes in source leaf order, excluding nested controls.
    pub const ALL: [Self; 8] = [
        Self::PrivateCompanyEmployee,
        Self::IncorporatedSelfEmployed,
        Self::NonprofitEmployee,
        Self::LocalGovernmentEmployee,
        Self::StateGovernmentEmployee,
        Self::FederalGovernmentEmployee,
        Self::UnincorporatedSelfEmployed,
        Self::UnpaidFamilyWorker,
    ];
    pub(super) const fn index(self) -> usize {
        match self {
            Self::PrivateCompanyEmployee => 0,
            Self::IncorporatedSelfEmployed => 1,
            Self::NonprofitEmployee => 2,
            Self::LocalGovernmentEmployee => 3,
            Self::StateGovernmentEmployee => 4,
            Self::FederalGovernmentEmployee => 5,
            Self::UnincorporatedSelfEmployed => 6,
            Self::UnpaidFamilyWorker => 7,
        }
    }
}

/// Published source partition, retained for exact estimate and margin provenance.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum SourceSex {
    /// B24080 male source partition.
    Male,
    /// B24080 female source partition.
    Female,
}

/// Resident worker observations with exact source controls and disjoint class sums.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResidentWorkerClasses {
    pub(super) geoid: CountyGeoid,
    pub(super) observations: Box<[AcsEstimate; 21]>,
    pub(super) persons: [Option<u64>; 8],
}
impl ResidentWorkerClasses {
    /// Residence county, not the workplace location.
    #[must_use]
    pub const fn geoid(&self) -> CountyGeoid {
        self.geoid
    }
    /// Civilian employed residents aged sixteen and over, including source margin.
    #[must_use]
    pub fn total(&self) -> &AcsEstimate {
        &self.observations[0]
    }
    /// Exact male-plus-female class estimate; unavailable if either estimate is unavailable.
    #[must_use]
    pub const fn persons(&self, class: WorkerClass) -> Option<u64> {
        self.persons[class.index()]
    }
    /// Original sex-specific class estimate and its own margin; margins are not added.
    #[must_use]
    pub fn observation(&self, class: WorkerClass, sex: SourceSex) -> &AcsEstimate {
        let offset = if sex == SourceSex::Female { 10 } else { 0 };
        &self.observations[3 + class.index() + offset]
    }
    /// All twenty-one source estimate/MOE pairs in B24080 line order.
    #[must_use]
    pub fn source_observations(&self) -> &[AcsEstimate; 21] {
        &self.observations
    }
}
