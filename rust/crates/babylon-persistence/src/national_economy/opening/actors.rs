//! Aggregate resident/workplace opening assignments, not simulated individuals.
use super::{
    amount, quantity, sum_amount, templates, ActorContext, Builder, NationalOpeningError, Result,
};
use crate::{
    economic_catalog::{
        CommodityAmount, EconomicHouseholdSeed, EconomicSiteSeed, EconomicSiteSource,
        HouseholdTemplateId, MerchantSeed, OpeningCommodityStock, ProcessInstallation,
    },
    national_counties::NationalCountyReference,
    national_economy::{household_principal, ResidentWorkplaceSource},
    national_resident_allocation::{ResidentAttendanceMode, ResidentWorkplaceAllocation},
};
use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::{
    content_digest::sha256_of, currency::Currency, economic_identity::EconomicFunction,
    economic_location::EconomicLocation,
};
use babylon_material_circuit::{
    CommodityKind, CorridorId, EmploymentTerms, HouseholdNeedBasis, LaborCompensation,
    LogisticsNodeId, MerchantRole, ProcessId, StaffingPolicy, StaffingWorkSource,
};

pub(super) fn domestic(
    builder: &mut Builder<'_>,
    counties: &NationalCountyReference,
    allocation: &ResidentWorkplaceAllocation,
) -> Result<()> {
    for controls in &allocation.counties {
        let location = EconomicLocation::domestic_county(controls.county)
            .map_err(|_| NationalOpeningError::SourceScope)?;
        household(
            builder,
            location,
            controls.population,
            controls.households,
            10_000,
        )?;
    }
    for row in &allocation.workplaces {
        let target = &row.target;
        let employed = row.members.iter().try_fold(0_u64, |n, member| {
            n.checked_add(member.seed.employed)
                .ok_or(NationalOpeningError::Arithmetic)
        })?;
        let force = row.members.iter().try_fold(0_u64, |n, member| {
            n.checked_add(member.seed.member.labor_force())
                .ok_or(NationalOpeningError::Arithmetic)
        })?;
        let employee_persons = row
            .members
            .iter()
            .filter(|m| m.mode == ResidentAttendanceMode::Employee)
            .try_fold(0_u64, |n, member| {
                n.checked_add(member.seed.employed)
                    .ok_or(NationalOpeningError::Arithmetic)
            })?;
        let source = match &target.source {
            ResidentWorkplaceSource::Qcew(key) => EconomicSiteSource::Qcew(*key),
            ResidentWorkplaceSource::HouseholdEnterprise => EconomicSiteSource::Designed {
                key: "household-enterprise".into(),
            },
            ResidentWorkplaceSource::ResidentEmployerFallback => EconomicSiteSource::Designed {
                key: format!("resident-employer-{}", target.ownership.source_code()),
            },
        };
        let EconomicLocation::County(county) = target.location else {
            return Err(NationalOpeningError::SourceScope);
        };
        let county_name = counties
            .county(county.geoid())
            .map_err(|_| NationalOpeningError::SourceScope)?
            .name();
        let label = format!(
            "{county_name}: {} ({})",
            target.function.source_key(),
            target.ownership.source_code()
        );
        let context = ActorContext {
            site_id: target.site_id,
            function: target.function,
            source_ownership: matches!(source, EconomicSiteSource::Qcew(_))
                .then_some(target.ownership),
            location: target.location,
            employed,
            employee_persons,
            force,
            wage: builder.policy.default_wage,
            price_scale_bps: 10_000,
            planned_batches: 0,
            process_id: None,
        };
        site(builder, context, target.workplace.clone(), source, label)?;
        employment(builder, row);
    }
    builder.opening.staffing = allocation
        .staffing_seeds(|target| {
            let actor = builder
                .actors
                .get(&target.site_id)
                .ok_or(crate::national_resident_allocation::AllocationError::Identity)?;
            let work_sources = sources(actor);
            let previous = actor
                .employed
                .checked_mul(builder.policy.work_hours_per_person)
                .ok_or(crate::national_resident_allocation::AllocationError::Arithmetic)?;
            Ok((
                builder.labor_unit,
                StaffingPolicy::one_period(builder.policy.work_hours_per_person)
                    .map_err(|_| crate::national_resident_allocation::AllocationError::Policy)?,
                previous,
                work_sources,
            ))
        })
        .map_err(NationalOpeningError::Workforce)?;
    Ok(())
}

fn employment(
    builder: &mut Builder<'_>,
    row: &crate::national_resident_allocation::AssignedResidentWorkplace,
) {
    for member in &row.members {
        let compensation = match member.mode {
            ResidentAttendanceMode::Employee => {
                LaborCompensation::Wage(builder.policy.default_wage)
            }
            ResidentAttendanceMode::WorkingOwner => LaborCompensation::WorkingOwner,
            ResidentAttendanceMode::UnpaidFamily => LaborCompensation::UnpaidFamily,
        };
        builder.opening.employment.push(EmploymentTerms {
            member_id: member.seed.member.member_id(),
            site_id: row.target.site_id,
            unit_id: builder.labor_unit,
            payee: member.seed.member.household_id(),
            compensation,
        });
    }
}

pub(super) fn sources(actor: &ActorContext) -> Vec<StaffingWorkSource> {
    actor.process_id.map_or_else(
        || vec![StaffingWorkSource::MerchantHandling(actor.site_id)],
        |process| vec![StaffingWorkSource::Production(process)],
    )
}

pub(super) fn household(
    builder: &mut Builder<'_>,
    location: EconomicLocation,
    persons: u64,
    households: u64,
    price_scale_bps: u16,
) -> Result<()> {
    if persons == 0 || households == 0 || households > persons {
        return Err(NationalOpeningError::MissingObservation);
    }
    let mut stock = vec![];
    let mut period_needs_cost = Currency::from_micro_units(0);
    for need in &builder.policy.household_needs {
        let good = builder.commodity(&need.key)?;
        let units = quantity(
            match need.basis {
                HouseholdNeedBasis::Persons => persons,
                HouseholdNeedBasis::Households => households,
            },
            need.units_per_basis,
        )?;
        let price = good
            .price
            .as_ref()
            .ok_or(NationalOpeningError::Policy)?
            .scaled(price_scale_bps)
            .map_err(|_| NationalOpeningError::Arithmetic)?
            .opening;
        period_needs_cost = sum_amount(period_needs_cost, amount(units, price)?)?;
        if matches!(good.kind, CommodityKind::Storable { .. }) {
            stock.push(OpeningCommodityStock {
                amount: CommodityAmount {
                    good_id: good.good_id,
                    unit_id: good.unit_id,
                    quantity: quantity(units, builder.policy.opening_pantry_periods)?,
                },
                total_cost: amount(
                    quantity(units, builder.policy.opening_pantry_periods)?,
                    price,
                )?,
            });
        }
    }
    builder.opening.households.push(EconomicHouseholdSeed {
        principal_id: household_principal(location),
        subject: subject(location, "household"),
        location,
        persons,
        households,
        template: HouseholdTemplateId(1),
        opening_stock: stock,
        opening_cash: amount(builder.policy.working_capital_periods, period_needs_cost)?,
    });
    Ok(())
}

pub(super) fn site(
    builder: &mut Builder<'_>,
    mut context: ActorContext,
    subject: StableElementKey,
    source: EconomicSiteSource,
    label: String,
) -> Result<()> {
    let logistics_node_id = *builder
        .logistics_nodes
        .get(&context.location)
        .ok_or(NationalOpeningError::SourceScope)?;
    let mut processes = vec![];
    let mut opening_stock = vec![];
    let mut inputs_cost = Currency::from_micro_units(0);
    let merchant = if context.function == EconomicFunction::DistributionTransport {
        let mut capacity = b"NationalMerchantHandlingV1\0".to_vec();
        capacity.extend_from_slice(&context.site_id.as_bytes());
        Some(MerchantSeed {
            role: MerchantRole::Retail,
            capacity_id: CorridorId::from_bytes(sha256_of(&capacity)),
            labor_unit_id: builder.labor_unit,
            handling: handling_requirements(builder)?,
        })
    } else {
        let (installation, cost) = process(builder, &mut context, &mut opening_stock)?;
        processes.push(installation);
        inputs_cost = cost;
        None
    };
    let wages = amount(
        quantity(
            context.employee_persons,
            builder.policy.work_hours_per_person,
        )?,
        context.wage,
    )?;
    let opening_cash = amount(
        builder.policy.working_capital_periods,
        sum_amount(wages, inputs_cost)?,
    )?;
    builder.add_site(
        context.clone(),
        EconomicSiteSeed {
            site_id: context.site_id,
            label,
            function: context.function,
            subject,
            location: context.location,
            logistics_node_id,
            source,
            processes,
            merchant,
            opening_stock,
            opening_cash,
        },
    )
}

fn process(
    builder: &Builder<'_>,
    context: &mut ActorContext,
    opening_stock: &mut Vec<OpeningCommodityStock>,
) -> Result<(ProcessInstallation, Currency)> {
    let mut inputs_cost = Currency::from_micro_units(0);
    let recipe = builder
        .policy
        .recipes
        .get(&context.function)
        .ok_or(NationalOpeningError::Policy)?;
    if recipe.labor_hours_per_batch == 0 {
        return Err(NationalOpeningError::Policy);
    }
    context.planned_batches = quantity(context.employed, builder.policy.work_hours_per_person)?
        / recipe.labor_hours_per_batch;
    let mut identity = b"NationalProcessV1\0".to_vec();
    identity.extend_from_slice(&context.site_id.as_bytes());
    let process_id = ProcessId::from_bytes(sha256_of(&identity));
    context.process_id = Some(process_id);
    let output_units = quantity(context.planned_batches, recipe.output_units_per_batch)?;
    let installation = ProcessInstallation {
        process_id,
        recipe: templates::recipe_id(context.function)?,
        installed_batches: context.planned_batches,
        planned_batches: context.planned_batches,
        output_buffer: output_units,
    };
    for (key, coefficient) in &recipe.inputs {
        let good = builder.commodity(key)?;
        let needed = quantity(context.planned_batches, *coefficient)?;
        if let Some(price) = &good.price {
            let price = price
                .scaled(context.price_scale_bps)
                .map_err(|_| NationalOpeningError::Arithmetic)?
                .opening;
            inputs_cost = sum_amount(inputs_cost, amount(needed, price)?)?;
        }
        if matches!(good.kind, CommodityKind::Storable { .. }) {
            let periods = if key == "resource_deposit" {
                builder.policy.resource_reserve_output_periods
            } else {
                builder.policy.opening_input_periods
            };
            opening_stock.push(stock(
                builder,
                key,
                quantity(needed, periods)?,
                context.price_scale_bps,
            )?);
        }
    }
    let output = builder.commodity(&recipe.output)?;
    if matches!(output.kind, CommodityKind::Storable { .. }) {
        opening_stock.push(stock(
            builder,
            &recipe.output,
            output_units,
            context.price_scale_bps,
        )?);
    }

    Ok((installation, inputs_cost))
}

pub(super) fn stock(
    builder: &Builder<'_>,
    key: &str,
    units: u64,
    price_scale_bps: u16,
) -> Result<OpeningCommodityStock> {
    let good = builder.commodity(key)?;
    let cost = match &good.price {
        Some(price) => amount(
            units,
            price
                .scaled(price_scale_bps)
                .map_err(|_| NationalOpeningError::Arithmetic)?
                .opening,
        )?,
        None => Currency::from_micro_units(0),
    };
    Ok(OpeningCommodityStock {
        amount: CommodityAmount {
            good_id: good.good_id,
            unit_id: good.unit_id,
            quantity: units,
        },
        total_cost: cost,
    })
}

pub(super) fn subject(location: EconomicLocation, prefix: &str) -> StableElementKey {
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let encoded: String = location
        .canonical_bytes()
        .into_iter()
        .flat_map(|byte| {
            [
                char::from(HEX[usize::from(byte >> 4)]),
                char::from(HEX[usize::from(byte & 15)]),
            ]
        })
        .collect();
    StableElementKey::Node {
        scenario: "national-world".into(),
        local_name: format!("{}-{encoded}", prefix.replace('_', "-")),
    }
}
pub(super) fn node_id(source: &str) -> LogisticsNodeId {
    let mut bytes = b"NationalLogisticsNodeV1\0".to_vec();
    bytes.extend_from_slice(source.as_bytes());
    LogisticsNodeId::from_bytes(sha256_of(&bytes))
}

pub(super) fn handling_requirements(
    builder: &Builder<'_>,
) -> Result<Vec<crate::economic_catalog::HandlingRequirement>> {
    builder
        .policy
        .household_needs
        .iter()
        .filter_map(|need| match builder.commodity(&need.key) {
            Ok(good) if matches!(good.kind, CommodityKind::Storable { .. }) => {
                Some(Ok(crate::economic_catalog::HandlingRequirement {
                    good_id: good.good_id,
                    unit_id: good.unit_id,
                    hours_per_unit: builder.policy.handling_hours_per_unit,
                }))
            }
            Ok(_) => None,
            Err(error) => Some(Err(error)),
        })
        .collect()
}
