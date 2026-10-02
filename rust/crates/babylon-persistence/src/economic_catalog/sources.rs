//! Singular captured source rows. Hashing a row identifies bytes; the catalog's
//! source-specific admission must still prove its pinned schema and semantics.

use babylon_kernel::content_digest::sha256_of;

/// Exact current source role. Aggregate or unknown roles never silently bind.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
#[repr(u8)]
pub enum SourceArtifactKind {
    GraphDeclarations = 1,
    PreludeDeclarations = 2,
    Rules = 3,
    DesignedPolicy = 4,
    NationalCounties = 5,
    NationalCohorts = 6,
    ResidentWorkforce = 7,
    NationalTransport = 8,
    InternationalTrade = 9,
    WorldPopulation = 10,
    CohortFunctionMapping = 11,
    CounterpartMembership = 12,
    PopulationScopePolicy = 13,
    TransportPolicy = 14,
    TransportSourceManifest = 15,
    MichiganDefines = 16,
    MichiganQualification = 17,
    MichiganPhysicalNetwork = 18,
    MichiganDynamicHexes = 19,
    NationalGamePolicy = 20,
    MichiganCountyEvidence = 21,
    MichiganSectorEvidence = 22,
    MichiganSectorSources = 23,
    MichiganRegionalTopology = 24,
    MichiganIndustryBaseline = 25,
    MichiganCommodityRoster = 26,
    MichiganStatewideManifest = 27,
    MichiganMaintenanceIndustry = 28,
    MichiganExperiment = 29,
    /// Exact campaign UUID needed to regenerate the authored organizer authority.
    OrganizerContext = 30,
    /// Programmatic source input, distinct from an original gzip artifact.
    MichiganQualificationJson = 31,
    MichiganPhysicalNetworkJson = 32,
    /// Exact authored intervention parameters, never a generated material state.
    MichiganControlOverrides = 33,
    /// Exact local spatial products, checked against the captured H3 detail.
    MichiganSpatialProducts = 34,
}

/// One captured blob, independent of its evidence interpretation. Compressed
/// sources retain their exact compressed bytes; authored text retains UTF-8.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SourceArtifact {
    kind: SourceArtifactKind,
    bytes: std::sync::Arc<[u8]>,
    digest: [u8; 32],
}
impl SourceArtifact {
    /// Identify owned bytes without implying source-specific admission.
    #[must_use]
    pub fn capture(kind: SourceArtifactKind, bytes: Vec<u8>) -> Self {
        let digest = sha256_of(&bytes);
        Self {
            kind,
            bytes: bytes.into(),
            digest,
        }
    }
    #[must_use]
    pub const fn kind(&self) -> SourceArtifactKind {
        self.kind
    }
    #[must_use]
    pub fn bytes(&self) -> &[u8] {
        &self.bytes
    }
    #[must_use]
    pub const fn digest(&self) -> [u8; 32] {
        self.digest
    }
}

impl TryFrom<u8> for SourceArtifactKind {
    type Error = super::EconomicCatalogError;
    fn try_from(value: u8) -> Result<Self, Self::Error> {
        match value {
            1 => Ok(Self::GraphDeclarations),
            2 => Ok(Self::PreludeDeclarations),
            3 => Ok(Self::Rules),
            4 => Ok(Self::DesignedPolicy),
            5 => Ok(Self::NationalCounties),
            6 => Ok(Self::NationalCohorts),
            7 => Ok(Self::ResidentWorkforce),
            8 => Ok(Self::NationalTransport),
            9 => Ok(Self::InternationalTrade),
            10 => Ok(Self::WorldPopulation),
            11 => Ok(Self::CohortFunctionMapping),
            12 => Ok(Self::CounterpartMembership),
            13 => Ok(Self::PopulationScopePolicy),
            14 => Ok(Self::TransportPolicy),
            15 => Ok(Self::TransportSourceManifest),
            16 => Ok(Self::MichiganDefines),
            17 => Ok(Self::MichiganQualification),
            18 => Ok(Self::MichiganPhysicalNetwork),
            19 => Ok(Self::MichiganDynamicHexes),
            20 => Ok(Self::NationalGamePolicy),
            21 => Ok(Self::MichiganCountyEvidence),
            22 => Ok(Self::MichiganSectorEvidence),
            23 => Ok(Self::MichiganSectorSources),
            24 => Ok(Self::MichiganRegionalTopology),
            25 => Ok(Self::MichiganIndustryBaseline),
            26 => Ok(Self::MichiganCommodityRoster),
            27 => Ok(Self::MichiganStatewideManifest),
            28 => Ok(Self::MichiganMaintenanceIndustry),
            29 => Ok(Self::MichiganExperiment),
            30 => Ok(Self::OrganizerContext),
            31 => Ok(Self::MichiganQualificationJson),
            32 => Ok(Self::MichiganPhysicalNetworkJson),
            33 => Ok(Self::MichiganControlOverrides),
            34 => Ok(Self::MichiganSpatialProducts),
            _ => Err(super::EconomicCatalogError::WireTag),
        }
    }
}
