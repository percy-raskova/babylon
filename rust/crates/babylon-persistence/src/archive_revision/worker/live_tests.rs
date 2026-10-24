//! Live Archive worker proofs against the task-owned disposable `PostgreSQL` runtime.
//!
//! Each test clones the validated current runtime template, commits real
//! ticks through `DurableMaterialRuntime`, and then proves one worker
//! acceptance property against the committed dirty receipts.

#[path = "../../../tests/support/current_material.rs"]
mod current_material;

#[path = "live_tests/checkpoint_membership.rs"]
mod checkpoint_membership;

#[path = "live_tests/short_publication.rs"]
mod short_publication;

#[path = "live_tests/provenance.rs"]
mod provenance;

#[path = "live_tests/packed_membership.rs"]
mod packed_membership;

#[path = "live_tests/bounds.rs"]
mod bounds;

#[path = "../../../tests/support/archive_reader.rs"]
mod archive_reader;

#[path = "live_tests/organizer_capture.rs"]
mod organizer_capture;

#[path = "live_tests/revisions.rs"]
mod revisions;

#[path = "live_tests/wakeup.rs"]
mod wakeup;

#[path = "live_tests/support.rs"]
mod support;

use support::StubPageProducer;

use crate::archive_revision::ArchiveReadScope;
use crate::identity::CampaignId;
use crate::{install_reader_role, SemanticArchiveReader};
use crate::{material_runtime, michigan_content, michigan_material};
use archive_reader::scope_at;
