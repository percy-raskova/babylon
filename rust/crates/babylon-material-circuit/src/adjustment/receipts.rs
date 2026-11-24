//! What the rules of ADR314 did at one close.

use super::standing::StopHold;
use babylon_kernel::currency::Currency;

use crate::{FinalDemandPrincipalId, GoodId, SiteId, StaffingMemberId, StaffingPoolId, UnitId};

/// What the rules of ADR314 did at one close, in the order they acted.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum AdjustmentReceipt {
    /// What a workplace may ask of people for the next period, and what set the cut (A6, the bound on hiring).
    HiringBound(HiringBoundReceipt),
    /// Persons moved from one workplace's people looking for work to another that needed hands (A14).
    PlaceMove(PlaceMoveReceipt),
    /// What the stop rule decided of one workplace at the close (A17).
    Stop(StopReceipt),
    /// A workplace that employed nobody and offered nothing held a price at this close (A17, A19).
    RestingPrice(RestingPriceReceipt),
}

/// One price held at a close because its seller employed nobody and offered nothing.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RestingPriceReceipt {
    /// The period that closed: the one in which the seller employed nobody and offered nothing.
    pub period: u64,
    /// The seller.
    pub site_id: SiteId,
    /// Its product.
    pub good_id: GoodId,
    /// The product's unit.
    pub unit_id: UnitId,
    /// The posted price, which stays.
    pub price: Currency,
}

/// One workplace's test of the stop rule at one close: whether it could not pay, whether it is held back after
/// it, and how many persons it may employ.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct StopReceipt {
    /// The period that closed: the one whose attendance was tested.
    pub period: u64,
    /// The workplace.
    pub site_id: SiteId,
    /// Whether some of its people's hours were not paid this period.
    pub could_not_pay: bool,
    /// Whether it is held back after this close.
    pub hold: StopHold,
    /// The most persons it may employ after this close; `None` when not limited.
    pub limit: Option<u64>,
}

/// Persons of one household who left the people looking for work at one workplace of their place and were
/// taken on at another.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PlaceMoveReceipt {
    /// The period whose staffing moved them.
    pub period: u64,
    /// The pool that took them on.
    pub host_pool: StaffingPoolId,
    /// The host's member of their household.
    pub host_member: StaffingMemberId,
    /// The pool they left.
    pub from_pool: StaffingPoolId,
    /// The member of their household they left.
    pub from_member: StaffingMemberId,
    /// Their household.
    pub household_id: FinalDemandPrincipalId,
    /// How many persons.
    pub persons: u64,
    /// `None`: no record of layoffs covered them. `Some(age)`: from the cohort laid off `age` periods before.
    pub covered_age: Option<u8>,
}

/// One workplace's bound on hiring at one close: the hours its plan asked of people for the next period and the
/// hours it can work.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HiringBoundReceipt {
    /// The period whose hours the bound cuts: the one that opens after the close.
    pub period: u64,
    /// The workplace.
    pub site_id: SiteId,
    /// Its labor unit.
    pub unit_id: UnitId,
    /// The hours asked before the bound: batches' labor, handling and other work.
    pub asked_hours: u64,
    /// The hours it can work: what was asked less what the bound cut.
    pub bound_hours: u64,
    /// What set the cut; `None` where nothing was cut.
    pub limit: HiringLimit,
}

/// What set a cut: the bench writes 0 to 4 in this order.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum HiringLimit {
    /// The request is within every limit.
    None,
    /// The batches its capacity can run.
    Capacity,
    /// The batches its inputs can feed, or what there is to handle.
    Inputs,
    /// The hours and inputs its money can pay for.
    Money,
    /// The hours asked were not a whole number of batches, or another rule's limit cut them.
    Other,
}
