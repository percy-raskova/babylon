//! Separate full-observer material capability and exact historical projection.

mod storage_witness;

#[cfg(test)]
mod tests;

#[path = "observer_material/snapshot.rs"]
mod snapshot;

#[cfg(test)]
use snapshot::MaterialHistory;
use snapshot::MaterialObservationRow;
pub(crate) use snapshot::{
    committed_observation, committed_receipts, material_observation, production_history,
    read_material_header, MaterialHeader, MaterialObservation,
};
pub use snapshot::{ObserverMaterialCursor, ObserverOpeningFoundations};

#[cfg(test)]
use crate::economic_content::EconomicContentAdmission;
use crate::identity::CampaignId;
use crate::observer_reader::ObserverEconomyError;
#[cfg(test)]
use crate::production_projection::project_economic_current;
