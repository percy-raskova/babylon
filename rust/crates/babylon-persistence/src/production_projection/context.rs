//! Captured source context with native geographic scope and explicit missingness.
use super::{metadata::Metadata, ProductionProjectionError};
use crate::{
    economic_catalog::{EconomicProjectionView, EconomicSiteSource, EconomicSourceView},
    economic_content::EconomicContentAdmission,
    michigan_cohorts::michigan_business_subject_for_owner,
    michigan_economy::digest_hex,
    michigan_material::MichiganOwnerSource,
    observer_reader::ObserverVisibility,
    production_observation::{
        DesignedProcessAttribution, ObservedKnownSubtotal, ObservedNationalCohortContext,
        ObservedSectorContext, ProductionBusinessSubject, ProductionSnapshot,
    },
    ArchiveEvidenceClass,
};
use babylon_graph::stable_element::StableElementKey;
use std::collections::{BTreeMap, BTreeSet};
type Result<T> = std::result::Result<T, ProductionProjectionError>;
type ContextRows = (Vec<ObservedSectorContext>, Vec<DesignedProcessAttribution>);

pub(crate) fn attach_observed_context(
    admitted: &EconomicContentAdmission,
    visibility: ObserverVisibility,
    snapshot: &mut ProductionSnapshot,
) -> Result<()> {
    if visibility != ObserverVisibility::FullObserver {
        snapshot.observed_contexts.clear();
        snapshot.national_observed_contexts.clear();
        snapshot.process_attributions.clear();
        return Ok(());
    }
    let view = admitted.view();
    let (contexts, links, national) = match view.sources {
        EconomicSourceView::MichiganControl { .. } => {
            let (c, l) = context_rows(view, snapshot)?;
            (c, l, vec![])
        }
        EconomicSourceView::National { .. } => (vec![], vec![], national_rows(view, snapshot)?),
    };
    snapshot.observed_contexts = contexts;
    snapshot.process_attributions = links;
    snapshot.national_observed_contexts = national;
    Ok(())
}
fn visible_sites<'a>(
    metadata: &Metadata<'_>,
    snapshot: &'a ProductionSnapshot,
) -> Result<BTreeMap<String, &'a crate::production_observation::ProductionSite>> {
    let mut rows = BTreeMap::new();
    for row in &snapshot.sites {
        if rows.insert(row.id.clone(), row).is_some() {
            return Err(ProductionProjectionError::State);
        }
    }
    if rows.len() != metadata.sites.len() {
        return Err(ProductionProjectionError::Content);
    }
    for (&id, site) in &metadata.sites {
        let visible = rows
            .get(&digest_hex(&id.as_bytes()))
            .ok_or(ProductionProjectionError::Content)?;
        if visible.location != site.location
            || visible.function != site.function.source_key()
            || visible
                .processes
                .iter()
                .map(|r| r.id.clone())
                .collect::<BTreeSet<_>>()
                != site
                    .processes
                    .iter()
                    .map(|r| digest_hex(&r.process_id.as_bytes()))
                    .collect()
        {
            return Err(ProductionProjectionError::Content);
        }
    }
    Ok(rows)
}
fn context_rows(
    view: EconomicProjectionView<'_>,
    snapshot: &ProductionSnapshot,
) -> Result<ContextRows> {
    let metadata = Metadata::new(view)?;
    let visible = visible_sites(&metadata, snapshot)?;
    let EconomicSourceView::MichiganControl { catalog, .. } = view.sources else {
        return Ok((vec![], vec![]));
    };
    let mut contexts = BTreeMap::new();
    let mut links = Vec::new();
    let mut authored_processes = BTreeMap::<_, Vec<_>>::new();
    for process in catalog.processes() {
        authored_processes
            .entry(process.site_key.as_str())
            .or_default()
            .push(process);
    }
    for site in catalog.sites() {
        let site_id = digest_hex(&site.id().as_bytes());
        let shown = visible
            .get(&site_id)
            .ok_or(ProductionProjectionError::State)?;
        if !shown.is_in_county(&site.county_geoid)
            || shown.sector_code.as_deref() != Some(&site.sector_code)
            || shown.industry_code.as_deref() != Some(&site.naics)
        {
            return Err(ProductionProjectionError::Content);
        }
        let source = catalog
            .owner_source(&site.county_geoid, &site.sector_code)
            .ok_or(ProductionProjectionError::Content)?;
        let context = checked_context(source, catalog.source_url())?;
        let subject = context.subject.clone();
        if contexts
            .insert(subject.clone(), context.clone())
            .is_some_and(|old| old != context)
        {
            return Err(ProductionProjectionError::Content);
        }
        for process in authored_processes
            .get(site.key.as_str())
            .into_iter()
            .flatten()
        {
            links.push(DesignedProcessAttribution {
                process_id: digest_hex(&process.id().as_bytes()),
                site_id: site_id.clone(),
                industry_code: process.industry_code.clone(),
                cohort_subject: subject.clone(),
                scenario_artifact_sha256: digest_hex(&view.source_digest),
                industry_artifact_sha256: source.industry_artifact_sha256.clone(),
                evidence_class: ArchiveEvidenceClass::Designed,
            });
        }
    }
    links.sort_unstable();
    Ok((contexts.into_values().collect(), links))
}
fn subtotal(row: crate::national_cohorts::KnownSubtotal) -> ObservedKnownSubtotal {
    ObservedKnownSubtotal {
        known_subtotal: row.known_subtotal(),
        published_members: row.published_members(),
        missing_members: row.missing_members(),
    }
}
fn national_rows(
    view: EconomicProjectionView<'_>,
    snapshot: &ProductionSnapshot,
) -> Result<Vec<ObservedNationalCohortContext>> {
    let EconomicSourceView::National { cohorts, .. } = view.sources else {
        return Ok(vec![]);
    };
    let metadata = Metadata::new(view)?;
    let visible = visible_sites(&metadata, snapshot)?;
    let mut rows = Vec::new();
    for site in &view.opening.sites {
        let EconomicSiteSource::Qcew(key) = site.source else {
            continue;
        };
        let source = cohorts
            .group(key)
            .filter(|r| r.is_admitted())
            .ok_or(ProductionProjectionError::Content)?;
        let site_id = digest_hex(&site.site_id.as_bytes());
        let shown = visible
            .get(&site_id)
            .ok_or(ProductionProjectionError::State)?;
        if !shown.is_in_county(key.county.as_str())
            || key.function != Some(site.function)
            || shown.observed_employment != source.jobs().complete_total()
        {
            return Err(ProductionProjectionError::Content);
        }
        let StableElementKey::Node {
            scenario,
            local_name,
        } = &site.subject
        else {
            return Err(ProductionProjectionError::Content);
        };
        rows.push(ObservedNationalCohortContext {
            site_id,
            subject: ProductionBusinessSubject {
                scenario: scenario.clone(),
                local_name: local_name.clone(),
            },
            county_geoid: key.county.to_string(),
            function: site.function.source_key().to_owned(),
            ownership: key.ownership.source_code().to_owned(),
            vintage: 2024,
            establishments: subtotal(source.establishments()),
            annual_average_jobs: subtotal(source.jobs()),
            annual_payroll_usd: subtotal(source.annual_payroll_usd()),
            artifact_sha256: digest_hex(&cohorts.artifact_sha256()),
            function_mapping_sha256: digest_hex(&cohorts.function_mapping_sha256()),
            evidence_class: ArchiveEvidenceClass::Observed,
        });
    }
    rows.sort_unstable();
    Ok(rows)
}

fn checked_context(
    source: &MichiganOwnerSource,
    source_url: &str,
) -> Result<ObservedSectorContext> {
    let StableElementKey::Node {
        scenario,
        local_name,
    } = michigan_business_subject_for_owner(&source.county_geoid, &source.sector_code)
    else {
        return Err(ProductionProjectionError::Content);
    };
    Ok(ObservedSectorContext {
        subject: ProductionBusinessSubject {
            scenario,
            local_name,
        },
        county_geoid: source.county_geoid.clone(),
        sector_code: source.sector_code.clone(),
        sector_title: source.sector_title.clone(),
        vintage: 2024,
        annual_avg_estabs_count: source.annual_avg_estabs_count,
        annual_avg_emplvl: source.annual_avg_emplvl,
        total_annual_wages: source.total_annual_wages,
        annual_avg_wkly_wage: source.annual_avg_wkly_wage,
        source_url: source_url.to_owned(),
        source_file: source.county_source_file.clone(),
        source_sha256: source.county_source_sha256.clone(),
        artifact_sha256: source.sector_artifact_sha256.clone(),
        evidence_class: ArchiveEvidenceClass::Observed,
    })
}

#[cfg(test)]
mod tests;
