//! Exact shared order definitions and checked borrowed reservation joins.
use super::{ProductionFreightCapacityOrder, ProductionFreightOrderDefinition, ProductionSnapshot};
use std::collections::{BTreeMap, BTreeSet};
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FreightOrderError {
    Bound,
    Duplicate,
    Missing,
    Identity,
    Unused,
    Serialization,
    Arithmetic,
}
/// Identity covers every exact field, including u128 quantities and optional tags.
/// # Errors
/// Refuses serialization failure without narrowing any quantity.
pub fn freight_order_identity(
    order: &ProductionFreightCapacityOrder,
) -> Result<String, FreightOrderError> {
    let mut bytes = b"babylon.production-freight-order.v1\0".to_vec();
    serde_json::to_writer(&mut bytes, order).map_err(|_| FreightOrderError::Serialization)?;
    Ok(crate::michigan_economy::digest_hex(
        &babylon_kernel::content_digest::sha256_of(&bytes),
    ))
}
#[derive(Default)]
pub(crate) struct FreightOrderRegistry {
    definitions: BTreeMap<String, ProductionFreightCapacityOrder>,
}
impl FreightOrderRegistry {
    pub(crate) fn intern(
        &mut self,
        order: ProductionFreightCapacityOrder,
    ) -> Result<String, FreightOrderError> {
        let id = freight_order_identity(&order)?;
        if let Some(prior) = self.definitions.get(&id) {
            if prior != &order {
                return Err(FreightOrderError::Identity);
            }
        } else {
            if self.definitions.len() >= 2 * babylon_material_circuit::MAX_MATERIAL_ORDER_PRINCIPALS
            {
                return Err(FreightOrderError::Bound);
            }
            self.definitions.insert(id.clone(), order);
        }
        Ok(id)
    }
    pub(crate) fn finish(self) -> Vec<ProductionFreightOrderDefinition> {
        self.definitions
            .into_iter()
            .map(|(id, order)| ProductionFreightOrderDefinition { id, order })
            .collect()
    }
}
/// A snapshot-scoped index borrows full facts without expanding cloned vectors.
pub struct FreightOrderIndex<'a> {
    definitions: BTreeMap<&'a str, (usize, &'a ProductionFreightCapacityOrder)>,
}
impl<'a> FreightOrderIndex<'a> {
    /// Validate full tuple identities, every occurrence and exact definition use.
    /// # Errors
    /// Refuses bounds, invalid quantities, missing/unused/duplicate definitions and duplicate semantic orders.
    pub fn try_new(snapshot: &'a ProductionSnapshot) -> Result<Self, FreightOrderError> {
        if snapshot.freight_order_definitions.len()
            > 2 * babylon_material_circuit::MAX_MATERIAL_ORDER_PRINCIPALS
        {
            return Err(FreightOrderError::Bound);
        }
        let mut definitions = BTreeMap::new();
        for (ordinal, definition) in snapshot.freight_order_definitions.iter().enumerate() {
            if definition.id != freight_order_identity(&definition.order)? {
                return Err(FreightOrderError::Identity);
            }
            validate_quantities(&definition.order)?;
            if definitions
                .insert(definition.id.as_str(), (ordinal, &definition.order))
                .is_some()
            {
                return Err(FreightOrderError::Duplicate);
            }
        }
        let mut used = vec![false; definitions.len()];
        for account in &snapshot.freight_capacity_accounts {
            if let Some(completed) = &account.completed {
                for reservation in &completed.reservations {
                    let mut principals = BTreeSet::new();
                    for reference in &reservation.orders {
                        let (ordinal, order) = definitions
                            .get(reference.as_str())
                            .ok_or(FreightOrderError::Missing)?;
                        if !principals.insert((order.kind, order.order_id.as_str())) {
                            return Err(FreightOrderError::Duplicate);
                        }
                        used[*ordinal] = true;
                    }
                }
            }
        }
        if used.iter().any(|present| !present) {
            return Err(FreightOrderError::Unused);
        }
        Ok(Self { definitions })
    }
    /// Borrow an exact tuple; absent references must be refused by the view.
    #[must_use]
    pub fn get(&self, reference: &str) -> Option<&'a ProductionFreightCapacityOrder> {
        self.definitions.get(reference).map(|(_, order)| *order)
    }
}

fn validate_quantities(order: &ProductionFreightCapacityOrder) -> Result<(), FreightOrderError> {
    if order.grams_per_unit == 0
        || order.requested.checked_sub(order.dispatched) != Some(order.remaining_unshipped)
        || order.requested_grams != u128::from(order.requested) * u128::from(order.grams_per_unit)
        || order.dispatched.checked_mul(order.grams_per_unit) != Some(order.reserved_grams)
    {
        return Err(FreightOrderError::Arithmetic);
    }
    Ok(())
}
