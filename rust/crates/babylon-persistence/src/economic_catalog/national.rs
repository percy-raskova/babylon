//! National admission uses supplied checked source bytes only.
use super::preset::NationalGraph;
use super::{
    EconomicCatalogError, EconomicCatalogInput, EconomicOpening, EconomicSourceView,
    SourceArtifactKind as Kind,
};
use crate::national_ages::NationalAgeReference;
use crate::national_cohorts::NationalCohortReference;
use crate::national_counties::NationalCountyReference;
use crate::national_economy::companies::{CompanyCapture, CompanyFinances};
use crate::national_economy::grain::NationalGenerationWitness;
use crate::national_economy::NationalAidCapture;
use crate::national_economy::NationalGamePolicy;
use crate::national_household_refinement::NationalDetailPartition;
use crate::national_households::NationalHouseholdReference;
use crate::national_resident_workforce::NationalResidentWorkforceReference;
use crate::national_transport::NationalTransportReference;
use crate::world_reference::WorldReference;
use babylon_bsl::scenario_seed::GraphSeed;
use babylon_graph::hypergraph_store::HypergraphStore;
use std::result::Result as StdResult;

type Result<T> = StdResult<T, EconomicCatalogError>;

pub(super) struct NationalSources {
    pub(super) companies: Option<CompanyCapture>,
    pub(super) finances: Option<CompanyFinances>,
    pub(super) counties: NationalCountyReference,
    pub(super) aid: NationalAidCapture,
    pub(super) representation: NationalGenerationWitness,
    /// Authored foreground identities and counted background cohorts fixed at opening.
    pub(super) detail: NationalDetailPartition,
    cohorts: NationalCohortReference,
    residents: NationalResidentWorkforceReference,
    households: NationalHouseholdReference,
    ages: Option<NationalAgeReference>,
    world: WorldReference,
    transport: NationalTransportReference,
}
impl NationalSources {
    pub(super) fn admit(
        input: &EconomicCatalogInput,
        graph: NationalGraph,
    ) -> Result<(Self, EconomicOpening)> {
        let b = |kind| super::capture::source(input, kind);
        let policy = NationalGamePolicy::from_captured_bytes(b(Kind::NationalGamePolicy)?)
            .map_err(|_| EconomicCatalogError::Source(Kind::NationalGamePolicy))?;
        validate_graph_sources(input, graph, &policy)?;
        let counties = NationalCountyReference::decode_pinned(b(Kind::NationalCounties)?)
            .map_err(|_| EconomicCatalogError::Source(Kind::NationalCounties))?;
        let cohorts = NationalCohortReference::decode_captured(
            b(Kind::NationalCohorts)?,
            b(Kind::CohortFunctionMapping)?,
            &counties,
        )
        .map_err(|_| EconomicCatalogError::Source(Kind::NationalCohorts))?;
        let residents = NationalResidentWorkforceReference::decode_captured(
            b(Kind::ResidentWorkforce)?,
            &counties,
        )
        .map_err(|_| EconomicCatalogError::Source(Kind::ResidentWorkforce))?;
        let households =
            NationalHouseholdReference::decode_captured(b(Kind::NationalHouseholds)?, &counties)
                .map_err(|_| EconomicCatalogError::Source(Kind::NationalHouseholds))?;
        let world = WorldReference::decode_captured(
            b(Kind::WorldPopulation)?,
            b(Kind::InternationalTrade)?,
            b(Kind::CounterpartMembership)?,
            b(Kind::PopulationScopePolicy)?,
        )
        .map_err(|_| EconomicCatalogError::Source(Kind::WorldPopulation))?;
        let transport = NationalTransportReference::decode_captured(
            b(Kind::NationalTransport)?,
            b(Kind::TransportPolicy)?,
            b(Kind::TransportSourceManifest)?,
            &counties,
        )
        .map_err(|_| EconomicCatalogError::Source(Kind::NationalTransport))?;

        let ages = if policy.household_lifecycle.is_some() {
            Some(
                NationalAgeReference::decode_captured(b(Kind::NationalAges)?, &counties)
                    .map_err(|_| EconomicCatalogError::Source(Kind::NationalAges))?,
            )
        } else {
            None
        };
        let opening = crate::national_economy::build_national_opening(
            &counties,
            &cohorts,
            &residents,
            &households,
            &world,
            &transport,
            crate::national_economy::NationalOpeningPolicy {
                policy: &policy,
                ages: ages.as_ref(),
                source_hash: babylon_kernel::content_digest::sha256_of(b(
                    Kind::NationalGamePolicy,
                )?),
            },
        )
        .map_err(EconomicCatalogError::NationalOpening)?;
        Ok((
            Self {
                aid: opening.aid,
                companies: opening.companies,
                finances: opening.finances,
                representation: opening.representation,
                detail: opening.detail,
                counties,
                cohorts,
                residents,
                households,
                ages,
                world,
                transport,
            },
            opening.opening,
        ))
    }
    pub(super) fn view(&self) -> EconomicSourceView<'_> {
        EconomicSourceView::National {
            counties: &self.counties,
            cohorts: &self.cohorts,
            residents: &self.residents,
            households: &self.households,
            ages: self.ages.as_ref(),
            world: &self.world,
            transport: &self.transport,
        }
    }
}

fn validate_graph_sources(
    input: &EconomicCatalogInput,
    graph: NationalGraph,
    policy: &NationalGamePolicy,
) -> Result<()> {
    let mut required = vec![
        Kind::GraphDeclarations,
        Kind::Rules,
        Kind::NationalGamePolicy,
        Kind::NationalCounties,
        Kind::NationalCohorts,
        Kind::ResidentWorkforce,
        Kind::NationalHouseholds,
        Kind::NationalTransport,
        Kind::InternationalTrade,
        Kind::WorldPopulation,
        Kind::CohortFunctionMapping,
        Kind::CounterpartMembership,
        Kind::PopulationScopePolicy,
        Kind::TransportPolicy,
        Kind::TransportSourceManifest,
    ];
    if policy.household_lifecycle.is_some() {
        required.push(Kind::NationalAges);
    }
    super::capture::source_coverage(
        input,
        &required,
        &[
            Kind::PreludeDeclarations,
            Kind::MichiganDynamicHexes,
            Kind::MichiganSpatialProducts,
        ],
    )?;
    if graph == NationalGraph::Companies
        && super::capture::source(input, Kind::GraphDeclarations)?
            != super::preset::COMPANY_STRUCTURE
    {
        return Err(EconomicCatalogError::Source(Kind::GraphDeclarations));
    }
    validate_declarations(input)?;
    let expected_rules = if input.city_pd.is_some() {
        super::preset::national_city_pd_rules(graph)
    } else if input.organizer.is_some() {
        super::preset::national_organizer_rules(graph)
    } else {
        super::preset::national_material_rules(graph)
    };
    if super::capture::source(input, Kind::Rules)? != expected_rules {
        return Err(EconomicCatalogError::Source(Kind::Rules));
    }
    Ok(())
}

fn validate_declarations(input: &EconomicCatalogInput) -> Result<()> {
    let bytes = super::capture::source(input, Kind::GraphDeclarations)?;
    let text = std::str::from_utf8(bytes)
        .map_err(|_| EconomicCatalogError::Source(Kind::GraphDeclarations))?;
    let prelude = input
        .sources
        .iter()
        .find(|row| row.kind() == Kind::PreludeDeclarations)
        .map(|row| std::str::from_utf8(row.bytes()))
        .transpose()
        .map_err(|_| EconomicCatalogError::Source(Kind::PreludeDeclarations))?;
    let empty = GraphSeed::try_new(vec![], vec![], vec![]).map_err(EconomicCatalogError::from)?;
    let loaded = babylon_bsl::scenario_seed::load_scenario_with_seed(
        text,
        prelude,
        &empty,
        &mut HypergraphStore::new(),
    )
    .map_err(EconomicCatalogError::from)?;
    if loaded.id != input.scenario_id {
        return Err(EconomicCatalogError::Identity);
    }
    Ok(())
}
