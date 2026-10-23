//! Separate full-observer material capability and exact historical projection.

mod storage_witness;

#[cfg(test)]
mod tests;

#[path = "observer_material/snapshot.rs"]
mod snapshot;

#[allow(unused_imports)]
use snapshot::{
    attribute_production, authenticated_history_endpoints, authenticated_staffing,
    decode_material_row, extend_history, history_for_read, material_rows,
    project_authenticated_staffing, read_committed_receipts, MaterialHistory,
    MaterialObservationRow, MaterialRegisterBoundary, MATERIAL_PAGE_ROWS,
};
#[allow(unused_imports)]
pub(crate) use snapshot::{
    committed_observation, committed_receipts, material_observation, production_history,
    read_material_header, MaterialHeader, MaterialObservation,
};
pub use snapshot::{ObserverMaterialCursor, ObserverOpeningFoundations};

#[allow(unused_imports)]
use crate::production_projection::diagnostics::{self, Stage};
#[allow(unused_imports)]
use crate::{
    economic_content::{validate_economic_header, EconomicContentAdmission},
    identity::CampaignId,
    material_runtime::{
        capture_material_foundation_components, read_observer_material_endpoints,
        read_observer_material_tick, FoundationReadSource, ObserverEndpointLookup,
    },
    michigan_economy::digest_hex,
    observer_reader::{
        ObserverEconomyError, ObserverVisibility, ProductionHistoryTarget, ProductionOutputPoint,
    },
    production_observation::ProductionSnapshot,
    production_projection::{
        history::OrderHistory,
        metadata::Metadata,
        project_economic_current,
        sites::{project_process, Quantities},
    },
};
#[allow(unused_imports)]
use babylon_kernel::content_digest::sha256_of;
#[allow(unused_imports)]
use babylon_tick::{
    material_replay::IdentifiedMaterialTick,
    material_world::{nominal_material_world_hash, MaterialTickReceipts, MaterialWorldRegister},
};
#[allow(unused_imports)]
use postgres::GenericClient;
#[allow(unused_imports)]
use std::sync::{Arc, Weak};
