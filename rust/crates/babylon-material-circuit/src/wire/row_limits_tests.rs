use crate::wire;
use crate::wire::append_rows;
use crate::wire::decode_input_coefficients;
use crate::wire::decode_inventory;
use crate::wire::decode_stage_capacities;
use crate::wire::decode_supplier_routes;
use crate::wire::services;
use crate::wire::Cursor;
use crate::GoodId;
use crate::InventoryRow;
use crate::MaterialCircuitError;
use crate::SiteId;
use crate::UnitId;
use crate::MAX_MATERIAL_CIRCUIT_ROWS;

#[test]
fn inventory_tail_above_the_old_shared_ceiling_roundtrips_completely() {
    let rows: Vec<_> = (0..MAX_MATERIAL_CIRCUIT_ROWS + 2)
        .map(|index| {
            let mut id = [0; 32];
            id[..8].copy_from_slice(
                &u64::try_from(index)
                    .expect("the fixture value fits the target range")
                    .to_be_bytes(),
            );
            InventoryRow {
                site_id: SiteId::from_bytes(id),
                good_id: GoodId::from_bytes([1; 32]),
                unit_id: UnitId::from_bytes([2; 32]),
                quantity: u64::try_from(index).expect("the fixture value fits the target range"),
            }
        })
        .collect();
    let mut bytes = Vec::new();
    wire::append_inventory(&mut bytes, &rows)
        .expect("the fixture call `append_inventory` succeeds for the authored inputs");
    let mut cursor = Cursor::new(&bytes);
    assert_eq!(
        decode_inventory(&mut cursor).expect("the canonical bytes decode into the declared type"),
        rows
    );
    cursor
        .finish()
        .expect("the fixture finishes the authored period");
    assert_eq!(
        decode_inventory(&mut Cursor::new(&bytes[..bytes.len() - 1])),
        Err(MaterialCircuitError::WireTruncated)
    );
}

#[test]
fn family_excess_refuses_before_allocating_or_decoding_row_payloads() {
    fn header(limit: usize) -> [u8; 4] {
        u32::try_from(limit + 1)
            .expect("the fixture value fits the target range")
            .to_be_bytes()
    }
    assert_eq!(
        decode_inventory(&mut Cursor::new(&header(crate::MAX_INVENTORY_ROWS))),
        Err(MaterialCircuitError::WireLimit)
    );
    assert_eq!(
        decode_input_coefficients(&mut Cursor::new(&header(crate::MAX_INPUT_COEFFICIENTS))),
        Err(MaterialCircuitError::WireLimit)
    );
    assert_eq!(
        decode_supplier_routes(&mut Cursor::new(&header(crate::MAX_SUPPLIER_ROUTES))),
        Err(MaterialCircuitError::WireLimit)
    );
    assert_eq!(
        decode_stage_capacities(&mut Cursor::new(&header(
            crate::MAX_ROUTE_CAPACITY_MEMBERSHIPS
        ))),
        Err(MaterialCircuitError::WireLimit)
    );
    assert_eq!(
        services::decode_connections(&mut Cursor::new(&header(crate::MAX_SERVICE_CONNECTIONS))),
        Err(MaterialCircuitError::WireLimit)
    );
}

#[test]
fn overbound_encoding_leaves_existing_bytes_untouched() {
    let row = InventoryRow {
        site_id: SiteId::from_bytes([0; 32]),
        good_id: GoodId::from_bytes([1; 32]),
        unit_id: UnitId::from_bytes([2; 32]),
        quantity: 0,
    };
    let mut bytes = vec![7, 8, 9];
    assert_eq!(
        wire::append_inventory(&mut bytes, &vec![row; crate::MAX_INVENTORY_ROWS + 1]),
        Err(MaterialCircuitError::WireLimit)
    );
    assert_eq!(bytes, vec![7, 8, 9]);
    assert_eq!(
        append_rows(
            &mut bytes,
            &vec![0_u8; MAX_MATERIAL_CIRCUIT_ROWS + 1],
            |b, r| b.push(*r)
        ),
        Err(MaterialCircuitError::WireLimit)
    );
    assert_eq!(bytes, vec![7, 8, 9]);
}
