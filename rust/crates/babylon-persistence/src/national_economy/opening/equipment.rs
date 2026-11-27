//! Designed opening instruments with finite use, real sourcing and installation.
use super::{dealing, markets, routes, ActorContext, Builder, NationalOpeningError, Result};
use crate::economic_catalog::CatalogCapacity;
use crate::national_economy::{GameMachines, GameProcurement};
use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::{EconomicFunction, TradeSet};
use babylon_kernel::economic_location::EconomicLocation;

use babylon_kernel::content_digest;
use babylon_material_circuit::{
    AccountId, EquipmentAssetId, EquipmentBinding, EquipmentCarryingValue, EquipmentCohortId,
    EquipmentDefinition, EquipmentDefinitionId, EquipmentPosition, InstallationInput,
    InstallationPolicy, InstallationTarget, InstalledEquipmentCohort, InvestmentPolicy, ProcessId,
    ProductiveEquipment, RollingProcessSupply, SiteId, StaffingPoolBinding, StaffingWorkSource,
    SupplierRoute, SupplierTransport,
};
use markets::Preferences;
use markets::Providers;
use routes::Network;
use std::collections::{BTreeMap, BTreeSet};

/// The most rows a table of the material circuit holds (`MAX_MATERIAL_CIRCUIT_ROWS`).
const ROW_BOUND: u64 = 65_536;
/// The most ages one process opens with under schema 8.
const MOST_AGES: u64 = 8;

pub(super) fn wire(
    builder: &mut Builder<'_>,
    providers: &Providers,
    network: &mut Network<'_>,
    preferences: &mut Preferences,
) -> Result<()> {
    let definitions = definitions(builder)?;
    let mut distinct: Vec<EquipmentDefinition> = definitions.values().cloned().collect();
    distinct.sort_unstable_by_key(|d| d.id);
    distinct.dedup_by_key(|d| d.id);
    let mut equipment = ProductiveEquipment {
        definitions: distinct.clone(),
        bindings: vec![],
        installation_inputs: vec![],
        installation_policies: vec![],
        investment_policies: vec![],
    };
    let mut position = EquipmentPosition::default();
    for definition in &distinct {
        for (key, coefficient) in &builder.policy.equipment.installation_inputs {
            let good = builder.commodity(key)?;
            equipment.installation_inputs.push(InstallationInput {
                definition_id: definition.id,
                good_id: good.good_id,
                unit_id: good.unit_id,
                quantity_per_equipment_unit: *coefficient,
            });
        }
    }
    let abroad = equipment_abroad(builder)?;
    let machines = deal_machines(builder, providers, network, &abroad, &definitions)?;
    let mut sourcing = Sourcing {
        providers,
        network,
        preferences,
        abroad: &abroad,
        machines: machines.as_ref(),
    };
    let actors: Vec<_> = builder.actors.values().cloned().collect();
    let ages = machine_ages(processes_with_machines(builder, &actors)?)?;
    for actor in actors.into_iter().filter(|a| a.process_id.is_some()) {
        let definition = definitions
            .get(&actor.function)
            .ok_or(NationalOpeningError::Policy)?;
        opening_asset(
            builder,
            &actor,
            definition,
            ages,
            &mut equipment,
            &mut position,
        )?;
        policies(builder, &actor, definition, &mut equipment, &mut sourcing)?;
    }
    equipment.bindings.sort_unstable_by_key(|r| r.process_id);
    position
        .cohorts
        .sort_unstable_by_key(|r| (r.process_id, r.id));
    position.pending.sort_unstable_by_key(|r| r.id);
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
    builder.opening.equipment_position = position;
    builder.opening.capacity =
        CatalogCapacity::Rolling(RollingProcessSupply::Equipment(Box::new(equipment)));
    Ok(())
}

/// What a process's sourcing reads: the sellers, the routes, the cached preferences and the processes that
/// buy their machines abroad.
struct Sourcing<'a, 'n> {
    providers: &'a Providers,
    network: &'a mut Network<'n>,
    preferences: &'a mut Preferences,
    abroad: &'a BTreeSet<ProcessId>,
    /// Under schema 8, the maker each home process that buys its machines at home was dealt.
    machines: Option<&'a BTreeMap<SiteId, SiteId>>,
}

/// Under schema 8, deals the home processes that buy their machines at home one maker each (the engine's rule),
/// by nearness and room: a process's weight is its replacement machines. `None` under schema 7 and earlier.
fn deal_machines(
    builder: &Builder<'_>,
    providers: &Providers,
    network: &mut Network<'_>,
    abroad: &BTreeSet<ProcessId>,
    definitions: &BTreeMap<EconomicFunction, EquipmentDefinition>,
) -> Result<Option<BTreeMap<SiteId, SiteId>>> {
    if builder.policy.trades != TradeSet::Twelve
        || !matches!(
            builder.policy.markets.procurement,
            GameProcurement::ByProduct { .. }
        )
    {
        return Ok(None);
    }
    let good = builder.commodity("equipment")?;
    let cargo = good.cargo.ok_or(NationalOpeningError::Policy)?;
    let Some(locations) = providers.get(&(good.good_id, good.unit_id)) else {
        return Ok(Some(BTreeMap::new()));
    };
    let mut weights = Vec::new();
    for actor in builder.actors.values() {
        let Some(process) = actor.process_id else {
            continue;
        };
        if !matches!(actor.location, EconomicLocation::County(_)) || abroad.contains(&process) {
            continue;
        }
        let definition = definitions
            .get(&actor.function)
            .ok_or(NationalOpeningError::Policy)?;
        weights.push((
            actor.site_id,
            replacement_units(builder, actor, definition)?,
        ));
    }
    let custom = dealing::customs(builder, weights.into_iter())?;
    let makers = dealing::domestic_makers(builder, locations)?;
    let dealt = dealing::deal_makers(builder, network, cargo, &custom, &makers, 1)?;
    Ok(Some(
        dealt
            .into_iter()
            .filter_map(|(buyer, shares)| match (buyer, shares.first()) {
                (AccountId::Site(site), Some(share)) => Some((site, share.maker)),
                _ => None,
            })
            .collect(),
    ))
}

/// Which domestic processes buy their machines abroad (schema 8): processes in order of
/// sha256(b"NationalEquipmentAbroadV1\0" ++ process id), taken while the replacement machines of those taken stay
/// at or under `floor(total replacement machines x import_bps["equipment"] / 10_000)`, the total being that of every
/// domestic process; a process whose own machines would pass it is skipped, and the next tried. Empty under
/// schema 7 and earlier.
pub(super) fn equipment_abroad(builder: &Builder<'_>) -> Result<BTreeSet<ProcessId>> {
    let GameProcurement::ByProduct { import_bps } = &builder.policy.markets.procurement else {
        return Ok(BTreeSet::new());
    };
    let share = *import_bps
        .get("equipment")
        .ok_or(NationalOpeningError::Policy)?;
    let definitions = definitions(builder)?;
    let mut rows: Vec<([u8; 32], ProcessId, u64)> = Vec::new();
    for actor in builder.actors.values() {
        let Some(process) = actor.process_id else {
            continue;
        };
        if !matches!(actor.location, EconomicLocation::County(_)) {
            continue;
        }
        let definition = definitions
            .get(&actor.function)
            .ok_or(NationalOpeningError::Policy)?;
        let machines = replacement_units(builder, actor, definition)?;
        let mut identity = b"NationalEquipmentAbroadV1\0".to_vec();
        identity.extend_from_slice(&process.as_bytes());
        rows.push((content_digest::sha256_of(&identity), process, machines));
    }
    let total: u128 = rows
        .iter()
        .map(|(_, _, machines)| u128::from(*machines))
        .sum();
    let bound = total * u128::from(share) / 10_000;
    rows.sort_unstable();
    let (mut taken, mut found) = (0_u128, BTreeSet::new());
    for (_, process, machines) in rows {
        let machines = u128::from(machines);
        if machines > 0 && taken + machines <= bound {
            taken += machines;
            found.insert(process);
        }
    }
    Ok(found)
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

/// The processes that open with machines, which sets how many ages each may open with (decision 3).
fn processes_with_machines(builder: &Builder<'_>, actors: &[ActorContext]) -> Result<u64> {
    let GameMachines::Workers {
        workers_per_machine,
        ..
    } = &builder.policy.equipment.machines
    else {
        return Ok(0);
    };
    let mut count = 0_u64;
    for actor in actors.iter().filter(|a| a.process_id.is_some()) {
        let workers = workers_per_machine
            .get(&actor.function)
            .ok_or(NationalOpeningError::Policy)?;
        if machines_for(actor.force, *workers)? > 0 {
            count += 1;
        }
    }
    Ok(count)
}

/// One definition per trade under schema 8: its id from sha256(b"NationalEquipmentDefinitionV2\0" ++ good ++ unit
/// ++ trade key), `batches_per_unit_per_period = ceil(work_hours_per_person x workers_per_machine /
/// labor_hours_per_batch)`, `service_batches_per_unit = batches_per_unit_per_period x machine_life_periods`.
/// Under schema 7 and earlier every trade shares the one definition of today.
fn definitions(builder: &Builder<'_>) -> Result<BTreeMap<EconomicFunction, EquipmentDefinition>> {
    let good = builder.commodity("equipment")?;
    let policy = builder.policy;
    if policy.equipment.installation_hours_per_unit == 0 {
        return Err(NationalOpeningError::Policy);
    }
    let make = |identity: Vec<u8>, batches: u64, service: u64| {
        if batches == 0 || service == 0 {
            return Err(NationalOpeningError::Policy);
        }
        Ok(EquipmentDefinition {
            id: EquipmentDefinitionId::from_bytes(content_digest::sha256_of(&identity)),
            equipment_good_id: good.good_id,
            equipment_unit_id: good.unit_id,
            batches_per_unit_per_period: batches,
            service_batches_per_unit: service,
            installation_labor_unit_id: builder.labor_unit,
            installation_hours_per_unit: policy.equipment.installation_hours_per_unit,
        })
    };
    let mut found = BTreeMap::new();
    match &policy.equipment.machines {
        GameMachines::Batches {
            batches_per_unit_per_period,
            service_batches_per_unit,
            ..
        } => {
            let mut identity = b"NationalEquipmentDefinitionV1\0".to_vec();
            identity.extend_from_slice(&good.good_id.as_bytes());
            identity.extend_from_slice(&good.unit_id.as_bytes());
            let definition = make(
                identity,
                *batches_per_unit_per_period,
                *service_batches_per_unit,
            )?;
            for function in policy.recipes.keys() {
                found.insert(*function, definition.clone());
            }
        }
        GameMachines::Workers {
            workers_per_machine,
            life_periods,
        } => {
            for (function, workers) in workers_per_machine {
                let recipe = policy
                    .recipes
                    .get(function)
                    .ok_or(NationalOpeningError::Policy)?;
                let hours = policy
                    .work_hours_per_person
                    .checked_mul(*workers)
                    .ok_or(NationalOpeningError::Arithmetic)?;
                if recipe.labor_hours_per_batch == 0 {
                    return Err(NationalOpeningError::Policy);
                }
                let batches = hours.div_ceil(recipe.labor_hours_per_batch);
                let service = batches
                    .checked_mul(*life_periods)
                    .ok_or(NationalOpeningError::Arithmetic)?;
                let mut identity = b"NationalEquipmentDefinitionV2\0".to_vec();
                identity.extend_from_slice(&good.good_id.as_bytes());
                identity.extend_from_slice(&good.unit_id.as_bytes());
                identity.extend_from_slice(function.source_key().as_bytes());
                found.insert(*function, make(identity, batches, service)?);
            }
        }
    }
    Ok(found)
}

/// A site's machines under schema 8: the persons over the trade's workers a machine, rounded up.
fn machines_for(persons: u64, workers_per_machine: u64) -> Result<u64> {
    if workers_per_machine == 0 {
        return Err(NationalOpeningError::Policy);
    }
    Ok(persons.div_ceil(workers_per_machine))
}

/// The most cohorts a process may open with: 8, or the row bound over the processes when that is fewer; `Bounds` when that is 0.
pub(super) fn machine_ages(processes: u64) -> Result<u64> {
    let room = ROW_BOUND.checked_div(processes).unwrap_or(MOST_AGES);
    match room.min(MOST_AGES) {
        0 => Err(NationalOpeningError::Bounds),
        ages => Ok(ages),
    }
}

/// A process's cohorts as (machines, percent of life left): `c = min(units, ages)` cohorts, cohort `k` holding
/// `units / c` machines plus one for `k < units % c`, at the age `1 + (k x 100 / c + s) % 100` where `s` is the
/// first byte of the process id modulo `100 / c`.
fn cohort_plan(process: ProcessId, units: u64, ages: u64) -> Result<Vec<(u64, u64)>> {
    if ages == 0 || ages > 100 {
        return Err(NationalOpeningError::Bounds);
    }
    let cohorts = units.min(ages);
    let Some(share) = units.checked_div(cohorts) else {
        return Ok(Vec::new());
    };
    let extra = units % cohorts;
    let start = u64::from(process.as_bytes()[0]) % (100 / cohorts);
    Ok((0..cohorts)
        .map(|k| {
            (
                share + u64::from(k < extra),
                1 + (k * 100 / cohorts + start) % 100,
            )
        })
        .collect())
}

/// A process's opening cohorts under schema 8: up to `ages` cohorts of every age (decision 3). A cohort's
/// remaining service is `life_batches x machines x age / 100`, rounded down and at least 1.
fn opening_cohorts(
    process: ProcessId,
    units: u64,
    life_batches: u64,
    ages: u64,
) -> Result<Vec<InstalledEquipmentCohort>> {
    cohort_plan(process, units, ages)?
        .into_iter()
        .enumerate()
        .map(|(k, (machines, age))| {
            let remaining = u64::try_from(
                (u128::from(life_batches) * u128::from(machines) * u128::from(age) / 100).max(1),
            )
            .map_err(|_| NationalOpeningError::Arithmetic)?;
            let mut identity = b"NationalOpeningEquipmentV2\0".to_vec();
            identity.extend_from_slice(&process.as_bytes());
            identity.push(u8::try_from(k).map_err(|_| NationalOpeningError::Bounds)?);
            Ok(InstalledEquipmentCohort {
                id: EquipmentCohortId::from_bytes(content_digest::sha256_of(&identity)),
                process_id: process,
                units: machines,
                remaining_service_batches: remaining,
                usable_from_period: 1,
            })
        })
        .collect()
}

fn equipment_price(builder: &Builder<'_>, actor: &ActorContext) -> Result<Currency> {
    Ok(builder
        .commodity("equipment")?
        .price
        .as_ref()
        .ok_or(NationalOpeningError::Policy)?
        .scaled(actor.price_scale_bps)
        .map_err(|_| NationalOpeningError::Arithmetic)?
        .opening)
}

fn opening_asset(
    builder: &mut Builder<'_>,
    actor: &ActorContext,
    definition: &EquipmentDefinition,
    ages: u64,
    equipment: &mut ProductiveEquipment,
    position: &mut EquipmentPosition,
) -> Result<()> {
    let process = actor.process_id.ok_or(NationalOpeningError::Identity)?;
    equipment.bindings.push(EquipmentBinding {
        process_id: process,
        site_id: actor.site_id,
        definition_id: definition.id,
    });
    match &builder.policy.equipment.machines {
        GameMachines::Batches {
            opening_remaining_service_bps,
            ..
        } => {
            let fractions = *opening_remaining_service_bps;
            batch_asset(builder, actor, definition, fractions, position)
        }
        GameMachines::Workers { .. } => {
            let units = machine_units(builder, actor, actor.force, definition)?;
            worker_assets(builder, actor, definition, (units, ages), position)
        }
    }
}

/// Schema 8: a site's machines open in cohorts of every age; each carries the share of its price that is left.
fn worker_assets(
    builder: &mut Builder<'_>,
    actor: &ActorContext,
    definition: &EquipmentDefinition,
    (units, ages): (u64, u64),
    position: &mut EquipmentPosition,
) -> Result<()> {
    let process = actor.process_id.ok_or(NationalOpeningError::Identity)?;
    if units == 0 {
        return Ok(());
    }
    let plan = cohort_plan(process, units, ages)?;
    let cohorts = opening_cohorts(process, units, definition.service_batches_per_unit, ages)?;
    let price = equipment_price(builder, actor)?;
    for ((machines, age), cohort) in plan.into_iter().zip(cohorts) {
        let original = super::amount(machines, price)?.micro_units();
        let carrying = original
            .checked_mul(i128::from(age))
            .ok_or(NationalOpeningError::Arithmetic)?
            / 100;
        builder.opening.equipment.push(EquipmentCarryingValue {
            asset: EquipmentAssetId::Installed(cohort.id),
            owner: actor.site_id,
            amount: Currency::from_micro_units(carrying),
        });
        position.cohorts.push(cohort);
    }
    Ok(())
}

/// Schema 7 and earlier: today's single cohort, from the grain's endowment where the site has one.
fn batch_asset(
    builder: &mut Builder<'_>,
    actor: &ActorContext,
    definition: &EquipmentDefinition,
    fractions: [u16; 4],
    position: &mut EquipmentPosition,
) -> Result<()> {
    let process = actor.process_id.ok_or(NationalOpeningError::Identity)?;
    let endowment = builder.endowments.get(&actor.site_id);
    let units = if let Some(endowment) = endowment {
        endowment.equipment_units
    } else {
        machine_units(builder, actor, actor.employed, definition)?
    };
    if units == 0 {
        return Ok(());
    }
    let fraction = fractions[usize::from(actor.site_id.as_bytes()[0]) % fractions.len()];
    if fraction == 0 || fraction > 10_000 {
        return Err(NationalOpeningError::Policy);
    }
    let life = super::quantity(units, definition.service_batches_per_unit)?;
    let remaining = if let Some(endowment) = endowment {
        endowment.equipment_service_batches
    } else {
        u64::try_from(u128::from(life) * u128::from(fraction) / 10_000)
            .map_err(|_| NationalOpeningError::Arithmetic)?
    };
    if remaining == 0 {
        return Err(NationalOpeningError::Policy);
    }
    let mut identity = b"NationalOpeningEquipmentV1\0".to_vec();
    identity.extend_from_slice(&process.as_bytes());
    let id = EquipmentCohortId::from_bytes(content_digest::sha256_of(&identity));
    position.cohorts.push(InstalledEquipmentCohort {
        id,
        process_id: process,
        units,
        remaining_service_batches: remaining,
        usable_from_period: 1,
    });
    let price = equipment_price(builder, actor)?;
    let original = super::amount(units, price)?.micro_units();
    let carrying = (original / 10_000)
        .checked_mul(i128::from(fraction))
        .and_then(|n| n.checked_add((original % 10_000) * i128::from(fraction) / 10_000))
        .ok_or(NationalOpeningError::Arithmetic)?;
    builder.opening.equipment.push(EquipmentCarryingValue {
        asset: EquipmentAssetId::Installed(id),
        owner: actor.site_id,
        amount: Currency::from_micro_units(
            endowment.map_or(carrying, |e| e.equipment_carrying_micros),
        ),
    });
    Ok(())
}

/// One period of a site's machines' wear under schema 8: the machines `machines_for` gives for `actor.force`,
/// times the equipment's opening price at the actor's price scale, over `machine_life_periods`, rounded up.
/// Zero under schema 7 and earlier, whose machines have no life in periods.
pub(super) fn wear_per_period(builder: &Builder<'_>, actor: &ActorContext) -> Result<Currency> {
    let GameMachines::Workers {
        workers_per_machine,
        life_periods,
    } = &builder.policy.equipment.machines
    else {
        return Ok(Currency::from_micro_units(0));
    };
    let workers = workers_per_machine
        .get(&actor.function)
        .ok_or(NationalOpeningError::Policy)?;
    let machines = machines_for(actor.force, *workers)?;
    wear(machines, equipment_price(builder, actor)?, *life_periods)
}

/// Its arithmetic: ceil(machines x price / `life_periods`).
fn wear(machines: u64, price: Currency, life_periods: u64) -> Result<Currency> {
    let value = super::amount(machines, price)?.micro_units();
    let life = i128::from(life_periods);
    if life == 0 || value < 0 {
        return Err(NationalOpeningError::Arithmetic);
    }
    let rounded_up = value
        .checked_add(life - 1)
        .ok_or(NationalOpeningError::Arithmetic)?
        / life;
    Ok(Currency::from_micro_units(rounded_up))
}

fn machine_units(
    builder: &Builder<'_>,
    actor: &ActorContext,
    persons: u64,
    definition: &EquipmentDefinition,
) -> Result<u64> {
    if let GameMachines::Workers {
        workers_per_machine,
        ..
    } = &builder.policy.equipment.machines
    {
        let workers = workers_per_machine
            .get(&actor.function)
            .ok_or(NationalOpeningError::Policy)?;
        return machines_for(persons, *workers);
    }
    if let Some(endowment) = builder.endowments.get(&actor.site_id) {
        if persons == actor.employed {
            return Ok(endowment.equipment_units);
        }
        if persons == actor.force {
            return Ok(endowment.workforce_equipment_units);
        }
        return Err(NationalOpeningError::Identity);
    }
    let recipe = builder
        .policy
        .recipes
        .get(&actor.function)
        .ok_or(NationalOpeningError::Policy)?;
    let batches = super::quantity(persons, builder.policy.work_hours_per_person)?
        / recipe.labor_hours_per_batch;
    Ok(batches.div_ceil(definition.batches_per_unit_per_period))
}

/// The machines a site replaces: those of its whole workforce under schema 8 (O14), of its jobs before.
fn replacement_units(
    builder: &Builder<'_>,
    actor: &ActorContext,
    definition: &EquipmentDefinition,
) -> Result<u64> {
    let persons = match builder.policy.equipment.machines {
        GameMachines::Workers { .. } => actor.force,
        GameMachines::Batches { .. } => actor.employed,
    };
    machine_units(builder, actor, persons, definition)
}

fn policies(
    builder: &mut Builder<'_>,
    actor: &ActorContext,
    definition: &EquipmentDefinition,
    equipment: &mut ProductiveEquipment,
    sourcing: &mut Sourcing<'_, '_>,
) -> Result<()> {
    let Sourcing {
        providers,
        network,
        preferences,
        abroad,
        machines,
    } = sourcing;
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
                required: super::quantity(starts, coefficient)?,
                buffer_periods: builder.policy.opening_input_periods,
            },
        )?;
    }
    let good = builder.commodity("equipment")?.clone();
    let cargo = good.cargo.ok_or(NationalOpeningError::Policy)?;
    let locations = providers
        .get(&(good.good_id, good.unit_id))
        .ok_or(NationalOpeningError::MissingObservation)?;
    let dealt = machines.filter(|_| {
        matches!(actor.location, EconomicLocation::County(_)) && !abroad.contains(&process)
    });
    let primary = if let Some(dealt) = dealt {
        dealt.get(&actor.site_id).copied()
    } else {
        markets::primary_supplier(
            locations,
            network,
            preferences,
            actor.location,
            actor.site_id,
            &good,
        )?
    };
    let by_product = matches!(
        builder.policy.markets.procurement,
        GameProcurement::ByProduct { .. }
    );
    let domestic = matches!(actor.location, EconomicLocation::County(_));
    let (supplier, cap) = if by_product && domestic && abroad.contains(&process) {
        let secondary =
            markets::secondary_supplier(builder, locations, network, actor.site_id, cargo)?;
        (secondary.or(primary), starts)
    } else if let Some(supplier) = primary {
        (Some(supplier), starts)
    } else {
        let secondary =
            markets::secondary_supplier(builder, locations, network, actor.site_id, cargo)?;
        let cap = if by_product && domestic {
            starts
        } else {
            let share = markets::foreign_share_bps(builder.policy, actor.location, "equipment")?;
            u64::try_from(u128::from(starts) * u128::from(share) / 10_000)
                .map_err(|_| NationalOpeningError::Arithmetic)?
        };
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
        replacement_target_units: replacement_units(builder, actor, definition)?,
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
    let hours = super::quantity(actor.force, builder.policy.work_hours_per_person)?;
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
            replacement_units: replacement_units(builder, actor, definition)?,
        },
        maximum_started_units_per_period: starts,
        maximum_hours_per_period: hours,
    });
    Ok(Some((starts, maximum)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn wear_is_a_period_of_the_machines_life() {
        let micros = |n| Currency::from_micro_units(n);
        assert_eq!(
            wear(100, micros(1_000_000_000), 100),
            Ok(micros(1_000_000_000))
        );
        assert_eq!(wear(3, micros(1_000_000), 100), Ok(micros(30_000)));
        assert_eq!(wear(1, micros(1_000_001), 100), Ok(micros(10_001)));
        assert_eq!(wear(1, micros(1), 0), Err(NationalOpeningError::Arithmetic));
    }

    fn process(first: u8) -> ProcessId {
        let mut bytes = [7_u8; 32];
        bytes[0] = first;
        ProcessId::from_bytes(bytes)
    }

    #[test]
    fn machines_follow_workers_not_batches() {
        // 400 workers of 160 hours, four to a machine: a batch of 16 or of 32 hours changes the batches
        // a machine does (40 or 20), never the machines.
        for (batch_hours, batches_a_machine) in [(16_u64, 40_u64), (32, 20)] {
            assert_eq!((160_u64 * 4).div_ceil(batch_hours), batches_a_machine);
            assert_eq!(machines_for(400, 4), Ok(100));
        }
        assert_eq!(machines_for(401, 4), Ok(101));
        assert_eq!(machines_for(0, 4), Ok(0));
        assert_eq!(machines_for(1, 0), Err(NationalOpeningError::Policy));
    }

    #[test]
    fn ages_spread_over_the_life() {
        let cohorts = opening_cohorts(process(13), 1_000, 4_000, 8).expect("cohorts");
        assert_eq!(cohorts.len(), 8);
        assert!(cohorts.iter().all(|c| c.units == 125));
        let ages: BTreeSet<u64> = cohorts
            .iter()
            .map(|c| c.remaining_service_batches * 100 / (4_000 * c.units))
            .collect();
        assert_eq!(ages.len(), 8, "eight distinct ages: {ages:?}");
        assert!(ages.iter().all(|a| (1..=100).contains(a)));
        let ids: BTreeSet<_> = cohorts.iter().map(|c| c.id).collect();
        assert_eq!(ids.len(), 8);
        let small = opening_cohorts(process(13), 3, 4_000, 8).expect("cohorts");
        assert_eq!(small.len(), 3);
        assert!(small.iter().all(|c| c.units == 1));
        let uneven = opening_cohorts(process(13), 10, 4_000, 8).expect("cohorts");
        assert_eq!(uneven.iter().map(|c| c.units).sum::<u64>(), 10);
        assert_eq!(uneven.iter().filter(|c| c.units == 2).count(), 2);
        assert_eq!(
            opening_cohorts(process(13), 0, 4_000, 8)
                .expect("none")
                .len(),
            0
        );
        assert_eq!(
            opening_cohorts(process(13), 1, 4_000, 0),
            Err(NationalOpeningError::Bounds)
        );
    }

    #[test]
    fn the_start_of_the_spread_differs_by_process() {
        let age = |first| {
            let c = opening_cohorts(process(first), 1, 4_000, 8).expect("cohorts");
            c[0].remaining_service_batches
        };
        assert_ne!(age(0), age(1));
        assert_eq!(age(0), 40, "1 + 0 = a hundredth of 4,000");
        assert_eq!(age(99), 4_000, "1 + 99 = the whole life");
        assert_eq!(age(100), 40, "the first byte counts modulo 100");
    }

    #[test]
    fn machine_ages_fit_the_row_bound() {
        assert_eq!(machine_ages(7_463), Ok(8));
        assert_eq!(machine_ages(10_000), Ok(6));
        assert_eq!(machine_ages(65_536), Ok(1));
        assert_eq!(machine_ages(65_537), Err(NationalOpeningError::Bounds));
        assert_eq!(machine_ages(0), Ok(8));
    }
}
