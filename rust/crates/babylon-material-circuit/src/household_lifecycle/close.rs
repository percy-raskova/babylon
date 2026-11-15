//! Carry the household close forward to the next material opening.
use super::model::{HouseholdLifecycleBook, HouseholdLifecycleReceipt, Result, INVALID};
use crate::{
    CircuitAccounting, HouseholdTimeAccounting, MaterialCatalog, MaterialCircuitError,
    MaterialCircuitState, RecurringEconomy,
};
impl MaterialCircuitState {
    /// Household-specific resident positions, when the source modeled age composition.
    #[must_use]
    pub fn household_lifecycle(&self) -> Option<&HouseholdLifecycleBook> {
        let CircuitAccounting::Monetary(e) = &self.accounting else {
            return None;
        };
        let HouseholdTimeAccounting::Modeled(t) = &e.household_time else {
            return None;
        };
        t.lifecycle.as_ref()
    }
}
pub(crate) fn close(
    catalog: &MaterialCatalog,
    state: &mut MaterialCircuitState,
) -> Result<Vec<HouseholdLifecycleReceipt>> {
    let CircuitAccounting::Monetary(e) = &mut state.accounting else {
        return Ok(vec![]);
    };
    let HouseholdTimeAccounting::Modeled(t) = &mut e.household_time else {
        return Ok(vec![]);
    };
    let Some(life) = t.lifecycle.as_mut() else {
        return Ok(vec![]);
    };
    let recurring = e.recurring.as_mut().ok_or(INVALID)?;
    let cohorts = &mut recurring.households;
    let mut results = Vec::with_capacity(life.positions.len());
    for p in &mut life.positions {
        let index = cohorts
            .binary_search_by_key(&p.principal_id, |r| r.principal_id)
            .map_err(|_| INVALID)?;
        let c = &mut cohorts[index];
        if c.persons != p.ages.persons()? {
            return Err(INVALID);
        }
        let row = p.next(life.rates, state.period, c.households)?;
        c.persons = row.closing.persons()?;
        c.households = row.closing_households;
        results.push(row);
    }
    if let Some(periods) = life.purchase_buffer_periods {
        rebase_purchases(catalog, recurring, life, periods)?;
    }
    Ok(results)
}

fn rebase_purchases(
    catalog: &MaterialCatalog,
    recurring: &mut RecurringEconomy,
    life: &HouseholdLifecycleBook,
    periods: u64,
) -> Result<()> {
    for purchase in &mut recurring.household_purchases {
        if life.position(purchase.principal_id).is_none() {
            continue;
        }
        let key = (purchase.principal_id, purchase.good_id, purchase.unit_id);
        let need = catalog
            .household_needs
            .binary_search_by_key(&key, |v| (v.principal_id, v.good_id, v.unit_id))
            .map_err(|_| INVALID)?;
        let cohort = recurring
            .households
            .binary_search_by_key(&purchase.principal_id, |v| v.principal_id)
            .map_err(|_| INVALID)?;
        let units =
            catalog.household_needs[need].required_quantity(&recurring.households[cohort])?;
        purchase.maximum_purchase = units
            .checked_mul(periods)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        purchase.target_closing_stock =
            if crate::services::is_service(catalog, purchase.good_id, purchase.unit_id) {
                0
            } else {
                units
            };
    }
    Ok(())
}
