//! What a seller has on offer at a moment of sale: its stock less what it owes, and for a merchant
//! also what its hands and its handling room can pass over.

use crate::inventory::{InventoryKey, InventoryLedger};
use crate::transition::merchant_admission;
use crate::{GoodId, MaterialCatalog, MaterialCircuitError, MaterialCircuitState, SiteId, UnitId};
use std::collections::BTreeMap;

/// What the seller owes to accepted orders: unshipped deliveries and unfilled retail orders.
pub(crate) fn sale_commitments(
    state: &MaterialCircuitState,
) -> Result<InventoryLedger, MaterialCircuitError> {
    let mut rows = InventoryLedger::new();
    for order in &state.orders {
        let quantity = order
            .ordered
            .checked_sub(order.shipped)
            .ok_or(MaterialCircuitError::EquipmentInvariant)?;
        add(
            &mut rows,
            (order.supplier_site_id, order.good_id, order.unit_id),
            quantity,
        )?;
    }
    for order in &state.final_demand_orders {
        let quantity = order
            .ordered
            .checked_sub(order.fulfilled)
            .ok_or(MaterialCircuitError::EquipmentInvariant)?;
        add(
            &mut rows,
            (order.retailer_site_id, order.good_id, order.unit_id),
            quantity,
        )?;
    }
    Ok(rows)
}

fn add(
    rows: &mut InventoryLedger,
    key: (SiteId, GoodId, UnitId),
    quantity: u64,
) -> Result<(), MaterialCircuitError> {
    let value = rows.entry(key).or_default();
    *value = value
        .checked_add(quantity)
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(())
}

/// A merchant's hands and room at one moment of sale.
#[derive(Debug, Clone, Copy)]
struct Handling {
    hours: u64,
    grams: u64,
}

/// Tracks, for one moment of sale, what each seller still has on offer.
#[derive(Debug)]
pub(crate) struct Offer<'a> {
    catalog: &'a MaterialCatalog,
    stock: InventoryLedger,
    merchants: BTreeMap<SiteId, Handling>,
}

impl<'a> Offer<'a> {
    /// Read the stock, the hours and the room as they stand, less what accepted orders will need.
    ///
    /// # Errors
    /// `EquipmentInvariant` for an order shipped beyond its size, `MerchantInvariant` for an owed
    /// order of a merchant with no handling coefficient, and `Arithmetic` on overflow.
    pub(crate) fn new(
        catalog: &'a MaterialCatalog,
        state: &MaterialCircuitState,
    ) -> Result<Self, MaterialCircuitError> {
        let owed = sale_commitments(state)?;
        let mut stock: InventoryLedger = state
            .inventory
            .iter()
            .map(|row| ((row.site_id, row.good_id, row.unit_id), row.quantity))
            .collect();
        // A seller that owes more than it holds has nothing on offer; the shortfall is the
        // shipping pass's to share, so the mask stops at zero.
        for (key, pledged) in &owed {
            if let Some(quantity) = stock.get_mut(key) {
                *quantity = quantity.saturating_sub(*pledged);
            }
        }
        let mut merchants = BTreeMap::new();
        for merchant in &catalog.merchants {
            let mut hours = state
                .labor
                .binary_search_by_key(
                    &(state.period, merchant.site_id, merchant.labor_unit_id),
                    |r| (r.period, r.site_id, r.unit_id),
                )
                .map_or(0, |index| state.labor[index].available);
            let mut grams = crate::capacity::shared_available(
                catalog,
                state,
                state.period,
                merchant.capacity_id,
            )?;
            for (&(site, good, unit), &quantity) in &owed {
                if site != merchant.site_id {
                    continue;
                }
                let (needs_hours, needs_grams) =
                    Self::needs(catalog, site, (good, unit), quantity)?;
                hours = hours.saturating_sub(needs_hours);
                grams = grams.saturating_sub(needs_grams);
            }
            merchants.insert(merchant.site_id, Handling { hours, grams });
        }
        Ok(Self {
            catalog,
            stock,
            merchants,
        })
    }

    /// The hours and the grams that handling `quantity` of a product takes.
    fn needs(
        catalog: &MaterialCatalog,
        site: SiteId,
        product: (GoodId, UnitId),
        quantity: u64,
    ) -> Result<(u64, u64), MaterialCircuitError> {
        let hours = merchant_admission::hours_per_unit(catalog, site, product.0, product.1)?;
        let grams = catalog.grams_per_unit(product.0, product.1)?;
        let scale = |per_unit: u64| {
            per_unit
                .checked_mul(quantity)
                .ok_or(MaterialCircuitError::Arithmetic)
        };
        Ok((scale(hours)?, scale(grams)?))
    }

    /// What the seller can sell of this product now.
    ///
    /// # Errors
    /// `MerchantInvariant` for a merchant's product with no handling coefficient.
    pub(crate) fn supply(
        &self,
        site: SiteId,
        good: GoodId,
        unit: UnitId,
    ) -> Result<u64, MaterialCircuitError> {
        let key: InventoryKey = (site, good, unit);
        let stock = self.stock.get(&key).copied().unwrap_or(0);
        let Some(hands) = self.merchants.get(&site) else {
            return Ok(stock);
        };
        let (hours, grams) = Self::needs(self.catalog, site, (good, unit), 1)?;
        let by_hours = hands
            .hours
            .checked_div(hours)
            .ok_or(MaterialCircuitError::MerchantInvariant)?;
        let by_room = hands
            .grams
            .checked_div(grams)
            .ok_or(MaterialCircuitError::MerchantInvariant)?;
        Ok(stock.min(by_hours).min(by_room))
    }

    /// Take a sale out of the stock, the hours and the room.
    ///
    /// # Errors
    /// `MarketClearingInvariant` when the sale is more than the seller had on offer.
    pub(crate) fn take(
        &mut self,
        site: SiteId,
        good: GoodId,
        unit: UnitId,
        quantity: u64,
    ) -> Result<(), MaterialCircuitError> {
        if quantity > self.supply(site, good, unit)? {
            return Err(MaterialCircuitError::MarketClearingInvariant);
        }
        let stock = self
            .stock
            .get_mut(&(site, good, unit))
            .ok_or(MaterialCircuitError::MarketClearingInvariant)?;
        *stock -= quantity;
        if let Some(hands) = self.merchants.get_mut(&site) {
            let (hours, grams) = Self::needs(self.catalog, site, (good, unit), quantity)?;
            hands.hours -= hours;
            hands.grams -= grams;
        }
        Ok(())
    }
}
