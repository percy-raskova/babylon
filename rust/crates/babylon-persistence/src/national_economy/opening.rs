//! Regenerate one national opening from supplied source captures and Designed policy.
//! This module owns no mutable runtime or filesystem fallback.

mod actors;
mod equipment;
mod external;
mod financial;
mod markets;
mod routes;
mod templates;

use super::{GameCommodity, NationalGamePolicy};
use crate::{
    economic_catalog::{
        CatalogAccounting, CatalogCapacity, CatalogLogistics, CatalogOpeningOrders,
        CatalogPolicies, EconomicOpening, EconomicSiteSeed,
    },
    national_cohorts::NationalCohortReference,
    national_counties::NationalCountyReference,
    national_resident_allocation::{allocate_home_county, AllocationError},
    national_resident_workforce::NationalResidentWorkforceReference,
    national_transport::NationalTransportReference,
    world_reference::WorldReference,
};
use babylon_kernel::{
    currency::Currency,
    economic_identity::{EconomicFunction, QcewOwnership},
    economic_location::EconomicLocation,
};
use babylon_material_circuit::{
    FinancialInstitutions, GoodId, LogisticsNodeId, ProcessId, ReplenishmentPolicy,
    RollingProcessSupply, SellerOffer, SiteId, UnitId,
};
use std::collections::BTreeMap;

/// Specific opening refusals; no source absence becomes an invented observation.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum NationalOpeningError {
    SourceScope,
    MissingObservation,
    Policy,
    Identity,
    Route,
    Bounds,
    Arithmetic,
    Workforce(AllocationError),
}
impl std::fmt::Display for NationalOpeningError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "national economic opening refused: {self:?}")
    }
}
impl std::error::Error for NationalOpeningError {}
type Result<T> = std::result::Result<T, NationalOpeningError>;

pub(super) const FUNCTIONS: [EconomicFunction; 10] = [
    EconomicFunction::BusinessServices,
    EconomicFunction::CapitalGoods,
    EconomicFunction::ConstructionHousing,
    EconomicFunction::DistributionTransport,
    EconomicFunction::EnergyUtilities,
    EconomicFunction::Extraction,
    EconomicFunction::Food,
    EconomicFunction::HouseholdServices,
    EconomicFunction::Manufacturing,
    EconomicFunction::PublicProvisioning,
];

/// Initialization-only facts. Durable people and plans belong to graph/material state.
#[derive(Clone, Debug)]
struct ActorContext {
    site_id: SiteId,
    function: EconomicFunction,
    source_ownership: Option<QcewOwnership>,
    location: EconomicLocation,
    employed: u64,
    employee_persons: u64,
    force: u64,
    wage: Currency,
    price_scale_bps: u16,
    planned_batches: u64,
    process_id: Option<ProcessId>,
}

struct Builder<'a> {
    policy: &'a NationalGamePolicy,
    transport: &'a NationalTransportReference,
    labor_unit: UnitId,
    opening: EconomicOpening,
    actors: BTreeMap<SiteId, ActorContext>,
    sites: BTreeMap<SiteId, usize>,
    logistics_nodes: BTreeMap<EconomicLocation, LogisticsNodeId>,
    offer_indices: BTreeMap<(SiteId, GoodId, UnitId), usize>,
    procurement_indices: BTreeMap<(SiteId, SiteId, GoodId, UnitId), usize>,
}

/// Initialize every captured county and bounded foreign/dependency counterpart.
/// Households and workplace members are cohorts, never individual decision agents.
/// # Errors
/// Refuses contradictory supplied captures, invalid policy, unavailable required
/// observations, missing physical routes and checked quantity/currency overflow.
pub fn build_national_opening(
    counties: &NationalCountyReference,
    cohorts: &NationalCohortReference,
    residents: &NationalResidentWorkforceReference,
    world: &WorldReference,
    transport: &NationalTransportReference,
    policy: &NationalGamePolicy,
) -> Result<EconomicOpening> {
    if u64::from(transport.period_days()) != policy.period_days {
        return Err(NationalOpeningError::Policy);
    }
    let allocation = allocate_home_county(counties, cohorts, residents, policy)
        .map_err(NationalOpeningError::Workforce)?;
    let mut builder = Builder::new(policy, transport)?;
    actors::domestic(&mut builder, counties, &allocation)?;
    external::world(&mut builder, world)?;
    markets::wire(&mut builder)?;
    financial::wire(&mut builder, &allocation)?;
    routes::finish(&mut builder)?;
    builder
        .opening
        .sites
        .sort_unstable_by_key(|site| site.site_id);
    builder
        .opening
        .households
        .sort_unstable_by_key(|row| row.principal_id);
    builder
        .opening
        .staffing
        .sort_unstable_by_key(|row| row.pool.pool_id());
    builder
        .opening
        .employment
        .sort_unstable_by_key(|row| row.member_id);
    Ok(builder.opening)
}

impl<'a> Builder<'a> {
    fn new(
        policy: &'a NationalGamePolicy,
        transport: &'a NationalTransportReference,
    ) -> Result<Self> {
        let labor_unit = UnitId::from_bytes(babylon_kernel::content_digest::sha256_of(
            b"NationalLaborHourV1\0",
        ));
        let (commodities, commodity_labels, recipes, household_templates) =
            templates::compile(policy, labor_unit)?;
        Ok(Self {
            policy,
            transport,
            labor_unit,
            actors: BTreeMap::new(),
            sites: BTreeMap::new(),
            logistics_nodes: transport
                .nodes()
                .iter()
                .filter(|node| {
                    matches!(
                        node.kind(),
                        crate::national_transport::TransportNodeKind::County
                            | crate::national_transport::TransportNodeKind::Foreign
                            | crate::national_transport::TransportNodeKind::Dependency
                    )
                })
                .map(|node| (node.location(), actors::node_id(node.id())))
                .collect(),
            offer_indices: BTreeMap::new(),
            procurement_indices: BTreeMap::new(),
            opening: EconomicOpening {
                commodity_labels,
                commodities,
                recipes,
                household_templates,
                sites: vec![],
                households: vec![],
                staffing: vec![],
                employment: vec![],
                accounting: CatalogAccounting::Monetary,
                institutional_cash: vec![],
                institutions: FinancialInstitutions::empty(),
                equity: vec![],
                equipment: vec![],
                capacity: CatalogCapacity::Rolling(RollingProcessSupply::CapturedNameplate(vec![])),
                policies: CatalogPolicies {
                    offers: vec![],
                    replenishment: vec![],
                    household_purchases: vec![],
                    service_inputs: vec![],
                    service_connections: vec![],
                },
                logistics: CatalogLogistics {
                    supplier_routes: vec![],
                    route_stages: vec![],
                    memberships: vec![],
                    shared_capacity: vec![],
                },
                orders: CatalogOpeningOrders {
                    principals: vec![],
                    goods: vec![],
                    final_demand: vec![],
                },
                maintenance: None,
            },
        })
    }
    fn commodity(&self, key: &str) -> Result<&GameCommodity> {
        self.policy
            .commodities
            .get(key)
            .ok_or(NationalOpeningError::Policy)
    }
    fn add_site(&mut self, context: ActorContext, site: EconomicSiteSeed) -> Result<()> {
        let id = context.site_id;
        if id != site.site_id || self.actors.contains_key(&id) {
            return Err(NationalOpeningError::Identity);
        }
        self.sites.insert(id, self.opening.sites.len());
        self.opening.sites.push(site);
        self.actors.insert(id, context);
        Ok(())
    }
    fn set_offer(&mut self, offer: SellerOffer) {
        let key = (offer.site_id, offer.good_id, offer.unit_id);
        if let Some(index) = self.offer_indices.get(&key) {
            self.opening.policies.offers[*index] = offer;
        } else {
            self.offer_indices
                .insert(key, self.opening.policies.offers.len());
            self.opening.policies.offers.push(offer);
        }
    }
    fn add_procurement(&mut self, row: ReplenishmentPolicy) -> Result<()> {
        let key = (
            row.buyer_site_id,
            row.supplier_site_id,
            row.good_id,
            row.unit_id,
        );
        if let Some(index) = self.procurement_indices.get(&key) {
            let existing = &mut self.opening.policies.replenishment[*index];
            if existing.cash_floor != row.cash_floor {
                return Err(NationalOpeningError::Policy);
            }
            existing.target_stock = existing
                .target_stock
                .checked_add(row.target_stock)
                .ok_or(NationalOpeningError::Arithmetic)?;
            existing.maximum_purchase = existing
                .maximum_purchase
                .checked_add(row.maximum_purchase)
                .ok_or(NationalOpeningError::Arithmetic)?;
        } else {
            self.procurement_indices
                .insert(key, self.opening.policies.replenishment.len());
            self.opening.policies.replenishment.push(row);
        }
        Ok(())
    }
    fn site_mut(&mut self, id: SiteId) -> Result<&mut EconomicSiteSeed> {
        let index = *self.sites.get(&id).ok_or(NationalOpeningError::Identity)?;
        self.opening
            .sites
            .get_mut(index)
            .ok_or(NationalOpeningError::Identity)
    }
}

fn quantity(a: u64, b: u64) -> Result<u64> {
    a.checked_mul(b).ok_or(NationalOpeningError::Arithmetic)
}
fn amount(quantity: u64, price: Currency) -> Result<Currency> {
    price
        .micro_units()
        .checked_mul(i128::from(quantity))
        .map(Currency::from_micro_units)
        .ok_or(NationalOpeningError::Arithmetic)
}
fn sum_amount(left: Currency, right: Currency) -> Result<Currency> {
    left.checked_add(right)
        .map_err(|_| NationalOpeningError::Arithmetic)
}
