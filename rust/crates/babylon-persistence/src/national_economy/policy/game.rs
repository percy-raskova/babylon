//! Leaf implementation for the parent module; public paths stay on the parent.
use crate::national_economy::companies::CompanyPolicy;
use crate::national_economy::grain::NationalGrainError;
use crate::national_economy::grain::NationalGrainPolicy;

use super::admission;
use babylon_practice_contract::OrganizerSharingBasis;

use babylon_kernel::currency::Currency;
use babylon_kernel::economic_identity::{EconomicFunction, TradeSet};
use babylon_kernel::economic_location::ForeignCounterpart;
use babylon_kernel::geography::CountyGeoid;

use crate::national_household_allocation::HouseholdBudgetKey;
use babylon_material_circuit::{
    CommodityKind, GoodId, HouseholdLifecycleRates, HouseholdNeedBasis, UnitId, WantTier,
};

use crate::national_transport::CargoClass;
use babylon_practice_contract::OrganizerGiftConsent;
use babylon_practice_contract::OrganizerHearingDelegation;
use babylon_practice_contract::OrganizerHearingMandate;
use babylon_practice_contract::OrganizerPartnerPolicy;
use std::collections::BTreeMap;
use std::fmt::Formatter;
use std::fmt::Result as FmtResult;

/// One current policy decoded from captured bytes, independent of source paths.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NationalGamePolicy {
    pub grain: NationalGrainPolicy,
    pub companies: Option<CompanyPolicy>,
    pub source_digest: [u8; 32],
    /// Retained geographic identity basis, independent of new company policy parameters.
    pub grain_identity_policy_digest: [u8; 32],
    pub period_days: u64,
    pub work_hours_per_person: u64,
    /// Ten trades for schema 2 to 7, twelve for schema 8.
    pub trades: TradeSet,
    /// One wage for every workplace (schema 7 and earlier), or the observed wage of its trade and place.
    pub wages: GameWages,
    pub opening_pantry_periods: u64,
    pub opening_input_periods: u64,
    pub working_capital_periods: u64,
    pub retailer_buffer_periods: u64,
    pub resource_reserve_output_periods: u64,
    /// One handling figure for every good: `Some` under schema 7 and earlier; schema 8 writes it by good.
    pub handling_hours_per_unit: Option<u64>,
    pub missing_peer_weight_per_establishment: u64,
    pub household_enterprise_function: EconomicFunction,
    pub aid: GameAidPolicy,
    pub household_support_claimant: Option<GameHouseholdSupportClaimant>,
    /// Required from policy schema 7; names the City PD's books, not its engine lines.
    pub city_pd: Option<GameCityPdPolicy>,
    /// Required from policy schema 7; the county review's session terms and its three names.
    pub county_review: Option<GameCountyReviewPolicy>,
    pub organizer: GameOrganizerPolicy,
    pub financial: GameFinancialPolicy,
    pub households: GameHouseholdPolicy,
    pub household_time: GameHouseholdTimePolicy,
    pub household_lifecycle: Option<GameHouseholdLifecyclePolicy>,
    pub markets: GameMarketPolicy,
    pub equipment: GameEquipmentPolicy,
    pub commodities: BTreeMap<String, GameCommodity>,
    pub recipes: BTreeMap<EconomicFunction, GameRecipe>,
    pub household_needs: Vec<GameNeed>,
    /// What a household buys after its needs, sorted `(tier, key)`; empty under schema 7 and earlier.
    pub household_wants: Vec<GameWant>,
    /// The national fund's terms: `Some` exactly under schema 8.
    pub fund: Option<GameFundPolicy>,
    /// The public programs, in key order: three rows exactly under schema 8, none before.
    pub programs: Vec<GameProgram>,
    /// Accounts whose money passes their three tiers buy luxuries times a scale, sorted `(place, key)`.
    pub luxury_scales: Vec<GameLuxuryScale>,
    /// Period services a buyer takes only in its own place, sorted; empty before schema 8.
    pub place_services: Vec<String>,
    /// K1: period services bought and sold across the border by shares, sorted; empty before schema 8.
    pub crossing_services: Vec<String>,
    /// K2: period services sold across state lines, sorted; empty before schema 8.
    pub country_services: Vec<String>,
    /// K5: what the fund pays a part's funded public providers a period, sorted by part; empty before schema 8.
    pub place_grants: Vec<GamePlaceGrant>,
    /// The food figures that fold the counties into places: `Some` exactly under schema 8.
    pub map_basis: Option<GameMapBasis>,
    pub counterparts: BTreeMap<ForeignCounterpart, GameProfile>,
    pub dependency: GameDependencyProfile,
}

/// Designed allocation of the initially mixed ages within each published band.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum InitialAgeDistribution {
    UniformRemainingBirthdays,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameHouseholdLifecyclePolicy {
    pub rates: HouseholdLifecycleRates,
    pub initial_age_distribution: InitialAgeDistribution,
    /// Designed within the preexisting 16+ count in foreign and dependency markets.
    pub external_eligible_age_bps: [u16; 3],
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameCommodity {
    pub good_id: GoodId,
    pub unit_id: UnitId,
    pub label: String,
    pub unit_label: String,
    pub kind: CommodityKind,
    pub cargo: Option<CargoClass>,
    pub price: Option<GamePrice>,
    /// Retail handling of a storable good that households need or want: `Some` exactly under
    /// schema 8, and only for such a good.
    pub handling: Option<GameHandling>,
}

/// Retail handling of one shop good: `hours` of retail work for every `units` units.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GameHandling {
    pub hours: u64,
    pub units: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GamePrice {
    pub opening: Currency,
    pub minimum: Currency,
    pub maximum: Currency,
    pub step: Currency,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameRecipe {
    pub output: String,
    pub output_units_per_batch: u64,
    pub labor_hours_per_batch: u64,
    pub inputs: BTreeMap<String, u64>,
    /// The trade's margin over cost, in basis points: `Some` under schema 8 for every private trade.
    pub margin_bps: Option<u32>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameNeed {
    pub key: String,
    pub basis: HouseholdNeedBasis,
    pub units_per_basis: u64,
}

/// One want of a household account: a tier, a good and a count a person or a household.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameWant {
    pub key: String,
    pub tier: WantTier,
    pub basis: HouseholdNeedBasis,
    pub units_per_basis: u64,
}

/// The national fund's terms: one share of each tax, the same in every place unless a part has its own.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameFundPolicy {
    pub wage_tax_share_bps: u16,
    pub operating_income_tax_share_bps: u16,
    /// Periods of its payments the fund opens with.
    pub reserve_periods: u64,
    /// K4: the fund's share of both taxes collected in a part, by the part's label. Empty: the two shares above
    /// apply everywhere.
    pub share_by_part: BTreeMap<String, u16>,
}

/// K5: what the fund pays a part's funded public providers a period (D4).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GamePlaceGrant {
    pub part: String,
    pub amount_per_period: Currency,
}

/// The most an own-needs program's share may be: ten times the needs. Equal to the engine's
/// `MAX_PROGRAM_SHARE_BPS` (Task 4a); Task 4 asserts the two equal at compile time.
pub const MAX_GAME_PROGRAM_SHARE_BPS: u32 = 100_000;
/// The most bytes a policy's text may hold under schema 7 and earlier.
pub const MAX_POLICY_BYTES: usize = 65_536;
/// The most bytes a policy's text may hold under schema 8 (E4).
pub const MAX_POLICY_BYTES_SCHEMA_8: usize = 262_144;

/// What a public program pays.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GameProgramTerms {
    PerPerson {
        amount_per_person: Currency,
    },
    /// "The needs in full", times `share_bps / 10_000`: each recipient its own needs a person at its own
    /// sellers' posted opening prices, worked out by the compiler (E8, Task 4).
    OwnNeeds {
        share_bps: u32,
    },
    AfterLayoff {
        wage_share_bps: u16,
        half_periods: u16,
    },
}

/// Who a program pays at the opening.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameProgramRecipients {
    NoEarnerAtOpening,
    EarningOrResidenceAtOpening,
    CollectiveResidenceAtOpening,
}

/// One public program of the scenario.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameProgram {
    pub key: String,
    pub rank: u32,
    pub terms: GameProgramTerms,
    pub recipients: GameProgramRecipients,
}

/// An account whose money passes its three tiers buys its luxuries times `bps / 10_000`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameLuxuryScale {
    /// A domestic part's label (`<hub geoid>` or `<hub geoid>/<position>`), or a counterpart's or
    /// the dependency's key.
    pub place: String,
    pub key: HouseholdBudgetKey,
    pub bps: u32,
}

/// The food figures that fold the counties into places, written down so recipes can change.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GameMapBasis {
    pub food_labor_hours_per_batch: u64,
    pub food_output_units_per_batch: u64,
    pub food_units_per_person: u64,
    pub food_grams_per_unit: u64,
}

/// How a scenario sets the pay of its workplaces.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameWages {
    /// One designed wage for every workplace: schema 7 and earlier.
    Single(Currency),
    /// The observed wage of each trade in its place: schema 8.
    Observed,
}

impl GameWages {
    /// The one wage, when the scenario has one.
    #[must_use]
    pub const fn single(self) -> Option<Currency> {
        match self {
            Self::Single(wage) => Some(wage),
            Self::Observed => None,
        }
    }
}

/// The pay of a foreign region or the dependency.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameProfileWage {
    /// A designed wage per hour: schema 7 and earlier.
    PerHour(Currency),
    /// A designed fraction of the United States wage, in basis points: schema 8.
    FractionOfUnitedStates {
        /// Basis points of the United States wage, in `1..=10_000`.
        bps: u16,
    },
}

/// Statistical source population is not itself a labor-force observation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameProfile {
    pub participation_bps: u16,
    pub opening_employment_bps: u16,
    pub persons_per_household: u64,
    pub wage: GameProfileWage,
    pub price_scale_bps: u16,
    /// A buyer of this region's share bought from the United States, by product key: `Some` exactly
    /// under schema 8.
    pub export_bps: Option<BTreeMap<String, u16>>,
    /// `Ord` order of the scenario's trades (ten or twelve rows), independent of ownership or class.
    pub function_weights_bps: Vec<u16>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameDependencyProfile {
    pub profile: GameProfile,
    pub missing_population_game_persons: u64,
}

/// Designed ownership exposure among historical household-earnings margins.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameHouseholdPolicy {
    pub private_owner_households_bps: u16,
    /// The share of earning households in the better-paid account; `Some` only under schema 8.
    pub next_forty_households_bps: Option<u16>,
}

/// Designed rates and budget commitments; payments still require actual funds.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameFinancialPolicy {
    pub wage_tax_bps: u16,
    pub operating_income_tax_bps: u16,
    pub private_distribution_bps: u16,
    pub reserve_food_support_periods: u64,
    pub cross_border_ownership_bps: u16,
}

/// Designed resident time commitments; neither wages nor political consent.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameHouseholdTimePolicy {
    pub hours_per_eligible_person: u64,
    pub ordinary_protected_hours_per_household: u64,
    pub ordinary_provisioning_hours_per_household: u64,
    pub collective_protected_hours_per_person: u64,
    pub collective_provisioning_hours_per_person: u64,
    pub external_eligible_persons_bps: u16,
    pub unmet_hours_per_unit: BTreeMap<String, u64>,
}

/// Finite productive use and installation requirements, independent of the horizon.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameEquipmentPolicy {
    pub machines: GameMachines,
    pub installation_hours_per_unit: u64,
    pub installation_inputs: BTreeMap<String, u64>,
    pub installation_workforce_hours_bps: u16,
    pub expansion_earnings_fraction_bps: u16,
}

/// Machines of the scenario.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GameMachines {
    /// Schema 7 and earlier.
    Batches {
        batches_per_unit_per_period: u64,
        service_batches_per_unit: u64,
        opening_remaining_service_bps: [u16; 4],
    },
    /// Schema 8: workers per machine by trade, one life for all.
    Workers {
        workers_per_machine: BTreeMap<EconomicFunction, u64>,
        life_periods: u64,
    },
}

/// Disjoint fixed person pools; no jobs are converted into additional people.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ResidentOpeningCounts {
    pub persons: u64,
    pub households: u64,
    pub employed: u64,
    pub reserve: u64,
    pub inactive: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NationalGamePolicyError {
    Grain(NationalGrainError),
    Syntax,
    Bounds,
    Evidence,
    Shape,
    Commodity(String),
    Recipe(String),
    HouseholdNeed(String),
    Profile(String),
    Location,
    Arithmetic,
}

impl std::fmt::Display for NationalGamePolicyError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FmtResult {
        write!(f, "national game policy refused: {self:?}")
    }
}

impl std::error::Error for NationalGamePolicyError {}

impl NationalGamePolicy {
    /// Decode the singular captured policy; never reads a current filesystem path.
    /// # Errors
    /// Refuses unsupported versions, missing declarations, ambiguous units and overflow.
    pub fn from_captured_bytes(bytes: &[u8]) -> Result<Self, NationalGamePolicyError> {
        if bytes.len() > MAX_POLICY_BYTES_SCHEMA_8 {
            return Err(NationalGamePolicyError::Bounds);
        }
        let text = std::str::from_utf8(bytes).map_err(|_| {
            if bytes.len() > MAX_POLICY_BYTES {
                NationalGamePolicyError::Bounds
            } else {
                NationalGamePolicyError::Syntax
            }
        })?;
        Self::parse(text)
    }

    /// Decode authoring text using the same strict admission as saved captures.
    /// # Errors
    /// Refuses unknown fields, invalid prices, false evidence and unsupported service dependencies.
    pub fn parse(source: &str) -> Result<Self, NationalGamePolicyError> {
        admission::parse(source)
    }
}

impl GameProfile {
    /// Allocate this explicitly Designed fixed workforce within the supplied persons.
    /// # Errors
    /// Refuses a zero population or unrepresentable current-period person-hours.
    pub fn opening_counts(
        &self,
        persons: u64,
    ) -> Result<ResidentOpeningCounts, NationalGamePolicyError> {
        if persons == 0
            || self.persons_per_household == 0
            || !(1..=10_000).contains(&self.participation_bps)
            || self.opening_employment_bps > 10_000
        {
            return Err(NationalGamePolicyError::Profile(
                "invalid resident or workforce control".to_owned(),
            ));
        }
        let force =
            u64::try_from(u128::from(persons) * u128::from(self.participation_bps) / 10_000)
                .map_err(|_| NationalGamePolicyError::Arithmetic)?;
        let employed =
            u64::try_from(u128::from(force) * u128::from(self.opening_employment_bps) / 10_000)
                .map_err(|_| NationalGamePolicyError::Arithmetic)?;
        // A future compiler cannot accept a population whose largest allowed
        // 28-day work schedule could overflow its u64 labor-time accounts.
        force
            .checked_mul(28 * 24)
            .ok_or(NationalGamePolicyError::Arithmetic)?;
        Ok(ResidentOpeningCounts {
            persons,
            households: persons.div_ceil(self.persons_per_household),
            employed,
            reserve: force
                .checked_sub(employed)
                .ok_or(NationalGamePolicyError::Arithmetic)?,
            inactive: persons
                .checked_sub(force)
                .ok_or(NationalGamePolicyError::Arithmetic)?,
        })
    }
}

impl GamePrice {
    /// Apply a captured common-currency price scale, rounded to exact micro-units.
    /// This changes an opening offer, not an exchange rate or a population source.
    /// # Errors
    /// Refuses zero scale, invalid prices or arithmetic overflow.
    pub fn scaled(&self, scale_bps: u16) -> Result<Self, NationalGamePolicyError> {
        let scale = |price: Currency| {
            let product = price
                .micro_units()
                .checked_mul(i128::from(scale_bps))
                .ok_or(NationalGamePolicyError::Arithmetic)?;
            let micros = babylon_kernel::currency::round_half_even_div(product, 10_000);
            if micros <= 0 {
                return Err(NationalGamePolicyError::Profile(
                    "invalid price scale".to_owned(),
                ));
            }
            Ok(Currency::from_micro_units(micros))
        };
        if scale_bps == 0
            || self.minimum.micro_units() <= 0
            || self.step.micro_units() <= 0
            || self.minimum > self.opening
            || self.opening > self.maximum
        {
            return Err(NationalGamePolicyError::Profile(
                "invalid price scale".to_owned(),
            ));
        }
        Ok(Self {
            opening: scale(self.opening)?,
            minimum: scale(self.minimum)?,
            maximum: scale(self.maximum)?,
            step: scale(self.step)?,
        })
    }
}

/// Captured trade sourcing and coarse journey conventions, not observed flows.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameMarketPolicy {
    pub procurement: GameProcurement,
    /// What a household buys first and last; `Some` only under schema 8.
    pub paying_order: Option<Vec<String>>,
    pub journey_timing: GameJourneyTiming,
    pub service_reach: GameServiceReach,
}

/// How much of each storable good a buyer may take from abroad.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GameProcurement {
    /// One cap for every good and both directions: schema 7 and earlier.
    Single(u16),
    /// Schema 8: a domestic buyer's share bought abroad, by product key.
    ByProduct { import_bps: BTreeMap<String, u16> },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameJourneyTiming {
    SlowestProfile,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GameServiceReach {
    SameStateOrOwnCounterpart,
}

/// Designed counted subset of Wayne's no-earner nonowner households.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GameHouseholdSupportClaimant {
    pub county: CountyGeoid,
    pub households: u64,
    pub reserve_persons: u64,
}

/// Designed City PD terms: its positions, sourced, and the visits its appropriation pays for.
/// The wage is the scenario's wage and the payroll is worked out from it, never written here.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameCityPdPolicy {
    pub positions: u64,
    pub positions_source: String,
    pub visits_per_period: u64,
    pub visit_hours: u64,
}

/// Designed county review terms: the first session, what a session and a bringing cost in hours,
/// and the names of the administration and the two bodies that come to it. The price of a unit is
/// worked out from the opening and never written here.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GameCountyReviewPolicy {
    pub county: CountyGeoid,
    pub first_session_period: u64,
    pub session_hours: u64,
    pub bring_hours: u64,
    pub administration_label: String,
    pub claimants_body_label: String,
    pub aid_body_label: String,
}

/// Captured Designed gift terms; ordinary market prices remain independent.
#[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GameAidPolicy {
    pub evidence_class: String,
    pub donor_actor: u64,
    pub local_recipient_actor: u64,
    pub remote_recipient_actor: u64,
    pub donor_contributor_id: u64,
    pub local_recipient_contributor_id: u64,
    pub remote_recipient_contributor_id: u64,
    pub organization_opening_cash_micros: i128,
    pub maximum_cash_micros: i128,
    pub initial_food_quantity: u64,
    pub initial_cash_micros: i128,
    pub local_cash_receiving_consent: OrganizerGiftConsent,
    pub remote_cash_receiving_consent: OrganizerGiftConsent,
    pub fulfillment_hours_per_unit: u64,
    pub maximum_quantity: u64,
}

/// Authored reader of the public workplace visitor log.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum VenueLogReader {
    ControlledOrganizer,
    WorkplaceCommittee,
}

/// Designed political consent and time promises; actual supply remains household time.
#[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GameOrganizerPolicy {
    pub hearing: Option<GameHearingPolicy>,
    pub local_report_sharing: GamePartnerReportSharing,
    pub remote_report_sharing: GamePartnerReportSharing,
    pub evidence_class: String,
    pub venue_log_reader: VenueLogReader,
    pub organization_label: String,
    pub workplace_partner_label: String,
    pub neighborhood_partner_label: String,
    pub local_partner_label: String,
    pub remote_partner_label: String,
    pub contributor_hours_cap: u64,
    pub inquiry_hours: u64,
    pub contact_hours: u64,
    pub partner_response_hours: u64,
    pub aid_coordination_hours: u64,
    pub initial_agreement_through_period: u64,
    pub contact_renewal_periods: u64,
    pub local_receiving_consent: OrganizerGiftConsent,
    pub remote_receiving_consent: OrganizerGiftConsent,
    pub collection_cash_consent: OrganizerGiftConsent,
    pub collection_initial_cash_micros: i128,
    pub collection_maximum_cash_micros: i128,
    pub collection_protected_cash_floor_micros: i128,
    pub collection_hours: u64,
    pub workplace_policy: OrganizerPartnerPolicy,
    pub neighborhood_policy: OrganizerPartnerPolicy,
    pub local_policy: OrganizerPartnerPolicy,
    pub remote_policy: OrganizerPartnerPolicy,
}

/// Designed membership instructions for one relief hearing. Settlement grants review access.
#[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GameHearingPolicy {
    pub evidence_class: String,
    pub county_geoid: String,
    pub period: u64,
    pub review_period: u64,
    pub claimant_label: String,
    pub claimant_claim: String,
    pub partner_claim: String,
    pub attendance_hours: u64,
    pub claimant_mandate: OrganizerHearingMandate,
    pub partner_mandate: OrganizerHearingMandate,
    pub claimant_delegation: OrganizerHearingDelegation,
    pub partner_delegation: OrganizerHearingDelegation,
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GamePartnerReportSharing {
    pub evidence_class: OrganizerSharingBasis,
    pub food: Vec<String>,
    pub essential_services: Vec<String>,
    pub participation_time: bool,
}
