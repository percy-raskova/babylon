//! Byte-exact contracts for the PER-23 Slice 1 read-only reader role and
//! fog-safe committed-tick status view (ADR249 R8).

use babylon_persistence::{
    CommittedTickStatusV1, LegacyConnectionTargetRejection, ReaderRoleDispositionV1,
    SemanticArchiveReaderErrorV1, SemanticArchiveReaderV1, COMMITTED_TICK_STATUS_SQL_V1,
    READER_DSN_ENV_V1, READER_ROLE_CREATE_SQL_V1, READER_ROLE_NAME_V1, READER_ROLE_SCHEMA_V1_SQL,
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
fn reader_role_schema_grants_select_only_on_the_tick_status_view() {
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
        1,
        "exactly one SELECT grant exists and it is the view grant"
    );
    assert!(READER_ROLE_SCHEMA_V1_SQL
        .contains("GRANT SELECT ON public.v_committed_tick_status_v1 TO babylon_reader"));
    for table in [
        "archive_page_v1",
        "archive_knowledge_grant_v1",
        "archive_receipt_consumption_v1",
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
        "archive-table revokes must tolerate an absent Archive schema"
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
