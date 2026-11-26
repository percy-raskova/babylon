//! Finite supplier preferences, recurring household purchases and funded offers.
use super::routes::Network;
use super::{actors, templates, ActorContext, Builder, NationalOpeningError, Result};
use crate::national_economy::grain::FinancialDomainId;

use crate::economic_catalog::{EconomicHouseholdSeed, MerchantSeed, ResidentStaffingPoolSeed};
use crate::national_transport::CargoClass;

use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::EconomicFunction;
use babylon_kernel::economic_location::EconomicLocation;

use crate::national_economy::{GameCommodity, GameHandling, GameProcurement, NationalGamePolicy};
use babylon_kernel::content_digest;
use babylon_material_circuit::HouseholdKind;
use babylon_material_circuit::{
    AccountId, CommodityKind, CorridorId, GoodId, HouseholdNeedBasis, HouseholdPurchasePolicy,
    MerchantRole, PricePolicy, ReplenishmentPolicy, SellerOffer, ServiceConnection,
    ServiceInputPolicy, SiteId, StaffingPoolBinding, StaffingWorkSource, UnitId,
    MAX_HOUSEHOLD_NEEDS, MAX_HOUSEHOLD_WANTS,
};
use std::collections::BTreeMap;

#[derive(Default)]
pub(super) struct Preferences {
    services: BTreeMap<(EconomicLocation, GoodId, UnitId), Option<SiteId>>,
    domestic: BTreeMap<(EconomicLocation, GoodId, UnitId, Option<SiteId>), Option<SiteId>>,
}

pub(super) type Providers = BTreeMap<(GoodId, UnitId), ProviderLocations>;

pub(super) struct ProviderLocations {
    sites: BTreeMap<EconomicLocation, Vec<SiteId>>,
    foreign: Vec<EconomicLocation>,
    counties_by_employment: Vec<EconomicLocation>,
}

impl ProviderLocations {
    fn new(
        mut sites: BTreeMap<EconomicLocation, Vec<SiteId>>,
        actors: &BTreeMap<SiteId, ActorContext>,
    ) -> Self {
        let mut foreign = Vec::new();
        let mut counties_by_employment = Vec::new();
        for (&location, ids) in &mut sites {
            ids.sort_unstable_by_key(|id| (std::cmp::Reverse(actors[id].employed), *id));
            match location {
                EconomicLocation::Foreign(_) => foreign.push(location),
                EconomicLocation::County(_) => counties_by_employment.push(location),
                EconomicLocation::Dependency(_) => {}
            }
        }
        counties_by_employment
            .sort_unstable_by_key(|loc| (std::cmp::Reverse(actors[&sites[loc][0]].employed), *loc));
        Self {
            sites,
            foreign,
            counties_by_employment,
        }
    }

    // Workplaces rotate the same finite counterpart roster independently.
    fn secondary_candidates(
        &self,
        location: EconomicLocation,
        buyer: SiteId,
    ) -> Result<impl Iterator<Item = EconomicLocation> + '_> {
        let county_buyer = matches!(location, EconomicLocation::County(_));
        let order = if county_buyer {
            &self.foreign
        } else {
            &self.counties_by_employment
        };
        let rotation = if county_buyer && !order.is_empty() {
            let bytes = buyer.as_bytes();
            usize::try_from(u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]))
                .map_err(|_| NationalOpeningError::Bounds)?
                % order.len()
        } else {
            0
        };
        let (before, after) = order.split_at(rotation);
        Ok(after.iter().chain(before).copied())
    }
}

pub(super) fn wire(builder: &mut Builder<'_>) -> Result<()> {
    let retailers = local_retailers(builder)?;
    let mut sites_by_good = BTreeMap::<_, BTreeMap<_, Vec<_>>>::new();
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
                    target_stock: super::quantity(
                        actor.planned_batches,
                        recipe.output_units_per_batch,
                    )?,
                },
                CommodityKind::PeriodService { .. } => PricePolicy::ServiceResponsive {
                    minimum: price.minimum,
                    maximum: price.maximum,
                    step: price.step,
                },
            },
        });
        if actor.employed > 0 {
            sites_by_good
                .entry((good.good_id, good.unit_id))
                .or_default()
                .entry(actor.location)
                .or_default()
                .push(actor.site_id);
        }
    }
    let providers = sites_by_good
        .into_iter()
        .map(|(good, sites)| (good, ProviderLocations::new(sites, &builder.actors)))
        .collect();
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
    super::equipment::wire(builder, &providers, &mut network, &mut preferences)?;
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

// Only missing retailer locations need these indices. Actor locations/employment
// and staffing row positions do not change while retail roles are installed.
struct RetailFallbackIndices {
    sites: BTreeMap<EconomicLocation, SiteId>,
    staffing: BTreeMap<SiteId, usize>,
}
impl RetailFallbackIndices {
    fn new(actors: &BTreeMap<SiteId, ActorContext>, rows: &[ResidentStaffingPoolSeed]) -> Self {
        let mut sites = BTreeMap::new();
        for actor in actors.values().filter(|actor| actor.employed > 0) {
            let chosen = sites.entry(actor.location).or_insert(actor.site_id);
            if (actor.employed, std::cmp::Reverse(actor.site_id))
                > (actors[chosen].employed, std::cmp::Reverse(*chosen))
            {
                *chosen = actor.site_id;
            }
        }
        let mut staffing = BTreeMap::new();
        for (index, row) in rows.iter().enumerate() {
            // Preserve iter_mut().find's first matching row, including malformed duplicates.
            staffing.entry(row.pool.site_id()).or_insert(index);
        }
        Self { sites, staffing }
    }
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
    let mut resident_totals = BTreeMap::<EconomicLocation, (u64, u64)>::new();
    for row in &builder.opening.households {
        let totals = resident_totals.entry(row.location).or_default();
        totals.0 = totals
            .0
            .checked_add(row.persons)
            .ok_or(NationalOpeningError::Arithmetic)?;
        totals.1 = totals
            .1
            .checked_add(row.households)
            .ok_or(NationalOpeningError::Arithmetic)?;
    }
    let missing: Vec<_> = resident_totals
        .into_iter()
        .filter(|(location, _)| !selected.contains_key(location))
        .map(|(location, (persons, households))| (location, persons, households))
        .collect();
    if missing.is_empty() {
        return Ok(selected);
    }
    let fallback = RetailFallbackIndices::new(&builder.actors, &builder.opening.staffing);
    for (location, persons, households) in missing {
        let site = fallback
            .sites
            .get(&location)
            .copied()
            .ok_or(NationalOpeningError::MissingObservation)?;
        let mut identity = b"NationalMerchantHandlingV1\0".to_vec();
        identity.extend_from_slice(&site.as_bytes());
        let merchant = MerchantSeed {
            role: MerchantRole::Retail,
            capacity_id: CorridorId::from_bytes(content_digest::sha256_of(&identity)),
            labor_unit_id: builder.labor_unit,
            handling: actors::handling_requirements(builder)?,
        };
        let retail_hours = retail_hours(builder, persons, households)?;
        reserve_retail_labor(builder, site, retail_hours)?;
        builder.site_mut(site)?.merchant = Some(merchant);
        let index = *fallback
            .staffing
            .get(&site)
            .ok_or(NationalOpeningError::Identity)?;
        let staffing = builder
            .opening
            .staffing
            .get_mut(index)
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

fn reserve_retail_labor(builder: &mut Builder<'_>, site: SiteId, retail_hours: u64) -> Result<()> {
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
        let available = super::quantity(actor.employed, builder.policy.work_hours_per_person)?;
        actor.planned_batches =
            available.saturating_sub(retail_hours) / recipe.labor_hours_per_batch;
        let output_buffer = if matches!(
            builder
                .policy
                .commodities
                .get(&recipe.output)
                .ok_or(NationalOpeningError::Policy)?
                .kind,
            CommodityKind::Storable { .. }
        ) {
            super::quantity(actor.planned_batches, recipe.output_units_per_batch)?
        } else {
            0
        };
        let row = builder.opening.sites[*builder
            .sites
            .get(&site)
            .ok_or(NationalOpeningError::Identity)?]
        .processes
        .iter_mut()
        .find(|p| p.process_id == process)
        .ok_or(NationalOpeningError::Identity)?;
        row.planned_batches = actor.planned_batches;
        row.output_buffer = output_buffer;
    }
    Ok(())
}

/// The hours a fallback retailer reserves: for each shop good its units of needs and of wants (the
/// scenario's rows, unscaled), handled in hours rounded up to a whole block.
fn retail_hours(builder: &Builder<'_>, persons: u64, households: u64) -> Result<u64> {
    let policy = builder.policy;
    let rows = policy
        .household_needs
        .iter()
        .map(|need| (&need.key, need.basis, need.units_per_basis))
        .chain(
            policy
                .household_wants
                .iter()
                .map(|want| (&want.key, want.basis, want.units_per_basis)),
        );
    let mut units = BTreeMap::<&String, u64>::new();
    for (key, basis, per_basis) in rows {
        if !matches!(builder.commodity(key)?.kind, CommodityKind::Storable { .. }) {
            continue;
        }
        let count = match basis {
            HouseholdNeedBasis::Persons => persons,
            HouseholdNeedBasis::Households => households,
        };
        let total = units.entry(key).or_default();
        *total = total
            .checked_add(super::quantity(count, per_basis)?)
            .ok_or(NationalOpeningError::Arithmetic)?;
    }
    units.into_iter().try_fold(0_u64, |hours, (key, total)| {
        let block = handling(policy, key)?;
        let needed = u128::from(total) * u128::from(block.hours);
        let rounded = u64::try_from(needed.div_ceil(u128::from(block.units)))
            .map_err(|_| NationalOpeningError::Arithmetic)?;
        hours
            .checked_add(rounded)
            .ok_or(NationalOpeningError::Arithmetic)
    })
}

/// What an account buys of one good in a period: its need and its wants.
struct Purchase {
    key: String,
    need: u64,
    want: u64,
}

/// An account's purchases, needs first in their order and then the goods only wanted; a want of
/// the households of a collective residence is left out, as a need of theirs is.
fn purchases(
    builder: &Builder<'_>,
    household: &EconomicHouseholdSeed,
    scale_bps: Option<u32>,
) -> Result<Vec<Purchase>> {
    let collective = household.kind == HouseholdKind::CollectiveResidence;
    let count = |basis| match basis {
        HouseholdNeedBasis::Persons => household.persons,
        HouseholdNeedBasis::Households => household.households,
    };
    let mut rows: Vec<Purchase> = Vec::new();
    let mut add = |key: &str, need: u64, want: u64| -> Result<()> {
        if let Some(row) = rows.iter_mut().find(|row| row.key == key) {
            row.need = row
                .need
                .checked_add(need)
                .ok_or(NationalOpeningError::Arithmetic)?;
            row.want = row
                .want
                .checked_add(want)
                .ok_or(NationalOpeningError::Arithmetic)?;
        } else {
            rows.push(Purchase {
                key: key.to_owned(),
                need,
                want,
            });
        }
        Ok(())
    };
    for need in &builder.policy.household_needs {
        if collective && need.basis == HouseholdNeedBasis::Households {
            continue;
        }
        add(
            &need.key,
            super::quantity(count(need.basis), need.units_per_basis)?,
            0,
        )?;
    }
    for want in &builder.policy.household_wants {
        if collective && want.basis == HouseholdNeedBasis::Households {
            continue;
        }
        let per_basis = templates::scaled_units(want, scale_bps)?;
        add(&want.key, 0, super::quantity(count(want.basis), per_basis)?)?;
    }
    Ok(rows)
}

/// The purchase rows of the opening, needs and wants together, stay within the engine's bound, and so
/// do the wants.
fn check_bounds(purchase_rows: usize, wants: usize) -> Result<()> {
    if purchase_rows > MAX_HOUSEHOLD_NEEDS || wants > MAX_HOUSEHOLD_WANTS {
        return Err(NationalOpeningError::Bounds);
    }
    Ok(())
}

fn households(
    builder: &mut Builder<'_>,
    retailers: &BTreeMap<EconomicLocation, SiteId>,
    providers: &Providers,
    network: &mut Network<'_>,
    preferences: &mut Preferences,
) -> Result<()> {
    let households = builder.opening.households.clone();
    let scales = templates::luxury_scales(builder)?;
    let domain_retailers = representative_retailers(builder)?;
    let mut retail_requirements = BTreeMap::<(SiteId, String), u64>::new();
    for household in households {
        let domain = builder.domain(
            AccountId::Household(household.principal_id),
            household.location,
        )?;
        let retailer = *domain_retailers
            .get(&domain)
            .or_else(|| retailers.get(&household.location))
            .ok_or(NationalOpeningError::Identity)?;
        for row in purchases(
            builder,
            &household,
            scales.get(&household.principal_id).copied(),
        )? {
            let good = builder.commodity(&row.key)?.clone();
            let required = row
                .need
                .checked_add(row.want)
                .ok_or(NationalOpeningError::Arithmetic)?;
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
            // A want is used where it is bought: it has no pantry, so no stock to hold.
            builder
                .opening
                .policies
                .household_purchases
                .push(HouseholdPurchasePolicy {
                    principal_id: household.principal_id,
                    retailer_site_id: seller,
                    good_id: good.good_id,
                    unit_id: good.unit_id,
                    target_closing_stock: if good.cargo.is_some() { row.need } else { 0 },
                    maximum_purchase: super::quantity(
                        required,
                        builder.policy.retailer_buffer_periods,
                    )?,
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
            let total = retail_requirements.entry((retailer, row.key)).or_default();
            *total = total
                .checked_add(required)
                .ok_or(NationalOpeningError::Arithmetic)?;
        }
    }
    check_bounds(builder.opening.policies.household_purchases.len(), 0)?;
    // Supply and fractional sourcing are calculated once from the location total.
    for ((retailer, key), required) in retail_requirements {
        retail_stock(builder, retailer, &key, required)?;
        procure(
            builder,
            providers,
            network,
            preferences,
            ProcurementNeed {
                buyer: retailer,
                key: &key,
                required,
                buffer_periods: builder.policy.retailer_buffer_periods,
            },
        )?;
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
    let handling_charge = handling_charge(handling(builder.policy, key)?, actor.wage)?;
    let unit_price = super::sum_amount(price.opening, handling_charge)?;
    let minimum = super::sum_amount(price.minimum, handling_charge)?;
    let maximum = super::sum_amount(price.maximum, handling_charge)?;
    let stock = super::quantity(required, builder.policy.retailer_buffer_periods)?;
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
    let working_cash = super::amount(
        builder.policy.working_capital_periods,
        super::amount(required, price.opening)?,
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
        existing.total_cost = super::sum_amount(existing.total_cost, opening_stock.total_cost)?;
    } else {
        site.opening_stock.push(opening_stock);
    }
    site.opening_cash = super::sum_amount(site.opening_cash, working_cash)?;

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
        let maximum_batches = super::quantity(actor.force, builder.policy.work_hours_per_person)?
            / recipe.labor_hours_per_batch;
        for (key, coefficient) in recipe.inputs {
            let good = builder.commodity(&key)?.clone();
            if good.price.is_none() {
                continue;
            } // finite deposit is not bought or reproduced
            let required = super::quantity(maximum_batches, coefficient)?;
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
    let locations = &locations.sites;
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
pub(super) struct ProcurementNeed<'a> {
    pub(super) buyer: SiteId,
    pub(super) key: &'a str,
    pub(super) required: u64,
    pub(super) buffer_periods: u64,
}

pub(super) fn primary_supplier(
    locations: &ProviderLocations,
    network: &mut Network<'_>,
    preferences: &mut Preferences,
    location: EconomicLocation,
    buyer: SiteId,
    good: &GameCommodity,
) -> Result<Option<SiteId>> {
    let cargo = good.cargo.ok_or(NationalOpeningError::Policy)?;
    let locations = &locations.sites;
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

pub(super) fn secondary_supplier(
    builder: &Builder<'_>,
    locations: &ProviderLocations,
    network: &mut Network<'_>,
    buyer: SiteId,
    cargo: CargoClass,
) -> Result<Option<SiteId>> {
    let location = builder
        .actors
        .get(&buyer)
        .ok_or(NationalOpeningError::Identity)?
        .location;
    let mut secondary = None;
    for candidate in locations.secondary_candidates(location, buyer)? {
        if network.path(candidate, location, cargo)?.is_some() {
            secondary = locations.sites[&candidate]
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

/// The retail handling of a shop good: schema 7's one figure for every good, in blocks of one unit, or
/// schema 8's row of the good.
pub(super) fn handling(policy: &NationalGamePolicy, key: &str) -> Result<GameHandling> {
    if let Some(hours) = policy.handling_hours_per_unit {
        return Ok(GameHandling { hours, units: 1 });
    }
    policy
        .commodities
        .get(key)
        .and_then(|good| good.handling)
        .ok_or(NationalOpeningError::Policy)
}

/// The retail charge of a unit, in micros: `ceil(hours x wage / units)`, the engine's cost of a unit.
pub(super) fn handling_charge(handling: GameHandling, wage: Currency) -> Result<Currency> {
    let hours = i128::from(handling.hours)
        .checked_mul(wage.micro_units())
        .ok_or(NationalOpeningError::Arithmetic)?;
    let units = i128::from(handling.units);
    if units == 0 {
        return Err(NationalOpeningError::Policy);
    }
    let whole = hours.div_euclid(units);
    let charge = if hours.rem_euclid(units) == 0 {
        whole
    } else {
        whole + 1
    };
    Ok(Currency::from_micro_units(charge))
}

/// A buyer's share, in basis points, bought from the second supplier of a good: schema 7's one cap,
/// or schema 8's share of a domestic buyer's imports and of a foreign buyer's region (Task 5
/// replaces this).
pub(super) fn abroad_bps(builder: &Builder<'_>, buyer: SiteId, key: &str) -> Result<u16> {
    match &builder.policy.markets.procurement {
        GameProcurement::Single(bps) => Ok(*bps),
        GameProcurement::ByProduct { import_bps } => {
            let location = builder
                .actors
                .get(&buyer)
                .ok_or(NationalOpeningError::Identity)?
                .location;
            let profile = match location {
                EconomicLocation::County(_) => None,
                EconomicLocation::Foreign(counterpart) => Some(
                    &builder
                        .policy
                        .counterparts
                        .get(&counterpart)
                        .ok_or(NationalOpeningError::Policy)?
                        .export_bps,
                ),
                EconomicLocation::Dependency(_) => {
                    Some(&builder.policy.dependency.profile.export_bps)
                }
            };
            let table = match profile {
                None => Some(import_bps),
                Some(export) => export.as_ref(),
            };
            table
                .and_then(|rows| rows.get(key))
                .copied()
                .ok_or(NationalOpeningError::Policy)
        }
    }
}

pub(super) fn procure(
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
        u64::try_from(u128::from(required) * u128::from(abroad_bps(builder, buyer, key)?) / 10_000)
            .map_err(|_| NationalOpeningError::Arithmetic)?
    } else {
        0
    };
    let domestic_cap = required
        .checked_sub(foreign_cap)
        .ok_or(NationalOpeningError::Arithmetic)?;
    let target = super::quantity(required, buffer_periods)?;
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
pub(super) fn payroll(builder: &Builder<'_>, site: SiteId) -> Result<Currency> {
    let actor = builder
        .actors
        .get(&site)
        .ok_or(NationalOpeningError::Identity)?;
    super::amount(
        super::quantity(actor.employee_persons, builder.policy.work_hours_per_person)?,
        actor.wage,
    )
}

fn representative_retailers(builder: &Builder<'_>) -> Result<BTreeMap<FinancialDomainId, SiteId>> {
    let mut domain_retailers = BTreeMap::new();
    for actor in builder
        .actors
        .values()
        .filter(|a| a.employed > 0 && a.function == EconomicFunction::DistributionTransport)
    {
        let domain = builder.domain(AccountId::Site(actor.site_id), actor.location)?;
        let selected = domain_retailers.entry(domain).or_insert(actor.site_id);
        if (actor.employed, std::cmp::Reverse(actor.site_id))
            > (
                builder.actors[selected].employed,
                std::cmp::Reverse(*selected),
            )
        {
            *selected = actor.site_id;
        }
    }
    Ok(domain_retailers)
}

#[cfg(test)]
mod retailer_index_controls {
    use super::*;
    use babylon_graph::stable_element::StableElementKey;
    use babylon_kernel::geography::CountyGeoid;
    use babylon_material_circuit::{StaffingPolicy, StaffingPoolId};

    fn actor(id: u8, county: &str, employed: u64) -> ActorContext {
        ActorContext {
            site_id: SiteId::from_bytes([id; 32]),
            function: EconomicFunction::CapitalGoods,
            source_ownership: None,
            location: EconomicLocation::domestic_county(
                CountyGeoid::try_from(county).expect("the fixture value fits the target range"),
            )
            .expect("the fixture geoid names a domestic county"),
            employed,
            employee_persons: employed,
            force: employed,
            wage: Currency::from_micro_units(1),
            price_scale_bps: 10_000,
            planned_batches: 1,
            process_id: None,
        }
    }
    fn staffing(site: SiteId, id: u8) -> ResidentStaffingPoolSeed {
        ResidentStaffingPoolSeed {
            workplace: StableElementKey::Node {
                scenario: "index-control".into(),
                local_name: "workplace".into(),
            },
            pool: StaffingPoolBinding::try_new(
                StaffingPoolId::from_bytes([id; 32]),
                site,
                UnitId::from_bytes([3; 32]),
                2,
                StaffingPolicy::one_period(1).expect("the one-period fixture advances"),
                vec![StaffingWorkSource::MerchantHandling(site)],
            )
            .expect("the authored fixture satisfies the constructor invariants"),
            previous_unretained_hours: 0,
            members: vec![],
        }
    }
    #[test]
    fn secondary_candidates_preserve_buyer_rotation_and_county_ties() {
        use babylon_kernel::economic_location::{ForeignCounterpart, UsDependency};

        let first = actor(1, "26001", 30);
        let second = actor(2, "26003", 30);
        let third = actor(3, "26163", 40);
        let counties = [first.location, second.location, third.location];
        let canada = EconomicLocation::Foreign(ForeignCounterpart::Canada);
        let mexico = EconomicLocation::Foreign(ForeignCounterpart::Mexico);
        let japan = EconomicLocation::Foreign(ForeignCounterpart::Japan);
        let dependency = EconomicLocation::Dependency(UsDependency::Guam);
        let foreign_rows = [canada, mexico, japan, dependency]
            .into_iter()
            .zip([4, 5, 6, 7])
            .map(|(location, id)| ActorContext {
                location,
                ..actor(id, "26163", 10)
            });
        let actors: BTreeMap<_, _> = [first, second, third]
            .into_iter()
            .chain(foreign_rows)
            .map(|row| (row.site_id, row))
            .collect();
        let sites = actors
            .values()
            .map(|row| (row.location, vec![row.site_id]))
            .collect();
        let providers = ProviderLocations::new(sites, &actors);
        let order = |location, offset| {
            let mut bytes = [0; 32];
            bytes[3] = offset;
            providers
                .secondary_candidates(location, SiteId::from_bytes(bytes))
                .expect("the fixture rotation fits the host index")
                .collect::<Vec<_>>()
        };
        assert_eq!(order(counties[0], 1), [mexico, japan, canada]);
        assert_eq!(order(counties[0], 2), [japan, canada, mexico]);
        assert_eq!(order(counties[0], 4), [mexico, japan, canada]);
        assert_eq!(order(japan, 2), [counties[2], counties[0], counties[1]]);
        assert_eq!(
            order(dependency, 1),
            [counties[2], counties[0], counties[1]]
        );
    }

    #[test]
    fn fallback_indices_match_original_location_selection_and_first_pool() {
        let rows = [
            actor(9, "26163", 10),
            actor(2, "26163", 10),
            actor(1, "26163", 0),
            actor(4, "26001", 3),
            actor(5, "26001", 7),
            actor(6, "26003", 0),
        ];
        let actors: BTreeMap<_, _> = rows.into_iter().map(|row| (row.site_id, row)).collect();
        let site = SiteId::from_bytes([2; 32]);
        let pools = vec![
            staffing(site, 7),
            staffing(site, 8),
            staffing(SiteId::from_bytes([5; 32]), 9),
        ];
        let indices = RetailFallbackIndices::new(&actors, &pools);
        for county in ["26163", "26001", "26003"] {
            let location = actor(99, county, 0).location;
            let original = actors
                .values()
                .filter(|row| row.location == location && row.employed > 0)
                .max_by_key(|row| (row.employed, std::cmp::Reverse(row.site_id)))
                .map(|row| row.site_id);
            assert_eq!(indices.sites.get(&location).copied(), original);
        }
        assert_eq!(indices.sites[&actor(99, "26163", 0).location], site);
        for row in &pools {
            let original = pools
                .iter()
                .position(|pool| pool.pool.site_id() == row.pool.site_id())
                .expect("the fixture sequence holds the addressed position");
            assert_eq!(indices.staffing[&row.pool.site_id()], original);
        }
        let empty = RetailFallbackIndices::new(&BTreeMap::new(), &[]);
        assert!(empty.sites.is_empty() && empty.staffing.is_empty());
    }

    #[test]
    fn a_handling_block_sets_the_retail_charge() {
        let charge = |hours, units, wage: i128| {
            handling_charge(
                GameHandling { hours, units },
                Currency::from_micro_units(wage),
            )
            .map(Currency::micro_units)
        };
        // Three hours for forty units at $30: 90,000,000 / 40 = 2,250,000 micros.
        assert_eq!(charge(3, 40, 30_000_000), Ok(2_250_000));
        // Rounded up to a whole micro; a block of one unit is the hours times the wage.
        assert_eq!(charge(1, 3, 10), Ok(4));
        assert_eq!(charge(2, 1, 30_000_000), Ok(60_000_000));
    }

    #[test]
    fn too_many_purchase_rows_are_refused() {
        assert_eq!(
            check_bounds(MAX_HOUSEHOLD_NEEDS, MAX_HOUSEHOLD_WANTS),
            Ok(())
        );
        assert_eq!(
            check_bounds(MAX_HOUSEHOLD_NEEDS + 1, 0),
            Err(NationalOpeningError::Bounds)
        );
        assert_eq!(
            check_bounds(0, MAX_HOUSEHOLD_WANTS + 1),
            Err(NationalOpeningError::Bounds)
        );
    }
}
