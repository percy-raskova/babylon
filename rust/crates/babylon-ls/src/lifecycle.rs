//! The `initialize` -> `initialized` -> (`didOpen`/`didChange`/`didClose`)*
//! -> `shutdown` -> `exit` lifecycle (Task 5.3) — the ONE dispatch loop
//! `main.rs`'s stdio wire-up calls, and the same function
//! `tests/protocol.rs` drives through the real binary and this module's
//! own unit tests drive through [`lsp_server::Connection::memory`].
//!
//! **Observes-only (global constraint 1).** Nothing in this loop writes
//! content or gates a load — the load path (`babylon-bsl`/`babylon-tick`)
//! stays the only door. This module's whole job through Task 5 is
//! protocol plumbing: the diagnostics that will eventually flow through
//! [`crate::document_store::DocumentStore`] are Task 6's.
//!
//! **No panic-catching (global constraint 8).** A panic in a handler here
//! is a bug; this module never wraps dispatch in `catch_unwind` — the
//! server logs and dies, and the client restarts it.

use lsp_server::{
    Connection, ErrorCode, Message, Notification as RawNotification, Request as RawRequest,
    RequestId, Response,
};
use lsp_types::notification::{
    DidChangeTextDocument, DidChangeWatchedFiles, DidCloseTextDocument, DidOpenTextDocument, Exit,
    LogMessage, Notification as _,
};
use lsp_types::request::{RegisterCapability, Request as _};
use lsp_types::{
    ClientCapabilities, DidChangeTextDocumentParams, DidChangeWatchedFilesRegistrationOptions,
    DidCloseTextDocumentParams, DidOpenTextDocumentParams, FileSystemWatcher, GlobPattern,
    InitializeParams, LogMessageParams, MessageType, Registration, RegistrationParams,
};

use crate::capabilities::server_capabilities;
use crate::document_store::DocumentStore;

/// Exit code for a clean `shutdown` -> `exit` sequence (the LSP spec:
/// "exit should exit... with success code 0 if... shutdown request was
/// received before").
const EXIT_CLEAN: i32 = 0;

/// Exit code for `exit` arriving without a preceding `shutdown`, or for
/// the connection dropping before either — the spec's own "non-zero
/// (i.e. error) exit code" for the improper sequence.
const EXIT_UNCLEAN: i32 = 1;

/// The fixed registration id this crate's ONE outbound
/// `client/registerCapability` request uses — a constant, not a generated
/// id, because Task 5 sends exactly one such request per server lifetime.
const WATCHED_FILES_REGISTRATION_ID: &str = "babylon-ls/watched-files";

/// Runs the full server lifecycle over `connection` end to end and returns
/// the process exit code. `main.rs` is the only production caller; this
/// crate's own tests call it directly against
/// [`lsp_server::Connection::memory`], and `tests/protocol.rs` calls it
/// indirectly by spawning the real binary.
#[must_use]
pub fn serve(connection: &Connection) -> i32 {
    let (initialize_id, initialize_params) = match connection.initialize_start() {
        Ok(pair) => pair,
        Err(err) => {
            eprintln!("babylon-ls: initialize handshake failed: {err}");
            return EXIT_UNCLEAN;
        }
    };

    let client_capabilities = match serde_json::from_value::<InitializeParams>(initialize_params) {
        Ok(params) => params.capabilities,
        Err(err) => {
            eprintln!("babylon-ls: malformed InitializeParams: {err}");
            return EXIT_UNCLEAN;
        }
    };

    let result = serde_json::json!({ "capabilities": server_capabilities() });
    if let Err(err) = connection.initialize_finish(initialize_id, result) {
        eprintln!("babylon-ls: initialize handshake failed: {err}");
        return EXIT_UNCLEAN;
    }

    announce_watched_files(connection, &client_capabilities);

    let mut store = DocumentStore::default();
    main_loop(connection, &mut store)
}

/// What `initialized` does about `workspace/didChangeWatchedFiles` (§6.1):
/// dynamic registration when the client supports it, a loud
/// `window/logMessage` warning when it doesn't — never a silent fallback
/// to "just don't watch."
enum WatchAction {
    Register(RegistrationParams),
    Degrade(LogMessageParams),
}

fn watch_action_for(client_capabilities: &ClientCapabilities) -> WatchAction {
    let supports_dynamic = client_capabilities
        .workspace
        .as_ref()
        .and_then(|workspace| workspace.did_change_watched_files.as_ref())
        .and_then(|caps| caps.dynamic_registration)
        .unwrap_or(false);

    if supports_dynamic {
        WatchAction::Register(watched_files_registration())
    } else {
        WatchAction::Degrade(LogMessageParams {
            typ: MessageType::WARNING,
            message: "babylon-ls: client does not support dynamic \
                workspace/didChangeWatchedFiles registration; on-disk edits \
                outside open documents are picked up only at pull time \
                (workspace/diagnostic), never pushed automatically"
                .to_owned(),
        })
    }
}

/// The `RegistrationParams` for `**/*.{bsl,bscn}` and
/// `**/content-sets.toml` (§6.1) — "the spec's own argument against
/// rolling our own watcher".
fn watched_files_registration() -> RegistrationParams {
    let watchers = vec![
        FileSystemWatcher {
            glob_pattern: GlobPattern::String("**/*.{bsl,bscn}".to_owned()),
            kind: None,
        },
        FileSystemWatcher {
            glob_pattern: GlobPattern::String("**/content-sets.toml".to_owned()),
            kind: None,
        },
    ];
    let options = DidChangeWatchedFilesRegistrationOptions { watchers };
    RegistrationParams {
        registrations: vec![Registration {
            id: WATCHED_FILES_REGISTRATION_ID.to_owned(),
            method: DidChangeWatchedFiles::METHOD.to_owned(),
            register_options: Some(
                serde_json::to_value(options).expect(
                    "babylon-ls: DidChangeWatchedFilesRegistrationOptions always serializes",
                ),
            ),
        }],
    }
}

fn announce_watched_files(connection: &Connection, client_capabilities: &ClientCapabilities) {
    match watch_action_for(client_capabilities) {
        WatchAction::Register(params) => {
            let request = RawRequest::new(
                RequestId::from(WATCHED_FILES_REGISTRATION_ID.to_owned()),
                RegisterCapability::METHOD.to_owned(),
                params,
            );
            // Best-effort: a send failure means the client pipe is already
            // gone, which the main loop's own channel-disconnect exit path
            // handles.
            let _ = connection.sender.send(request.into());
        }
        WatchAction::Degrade(log_params) => {
            let note = RawNotification::new(LogMessage::METHOD.to_owned(), log_params);
            let _ = connection.sender.send(note.into());
        }
    }
}

fn main_loop(connection: &Connection, store: &mut DocumentStore) -> i32 {
    for msg in &connection.receiver {
        match msg {
            Message::Request(req) => {
                if let Some(exit_code) = handle_request(connection, &req) {
                    return exit_code;
                }
            }
            Message::Notification(note) => {
                if note.method.as_str() == Exit::METHOD {
                    // `exit` without a preceding `shutdown`: the spec
                    // mandates a non-zero exit code here.
                    return EXIT_UNCLEAN;
                }
                dispatch_notification(store, &note);
            }
            Message::Response(_) => {
                // The only outbound request this crate sends
                // (`announce_watched_files`) has no follow-up action on
                // its result.
            }
        }
    }
    // The channel disconnected (the client closed the pipe) without a
    // clean shutdown/exit sequence — the same "no clean shutdown" exit
    // code as the bare-`exit` branch above.
    EXIT_UNCLEAN
}

/// Handles one request. Returns `Some(exit_code)` when the request ends
/// the server's lifecycle (`shutdown`), `None` otherwise.
fn handle_request(connection: &Connection, req: &RawRequest) -> Option<i32> {
    match connection.handle_shutdown(req) {
        Ok(true) => Some(EXIT_CLEAN),
        Ok(false) => {
            // Task 5 advertises no request-shaped capability besides
            // `initialize`/`shutdown` (both handled by `lsp-server`
            // itself); anything else is unimplemented today.
            let resp = Response::new_err(
                req.id.clone(),
                ErrorCode::MethodNotFound as i32,
                format!("babylon-ls: unhandled request method {}", req.method),
            );
            let _ = connection.sender.send(resp.into());
            None
        }
        Err(err) => {
            eprintln!("babylon-ls: shutdown handshake failed: {err}");
            Some(EXIT_UNCLEAN)
        }
    }
}

fn dispatch_notification(store: &mut DocumentStore, note: &RawNotification) {
    match note.method.as_str() {
        m if m == DidOpenTextDocument::METHOD => apply_did_open(store, note),
        m if m == DidChangeTextDocument::METHOD => apply_did_change(store, note),
        m if m == DidCloseTextDocument::METHOD => apply_did_close(store, note),
        _ => {} // Unhandled notifications are ignored per the LSP spec's own tolerance.
    }
}

fn apply_did_open(store: &mut DocumentStore, note: &RawNotification) {
    match serde_json::from_value::<DidOpenTextDocumentParams>(note.params.clone()) {
        Ok(params) => store.open(
            params.text_document.uri,
            params.text_document.version,
            params.text_document.text,
        ),
        Err(err) => eprintln!("babylon-ls: malformed didOpen params: {err}"),
    }
}

fn apply_did_change(store: &mut DocumentStore, note: &RawNotification) {
    match serde_json::from_value::<DidChangeTextDocumentParams>(note.params.clone()) {
        Ok(mut params) => {
            // Full sync (§6.1): exactly one change event holding the
            // whole document text, never a range-based delta.
            if let Some(change) = params.content_changes.pop() {
                let known = store.change_full(
                    &params.text_document.uri,
                    params.text_document.version,
                    change.text,
                );
                if !known {
                    eprintln!(
                        "babylon-ls: didChange for a document never opened: {}",
                        params.text_document.uri
                    );
                }
            }
        }
        Err(err) => eprintln!("babylon-ls: malformed didChange params: {err}"),
    }
}

fn apply_did_close(store: &mut DocumentStore, note: &RawNotification) {
    match serde_json::from_value::<DidCloseTextDocumentParams>(note.params.clone()) {
        Ok(params) => {
            let _ = store.close(&params.text_document.uri);
        }
        Err(err) => eprintln!("babylon-ls: malformed didClose params: {err}"),
    }
}

#[cfg(test)]
mod tests {
    use super::{EXIT_CLEAN, EXIT_UNCLEAN};
    use lsp_server::{
        Connection, ErrorCode, Message, Notification as RawNotification, Request as RawRequest,
        RequestId,
    };
    use lsp_types::notification::{Exit, Initialized, LogMessage, Notification as _};
    use lsp_types::request::{Initialize, RegisterCapability, Request as _, Shutdown};
    use lsp_types::{
        ClientCapabilities, DidChangeWatchedFilesClientCapabilities, InitializeParams,
        InitializedParams, WorkspaceClientCapabilities,
    };
    use std::thread;
    use std::time::Duration;

    const TIMEOUT: Duration = Duration::from_secs(5);

    fn init_params(dynamic_watch: Option<bool>) -> InitializeParams {
        let mut capabilities = ClientCapabilities::default();
        if let Some(dynamic) = dynamic_watch {
            capabilities.workspace = Some(WorkspaceClientCapabilities {
                did_change_watched_files: Some(DidChangeWatchedFilesClientCapabilities {
                    dynamic_registration: Some(dynamic),
                    relative_pattern_support: None,
                }),
                ..Default::default()
            });
        }
        InitializeParams {
            capabilities,
            ..Default::default()
        }
    }

    /// Drives `initialize` -> `initialized` and, when `dynamic_watch` is
    /// `false`/`None`, drains the resulting `window/logMessage`
    /// degradation warning. Returns the message that follows `initialized`
    /// so a test can assert on it (the `client/registerCapability`
    /// request when `dynamic_watch` is `Some(true)`).
    fn handshake(client: &Connection, dynamic_watch: Option<bool>) -> Message {
        client
            .sender
            .send(
                RawRequest::new(
                    RequestId::from(1),
                    Initialize::METHOD.to_owned(),
                    init_params(dynamic_watch),
                )
                .into(),
            )
            .expect("send initialize");
        client
            .receiver
            .recv_timeout(TIMEOUT)
            .expect("initialize response");

        client
            .sender
            .send(RawNotification::new(Initialized::METHOD.to_owned(), InitializedParams {}).into())
            .expect("send initialized");

        client
            .receiver
            .recv_timeout(TIMEOUT)
            .expect("post-initialized message")
    }

    fn clean_shutdown(client: &Connection) {
        client
            .sender
            .send(RawRequest::new(RequestId::from(2), Shutdown::METHOD.to_owned(), ()).into())
            .expect("send shutdown");
        client
            .receiver
            .recv_timeout(TIMEOUT)
            .expect("shutdown response");
        client
            .sender
            .send(RawNotification::new(Exit::METHOD.to_owned(), ()).into())
            .expect("send exit");
    }

    #[test]
    fn full_lifecycle_clean_shutdown_exits_zero() {
        let (server, client) = Connection::memory();
        let handle = thread::spawn(move || super::serve(&server));

        let degrade = handshake(&client, None);
        assert!(matches!(degrade, Message::Notification(n) if n.method == LogMessage::METHOD));

        clean_shutdown(&client);

        assert_eq!(handle.join().expect("serve thread"), EXIT_CLEAN);
    }

    #[test]
    fn exit_without_shutdown_exits_uncleanly() {
        let (server, client) = Connection::memory();
        let handle = thread::spawn(move || super::serve(&server));

        handshake(&client, None);
        client
            .sender
            .send(RawNotification::new(Exit::METHOD.to_owned(), ()).into())
            .expect("send exit");

        assert_eq!(handle.join().expect("serve thread"), EXIT_UNCLEAN);
    }

    #[test]
    fn dynamic_registration_true_sends_register_capability_request() {
        let (server, client) = Connection::memory();
        let handle = thread::spawn(move || super::serve(&server));

        let registration = handshake(&client, Some(true));
        match registration {
            Message::Request(req) => assert_eq!(req.method, RegisterCapability::METHOD),
            other => panic!("expected client/registerCapability request, got {other:?}"),
        }

        clean_shutdown(&client);
        assert_eq!(handle.join().expect("serve thread"), EXIT_CLEAN);
    }

    #[test]
    fn dynamic_registration_false_degrades_loudly() {
        let (server, client) = Connection::memory();
        let handle = thread::spawn(move || super::serve(&server));

        let degrade = handshake(&client, Some(false));
        match degrade {
            Message::Notification(n) => assert_eq!(n.method, LogMessage::METHOD),
            other => panic!("expected window/logMessage, got {other:?}"),
        }

        clean_shutdown(&client);
        assert_eq!(handle.join().expect("serve thread"), EXIT_CLEAN);
    }

    #[test]
    fn request_before_initialize_gets_server_not_initialized() {
        let (server, client) = Connection::memory();
        let handle = thread::spawn(move || super::serve(&server));

        client
            .sender
            .send(RawRequest::new(RequestId::from(99), Shutdown::METHOD.to_owned(), ()).into())
            .expect("send premature shutdown");
        let msg = client
            .receiver
            .recv_timeout(TIMEOUT)
            .expect("error response");
        match msg {
            Message::Response(resp) => {
                let err = resp
                    .response_result
                    .expect_err("expected an error response before initialize");
                assert_eq!(err.code, ErrorCode::ServerNotInitialized as i32);
            }
            other => panic!("expected an error Response, got {other:?}"),
        }

        // `initialize_start` keeps looping past the rejected request —
        // walk it through a real handshake so the spawned thread
        // terminates cleanly.
        handshake(&client, None);
        clean_shutdown(&client);
        assert_eq!(handle.join().expect("serve thread"), EXIT_CLEAN);
    }
}
