//! Shared gram capacity from authenticated opening budgets and committed movements.

mod aid;
mod rolling;

use super::{
    outbound::{completed_facts, identity, same_rows, OutboundFact},
    ProductionProjectionError,
};
use crate::{
    michigan_economy::digest_hex,
    production_observation::CompletedProductionFreightCapacity,
    production_observation::ProductionCapacityKind,
    production_observation::ProductionFreightCapacityAccount,
    production_observation::ProductionFreightCapacityOrder,
    production_observation::{
        FreightOrderRegistry, ProductionFreightOrderDefinition, ProductionFreightReservation,
    },
};
use babylon_material_circuit::{
    CorridorId, MaterialCircuitState, RouteId, RouteStage, SiteId, SupplierTransport,
};
use babylon_tick::material_world::MaterialTickReceipts;
use std::collections::{BTreeMap, BTreeSet};

type Result<T> = std::result::Result<T, ProductionProjectionError>;
type CapacityKey = (CorridorId, u64);
type Budgets = BTreeMap<CapacityKey, u64>;
type Reservations = BTreeMap<CapacityKey, ReservationOrders>;
type ReservationInput = (Reservations, Vec<ProductionFreightCapacityOrder>);
struct CompletedReservations {
    rows: BTreeMap<CapacityKey, RawReservation>,
    orders: Vec<ProductionFreightCapacityOrder>,
}
struct OrderDefinitions {
    pending: Vec<Option<ProductionFreightCapacityOrder>>,
    references: Vec<Option<String>>,
}
impl OrderDefinitions {
    fn new(orders: Vec<ProductionFreightCapacityOrder>) -> Self {
        let references = vec![None; orders.len()];
        Self {
            pending: orders.into_iter().map(Some).collect(),
            references,
        }
    }
    fn reference(
        &mut self,
        ordinal: usize,
        definitions: &mut FreightOrderRegistry,
    ) -> Result<String> {
        let reference = self
            .references
            .get_mut(ordinal)
            .ok_or(ProductionProjectionError::State)?;
        if let Some(id) = reference {
            return Ok(id.clone());
        }
        let order = self
            .pending
            .get_mut(ordinal)
            .and_then(Option::take)
            .ok_or(ProductionProjectionError::State)?;
        let id = definitions
            .intern(order)
            .map_err(|_| ProductionProjectionError::State)?;
        *reference = Some(id.clone());
        Ok(id)
    }
}
#[derive(Clone)]
struct RawReservation {
    reservation_period: u64,
    opening_available_grams: u64,
    newly_reserved_grams: u64,
    remaining_available_grams: u64,
    orders: Vec<usize>,
    support_orders: Vec<crate::production_observation::ProductionAidCapacityOrder>,
}
impl RawReservation {
    fn factor(
        self,
        definitions: &mut FreightOrderRegistry,
        order_definitions: &mut OrderDefinitions,
    ) -> Result<ProductionFreightReservation> {
        let orders = self
            .orders
            .into_iter()
            .map(|ordinal| order_definitions.reference(ordinal, definitions))
            .collect::<Result<Vec<_>>>()?;
        Ok(ProductionFreightReservation {
            reservation_period: self.reservation_period,
            opening_available_grams: self.opening_available_grams,
            newly_reserved_grams: self.newly_reserved_grams,
            remaining_available_grams: self.remaining_available_grams,
            orders,
            support_orders: self.support_orders,
        })
    }
}

#[derive(Default)]
struct ReservationOrders {
    commercial: Vec<usize>,
    support: Vec<crate::production_observation::ProductionAidCapacityOrder>,
}

#[derive(Default)]
struct Participants {
    routes: BTreeSet<RouteId>,
    merchants: BTreeSet<SiteId>,
}

struct RouteIndex<'a> {
    stages: BTreeMap<RouteId, Vec<&'a RouteStage>>,
    memberships: BTreeMap<(RouteId, u16), BTreeSet<CorridorId>>,
}
impl<'a> RouteIndex<'a> {
    fn new(state: &'a MaterialCircuitState) -> Result<Self> {
        let mut memberships = BTreeMap::<_, BTreeSet<_>>::new();
        for row in &state.route_stage_capacities {
            if !memberships
                .entry((row.route_id, row.stage_index))
                .or_default()
                .insert(row.corridor_id)
            {
                return Err(ProductionProjectionError::State);
            }
        }
        let mut stages = BTreeMap::<_, Vec<_>>::new();
        for row in &state.route_stages {
            if !memberships.contains_key(&(row.route_id, row.stage_index)) {
                return Err(ProductionProjectionError::State);
            }
            stages.entry(row.route_id).or_default().push(row);
        }
        let count = stages.values().map(Vec::len).sum::<usize>();
        if count != memberships.len() {
            return Err(ProductionProjectionError::State);
        }
        for rows in stages.values_mut() {
            rows.sort_unstable_by_key(|r| r.stage_index);
            if rows
                .iter()
                .enumerate()
                .any(|(i, r)| usize::from(r.stage_index) != i || r.travel_periods == 0)
            {
                return Err(ProductionProjectionError::State);
            }
        }
        Ok(Self {
            stages,
            memberships,
        })
    }
}

fn budgets(state: &MaterialCircuitState) -> Result<Budgets> {
    let mut rows = BTreeMap::new();
    for row in &state.corridor_capacities {
        if row.period < state.period
            || rows
                .insert((row.corridor_id, row.period), row.available_grams)
                .is_some()
        {
            return Err(ProductionProjectionError::State);
        }
    }
    Ok(rows)
}

fn participants(state: &MaterialCircuitState) -> Result<BTreeMap<CorridorId, Participants>> {
    let mut result = BTreeMap::<CorridorId, Participants>::new();
    let index = RouteIndex::new(state)?;
    for ((route, _), ids) in index.memberships {
        for id in ids {
            result.entry(id).or_default().routes.insert(route);
        }
    }
    for merchant in &state.merchants {
        let row = result.entry(merchant.capacity_id).or_default();
        if !row.routes.is_empty()
            || !row.merchants.insert(merchant.site_id)
            || row.merchants.len() != 1
        {
            return Err(ProductionProjectionError::State);
        }
    }
    if state
        .corridor_capacities
        .iter()
        .any(|row| !result.contains_key(&row.corridor_id))
    {
        return Err(ProductionProjectionError::State);
    }
    Ok(result)
}

#[cfg(test)]
pub(super) fn project_freight_capacity_accounts(
    catalog: &crate::michigan_material::MichiganMaterialCatalog,
    state: &MaterialCircuitState,
    opening: Option<&MaterialCircuitState>,
    receipt: Option<&MaterialTickReceipts>,
) -> Result<(
    Vec<ProductionFreightCapacityAccount>,
    Vec<ProductionFreightOrderDefinition>,
)> {
    project_with_labels(state, opening, receipt, |id| {
        catalog.corridor_label(id).map(str::to_owned)
    })
}

pub(super) fn project_with_labels(
    state: &MaterialCircuitState,
    opening: Option<&MaterialCircuitState>,
    receipt: Option<&MaterialTickReceipts>,
    label: impl Fn(CorridorId) -> Option<String>,
) -> Result<(
    Vec<ProductionFreightCapacityAccount>,
    Vec<ProductionFreightOrderDefinition>,
)> {
    let current = budgets(state)?;
    let principals = participants(state)?;
    let completed = match (opening, receipt) {
        (None, None) if state.period == 1 => None,
        (Some(prior), Some(receipt)) => Some(completed_reservations(
            prior,
            state,
            receipt,
            &current,
            &principals,
        )?),
        _ => return Err(ProductionProjectionError::History),
    };
    let has_completed = completed.is_some();
    let mut completed_groups = BTreeMap::<_, Vec<_>>::new();
    let mut order_definitions = OrderDefinitions::new(Vec::new());
    if let Some(rows) = completed {
        order_definitions = OrderDefinitions::new(rows.orders);
        for ((id, _), row) in rows.rows {
            completed_groups.entry(id).or_default().push(row);
        }
    }
    let mut definitions = FreightOrderRegistry::default();
    let accounts = principals
        .into_iter()
        .map(|(id, participating)| {
            let complete = if has_completed {
                Some(CompletedProductionFreightCapacity {
                    period: state.period - 1,
                    reservations: completed_groups
                        .remove(&id)
                        .unwrap_or_default()
                        .into_iter()
                        .map(|row| row.factor(&mut definitions, &mut order_definitions))
                        .collect::<Result<Vec<_>>>()?,
                })
            } else {
                None
            };
            if complete
                .as_ref()
                .is_some_and(|row| row.reservations.is_empty())
            {
                return Err(ProductionProjectionError::State);
            }
            Ok(ProductionFreightCapacityAccount {
                corridor_id: digest_hex(&id.as_bytes()),
                corridor_label: label(id).ok_or(ProductionProjectionError::Content)?,
                kind: if participating.merchants.is_empty() {
                    ProductionCapacityKind::Transport
                } else {
                    ProductionCapacityKind::MerchantHandling
                },
                merchant_site_ids: participating
                    .merchants
                    .iter()
                    .map(|id| digest_hex(&id.as_bytes()))
                    .collect(),
                route_ids: participating
                    .routes
                    .iter()
                    .map(|id| digest_hex(&id.as_bytes()))
                    .collect(),
                next_opening_period: state.period,
                next_opening_available_grams: current
                    .get(&(id, state.period))
                    .copied()
                    .unwrap_or(0),
                completed: complete,
            })
        })
        .collect::<Result<Vec<_>>>()?;
    Ok((accounts, definitions.finish()))
}

fn capacity_order(fact: &OutboundFact) -> Result<ProductionFreightCapacityOrder> {
    let (id, kind) = identity(fact.id)?;
    Ok(ProductionFreightCapacityOrder {
        supplier_relation_id: fact
            .route
            .and(fact.buyer)
            .map(|buyer| super::routes::relation_id((buyer, fact.site, fact.good, fact.unit))),
        order_id: digest_hex(&id.as_bytes()),
        kind,
        supplier_site_id: digest_hex(&fact.site.as_bytes()),
        route_id: fact.route.map(|id| digest_hex(&id.as_bytes())),
        good_id: digest_hex(&fact.good.as_bytes()),
        unit_id: digest_hex(&fact.unit.as_bytes()),
        requested: fact.requested,
        dispatched: fact.quantity,
        remaining_unshipped: fact.remaining,
        grams_per_unit: fact.grams_per_unit,
        requested_grams: u128::from(fact.requested) * u128::from(fact.grams_per_unit),
        reserved_grams: fact
            .quantity
            .checked_mul(fact.grams_per_unit)
            .ok_or(ProductionProjectionError::Arithmetic)?,
    })
}

fn completed_reservations(
    prior: &MaterialCircuitState,
    current: &MaterialCircuitState,
    receipt: &MaterialTickReceipts,
    current_budgets: &Budgets,
    principals: &BTreeMap<CorridorId, Participants>,
) -> Result<CompletedReservations> {
    if !same_rows(&prior.route_stages, &current.route_stages)
        || !same_rows(
            &prior.route_stage_capacities,
            &current.route_stage_capacities,
        )
    {
        return Err(ProductionProjectionError::State);
    }
    let facts = completed_facts(prior, current, receipt)?;
    let mut reservations = Reservations::new();
    let mut orders = Vec::new();
    // A completed zero principal remains visible even after all finite orders finish.
    for id in principals.keys() {
        reservations.entry((*id, prior.period)).or_default();
    }
    let route_index = RouteIndex::new(prior)?;
    let merchants: BTreeMap<_, _> = prior.merchants.iter().map(|r| (r.site_id, r)).collect();
    let dispatches: BTreeMap<_, _> = receipt.dispatches.iter().map(|r| (r.order_id, r)).collect();
    for fact in facts {
        let order = capacity_order(&fact)?;
        if fact.transport != Some(SupplierTransport::Staged) && !merchants.contains_key(&fact.site)
        {
            continue;
        }
        let ordinal = orders.len();
        orders.push(order);
        if fact.transport == Some(SupplierTransport::Staged) {
            let route = fact.route.ok_or(ProductionProjectionError::State)?;
            let mut departure = prior.period;
            let stages = route_index
                .stages
                .get(&route)
                .ok_or(ProductionProjectionError::State)?;
            if stages.is_empty() {
                return Err(ProductionProjectionError::State);
            }
            for stage in stages {
                for capacity in route_index
                    .memberships
                    .get(&(route, stage.stage_index))
                    .ok_or(ProductionProjectionError::State)?
                {
                    reservations
                        .entry((*capacity, departure))
                        .or_default()
                        .commercial
                        .push(ordinal);
                }
                departure = departure
                    .checked_add(u64::from(stage.travel_periods))
                    .ok_or(ProductionProjectionError::Arithmetic)?;
            }
            let (id, _) = identity(fact.id)?;
            if dispatches
                .get(&id)
                .is_some_and(|row| row.final_arrival_period != departure)
            {
                return Err(ProductionProjectionError::State);
            }
        }
        if let Some(merchant) = merchants.get(&fact.site) {
            reservations
                .entry((merchant.capacity_id, prior.period))
                .or_default()
                .commercial
                .push(ordinal);
        }
    }
    aid::append(prior, current, receipt, &route_index, &mut reservations)?;
    match (&prior.capacity_supply, &current.capacity_supply) {
        (
            babylon_material_circuit::CapacitySupply::FiniteSchedule,
            babylon_material_circuit::CapacitySupply::FiniteSchedule,
        ) => reconcile_reservation_budgets(
            &budgets(prior)?,
            current_budgets,
            current.period,
            (reservations, orders),
        ),
        (
            babylon_material_circuit::CapacitySupply::Rolling(before),
            babylon_material_circuit::CapacitySupply::Rolling(after),
        ) => rolling::reconcile(
            prior,
            current,
            before,
            after,
            (reservations, orders),
            receipt,
        ),
        _ => Err(ProductionProjectionError::State),
    }
}

fn reconcile_reservation_budgets(
    prior: &Budgets,
    current: &Budgets,
    next_period: u64,
    reservations: ReservationInput,
) -> Result<CompletedReservations> {
    let (mut expected, result) = reservation_receipts(prior, reservations)?;
    expected.retain(|(_, period), _| *period >= next_period);
    if expected != *current {
        return Err(ProductionProjectionError::State);
    }
    Ok(result)
}

fn reservation_receipts(
    prior: &Budgets,
    input: ReservationInput,
) -> Result<(Budgets, CompletedReservations)> {
    let (reservations, orders_by_ordinal) = input;
    let mut expected = prior.clone();
    let mut result = BTreeMap::new();
    for (key, mut orders) in reservations {
        if orders
            .commercial
            .iter()
            .any(|ordinal| orders_by_ordinal.get(*ordinal).is_none())
        {
            return Err(ProductionProjectionError::State);
        }
        orders.commercial.sort_unstable_by(|left, right| {
            orders_by_ordinal
                .get(*left)
                .cmp(&orders_by_ordinal.get(*right))
        });
        orders.support.sort_unstable();
        let opening_available_grams = prior.get(&key).copied().unwrap_or(0);
        let newly_reserved_grams = orders
            .commercial
            .iter()
            .try_fold(0_u64, |sum, ordinal| {
                orders_by_ordinal
                    .get(*ordinal)
                    .and_then(|row| sum.checked_add(row.reserved_grams))
            })
            .and_then(|sum| {
                orders
                    .support
                    .iter()
                    .try_fold(sum, |sum, row| sum.checked_add(row.reserved_grams))
            })
            .ok_or(ProductionProjectionError::Arithmetic)?;
        let remaining_available_grams = opening_available_grams
            .checked_sub(newly_reserved_grams)
            .ok_or(ProductionProjectionError::State)?;
        if let Some(value) = expected.get_mut(&key) {
            *value = remaining_available_grams;
        }
        result.insert(
            key,
            RawReservation {
                reservation_period: key.1,
                opening_available_grams,
                newly_reserved_grams,
                remaining_available_grams,
                orders: orders.commercial,
                support_orders: orders.support,
            },
        );
    }
    Ok((
        expected,
        CompletedReservations {
            rows: result,
            orders: orders_by_ordinal,
        },
    ))
}

#[cfg(test)]
mod tests;
