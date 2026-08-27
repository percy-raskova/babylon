//! Bounded, provenance-pinned H3 reference-cohort construction.

use std::collections::BTreeSet;

use babylon_kernel::{sha256_of, RefDigestV1};

use crate::{H3CellId, H3CellIdError};

const SOURCE_DOMAIN: &[u8] = b"babylon.h3.reference-source.v1\0";
const ROW_DOMAIN: &[u8] = b"babylon.h3.reference-rows.v1\0";
const MEMBERSHIP_DOMAIN: &[u8] = b"babylon.h3.reference-membership.v1\0";
const COHORT_DOMAIN: &[u8] = b"babylon.h3.reference-cohort.v1\0";
const EXPECTED_SOURCE_CELLS: usize = 48_764;
const MAX_H3_RESOLUTIONS: usize = 16;
pub(crate) const MAX_H3_REFERENCE_CLOSURE_ROWS: usize =
    MAX_H3_REFERENCE_SOURCE_CELLS * MAX_H3_RESOLUTIONS;
const SOURCE_ROW_BYTES: usize = 8;
const CLOSURE_ROW_BYTES: usize = 49;
const MEMBERSHIP_ROW_BYTES: usize = 9;
const DIRECT_ORIGIN_CODE: u8 = 1;
const DERIVED_ANCESTOR_ORIGIN_CODE: u8 = 2;
const EXPECTED_SOURCE_COUNTS: [u32; MAX_H3_RESOLUTIONS] =
    [0, 0, 0, 0, 0, 3_192, 0, 45_572, 0, 0, 0, 0, 0, 0, 0, 0];
const EXPECTED_ARTIFACT_DIGEST: [u8; 32] = [
    0xe6, 0x0d, 0x93, 0xa4, 0x3d, 0x6c, 0x66, 0xe8, 0x4f, 0x1e, 0x53, 0xec, 0xaf, 0x63, 0x3a, 0xf5,
    0x91, 0x1b, 0xd5, 0xb4, 0x8b, 0x0e, 0xf0, 0xad, 0x6a, 0x01, 0x2f, 0x6d, 0x9f, 0x5b, 0x13, 0xa9,
];
const EXPECTED_SOURCE_DIGEST: [u8; 32] = [
    0xa4, 0x68, 0x5e, 0x6a, 0xd8, 0x82, 0x93, 0x0e, 0x70, 0x64, 0xcb, 0x22, 0x5e, 0xe6, 0x49, 0x15,
    0x5f, 0xb7, 0x4e, 0x52, 0xef, 0x8b, 0x7d, 0x75, 0x50, 0x69, 0x1a, 0x70, 0xa6, 0x08, 0x7f, 0x5a,
];

/// Fixed v1 ceiling checked before any allocation or source traversal.
pub const MAX_H3_REFERENCE_SOURCE_CELLS: usize = 65_536;

/// How one canonical cell entered the immutable reference cohort.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[repr(u8)]
pub enum H3ReferenceOrigin {
    /// The pinned artifact named this cell directly.
    Direct = DIRECT_ORIGIN_CODE,
    /// The importer added this strict parent to close the H3 hierarchy.
    DerivedAncestor = DERIVED_ANCESTOR_ORIGIN_CODE,
}

impl H3ReferenceOrigin {
    pub(crate) fn code(self) -> u8 {
        match self {
            Self::Direct => DIRECT_ORIGIN_CODE,
            Self::DerivedAncestor => DERIVED_ANCESTOR_ORIGIN_CODE,
        }
    }
}

/// One immutable row for `babylon_ref.h3_cell` plus its cohort provenance.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct H3ReferenceCellRow {
    cell_id: H3CellId,
    resolution: u8,
    immediate_parent: Option<H3CellId>,
    ancestor_r4: Option<H3CellId>,
    ancestor_r5: Option<H3CellId>,
    ancestor_r6: Option<H3CellId>,
    ancestor_r7: Option<H3CellId>,
    origin: H3ReferenceOrigin,
}

impl H3ReferenceCellRow {
    /// Canonical cell identity.
    #[must_use]
    pub fn cell_id(&self) -> H3CellId {
        self.cell_id
    }

    /// H3 resolution encoded by the identity.
    #[must_use]
    pub fn resolution(&self) -> u8 {
        self.resolution
    }

    /// Immediate semantic parent, absent at resolution zero.
    #[must_use]
    pub fn immediate_parent(&self) -> Option<H3CellId> {
        self.immediate_parent
    }

    /// Resolution-4 ancestor when the cell is at least resolution 4.
    #[must_use]
    pub fn ancestor_r4(&self) -> Option<H3CellId> {
        self.ancestor_r4
    }

    /// Resolution-5 ancestor when the cell is at least resolution 5.
    #[must_use]
    pub fn ancestor_r5(&self) -> Option<H3CellId> {
        self.ancestor_r5
    }

    /// Resolution-6 ancestor when the cell is at least resolution 6.
    #[must_use]
    pub fn ancestor_r6(&self) -> Option<H3CellId> {
        self.ancestor_r6
    }

    /// Resolution-7 ancestor when the cell is at least resolution 7.
    #[must_use]
    pub fn ancestor_r7(&self) -> Option<H3CellId> {
        self.ancestor_r7
    }

    /// Direct artifact membership or strict derived ancestry.
    #[must_use]
    pub fn origin(&self) -> H3ReferenceOrigin {
        self.origin
    }
}

/// Exact provenance and equivalence receipt for one built cohort.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct H3ReferenceCohortReceipt {
    artifact_digest: RefDigestV1,
    source_counts: [u32; MAX_H3_RESOLUTIONS],
    closure_counts: [u32; MAX_H3_RESOLUTIONS],
    source_digest: RefDigestV1,
    source_r5_digest: RefDigestV1,
    source_r7_digest: RefDigestV1,
    closure_digest: RefDigestV1,
    membership_digest: RefDigestV1,
    ref_digest: RefDigestV1,
    direct_cell_count: usize,
    derived_ancestor_count: usize,
}

impl H3ReferenceCohortReceipt {
    /// SHA-256 identity of the pinned source artifact bytes.
    #[must_use]
    pub fn artifact_digest(&self) -> RefDigestV1 {
        self.artifact_digest
    }

    /// Number of direct source identities.
    #[must_use]
    pub fn source_cell_count(&self) -> usize {
        self.direct_cell_count
    }

    /// Direct source counts at resolutions 0 through 15.
    #[must_use]
    pub fn source_counts_by_resolution(&self) -> &[u32; MAX_H3_RESOLUTIONS] {
        &self.source_counts
    }

    /// Closed cohort counts at resolutions 0 through 15.
    #[must_use]
    pub fn closure_counts_by_resolution(&self) -> &[u32; MAX_H3_RESOLUTIONS] {
        &self.closure_counts
    }

    /// Container-independent digest of the direct source identities.
    #[must_use]
    pub fn source_digest(&self) -> RefDigestV1 {
        self.source_digest
    }

    /// Container-independent digest of the direct resolution-5 subset.
    #[must_use]
    pub fn source_r5_digest(&self) -> RefDigestV1 {
        self.source_r5_digest
    }

    /// Container-independent digest of the direct resolution-7 subset.
    #[must_use]
    pub fn source_r7_digest(&self) -> RefDigestV1 {
        self.source_r7_digest
    }

    /// Digest of the complete canonical H3 identity and hierarchy rows.
    #[must_use]
    pub fn closure_digest(&self) -> RefDigestV1 {
        self.closure_digest
    }

    /// Digest of direct-versus-derived cohort membership.
    #[must_use]
    pub fn membership_digest(&self) -> RefDigestV1 {
        self.membership_digest
    }

    /// Durable identity of the complete H3 reference cohort.
    #[must_use]
    pub fn ref_digest(&self) -> RefDigestV1 {
        self.ref_digest
    }

    /// Number of cells present directly in the source artifact.
    #[must_use]
    pub fn direct_cell_count(&self) -> usize {
        self.direct_cell_count
    }

    /// Number of strict parents added only to close the hierarchy.
    #[must_use]
    pub fn derived_ancestor_count(&self) -> usize {
        self.derived_ancestor_count
    }
}

/// One validated, immutable representative H3 reference cohort.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct H3ReferenceCohort {
    rows: Box<[H3ReferenceCellRow]>,
    receipt: H3ReferenceCohortReceipt,
}

impl H3ReferenceCohort {
    /// Canonical parent-first rows.
    #[must_use]
    pub fn rows(&self) -> &[H3ReferenceCellRow] {
        &self.rows
    }

    /// Exact build receipt.
    #[must_use]
    pub fn receipt(&self) -> &H3ReferenceCohortReceipt {
        &self.receipt
    }
}

/// Closed failures for representative H3 cohort construction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum H3ReferenceCohortError {
    /// The artifact bytes did not match the governed release pin.
    ArtifactDigestMismatch {
        expected: RefDigestV1,
        actual: RefDigestV1,
    },
    /// No source identities were supplied.
    EmptySource,
    /// Input exceeded the fixed pre-allocation ceiling.
    TooManySourceCells { actual: usize, max: usize },
    /// The artifact repeated one direct identity.
    DuplicateSourceCell { cell: H3CellId },
    /// The source cardinality drifted from the governed artifact.
    UnexpectedSourceCount { expected: usize, actual: usize },
    /// The v1 source contains only resolution-5 and resolution-7 identities.
    UnexpectedSourceResolution { cell: H3CellId, actual: u8 },
    /// One governed resolution count drifted.
    UnexpectedResolutionCount {
        resolution: u8,
        expected: u32,
        actual: u32,
    },
    /// The direct identity set did not match the governed artifact.
    SourceDigestMismatch {
        expected: RefDigestV1,
        actual: RefDigestV1,
    },
    /// Semantic H3 ancestry construction failed.
    AncestorConstruction {
        cell: H3CellId,
        requested: u8,
        source: H3CellIdError,
    },
    /// Ancestor closure exceeded its static ceiling.
    TooManyClosureRows { actual: usize, max: usize },
    /// A canonical framing allocation overflowed or exceeded its fixed ceiling.
    CanonicalByteLengthOverflow,
}

impl std::fmt::Display for H3ReferenceCohortError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "invalid H3 reference cohort: {self:?}")
    }
}

impl std::error::Error for H3ReferenceCohortError {}

/// Build the exact representative v1 H3 cohort from typed source identities.
///
/// # Errors
/// Returns [`H3ReferenceCohortError`] before publication when provenance,
/// source shape, ancestry, or canonical framing differs from the v1 contract.
pub fn build_representative_h3_cohort_v1(
    artifact_digest: RefDigestV1,
    source_cells: &[H3CellId],
) -> Result<H3ReferenceCohort, H3ReferenceCohortError> {
    validate_artifact_and_bound(artifact_digest, source_cells.len())?;
    let ordered_source = validate_and_order_source(source_cells)?;
    let source_counts = count_resolutions(&ordered_source)?;
    validate_source_counts(&source_counts)?;
    let source_digest = digest_source_cells(&ordered_source, None)?;
    let expected_source_digest = RefDigestV1::from_bytes(EXPECTED_SOURCE_DIGEST);
    if source_digest != expected_source_digest {
        return Err(H3ReferenceCohortError::SourceDigestMismatch {
            expected: expected_source_digest,
            actual: source_digest,
        });
    }

    let rows = close_hierarchy(&ordered_source)?;
    let closure_counts = count_row_resolutions(&rows)?;
    let source_r5_digest = digest_source_cells(&ordered_source, Some(5))?;
    let source_r7_digest = digest_source_cells(&ordered_source, Some(7))?;
    let closure_digest = digest_closure_rows(&rows)?;
    let membership_digest = digest_membership_rows(&rows)?;
    let ref_digest = digest_cohort(
        artifact_digest,
        source_digest,
        closure_digest,
        membership_digest,
    )?;
    let derived_ancestor_count = rows
        .len()
        .checked_sub(ordered_source.len())
        .ok_or(H3ReferenceCohortError::CanonicalByteLengthOverflow)?;
    let receipt = H3ReferenceCohortReceipt {
        artifact_digest,
        source_counts,
        closure_counts,
        source_digest,
        source_r5_digest,
        source_r7_digest,
        closure_digest,
        membership_digest,
        ref_digest,
        direct_cell_count: ordered_source.len(),
        derived_ancestor_count,
    };
    Ok(H3ReferenceCohort {
        rows: rows.into_boxed_slice(),
        receipt,
    })
}

fn validate_artifact_and_bound(
    artifact_digest: RefDigestV1,
    source_count: usize,
) -> Result<(), H3ReferenceCohortError> {
    let expected = RefDigestV1::from_bytes(EXPECTED_ARTIFACT_DIGEST);
    if artifact_digest != expected {
        return Err(H3ReferenceCohortError::ArtifactDigestMismatch {
            expected,
            actual: artifact_digest,
        });
    }
    if source_count == 0 {
        return Err(H3ReferenceCohortError::EmptySource);
    }
    if source_count > MAX_H3_REFERENCE_SOURCE_CELLS {
        return Err(H3ReferenceCohortError::TooManySourceCells {
            actual: source_count,
            max: MAX_H3_REFERENCE_SOURCE_CELLS,
        });
    }
    Ok(())
}

fn validate_and_order_source(
    source_cells: &[H3CellId],
) -> Result<Vec<H3CellId>, H3ReferenceCohortError> {
    let mut ordered = source_cells
        .iter()
        .take(MAX_H3_REFERENCE_SOURCE_CELLS)
        .copied()
        .collect::<Vec<_>>();
    ordered.sort_unstable_by_key(|cell| (cell.resolution(), *cell));
    for pair in ordered.windows(2).take(MAX_H3_REFERENCE_SOURCE_CELLS) {
        if pair[0] == pair[1] {
            return Err(H3ReferenceCohortError::DuplicateSourceCell { cell: pair[0] });
        }
    }
    if ordered.len() != EXPECTED_SOURCE_CELLS {
        return Err(H3ReferenceCohortError::UnexpectedSourceCount {
            expected: EXPECTED_SOURCE_CELLS,
            actual: ordered.len(),
        });
    }
    for cell in ordered.iter().take(MAX_H3_REFERENCE_SOURCE_CELLS) {
        let resolution = cell.resolution();
        if !matches!(resolution, 5 | 7) {
            return Err(H3ReferenceCohortError::UnexpectedSourceResolution {
                cell: *cell,
                actual: resolution,
            });
        }
    }
    Ok(ordered)
}

fn count_resolutions(
    cells: &[H3CellId],
) -> Result<[u32; MAX_H3_RESOLUTIONS], H3ReferenceCohortError> {
    let mut counts = [0_u32; MAX_H3_RESOLUTIONS];
    for cell in cells.iter().take(MAX_H3_REFERENCE_SOURCE_CELLS) {
        let index = usize::from(cell.resolution());
        counts[index] = counts[index]
            .checked_add(1)
            .ok_or(H3ReferenceCohortError::CanonicalByteLengthOverflow)?;
    }
    Ok(counts)
}

fn validate_source_counts(
    actual: &[u32; MAX_H3_RESOLUTIONS],
) -> Result<(), H3ReferenceCohortError> {
    for resolution in 0..MAX_H3_RESOLUTIONS {
        if actual[resolution] != EXPECTED_SOURCE_COUNTS[resolution] {
            return Err(H3ReferenceCohortError::UnexpectedResolutionCount {
                resolution: u8::try_from(resolution)
                    .map_err(|_| H3ReferenceCohortError::CanonicalByteLengthOverflow)?,
                expected: EXPECTED_SOURCE_COUNTS[resolution],
                actual: actual[resolution],
            });
        }
    }
    Ok(())
}

fn close_hierarchy(
    source_cells: &[H3CellId],
) -> Result<Vec<H3ReferenceCellRow>, H3ReferenceCohortError> {
    let source_set = source_cells
        .iter()
        .take(MAX_H3_REFERENCE_SOURCE_CELLS)
        .copied()
        .collect::<BTreeSet<_>>();
    let mut closure = BTreeSet::new();
    for cell in source_cells.iter().take(MAX_H3_REFERENCE_SOURCE_CELLS) {
        for requested in 0..=cell.resolution() {
            let ancestor = cell.ancestor_at(requested).map_err(|source| {
                H3ReferenceCohortError::AncestorConstruction {
                    cell: *cell,
                    requested,
                    source,
                }
            })?;
            closure.insert((ancestor.resolution(), ancestor));
        }
    }
    if closure.len() > MAX_H3_REFERENCE_CLOSURE_ROWS {
        return Err(H3ReferenceCohortError::TooManyClosureRows {
            actual: closure.len(),
            max: MAX_H3_REFERENCE_CLOSURE_ROWS,
        });
    }

    let mut rows = Vec::with_capacity(closure.len());
    for (_, cell) in closure.iter().take(MAX_H3_REFERENCE_CLOSURE_ROWS) {
        let origin = if source_set.contains(cell) {
            H3ReferenceOrigin::Direct
        } else {
            H3ReferenceOrigin::DerivedAncestor
        };
        rows.push(reference_row(*cell, origin)?);
    }
    Ok(rows)
}

fn reference_row(
    cell: H3CellId,
    origin: H3ReferenceOrigin,
) -> Result<H3ReferenceCellRow, H3ReferenceCohortError> {
    let resolution = cell.resolution();
    let immediate_parent = if resolution == 0 {
        None
    } else {
        Some(ancestor(cell, resolution - 1)?)
    };
    Ok(H3ReferenceCellRow {
        cell_id: cell,
        resolution,
        immediate_parent,
        ancestor_r4: optional_ancestor(cell, 4)?,
        ancestor_r5: optional_ancestor(cell, 5)?,
        ancestor_r6: optional_ancestor(cell, 6)?,
        ancestor_r7: optional_ancestor(cell, 7)?,
        origin,
    })
}

fn optional_ancestor(
    cell: H3CellId,
    requested: u8,
) -> Result<Option<H3CellId>, H3ReferenceCohortError> {
    if cell.resolution() < requested {
        return Ok(None);
    }
    ancestor(cell, requested).map(Some)
}

fn ancestor(cell: H3CellId, requested: u8) -> Result<H3CellId, H3ReferenceCohortError> {
    cell.ancestor_at(requested)
        .map_err(|source| H3ReferenceCohortError::AncestorConstruction {
            cell,
            requested,
            source,
        })
}

fn count_row_resolutions(
    rows: &[H3ReferenceCellRow],
) -> Result<[u32; MAX_H3_RESOLUTIONS], H3ReferenceCohortError> {
    let mut counts = [0_u32; MAX_H3_RESOLUTIONS];
    for row in rows.iter().take(MAX_H3_REFERENCE_CLOSURE_ROWS) {
        let index = usize::from(row.resolution);
        counts[index] = counts[index]
            .checked_add(1)
            .ok_or(H3ReferenceCohortError::CanonicalByteLengthOverflow)?;
    }
    Ok(counts)
}

fn digest_source_cells(
    cells: &[H3CellId],
    resolution: Option<u8>,
) -> Result<RefDigestV1, H3ReferenceCohortError> {
    let count = cells
        .iter()
        .take(MAX_H3_REFERENCE_SOURCE_CELLS)
        .filter(|cell| resolution.is_none_or(|wanted| cell.resolution() == wanted))
        .count();
    let capacity = framed_capacity(SOURCE_DOMAIN.len(), count, SOURCE_ROW_BYTES)?;
    let mut bytes = Vec::with_capacity(capacity);
    bytes.extend_from_slice(SOURCE_DOMAIN);
    push_count(&mut bytes, count)?;
    for cell in cells
        .iter()
        .take(MAX_H3_REFERENCE_SOURCE_CELLS)
        .filter(|cell| resolution.is_none_or(|wanted| cell.resolution() == wanted))
    {
        bytes.extend_from_slice(&cell.to_be_bytes());
    }
    Ok(RefDigestV1::from_bytes(sha256_of(&bytes)))
}

fn digest_closure_rows(rows: &[H3ReferenceCellRow]) -> Result<RefDigestV1, H3ReferenceCohortError> {
    let capacity = framed_capacity(ROW_DOMAIN.len(), rows.len(), CLOSURE_ROW_BYTES)?;
    let mut bytes = Vec::with_capacity(capacity);
    bytes.extend_from_slice(ROW_DOMAIN);
    push_count(&mut bytes, rows.len())?;
    for row in rows.iter().take(MAX_H3_REFERENCE_CLOSURE_ROWS) {
        bytes.extend_from_slice(&row.cell_id.to_be_bytes());
        bytes.push(row.resolution);
        push_optional_cell(&mut bytes, row.immediate_parent);
        push_optional_cell(&mut bytes, row.ancestor_r4);
        push_optional_cell(&mut bytes, row.ancestor_r5);
        push_optional_cell(&mut bytes, row.ancestor_r6);
        push_optional_cell(&mut bytes, row.ancestor_r7);
    }
    Ok(RefDigestV1::from_bytes(sha256_of(&bytes)))
}

fn digest_membership_rows(
    rows: &[H3ReferenceCellRow],
) -> Result<RefDigestV1, H3ReferenceCohortError> {
    let capacity = framed_capacity(MEMBERSHIP_DOMAIN.len(), rows.len(), MEMBERSHIP_ROW_BYTES)?;
    let mut bytes = Vec::with_capacity(capacity);
    bytes.extend_from_slice(MEMBERSHIP_DOMAIN);
    push_count(&mut bytes, rows.len())?;
    for row in rows.iter().take(MAX_H3_REFERENCE_CLOSURE_ROWS) {
        bytes.extend_from_slice(&row.cell_id.to_be_bytes());
        bytes.push(row.origin.code());
    }
    Ok(RefDigestV1::from_bytes(sha256_of(&bytes)))
}

fn digest_cohort(
    artifact_digest: RefDigestV1,
    source_digest: RefDigestV1,
    closure_digest: RefDigestV1,
    membership_digest: RefDigestV1,
) -> Result<RefDigestV1, H3ReferenceCohortError> {
    let capacity = COHORT_DOMAIN
        .len()
        .checked_add(32 * 4)
        .ok_or(H3ReferenceCohortError::CanonicalByteLengthOverflow)?;
    let mut bytes = Vec::with_capacity(capacity);
    bytes.extend_from_slice(COHORT_DOMAIN);
    bytes.extend_from_slice(artifact_digest.as_bytes());
    bytes.extend_from_slice(source_digest.as_bytes());
    bytes.extend_from_slice(closure_digest.as_bytes());
    bytes.extend_from_slice(membership_digest.as_bytes());
    Ok(RefDigestV1::from_bytes(sha256_of(&bytes)))
}

fn framed_capacity(
    domain_bytes: usize,
    row_count: usize,
    row_bytes: usize,
) -> Result<usize, H3ReferenceCohortError> {
    domain_bytes
        .checked_add(8)
        .and_then(|prefix| {
            row_count
                .checked_mul(row_bytes)
                .and_then(|rows| prefix.checked_add(rows))
        })
        .ok_or(H3ReferenceCohortError::CanonicalByteLengthOverflow)
}

fn push_count(bytes: &mut Vec<u8>, count: usize) -> Result<(), H3ReferenceCohortError> {
    let count =
        u64::try_from(count).map_err(|_| H3ReferenceCohortError::CanonicalByteLengthOverflow)?;
    bytes.extend_from_slice(&count.to_be_bytes());
    Ok(())
}

fn push_optional_cell(bytes: &mut Vec<u8>, cell: Option<H3CellId>) {
    bytes.extend_from_slice(&cell.map_or([0; 8], H3CellId::to_be_bytes));
}
