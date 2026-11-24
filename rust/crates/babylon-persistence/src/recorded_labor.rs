//! Derived physical labor accounting from authenticated adjacent material registers and their receipts.
//! All post-foundation hours are exact micro-hours. Positive foundation stock retains unknown
//! prehistory as it mixes, transforms and moves. A partial withdrawal takes its floor share and
//! a complete withdrawal carries the remaining recorded balance. Wages do not determine hours.
mod attendance;
mod auxiliary;
mod book;
mod checkpoint;
mod circulation;
#[cfg(test)]
mod collection_tests;
mod household_work;
mod identities;
mod model;
mod period;
mod production;
mod services;
mod view;

pub use checkpoint::RecordedLaborCheckpoint;
pub use identities::{RecordedAsset, RecordedAssetIdentity};
pub use model::{
    LaborBasis, LaborDisposition, LaborEdge, LaborId, LaborNode, LaborReceiptFamily, ReceiptRef,
    RecordedAttendance, RecordedCompensation, RecordedHouseholdTime, RecordedLaborError,
    RecordedLaborPeriod, RecordedLaborPosition, MICROS_PER_HOUR,
};
pub use period::RecordedLaborLedger;
#[cfg(test)]
mod tests;

#[cfg(test)]
mod checkpoint_tests;
#[cfg(test)]
mod stored_form_tests;
