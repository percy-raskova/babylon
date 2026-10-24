//! Restart-safe installation of the native schema and immutable H3 reference bundle.

use crate::michigan_dynamic_hex_foundation;
use postgres::Config;

use crate::current_schema;
use crate::current_schema::{CurrentSchemaError, CurrentSchemaReport};
use crate::h3_reference_cohort;
use crate::h3_reference_cohort::H3ReferenceCohortError;
use crate::h3_reference_installer;
use crate::h3_reference_installer::{H3ReferenceInstallError, H3ReferenceInstallReport};
use crate::michigan_dynamic_hex_foundation::MichiganDynamicHexFoundationDecodeError;
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;

/// Receipts from the native schema and immutable reference installation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CurrentRuntimeBootstrapReport {
    /// Exact immutable Michigan H3 reference-bundle installation receipt.
    pub reference_bundle_installation: H3ReferenceInstallReport,
    /// Completed native schema construction.
    pub schema: CurrentSchemaReport,
}

/// Closed failure boundary for native H3 bootstrap.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CurrentRuntimeBootstrapError {
    /// The embedded H3 source fixture failed before database access.
    ReferenceCohort(H3ReferenceCohortError),
    /// The embedded Michigan foundation fixture failed before database access.
    ReferenceFoundation(MichiganDynamicHexFoundationDecodeError),
    /// The current schema could not be constructed or verified.
    CurrentSchema(CurrentSchemaError),
    /// The exact immutable reference bundle could not be installed.
    ReferenceInstall(H3ReferenceInstallError),
}

impl std::fmt::Display for CurrentRuntimeBootstrapError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        write!(formatter, "H3 reader bootstrap failed: {self:?}")
    }
}

impl std::error::Error for CurrentRuntimeBootstrapError {}

/// Validate source bytes, construct the current schema, and install its reference bundle.
///
/// Existing current schemas are verified before idempotent installation. Unrelated database
/// objects cannot enter the exact fresh/current schema census and are never adopted or deleted.
///
/// # Errors
/// Returns [`CurrentRuntimeBootstrapError`] for invalid source data, a refused database shape,
/// incomplete schema construction, or a failed immutable reference installation.
pub fn bootstrap_current_runtime(
    config: &Config,
) -> Result<CurrentRuntimeBootstrapReport, CurrentRuntimeBootstrapError> {
    let cohort = h3_reference_cohort::representative_h3_reference_cohort()
        .map_err(CurrentRuntimeBootstrapError::ReferenceCohort)?;
    let foundation = michigan_dynamic_hex_foundation::michigan_dynamic_hex_foundation()
        .map_err(CurrentRuntimeBootstrapError::ReferenceFoundation)?;
    let schema = current_schema::install_current_schema(config)
        .map_err(CurrentRuntimeBootstrapError::CurrentSchema)?;
    let reference_bundle_installation =
        h3_reference_installer::install_michigan_h3_reference_bundle(config, cohort, foundation)
            .map_err(CurrentRuntimeBootstrapError::ReferenceInstall)?;
    Ok(CurrentRuntimeBootstrapReport {
        reference_bundle_installation,
        schema,
    })
}
