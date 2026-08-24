//! Post-commit evidence contracts that never feed engine judgment.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

mod classifier;
mod digest;
mod records;
mod wire;

pub use classifier::{
    classify_persistence, classify_sfs, PersistenceClass, PersistenceClassError, SfsClass,
    SfsClassError,
};
pub use digest::{record_digest, Digest32, RecordDigest};
pub use records::{
    practice_attempt_row_id, PracticeAttemptLedgerV1, PracticeAttemptRowV1, PracticeCandidateRowV1,
    PracticeCandidateScheduleV1, PracticeDispositionV1, RunIdentityField, RunIdentityV1,
    SfsPreregistrationV1, SfsRecordError, SfsSampleV1, SfsTraceV1,
};
pub use wire::{
    canonical_envelope, decode_envelope, PayloadCursor, PayloadEncoder, SfsWireError, T3Record,
};

#[cfg(test)]
mod tests {
    #[test]
    fn shared_normalizer_exports_the_pinned_unicode_data_version() {
        assert_eq!(unicode_normalization::UNICODE_VERSION, (17, 0, 0));
    }
}
