use super::*;

const DELIVERY_LIMIT: usize = 131_072;
const ORDER_BYTES: usize = 32 + 1 + 4 * 32 + 5 * 8;
const BACKLOG_BYTES: usize = 32 + 8;

fn order_id(index: usize) -> OrderId {
    let mut bytes = [165; 32];
    bytes[24..].copy_from_slice(&u64::try_from(index).unwrap().to_be_bytes());
    OrderId::from_bytes(bytes)
}
fn local_orders(count: usize) -> MaterialCircuitState {
    let mut state = paid_state();
    state.accounting = CircuitAccounting::PhysicalControl;
    let template = state.orders[0].clone();
    state.orders = (0..count)
        .map(|index| OrderRow {
            order_id: order_id(index),
            ordered: 1,
            ..template.clone()
        })
        .collect();
    state.backlog = state
        .orders
        .iter()
        .map(|r| BacklogRow {
            order_id: r.order_id,
            quantity: 1,
        })
        .collect();
    state.inventory[0].quantity = u64::try_from(count).unwrap();
    state
}
#[test]
fn delivery_and_backlog_wire_reaches_its_bound_and_checks_the_entire_tail() {
    let state = local_orders(DELIVERY_LIMIT);
    let bytes = encode_material_circuit_state(&state).unwrap();
    assert_eq!(decode_material_circuit_state(&bytes).unwrap(), state);
    let start = bytes
        .windows(32)
        .position(|w| w == order_id(0).as_bytes())
        .unwrap();
    let last = start + (DELIVERY_LIMIT - 1) * ORDER_BYTES;
    let mut duplicate = bytes.clone();
    duplicate.copy_within(last - ORDER_BYTES..last - ORDER_BYTES + 32, last);
    assert_eq!(
        decode_material_circuit_state(&duplicate),
        Err(MaterialCircuitError::DuplicateRow)
    );
    let mut excess = bytes.clone();
    excess[start - 4..start]
        .copy_from_slice(&u32::try_from(DELIVERY_LIMIT + 1).unwrap().to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&excess),
        Err(MaterialCircuitError::WireLimit)
    );
    let backlog = start + DELIVERY_LIMIT * ORDER_BYTES;
    let mut corrupt_tail = bytes;
    let quantity = backlog + 4 + DELIVERY_LIMIT * BACKLOG_BYTES - 8;
    corrupt_tail[quantity..quantity + 8].copy_from_slice(&2_u64.to_be_bytes());
    assert_eq!(
        decode_material_circuit_state(&corrupt_tail),
        Err(MaterialCircuitError::BacklogInvariant)
    );
    assert_eq!(
        encode_material_circuit_state(&local_orders(DELIVERY_LIMIT + 1)),
        Err(MaterialCircuitError::RowLimit)
    );
}
#[test]
fn local_dispatch_and_rebuilt_backlog_include_the_last_delivery_above_the_old_cap() {
    let state = local_orders(DELIVERY_LIMIT);
    let closed = advance_material_circuit(&state).unwrap();
    assert_eq!(closed.local_transfers.len(), DELIVERY_LIMIT);
    assert_eq!(closed.state.orders.len(), DELIVERY_LIMIT);
    assert_eq!(
        closed.state.orders.last().unwrap().order_id,
        order_id(DELIVERY_LIMIT - 1)
    );
    assert!(closed
        .state
        .orders
        .iter()
        .all(|r| r.delivered == 1 && r.realized == 1));
    assert_eq!(closed.state.backlog.len(), DELIVERY_LIMIT);
    assert!(closed.state.backlog.iter().all(|r| r.quantity == 0));
    assert!(closed.state.freight.is_empty());
}
