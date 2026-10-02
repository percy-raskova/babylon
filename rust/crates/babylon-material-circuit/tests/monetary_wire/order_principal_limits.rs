use super::*;
fn order_id(index: usize) -> OrderId {
    let mut bytes = [0; 32];
    bytes[..8].copy_from_slice(&u64::try_from(index).unwrap().to_be_bytes());
    OrderId::from_bytes(bytes)
}
fn mixed_order_state_counts(delivery: usize, retail: usize) -> MaterialCircuitState {
    let mut state = paid_state();
    let template = state.orders[0].clone();
    state.orders = (0..delivery)
        .map(|index| OrderRow {
            order_id: order_id(index),
            ordered: 1,
            ..template.clone()
        })
        .collect();
    state.backlog = state
        .orders
        .iter()
        .map(|row| BacklogRow {
            order_id: row.order_id,
            quantity: row.ordered,
        })
        .collect();
    let household = state.final_demand_principals[0].id;
    state.merchants.push(MerchantHandling {
        site_id: template.supplier_site_id,
        location: state.final_demand_principals[0].location,
        role: MerchantRole::Retail,
        capacity_id: CorridorId::from_bytes([99; 32]),
        labor_unit_id: state.labor[0].unit_id,
    });
    state
        .handling_coefficients
        .push(MerchantHandlingCoefficient {
            site_id: template.supplier_site_id,
            good_id: template.good_id,
            unit_id: template.unit_id,
            hours_per_unit: 1,
        });
    state.final_demand_orders = (0..retail)
        .map(|index| FinalDemandOrder {
            order_id: order_id(index),
            retailer_site_id: template.supplier_site_id,
            demand_principal_id: household,
            good_id: template.good_id,
            unit_id: template.unit_id,
            ordered: 1,
            fulfilled: 0,
        })
        .collect();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let mut snapshot = economy.book.snapshot();
    snapshot.purchases = state
        .orders
        .iter()
        .map(|row| {
            PurchaseEscrow::new(
                OutboundOrderId::Delivery(row.order_id),
                AccountId::Site(row.buyer_site_id),
                AccountId::Site(row.supplier_site_id),
                1,
                money(1),
            )
            .unwrap()
        })
        .chain(state.final_demand_orders.iter().map(|row| {
            PurchaseEscrow::new(
                OutboundOrderId::LocalFinalDemand(row.order_id),
                AccountId::Household(household),
                AccountId::Site(row.retailer_site_id),
                1,
                money(1),
            )
            .unwrap()
        }))
        .collect();
    economy.book = MonetaryBook::from_snapshot(snapshot).unwrap();
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        vec![StockCarryingValue {
            owner: AccountId::Site(template.supplier_site_id),
            good_id: template.good_id,
            unit_id: template.unit_id,
            amount: money(0),
        }],
        vec![],
        vec![],
        vec![],
    )
    .unwrap();
    state
}
fn mixed_order_state() -> MaterialCircuitState {
    let count = MAX_MATERIAL_CIRCUIT_ROWS / 2 + 1;
    mixed_order_state_counts(count, count)
}
#[test]
fn mixed_physical_orders_and_escrow_roundtrip_beyond_the_old_combined_limit() {
    let state = mixed_order_state();
    let bytes = encode_material_circuit_state(&state).unwrap();
    let restored = decode_material_circuit_state(&bytes).unwrap();
    assert_eq!(restored, state);
    assert_eq!(encode_material_circuit_state(&restored).unwrap(), bytes);
    let CircuitAccounting::Monetary(economy) = &restored.accounting else {
        unreachable!()
    };
    assert_eq!(
        economy.book.snapshot().purchases.len(),
        MAX_MATERIAL_CIRCUIT_ROWS + 2
    );
    assert_eq!(
        economy
            .book
            .purchase(OutboundOrderId::LocalFinalDemand(order_id(
                MAX_MATERIAL_CIRCUIT_ROWS / 2
            )))
            .unwrap()
            .quantity,
        1
    );
    let start = accounting_offset(&state) + 1 + 4 + 5 * ACCOUNT_BYTES + 4;
    let last = start + (MAX_MATERIAL_CIRCUIT_ROWS + 1) * PURCHASE_BYTES;
    let mut duplicate = bytes.clone();
    duplicate.copy_within(last - PURCHASE_BYTES..last, last);
    assert_eq!(
        decode_material_circuit_state(&duplicate),
        Err(MaterialCircuitError::WireNoncanonical)
    );
}
#[test]
fn public_purchase_admission_preserves_each_physical_family_ceiling() {
    let state = mixed_order_state();
    let mut order = state.orders[0].clone();
    order.order_id = order_id(MAX_MATERIAL_CIRCUIT_ROWS);
    let (admitted, _) =
        admit_material_purchase(&state, MaterialPurchase::Delivery(order), money(1)).unwrap();
    assert_eq!(admitted.orders.len(), state.orders.len() + 1);
    let mut overbound = state;
    overbound.orders.resize(
        2 * MAX_MATERIAL_CIRCUIT_ROWS + 1,
        overbound.orders[0].clone(),
    );
    assert_eq!(
        encode_material_circuit_state(&overbound),
        Err(MaterialCircuitError::RowLimit)
    );
}

#[test]
fn retail_admission_and_wire_keep_the_independent_unchanged_ceiling() {
    let state = mixed_order_state_counts(1, MAX_MATERIAL_CIRCUIT_ROWS - 1);
    let mut order = state.final_demand_orders[0].clone();
    order.order_id = order_id(MAX_MATERIAL_CIRCUIT_ROWS - 1);
    let (full, _) = admit_material_purchase(
        &state,
        MaterialPurchase::LocalFinalDemand(order.clone()),
        money(1),
    )
    .unwrap();
    assert_eq!(full.final_demand_orders.len(), MAX_MATERIAL_CIRCUIT_ROWS);
    let bytes = encode_material_circuit_state(&full).unwrap();
    assert_eq!(decode_material_circuit_state(&bytes).unwrap(), full);
    order.order_id = order_id(MAX_MATERIAL_CIRCUIT_ROWS);
    assert_eq!(
        admit_material_purchase(&full, MaterialPurchase::LocalFinalDemand(order), money(1)),
        Err(MaterialCircuitError::RowLimit)
    );
    assert_eq!(encode_material_circuit_state(&full).unwrap(), bytes);
}
