//! Finite supplier preferences, recurring household purchases and funded offers.
use super::{
    actors, amount, quantity, routes::Network, sum_amount, Builder, NationalOpeningError, Result,
};
use crate::{economic_catalog::MerchantSeed, national_transport::CargoClass};
use babylon_kernel::{
    content_digest::sha256_of, currency::Currency, economic_identity::EconomicFunction,
    economic_location::EconomicLocation,
};
use babylon_material_circuit::{
    AccountId, CommodityKind, CorridorId, GoodId, HouseholdNeedBasis, HouseholdPurchasePolicy,
    MerchantRole, PricePolicy, ReplenishmentPolicy, SellerOffer, ServiceConnection,
    ServiceInputPolicy, SiteId, StaffingPoolBinding, StaffingWorkSource, UnitId,
};
use std::collections::BTreeMap;

#[derive(Default)]
struct Preferences {
    services: BTreeMap<(EconomicLocation, GoodId, UnitId), Option<SiteId>>,
    domestic: BTreeMap<(EconomicLocation, GoodId, UnitId, Option<SiteId>), Option<SiteId>>,
}

type Providers = BTreeMap<(GoodId, UnitId), BTreeMap<EconomicLocation, Vec<SiteId>>>;

pub(super) fn wire(builder: &mut Builder<'_>) -> Result<()> {
    let retailers = local_retailers(builder)?;
    let mut providers: Providers = BTreeMap::new();
    let actors: Vec<_> = builder.actors.values().cloned().collect();
    for actor in actors {
        if actor.process_id.is_none() {
            continue;
        }
        let recipe = builder
            .policy
            .recipes
            .get(&actor.function)
            .ok_or(NationalOpeningError::Policy)?;
        let good = builder.commodity(&recipe.output)?.clone();
        let price = good
            .price
            .as_ref()
            .ok_or(NationalOpeningError::Policy)?
            .scaled(actor.price_scale_bps)
            .map_err(|_| NationalOpeningError::Arithmetic)?;
        builder.set_offer(SellerOffer {
            site_id: actor.site_id,
            good_id: good.good_id,
            unit_id: good.unit_id,
            unit_price: price.opening,
            pricing: match good.kind {
                CommodityKind::Storable { .. } => PricePolicy::Responsive {
                    minimum: price.minimum,
                    maximum: price.maximum,
                    step: price.step,
                    target_stock: quantity(actor.planned_batches, recipe.output_units_per_batch)?,
                },
                CommodityKind::PeriodService { .. } => PricePolicy::ServiceResponsive {
                    minimum: price.minimum,
                    maximum: price.maximum,
                    step: price.step,
                },
            },
        });
        if actor.employed > 0 {
            providers
                .entry((good.good_id, good.unit_id))
                .or_default()
                .entry(actor.location)
                .or_default()
                .push(actor.site_id);
        }
    }
    for locations in providers.values_mut() {
        for ids in locations.values_mut() {
            ids.sort_unstable_by_key(|id| (std::cmp::Reverse(builder.actors[id].employed), *id));
        }
    }
    let mut network = Network::new(builder.transport)?;
    let mut preferences = Preferences::default();
    households(
        builder,
        &retailers,
        &providers,
        &mut network,
        &mut preferences,
    )?;
    producers(builder, &providers, &mut network, &mut preferences)?;
    let policies = &mut builder.opening.policies;
    policies
        .offers
        .sort_unstable_by_key(|r| (r.site_id, r.good_id, r.unit_id));
    policies
        .replenishment
        .sort_unstable_by_key(|r| (r.buyer_site_id, r.supplier_site_id, r.good_id, r.unit_id));
    policies
        .household_purchases
        .sort_unstable_by_key(|r| (r.principal_id, r.good_id, r.unit_id));
    policies
        .service_inputs
        .sort_unstable_by_key(|r| (r.buyer_site_id, r.good_id, r.unit_id));
    policies.service_connections.sort_unstable();
    Ok(())
}

fn local_retailers(builder: &mut Builder<'_>) -> Result<BTreeMap<EconomicLocation, SiteId>> {
    let mut selected = BTreeMap::new();
    for actor in builder
        .actors
        .values()
        .filter(|a| a.employed > 0 && a.function == EconomicFunction::DistributionTransport)
    {
        let entry = selected.entry(actor.location).or_insert(actor.site_id);
        if (actor.employed, std::cmp::Reverse(actor.site_id))
            > (builder.actors[entry].employed, std::cmp::Reverse(*entry))
        {
            *entry = actor.site_id;
        }
    }
    // Missing commercial distribution becomes a role at an existing accounted
    // workplace, with its existing people, shared attendance and actual cash.
    let missing: Vec<_> = builder
        .opening
        .households
        .iter()
        .filter(|h| !selected.contains_key(&h.location))
        .map(|h| (h.location, h.persons, h.households))
        .collect();
    for (location, persons, households) in missing {
        let site = builder
            .actors
            .values()
            .filter(|a| a.location == location && a.employed > 0)
            .max_by_key(|a| (a.employed, std::cmp::Reverse(a.site_id)))
            .map(|a| a.site_id)
            .ok_or(NationalOpeningError::MissingObservation)?;
        let mut identity = b"NationalMerchantHandlingV1\0".to_vec();
        identity.extend_from_slice(&site.as_bytes());
        let merchant = MerchantSeed {
            role: MerchantRole::Retail,
            capacity_id: CorridorId::from_bytes(sha256_of(&identity)),
            labor_unit_id: builder.labor_unit,
            handling: actors::handling_requirements(builder)?,
        };
        let retail_hours = retail_hours(builder, persons, households)?;
        let actor = builder
            .actors
            .get_mut(&site)
            .ok_or(NationalOpeningError::Identity)?;
        if let Some(process) = actor.process_id {
            let recipe = builder
                .policy
                .recipes
                .get(&actor.function)
                .ok_or(NationalOpeningError::Policy)?;
            let available = quantity(actor.employed, builder.policy.work_hours_per_person)?;
            actor.planned_batches =
                available.saturating_sub(retail_hours) / recipe.labor_hours_per_batch;
            let row = builder.opening.sites[*builder
                .sites
                .get(&site)
                .ok_or(NationalOpeningError::Identity)?]
            .processes
            .iter_mut()
            .find(|p| p.process_id == process)
            .ok_or(NationalOpeningError::Identity)?;
            row.planned_batches = actor.planned_batches;
            row.output_buffer = quantity(actor.planned_batches, recipe.output_units_per_batch)?;
        }
        builder.site_mut(site)?.merchant = Some(merchant);
        let staffing = builder
            .opening
            .staffing
            .iter_mut()
            .find(|s| s.pool.site_id() == site)
            .ok_or(NationalOpeningError::Identity)?;
        let pool = &staffing.pool;
        let mut sources = pool.work_sources().to_vec();
        sources.push(StaffingWorkSource::MerchantHandling(site));
        staffing.pool = StaffingPoolBinding::try_new(
            pool.pool_id(),
            pool.site_id(),
            pool.unit_id(),
            pool.labor_force(),
            pool.policy(),
            sources,
        )
        .map_err(|_| NationalOpeningError::Policy)?;
        selected.insert(location, site);
    }
    Ok(selected)
}

fn retail_hours(builder: &Builder<'_>, persons: u64, households: u64) -> Result<u64> {
    let hours = builder
        .policy
        .household_needs
        .iter()
        .try_fold(0_u64, |hours, need| {
            let good = builder.commodity(&need.key)?;
            if !matches!(good.kind, CommodityKind::Storable { .. }) {
                return Ok(hours);
            }
            let units = quantity(
                match need.basis {
                    HouseholdNeedBasis::Persons => persons,
                    HouseholdNeedBasis::Households => households,
                },
                need.units_per_basis,
            )?;
            hours
                .checked_add(quantity(units, builder.policy.handling_hours_per_unit)?)
                .ok_or(NationalOpeningError::Arithmetic)
        })?;

    Ok(hours)
}

fn households(
    builder: &mut Builder<'_>,
    retailers: &BTreeMap<EconomicLocation, SiteId>,
    providers: &Providers,
    network: &mut Network<'_>,
    preferences: &mut Preferences,
) -> Result<()> {
    let households = builder.opening.households.clone();
    for household in households {
        let retailer = *retailers
            .get(&household.location)
            .ok_or(NationalOpeningError::Identity)?;
        for need in builder.policy.household_needs.clone() {
            let good = builder.commodity(&need.key)?.clone();
            let required = quantity(
                match need.basis {
                    HouseholdNeedBasis::Persons => household.persons,
                    HouseholdNeedBasis::Households => household.households,
                },
                need.units_per_basis,
            )?;
            let seller = match good.kind {
                CommodityKind::Storable { .. } => retailer,
                CommodityKind::PeriodService { .. } => service_provider(
                    providers,
                    network,
                    preferences,
                    household.location,
                    good.good_id,
                    good.unit_id,
                )?
                .ok_or(NationalOpeningError::MissingObservation)?,
            };
            builder
                .opening
                .policies
                .household_purchases
                .push(HouseholdPurchasePolicy {
                    principal_id: household.principal_id,
                    retailer_site_id: seller,
                    good_id: good.good_id,
                    unit_id: good.unit_id,
                    target_closing_stock: if good.cargo.is_some() { required } else { 0 },
                    maximum_purchase: quantity(required, builder.policy.retailer_buffer_periods)?,
                    enabled: true,
                });
            if let CommodityKind::PeriodService { .. } = good.kind {
                builder
                    .opening
                    .policies
                    .service_connections
                    .push(ServiceConnection {
                        provider_site_id: seller,
                        buyer: AccountId::Household(household.principal_id),
                        good_id: good.good_id,
                        unit_id: good.unit_id,
                    });
                continue;
            }
            retail_stock(builder, retailer, &need.key, required)?;
            procure(
                builder,
                providers,
                network,
                preferences,
                ProcurementNeed {
                    buyer: retailer,
                    key: &need.key,
                    required,
                    buffer_periods: builder.policy.retailer_buffer_periods,
                },
            )?;
        }
    }
    Ok(())
}

fn retail_stock(
    builder: &mut Builder<'_>,
    retailer: SiteId,
    key: &str,
    required: u64,
) -> Result<()> {
    let good = builder.commodity(key)?.clone();
    let actor = builder.actors[&retailer].clone();
    let price = good
        .price
        .as_ref()
        .ok_or(NationalOpeningError::Policy)?
        .scaled(actor.price_scale_bps)
        .map_err(|_| NationalOpeningError::Arithmetic)?;
    let handling_charge = amount(builder.policy.handling_hours_per_unit, actor.wage)?;
    let unit_price = sum_amount(price.opening, handling_charge)?;
    let minimum = sum_amount(price.minimum, handling_charge)?;
    let maximum = sum_amount(price.maximum, handling_charge)?;
    let stock = quantity(required, builder.policy.retailer_buffer_periods)?;
    let offer = SellerOffer {
        site_id: retailer,
        good_id: good.good_id,
        unit_id: good.unit_id,
        unit_price,
        pricing: PricePolicy::Responsive {
            minimum,
            maximum,
            step: price.step,
            target_stock: stock,
        },
    };
    builder.set_offer(offer);
    let opening_stock = actors::stock(builder, key, stock, actor.price_scale_bps)?;
    let working_cash = amount(
        builder.policy.working_capital_periods,
        amount(required, price.opening)?,
    )?;
    let site = builder.site_mut(retailer)?;
    if let Some(existing) = site
        .opening_stock
        .iter_mut()
        .find(|s| s.amount.good_id == good.good_id && s.amount.unit_id == good.unit_id)
    {
        existing.amount.quantity = existing
            .amount
            .quantity
            .checked_add(opening_stock.amount.quantity)
            .ok_or(NationalOpeningError::Arithmetic)?;
        existing.total_cost = sum_amount(existing.total_cost, opening_stock.total_cost)?;
    } else {
        site.opening_stock.push(opening_stock);
    }
    site.opening_cash = sum_amount(site.opening_cash, working_cash)?;

    Ok(())
}

fn producers(
    builder: &mut Builder<'_>,
    providers: &Providers,
    network: &mut Network<'_>,
    preferences: &mut Preferences,
) -> Result<()> {
    let actors: Vec<_> = builder.actors.values().cloned().collect();
    for actor in actors {
        if actor.process_id.is_none() {
            continue;
        }
        let recipe = builder
            .policy
            .recipes
            .get(&actor.function)
            .ok_or(NationalOpeningError::Policy)?
            .clone();
        let maximum_batches = quantity(actor.force, builder.policy.work_hours_per_person)?
            / recipe.labor_hours_per_batch;
        for (key, coefficient) in recipe.inputs {
            let good = builder.commodity(&key)?.clone();
            if good.price.is_none() {
                continue;
            } // finite deposit is not bought or reproduced
            let required = quantity(maximum_batches, coefficient)?;
            if required == 0 {
                continue;
            }
            match good.kind {
                CommodityKind::Storable { .. } => procure(
                    builder,
                    providers,
                    network,
                    preferences,
                    ProcurementNeed {
                        buyer: actor.site_id,
                        key: &key,
                        required,
                        buffer_periods: builder.policy.opening_input_periods,
                    },
                )?,
                CommodityKind::PeriodService { .. } => {
                    let Some(provider) = service_provider(
                        providers,
                        network,
                        preferences,
                        actor.location,
                        good.good_id,
                        good.unit_id,
                    )?
                    else {
                        continue;
                    };
                    if provider == actor.site_id {
                        return Err(NationalOpeningError::Policy);
                    }
                    builder
                        .opening
                        .policies
                        .service_inputs
                        .push(ServiceInputPolicy {
                            buyer_site_id: actor.site_id,
                            provider_site_id: provider,
                            good_id: good.good_id,
                            unit_id: good.unit_id,
                            quantity_per_period: required,
                            maximum_purchase: required,
                            cash_floor: payroll(builder, actor.site_id)?,
                        });
                    builder
                        .opening
                        .policies
                        .service_connections
                        .push(ServiceConnection {
                            provider_site_id: provider,
                            buyer: AccountId::Site(actor.site_id),
                            good_id: good.good_id,
                            unit_id: good.unit_id,
                        });
                }
            }
        }
    }
    Ok(())
}

fn service_provider(
    providers: &Providers,
    network: &mut Network<'_>,
    preferences: &mut Preferences,
    buyer: EconomicLocation,
    good: GoodId,
    unit: UnitId,
) -> Result<Option<SiteId>> {
    let cache_key = (buyer, good, unit);
    if let Some(cached) = preferences.services.get(&cache_key) {
        return Ok(*cached);
    }
    let Some(locations) = providers.get(&(good, unit)) else {
        return Ok(None);
    };
    let candidates = locations
        .keys()
        .copied()
        .filter(|&location| match (buyer, location) {
            (EconomicLocation::County(a), EconomicLocation::County(b)) => {
                a.geoid().as_bytes()[..2] == b.geoid().as_bytes()[..2]
            }
            _ => buyer == location,
        });
    let selected = network
        .nearest(buyer, CargoClass::General, candidates)?
        .and_then(|location| {
            locations
                .get(&location)
                .and_then(|ids| ids.first())
                .copied()
        });
    preferences.services.insert(cache_key, selected);
    Ok(selected)
}

#[derive(Clone, Copy)]
struct ProcurementNeed<'a> {
    buyer: SiteId,
    key: &'a str,
    required: u64,
    buffer_periods: u64,
}

fn primary_supplier(
    locations: &BTreeMap<EconomicLocation, Vec<SiteId>>,
    network: &mut Network<'_>,
    preferences: &mut Preferences,
    location: EconomicLocation,
    buyer: SiteId,
    good: &crate::national_economy::GameCommodity,
) -> Result<Option<SiteId>> {
    let cargo = good.cargo.ok_or(NationalOpeningError::Policy)?;
    let excluded = locations
        .get(&location)
        .filter(|ids| ids.contains(&buyer))
        .map(|_| buyer);
    let cache_key = (location, good.good_id, good.unit_id, excluded);
    let primary = if let Some(cached) = preferences.domestic.get(&cache_key) {
        *cached
    } else {
        let primary_location = network.nearest(
            location,
            cargo,
            locations
                .iter()
                .filter(|(candidate, ids)| {
                    ids.iter().any(|&site| Some(site) != excluded)
                        && if matches!(location, EconomicLocation::County(_)) {
                            matches!(candidate, EconomicLocation::County(_))
                        } else {
                            **candidate == location
                        }
                })
                .map(|(candidate, _)| *candidate),
        )?;
        let selected = primary_location.and_then(|loc| {
            locations[&loc]
                .iter()
                .copied()
                .find(|&site| Some(site) != excluded)
        });
        preferences.domestic.insert(cache_key, selected);
        selected
    };

    Ok(primary)
}

fn secondary_supplier(
    builder: &Builder<'_>,
    locations: &BTreeMap<EconomicLocation, Vec<SiteId>>,
    network: &mut Network<'_>,
    buyer: SiteId,
    cargo: CargoClass,
) -> Result<Option<SiteId>> {
    let location = builder
        .actors
        .get(&buyer)
        .ok_or(NationalOpeningError::Identity)?
        .location;
    // Source rosters qualify identity, not a promised annual import quantity.
    // Rotate bounded counterpart preferences deterministically across workplaces.
    let mut external: Vec<_> = locations
        .keys()
        .copied()
        .filter(|&candidate| match location {
            EconomicLocation::County(_) => matches!(candidate, EconomicLocation::Foreign(_)),
            _ => matches!(candidate, EconomicLocation::County(_)),
        })
        .collect();
    if matches!(location, EconomicLocation::County(_)) && !external.is_empty() {
        let bytes = buyer.as_bytes();
        let rotation =
            usize::try_from(u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]))
                .map_err(|_| NationalOpeningError::Bounds)?
                % external.len();
        external.rotate_left(rotation);
    } else {
        external.sort_unstable_by_key(|loc| {
            (
                std::cmp::Reverse(builder.actors[&locations[loc][0]].employed),
                *loc,
            )
        });
    }
    let mut secondary = None;
    for candidate in external {
        if network.path(candidate, location, cargo)?.is_some() {
            secondary = locations[&candidate]
                .iter()
                .copied()
                .find(|&site| site != buyer);
            if secondary.is_some() {
                break;
            }
        }
    }

    Ok(secondary)
}

fn procure(
    builder: &mut Builder<'_>,
    providers: &Providers,
    network: &mut Network<'_>,
    preferences: &mut Preferences,
    need: ProcurementNeed<'_>,
) -> Result<()> {
    let ProcurementNeed {
        buyer,
        key,
        required,
        buffer_periods,
    } = need;
    let actor = builder
        .actors
        .get(&buyer)
        .ok_or(NationalOpeningError::Identity)?;
    let location = actor.location;
    let good = builder.commodity(key)?.clone();
    let cargo = good.cargo.ok_or(NationalOpeningError::Policy)?;
    let Some(locations) = providers.get(&(good.good_id, good.unit_id)) else {
        return Ok(());
    };
    let primary = primary_supplier(locations, network, preferences, location, buyer, &good)?;
    let secondary = secondary_supplier(builder, locations, network, buyer, cargo)?;
    let foreign_cap = if secondary.is_some() {
        u64::try_from(
            u128::from(required) * u128::from(builder.policy.markets.foreign_procurement_bps)
                / 10_000,
        )
        .map_err(|_| NationalOpeningError::Arithmetic)?
    } else {
        0
    };
    let domestic_cap = required
        .checked_sub(foreign_cap)
        .ok_or(NationalOpeningError::Arithmetic)?;
    let target = quantity(required, buffer_periods)?;
    let floor = payroll(builder, buyer)?;
    for (supplier, cap) in [(primary, domestic_cap), (secondary, foreign_cap)] {
        if let Some(supplier) = supplier.filter(|_| cap > 0) {
            builder.add_procurement(ReplenishmentPolicy {
                buyer_site_id: buyer,
                supplier_site_id: supplier,
                good_id: good.good_id,
                unit_id: good.unit_id,
                target_stock: target,
                maximum_purchase: cap,
                cash_floor: floor,
            })?;
        }
    }
    Ok(())
}
fn payroll(builder: &Builder<'_>, site: SiteId) -> Result<Currency> {
    let actor = builder
        .actors
        .get(&site)
        .ok_or(NationalOpeningError::Identity)?;
    amount(
        quantity(actor.employee_persons, builder.policy.work_hours_per_person)?,
        actor.wage,
    )
}
