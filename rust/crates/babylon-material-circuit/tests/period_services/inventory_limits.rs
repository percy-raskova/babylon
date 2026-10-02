use super::*;

fn padded_goods_inventory(include_output: bool) -> MaterialCircuitState {
    let mut state = opening();
    state.inventory[0].quantity = 2;
    let mut state = funded(state);
    if !include_output {
        state.inventory.retain(|r| r.good_id != good(3));
    }
    let missing = MAX_INVENTORY_ROWS - state.inventory.len();
    for index in 0..missing {
        let mut identity = [0; 32];
        identity[0] = 170;
        identity[24..].copy_from_slice(&u64::try_from(index / 3).unwrap().to_be_bytes());
        let extra_good = GoodId::from_bytes(identity);
        if index % 3 == 0 {
            state.commodities.push(CommodityDefinition {
                good_id: extra_good,
                unit_id: unit(4),
                kind: CommodityKind::Storable { grams_per_unit: 1 },
            });
        }
        state.inventory.push(InventoryRow {
            site_id: site(u8::try_from(index % 3 + 1).unwrap()),
            good_id: extra_good,
            unit_id: unit(4),
            quantity: 1,
        });
    }
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        unreachable!()
    };
    e.costs = HistoricalCostBook::open(
        &e.book,
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
fn temporary_service_outputs_and_grants_do_not_consume_durable_stock_row_budget() {
    let opening = padded_goods_inventory(true);
    let opening_bytes = encode_material_circuit_state(&opening).unwrap();
    let closed = advance_material_circuit(&opening).unwrap();
    assert_eq!(closed.state.inventory.len(), MAX_INVENTORY_ROWS);
    assert_eq!(
        closed
            .production
            .iter()
            .map(|r| r.produced_batches)
            .collect::<Vec<_>>(),
        vec![2, 1, 1]
    );
    assert!(closed
        .state
        .inventory
        .iter()
        .all(|r| r.good_id != good(1) && r.good_id != good(2)));
    assert!(closed
        .service_performance
        .iter()
        .all(|r| r.performed_quantity == 1 && r.used_quantity == 1));
    assert!(closed.state.service_orders.is_empty());
    let bytes = encode_material_circuit_state(&closed.state).unwrap();
    assert_eq!(decode_material_circuit_state(&bytes).unwrap(), closed.state);
    assert_eq!(
        encode_material_circuit_state(&opening).unwrap(),
        opening_bytes
    );
}

#[test]
fn a_new_durable_stock_key_above_its_own_limit_still_refuses_the_successor() {
    let opening = padded_goods_inventory(false);
    let opening_bytes = encode_material_circuit_state(&opening).unwrap();
    let detached = close_material_period(&opening).unwrap();
    assert_eq!(detached.inventory().len(), MAX_INVENTORY_ROWS + 1);
    assert!(detached
        .inventory()
        .iter()
        .all(|r| r.good_id != good(1) && r.good_id != good(2)));
    assert_eq!(
        advance_material_circuit(&opening),
        Err(MaterialCircuitError::RowLimit)
    );
    assert_eq!(
        encode_material_circuit_state(&opening).unwrap(),
        opening_bytes
    );
}
