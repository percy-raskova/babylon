//! Separate read-only economic observer and per-signal granted preview capabilities.

mod company_decision;
mod counties;

pub use company_decision::CompanyDecisionReport;

mod history;

pub use crate::observer_material::{ObserverMaterialCursor, ObserverOpeningFoundations};

pub use history::{ProductionHistoryTarget, ProductionOutputPoint};

#[path = "observer_reader/observer.rs"]
mod observer;

pub(crate) use observer::{confine_authority, ReceiptPurpose, MATERIAL_READ_TRANSACTION_OPTIONS};
pub use observer::{
    provision_observer_role, CampaignSummary, CommittedMaterialObservation,
    CommittedMaterialReceipts, ObserverCountyEconomy, ObserverEconomyError, ObserverEconomyReader,
    ObserverEconomySnapshot, ObserverVisibility, OBSERVER_DSN_ENV, OBSERVER_ROLE_NAME,
};
use observer::{read_commit_identity, read_committed_counties, read_foundation, SNAPSHOT_COLUMNS};

use crate::economic_content::EconomicContentAdmission;
use crate::identity::CampaignId;
