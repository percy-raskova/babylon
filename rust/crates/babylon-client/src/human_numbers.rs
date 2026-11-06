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
