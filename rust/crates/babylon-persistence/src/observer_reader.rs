//! Separate read-only economic observer and per-signal granted preview capabilities.

mod counties;

mod history;

pub use crate::observer_material::{ObserverMaterialCursor, ObserverOpeningFoundations};

pub use history::{ProductionHistoryTarget, ProductionOutputPoint};

#[path = "observer_reader/observer.rs"]
mod observer;

#[allow(unused_imports)]
use observer::{
    campaign_summary, confine_authority, graph_only_observer_identity, observer_role_views,
    project_county, read_commit_identity, read_committed_counties, read_foundation,
    validate_observer_graph, AUTHORITY_SQL, CAMPAIGN_CATALOG_SQL, HELD_SQL,
    MATERIAL_READ_TRANSACTION_OPTIONS, SNAPSHOT_COLUMNS,
};
pub use observer::{
    provision_observer_role, CampaignSummary, CommittedMaterialObservation,
    CommittedMaterialReceipts, ObserverCountyEconomy, ObserverEconomyError, ObserverEconomyReader,
    ObserverEconomySnapshot, ObserverVisibility, OBSERVER_DSN_ENV, OBSERVER_ROLE_NAME,
};

#[allow(unused_imports)]
use crate::{
    economic_content::{
        validate_economic_header, EconomicAdmissionOwner, EconomicContentAdmission,
    },
    identity::CampaignId,
    michigan_content::{MichiganContentPreset, MICHIGAN_CONTENT_PRESETS},
    michigan_economy::{digest_hex, MichiganCountyEconomy},
    postgres_catalog::validate_connection_target,
};
#[allow(unused_imports)]
use babylon_kernel::content_digest::sha256_of;
#[allow(unused_imports)]
use postgres::{Config, IsolationLevel, NoTls};
#[allow(unused_imports)]
use serde::{Deserialize, Serialize};
