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
fn refusal_is_a_typed_public_error() {
    fn assert_error<T: std::error::Error + Send + Sync + 'static>() {}

    assert_error::<RustWriterAuthorityError>();
    assert_eq!(
        RustWriterAuthorityError::PythonAuthorityActive.to_string(),
        "Rust writer authority is unavailable while Python authority is active"
    );
}
