//! Checked immutable publication payload with its required emission witness.

#[cfg(test)]
mod tests;

#[path = "record/revision.rs"]
mod revision;

#[allow(unused_imports)]
use revision::hash_text;
#[allow(unused_imports)]
pub(super) use revision::{
    is_link, parse_page_key, CheckedRevision, GrantDependency, RevisionRecord, REVISION_DOMAIN,
};

#[allow(unused_imports)]
use super::emission::ArchiveEmissionManifest;
#[allow(unused_imports)]
use super::ArchiveReadScope;
#[allow(unused_imports)]
use crate::archive::{validate_text, MAX_LINKS, MAX_PAGE_BYTES, MAX_SIGNALS};
#[allow(unused_imports)]
use crate::{
    ArchiveAtom, ArchiveAtomSubject, ArchiveCitation, ArchivePageRef, SemanticArchiveError,
};
#[allow(unused_imports)]
use sha2::{Digest as _, Sha256};
#[allow(unused_imports)]
use std::collections::BTreeSet;
