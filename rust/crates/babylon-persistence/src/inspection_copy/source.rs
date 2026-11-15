//! Exact PG17 predecessor catalog admission for the read-only inspection source.
use super::InspectionCopyError;
use crate::current_schema;
use crate::postgres_catalog::{self, CatalogObjectKind};
use postgres::Transaction;
use sha2::{Digest as _, Sha256};

pub(super) const SCHEMA: &str = "f984e7ee59fa650fc470f884b4663a6fc773c44ed4494254727273e50093d071";
// SHA-256 of each positional, length-framed kind, schema, name and object signature at
// 2824cf38eb5c26fd721f1bf28c50989091448491. Each of its four role footprints has 155 objects.
const FOOTPRINTS: [&str; 4] = [
    "c38af76bf59866d6675eb56e1f8673ecc33ff883016202030c938307b123071f",
    "881d134225636629defdb4fb06cdc4b91ab1c5acedd833290c735f816df2c836",
    "613d4b07f48678df360a228b9cd79d7d9fd8a1e5f6d004e817c86b7ee4593dd8",
    "16a87359b6ad125a622c45bde75ce039497fff9ae79b7a44fc057a49282e08d4",
];
const INTEL: &str = "c3eac28a2cc8dcc019a4d1158d1e22c79737113927816086ca7d268f7ad77184";

pub(super) fn check(tx: &mut Transaction<'_>) -> Result<(), InspectionCopyError> {
    current_schema::verify_owner_and_server(tx)
        .and_then(|()| current_schema::verify_sentinels(tx))
        .map_err(|_| InspectionCopyError::SourceSchema)?;
    let entries =
        postgres_catalog::read_census_rows(tx).map_err(|_| InspectionCopyError::SourceSchema)?;
    let mut hash = Sha256::new();
    for entry in entries {
        let key = entry.key();
        let kind = match key.kind() {
            CatalogObjectKind::Database => "database",
            CatalogObjectKind::Extension => "extension",
            CatalogObjectKind::Relation => "relation",
            CatalogObjectKind::Routine => "routine",
            CatalogObjectKind::Schema => "schema",
            CatalogObjectKind::SchemaGrant => "schema_grant",
            CatalogObjectKind::View => "view",
            CatalogObjectKind::Role
                if key.schema() == "pg_roles"
                    && key.name() == "babylon_intel"
                    && entry.digest_hex() == INTEL =>
            {
                continue
            }
            _ => return Err(InspectionCopyError::SourceSchema),
        };
        for field in [kind, key.schema(), key.name(), entry.digest_hex()] {
            let len = u64::try_from(field.len()).map_err(|_| InspectionCopyError::SourceSchema)?;
            hash.update(len.to_le_bytes());
            hash.update(field.as_bytes());
        }
    }
    let actual = crate::qualification_audit::trade::hex(&hash.finalize());
    if !FOOTPRINTS.contains(&actual.as_str()) {
        return Err(InspectionCopyError::SourceSchema);
    }
    let row=tx.query_one("SELECT current_setting('transaction_read_only')='on',singleton,encode(schema_sha256,'hex') FROM babylon_meta.current_schema",&[]).map_err(|_|InspectionCopyError::SourceSchema)?;
    if !row
        .try_get::<_, bool>(0)
        .map_err(|_| InspectionCopyError::SourceSchema)?
        || !row
            .try_get::<_, bool>(1)
            .map_err(|_| InspectionCopyError::SourceSchema)?
        || row
            .try_get::<_, String>(2)
            .map_err(|_| InspectionCopyError::SourceSchema)?
            != SCHEMA
    {
        return Err(InspectionCopyError::SourceSchema);
    }
    Ok(())
}
