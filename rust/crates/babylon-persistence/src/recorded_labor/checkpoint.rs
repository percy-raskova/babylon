//! Versioned, disposable cache of derived labor. The authenticated material register owns all
//! physical quantities and identities. Payload positions follow their canonical sorted order.
use super::{LaborBasis, LaborNode, RecordedLaborError, Result};
use babylon_kernel::content_digest;
use babylon_recorded_labor::{Book, Position};
use sha2::Sha256;
use std::collections::BTreeMap;

const MAGIC: [u8; 8] = *b"BYLLABOR";
const VERSION: u16 = 1;
const MAX_ROW_BYTES: usize = 17;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(super) struct Source {
    pub foundation: [u8; 32],
    pub catalog: [u8; 32],
    pub register: [u8; 32],
    pub completed: u64,
}

/// Canonical cache bytes and their SHA-256. Persist the digest with its campaign and committed
/// boundary marker so a reader can validate it independently of the cache payload.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecordedLaborCheckpoint {
    pub bytes: Vec<u8>,
    pub sha256: [u8; 32],
}

fn physical_digest<'a>(rows: impl Iterator<Item = (&'a LaborNode, u64)>) -> Result<[u8; 32]> {
    use sha2::Digest;
    let mut hash = Sha256::new();
    hash.update(b"babylon.recorded-labor.physical-positions.v1\0");
    for (node, quantity) in rows {
        match node {
            LaborNode::SiteStock { site, good, unit } => {
                hash.update([1]);
                hash.update(site.0);
                hash.update(good.0);
                hash.update(unit.0);
            }
            LaborNode::HouseholdStock {
                household,
                good,
                unit,
            } => {
                hash.update([2]);
                hash.update(household.0);
                hash.update(good.0);
                hash.update(unit.0);
            }
            LaborNode::Freight { lot } => {
                hash.update([3]);
                hash.update(lot.0);
            }
            LaborNode::Equipment { cohort } => {
                hash.update([4]);
                hash.update(cohort.0);
            }
            LaborNode::Installation { installation } => {
                hash.update([5]);
                hash.update(installation.0);
            }
            LaborNode::Maintenance { process } => {
                hash.update([6]);
                hash.update(process.0);
            }
            LaborNode::Process { .. }
            | LaborNode::Work { .. }
            | LaborNode::HouseholdWork { .. }
            | LaborNode::Sink { .. } => return Err(RecordedLaborError::CheckpointFormat),
        }
        hash.update(quantity.to_be_bytes());
    }
    Ok(hash.finalize().into())
}

pub(super) fn encode(source: Source, book: &Book) -> Result<RecordedLaborCheckpoint> {
    let count = u32::try_from(book.len()).map_err(|_| RecordedLaborError::Arithmetic)?;
    let mut bytes = Vec::new();
    bytes.extend(MAGIC);
    bytes.extend(VERSION.to_be_bytes());
    bytes.extend(source.foundation);
    bytes.extend(source.catalog);
    bytes.extend(source.register);
    bytes.extend(source.completed.to_be_bytes());
    bytes.extend(count.to_be_bytes());
    bytes.extend(physical_digest(
        book.iter().map(|(node, p)| (node, p.quantity)),
    )?);
    let mut total = 0_u128;
    for p in book.values() {
        let amount = p.basis.recorded_micro_hours;
        total = total
            .checked_add(amount)
            .ok_or(RecordedLaborError::Arithmetic)?;
        bytes.push(u8::from(p.basis.unknown_opening) | (u8::from(amount != 0) << 1));
        if amount != 0 {
            bytes.extend(amount.to_be_bytes());
        }
    }
    bytes.extend(total.to_be_bytes());
    Ok(RecordedLaborCheckpoint {
        sha256: content_digest::sha256_of(&bytes),
        bytes,
    })
}

fn take<const N: usize>(bytes: &mut &[u8]) -> Result<[u8; N]> {
    let (value, rest) = bytes
        .split_first_chunk::<N>()
        .ok_or(RecordedLaborError::CheckpointFormat)?;
    *bytes = rest;
    Ok(*value)
}

fn next_basis(bytes: &mut &[u8], completed: u64) -> Result<LaborBasis> {
    let [tag] = take(bytes)?;
    let amount = match tag {
        0 | 1 => 0,
        2 | 3 => {
            let amount = u128::from_be_bytes(take(bytes)?);
            if amount == 0 {
                return Err(RecordedLaborError::CheckpointFormat);
            }
            amount
        }
        _ => return Err(RecordedLaborError::CheckpointFormat),
    };
    if completed == 0 && tag != 1 {
        return Err(RecordedLaborError::CheckpointFormat);
    }
    Ok(LaborBasis {
        recorded_micro_hours: amount,
        unknown_opening: tag & 1 == 1,
    })
}

pub(super) fn decode(
    source: Source,
    quantities: BTreeMap<LaborNode, u64>,
    bytes: &[u8],
    expected_sha256: [u8; 32],
) -> Result<Book> {
    let mut data = bytes;
    if take(&mut data)? != MAGIC {
        return Err(RecordedLaborError::CheckpointFormat);
    }
    if u16::from_be_bytes(take(&mut data)?) != VERSION {
        return Err(RecordedLaborError::CheckpointVersion);
    }
    let binding = Source {
        foundation: take(&mut data)?,
        catalog: take(&mut data)?,
        register: take(&mut data)?,
        completed: u64::from_be_bytes(take(&mut data)?),
    };
    if binding != source {
        return Err(RecordedLaborError::CheckpointBinding);
    }
    let count = usize::try_from(u32::from_be_bytes(take(&mut data)?))
        .map_err(|_| RecordedLaborError::CheckpointFormat)?;
    let physical: [u8; 32] = take(&mut data)?;
    // Both the count and the variable payload must fit the real positive material positions.
    if count != quantities.len()
        || data.len()
            < count
                .checked_add(16)
                .ok_or(RecordedLaborError::Arithmetic)?
        || data.len()
            > count
                .checked_mul(MAX_ROW_BYTES)
                .and_then(|n| n.checked_add(16))
                .ok_or(RecordedLaborError::Arithmetic)?
    {
        return Err(RecordedLaborError::CheckpointFormat);
    }
    if content_digest::sha256_of(bytes) != expected_sha256 {
        return Err(RecordedLaborError::CheckpointDigest);
    }
    if physical_digest(quantities.iter().map(|(n, q)| (n, *q)))? != physical {
        return Err(RecordedLaborError::CheckpointBinding);
    }
    let mut book = Book::new();
    let mut total = 0_u128;
    for (node, quantity) in quantities {
        let basis = next_basis(&mut data, source.completed)?;
        total = total
            .checked_add(basis.recorded_micro_hours)
            .ok_or(RecordedLaborError::Arithmetic)?;
        book.insert(node, Position { quantity, basis });
    }
    if total != u128::from_be_bytes(take(&mut data)?) || !data.is_empty() {
        return Err(RecordedLaborError::CheckpointFormat);
    }
    Ok(book)
}
