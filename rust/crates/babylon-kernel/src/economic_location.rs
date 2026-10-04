//! Closed game-market locations, independent of ownership, class and sovereignty.
//!
//! County construction checks the domestic jurisdiction, not vintage membership.
//! Campaign capture must still admit counties against its pinned geographic roster.

use crate::geography::{CountyGeoid, CountyGeoidError, CountyJurisdiction};

/// One county in a US state or DC, subject to independent roster admission.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct DomesticCounty(CountyGeoid);

impl DomesticCounty {
    /// Exact source geographic identity, with leading zeros intact.
    #[must_use]
    pub const fn geoid(self) -> CountyGeoid {
        self.0
    }
}

/// The twelve Designed foreign economic counterparts, with stable wire codes.
///
/// Aggregated markets do not imply a shared government or political alignment.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[repr(u8)]
pub enum ForeignCounterpart {
    /// Canada.
    Canada = 1,
    /// Mexico.
    Mexico = 2,
    /// Mainland China's statistical scope; other reporting areas stay separate.
    China = 3,
    /// Russia.
    Russia = 4,
    /// India.
    India = 5,
    /// Japan.
    Japan = 6,
    /// Pinned EU27 membership, excluding separately assigned overseas areas.
    EuropeanUnion = 7,
    /// Remaining Europe and explicitly assigned northern Atlantic reporting areas.
    RemainingEurope = 8,
    /// Latin America and Caribbean, excluding Mexico and US dependencies.
    LatinAmericaCaribbean = 9,
    /// West Asia and North Africa, including the policy's explicit Iran assignment.
    WestAsiaNorthAfrica = 10,
    /// Sub-Saharan Africa.
    SubSaharanAfrica = 11,
    /// Remaining Asia-Pacific, excluding separately represented counterparts.
    RemainingAsiaPacific = 12,
}

impl ForeignCounterpart {
    /// Every admitted counterpart in stable wire order.
    pub const ALL: [Self; 12] = [
        Self::Canada,
        Self::Mexico,
        Self::China,
        Self::Russia,
        Self::India,
        Self::Japan,
        Self::EuropeanUnion,
        Self::RemainingEurope,
        Self::LatinAmericaCaribbean,
        Self::WestAsiaNorthAfrica,
        Self::SubSaharanAfrica,
        Self::RemainingAsiaPacific,
    ];

    /// Exact key in the pinned counterpart membership policy.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Canada => "canada",
            Self::Mexico => "mexico",
            Self::China => "china",
            Self::Russia => "russia",
            Self::India => "india",
            Self::Japan => "japan",
            Self::EuropeanUnion => "european_union",
            Self::RemainingEurope => "remaining_europe",
            Self::LatinAmericaCaribbean => "latin_america_caribbean",
            Self::WestAsiaNorthAfrica => "west_asia_north_africa",
            Self::SubSaharanAfrica => "sub_saharan_africa",
            Self::RemainingAsiaPacific => "remaining_asia_pacific",
        }
    }

    /// Admit a policy key without aliases, trimming or case folding.
    #[must_use]
    pub fn from_key(value: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|id| id.as_str() == value)
    }

    fn from_code(code: u8) -> Option<Self> {
        Self::ALL.into_iter().find(|id| *id as u8 == code)
    }
}

/// US dependency reporting scopes; none is a foreign counterpart or domestic county.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[repr(u8)]
pub enum UsDependency {
    /// American Samoa.
    AmericanSamoa = 1,
    /// Guam.
    Guam = 2,
    /// Northern Mariana Islands.
    NorthernMarianaIslands = 3,
    /// Puerto Rico.
    PuertoRico = 4,
    /// US Minor Outlying Islands, with missing source quantities kept explicit.
    MinorOutlyingIslands = 5,
    /// US Virgin Islands.
    VirginIslands = 6,
}

impl UsDependency {
    /// Every admitted dependency in stable wire order.
    pub const ALL: [Self; 6] = [
        Self::AmericanSamoa,
        Self::Guam,
        Self::NorthernMarianaIslands,
        Self::PuertoRico,
        Self::MinorOutlyingIslands,
        Self::VirginIslands,
    ];

    /// Exact UN M49 reporting code; not a Census state-prefix code.
    #[must_use]
    pub const fn m49(self) -> &'static str {
        match self {
            Self::AmericanSamoa => "016",
            Self::Guam => "316",
            Self::NorthernMarianaIslands => "580",
            Self::PuertoRico => "630",
            Self::MinorOutlyingIslands => "581",
            Self::VirginIslands => "850",
        }
    }

    /// Admit an exact M49 dependency code; freely associated states are excluded.
    #[must_use]
    pub fn from_m49(value: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|id| id.m49() == value)
    }

    fn from_code(code: u8) -> Option<Self> {
        Self::ALL.into_iter().find(|id| *id as u8 == code)
    }
}

/// Where an economic account or actor operates; its owner is a separate relation.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum EconomicLocation {
    /// Domestic county detail retained throughout the national economy.
    County(DomesticCounty),
    /// One finite foreign economic counterpart.
    Foreign(ForeignCounterpart),
    /// A separately accounted US dependency.
    Dependency(UsDependency),
}

/// Strict identity and canonical-byte refusals.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum EconomicLocationError {
    /// Invalid county syntax.
    CountySyntax(CountyGeoidError),
    /// A county prefix is outside the fifty states and DC.
    NonDomesticCounty(CountyGeoid),
    /// No location has this wire tag.
    UnknownTag(u8),
    /// No foreign counterpart has this wire code.
    UnknownCounterpart(u8),
    /// No US dependency has this wire code.
    UnknownDependency(u8),
    /// Foreign and dependency identities require four zero padding bytes.
    NoncanonicalPadding,
    /// Text identities require one of the three exact namespace prefixes.
    UnknownNamespace,
    /// The foreign namespace contains no such pinned counterpart key.
    UnknownCounterpartKey,
    /// The dependency namespace contains no such exact M49 code.
    UnknownDependencyKey,
}

impl EconomicLocation {
    /// Check domestic jurisdiction without claiming membership in a county vintage.
    ///
    /// # Errors
    /// Refuses dependency and unknown state-prefix codes.
    pub const fn domestic_county(county: CountyGeoid) -> Result<Self, EconomicLocationError> {
        match county.jurisdiction() {
            CountyJurisdiction::State | CountyJurisdiction::DistrictOfColumbia => {
                Ok(Self::County(DomesticCounty(county)))
            }
            CountyJurisdiction::Dependency | CountyJurisdiction::Unknown => {
                Err(EconomicLocationError::NonDomesticCounty(county))
            }
        }
    }

    /// Six disjoint canonical bytes: county tag and five digits, or tag/code/zero padding.
    #[must_use]
    pub const fn canonical_bytes(self) -> [u8; 6] {
        match self {
            Self::County(county) => {
                let geoid = county.geoid().as_bytes();
                [0, geoid[0], geoid[1], geoid[2], geoid[3], geoid[4]]
            }
            Self::Foreign(id) => [1, id as u8, 0, 0, 0, 0],
            Self::Dependency(id) => [2, id as u8, 0, 0, 0, 0],
        }
    }

    /// Decode only the closed canonical form.
    ///
    /// # Errors
    /// Refuses unknown tags/codes, nonzero padding and non-domestic county prefixes.
    pub fn from_canonical_bytes(bytes: [u8; 6]) -> Result<Self, EconomicLocationError> {
        match bytes[0] {
            0 => {
                let county =
                    CountyGeoid::try_from([bytes[1], bytes[2], bytes[3], bytes[4], bytes[5]])
                        .map_err(EconomicLocationError::CountySyntax)?;
                Self::domestic_county(county)
            }
            1 | 2 => {
                if bytes[2..] != [0; 4] {
                    return Err(EconomicLocationError::NoncanonicalPadding);
                }
                if bytes[0] == 1 {
                    ForeignCounterpart::from_code(bytes[1])
                        .map(Self::Foreign)
                        .ok_or(EconomicLocationError::UnknownCounterpart(bytes[1]))
                } else {
                    UsDependency::from_code(bytes[1])
                        .map(Self::Dependency)
                        .ok_or(EconomicLocationError::UnknownDependency(bytes[1]))
                }
            }
            tag => Err(EconomicLocationError::UnknownTag(tag)),
        }
    }
}

impl std::fmt::Display for EconomicLocation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::County(county) => write!(f, "county:{}", county.geoid()),
            Self::Foreign(id) => write!(f, "foreign:{}", id.as_str()),
            Self::Dependency(id) => write!(f, "dependency:{}", id.m49()),
        }
    }
}

impl std::str::FromStr for EconomicLocation {
    type Err = EconomicLocationError;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        let (namespace, key) = value
            .split_once(':')
            .ok_or(EconomicLocationError::UnknownNamespace)?;
        match namespace {
            "county" => Self::domestic_county(
                CountyGeoid::try_from(key).map_err(EconomicLocationError::CountySyntax)?,
            ),
            "foreign" => ForeignCounterpart::from_key(key)
                .map(Self::Foreign)
                .ok_or(EconomicLocationError::UnknownCounterpartKey),
            "dependency" => UsDependency::from_m49(key)
                .map(Self::Dependency)
                .ok_or(EconomicLocationError::UnknownDependencyKey),
            _ => Err(EconomicLocationError::UnknownNamespace),
        }
    }
}

impl serde::Serialize for EconomicLocation {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        serializer.collect_str(self)
    }
}

impl<'de> serde::Deserialize<'de> for EconomicLocation {
    fn deserialize<D: serde::Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        struct LocationVisitor;

        impl serde::de::Visitor<'_> for LocationVisitor {
            type Value = EconomicLocation;

            fn expecting(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                formatter.write_str("an exact county:, foreign:, or dependency: location key")
            }

            fn visit_str<E: serde::de::Error>(self, value: &str) -> Result<Self::Value, E> {
                value.parse().map_err(E::custom)
            }
        }

        deserializer.deserialize_str(LocationVisitor)
    }
}

impl std::fmt::Display for EconomicLocationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "economic location refused: {self:?}")
    }
}
impl std::error::Error for EconomicLocationError {}
