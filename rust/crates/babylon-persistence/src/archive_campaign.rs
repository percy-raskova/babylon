//! Current Archive producer selection from one authenticated campaign capture.
use std::collections::BTreeSet;

use postgres::Config;

use crate::{
    county_producer::CountySource, economic_catalog::EconomicSourceView, identity::CampaignId,
    ArchiveDossierProducer, CampaignFoundation, CompositeArchiveDossierProducer,
    CountyDossierProducer, FoundationContentKind, PlaceDossierProducer,
    RustPersistenceRuntimeError, SemanticArchiveError,
};

/// Construct a fixed-campaign Archive producer from its captured source authority.
/// Call once at driver startup; the result retains immutable presentation inputs
/// and does not regenerate the national opening during subsequent sweeps.
/// # Errors
/// Refuses an incompatible foundation, altered source or invalid county mapping.
pub fn captured_archive_producer(
    config: &Config,
    campaign: CampaignId,
) -> Result<CompositeArchiveDossierProducer, SemanticArchiveError> {
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
    from_foundation(&readers, campaign, &foundation)
}

fn from_foundation(
    config: &Config,
    campaign: CampaignId,
    foundation: &CampaignFoundation,
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
            if catalog.has_organizer() {
                producers.push(Box::new(crate::OrganizerDossierProducer::new(config)));
            }
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
    Ok(CompositeArchiveDossierProducer::new(producers))
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_kernel::replay::{ReplaySeed, ReplaySessionId};

    #[test]
    fn captured_control_factory_selects_county_and_place_without_absent_organizer() {
        let control = crate::michigan_material::MichiganMaterialCatalog::from_defines_toml(
            include_str!("../../../../content/scenarios/michigan/defines.toml"),
        )
        .unwrap();
        let foundation = crate::economic_catalog::CapturedEconomicCatalog::from_michigan(&control)
            .unwrap()
            .create_foundation(
                ReplaySessionId::try_from("archive-source").unwrap(),
                ReplaySeed::new(41),
            )
            .unwrap();
        let config = Config::new();
        let producer = from_foundation(
            &config,
            CampaignId::from_uuid(uuid::Uuid::nil()),
            foundation.graph_foundation(),
        )
        .unwrap();
        assert_eq!(producer.producers().len(), 2);
    }
}
