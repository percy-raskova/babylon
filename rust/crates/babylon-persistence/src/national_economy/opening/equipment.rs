//! Designed opening instruments with finite use, real sourcing and installation.
use super::{
    amount, markets, quantity, routes, ActorContext, Builder, NationalOpeningError, Result,
};
use crate::economic_catalog::CatalogCapacity;
use babylon_kernel::{content_digest::sha256_of, currency::Currency};
use babylon_material_circuit::{
    EquipmentAssetId, EquipmentBinding, EquipmentCarryingValue, EquipmentCohortId,
    EquipmentDefinition, EquipmentDefinitionId, InstallationInput, InstallationPolicy,
    InstallationTarget, InstalledEquipmentCohort, InvestmentPolicy, ProductiveEquipment,
    RollingProcessSupply, StaffingPoolBinding, StaffingWorkSource, SupplierRoute,
    SupplierTransport,
};
use std::collections::BTreeSet;

pub(super) fn wire(
    builder: &mut Builder<'_>,
    providers: &markets::Providers,
    network: &mut routes::Network<'_>,
    preferences: &mut markets::Preferences,
) -> Result<()> {
    let definition = definition(builder)?;
    let mut equipment = ProductiveEquipment {
        definitions: vec![definition.clone()],
        bindings: vec![],
        installation_inputs: vec![],
        cohorts: vec![],
        pending: vec![],
        installation_policies: vec![],
        investment_policies: vec![],
    };
    for (key, coefficient) in &builder.policy.equipment.installation_inputs {
        let good = builder.commodity(key)?;
        equipment.installation_inputs.push(InstallationInput {
            definition_id: definition.id,
            good_id: good.good_id,
            unit_id: good.unit_id,
            quantity_per_equipment_unit: *coefficient,
        });
    }
    let actors: Vec<_> = builder.actors.values().cloned().collect();
    for actor in actors.into_iter().filter(|a| a.process_id.is_some()) {
        opening_asset(builder, &actor, &definition, &mut equipment)?;
        policies(
            builder,
            &actor,
            &definition,
            &mut equipment,
            providers,
            network,
            preferences,
        )?;
    }
    equipment.bindings.sort_unstable_by_key(|r| r.process_id);
    equipment
        .cohorts
        .sort_unstable_by_key(|r| (r.process_id, r.id));
    equipment
        .installation_inputs
        .sort_unstable_by_key(|r| (r.definition_id, r.good_id, r.unit_id));
    equipment
        .installation_policies
        .sort_unstable_by_key(|r| r.process_id);
    equipment
        .investment_policies
        .sort_unstable_by_key(|r| r.process_id);
    bind_installation_work(builder, &equipment)?;
    builder.opening.equipment.sort_unstable_by_key(|r| r.asset);
    builder.opening.capacity =
        CatalogCapacity::Rolling(RollingProcessSupply::Equipment(Box::new(equipment)));
    Ok(())
}

fn bind_installation_work(
    builder: &mut Builder<'_>,
    equipment: &ProductiveEquipment,
) -> Result<()> {
    let processes: BTreeSet<_> = equipment
        .installation_policies
        .iter()
        .map(|policy| policy.process_id)
        .collect();
    for staffing in &mut builder.opening.staffing {
        let actor = builder
            .actors
            .get(&staffing.pool.site_id())
            .ok_or(NationalOpeningError::Identity)?;
        let Some(process) = actor.process_id.filter(|id| processes.contains(id)) else {
            continue;
        };
        let mut sources = staffing.pool.work_sources().to_vec();
        sources.push(StaffingWorkSource::Installation(process));
        staffing.pool = StaffingPoolBinding::try_new(
            staffing.pool.pool_id(),
            staffing.pool.site_id(),
            staffing.pool.unit_id(),
            staffing.pool.labor_force(),
            staffing.pool.policy(),
            sources,
        )
        .map_err(|_| NationalOpeningError::Policy)?;
    }
    Ok(())
}

fn definition(builder: &Builder<'_>) -> Result<EquipmentDefinition> {
    let good = builder.commodity("equipment")?;
    let policy = &builder.policy.equipment;
    if policy.batches_per_unit_per_period == 0
        || policy.service_batches_per_unit == 0
        || policy.installation_hours_per_unit == 0
    {
        return Err(NationalOpeningError::Policy);
    }
    let mut identity = b"NationalEquipmentDefinitionV1\0".to_vec();
    identity.extend_from_slice(&good.good_id.as_bytes());
    identity.extend_from_slice(&good.unit_id.as_bytes());
    Ok(EquipmentDefinition {
        id: EquipmentDefinitionId::from_bytes(sha256_of(&identity)),
        equipment_good_id: good.good_id,
        equipment_unit_id: good.unit_id,
        batches_per_unit_per_period: policy.batches_per_unit_per_period,
        service_batches_per_unit: policy.service_batches_per_unit,
        installation_labor_unit_id: builder.labor_unit,
        installation_hours_per_unit: policy.installation_hours_per_unit,
    })
}

fn opening_asset(
    builder: &mut Builder<'_>,
    actor: &ActorContext,
    definition: &EquipmentDefinition,
    equipment: &mut ProductiveEquipment,
) -> Result<()> {
    let process = actor.process_id.ok_or(NationalOpeningError::Identity)?;
    equipment.bindings.push(EquipmentBinding {
        process_id: process,
        site_id: actor.site_id,
        definition_id: definition.id,
    });
    let units = machine_units(builder, actor, actor.employed, definition)?;
    if units == 0 {
        return Ok(());
    }
    let fractions = builder.policy.equipment.opening_remaining_service_bps;
    let fraction = fractions[usize::from(actor.site_id.as_bytes()[0]) % fractions.len()];
    if fraction == 0 || fraction > 10_000 {
        return Err(NationalOpeningError::Policy);
    }
    let life = quantity(units, definition.service_batches_per_unit)?;
    let remaining = u64::try_from(u128::from(life) * u128::from(fraction) / 10_000)
        .map_err(|_| NationalOpeningError::Arithmetic)?;
    if remaining == 0 {
        return Err(NationalOpeningError::Policy);
    }
    let mut identity = b"NationalOpeningEquipmentV1\0".to_vec();
    identity.extend_from_slice(&process.as_bytes());
    let id = EquipmentCohortId::from_bytes(sha256_of(&identity));
    equipment.cohorts.push(InstalledEquipmentCohort {
        id,
        process_id: process,
        units,
        remaining_service_batches: remaining,
        usable_from_period: 1,
    });
    let price = builder
        .commodity("equipment")?
        .price
        .as_ref()
        .ok_or(NationalOpeningError::Policy)?
        .scaled(actor.price_scale_bps)
        .map_err(|_| NationalOpeningError::Arithmetic)?
        .opening;
    let original = amount(units, price)?.micro_units();
    let carrying = (original / 10_000)
        .checked_mul(i128::from(fraction))
        .and_then(|n| n.checked_add((original % 10_000) * i128::from(fraction) / 10_000))
        .ok_or(NationalOpeningError::Arithmetic)?;
    builder.opening.equipment.push(EquipmentCarryingValue {
        asset: EquipmentAssetId::Installed(id),
        owner: actor.site_id,
        amount: Currency::from_micro_units(carrying),
    });
    Ok(())
}

fn machine_units(
    builder: &Builder<'_>,
    actor: &ActorContext,
    persons: u64,
    definition: &EquipmentDefinition,
) -> Result<u64> {
    let recipe = builder
        .policy
        .recipes
        .get(&actor.function)
        .ok_or(NationalOpeningError::Policy)?;
    let batches =
        quantity(persons, builder.policy.work_hours_per_person)? / recipe.labor_hours_per_batch;
    Ok(batches.div_ceil(definition.batches_per_unit_per_period))
}

fn policies(
    builder: &mut Builder<'_>,
    actor: &ActorContext,
    definition: &EquipmentDefinition,
    equipment: &mut ProductiveEquipment,
    providers: &markets::Providers,
    network: &mut routes::Network<'_>,
    preferences: &mut markets::Preferences,
) -> Result<()> {
    let process = actor.process_id.ok_or(NationalOpeningError::Identity)?;
    let Some((starts, maximum)) = installation_policy(builder, actor, definition, equipment)?
    else {
        return Ok(());
    };
    for (key, coefficient) in builder.policy.equipment.installation_inputs.clone() {
        markets::procure(
            builder,
            providers,
            network,
            preferences,
            markets::ProcurementNeed {
                buyer: actor.site_id,
                key: &key,
                required: quantity(starts, coefficient)?,
                buffer_periods: builder.policy.opening_input_periods,
            },
        )?;
    }
    let good = builder.commodity("equipment")?.clone();
    let cargo = good.cargo.ok_or(NationalOpeningError::Policy)?;
    let locations = providers
        .get(&(good.good_id, good.unit_id))
        .ok_or(NationalOpeningError::MissingObservation)?;
    let primary = markets::primary_supplier(
        locations,
        network,
        preferences,
        actor.location,
        actor.site_id,
        &good,
    )?;
    let (supplier, cap) = if let Some(supplier) = primary {
        (Some(supplier), starts)
    } else {
        let secondary =
            markets::secondary_supplier(builder, locations, network, actor.site_id, cargo)?;
        let cap = u64::try_from(
            u128::from(starts) * u128::from(builder.policy.markets.foreign_procurement_bps)
                / 10_000,
        )
        .map_err(|_| NationalOpeningError::Arithmetic)?;
        (secondary, cap)
    };
    let Some(supplier) = supplier.filter(|_| cap > 0) else {
        return Ok(());
    };
    let from = builder.actors[&supplier].location;
    builder
        .opening
        .logistics
        .supplier_routes
        .push(SupplierRoute {
            buyer_site_id: actor.site_id,
            supplier_site_id: supplier,
            good_id: good.good_id,
            unit_id: good.unit_id,
            route_id: routes::route_id(from, actor.location, cargo),
            transport_kind: if from == actor.location {
                SupplierTransport::Local
            } else {
                SupplierTransport::Staged
            },
        });
    equipment.investment_policies.push(InvestmentPolicy {
        process_id: process,
        supplier_site_id: supplier,
        replacement_target_units: machine_units(builder, actor, actor.employed, definition)?,
        maximum_installed_units: maximum,
        maximum_purchase_per_period: cap,
        expansion_earnings_fraction_bps: builder.policy.equipment.expansion_earnings_fraction_bps,
        cash_floor: markets::payroll(builder, actor.site_id)?,
    });
    Ok(())
}

fn installation_policy(
    builder: &Builder<'_>,
    actor: &ActorContext,
    definition: &EquipmentDefinition,
    equipment: &mut ProductiveEquipment,
) -> Result<Option<(u64, u64)>> {
    let process = actor.process_id.ok_or(NationalOpeningError::Identity)?;
    let maximum = machine_units(builder, actor, actor.force, definition)?;
    let hours = quantity(actor.force, builder.policy.work_hours_per_person)?;
    let hours = u64::try_from(
        u128::from(hours) * u128::from(builder.policy.equipment.installation_workforce_hours_bps)
            / 10_000,
    )
    .map_err(|_| NationalOpeningError::Arithmetic)?;
    if maximum == 0 || hours == 0 {
        return Ok(None);
    }
    let starts = hours
        .div_ceil(definition.installation_hours_per_unit)
        .min(maximum);
    equipment.installation_policies.push(InstallationPolicy {
        process_id: process,
        target: InstallationTarget::ProductionPlan {
            replacement_units: machine_units(builder, actor, actor.employed, definition)?,
        },
        maximum_started_units_per_period: starts,
        maximum_hours_per_period: hours,
    });
    Ok(Some((starts, maximum)))
}
