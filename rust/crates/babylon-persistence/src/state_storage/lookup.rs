//! Shared, append-only typed identity ownership for state and receipt storage.
use super::StorageError;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;

/// The closed set of current circuit identity domains; equal bytes in distinct
/// domains intentionally have distinct references.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
#[repr(u8)]
pub enum IdentityKind {
    Process = 1,
    Site,
    FreightLot,
    Order,
    Route,
    FinalDemandPrincipal,
    Good,
    Unit,
    Shift,
    OrganizationAccount,
    PublicAccount,
    Contribution,
    StaffingPool,
    StaffingMember,
    Installation,
    EquipmentCohort,
    EquipmentDefinition,
    LogisticsNode,
    Corridor,
    AidMandate = 20,
}
impl IdentityKind {
    /// Decode the closed storage identity tag.
    /// # Errors
    /// Refuses unknown identity domains.
    pub fn from_tag(tag: u8) -> Result<Self, StorageError> {
        match tag {
            1 => Ok(Self::Process),
            2 => Ok(Self::Site),
            3 => Ok(Self::FreightLot),
            4 => Ok(Self::Order),
            5 => Ok(Self::Route),
            6 => Ok(Self::FinalDemandPrincipal),
            7 => Ok(Self::Good),
            8 => Ok(Self::Unit),
            9 => Ok(Self::Shift),
            10 => Ok(Self::OrganizationAccount),
            11 => Ok(Self::PublicAccount),
            12 => Ok(Self::Contribution),
            13 => Ok(Self::StaffingPool),
            14 => Ok(Self::StaffingMember),
            15 => Ok(Self::Installation),
            16 => Ok(Self::EquipmentCohort),
            17 => Ok(Self::EquipmentDefinition),
            18 => Ok(Self::LogisticsNode),
            19 => Ok(Self::Corridor),
            20 => Ok(Self::AidMandate),
            _ => Err(StorageError::IdentityKind),
        }
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub struct IdentityEntry {
    pub kind: IdentityKind,
    pub bytes: [u8; 32],
}
#[derive(Clone, Debug, Default)]
pub struct TypedLookup {
    entries: Vec<IdentityEntry>,
    indices: BTreeMap<IdentityEntry, u32>,
}
impl TypedLookup {
    /// Admit exact ordered persisted entries; duplicates cannot silently collapse.
    /// # Errors
    /// Refuses duplicate typed entries or reference count overflow.
    pub fn from_entries(entries: Vec<IdentityEntry>) -> Result<Self, StorageError> {
        let mut result = Self::default();
        for entry in entries {
            if result.indices.contains_key(&entry) {
                return Err(StorageError::DuplicateIdentity);
            }
            result.intern(entry.kind, entry.bytes)?;
        }
        Ok(result)
    }
    #[must_use]
    pub fn entries(&self) -> &[IdentityEntry] {
        &self.entries
    }
    /// Return the existing reference or append this exact typed identity.
    /// # Errors
    /// Refuses a lookup exceeding the representable reference range.
    pub fn intern(&mut self, kind: IdentityKind, bytes: [u8; 32]) -> Result<u32, StorageError> {
        let entry = IdentityEntry { kind, bytes };
        if let Some(index) = self.indices.get(&entry) {
            return Ok(*index);
        }
        let index = u32::try_from(self.entries.len()).map_err(|_| StorageError::Bounds)?;
        self.entries.push(entry);
        self.indices.insert(entry, index);
        Ok(index)
    }
    /// Resolve one reference in its exact expected domain.
    /// # Errors
    /// Refuses an absent reference or mismatched identity kind.
    pub fn resolve(&self, index: u32, expected: IdentityKind) -> Result<[u8; 32], StorageError> {
        let entry = self
            .entries
            .get(usize::try_from(index).map_err(|_| StorageError::Bounds)?)
            .ok_or(StorageError::LookupIndex)?;
        if entry.kind != expected {
            return Err(StorageError::IdentityKind);
        }
        Ok(entry.bytes)
    }
    pub(super) fn index(&self, entry: IdentityEntry) -> Result<u32, StorageError> {
        self.indices
            .get(&entry)
            .copied()
            .ok_or(StorageError::LookupIndex)
    }
    /// Authenticate an exact prefix while allowing later appended entries.
    /// # Errors
    /// Refuses a prefix longer than the admitted lookup.
    pub fn prefix_digest(&self, count: usize) -> Result<[u8; 32], StorageError> {
        let entries = self.entries.get(..count).ok_or(StorageError::LookupIndex)?;
        let mut hash = Sha256::new();
        for entry in entries {
            hash.update([entry.kind as u8]);
            hash.update(entry.bytes);
        }
        Ok(hash.finalize().into())
    }
}
