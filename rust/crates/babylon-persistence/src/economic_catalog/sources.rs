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
}

/// One captured blob, independent of its evidence interpretation. Compressed
/// sources retain their exact compressed bytes; authored text retains UTF-8.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SourceArtifact {
    kind: SourceArtifactKind,
    bytes: Box<[u8]>,
    digest: [u8; 32],
}
impl SourceArtifact {
    /// Identify owned bytes without implying source-specific admission.
    #[must_use]
    pub fn capture(kind: SourceArtifactKind, bytes: Vec<u8>) -> Self {
        let digest = sha256_of(&bytes);
        Self {
            kind,
            bytes: bytes.into_boxed_slice(),
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
