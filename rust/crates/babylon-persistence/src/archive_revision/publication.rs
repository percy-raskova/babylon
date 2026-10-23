//! One ordered atomic publication path; no mutable-head write remains.

#[cfg(test)]
mod selection_tests;

#[path = "publication/publish.rs"]
mod publish;

#[allow(unused_imports)]
pub(super) use publish::{
    authenticate_existing, next_receipt, prepare, publish, revalidate_prepared, with_campaign_lock,
    PreparedPublication,
};
#[allow(unused_imports)]
use publish::{
    claim, known_page_inputs, prepare_page, reconcile, validate_receipt, validate_receipt_identity,
};
#[allow(unused_imports)]
pub(crate) use publish::{materialize, select_dirty_pages, ArchivePagePlan};

#[allow(unused_imports)]
use super::{
    knowledge,
    record::{is_link, parse_page_key, CheckedRevision, GrantDependency, RevisionRecord},
    storage, tick_knowledge, ArchiveReadScope,
};
#[allow(unused_imports)]
use crate::archive::{database, decode, decode_digest, mint_page_atoms, persist_atom_rows};
#[allow(unused_imports)]
use crate::production_projection::diagnostics::{Stage, Timing};
#[allow(unused_imports)]
use crate::{
    identity::CampaignId, ArchiveDirtyBatch, ArchiveKnowledge, ArchiveMaterializeDisposition,
    ArchiveMaterializeMode, ArchiveMaterializeReport, ArchivePageInput, FogSafeArchiveRenderer,
    MaterializedArchivePage, PendingArchiveReceipt, RenderedArchivePage, SemanticArchiveError,
    SemanticArchiveStore,
};
#[allow(unused_imports)]
use postgres::{Client, GenericClient, IsolationLevel};
#[allow(unused_imports)]
use sha2::{Digest as _, Sha256};
