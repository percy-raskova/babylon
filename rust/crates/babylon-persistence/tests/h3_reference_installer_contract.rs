//! Public contract for the bounded representative H3 cohort installer.

use babylon_persistence::{
    install_representative_h3_cohort, H3ReferenceCohort, H3ReferenceDatabaseDiagnostic,
    H3ReferenceInstallDisposition, H3ReferenceInstallError, H3ReferenceInstallOperation,
    H3ReferenceInstallReport, H3ReferenceMembershipReadContext, RefDigest,
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
fn membership_read_operations_distinguish_query_and_lifecycle_context() {
    let initial = H3ReferenceMembershipReadContext::InitialInspection;
    let attempt = H3ReferenceMembershipReadContext::CommitAttempt { attempt: 1 };
    let reconciliation =
        H3ReferenceMembershipReadContext::AmbiguousCommitReconciliation { attempt: 1 };

    assert_ne!(initial, attempt);
    assert_ne!(attempt, reconciliation);
    assert_ne!(
        H3ReferenceInstallOperation::ReadMembershipCardinality { context: initial },
        H3ReferenceInstallOperation::ReadMembershipRows { context: initial },
    );
}

#[test]
fn database_diagnostic_exposes_a_typed_server_error_boundary() {
    let _: for<'diagnostic> fn(
        &'diagnostic H3ReferenceDatabaseDiagnostic,
    ) -> Option<&'diagnostic postgres::error::DbError> = H3ReferenceDatabaseDiagnostic::server;
}

#[test]
fn installer_failures_remain_a_typed_thread_safe_boundary() {
    fn assert_error<T: std::error::Error + Send + Sync + Clone + Eq + 'static>() {}

    assert_error::<H3ReferenceInstallError>();
}
