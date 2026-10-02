//! National admission uses supplied checked source bytes only.
use super::{
    EconomicCatalogError, EconomicCatalogInput, EconomicOpening, EconomicSourceView,
    SourceArtifactKind as Kind,
};
use crate::{
    national_cohorts::NationalCohortReference, national_counties::NationalCountyReference,
    national_economy::NationalGamePolicy, national_households::NationalHouseholdReference,
    national_resident_workforce::NationalResidentWorkforceReference,
    national_transport::NationalTransportReference, world_reference::WorldReference,
};
type Result<T> = std::result::Result<T, EconomicCatalogError>;

pub(super) struct NationalSources {
    pub(super) counties: NationalCountyReference,
    cohorts: NationalCohortReference,
    residents: NationalResidentWorkforceReference,
    households: NationalHouseholdReference,
    world: WorldReference,
    transport: NationalTransportReference,
}
impl NationalSources {
    pub(super) fn admit(input: &EconomicCatalogInput) -> Result<(Self, EconomicOpening)> {
        let required = [
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
        super::capture::source_coverage(
            input,
            &required,
            &[
                Kind::PreludeDeclarations,
                Kind::MichiganDynamicHexes,
                Kind::MichiganSpatialProducts,
            ],
        )?;
        validate_declarations(input)?;
        let b = |kind| super::capture::source(input, kind);
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
        let policy = NationalGamePolicy::from_captured_bytes(b(Kind::NationalGamePolicy)?)
            .map_err(|_| EconomicCatalogError::Source(Kind::NationalGamePolicy))?;
        let opening = crate::national_economy::build_national_opening(
            &counties,
            &cohorts,
            &residents,
            &households,
            &world,
            &transport,
            &policy,
        )
        .map_err(EconomicCatalogError::NationalOpening)?;
        Ok((
            Self {
                counties,
                cohorts,
                residents,
                households,
                world,
                transport,
            },
            opening,
        ))
    }
    pub(super) fn view(&self) -> EconomicSourceView<'_> {
        EconomicSourceView::National {
            counties: &self.counties,
            cohorts: &self.cohorts,
            residents: &self.residents,
            households: &self.households,
            world: &self.world,
            transport: &self.transport,
        }
    }
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
    let empty = babylon_bsl::scenario_seed::GraphSeed::try_new(vec![], vec![], vec![])
        .map_err(EconomicCatalogError::from)?;
    let loaded = babylon_bsl::scenario_seed::load_scenario_with_seed(
        text,
        prelude,
        &empty,
        &mut babylon_graph::hypergraph_store::HypergraphStore::new(),
    )
    .map_err(EconomicCatalogError::from)?;
    if loaded.id != input.scenario_id {
        return Err(EconomicCatalogError::Identity);
    }
    Ok(())
}
