//! Checked resource cuts and a deterministic, single-increment-maximal residual fold.
use super::BTreeMap;
use super::FreightRequest;
use super::FreightResourceKey;
use super::MaterialCircuitError;
use crate::OrderId;

pub(super) type Groups = BTreeMap<FreightResourceKey, Vec<FreightRequest>>;

/// Every repeated membership incurs its actual coefficient. A request's native
/// bound cannot change between memberships of the same resource.
pub(super) fn aggregate(groups: &Groups) -> Result<Groups, MaterialCircuitError> {
    groups
        .iter()
        .map(|(key, requests)| {
            let mut merged: BTreeMap<usize, FreightRequest> = BTreeMap::new();
            for request in requests {
                if request.resource_per_unit == 0 {
                    return Err(MaterialCircuitError::FreightInvariant);
                }
                if let Some(row) = merged.get_mut(&request.order_index) {
                    if row.requested != request.requested {
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
    cuts: Vec<Vec<(usize, u64)>>,
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
                if request.resource_per_unit == 0 {
                    return Err(MaterialCircuitError::FreightInvariant);
                }
                let cuts = matrix
                    .cuts
                    .get_mut(request.order_index)
                    .ok_or(MaterialCircuitError::FreightInvariant)?;
                cuts.push((resource, request.resource_per_unit));
            }
        }
        Ok(matrix)
    }
    /// Independent physical ceiling, excluding competition and handling labor.
    pub(super) fn ceilings(&self) -> Vec<u64> {
        self.cuts
            .iter()
            .zip(&self.bounds)
            .map(|(cuts, bound)| {
                cuts.iter()
                    .fold(*bound, |n, (r, c)| n.min(self.available[*r] / c))
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
            for (r, c) in cuts {
                used[*r] = used[*r]
                    .checked_add(u128::from(*quantity) * u128::from(*c))
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
            let extra = self.cuts[i]
                .iter()
                .fold(self.bounds[i] - allocations[i], |n, (r, c)| {
                    n.min(remaining[*r] / c)
                });
            allocations[i] = allocations[i]
                .checked_add(extra)
                .ok_or(MaterialCircuitError::Arithmetic)?;
            for (r, c) in &self.cuts[i] {
                remaining[*r] = remaining[*r]
                    .checked_sub(
                        extra
                            .checked_mul(*c)
                            .ok_or(MaterialCircuitError::Arithmetic)?,
                    )
                    .ok_or(MaterialCircuitError::FreightInvariant)?;
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
        }
    }
    fn matrix(available: Vec<u64>, cuts: Vec<Vec<(usize, u64)>>, bounds: Vec<u64>) -> Matrix {
        Matrix {
            available,
            cuts,
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
        .unwrap();
        let mut actual = vec![0];
        matrix.augment(&mut actual, &[0]).unwrap();
        assert_eq!(actual, [1]);
        let matrix = Matrix::new(&groups, vec![2], |_| Ok(100)).unwrap();
        matrix.augment(&mut actual, &[0]).unwrap();
        assert_eq!(actual, [2]);
    }
    #[test]
    fn repeated_actual_debits_are_summed_and_crossed_native_bounds_refuse() {
        let key =
            FreightResourceKey::Labor(SiteId::from_bytes([1; 32]), UnitId::from_bytes([2; 32]));
        let mut groups = BTreeMap::from([(key, vec![request(0, 3, 2), request(0, 3, 3)])]);
        let normalized = aggregate(&groups).unwrap();
        assert_eq!(normalized[&key][0].resource_per_unit, 5);
        let matrix = Matrix::new(&normalized, vec![3], |_| Ok(9)).unwrap();
        let mut actual = vec![0];
        matrix.augment(&mut actual, &[0]).unwrap();
        assert_eq!(actual, [1]);
        groups.get_mut(&key).unwrap()[1].requested = 2;
        assert!(matches!(
            aggregate(&groups),
            Err(MaterialCircuitError::FreightInvariant)
        ));
        groups.get_mut(&key).unwrap()[0].resource_per_unit = u64::MAX;
        groups.get_mut(&key).unwrap()[1].requested = 3;
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
                matrix.augment(&mut actual, &[0, 1]).unwrap();
                let remaining = matrix.residuals(&actual).unwrap();
                for (i, cuts) in matrix.cuts.iter().enumerate() {
                    assert!(actual[i] == bound || cuts.iter().any(|(r, c)| remaining[*r] < *c));
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
