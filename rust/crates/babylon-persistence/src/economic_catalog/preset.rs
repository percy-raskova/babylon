//! The pinned production source roster for the explicit national economy preset.
use super::{CatalogGeography, EconomicCatalogInput, SourceArtifact, SourceArtifactKind as Kind};
use babylon_kernel::clock::CampaignDuration;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum NationalGraph {
    OperatingSites,
    Companies,
}
impl NationalGraph {
    pub(super) fn from_compiler(compiler: &str) -> Self {
        if matches!(compiler, "national-world-v8" | "national-company-scale-v1") {
            Self::Companies
        } else {
            Self::OperatingSites
        }
    }
}

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
    let mut input = EconomicCatalogInput {
        scenario_id: crate::national_economy::NATIONAL_SCENARIO_ID.into(),
        preset_id: "national-world".into(),
        duration: CampaignDuration::Continuous,
        sources: rows
            .iter()
            .map(|(kind, bytes)| SourceArtifact::capture(*kind, bytes.to_vec()))
            .collect(),
        geography: CatalogGeography::NationalCounties,
        organizer: None,
        city_pd: None,
    };
    capture_company_graph(&mut input);
    input
}

/// Exact authored composition for the playable capture, sharing the economic core.
pub(super) fn national_organizer_rules(graph: NationalGraph) -> Vec<u8> {
    let mut rules = national_material_rules(graph);
    rules.push(b'\n');
    rules.extend_from_slice(include_bytes!(
        "../../../../../content/scenarios/national/organizer-cycle.bsl"
    ));
    rules
}

pub(super) fn national_city_pd_rules(graph: NationalGraph) -> Vec<u8> {
    let mut rules = national_organizer_rules(graph);
    rules.push(b'\n');
    rules.extend_from_slice(include_bytes!(
        "../../../../../content/scenarios/national/state-opponent-cycle.bsl"
    ));
    rules
}

pub(super) const COMPANY_STRUCTURE: &[u8] =
    include_bytes!("../../../../../content/scenarios/national/structure-companies.bscn");
const NATIONAL_STRUCTURE: &[u8] =
    include_bytes!("../../../../../content/scenarios/national/structure.bscn");
pub(super) fn national_material_rules(graph: NationalGraph) -> Vec<u8> {
    let mut rules =
        include_bytes!("../../../../../content/scenarios/national/material-cycle.bsl").to_vec();
    if graph == NationalGraph::Companies {
        rules.push(b'\n');
        rules.extend_from_slice(include_bytes!(
            "../../../../../content/scenarios/national/company-portfolio.bsl"
        ));
    }
    rules
}

/// When a new national input opts into companies, couple its unchanged base graph
/// sources to the matching v8 declarations and rules. Reopening verifies canonical bytes.
pub(super) fn capture_company_graph(input: &mut EconomicCatalogInput) {
    if input.organizer.is_some() || input.city_pd.is_some() {
        return;
    }
    let matches = |kind, expected: &[u8]| {
        input
            .sources
            .iter()
            .any(|r| r.kind() == kind && r.bytes() == expected)
    };
    if matches(Kind::GraphDeclarations, NATIONAL_STRUCTURE)
        && matches(
            Kind::Rules,
            &national_material_rules(NationalGraph::OperatingSites),
        )
    {
        for source in &mut input.sources {
            match source.kind() {
                Kind::GraphDeclarations => {
                    *source = SourceArtifact::capture(
                        Kind::GraphDeclarations,
                        COMPANY_STRUCTURE.to_vec(),
                    );
                }
                Kind::Rules => {
                    *source = SourceArtifact::capture(
                        Kind::Rules,
                        national_material_rules(NationalGraph::Companies),
                    );
                }
                _ => {}
            }
        }
    }
}
