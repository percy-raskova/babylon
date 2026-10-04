//! One checked inventory ledger for production and freight.

use crate::{
    GoodId, InventoryRow, MaterialCircuitError, MaterialCircuitState, SiteId, UnitId,
    MAX_INVENTORY_ROWS,
};
use std::collections::BTreeMap;
// A close combines opening stocks, arriving freight, produced outputs and service grants.
// Planning combines stocks, future freight, prebooked services and bounded service policies.
// This temporary ledger is not a durable stock allowance: final canonical admission still
// checks MAX_INVENTORY_ROWS after all service quantities have expired.
const MAX_WORKING_INVENTORY_ROWS: usize =
    MAX_INVENTORY_ROWS + crate::MAX_SERVICE_ORDERS + 2 * crate::MAX_MATERIAL_CIRCUIT_ROWS;
pub(crate) type InventoryKey = (SiteId, GoodId, UnitId);
pub(crate) type InventoryLedger = BTreeMap<InventoryKey, u64>;

pub(crate) fn take_inventory(state: &mut MaterialCircuitState) -> InventoryLedger {
    std::mem::take(&mut state.inventory)
        .into_iter()
        .map(|row| ((row.site_id, row.good_id, row.unit_id), row.quantity))
        .collect()
}

pub(crate) fn publish_inventory(state: &mut MaterialCircuitState, inventory: InventoryLedger) {
    state.inventory = inventory
        .into_iter()
        .map(|((site_id, good_id, unit_id), quantity)| InventoryRow {
            site_id,
            good_id,
            unit_id,
            quantity,
        })
        .collect();
}

pub(crate) fn credit_inventory(
    inventory: &mut InventoryLedger,
    key: InventoryKey,
    quantity: u64,
) -> Result<(), MaterialCircuitError> {
    if quantity == 0 {
        return Ok(());
    }
    if let Some(current) = inventory.get_mut(&key) {
        *current = current
            .checked_add(quantity)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        return Ok(());
    }
    if inventory.len() >= MAX_WORKING_INVENTORY_ROWS {
        return Err(MaterialCircuitError::RowLimit);
    }
    inventory.insert(key, quantity);
    Ok(())
}

pub(crate) fn debit_inventory(
    inventory: &mut InventoryLedger,
    key: InventoryKey,
    quantity: u64,
    missing: MaterialCircuitError,
) -> Result<(), MaterialCircuitError> {
    if quantity == 0 {
        return Ok(());
    }
    let current = inventory.get_mut(&key).ok_or(missing)?;
    *current = current
        .checked_sub(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn key(index: usize) -> InventoryKey {
        let mut bytes = [0; 32];
        bytes[..8].copy_from_slice(&u64::try_from(index).unwrap().to_be_bytes());
        (
            SiteId::from_bytes(bytes),
            GoodId::from_bytes([1; 32]),
            UnitId::from_bytes([2; 32]),
        )
    }

    #[test]
    fn transient_inventory_has_its_own_exact_finite_insertion_bound() {
        let limit = 393_216;
        let mut inventory: InventoryLedger = (0..limit - 1).map(|i| (key(i), 1)).collect();
        credit_inventory(&mut inventory, key(limit - 1), 7).unwrap();
        assert_eq!(inventory.len(), limit);
        credit_inventory(&mut inventory, key(limit - 1), 3).unwrap();
        assert_eq!(inventory[&key(limit - 1)], 10);
        assert_eq!(
            credit_inventory(&mut inventory, key(limit), 1),
            Err(MaterialCircuitError::RowLimit)
        );
        assert_eq!(inventory.len(), limit);
        assert!(!inventory.contains_key(&key(limit)));
    }
}
