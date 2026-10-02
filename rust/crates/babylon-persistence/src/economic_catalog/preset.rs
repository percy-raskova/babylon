//! The pinned production source roster for the explicit national economy preset.
use super::{CatalogGeography, EconomicCatalogInput, SourceArtifact, SourceArtifactKind as Kind};
use babylon_kernel::clock::CampaignDuration;

/// Capture the committed source artifacts and Designed policy.
/// No live dataset or caller-provided Michigan defines file participates.
#[must_use]
pub fn national_catalog_input() -> EconomicCatalogInput {
    let rows: &[(Kind, &[u8])] = &[
        (Kind::GraphDeclarations, include_bytes!("../../../../../content/scenarios/national/structure.bscn")),
        (Kind::Rules, include_bytes!("../../../../../content/scenarios/national/material-cycle.bsl")),
        (Kind::NationalGamePolicy, include_bytes!("../../../../../content/scenarios/national/defines.toml")),
        (Kind::NationalCounties, include_bytes!("../../../../../src/babylon/data/reference/economy/national_county_reference_2024.csv.gz")),
        (Kind::NationalCohorts, include_bytes!("../../../../../src/babylon/data/reference/economy/national_cohort_reference_2024.csv.gz")),
        (Kind::ResidentWorkforce, include_bytes!("../../../../../src/babylon/data/reference/economy/national_resident_workforce_2024.csv.gz")),
        (Kind::NationalHouseholds, include_bytes!("../../../../../src/babylon/data/reference/economy/national_household_reference_2024.csv.gz")),
        (Kind::NationalTransport, include_bytes!("../../../../../src/babylon/data/reference/transport/national_transport_reference_2024.json.gz")),
        (Kind::InternationalTrade, include_bytes!("../../../../../src/babylon/data/reference/economy/international_counterpart_reference_2024.csv.gz")),
        (Kind::WorldPopulation, include_bytes!("../../../../../src/babylon/data/reference/economy/world_population_reference_2024.csv.gz")),
        (Kind::CohortFunctionMapping, include_bytes!("../../../../../contracts/national_qcew_function_mapping_v1.json")),
        (Kind::CounterpartMembership, include_bytes!("../../../../../contracts/international_counterpart_membership_v1.json")),
        (Kind::PopulationScopePolicy, include_bytes!("../../../../../contracts/world_population_scope_v1.json")),
        (Kind::TransportPolicy, include_bytes!("../../../../../contracts/national_transport_policy_v1.json")),
        (Kind::TransportSourceManifest, include_bytes!("../../../../../tools/national_transport_2024_sources.json")),
    ];
    EconomicCatalogInput {
        scenario_id: crate::national_economy::NATIONAL_SCENARIO_ID.into(),
        preset_id: "national-world".into(),
        duration: CampaignDuration::Continuous,
        sources: rows
            .iter()
            .map(|(kind, bytes)| SourceArtifact::capture(*kind, bytes.to_vec()))
            .collect(),
        geography: CatalogGeography::NationalCounties,
        organizer: None,
    }
}
