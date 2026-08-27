//! Durable database identities that never enter deterministic engine physics.

use h3o::{CellIndex, Resolution};
use std::str::FromStr;
use uuid::Uuid;

/// Durable `PostgreSQL` campaign key, distinct from the deterministic session namespace.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct CampaignId(Uuid);

impl CampaignId {
    /// Wrap an already-minted UUID as a campaign storage identity.
    #[must_use]
    pub fn from_uuid(uuid: Uuid) -> Self {
        Self(uuid)
    }

    /// Return the UUID used by `PostgreSQL` foreign keys and partitions.
    #[must_use]
    pub fn as_uuid(&self) -> &Uuid {
        &self.0
    }

    /// Borrow the exact 16 UUID bytes in network order.
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8; 16] {
        self.0.as_bytes()
    }
}

/// Canonical H3 cell identity stored at the `PostgreSQL` seam.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
#[repr(transparent)]
pub struct H3CellId(u64);

/// Typed H3 cell identity failures with no catch-all variant.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum H3CellIdError {
    /// The raw unsigned value is not a valid H3 cell index.
    InvalidCellIndex { raw: u64 },
    /// `PostgreSQL` delivered a negative signed value.
    NegativeSqlValue { raw: i64 },
    /// A valid H3 cell exceeded `PostgreSQL`'s signed range.
    SqlValueOutOfRange { raw: u64 },
    /// The input text length was not the canonical 15 bytes.
    InvalidTextLength { actual_bytes: usize },
    /// The input text contained at least one non-ASCII byte.
    NonAsciiText,
    /// The input text was not lowercase hexadecimal.
    NonLowercaseHexText,
    /// The requested ancestor resolution exceeds H3's 0-15 range.
    ResolutionOutOfRange { requested: u8 },
    /// The requested ancestor resolution is finer than the current cell.
    AncestorResolutionTooFine { current: u8, requested: u8 },
}

impl H3CellId {
    /// Return the stored unsigned identity.
    #[must_use]
    pub fn as_u64(self) -> u64 {
        self.0
    }

    /// Return the cell resolution as one unsigned byte.
    #[must_use]
    pub fn resolution(self) -> u8 {
        u8::from(self.to_cell_index().resolution())
    }

    /// Return the semantic immediate parent, or `None` at resolution zero.
    #[must_use]
    pub fn immediate_parent(self) -> Option<Self> {
        let current = self.resolution();
        if current == 0 {
            return None;
        }
        self.ancestor_at(current - 1).ok()
    }

    /// Return the semantic ancestor at the requested resolution.
    ///
    /// # Errors
    /// Returns [`H3CellIdError`] if the request exceeds the legal H3 range or
    /// asks for a finer resolution than the current cell.
    pub fn ancestor_at(self, requested: u8) -> Result<Self, H3CellIdError> {
        let current = self.resolution();
        if requested > 15 {
            return Err(H3CellIdError::ResolutionOutOfRange { requested });
        }
        if requested > current {
            return Err(H3CellIdError::AncestorResolutionTooFine { current, requested });
        }
        if requested == current {
            return Ok(self);
        }
        let resolution = resolution_from_u8(requested)?;
        match self.to_cell_index().parent(resolution) {
            Some(parent) => Ok(Self::from_cell_index(parent)),
            None => Err(H3CellIdError::AncestorResolutionTooFine { current, requested }),
        }
    }

    /// Return the canonical unsigned big-endian bytes.
    #[must_use]
    pub fn to_be_bytes(self) -> [u8; 8] {
        self.0.to_be_bytes()
    }

    fn to_cell_index(self) -> CellIndex {
        CellIndex::try_from(self.0).expect("H3CellId guarantees validated raw identities")
    }

    fn from_cell_index(cell: CellIndex) -> Self {
        Self(u64::from(cell))
    }
}

impl TryFrom<u64> for H3CellId {
    type Error = H3CellIdError;

    fn try_from(raw: u64) -> Result<Self, Self::Error> {
        CellIndex::try_from(raw)
            .map(Self::from_cell_index)
            .map_err(|_| H3CellIdError::InvalidCellIndex { raw })
    }
}

impl TryFrom<i64> for H3CellId {
    type Error = H3CellIdError;

    fn try_from(raw: i64) -> Result<Self, Self::Error> {
        let unsigned = u64::try_from(raw).map_err(|_| H3CellIdError::NegativeSqlValue { raw })?;
        Self::try_from(unsigned)
    }
}

impl TryFrom<H3CellId> for i64 {
    type Error = H3CellIdError;

    fn try_from(cell: H3CellId) -> Result<Self, Self::Error> {
        i64::try_from(cell.as_u64())
            .map_err(|_| H3CellIdError::SqlValueOutOfRange { raw: cell.as_u64() })
    }
}

impl FromStr for H3CellId {
    type Err = H3CellIdError;

    fn from_str(text: &str) -> Result<Self, Self::Err> {
        if text.len() != 15 {
            return Err(H3CellIdError::InvalidTextLength {
                actual_bytes: text.len(),
            });
        }
        if !text.is_ascii() {
            return Err(H3CellIdError::NonAsciiText);
        }
        if text
            .bytes()
            .any(|byte| !matches!(byte, b'0'..=b'9' | b'a'..=b'f'))
        {
            return Err(H3CellIdError::NonLowercaseHexText);
        }

        let raw = u64::from_str_radix(text, 16).map_err(|_| H3CellIdError::NonLowercaseHexText)?;
        let cell = Self::try_from(raw)?;
        if cell.to_string() != text {
            return Err(H3CellIdError::NonLowercaseHexText);
        }
        Ok(cell)
    }
}

impl std::fmt::Display for H3CellId {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "{:x}", self.0)
    }
}

impl std::error::Error for H3CellIdError {}

impl std::fmt::Display for H3CellIdError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "invalid H3 cell identity: {self:?}")
    }
}

fn resolution_from_u8(requested: u8) -> Result<Resolution, H3CellIdError> {
    Resolution::try_from(requested).map_err(|_| H3CellIdError::ResolutionOutOfRange { requested })
}
