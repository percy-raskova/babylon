//! Exact binary codecs for money, choice endpoints and bounded payloads.
//!
//! Canonical identities hash decoded bytes, never stored bytes. Money is signed
//! `i128` micro-units in sixteen canonical big-endian bytes. Choice interval
//! endpoints and counts that may equal `2^64` use sixteen big-endian unsigned
//! bytes with the exact governed upper-bound check. Immutable bulk payloads are
//! one exact zstd frame; the small mutable service singleton stays literal.

use babylon_kernel::content_digest;

use crate::sqlite_store::SaveError;
use crate::storage_compression;
use crate::storage_compression::StorageCompressionError;

/// Width of one canonical signed money value.
pub const MONEY_BYTES: usize = 16;

/// Width of one canonical unsigned choice endpoint.
pub const CHOICE_ENDPOINT_BYTES: usize = 16;

/// Exact governed upper bound for a choice endpoint or count.
pub const MAX_CHOICE_ENDPOINT: u128 = 1_u128 << 64;

/// Decoded ceiling for one state chunk.
pub const MAX_STATE_CHUNK_BYTES: usize = 4 * 1024 * 1024;

/// Decoded ceiling for one captured content or compiled-definition chunk.
pub const MAX_CONTENT_CHUNK_BYTES: usize = 4 * 1024 * 1024;

/// Decoded ceiling for one recent-detail row.
pub const MAX_RECENT_DETAIL_BYTES: usize = 4 * 1024 * 1024;

/// Decoded ceiling for one permanent journal record.
pub const MAX_PERMANENT_JOURNAL_BYTES: usize = 16 * 1024 * 1024;

/// Decoded ceiling for the single service-state record.
pub const MAX_SERVICE_STATE_BYTES: usize = 1024 * 1024;

/// Closed payload codec registry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub enum PayloadCodec {
    /// The stored bytes are the decoded bytes.
    Literal = 1,
    /// The stored bytes are one exact zstd frame.
    ZstdFrame = 2,
}

impl PayloadCodec {
    /// Return the exact versioned integer stored in a `codec` column.
    #[must_use]
    pub const fn code(self) -> i64 {
        self as i64
    }

    /// Recover a closed codec from its stored integer.
    ///
    /// # Errors
    ///
    /// Refuses an integer outside the closed registry.
    pub fn from_code(code: i64) -> Result<Self, SaveError> {
        match code {
            1 => Ok(Self::Literal),
            2 => Ok(Self::ZstdFrame),
            other => Err(SaveError::UnsupportedCodec { codec: other }),
        }
    }
}

/// Closed payload budget registry; each table owns one identity and one codec.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum PayloadBudget {
    /// Immutable captured content and compiled definitions.
    ContentEntry,
    /// Immutable current, opening or checkpoint state.
    StateChunk,
    /// Exhaustive technical receipts and events.
    RecentDetail,
    /// Permanent player history and earned knowledge.
    PermanentJournal,
    /// The small, independently writable Archive service record.
    ServiceState,
}

impl PayloadBudget {
    /// Return the published table name used in refusal reports.
    #[must_use]
    pub const fn table(self) -> &'static str {
        match self {
            Self::ContentEntry => "content_entry",
            Self::StateChunk => "state_chunk",
            Self::RecentDetail => "recent_detail",
            Self::PermanentJournal => "permanent_journal",
            Self::ServiceState => "service_state",
        }
    }

    /// Return the exact decoded-byte ceiling for this budget.
    #[must_use]
    pub const fn max_decoded_bytes(self) -> usize {
        match self {
            Self::ContentEntry => MAX_CONTENT_CHUNK_BYTES,
            Self::StateChunk => MAX_STATE_CHUNK_BYTES,
            Self::RecentDetail => MAX_RECENT_DETAIL_BYTES,
            Self::PermanentJournal => MAX_PERMANENT_JOURNAL_BYTES,
            Self::ServiceState => MAX_SERVICE_STATE_BYTES,
        }
    }

    /// Return the codec fixed by this format version for this budget.
    #[must_use]
    pub const fn codec(self) -> PayloadCodec {
        match self {
            Self::ContentEntry | Self::StateChunk | Self::RecentDetail | Self::PermanentJournal => {
                PayloadCodec::ZstdFrame
            }
            Self::ServiceState => PayloadCodec::Literal,
        }
    }
}

/// One encoded payload with its exact decoded identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EncodedPayload {
    /// Codec that produced the stored bytes.
    pub codec: PayloadCodec,
    /// Exact decoded byte length.
    pub raw_len: u32,
    /// SHA-256 of the exact decoded bytes.
    pub raw_hash: [u8; 32],
    /// Stored payload bytes.
    pub payload: Vec<u8>,
}

/// One stored payload as read back from a table row.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct StoredPayload<'a> {
    /// Codec recorded beside the payload.
    pub codec: PayloadCodec,
    /// Recorded decoded byte length.
    pub raw_len: u32,
    /// Recorded SHA-256 of the decoded bytes.
    pub raw_hash: [u8; 32],
    /// Stored payload bytes.
    pub payload: &'a [u8],
}

/// Encode signed micro-unit money as sixteen canonical big-endian bytes.
#[must_use]
pub fn encode_money_i128(value: i128) -> [u8; MONEY_BYTES] {
    value.to_be_bytes()
}

/// Decode sixteen canonical big-endian bytes as signed micro-unit money.
#[must_use]
pub fn decode_money_i128(bytes: [u8; MONEY_BYTES]) -> i128 {
    i128::from_be_bytes(bytes)
}

/// Encode one choice endpoint inside the governed `2^64` upper bound.
///
/// # Errors
///
/// Refuses an endpoint above [`MAX_CHOICE_ENDPOINT`] before publication.
pub fn encode_choice_endpoint_u128(value: u128) -> Result<[u8; CHOICE_ENDPOINT_BYTES], SaveError> {
    if value > MAX_CHOICE_ENDPOINT {
        return Err(SaveError::ChoiceEndpointOutOfRange { endpoint: value });
    }
    Ok(value.to_be_bytes())
}

/// Decode one stored choice endpoint and re-check the governed upper bound.
///
/// # Errors
///
/// Refuses a stored endpoint above [`MAX_CHOICE_ENDPOINT`].
pub fn decode_choice_endpoint_u128(bytes: [u8; CHOICE_ENDPOINT_BYTES]) -> Result<u128, SaveError> {
    let value = u128::from_be_bytes(bytes);
    if value > MAX_CHOICE_ENDPOINT {
        return Err(SaveError::ChoiceEndpointOutOfRange { endpoint: value });
    }
    Ok(value)
}

/// Encode one decoded payload under its table's exact byte and codec contract.
///
/// # Errors
///
/// Refuses decoded bytes above the budget before any statement executes, and
/// refuses a failed zstd frame construction.
pub fn encode_chunk_payload(
    budget: PayloadBudget,
    raw: &[u8],
) -> Result<EncodedPayload, SaveError> {
    let limit = budget.max_decoded_bytes();
    if raw.len() > limit {
        return Err(SaveError::PayloadTooLarge {
            table: budget.table(),
            limit,
            actual: raw.len(),
        });
    }
    let codec = budget.codec();
    let payload = match codec {
        PayloadCodec::Literal => raw.to_vec(),
        PayloadCodec::ZstdFrame => {
            storage_compression::compress_exact(raw, limit).map_err(|_| {
                SaveError::CompressionFailed {
                    table: budget.table(),
                }
            })?
        }
    };
    Ok(EncodedPayload {
        codec,
        raw_len: u32::try_from(raw.len()).map_err(|_| SaveError::Arithmetic {
            field: "payload raw length",
        })?,
        raw_hash: content_digest::sha256_of(raw),
        payload,
    })
}

/// Decode one stored payload and authenticate its length, hash and single frame.
///
/// # Errors
///
/// Refuses a decoded length above the budget before decompression, a codec
/// outside the table's fixed selection, and any truncated, trailing, oversized
/// or digest-mismatched stored bytes.
pub fn decode_chunk_payload(
    budget: PayloadBudget,
    stored: &StoredPayload<'_>,
) -> Result<Vec<u8>, SaveError> {
    let limit = budget.max_decoded_bytes();
    let raw_len = usize::try_from(stored.raw_len).map_err(|_| SaveError::Arithmetic {
        field: "payload raw length",
    })?;
    if raw_len > limit {
        return Err(SaveError::PayloadTooLarge {
            table: budget.table(),
            limit,
            actual: raw_len,
        });
    }
    let expected = budget.codec();
    if stored.codec != expected {
        return Err(SaveError::CodecMismatch {
            table: budget.table(),
            expected,
            actual: stored.codec,
        });
    }
    match stored.codec {
        PayloadCodec::Literal => {
            if stored.payload.len() != raw_len {
                return Err(corrupt(budget, "literal length does not match raw_len"));
            }
            if content_digest::sha256_of(stored.payload) != stored.raw_hash {
                return Err(corrupt(budget, "literal digest does not match raw_hash"));
            }
            Ok(stored.payload.to_vec())
        }
        PayloadCodec::ZstdFrame => {
            storage_compression::decompress_exact(stored.payload, raw_len, stored.raw_hash, limit)
                .map_err(|error| corrupt(budget, compression_reason(error)))
        }
    }
}

fn corrupt(budget: PayloadBudget, reason: &'static str) -> SaveError {
    SaveError::CorruptPayload {
        table: budget.table(),
        reason,
    }
}

fn compression_reason(error: StorageCompressionError) -> &'static str {
    match error {
        StorageCompressionError::LengthLimit => "decoded length exceeds the budget",
        StorageCompressionError::Compress => "the canonical frame could not be produced",
        StorageCompressionError::MalformedFrame => "the stored frame is malformed",
        StorageCompressionError::TrailingFrame => "the stored frame has trailing bytes",
        StorageCompressionError::Decompress => "the stored frame does not decompress",
        StorageCompressionError::DecodedLength => "the decoded length does not match raw_len",
        StorageCompressionError::DigestMismatch => "the decoded digest does not match raw_hash",
    }
}
