//! Bounded, captured organizer practices and period-specific earned knowledge.
//!
//! This module is a pure transition. Durable admission and atomic publication
//! belong to the runtime. No practice changes factory production or staffing.

mod aid;

mod collection;

mod contract;

mod nonnegative_decimal_i128;

mod time_resources;

mod transition;

pub use aid::*;

pub use collection::*;

pub use contract::*;

pub use time_resources::*;

pub use transition::*;

#[path = "organizer/types.rs"]
mod types;

pub use types::{
    OrganizerAgreement, OrganizerChoice, OrganizerCommand, OrganizerCommitment, OrganizerConfig,
    OrganizerContactProduct, OrganizerContribution, OrganizerError, OrganizerHouseholdBinding,
    OrganizerInquiry, OrganizerMaterialSupport, OrganizerObservation, OrganizerOutcome,
    OrganizerParticipant, OrganizerPartner, OrganizerPartnerPolicy, OrganizerPartnerResponse,
    OrganizerPauseReason, OrganizerPosition, OrganizerPreview, OrganizerReceipt, OrganizerRefusal,
    OrganizerReport, OrganizerStandingWork, OrganizerState, OrganizerTimeBindingMode,
    OrganizerTimeUse, OrganizerView, OrganizerWorkplaceFacts, ORGANIZER_RECENT_OBSERVATIONS,
    ORGANIZER_RECENT_RECEIPTS, ORGANIZER_SCHEMA_VERSION,
};

#[allow(unused_imports)]
use serde::{Deserialize, Serialize};
