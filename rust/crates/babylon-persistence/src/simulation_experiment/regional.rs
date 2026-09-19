//! Diagnostic authoring over the existing regional recipes, resources and staffing.
use super::{
    product, ExperimentError, ExperimentIntervention, ExperimentProfile, Result,
    SimulationExperimentV1, StartingSnapshot,
};
use crate::michigan_material::{
    MichiganMaterialCatalog, MichiganMaterialPath, MichiganNormalizedContent,
};
use std::collections::BTreeMap;
use std::fmt::Write;

pub(super) fn catalog(spec: &SimulationExperimentV1) -> Result<MichiganMaterialCatalog> {
    MichiganMaterialCatalog::from_defines_toml(include_str!(
        "../../../../../content/scenarios/michigan/defines.toml"
    ))
    .map_err(|_| ExperimentError::Content)?
    .with_experiment(spec)
    .map_err(|_| ExperimentError::Content)
}

pub(crate) fn configure(
    c: &mut MichiganNormalizedContent,
    spec: &SimulationExperimentV1,
    defines: &crate::michigan_defines::MichiganDefines,
) -> Result<()> {
    spec.validate()?;
    if spec.profile == ExperimentProfile::HistoricalFreight {
        return Err(ExperimentError::Profile);
    }
    c.horizon_ticks = spec.horizon;
    // Historical observations seed employment slots only. Designed hours and
    // recipe labor requirements remain unchanged and are captured separately.
    if let Some(StartingSnapshot::Employment { series, .. }) = &spec.starting_snapshot {
        let jobs: BTreeMap<_, _> = series
            .iter()
            .map(|r| (r.series_id.as_str(), r.jobs))
            .collect();
        for pool in &mut c.staffing.pools {
            let site = c
                .sites
                .iter()
                .find(|s| s.key == pool.site_key)
                .ok_or(ExperimentError::Content)?;
            let count = *jobs
                .get(format!("{}/{}", site.county_geoid, site.naics).as_str())
                .ok_or(ExperimentError::StartingSnapshot)?;
            pool.employed = count;
            pool.reserve = 0;
            pool.previous_unretained_hours = product(count, c.staffing.hours_per_worker_period)?;
            for p in c
                .processes
                .iter_mut()
                .filter(|p| p.site_key == pool.site_key)
            {
                let weekly = product(count, c.staffing.hours_per_worker_period / 4)?
                    / p.labor_hours_per_batch;
                p.capacity_batches_per_period = product(weekly, 4)?;
            }
        }
    }
    if !matches!(
        spec.profile,
        ExperimentProfile::Depletion | ExperimentProfile::DeliveryStock
    ) {
        initialize_stocks_and_routes(c, spec.horizon)?;
    }
    for corridor in &mut c.corridors {
        corridor.capacity_grams_per_period = product(
            corridor.capacity_grams_per_period,
            spec.transport_permille(),
        )? / 1000;
    }
    for intervention in &spec.interventions {
        if let ExperimentIntervention::RegionalDelivery { delivery } = intervention {
            let route = c
                .routes
                .iter_mut()
                .find(|r| r.key == "sheet-transfer")
                .ok_or(ExperimentError::Content)?;
            let value = defines
                .route
                .get("sheet_transfer")
                .ok_or(ExperimentError::Content)?;
            let MichiganMaterialPath::Routed { travel_periods, .. } = &mut route.path else {
                return Err(ExperimentError::Content);
            };
            *travel_periods = if *delivery == super::ExperimentDelivery::Delayed {
                value.delayed_travel_periods
            } else {
                value.travel_periods
            };
        }
        if let ExperimentIntervention::OpeningSheetStock { kilograms } = intervention {
            let input = c
                .processes
                .iter_mut()
                .find(|p| p.key == "panel-forming")
                .and_then(|p| p.inputs.iter_mut().find(|i| i.good_key == "sheet"))
                .ok_or(ExperimentError::Content)?;
            input.opening_quantity = *kilograms;
            // A smaller opening stock must not claim an impossible commitment.
            let p = c
                .processes
                .iter_mut()
                .find(|p| p.key == "panel-forming")
                .ok_or(ExperimentError::Content)?;
            if spec.profile != ExperimentProfile::DeliveryStock {
                p.opening_planned_batches = p
                    .capacity_batches_per_period
                    .min(*kilograms / p.inputs[0].quantity_per_batch);
            }
        }
    }
    Ok(())
}

fn initialize_stocks_and_routes(c: &mut MichiganNormalizedContent, horizon: u64) -> Result<()> {
    // Every upstream process has finite horizon-covering inputs. Downstream
    // processes start with one period of input and an explicit commitment.
    for p in &mut c.processes {
        p.opening_planned_batches = p.capacity_batches_per_period;
        for i in &mut p.inputs {
            let incoming = c
                .routes
                .iter()
                .any(|r| r.buyer_site_key == p.site_key && r.good_key == i.good_key);
            let periods = if incoming { 1 } else { horizon };
            i.opening_quantity = product(
                product(p.capacity_batches_per_period, i.quantity_per_batch)?,
                periods,
            )?;
        }
    }
    for route in &mut c.routes {
        let supplier = c
            .processes
            .iter()
            .find(|p| p.site_key == route.supplier_site_key && p.output_good_key == route.good_key)
            .ok_or(ExperimentError::Content)?;
        route.ordered_quantity = product(
            product(
                supplier.capacity_batches_per_period,
                supplier.output_quantity_per_batch,
            )?,
            horizon,
        )?;
        if let MichiganMaterialPath::Routed { capacity_keys, .. } = &route.path {
            let good = c
                .goods
                .iter()
                .find(|g| g.key == route.good_key)
                .ok_or(ExperimentError::Content)?;
            let mass = product(
                product(
                    supplier.capacity_batches_per_period,
                    supplier.output_quantity_per_batch,
                )?,
                good.grams_per_unit,
            )?;
            for key in capacity_keys {
                let corridor = c
                    .corridors
                    .iter_mut()
                    .find(|r| r.key == *key)
                    .ok_or(ExperimentError::Content)?;
                corridor.capacity_grams_per_period = mass;
            }
        }
    }
    Ok(())
}

/// Re-derive admitted opening rows from captured numeric definitions and the
/// typed experiment. Durable reconstruction must not silently accept a changed
/// job count, rounding result, stock ceiling, or undeclared intervention.
pub(crate) fn validate_captured(
    captured: &MichiganNormalizedContent,
    defines: &crate::michigan_defines::MichiganDefines,
    spec: &SimulationExperimentV1,
) -> Result<()> {
    let mut expected = captured.clone();
    if expected.processes.len() != defines.process.len()
        || expected.staffing.pools.len() != defines.process.len()
        || expected.routes.len() != defines.route.len()
        || expected.corridors.len() != defines.corridor.len() + 1
        || expected.staffing.hours_per_worker_period != defines.hours_per_period()
    {
        return Err(ExperimentError::Content);
    }
    for process in &mut expected.processes {
        let value = defines
            .process
            .get(&process.key.replace('-', "_"))
            .ok_or(ExperimentError::Content)?;
        if process.inputs.len() != 1
            || process.inputs[0].quantity_per_batch != value.input_units_per_batch
            || process.output_quantity_per_batch != value.output_units_per_batch
            || process.labor_hours_per_batch != value.labor_hours_per_batch
        {
            return Err(ExperimentError::Content);
        }
        process.capacity_batches_per_period = product(value.batches_per_week, 4)?;
        process.opening_planned_batches = value.opening_planned_batches;
        process.inputs[0].opening_quantity = value.opening_input_units;
        let pool = expected
            .staffing
            .pools
            .iter_mut()
            .find(|pool| pool.key == process.key)
            .ok_or(ExperimentError::Content)?;
        if pool.site_key != process.site_key
            || pool.process_keys != [process.key.clone()]
            || pool.merchant_handling
            || pool.maintenance
        {
            return Err(ExperimentError::Content);
        }
        pool.employed = value.employed_people;
        pool.reserve = value.reserve_people;
        pool.previous_unretained_hours =
            product(value.employed_people, defines.hours_per_period())?;
    }
    restore_designed_transport(&mut expected, defines)?;
    configure(&mut expected, spec, defines)?;
    if &expected != captured {
        return Err(ExperimentError::Content);
    }
    Ok(())
}

fn restore_designed_transport(
    expected: &mut MichiganNormalizedContent,
    defines: &crate::michigan_defines::MichiganDefines,
) -> Result<()> {
    for route in &mut expected.routes {
        let value = defines
            .route
            .get(&route.key.replace('-', "_"))
            .ok_or(ExperimentError::Content)?;
        route.ordered_quantity = value.ordered_units;
        let MichiganMaterialPath::Routed {
            travel_periods,
            capacity_keys,
            physical_edge_keys,
            distance_mm,
        } = &mut route.path
        else {
            return Err(ExperimentError::Content);
        };
        if capacity_keys != std::slice::from_ref(&route.key)
            || !physical_edge_keys.is_empty()
            || distance_mm.is_some()
        {
            return Err(ExperimentError::Content);
        }
        *travel_periods = value.travel_periods;
    }
    for corridor in &mut expected.corridors {
        let (rate, mass) = if corridor.key == "shared-freight" {
            (
                defines.shared_freight.ample_units_per_week,
                defines.regional_mass.kilogram_grams_per_unit,
            )
        } else {
            let route = expected
                .routes
                .iter()
                .find(|r| r.key == corridor.key)
                .ok_or(ExperimentError::Content)?;
            let good = expected
                .goods
                .iter()
                .find(|g| g.key == route.good_key)
                .ok_or(ExperimentError::Content)?;
            (
                defines
                    .corridor
                    .get(&corridor.key.replace('-', "_"))
                    .ok_or(ExperimentError::Content)?
                    .units_per_week,
                good.grams_per_unit,
            )
        };
        corridor.capacity_grams_per_period = product(product(rate, 4)?, mass)?;
    }
    Ok(())
}

/// Historical diagnostic graphs contain only staffed mechanical fields, not the
/// fixed 2024 QCEW observations used by the ordinary player display.
pub(crate) fn scenario(c: &MichiganNormalizedContent) -> String {
    let mut text = format!(
        "(scenario {}\n  (defvocabulary NodeType (SOCIAL_CLASS))\n",
        crate::michigan_cohorts::MICHIGAN_COHORT_SCENARIO
    );
    for field in babylon_tick::material_staffing::STAFFING_FIELDS {
        writeln!(&mut text, "  (deffield {field} int extensive)").expect("String write");
    }
    for pool in &c.staffing.pools {
        writeln!(&mut text,"  (node {} NodeType/SOCIAL_CLASS (social-class/employed-population {}) (social-class/reserve-population {}) (social-class/previous-unretained-labor-hours {}))",pool.local_name(),pool.employed,pool.reserve,pool.previous_unretained_hours).expect("String write");
    }
    text.push_str(")\n");
    text
}
