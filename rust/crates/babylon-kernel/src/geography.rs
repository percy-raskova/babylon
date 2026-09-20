//! Source geographic identities. Syntax and jurisdiction do not establish roster membership.

/// Exact five ASCII digits of a county or county-equivalent GEOID.
///
/// Construction checks syntax only. A captured, vintage-specific county roster
/// must independently admit the identity before it becomes campaign geography.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct CountyGeoid([u8; 5]);

/// The jurisdiction indicated by a Census state-prefix code, not county membership.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CountyJurisdiction {
    /// One of the fifty US states, including Alaska and Hawaii.
    State,
    /// The District of Columbia.
    DistrictOfColumbia,
    /// A US dependency: AS, GU, MP, PR, UM or VI; outside the domestic county roster.
    Dependency,
    /// An unrecognized prefix; syntax alone accepts it without geographic authority.
    Unknown,
}

/// A GEOID cannot be padded, rounded or parsed as a numeric quantity.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum CountyGeoidError {
    /// Exactly five source bytes are required.
    Length {
        /// The supplied byte length.
        actual: usize,
    },
    /// At least one byte was not an ASCII decimal digit.
    NonDecimal,
}

impl CountyGeoid {
    /// Return the exact five source bytes, preserving leading zeros.
    #[must_use]
    pub const fn as_bytes(self) -> [u8; 5] {
        self.0
    }

    /// Return the exact source text without allocation.
    ///
    /// # Panics
    /// Panics only if the private ASCII construction invariant is violated.
    #[must_use]
    pub fn as_str(&self) -> &str {
        std::str::from_utf8(&self.0).expect("CountyGeoid contains checked ASCII digits")
    }

    /// Return the two-digit Census state/area prefix; this is not an ISO code.
    #[must_use]
    pub const fn state_fips(self) -> [u8; 2] {
        [self.0[0], self.0[1]]
    }

    /// Return the three-digit county portion, preserving leading zeros.
    #[must_use]
    pub const fn county_fips(self) -> [u8; 3] {
        [self.0[2], self.0[3], self.0[4]]
    }

    /// Classify the Census prefix without claiming that this county exists.
    #[must_use]
    pub const fn jurisdiction(self) -> CountyJurisdiction {
        let code = (self.0[0] - b'0') * 10 + (self.0[1] - b'0');
        match code {
            11 => CountyJurisdiction::DistrictOfColumbia,
            1 | 2 | 4 | 5 | 6 | 8 | 9 | 10 | 12 | 13 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22
            | 23 | 24 | 25 | 26 | 27 | 28 | 29 | 30 | 31 | 32 | 33 | 34 | 35 | 36 | 37 | 38
            | 39 | 40 | 41 | 42 | 44 | 45 | 46 | 47 | 48 | 49 | 50 | 51 | 53 | 54 | 55 | 56 => {
                CountyJurisdiction::State
            }
            60 | 66 | 69 | 72 | 74 | 78 => CountyJurisdiction::Dependency,
            _ => CountyJurisdiction::Unknown,
        }
    }
}
impl TryFrom<[u8; 5]> for CountyGeoid {
    type Error = CountyGeoidError;
    fn try_from(value: [u8; 5]) -> Result<Self, Self::Error> {
        if !value.iter().all(u8::is_ascii_digit) {
            return Err(CountyGeoidError::NonDecimal);
        }
        Ok(Self(value))
    }
}
impl TryFrom<&str> for CountyGeoid {
    type Error = CountyGeoidError;
    fn try_from(value: &str) -> Result<Self, Self::Error> {
        let bytes: [u8; 5] = value
            .as_bytes()
            .try_into()
            .map_err(|_| CountyGeoidError::Length {
                actual: value.len(),
            })?;
        Self::try_from(bytes)
    }
}
impl std::str::FromStr for CountyGeoid {
    type Err = CountyGeoidError;
    fn from_str(value: &str) -> Result<Self, Self::Err> {
        Self::try_from(value)
    }
}
impl std::fmt::Display for CountyGeoid {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(self.as_str())
    }
}
impl std::fmt::Display for CountyGeoidError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "county GEOID refused: {self:?}")
    }
}
impl std::error::Error for CountyGeoidError {}
