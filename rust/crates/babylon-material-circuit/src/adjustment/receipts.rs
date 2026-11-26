//! What the rules of ADR314 did at one close.

use super::standing::StopHold;
use babylon_kernel::currency::Currency;

use crate::{
    AccountId, FinalDemandPrincipalId, GoodId, SiteId, StaffingMemberId, StaffingPoolId, UnitId,
};

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
    /// A resting price under one unit's cost was raised to it (A19).
    RestingPriceToCost(RestingPriceToCostReceipt),
    /// The restart's test of one stopped workplace, and its money when it passed (A17, A19, ADR318 L1).
    Restart(RestartReceipt),
    /// What an owner has beyond one period of its own need: the money a restart may use.
    OwnerSpare(OwnerSpareReceipt),
    /// What a goods seller offered and sold at its markets, and the plan it made for the price it posted (A1).
    GoodsOffer(GoodsOfferReceipt),
}

/// What one goods seller offered and sold of a product at its goods markets in the period that closed, when a
/// catalog that asks for the step down quotes goods before plans. A seller with no goods market has no receipt.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct GoodsOfferReceipt {
    /// The period that closed.
    pub period: u64,
    /// The seller.
    pub site_id: SiteId,
    /// Its product.
    pub good_id: GoodId,
    /// The product's unit.
    pub unit_id: UnitId,
    /// What its goods markets offered to new buyers.
    pub offered: u64,
    /// What they sold.
    pub sold: u64,
    /// What its production policy keeps as a buffer; goods beyond it that were not sold are unsold.
    pub kept: u64,
    /// What its buyers could pay for at the price it posted for the next period, beyond what they could pay
    /// for at the old one; 0 unless the price stepped down. The seller's plan adds it.
    pub planned_gain: u64,
}

/// A resting price raised to the cost of one unit.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RestingPriceToCostReceipt {
    /// The period that closed.
    pub period: u64,
    /// The seller.
    pub site_id: SiteId,
    /// The good whose price was raised.
    pub good_id: GoodId,
    /// The unit it is priced in.
    pub unit_id: UnitId,
    /// The price that stood.
    pub old: Currency,
    /// The price now: one unit's cost, rounded up to the micro-unit.
    pub raised: Currency,
}

/// What the restart's test made of a workplace that employed nobody: the bench writes 0 to 3 in this order.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RestartTest {
    /// Not tested: it works, or it has not been quiet long enough.
    NotTested,
    /// Tested and not restarted: what the buyers it turned away would pay does not cover one batch, the
    /// inputs of a batch cannot be had, or the restart would put in nothing.
    Failed,
    /// It passed, and its owner has not the spare money.
    NoBuyer,
    /// Its owner put money in.
    Restarted,
}

/// The restart's test of one workplace at one close. A workplace that was not tested has no receipt.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct RestartReceipt {
    /// The period that closed.
    pub period: u64,
    /// The workplace.
    pub site_id: SiteId,
    /// What the test made of it.
    pub test: RestartTest,
    /// Whether it passed on its sales and failed because the inputs of one batch could not be had.
    pub inputs_short: bool,
    /// The owner whose money it was tested against; `None` when it did not pass.
    pub owner: Option<AccountId>,
    /// The money the owner put in; 0 unless restarted.
    pub money: Currency,
    /// The cost of one batch.
    pub batch_cost: Currency,
    /// The units its buyers could pay for at its price and were not sold.
    pub turned: u64,
}

/// One owner's money beyond one period of its own need, at a close.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct OwnerSpareReceipt {
    /// The period that closed.
    pub period: u64,
    /// The owner.
    pub owner: AccountId,
    /// Its cash less one period of the goods and services it requires, at posted prices.
    pub spare: Currency,
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
