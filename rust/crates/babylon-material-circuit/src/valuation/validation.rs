//! Reconcile physical identities and per-account net assets without recapture.
use super::{add, Result};
use crate::{AccountId, CircuitAccounting, MaterialCircuitError, MaterialCircuitState};
use std::collections::BTreeMap;

pub(crate) fn validate(state: &MaterialCircuitState) -> Result<()> {
    let CircuitAccounting::Monetary(economy) = &state.accounting else {
        return Ok(());
    };
    let costs = &economy.costs;
    let mut quantities: BTreeMap<_, _> = state
        .inventory
        .iter()
        .map(|r| {
            (
                (AccountId::Site(r.site_id), r.good_id, r.unit_id),
                r.quantity,
            )
        })
        .collect();
    if let Some(recurring) = &economy.recurring {
        for row in &recurring.household_stocks {
            quantities.insert(
                (
                    AccountId::Household(row.principal_id),
                    row.good_id,
                    row.unit_id,
                ),
                row.quantity,
            );
        }
    }
    if !quantities.keys().eq(costs.stocks.keys()) {
        return Err(MaterialCircuitError::ValuationInvariant);
    }
    for (key, quantity) in quantities {
        if quantity == 0 && costs.stocks[&key].micro_units() != 0 {
            return Err(MaterialCircuitError::ValuationInvariant);
        }
    }
    if costs.freight.len() != state.freight.len() {
        return Err(MaterialCircuitError::ValuationInvariant);
    }
    for lot in &state.freight {
        let &(owner, cost) = costs
            .freight
            .get(&lot.lot_id)
            .ok_or(MaterialCircuitError::ValuationInvariant)?;
        if owner != lot.source_site_id || (lot.quantity == 0 && cost.micro_units() != 0) {
            return Err(MaterialCircuitError::ValuationInvariant);
        }
    }
    for (account, assets) in costs.net_assets(&economy.book)? {
        let row = &costs.accounts[&account];
        if assets
            != add(
                add(row.opening_capital, row.contributed_capital)?,
                row.retained_earnings,
            )?
        {
            return Err(MaterialCircuitError::ValuationInvariant);
        }
    }
    Ok(())
}
