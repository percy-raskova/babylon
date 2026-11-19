//! Canonical nonnegative decimal strings for County Review money.
use serde::de::Error;
use serde::{Deserialize, Deserializer, Serializer};

fn canonical_string<E: serde::ser::Error>(value: i128) -> Result<String, E> {
    if value < 0 {
        return Err(E::custom("negative County Review amount"));
    }
    Ok(value.to_string())
}

fn parse_canonical<E: Error>(value: &str) -> Result<i128, E> {
    if value.len() > 39 {
        return Err(E::custom(
            "County Review amount decimal length exceeds bound",
        ));
    }
    let number = value
        .parse::<i128>()
        .map_err(|_| E::custom("invalid or overflowing County Review amount decimal"))?;
    if number < 0 || number.to_string() != value {
        return Err(E::custom(
            "noncanonical nonnegative County Review amount decimal",
        ));
    }
    Ok(number)
}

pub fn serialize<S: Serializer>(value: &i128, serializer: S) -> Result<S::Ok, S::Error> {
    serializer.serialize_str(&canonical_string(*value)?)
}

pub fn deserialize<'de, D: Deserializer<'de>>(deserializer: D) -> Result<i128, D::Error> {
    parse_canonical(&String::deserialize(deserializer)?)
}

/// The same canonical decimal string for an amount that may be absent: `None` is `null`.
pub mod option {
    use super::{canonical_string, parse_canonical};
    use serde::{Deserialize, Deserializer, Serializer};

    #[allow(
        clippy::ref_option,
        reason = "serde's `with` calls `serialize` with a reference to the field"
    )]
    pub fn serialize<S: Serializer>(
        value: &Option<i128>,
        serializer: S,
    ) -> Result<S::Ok, S::Error> {
        match value {
            None => serializer.serialize_none(),
            Some(amount) => serializer.serialize_str(&canonical_string(*amount)?),
        }
    }

    pub fn deserialize<'de, D: Deserializer<'de>>(
        deserializer: D,
    ) -> Result<Option<i128>, D::Error> {
        Option::<String>::deserialize(deserializer)?
            .map(|value| parse_canonical(&value))
            .transpose()
    }
}
