//! Bounded lossless storage for immutable Archive publication bodies.
//! Storage framing changes; semantic page/revision hashes remain decoded-field hashes.

use super::record::RevisionRecord;
use crate::storage_compression::{compress_exact, decompress_exact, StorageCompressionError};
use crate::SemanticArchiveError;
use babylon_kernel::content_digest::sha256_of;

const DOMAIN: &[u8] = b"BabylonArchivePageBodyV1\0";
pub(super) const ENCODING: i16 = 1;
const TITLE_BYTES: usize = 4_096;
const PAGE_BYTES: usize = 1_048_576;
const EMISSION_BYTES: usize = PAGE_BYTES * 8;
// The exact existing five-field logical limits, plus domain and u32 lengths.
pub(super) const MAX_BODY_BYTES: usize =
    DOMAIN.len() + 5 * 4 + TITLE_BYTES + PAGE_BYTES * 3 + EMISSION_BYTES;
pub(super) const MAX_ENCODED_BYTES: usize = MAX_BODY_BYTES + MAX_BODY_BYTES / 256 + 1_024;

#[derive(Debug)]
pub(super) enum Error {
    UnsupportedEncoding,
    LengthLimit,
    Allocation,
    EmptyTitle,
    NullByte,
    Domain,
    Truncated,
    Trailing,
    Utf8,
    Compression(StorageCompressionError),
    Semantic(SemanticArchiveError),
}

impl Error {
    fn from_compression(error: StorageCompressionError) -> Self {
        match error {
            StorageCompressionError::LengthLimit => Self::LengthLimit,
            StorageCompressionError::Compress
            | StorageCompressionError::MalformedFrame
            | StorageCompressionError::TrailingFrame
            | StorageCompressionError::Decompress
            | StorageCompressionError::DecodedLength
            | StorageCompressionError::DigestMismatch => Self::Compression(error),
        }
    }
    pub(super) fn into_semantic(self) -> SemanticArchiveError {
        match self {
            Self::LengthLimit | Self::Allocation => SemanticArchiveError::CollectionBound,
            Self::Compression(error) => match error {
                StorageCompressionError::LengthLimit => SemanticArchiveError::CollectionBound,
                StorageCompressionError::Compress
                | StorageCompressionError::MalformedFrame
                | StorageCompressionError::TrailingFrame
                | StorageCompressionError::Decompress
                | StorageCompressionError::DecodedLength
                | StorageCompressionError::DigestMismatch => {
                    SemanticArchiveError::StoredPageMismatch
                }
            },
            Self::Semantic(error) => {
                let _ = error;
                SemanticArchiveError::StoredPageMismatch
            }
            Self::UnsupportedEncoding
            | Self::EmptyTitle
            | Self::NullByte
            | Self::Domain
            | Self::Truncated
            | Self::Trailing
            | Self::Utf8 => SemanticArchiveError::StoredPageMismatch,
        }
    }
}

// Bounded private observation of the actual codec call and publication scope.
#[cfg(test)]
thread_local! {
    static DECODE_COUNTS: std::cell::Cell<(usize,usize)> = const { std::cell::Cell::new((0,0)) };
    static PUBLICATION_DEPTH: std::cell::Cell<usize> = const { std::cell::Cell::new(0) };
    static DECODE_OBSERVER: std::cell::RefCell<Option<Box<dyn FnMut()>>> = const { std::cell::RefCell::new(None) };
}
#[cfg(test)]
pub(super) fn decode_counts() -> (usize, usize) {
    DECODE_COUNTS.with(std::cell::Cell::get)
}
#[cfg(test)]
pub(super) fn reset_decode_counts() {
    DECODE_COUNTS.with(|counts| counts.set((0, 0)));
}
#[cfg(test)]
pub(super) struct PublicationObservation;
#[cfg(test)]
impl PublicationObservation {
    pub(super) fn enter() -> Self {
        PUBLICATION_DEPTH.with(|depth| {
            depth.set(
                depth
                    .get()
                    .checked_add(1)
                    .expect("bounded publication nesting"),
            );
        });
        Self
    }
}
#[cfg(test)]
impl Drop for PublicationObservation {
    fn drop(&mut self) {
        PUBLICATION_DEPTH.with(|depth| {
            depth.set(
                depth
                    .get()
                    .checked_sub(1)
                    .expect("balanced publication scope"),
            );
        });
    }
}
#[cfg(test)]
pub(super) struct DecodeObservation;
#[cfg(test)]
pub(super) fn observe_decode(observer: impl FnMut() + 'static) -> DecodeObservation {
    DECODE_OBSERVER.with(|slot| {
        assert!(slot.borrow().is_none());
        *slot.borrow_mut() = Some(Box::new(observer));
    });
    DecodeObservation
}
#[cfg(test)]
impl Drop for DecodeObservation {
    fn drop(&mut self) {
        DECODE_OBSERVER.with(|slot| *slot.borrow_mut() = None);
    }
}
#[cfg(test)]
fn observe_decompression() {
    let inside = PUBLICATION_DEPTH.with(|depth| depth.get() > 0);
    DECODE_COUNTS.with(|counts| {
        let (total, in_publication) = counts.get();
        counts.set((
            total.checked_add(1).expect("bounded decode observations"),
            in_publication
                .checked_add(usize::from(inside))
                .expect("bounded decode observations"),
        ));
    });
    DECODE_OBSERVER.with(|slot| {
        if let Some(observer) = slot.borrow_mut().as_mut() {
            observer();
        }
    });
}

#[derive(Debug, PartialEq, Eq)]
pub(super) struct EncodedBody {
    pub encoding: i16,
    pub decoded_length: u32,
    pub decoded_sha256: [u8; 32],
    pub bytes: Vec<u8>,
}

/// Storage-private exact strings; the existing record remains semantic authority.
pub(super) struct DecodedBody {
    pub title: String,
    pub markdown: String,
    pub search_text: String,
    pub provenance_json: String,
    pub emission_json: String,
}

type Result<T> = std::result::Result<T, Error>;

/// Encode only an already checked immutable publication, before the writer transaction.
pub(super) fn encode(record: &RevisionRecord) -> Result<EncodedBody> {
    let emission = record.emission.encode().map_err(Error::Semantic)?;
    let fields = [
        (record.title.as_str(), TITLE_BYTES),
        (record.markdown.as_str(), PAGE_BYTES),
        (record.search_text.as_str(), PAGE_BYTES),
        (record.provenance_json.as_str(), PAGE_BYTES),
        (emission.as_str(), EMISSION_BYTES),
    ];
    let capacity = fields
        .iter()
        .try_fold(DOMAIN.len(), |size, (field, limit)| {
            if field.len() > *limit || field.as_bytes().contains(&0) {
                return Err(if field.len() > *limit {
                    Error::LengthLimit
                } else {
                    Error::NullByte
                });
            }
            size.checked_add(4)
                .and_then(|size| size.checked_add(field.len()))
                .ok_or(Error::LengthLimit)
        })?;
    if record.title.is_empty() {
        return Err(Error::EmptyTitle);
    }
    let mut packed = Vec::new();
    packed
        .try_reserve_exact(capacity)
        .map_err(|_| Error::Allocation)?;
    packed.extend_from_slice(DOMAIN);
    for (field, _) in fields {
        let length = u32::try_from(field.len()).map_err(|_| Error::LengthLimit)?;
        packed.extend_from_slice(&length.to_be_bytes());
        packed.extend_from_slice(field.as_bytes());
    }
    let decoded_length = u32::try_from(packed.len()).map_err(|_| Error::LengthLimit)?;
    let decoded_sha256 = sha256_of(&packed);
    let bytes = compress_exact(&packed, MAX_BODY_BYTES).map_err(Error::from_compression)?;
    if bytes.len() > MAX_ENCODED_BYTES {
        return Err(Error::LengthLimit);
    }
    Ok(EncodedBody {
        encoding: ENCODING,
        decoded_length,
        decoded_sha256,
        bytes,
    })
}

/// Authenticate framing and exact bytes before constructing the existing `RevisionRecord`.
/// The caller must additionally require decoded `search_text` == SQL search projection,
/// decode the canonical emission manifest, attach exact frozen membership and use
/// `CapturedRevision::admit` and the record digest; transport authentication never replaces those checks.
pub(super) fn decode(
    encoding: i16,
    expected_length: u32,
    expected_sha256: [u8; 32],
    encoded: &[u8],
) -> Result<DecodedBody> {
    if encoding != ENCODING {
        return Err(Error::UnsupportedEncoding);
    }
    if encoded.len() > MAX_ENCODED_BYTES {
        return Err(Error::LengthLimit);
    }
    let expected_length = usize::try_from(expected_length).map_err(|_| Error::LengthLimit)?;
    #[cfg(test)]
    observe_decompression();
    let packed = decompress_exact(encoded, expected_length, expected_sha256, MAX_BODY_BYTES)
        .map_err(Error::from_compression)?;
    let mut cursor = Cursor {
        bytes: &packed,
        offset: 0,
    };
    if cursor.take(DOMAIN.len())? != DOMAIN {
        return Err(Error::Domain);
    }
    let title = cursor.field(TITLE_BYTES)?;
    if title.is_empty() {
        return Err(Error::EmptyTitle);
    }
    let markdown = cursor.field(PAGE_BYTES)?;
    let search_text = cursor.field(PAGE_BYTES)?;
    let provenance_json = cursor.field(PAGE_BYTES)?;
    let emission_json = cursor.field(EMISSION_BYTES)?;
    if cursor.offset != packed.len() {
        return Err(Error::Trailing);
    }
    Ok(DecodedBody {
        title,
        markdown,
        search_text,
        provenance_json,
        emission_json,
    })
}

struct Cursor<'a> {
    bytes: &'a [u8],
    offset: usize,
}

impl<'a> Cursor<'a> {
    fn take(&mut self, length: usize) -> Result<&'a [u8]> {
        let end = self.offset.checked_add(length).ok_or(Error::LengthLimit)?;
        let value = self.bytes.get(self.offset..end).ok_or(Error::Truncated)?;
        self.offset = end;
        Ok(value)
    }

    fn field(&mut self, maximum: usize) -> Result<String> {
        let raw: [u8; 4] = self.take(4)?.try_into().map_err(|_| Error::Truncated)?;
        let length = usize::try_from(u32::from_be_bytes(raw)).map_err(|_| Error::LengthLimit)?;
        if length > maximum {
            return Err(Error::LengthLimit);
        }
        let bytes = self.take(length)?;
        if bytes.contains(&0) {
            return Err(Error::NullByte);
        }
        let text = std::str::from_utf8(bytes).map_err(|_| Error::Utf8)?;
        let mut value = String::new();
        value
            .try_reserve_exact(text.len())
            .map_err(|_| Error::Allocation)?;
        value.push_str(text);
        Ok(value)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn tuple(fields: [&[u8]; 5]) -> Vec<u8> {
        let mut raw = DOMAIN.to_vec();
        for field in fields {
            raw.extend_from_slice(&u32::try_from(field.len()).unwrap().to_be_bytes());
            raw.extend_from_slice(field);
        }
        raw
    }
    fn admit(raw: &[u8]) -> Result<DecodedBody> {
        let encoded = compress_exact(raw, MAX_BODY_BYTES).unwrap();
        decode(
            ENCODING,
            u32::try_from(raw.len()).unwrap(),
            sha256_of(raw),
            &encoded,
        )
    }
    #[test]
    fn exact_utf8_tuple_is_bounded_and_rejects_invalid_framing() {
        let raw = tuple(["題|é".as_bytes(), b"# markdown\n", b"search", b"[]", b"{}"]);
        let decoded = admit(&raw).unwrap();
        assert_eq!(decoded.title, "題|é");
        assert_eq!(decoded.markdown, "# markdown\n");
        assert_eq!(decoded.search_text, "search");
        assert_eq!(decoded.provenance_json, "[]");
        assert_eq!(decoded.emission_json, "{}");
        for fields in [
            [b"".as_slice(), b"m", b"s", b"[]", b"{}"],
            [b"a\0", b"m", b"s", b"[]", b"{}"],
            [b"\xff", b"m", b"s", b"[]", b"{}"],
        ] {
            assert!(admit(&tuple(fields)).is_err());
        }
        let mut trailing = raw.clone();
        trailing.push(0);
        assert!(admit(&trailing).is_err());
        let mut domain = raw.clone();
        domain[0] ^= 1;
        assert!(admit(&domain).is_err());
        let mut overlong = DOMAIN.to_vec();
        overlong.extend_from_slice(&u32::try_from(TITLE_BYTES + 1).unwrap().to_be_bytes());
        assert!(admit(&overlong).is_err());
        assert!(admit(&raw[..raw.len() - 1]).is_err());
        let encoded = compress_exact(&raw, MAX_BODY_BYTES).unwrap();
        assert!(decode(
            2,
            u32::try_from(raw.len()).unwrap(),
            sha256_of(&raw),
            &encoded
        )
        .is_err());
        assert!(decode(
            ENCODING,
            u32::try_from(raw.len()).unwrap(),
            [0; 32],
            &encoded
        )
        .is_err());
        assert!(decode(
            ENCODING,
            u32::try_from(raw.len() + 1).unwrap(),
            sha256_of(&raw),
            &encoded
        )
        .is_err());
        assert!(decode(
            ENCODING,
            u32::try_from(raw.len()).unwrap(),
            sha256_of(&raw),
            &encoded[..encoded.len() - 1]
        )
        .is_err());
        let mut appended = encoded;
        appended.extend(compress_exact(&[], 0).unwrap());
        assert!(decode(
            ENCODING,
            u32::try_from(raw.len()).unwrap(),
            sha256_of(&raw),
            &appended
        )
        .is_err());
    }
    #[test]
    fn bounded_errors_and_malformed_storage_have_distinct_semantic_refusals() {
        assert_eq!(
            Error::Allocation.into_semantic(),
            SemanticArchiveError::CollectionBound
        );
        let raw = tuple([b"a", b"m", b"s", b"[]", b"{}"]);
        let frame = compress_exact(&raw, MAX_BODY_BYTES).unwrap();
        let bounded = decode(
            ENCODING,
            u32::try_from(MAX_BODY_BYTES + 1).unwrap(),
            sha256_of(&raw),
            &frame,
        )
        .err()
        .unwrap();
        assert_eq!(
            bounded.into_semantic(),
            SemanticArchiveError::CollectionBound
        );
        assert_eq!(
            Error::LengthLimit.into_semantic(),
            SemanticArchiveError::CollectionBound
        );
        assert_eq!(
            Error::from_compression(StorageCompressionError::LengthLimit).into_semantic(),
            SemanticArchiveError::CollectionBound
        );
        for error in [
            Error::UnsupportedEncoding,
            Error::Domain,
            Error::Utf8,
            Error::NullByte,
            Error::Truncated,
            Error::Trailing,
            Error::EmptyTitle,
            Error::from_compression(StorageCompressionError::DigestMismatch),
            Error::Semantic(SemanticArchiveError::InvalidText),
        ] {
            assert_eq!(
                error.into_semantic(),
                SemanticArchiveError::StoredPageMismatch
            );
        }
    }
}
