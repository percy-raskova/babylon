//! Current lossless state17 storage. Canonical engine bytes remain the authority.
//! Storage sections have compiled schemas; no identity position maps are stored.
mod layout;
mod lookup;
mod offers;
mod schema;
#[cfg(test)]
mod tests;
use crate::storage_compression::{compress_exact, decompress_exact};
use babylon_tick::material_world::{MaterialWorldRegister, MAX_MATERIAL_WORLD_REGISTER_BYTES};
use layout::{kind, layout, Layout};
pub use lookup::{IdentityEntry, IdentityKind, TypedLookup};
use schema::{sections, Cursor, Section};
use sha2::{Digest, Sha256};
use std::{collections::BTreeMap, fmt};
const DOMAIN: &[u8] = b"babylon.state-storage.v4\0";
const MAX_BYTES: usize = MAX_MATERIAL_WORLD_REGISTER_BYTES;
// Canonical bytes retain their 1 GB limit; storage also owns compression and
// framing for at most seventy sections. This stays below PostgreSQL's bytea bound.
pub(crate) const MAX_STATE_PACKAGE_BYTES: usize = MAX_BYTES + MAX_BYTES / 256 + 16_384;
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StorageError {
    Version,
    Framing,
    Trailing,
    Bounds,
    Count,
    Layout,
    IdentityKind,
    LookupIndex,
    DuplicateIdentity,
    DigestMismatch,
    Compression,
    Canonical,
    ParentMismatch,
}
impl fmt::Display for StorageError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "state storage refused: {self:?}")
    }
}
impl std::error::Error for StorageError {}
fn digest(bytes: &[u8]) -> [u8; 32] {
    Sha256::digest(bytes).into()
}
/// Immutable, admitted opening bytes, parsed section ranges and typed identity seed.
/// Clones share this authority; period encoding never decodes the opening again.
#[derive(Clone, Debug)]
pub struct OpeningRegister {
    bytes: std::sync::Arc<Vec<u8>>,
    digest: [u8; 32],
    sections: std::sync::Arc<[Section]>,
    lookup: std::sync::Arc<TypedLookup>,
}
impl OpeningRegister {
    /// Capture an already admitted tick-zero register without decoding it again.
    /// # Errors
    /// Refuses a non-opening register, unsupported sections or typed identity bounds.
    pub fn from_opening(register: &MaterialWorldRegister) -> Result<Self, StorageError> {
        if register.completed_tick() != 0 {
            return Err(StorageError::ParentMismatch);
        }
        let bytes = register.shared_canonical_bytes();
        let parsed = sections(bytes.as_slice())?;
        let mut lookup = TypedLookup::default();
        for section in &parsed {
            if let Some(shape) = layout(section.id) {
                normalize(section.raw(bytes.as_slice()), shape, &mut lookup, true)?;
            }
        }
        Ok(Self {
            digest: register.digest(),
            bytes,
            sections: parsed.into(),
            lookup: std::sync::Arc::new(lookup),
        })
    }
    /// Admit canonical opening bytes once for standalone codec tooling.
    /// # Errors
    /// Refuses invalid canonical input or a non-opening register.
    pub fn from_canonical(bytes: &[u8]) -> Result<Self, StorageError> {
        let register = MaterialWorldRegister::decode(bytes).map_err(|_| StorageError::Canonical)?;
        Self::from_opening(&register)
    }
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8] {
        self.bytes.as_slice()
    }
    #[must_use]
    pub const fn digest(&self) -> [u8; 32] {
        self.digest
    }
    #[must_use]
    pub fn lookup(&self) -> &TypedLookup {
        &self.lookup
    }
    /// Borrow an authenticated original section and its checked row count.
    #[must_use]
    pub fn section(&self, id: u16) -> Option<(&[u8], Option<usize>)> {
        self.sections
            .iter()
            .find(|section| section.id == id)
            .map(|section| (section.raw(self.canonical_bytes()), section.count))
    }
    /// Borrow one identity from a closed recipe source using the current layout owner.
    /// No arbitrary byte offset, account selector or variable row is accepted.
    pub(crate) fn recipe_row_identity(
        &self,
        section: u16,
        row: usize,
        field: usize,
        expected: IdentityKind,
    ) -> Result<[u8; 32], StorageError> {
        if ![2, 27, 32, 33, 35, 38, 63].contains(&section) {
            return Err(StorageError::Layout);
        }
        let shape = layout::layout(section).ok_or(StorageError::Layout)?;
        let (raw, count) = self.section(section).ok_or(StorageError::Layout)?;
        let count = count.ok_or(StorageError::Layout)?;
        if row >= count || count > shape.maximum {
            return Err(StorageError::LookupIndex);
        }
        let expected_length = count
            .checked_mul(shape.width)
            .and_then(|n| n.checked_add(4))
            .ok_or(StorageError::Bounds)?;
        if raw.len() != expected_length {
            return Err(StorageError::Layout);
        }
        let field = shape.fields.get(field).ok_or(StorageError::Layout)?;
        if field
            .offset
            .checked_add(32)
            .is_none_or(|end| end > shape.width)
        {
            return Err(StorageError::Layout);
        }
        if !matches!(field.kind, layout::FieldKind::Identity(kind) if kind == expected) {
            return Err(StorageError::IdentityKind);
        }
        let start = row
            .checked_mul(shape.width)
            .and_then(|n| n.checked_add(4))
            .and_then(|n| n.checked_add(field.offset))
            .ok_or(StorageError::Bounds)?;
        let end = start.checked_add(32).ok_or(StorageError::Bounds)?;
        raw.get(start..end)
            .ok_or(StorageError::Layout)?
            .try_into()
            .map_err(|_| StorageError::Layout)
    }
}

/// Packed lookup delta and storage package belong to the same marker-last commit.
#[derive(Clone, Debug)]
pub struct EncodedState {
    pub package: Vec<u8>,
    pub lookup_delta: Vec<IdentityEntry>,
}
impl EncodedState {
    /// Bind this staged state package to the complete period lookup history.
    /// Called after receipt-only IDs are staged; canonical engine bytes stay unchanged.
    /// # Errors
    /// Refuses a malformed or unsupported staged package header.
    pub fn bind_lookup_chain(&mut self, chain: [u8; 32]) -> Result<(), StorageError> {
        if self.package.get(..DOMAIN.len()) != Some(DOMAIN) {
            return Err(StorageError::Version);
        }
        let offset = DOMAIN.len() + 64;
        self.package
            .get_mut(offset..offset + 32)
            .ok_or(StorageError::Framing)?
            .copy_from_slice(&chain);
        Ok(())
    }
}
struct Normalized {
    bytes: Vec<u8>,
    keys: Vec<u32>,
}
fn normalize_with(
    raw: &[u8],
    shape: Layout,
    mut reference: impl FnMut(IdentityEntry) -> Result<u32, StorageError>,
) -> Result<Normalized, StorageError> {
    let body = raw.get(4..).ok_or(StorageError::Framing)?;
    if !body.len().is_multiple_of(shape.width) {
        return Err(StorageError::Layout);
    }
    let mut result = Normalized {
        bytes: Vec::new(),
        keys: Vec::new(),
    };
    for row in body.chunks_exact(shape.width) {
        let mut last = 0;
        for field in shape.fields {
            result
                .bytes
                .extend_from_slice(row.get(last..field.offset).ok_or(StorageError::Layout)?);
            let bytes = row
                .get(field.offset..field.offset + 32)
                .ok_or(StorageError::Layout)?
                .try_into()
                .map_err(|_| StorageError::Layout)?;
            let entry = IdentityEntry {
                kind: kind(*field, row)?,
                bytes,
            };
            let index = reference(entry)?;
            result.bytes.extend_from_slice(&index.to_be_bytes());
            result.keys.push(index);
            last = field.offset + 32;
        }
        result
            .bytes
            .extend_from_slice(row.get(last..).ok_or(StorageError::Layout)?);
    }
    Ok(result)
}
fn normalize(
    raw: &[u8],
    shape: Layout,
    lookup: &mut TypedLookup,
    append: bool,
) -> Result<Normalized, StorageError> {
    normalize_with(raw, shape, |entry| {
        if append {
            lookup.intern(entry.kind, entry.bytes)
        } else {
            lookup.index(entry)
        }
    })
}
fn normalize_existing_bounded(
    raw: &[u8],
    shape: Layout,
    lookup: &TypedLookup,
    prefix: usize,
) -> Result<Normalized, StorageError> {
    normalize_with(raw, shape, |entry| {
        let index = lookup.index(entry)?;
        if index as usize >= prefix {
            return Err(StorageError::LookupIndex);
        }
        Ok(index)
    })
}
fn normalized_width(shape: Layout) -> Result<usize, StorageError> {
    shape
        .width
        .checked_sub(
            shape
                .fields
                .len()
                .checked_mul(28)
                .ok_or(StorageError::Bounds)?,
        )
        .ok_or(StorageError::Layout)
}
fn columns(bytes: &[u8], count: usize, width: usize) -> Result<Vec<u8>, StorageError> {
    if bytes.len() != count.checked_mul(width).ok_or(StorageError::Bounds)? {
        return Err(StorageError::Layout);
    }
    let mut result = vec![0; bytes.len()];
    for row in 0..count {
        for column in 0..width {
            result[column * count + row] = bytes[row * width + column];
        }
    }
    Ok(result)
}
// Generate target-length columns directly: added bytes XOR zero; omitted
// opening tail bytes cannot affect the target's authenticated extent.
fn opening_xor_columns(
    current: &[u8],
    opening: &[u8],
    count: usize,
    width: usize,
) -> Result<Vec<u8>, StorageError> {
    if width == 0
        || current.len() != count.checked_mul(width).ok_or(StorageError::Bounds)?
        || !opening.len().is_multiple_of(width)
    {
        return Err(StorageError::Layout);
    }
    let mut result = vec![0; current.len()];
    for row in 0..count {
        for column in 0..width {
            let index = row * width + column;
            result[column * count + row] =
                current[index] ^ opening.get(index).copied().unwrap_or(0);
        }
    }
    Ok(result)
}
fn validate_opening_section(
    section: &Section,
    raw: &[u8],
    id: u16,
    shape: Layout,
) -> Result<(), StorageError> {
    if section.id != id {
        return Err(StorageError::Layout);
    }
    let count = section.count.ok_or(StorageError::Count)?;
    if count == 0 || count > shape.maximum {
        return Err(StorageError::Count);
    }
    let length = count
        .checked_mul(shape.width)
        .and_then(|length| length.checked_add(4))
        .ok_or(StorageError::Bounds)?;
    if raw.len() != length {
        return Err(StorageError::Layout);
    }
    let declared = u32::from_be_bytes(raw[..4].try_into().map_err(|_| StorageError::Framing)?);
    if usize::try_from(declared).map_err(|_| StorageError::Bounds)? != count {
        return Err(StorageError::Layout);
    }
    Ok(())
}
fn rows(bytes: &[u8], count: usize, width: usize) -> Result<Vec<u8>, StorageError> {
    if bytes.len() != count.checked_mul(width).ok_or(StorageError::Bounds)? {
        return Err(StorageError::Layout);
    }
    let mut result = vec![0; bytes.len()];
    for row in 0..count {
        for column in 0..width {
            result[row * width + column] = bytes[column * count + row];
        }
    }
    Ok(result)
}
fn expand(
    bytes: &[u8],
    count: usize,
    shape: Layout,
    lookup: &TypedLookup,
    prefix: usize,
) -> Result<Vec<u8>, StorageError> {
    let width = normalized_width(shape)?;
    if bytes.len() != count.checked_mul(width).ok_or(StorageError::Bounds)? {
        return Err(StorageError::Layout);
    }
    let length = 4_usize
        .checked_add(count.checked_mul(shape.width).ok_or(StorageError::Bounds)?)
        .ok_or(StorageError::Bounds)?;
    if length > MAX_BYTES {
        return Err(StorageError::Bounds);
    }
    let mut result = Vec::with_capacity(length);
    result.extend_from_slice(
        &u32::try_from(count)
            .map_err(|_| StorageError::Count)?
            .to_be_bytes(),
    );
    for row in bytes.chunks_exact(width) {
        let mut restored = Vec::with_capacity(shape.width);
        let mut cursor = 0;
        for field in shape.fields {
            let literal = field
                .offset
                .checked_sub(restored.len())
                .ok_or(StorageError::Layout)?;
            restored.extend_from_slice(
                row.get(cursor..cursor + literal)
                    .ok_or(StorageError::Framing)?,
            );
            cursor += literal;
            let index = u32::from_be_bytes(
                row.get(cursor..cursor + 4)
                    .ok_or(StorageError::Framing)?
                    .try_into()
                    .map_err(|_| StorageError::Framing)?,
            );
            cursor += 4;
            if index as usize >= prefix {
                return Err(StorageError::LookupIndex);
            }
            let expected = kind(*field, &restored)?;
            restored.extend_from_slice(&lookup.resolve(index, expected)?);
        }
        restored.extend_from_slice(row.get(cursor..).ok_or(StorageError::Framing)?);
        if restored.len() != shape.width {
            return Err(StorageError::Layout);
        }
        result.extend_from_slice(&restored);
    }
    Ok(result)
}
struct Block {
    mode: u8,
    body_length: usize,
    body_digest: [u8; 32],
    encoded: Vec<u8>,
}
fn compressed(mode: u8, body: Vec<u8>) -> Result<Block, StorageError> {
    let encoded = compress_exact(&body, MAX_BYTES).map_err(|_| StorageError::Compression)?;
    let body_length = body.len();
    let body_digest = digest(&body);
    drop(body);
    Ok(Block {
        mode,
        body_length,
        body_digest,
        encoded,
    })
}
fn block(
    current: &[u8],
    section: &Section,
    base: Option<(&Section, &[u8])>,
    lookup: &mut TypedLookup,
) -> Result<Block, StorageError> {
    let raw = section.raw(current);
    if base.is_some_and(|(_, previous)| previous == raw) {
        return Ok(Block {
            mode: 0,
            body_length: 0,
            body_digest: digest(&[]),
            encoded: Vec::new(),
        });
    }
    if section.id == 34 {
        let count = section.count.ok_or(StorageError::Count)?;
        let literal = compressed(1, raw.to_vec())?;
        // Reuse the exact existing prefix. A smaller frame cannot hide added
        // lookup storage or shift references used by subsequent sections.
        let body = match offers::encode(raw, count, lookup) {
            Ok(body) => body,
            Err(StorageError::LookupIndex) => return Ok(literal),
            Err(error) => return Err(error),
        };
        let candidate = compressed(5, body)?;
        if candidate.encoded.len() < literal.encoded.len() {
            return Ok(candidate);
        }
        return Ok(literal);
    }
    let Some(shape) = layout(section.id) else {
        return compressed(1, raw.to_vec());
    };
    let count = section.count.ok_or(StorageError::Count)?;
    let width = normalized_width(shape)?;
    let Normalized {
        bytes: normalized,
        keys,
    } = normalize(raw, shape, lookup, true)?;
    let mut selected = compressed(2, columns(&normalized, count, width)?)?;
    let Some((old, bytes)) = base else {
        return Ok(selected);
    };
    if count == 0 || old.count == Some(0) {
        return Ok(selected);
    }
    validate_opening_section(old, bytes, section.id, shape)?;
    let Normalized {
        bytes: previous,
        keys: previous_keys,
    } = normalize(bytes, shape, lookup, false)?;
    let mode = if old.count == section.count && previous_keys == keys {
        3
    } else {
        4
    };
    drop(previous_keys);
    drop(keys);
    let candidate = compressed(
        mode,
        opening_xor_columns(&normalized, &previous, count, width)?,
    )?;
    if candidate.encoded.len() < selected.encoded.len() {
        selected = candidate;
    }
    Ok(selected)
}
fn append_block(
    package: &mut Vec<u8>,
    current: &[u8],
    section: &Section,
    block: &Block,
) -> Result<(), StorageError> {
    package.extend_from_slice(&section.id.to_be_bytes());
    package.push(block.mode);
    package.extend_from_slice(
        &section
            .count
            .map(u32::try_from)
            .transpose()
            .map_err(|_| StorageError::Count)?
            .unwrap_or(u32::MAX)
            .to_be_bytes(),
    );
    package.extend_from_slice(
        &u64::try_from(section.end - section.start)
            .map_err(|_| StorageError::Bounds)?
            .to_be_bytes(),
    );
    package.extend_from_slice(&digest(section.raw(current)));
    package.extend_from_slice(
        &u64::try_from(block.body_length)
            .map_err(|_| StorageError::Bounds)?
            .to_be_bytes(),
    );
    package.extend_from_slice(&block.body_digest);
    package.extend_from_slice(
        &u64::try_from(block.encoded.len())
            .map_err(|_| StorageError::Bounds)?
            .to_be_bytes(),
    );
    package.extend_from_slice(&block.encoded);
    if package.len() > MAX_STATE_PACKAGE_BYTES {
        return Err(StorageError::Bounds);
    }
    Ok(())
}
/// Encode using cached authenticated opening sections and identity seed.
/// # Errors
/// Refuses invalid current state, a different seed or any codec bound.
pub fn encode_register_with_opening(
    opening: &OpeningRegister,
    current: &MaterialWorldRegister,
    lookup: &TypedLookup,
) -> Result<EncodedState, StorageError> {
    let current_bytes = current.canonical_bytes();
    let base = opening.canonical_bytes();
    let old = &opening.sections;
    if lookup.entries().get(..opening.lookup.entries().len()) != Some(opening.lookup.entries()) {
        return Err(StorageError::ParentMismatch);
    }
    let current_sections = sections(current_bytes)?;
    let old_map = old.iter().map(|s| (s.id, s)).collect::<BTreeMap<_, _>>();
    let mut updated = lookup.clone();
    let mut blocks = Vec::with_capacity(current_sections.len());
    for section in &current_sections {
        let previous = old_map.get(&section.id).map(|s| (*s, s.raw(base)));
        blocks.push(block(current_bytes, section, previous, &mut updated)?);
    }
    let mut package = DOMAIN.to_vec();
    package.extend_from_slice(&opening.digest);
    package.extend_from_slice(&current.digest());
    package.extend_from_slice(&[0; 32]);
    package.extend_from_slice(
        &u64::try_from(current_bytes.len())
            .map_err(|_| StorageError::Bounds)?
            .to_be_bytes(),
    );
    package.extend_from_slice(
        &u32::try_from(updated.entries().len())
            .map_err(|_| StorageError::Bounds)?
            .to_be_bytes(),
    );
    package.extend_from_slice(&updated.prefix_digest(updated.entries().len())?);
    package.extend_from_slice(
        &u16::try_from(current_sections.len())
            .map_err(|_| StorageError::Count)?
            .to_be_bytes(),
    );
    for (section, block) in current_sections.iter().zip(blocks) {
        append_block(&mut package, current_bytes, section, &block)?;
    }
    Ok(EncodedState {
        package,
        lookup_delta: updated.entries()[lookup.entries().len()..].to_vec(),
    })
}
struct StoredSection {
    id: u16,
    mode: u8,
    count: Option<usize>,
    raw_length: usize,
    raw_digest: [u8; 32],
    body_length: usize,
    body_digest: [u8; 32],
    encoded: Vec<u8>,
}
fn array32(c: &mut Cursor<'_>) -> Result<[u8; 32], StorageError> {
    c.take(32)?.try_into().map_err(|_| StorageError::Framing)
}
fn stored_section(c: &mut Cursor<'_>) -> Result<StoredSection, StorageError> {
    let id = u16::try_from(c.number(2)?).map_err(|_| StorageError::Bounds)?;
    if id > 72 {
        return Err(StorageError::Layout);
    }
    let mode = c.tag(&[0, 1, 2, 3, 4, 5])?;
    let count = c.number(4)?;
    let count = if count == usize::try_from(u32::MAX).map_err(|_| StorageError::Bounds)? {
        None
    } else {
        Some(count)
    };
    let raw_length = c.number(8)?;
    if raw_length > MAX_BYTES {
        return Err(StorageError::Bounds);
    }
    let raw_digest = array32(c)?;
    let body_length = c.number(8)?;
    if body_length > MAX_BYTES {
        return Err(StorageError::Bounds);
    }
    let body_digest = array32(c)?;
    let size = c.number(8)?;
    if size > MAX_STATE_PACKAGE_BYTES {
        return Err(StorageError::Bounds);
    }
    let encoded = c.take(size)?.to_vec();
    Ok(StoredSection {
        id,
        mode,
        count,
        raw_length,
        raw_digest,
        body_length,
        body_digest,
        encoded,
    })
}
fn validate_body_length(stored: &StoredSection) -> Result<(), StorageError> {
    if stored.mode == 5 {
        if stored.id != 34 {
            return Err(StorageError::Layout);
        }
        return offers::validate_lengths(
            stored.count.ok_or(StorageError::Count)?,
            stored.raw_length,
            stored.body_length,
        );
    }
    if stored.mode == 1 {
        if stored.body_length != stored.raw_length {
            return Err(StorageError::Framing);
        }
    } else {
        let shape = layout(stored.id).ok_or(StorageError::Layout)?;
        let count = stored.count.ok_or(StorageError::Count)?;
        if count > shape.maximum {
            return Err(StorageError::Count);
        }
        let raw = 4_usize
            .checked_add(count.checked_mul(shape.width).ok_or(StorageError::Bounds)?)
            .ok_or(StorageError::Bounds)?;
        let normalized = count
            .checked_mul(normalized_width(shape)?)
            .ok_or(StorageError::Bounds)?;
        if stored.raw_length != raw || stored.body_length != normalized {
            return Err(StorageError::Layout);
        }
    }
    Ok(())
}
fn restore_section(
    stored: &StoredSection,
    base: Option<(&Section, &[u8])>,
    lookup: &TypedLookup,
    prefix: usize,
) -> Result<Vec<u8>, StorageError> {
    if stored.mode == 0 {
        if stored.body_length != 0
            || !stored.encoded.is_empty()
            || stored.body_digest != digest(&[])
        {
            return Err(StorageError::Framing);
        }
        let (old, raw) = base.ok_or(StorageError::ParentMismatch)?;
        if old.count != stored.count {
            return Err(StorageError::Count);
        }
        return Ok(raw.to_vec());
    }
    validate_body_length(stored)?;
    let body = decompress_exact(
        &stored.encoded,
        stored.body_length,
        stored.body_digest,
        MAX_BYTES,
    )
    .map_err(|_| StorageError::Compression)?;
    if stored.mode == 1 {
        if stored.body_length != stored.raw_length {
            return Err(StorageError::Framing);
        }
        return Ok(body);
    }
    if stored.mode == 5 {
        return offers::decode(
            &body,
            stored.count.ok_or(StorageError::Count)?,
            stored.raw_length,
            lookup,
            prefix,
        );
    }
    let shape = layout(stored.id).ok_or(StorageError::Layout)?;
    let count = stored.count.ok_or(StorageError::Count)?;
    if count > shape.maximum
        || stored.raw_length
            != 4_usize
                .checked_add(count.checked_mul(shape.width).ok_or(StorageError::Bounds)?)
                .ok_or(StorageError::Bounds)?
    {
        return Err(StorageError::Count);
    }
    let width = normalized_width(shape)?;
    let mut normalized = rows(&body, count, width)?;
    drop(body);
    if stored.mode == 4 {
        let (old, raw) = base.ok_or(StorageError::ParentMismatch)?;
        if count == 0 {
            return Err(StorageError::Count);
        }
        validate_opening_section(old, raw, stored.id, shape)?;
        let Normalized {
            bytes: previous,
            keys,
        } = normalize_existing_bounded(raw, shape, lookup, prefix)?;
        drop(keys);
        for (index, byte) in normalized.iter_mut().enumerate() {
            *byte ^= previous.get(index).copied().unwrap_or(0);
        }
        drop(previous);
        return expand(&normalized, count, shape, lookup, prefix);
    }
    if stored.mode == 3 {
        let (old, raw) = base.ok_or(StorageError::ParentMismatch)?;
        if old.count != stored.count {
            return Err(StorageError::Count);
        }
        let previous = normalize_existing_bounded(raw, shape, lookup, prefix)?;
        for (byte, old) in normalized.iter_mut().zip(previous.bytes) {
            *byte ^= old;
        }
        // The reconstructed ID references must remain the exact stable row keys.
        let restored = expand(&normalized, count, shape, lookup, prefix)?;
        if normalize_existing_bounded(&restored, shape, lookup, prefix)?.keys != previous.keys {
            return Err(StorageError::Layout);
        }
        return Ok(restored);
    }
    expand(&normalized, count, shape, lookup, prefix)
}
// Retain the typed register produced by complete canonical admission.
// Callers cannot replace it with an unchecked framing/header read.
pub(crate) fn decode_admitted(
    opening: &OpeningRegister,
    package: &[u8],
    lookup: &TypedLookup,
    expected_lookup_chain: [u8; 32],
) -> Result<(Vec<u8>, MaterialWorldRegister), StorageError> {
    let result = restore_register(opening, package, lookup, expected_lookup_chain)?;
    let admitted = MaterialWorldRegister::decode(&result).map_err(|_| StorageError::Canonical)?;
    Ok((result, admitted))
}

pub(crate) fn decode_against_admitted(
    opening: &OpeningRegister,
    package: &[u8],
    lookup: &TypedLookup,
    expected_lookup_chain: [u8; 32],
    witness: &MaterialWorldRegister,
) -> Result<Vec<u8>, StorageError> {
    let result = restore_register(opening, package, lookup, expected_lookup_chain)?;
    if result != witness.canonical_bytes() {
        return Err(StorageError::Canonical);
    }
    Ok(result)
}

fn restore_register(
    opening: &OpeningRegister,
    package: &[u8],
    lookup: &TypedLookup,
    expected_lookup_chain: [u8; 32],
) -> Result<Vec<u8>, StorageError> {
    let base = opening.canonical_bytes();
    if package.len() > MAX_STATE_PACKAGE_BYTES {
        return Err(StorageError::Bounds);
    }
    let old = &opening.sections;
    let old_map = old.iter().map(|s| (s.id, s)).collect::<BTreeMap<_, _>>();
    let mut cursor = Cursor::new(package);
    cursor.expect(DOMAIN)?;
    if array32(&mut cursor)? != opening.digest {
        return Err(StorageError::ParentMismatch);
    }
    let expected = array32(&mut cursor)?;
    if array32(&mut cursor)? != expected_lookup_chain {
        return Err(StorageError::DigestMismatch);
    }
    let length = cursor.number(8)?;
    if length > MAX_BYTES {
        return Err(StorageError::Bounds);
    }
    let lookup_count = cursor.number(4)?;
    if lookup_count < opening.lookup.entries().len() {
        return Err(StorageError::ParentMismatch);
    }
    if array32(&mut cursor)? != lookup.prefix_digest(lookup_count)? {
        return Err(StorageError::DigestMismatch);
    }
    let count = cursor.number(2)?;
    if count > 73 {
        return Err(StorageError::Count);
    }
    let mut result = Vec::new();
    let mut descriptors = Vec::new();
    for _ in 0..count {
        let stored = stored_section(&mut cursor)?;
        if descriptors.iter().any(|(id, _, _)| *id == stored.id) {
            return Err(StorageError::Layout);
        }
        let previous = old_map.get(&stored.id).map(|s| (*s, s.raw(base)));
        let restored = restore_section(&stored, previous, lookup, lookup_count)?;
        if restored.len() != stored.raw_length || digest(&restored) != stored.raw_digest {
            return Err(StorageError::DigestMismatch);
        }
        if result
            .len()
            .checked_add(restored.len())
            .ok_or(StorageError::Bounds)?
            > length
        {
            return Err(StorageError::Bounds);
        }
        descriptors.push((stored.id, stored.count, restored.len()));
        result.extend_from_slice(&restored);
    }
    cursor.done()?;
    if result.len() != length || digest(&result) != expected {
        return Err(StorageError::DigestMismatch);
    }
    let actual = sections(&result)?;
    if actual
        .iter()
        .map(|s| (s.id, s.count, s.end - s.start))
        .collect::<Vec<_>>()
        != descriptors
    {
        return Err(StorageError::Layout);
    }
    Ok(result)
}
/// One packed table/chunk, not one SQL row per identity. Tags are closed/versioned
/// by the storage codec; preserve insertion order when appending.
/// # Errors
/// Refuses an entry count or packed length beyond the current byte bound.
pub fn encode_lookup(entries: &[IdentityEntry]) -> Result<Vec<u8>, StorageError> {
    let mut result = u32::try_from(entries.len())
        .map_err(|_| StorageError::Bounds)?
        .to_be_bytes()
        .to_vec();
    for entry in entries {
        result.push(entry.kind as u8);
        result.extend_from_slice(&entry.bytes);
    }
    if result.len() > MAX_BYTES {
        return Err(StorageError::Bounds);
    }
    Ok(result)
}
