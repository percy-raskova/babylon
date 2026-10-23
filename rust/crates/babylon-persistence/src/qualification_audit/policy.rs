//! Consume selected fields of the supervisor's exact frozen policy, never defaults.

use super::Scope;
use crate::identity::CampaignId;
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::{
    fs::File,
    io::Read,
    path::{Path, PathBuf},
};

const POLICY_BYTES: u64 = 65_536;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Refusal {
    Path,
    Read,
    Changed,
    Fields,
    Digest,
    Periods,
}
impl std::fmt::Display for Refusal {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "frozen qualification policy refused: {self:?}")
    }
}
impl std::error::Error for Refusal {}

/// The supervisor still validates the complete policy. This typed subset rejects
/// duplicate consumed fields and supplies no defaults or admission decision.
#[derive(Deserialize)]
struct Consumed {
    version: u64,
    name: String,
    county_count: u64,
    qualification_ticks: u64,
    economic_renewal_window_ticks: u64,
    maximum_material_register_bytes: u64,
    maximum_production_evidence_body_bytes: u64,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FrozenPolicy {
    path: PathBuf,
    sha256: [u8; 32],
    periods: u64,
    renewal_seed_tick: u64,
    material_register_bytes: usize,
    production_evidence_bytes: usize,
}
impl FrozenPolicy {
    /// # Errors
    /// Refuses changed/unbounded bytes, unsupported fields and a zero run horizon.
    pub fn open(path: &Path, sha256: [u8; 32], periods: u64) -> Result<Self, Refusal> {
        if periods == 0 {
            return Err(Refusal::Periods);
        }
        let policy: Consumed =
            serde_json::from_slice(&read(path, sha256)?).map_err(|_| Refusal::Fields)?;
        if policy.version != 6
            || policy.name != "national_storage_qualification_v6"
            || policy.county_count != 3_144
            || policy.qualification_ticks != 52
            || !(2..=52).contains(&policy.economic_renewal_window_ticks)
        {
            return Err(Refusal::Fields);
        }
        Ok(Self {
            path: path.to_owned(),
            sha256,
            periods,
            renewal_seed_tick: periods
                .saturating_sub(policy.economic_renewal_window_ticks)
                .max(1),
            material_register_bytes: limit(policy.maximum_material_register_bytes)?,
            production_evidence_bytes: limit(policy.maximum_production_evidence_body_bytes)?,
        })
    }

    /// # Errors
    /// Refuses replacement, corruption or unbounded bytes after capture.
    pub fn verify(&self) -> Result<(), Refusal> {
        read(&self.path, self.sha256).map(|_| ())
    }

    #[must_use]
    pub const fn periods(&self) -> u64 {
        self.periods
    }

    #[must_use]
    pub const fn scope(&self, campaign: CampaignId, foundation: [u8; 32]) -> Scope {
        Scope {
            campaign,
            foundation,
            policy: self.sha256,
            renewal_seed_tick: self.renewal_seed_tick,
            material_register_bytes: self.material_register_bytes,
            production_evidence_bytes: self.production_evidence_bytes,
        }
    }
}

fn limit(value: u64) -> Result<usize, Refusal> {
    if value == 0 || value > 1_000_000_000 {
        return Err(Refusal::Fields);
    }
    usize::try_from(value).map_err(|_| Refusal::Fields)
}

fn read(path: &Path, sha256: [u8; 32]) -> Result<Vec<u8>, Refusal> {
    if !path.is_absolute()
        || !path
            .symlink_metadata()
            .map_err(|_| Refusal::Path)?
            .is_file()
    {
        return Err(Refusal::Path);
    }
    let mut bytes = Vec::new();
    File::open(path)
        .map_err(|_| Refusal::Read)?
        .take(POLICY_BYTES + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| Refusal::Read)?;
    if u64::try_from(bytes.len()).map_err(|_| Refusal::Changed)? > POLICY_BYTES
        || <[u8; 32]>::from(Sha256::digest(&bytes)) != sha256
    {
        return Err(Refusal::Changed);
    }
    Ok(bytes)
}

/// # Errors
/// Refuses a digest other than exactly 64 lowercase hexadecimal characters.
pub fn canonical_digest(value: &str) -> Result<[u8; 32], Refusal> {
    if value.len() != 64
        || !value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err(Refusal::Digest);
    }
    let mut bytes = [0; 32];
    for (index, byte) in bytes.iter_mut().enumerate() {
        *byte = u8::from_str_radix(&value[index * 2..index * 2 + 2], 16)
            .map_err(|_| Refusal::Digest)?;
    }
    Ok(bytes)
}

#[cfg(test)]
mod tests {
    use super::*;
    use sha2::{Digest, Sha256};
    use std::{fs, path::PathBuf};

    struct Fixture(PathBuf);
    impl Fixture {
        fn new() -> Self {
            use std::sync::atomic::{AtomicU64, Ordering};
            static NEXT: AtomicU64 = AtomicU64::new(0);
            let path = std::env::temp_dir().join(format!(
                "babylon-audit-policy-{}.json",
                format_args!(
                    "{}-{}",
                    std::process::id(),
                    NEXT.fetch_add(1, Ordering::Relaxed)
                )
            ));
            fs::write(
                &path,
                include_bytes!("../../../../../contracts/national_storage_qualification_v6.json"),
            )
            .unwrap();
            Self(path)
        }
        fn digest(&self) -> [u8; 32] {
            Sha256::digest(fs::read(&self.0).unwrap()).into()
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            fs::remove_file(&self.0).unwrap();
        }
    }

    #[test]
    fn frozen_fields_and_renewal_seed_are_shared_without_defaults() {
        let file = Fixture::new();
        let policy = FrozenPolicy::open(&file.0, file.digest(), 52).unwrap();
        let scope = policy.scope(
            crate::identity::CampaignId::from_uuid(uuid::Uuid::from_u128(1)),
            [7; 32],
        );
        assert_eq!(scope.renewal_seed_tick, 39);
        assert_eq!(scope.material_register_bytes, 1_000_000_000);
        assert_eq!(scope.production_evidence_bytes, 1_000_000_000);
        assert_eq!(scope.policy, file.digest());
        assert!(policy.verify().is_ok());
        fs::write(&file.0, b"{}").unwrap();
        assert_eq!(policy.verify(), Err(Refusal::Changed));
    }

    #[test]
    fn unsupported_missing_and_duplicated_consumed_fields_refuse() {
        let file = Fixture::new();
        for replacement in [
            b"{}".as_slice(),
            b"{\"version\":5}",
            b"{\"version\":6,\"version\":6}",
        ] {
            fs::write(&file.0, replacement).unwrap();
            assert!(FrozenPolicy::open(&file.0, file.digest(), 2).is_err());
        }
        assert!(canonical_digest(&"A".repeat(64)).is_err());
        assert!(canonical_digest(&"a".repeat(63)).is_err());
        assert_eq!(canonical_digest(&"ab".repeat(32)).unwrap(), [0xab; 32]);
    }
}
