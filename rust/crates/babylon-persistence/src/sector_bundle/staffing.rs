//! Closed staffing authority stored with the executable sector definitions.

use babylon_graph::stable_element::StableElementKey;
use babylon_kernel::{content_digest::sha256_of, economic_location::EconomicLocation};
use babylon_material_circuit::{
    FinalDemandPrincipalId, ProcessId, SiteId, StaffingMemberBinding, StaffingMemberId,
    StaffingPolicy, StaffingPoolBinding, StaffingPoolId, StaffingWorkSource, UnitId,
};
use babylon_tick::material_staffing::{
    StaffingComposition, StaffingMemberNodeBinding, StaffingNodeBinding,
};
use serde::{Deserialize, Serialize};

use super::SectorBundleError;
use crate::michigan_cohorts::MICHIGAN_COHORT_SCENARIO;
use crate::michigan_material::{MichiganMaterialCatalog, MichiganStaffingDesign};

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(tag = "kind", content = "id", rename_all = "snake_case")]
enum StoredWorkSource {
    Production([u8; 32]),
    MerchantHandling([u8; 32]),
    Maintenance([u8; 32]),
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct StoredPool {
    scenario: String,
    local_name: String,
    workplace_local_name: String,
    residence_county: String,
    pool_id: [u8; 32],
    site_id: [u8; 32],
    unit_id: [u8; 32],
    work_sources: Vec<StoredWorkSource>,
    labor_force: u64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub(super) struct StoredStaffing {
    authority: String,
    design: MichiganStaffingDesign,
    bindings: Vec<StoredPool>,
}

impl StoredStaffing {
    pub(super) fn authored(catalog: &MichiganMaterialCatalog) -> Result<Self, SectorBundleError> {
        let mut bindings = Vec::new();
        for seed in &catalog.staffing().pools {
            let site = catalog
                .site(&seed.site_key)
                .ok_or(SectorBundleError::ProcessOwnership)?;
            let mut work_sources = seed
                .process_keys
                .iter()
                .map(|key| {
                    catalog
                        .processes()
                        .iter()
                        .find(|p| p.key == *key)
                        .map(|p| StoredWorkSource::Production(p.id().as_bytes()))
                        .ok_or(SectorBundleError::ProcessOwnership)
                })
                .collect::<Result<Vec<_>, _>>()?;
            if seed.merchant_handling {
                work_sources.push(StoredWorkSource::MerchantHandling(site.id().as_bytes()));
            }
            if seed.maintenance {
                work_sources.push(StoredWorkSource::Maintenance(site.id().as_bytes()));
            }
            work_sources.sort();
            bindings.push(StoredPool {
                scenario: MICHIGAN_COHORT_SCENARIO.to_owned(),
                local_name: seed.local_name(),
                workplace_local_name: seed.workplace_local_name(),
                residence_county: site.county_geoid.clone(),
                pool_id: sha256_of(
                    format!("babylon.michigan-staffing.v1\0pool\0{}", seed.key).as_bytes(),
                ),
                site_id: site.id().as_bytes(),
                unit_id: sha256_of(b"babylon.michigan-material.v1\0unit\0labor-hour"),
                work_sources,
                labor_force: seed
                    .employed
                    .checked_add(seed.reserve)
                    .ok_or(SectorBundleError::Arithmetic)?,
            });
        }
        bindings.sort_unstable_by_key(|binding| binding.pool_id);
        Ok(Self {
            authority: "Staffed".to_owned(),
            design: catalog.staffing().clone(),
            bindings,
        })
    }

    pub(super) fn encode(&self) -> Result<Vec<u8>, SectorBundleError> {
        serde_json::to_vec(self).map_err(|_| SectorBundleError::WireNoncanonical)
    }

    pub(super) fn decode(
        bytes: &[u8],
        catalog: &MichiganMaterialCatalog,
    ) -> Result<Self, SectorBundleError> {
        let value: Self =
            serde_json::from_slice(bytes).map_err(|_| SectorBundleError::WireNoncanonical)?;
        if value.encode()? != bytes {
            return Err(SectorBundleError::WireNoncanonical);
        }
        // Exact source admission also proves seeds, policy, placement, principal
        // bindings and canonical ordering. A self-hash cannot grant authority.
        if value != Self::authored(catalog)? {
            return Err(SectorBundleError::Source);
        }
        value.composition()?;
        Ok(value)
    }

    #[cfg(test)]
    pub(super) fn design(&self) -> &MichiganStaffingDesign {
        &self.design
    }

    pub(super) fn composition(&self) -> Result<StaffingComposition, SectorBundleError> {
        let bindings = self
            .bindings
            .iter()
            .map(|binding| {
                let pool = StaffingPoolBinding::try_new(
                    StaffingPoolId::from_bytes(binding.pool_id),
                    SiteId::from_bytes(binding.site_id),
                    UnitId::from_bytes(binding.unit_id),
                    binding.labor_force,
                    StaffingPolicy::one_period(self.design.hours_per_worker_period)
                        .map_err(|_| SectorBundleError::Resource)?,
                    binding
                        .work_sources
                        .iter()
                        .map(|source| match source {
                            StoredWorkSource::Production(id) => {
                                StaffingWorkSource::Production(ProcessId::from_bytes(*id))
                            }
                            StoredWorkSource::MerchantHandling(id) => {
                                StaffingWorkSource::MerchantHandling(SiteId::from_bytes(*id))
                            }
                            StoredWorkSource::Maintenance(id) => {
                                StaffingWorkSource::Maintenance(SiteId::from_bytes(*id))
                            }
                        })
                        .collect(),
                )
                .map_err(|_| SectorBundleError::Resource)?;
                StaffingNodeBinding::try_new(
                    StableElementKey::Node {
                        scenario: binding.scenario.clone(),
                        local_name: binding.workplace_local_name.clone(),
                    },
                    pool,
                    binding.members()?,
                )
                .map_err(|_| SectorBundleError::Resource)
            })
            .collect::<Result<Vec<_>, _>>()?;
        StaffingComposition::try_new(bindings).map_err(|_| SectorBundleError::Resource)
    }
}

impl StoredPool {
    fn members(&self) -> Result<Vec<StaffingMemberNodeBinding>, SectorBundleError> {
        if self.labor_force == 0 {
            return Ok(vec![]);
        }
        let county = self
            .residence_county
            .parse()
            .map_err(|_| SectorBundleError::Source)?;
        let residence =
            EconomicLocation::domestic_county(county).map_err(|_| SectorBundleError::Source)?;
        // These explicitly Designed physical controls have no funded household
        // account. Their aggregate resident identity is not the finite retail buyer.
        let identity = |kind: &str| {
            let mut bytes = format!("babylon.michigan-control-resident.v1\0{kind}\0").into_bytes();
            bytes.extend_from_slice(&self.pool_id);
            sha256_of(&bytes)
        };
        let member = StaffingMemberBinding::try_new(
            StaffingMemberId::from_bytes(identity("member")),
            FinalDemandPrincipalId::from_bytes(identity("household")),
            residence,
            self.labor_force,
        )
        .map_err(|_| SectorBundleError::Resource)?;
        let binding = StaffingMemberNodeBinding::try_new(
            StableElementKey::Node {
                scenario: self.scenario.clone(),
                local_name: self.local_name.clone(),
            },
            member,
        )
        .map_err(|_| SectorBundleError::Resource)?;
        Ok(vec![binding])
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stored_authority_refuses_policy_placement_seed_and_every_principal_mutation() {
        let original = StoredStaffing::authored(&crate::test_support::catalog()).unwrap();
        let bytes = original.encode().unwrap();
        let decoded = StoredStaffing::decode(&bytes, &crate::test_support::catalog()).unwrap();
        assert_eq!(decoded, original);
        assert_eq!(decoded.composition().unwrap().bindings().len(), 5);
        for change in 0..13 {
            let mut changed = original.clone();
            match change {
                0 => changed.authority = "Scheduled".to_owned(),
                1 => changed.design.hours_per_worker_period = 39,
                2 => changed.design.retention_periods = 2,
                3 => changed.design.placement = "before-metabolism".to_owned(),
                4 => changed.design.pools[0].previous_unretained_hours += 1,
                5 => changed.bindings[0].pool_id[0] ^= 1,
                6 => changed.bindings[0].site_id[0] ^= 1,
                7 => changed.bindings[0].unit_id[0] ^= 1,
                8 => match &mut changed.bindings[0].work_sources[0] {
                    StoredWorkSource::Production(id)
                    | StoredWorkSource::MerchantHandling(id)
                    | StoredWorkSource::Maintenance(id) => {
                        id[0] ^= 1;
                    }
                },
                9 => changed.bindings[0].local_name.push('x'),
                10 => changed.design.composition_id.push('x'),
                11 => changed.bindings[0].workplace_local_name.push('x'),
                _ => changed.bindings[0].residence_county = "26001".to_owned(),
            }
            assert_eq!(
                StoredStaffing::decode(&changed.encode().unwrap(), &crate::test_support::catalog()),
                Err(SectorBundleError::Source)
            );
        }
        assert!(StoredStaffing::decode(b"{}", &crate::test_support::catalog()).is_err());
    }
}
