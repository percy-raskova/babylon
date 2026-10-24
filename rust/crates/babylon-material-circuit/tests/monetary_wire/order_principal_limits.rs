use crate::ACCOUNT_BYTES;
use crate::PURCHASE_BYTES;
use babylon_material_circuit::AccountId;
use babylon_material_circuit::BacklogRow;
use babylon_material_circuit::CircuitAccounting;
use babylon_material_circuit::CorridorId;
use babylon_material_circuit::FinalDemandOrder;
use babylon_material_circuit::HistoricalCostBook;
use babylon_material_circuit::MaterialCircuitError;
use babylon_material_circuit::MaterialCircuitState;
use babylon_material_circuit::MaterialPurchase;
use babylon_material_circuit::MerchantHandling;
use babylon_material_circuit::MerchantHandlingCoefficient;
use babylon_material_circuit::MerchantRole;
use babylon_material_circuit::MonetaryBook;
use babylon_material_circuit::OrderId;
use babylon_material_circuit::OrderRow;
use babylon_material_circuit::OutboundOrderId;
use babylon_material_circuit::PurchaseEscrow;
use babylon_material_circuit::StockCarryingValue;
use babylon_material_circuit::MAX_MATERIAL_CIRCUIT_ROWS;
fn order_id(index: usize) -> OrderId {
    let mut bytes = [0; 32];
    bytes[..8].copy_from_slice(
        &u64::try_from(index)
            .expect("the fixture value fits the target range")
            .to_be_bytes(),
    );
    OrderId::from_bytes(bytes)
}
fn mixed_order_state_counts(delivery: usize, retail: usize) -> MaterialCircuitState {
    let mut state = crate::paid_state();
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
                crate::money(1),
            )
            .expect("the constructor accepts the authored fixture arguments")
        })
        .chain(state.final_demand_orders.iter().map(|row| {
            PurchaseEscrow::new(
                OutboundOrderId::LocalFinalDemand(row.order_id),
                AccountId::Household(household),
                AccountId::Site(row.retailer_site_id),
                1,
                crate::money(1),
            )
            .expect("the constructor accepts the authored fixture arguments")
        }))
        .collect();
    economy.book =
        MonetaryBook::from_snapshot(snapshot).expect("the snapshot admits the derived value");
    economy.costs = HistoricalCostBook::open(
        &economy.book,
        vec![StockCarryingValue {
            owner: AccountId::Site(template.supplier_site_id),
            good_id: template.good_id,
            unit_id: template.unit_id,
            amount: crate::money(0),
        }],
        vec![],
        vec![],
        vec![],
    )
    .expect("the fixture opens the authored source");
    state
}
fn mixed_order_state() -> MaterialCircuitState {
    let count = MAX_MATERIAL_CIRCUIT_ROWS / 2 + 1;
    mixed_order_state_counts(count, count)
}
#[test]
fn mixed_physical_orders_and_escrow_roundtrip_beyond_the_old_combined_limit() {
    let state = mixed_order_state();
    let bytes = babylon_material_circuit::encode_material_circuit_state(&state)
        .expect("the canonical material state encodes");
    let restored = babylon_material_circuit::decode_material_circuit_state(&bytes)
        .expect("the canonical material bytes decode");
    assert_eq!(restored, state);
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&restored)
            .expect("the canonical material state encodes"),
        bytes
    );
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
            .expect("the fixture purchase is present")
            .quantity,
        1
    );
    let start = crate::accounting_offset(&state) + 1 + 4 + 5 * ACCOUNT_BYTES + 4;
    let last = start + (MAX_MATERIAL_CIRCUIT_ROWS + 1) * PURCHASE_BYTES;
    let mut duplicate = bytes.clone();
    duplicate.copy_within(last - PURCHASE_BYTES..last, last);
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&duplicate),
        Err(MaterialCircuitError::WireNoncanonical)
    );
}
#[test]
fn public_purchase_admission_preserves_each_physical_family_ceiling() {
    let state = mixed_order_state();
    let mut order = state.orders[0].clone();
    order.order_id = order_id(MAX_MATERIAL_CIRCUIT_ROWS);
    let (admitted, _) = babylon_material_circuit::admit_material_purchase(
        &state,
        MaterialPurchase::Delivery(order),
        crate::money(1),
    )
    .expect("the fixture admits the authored purchase");
    assert_eq!(admitted.orders.len(), state.orders.len() + 1);
    let mut overbound = state;
    overbound.orders.resize(
        2 * MAX_MATERIAL_CIRCUIT_ROWS + 1,
        overbound.orders[0].clone(),
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&overbound),
        Err(MaterialCircuitError::RowLimit)
    );
}

#[test]
fn retail_admission_and_wire_keep_the_independent_unchanged_ceiling() {
    let state = mixed_order_state_counts(1, MAX_MATERIAL_CIRCUIT_ROWS - 1);
    let mut order = state.final_demand_orders[0].clone();
    order.order_id = order_id(MAX_MATERIAL_CIRCUIT_ROWS - 1);
    let (full, _) = babylon_material_circuit::admit_material_purchase(
        &state,
        MaterialPurchase::LocalFinalDemand(order.clone()),
        crate::money(1),
    )
    .expect("the fixture admits the authored purchase");
    assert_eq!(full.final_demand_orders.len(), MAX_MATERIAL_CIRCUIT_ROWS);
    let bytes = babylon_material_circuit::encode_material_circuit_state(&full)
        .expect("the canonical material state encodes");
    assert_eq!(
        babylon_material_circuit::decode_material_circuit_state(&bytes)
            .expect("the canonical material bytes decode"),
        full
    );
    order.order_id = order_id(MAX_MATERIAL_CIRCUIT_ROWS);
    assert_eq!(
        babylon_material_circuit::admit_material_purchase(
            &full,
            MaterialPurchase::LocalFinalDemand(order),
            crate::money(1)
        ),
        Err(MaterialCircuitError::RowLimit)
    );
    assert_eq!(
        babylon_material_circuit::encode_material_circuit_state(&full)
            .expect("the canonical material state encodes"),
        bytes
    );
}
