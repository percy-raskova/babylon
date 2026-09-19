//! Human-readable initialization evidence projected from captured authority.
use super::{ExperimentError, ExperimentProfile, Result, SimulationExperimentV1};
use crate::michigan_material::{MichiganMaterialCatalog, MichiganMaterialPath};
use serde::Serialize;

#[derive(Debug, Serialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum ResolvedInputs {
    Regional {
        capacity_derivation: &'static str,
        hours_per_person_period: u64,
        opening_policy: &'static str,
        processes: Vec<ProcessSetup>,
        routes: Vec<RouteSetup>,
    },
    Freight(Box<FreightSetup>),
}
#[derive(Debug, Serialize)]
pub struct InputSetup {
    pub good_key: String,
    pub unit: String,
    pub quantity_per_batch: u64,
    pub opening_quantity: u64,
}
#[derive(Debug, Serialize)]
pub struct ProcessSetup {
    pub process_key: String,
    pub series_id: String,
    pub initial_jobs: u64,
    pub initial_reserve: u64,
    pub jobs_evidence: &'static str,
    pub hours_per_person_week: u64,
    pub labor_hours_per_batch: u64,
    pub weekly_capacity_batches: u64,
    pub period_capacity_batches: u64,
    pub opening_planned_batches: u64,
    pub inputs: Vec<InputSetup>,
}
#[derive(Debug, Serialize)]
pub struct CapacitySetup {
    pub key: String,
    pub grams_per_period: u64,
}
#[derive(Debug, Serialize)]
pub struct RouteSetup {
    pub route_key: String,
    pub supplier_site: String,
    pub buyer_site: String,
    pub good_key: String,
    pub unit: String,
    pub ordered_quantity: u64,
    pub travel_periods: u16,
    pub capacities: Vec<CapacitySetup>,
}
#[derive(Debug, Serialize)]
pub struct FreightSetup {
    pub source_site: String,
    pub destination_site: String,
    pub commodity: String,
    pub unit: String,
    pub port_code: String,
    pub partner_code: String,
    pub mode_code: String,
    pub trade_type_code: String,
    pub hs_chapter: String,
    pub geographic_scope: String,
    pub january_observed_kg: u64,
    pub capacity_derivation: &'static str,
    pub capacity_kg_per_period: u64,
    pub ordered_kg: u64,
    pub opening_inventory_kg: u64,
    pub travel_periods: u16,
    pub inventory_evidence: String,
    pub order_evidence: String,
    pub capacity_evidence: String,
    pub inventory_derivation: &'static str,
    pub order_derivation: &'static str,
}
fn regional(
    spec: &SimulationExperimentV1,
    catalog: &MichiganMaterialCatalog,
) -> Result<ResolvedInputs> {
    let mut processes = Vec::new();
    for p in catalog.processes() {
        let pool = catalog
            .staffing()
            .pools
            .iter()
            .find(|s| s.process_keys.contains(&p.key))
            .ok_or(ExperimentError::Content)?;
        let site = catalog.site(&p.site_key).ok_or(ExperimentError::Content)?;
        let inputs = p
            .inputs
            .iter()
            .map(|i| {
                let good = catalog.good(&i.good_key).ok_or(ExperimentError::Content)?;
                Ok(InputSetup {
                    good_key: i.good_key.clone(),
                    unit: good.unit_key.clone(),
                    quantity_per_batch: i.quantity_per_batch,
                    opening_quantity: i.opening_quantity,
                })
            })
            .collect::<Result<Vec<_>>>()?;
        processes.push(ProcessSetup {
            process_key: p.key.clone(),
            series_id: format!("{}/{}", site.county_geoid, p.industry_code),
            initial_jobs: pool.employed,
            initial_reserve: pool.reserve,
            jobs_evidence: if spec.profile == ExperimentProfile::HistoricalEmployment {
                "Observed QWI jobs represented as employed slots"
            } else {
                "Designed employed slots"
            },
            hours_per_person_week: catalog.staffing().hours_per_worker_period / 4,
            labor_hours_per_batch: p.labor_hours_per_batch,
            weekly_capacity_batches: p.capacity_batches_per_period / 4,
            period_capacity_batches: p.capacity_batches_per_period,
            opening_planned_batches: p.opening_planned_batches,
            inputs,
        });
    }
    let mut routes = Vec::new();
    for r in catalog.routes() {
        let (travel_periods, keys) = match &r.path {
            MichiganMaterialPath::Local => (0, Vec::new()),
            MichiganMaterialPath::Routed {
                travel_periods,
                capacity_keys,
                ..
            } => (
                *travel_periods,
                capacity_keys.iter().map(String::as_str).collect(),
            ),
        };
        let capacities = keys
            .into_iter()
            .map(|key| {
                let c = catalog
                    .corridors()
                    .iter()
                    .find(|c| c.key == key)
                    .ok_or(ExperimentError::Content)?;
                Ok(CapacitySetup {
                    key: c.key.clone(),
                    grams_per_period: c.capacity_grams_per_period,
                })
            })
            .collect::<Result<Vec<_>>>()?;
        routes.push(RouteSetup {
            route_key: r.key.clone(),
            supplier_site: r.supplier_site_key.clone(),
            buyer_site: r.buyer_site_key.clone(),
            good_key: r.good_key.clone(),
            unit: catalog
                .good(&r.good_key)
                .ok_or(ExperimentError::Content)?
                .unit_key
                .clone(),
            ordered_quantity: r.ordered_quantity,
            travel_periods,
            capacities,
        });
    }
    Ok(ResolvedInputs::Regional {
        capacity_derivation: if spec.profile == ExperimentProfile::HistoricalEmployment {
            "weekly batches = floor(initial observed jobs * Designed hours per person per week / Designed labor hours per batch); period batches = weekly batches * 4"
        } else {
            "Designed weekly capacity from defines.toml, multiplied by four weeks per period"
        },
        hours_per_person_period: catalog.staffing().hours_per_worker_period,
        opening_policy: if matches!(
            spec.profile,
            ExperimentProfile::Sustained | ExperimentProfile::HistoricalEmployment
        ) {
            "Designed upstream input = period capacity * recipe input * horizon; downstream input = one period capacity * recipe input; initial commitments = period capacity; finite route order = supplier period output * horizon. Typed stock intervention may replace its named opening input and bound that commitment."
        } else {
            "Current finite endowment and opening commitments, with only the declared delivery and stock interventions."
        },
        processes,
        routes,
    })
}
pub(super) fn capture(
    spec: &SimulationExperimentV1,
    graph: &crate::CampaignFoundation,
) -> Result<ResolvedInputs> {
    if spec.profile == ExperimentProfile::HistoricalFreight {
        return Ok(ResolvedInputs::Freight(Box::new(
            super::freight::resolved_setup(graph.content_bundle().defines_bytes())?,
        )));
    }
    let stored = crate::sector_bundle::foundation::decode_stored_bundle_defines(
        graph.content_bundle().defines_bytes(),
        graph.content_digest().defines_hash,
    )
    .map_err(|_| ExperimentError::Content)?;
    regional(spec, stored.catalog())
}
