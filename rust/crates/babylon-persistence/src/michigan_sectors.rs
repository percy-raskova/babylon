//! Pinned observed county-sector cells, without enterprise or mechanics inference.

#[cfg(test)]
mod tests;

#[path = "michigan_sectors/sources.rs"]
mod sources;

pub use sources::{
    michigan_county_sectors, MichiganCountySector, MichiganCountySectors, MichiganSectorCode,
    MichiganSectorDisclosure, MichiganSectorDisposition, MichiganSectorsError,
    QCEW_SECTORS_ARTIFACT_SHA256, QCEW_SECTORS_SEMANTIC_SHA256, QCEW_SECTORS_VINTAGE,
};
