//! §6.1's exact server capabilities (the wave-1 plan,
//! `docs/superpowers/plans/2026-08-17-652-bsl-ls.md`): what `initialize`
//! advertises. This module's own test asserts the serialized JSON against
//! the spec's literal, so any future accidental capability drift shows up
//! as a failing diff, not a silent behavior change.

use lsp_types::{
    DiagnosticOptions, DiagnosticServerCapabilities, OneOf, ServerCapabilities,
    TextDocumentSyncCapability, TextDocumentSyncKind, TextDocumentSyncOptions,
    WorkDoneProgressOptions, WorkspaceFoldersServerCapabilities, WorkspaceServerCapabilities,
};

/// The [`ServerCapabilities`] `initialize` advertises.
///
/// Full sync, not Incremental (§6.1): the loader re-reads the whole file on
/// every change regardless, the content estate is small (largest file
/// 24 KB against a ~440 KB total), and Full sync deletes a whole class of
/// position-mapping bugs — Incremental is a wave-2 optimization to be taken
/// only against a measurement.
///
/// Push AND pull diagnostics: `interFileDependencies: true` and
/// `workspaceDiagnostics: true` both hold because a content set spans
/// files (a manifest-declared set, not one file in isolation) and
/// `workspace/diagnostic` is the capability a coding agent needs — one
/// synchronous "entire current error state" call after an edit.
///
/// `positionEncoding` is left unset (omitted from the JSON), which the LSP
/// spec makes the client default to UTF-16 — the encoding
/// [`crate::line_index`] assumes throughout.
#[must_use]
pub fn server_capabilities() -> ServerCapabilities {
    ServerCapabilities {
        text_document_sync: Some(TextDocumentSyncCapability::Options(
            TextDocumentSyncOptions {
                open_close: Some(true),
                change: Some(TextDocumentSyncKind::FULL),
                will_save: None,
                will_save_wait_until: None,
                save: None,
            },
        )),
        diagnostic_provider: Some(DiagnosticServerCapabilities::Options(DiagnosticOptions {
            identifier: Some("bsl".to_owned()),
            inter_file_dependencies: true,
            workspace_diagnostics: true,
            work_done_progress_options: WorkDoneProgressOptions {
                work_done_progress: None,
            },
        })),
        workspace: Some(WorkspaceServerCapabilities {
            workspace_folders: Some(WorkspaceFoldersServerCapabilities {
                supported: Some(true),
                change_notifications: Some(OneOf::Left(true)),
            }),
            file_operations: None,
        }),
        ..ServerCapabilities::default()
    }
}

#[cfg(test)]
mod tests {
    use super::server_capabilities;

    /// Golden JSON, transcribed verbatim from plan §6.1 — this is the
    /// regression test for capability drift, not just a smoke test.
    #[test]
    fn matches_section_6_1_exactly() {
        let value = serde_json::to_value(server_capabilities()).expect("capabilities serialize");
        let expected = serde_json::json!({
            "textDocumentSync": { "openClose": true, "change": 1 },
            "diagnosticProvider": {
                "identifier": "bsl",
                "interFileDependencies": true,
                "workspaceDiagnostics": true
            },
            "workspace": {
                "workspaceFolders": { "supported": true, "changeNotifications": true }
            }
        });
        assert_eq!(value, expected);
    }
}
