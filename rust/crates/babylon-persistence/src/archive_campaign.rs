//! Current Archive producer selection from one authenticated campaign capture.
use std::collections::BTreeSet;

use postgres::Config;

use crate::county_producer::CountySource;
use crate::economic_catalog::EconomicSourceView;
use crate::identity::CampaignId;
use crate::production_projection::diagnostics::Stage;
use crate::production_projection::diagnostics::Timing;
use crate::OrganizerDossierProducer;
use crate::{
    ArchiveDossierProducer, CampaignFoundation, CompositeArchiveDossierProducer,
    CountyDossierProducer, FoundationContentKind, PlaceDossierProducer,
    RustPersistenceRuntimeError, SemanticArchiveError,
};

/// Construct a fixed-campaign Archive producer from its captured source authority.
/// Admit when the ordered worker first requests production; the result retains
/// immutable presentation inputs
/// and does not regenerate the national opening during subsequent sweeps.
/// # Errors
/// Refuses an incompatible foundation, altered source or invalid county mapping.
pub fn captured_archive_producer(
    config: &Config,
    campaign: CampaignId,
) -> Result<CompositeArchiveDossierProducer, SemanticArchiveError> {
    let _timing = Timing::start(Stage::ArchiveProducerFoundation, 0);
    let foundation =
        crate::hydrate_campaign_foundation(config, campaign).map_err(|error| match error {
            RustPersistenceRuntimeError::CurrentSchema(error) => {
                SemanticArchiveError::CurrentSchema(error)
            }
            RustPersistenceRuntimeError::Database {
                operation,
                diagnostic: Some(diagnostic),
            } => SemanticArchiveError::Database {
                operation,
                diagnostic,
            },
            _ => SemanticArchiveError::StoredPageMismatch,
        })?;
    let readers = crate::current_schema::bounded_config(config);
    from_foundation(&readers, campaign, foundation)
}

fn from_foundation(
    config: &Config,
    campaign: CampaignId,
    foundation: CampaignFoundation,
) -> Result<CompositeArchiveDossierProducer, SemanticArchiveError> {
    let content = foundation.content_bundle();
    let mapping = content
        .territory_county_map()
        .map_err(|_| SemanticArchiveError::StoredPageMismatch)?;
    let counties: BTreeSet<_> = mapping
        .iter()
        .map(|row| row.county_geoid().to_owned())
        .collect();
    let mapping = mapping
        .iter()
        .map(|row| {
            (
                row.county_geoid().to_owned(),
                row.territory_local_name().to_owned(),
            )
        })
        .collect();
    let mut producers: Vec<Box<dyn ArchiveDossierProducer>> = Vec::new();
    let mut organizer = false;
    match content.kind() {
        FoundationContentKind::EconomicCatalog => {
            let catalog = content
                .economic_catalog()
                .ok_or(SemanticArchiveError::StoredPageMismatch)?;
            let view = catalog.view();
            let detail = catalog.spatial_detail();
            let source = match view.sources {
                EconomicSourceView::National { counties, .. } => {
                    CountySource::national(counties, detail)?
                }
                EconomicSourceView::MichiganControl { .. } => CountySource::Michigan(
                    detail.ok_or(SemanticArchiveError::ArtifactDigest)?.clone(),
                ),
            };
            organizer = catalog.has_organizer();
            producers.push(Box::new(CountyDossierProducer::from_captured(
                config, campaign, source, mapping,
            )));
            if let Some(detail) = detail {
                producers.push(Box::new(PlaceDossierProducer::from_captured(
                    config,
                    campaign,
                    detail.clone(),
                    &counties,
                )?));
            }
        }
        FoundationContentKind::AuthoredBscn => {
            // This current source kind explicitly uses the pinned Michigan H3
            // control reference. It never substitutes for a missing catalog.
            let cohort = crate::h3_reference_cohort::representative_h3_reference_cohort()
                .map_err(|_| SemanticArchiveError::ArtifactDigest)?;
            let detail =
                crate::spatial_reference_products::michigan_spatial_reference_products(cohort)
                    .map_err(|_| SemanticArchiveError::ArtifactDigest)?;
            producers.push(Box::new(CountyDossierProducer::from_captured(
                config,
                campaign,
                CountySource::Michigan(detail.clone()),
                mapping,
            )));
            producers.push(Box::new(PlaceDossierProducer::from_captured(
                config, campaign, detail, &counties,
            )?));
        }
    }
    if organizer {
        producers.insert(
            0,
            Box::new(OrganizerDossierProducer::from_captured(
                config, campaign, foundation,
            )),
        );
    }
    Ok(CompositeArchiveDossierProducer::new(producers))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::economic_catalog::CapturedEconomicCatalog;
    use crate::michigan_material::MichiganMaterialCatalog;
    use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};
    use uuid::Uuid;

    #[test]
    fn captured_control_factory_selects_county_and_place_without_absent_organizer() {
        let control = MichiganMaterialCatalog::from_defines_toml(include_str!(
            "../../../../content/scenarios/michigan/defines.toml"
        ))
        .unwrap();
        let foundation = CapturedEconomicCatalog::from_michigan(&control)
            .unwrap()
            .create_foundation(
                ReplaySessionId::try_from("archive-source").unwrap(),
                ReplaySeed::new(41),
            )
            .unwrap();
        let config = Config::new();
        let producer = from_foundation(
            &config,
            CampaignId::from_uuid(Uuid::nil()),
            crate::material_runtime::persisted_graph_copy(foundation.graph_foundation()),
        )
        .unwrap();
        assert_eq!(producer.producers().len(), 2);
    }
}
