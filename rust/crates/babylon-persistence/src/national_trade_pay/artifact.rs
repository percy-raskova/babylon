//! Leaf implementation for the parent module; public paths stay on the parent.

use super::model::{NationalTradePayError as Error, NationalTradePayReference, TradePayRow};
use super::parse;
use crate::national_cohorts::{self, CohortReference, NationalCohortReference};
use crate::national_counties::{self, NationalCountyReference};
use babylon_kernel::content_digest;
use babylon_kernel::economic_identity::TradeSet;
use flate2::bufread::GzDecoder;
use std::io::Read;
use std::sync::OnceLock;

/// The pay table of stage 1, embedded.
pub(crate) const ARTIFACT: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/../../../src/babylon/data/reference/economy/national_trade_pay_2024.csv.gz"
));

const MAX_COMPRESSED_BYTES: usize = 2_097_152;
const MAX_CSV_BYTES: usize = 8_388_608;
const ROW_COUNT: usize = 65_065;

// Exact deterministic gzip digest recorded by the source builder.
pub(crate) const ARTIFACT_SHA256: [u8; 32] = [
    200, 130, 137, 177, 6, 211, 122, 114, 58, 176, 117, 110, 81, 39, 177, 247, 31, 166, 101, 226,
    185, 43, 165, 8, 115, 211, 188, 94, 208, 240, 50, 103,
];

static REFERENCE: OnceLock<Result<NationalTradePayReference, Error>> = OnceLock::new();

impl NationalTradePayReference {
    /// Admit the supplied table bytes against the supplied twelve-trade cohort table and county
    /// capture. The table must hold one row for every admitted cohort group, and no other.
    ///
    /// # Errors
    /// Refuses altered bytes, bounds, malformed rows, and a table that does not cover the cohorts.
    pub fn decode_captured(
        bytes: &[u8],
        cohorts: &NationalCohortReference,
        counties: &NationalCountyReference,
    ) -> Result<Self, Error> {
        if bytes.len() > MAX_COMPRESSED_BYTES {
            return Err(Error::Bound);
        }
        if content_digest::sha256_of(bytes) != ARTIFACT_SHA256 {
            return Err(Error::ArtifactDigest);
        }
        let rows = parse::parse_csv(&decode_gzip(bytes)?, counties, ROW_COUNT)?;
        check_coverage(&rows, cohorts)?;
        Self::from_rows(rows, ARTIFACT_SHA256)
    }
}

/// One row for every admitted group of the twelve-trade cohort table, and no other.
pub(super) fn check_coverage(
    rows: &[TradePayRow],
    cohorts: &NationalCohortReference,
) -> Result<(), Error> {
    if cohorts.trades() != TradeSet::Twelve
        || rows.len() != ROW_COUNT
        || !rows
            .iter()
            .map(|row| row.key)
            .eq(cohorts.admitted_cohorts().map(CohortReference::key))
    {
        return Err(Error::Coverage);
    }
    Ok(())
}

/// The embedded pay table, decoded once against the embedded twelve-trade cohort table.
///
/// # Errors
/// Returns the exact refusal without a fallback.
pub fn national_trade_pay_reference() -> Result<&'static NationalTradePayReference, Error> {
    REFERENCE
        .get_or_init(|| {
            let counties =
                national_counties::national_county_reference().map_err(Error::CountyTable)?;
            let cohorts =
                national_cohorts::national_cohort_reference_v2().map_err(Error::CohortTable)?;
            NationalTradePayReference::decode_captured(ARTIFACT, cohorts, counties)
        })
        .as_ref()
        .map_err(Clone::clone)
}

pub(super) fn decode_gzip(bytes: &[u8]) -> Result<String, Error> {
    let mut decoder = GzDecoder::new(bytes);
    let mut text = String::new();
    decoder
        .by_ref()
        .take((MAX_CSV_BYTES + 1) as u64)
        .read_to_string(&mut text)
        .map_err(|_| Error::Compression)?;
    if text.len() > MAX_CSV_BYTES {
        return Err(Error::Bound);
    }
    if !decoder.into_inner().is_empty() {
        return Err(Error::Compression);
    }
    Ok(text)
}
