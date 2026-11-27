//! Checked resource cuts and a deterministic, single-increment-maximal residual fold.
use super::BTreeMap;
use super::FreightRequest;
use super::FreightResourceKey;
use super::MaterialCircuitError;
use crate::OrderId;

pub(super) type Groups = BTreeMap<FreightResourceKey, Vec<FreightRequest>>;

/// The resource a request uses for `quantity` units: `ceil(quantity x resource_per_unit / block_units)`.
fn used_by(quantity: u64, per_unit: u64, block: u64) -> Result<u128, MaterialCircuitError> {
    if block == 0 {
        return Err(MaterialCircuitError::FreightInvariant);
    }
    let total = u128::from(quantity)
        .checked_mul(u128::from(per_unit))
        .ok_or(MaterialCircuitError::Arithmetic)?;
    Ok(total.div_ceil(u128::from(block)))
}

/// The most units that `resource` of a resource serves: `floor(resource x block / per_unit)`.
fn units_served(resource: u128, per_unit: u64, block: u64) -> Result<u128, MaterialCircuitError> {
    resource
        .checked_mul(u128::from(block))
        .ok_or(MaterialCircuitError::Arithmetic)?
        .checked_div(u128::from(per_unit))
        .ok_or(MaterialCircuitError::FreightInvariant)
}

/// What a request's whole quantity uses of its resource.
pub(super) fn usage(request: &FreightRequest) -> Result<u128, MaterialCircuitError> {
    used_by(
        request.requested,
        request.resource_per_unit,
        request.block_units,
    )
}

/// The units of a request that `share` of its resource serves, at most the request.
pub(super) fn units_within(
    request: &FreightRequest,
    share: u64,
) -> Result<u64, MaterialCircuitError> {
    let units = units_served(
        u128::from(share),
        request.resource_per_unit,
        request.block_units,
    )?;
    Ok(u64::try_from(units.min(u128::from(request.requested))).unwrap_or(request.requested))
}

/// Every repeated membership incurs its actual coefficient. A request's native
/// bound cannot change between memberships of the same resource.
pub(super) fn aggregate(groups: &Groups) -> Result<Groups, MaterialCircuitError> {
    groups
        .iter()
        .map(|(key, requests)| {
            let mut merged: BTreeMap<usize, FreightRequest> = BTreeMap::new();
            for request in requests {
                if request.resource_per_unit == 0 || request.block_units == 0 {
                    return Err(MaterialCircuitError::FreightInvariant);
                }
                if let Some(row) = merged.get_mut(&request.order_index) {
                    if row.requested != request.requested
                        || row.block_units != 1
                        || request.block_units != 1
                    {
                        return Err(MaterialCircuitError::FreightInvariant);
                    }
                    row.resource_per_unit = row
                        .resource_per_unit
                        .checked_add(request.resource_per_unit)
                        .ok_or(MaterialCircuitError::Arithmetic)?;
                } else {
                    merged.insert(request.order_index, *request);
                }
            }
            Ok((*key, merged.into_values().collect()))
        })
        .collect()
}

/// Native identity is primary across domains; the explicit discriminator only
/// resolves equal identities. Source vector positions never choose priority.
pub(super) fn identity_order(identities: &[(OrderId, u8)]) -> Vec<usize> {
    let mut order: Vec<_> = (0..identities.len()).collect();
    order.sort_by_key(|&i| identities[i]);
    order
}

pub(super) struct Matrix {
    available: Vec<u64>,
    /// For each order, each resource it draws on, its coefficient and the block of units it is given for.
    cuts: Vec<Vec<(usize, u64, u64)>>,
    bounds: Vec<u64>,
}
impl Matrix {
    pub(super) fn new(
        groups: &Groups,
        bounds: Vec<u64>,
        mut availability: impl FnMut(FreightResourceKey) -> Result<u64, MaterialCircuitError>,
    ) -> Result<Self, MaterialCircuitError> {
        let mut matrix = Self {
            available: Vec::with_capacity(groups.len()),
            cuts: vec![Vec::new(); bounds.len()],
            bounds,
        };
        for (resource, (key, requests)) in groups.iter().enumerate() {
            matrix.available.push(availability(*key)?);
            for request in requests {
                if request.resource_per_unit == 0 || request.block_units == 0 {
                    return Err(MaterialCircuitError::FreightInvariant);
                }
                let cuts = matrix
                    .cuts
                    .get_mut(request.order_index)
                    .ok_or(MaterialCircuitError::FreightInvariant)?;
                cuts.push((resource, request.resource_per_unit, request.block_units));
            }
        }
        Ok(matrix)
    }
    /// Independent physical ceiling, excluding competition and handling labor.
    pub(super) fn ceilings(&self) -> Result<Vec<u64>, MaterialCircuitError> {
        self.cuts
            .iter()
            .zip(&self.bounds)
            .map(|(cuts, bound)| {
                cuts.iter().try_fold(*bound, |n, (r, c, b)| {
                    let served = units_served(u128::from(self.available[*r]), *c, *b)?;
                    Ok(n.min(u64::try_from(served).unwrap_or(u64::MAX)))
                })
            })
            .collect()
    }
    fn residuals(&self, allocations: &[u64]) -> Result<Vec<u64>, MaterialCircuitError> {
        if allocations.len() != self.bounds.len() {
            return Err(MaterialCircuitError::FreightInvariant);
        }
        let mut used = vec![0_u128; self.available.len()];
        for ((quantity, bound), cuts) in allocations.iter().zip(&self.bounds).zip(&self.cuts) {
            if quantity > bound || (*quantity > 0 && cuts.is_empty()) {
                return Err(MaterialCircuitError::FreightInvariant);
            }
            for (r, c, b) in cuts {
                used[*r] = used[*r]
                    .checked_add(used_by(*quantity, *c, *b)?)
                    .ok_or(MaterialCircuitError::Arithmetic)?;
            }
        }
        self.available
            .iter()
            .zip(used)
            .map(|(available, used)| {
                u64::try_from(
                    u128::from(*available)
                        .checked_sub(used)
                        .ok_or(MaterialCircuitError::FreightInvariant)?,
                )
                .map_err(|_| MaterialCircuitError::Arithmetic)
            })
            .collect()
    }
    /// The caller supplies a permutation in canonical identity order. Residuals
    /// only decrease: a candidate blocked after its maximal addition stays
    /// blocked. This does not optimize throughput or claim equal treatment.
    pub(super) fn augment(
        &self,
        allocations: &mut [u64],
        order: &[usize],
    ) -> Result<(), MaterialCircuitError> {
        let mut candidate = allocations.to_vec();
        self.augment_candidate(&mut candidate, order)?;
        allocations.copy_from_slice(&candidate);
        Ok(())
    }
    fn augment_candidate(
        &self,
        allocations: &mut [u64],
        order: &[usize],
    ) -> Result<(), MaterialCircuitError> {
        let mut remaining = self.residuals(allocations)?;
        if order.len() != allocations.len() {
            return Err(MaterialCircuitError::FreightInvariant);
        }
        let mut seen = vec![false; allocations.len()];
        for &i in order {
            let visited = seen
                .get_mut(i)
                .ok_or(MaterialCircuitError::FreightInvariant)?;
            if *visited {
                return Err(MaterialCircuitError::FreightInvariant);
            }
            *visited = true;
            if self.cuts[i].is_empty() {
                continue;
            }
            // The most units this order can reach, given what it already holds of each resource and what
            // is left: `floor((held + remaining) x block / coefficient)`, then less what it has.
            let mut reach = self.bounds[i];
            for (r, c, b) in &self.cuts[i] {
                let held = used_by(allocations[i], *c, *b)?;
                let room = held
                    .checked_add(u128::from(remaining[*r]))
                    .ok_or(MaterialCircuitError::Arithmetic)?;
                let served = units_served(room, *c, *b)?;
                reach = reach.min(u64::try_from(served).unwrap_or(u64::MAX));
            }
            let extra = reach.saturating_sub(allocations[i]);
            let before = allocations[i];
            allocations[i] = allocations[i]
                .checked_add(extra)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            for (r, c, b) in &self.cuts[i] {
                let spent = used_by(allocations[i], *c, *b)?
                    .checked_sub(used_by(before, *c, *b)?)
                    .ok_or(MaterialCircuitError::FreightInvariant)?;
                remaining[*r] = u64::try_from(
                    u128::from(remaining[*r])
                        .checked_sub(spent)
                        .ok_or(MaterialCircuitError::FreightInvariant)?,
                )
                .map_err(|_| MaterialCircuitError::Arithmetic)?;
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod controls {
    use super::*;
    use crate::{FinalDemandPrincipalId, GoodId, SiteId, UnitId};
    fn request(index: usize, bound: u64, coefficient: u64) -> FreightRequest {
        FreightRequest {
            order_index: index,
            requested: bound,
            resource_per_unit: coefficient,
            block_units: 1,
        }
    }
    fn matrix(available: Vec<u64>, cuts: Vec<Vec<(usize, u64)>>, bounds: Vec<u64>) -> Matrix {
        Matrix {
            available,
            cuts: cuts
                .into_iter()
                .map(|row| row.into_iter().map(|(r, c)| (r, c, 1)).collect())
                .collect(),
            bounds,
        }
    }
    #[test]
    fn donor_time_stock_and_funded_admission_bound_are_independent_cuts() {
        let principal = FinalDemandPrincipalId::from_bytes([1; 32]);
        let unit = UnitId::from_bytes([2; 32]);
        let good = GoodId::from_bytes([3; 32]);
        let groups = BTreeMap::from([
            (
                FreightResourceKey::HouseholdStock((principal, good, unit)),
                vec![request(0, 2, 1)],
            ),
            (
                FreightResourceKey::HouseholdTime(principal, unit),
                vec![request(0, 2, 2)],
            ),
        ]);
        let matrix = Matrix::new(&groups, vec![2], |key| {
            Ok(if matches!(key, FreightResourceKey::HouseholdTime(..)) {
                3
            } else {
                8
            })
        })
        .expect("the constructor accepts the authored fixture arguments");
        let mut actual = vec![0];
        matrix
            .augment(&mut actual, &[0])
            .expect("the fixture call `augment` succeeds for the authored inputs");
        assert_eq!(actual, [1]);
        let matrix = Matrix::new(&groups, vec![2], |_| Ok(100))
            .expect("the constructor accepts the authored fixture arguments");
        matrix
            .augment(&mut actual, &[0])
            .expect("the fixture call `augment` succeeds for the authored inputs");
        assert_eq!(actual, [2]);
    }
    #[test]
    fn repeated_actual_debits_are_summed_and_crossed_native_bounds_refuse() {
        let key =
            FreightResourceKey::Labor(SiteId::from_bytes([1; 32]), UnitId::from_bytes([2; 32]));
        let mut groups = BTreeMap::from([(key, vec![request(0, 3, 2), request(0, 3, 3)])]);
        let normalized = aggregate(&groups)
            .expect("the fixture call `aggregate` succeeds for the authored inputs");
        assert_eq!(normalized[&key][0].resource_per_unit, 5);
        let matrix = Matrix::new(&normalized, vec![3], |_| Ok(9))
            .expect("the constructor accepts the authored fixture arguments");
        let mut actual = vec![0];
        matrix
            .augment(&mut actual, &[0])
            .expect("the fixture call `augment` succeeds for the authored inputs");
        assert_eq!(actual, [1]);
        groups
            .get_mut(&key)
            .expect("the fixture holds the addressed entry")[1]
            .requested = 2;
        assert!(matches!(
            aggregate(&groups),
            Err(MaterialCircuitError::FreightInvariant)
        ));
        groups
            .get_mut(&key)
            .expect("the fixture holds the addressed entry")[0]
            .resource_per_unit = u64::MAX;
        groups
            .get_mut(&key)
            .expect("the fixture holds the addressed entry")[1]
            .requested = 3;
        assert!(matches!(
            aggregate(&groups),
            Err(MaterialCircuitError::Arithmetic)
        ));
    }
    #[test]
    fn residual_has_no_feasible_increment_for_small_two_cut_demands() {
        for available in 0..=8 {
            for bound in 0..=4 {
                let matrix = matrix(
                    vec![available, 3],
                    vec![vec![(0, 2)], vec![(0, 1), (1, 1)]],
                    vec![bound, bound],
                );
                let mut actual = vec![0, 0];
                matrix
                    .augment(&mut actual, &[0, 1])
                    .expect("the fixture call `augment` succeeds for the authored inputs");
                let remaining = matrix
                    .residuals(&actual)
                    .expect("the fixture call `residuals` succeeds for the authored inputs");
                for (i, cuts) in matrix.cuts.iter().enumerate() {
                    assert!(actual[i] == bound || cuts.iter().any(|(r, c, _)| remaining[*r] < *c));
                }
            }
        }
    }
    #[test]
    fn invalid_base_or_permutation_refuses_without_publishing_partial_grants() {
        let matrix = matrix(vec![3], vec![vec![(0, 1)], vec![(0, 1)]], vec![2, 2]);
        let mut actual = vec![0, 0];
        let before = actual.clone();
        assert_eq!(
            matrix.augment(&mut actual, &[0, 0]),
            Err(MaterialCircuitError::FreightInvariant)
        );
        assert_eq!(actual, before);
        actual = vec![2, 2];
        let before = actual.clone();
        assert_eq!(
            matrix.augment(&mut actual, &[0, 1]),
            Err(MaterialCircuitError::FreightInvariant)
        );
        assert_eq!(actual, before);
    }
    #[test]
    fn native_identity_precedes_domain_discriminator_in_residual_order() {
        let low = OrderId::from_bytes([1; 32]);
        let high = OrderId::from_bytes([2; 32]);
        let identities = [(high, 0), (low, 3), (low, 0), (low, 2), (low, 1)];
        assert_eq!(identity_order(&identities), [2, 4, 3, 1, 0]);
    }
}
