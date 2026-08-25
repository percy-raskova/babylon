//! Structural interlock for the future one-way Rust writer cutover.

/// Capability required by any future authoritative Rust tick writer.
///
/// Its field is private, and this module provides no successful construction
/// path while Python retains live writer authority.
#[derive(Debug)]
pub struct RustWriterAuthority {
    _private: (),
}

/// Exact reason Rust writer authority cannot currently be acquired.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RustWriterAuthorityError {
    /// Python remains the sole live runtime writer.
    PythonAuthorityActive,
}

/// Request authoritative Rust writer capability.
///
/// # Errors
///
/// Always returns [`RustWriterAuthorityError::PythonAuthorityActive`] until a
/// separately accepted one-way cutover replaces this implementation.
pub fn request_rust_writer_authority() -> Result<RustWriterAuthority, RustWriterAuthorityError> {
    Err(RustWriterAuthorityError::PythonAuthorityActive)
}

impl std::fmt::Display for RustWriterAuthorityError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::PythonAuthorityActive => formatter
                .write_str("Rust writer authority is unavailable while Python authority is active"),
        }
    }
}

impl std::error::Error for RustWriterAuthorityError {}
