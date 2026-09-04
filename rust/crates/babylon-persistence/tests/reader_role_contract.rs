//! Byte-exact contracts for the PER-23 Slice 1 read-only reader role and
//! fog-safe committed-tick status view (ADR249 R8).

use babylon_persistence::{
    CommittedTickStatusV1, LegacyConnectionTargetRejection, ReaderRoleDispositionV1,
    SemanticArchiveErrorV1, SemanticArchiveReaderErrorV1, SemanticArchiveReaderV1,
    COMMITTED_TICK_STATUS_SQL_V1, READER_DSN_ENV_V1, READER_ROLE_CREATE_SQL_V1,
    READER_ROLE_NAME_V1, READER_ROLE_SCHEMA_V1_SQL, READER_VIEW_CANONICAL_DEF_V1,
};

#[test]
fn reader_role_create_sql_pins_exact_locked_attributes() {
    assert_eq!(READER_ROLE_NAME_V1, "babylon_reader");
    assert_eq!(
        READER_ROLE_CREATE_SQL_V1,
        "CREATE ROLE babylon_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE"
    );
    assert!(!READER_ROLE_CREATE_SQL_V1.contains("PASSWORD"));
    assert!(!READER_ROLE_CREATE_SQL_V1.contains(" LOGIN"));
    assert!(!READER_ROLE_CREATE_SQL_V1.contains("BYPASSRLS"));
    assert_eq!(READER_DSN_ENV_V1, "BABYLON_READER_DSN");
}

#[test]
fn reader_role_schema_grants_select_only_on_the_fog_safe_views() {
    assert!(READER_ROLE_SCHEMA_V1_SQL.contains("CREATE VIEW public.v_committed_tick_status_v1"));
    assert!(READER_ROLE_SCHEMA_V1_SQL.contains("FROM babylon_state.tick_commit"));
    for column in [
        "campaign_id",
        "resolve_tick",
        "envelope_layout_version",
        "tick_content_hash",
        "envelope_digest",
    ] {
        assert!(
            READER_ROLE_SCHEMA_V1_SQL.contains(column),
            "view projection must expose {column}"
        );
    }
    assert_eq!(
        READER_ROLE_SCHEMA_V1_SQL.matches("GRANT SELECT").count(),
        4,
        "one tick-view grant plus three guarded atom-view grants, nothing else"
    );
    assert!(READER_ROLE_SCHEMA_V1_SQL
        .contains("GRANT SELECT ON public.v_committed_tick_status_v1 TO babylon_reader"));
    for view in [
        "public.v_archive_page_known_v1",
        "public.v_archive_atom_visible",
        "public.v_county_card_atoms",
    ] {
        assert!(
            READER_ROLE_SCHEMA_V1_SQL
                .contains(&format!("GRANT SELECT ON {view} TO babylon_reader")),
            "the guarded block grants {view} when the atom schema is present"
        );
    }
    for table in [
        "archive_page_v1",
        "archive_knowledge_grant_v1",
        "archive_receipt_consumption_v1",
        "archive_atom_v1",
        "archive_page_atom_v1",
    ] {
        assert!(READER_ROLE_SCHEMA_V1_SQL.contains(&format!(
            "REVOKE ALL ON TABLE babylon_meta.{table} FROM babylon_reader"
        )));
    }
    assert!(!READER_ROLE_SCHEMA_V1_SQL.contains("IF NOT EXISTS"));
    assert!(!READER_ROLE_SCHEMA_V1_SQL.contains("GRANT USAGE ON SCHEMA"));
    assert!(!READER_ROLE_SCHEMA_V1_SQL.contains("GRANT ALL"));
    assert!(
        READER_ROLE_SCHEMA_V1_SQL.contains("pg_catalog.to_regclass"),
        "archive-table revokes and atom-view grants must tolerate an absent Archive schema"
    );
}

#[test]
fn committed_tick_status_read_goes_through_the_view_only() {
    assert!(COMMITTED_TICK_STATUS_SQL_V1.contains("FROM public.v_committed_tick_status_v1"));
    assert!(COMMITTED_TICK_STATUS_SQL_V1.contains("WHERE campaign_id = $1::uuid"));
    assert!(
        !COMMITTED_TICK_STATUS_SQL_V1.contains("babylon_state"),
        "the reader must never touch the base table directly"
    );
    assert!(COMMITTED_TICK_STATUS_SQL_V1.contains("ORDER BY resolve_tick DESC"));
}

#[test]
fn reader_view_canonical_definition_pins_the_exact_view_identity() {
    assert_eq!(
        READER_VIEW_CANONICAL_DEF_V1,
        "SELECT campaign_id, resolve_tick, envelope_layout_version, tick_content_hash, \
         envelope_digest FROM babylon_state.tick_commit"
    );
    assert!(
        !READER_VIEW_CANONICAL_DEF_V1.contains(';'),
        "the canonical definition carries no statement separator"
    );
}

#[test]
fn reader_privilege_census_pins_the_exact_restricted_relation_set() {
    let source = include_str!("../src/reader.rs");
    let census = source
        .split("READER_PRIVILEGE_CENSUS_SQL_V1: &str =")
        .nth(1)
        .expect("census SQL constant exists")
        .split(';')
        .next()
        .expect("census SQL constant terminates");
    for marker in [
        "WITH RECURSIVE role_closure(oid) AS",
        "SELECT 0::pg_catalog.oid",
        "pg_catalog.pg_auth_members",
        "pg_catalog.aclexplode",
        "'babylon_state'",
        "archive_page_v1",
        "archive_knowledge_grant_v1",
        "archive_receipt_consumption_v1",
        "archive_atom_v1",
        "archive_page_atom_v1",
        "'v_committed_tick_status_v1'",
        "'v_archive_page_known_v1'",
        "'v_archive_atom_visible'",
        "'v_county_card_atoms'",
        ":OWNERSHIP",
        "is_grantable",
        "attacl",
    ] {
        assert!(census.contains(marker), "census SQL must pin {marker}");
    }
    for forbidden in ["GRANT ", "REVOKE ", "has_table_privilege"] {
        assert!(
            !census.contains(forbidden),
            "the census query is read-only and must not contain {forbidden}"
        );
    }
    let authority = source
        .split("READER_SESSION_AUTHORITY_SQL_V1: &str =")
        .nth(1)
        .expect("session authority SQL constant exists")
        .split(';')
        .next()
        .expect("session authority SQL constant terminates");
    assert!(authority.contains("current_user"));
    assert!(authority.contains("rolsuper"));
}

/// Extract one `&str` constant body from the reader source, terminated by the
/// first `;` outside the literal (the pinned SQL carries no semicolon).
fn reader_constant_body<'a>(source: &'a str, name: &str) -> &'a str {
    source
        .split(&format!("{name}: &str = "))
        .nth(1)
        .unwrap_or_else(|| panic!("{name} constant exists"))
        .split(';')
        .next()
        .unwrap_or_else(|| panic!("{name} constant terminates"))
}

/// Extract the quoted entries of one `[&str; N]` constant from the reader
/// source, terminated by the first `]`.
fn reader_string_array_body<'a>(source: &'a str, name: &str) -> Vec<&'a str> {
    let body = source
        .split(&format!("{name}: [&str;"))
        .nth(1)
        .unwrap_or_else(|| panic!("{name} constant exists"))
        .split('[')
        .nth(1)
        .unwrap_or_else(|| panic!("{name} array opens"))
        .split(']')
        .next()
        .unwrap_or_else(|| panic!("{name} constant terminates"));
    body.split('"').skip(1).step_by(2).collect()
}

#[test]
fn reader_footprint_is_existence_dependent_on_the_atom_schema() {
    let source = include_str!("../src/reader.rs");
    assert_eq!(
        reader_string_array_body(source, "READER_FOOTPRINT_V1"),
        ["public.v_committed_tick_status_v1:SELECT"],
        "before the atom schema the tick-status view is the whole footprint"
    );
    let with_atoms = reader_string_array_body(source, "READER_FOOTPRINT_WITH_ATOMS_V1");
    assert_eq!(
        with_atoms,
        [
            "public.v_archive_atom_visible:SELECT",
            "public.v_archive_page_known_v1:SELECT",
            "public.v_committed_tick_status_v1:SELECT",
            "public.v_county_card_atoms:SELECT",
        ],
        "after the atom schema the footprint is exactly the four fog-safe views"
    );
    let mut sorted = with_atoms.clone();
    sorted.sort_unstable();
    assert_eq!(sorted, with_atoms, "the census emits entries sorted");
}

#[test]
fn reader_search_and_projection_reads_touch_only_fog_safe_views() {
    let source = include_str!("../src/reader.rs");
    for (name, view) in [
        (
            "READER_KNOWN_SEARCH_SQL_V1",
            "public.v_archive_page_known_v1",
        ),
        ("READER_PAGE_ATOMS_SQL_V1", "public.v_archive_atom_visible"),
        ("COUNTY_CARD_ATOMS_SQL_V1", "public.v_county_card_atoms"),
    ] {
        let body = reader_constant_body(source, name);
        assert!(
            body.contains(&format!("FROM {view}")),
            "{name} must read through {view}"
        );
        for forbidden in [
            "babylon_meta",
            "babylon_state",
            "MAX(",
            "archive_page_atom_v1",
        ] {
            assert!(
                !body.contains(forbidden),
                "{name} must never name {forbidden}"
            );
        }
    }
    let atoms = reader_constant_body(source, "READER_PAGE_ATOMS_SQL_V1");
    assert!(
        atoms.contains("page_subject_kind = $2"),
        "the page atom read addresses the composing page"
    );
    assert!(atoms.contains("ORDER BY position"));
    let county = reader_constant_body(source, "COUNTY_CARD_ATOMS_SQL_V1");
    assert!(county.contains("page_subject_id = $2"));
    assert!(county.contains("ORDER BY position"));
    // The atom reads carry the exact 15-column decode layout the shared
    // `decode_stored_atom` revalidator expects, `valid_tick` then `atom_id`
    // last. Continuation backslashes are whitespace-normalized first.
    for name in ["READER_PAGE_ATOMS_SQL_V1", "COUNTY_CARD_ATOMS_SQL_V1"] {
        let body = reader_constant_body(source, name).replace("\\\n", " ");
        let body = body.split_whitespace().collect::<Vec<_>>().join(" ");
        assert!(
            body.contains(
                "SELECT campaign_id, subject_kind, subject_id, signal_key, grant_key, \
                 evidence_class, value_kind, value_text, value_f64, value_u64, value_bool, \
                 provenance_source_id, provenance_locator, valid_tick, atom_id FROM"
            ),
            "{name} must pin the exact decode column layout, got {body}"
        );
    }
}

#[test]
fn reader_error_taxonomy_is_closed_and_reader_scoped() {
    fn assert_exhaustive(error: &SemanticArchiveReaderErrorV1) -> usize {
        match error {
            SemanticArchiveReaderErrorV1::MissingEnv(_)
            | SemanticArchiveReaderErrorV1::EnvNotUtf8(_)
            | SemanticArchiveReaderErrorV1::InvalidDsn
            | SemanticArchiveReaderErrorV1::ConnectionTarget(_)
            | SemanticArchiveReaderErrorV1::RoleMismatch
            | SemanticArchiveReaderErrorV1::ViewMismatch
            | SemanticArchiveReaderErrorV1::PrivilegeDrift(_)
            | SemanticArchiveReaderErrorV1::WriterAuthorityRefused(_)
            | SemanticArchiveReaderErrorV1::Archive(_)
            | SemanticArchiveReaderErrorV1::LockMismatch
            | SemanticArchiveReaderErrorV1::Database { .. } => 1,
        }
    }
    assert_eq!(
        assert_exhaustive(&SemanticArchiveReaderErrorV1::PrivilegeDrift(Vec::new())),
        1
    );
    assert_eq!(
        assert_exhaustive(&SemanticArchiveReaderErrorV1::WriterAuthorityRefused(vec![
            "babylon_state.tick_commit:OWNERSHIP".to_owned()
        ])),
        1
    );
    assert_eq!(
        assert_exhaustive(&SemanticArchiveReaderErrorV1::Archive(
            SemanticArchiveErrorV1::CollectionBound
        )),
        1
    );
    assert_ne!(
        SemanticArchiveReaderErrorV1::PrivilegeDrift(Vec::new()),
        SemanticArchiveReaderErrorV1::WriterAuthorityRefused(Vec::new()),
        "drift and writer authority are distinct refusals"
    );
}

fn refusal(raw: &str) -> SemanticArchiveReaderErrorV1 {
    SemanticArchiveReaderV1::from_dsn(raw)
        .map(|_| ())
        .unwrap_err()
}

#[test]
fn from_dsn_admits_only_validated_loopback_targets() {
    fn assert_send_sync<T: Send + Sync>() {}
    assert_send_sync::<SemanticArchiveReaderV1>();
    assert_send_sync::<SemanticArchiveReaderErrorV1>();
    assert_send_sync::<CommittedTickStatusV1>();
    assert_send_sync::<ReaderRoleDispositionV1>();

    assert_eq!(
        refusal("not a postgres DSN"),
        SemanticArchiveReaderErrorV1::InvalidDsn
    );
    assert_eq!(
        refusal("postgresql://reader:secret@203.0.113.10:5432/babylon"),
        SemanticArchiveReaderErrorV1::ConnectionTarget(
            LegacyConnectionTargetRejection::NonLoopbackTcp
        )
    );
    assert_eq!(
        refusal("postgresql://reader@127.0.0.1:5432/babylon?options=-c%20search_path%3Dredirected"),
        SemanticArchiveReaderErrorV1::ConnectionTarget(
            LegacyConnectionTargetRejection::StartupOptionsOverride
        )
    );
    assert_eq!(
        refusal("postgresql://reader@127.0.0.1,127.0.0.2/babylon"),
        SemanticArchiveReaderErrorV1::ConnectionTarget(
            // The driver expands one default port per named host, so the
            // redundant port list is reported before the host count.
            LegacyConnectionTargetRejection::MultiplePorts
        )
    );

    SemanticArchiveReaderV1::from_dsn("postgresql://reader:secret@127.0.0.1:5432/babylon")
        .expect("loopback reader DSN admits");
    SemanticArchiveReaderV1::from_dsn("postgresql://reader@/babylon?host=/var/run/postgresql")
        .expect("absolute unix-socket target admits");
}

#[test]
fn from_env_reports_a_missing_reader_dsn() {
    std::env::remove_var(READER_DSN_ENV_V1);
    assert_eq!(
        SemanticArchiveReaderV1::from_env().map(|_| ()).unwrap_err(),
        SemanticArchiveReaderErrorV1::MissingEnv(READER_DSN_ENV_V1)
    );
    std::env::set_var(
        READER_DSN_ENV_V1,
        "postgresql://reader@127.0.0.1:5432/babylon",
    );
    SemanticArchiveReaderV1::from_env().expect("loopback reader DSN admits");
    std::env::remove_var(READER_DSN_ENV_V1);
}
