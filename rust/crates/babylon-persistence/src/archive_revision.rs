//! Immutable Archive publications and exact scoped dossier observations.

mod body_encoding;

mod changes;

pub(crate) mod emission;

mod knowledge;

pub(crate) mod publication;

mod read;

mod read_history;

mod record;

mod storage;

mod tick_knowledge;

pub(crate) mod worker;

#[path = "archive_revision/dossier.rs"]
mod dossier;

pub use dossier::{
    ArchiveAtomChange, ArchiveChangeCursor, ArchiveChangePage, ArchiveDossierBounds,
    ArchiveDossierLink, ArchiveDossierPage, ArchiveDossierPending, ArchiveDossierRead,
    ArchiveDossierState, ArchiveDossierUnavailable, ArchiveLinkedPageState, ArchiveReadScope,
    ArchiveSearchHit, ArchiveSearchRead, ArchiveSearchState,
};
