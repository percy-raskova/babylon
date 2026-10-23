//! Separate read-only economic observer and per-signal granted preview capabilities.

mod counties;

mod history;

pub use crate::observer_material::{ObserverMaterialCursor, ObserverOpeningFoundations};

pub use history::{ProductionHistoryTarget, ProductionOutputPoint};

#[path = "observer_reader/observer.rs"]
mod observer;

use observer::{
    confine_authority, read_commit_identity, read_committed_counties, read_foundation,
    MATERIAL_READ_TRANSACTION_OPTIONS, SNAPSHOT_COLUMNS,
};
pub use observer::{
    provision_observer_role, CampaignSummary, CommittedMaterialObservation,
    CommittedMaterialReceipts, ObserverCountyEconomy, ObserverEconomyError, ObserverEconomyReader,
    ObserverEconomySnapshot, ObserverVisibility, OBSERVER_DSN_ENV, OBSERVER_ROLE_NAME,
};

use crate::economic_content::EconomicContentAdmission;
use crate::identity::CampaignId;
