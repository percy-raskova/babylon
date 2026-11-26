//! Leaf implementation for the parent module; public paths stay on the parent.

use super::CommodityDefinition;
use super::CommodityKind;
use super::ServiceInputPolicy;
use super::ServiceStage;

use crate::inventory::InventoryLedger;
use crate::CircuitAccounting;
use crate::MaterialCatalog;
use crate::SiteId;
use crate::{GoodId, MaterialCircuitError, MaterialCircuitState, ProcessOutput, UnitId};
use std::collections::BTreeMap;
use std::result::Result as StdResult;

pub(crate) type Result<T> = StdResult<T, MaterialCircuitError>;

impl CommodityDefinition {
    /// Positive shipment mass exists only for stored commodities.
    /// # Errors
    /// Refuses service units and nonpositive captured mass.
    pub fn grams_per_unit(&self) -> Result<u64> {
        match self.kind {
            CommodityKind::Storable { grams_per_unit } if grams_per_unit > 0 => Ok(grams_per_unit),
            _ => Err(MaterialCircuitError::MassInvariant),
        }
    }
}

pub(crate) fn kind(catalog: &MaterialCatalog, good: GoodId, unit: UnitId) -> Result<CommodityKind> {
    catalog
        .commodities
        .binary_search_by_key(&(good, unit), |r| (r.good_id, r.unit_id))
        .ok()
        .map(|i| catalog.commodities[i].kind)
        .ok_or(MaterialCircuitError::MassInvariant)
}

pub(crate) fn stage(
    catalog: &MaterialCatalog,
    output: &ProcessOutput,
) -> Result<Option<ServiceStage>> {
    Ok(match kind(catalog, output.good_id, output.unit_id)? {
        CommodityKind::Storable { .. } => None,
        CommodityKind::PeriodService { stage } => Some(stage),
    })
}

pub(crate) fn is_service(catalog: &MaterialCatalog, good: GoodId, unit: UnitId) -> bool {
    matches!(
        kind(catalog, good, unit),
        Ok(CommodityKind::PeriodService { .. })
    )
}

/// Planning may count a finite requested grant; actual work must obtain it anew.
pub(crate) fn planning_grants(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    period: u64,
    inventory: &mut InventoryLedger,
) -> Result<()> {
    let requirements = input_requirements(catalog, state, true)?;
    let mut future = BTreeMap::new();
    for order in &state.service_orders {
        if order.performance_period == period {
            if let crate::AccountId::Site(site) = order.buyer {
                crate::inventory::credit_inventory(
                    &mut future,
                    (site, order.good_id, order.unit_id),
                    order.quantity,
                )?;
            }
        }
    }
    if matches!(state.accounting, CircuitAccounting::Monetary(_)) {
        for ((buyer, _, good, unit), share) in required_inputs(catalog, &requirements)? {
            crate::inventory::credit_inventory(&mut future, (buyer, good, unit), share)?;
        }
    }
    for (key, q) in future {
        crate::inventory::credit_inventory(inventory, key, q)?;
    }
    Ok(())
}

pub(crate) type InputRequirements = BTreeMap<(SiteId, GoodId, UnitId), u128>;

/// Build once per planning boundary; coefficients preserve their declared native units.
pub(crate) fn input_requirements(
    catalog: &MaterialCatalog,
    state: &MaterialCircuitState,
    next_plan: bool,
) -> Result<InputRequirements> {
    let owners: BTreeMap<_, _> = catalog
        .process_outputs
        .iter()
        .map(|o| (o.process_id, o.site_id))
        .collect();
    let plans: BTreeMap<_, _> = if next_plan {
        match &state.accounting {
            CircuitAccounting::Monetary(e) => e
                .recurring
                .as_ref()
                .map(|r| {
                    r.production
                        .iter()
                        .map(|p| (p.process_id, p.planned_batches))
                        .collect()
                })
                .unwrap_or_default(),
            CircuitAccounting::PhysicalControl => BTreeMap::new(),
        }
    } else {
        state
            .production_commitments
            .iter()
            .filter(|p| p.period == state.period)
            .map(|p| (p.process_id, p.planned_batches))
            .collect()
    };
    let mut result = InputRequirements::new();
    for coefficient in &catalog.input_coefficients {
        if !is_service(catalog, coefficient.good_id, coefficient.unit_id) {
            continue;
        }
        let site = *owners
            .get(&coefficient.process_id)
            .ok_or(MaterialCircuitError::ProcessInvariant)?;
        let batches = plans.get(&coefficient.process_id).copied().unwrap_or(0);
        let requested = u128::from(batches) * u128::from(coefficient.quantity_per_batch);
        let quantity = result
            .entry((site, coefficient.good_id, coefficient.unit_id))
            .or_default();
        *quantity = quantity
            .checked_add(requested)
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    Ok(result)
}

/// A buyer's requirement of one service shared over its rows of that service, in the rows' order (provider id):
/// the requirement, capped at the sum of the rows' caps (`quantity_per_period`), times a row's cap over that sum,
/// rounded down; the units left over one each to the rows with the largest remainders, the lower provider id on a
/// tie; each row's share then capped by its own `maximum_purchase`. With one row: `min(requirement, cap,
/// maximum_purchase)`, today's figure.
/// # Errors
/// `Arithmetic` on overflow; `ServiceInvariant` for no row.
pub(crate) fn input_shares(requirement: u128, rows: &[&ServiceInputPolicy]) -> Result<Vec<u64>> {
    if rows.is_empty() {
        return Err(MaterialCircuitError::ServiceInvariant);
    }
    let caps = total_caps(rows)?;
    let dealt = requirement.min(caps);
    let mut shares = Vec::with_capacity(rows.len());
    let mut remainders = Vec::with_capacity(rows.len());
    let mut floors = 0_u128;
    for (index, row) in rows.iter().enumerate() {
        let product = dealt
            .checked_mul(u128::from(row.quantity_per_period))
            .ok_or(MaterialCircuitError::Arithmetic)?;
        let floor = product.checked_div(caps).unwrap_or(0);
        let remainder = product.checked_rem(caps).unwrap_or(0);
        floors = floors
            .checked_add(floor)
            .ok_or(MaterialCircuitError::Arithmetic)?;
        shares.push(floor);
        remainders.push((std::cmp::Reverse(remainder), index));
    }
    remainders.sort_unstable();
    let left = usize::try_from(dealt - floors).map_err(|_| MaterialCircuitError::Arithmetic)?;
    for &(_, index) in remainders.iter().take(left) {
        shares[index] += 1;
    }
    shares
        .iter()
        .zip(rows)
        .map(|(share, row)| {
            u64::try_from((*share).min(u128::from(row.maximum_purchase)))
                .map_err(|_| MaterialCircuitError::Arithmetic)
        })
        .collect()
}

/// The sum of the rows' caps.
fn total_caps(rows: &[&ServiceInputPolicy]) -> Result<u128> {
    rows.iter().try_fold(0_u128, |sum, row| {
        sum.checked_add(u128::from(row.quantity_per_period))
            .ok_or(MaterialCircuitError::Arithmetic)
    })
}

/// Every row's share, by (buyer, provider, good, unit), built once per planning boundary from `input_requirements`.
/// Captured policy quantities cap the recipe-derived requirement; they do not create demand.
/// # Errors
/// `Arithmetic` on overflow.
pub(crate) fn required_inputs(
    catalog: &MaterialCatalog,
    requirements: &InputRequirements,
) -> Result<BTreeMap<(SiteId, SiteId, GoodId, UnitId), u64>> {
    let mut groups: BTreeMap<(SiteId, GoodId, UnitId), Vec<&ServiceInputPolicy>> = BTreeMap::new();
    for row in &catalog.service_inputs {
        groups
            .entry((row.buyer_site_id, row.good_id, row.unit_id))
            .or_default()
            .push(row);
    }
    let mut result = BTreeMap::new();
    for (key, mut rows) in groups {
        rows.sort_by_key(|row| row.provider_site_id);
        let requirement = requirements.get(&key).copied().unwrap_or(0);
        for (row, share) in rows.iter().zip(input_shares(requirement, &rows)?) {
            result.insert((key.0, row.provider_site_id, key.1, key.2), share);
        }
    }
    Ok(result)
}

/// The units of a service `site` can have for its requirement from its rows, each row offering `available[i]` (what
/// the provider can make less what its other buyers take, capped by the row's cap and maximum): a requirement up to
/// which every share fits, min over rows of floor(available[i] x sum of caps / cap[i]); with one row, `available[0]`.
/// It is a safe bound, not always the largest (caps 70 and 30 with availabilities 70 and 10 give 33, and 34, shared
/// 24 and 10, also fits).
/// # Errors
/// `Arithmetic` on overflow; `ServiceInvariant` for no row or a row count that differs from `available`.
pub(crate) fn shared_availability(rows: &[&ServiceInputPolicy], available: &[u64]) -> Result<u64> {
    if rows.is_empty() || rows.len() != available.len() {
        return Err(MaterialCircuitError::ServiceInvariant);
    }
    if let ([_], [only]) = (rows, available) {
        return Ok(*only);
    }
    let caps = total_caps(rows)?;
    let mut fits = u128::from(u64::MAX);
    for (row, have) in rows.iter().zip(available) {
        if row.quantity_per_period == 0 {
            continue;
        }
        let bound = u128::from(*have)
            .checked_mul(caps)
            .ok_or(MaterialCircuitError::Arithmetic)?
            / u128::from(row.quantity_per_period);
        fits = fits.min(bound);
    }
    u64::try_from(fits).map_err(|_| MaterialCircuitError::Arithmetic)
}

/// The price a buyer pays a unit of a service over its rows: ceil(sum(cap x posted price) / sum of caps); with one
/// row the provider's price.
/// # Errors
/// `Arithmetic` on overflow; `ServiceInvariant` for no row, no caps or a price count that differs from the rows.
pub(crate) fn shared_price(rows: &[&ServiceInputPolicy], prices: &[i128]) -> Result<i128> {
    if rows.is_empty() || rows.len() != prices.len() {
        return Err(MaterialCircuitError::ServiceInvariant);
    }
    if let [only] = prices {
        return Ok(*only);
    }
    let caps = i128::try_from(total_caps(rows)?).map_err(|_| MaterialCircuitError::Arithmetic)?;
    if caps == 0 {
        return Err(MaterialCircuitError::ServiceInvariant);
    }
    let mut sum = 0_i128;
    for (row, price) in rows.iter().zip(prices) {
        sum = i128::from(row.quantity_per_period)
            .checked_mul(*price)
            .and_then(|weighted| sum.checked_add(weighted))
            .ok_or(MaterialCircuitError::Arithmetic)?;
    }
    let whole = sum / caps;
    Ok(if sum % caps > 0 { whole + 1 } else { whole })
}

#[cfg(test)]
mod tests {
    use super::*;
    use babylon_kernel::currency::Currency;

    fn row(provider: u8, cap: u64, maximum: u64) -> ServiceInputPolicy {
        ServiceInputPolicy {
            buyer_site_id: SiteId::from_bytes([1; 32]),
            provider_site_id: SiteId::from_bytes([provider; 32]),
            good_id: GoodId::from_bytes([2; 32]),
            unit_id: UnitId::from_bytes([3; 32]),
            quantity_per_period: cap,
            maximum_purchase: maximum,
            cash_floor: Currency::from_micro_units(0),
        }
    }

    fn shares(requirement: u128, rows: &[ServiceInputPolicy]) -> Result<Vec<u64>> {
        input_shares(requirement, &rows.iter().collect::<Vec<_>>())
    }

    #[test]
    fn a_requirement_is_shared_by_the_caps() {
        let rows = [row(10, 70, 70), row(11, 30, 30)];
        assert_eq!(shares(100, &rows), Ok(vec![70, 30]));
        assert_eq!(shares(50, &rows), Ok(vec![35, 15]));
        // Floors 35 and 15, remainders 70 and 30: the unit left goes to the first.
        assert_eq!(shares(51, &rows), Ok(vec![36, 15]));
        assert_eq!(shares(120, &rows), Ok(vec![70, 30]));
        // A maximum cuts its row's share and is not dealt to the other.
        let cut = [row(10, 70, 20), row(11, 30, 30)];
        assert_eq!(shares(100, &cut), Ok(vec![20, 30]));
        // Equal remainders go to the lower provider ids.
        let ones = [row(10, 1, 1), row(11, 1, 1), row(12, 1, 1)];
        assert_eq!(shares(2, &ones), Ok(vec![1, 1, 0]));
        // One row is today's min of the three.
        let one = [row(10, 40, 25)];
        assert_eq!(
            [10, 30, 50].map(|requirement| shares(requirement, &one)),
            [Ok(vec![10]), Ok(vec![25]), Ok(vec![25])]
        );
        assert_eq!(shares(5, &[]), Err(MaterialCircuitError::ServiceInvariant));
    }

    fn can_give(rows: &[ServiceInputPolicy], available: &[u64]) -> Result<u64> {
        shared_availability(&rows.iter().collect::<Vec<_>>(), available)
    }

    #[test]
    fn what_two_providers_can_give() {
        let rows = [row(10, 70, 70), row(11, 30, 30)];
        assert_eq!(can_give(&rows, &[70, 30]), Ok(100));
        assert_eq!(can_give(&rows, &[35, 30]), Ok(50));
        assert_eq!(can_give(&rows, &[70, 10]), Ok(33));
        assert_eq!(can_give(&rows[..1], &[17]), Ok(17));
        assert_eq!(
            can_give(&rows, &[70]),
            Err(MaterialCircuitError::ServiceInvariant)
        );
    }

    fn price_of(rows: &[ServiceInputPolicy], prices: &[i128]) -> Result<i128> {
        shared_price(&rows.iter().collect::<Vec<_>>(), prices)
    }

    #[test]
    fn the_weighted_price_is_rounded_up() {
        let rows = [row(10, 70, 70), row(11, 30, 30)];
        assert_eq!(price_of(&rows, &[10_000_000, 4_000_000]), Ok(8_200_000));
        let two_one = [row(10, 2, 2), row(11, 1, 1)];
        assert_eq!(price_of(&two_one, &[10, 11]), Ok(11));
        assert_eq!(price_of(&rows[..1], &[7_654_321]), Ok(7_654_321));
    }
}
