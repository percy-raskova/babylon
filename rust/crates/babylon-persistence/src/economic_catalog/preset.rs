//! The pinned production source roster for the explicit national economy preset.
use super::{
    CatalogGeography, EconomicCatalogError, EconomicCatalogInput, SourceArtifact,
    SourceArtifactKind as Kind,
};
use crate::national_economy::NationalGamePolicy;
use babylon_kernel::clock::CampaignDuration;
use babylon_kernel::economic_identity::TradeSet;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(super) enum NationalGraph {
    OperatingSites,
    Companies,
}
impl NationalGraph {
    pub(super) fn from_compiler(compiler: &str) -> Self {
        if matches!(
            compiler,
            "national-world-v8"
                | "national-world-v9"
                | "national-world-v10"
                | "national-world-v11"
                | "national-world-v12"
                | "national-world-v13"
                | "national-company-scale-v1"
                | "national-company-scale-v2"
                | "national-company-scale-v3"
                | "national-company-scale-v4"
        ) {
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
    national_input(None, TradeSet::Ten)
}

/// The national input for these defines: the version 1 or 2 cohort table and mapping as the
/// policy's trade set names them, and the pay table for the twelve. `national_catalog_input()`
/// is this with the shipped defines.
///
/// # Errors
/// `Source(NationalGamePolicy)` for defines that do not parse.
pub fn national_catalog_input_for(
    defines: &[u8],
) -> Result<EconomicCatalogInput, EconomicCatalogError> {
    let policy = NationalGamePolicy::from_captured_bytes(defines)
        .map_err(|_| EconomicCatalogError::Source(Kind::NationalGamePolicy))?;
    Ok(national_input(Some(defines), policy.trades))
}

/// The shipped sources in the catalog's order, with the caller's defines in place of the shipped
/// ones when it gives any, and for the twelve trades the version 2 cohort table and mapping and,
/// last, the pay table.
fn national_input(defines: Option<&[u8]>, trades: TradeSet) -> EconomicCatalogInput {
    // `tools/postgres_national_lifecycle.sh` (`national_input_paths`) reads this block by its
    // shape: the fifteen `include_bytes!` rows of the shipped world, one a line, between
    // `let rows` and its closing line. Keep it.
    let rows: &[(Kind, &[u8])] = &[
        (Kind::GraphDeclarations, include_bytes!("../../../../../content/scenarios/national/structure.bscn")),
        (Kind::Rules, include_bytes!("../../../../../content/scenarios/national/material-cycle.bsl")),
        (Kind::NationalGamePolicy, include_bytes!("../../../../../content/scenarios/national/defines.toml")),
        (Kind::NationalCounties, include_bytes!("../../../../../src/babylon/data/reference/economy/national_county_reference_2024.csv.gz")),
        (Kind::NationalCohorts, include_bytes!("../../../../../src/babylon/data/reference/economy/national_cohort_reference_2024.csv.gz")),
        (Kind::ResidentWorkforce, include_bytes!("../../../../../src/babylon/data/reference/economy/national_resident_workforce_2024.csv.gz")),
        (Kind::NationalAges, crate::national_ages::ARTIFACT),
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
    let twelve = trades == TradeSet::Twelve;
    let mut sources: Vec<SourceArtifact> = rows
        .iter()
        .map(|&(kind, shipped)| {
            let bytes = match kind {
                Kind::NationalGamePolicy => defines.unwrap_or(shipped),
                Kind::NationalCohorts if twelve => crate::national_cohorts::ARTIFACT_V2,
                Kind::CohortFunctionMapping if twelve => crate::national_cohorts::MAPPING_V2,
                _ => shipped,
            };
            SourceArtifact::capture(kind, bytes.to_vec())
        })
        .collect();
    if twelve {
        sources.push(SourceArtifact::capture(
            Kind::NationalTradePay,
            crate::national_trade_pay::ARTIFACT.to_vec(),
        ));
    }
    let mut input = EconomicCatalogInput {
        scenario_id: crate::national_economy::NATIONAL_SCENARIO_ID.into(),
        preset_id: "national-world".into(),
        duration: CampaignDuration::Continuous,
        sources,
        geography: CatalogGeography::NationalCounties,
        organizer: None,
        city_pd: None,
        county_review: None,
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

/// The City PD's rules and the county review's session, which runs after them.
pub(super) fn national_county_review_rules(graph: NationalGraph) -> Vec<u8> {
    let mut rules = national_city_pd_rules(graph);
    rules.push(b'\n');
    rules.extend_from_slice(include_bytes!(
        "../../../../../content/scenarios/national/county-review-cycle.bsl"
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
    if input.organizer.is_some() || input.city_pd.is_some() || input.county_review.is_some() {
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

#[cfg(test)]
mod tests {
    /// `tools/postgres_national_lifecycle.sh` (`national_input_paths`) reads this file by its
    /// shape: every block from a line that opens `let rows` as a borrowed array, at the indentation
    /// of a function's body, to that block's closing line, and in it one path for each
    /// `include_bytes!` row. It expects fifteen. Python tests of the PostgreSQL lane check the
    /// tool; this test lets a Rust gate see a change of the shape first.
    #[test]
    fn the_release_tool_can_read_the_national_rows() {
        let opens = |line: &str| line.starts_with("    let rows: ") && line.contains(" = &[");
        let mut inside = false;
        let mut rows = 0_usize;
        for line in include_str!("preset.rs").lines() {
            if inside && line.starts_with("    ];") {
                inside = false;
            } else if inside {
                rows += usize::from(line.contains("include_bytes!(\""));
            } else {
                inside = opens(line);
            }
        }
        assert_eq!(rows, 15, "the rows that `national_input_paths` reads");
    }
}
