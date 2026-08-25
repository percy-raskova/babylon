//! Public contract for the bounded representative H3 cohort installer.

use babylon_persistence::{
    install_representative_h3_cohort, H3ReferenceCohort, H3ReferenceInstallDisposition,
    H3ReferenceInstallError, H3ReferenceInstallReport, RefDigest,
};
use postgres::Config;

#[test]
fn installer_signature_cannot_accept_unvalidated_rows_or_caller_provenance() {
    let install: fn(
        &Config,
        &H3ReferenceCohort,
    ) -> Result<H3ReferenceInstallReport, H3ReferenceInstallError> =
        install_representative_h3_cohort;

    let _ = install;
}

#[test]
fn report_accessors_preserve_exact_provenance_and_bounded_count_types() {
    let _: fn(&H3ReferenceInstallReport) -> H3ReferenceInstallDisposition =
        H3ReferenceInstallReport::disposition;
    let _: fn(&H3ReferenceInstallReport) -> RefDigest = H3ReferenceInstallReport::ref_digest;
    let _: fn(&H3ReferenceInstallReport) -> RefDigest = H3ReferenceInstallReport::artifact_digest;
    let _: fn(&H3ReferenceInstallReport) -> i16 = H3ReferenceInstallReport::format_version;
    let _: for<'report> fn(&'report H3ReferenceInstallReport) -> &'report str =
        H3ReferenceInstallReport::artifact_name;
    let _: for<'report> fn(&'report H3ReferenceInstallReport) -> &'report str =
        H3ReferenceInstallReport::artifact_manifest_version;
    let _: fn(&H3ReferenceInstallReport) -> usize = H3ReferenceInstallReport::direct_cell_count;
    let _: fn(&H3ReferenceInstallReport) -> usize =
        H3ReferenceInstallReport::derived_ancestor_count;
    let _: fn(&H3ReferenceInstallReport) -> usize = H3ReferenceInstallReport::closure_cell_count;
    let _: fn(&H3ReferenceInstallReport) -> usize = H3ReferenceInstallReport::commit_attempts;
}

#[test]
fn disposition_does_not_conflate_install_idempotence_and_commit_reconciliation() {
    let installed = H3ReferenceInstallDisposition::Installed;
    let already_present = H3ReferenceInstallDisposition::AlreadyPresent;
    let reconciled = H3ReferenceInstallDisposition::ReconciledAfterAmbiguousCommit;

    assert_ne!(installed, already_present);
    assert_ne!(installed, reconciled);
    assert_ne!(already_present, reconciled);
}

#[test]
fn installer_failures_remain_a_typed_thread_safe_boundary() {
    fn assert_error<T: std::error::Error + Send + Sync + 'static>() {}

    assert_error::<H3ReferenceInstallError>();
}
