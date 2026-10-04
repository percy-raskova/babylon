//! Exact positive cash amounts shared only within one receipt family.
use super::{buffer, Error, Result};

pub(super) const ROW_WIDTH: usize = 18;
const CONTEXT_WIDTH: usize = 14;
const NORMALIZED_WIDTH: usize = 30;

#[derive(Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
struct PositiveAmount(i128);

impl PositiveAmount {
    fn from_bytes(bytes: [u8; 16]) -> Result<Self> {
        let amount = i128::from_be_bytes(bytes);
        if amount <= 0 {
            return Err(Error::Canonical);
        }
        Ok(Self(amount))
    }
}

pub(super) struct PackedAmounts {
    pub dictionary_count: u32,
    pub columns: Vec<u8>,
}

/// Only a strictly smaller normalized representation is an eligible mode.
pub(super) fn decoded_length(count: usize, unique: u32) -> Result<usize> {
    let unique = usize::try_from(unique).map_err(|_| Error::Count)?;
    if count == 0 || unique == 0 || unique > count {
        return Err(Error::Count);
    }
    let length = count
        .checked_mul(ROW_WIDTH)
        .and_then(|n| unique.checked_mul(16).and_then(|d| n.checked_add(d)))
        .ok_or(Error::Arithmetic)?;
    if length
        >= count
            .checked_mul(NORMALIZED_WIDTH)
            .ok_or(Error::Arithmetic)?
    {
        return Err(Error::Count);
    }
    Ok(length)
}

fn context_amount(row: &[u8]) -> Result<([u8; CONTEXT_WIDTH], PositiveAmount)> {
    if row.len() != NORMALIZED_WIDTH || !matches!(row[0], 1..=10) {
        return Err(Error::Canonical);
    }
    let mut context = [0; CONTEXT_WIDTH];
    let offset = if row[0] == 7 {
        context.copy_from_slice(&row[..CONTEXT_WIDTH]);
        14
    } else {
        if row[28..] != [0; 2] {
            return Err(Error::Padding);
        }
        context[..12].copy_from_slice(&row[..12]);
        12
    };
    let amount = PositiveAmount::from_bytes(
        row[offset..offset + 16]
            .try_into()
            .map_err(|_| Error::Width)?,
    )?;
    Ok((context, amount))
}

pub(super) fn pack(rows: &[u8], count: usize) -> Result<Option<PackedAmounts>> {
    if rows.len()
        != count
            .checked_mul(NORMALIZED_WIDTH)
            .ok_or(Error::Arithmetic)?
    {
        return Err(Error::Width);
    }
    if count == 0 {
        return Ok(None);
    }
    let mut values = Vec::new();
    values
        .try_reserve_exact(count)
        .map_err(|_| Error::Allocation)?;
    for row in rows.chunks_exact(NORMALIZED_WIDTH) {
        values.push(context_amount(row)?.1);
    }
    values.sort_unstable();
    values.dedup();
    let dictionary_count = u32::try_from(values.len()).map_err(|_| Error::Count)?;
    let length = match decoded_length(count, dictionary_count) {
        Ok(length) => length,
        Err(Error::Count) => return Ok(None),
        Err(error) => return Err(error),
    };
    let mut columns = buffer(length)?;
    columns.resize(length, 0);
    let dictionary_start = count * CONTEXT_WIDTH;
    let reference_start = dictionary_start + values.len() * 16;
    for (index, value) in values.iter().enumerate() {
        for (column, byte) in value.0.to_be_bytes().into_iter().enumerate() {
            columns[dictionary_start + column * values.len() + index] = byte;
        }
    }
    for (index, row) in rows.chunks_exact(NORMALIZED_WIDTH).enumerate() {
        let (context, amount) = context_amount(row)?;
        let reference = values
            .binary_search(&amount)
            .map_err(|_| Error::AmountIndex)?;
        let reference = u32::try_from(reference).map_err(|_| Error::AmountIndex)?;
        for (column, byte) in context.into_iter().enumerate() {
            columns[column * count + index] = byte;
        }
        for (column, byte) in reference.to_be_bytes().into_iter().enumerate() {
            columns[reference_start + column * count + index] = byte;
        }
    }
    Ok(Some(PackedAmounts {
        dictionary_count,
        columns,
    }))
}

pub(super) fn unpack(columns: &[u8], count: usize, unique: u32) -> Result<Vec<u8>> {
    if columns.len() != decoded_length(count, unique)? {
        return Err(Error::Width);
    }
    let unique = usize::try_from(unique).map_err(|_| Error::Count)?;
    let dictionary_start = count * CONTEXT_WIDTH;
    let reference_start = dictionary_start + unique * 16;
    let mut values = Vec::new();
    values
        .try_reserve_exact(unique)
        .map_err(|_| Error::Allocation)?;
    for index in 0..unique {
        let mut bytes = [0; 16];
        for (column, byte) in bytes.iter_mut().enumerate() {
            *byte = columns[dictionary_start + column * unique + index];
        }
        let value = PositiveAmount::from_bytes(bytes)?;
        if values.last().is_some_and(|prior| *prior >= value) {
            return Err(Error::AmountOrder);
        }
        values.push(value);
    }
    let mut used = buffer(unique)?;
    used.resize(unique, 0);
    let mut rows = buffer(
        count
            .checked_mul(NORMALIZED_WIDTH)
            .ok_or(Error::Arithmetic)?,
    )?;
    rows.resize(count * NORMALIZED_WIDTH, 0);
    for index in 0..count {
        let mut context = [0; CONTEXT_WIDTH];
        for (column, byte) in context.iter_mut().enumerate() {
            *byte = columns[column * count + index];
        }
        let mut reference = [0; 4];
        for (column, byte) in reference.iter_mut().enumerate() {
            *byte = columns[reference_start + column * count + index];
        }
        let reference =
            usize::try_from(u32::from_be_bytes(reference)).map_err(|_| Error::AmountIndex)?;
        let amount = values
            .get(reference)
            .ok_or(Error::AmountIndex)?
            .0
            .to_be_bytes();
        used[reference] = 1;
        let row = &mut rows[index * NORMALIZED_WIDTH..(index + 1) * NORMALIZED_WIDTH];
        if context[0] == 7 {
            row[..CONTEXT_WIDTH].copy_from_slice(&context);
            row[14..].copy_from_slice(&amount);
        } else if matches!(context[0], 1..=6 | 8..=10) {
            if context[12..] != [0; 2] {
                return Err(Error::Padding);
            }
            row[..12].copy_from_slice(&context[..12]);
            row[12..28].copy_from_slice(&amount);
        } else {
            return Err(Error::Canonical);
        }
    }
    if used.contains(&0) {
        return Err(Error::UnusedAmount);
    }
    Ok(rows)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn repeated_rows() -> Vec<u8> {
        [1_i128, 9, 1, 9, 9, 1, 9, 1]
            .into_iter()
            .flat_map(|amount| {
                let mut row = vec![0; NORMALIZED_WIDTH];
                row[0] = 7;
                row[1] = 7;
                row[2] = 1;
                row[3] = 3;
                row[8] = 1;
                row[9] = 2;
                row[14..].copy_from_slice(&amount.to_be_bytes());
                row
            })
            .collect()
    }

    #[test]
    fn dictionary_order_usage_and_exact_positive_values_are_required() {
        let rows = repeated_rows();
        let packed = pack(&rows, 8).unwrap().unwrap();
        assert_eq!(packed.dictionary_count, 2);
        assert_eq!(unpack(&packed.columns, 8, 2).unwrap(), rows);
        let dictionary = 8 * CONTEXT_WIDTH;
        for (second, expected) in [
            (1_i128, Error::AmountOrder),
            (0, Error::Canonical),
            (-1, Error::Canonical),
        ] {
            let mut changed = packed.columns.clone();
            for (column, byte) in second.to_be_bytes().into_iter().enumerate() {
                changed[dictionary + column * 2 + 1] = byte;
            }
            assert_eq!(unpack(&changed, 8, 2), Err(expected));
        }
        let reference = dictionary + 2 * 16;
        let mut unused = packed.columns.clone();
        unused[reference..].fill(0);
        assert_eq!(unpack(&unused, 8, 2), Err(Error::UnusedAmount));
        let mut outside = packed.columns.clone();
        for (column, byte) in 2_u32.to_be_bytes().into_iter().enumerate() {
            outside[reference + column * 8] = byte;
        }
        assert_eq!(unpack(&outside, 8, 2), Err(Error::AmountIndex));
        let mut trailing = packed.columns;
        trailing.push(0);
        assert_eq!(unpack(&trailing, 8, 2), Err(Error::Width));
    }

    #[test]
    fn dictionary_extent_and_overflow_refuse_before_allocation() {
        for (count, unique) in [(0, 0), (10, 0), (10, 11), (10, 8)] {
            assert_eq!(decoded_length(count, unique), Err(Error::Count));
        }
        assert_eq!(decoded_length(usize::MAX, u32::MAX), Err(Error::Arithmetic));
        assert_eq!(unpack(&[], 10, 2), Err(Error::Width));
        assert!(pack(&[], 0).unwrap().is_none());
    }
}
