use serde::{de::Error, Deserialize, Deserializer, Serializer};

pub fn serialize<S: Serializer>(value: &i128, serializer: S) -> Result<S::Ok, S::Error> {
    if *value < 0 {
        return Err(serde::ser::Error::custom("negative aid cash posting"));
    }
    serializer.serialize_str(&value.to_string())
}

pub fn deserialize<'de, D: Deserializer<'de>>(deserializer: D) -> Result<i128, D::Error> {
    let value = String::deserialize(deserializer)?;
    if value.len() > 39 {
        return Err(D::Error::custom("aid cash decimal length exceeds bound"));
    }
    let number = value
        .parse::<i128>()
        .map_err(|_| D::Error::custom("invalid or overflowing aid cash decimal"))?;
    if number < 0 || number.to_string() != value {
        return Err(D::Error::custom(
            "noncanonical nonnegative aid cash decimal",
        ));
    }
    Ok(number)
}
