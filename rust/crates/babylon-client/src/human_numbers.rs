//! Exact grouped quantities and money for the native client.

/// Group an unsigned quantity without narrowing its range.
pub(crate) fn grouped(value: u128) -> String {
    let raw = value.to_string();
    let mut text = String::with_capacity(raw.len() + raw.len() / 3);
    for (index, byte) in raw.bytes().enumerate() {
        if index > 0 && (raw.len() - index).is_multiple_of(3) {
            text.push(',');
        }
        text.push(char::from(byte));
    }
    text
}

/// Display common-currency micros exactly, with at least two decimal places.
pub(crate) fn currency(micros: i128) -> String {
    let amount = micros.unsigned_abs();
    let whole = grouped(amount / 1_000_000);
    let fraction = format!("{:06}", amount % 1_000_000);
    let trimmed = fraction.trim_end_matches('0');
    let digits = trimmed.len().max(2);
    let sign = if micros < 0 { "-" } else { "" };
    format!("{sign}${whole}.{}", &fraction[..digits])
}

/// Display common-currency micros rounded to the cent (half away from zero), grouped and signed
/// as `currency` writes them. A negative sum that rounds to nothing carries no sign.
pub(crate) fn currency_to_cent(micros: i128) -> String {
    const MICROS_PER_CENT: u128 = 10_000;
    let amount = micros.unsigned_abs();
    let whole_cents = amount / MICROS_PER_CENT;
    let cents = if amount % MICROS_PER_CENT >= MICROS_PER_CENT / 2 {
        whole_cents.saturating_add(1)
    } else {
        whole_cents
    };
    let sign = if micros < 0 && cents > 0 { "-" } else { "" };
    format!("{sign}${}.{:02}", grouped(cents / 100), cents % 100)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn money_to_the_cent_rounds_half_away_from_zero() {
        assert_eq!(currency_to_cent(1_823_642_480), "$1,823.64");
        assert_eq!(currency_to_cent(1_823_645_000), "$1,823.65");
        assert_eq!(currency_to_cent(4_800_000_000), "$4,800.00");
        assert_eq!(currency_to_cent(0), "$0.00");
        assert_eq!(currency_to_cent(-5_000), currency(-10_000));
        assert_eq!(currency_to_cent(-4_999), "$0.00");
    }

    #[test]
    fn money_to_the_cent_never_panics() {
        assert!(currency_to_cent(i128::MAX).starts_with('$'));
        assert!(currency_to_cent(i128::MIN).starts_with("-$"));
    }
}
