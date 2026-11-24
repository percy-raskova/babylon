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

/// Micro-hours as an exact decimal of hours, trailing zeros dropped, the whole hours grouped:
/// `239_921_875` is "239.921875".
pub(crate) fn micro_hours(value: u128) -> String {
    let whole = grouped(value / 1_000_000);
    let fraction = format!("{:06}", value % 1_000_000);
    let fraction = fraction.trim_end_matches('0');
    if fraction.is_empty() {
        whole
    } else {
        format!("{whole}.{fraction}")
    }
}

/// Micro-hours to the nearest whole hour, half up, grouped as `grouped` groups.
pub(crate) fn micro_hours_to_hour(value: u128) -> String {
    let whole = value / 1_000_000;
    let half_or_more = value % 1_000_000 >= 500_000;
    grouped(if half_or_more {
        whole.saturating_add(1)
    } else {
        whole
    })
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
    fn micro_hours_are_written_exactly() {
        assert_eq!(micro_hours(239_921_875), "239.921875");
        assert_eq!(micro_hours(1_000_000), "1");
        assert_eq!(micro_hours(2_222_222), "2.222222");
        assert_eq!(micro_hours(0), "0");
        assert_eq!(micro_hours(1_234_000_000), "1,234");
        assert_eq!(micro_hours_to_hour(237_500_000), "238");
        assert_eq!(micro_hours_to_hour(237_499_999), "237");
        assert!(micro_hours_to_hour(u128::MAX).starts_with("340,282,366"));
    }

    #[test]
    fn money_to_the_cent_never_panics() {
        assert!(currency_to_cent(i128::MAX).starts_with('$'));
        assert!(currency_to_cent(i128::MIN).starts_with("-$"));
    }
}
