//! Checked immutable publication payload with its required emission witness.

#[cfg(test)]
mod tests;

#[path = "record/revision.rs"]
mod revision;

pub(super) use revision::{
    is_link, parse_page_key, CheckedRevision, GrantDependency, RevisionRecord,
};

#[cfg(test)]
use super::emission::ArchiveEmissionManifest;
#[cfg(test)]
use super::ArchiveReadScope;
#[cfg(test)]
use crate::{
    ArchiveAtom, ArchiveAtomSubject, ArchiveCitation, ArchivePageRef, SemanticArchiveError,
};
#[cfg(test)]
use sha2::{Digest as _, Sha256};
