//! Disposable source-bound sparse group reserves. Legal balances live in the material register.
use super::carrying::CompanyCarryingLedger;
use super::{CompanyBooks, CompanyStatementsError};
use crate::identity::CampaignId;
use babylon_kernel::currency::Currency;
use babylon_material_circuit::{
    CompanyBasisAsset, EquipmentCohortId, FreightLotId, GoodId, InstallationId, SiteId, UnitId,
};
use sha2::{Digest, Sha256};

const DOMAIN: &[u8] = b"babylon.company-books.checkpoint.v1\0";
const WIDTH: usize = 97 + 16;
impl CompanyBooks {
    pub(crate) fn checkpoint(
        &self,
        campaign: CampaignId,
        foundation: [u8; 32],
        world: [u8; 32],
    ) -> Result<(Vec<u8>, [u8; 32]), CompanyStatementsError> {
        let n = u64::try_from(self.carry.balances.len())
            .map_err(|_| CompanyStatementsError::Arithmetic)?;
        let mut bytes = DOMAIN.to_vec();
        bytes.extend_from_slice(campaign.canonical_bytes());
        bytes.extend_from_slice(&foundation);
        bytes.extend_from_slice(&world);
        bytes.extend_from_slice(&self.next.to_be_bytes());
        bytes.extend_from_slice(&n.to_be_bytes());
        for (&a, &value) in &self.carry.balances {
            let (tag, id, unit) = match a {
                CompanyBasisAsset::Stock(_, g, u) => (1, g.as_bytes(), u.as_bytes()),
                CompanyBasisAsset::Freight(_, l) => (2, l.as_bytes(), [0; 32]),
                CompanyBasisAsset::Installation(_, i) => (3, i.as_bytes(), [0; 32]),
                CompanyBasisAsset::Equipment(_, c) => (4, c.as_bytes(), [0; 32]),
                _ => return Err(CompanyStatementsError::BasisMismatch),
            };
            bytes.push(tag);
            bytes.extend_from_slice(&a.site().as_bytes());
            bytes.extend_from_slice(&id);
            bytes.extend_from_slice(&unit);
            bytes.extend_from_slice(&value.micro_units().to_be_bytes());
        }
        let hash = Sha256::digest(&bytes).into();
        Ok((bytes, hash))
    }
    pub(crate) fn restore(
        &mut self,
        campaign: CampaignId,
        foundation: [u8; 32],
        world: [u8; 32],
        next: u64,
        bytes: &[u8],
        sha256: [u8; 32],
    ) -> Result<(), CompanyStatementsError> {
        let digest: [u8; 32] = Sha256::digest(bytes).into();
        if digest != sha256 {
            return Err(CompanyStatementsError::BasisMismatch);
        }
        let mut b = bytes
            .strip_prefix(DOMAIN)
            .ok_or(CompanyStatementsError::BasisMismatch)?;
        if &take::<16>(&mut b)? != campaign.canonical_bytes()
            || take::<32>(&mut b)? != foundation
            || take::<32>(&mut b)? != world
            || u64::from_be_bytes(take(&mut b)?) != next
        {
            return Err(CompanyStatementsError::BasisMismatch);
        }
        let n = usize::try_from(u64::from_be_bytes(take(&mut b)?))
            .map_err(|_| CompanyStatementsError::Arithmetic)?;
        if n.checked_mul(WIDTH) != Some(b.len()) {
            return Err(CompanyStatementsError::BasisMismatch);
        }
        let mut carry = CompanyCarryingLedger::default();
        let mut previous = None;
        for _ in 0..n {
            let [tag] = take(&mut b)?;
            let site = SiteId::from_bytes(take(&mut b)?);
            let id = take(&mut b)?;
            let unit = take(&mut b)?;
            let value = i128::from_be_bytes(take(&mut b)?);
            if !self.members.contains_key(&site) || value == 0 || (tag != 1 && unit != [0; 32]) {
                return Err(CompanyStatementsError::BasisMismatch);
            }
            let node = match tag {
                1 => {
                    CompanyBasisAsset::Stock(site, GoodId::from_bytes(id), UnitId::from_bytes(unit))
                }
                2 => CompanyBasisAsset::Freight(site, FreightLotId::from_bytes(id)),
                3 => CompanyBasisAsset::Installation(site, InstallationId::from_bytes(id)),
                4 => CompanyBasisAsset::Equipment(site, EquipmentCohortId::from_bytes(id)),
                _ => return Err(CompanyStatementsError::BasisMismatch),
            };
            if previous.is_some_and(|prior| prior >= node) {
                return Err(CompanyStatementsError::BasisMismatch);
            }
            carry
                .balances
                .insert(node, Currency::from_micro_units(value));
            previous = Some(node);
        }
        self.carry = carry;
        self.next = next;
        Ok(())
    }
}
fn take<const N: usize>(b: &mut &[u8]) -> Result<[u8; N], CompanyStatementsError> {
    let (data, rest) = b
        .split_first_chunk::<N>()
        .ok_or(CompanyStatementsError::BasisMismatch)?;
    *b = rest;
    Ok(*data)
}
