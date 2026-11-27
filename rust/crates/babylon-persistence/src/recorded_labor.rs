//! Derived physical labor accounting from authenticated adjacent material registers and their receipts.
//! All post-foundation hours are exact micro-hours. Positive foundation stock retains unknown
//! prehistory as it mixes, transforms and moves. A partial withdrawal takes its floor share and
//! a complete withdrawal carries the remaining recorded balance. Wages do not determine hours.
mod attendance;
mod auxiliary;
mod checkpoint;
#[cfg(test)]
mod collection_tests;
mod identities;
mod model;
mod period;
mod services;
mod view;

use model::Result;

pub use babylon_recorded_labor::{
    LaborBasis, LaborDisposition, LaborEdge, LaborId, LaborNode, LaborReceiptFamily, ReceiptRef,
    RecordedLaborError, RecordedLaborPosition, MICROS_PER_HOUR,
};
pub use checkpoint::RecordedLaborCheckpoint;
pub use identities::{RecordedAsset, RecordedAssetIdentity};
pub use model::{
    RecordedAttendance, RecordedCompensation, RecordedHouseholdTime, RecordedLaborPeriod,
};
pub use period::RecordedLaborLedger;
#[cfg(test)]
mod tests;

#[cfg(test)]
mod checkpoint_tests;
#[cfg(test)]
mod stored_form_tests;
