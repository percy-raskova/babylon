//! Closed `SellerOffer` storage: ordinal tags, common columns, then variant columns.
//! Only Site/Good/Unit identities are normalized; every numeric byte is literal.
use super::{columns, rows, Cursor, IdentityEntry, IdentityKind, StorageError, TypedLookup};
use babylon_material_circuit::MAX_MATERIAL_CIRCUIT_ROWS;

const COMMON_WIDTH: usize = 28;
const KINDS: [IdentityKind; 3] = [IdentityKind::Site, IdentityKind::Good, IdentityKind::Unit];

fn tail_width(tag: u8) -> Result<usize, StorageError> {
    match tag {
        1 => Ok(0),
        2 => Ok(56),
        3 => Ok(48),
        _ => Err(StorageError::Framing),
    }
}

/// Check the section's closed bounds before decompressing its body.
pub(super) fn validate_lengths(
    count: usize,
    raw_length: usize,
    body_length: usize,
) -> Result<(), StorageError> {
    if count > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(StorageError::Count);
    }
    let minimum = 4 + count * 113;
    if raw_length < minimum
        || raw_length > minimum + count * 56
        || raw_length.checked_sub(body_length) != Some(count * 84)
    {
        return Err(StorageError::Layout);
    }
    Ok(())
}

pub(super) fn encode(
    raw: &[u8],
    count: usize,
    lookup: &TypedLookup,
) -> Result<Vec<u8>, StorageError> {
    if count > MAX_MATERIAL_CIRCUIT_ROWS {
        return Err(StorageError::Count);
    }
    let mut cursor = Cursor::new(raw);
    if cursor.number(4)? != count {
        return Err(StorageError::Count);
    }
    let mut common = Vec::with_capacity(count * COMMON_WIDTH);
    let mut tags = Vec::with_capacity(count);
    let mut responsive = Vec::new();
    let mut service = Vec::new();
    let mut missing_reference = false;
    for _ in 0..count {
        for kind in KINDS {
            let bytes = cursor
                .take(32)?
                .try_into()
                .map_err(|_| StorageError::Framing)?;
            match lookup.index(IdentityEntry { kind, bytes }) {
                Ok(index) => common.extend_from_slice(&index.to_be_bytes()),
                Err(StorageError::LookupIndex) => {
                    missing_reference = true;
                    common.extend_from_slice(&0_u32.to_be_bytes());
                }
                Err(error) => return Err(error),
            }
        }
        common.extend_from_slice(cursor.take(16)?);
        let tag = cursor.tag(&[1, 2, 3])?;
        tags.push(tag);
        let tail = cursor.take(tail_width(tag)?)?;
        match tag {
            2 => responsive.extend_from_slice(tail),
            3 => service.extend_from_slice(tail),
            _ => {}
        }
    }
    cursor.done()?;
    // Validate the whole row sequence before declining normalization. Missing
    // references must never hide a later malformed tag, tail or trailing byte.
    if missing_reference {
        return Err(StorageError::LookupIndex);
    }
    let mut body = u32::try_from(count)
        .map_err(|_| StorageError::Count)?
        .to_be_bytes()
        .to_vec();
    body.extend_from_slice(&tags);
    body.extend_from_slice(&columns(&common, count, COMMON_WIDTH)?);
    body.extend_from_slice(&columns(&responsive, responsive.len() / 56, 56)?);
    body.extend_from_slice(&columns(&service, service.len() / 48, 48)?);
    validate_lengths(count, raw.len(), body.len())?;
    Ok(body)
}

pub(super) fn decode(
    body: &[u8],
    count: usize,
    raw_length: usize,
    lookup: &TypedLookup,
    prefix: usize,
) -> Result<Vec<u8>, StorageError> {
    validate_lengths(count, raw_length, body.len())?;
    let mut cursor = Cursor::new(body);
    if cursor.number(4)? != count {
        return Err(StorageError::Count);
    }
    let tags = cursor.take(count)?;
    let mut responsive_count = 0;
    let mut service_count = 0;
    for &tag in tags {
        tail_width(tag)?;
        responsive_count += usize::from(tag == 2);
        service_count += usize::from(tag == 3);
    }
    if raw_length != 4 + count * 113 + responsive_count * 56 + service_count * 48 {
        return Err(StorageError::Layout);
    }
    let common = rows(cursor.take(count * COMMON_WIDTH)?, count, COMMON_WIDTH)?;
    let responsive = rows(cursor.take(responsive_count * 56)?, responsive_count, 56)?;
    let service = rows(cursor.take(service_count * 48)?, service_count, 48)?;
    cursor.done()?;
    let mut responsive = Cursor::new(&responsive);
    let mut service = Cursor::new(&service);
    let mut raw = Vec::with_capacity(raw_length);
    raw.extend_from_slice(
        &u32::try_from(count)
            .map_err(|_| StorageError::Count)?
            .to_be_bytes(),
    );
    for (&tag, row) in tags.iter().zip(common.chunks_exact(COMMON_WIDTH)) {
        let mut row = Cursor::new(row);
        for kind in KINDS {
            let index = u32::try_from(row.number(4)?).map_err(|_| StorageError::Bounds)?;
            if index as usize >= prefix {
                return Err(StorageError::LookupIndex);
            }
            raw.extend_from_slice(&lookup.resolve(index, kind)?);
        }
        raw.extend_from_slice(row.take(16)?);
        row.done()?;
        raw.push(tag);
        match tag {
            2 => raw.extend_from_slice(responsive.take(56)?),
            3 => raw.extend_from_slice(service.take(48)?),
            _ => {}
        }
    }
    responsive.done()?;
    service.done()?;
    Ok(raw)
}
