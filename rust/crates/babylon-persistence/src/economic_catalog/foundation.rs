//! Bind the common initialization compiler to the existing authoritative replay.

use super::capture::CapturedSources;
use super::{CapturedEconomicCatalog, EconomicCatalogError};
use babylon_graph::stable_element::StableElementResolver;
use babylon_material_circuit::MaterialCatalog;
use babylon_material_circuit::MaterialCircuitState;
use babylon_practice_contract::CityPdCaseSource;
use babylon_practice_contract::CityPdCaseStatus;
use babylon_practice_contract::PublicVenueHistory;
use babylon_tick::material_world::CityPdRegister;

use crate::material_runtime::{
    AdmittedMaterial, MaterialFoundationSpec, MaterialRuntimeError, MaterialRuntimeFoundation,
};
use crate::{CampaignFoundation, FoundationContentBundle};

use crate::RustPersistenceRuntimeError;
use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
use babylon_practice_contract::OrganizerPeriodJournal;
use babylon_tick::material_world::MaterialWorldRegister;

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
        let mut register = MaterialWorldRegister::try_new(&compiled.catalog, 0, compiled.state)?;
        if let Some(config) = &catalog.input.organizer {
            let state = babylon_practice_contract::initial_organizer_state(config)
                .map_err(|_| MaterialRuntimeError::FoundationMismatch)?;
            register = register.with_organizer(
                &compiled.catalog,
                config.clone(),
                state,
                OrganizerPeriodJournal::empty(),
            )?;
        }
        if let Some(venue) = catalog.initial_public_venue().map_err(catalog_error)? {
            register = register.with_public_venue(&compiled.catalog, venue, None)?;
        }
        if let Some(city_pd) = catalog
            .initial_city_pd(&compiled.catalog, register.state(), graph.stable_resolver())
            .map_err(catalog_error)?
        {
            register =
                register.with_city_pd(&compiled.catalog, city_pd, graph.stable_resolver())?;
        }
        let spec = MaterialFoundationSpec {
            preset_id: catalog.input.preset_id.clone(),
            duration: catalog.input.duration,
            content_digest: catalog.digest,
        };
        MaterialRuntimeFoundation::capture_register(graph, bundle, register, spec)
    }

    pub(crate) fn initial_public_venue(
        &self,
    ) -> Result<Option<PublicVenueHistory>, EconomicCatalogError> {
        match (&self.sources, &self.input.organizer) {
            (CapturedSources::National(_), Some(_)) => Ok(Some(
                crate::national_economy::city_pd::public_venue(&self.input)?,
            )),
            (_, None) | (CapturedSources::Michigan(_), Some(_)) => Ok(None),
        }
    }

    pub(crate) fn initial_city_pd(
        &self,
        catalog: &MaterialCatalog,
        material: &MaterialCircuitState,
        resolver: &StableElementResolver,
    ) -> Result<Option<CityPdRegister>, EconomicCatalogError> {
        let Some(config) = &self.input.city_pd else {
            return Ok(None);
        };
        let organizer = self
            .input
            .organizer
            .as_ref()
            .ok_or(EconomicCatalogError::Identity)?;
        let venue = self
            .initial_public_venue()?
            .ok_or(EconomicCatalogError::Identity)?;
        let notice = venue
            .records
            .first()
            .ok_or(EconomicCatalogError::Identity)?;
        let sites = self
            .opening
            .sites
            .iter()
            .filter(|site| {
                site.processes
                    .iter()
                    .any(|process| process.process_id.as_bytes() == organizer.workplace_process_id)
            })
            .collect::<Vec<_>>();
        let [site] = sites.as_slice() else {
            return Err(EconomicCatalogError::Identity);
        };
        let subject_digest = babylon_kernel::content_digest::sha256_of(
            &site
                .subject
                .canonical_bytes()
                .map_err(|_| EconomicCatalogError::Identity)?,
        );
        let subject = u64::from_be_bytes(
            subject_digest[..8]
                .try_into()
                .map_err(|_| EconomicCatalogError::Identity)?,
        );
        if subject != organizer.workplace_id || notice.workplace_id != subject {
            return Err(EconomicCatalogError::Identity);
        }
        let mut case = babylon_practice_contract::CityPdCase {
            case_id: [0; 32],
            actor_id: config.actor_id,
            subject_id: subject,
            county: config.county,
            public_venue_id: notice.venue_id,
            source_id: notice.source_id,
            source_kind: CityPdCaseSource::CapturedPublicRecord,
            source_receipt_id: None,
            case_source_witness_id: None,
            observed_period: notice.period,
            acquired_period: 0,
            status: CityPdCaseStatus::Open,
        };
        case.case_id = babylon_practice_contract::city_pd_case_id(&case)
            .map_err(|_| EconomicCatalogError::Identity)?;
        let bindings = vec![
            (
                config.actor_id,
                crate::national_economy::city_pd::actor_key(),
            ),
            (subject, site.subject.clone()),
        ];
        let register = CityPdRegister::try_initial(
            config.clone(),
            case,
            bindings,
            catalog,
            material,
            resolver,
        )
        .map_err(|_| EconomicCatalogError::Foundation)?;
        Ok(Some(register))
    }
    /// Derive the one immutable definition set and opening its sources authorize.
    /// # Errors
    /// Refuses a spec, graph identity or organizer binding from another capture.
    pub(crate) fn admitted_material(
        &self,
        graph: &CampaignFoundation,
        spec: &MaterialFoundationSpec,
    ) -> Result<AdmittedMaterial, EconomicCatalogError> {
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
        Ok(AdmittedMaterial {
            catalog: compiled.catalog,
            state: compiled.state,
            staffing: compiled.staffing,
            organizer: self.input.organizer.clone().zip(initial_organizer),
        })
    }
}
fn catalog_error(error: EconomicCatalogError) -> MaterialRuntimeError {
    MaterialRuntimeError::Graph(RustPersistenceRuntimeError::EconomicCatalog(error))
}
