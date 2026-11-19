//! Experiment-only subdivision of the occupied commercial strata after the normal site assignment.
use super::{
    CompanyCapture, CompanyCaptureError, CompanyKey, CompanyMember, CompanyPopulation,
    ExperimentalPopulation,
};
use std::cmp::{Ordering, Reverse};
use std::collections::BTreeMap;
use std::num::NonZeroU16;

struct Stratum {
    key: CompanyKey,
    members: Vec<CompanyMember>,
    employment: u64,
    positive_sites: usize,
    seats: u16,
}
impl Stratum {
    /// Compare the exact employment per next controller. An exact tie uses the smaller original key.
    fn priority(&self, other: &Self) -> Ordering {
        let left = u128::from(self.employment) * (u128::from(other.seats) + 1);
        let right = u128::from(other.employment) * (u128::from(self.seats) + 1);
        left.cmp(&right).then_with(|| other.key.cmp(&self.key))
    }
    fn split(mut self, roster: &mut CompanyCapture) -> Result<(), CompanyCaptureError> {
        self.members
            .sort_unstable_by_key(|m| (Reverse(m.employed), m.site));
        let mut children: Vec<_> = (1..=self.seats)
            .map(|index| CompanyPopulation {
                key: CompanyKey {
                    experiment_partition: NonZeroU16::new(index),
                    ..self.key
                },
                employed: 0,
                sites: 0,
            })
            .collect();
        for mut site in self.members {
            let child = children
                .iter_mut()
                .min_by_key(|c| (c.employed, c.sites, c.key))
                .ok_or(CompanyCaptureError::Arithmetic)?;
            child.employed = child
                .employed
                .checked_add(site.employed)
                .ok_or(CompanyCaptureError::Arithmetic)?;
            child.sites = child
                .sites
                .checked_add(1)
                .ok_or(CompanyCaptureError::Arithmetic)?;
            site.company = child.key;
            roster.members.push(site);
        }
        if children.iter().any(|c| c.employed == 0) {
            return Err(CompanyCaptureError::InvalidTargets);
        }
        roster.companies.extend(children);
        Ok(())
    }
}

pub(in crate::national_economy) fn partition(
    mut base: CompanyCapture,
    goal: ExperimentalPopulation,
) -> Result<CompanyCapture, CompanyCaptureError> {
    let mut strata: BTreeMap<_, _> = base
        .companies
        .drain(..)
        .map(|company| {
            (
                company.key,
                Stratum {
                    key: company.key,
                    employment: company.employed,
                    positive_sites: 0,
                    seats: 1,
                    members: Vec::new(),
                },
            )
        })
        .collect();
    for member in base.members.drain(..) {
        let group = strata
            .get_mut(&member.company)
            .ok_or(CompanyCaptureError::InvalidSource(member.site))?;
        group.positive_sites += usize::from(member.employed > 0);
        group.members.push(member);
    }
    let available = strata.values().map(|s| s.positive_sites).sum();
    let requested = goal.count();
    if available < usize::from(requested)
        || strata.values().any(|s| s.positive_sites == 0)
        || strata.len() > usize::from(requested)
    {
        return Err(CompanyCaptureError::ControllerCapacity {
            requested,
            available,
        });
    }
    for _ in strata.len()..usize::from(requested) {
        let group = strata
            .values_mut()
            .filter(|r| usize::from(r.seats) < r.positive_sites)
            .max_by(|l, r| l.priority(r))
            .ok_or(CompanyCaptureError::ControllerCapacity {
                requested,
                available,
            })?;
        group.seats += 1;
    }
    for group in strata.into_values() {
        group.split(&mut base)?;
    }
    base.members.sort_unstable_by_key(|m| m.site);
    Ok(base)
}
