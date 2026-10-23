//! Complete typed known-only rendering witness. Markdown is never its authority.

#[cfg(test)]
mod tests;

#[path = "emission/manifest.rs"]
mod manifest;

#[allow(unused_imports)]
pub(crate) use manifest::{ArchiveEmissionLink, ArchiveEmissionManifest};
#[allow(unused_imports)]
use manifest::{LinkWire, ManifestWire, SignalWire, MAX_EMISSION_BYTES};

#[allow(unused_imports)]
use crate::archive::{decode_subject_kind, validate_text, MAX_LINKS, MAX_PAGE_BYTES, MAX_SIGNALS};
#[allow(unused_imports)]
use crate::{
    ArchiveCitation, ArchiveLink, ArchivePageInput, ArchivePageRef, ArchiveSignal, ArchiveSubject,
    SemanticArchiveError,
};
#[allow(unused_imports)]
use serde::{Deserialize, Serialize};
#[allow(unused_imports)]
use std::collections::BTreeSet;
