//! County Review values: the configuration, the roster and the engine's facts.
use std::fmt::{Display, Formatter, Result as FormatResult};

use serde::{Deserialize, Serialize};

/// Current wire schema.
pub const COUNTY_REVIEW_SCHEMA_VERSION: u32 = 1;
/// Largest number of groups, crews or roster rows.
pub const COUNTY_REVIEW_MAX_ROWS: usize = 65_536;

/// A refusal of the County Review kernel.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CountyReviewError {
    /// The wire schema is not the current one.
    UnsupportedSchema,
    /// A configured price, wage or session length is zero.
    InvalidTerms,
    /// Groups are not sorted by identifier and unique.
    GroupsNotCanonical,
    /// Crews are not sorted by identifier and unique.
    CrewsNotCanonical,
    /// A crew names a group the configuration does not hold.
    UnknownGroup,
    /// A crew index is outside the configuration.
    UnknownCrew,
    /// An opening names one crew twice.
    DuplicateCrew,
    /// A crew belongs to a collective residence, which has no households.
    CrewInCollectiveResidence,
    /// A collective residence holds households.
    CollectiveResidenceWithHouseholds,
    /// A split asks for more than the weights hold.
    SplitExceedsWeights,
    /// A group has more crews with people than households.
    MoreCrewsThanHouseholds,
    /// The units placed in a group differ from its roll.
    RollMismatch,
    /// The owners have too few households with nobody in the labor force for the top 1%.
    TopBandInLaborForce,
    /// The other households have too few in the labor force for the next 40%.
    WageBandOutsideLaborForce,
    /// An opening reach cannot be placed on the group's households.
    OpeningReachNotPlaceable,
    /// The roster's group list does not match the configuration.
    RosterShape,
    /// Roster rows are not sorted by key and unique.
    RosterNotCanonical,
    /// A roster row holds no household.
    EmptyRosterRow,
    /// A roster row has more reached households than households.
    ReachedExceedsHouseholds,
    /// A household with no crew has people in the labor force.
    CrewlessRowInLaborForce,
    /// A top 1% household has a crew.
    TopBandWithCrew,
    /// A row's crew does not belong to its group.
    CrewGroupMismatch,
    /// A group's rows do not sum to its households.
    GroupHouseholdsMismatch,
    /// The roster does not follow the engine's sums.
    RosterEngineMismatch,
    /// The facts do not hold one entry for every configured crew and group, in order.
    FactsShape,
    /// A group lost more households than the ones with nobody in the labor force.
    HouseholdsBelowLaborHouseholds,
    /// An exact sum or product left its range.
    Arithmetic,
    /// A value could not be written or read as canonical JSON.
    Codec,
    /// A value exceeds its size bound.
    SizeLimit,
    /// Bytes decode but are not the canonical encoding.
    NonCanonical,
}
impl Display for CountyReviewError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "County Review: {self:?}")
    }
}
impl std::error::Error for CountyReviewError {}

/// How a crew's people are paid at their workplace.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum PayMode {
    /// A wage.
    Wage,
    /// A working owner, paid no wage.
    WorkingOwner,
    /// An unpaid family worker.
    UnpaidFamily,
}

/// Whether a group has households.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum GroupKind {
    /// A budget group with households.
    Ordinary,
    /// Persons and no households; outside the review.
    CollectiveResidence,
}

/// A household's band in the rule of thirds at the opening. Declared lowest first: an exact tie
/// falls on the lower band.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Band {
    /// The bottom 50%.
    Bottom50,
    /// The next 40%.
    Next40,
    /// The next 9%.
    Next9,
    /// The top 1%.
    Top1,
}

/// A position. `group` and `crew` index the config's tables. Rows sort by the fields in this
/// order.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PositionKey {
    /// Index of the budget group.
    pub group: u32,
    /// The band at the opening.
    pub band: Band,
    /// Index of the crew, or none when nobody is in the labor force.
    pub crew: Option<u32>,
    /// People at work now.
    pub at_work: u16,
    /// People looking for work now.
    pub seeking: u16,
    /// Units the household holds.
    pub units: u16,
}

/// Who works in one band: county totals worked out from the roster.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BandCount {
    /// The band.
    pub band: Band,
    /// Households in the band.
    pub households: u64,
    /// Households with someone at work.
    pub with_work: u64,
    /// Households with nobody at work and someone looking.
    pub seeking_only: u64,
    /// Households with nobody in the labor force.
    pub outside_labor_force: u64,
    /// People at work, summed over households.
    pub people_at_work: u64,
    /// People looking for work, summed over households.
    pub people_seeking: u64,
    /// Units, summed over households.
    pub units: u64,
}

/// One budget group of the county.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CountyReviewGroup {
    /// The engine's group identifier.
    pub group_id: [u8; 32],
    /// The name shown to the player.
    pub label: String,
    /// Whether the group has households.
    pub kind: GroupKind,
    /// Households at the opening.
    pub opening_households: u64,
    /// Units on the roll at the opening.
    pub roll_units: u64,
    /// Whether the group draws income from a share of a business.
    pub has_ownership_income: bool,
    /// Whether the group receives mutual aid.
    pub receives_mutual_aid: bool,
}

/// One budget group's people at one workplace, paid one way.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CountyReviewCrew {
    /// The engine's staffing member identifier.
    pub crew_id: [u8; 32],
    /// Index of the crew's group.
    pub group: u32,
    /// The workplace's site.
    pub site_id: [u8; 32],
    /// The labor unit.
    pub unit_id: [u8; 32],
    /// The workplace's name shown to the player.
    pub workplace_label: String,
    /// How the crew is paid.
    pub pay_mode: PayMode,
}

/// The county's captured configuration.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CountyReviewConfig {
    /// Wire schema.
    pub schema_version: u32,
    /// The campaign.
    pub campaign_id: [u8; 16],
    /// The organizer's actor.
    pub actor_id: u64,
    /// The authority the practice runs under.
    pub authority_id: [u8; 16],
    /// The county's FIPS code.
    pub county: [u8; 5],
    /// The administration's name.
    pub administration_label: String,
    /// The Claimants' Assembly's name.
    pub claimants_body_label: String,
    /// The aid partners' name.
    pub aid_body_label: String,
    /// The county's account.
    pub public_account_id: [u8; 32],
    /// One unit of relief, in millionths of a dollar.
    #[serde(with = "super::decimal")]
    pub unit_price_micros: i128,
    /// The going hourly wage, in millionths of a dollar.
    #[serde(with = "super::decimal")]
    pub going_wage_micros: i128,
    /// Hours a session takes.
    pub session_hours: u64,
    /// Hours bringing a household takes.
    pub bring_hours: u64,
    /// The first period with a session.
    pub first_session_period: u64,
    /// Groups, sorted by identifier and unique.
    pub groups: Vec<CountyReviewGroup>,
    /// Crews, sorted by identifier and unique.
    pub crews: Vec<CountyReviewCrew>,
    /// Digest of the content the configuration was built from.
    pub content_digest: [u8; 32],
    /// Digest of the policy source.
    pub policy_source_digest: [u8; 32],
}

/// A row of the roster: households at one position and how many are reached.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RosterRow {
    /// The position.
    pub key: PositionKey,
    /// Households there.
    pub households: u64,
    /// Of those, the households reached.
    pub reached: u64,
}

/// A group's households and the units that left with households. One per config group, in order.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RosterGroup {
    /// Households the roster holds.
    pub households: u64,
    /// Units that left with a household and are held by nobody.
    pub departed_units: u64,
}

/// The table of positions. Rows are sorted by key, unique, and hold households.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Roster {
    /// The period the roster stands for.
    pub period: u64,
    /// One entry per config group, in the config's order.
    pub groups: Vec<RosterGroup>,
    /// The positions.
    pub rows: Vec<RosterRow>,
}

/// What the engine reports for one crew in one period.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CrewPeriodFacts {
    /// Index of the crew.
    pub crew: u32,
    /// Wages accrued to the crew in the period just closed.
    #[serde(with = "super::decimal")]
    pub accrued_wages_micros: i128,
    /// People at work before the period's changes.
    pub opening_at_work: u64,
    /// People looking for work before the period's changes.
    pub opening_seeking: u64,
    /// People at work who left the labor force.
    pub left_at_work: u64,
    /// People looking for work who left the labor force.
    pub left_seeking: u64,
    /// People hired.
    pub hires: u64,
    /// People laid off.
    pub separations: u64,
    /// People at work after the changes.
    pub closing_at_work: u64,
    /// People looking for work after the changes.
    pub closing_seeking: u64,
}

/// What the engine reports for one group in one period.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GroupPeriodFacts {
    /// Index of the group.
    pub group: u32,
    /// Wages taxed in the period.
    #[serde(with = "super::decimal")]
    pub taxed_wages_micros: i128,
    /// Wage tax the county collected from the group.
    #[serde(with = "super::decimal")]
    pub wage_tax_collected_micros: i128,
    /// Income from ownership.
    #[serde(with = "super::decimal")]
    pub ownership_income_micros: i128,
    /// Income from county support.
    #[serde(with = "super::decimal")]
    pub support_income_micros: i128,
    /// Income from mutual aid.
    #[serde(with = "super::decimal")]
    pub aid_income_micros: i128,
    /// Hours the group's households have free.
    pub free_hours: u64,
    /// Households after the period.
    pub closing_households: u64,
}

/// What the engine reports for the county at one close.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CountyPeriodFacts {
    /// The period just closed.
    pub period: u64,
    /// One entry for every configured crew, in the config's order.
    pub crews: Vec<CrewPeriodFacts>,
    /// One entry for every configured group, in the config's order.
    pub groups: Vec<GroupPeriodFacts>,
    /// The county's cash.
    #[serde(with = "super::decimal")]
    pub cash_micros: i128,
    /// The cash floor.
    #[serde(with = "super::decimal")]
    pub cash_floor_micros: i128,
    /// The spending limit.
    #[serde(with = "super::decimal")]
    pub spending_limit_micros: i128,
    /// The first class: every line that is not household support.
    #[serde(with = "super::decimal")]
    pub first_class_micros: i128,
}
