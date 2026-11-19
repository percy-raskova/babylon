//! Captured ACS 2020–2024 resident age estimates for the 3,144 domestic counties.
use crate::national_counties::NationalCountyReference;
use babylon_kernel::content_digest;
use babylon_kernel::geography::CountyGeoid;
use babylon_material_circuit::ResidentAges;
use flate2::bufread::GzDecoder;
use std::collections::BTreeMap;
use std::fmt::{Display, Formatter, Result as FmtResult};
use std::io::Read;
use std::sync::OnceLock;

pub(crate) const ARTIFACT: &[u8] = include_bytes!(
    "../../../../src/babylon/data/reference/economy/national_age_reference_2024.csv.gz"
);

const SHA256: [u8; 32] = [
    181, 119, 130, 216, 144, 16, 28, 5, 157, 232, 116, 215, 202, 60, 190, 211, 136, 132, 123, 229,
    18, 213, 182, 237, 133, 108, 214, 134, 29, 136, 53, 84,
];

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum AgeReferenceError {
    Digest,
    Csv,
    CountyRoster,
    CountyControl(CountyGeoid),
}

impl Display for AgeReferenceError {
    fn fmt(&self, out: &mut Formatter<'_>) -> FmtResult {
        write!(out, "national county age reference refused: {self:?}")
    }
}
impl std::error::Error for AgeReferenceError {}

/// Derived margins for resident persons, including group quarters.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct NationalAgeReference {
    pub(crate) counties: BTreeMap<CountyGeoid, ResidentAges>,
}

impl NationalAgeReference {
    /// # Errors
    /// Refuses a changed artifact, roster, or age estimate that disagrees with the captured county.
    pub fn decode_captured(
        bytes: &[u8],
        counties: &NationalCountyReference,
    ) -> Result<Self, AgeReferenceError> {
        if bytes.len() != ARTIFACT.len() || content_digest::sha256_of(bytes) != SHA256 {
            return Err(AgeReferenceError::Digest);
        }
        let mut text = String::new();
        GzDecoder::new(bytes)
            .read_to_string(&mut text)
            .map_err(|_| AgeReferenceError::Csv)?;
        let mut rows = text.lines();
        if rows.next() != Some("county_geoid,under_16,age_16_17,age_18_64,age_65_plus") {
            return Err(AgeReferenceError::Csv);
        }
        let mut ages = BTreeMap::new();
        for county in counties.counties() {
            let line = rows.next().ok_or(AgeReferenceError::CountyRoster)?;
            let mut cells = line.split(',');
            let geoid = cells
                .next()
                .and_then(|value| CountyGeoid::try_from(value).ok())
                .ok_or(AgeReferenceError::Csv)?;
            if geoid != county.geoid() {
                return Err(AgeReferenceError::CountyRoster);
            }
            let mut count = || {
                cells
                    .next()
                    .and_then(|field| field.parse::<u64>().ok())
                    .ok_or(AgeReferenceError::Csv)
            };
            let bands = ResidentAges {
                under_16: count()?,
                age_16_17: count()?,
                age_18_64: count()?,
                age_65_plus: count()?,
            };
            let eligible = bands
                .eligible()
                .map_err(|_| AgeReferenceError::CountyControl(geoid))?;
            let total = bands
                .persons()
                .map_err(|_| AgeReferenceError::CountyControl(geoid))?;
            let resident = county.residents();
            if cells.next().is_some()
                || Some(total) != resident.population_persons.estimate.value()
                || Some(eligible) != resident.age_16_plus_persons.estimate.value()
            {
                return Err(AgeReferenceError::CountyControl(geoid));
            }
            ages.insert(geoid, bands);
        }
        if rows.next().is_some() {
            return Err(AgeReferenceError::CountyRoster);
        }
        Ok(Self { counties: ages })
    }

    /// Ages derived from the captured county estimates, before allocation to game cohorts.
    #[must_use]
    pub fn county(&self, geoid: CountyGeoid) -> Option<&ResidentAges> {
        self.counties.get(&geoid)
    }
}

/// Load the packaged opening reference. A recovered campaign uses its captured bytes.
/// # Errors
/// Refuses an unavailable or inconsistent county or age source.
pub fn national_age_reference() -> Result<&'static NationalAgeReference, AgeReferenceError> {
    static REFERENCE: OnceLock<Result<NationalAgeReference, AgeReferenceError>> = OnceLock::new();
    REFERENCE
        .get_or_init(|| {
            let counties = crate::national_counties::national_county_reference()
                .map_err(|_| AgeReferenceError::CountyRoster)?;
            NationalAgeReference::decode_captured(ARTIFACT, counties)
        })
        .as_ref()
        .map_err(|err| *err)
}
