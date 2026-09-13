//! One source-qualified service provider added only to the maintenance family.

use super::{
    regional, MichiganDefinesError, MichiganDeliveryPreset, MichiganIndustryBaselineRow,
    MichiganIntervention, MichiganMaintenance, MichiganMaintenanceOverride,
    MichiganMaterialCatalog, MichiganMaterialError, MichiganMaterialPath, MichiganMaterialRoute,
    MichiganMaterialSite, MichiganNormalizedContent, MichiganSiteRole, MichiganWorkforceSeed,
    SOURCE_URL,
};
use crate::michigan_defines::MaintenanceDefines;
use babylon_kernel::content_digest::sha256_of;
use serde::Deserialize;
use std::collections::BTreeMap;

pub(super) const PROVIDER: &str = "owner-26163-81";
const CONSUMER: &str = "26163-31-33-metal_parts";
const ACTIVITY: &str = "26163-81-maintenance";
const SPARES: &str = "metal_parts";
const STOCK: &str = "metal_stock";
const SOURCE_HASH: &str = "1382b5821ac95ca6f344e50f76b6846f76f841b0bc32ebf69ee8fbadc545481a";
const ARTIFACT_HASH: &str = "1a6bf597ac4f0a01f6467bb398e71aec06527ece5671286eb900c7d1e03ae38f";
const ARTIFACT: &[u8] = include_bytes!(
    "../../../../../src/babylon/data/reference/economy/wayne_maintenance_industry_2024.json"
);

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RepairIndustryObservation {
    schema: String,
    evidence_class: String,
    vintage: u16,
    source_url: String,
    selection: BTreeMap<String, String>,
    row: MichiganIndustryBaselineRow,
}

fn source() -> Result<MichiganIndustryBaselineRow, MichiganMaterialError> {
    use MichiganMaterialError::{ArtifactDecode, ArtifactDigest, SourceValue};
    if crate::michigan_economy::digest_hex(&sha256_of(ARTIFACT)) != ARTIFACT_HASH {
        return Err(ArtifactDigest);
    }
    let source: RepairIndustryObservation =
        serde_json::from_slice(ARTIFACT).map_err(|_| ArtifactDecode)?;
    let expected: BTreeMap<_, _> = [
        ("area_fips", "26163"),
        ("own_code", "5"),
        ("industry_code", "811310"),
        ("agglvl_code", "78"),
        ("size_code", "0"),
        ("year", "2024"),
        ("qtr", "A"),
    ]
    .into_iter()
    .map(|(k, v)| (k.to_owned(), v.to_owned()))
    .collect();
    if source.schema != "MichiganMaintenanceIndustryV1"
        || source.evidence_class != "Observed"
        || source.vintage != 2024
        || source.source_url != SOURCE_URL
        || source.selection != expected
        || source.row.source_sha256 != SOURCE_HASH
        || source.row.annual_avg_estabs_count != 122
        || source.row.annual_avg_emplvl != Some(1480)
        || source.row.total_annual_wages != Some(119_725_241)
        || source.row.annual_avg_wkly_wage != Some(1556)
        || !source.row.disclosure_code.is_empty()
    {
        return Err(SourceValue);
    }
    Ok(source.row)
}

pub(super) fn compile(
    base: &MichiganMaterialCatalog,
) -> Result<MichiganMaterialCatalog, MichiganDefinesError> {
    use MichiganDefinesError::Material;
    if base.preset() != MichiganDeliveryPreset::StatewideBaseline || base.maintenance().is_some() {
        return Err(Material(MichiganMaterialError::Preset));
    }
    let defines = base.capture.defines.clone();
    let d = &defines.maintenance;
    let mut c = base.scenario.clone();
    let consumer = c
        .processes
        .iter_mut()
        .find(|p| p.key == CONSUMER)
        .ok_or(Material(MichiganMaterialError::ContentReference))?;
    let consumer_site = consumer.site_key.clone();
    consumer
        .inputs
        .iter_mut()
        .find(|i| i.good_key == STOCK)
        .ok_or(Material(MichiganMaterialError::ContentReference))?
        .opening_quantity = d.consumer_opening_metal_stock;
    append_provider(&mut c, d, defines.hours_per_period())?;
    c.routes.push(MichiganMaterialRoute {
        key: "26163-metal-parts-maintenance-replenishment".to_owned(),
        supplier_site_key: consumer_site,
        buyer_site_key: PROVIDER.to_owned(),
        good_key: SPARES.to_owned(),
        ordered_quantity: d.replenishment_order_units,
        path: MichiganMaterialPath::Local,
    });
    let interventions = interventions(d);
    MichiganMaterialCatalog::from_normalized(
        defines,
        c,
        MichiganDeliveryPreset::StatewideMaintenanceBaseline,
        interventions,
    )
}

fn append_provider(
    c: &mut MichiganNormalizedContent,
    d: &MaintenanceDefines,
    hours_per_period: u64,
) -> Result<(), MichiganDefinesError> {
    use MichiganDefinesError::Material;
    c.sites.push(MichiganMaterialSite {
        key: PROVIDER.to_owned(),
        label: "Wayne · industrial maintenance".to_owned(),
        county_geoid: "26163".to_owned(),
        naics: "811310".to_owned(),
        sector_code: "81".to_owned(),
        role: MichiganSiteRole::Maintenance,
    });
    c.owners
        .push(regional::owner_source("26163", "81", ARTIFACT_HASH)?);
    c.industry.push(source().map_err(Material)?);
    c.staffing.pools.push(MichiganWorkforceSeed {
        key: PROVIDER.to_owned(),
        site_key: PROVIDER.to_owned(),
        process_keys: Vec::new(),
        merchant_handling: false,
        maintenance: true,
        employed: d.employed_people,
        reserve: d.reserve_people,
        previous_unretained_hours: d
            .employed_people
            .checked_mul(hours_per_period)
            .ok_or(Material(MichiganMaterialError::ContentValue))?,
    });
    c.maintenance = Some(MichiganMaintenance {
        activity_key: ACTIVITY.to_owned(),
        provider_site_key: PROVIDER.to_owned(),
        consumer_process_key: CONSUMER.to_owned(),
        spare_good_key: SPARES.to_owned(),
        spare_units_per_job: d.spare_units_per_job,
        labor_units_per_job: d.labor_units_per_job,
        enabled_batches_per_job: d.enabled_batches_per_job,
        maximum_jobs_per_period: d.maximum_jobs_per_period,
        opening_service_batches: d.opening_service_batches,
        opening_spare_parts: d.provider_opening_spare_parts,
    });
    Ok(())
}

fn interventions(d: &MaintenanceDefines) -> Vec<MichiganIntervention> {
    [
        (
            MichiganDeliveryPreset::StatewideMaintenanceLaborShortage,
            d.provider_opening_spare_parts,
            d.shortage_employed_people,
            d.shortage_reserve_people,
        ),
        (
            MichiganDeliveryPreset::StatewideMaintenancePartsShortage,
            d.shortage_opening_spare_parts,
            d.employed_people,
            d.reserve_people,
        ),
        (
            MichiganDeliveryPreset::StatewideMaintenanceBoth,
            d.shortage_opening_spare_parts,
            d.shortage_employed_people,
            d.shortage_reserve_people,
        ),
    ]
    .into_iter()
    .map(
        |(preset, opening_spare_parts, employed_people, reserve_people)| MichiganIntervention {
            preset,
            capacities: Vec::new(),
            opening_stocks: Vec::new(),
            routes: Vec::new(),
            maintenance: Some(MichiganMaintenanceOverride {
                opening_spare_parts,
                employed_people,
                reserve_people,
            }),
            graph_scenario_source: None,
        },
    )
    .collect()
}

pub(super) fn validate(c: &MichiganNormalizedContent) -> Result<(), MichiganMaterialError> {
    use MichiganMaterialError::{ContentReference, ContentValue, SourceValue};
    let providers: Vec<_> = c
        .sites
        .iter()
        .filter(|s| s.role == MichiganSiteRole::Maintenance)
        .collect();
    let Some(m) = &c.maintenance else {
        return if providers.is_empty() {
            Ok(())
        } else {
            Err(ContentReference)
        };
    };
    if providers.len() != 1
        || m.provider_site_key != PROVIDER
        || m.activity_key != ACTIVITY
        || m.consumer_process_key != CONSUMER
        || m.spare_good_key != SPARES
    {
        return Err(ContentReference);
    }
    let provider = providers[0];
    if provider.key != PROVIDER
        || provider.county_geoid != "26163"
        || provider.sector_code != "81"
        || provider.naics != "811310"
        || c.industry
            .iter()
            .find(|r| r.area_fips == "26163" && r.industry_code == "811310")
            != Some(&source()?)
    {
        return Err(SourceValue);
    }
    let consumer = c
        .processes
        .iter()
        .find(|p| p.key == CONSUMER)
        .ok_or(ContentReference)?;
    if consumer.site_key != "owner-26163-31-33"
        || consumer.output_good_key != SPARES
        || consumer.inputs.is_empty()
        || consumer.inputs.iter().any(|i| i.good_key == SPARES)
        || c.processes
            .iter()
            .filter(|p| p.site_key == consumer.site_key)
            .count()
            != 1
        || c.processes.iter().any(|p| p.site_key == PROVIDER)
        || c.merchants
            .iter()
            .any(|s| s.site_key == PROVIDER || s.site_key == consumer.site_key)
        || c.routes.iter().any(|r| {
            r.supplier_site_key == PROVIDER
                || (r.supplier_site_key == consumer.site_key
                    && consumer.inputs.iter().any(|i| i.good_key == r.good_key))
        })
    {
        return Err(ContentReference);
    }
    let incoming: Vec<_> = c
        .routes
        .iter()
        .filter(|r| r.buyer_site_key == PROVIDER)
        .collect();
    if incoming.len() != 1
        || incoming[0].supplier_site_key != consumer.site_key
        || incoming[0].good_key != SPARES
        || incoming[0].path != MichiganMaterialPath::Local
    {
        return Err(ContentReference);
    }
    let max = m
        .maximum_jobs_per_period
        .checked_mul(m.enabled_batches_per_job)
        .ok_or(ContentValue)?;
    if m.spare_units_per_job == 0
        || m.labor_units_per_job == 0
        || m.enabled_batches_per_job == 0
        || m.maximum_jobs_per_period == 0
        || m.opening_service_batches > max
        || m.maximum_jobs_per_period
            .checked_mul(m.labor_units_per_job)
            .is_none_or(|n| n > (1 << 53))
        || m.opening_spare_parts
            .checked_add(incoming[0].ordered_quantity)
            .and_then(|n| n.checked_mul(1000))
            .is_none()
    {
        return Err(ContentValue);
    }
    Ok(())
}
