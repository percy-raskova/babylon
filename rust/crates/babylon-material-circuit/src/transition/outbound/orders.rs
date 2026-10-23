//! Leaf implementation for the parent module; public paths stay on the parent.

use super::residual;

use super::super::merchant_admission::{hours_per_unit, merchant};

use super::super::{
    credit_inventory, debit_inventory, freight_lot_id, grams_per_unit, route_stages,
    stage_capacities, supplier_routes, BTreeMap, CapacityKey, InventoryKey, InventoryLedger,
    MaterialCircuitError, MaterialCircuitState, RouteId, RoutedDispatchReceipt, RoutedFreightLot,
    SiteId, SupplierKey, SupplyPath, UnitId,
};

use crate::production::proportional_floor;

use crate::valuation::CostClose;

use crate::{
    LocalRetailFulfillmentReceipt, LocalTransferReceipt, MerchantHandlingReceipt, OutboundOrderId,
    SupplierTransport, MAX_FREIGHT_RESOURCE_REQUESTS,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub(in crate::transition) enum FreightResourceKey {
    Inventory(InventoryKey),
    HouseholdStock((crate::FinalDemandPrincipalId, crate::GoodId, UnitId)),
    HouseholdTime(crate::FinalDemandPrincipalId, UnitId),
    Corridor(CapacityKey),
    Labor(SiteId, UnitId),
}

#[derive(Debug, Clone, Copy)]
pub(in crate::transition) struct FreightRequest {
    pub(in crate::transition) order_index: usize,
    pub(in crate::transition) requested: u64,
    pub(in crate::transition) resource_per_unit: u64,
}

pub(in crate::transition) fn add_request(
    groups: &mut BTreeMap<FreightResourceKey, Vec<FreightRequest>>,
    count: &mut usize,
    key: FreightResourceKey,
    order_index: usize,
    requested: u64,
    resource_per_unit: u64,
) -> Result<(), MaterialCircuitError> {
    *count = count
        .checked_add(1)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    ensure_resource_group_count(*count)?;
    groups.entry(key).or_default().push(FreightRequest {
        order_index,
        requested,
        resource_per_unit,
    });
    Ok(())
}

#[derive(Debug)]
pub(in crate::transition) struct OutboundOrder {
    id: OutboundOrderId,
    stock: InventoryKey,
    requested: u64,
    route: Option<RouteId>,
    eligible: bool,
    included: bool,
}

/// A replenishment pass may consume only its newly admitted deliveries. Existing
/// orders already competed in the first pass and cannot obtain a second grant.
pub(in crate::transition) enum OutboundSelection<'a> {
    All,
    NewDeliveries(&'a std::collections::BTreeSet<crate::OrderId>),
}

impl OutboundSelection<'_> {
    fn includes(&self, order: OutboundOrderId) -> bool {
        match (self, order) {
            (Self::All, _) => true,
            (Self::NewDeliveries(ids), OutboundOrderId::Delivery(id)) => ids.contains(&id),
            (
                Self::NewDeliveries(_),
                OutboundOrderId::LocalFinalDemand(_) | OutboundOrderId::Service(_),
            ) => false,
        }
    }
}

pub(in crate::transition) fn outbound_orders(
    state: &MaterialCircuitState,
    routes: &BTreeMap<SupplierKey, SupplyPath>,
    selection: &OutboundSelection<'_>,
) -> Vec<OutboundOrder> {
    let shipments = state.orders.iter().map(|row| {
        let route = routes
            .get(&(
                row.buyer_site_id,
                row.supplier_site_id,
                row.good_id,
                row.unit_id,
            ))
            .map(|(route, _)| *route);
        OutboundOrder {
            id: OutboundOrderId::Delivery(row.order_id),
            stock: (row.supplier_site_id, row.good_id, row.unit_id),
            requested: row.ordered - row.shipped,
            eligible: route.is_some(),
            included: selection.includes(OutboundOrderId::Delivery(row.order_id)),
            route,
        }
    });
    let local = state.final_demand_orders.iter().map(|row| OutboundOrder {
        id: OutboundOrderId::LocalFinalDemand(row.order_id),
        stock: (row.retailer_site_id, row.good_id, row.unit_id),
        requested: row.ordered - row.fulfilled,
        route: None,
        eligible: true,
        included: selection.includes(OutboundOrderId::LocalFinalDemand(row.order_id)),
    });
    shipments.chain(local).collect()
}

pub(in crate::transition) fn add_route_requests(
    state: &MaterialCircuitState,
    route: RouteId,
    request: FreightRequest,
    groups: &mut BTreeMap<FreightResourceKey, Vec<FreightRequest>>,
    count: &mut usize,
) -> Result<(), MaterialCircuitError> {
    let mut departure_period = state.period;
    for stage in route_stages(state, route) {
        for capacity in stage_capacities(state, route, stage.stage_index) {
            add_request(
                groups,
                count,
                FreightResourceKey::Corridor((departure_period, capacity.corridor_id)),
                request.order_index,
                request.requested,
                request.resource_per_unit,
            )?;
        }
        departure_period = departure_period
            .checked_add(u64::from(stage.travel_periods))
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(())
}

pub(in crate::transition) fn resource_groups(
    state: &MaterialCircuitState,
    orders: &[OutboundOrder],
) -> Result<BTreeMap<FreightResourceKey, Vec<FreightRequest>>, MaterialCircuitError> {
    let mut groups = BTreeMap::new();
    let mut count = 0;
    for (index, order) in orders.iter().enumerate() {
        if !order.included || !order.eligible || order.requested == 0 {
            continue;
        }
        add_request(
            &mut groups,
            &mut count,
            FreightResourceKey::Inventory(order.stock),
            index,
            order.requested,
            1,
        )?;
        if matches!(order.id, OutboundOrderId::Service(_)) {
            continue;
        }
        let grams = grams_per_unit(state, order.stock.1, order.stock.2)?;
        if let Some(route) = order.route {
            add_route_requests(
                state,
                route,
                FreightRequest {
                    order_index: index,
                    requested: order.requested,
                    resource_per_unit: grams,
                },
                &mut groups,
                &mut count,
            )?;
        }
        if let Some(merchant) = merchant(state, order.stock.0) {
            add_request(
                &mut groups,
                &mut count,
                FreightResourceKey::Corridor((state.period, merchant.capacity_id)),
                index,
                order.requested,
                grams,
            )?;
        }
    }
    Ok(groups)
}

pub(in crate::transition) fn ensure_resource_group_count(
    count: usize,
) -> Result<(), MaterialCircuitError> {
    if count > MAX_FREIGHT_RESOURCE_REQUESTS {
        Err(MaterialCircuitError::RowLimit)
    } else {
        Ok(())
    }
}

pub(in crate::transition) fn resource_available(
    state: &MaterialCircuitState,
    inventory: &InventoryLedger,
    key: FreightResourceKey,
    aid: &crate::aid::PreparedAid,
) -> Result<u64, MaterialCircuitError> {
    match key {
        FreightResourceKey::HouseholdStock(key) => Ok(aid.surplus.get(&key).copied().unwrap_or(0)),
        FreightResourceKey::HouseholdTime(principal, unit) => {
            Ok(aid.hours.get(&(principal, unit)).copied().unwrap_or(0))
        }
        FreightResourceKey::Inventory(inventory_key) => {
            Ok(inventory.get(&inventory_key).copied().unwrap_or(0))
        }
        FreightResourceKey::Corridor((period, corridor)) => {
            crate::capacity::shared_available(state, period, corridor)
        }
        FreightResourceKey::Labor(site, unit) => {
            Ok(labor_index(state, site, unit).map_or(0, |index| state.labor[index].available))
        }
    }
}

pub(in crate::transition) fn order_allocations(
    state: &MaterialCircuitState,
    inventory: &InventoryLedger,
    groups: &BTreeMap<FreightResourceKey, Vec<FreightRequest>>,
    order_count: usize,
    aid: &crate::aid::PreparedAid,
) -> Result<Vec<u64>, MaterialCircuitError> {
    let mut allocations = vec![0_u64; order_count];
    // Each active order has exactly one inventory request, regardless of the
    // number of capacity principals on its preselected route.
    for (key, requests) in groups {
        if matches!(
            key,
            FreightResourceKey::Inventory(_) | FreightResourceKey::HouseholdStock(_)
        ) {
            for request in requests {
                allocations[request.order_index] = request.requested;
            }
        }
    }
    limit_allocations(state, inventory, groups, &mut allocations, aid)?;
    Ok(allocations)
}

pub(in crate::transition) fn limit_allocations(
    state: &MaterialCircuitState,
    inventory: &InventoryLedger,
    groups: &BTreeMap<FreightResourceKey, Vec<FreightRequest>>,
    allocations: &mut [u64],
    aid: &crate::aid::PreparedAid,
) -> Result<(), MaterialCircuitError> {
    let groups = residual::aggregate(groups)?;
    for (key, requests) in &groups {
        let total = requests.iter().try_fold(0_u128, |sum, request| {
            let requested = u128::from(request.requested) * u128::from(request.resource_per_unit);
            sum.checked_add(requested)
                .ok_or(MaterialCircuitError::Arithmetic)
        })?;
        let available = resource_available(state, inventory, *key, aid)?;
        for request in requests {
            let resource_request =
                u128::from(request.requested) * u128::from(request.resource_per_unit);
            let grant = if u128::from(available) >= total {
                request.requested
            } else {
                proportional_floor(available, resource_request, total)? / request.resource_per_unit
            };
            allocations[request.order_index] = allocations[request.order_index].min(grant);
        }
    }
    Ok(())
}

pub(in crate::transition) fn allocation_matrix(
    state: &MaterialCircuitState,
    inventory: &InventoryLedger,
    groups: &residual::Groups,
    count: usize,
    aid: &crate::aid::PreparedAid,
) -> Result<residual::Matrix, MaterialCircuitError> {
    let mut bounds = vec![0; count];
    for (key, rows) in groups {
        if matches!(
            key,
            FreightResourceKey::Inventory(_) | FreightResourceKey::HouseholdStock(_)
        ) {
            for row in rows {
                bounds[row.order_index] = row.requested;
            }
        }
    }
    residual::Matrix::new(groups, bounds, |key| {
        resource_available(state, inventory, key, aid)
    })
}

pub(in crate::transition) fn canonical_requests(
    orders: &[OutboundOrder],
    aid: &crate::aid::PreparedAid,
) -> Vec<usize> {
    let identities: Vec<_> = orders
        .iter()
        .map(|order| match order.id {
            OutboundOrderId::Delivery(id) => (id, 0_u8),
            OutboundOrderId::LocalFinalDemand(id) => (id, 1),
            OutboundOrderId::Service(id) => (id, 2),
        })
        .chain(aid.orders.iter().map(|(_, id, _)| (*id, 3)))
        .collect();
    residual::identity_order(&identities)
}

pub(in crate::transition) fn complete_allocations(
    state: &MaterialCircuitState,
    inventory: &InventoryLedger,
    orders: &[OutboundOrder],
    groups: &residual::Groups,
    count: usize,
    aid: &crate::aid::PreparedAid,
) -> Result<(Vec<u64>, Vec<u64>), MaterialCircuitError> {
    let base_physical = order_allocations(state, inventory, groups, count, aid)?;
    let physical = residual::aggregate(groups)?;
    let ceilings = allocation_matrix(state, inventory, &physical, count, aid)?.ceilings();
    let request_count = groups.values().try_fold(0_usize, |n, rows| {
        n.checked_add(rows.len())
            .ok_or(MaterialCircuitError::Arithmetic)
    })?;
    let base_labor = labor_groups(state, orders, &base_physical, request_count)?;
    let mut allocations = base_physical;
    limit_allocations(state, inventory, &base_labor, &mut allocations, aid)?;
    // Zero base grants still require every handling coefficient in the residual
    // cuts. Ceilings are independent of competition and current staffing.
    let labor = labor_groups(state, orders, &ceilings, request_count)?;
    let mut all = physical;
    for (key, rows) in labor {
        all.entry(key).or_default().extend(rows);
    }
    let all = residual::aggregate(&all)?;
    let matrix = allocation_matrix(state, inventory, &all, count, aid)?;
    matrix.augment(&mut allocations, &canonical_requests(orders, aid))?;
    Ok((ceilings, allocations))
}

pub(in crate::transition) fn reserve_route_capacity(
    state: &mut MaterialCircuitState,
    route: RouteId,
    grams: u64,
) -> Result<u64, MaterialCircuitError> {
    let mut departure_period = state.period;
    for stage in route_stages(state, route).to_vec() {
        let capacities = stage_capacities(state, route, stage.stage_index).to_vec();
        for capacity in capacities {
            crate::capacity::reserve(state, departure_period, capacity.corridor_id, grams)?;
        }
        departure_period = departure_period
            .checked_add(u64::from(stage.travel_periods))
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(departure_period)
}

pub(in crate::transition) fn apply_local_transfer(
    state: &mut MaterialCircuitState,
    inventory: &mut InventoryLedger,
    index: usize,
    order: &crate::OrderRow,
    quantity: u64,
) -> Result<LocalTransferReceipt, MaterialCircuitError> {
    debit_inventory(
        inventory,
        (order.supplier_site_id, order.good_id, order.unit_id),
        quantity,
        MaterialCircuitError::FreightInvariant,
    )?;
    let updated = &mut state.orders[index];
    updated.shipped = updated
        .shipped
        .checked_add(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    updated.delivered = updated
        .delivered
        .checked_add(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    updated.realized = updated
        .realized
        .checked_add(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(LocalTransferReceipt {
        order_id: order.order_id,
        supplier_site_id: order.supplier_site_id,
        buyer_site_id: order.buyer_site_id,
        good_id: order.good_id,
        unit_id: order.unit_id,
        quantity,
    })
}

pub(in crate::transition) fn apply_dispatches(
    state: &mut MaterialCircuitState,
    inventory: &mut InventoryLedger,
    routes: &BTreeMap<SupplierKey, SupplyPath>,
    allocations: &[u64],
    receipts: &mut Vec<RoutedDispatchReceipt>,
    costs: &mut CostClose,
) -> Result<Vec<LocalTransferReceipt>, MaterialCircuitError> {
    let mut local_transfers = Vec::new();
    for (index, quantity) in allocations.iter().copied().enumerate() {
        if quantity == 0 {
            continue;
        }
        let order = state.orders[index].clone();
        let supplier_key = (
            order.buyer_site_id,
            order.supplier_site_id,
            order.good_id,
            order.unit_id,
        );
        let (route, mode) = routes[&supplier_key];
        let local = mode == SupplierTransport::Local;
        let key = (order.supplier_site_id, order.good_id, order.unit_id);
        let available = inventory.get(&key).copied().unwrap_or(0);
        if local {
            costs.local_sale(state, &order, available, quantity)?;
            local_transfers.push(apply_local_transfer(
                state, inventory, index, &order, quantity,
            )?);
            continue;
        }
        let lot_id = freight_lot_id(order.order_id, state.period);
        costs.dispatch(
            (crate::AccountId::Site(key.0), key.1, key.2),
            available,
            quantity,
            lot_id,
        )?;
        let legs = route_stages(state, route);
        let first_arrival_period = state
            .period
            .checked_add(u64::from(legs[0].travel_periods))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        debit_inventory(
            inventory,
            (order.supplier_site_id, order.good_id, order.unit_id),
            quantity,
            MaterialCircuitError::FreightInvariant,
        )?;
        let grams = quantity
            .checked_mul(grams_per_unit(state, order.good_id, order.unit_id)?)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let final_arrival_period = reserve_route_capacity(state, route, grams)?;
        state.orders[index].shipped = state.orders[index]
            .shipped
            .checked_add(quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        state.freight.push(RoutedFreightLot {
            lot_id,
            order_id: order.order_id,
            route_id: route,
            dispatch_period: state.period,
            current_stage_index: 0,
            stage_arrival_period: first_arrival_period,
            source_site_id: order.supplier_site_id,
            destination_site_id: order.buyer_site_id,
            good_id: order.good_id,
            unit_id: order.unit_id,
            quantity,
        });
        receipts.push(RoutedDispatchReceipt {
            lot_id,
            order_id: order.order_id,
            route_id: route,
            quantity,
            final_arrival_period,
        });
    }
    Ok(local_transfers)
}

pub(in crate::transition) fn labor_index(
    state: &MaterialCircuitState,
    site: SiteId,
    unit: UnitId,
) -> Option<usize> {
    state
        .labor
        .binary_search_by_key(&(state.period, site, unit), |row| {
            (row.period, row.site_id, row.unit_id)
        })
        .ok()
}

pub(in crate::transition) fn labor_groups(
    state: &MaterialCircuitState,
    orders: &[OutboundOrder],
    feasible: &[u64],
    existing_requests: usize,
) -> Result<BTreeMap<FreightResourceKey, Vec<FreightRequest>>, MaterialCircuitError> {
    let mut groups = BTreeMap::new();
    let mut count = existing_requests;
    for (index, (order, quantity)) in orders.iter().zip(feasible).enumerate() {
        if !order.included {
            continue;
        }
        if let Some(merchant) = merchant(state, order.stock.0) {
            let hours = hours_per_unit(state, order.stock.0, order.stock.1, order.stock.2)?;
            add_request(
                &mut groups,
                &mut count,
                FreightResourceKey::Labor(merchant.site_id, merchant.labor_unit_id),
                index,
                *quantity,
                hours,
            )?;
        }
    }
    Ok(groups)
}

pub(in crate::transition) fn apply_handling(
    state: &mut MaterialCircuitState,
    orders: &[OutboundOrder],
    feasible: &[u64],
    actual: &[u64],
    costs: &mut CostClose,
) -> Result<Vec<MerchantHandlingReceipt>, MaterialCircuitError> {
    let mut receipts = Vec::new();
    for ((order, feasible_quantity), handled_quantity) in orders.iter().zip(feasible).zip(actual) {
        if !order.included {
            continue;
        }
        let Some(merchant) = merchant(state, order.stock.0).cloned() else {
            continue;
        };
        let hours = hours_per_unit(state, order.stock.0, order.stock.1, order.stock.2)?;
        let needed_hours = feasible_quantity
            .checked_mul(hours)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let used_hours = handled_quantity
            .checked_mul(hours)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        costs.handling(
            order.stock,
            merchant.labor_unit_id,
            *handled_quantity,
            used_hours,
        )?;
        if *handled_quantity > 0 {
            let labor = labor_index(state, merchant.site_id, merchant.labor_unit_id)
                .ok_or(MaterialCircuitError::CapacityInvariant)?;
            state.labor[labor].available = state.labor[labor]
                .available
                .checked_sub(used_hours)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            let grams = handled_quantity
                .checked_mul(grams_per_unit(state, order.stock.1, order.stock.2)?)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            crate::capacity::reserve(state, state.period, merchant.capacity_id, grams)?;
        }
        receipts.push(MerchantHandlingReceipt {
            site_id: merchant.site_id,
            order: order.id,
            feasible_quantity: *feasible_quantity,
            handled_quantity: *handled_quantity,
            needed_hours,
            used_hours,
        });
    }
    receipts.sort_by_key(|row| (row.site_id, row.order));
    Ok(receipts)
}

pub(in crate::transition) fn apply_local_fulfillments(
    state: &mut MaterialCircuitState,
    inventory: &mut InventoryLedger,
    allocations: &[u64],
    costs: &mut CostClose,
) -> Result<Vec<LocalRetailFulfillmentReceipt>, MaterialCircuitError> {
    let mut receipts = Vec::new();
    for (index, quantity) in allocations.iter().enumerate() {
        let row = state.final_demand_orders[index].clone();
        if *quantity == 0 {
            continue;
        }
        let available = inventory
            .get(&(row.retailer_site_id, row.good_id, row.unit_id))
            .copied()
            .unwrap_or(0);
        costs.retail(state, &row, available, *quantity)?;
        debit_inventory(
            inventory,
            (row.retailer_site_id, row.good_id, row.unit_id),
            *quantity,
            MaterialCircuitError::FreightInvariant,
        )?;
        state.final_demand_orders[index].fulfilled = row
            .fulfilled
            .checked_add(*quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        receipts.push(LocalRetailFulfillmentReceipt {
            order_id: row.order_id,
            retailer_site_id: row.retailer_site_id,
            demand_principal_id: row.demand_principal_id,
            good_id: row.good_id,
            unit_id: row.unit_id,
            quantity: *quantity,
        });
    }
    Ok(receipts)
}

pub(in crate::transition) struct OutboundReceipts {
    pub handling: Vec<MerchantHandlingReceipt>,
    pub local_fulfillments: Vec<LocalRetailFulfillmentReceipt>,
    pub local_transfers: Vec<LocalTransferReceipt>,
}

pub(in crate::transition) fn dispatch_orders(
    state: &mut MaterialCircuitState,
    inventory: &mut InventoryLedger,
    receipts: &mut Vec<RoutedDispatchReceipt>,
    selection: &OutboundSelection<'_>,
    costs: &mut CostClose,
) -> Result<OutboundReceipts, MaterialCircuitError> {
    dispatch_orders_with_aid(
        state,
        inventory,
        receipts,
        selection,
        costs,
        AidDispatch {
            prepared: &crate::aid::PreparedAid::empty(),
            money: &mut Vec::new(),
            receipts: &mut Vec::new(),
        },
    )
}

pub(in crate::transition) struct AidDispatch<'a> {
    pub prepared: &'a crate::aid::PreparedAid,
    pub money: &'a mut Vec<crate::MoneyTransferReceipt>,
    pub receipts: &'a mut Vec<crate::AidReceipt>,
}

pub(in crate::transition) fn dispatch_orders_with_aid(
    state: &mut MaterialCircuitState,
    inventory: &mut InventoryLedger,
    receipts: &mut Vec<RoutedDispatchReceipt>,
    selection: &OutboundSelection<'_>,
    costs: &mut CostClose,
    aid: AidDispatch<'_>,
) -> Result<OutboundReceipts, MaterialCircuitError> {
    let AidDispatch {
        prepared: aid,
        money,
        receipts: aid_receipts,
    } = aid;
    let routes = supplier_routes(state);
    let orders = outbound_orders(state, &routes, selection);
    let mut groups = resource_groups(state, &orders)?;
    add_aid_requests(state, aid, orders.len(), &mut groups)?;
    let count = orders
        .len()
        .checked_add(aid.orders.len())
        .ok_or(MaterialCircuitError::Arithmetic)?;
    let (feasible, allocations) =
        complete_allocations(state, inventory, &orders, &groups, count, aid)?;
    let handling = apply_handling(state, &orders, &feasible, &allocations, costs)?;
    let routed_count = state.orders.len();
    let local_transfers = apply_dispatches(
        state,
        inventory,
        &routes,
        &allocations[..routed_count],
        receipts,
        costs,
    )?;
    let local = apply_local_fulfillments(
        state,
        inventory,
        &allocations[routed_count..orders.len()],
        costs,
    )?;
    apply_aid_dispatches(
        state,
        aid,
        &allocations[orders.len()..],
        costs,
        money,
        aid_receipts,
    )?;
    Ok(OutboundReceipts {
        handling,
        local_fulfillments: local,
        local_transfers,
    })
}

/// Credit local firm buyers only after every outbound pass has consumed its
/// grants. This preserves the no recursive same-close supply boundary.
pub(in crate::transition) fn credit_local_transfers(
    inventory: &mut InventoryLedger,
    transfers: &[LocalTransferReceipt],
) -> Result<(), MaterialCircuitError> {
    for transfer in transfers {
        credit_inventory(
            inventory,
            (transfer.buyer_site_id, transfer.good_id, transfer.unit_id),
            transfer.quantity,
        )?;
    }
    Ok(())
}

/// Services reuse the native-unit outbound allocation; no freight or handling resource exists.
pub(crate) fn allocate_services(
    state: &MaterialCircuitState,
    services: &[crate::ServiceOrder],
    available: &InventoryLedger,
) -> Result<Vec<u64>, MaterialCircuitError> {
    let orders: Vec<_> = services
        .iter()
        .map(|r| OutboundOrder {
            id: OutboundOrderId::Service(r.order_id),
            stock: (r.provider_site_id, r.good_id, r.unit_id),
            requested: r.quantity,
            route: None,
            eligible: true,
            included: true,
        })
        .collect();
    let groups = resource_groups(state, &orders)?;
    let aid = crate::aid::PreparedAid::empty();
    let mut allocations = order_allocations(state, available, &groups, orders.len(), &aid)?;
    let groups = residual::aggregate(&groups)?;
    let matrix = allocation_matrix(state, available, &groups, orders.len(), &aid)?;
    matrix.augment(&mut allocations, &canonical_requests(&orders, &aid))?;
    Ok(allocations)
}

pub(in crate::transition) fn add_aid_requests(
    state: &MaterialCircuitState,
    aid: &crate::aid::PreparedAid,
    offset: usize,
    groups: &mut BTreeMap<FreightResourceKey, Vec<FreightRequest>>,
) -> Result<(), MaterialCircuitError> {
    let mut count = groups.values().try_fold(0usize, |n, rows| {
        n.checked_add(rows.len())
            .ok_or(MaterialCircuitError::Arithmetic)
    })?;
    for (index, (mandate, _, quantity)) in aid.orders.iter().enumerate() {
        let index = offset
            .checked_add(index)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        add_request(
            groups,
            &mut count,
            FreightResourceKey::HouseholdStock((mandate.donor, mandate.good_id, mandate.unit_id)),
            index,
            *quantity,
            1,
        )?;
        add_request(
            groups,
            &mut count,
            FreightResourceKey::HouseholdTime(mandate.donor, mandate.labor_unit_id),
            index,
            *quantity,
            mandate.hours_per_unit,
        )?;
        if let crate::AidTransport::Routed { route_id, .. } = mandate.transport {
            add_route_requests(
                state,
                route_id,
                FreightRequest {
                    order_index: index,
                    requested: *quantity,
                    resource_per_unit: grams_per_unit(state, mandate.good_id, mandate.unit_id)?,
                },
                groups,
                &mut count,
            )?;
        }
    }
    Ok(())
}

pub(in crate::transition) fn apply_aid_dispatches(
    state: &mut MaterialCircuitState,
    aid: &crate::aid::PreparedAid,
    allocations: &[u64],
    costs: &mut CostClose,
    money: &mut Vec<crate::MoneyTransferReceipt>,
    receipts: &mut Vec<crate::AidReceipt>,
) -> Result<(), MaterialCircuitError> {
    for ((mandate, id, reserved_quantity), quantity) in aid.orders.iter().zip(allocations) {
        let unshipped = reserved_quantity
            .checked_sub(*quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        if unshipped > 0 {
            let crate::CircuitAccounting::Monetary(economy) = &mut state.accounting else {
                return Err(MaterialCircuitError::AidInvariant);
            };
            money.push(economy.book.resolve_aid(*id, unshipped, true)?);
            receipts.push(crate::aid::receipt(
                mandate,
                *id,
                state.period,
                crate::AidOutcome::Unshipped,
                crate::aid::AidFlow {
                    quantity: unshipped,
                    carrying: babylon_kernel::currency::Currency::from_micro_units(0),
                    cash: crate::aid::cash_amount(unshipped, mandate)?,
                    hours: 0,
                },
            ));
        }
        if *quantity > 0 {
            apply_one_aid_dispatch(state, mandate, *id, *quantity, costs, money, receipts)?;
        }
        let crate::CircuitAccounting::Monetary(economy) = &mut state.accounting else {
            return Err(MaterialCircuitError::AidInvariant);
        };
        if economy
            .book
            .aid_reserve(*id)?
            .reserved_amount()?
            .micro_units()
            == 0
        {
            economy.book.retire_aid(*id)?;
        }
    }
    Ok(())
}

pub(in crate::transition) fn apply_one_aid_dispatch(
    state: &mut MaterialCircuitState,
    mandate: &crate::AidMandate,
    id: crate::OrderId,
    quantity: u64,
    costs: &mut CostClose,
    money: &mut Vec<crate::MoneyTransferReceipt>,
    receipts: &mut Vec<crate::AidReceipt>,
) -> Result<(), MaterialCircuitError> {
    let available = crate::aid::take_household_stock(state, mandate, quantity)?;
    let lot_id = crate::aid::aid_lot_id(id);
    let cash = crate::aid::cash_amount(quantity, mandate)?;
    let hours = quantity
        .checked_mul(mandate.hours_per_unit)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    match mandate.transport {
        crate::AidTransport::Local => {
            let carrying = costs.local_aid(mandate, available, quantity, cash)?;
            crate::aid::grant_household_stock(state, mandate, quantity)?;
            let crate::CircuitAccounting::Monetary(economy) = &mut state.accounting else {
                return Err(MaterialCircuitError::AidInvariant);
            };
            money.push(economy.book.resolve_aid(id, quantity, false)?);
            receipts.push(crate::aid::receipt(
                mandate,
                id,
                state.period,
                crate::AidOutcome::Granted,
                crate::aid::AidFlow {
                    quantity,
                    carrying,
                    cash,
                    hours,
                },
            ));
        }
        crate::AidTransport::Routed { route_id, .. } => {
            let carrying = costs.dispatch_aid(mandate, available, quantity, lot_id)?;
            let grams = quantity
                .checked_mul(grams_per_unit(state, mandate.good_id, mandate.unit_id)?)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            reserve_route_capacity(state, route_id, grams)?;
            let first_leg = route_stages(state, route_id)
                .first()
                .ok_or(MaterialCircuitError::AidInvariant)?;
            let stage_arrival_period = state
                .period
                .checked_add(u64::from(first_leg.travel_periods))
                .ok_or(MaterialCircuitError::Arithmetic)?;
            let lot = crate::AidFreightLot {
                lot_id,
                commitment_id: id,
                mandate_id: mandate.id,
                route_id,
                dispatch_period: state.period,
                current_stage_index: first_leg.stage_index,
                stage_arrival_period,
                donor: mandate.donor,
                recipient: mandate.recipient,
                good_id: mandate.good_id,
                unit_id: mandate.unit_id,
                quantity,
            };
            let crate::CircuitAccounting::Monetary(economy) = &mut state.accounting else {
                return Err(MaterialCircuitError::AidInvariant);
            };
            if economy
                .aid
                .freight
                .len()
                .checked_add(state.freight.len())
                .ok_or(MaterialCircuitError::Arithmetic)?
                >= crate::MAX_MATERIAL_CIRCUIT_ROWS
            {
                return Err(MaterialCircuitError::RowLimit);
            }
            economy.aid.freight.push(lot);
            receipts.push(crate::aid::receipt(
                mandate,
                id,
                state.period,
                crate::AidOutcome::Dispatched,
                crate::aid::AidFlow {
                    quantity,
                    carrying,
                    cash,
                    hours,
                },
            ));
        }
    }

    Ok(())
}
