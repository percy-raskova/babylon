//! Sole restart-safe H3 reader bootstrap composition.

use postgres::Config;

use crate::h3_reference_cohort::{representative_h3_reference_cohort_v1, H3ReferenceCohortError};
use crate::h3_reference_installer::{
    install_michigan_h3_reference_bundle_v1, H3ReferenceInstallError, H3ReferenceInstallReport,
};
use crate::h3_shadow_backfill::{
    backfill_legacy_h3_shadow_keys, H3ShadowBackfillError, H3ShadowBackfillReport,
};
use crate::michigan_dynamic_hex_foundation::{
    michigan_dynamic_hex_foundation_v1, MichiganDynamicHexFoundationDecodeErrorV1,
};
use crate::schema_epoch::{
    migrate_schema_epoch, migrate_schema_epoch_to_h3_handoff, SchemaEpochError, SchemaEpochReport,
    CURRENT_SCHEMA_EPOCH, LEGACY_H3_CUTOVER_INPUT_EPOCH,
};

/// Successful receipts from the one restart-safe H3 reader bootstrap.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct H3ReaderBootstrapReportV1 {
    /// Migration receipt for the initial handoff attempt.
    pub handoff_epoch: SchemaEpochReport,
    /// Exact immutable Michigan H3 reference-bundle installation receipt.
    pub reference_bundle_installation: H3ReferenceInstallReport,
    /// Legacy-only shadow-key backfill receipt.
    pub shadow_backfill: Option<H3ShadowBackfillReport>,
    /// Terminal schema-epoch receipt after all required preparation.
    pub final_epoch: SchemaEpochReport,
}

/// Closed failure boundary for the one H3 reader bootstrap composition.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum H3ReaderBootstrapErrorV1 {
    /// The sole embedded H3 source fixture failed before database access.
    ReferenceCohort(H3ReferenceCohortError),
    /// The sole embedded Michigan foundation fixture failed before database access.
    ReferenceFoundation(MichiganDynamicHexFoundationDecodeErrorV1),
    /// The database could not reach the exact preparation handoff.
    HandoffEpoch(SchemaEpochError),
    /// The exact immutable H3 cohort could not be installed.
    ReferenceInstall(H3ReferenceInstallError),
    /// The frozen legacy H3 estate could not be backfilled.
    ShadowBackfill(H3ShadowBackfillError),
    /// The prepared legacy estate could not reach the terminal reader epoch.
    FinalEpoch(SchemaEpochError),
    /// The targeted migrator returned neither the handoff nor terminal epoch.
    UnexpectedHandoffEpoch { actual: usize },
}

impl std::fmt::Display for H3ReaderBootstrapErrorV1 {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "H3 reader bootstrap failed: {self:?}")
    }
}

impl std::error::Error for H3ReaderBootstrapErrorV1 {}

/// Validate the sole source fixture, install its cohort, and reach the canonical reader epoch.
///
/// Fixture validation deliberately runs before the first database operation. Exact legacy and
/// interrupted legacy-origin prefixes stop at epoch 6, install the immutable cohort, backfill the
/// governed shadow identities, and then use the normal migrator to reach epoch 7. Fresh and
/// already-current databases remain exact and idempotently install the same cohort at epoch 7.
///
/// # Errors
/// Returns [`H3ReaderBootstrapErrorV1`] for any fixture, migration, installation, backfill, or
/// terminal-epoch failure without introducing another migration or database authority.
pub fn bootstrap_h3_reader_epoch_v1(
    config: &Config,
) -> Result<H3ReaderBootstrapReportV1, H3ReaderBootstrapErrorV1> {
    let cohort = representative_h3_reference_cohort_v1()
        .map_err(H3ReaderBootstrapErrorV1::ReferenceCohort)?;
    let foundation = michigan_dynamic_hex_foundation_v1()
        .map_err(H3ReaderBootstrapErrorV1::ReferenceFoundation)?;
    let handoff_epoch = migrate_schema_epoch_to_h3_handoff(config)
        .map_err(H3ReaderBootstrapErrorV1::HandoffEpoch)?;
    if !matches!(
        handoff_epoch.final_applied,
        LEGACY_H3_CUTOVER_INPUT_EPOCH | CURRENT_SCHEMA_EPOCH
    ) {
        return Err(H3ReaderBootstrapErrorV1::UnexpectedHandoffEpoch {
            actual: handoff_epoch.final_applied,
        });
    }

    let reference_bundle_installation =
        install_michigan_h3_reference_bundle_v1(config, cohort, foundation)
            .map_err(H3ReaderBootstrapErrorV1::ReferenceInstall)?;
    let (shadow_backfill, final_epoch) =
        if handoff_epoch.final_applied == LEGACY_H3_CUTOVER_INPUT_EPOCH {
            let backfill = backfill_legacy_h3_shadow_keys(config)
                .map_err(H3ReaderBootstrapErrorV1::ShadowBackfill)?;
            let terminal =
                migrate_schema_epoch(config).map_err(H3ReaderBootstrapErrorV1::FinalEpoch)?;
            (Some(backfill), terminal)
        } else {
            (None, handoff_epoch.clone())
        };

    if final_epoch.final_applied != CURRENT_SCHEMA_EPOCH {
        return Err(H3ReaderBootstrapErrorV1::UnexpectedHandoffEpoch {
            actual: final_epoch.final_applied,
        });
    }
    Ok(H3ReaderBootstrapReportV1 {
        handoff_epoch,
        reference_bundle_installation,
        shadow_backfill,
        final_epoch,
    })
}
