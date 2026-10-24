use babylon_material_circuit::AccountId;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialPurchase;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::OrderId;
use babylon_material_circuit::OutboundOrderId;
use babylon_material_circuit::PurchaseEscrow;
use babylon_material_circuit::ServiceOrder;
use babylon_material_circuit::StockCarryingValue;
use babylon_material_circuit::MAX_MATERIAL_CIRCUIT_ROWS;

const SERVICE_LIMIT: usize = 2 * MAX_MATERIAL_CIRCUIT_ROWS;
const SERVICE_ORDER_BYTES: usize = 32 + 8 + 32 + 33 + 32 + 32 + 8;

fn order_id(index: usize) -> OrderId {
    let mut bytes = [0; 32];
    bytes[..8].copy_from_slice(
        &u64::try_from(index)
            .expect("the fixture value fits the target range")
            .to_be_bytes(),
    );
    OrderId::from_bytes(bytes)
}
fn order(index: usize) -> ServiceOrder {
    ServiceOrder {
        order_id: order_id(index),
        performance_period: 1,
        provider_site_id: crate::site(1),
        buyer: AccountId::Site(crate::site(2)),
        good_id: crate::good(1),
        unit_id: crate::unit(1),
        quantity: 1,
    }
}
fn reserved_orders(count: usize) -> MaterialCircuitState {
    let mut state = crate::opening();
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
                crate::money(1),
            )
            .expect("the constructor accepts the authored fixture arguments")
        })
        .collect();
    economy.book =
        MonetaryBook::from_snapshot(snapshot).expect("the snapshot admits the derived value");
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        state
            .inventory
            .iter()
            .map(|row| StockCarryingValue {
                owner: AccountId::Site(row.site_id),
                good_id: row.good_id,
                unit_id: row.unit_id,
                amount: crate::money(0),
            })
            .collect(),
        vec![],
        vec![],
        vec![],
    )
    .expect("the fixture opens the authored source");
    state
}

#[test]
fn service_principals_reach_the_named_bound_and_refuse_the_next_purchase() {
    let before = reserved_orders(SERVICE_LIMIT - 1);
    let (full, _) = babylon_material_circuit::admit_material_purchase(
        &before,
        MaterialPurchase::Service(order(SERVICE_LIMIT - 1)),
        crate::money(1),
    )
    .expect("the fixture admits the authored purchase");
    assert_eq!(full.service_orders.len(), SERVICE_LIMIT);
    assert_eq!(
        babylon_material_circuit::admit_material_purchase(
            &full,
            MaterialPurchase::Service(order(SERVICE_LIMIT)),
            crate::money(1)
        ),
        Err(MaterialCircuitError::RowLimit)
    );
    let bytes = babylon_material_circuit::encode_material_circuit_state(&full)
        .expect("the canonical material state encodes");
    let restored = babylon_material_circuit::decode_material_circuit_state(&bytes)
        .expect("the canonical material bytes decode");
    assert_eq!(restored, full);
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&restored)
            .expect("the canonical material state encodes"),
        bytes
    );
    let last = bytes.len() - SERVICE_ORDER_BYTES;
    let mut duplicate = bytes.clone();
    duplicate.copy_within(last - SERVICE_ORDER_BYTES..last, last);
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&duplicate),
        Err(MaterialCircuitError::DuplicateRow)
    );
    let mut excess = bytes;
    let count_offset = excess.len() - SERVICE_LIMIT * SERVICE_ORDER_BYTES - 4;
    excess[count_offset..count_offset + 4].copy_from_slice(
        &u32::try_from(SERVICE_LIMIT + 1)
            .expect("the fixture value fits the target range")
            .to_be_bytes(),
    );
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&excess),
        Err(MaterialCircuitError::WireLimit)
    );
}
