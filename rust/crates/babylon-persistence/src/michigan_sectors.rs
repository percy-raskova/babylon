//! Pinned observed county-sector cells, without enterprise or mechanics inference.

#[cfg(test)]
mod tests;

#[path = "michigan_sectors/sources.rs"]
mod sources;

#[allow(unused_imports)]
use sources::{
    admit, ascii_json_line, checked_csv, county_index, csv_record, decode_gzip, integer, parse_row,
    semantic_digest, source_pins, SourceManifest, SourcePin, ARTIFACT, COLUMNS, DOMAIN, MAX_BYTES,
    MAX_ROWS, MAX_SOURCE_BYTES, SECTOR_CODES, SOURCE_MANIFEST, SOURCE_MANIFEST_SHA256,
};
pub use sources::{
    michigan_county_sectors, MichiganCountySector, MichiganCountySectors, MichiganSectorCode,
    MichiganSectorDisclosure, MichiganSectorDisposition, MichiganSectorsError,
    QCEW_SECTORS_ARTIFACT_SHA256, QCEW_SECTORS_SEMANTIC_SHA256, QCEW_SECTORS_VINTAGE,
};

#[allow(unused_imports)]
use crate::michigan_economy::digest_hex;
#[allow(unused_imports)]
use babylon_kernel::content_digest::sha256_of;
#[allow(unused_imports)]
use serde::{Deserialize, Serialize};
#[allow(unused_imports)]
use std::fmt::Write as _;
#[allow(unused_imports)]
use std::io::Read as _;
#[allow(unused_imports)]
use std::sync::OnceLock;
