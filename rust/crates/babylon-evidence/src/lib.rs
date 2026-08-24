//! Post-commit evidence contracts that never feed engine judgment.
#![forbid(unsafe_code)]
#![warn(clippy::pedantic)]

mod classifier;
mod digest;
mod wire;

pub use classifier::{
    classify_persistence, classify_sfs, PersistenceClass, PersistenceClassError, SfsClass,
    SfsClassError,
};
pub use digest::{record_digest, Digest32, RecordDigest};
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
