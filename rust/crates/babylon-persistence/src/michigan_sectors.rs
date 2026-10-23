//! Pinned observed county-sector cells, without enterprise or mechanics inference.

#[cfg(test)]
mod tests;

#[path = "michigan_sectors/sources.rs"]
mod sources;

#[cfg(test)]
use sources::{
    admit, ascii_json_line, checked_csv, county_index, csv_record, decode_gzip, integer, parse_row,
    semantic_digest, source_pins, ARTIFACT, MAX_BYTES, MAX_ROWS, SECTOR_CODES, SOURCE_MANIFEST,
};
pub use sources::{
    michigan_county_sectors, MichiganCountySector, MichiganCountySectors, MichiganSectorCode,
    MichiganSectorDisclosure, MichiganSectorDisposition, MichiganSectorsError,
    QCEW_SECTORS_ARTIFACT_SHA256, QCEW_SECTORS_SEMANTIC_SHA256, QCEW_SECTORS_VINTAGE,
};
