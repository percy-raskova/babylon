use super::*;

const SERVICE_LIMIT: usize = 2 * MAX_MATERIAL_CIRCUIT_ROWS;
const SERVICE_ORDER_BYTES: usize = 32 + 8 + 32 + 33 + 32 + 32 + 8;

fn order_id(index: usize) -> OrderId {
    let mut bytes = [0; 32];
    bytes[..8].copy_from_slice(&u64::try_from(index).unwrap().to_be_bytes());
    OrderId::from_bytes(bytes)
}
fn order(index: usize) -> ServiceOrder {
    ServiceOrder {
        order_id: order_id(index),
        performance_period: 1,
        provider_site_id: site(1),
        buyer: AccountId::Site(site(2)),
        good_id: good(1),
        unit_id: unit(1),
        quantity: 1,
    }
}
fn reserved_orders(count: usize) -> MaterialCircuitState {
    let mut state = opening();
    state.service_orders = (0..count).map(order).collect();
    let CircuitAccounting::Monetary(economy) = &mut state.accounting else {
        unreachable!()
    };
    let mut snapshot = economy.book.snapshot();
    snapshot.purchases = state
        .service_orders
        .iter()
        .map(|order| {
            PurchaseEscrow::new(
                OutboundOrderId::Service(order.order_id),
                order.buyer,
                AccountId::Site(order.provider_site_id),
                order.quantity,
                money(1),
            )
            .unwrap()
        })
        .collect();
    economy.book = MonetaryBook::from_snapshot(snapshot).unwrap();
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        state
            .inventory
            .iter()
            .map(|row| StockCarryingValue {
                owner: AccountId::Site(row.site_id),
                good_id: row.good_id,
                unit_id: row.unit_id,
                amount: money(0),
            })
            .collect(),
        vec![],
        vec![],
        vec![],
    )
    .unwrap();
    state
}

#[test]
fn service_principals_reach_the_named_bound_and_refuse_the_next_purchase() {
    let before = reserved_orders(SERVICE_LIMIT - 1);
    let (full, _) = admit_material_purchase(
        &before,
        MaterialPurchase::Service(order(SERVICE_LIMIT - 1)),
        money(1),
    )
    .unwrap();
    assert_eq!(full.service_orders.len(), SERVICE_LIMIT);
    assert_eq!(
        admit_material_purchase(
            &full,
            MaterialPurchase::Service(order(SERVICE_LIMIT)),
            money(1)
        ),
        Err(MaterialCircuitError::RowLimit)
    );
    let bytes = encode_material_circuit_state(&full).unwrap();
    let restored = decode_material_circuit_state(&bytes).unwrap();
    assert_eq!(restored, full);
    assert_eq!(encode_material_circuit_state(&restored).unwrap(), bytes);
    let last = bytes.len() - SERVICE_ORDER_BYTES;
    let mut duplicate = bytes.clone();
    duplicate.copy_within(last - SERVICE_ORDER_BYTES..last, last);
    assert_eq!(
        decode_material_circuit_state(&duplicate),
        Err(MaterialCircuitError::DuplicateRow)
    );
    let mut excess = bytes;
    let count_offset = excess.len() - SERVICE_LIMIT * SERVICE_ORDER_BYTES - 4;
    excess[count_offset..count_offset + 4]
        .copy_from_slice(&u32::try_from(SERVICE_LIMIT + 1).unwrap().to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&excess),
        Err(MaterialCircuitError::WireLimit)
    );
}
