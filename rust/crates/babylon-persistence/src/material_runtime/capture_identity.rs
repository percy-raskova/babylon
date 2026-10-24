//! Exact SQL capture freshness, separate from canonical game-state identity.
use postgres::types::{FromSql, Type};
use postgres::Row;

use postgres::Error as PostgresError;
use sha2::{Digest, Sha256};

#[derive(Debug)]
struct RawField<'a>(&'a [u8]);
impl<'a> FromSql<'a> for RawField<'a> {
    fn from_sql(
        _: &Type,
        bytes: &'a [u8],
    ) -> Result<Self, Box<dyn std::error::Error + Sync + Send>> {
        Ok(Self(bytes))
    }
    fn accepts(_: &Type) -> bool {
        true
    }
}

/// Hash the actual protocol fields without formatting, copying large bytea
/// owners, or trusting stored digest claims. Names, types, nulls, lengths and
/// row boundaries all participate. Call only after the capture transaction ends.
pub(crate) fn rows_digest<'a>(
    rows: impl IntoIterator<Item = &'a Row>,
) -> Result<[u8; 32], PostgresError> {
    let mut hash = Sha256::new();
    hash.update(b"babylon.sql-capture-freshness.v1\0");
    for row in rows {
        hash.update([1]);
        for (index, column) in row.columns().iter().enumerate() {
            hash.update([1]);
            hash.update(column.name().as_bytes());
            hash.update([0]);
            hash.update(column.type_().oid().to_be_bytes());
            match row.try_get::<_, Option<RawField<'_>>>(index)? {
                None => hash.update([0]),
                Some(field) => {
                    hash.update([1]);
                    hash.update((field.0.len() as u64).to_be_bytes());
                    hash.update(field.0);
                }
            }
        }
        hash.update([0]);
    }
    hash.update([0]);
    Ok(hash.finalize().into())
}
