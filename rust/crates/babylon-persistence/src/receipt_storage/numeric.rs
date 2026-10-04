//! Checked relations already required by current typed receipt validators.
use super::{buffer, Error, Result};
fn u(row: &[u8], offset: usize) -> Result<u64> {
    Ok(u64::from_be_bytes(
        row.get(offset..offset + 8)
            .ok_or(Error::Width)?
            .try_into()
            .map_err(|_| Error::Width)?,
    ))
}
fn c(row: &[u8], offset: usize) -> Result<i128> {
    Ok(i128::from_be_bytes(
        row.get(offset..offset + 16)
            .ok_or(Error::Width)?
            .try_into()
            .map_err(|_| Error::Width)?,
    ))
}
fn sum(values: impl IntoIterator<Item = i128>) -> Result<i128> {
    values
        .into_iter()
        .try_fold(0_i128, |a, b| a.checked_add(b).ok_or(Error::Arithmetic))
}
pub(super) fn retained_width(tag: u8, mode: u8, original: usize) -> Result<usize> {
    match (mode, tag) {
        (0, _) => Ok(original),
        (1, 11) => Ok(30),
        (1, 28) => Ok(66),
        (1, 29) => Ok(89),
        (1, 19) => Ok(421),
        _ => Err(Error::Mode),
    }
}
fn reserve_tag(tag: u8) -> Result<u8> {
    match tag {
        1..=3 => Ok(2),
        4..=6 => Ok(3),
        8..=10 => Ok(4),
        _ => Err(Error::Canonical),
    }
}
fn keep(tag: u8, row: &[u8]) -> Result<Vec<u8>> {
    if tag == 11 {
        if row.len() != 50 {
            return Err(Error::Width);
        }
        let tag = row[0];
        let amount = c(row, 34)?;
        if amount <= 0 || c(row, 12)?.checked_neg() != Some(amount) {
            return Err(Error::Canonical);
        }
        let mut out = buffer(30)?;
        if tag == 7 {
            if row[2..6] != [0; 4] || row[6] != 1 || row[28] != 1 {
                return Err(Error::Canonical);
            }
            out.extend_from_slice(&row[..2]);
            out.extend_from_slice(&row[6..12]);
            out.extend_from_slice(&row[28..34]);
            out.extend_from_slice(&row[34..50]);
        } else if matches!(tag, 1..=6 | 8..=10) {
            out.extend_from_slice(&row[..6]);
            let reserve = reserve_tag(tag)?;
            let (cash, reserved) = if matches!(tag, 1 | 4 | 8) {
                (&row[6..12], &row[28..34])
            } else {
                (&row[28..34], &row[6..12])
            };
            if cash[0] != 1 || reserved[0] != reserve || reserved[1..] != row[1..6] {
                return Err(Error::Canonical);
            }
            out.extend_from_slice(cash);
            out.extend_from_slice(&row[34..50]);
            out.extend_from_slice(&[0; 2]);
        } else {
            return Err(Error::Canonical);
        }
        return Ok(out);
    }

    let (prefix, start, unit, indices): (usize, usize, usize, &[usize]) = match tag {
        28 => (26, 26, 8, &[1, 2, 3, 5, 6]),
        29 => (33, 33, 8, &[1, 2, 4, 6, 7, 8, 9]),
        19 => (
            5,
            13,
            16,
            &[
                0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,
                24, 25, 26,
            ],
        ),
        _ => return Err(Error::Mode),
    };
    let mut out = buffer(prefix + unit * indices.len())?;
    out.extend_from_slice(row.get(..prefix).ok_or(Error::Width)?);
    for i in indices {
        out.extend_from_slice(
            row.get(start + i * unit..start + (i + 1) * unit)
                .ok_or(Error::Width)?,
        );
    }
    Ok(out)
}
pub(super) fn pack_family(
    tag: u8,
    rows: &[u8],
    count: usize,
    width: usize,
    tick: u64,
) -> Result<(u8, usize, Vec<u8>)> {
    if !matches!(tag, 11 | 19 | 28 | 29) {
        return Ok((0, width, rows.to_vec()));
    }
    let retained = retained_width(tag, 1, width)?;
    let mut packed = buffer(count.checked_mul(retained).ok_or(Error::Arithmetic)?)?;
    for row in rows.chunks_exact(width) {
        let kept = keep(tag, row)?;
        if unpack_row(tag, 1, &kept, tick, width)? != row {
            return Ok((0, width, rows.to_vec()));
        }
        packed.extend(kept);
    }
    Ok((1, retained, packed))
}
pub(super) fn unpack_row(
    tag: u8,
    mode: u8,
    row: &[u8],
    tick: u64,
    width: usize,
) -> Result<Vec<u8>> {
    if mode == 0 {
        if row.len() != width {
            return Err(Error::Width);
        }
        return Ok(row.to_vec());
    }
    if row.len() != retained_width(tag, mode, width)? || tick == 0 {
        return Err(Error::Width);
    }
    let mut out = buffer(width)?;
    match tag {
        11 => unpack_cash(row, &mut out)?,
        28 => unpack_staffing(row, tick, &mut out)?,
        29 => unpack_member_labor(row, tick, &mut out)?,
        19 => unpack_income(row, tick, &mut out)?,
        _ => return Err(Error::Mode),
    }
    if out.len() != width {
        return Err(Error::Width);
    }
    Ok(out)
}

fn unpack_cash(row: &[u8], out: &mut Vec<u8>) -> Result<()> {
    let tag = row[0];
    let (purpose, cash, reserve, credit) = if tag == 7 {
        let mut purpose = vec![tag, row[1]];
        purpose.extend_from_slice(&[0; 4]);
        (
            purpose,
            row[2..8].to_vec(),
            row[8..14].to_vec(),
            c(row, 14)?,
        )
    } else if matches!(tag, 1..=6 | 8..=10) {
        if row[28..30] != [0; 2] {
            return Err(Error::Padding);
        }
        let mut reserve = vec![reserve_tag(tag)?];
        reserve.extend_from_slice(&row[1..6]);
        (row[..6].to_vec(), row[6..12].to_vec(), reserve, c(row, 12)?)
    } else {
        return Err(Error::Canonical);
    };
    if credit <= 0 {
        return Err(Error::Canonical);
    }
    let debit = credit.checked_neg().ok_or(Error::Arithmetic)?;
    let (from, to) = if tag == 7 || matches!(tag, 1 | 4 | 8) {
        (cash, reserve)
    } else {
        (reserve, cash)
    };
    out.extend(purpose);
    out.extend(from);
    out.extend_from_slice(&debit.to_be_bytes());
    out.extend(to);
    out.extend_from_slice(&credit.to_be_bytes());
    Ok(())
}

fn unpack_staffing(row: &[u8], tick: u64, out: &mut Vec<u8>) -> Result<()> {
    out.extend_from_slice(&row[..26]);
    let (force, hpp, opening, hires, separations) = (
        u(row, 26)?,
        u(row, 34)?,
        u(row, 42)?,
        u(row, 50)?,
        u(row, 58)?,
    );
    let closing = opening
        .checked_add(hires)
        .and_then(|n| n.checked_sub(separations))
        .ok_or(Error::Arithmetic)?;
    for value in [
        tick,
        force,
        hpp,
        opening,
        force.checked_sub(opening).ok_or(Error::Arithmetic)?,
        hires,
        separations,
        closing,
        force.checked_sub(closing).ok_or(Error::Arithmetic)?,
        closing.checked_mul(hpp).ok_or(Error::Arithmetic)?,
    ] {
        out.extend_from_slice(&value.to_be_bytes());
    }
    Ok(())
}

fn unpack_member_labor(row: &[u8], tick: u64, out: &mut Vec<u8>) -> Result<()> {
    out.extend_from_slice(&row[..33]);
    let tag = row[16];
    let rate = c(row, 17)?;
    if !matches!((tag, rate), (1, 1..) | (2 | 3, 0)) {
        return Err(Error::Canonical);
    }
    let (avail, planned, attended, production, handling, maintenance, installation) = (
        u(row, 33)?,
        u(row, 41)?,
        u(row, 49)?,
        u(row, 57)?,
        u(row, 65)?,
        u(row, 73)?,
        u(row, 81)?,
    );
    let used = production
        .checked_add(handling)
        .and_then(|n| n.checked_add(maintenance))
        .and_then(|n| n.checked_add(installation))
        .ok_or(Error::Arithmetic)?;
    let idle = attended.checked_sub(used).ok_or(Error::Arithmetic)?;
    let unattended = planned.checked_sub(attended).ok_or(Error::Arithmetic)?;
    if tag != 1 && unattended != 0 {
        return Err(Error::Canonical);
    }
    for value in [
        tick,
        avail,
        planned,
        avail.checked_sub(planned).ok_or(Error::Arithmetic)?,
        attended,
        unattended,
        production,
        handling,
        maintenance,
        installation,
        idle,
    ] {
        out.extend_from_slice(&value.to_be_bytes());
    }
    for hours in [
        attended,
        production,
        handling,
        maintenance,
        installation,
        idle,
    ] {
        let wages = rate
            .checked_mul(i128::from(hours))
            .ok_or(Error::Arithmetic)?;
        out.extend_from_slice(&wages.to_be_bytes());
    }
    Ok(())
}

fn unpack_income(row: &[u8], tick: u64, out: &mut Vec<u8>) -> Result<()> {
    out.extend_from_slice(&row[..5]);
    out.extend_from_slice(&tick.to_be_bytes());
    let mut values = [0_i128; 29];
    let mut source = 5;
    for (index, value) in values.iter_mut().enumerate() {
        if !matches!(index, 4 | 27 | 28) {
            *value = c(row, source)?;
            source += 16;
        }
    }
    for index in [
        0, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,
    ] {
        if values[index] < 0 {
            return Err(Error::Canonical);
        }
    }
    let expenses = sum([8, 12, 13, 14, 15, 16, 17, 18, 19].map(|i| values[i]))?;
    let operating = values[6].checked_sub(expenses).ok_or(Error::Arithmetic)?;
    let income = sum([7, 20, 22, 24, 25].map(|i| values[i]))?;
    let outlays = sum([21, 23, 26].map(|i| values[i]))?;
    values[4] = values[2].checked_add(values[3]).ok_or(Error::Arithmetic)?;
    values[27] = operating
        .checked_add(income)
        .and_then(|n| n.checked_sub(outlays))
        .ok_or(Error::Arithmetic)?;
    values[28] = values[1]
        .checked_add(values[27])
        .and_then(|n| n.checked_sub(values[5]))
        .ok_or(Error::Arithmetic)?;
    for value in values {
        out.extend_from_slice(&value.to_be_bytes());
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn staffed_rows_reconstruct_without_losing_inputs() {
        let mut row = vec![0; 106];
        for (i, v) in [1_u64, 5, 8, 3, 2, 1, 0, 4, 1, 32].into_iter().enumerate() {
            row[26 + i * 8..34 + i * 8].copy_from_slice(&v.to_be_bytes());
        }
        let kept = keep(28, &row).unwrap();
        assert_eq!(unpack_row(28, 1, &kept, 1, 106).unwrap(), row);
    }
    #[test]
    fn independently_authored_period_uses_exact_generic_fallback() {
        let mut row = vec![0; 106];
        for (i, v) in [2_u64, 5, 8, 3, 2, 1, 0, 4, 1, 32].into_iter().enumerate() {
            row[26 + i * 8..34 + i * 8].copy_from_slice(&v.to_be_bytes());
        }
        let (mode, width, packed) = pack_family(28, &row, 1, 106, 1).unwrap();
        assert_eq!(mode, 0);
        assert_eq!(width, 106);
        assert_eq!(packed, row);
    }
    #[test]
    fn capitalized_costs_remain_inputs_without_becoming_expenses() {
        let mut row = vec![0; 477];
        let mut values = [0_i128; 29];
        values[6] = 100;
        values[8] = 10;
        values[9] = 50;
        values[10] = 20;
        values[11] = 30;
        values[27] = 90;
        values[28] = 90;
        row[5..13].copy_from_slice(&1_u64.to_be_bytes());
        for (i, value) in values.into_iter().enumerate() {
            row[13 + i * 16..29 + i * 16].copy_from_slice(&value.to_be_bytes());
        }
        let (mode, width, packed) = pack_family(19, &row, 1, 477, 1).unwrap();
        assert_eq!(mode, 1);
        assert_eq!(width, 421);
        assert_eq!(unpack_row(19, mode, &packed, 1, 477).unwrap(), row);
    }
    #[test]
    fn overflow_and_underflow_refuse() {
        let mut row = vec![0; 66];
        row[26..34].copy_from_slice(&1_u64.to_be_bytes());
        row[42..50].copy_from_slice(&u64::MAX.to_be_bytes());
        row[50..58].copy_from_slice(&1_u64.to_be_bytes());
        assert_eq!(unpack_row(28, 1, &row, 1, 106), Err(Error::Arithmetic));
    }
    #[test]
    fn gifts_preserve_independent_income_and_expense_inputs() {
        let mut row = vec![0; 477];
        row[5..13].copy_from_slice(&1_u64.to_be_bytes());
        let mut amounts = [0_i128; 29];
        amounts[1] = 50;
        amounts[2] = 10;
        amounts[3] = 20;
        amounts[4] = 30;
        amounts[6] = 100;
        amounts[8] = 10;
        amounts[25] = 17;
        amounts[26] = 9;
        amounts[27] = 98;
        amounts[28] = 148;
        for (i, amount) in amounts.into_iter().enumerate() {
            row[13 + i * 16..29 + i * 16].copy_from_slice(&amount.to_be_bytes());
        }
        let (mode, width, packed) = pack_family(19, &row, 1, 477, 1).unwrap();
        assert_eq!((mode, width), (1, 421));
        assert_eq!(unpack_row(19, mode, &packed, 1, 477).unwrap(), row);
        assert_eq!(c(&row, 13 + 25 * 16).unwrap(), 17);
        assert_eq!(c(&row, 13 + 26 * 16).unwrap(), 9);
        let (mode, width, packed) = pack_family(19, &row, 1, 477, 2).unwrap();
        assert_eq!((mode, width), (0, 477));
        assert_eq!(packed, row);
    }

    #[test]
    fn all_aid_cash_purposes_reconstruct_exact_reserve_direction() {
        for purpose in [8, 9, 10] {
            let mut row = vec![0; 50];
            row[0] = purpose;
            row[2..6].copy_from_slice(&11_u32.to_be_bytes());
            let cash = [1, 2, 0, 0, 0, 23];
            let reserve = [4, 0, 0, 0, 0, 11];
            let (debit, credit) = if purpose == 8 {
                (cash, reserve)
            } else {
                (reserve, cash)
            };
            row[6..12].copy_from_slice(&debit);
            row[12..28].copy_from_slice(&(-31_i128).to_be_bytes());
            row[28..34].copy_from_slice(&credit);
            row[34..50].copy_from_slice(&31_i128.to_be_bytes());
            let (mode, width, packed) = pack_family(11, &row, 1, 50, 1).unwrap();
            assert_eq!((mode, width), (1, 30));
            assert_eq!(unpack_row(11, mode, &packed, 1, 50).unwrap(), row);
            let bad_reserve = if purpose == 8 { 28 } else { 6 };
            row[bad_reserve] = 2;
            assert_eq!(keep(11, &row), Err(Error::Canonical));
        }
    }
}
