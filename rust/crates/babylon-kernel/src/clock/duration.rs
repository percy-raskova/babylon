//! Captured campaign stopping policy, independent of the fixed causal interval.
use serde::{Deserialize, Serialize};

/// Continuous campaigns have no designed final period. Finite controls do.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum CampaignDuration {
    Continuous,
    Finite { final_period: u64 },
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct InvalidCampaignDuration;
impl std::fmt::Display for InvalidCampaignDuration {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str("campaign duration must be continuous or a positive signed-64 final period")
    }
}
impl std::error::Error for InvalidCampaignDuration {}

impl CampaignDuration {
    /// # Errors
    /// Refuses empty finite controls and periods outside the shared signed clock.
    pub const fn validate(self) -> Result<(), InvalidCampaignDuration> {
        match self {
            Self::Finite { final_period }
                if final_period == 0 || final_period > i64::MAX as u64 =>
            {
                Err(InvalidCampaignDuration)
            }
            _ => Ok(()),
        }
    }
    #[must_use]
    pub const fn final_period(self) -> Option<u64> {
        match self {
            Self::Continuous => None,
            Self::Finite { final_period } => Some(final_period),
        }
    }
    #[must_use]
    pub const fn contains(self, period: u64) -> bool {
        if self.validate().is_err() || period > i64::MAX as u64 {
            return false;
        }
        match self {
            Self::Continuous => true,
            Self::Finite { final_period } => period <= final_period,
        }
    }
    #[must_use]
    pub const fn complete(self, period: u64) -> bool {
        matches!(self, Self::Finite { final_period } if period >= final_period)
    }
    #[must_use]
    pub const fn can_advance(self, completed: u64) -> bool {
        match completed.checked_add(1) {
            Some(next) => self.contains(next),
            None => false,
        }
    }
    /// Exact tagged bytes. Continuous has canonical zero padding, never a large horizon.
    /// # Errors
    /// Refuses invalid finite durations.
    pub fn canonical_bytes(self) -> Result<[u8; 9], InvalidCampaignDuration> {
        self.validate()?;
        let mut bytes = [0; 9];
        match self {
            Self::Continuous => bytes[0] = 0,
            Self::Finite { final_period } => {
                bytes[0] = 1;
                bytes[1..].copy_from_slice(&final_period.to_be_bytes());
            }
        }
        Ok(bytes)
    }
    /// # Errors
    /// Refuses unknown tags, nonzero continuous padding, zero and oversized finite durations.
    pub fn decode(bytes: [u8; 9]) -> Result<Self, InvalidCampaignDuration> {
        let period =
            u64::from_be_bytes(bytes[1..].try_into().map_err(|_| InvalidCampaignDuration)?);
        let value = match (bytes[0], period) {
            (0, 0) => Self::Continuous,
            (1, final_period) => Self::Finite { final_period },
            _ => return Err(InvalidCampaignDuration),
        };
        value.validate()?;
        Ok(value)
    }
}

impl std::fmt::Display for CampaignDuration {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Continuous => formatter.write_str("continuous"),
            Self::Finite { final_period } => write!(formatter, "finite {final_period}-period"),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn continuous_has_no_designed_stop_and_finite_stops_exactly() {
        assert!(CampaignDuration::Continuous.can_advance(80));
        assert!(!CampaignDuration::Continuous.complete(80));
        assert!(!CampaignDuration::Continuous.can_advance(i64::MAX as u64));
        let finite = CampaignDuration::Finite { final_period: 16 };
        assert!(finite.can_advance(15));
        assert!(!finite.can_advance(16));
        assert!(finite.complete(16));
        assert!(!finite.contains(17));
    }
    #[test]
    fn duration_encoding_refuses_noncanonical_padding_and_invalid_endpoints() {
        for duration in [
            CampaignDuration::Continuous,
            CampaignDuration::Finite { final_period: 131 },
        ] {
            assert_eq!(
                CampaignDuration::decode(duration.canonical_bytes().unwrap()),
                Ok(duration)
            );
        }
        let mut padding = CampaignDuration::Continuous.canonical_bytes().unwrap();
        padding[8] = 1;
        assert!(CampaignDuration::decode(padding).is_err());
        let mut unknown = [0; 9];
        unknown[0] = 2;
        assert!(CampaignDuration::decode(unknown).is_err());
        for final_period in [0, u64::MAX] {
            assert!(CampaignDuration::Finite { final_period }
                .canonical_bytes()
                .is_err());
        }
    }
}
