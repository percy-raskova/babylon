//! Allocation weights preserve missing observations and the selected peer evidence.
use super::{AllocationError, Result};
use crate::national_cohorts::{CohortReference, NationalCohortReference};
use babylon_kernel::economic_identity::{EconomicFunction, QcewOwnership};
use std::collections::BTreeMap;

/// The source relationship used for one missing leaf's Designed weight.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PeerScope {
    IndustryOwnership,
    FunctionOwnership,
    Industry,
    DesignedEstablishmentPoints,
}
/// A weight calculation, never a replacement observation of suppressed jobs.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ImputedWeight {
    pub naics_code: String,
    pub establishments: u64,
    pub peer_scope: PeerScope,
    pub peer_jobs: Option<u64>,
    pub peer_establishments: Option<u64>,
    pub designed_points_per_establishment: Option<u64>,
    pub allocation_weight: u64,
}
/// Published jobs remain separate from every Designed contribution.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct WorkforceAllocationWeight {
    pub published_jobs: u64,
    pub source_jobs_complete: bool,
    pub imputed: Vec<ImputedWeight>,
    pub total: u64,
}
#[derive(Clone, Copy, Default)]
struct Peer {
    jobs: u64,
    establishments: u64,
}
impl Peer {
    fn add(&mut self, jobs: u64, establishments: u64) -> Result<()> {
        self.jobs = self
            .jobs
            .checked_add(jobs)
            .ok_or(AllocationError::Arithmetic)?;
        self.establishments = self
            .establishments
            .checked_add(establishments)
            .ok_or(AllocationError::Arithmetic)?;
        Ok(())
    }
}
pub(super) struct Peers {
    industry_ownership: BTreeMap<(String, QcewOwnership), Peer>,
    function_ownership: BTreeMap<(EconomicFunction, QcewOwnership), Peer>,
    industry: BTreeMap<String, Peer>,
}
impl Peers {
    pub(super) fn new(source: &NationalCohortReference) -> Result<Self> {
        let mut peers = Self {
            industry_ownership: BTreeMap::new(),
            function_ownership: BTreeMap::new(),
            industry: BTreeMap::new(),
        };
        for group in source.groups() {
            let Some(function) = group.key().function else {
                continue;
            };
            for member in group.members() {
                let Some(jobs) = member.annual_average_jobs else {
                    continue;
                };
                let establishments = member.annual_average_establishments;
                peers
                    .industry_ownership
                    .entry((member.naics_code.clone(), group.key().ownership))
                    .or_default()
                    .add(jobs, establishments)?;
                peers
                    .function_ownership
                    .entry((function, group.key().ownership))
                    .or_default()
                    .add(jobs, establishments)?;
                peers
                    .industry
                    .entry(member.naics_code.clone())
                    .or_default()
                    .add(jobs, establishments)?;
            }
        }
        Ok(peers)
    }
    pub(super) fn weight(
        &self,
        group: &CohortReference,
        missing_peer_weight_per_establishment: u64,
    ) -> Result<WorkforceAllocationWeight> {
        let key = group.key();
        let function = key.function.ok_or(AllocationError::SourceScope)?;
        let mut result = WorkforceAllocationWeight {
            published_jobs: group.jobs().known_subtotal(),
            source_jobs_complete: group.jobs().complete_total().is_some(),
            imputed: vec![],
            total: group.jobs().known_subtotal(),
        };
        for member in group
            .members()
            .iter()
            .filter(|row| row.annual_average_jobs.is_none())
        {
            // A rounded-zero establishment count contributes no invented minimum activity.
            if member.annual_average_establishments == 0 {
                continue;
            }
            let candidates = [
                (
                    PeerScope::IndustryOwnership,
                    self.industry_ownership
                        .get(&(member.naics_code.clone(), key.ownership)),
                ),
                (
                    PeerScope::FunctionOwnership,
                    self.function_ownership.get(&(function, key.ownership)),
                ),
                (PeerScope::Industry, self.industry.get(&member.naics_code)),
            ];
            let peer = candidates
                .into_iter()
                .find_map(|(scope, p)| p.filter(|p| p.establishments > 0).map(|p| (scope, p)));
            let (scope, jobs, establishments, points, weight) = if let Some((scope, peer)) = peer {
                let numerator =
                    u128::from(member.annual_average_establishments) * u128::from(peer.jobs);
                let weight = u64::try_from(
                    (numerator + u128::from(peer.establishments) / 2)
                        / u128::from(peer.establishments),
                )
                .map_err(|_| AllocationError::Arithmetic)?;
                (
                    scope,
                    Some(peer.jobs),
                    Some(peer.establishments),
                    None,
                    weight,
                )
            } else {
                if missing_peer_weight_per_establishment == 0 {
                    return Err(AllocationError::Policy);
                }
                let weight = member
                    .annual_average_establishments
                    .checked_mul(missing_peer_weight_per_establishment)
                    .ok_or(AllocationError::Arithmetic)?;
                (
                    PeerScope::DesignedEstablishmentPoints,
                    None,
                    None,
                    Some(missing_peer_weight_per_establishment),
                    weight,
                )
            };
            result.total = result
                .total
                .checked_add(weight)
                .ok_or(AllocationError::Arithmetic)?;
            result.imputed.push(ImputedWeight {
                naics_code: member.naics_code.clone(),
                establishments: member.annual_average_establishments,
                peer_scope: scope,
                peer_jobs: jobs,
                peer_establishments: establishments,
                designed_points_per_establishment: points,
                allocation_weight: weight,
            });
        }
        Ok(result)
    }
}
