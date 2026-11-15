//! Exact PG17 predecessor catalog admission for the read-only inspection source.
use super::InspectionCopyError;
use crate::current_schema;
use crate::postgres_catalog::{self, CatalogObjectKind};
use postgres::Transaction;
use sha2::{Digest as _, Sha256};

// Marker and four PG17 owner/reader/observer ACL footprints must identify the same pinned layout.
struct SourceSchema {
    marker: &'static str,
    footprints: [&'static str; 4],
}
const SOURCES: [SourceSchema; 2] = [
    // 2824cf38eb5c26fd721f1bf28c50989091448491, 155 catalog objects.
    SourceSchema {
        marker: "f984e7ee59fa650fc470f884b4663a6fc773c44ed4494254727273e50093d071",
        footprints: [
            "c38af76bf59866d6675eb56e1f8673ecc33ff883016202030c938307b123071f",
            "881d134225636629defdb4fb06cdc4b91ab1c5acedd833290c735f816df2c836",
            "613d4b07f48678df360a228b9cd79d7d9fd8a1e5f6d004e817c86b7ee4593dd8",
            "16a87359b6ad125a622c45bde75ce039497fff9ae79b7a44fc057a49282e08d4",
        ],
    },
    // dccef45d6, 204 catalog objects.
    SourceSchema {
        marker: "a8e623cb0f0a414e1bfebe808ae2f6631798070810f679bf8dca14198c4f9e69",
        footprints: [
            "f3796d7d4ecdc3a9afb5a90df21648d52c7364fd8019e9a344221769c5a04e89",
            "239da0c94f1335d02420cf370c6c471e2f51a94a82a1e687bc8e6df1162d3817",
            "4b95c3623343aaff76e6de458fa2f93fe71a715645e269a53ff8712a8c3ee997",
            "e672d7a3026cd7b3c0beacccd4d6774a5c0cbe5446fcfa94025cb4e28a0402f5",
        ],
    },
];
const INTEL: &str = "c3eac28a2cc8dcc019a4d1158d1e22c79737113927816086ca7d268f7ad77184";

fn admit(marker: &str, footprint: &str) -> Result<&'static str, InspectionCopyError> {
    SOURCES
        .iter()
        .find(|s| s.marker == marker && s.footprints.contains(&footprint))
        .map(|s| s.marker)
        .ok_or(InspectionCopyError::SourceSchema)
}

pub(super) fn check(tx: &mut Transaction<'_>) -> Result<&'static str, InspectionCopyError> {
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
    let row=tx.query_one("SELECT current_setting('transaction_read_only')='on',singleton,encode(schema_sha256,'hex') FROM babylon_meta.current_schema",&[]).map_err(|_|InspectionCopyError::SourceSchema)?;
    if !row
        .try_get::<_, bool>(0)
        .map_err(|_| InspectionCopyError::SourceSchema)?
        || !row
            .try_get::<_, bool>(1)
            .map_err(|_| InspectionCopyError::SourceSchema)?
    {
        return Err(InspectionCopyError::SourceSchema);
    }
    admit(
        row.try_get::<_, &str>(2)
            .map_err(|_| InspectionCopyError::SourceSchema)?,
        &actual,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn inspection_requires_marker_and_role_footprint_from_the_same_layout() {
        let [legacy, national] = &SOURCES;
        for layout in [legacy, national] {
            for footprint in layout.footprints {
                assert_eq!(admit(layout.marker, footprint), Ok(layout.marker));
            }
        }
        assert_eq!(
            admit(legacy.marker, national.footprints[0]),
            Err(InspectionCopyError::SourceSchema)
        );
        assert_eq!(
            admit(national.marker, legacy.footprints[3]),
            Err(InspectionCopyError::SourceSchema)
        );
        assert_eq!(
            admit(national.marker, "unknown footprint"),
            Err(InspectionCopyError::SourceSchema)
        );
        assert_eq!(
            admit("unknown marker", national.footprints[2]),
            Err(InspectionCopyError::SourceSchema)
        );
    }
}
