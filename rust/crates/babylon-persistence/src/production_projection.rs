//! Exact committed material presentation using one captured economic opening.
pub(crate) mod context;
pub(crate) mod diagnostics;
mod equipment;
#[cfg(test)]
mod equipment_fixture;
mod events;
#[cfg(test)]
mod events_tests;
mod freight;
#[cfg(test)]
mod generic_tests;
pub(crate) mod history;
pub(crate) mod households;
mod labor;
pub(crate) mod lifecycle;
mod maintenance;
pub(crate) mod material_balance;
mod merchants;
pub(crate) mod metadata;
mod outbound;
pub(crate) mod prices;
#[cfg(test)]
mod prices_tests;
#[cfg(test)]
mod recurring_fixture;
mod routes;
mod services;
#[cfg(test)]
mod services_fixture;
pub(crate) mod sites;
pub(crate) mod staffing;
#[cfg(test)]
mod tests;

use crate::{
    economic_catalog::EconomicProjectionView,
    michigan_economy::digest_hex,
    production_observation::{
        ProductionFreight, ProductionPhysicalEdge, ProductionRoadSource, ProductionSnapshot,
    },
};
use babylon_tick::material_world::{MaterialTickReceipts, MaterialWorldRegister};
use metadata::Metadata;
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum ProductionProjectionError {
    Content,
    State,
    History,
    Arithmetic,
}
type Result<T> = std::result::Result<T, ProductionProjectionError>;

/// Quantities and completed witnesses come only from the authenticated register pair.
pub(crate) fn project_economic_current(
    view: EconomicProjectionView<'_>,
    register: &MaterialWorldRegister,
    opening: Option<&MaterialWorldRegister>,
    receipt: Option<&(MaterialTickReceipts, [u8; 32])>,
    order_history: &history::OrderHistory,
) -> Result<ProductionSnapshot> {
    let tick = register.completed_tick();
    let metadata =
        diagnostics::projection(diagnostics::Stage::Metadata, tick, Metadata::new(view))?;
    let state = register.state();
    if !view.duration.contains(register.completed_tick()) {
        return diagnostics::projection(
            diagnostics::Stage::Duration,
            tick,
            Err(ProductionProjectionError::History),
        );
    }
    let prior = opening.map(MaterialWorldRegister::state);
    let done = receipt.map(|(r, _)| r);
    let mut events = Vec::new();
    if let Some((receipt, digest)) = receipt {
        diagnostics::projection(
            diagnostics::Stage::Events,
            tick,
            events::project_events(&metadata, order_history, receipt, *digest, &mut events),
        )?;
    }
    let maintenance_account = diagnostics::projection(
        diagnostics::Stage::Maintenance,
        tick,
        maintenance::project_maintenance(&metadata, state, prior, done),
    )?;
    let labor_accounts = diagnostics::projection(
        diagnostics::Stage::Labor,
        tick,
        labor::project_labor_accounts(state, prior, done),
    )?;
    let household_accounts = diagnostics::projection(
        diagnostics::Stage::Households,
        tick,
        households::project_with_labels(state, prior, done, |g, u| metadata.labels(g, u)),
    )?;
    let household_service_accounts = diagnostics::projection(
        diagnostics::Stage::HouseholdServices,
        tick,
        households::services::project_with_labels(state, prior, done, |g, u| metadata.labels(g, u)),
    )?;
    let goods_price_accounts = diagnostics::projection(
        diagnostics::Stage::Prices,
        tick,
        prices::project_with_labels(state, prior, done, |g, u| metadata.labels(g, u)),
    )?;
    let material_balance = diagnostics::projection(
        diagnostics::Stage::MaterialBalance,
        tick,
        material_balance::project_with_labels(state, prior, done, |g, u| metadata.labels(g, u)),
    )?;
    let (freight_capacity_accounts, freight_order_definitions) = diagnostics::projection(
        diagnostics::Stage::FreightCapacity,
        tick,
        freight::project_with_labels(state, prior, done, |id| metadata.capacity_label(id)),
    )?;
    let (merchant_handling_accounts, final_demand_accounts) = diagnostics::projection(
        diagnostics::Stage::Merchants,
        tick,
        merchants::project_with_labels(state, prior, done, order_history, |g, u| {
            metadata.labels(g, u)
        }),
    )?;
    let sites = diagnostics::projection(
        diagnostics::Stage::Sites,
        tick,
        sites::project(&metadata, state, done),
    )?;
    let (routes, physical_routes) = diagnostics::projection(
        diagnostics::Stage::Routes,
        tick,
        routes::project(&metadata, state, order_history),
    )?;
    let freight = diagnostics::projection(
        diagnostics::Stage::Freight,
        tick,
        project_freight(&metadata, state),
    )?;
    let (physical_edges, road_source) = physical_context(&metadata);
    Ok(ProductionSnapshot {

        scenario_label:view.preset_id.to_owned(), duration:view.duration,
        content_authority_sha256:digest_hex(&view.source_digest),
        physical_edges,road_source,sites,routes,physical_routes,freight,freight_capacity_accounts,freight_order_definitions,events,
        merchant_handling_accounts,final_demand_accounts,household_accounts,household_service_accounts,
        goods_price_accounts,maintenance_account,labor_accounts,material_balance,
        staffing_accounts:vec![],observed_contexts:vec![],national_observed_contexts:vec![],process_attributions:vec![],
        provenance:vec![
            format!("Designed {} economic circuit.",view.duration),
            "Recipes, opening stock, purchase policies, workforce schedules and capacity quantities are Designed.".into(),
            "Source annual-average jobs are separate from current modeled employed and reserve persons; households and workplace members are aggregate cohorts.".into(),
            "Events disclose this selected period. Earlier committed receipts remain available through historical observations.".into(),
            "Household stock, consumption, service needs and service satisfaction are separate accounts. Delivery alone does not prove payment or consumption.".into(),
            format!("Captured source/compiler/policy authority sha256:{}",digest_hex(&view.source_digest)),
        ],
    })
}
fn project_freight(
    metadata: &Metadata<'_>,
    state: &babylon_material_circuit::MaterialCircuitState,
) -> Result<Vec<ProductionFreight>> {
    state
        .freight
        .iter()
        .map(|lot| {
            let good = metadata.good(lot.good_id, lot.unit_id)?;
            let relation = metadata
                .routes
                .get(&(
                    lot.destination_site_id,
                    lot.source_site_id,
                    lot.good_id,
                    lot.unit_id,
                ))
                .ok_or(ProductionProjectionError::Content)?;
            if relation.route_id != lot.route_id {
                return Err(ProductionProjectionError::State);
            }
            let mass = outbound::mass(state, lot.good_id, lot.unit_id)?;
            Ok(ProductionFreight {
                id: digest_hex(&lot.lot_id.as_bytes()),
                route_id: digest_hex(&lot.route_id.as_bytes()),
                source_site_id: digest_hex(&lot.source_site_id.as_bytes()),
                destination_site_id: digest_hex(&lot.destination_site_id.as_bytes()),
                good_id: digest_hex(&lot.good_id.as_bytes()),
                unit_id: digest_hex(&lot.unit_id.as_bytes()),
                good: good.label.clone(),
                unit: good.unit_label.clone(),
                quantity: lot.quantity,
                dispatch_period: lot.dispatch_period,
                arrival_period: lot.stage_arrival_period,
                current_stage_index: lot.current_stage_index,
                grams_per_unit: mass,
                mass_grams: lot
                    .quantity
                    .checked_mul(mass)
                    .ok_or(ProductionProjectionError::Arithmetic)?,
            })
        })
        .collect()
}
fn physical_context(
    metadata: &Metadata<'_>,
) -> (Vec<ProductionPhysicalEdge>, Option<ProductionRoadSource>) {
    let Some(network) = metadata.michigan().and_then(|c| c.physical_network()) else {
        return (vec![], None);
    };
    let edges = network
        .edges
        .iter()
        .map(|e| ProductionPhysicalEdge {
            id: e.id.clone(),
            shape_e7: e.shape_e7.clone(),
            distance_mm: e.distance_mm,
        })
        .collect();
    let s = &network.source;
    (
        edges,
        Some(ProductionRoadSource {
            pbf_sha256: s.pbf_sha256.clone(),
            pbf_bytes: s.pbf_bytes,
            pbf_url: s.pbf_url.clone(),
            replication_timestamp: s.replication_timestamp.clone(),
            footprint_sha256: s.footprint_sha256.clone(),
            buffer_degrees_e7: s.buffer_degrees_e7,
            extraction_version: s.extraction_version.clone(),
            distance_version: s.distance_version.clone(),
            routing_profile_version: s.routing_profile_version.clone(),
            graph_sha256: s.graph_sha256.clone(),
        }),
    )
}

/// Test assembly captures real source content and runs the same lifecycle validator.
#[cfg(test)]
pub(crate) fn project_material_observation(
    catalog: &crate::michigan_material::MichiganMaterialCatalog,
    preset: crate::michigan_material::MichiganDeliveryPreset,
    register: &MaterialWorldRegister,
    opening: Option<&MaterialWorldRegister>,
    rows: &[(MaterialWorldRegister, MaterialTickReceipts, [u8; 32])],
) -> Result<ProductionSnapshot> {
    let catalog = catalog
        .with_preset(preset)
        .map_err(|_| ProductionProjectionError::Content)?;
    let source = crate::economic_catalog::CapturedEconomicCatalog::from_michigan(&catalog)
        .map_err(|_| ProductionProjectionError::Content)?;
    let compiled = source
        .view()
        .opening
        .compile()
        .map_err(|_| ProductionProjectionError::Content)?;
    if u64::try_from(rows.len()).ok() != Some(register.completed_tick()) {
        return Err(ProductionProjectionError::History);
    }
    let mut history = history::OrderHistory::from_opening(&compiled.state)?;
    for (i, (prior, receipt, _)) in rows.iter().enumerate() {
        if usize::try_from(receipt.resolve_tick).ok() != Some(i + 1) {
            return Err(ProductionProjectionError::History);
        }
        let next = rows.get(i + 1).map_or(register, |r| &r.0);
        let period = lifecycle::validate_period(prior.state(), next.state(), receipt)?;
        history.record(prior.state(), &period)?;
    }
    let last = rows.last().map(|(_, r, d)| (r.clone(), *d));
    project_economic_current(source.view(), register, opening, last.as_ref(), &history)
}

mod aid;
#[cfg(test)]
#[path = "production_projection/aid_projection_tests.rs"]
mod aid_projection_tests;
