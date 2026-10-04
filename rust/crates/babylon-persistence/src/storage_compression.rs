//! Bounded lossless storage frames; canonical hashes remain over decoded bytes.

use babylon_kernel::content_digest::sha256_of;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StorageCompressionError {
    LengthLimit,
    Compress,
    MalformedFrame,
    TrailingFrame,
    Decompress,
    DecodedLength,
    DigestMismatch,
}

pub(crate) fn compress_exact(
    bytes: &[u8],
    maximum: usize,
) -> Result<Vec<u8>, StorageCompressionError> {
    if bytes.len() > maximum {
        return Err(StorageCompressionError::LengthLimit);
    }
    zstd::bulk::compress(bytes, 3).map_err(|_| StorageCompressionError::Compress)
}

pub(crate) fn decompress_exact(
    encoded: &[u8],
    expected_length: usize,
    expected_sha256: [u8; 32],
    maximum: usize,
) -> Result<Vec<u8>, StorageCompressionError> {
    if expected_length > maximum {
        return Err(StorageCompressionError::LengthLimit);
    }
    if !encoded.starts_with(&[0x28, 0xb5, 0x2f, 0xfd]) {
        return Err(StorageCompressionError::MalformedFrame);
    }
    let frame_length = zstd::zstd_safe::find_frame_compressed_size(encoded)
        .map_err(|_| StorageCompressionError::MalformedFrame)?;
    if frame_length != encoded.len() {
        return Err(StorageCompressionError::TrailingFrame);
    }
    let bytes = zstd::bulk::decompress(encoded, expected_length)
        .map_err(|_| StorageCompressionError::Decompress)?;
    if bytes.len() != expected_length {
        return Err(StorageCompressionError::DecodedLength);
    }
    if sha256_of(&bytes) != expected_sha256 {
        return Err(StorageCompressionError::DigestMismatch);
    }
    Ok(bytes)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn single_frame_restores_every_byte_with_a_bounded_canonical_claim() {
        for bytes in [b"".as_slice(), b"exact currency bits and typed identities"] {
            let encoded = compress_exact(bytes, bytes.len()).unwrap();
            assert_eq!(
                decompress_exact(&encoded, bytes.len(), sha256_of(bytes), bytes.len()).unwrap(),
                bytes
            );
        }
    }

    #[test]
    fn appended_empty_frame_cannot_hide_behind_the_same_decoded_digest() {
        let bytes = b"committed state";
        let mut encoded = compress_exact(bytes, bytes.len()).unwrap();
        encoded.extend(compress_exact(&[], 0).unwrap());
        assert!(decompress_exact(&encoded, bytes.len(), sha256_of(bytes), bytes.len()).is_err());
    }

    #[test]
    fn limits_and_altered_canonical_claims_refuse() {
        let bytes = b"committed state";
        assert_eq!(
            compress_exact(bytes, 1),
            Err(StorageCompressionError::LengthLimit)
        );
        let encoded = compress_exact(bytes, bytes.len()).unwrap();
        assert_eq!(
            decompress_exact(&encoded, bytes.len(), sha256_of(bytes), 1),
            Err(StorageCompressionError::LengthLimit)
        );
        assert_eq!(
            decompress_exact(&encoded, bytes.len() + 1, sha256_of(bytes), bytes.len() + 1),
            Err(StorageCompressionError::DecodedLength)
        );
        assert_eq!(
            decompress_exact(&encoded, bytes.len(), [0; 32], bytes.len()),
            Err(StorageCompressionError::DigestMismatch)
        );
        assert!(decompress_exact(
            &encoded[..encoded.len() - 1],
            bytes.len(),
            sha256_of(bytes),
            bytes.len()
        )
        .is_err());
    }
}
