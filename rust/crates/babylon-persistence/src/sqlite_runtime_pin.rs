//! Pinned `SQLite` runtime identity for the embedded campaign store.

use std::fmt::Formatter;
use std::fmt::Result as FmtResult;

/// Exact numeric `SQLite` version required by the embedded campaign store.
pub const PINNED_SQLITE_VERSION_NUMBER: i32 = 3_053_001;

/// Exact version text required by the embedded campaign store.
pub const PINNED_SQLITE_VERSION_TEXT: &str = "3.53.1";

/// Identity of the `SQLite` library linked into this build.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SqliteRuntimeIdentity {
    /// Numeric version reported by the linked library.
    pub version_number: i32,
    /// Version text reported by the linked library.
    pub version_text: &'static str,
}

/// Why the linked `SQLite` library cannot serve the campaign store.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SqlitePinError {
    /// The linked library reports a different numeric version.
    VersionNumberMismatch {
        /// Version number required by the pinned build.
        expected: i32,
        /// Version number reported by the linked library.
        actual: i32,
    },
    /// The linked library reports a different version string.
    VersionTextMismatch {
        /// Version text required by the pinned build.
        expected: &'static str,
        /// Version text reported by the linked library.
        actual: &'static str,
    },
}

impl std::fmt::Display for SqlitePinError {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> FmtResult {
        match self {
            Self::VersionNumberMismatch { expected, actual } => write!(
                formatter,
                "linked SQLite version number {actual} does not match pinned {expected}"
            ),
            Self::VersionTextMismatch { expected, actual } => write!(
                formatter,
                "linked SQLite version {actual} does not match pinned {expected}"
            ),
        }
    }
}

impl std::error::Error for SqlitePinError {}

/// Verify that the linked `SQLite` library is the pinned 3.53.1 build.
///
/// # Errors
///
/// Returns [`SqlitePinError`] when the linked library reports a different
/// numeric version or version text. A campaign must refuse to open under a
/// mismatched `SQLite` engine.
pub fn verify_sqlite_runtime() -> Result<SqliteRuntimeIdentity, SqlitePinError> {
    let identity = SqliteRuntimeIdentity {
        version_number: rusqlite::version_number(),
        version_text: rusqlite::version(),
    };
    if identity.version_number != PINNED_SQLITE_VERSION_NUMBER {
        return Err(SqlitePinError::VersionNumberMismatch {
            expected: PINNED_SQLITE_VERSION_NUMBER,
            actual: identity.version_number,
        });
    }
    if identity.version_text != PINNED_SQLITE_VERSION_TEXT {
        return Err(SqlitePinError::VersionTextMismatch {
            expected: PINNED_SQLITE_VERSION_TEXT,
            actual: identity.version_text,
        });
    }
    Ok(identity)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn linked_sqlite_matches_pinned_3_53_1_runtime() {
        let identity = verify_sqlite_runtime().expect("linked SQLite must match pinned 3.53.1");
        assert_eq!(
            identity.version_number, 3_053_001,
            "SQLite version number must be 3.53.1"
        );
        assert_eq!(
            identity.version_text, "3.53.1",
            "SQLite version string must be 3.53.1"
        );
    }
}
