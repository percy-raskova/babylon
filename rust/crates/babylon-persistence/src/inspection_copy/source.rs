//! Exact PG17 predecessor catalog admission for the read-only inspection source.
use super::InspectionCopyError;
use crate::current_schema;
use crate::postgres_catalog::{self, CatalogCensusEntry, CatalogObjectKind};
use postgres::Transaction;
use sha2::{Digest as _, Sha256};

// Marker and four PG17 owner/reader/observer ACL footprints must identify the same pinned layout.
struct SourceSchema {
    marker: &'static str,
    footprints: [&'static str; 4],
}
const SOURCES: [SourceSchema; 5] = [
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
    // 3db768eeb, 207 catalog objects.
    SourceSchema {
        marker: "27a833249a240ffdb2e524a45905f77b19dadb7dd05cf5db2e1c59d83318396b",
        footprints: [
            "9ef76248952dd552ea86cdba24b21c27a00d188d74925e517518501c23968bb6",
            "7bc8db465b231b6363a86585a9f898f2d4d33c15233d6986bb822b51fa416a82",
            "1e54dab3af3df74ad252d7eb87fe675ea4e7d7e4925d65b3d8885a72ad7693b7",
            "d15e5c8745c5682d1d8920741dcfc30aceb0779c631fd46547246e9ec6397b1d",
        ],
    },
    // bfa871b08, 248 catalog objects.
    SourceSchema {
        marker: "85346ef39af0c28ce6455ab60fb2f2abb2f39b7f23bbbf07ad5ab4afd1013ba3",
        footprints: [
            "3e8df25ec079f7200370ca587237dd1f9575d4ec890f647d11d2f4e8e7ace929",
            "71e2f20dd8e61a0122c5b0b273bb35a076f07e3d531ff2d86664b108bbde3b99",
            "73b9e867afbc830f8a68b3207c52b0d7742c34303cf888c6b26e4c9a4cfe346f",
            "bc983e892397c35f9963550f817a6610288977df85eee63830580c9851642c9b",
        ],
    },
    // e16170cf0^ (dev at 56483608e), 248 catalog objects.
    SourceSchema {
        marker: "928796a327c81ef7b0bb716a2afddfd8cb761b1a4adf69e8edff3dbf11aa3f7b",
        footprints: [
            "a404e8d7e51a8d4f90bc63c06e446541a824ac07f9bfeb3f57dee5bda74b353f",
            "6bee3b53a7da970c346fc1bbf8561045253e3637cd7b7fd660c37476deb7a250",
            "a4e4ef6bb96deed6fcc1aab2f61fe2b86216efe9d938d9895d11ec22ca45d9b4",
            "ba17ca78f45f140f9257f8a3ac1f13e2b80b2cbfce55d896294a984127bc5a4d",
        ],
    },
];
/// The marker and the four ACL footprints of the layout this build installs (owner, reader,
/// observer, reader and observer: the order of the fixtures `current_schema` embeds).
///
/// When the stored layout changes, the two tests `the_current_layout_is_the_one_this_file_names`
/// and `the_current_layout_is_not_its_own_predecessor` fail. Then, in this order: take the values
/// these constants held, for they name the layout that has just become a predecessor, and add
/// them to `SOURCES` as a new entry; make the live test
/// `predecessor_inspection_copies_only_the_named_campaign_without_adopting_its_database` restore
/// that layout in its private source and copy from it; decide in `rows.rs` (`carries`) whether a
/// table the new layout adds is carried by the older ones; and only then set these constants to
/// the new layout's values. Run the live focus `money_journal` for any such change.
#[cfg(test)]
const CURRENT_MARKER: &str = "39e625875539577ccce7d0768d20f01c6084aa08d56df890dcd26486369afedb";
#[cfg(test)]
const CURRENT_FOOTPRINTS: [&str; 4] = [
    "3f39105e7b8a6c43926deb5677ddd034a23353239d7e11615c0b0a4c9d1e2742",
    "5e2c844d50a0cbc9b6736cc1c39eb2362f3323ed2c30eb9cfd0da7e99225302d",
    "b755f50de4c1864c4bdf41f2558295cdeb02f637ddbbf361f8cdc20feb7758ec",
    "eb616d229236bfc5173dadd4ce7d28470e63ebbe4397bba87e35e9b2acd2e100",
];
const INTEL: &str = "c3eac28a2cc8dcc019a4d1158d1e22c79737113927816086ca7d268f7ad77184";

/// The table the layout of memberships carrying a value added; no admitted predecessor has it.
const MEMBER_VALUES: &str = "babylon_state.graph_hyperedge_member_f64_v1";
/// Markers of the admitted layouts that lack `MEMBER_VALUES`: the five predecessors.
const WITHOUT_MEMBER_VALUES: [&str; 5] = [
    "f984e7ee59fa650fc470f884b4663a6fc773c44ed4494254727273e50093d071",
    "a8e623cb0f0a414e1bfebe808ae2f6631798070810f679bf8dca14198c4f9e69",
    "27a833249a240ffdb2e524a45905f77b19dadb7dd05cf5db2e1c59d83318396b",
    "85346ef39af0c28ce6455ab60fb2f2abb2f39b7f23bbbf07ad5ab4afd1013ba3",
    "928796a327c81ef7b0bb716a2afddfd8cb761b1a4adf69e8edff3dbf11aa3f7b",
];

/// Whether the layout an admitted marker names holds the table. Decided by the marker alone.
pub(super) fn carries(marker: &str, table: &str) -> bool {
    !(table == MEMBER_VALUES && WITHOUT_MEMBER_VALUES.contains(&marker))
}

fn admit(marker: &str, footprint: &str) -> Result<&'static str, InspectionCopyError> {
    SOURCES
        .iter()
        .find(|s| s.marker == marker && s.footprints.contains(&footprint))
        .map(|s| s.marker)
        .ok_or(InspectionCopyError::SourceSchema)
}

/// The digest of the admitted census entries, each as kind, schema, name and digest with a
/// little-endian `u64` length before its bytes; the `babylon_intel` role is the one entry skipped.
fn footprint(entries: &[CatalogCensusEntry]) -> Result<String, InspectionCopyError> {
    let mut hash = Sha256::new();
    for entry in entries {
        let key = entry.key();
        let kind = match key.kind() {
            CatalogObjectKind::Database => "database",
            CatalogObjectKind::Domain => "domain",
            CatalogObjectKind::Extension => "extension",
            CatalogObjectKind::Relation => "relation",
            CatalogObjectKind::Routine => "routine",
            CatalogObjectKind::Schema => "schema",
            CatalogObjectKind::SchemaGrant => "schema_grant",
            CatalogObjectKind::UserType => "user_type",
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
    Ok(crate::qualification_audit::trade::hex(&hash.finalize()))
}

pub(super) fn check(tx: &mut Transaction<'_>) -> Result<&'static str, InspectionCopyError> {
    current_schema::verify_owner_and_server(tx)
        .and_then(|()| current_schema::verify_sentinels(tx))
        .map_err(|_| InspectionCopyError::SourceSchema)?;
    let entries =
        postgres_catalog::read_census_rows(tx).map_err(|_| InspectionCopyError::SourceSchema)?;
    let actual = footprint(&entries)?;
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
    fn the_layout_before_membership_values_is_admitted() {
        let marker = "928796a327c81ef7b0bb716a2afddfd8cb761b1a4adf69e8edff3dbf11aa3f7b";
        for footprint in [
            "a404e8d7e51a8d4f90bc63c06e446541a824ac07f9bfeb3f57dee5bda74b353f",
            "6bee3b53a7da970c346fc1bbf8561045253e3637cd7b7fd660c37476deb7a250",
            "a4e4ef6bb96deed6fcc1aab2f61fe2b86216efe9d938d9895d11ec22ca45d9b4",
            "ba17ca78f45f140f9257f8a3ac1f13e2b80b2cbfce55d896294a984127bc5a4d",
        ] {
            assert_eq!(admit(marker, footprint), Ok(marker));
        }
    }

    #[test]
    fn only_the_five_predecessors_lack_the_membership_value_table() {
        for source in &SOURCES {
            assert!(!carries(source.marker, MEMBER_VALUES));
            assert!(carries(
                source.marker,
                "babylon_state.graph_hyperedge_member_v1"
            ));
        }
        assert_eq!(WITHOUT_MEMBER_VALUES.len(), SOURCES.len());
        for marker in WITHOUT_MEMBER_VALUES {
            assert!(SOURCES.iter().any(|s| s.marker == marker));
        }
        assert!(carries(CURRENT_MARKER, MEMBER_VALUES));
        assert!(carries("unknown marker", MEMBER_VALUES));
        assert!(carries("unknown marker", "babylon_state.tick_commit"));
    }

    #[test]
    fn the_current_layout_is_the_one_this_file_names() {
        assert_eq!(
            crate::qualification_audit::trade::hex(&current_schema::current_schema_sha256()),
            CURRENT_MARKER
        );
        let actual: Vec<String> = current_schema::current_census_fixtures()
            .iter()
            .map(|text| {
                let census = postgres_catalog::parse_catalog_census(text).expect("fixture parses");
                footprint(census.entries()).expect("fixture entries are admitted kinds")
            })
            .collect();
        assert_eq!(actual, CURRENT_FOOTPRINTS);
    }

    #[test]
    fn the_current_layout_is_not_its_own_predecessor() {
        for source in &SOURCES {
            assert_ne!(source.marker, CURRENT_MARKER);
            for footprint in CURRENT_FOOTPRINTS {
                assert!(!source.footprints.contains(&footprint));
            }
        }
    }

    #[test]
    fn inspection_requires_marker_and_role_footprint_from_the_same_layout() {
        let archive_marker = "27a833249a240ffdb2e524a45905f77b19dadb7dd05cf5db2e1c59d83318396b";
        let reader_observer = "d15e5c8745c5682d1d8920741dcfc30aceb0779c631fd46547246e9ec6397b1d";
        assert_eq!(admit(archive_marker, reader_observer), Ok(archive_marker));

        for source in &SOURCES {
            for candidate in &SOURCES {
                for footprint in candidate.footprints {
                    let expected = if candidate.marker == source.marker {
                        Ok(source.marker)
                    } else {
                        Err(InspectionCopyError::SourceSchema)
                    };
                    assert_eq!(admit(source.marker, footprint), expected);
                }
            }
            assert_eq!(
                admit(source.marker, "unknown footprint"),
                Err(InspectionCopyError::SourceSchema)
            );
        }
        assert_eq!(
            admit("unknown marker", reader_observer),
            Err(InspectionCopyError::SourceSchema)
        );
    }
}
