//! Reuse one admitted immutable catalog for graph and material initialization.
use super::{
    capture::CapturedSources, CapturedEconomicCatalog, EconomicCatalogError,
    SourceArtifactKind as K,
};
use babylon_bsl::scenario::{load_scenario, LoadedScenario};
use babylon_graph::hypergraph_store::HypergraphStore;
use babylon_kernel::{
    content_digest::ContentDigest,
    replay::{ReplaySeed, ReplaySessionId},
    tick_content_hash::RefDigest,
};
use babylon_tick::{
    material_state::{MaterialGeography, MaterialState},
    replay_session::ReplayTickSession,
};
type Result<T> = std::result::Result<T, EconomicCatalogError>;

impl CapturedEconomicCatalog {
    pub(crate) fn scenario_source(&self) -> Result<&str> {
        match &self.sources {
            CapturedSources::Michigan(sources) => Ok(sources.catalog.graph_scenario_source()),
            CapturedSources::National(_) => self.source_text(K::GraphDeclarations),
        }
    }
    pub(crate) fn source_text(&self, kind: K) -> Result<&str> {
        std::str::from_utf8(
            self.source(kind)
                .ok_or(EconomicCatalogError::Source(kind))?,
        )
        .map_err(|_| EconomicCatalogError::Source(kind))
    }
    pub(crate) fn prelude(&self) -> Result<Option<&str>> {
        self.source(K::PreludeDeclarations)
            .map(std::str::from_utf8)
            .transpose()
            .map_err(|_| EconomicCatalogError::Source(K::PreludeDeclarations))
    }
    pub(crate) fn load_graph(&self, graph: &mut HypergraphStore) -> Result<LoadedScenario> {
        let result = match &self.sources {
            CapturedSources::Michigan(_) => load_scenario(self.scenario_source()?, graph),
            CapturedSources::National(sources) => {
                let seed = super::graph::national_seed(
                    &self.input.scenario_id,
                    &self.opening,
                    &sources.counties,
                )?;
                babylon_bsl::scenario_seed::load_scenario_with_seed(
                    self.scenario_source()?,
                    self.prelude()?,
                    &seed,
                    graph,
                )
            }
        };
        result.map_err(EconomicCatalogError::from)
    }
    pub(crate) fn new_graph_session(
        &self,
        session: ReplaySessionId,
        seed: ReplaySeed,
        content: ContentDigest,
        reference: RefDigest,
    ) -> Result<ReplayTickSession<HypergraphStore>> {
        let material = self.material_geography()?;
        let graph = HypergraphStore::new();
        let result = match &self.sources {
            CapturedSources::Michigan(_) => ReplayTickSession::new(
                self.scenario_source()?,
                None,
                self.source_text(K::Rules)?,
                graph,
                session,
                seed,
                content,
                reference,
                material,
            ),
            CapturedSources::National(sources) => {
                let instances = super::graph::national_seed(
                    &self.input.scenario_id,
                    &self.opening,
                    &sources.counties,
                )?;
                ReplayTickSession::new_with_graph_seed(
                    self.scenario_source()?,
                    self.prelude()?,
                    self.source_text(K::Rules)?,
                    graph,
                    session,
                    seed,
                    content,
                    reference,
                    material,
                    &instances,
                )
            }
        };
        result.map_err(EconomicCatalogError::from)
    }
    fn material_geography(&self) -> Result<MaterialState> {
        let geography = match &self.sources {
            CapturedSources::Michigan(_) => MaterialGeography::MichiganControl {
                local_detail: self
                    .local_detail
                    .as_ref()
                    .ok_or(EconomicCatalogError::Source(K::MichiganDynamicHexes))?,
                reference_bundle_digest: self.digest,
            },
            CapturedSources::National(sources) => MaterialGeography::NationalCounties {
                roster: sources.counties.roster(),
                reference_bundle_digest: self.digest,
                local_detail: self.local_detail.as_ref(),
            },
        };
        MaterialState::try_from_geography(geography).map_err(EconomicCatalogError::from)
    }
    pub(crate) fn geographic_binding(&self) -> (&'static str, Option<[u8; 32]>) {
        let scope = match &self.sources {
            CapturedSources::Michigan(_) => "michigan-control",
            CapturedSources::National(_) => "national-counties",
        };
        (scope, self.local_detail.as_ref().map(babylon_tick::h3_runtime::MichiganDynamicHexFoundation::base_reference_cohort_digest))
    }
    pub(crate) fn county_map(
        &self,
    ) -> Result<Vec<crate::territory_county_map::TerritoryCountyMapRow>> {
        use crate::territory_county_map::TerritoryCountyMapRow;
        match &self.sources {
            CapturedSources::Michigan(_) => {
                crate::territory_county_map::extract_declared_territory_county_map(
                    self.scenario_source()?,
                    None,
                )
                .map_err(|_| EconomicCatalogError::Graph)
            }
            CapturedSources::National(sources) => sources
                .counties
                .counties()
                .iter()
                .map(|county| {
                    TerritoryCountyMapRow::try_new(
                        format!("county-{}", county.geoid()),
                        county.geoid().to_string(),
                    )
                    .map_err(|_| EconomicCatalogError::Graph)
                })
                .collect(),
        }
    }
}
