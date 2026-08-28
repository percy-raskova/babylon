//! Rust writer authority remains unavailable until the one-way cutover lands.

#[path = "../src/writer_gate.rs"]
mod writer_gate;

use writer_gate::{request_rust_writer_authority, RustWriterAuthority, RustWriterAuthorityError};

#[test]
fn production_request_refuses_while_python_authority_is_active() {
    let request: fn() -> Result<RustWriterAuthority, RustWriterAuthorityError> =
        request_rust_writer_authority;

    let first = request();
    let second = request();

    assert!(matches!(
        first,
        Err(RustWriterAuthorityError::PythonAuthorityActive)
    ));
    assert!(matches!(
        second,
        Err(RustWriterAuthorityError::PythonAuthorityActive)
    ));
}

#[test]
fn source_exposes_no_alternate_activation_channel() {
    let source = include_str!("../src/writer_gate.rs");
    let forbidden = [
        "std::env",
        "env::",
        "env!",
        "option_env!",
        "#[cfg",
        "feature =",
        "postgres",
        ".connect(",
        "schema_migration",
        "babylon_state",
        ": bool",
        "unsafe",
        "Default",
        "Deserialize",
        "pub(crate)",
        "fn new",
        "fn from",
        "impl From",
        "static mut",
        "AtomicBool",
        "OnceLock",
        "Mutex",
    ];

    for token in forbidden {
        assert!(
            !source.contains(token),
            "writer authority source must not expose forbidden activation token {token:?}"
        );
    }
    assert!(source.contains("pub struct RustWriterAuthority"));
    assert!(source.contains("_private: ()"));
    assert!(!source.contains("pub _private"));
    assert!(!source.contains("pub(crate) _private"));
}

#[test]
fn production_tree_has_exactly_one_closed_authority_definition() {
    let source_root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
    let mut pending = vec![source_root];
    let mut rust_sources = Vec::new();
    while let Some(directory) = pending.pop() {
        for entry in std::fs::read_dir(directory).expect("read production source directory") {
            let path = entry.expect("read production source entry").path();
            if path.is_dir() {
                pending.push(path);
            } else if path.extension().is_some_and(|extension| extension == "rs") {
                rust_sources.push(path);
            }
        }
    }
    rust_sources.sort();

    let mut request_definitions = 0;
    let mut authority_definitions_or_literals = 0;
    let mut authority_impls = 0;
    for path in rust_sources {
        let source = std::fs::read_to_string(&path).expect("read UTF-8 production Rust source");
        request_definitions += source
            .matches("pub fn request_rust_writer_authority(")
            .count();
        authority_definitions_or_literals += source.matches("RustWriterAuthority {").count();
        authority_impls += source.matches("impl RustWriterAuthority").count();
    }

    assert_eq!(request_definitions, 1, "one public authority request path");
    assert_eq!(
        authority_definitions_or_literals, 1,
        "the private struct definition must be the only constructor-shaped source"
    );
    assert_eq!(authority_impls, 0, "no alternate inherent constructor path");
}

#[test]
fn refusal_is_a_typed_public_error() {
    fn assert_error<T: std::error::Error + Send + Sync + 'static>() {}

    assert_error::<RustWriterAuthorityError>();
    assert_eq!(
        RustWriterAuthorityError::PythonAuthorityActive.to_string(),
        "Rust writer authority is unavailable while Python authority is active"
    );
}
