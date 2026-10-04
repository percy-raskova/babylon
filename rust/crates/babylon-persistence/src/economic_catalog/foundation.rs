//! Bind the common initialization compiler to the existing authoritative replay.
use super::{capture::CapturedSources, CapturedEconomicCatalog, EconomicCatalogError};
use crate::{
    material_runtime::{MaterialFoundationSpec, MaterialRuntimeError, MaterialRuntimeFoundation},
    CampaignFoundation, FoundationContentBundle,
};
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_tick::{material_staffing::StaffingComposition, material_world::MaterialWorldRegister};

impl CapturedEconomicCatalog {
    /// Initialize through the same graph/material replay and marker-last runtime.
    /// # Errors
    /// Refuses invalid opening state, graph bindings, explicit organizer authority,
    /// unsupported instance counts or nonreproducible foundation sources.
    pub fn create_foundation(
        self,
        session: ReplaySessionId,
        seed: ReplaySeed,
    ) -> Result<MaterialRuntimeFoundation, MaterialRuntimeError> {
        let bundle = FoundationContentBundle::from_economic_catalog(self)?;
        let catalog = bundle
            .economic_catalog()
            .ok_or(MaterialRuntimeError::FoundationMismatch)?;
        let graph = catalog
            .new_graph_session(
                session,
                seed,
                bundle.content_digest().clone(),
                bundle.reference_digest(),
            )
            .map_err(catalog_error)?;
        let compiled = catalog.opening.compile().map_err(catalog_error)?;
        let mut register = MaterialWorldRegister::try_new(0, compiled.state)?;
        if let Some(config) = &catalog.input.organizer {
            let state = babylon_practice_contract::initial_organizer_state(config)
                .map_err(|_| MaterialRuntimeError::FoundationMismatch)?;
            register = register.with_organizer(config.clone(), state)?;
        }
        let spec = MaterialFoundationSpec {
            preset_id: catalog.input.preset_id.clone(),
            duration: catalog.input.duration,
            content_digest: catalog.digest,
        };
        MaterialRuntimeFoundation::capture_register(graph, bundle, register, spec)
    }
    pub(crate) fn validate_foundation(
        &self,
        graph: &CampaignFoundation,
        register: &MaterialWorldRegister,
        spec: &MaterialFoundationSpec,
    ) -> Result<StaffingComposition, EconomicCatalogError> {
        let compiled = self.opening.compile()?;
        let initial_organizer = self
            .input
            .organizer
            .as_ref()
            .map(babylon_practice_contract::initial_organizer_state)
            .transpose()
            .map_err(|_| EconomicCatalogError::Foundation)?;
        if spec.preset_id != self.input.preset_id
            || spec.duration != self.input.duration
            || spec.content_digest != self.digest
            || graph.content_digest().defines_hash != self.digest
            || graph.reference_digest().as_bytes() != &self.digest
            || register.state() != &compiled.state
            || register.organizer_config() != self.input.organizer.as_ref()
            || register.organizer_state() != initial_organizer.as_ref()
        {
            return Err(EconomicCatalogError::Foundation);
        }
        if let CapturedSources::Michigan(sources) = &self.sources {
            if sources
                .catalog
                .experiment()
                .is_some_and(|experiment| graph.rng_seed() != ReplaySeed::new(experiment.seed))
            {
                return Err(EconomicCatalogError::Foundation);
            }
        }
        Ok(compiled.staffing)
    }
}
fn catalog_error(error: EconomicCatalogError) -> MaterialRuntimeError {
    MaterialRuntimeError::Graph(crate::RustPersistenceRuntimeError::EconomicCatalog(error))
}
