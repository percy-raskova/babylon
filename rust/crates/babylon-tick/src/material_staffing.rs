//! The admitted G4 workforce composition's exact graph effects.
//!
//! Staffing state is a transient projection of the supplied detached graph.
//! This module neither owns durable state nor publishes a tick. A caller must
//! discard its entire candidate if an effect or a later tick stage refuses.

mod bindings;

pub use bindings::{StaffingComposition, StaffingMemberNodeBinding, StaffingNodeBinding};

#[cfg(test)]
mod tests;

#[path = "material_staffing/composition.rs"]
mod composition;

use composition::exact_real;
#[cfg(test)]
use composition::read_stock;
pub use composition::{
    apply_material_staffing, validate_opening_labor, MaterialStaffingError, StaffingEffectContext,
    StaffingEffects, EMPLOYED_POPULATION, MAX_EXACT_STAFFING_INTEGER, PREVIOUS_UNRETAINED_HOURS,
    RESERVE_POPULATION, STAFFING_COMPOSITION_ID, STAFFING_FIELDS,
};
