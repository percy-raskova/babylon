//! One ordered atomic publication path; no mutable-head write remains.

#[cfg(test)]
mod selection_tests;

#[path = "publication/publish.rs"]
mod publish;

#[cfg(test)]
use publish::known_page_inputs;
#[cfg(test)]
pub(super) use publish::PreparedPublication;
pub(super) use publish::{
    authenticate_existing, next_receipt, prepare, publish, revalidate_prepared, with_campaign_lock,
};
pub(crate) use publish::{materialize, select_dirty_pages, ArchivePagePlan};

#[cfg(test)]
use crate::{ArchiveKnowledge, PendingArchiveReceipt, SemanticArchiveError};
